"""
ماژول ابزارهای سیستمی MathAssistant

این ماژول توابع کمکی برای تعامل با سیستم عامل،
اجرای برنامه‌های خارجی، و مدیریت فرآیندها را فراهم می‌کند.

ویژگی‌ها:
- اجرای برنامه‌های سیستمی با retry logic یکپارچه و timeout
- تشخیص و مدیریت فرآیندها با اعتبارسنجی
- کار با فایل‌های موقت و کش با atomic write و rollback
- logging متمرکز Thread-Safe با فرمت‌های قابل تنظیم
- مدیریت مسیرهای پروژه با marker file و thread-safety
- Clipboard manager با قابلیت ساخت خودکار QApplication
- Validation متمرکز با جایگزینی امن کاراکترها
- Async support با timeout و cancellation
- RetryPolicy یکپارچه برای decorator و متدها
- ThreadPoolExecutor مدیریت شده با shutdown خودکار

Design Patterns:
- Utility Module (Stateless)
- Singleton (Thread-Safe): LogSetup, ProjectPaths, QtHelper
- Retry Policy: یکپارچه در decorator و متدها
- Atomic Write Pattern: FileUtils
- Strategy: RetryPolicy با تنظیمات قابل تغییر

Thread Safety: کامل با Lock، double-checked locking، و atexit cleanup
Performance: Caching با دیکشنری ساده (6 آیتم)، executor مشترک

Author: MathAssistant Team
Version: 4.0.0 - Production Ready
"""

import os
import sys
import re
import subprocess
import platform
import logging
import tempfile
import shutil
import time
import asyncio
import threading
import atexit
from pathlib import Path
from typing import (
    Optional, List, Tuple, Dict, Any, Union, Callable,
    Literal, TypeVar
)
from importlib import import_module
from enum import Enum
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Type Aliases
# ============================================================================

AppTypeType = Literal[
    "calculator", "browser", "file_explorer",
    "terminal", "text_editor", "pdf_viewer", "image_viewer"
]

OSTypeType = Literal["windows", "macos", "linux", "unknown"]


# ============================================================================
# Enums (StrEnum for type safety + easy debug)
# ============================================================================

class OSType(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


class AppType(str, Enum):
    CALCULATOR = "calculator"
    BROWSER = "browser"
    FILE_EXPLORER = "file_explorer"
    TERMINAL = "terminal"
    TEXT_EDITOR = "text_editor"
    PDF_VIEWER = "pdf_viewer"
    IMAGE_VIEWER = "image_viewer"


# ============================================================================
# Retry Policy (یکپارچه برای کل پروژه)
# ============================================================================

class RetryPolicy:
    """
    سیاست retry یکپارچه برای استفاده در decorator و متدها.

    Attributes:
        max_attempts: حداکثر تعداد تلاش
        delay: تأخیر اولیه (ثانیه)
        backoff: ضریب افزایش تأخیر
        exceptions: tuple exceptions که retry می‌شوند
    """

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 0.5,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        اجرای تابع با retry policy.

        Args:
            func: تابع برای اجرا
            *args, **kwargs: آرگومان‌های تابع

        Returns:
            مقدار بازگشتی تابع

        Raises:
            RuntimeError: اگر همه تلاش‌ها ناموفق باشند
        """
        current_delay = self.delay
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                if attempt < self.max_attempts:
                    logger.debug(
                        f"Retry {attempt}/{self.max_attempts} "
                        f"for {getattr(func, '__name__', func)}: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= self.backoff

        raise RuntimeError(
            f"All {self.max_attempts} retry attempts failed. "
            f"Last error: {last_exception}"
        )

    def as_decorator(self) -> Callable:
        """
        استفاده از RetryPolicy به عنوان decorator.

        Returns:
            decorator function

        Example:
            >>> policy = RetryPolicy(max_attempts=3)
            >>> @policy.as_decorator()
            ... def unstable_func():
            ...     ...
        """
        policy = self

        def decorator(func: Callable) -> Callable:
            from functools import wraps

            @wraps(func)
            def wrapper(*args, **kwargs):
                return policy.execute(func, *args, **kwargs)

            return wrapper

        return decorator


# ============================================================================
# Timeout Executor (مدیریت شده با atexit)
# ============================================================================

class TimeoutExecutor:
    """
    ThreadPoolExecutor مدیریت شده با shutdown خودکار.

    Features:
    - یک executor مشترک برای جلوگیری از thread leak
    - Shutdown خودکار در atexit
    - Thread-safe initialization
    """

    _executor: Optional[ThreadPoolExecutor] = None
    _lock = threading.Lock()

    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        """دریافت executor مشترک (Thread-Safe)."""
        if cls._executor is None:
            with cls._lock:
                if cls._executor is None:
                    cls._executor = ThreadPoolExecutor(
                        max_workers=4,
                        thread_name_prefix="mathassistant"
                    )
                    logger.debug("TimeoutExecutor initialized")
        return cls._executor

    @classmethod
    def execute(
        cls,
        func: Callable,
        timeout_seconds: float,
        *args,
        **kwargs
    ) -> Any:
        """
        اجرای تابع با timeout.

        Args:
            func: تابع
            timeout_seconds: حداکثر زمان (ثانیه)
            *args, **kwargs: آرگومان‌های تابع

        Returns:
            مقدار بازگشتی تابع

        Raises:
            TimeoutError: اگر زمان بیش از حد طول بکشد
        """
        executor = cls.get_executor()
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            future.cancel()
            raise TimeoutError(
                f"Function '{getattr(func, '__name__', func)}' "
                f"timed out after {timeout_seconds}s"
            )

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown امن executor."""
        with cls._lock:
            if cls._executor is not None:
                cls._executor.shutdown(wait=True)
                cls._executor = None
                logger.debug("TimeoutExecutor shutdown")


# ثبت shutdown خودکار
atexit.register(TimeoutExecutor.shutdown)


# ============================================================================
# Validation Utilities
# ============================================================================

class ValidationUtils:
    """توابع اعتبارسنجی متمرکز با جایگزینی امن."""

    _URL_PATTERN = re.compile(r'^https?://')

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """اعتبارسنجی URL."""
        if not url:
            return False, "URL نمی‌تواند خالی باشد."
        if not ValidationUtils._URL_PATTERN.match(url):
            return False, "URL باید با http:// یا https:// شروع شود."
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "URL نامعتبر: دامنه یافت نشد."
        except Exception:
            return False, "URL نامعتبر: خطا در تجزیه."
        return True, ""

    @staticmethod
    def sanitize_path(path: str, replacement: str = "_") -> str:
        """
        پاکسازی مسیر با جایگزینی کاراکترهای خطرناک.

        Args:
            path: مسیر ورودی
            replacement: کاراکتر جایگزین (پیش‌فرض: '_')

        Returns:
            مسیر پاکسازی شده

        Example:
            >>> ValidationUtils.sanitize_path("file(name).txt")
            'file_name_.txt'
        """
        dangerous = [';', '|', '&', '$', '`', '(', ')', '{', '}', '<', '>']
        for char in dangerous:
            path = path.replace(char, replacement)
        return path.strip()


# ============================================================================
# Thread-Safe Qt Helper
# ============================================================================

class _QtHelper:
    """
    کمک‌کننده داخلی Qt - Thread-Safe با auto-create.
    """

    _qt_module: Optional[str] = None
    _QtWidgets: Optional[Any] = None
    _discovery_done: bool = False
    _lock = threading.Lock()

    @classmethod
    def _discover(cls, auto_create: bool = False) -> None:
        """کشف Qt با double-checked locking."""
        if cls._discovery_done:
            return

        with cls._lock:
            if cls._discovery_done:
                return

            for module_name in ('PyQt6', 'PyQt5'):
                try:
                    QtWidgets = import_module(f'{module_name}.QtWidgets')
                    app = QtWidgets.QApplication.instance()

                    if app is None and auto_create:
                        try:
                            app = QtWidgets.QApplication(sys.argv)
                        except Exception:
                            continue

                    if app is not None:
                        cls._qt_module = module_name
                        cls._QtWidgets = QtWidgets
                        break
                except ImportError:
                    continue

            cls._discovery_done = True

    @classmethod
    def _get_app(cls, auto_create: bool = False) -> Optional[Any]:
        """دریافت QApplication instance."""
        cls._discover(auto_create=auto_create)
        if cls._QtWidgets is None:
            return None
        try:
            return cls._QtWidgets.QApplication.instance()
        except Exception:
            return None

    @classmethod
    def get_clipboard_text(cls) -> Optional[str]:
        """دریافت متن کلیپبورد."""
        app = cls._get_app(auto_create=True)
        if app is None:
            return None
        try:
            clipboard = app.clipboard()
            if clipboard is not None:
                text = clipboard.text()
                return text if text else None
        except Exception:
            pass
        return None

    @classmethod
    def set_clipboard_text(cls, text: str) -> bool:
        """تنظیم متن کلیپبورد."""
        if not text:
            return False
        app = cls._get_app(auto_create=True)
        if app is None:
            return False
        try:
            clipboard = app.clipboard()
            if clipboard is not None:
                clipboard.setText(text)
                return True
        except Exception:
            pass
        return False

    @classmethod
    def get_screen_resolution(cls) -> Optional[Tuple[int, int]]:
        """دریافت رزولوشن."""
        cls._discover(auto_create=True)
        if cls._QtWidgets is None:
            return None
        app = cls._QtWidgets.QApplication.instance()
        if app is None:
            return None
        try:
            if cls._qt_module == 'PyQt6':
                screen = app.primaryScreen()
                if screen is not None:
                    size = screen.size()
                    return (size.width(), size.height())
            else:
                desktop = cls._QtWidgets.QApplication.desktop()
                if desktop is not None:
                    geometry = desktop.screenGeometry()
                    return (geometry.width(), geometry.height())
        except Exception:
            pass
        return None


# ============================================================================
# System Information
# ============================================================================

class SystemInfo:
    """اطلاعات سیستم - تمام متدها stateless و thread-safe."""

    @staticmethod
    def get_os() -> OSType:
        system = platform.system().lower()
        return {
            "windows": OSType.WINDOWS,
            "darwin": OSType.MACOS,
            "linux": OSType.LINUX,
        }.get(system, OSType.UNKNOWN)

    @staticmethod
    def get_os_name() -> str:
        os_type = SystemInfo.get_os()
        if os_type == OSType.WINDOWS:
            return f"Windows {platform.release()}"
        elif os_type == OSType.MACOS:
            mac_ver = platform.mac_ver()[0]
            return f"macOS {mac_ver}" if mac_ver else "macOS"
        elif os_type == OSType.LINUX:
            try:
                distro = platform.freedesktop_os_release().get("PRETTY_NAME", "")
                return distro if distro else f"Linux ({platform.platform()})"
            except Exception:
                return f"Linux ({platform.platform()})"
        return platform.platform()

    @staticmethod
    def get_architecture() -> str:
        return platform.machine()

    @staticmethod
    def is_64bit() -> bool:
        return sys.maxsize > 2**32

    @staticmethod
    def get_python_info() -> Dict[str, str]:
        return {
            "version": sys.version.split()[0],
            "full_version": sys.version.split('\n')[0],
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "is_64bit": str(SystemInfo.is_64bit()),
        }

    @staticmethod
    def get_user_name() -> str:
        try:
            return os.getlogin()
        except OSError:
            return os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))

    @staticmethod
    def get_home_dir() -> Path:
        return Path.home()

    @staticmethod
    def get_temp_dir() -> Path:
        return Path(tempfile.gettempdir())

    @staticmethod
    def get_screen_resolution() -> Optional[Tuple[int, int]]:
        return _QtHelper.get_screen_resolution()

    @staticmethod
    def get_clipboard_text() -> Optional[str]:
        return _QtHelper.get_clipboard_text()

    @staticmethod
    def copy_to_clipboard(text: str) -> bool:
        return _QtHelper.set_clipboard_text(text)


# ============================================================================
# Application Launcher
# ============================================================================

class AppLauncher:
    """
    اجرای برنامه‌های سیستمی با retry یکپارچه و timeout.

    از RetryPolicy برای launch_with_retry استفاده می‌کند.
    Caching با دیکشنری ساده برای 6 حالت AppType.
    """

    _APP_PATHS: Dict[OSType, Dict[AppType, List[str]]] = {
        OSType.WINDOWS: {
            AppType.CALCULATOR: ["calc.exe"],
            AppType.BROWSER: ["msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "iexplore.exe"],
            AppType.FILE_EXPLORER: ["explorer.exe"],
            AppType.TERMINAL: ["wt.exe", "powershell.exe", "cmd.exe"],
            AppType.TEXT_EDITOR: ["notepad++.exe", "code.exe", "notepad.exe"],
            AppType.PDF_VIEWER: ["msedge.exe", "AcroRd32.exe", "SumatraPDF.exe"],
            AppType.IMAGE_VIEWER: ["mspaint.exe", "Microsoft.Photos.exe"],
        },
        OSType.MACOS: {
            AppType.CALCULATOR: ["/System/Applications/Calculator.app"],
            AppType.BROWSER: ["/Applications/Safari.app", "/Applications/Google Chrome.app",
                            "/Applications/Firefox.app", "/Applications/Brave Browser.app"],
            AppType.FILE_EXPLORER: ["/System/Library/CoreServices/Finder.app"],
            AppType.TERMINAL: ["/System/Applications/Utilities/Terminal.app", "/Applications/iTerm.app"],
            AppType.TEXT_EDITOR: ["/Applications/Visual Studio Code.app", "/Applications/TextEdit.app"],
            AppType.PDF_VIEWER: ["/Applications/Preview.app", "/Applications/Adobe Acrobat Reader DC.app"],
            AppType.IMAGE_VIEWER: ["/Applications/Preview.app", "/System/Applications/Photos.app"],
        },
        OSType.LINUX: {
            AppType.CALCULATOR: ["qalculate-gtk", "gnome-calculator", "kcalc"],
            AppType.BROWSER: ["firefox", "google-chrome-stable", "chromium-browser", "brave-browser"],
            AppType.FILE_EXPLORER: ["nautilus", "dolphin", "thunar", "pcmanfm"],
            AppType.TERMINAL: ["gnome-terminal", "konsole", "alacritty", "xterm"],
            AppType.TEXT_EDITOR: ["code", "gedit", "kate", "nano"],
            AppType.PDF_VIEWER: ["evince", "okular", "zathura", "xdg-open"],
            AppType.IMAGE_VIEWER: ["eog", "gwenview", "gthumb", "feh"],
        },
    }

    _APP_NAMES: Dict[AppType, str] = {
        AppType.CALCULATOR: "ماشین حساب",
        AppType.BROWSER: "مرورگر",
        AppType.FILE_EXPLORER: "مدیریت فایل",
        AppType.TERMINAL: "ترمینال",
        AppType.TEXT_EDITOR: "ویرایشگر متن",
        AppType.PDF_VIEWER: "نمایشگر PDF",
        AppType.IMAGE_VIEWER: "نمایشگر تصویر",
    }

    # کش ساده برای ۶ حالت AppType
    _availability_cache: Dict[AppType, bool] = {}

    @staticmethod
    def _find_app(app_type: AppType) -> Optional[str]:
        """جستجوی progressive برنامه."""
        os_type = SystemInfo.get_os()
        paths = AppLauncher._APP_PATHS.get(os_type, {}).get(app_type, [])

        for path in paths:
            if os.path.isabs(path):
                if os.path.exists(path):
                    return path
            else:
                executable = shutil.which(path)
                if executable:
                    return executable
        return None

    @staticmethod
    def is_available(app_type: AppType) -> bool:
        """
        بررسی موجود بودن برنامه (cached با دیکشنری).

        چون AppType فقط ۶ حالت دارد، دیکشنری ساده از lru_cache مناسب‌تر است.
        """
        if app_type not in AppLauncher._availability_cache:
            AppLauncher._availability_cache[app_type] = (
                AppLauncher._find_app(app_type) is not None
            )
        return AppLauncher._availability_cache[app_type]

    @staticmethod
    def launch(
        app_type: AppType,
        *args: str,
        timeout_seconds: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        اجرای برنامه با اعتبارسنجی args.

        Args:
            app_type: نوع برنامه
            *args: آرگومان‌ها (sanitize می‌شوند)
            timeout_seconds: حداکثر زمان انتظار

        Returns:
            (success, message)
        """
        sanitized_args = [
            ValidationUtils.sanitize_path(arg) for arg in args
        ]

        app_path = AppLauncher._find_app(app_type)
        if app_path is None:
            name = AppLauncher._APP_NAMES.get(app_type, str(app_type))
            return False, f"{name} در سیستم یافت نشد."

        try:
            cmd = [app_path] + sanitized_args
            process = subprocess.Popen(
                cmd, shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if platform.system() == "Windows" else 0
                )
            )

            if timeout_seconds is not None:
                try:
                    process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    return False, f"اجرا بیش از {timeout_seconds}s طول کشید."

            return True, "برنامه با موفقیت اجرا شد."

        except FileNotFoundError:
            return False, f"فایل اجرایی یافت نشد: {app_path}"
        except PermissionError:
            return False, "دسترسی کافی وجود ندارد."
        except OSError as e:
            logger.error(f"OS error: {e}")
            return False, f"خطای سیستم: {e}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, f"خطای غیرمنتظره: {e}"

    @staticmethod
    def launch_with_retry(
        app_type: AppType,
        *args: str,
        retry_policy: Optional[RetryPolicy] = None
    ) -> Tuple[bool, str]:
        """
        اجرای برنامه با retry یکپارچه.

        Args:
            app_type: نوع برنامه
            *args: آرگومان‌ها
            retry_policy: سیاست retry (پیش‌فرض: 3 تلاش، 0.5s تأخیر)

        Returns:
            (success, message)
        """
        if retry_policy is None:
            retry_policy = RetryPolicy(max_attempts=3, delay=0.5)

        try:
            return retry_policy.execute(AppLauncher.launch, app_type, *args)
        except RuntimeError as e:
            return False, str(e)

    @staticmethod
    async def launch_async(
        app_type: AppType,
        *args: str,
        timeout_seconds: float = 30.0
    ) -> Tuple[bool, str]:
        """
        نسخه async با timeout و cancellation.

        Args:
            app_type: نوع برنامه
            *args: آرگومان‌ها
            timeout_seconds: timeout عملیات

        Returns:
            (success, message)
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None, AppLauncher.launch, app_type, *args
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            return False, f"عملیات async پس از {timeout_seconds}s timeout شد."
        except asyncio.CancelledError:
            return False, "عملیات async لغو شد."

    # ----- Convenience Methods -----

    @staticmethod
    def launch_calculator() -> Tuple[bool, str]:
        return AppLauncher.launch(AppType.CALCULATOR)

    @staticmethod
    def launch_browser(url: str = "") -> Tuple[bool, str]:
        return AppLauncher.launch(AppType.BROWSER, url) if url else AppLauncher.launch(AppType.BROWSER)

    @staticmethod
    def launch_file_explorer(path: str = ".") -> Tuple[bool, str]:
        return AppLauncher.launch(
            AppType.FILE_EXPLORER,
            os.path.abspath(ValidationUtils.sanitize_path(path))
        )

    @staticmethod
    def launch_terminal() -> Tuple[bool, str]:
        return AppLauncher.launch(AppType.TERMINAL)

    @staticmethod
    def launch_text_editor(filepath: str = "") -> Tuple[bool, str]:
        return AppLauncher.launch(
            AppType.TEXT_EDITOR,
            os.path.abspath(filepath)
        ) if filepath else AppLauncher.launch(AppType.TEXT_EDITOR)

    @staticmethod
    def launch_pdf_viewer(filepath: str = "") -> Tuple[bool, str]:
        return AppLauncher.launch(
            AppType.PDF_VIEWER,
            os.path.abspath(filepath)
        ) if filepath else AppLauncher.launch(AppType.PDF_VIEWER)

    @staticmethod
    def launch_image_viewer(filepath: str = "") -> Tuple[bool, str]:
        return AppLauncher.launch(
            AppType.IMAGE_VIEWER,
            os.path.abspath(filepath)
        ) if filepath else AppLauncher.launch(AppType.IMAGE_VIEWER)

    @staticmethod
    def open_url(url: str) -> Tuple[bool, str]:
        """باز کردن URL با اعتبارسنجی."""
        is_valid, error = ValidationUtils.validate_url(url)
        if not is_valid:
            return False, error

        import webbrowser
        try:
            success = webbrowser.open(url)
            return (
                (True, f"URL باز شد: {url}")
                if success
                else (False, "مرورگر نتوانست URL را باز کند.")
            )
        except Exception as e:
            logger.error(f"Failed to open URL '{url}': {e}")
            return False, f"خطا: {e}"


# ============================================================================
# Process Manager
# ============================================================================

class ProcessManager:
    """مدیریت فرآیندها با timeout و اعتبارسنجی."""

    @staticmethod
    def run_python_script(
        script_path: str,
        *args: str,
        wait: bool = False,
        timeout_seconds: Optional[float] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """اجرای اسکریپت Python."""
        if not os.path.exists(script_path):
            return False, f"اسکریپت یافت نشد: {script_path}", None

        sanitized_args = [
            ValidationUtils.sanitize_path(arg) for arg in args
        ]

        try:
            cmd = [sys.executable, script_path] + sanitized_args

            if wait:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout_seconds
                )
                if result.returncode == 0:
                    return True, result.stdout.strip(), 0
                else:
                    return False, result.stderr.strip(), result.returncode
            else:
                subprocess.Popen(
                    cmd, shell=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return True, "اسکریپت در پس‌زمینه اجرا شد.", None

        except subprocess.TimeoutExpired:
            return False, f"زمان اجرا بیش از {timeout_seconds}s طول کشید.", -1
        except Exception as e:
            logger.error(f"Failed to run script: {e}")
            return False, f"خطا: {e}", None

    @staticmethod
    def is_process_running(process_name: str) -> bool:
        """بررسی اجرای فرآیند."""
        try:
            if platform.system() == "Windows":
                name = process_name.replace('.exe', '').lower()
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {name}.exe"],
                    capture_output=True, text=True, timeout=5
                )
                return name in result.stdout.lower()
            else:
                result = subprocess.run(
                    ["pgrep", "-x", process_name],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def kill_process(process_name: str) -> Tuple[bool, str]:
        """پایان فرآیند."""
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    capture_output=True, timeout=10
                )
            else:
                subprocess.run(
                    ["pkill", "-x", process_name],
                    capture_output=True, timeout=10
                )
            return True, f"فرآیند {process_name} متوقف شد."
        except subprocess.TimeoutExpired:
            return False, "زمان پایان فرآیند به اتمام رسید."
        except FileNotFoundError:
            return False, "ابزار مدیریت فرآیند یافت نشد."
        except Exception as e:
            return False, f"خطا: {e}"


# ============================================================================
# Project Paths (Thread-Safe)
# ============================================================================

class ProjectPaths:
    """مدیریت مسیرهای پروژه - Thread-Safe."""

    _root: Optional[Path] = None
    _lock = threading.Lock()
    _MARKER_FILES = ["pyproject.toml", "setup.py", "setup.cfg", ".git"]

    @classmethod
    def get_root(cls) -> Path:
        """ریشه پروژه (Thread-Safe با double-checked locking)."""
        if cls._root is not None:
            return cls._root

        with cls._lock:
            if cls._root is not None:
                return cls._root

            current = Path(__file__).resolve()
            for parent in current.parents:
                for marker in cls._MARKER_FILES:
                    if (parent / marker).exists():
                        cls._root = parent
                        return cls._root

            cls._root = current.parents[3]
            return cls._root

    @classmethod
    def reset_cache(cls) -> None:
        with cls._lock:
            cls._root = None

    @classmethod
    def get_src_dir(cls) -> Path:
        return cls.get_root() / "src"

    @classmethod
    def get_assets_dir(cls) -> Path:
        return cls.get_root() / "assets"

    @classmethod
    def get_tests_dir(cls) -> Path:
        return cls.get_root() / "tests"

    @classmethod
    def get_logs_dir(cls) -> Path:
        logs = cls.get_root() / "logs"
        logs.mkdir(exist_ok=True)
        return logs

    @classmethod
    def get_cache_dir(cls) -> Path:
        cache = cls.get_root() / ".cache"
        cache.mkdir(exist_ok=True)
        return cache

    @classmethod
    def get_config_dir(cls) -> Path:
        config = cls.get_root() / "config"
        config.mkdir(exist_ok=True)
        return config

    @classmethod
    def resolve_asset(cls, filename: str) -> Path:
        return cls.get_assets_dir() / filename

    @classmethod
    def resolve_config(cls, filename: str) -> Path:
        return cls.get_config_dir() / filename


# ============================================================================
# File Utilities
# ============================================================================

class FileUtils:
    """توابع فایل با atomic write و rollback."""

    @staticmethod
    def safe_read(filepath: str, encoding: str = "utf-8") -> Optional[str]:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
        except PermissionError:
            logger.warning(f"Permission denied: {filepath}")
        except UnicodeDecodeError:
            logger.warning(f"Encoding error: {filepath}")
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
        return None

    @staticmethod
    def safe_write(
        filepath: str, content: str,
        encoding: str = "utf-8", atomic: bool = True
    ) -> bool:
        """نوشتن atomic با rollback."""
        path = Path(filepath)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            if atomic:
                temp_path = path.with_suffix(path.suffix + '.tmp')
                try:
                    with open(temp_path, 'w', encoding=encoding) as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    temp_path.replace(path)
                    return True
                except Exception:
                    if temp_path.exists():
                        temp_path.unlink()
                    raise
            else:
                with open(path, 'w', encoding=encoding) as f:
                    f.write(content)
                return True
        except Exception as e:
            logger.error(f"Error writing {filepath}: {e}")
            return False

    @staticmethod
    def safe_delete(filepath: str) -> bool:
        try:
            os.remove(filepath)
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"Error deleting {filepath}: {e}")
            return False

    @staticmethod
    def get_file_size_mb(filepath: str) -> float:
        try:
            return os.path.getsize(filepath) / (1024 * 1024)
        except OSError:
            return 0.0

    @staticmethod
    def ensure_dir(dirpath: str) -> Path:
        path = Path(dirpath)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def list_files(
        directory: str, pattern: str = "*", recursive: bool = False
    ) -> List[Path]:
        path = Path(directory)
        if not path.exists():
            return []
        if recursive and not pattern.startswith("**"):
            pattern = f"**/{pattern}"
        return list(path.glob(pattern))

    @staticmethod
    def clean_temp_files(
        directory: str, pattern: str = "*.tmp", older_than_hours: int = 24
    ) -> int:
        count = 0
        cutoff = time.time() - (older_than_hours * 3600)
        try:
            for file in Path(directory).glob(pattern):
                if file.is_file():
                    try:
                        if file.stat().st_mtime < cutoff:
                            file.unlink()
                            count += 1
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
        return count

    @staticmethod
    def copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
        try:
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if not overwrite and dst_path.exists():
                return False
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.error(f"Error copying {src} to {dst}: {e}")
            return False


# ============================================================================
# Thread-Safe Logging
# ============================================================================

class LogSetup:
    """تنظیمات logging - Thread-Safe Singleton."""

    _configured: bool = False
    _lock = threading.Lock()

    @classmethod
    def setup(
        cls,
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_format_console: Optional[str] = None,
        log_format_file: Optional[str] = None
    ) -> logging.Logger:
        if cls._configured:
            return logging.getLogger("MathAssistant")

        with cls._lock:
            if cls._configured:
                return logging.getLogger("MathAssistant")

            root_logger = logging.getLogger("MathAssistant")
            root_logger.setLevel(level)

            console = logging.StreamHandler()
            console.setLevel(level)
            console.setFormatter(logging.Formatter(
                log_format_console or '%(levelname)-8s [%(name)s] %(message)s'
            ))
            root_logger.addHandler(console)

            if log_to_file:
                try:
                    log_dir = ProjectPaths.get_logs_dir()
                    file_handler = logging.FileHandler(
                        log_dir / f"mathassistant_{time.strftime('%Y%m%d')}.log",
                        encoding='utf-8'
                    )
                    file_handler.setLevel(logging.DEBUG)
                    file_handler.setFormatter(logging.Formatter(
                        log_format_file or (
                            '%(asctime)s | %(levelname)-8s | '
                            '%(name)s:%(lineno)d | %(message)s'
                        ),
                        datefmt='%Y-%m-%d %H:%M:%S'
                    ))
                    root_logger.addHandler(file_handler)
                except Exception as e:
                    print(f"Warning: Could not set up file logging: {e}")

            cls._configured = True
            return root_logger

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        return logging.getLogger(f"MathAssistant.{name}")

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            root_logger = logging.getLogger("MathAssistant")
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            cls._configured = False


# ============================================================================
# Backward Compatibility
# ============================================================================

class SystemToolLauncher:
    """نسخه سازگار با کد قدیمی."""

    @staticmethod
    def launch_calculator() -> Tuple[bool, str]:
        return AppLauncher.launch_calculator()

    @staticmethod
    def launch_browser(url: str = "") -> Tuple[bool, str]:
        return AppLauncher.launch_browser(url)

    @staticmethod
    def launch_file_explorer(path: str = ".") -> Tuple[bool, str]:
        return AppLauncher.launch_file_explorer(path)


# ============================================================================
# System Diagnostics
# ============================================================================

def get_system_report() -> Dict[str, Any]:
    """گزارش کامل سیستم."""
    return {
        "os": SystemInfo.get_os_name(),
        "architecture": SystemInfo.get_architecture(),
        "is_64bit": SystemInfo.is_64bit(),
        "python": SystemInfo.get_python_info(),
        "user": SystemInfo.get_user_name(),
        "home": str(SystemInfo.get_home_dir()),
        "temp": str(SystemInfo.get_temp_dir()),
        "project_root": str(ProjectPaths.get_root()),
        "screen": SystemInfo.get_screen_resolution(),
        "available_apps": {
            app.value: AppLauncher.is_available(app)
            for app in AppType
        },
    }
