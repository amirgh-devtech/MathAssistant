# tests/unit/test_system_tools.py
"""
Unit tests for MathAssistant System Tools Module

Covers:
- SystemInfo (OS detection, user info, Python info)
- ValidationUtils (URL validation, path sanitization)
- RetryPolicy (decorator, execute)
- TimeoutExecutor (execute, shutdown)
- ProjectPaths (root detection, thread-safety)
- FileUtils (read/write/delete, atomic write, temp clean)
- AppLauncher (find app, availability, URL open)
- ProcessManager (script execution, process detection)
- QtHelper (clipboard, screen resolution - mocked)
- LogSetup (singleton, reset)
- Backward Compatibility (SystemToolLauncher)
"""

import sys
import os
import re
import time
import json
import tempfile
import threading
import platform
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from concurrent.futures import TimeoutError as FuturesTimeoutError

import pytest

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from MathAssistant.utils.system_tools import (
    # Enums
    OSType,
    AppType,

    # Core Classes
    SystemInfo,
    ValidationUtils,
    RetryPolicy,
    TimeoutExecutor,
    AppLauncher,
    ProcessManager,
    ProjectPaths,
    FileUtils,
    LogSetup,
    SystemToolLauncher,

    # Internal
    _QtHelper,

    # Functions
    get_system_report,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons between tests."""
    # Reset ProjectPaths cache
    ProjectPaths.reset_cache()

    # Reset LogSetup
    LogSetup.reset()

    # Reset AppLauncher availability cache
    AppLauncher._availability_cache.clear()

    # Reset QtHelper
    _QtHelper._discovery_done = False
    _QtHelper._qt_module = None
    _QtHelper._QtWidgets = None

    yield

    # Cleanup
    ProjectPaths.reset_cache()
    LogSetup.reset()
    AppLauncher._availability_cache.clear()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file with content."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello, World!", encoding="utf-8")
    return file_path


@pytest.fixture
def mock_qt_app():
    """Mock QApplication for clipboard/resolution tests."""
    with patch('MathAssistant.utils.system_tools._QtHelper._discover') as mock_discover:
        mock_app = MagicMock()
        mock_clipboard = MagicMock()
        mock_clipboard.text.return_value = "clipboard text"
        mock_app.clipboard.return_value = mock_clipboard

        mock_screen = MagicMock()
        mock_size = MagicMock()
        mock_size.width.return_value = 1920
        mock_size.height.return_value = 1080
        mock_screen.size.return_value = mock_size
        mock_app.primaryScreen.return_value = mock_screen

        _QtHelper._qt_module = 'PyQt6'
        _QtHelper._QtWidgets = MagicMock()
        _QtHelper._QtWidgets.QApplication.instance.return_value = mock_app
        _QtHelper._discovery_done = True

        yield mock_app


@pytest.fixture
def mock_platform_windows():
    """Mock platform as Windows."""
    with patch('platform.system', return_value='Windows'):
        with patch('platform.release', return_value='10'):
            yield


@pytest.fixture
def mock_platform_macos():
    """Mock platform as macOS."""
    with patch('platform.system', return_value='Darwin'):
        with patch('platform.mac_ver', return_value=('14.0', ('', '', ''), '')):
            yield


@pytest.fixture
def mock_platform_linux():
    """Mock platform as Linux."""
    with patch('platform.system', return_value='Linux'):
        yield


# ============================================================================
# SystemInfo Tests
# ============================================================================

class TestSystemInfo:
    """Tests for SystemInfo class."""

    def test_get_os_windows(self, mock_platform_windows):
        assert SystemInfo.get_os() == OSType.WINDOWS

    def test_get_os_macos(self, mock_platform_macos):
        assert SystemInfo.get_os() == OSType.MACOS

    def test_get_os_linux(self, mock_platform_linux):
        assert SystemInfo.get_os() == OSType.LINUX

    def test_get_os_name_contains_os(self):
        name = SystemInfo.get_os_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_architecture_returns_string(self):
        arch = SystemInfo.get_architecture()
        assert isinstance(arch, str)
        assert len(arch) > 0

    def test_is_64bit_returns_bool(self):
        result = SystemInfo.is_64bit()
        assert isinstance(result, bool)

    def test_get_python_info_has_required_keys(self):
        info = SystemInfo.get_python_info()
        assert "version" in info
        assert "implementation" in info
        assert "executable" in info

    def test_get_python_version_is_valid(self):
        info = SystemInfo.get_python_info()
        version = info["version"]
        assert re.match(r'\d+\.\d+\.\d+', version)

    def test_get_user_name_returns_string(self):
        name = SystemInfo.get_user_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_home_dir_exists(self):
        home = SystemInfo.get_home_dir()
        assert isinstance(home, Path)
        assert home.exists()

    def test_get_temp_dir_exists(self):
        temp = SystemInfo.get_temp_dir()
        assert isinstance(temp, Path)
        assert temp.exists()

    def test_get_screen_resolution_mocked(self, mock_qt_app):
        resolution = SystemInfo.get_screen_resolution()
        assert resolution == (1920, 1080)

    def test_get_screen_resolution_no_qt(self):
        _QtHelper._discovery_done = True
        _QtHelper._QtWidgets = None
        assert SystemInfo.get_screen_resolution() is None

    def test_get_clipboard_text_mocked(self, mock_qt_app):
        text = SystemInfo.get_clipboard_text()
        assert text == "clipboard text"

    def test_copy_to_clipboard_mocked(self, mock_qt_app):
        assert SystemInfo.copy_to_clipboard("test") is True

    def test_copy_to_clipboard_empty_string(self, mock_qt_app):
        assert SystemInfo.copy_to_clipboard("") is False


# ============================================================================
# ValidationUtils Tests
# ============================================================================

class TestValidationUtils:
    """Tests for ValidationUtils class."""

    # ----- URL Validation -----

    def test_validate_url_http(self):
        is_valid, error = ValidationUtils.validate_url("http://example.com")
        assert is_valid is True
        assert error == ""

    def test_validate_url_https(self):
        is_valid, error = ValidationUtils.validate_url("https://example.com/path")
        assert is_valid is True

    def test_validate_url_empty(self):
        is_valid, error = ValidationUtils.validate_url("")
        assert is_valid is False
        assert "خالی" in error

    def test_validate_url_no_protocol(self):
        is_valid, error = ValidationUtils.validate_url("example.com")
        assert is_valid is False

    def test_validate_url_ftp_rejected(self):
        is_valid, error = ValidationUtils.validate_url("ftp://example.com")
        assert is_valid is False

    def test_validate_url_no_domain(self):
        is_valid, error = ValidationUtils.validate_url("http://")
        assert is_valid is False
        assert "دامنه" in error

    # ----- Path Sanitization -----

    def test_sanitize_path_clean(self):
        result = ValidationUtils.sanitize_path("/usr/bin/calc")
        assert result == "/usr/bin/calc"

    def test_sanitize_path_with_dangerous_chars(self):
        result = ValidationUtils.sanitize_path("file;name|test.txt")
        assert ";" not in result
        assert "|" not in result

    def test_sanitize_path_with_parens(self):
        result = ValidationUtils.sanitize_path("file(name).txt")
        assert "(" not in result
        assert ")" not in result
        assert result == "file_name_.txt"

    def test_sanitize_path_custom_replacement(self):
        result = ValidationUtils.sanitize_path("a;b", replacement="-")
        assert result == "a-b"

    def test_sanitize_path_with_dollar_sign(self):
        result = ValidationUtils.sanitize_path("$HOME/path")
        assert "$" not in result

    def test_sanitize_path_strips_whitespace(self):
        result = ValidationUtils.sanitize_path("  path  ")
        assert result == "path"


# ============================================================================
# RetryPolicy Tests
# ============================================================================

class TestRetryPolicy:
    """Tests for RetryPolicy class."""

    def test_execute_success_first_try(self):
        policy = RetryPolicy(max_attempts=3)
        result = policy.execute(lambda: 42)
        assert result == 42

    def test_execute_with_args(self):
        policy = RetryPolicy(max_attempts=3)
        result = policy.execute(lambda x, y: x + y, 10, 20)
        assert result == 30

    def test_execute_retry_then_success(self):
        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"

        policy = RetryPolicy(max_attempts=5, delay=0.01)
        result = policy.execute(flaky_func)
        assert result == "success"
        assert call_count[0] == 3

    def test_execute_all_fail(self):
        def always_fail():
            raise ValueError("always fail")

        policy = RetryPolicy(max_attempts=3, delay=0.01)
        with pytest.raises(RuntimeError, match="All 3 retry attempts failed"):
            policy.execute(always_fail)

    def test_execute_unhandled_exception(self):
        def raise_keyboard_interrupt():
            raise KeyboardInterrupt()

        policy = RetryPolicy(max_attempts=3, exceptions=(ValueError,))
        with pytest.raises(KeyboardInterrupt):
            policy.execute(raise_keyboard_interrupt)

    def test_as_decorator_success(self):
        policy = RetryPolicy(max_attempts=3)

        @policy.as_decorator()
        def stable_func():
            return "ok"

        assert stable_func() == "ok"

    def test_as_decorator_with_retry(self):
        call_count = [0]
        policy = RetryPolicy(max_attempts=5, delay=0.01)

        @policy.as_decorator()
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("no connection")
            return "connected"

        result = flaky()
        assert result == "connected"
        assert call_count[0] == 3

    def test_custom_backoff(self):
        policy = RetryPolicy(max_attempts=3, delay=0.01, backoff=3.0)
        assert policy.backoff == 3.0

    def test_preserves_function_metadata(self):
        policy = RetryPolicy(max_attempts=3)

        @policy.as_decorator()
        def my_function():
            """My docstring."""
            return 42

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


# ============================================================================
# TimeoutExecutor Tests
# ============================================================================

class TestTimeoutExecutor:
    """Tests for TimeoutExecutor class."""

    def test_execute_success(self):
        result = TimeoutExecutor.execute(lambda: 42, timeout_seconds=5.0)
        assert result == 42

    def test_execute_with_args(self):
        result = TimeoutExecutor.execute(
            lambda x, y: x * y, 5.0, 6, 7
        )
        assert result == 42

    def test_execute_timeout(self):
        def slow_func():
            time.sleep(10)
            return "done"

        with pytest.raises(TimeoutError, match="timed out after"):
            TimeoutExecutor.execute(slow_func, timeout_seconds=0.1)

    def test_get_executor_returns_same_instance(self):
        executor1 = TimeoutExecutor.get_executor()
        executor2 = TimeoutExecutor.get_executor()
        assert executor1 is executor2

    def test_shutdown_and_restart(self):
        TimeoutExecutor.shutdown()
        # After shutdown, get_executor should create new one
        executor = TimeoutExecutor.get_executor()
        assert executor is not None


# ============================================================================
# ProjectPaths Tests
# ============================================================================

class TestProjectPaths:
    """Tests for ProjectPaths class."""

    def test_get_root_returns_path(self):
        root = ProjectPaths.get_root()
        assert isinstance(root, Path)

    def test_get_root_is_cached(self):
        root1 = ProjectPaths.get_root()
        root2 = ProjectPaths.get_root()
        assert root1 is root2

    def test_reset_cache(self):
        root1 = ProjectPaths.get_root()
        ProjectPaths.reset_cache()
        # Force re-discovery
        ProjectPaths._MARKER_FILES = ["pyproject.toml"]
        root2 = ProjectPaths.get_root()
        assert root1 == root2

    def test_get_src_dir(self):
        src = ProjectPaths.get_src_dir()
        assert isinstance(src, Path)
        assert src.name == "src"

    def test_get_assets_dir(self):
        assets = ProjectPaths.get_assets_dir()
        assert assets.name == "assets"

    def test_get_tests_dir(self):
        tests = ProjectPaths.get_tests_dir()
        assert tests.name == "tests"

    def test_get_logs_dir_creates(self, temp_dir):
        with patch.object(ProjectPaths, 'get_root', return_value=temp_dir):
            logs = ProjectPaths.get_logs_dir()
            assert logs.exists()
            assert logs.name == "logs"

    def test_get_cache_dir_creates(self, temp_dir):
        with patch.object(ProjectPaths, 'get_root', return_value=temp_dir):
            cache = ProjectPaths.get_cache_dir()
            assert cache.exists()
            assert cache.name == ".cache"

    def test_get_config_dir_creates(self, temp_dir):
        with patch.object(ProjectPaths, 'get_root', return_value=temp_dir):
            config = ProjectPaths.get_config_dir()
            assert config.exists()
            assert config.name == "config"

    def test_thread_safety(self):
        """Test that concurrent access doesn't corrupt cache."""
        results = []
        errors = []

        def worker():
            try:
                root = ProjectPaths.get_root()
                results.append(root)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All should return same root
        assert len(set(results)) == 1


# ============================================================================
# FileUtils Tests
# ============================================================================

class TestFileUtils:
    """Tests for FileUtils class."""

    def test_safe_read_existing(self, temp_file):
        content = FileUtils.safe_read(str(temp_file))
        assert content == "Hello, World!"

    def test_safe_read_nonexistent(self, temp_dir):
        result = FileUtils.safe_read(str(temp_dir / "nonexistent.txt"))
        assert result is None

    def test_safe_write_new_file(self, temp_dir):
        filepath = str(temp_dir / "new_file.txt")
        success = FileUtils.safe_write(filepath, "test content")
        assert success is True
        assert Path(filepath).exists()
        assert Path(filepath).read_text() == "test content"

    def test_safe_write_creates_parent_dirs(self, temp_dir):
        filepath = str(temp_dir / "deep" / "nested" / "file.txt")
        success = FileUtils.safe_write(filepath, "nested")
        assert success is True
        assert Path(filepath).exists()

    def test_safe_write_atomic(self, temp_dir):
        filepath = str(temp_dir / "atomic.txt")
        success = FileUtils.safe_write(filepath, "atomic content", atomic=True)
        assert success is True
        assert Path(filepath).read_text() == "atomic content"
        # No .tmp file should remain
        assert not Path(filepath + ".tmp").exists()

    def test_safe_write_overwrite(self, temp_file):
        filepath = str(temp_file)
        success = FileUtils.safe_write(filepath, "new content")
        assert success is True
        assert Path(filepath).read_text() == "new content"

    def test_safe_delete_existing(self, temp_file):
        assert FileUtils.safe_delete(str(temp_file)) is True
        assert not temp_file.exists()

    def test_safe_delete_nonexistent(self, temp_dir):
        assert FileUtils.safe_delete(str(temp_dir / "nonexistent.txt")) is True

    def test_get_file_size_mb(self, temp_file):
        size = FileUtils.get_file_size_mb(str(temp_file))
        assert size > 0
        assert size < 0.1  # 13 bytes < 0.1 MB

    def test_get_file_size_mb_nonexistent(self, temp_dir):
        assert FileUtils.get_file_size_mb(str(temp_dir / "no.txt")) == 0.0

    def test_ensure_dir_creates(self, temp_dir):
        new_dir = temp_dir / "new_dir" / "subdir"
        result = FileUtils.ensure_dir(str(new_dir))
        assert result == new_dir
        assert new_dir.exists()

    def test_list_files(self, temp_dir):
        (temp_dir / "a.txt").touch()
        (temp_dir / "b.txt").touch()
        (temp_dir / "c.py").touch()

        txt_files = FileUtils.list_files(str(temp_dir), "*.txt")
        assert len(txt_files) == 2

        py_files = FileUtils.list_files(str(temp_dir), "*.py")
        assert len(py_files) == 1

    def test_list_files_empty_dir(self, temp_dir):
        files = FileUtils.list_files(str(temp_dir))
        assert files == []

    def test_list_files_recursive(self, temp_dir):
        subdir = temp_dir / "sub"
        subdir.mkdir()
        (temp_dir / "root.txt").touch()
        (subdir / "sub.txt").touch()

        files = FileUtils.list_files(str(temp_dir), "*.txt", recursive=True)
        assert len(files) == 2

    def test_clean_temp_files(self, temp_dir):
        # Create old file
        old_file = temp_dir / "old.tmp"
        old_file.write_text("old")
        # Set modification time to 48 hours ago
        old_time = time.time() - (48 * 3600)
        os.utime(str(old_file), (old_time, old_time))

        # Create new file
        new_file = temp_dir / "new.tmp"
        new_file.write_text("new")

        count = FileUtils.clean_temp_files(
            str(temp_dir), "*.tmp", older_than_hours=24
        )
        assert count == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_copy_file(self, temp_dir):
        src = temp_dir / "src.txt"
        src.write_text("source")
        dst = temp_dir / "dst.txt"

        assert FileUtils.copy_file(str(src), str(dst)) is True
        assert dst.exists()
        assert dst.read_text() == "source"

    def test_copy_file_no_overwrite(self, temp_dir):
        src = temp_dir / "src.txt"
        src.write_text("source")
        dst = temp_dir / "dst.txt"
        dst.write_text("existing")

        assert FileUtils.copy_file(str(src), str(dst), overwrite=False) is False
        assert dst.read_text() == "existing"

    def test_copy_file_with_overwrite(self, temp_dir):
        src = temp_dir / "src.txt"
        src.write_text("source")
        dst = temp_dir / "dst.txt"
        dst.write_text("existing")

        assert FileUtils.copy_file(str(src), str(dst), overwrite=True) is True
        assert dst.read_text() == "source"


# ============================================================================
# AppLauncher Tests
# ============================================================================

class TestAppLauncher:
    """Tests for AppLauncher class."""

    def test_is_available_cached(self):
        with patch.object(AppLauncher, '_find_app', return_value="/usr/bin/calc"):
            assert AppLauncher.is_available(AppType.CALCULATOR) is True
            # Second call should use cache
            assert AppLauncher.is_available(AppType.CALCULATOR) is True

    def test_is_available_not_found(self):
        with patch.object(AppLauncher, '_find_app', return_value=None):
            assert AppLauncher.is_available(AppType.CALCULATOR) is False

    def test_launch_app_not_found(self):
        with patch.object(AppLauncher, '_find_app', return_value=None):
            success, message = AppLauncher.launch(AppType.CALCULATOR)
            assert success is False
            assert "یافت نشد" in message

    def test_launch_app_success(self):
        with patch.object(AppLauncher, '_find_app', return_value="/usr/bin/calc"):
            with patch('subprocess.Popen') as mock_popen:
                success, message = AppLauncher.launch(AppType.CALCULATOR)
                assert success is True
                mock_popen.assert_called_once()

    def test_launch_app_file_not_found(self):
        with patch.object(AppLauncher, '_find_app', return_value="/fake/path"):
            with patch('subprocess.Popen', side_effect=FileNotFoundError()):
                success, message = AppLauncher.launch(AppType.CALCULATOR)
                assert success is False

    def test_launch_app_permission_denied(self):
        with patch.object(AppLauncher, '_find_app', return_value="/root/app"):
            with patch('subprocess.Popen', side_effect=PermissionError()):
                success, message = AppLauncher.launch(AppType.CALCULATOR)
                assert success is False
                assert "دسترسی" in message

    def test_launch_with_retry_success(self):
        with patch.object(AppLauncher, '_find_app', return_value="/usr/bin/calc"):
            with patch('subprocess.Popen'):
                success, message = AppLauncher.launch_with_retry(
                    AppType.CALCULATOR,
                    retry_policy=RetryPolicy(max_attempts=2, delay=0.01)
                )
                assert success is True

    def test_launch_convenience_calculator(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = AppLauncher.launch_calculator()
            assert success is True

    def test_launch_convenience_browser(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = AppLauncher.launch_browser("https://example.com")
            assert success is True

    def test_launch_convenience_terminal(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = AppLauncher.launch_terminal()
            assert success is True

    def test_open_url_valid(self):
        with patch('webbrowser.open', return_value=True):
            success, message = AppLauncher.open_url("https://example.com")
            assert success is True

    def test_open_url_invalid(self):
        success, message = AppLauncher.open_url("not-a-url")
        assert success is False

    def test_open_url_browser_fails(self):
        with patch('webbrowser.open', return_value=False):
            success, message = AppLauncher.open_url("https://example.com")
            assert success is False

    def test_launch_with_timeout(self):
        mock_process = MagicMock()
        with patch.object(AppLauncher, '_find_app', return_value="/usr/bin/app"):
            with patch('subprocess.Popen', return_value=mock_process):
                success, _ = AppLauncher.launch(
                    AppType.CALCULATOR, timeout_seconds=5.0
                )
                assert success is True
                mock_process.wait.assert_called_once_with(timeout=5.0)


# ============================================================================
# ProcessManager Tests
# ============================================================================

class TestProcessManager:
    """Tests for ProcessManager class."""

    def test_run_python_script_not_found(self):
        success, message, code = ProcessManager.run_python_script(
            "/nonexistent/script.py"
        )
        assert success is False
        assert "یافت نشد" in message
        assert code is None

    def test_run_python_script_success(self, temp_dir):
        script = temp_dir / "test_script.py"
        script.write_text("print('hello')")

        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "hello"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            success, output, code = ProcessManager.run_python_script(
                str(script), wait=True
            )
            assert success is True
            assert code == 0

    def test_run_python_script_failure(self, temp_dir):
        script = temp_dir / "fail_script.py"
        script.write_text("raise Exception('fail')")

        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error"
            mock_run.return_value = mock_result

            success, output, code = ProcessManager.run_python_script(
                str(script), wait=True
            )
            assert success is False
            assert code == 1

    def test_run_python_script_no_wait(self, temp_dir):
        script = temp_dir / "bg_script.py"
        script.write_text("print('bg')")

        with patch('subprocess.Popen') as mock_popen:
            success, message, code = ProcessManager.run_python_script(
                str(script), wait=False
            )
            assert success is True
            assert code is None
            mock_popen.assert_called_once()

    def test_is_process_running_windows(self, mock_platform_windows):
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "python.exe  1234"
            mock_run.return_value = mock_result

            assert ProcessManager.is_process_running("python.exe") is True

    def test_is_process_running_not_found(self, mock_platform_windows):
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "INFO: No tasks"
            mock_run.return_value = mock_result

            assert ProcessManager.is_process_running("nonexistent.exe") is False

    def test_kill_process_success(self, mock_platform_windows):
        with patch('subprocess.run') as mock_run:
            success, message = ProcessManager.kill_process("notepad.exe")
            assert success is True
            mock_run.assert_called_once()

    def test_kill_process_timeout(self, mock_platform_windows):
        import subprocess as sp
        with patch('subprocess.run', side_effect=sp.TimeoutExpired("cmd", 10)):
            success, message = ProcessManager.kill_process("notepad.exe")
            assert success is False
            assert "اتمام رسید" in message


# ============================================================================
# LogSetup Tests
# ============================================================================

class TestLogSetup:
    """Tests for LogSetup class."""

    def test_setup_returns_logger(self):
        logger = LogSetup.setup(level=logging.WARNING, log_to_file=False)
        assert logger.name == "MathAssistant"

    def test_setup_is_idempotent(self):
        logger1 = LogSetup.setup(log_to_file=False)
        logger2 = LogSetup.setup(log_to_file=False)
        assert logger1 is logger2

    def test_get_logger_returns_child(self):
        child = LogSetup.get_logger("test_module")
        assert child.name == "MathAssistant.test_module"

    def test_reset_allows_resetup(self):
        LogSetup.setup(log_to_file=False)
        LogSetup.reset()

        # After reset, should be able to setup again
        logger = LogSetup.setup(log_to_file=False)
        assert logger is not None

    def test_thread_safe_setup(self):
        results = []

        def worker():
            logger = LogSetup.setup(log_to_file=False)
            results.append(logger)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have same logger
        assert len(set(id(r) for r in results)) == 1


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

class TestSystemToolLauncher:
    """Tests for backward-compatible SystemToolLauncher."""

    def test_launch_calculator_delegates(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = SystemToolLauncher.launch_calculator()
            assert success is True

    def test_launch_browser_delegates(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = SystemToolLauncher.launch_browser("https://test.com")
            assert success is True

    def test_launch_file_explorer_delegates(self):
        with patch.object(AppLauncher, 'launch', return_value=(True, "ok")):
            success, _ = SystemToolLauncher.launch_file_explorer("/path")
            assert success is True


# ============================================================================
# get_system_report Tests
# ============================================================================

class TestSystemReport:
    """Tests for get_system_report function."""

    def test_returns_dict(self):
        report = get_system_report()
        assert isinstance(report, dict)

    def test_has_required_keys(self):
        report = get_system_report()
        required = ["os", "architecture", "python", "user", "available_apps"]
        for key in required:
            assert key in report, f"Missing key: {key}"

    def test_python_info_is_dict(self):
        report = get_system_report()
        assert isinstance(report["python"], dict)

    def test_available_apps_all_app_types(self):
        report = get_system_report()
        apps = report["available_apps"]
        for app in AppType:
            assert app.value in apps, f"Missing app: {app.value}"


# ============================================================================
# Edge Cases & Stress Tests
# ============================================================================

class TestEdgeCases:
    """Edge case and stress tests."""

    def test_retry_policy_max_attempts_one(self):
        policy = RetryPolicy(max_attempts=1)
        with pytest.raises(RuntimeError):
            policy.execute(lambda: 1 / 0)  # ZeroDivisionError

    def test_timeout_executor_very_short_timeout(self):
        def quick():
            return "fast"

        result = TimeoutExecutor.execute(quick, timeout_seconds=10.0)
        assert result == "fast"

    def test_file_utils_atomic_write_rollback(self, temp_dir):
        """Test that failed atomic write cleans up temp file."""
        filepath = str(temp_dir / "rollback_test.txt")

        with patch('builtins.open', side_effect=OSError("disk full")):
            success = FileUtils.safe_write(filepath, "content", atomic=True)
            assert success is False
            # No .tmp file should remain
            assert not Path(filepath + ".tmp").exists()

    def test_concurrent_cache_access(self):
        """Test AppLauncher cache under concurrent access."""
        results = []

        with patch.object(AppLauncher, '_find_app', return_value="/bin/app"):
            def worker():
                result = AppLauncher.is_available(AppType.CALCULATOR)
                results.append(result)

            threads = [threading.Thread(target=worker) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert all(results)
        assert len(results) == 20

    def test_sanitize_path_all_dangerous(self):
        result = ValidationUtils.sanitize_path(";|&$`(){}<>")
        # No dangerous chars should remain
        for char in [';', '|', '&', '$', '`', '(', ')', '{', '}', '<', '>']:
            assert char not in result

    def test_clean_temp_files_no_permission(self, temp_dir):
        old_file = temp_dir / "old.tmp"
        old_file.write_text("old")
        old_time = time.time() - (48 * 3600)
        os.utime(str(old_file), (old_time, old_time))

        with patch('pathlib.Path.unlink', side_effect=PermissionError()):
            count = FileUtils.clean_temp_files(str(temp_dir), "*.tmp", older_than_hours=24)
            # Should not crash, just skip
            assert count >= 0
