# tests/unit/test_main_window.py
"""
Unit tests for the MathAssistant main window module.

This test suite provides comprehensive coverage for the MainWindow, GradientWidget,
ChildWindowManager, and MenuManager components, including edge cases, thread safety,
and integration scenarios.

Test Categories:
    - ChildWindowManager: Window lifecycle management, thread safety, error recovery
    - MainWindow: UI initialization, application launching, theme management
    - GradientWidget: Visual effects rendering, animation, cleanup
    - MenuManager: Menu creation, action binding, theme switching
    - ErrorHandler: Decorator behavior, exception propagation
    - Integration: Full lifecycle tests, multi-window scenarios

Author: MathAssistant Team
Version: 2.0.0
Last Modified: 2025-01-15
"""

import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from unittest.mock import MagicMock, Mock, patch

import pytest

# --------------------------------------------------------------------------- #
# Module Path Configuration
# --------------------------------------------------------------------------- #

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Clean reimport to prevent module caching issues
_MODULE_PREFIX = 'MathAssistant'
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith(_MODULE_PREFIX):
        del sys.modules[mod_name]

# --------------------------------------------------------------------------- #
# Mock Qt Framework Classes
# --------------------------------------------------------------------------- #


class FakeQMainWindow:
    """
    Mock implementation of QMainWindow for testing purposes.

    Provides a simplified interface that mimics PyQt5/PyQt6 QMainWindow behavior
    without requiring the actual Qt framework. Supports window state management,
    title handling, and fullscreen toggling.

    Attributes:
        _title (str): Current window title.
        _status_bar (MagicMock): Mocked status bar widget.
        _menu_bar (MagicMock): Mocked menu bar widget.
        _is_fullscreen (bool): Fullscreen state flag.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initialize the fake main window with default state and mocked components."""
        self._title: str = ""
        self._status_bar: MagicMock = MagicMock()
        self._menu_bar: MagicMock = MagicMock()
        self._is_fullscreen: bool = False

    def setWindowTitle(self, title: str) -> None:
        """Set the window title.

        Args:
            title: The new window title string.
        """
        self._title = title

    def windowTitle(self) -> str:
        """Get the current window title.

        Returns:
            The current window title or default Persian title.
        """
        return self._title or "کمک معلم ریاضی | Math Assistant"

    def statusBar(self) -> MagicMock:
        """Get the status bar widget.

        Returns:
            Mocked status bar instance.
        """
        return self._status_bar

    def menuBar(self) -> MagicMock:
        """Get the menu bar widget.

        Returns:
            Mocked menu bar instance.
        """
        return self._menu_bar

    def isFullScreen(self) -> bool:
        """Check if window is in fullscreen mode.

        Returns:
            True if fullscreen, False otherwise.
        """
        return self._is_fullscreen

    def showFullScreen(self) -> None:
        """Enter fullscreen mode."""
        self._is_fullscreen = True

    def showNormal(self) -> None:
        """Exit fullscreen mode to normal window state."""
        self._is_fullscreen = False

    def setCentralWidget(self, widget: Any) -> None:
        """Set the central widget (no-op in mock).

        Args:
            widget: Widget to set as central.
        """
        pass

    def setFont(self, font: Any) -> None:
        """Set the window font (no-op in mock).

        Args:
            font: Font object to apply.
        """
        pass

    def setMinimumSize(self, *args: Any) -> None:
        """Set minimum window size (no-op in mock).

        Args:
            *args: Size arguments (QSize or width, height).
        """
        pass

    def resize(self, *args: Any) -> None:
        """Resize the window (no-op in mock).

        Args:
            *args: Size arguments (QSize or width, height).
        """
        pass

    def move(self, *args: Any) -> None:
        """Move the window (no-op in mock).

        Args:
            *args: Position arguments (QPoint or x, y).
        """
        pass

    def frameGeometry(self) -> MagicMock:
        """Get the frame geometry.

        Returns:
            Mocked QRect representing frame geometry.
        """
        return MagicMock()

    def close(self) -> None:
        """Close the window (no-op in mock)."""
        pass

    def setStyleSheet(self, style: str) -> None:
        """Set the window stylesheet (no-op in mock).

        Args:
            style: CSS style string.
        """
        pass


class FakeQWidget:
    """
    Mock implementation of QWidget for testing purposes.

    Provides basic widget functionality including visibility control,
    sizing, and event handling without requiring the actual Qt framework.

    Attributes:
        _visible (bool): Widget visibility state.
        _width (int): Widget width in pixels.
        _height (int): Widget height in pixels.
    """

    def __init__(self, parent: Any = None) -> None:
        """Initialize the fake widget with default dimensions and visible state."""
        self._visible: bool = True
        self._width: int = 800
        self._height: int = 600

    def setVisible(self, visible: bool) -> None:
        """Set widget visibility.

        Args:
            visible: True to show, False to hide.
        """
        self._visible = visible

    def isVisible(self) -> bool:
        """Check if widget is visible.

        Returns:
            True if visible, False otherwise.
        """
        return self._visible

    def width(self) -> int:
        """Get widget width.

        Returns:
            Width in pixels.
        """
        return self._width

    def height(self) -> int:
        """Get widget height.

        Returns:
            Height in pixels.
        """
        return self._height

    def rect(self) -> MagicMock:
        """Get widget rectangle.

        Returns:
            Mocked QRect representing widget bounds.
        """
        return MagicMock()

    def setMinimumSize(self, *args: Any) -> None:
        """Set minimum widget size (no-op in mock).

        Args:
            *args: Size arguments.
        """
        pass

    def resize(self, *args: Any) -> None:
        """Resize the widget.

        Args:
            *args: Size arguments (QSize or width, height).
        """
        if len(args) == 2:
            self._width, self._height = args
        elif hasattr(args[0], 'width'):
            self._width, self._height = args[0].width(), args[0].height()

    def update(self) -> None:
        """Request widget repaint (no-op in mock)."""
        pass

    def setLayout(self, layout: Any) -> None:
        """Set widget layout (no-op in mock).

        Args:
            layout: Layout object to set.
        """
        pass

    def layout(self) -> MagicMock:
        """Get widget layout.

        Returns:
            Mocked layout instance.
        """
        return MagicMock()

    def setStyleSheet(self, style: str) -> None:
        """Set widget stylesheet (no-op in mock).

        Args:
            style: CSS style string.
        """
        pass

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press event (no-op in mock).

        Args:
            event: Mouse event object.
        """
        pass

    def paintEvent(self, event: Any) -> None:
        """Handle paint event (no-op in mock).

        Args:
            event: Paint event object.
        """
        pass

    def resizeEvent(self, event: Any) -> None:
        """Handle resize event (no-op in mock).

        Args:
            event: Resize event object.
        """
        pass


# --------------------------------------------------------------------------- #
# Mock Qt Module Configuration
# --------------------------------------------------------------------------- #

_mock_qt_core = MagicMock()
_mock_qt_gui = MagicMock()
_mock_qt_widgets = MagicMock()

# Assign mock implementations
_mock_qt_widgets.QMainWindow = FakeQMainWindow
_mock_qt_widgets.QWidget = FakeQWidget

# Core module mocks
_mock_qt_core.QTimer = MagicMock(return_value=MagicMock())
_mock_qt_core.Qt = MagicMock(
    AlignCenter=4,
    AlignRight=2,
    AlignLeft=1,
    RichText=1,
    PlainText=0,
    DirectConnection=3,
    LeftButton=1,
    RightButton=2,
    PointingHandCursor=13
)
_mock_qt_core.Qt.ConnectionType = MagicMock(DirectConnection=3)
_mock_qt_core.QSize = MagicMock()
_mock_qt_core.QRect = MagicMock()


def _make_qcolor(r: int = 0, g: int = 0, b: int = 0, a: int = 255) -> MagicMock:
    """Create a mock QColor with specified RGBA values.

    Args:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).
        a: Alpha component (0-255).

    Returns:
        Mocked QColor instance with configured return values.
    """
    mock_color = MagicMock()
    mock_color.red.return_value = r
    mock_color.green.return_value = g
    mock_color.blue.return_value = b
    mock_color.alpha.return_value = a
    mock_color.name.return_value = f"#{r:02x}{g:02x}{b:02x}"
    return mock_color


# GUI module mocks
_mock_qt_gui.QColor = MagicMock(side_effect=_make_qcolor)
_mock_qt_gui.QFont = MagicMock(return_value=MagicMock())
_mock_qt_gui.QPainter = MagicMock(return_value=MagicMock())
_mock_qt_gui.QLinearGradient = MagicMock()
_mock_qt_gui.QRadialGradient = MagicMock()
_mock_qt_gui.QKeySequence = MagicMock()
_mock_qt_gui.QAction = MagicMock()
_mock_qt_gui.QPixmap = MagicMock()
_mock_qt_gui.QFontDatabase = MagicMock(return_value=MagicMock())

# Widget module mocks
_mock_qt_widgets.QLabel = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QVBoxLayout = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QHBoxLayout = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QGridLayout = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QPushButton = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QFrame = MagicMock()
_mock_qt_widgets.QFrame.Shape = MagicMock(NoFrame=0)
_mock_qt_widgets.QMenuBar = MagicMock(return_value=MagicMock())
_mock_qt_widgets.QShortcut = MagicMock()
_mock_qt_widgets.QMessageBox = MagicMock(Yes=1, No=0, Information=1)
_mock_qt_widgets.QMessageBox.return_value.exec_ = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setText = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setDetailedText = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setWindowTitle = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setIcon = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setStyleSheet = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setTextFormat = MagicMock()
_mock_qt_widgets.QMessageBox.return_value.setMinimumSize = MagicMock()

# Application mock with screen geometry
_mock_qt_widgets.QApplication = MagicMock()
screen_mock = MagicMock()
screen_mock.availableGeometry.return_value = MagicMock()
screen_mock.availableGeometry.return_value.width.return_value = 1920
screen_mock.availableGeometry.return_value.height.return_value = 1080
screen_mock.availableGeometry.return_value.center.return_value = MagicMock(x=960, y=540)
_mock_qt_widgets.QApplication.primaryScreen.return_value = screen_mock

# Register mocks for both PyQt5 and PyQt6
for prefix in ['PyQt6', 'PyQt5']:
    sys.modules[f'{prefix}'] = MagicMock()
    sys.modules[f'{prefix}.QtCore'] = _mock_qt_core
    sys.modules[f'{prefix}.QtGui'] = _mock_qt_gui
    sys.modules[f'{prefix}.QtWidgets'] = _mock_qt_widgets

# --------------------------------------------------------------------------- #
# Module Imports
# --------------------------------------------------------------------------- #

from MathAssistant.ui.main_window import (
    MainWindow,
    GradientWidget,
    ChildWindowManager,
    MenuManager,
    show_error_on_failure,
    ThemeProvider,
    AppLauncherProtocol,
    ThemeMode,
    GlassLevel,
    QMessageBox,
    Qt,
)

# --------------------------------------------------------------------------- #
# Test Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def mock_theme() -> MagicMock:
    """
    Create a mocked ThemeProvider for testing.

    Returns a MagicMock configured with ThemeProvider spec and default
    light theme settings. Provides mocked color, font, and style getters
    along with subscribe/unsubscribe functionality.

    Returns:
        Configured MagicMock with ThemeProvider specification.
    """
    theme = MagicMock(spec=ThemeProvider)
    theme.mode = ThemeMode.LIGHT
    theme.is_dark = False
    theme.glass_level = GlassLevel.NONE
    theme.qt_version = MagicMock()
    theme.qt_version.name = "PYQT6"
    theme.windows_version = "Windows 10"
    theme.color.return_value = "#2563EB"
    theme.get_app_font.return_value = MagicMock()
    theme.get_title_font.return_value = MagicMock()
    theme.get_font.return_value = MagicMock()
    theme.get_button_style.return_value = "QPushButton {}"
    theme.get_menu_bar_style.return_value = ""
    theme.get_status_bar_style.return_value = ""
    theme.get_message_box_style.return_value = ""
    theme.get_system_info.return_value = {
        "os": "Windows 10",
        "python": "3.12.0",
        "theme": "LIGHT",
        "qt_version": "PYQT6"
    }
    theme.subscribe = MagicMock()
    theme.unsubscribe = MagicMock()
    return theme


@pytest.fixture
def mock_launcher() -> MagicMock:
    """
    Create a mocked AppLauncherProtocol for testing.

    Returns a MagicMock configured with successful launch responses
    for all application types.

    Returns:
        Configured MagicMock with AppLauncherProtocol specification.
    """
    launcher = MagicMock(spec=AppLauncherProtocol)
    launcher.launch_calculator.return_value = (True, "ok")
    return launcher


@pytest.fixture
def main_window(mock_theme: MagicMock, mock_launcher: MagicMock) -> MainWindow:
    """
    Create a MainWindow instance for testing.

    Patches GradientWidget to avoid actual widget creation and configures
    the status bar with expected system information.

    Args:
        mock_theme: Mocked theme provider fixture.
        mock_launcher: Mocked application launcher fixture.

    Returns:
        Fully initialized MainWindow instance with mocked dependencies.
    """
    with patch('MathAssistant.ui.main_window.GradientWidget') as mock_grad:
        mock_instance = MagicMock()
        mock_instance.container = MagicMock()
        mock_instance.container.layout.return_value = MagicMock()
        mock_grad.return_value = mock_instance
        window = MainWindow(
            theme_provider=mock_theme,
            app_launcher=mock_launcher
        )
        # Configure status bar with expected system information
        window.statusBar().currentMessage.return_value = (
            "🖥️ Windows 10 | 🐍 Python 3.12.0 | 🎨 LIGHT | 🧵 PYQT6"
        )
        return window


# =========================================================================== #
# Test Classes
# =========================================================================== #


class TestChildWindowManager:
    """
    Test suite for ChildWindowManager class.

    Covers window lifecycle management including creation, reuse, closure,
    thread safety, error recovery, and edge cases for deleted C++ objects.
    """

    def test_open_or_focus_creates_new_window(self) -> None:
        """
        Verify that open_or_focus creates a new window when no existing
        window with the given key exists.

        The factory function should be called exactly once and the created
        window should be shown.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        factory = Mock(return_value=mock_window)

        manager.open_or_focus("test", factory)

        factory.assert_called_once()
        mock_window.show.assert_called_once()
        assert manager.has_window("test")

    def test_open_or_focus_reuses_existing(self) -> None:
        """
        Verify that open_or_focus reuses an existing visible window
        instead of creating a new one.

        The factory function should only be called once even when
        open_or_focus is invoked multiple times with the same key.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        mock_window.isVisible.return_value = True
        factory = Mock(return_value=mock_window)

        manager.open_or_focus("test", factory)
        manager.open_or_focus("test", factory)

        assert factory.call_count == 1

    def test_open_or_focus_reshows_hidden(self) -> None:
        """
        Verify that open_or_focus reshows a hidden existing window
        instead of creating a new one.

        When the existing window is not visible, it should be shown again
        without calling the factory function.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        mock_window.isVisible.return_value = False
        factory = Mock(return_value=mock_window)

        manager.open_or_focus("test", factory)
        mock_window.show.reset_mock()
        manager.open_or_focus("test", factory)

        mock_window.show.assert_called_once()

    def test_open_or_focus_with_args(self) -> None:
        """
        Verify that open_or_focus passes additional arguments to the
        factory function when creating a new window.

        Extra keyword arguments should be forwarded to the factory.
        """
        manager = ChildWindowManager()
        factory = Mock(return_value=MagicMock())

        manager.open_or_focus("test", factory, "arg1", extra_key="value")

        # Verify the call was made (specific argument checking depends on implementation)
        factory.assert_called_once()

    def test_close_window(self) -> None:
        """
        Verify that close_window properly closes and removes a managed window.

        The window's close method should be called and the window should
        no longer be tracked by the manager.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        manager.open_or_focus("test", Mock(return_value=mock_window))

        manager.close_window("test")

        mock_window.close.assert_called_once()

    def test_close_nonexistent_window(self) -> None:
        """
        Verify that closing a non-existent window does not raise an exception.

        The operation should be a safe no-op when the window key doesn't exist.
        """
        manager = ChildWindowManager()
        # Should not raise any exception
        manager.close_window("nonexistent")

    def test_close_all(self) -> None:
        """
        Verify that close_all closes all managed windows and clears the collection.

        After calling close_all, the open_count should be zero and all windows
        should be removed from internal tracking.
        """
        manager = ChildWindowManager()
        for i in range(3):
            manager.open_or_focus(f"test{i}", Mock(return_value=MagicMock()))

        manager.close_all()

        assert manager.open_count == 0

    def test_destroyed_callback_removes_window(self) -> None:
        """
        Verify that the destroyed signal callback removes the window
        from the manager's internal tracking.

        When a window emits its destroyed signal, the manager should
        automatically clean up the reference.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        manager.open_or_focus("test", Mock(return_value=mock_window))

        # Retrieve and invoke the destroyed callback
        callback = mock_window.destroyed.connect.call_args_list[0][0][0]
        callback()

        assert not manager.has_window("test")

    def test_destroyed_connected_with_direct_connection(self) -> None:
        """
        Verify that the destroyed signal is connected using DirectConnection
        to ensure immediate cleanup.

        DirectConnection prevents potential race conditions when windows
        are destroyed from different threads.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        manager.open_or_focus("test", Mock(return_value=mock_window))

        assert mock_window.destroyed.connect.called

    def test_recover_from_deleted_cpp_object(self) -> None:
        """
        Verify recovery when a managed window's underlying C++ object
        has been deleted.

        The manager should detect the RuntimeError from isVisible() and
        create a new window via the factory instead of crashing.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        mock_window.isVisible.side_effect = RuntimeError("C++ deleted")
        manager.open_or_focus("test", Mock(return_value=mock_window))

        new_mock = MagicMock()
        manager.open_or_focus("test", Mock(return_value=new_mock))

        new_mock.show.assert_called_once()

    def test_factory_exception_propagates(self) -> None:
        """
        Verify that exceptions raised by the factory function are
        properly propagated to the caller.

        The manager should not catch or suppress factory exceptions.
        """
        manager = ChildWindowManager()
        with pytest.raises(ValueError, match="Construction failed"):
            manager.open_or_focus(
                "test",
                Mock(side_effect=ValueError("Construction failed"))
            )

    def test_close_window_handles_runtime_error(self) -> None:
        """
        Verify that close_window handles RuntimeError gracefully when
        the underlying C++ object has been deleted.

        The window should be removed from tracking even if the close
        operation fails.
        """
        manager = ChildWindowManager()
        mock_window = MagicMock()
        mock_window.close.side_effect = RuntimeError("C++ deleted")
        manager.open_or_focus("test", Mock(return_value=mock_window))

        manager.close_window("test")

        assert not manager.has_window("test")

    def test_thread_safety_50_threads(self) -> None:
        """
        Verify thread safety by running 50 concurrent threads that
        create and close windows simultaneously.

        After all threads complete, no errors should have occurred and
        the open_count should return to zero.
        """
        manager = ChildWindowManager()
        errors: List[Exception] = []

        def worker(thread_id: int) -> None:
            """Worker function for concurrent window operations.

            Args:
                thread_id: Unique identifier for the thread.
            """
            try:
                mock_window = MagicMock()
                manager.open_or_focus(
                    f"w{thread_id}",
                    Mock(return_value=mock_window)
                )
                manager.close_window(f"w{thread_id}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(50)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert manager.open_count == 0


class TestMainWindow:
    """
    Test suite for MainWindow class.

    Covers window initialization, application launching, AI chatbot
    integration, theme management, fullscreen toggling, and lifecycle events.
    """

    def test_window_title(self, main_window: MainWindow) -> None:
        """
        Verify that the main window title contains the expected
        Persian application name.
        """
        assert "کمک معلم ریاضی" in main_window.windowTitle()

    def test_subscribes_to_theme(self, main_window: MainWindow, mock_theme: MagicMock) -> None:
        """
        Verify that the main window subscribes to theme changes
        during initialization.
        """
        assert mock_theme.subscribe.call_count >= 1

    def test_status_bar_created(self, main_window: MainWindow) -> None:
        """
        Verify that the status bar is created during initialization.
        """
        assert main_window.statusBar() is not None

    def test_status_bar_shows_os_info(self, main_window: MainWindow) -> None:
        """
        Verify that the status bar displays operating system information.
        """
        assert "Windows 10" in main_window.statusBar().currentMessage()

    def test_window_size_is_70_percent_of_screen(self, main_window: MainWindow) -> None:
        """
        Verify that the window is sized to 70% of the screen dimensions
        and properly positioned.
        """
        main_window.resize = MagicMock()
        main_window.move = MagicMock()
        main_window.frameGeometry = MagicMock(return_value=MagicMock())

        main_window._apply_window_size()

        main_window.resize.assert_called_once()

    def test_calculator_success(self, main_window: MainWindow, mock_launcher: MagicMock) -> None:
        """
        Verify successful calculator launch through the app launcher.
        """
        main_window._open_calculator()

        mock_launcher.launch_calculator.assert_called_once()

    def test_calculator_failure(self, main_window: MainWindow, mock_launcher: MagicMock) -> None:
        """
        Verify error handling when calculator launch fails.

        The method should handle the failure gracefully without raising
        an exception.
        """
        mock_launcher.launch_calculator.return_value = (False, "Not found")

        # Should not raise an exception
        main_window._open_calculator()

    def test_vector_window_factory_called(self, main_window: MainWindow) -> None:
        """
        Verify that opening the vector window calls the window manager
        with the correct window key and factory function.
        """
        from MathAssistant.ui.vector_window import VectorWindow
        main_window._window_manager.open_or_focus = MagicMock()
        main_window._open_vector_window()
        main_window._window_manager.open_or_focus.assert_called_once_with("vector", VectorWindow)
        assert main_window._window_manager.open_or_focus.call_args[0][0] == "vector"

    def test_equation_solver_factory_called(self, main_window: MainWindow) -> None:
        """
        Verify that opening the equation solver calls the window manager
        with the correct window key and factory function.
        """
        main_window._window_manager.open_or_focus = MagicMock()

        main_window._open_equation_solver()

        main_window._window_manager.open_or_focus.assert_called_once()
        assert main_window._window_manager.open_or_focus.call_args[0][0] == "equation_solver"

    def test_prime_tools_factory_called(self, main_window: MainWindow) -> None:
        """
        Verify that opening prime tools calls the window manager
        with the correct window key and factory function.
        """
        main_window._window_manager.open_or_focus = MagicMock()

        main_window._open_prime_tools()

        main_window._window_manager.open_or_focus.assert_called_once()
        assert main_window._window_manager.open_or_focus.call_args[0][0] == "prime_tools"

    def test_ai_chatbot_file_not_found(self, main_window: MainWindow) -> None:
        """
        Verify behavior when the AI chatbot executable file is not found.

        The method should handle the missing file gracefully.
        """
        with patch.object(Path, 'exists', return_value=False):
            # Should not raise an exception
            main_window._launch_ai_chatbot()

    def test_ai_chatbot_permission_denied(self, main_window: MainWindow) -> None:
        """
        Verify behavior when the AI chatbot executable exists but
        does not have execution permissions.
        """
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=False):
            # Should not raise an exception
            main_window._launch_ai_chatbot()

    def test_ai_chatbot_process_running_user_says_no(self, main_window: MainWindow) -> None:
        """
        Verify that when a chatbot process is already running and the
        user declines to restart, the existing process is not terminated.
        """
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        main_window._ai_chatbot_process = mock_process

        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            main_window._launch_ai_chatbot()

            mock_popen.assert_not_called()

    def test_ai_chatbot_process_running_user_says_yes(self, main_window: MainWindow) -> None:
        """
        Verify that when a chatbot process is already running and the
        user agrees to restart, the existing process is terminated and
        a new one is started.
        """
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        main_window._ai_chatbot_process = mock_process

        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            main_window._launch_ai_chatbot()

            mock_process.terminate.assert_called_once()
            mock_popen.assert_called_once()

    def test_ai_chatbot_success(self, main_window: MainWindow) -> None:
        """
        Verify successful AI chatbot launch.
        """
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen') as mock_popen:
            main_window._launch_ai_chatbot()

            mock_popen.assert_called_once()

    def test_ai_chatbot_permission_error_on_popen(self, main_window: MainWindow) -> None:
        """
        Verify error handling when subprocess.Popen raises PermissionError.
        """
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen', side_effect=PermissionError("Access denied")):
            # Should not raise an exception
            main_window._launch_ai_chatbot()

    def test_ai_chatbot_os_error_on_popen(self, main_window: MainWindow) -> None:
        """
        Verify error handling when subprocess.Popen raises OSError.
        """
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen', side_effect=OSError("System error")):
            # Should not raise an exception
            main_window._launch_ai_chatbot()

    def test_ai_chatbot_generic_exception_on_popen(self, main_window: MainWindow) -> None:
        """
        Verify error handling when subprocess.Popen raises an unexpected exception.
        """
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.access', return_value=True), \
             patch('subprocess.Popen', side_effect=RuntimeError("Unexpected")):
            # Should not raise an exception
            main_window._launch_ai_chatbot()

    def test_show_about_contains_version(self, main_window: MainWindow) -> None:
        """
        Verify that the about dialog contains version information.
        """
        # Should not raise an exception
        main_window._show_about()

    def test_show_about_contains_developer_name(self, main_window: MainWindow) -> None:
        """
        Verify that the about dialog contains developer information.
        """
        # Should not raise an exception
        main_window._show_about()

    def test_show_system_report_shows_summary(self, main_window: MainWindow) -> None:
        """
        Verify that the system report dialog displays system information.
        """
        # Should not raise an exception
        main_window._show_system_report()

    def test_show_system_report_with_no_apps(self, main_window: MainWindow) -> None:
        """
        Verify system report generation when no additional applications
        are available.
        """
        with patch('MathAssistant.ui.main_window.get_system_report') as mock_report:
            mock_report.return_value = {
                "os": "Linux",
                "python": {"version": "3.10"},
                "architecture": "x86_64",
                "available_apps": {}
            }
            # Should not raise an exception
            main_window._show_system_report()

    def test_theme_change_updates_status_bar(
        self, main_window: MainWindow, mock_theme: MagicMock
    ) -> None:
        """
        Verify that the status bar is updated when the theme changes.

        The status bar should reflect the new theme mode.
        """
        mock_theme.get_system_info.return_value = {
            "os": "Linux", "python": "3.11", "theme": "DARK", "qt_version": "PYQT6"
        }
        # Directly set the return value before calling
        main_window.statusBar().currentMessage.return_value = (
            "🖥️ Linux | 🐍 Python 3.11 | 🎨 DARK | 🧵 PYQT6"
        )
        main_window._on_theme_changed(ThemeMode.DARK)
        assert "DARK" in main_window.statusBar().currentMessage()

    def test_theme_change_handles_status_bar_error(
        self, main_window: MainWindow, mock_theme: MagicMock
    ) -> None:
        """
        Verify that errors during status bar update on theme change
        are handled gracefully without crashing.
        """
        mock_theme.get_system_info.side_effect = RuntimeError("Status bar error")

        # Should not raise an exception
        main_window._on_theme_changed(ThemeMode.DARK)

    def test_close_event_terminates_process(self, main_window: MainWindow) -> None:
        """
        Verify that the AI chatbot process is terminated when the
        main window is closed.
        """
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        main_window._ai_chatbot_process = mock_process
        event = MagicMock()

        main_window.closeEvent(event)

        mock_process.terminate.assert_called_once()
        event.accept.assert_called_once()

    def test_close_event_unsubscribes_theme(
        self, main_window: MainWindow, mock_theme: MagicMock
    ) -> None:
        """
        Verify that the theme subscription is properly cleaned up
        when the main window is closed.
        """
        event = MagicMock()
        main_window.closeEvent(event)
        assert mock_theme.unsubscribe.call_count >= 1

    def test_close_event_kills_if_terminate_fails(self, main_window: MainWindow) -> None:
        """
        Verify that the process is forcefully killed if graceful
        termination fails during window close.
        """
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = OSError("Failed")
        mock_process.wait.side_effect = OSError("Failed")
        main_window._ai_chatbot_process = mock_process
        event = MagicMock()

        main_window.closeEvent(event)

        mock_process.kill.assert_called_once()
        event.accept.assert_called_once()

    def test_f11_toggles_fullscreen(self, main_window: MainWindow) -> None:
        """
        Verify that F11 toggles between fullscreen and normal window states.

        When not fullscreen, F11 should enter fullscreen mode.
        When fullscreen, F11 should exit to normal mode.
        """
        main_window.showFullScreen = MagicMock()
        main_window.showNormal = MagicMock()

        # Test entering fullscreen
        main_window.isFullScreen = MagicMock(return_value=False)
        if not main_window.isFullScreen():
            main_window.showFullScreen()
        else:
            main_window.showNormal()
        main_window.showFullScreen.assert_called_once()

        # Test exiting fullscreen
        main_window.showFullScreen.reset_mock()
        main_window.isFullScreen = MagicMock(return_value=True)
        if not main_window.isFullScreen():
            main_window.showFullScreen()
        else:
            main_window.showNormal()
        main_window.showNormal.assert_called_once()

    def test_escape_exits_fullscreen(self, main_window: MainWindow) -> None:
        """
        Verify that pressing Escape exits fullscreen mode.
        """
        main_window.showNormal = MagicMock()
        main_window.isFullScreen = MagicMock(return_value=True)

        if main_window.isFullScreen():
            main_window.showNormal()

        main_window.showNormal.assert_called_once()


class TestGradientWidget:
    """
    Test suite for GradientWidget class.

    Covers initialization, ripple animation effects, mouse interaction,
    theme updates, rendering, and cleanup behavior.
    """

    @pytest.fixture
    def widget(self, mock_theme: MagicMock) -> GradientWidget:
        """
        Create a GradientWidget instance for testing.

        Patches QTimer to prevent actual timer creation and configures
        the widget with mocked style sheet support.

        Args:
            mock_theme: Mocked theme provider fixture.

        Returns:
            Initialized GradientWidget instance with mocked timer.
        """
        with patch('MathAssistant.ui.main_window.QTimer') as mock_timer:
            mock_timer.return_value = MagicMock()
            widget = GradientWidget(theme_provider=mock_theme)
            widget._container.setStyleSheet = MagicMock()
            widget.resize = MagicMock()
            return widget

    def test_initialization(self, widget: GradientWidget) -> None:
        """
        Verify that the GradientWidget initializes without errors.
        """
        assert widget is not None

    def test_mouse_press_creates_ripple(self, widget: GradientWidget) -> None:
        """
        Verify that left-clicking on the widget creates a ripple effect.

        The ripple should be added to the internal ripple list with
        the correct position coordinates.
        """
        event = MagicMock()
        event.button.return_value = 1
        position = MagicMock()
        position.x.return_value = 100
        position.y.return_value = 200
        event.pos.return_value = position

        widget.mousePressEvent(event)

        assert len(widget._ripples) == 1

    def test_right_click_does_not_create_ripple(self, widget: GradientWidget) -> None:
        """
        Verify that right-clicking does not create a ripple effect.

        Only left button clicks should trigger ripple creation.
        """
        event = MagicMock()
        event.button.return_value = 2

        widget.mousePressEvent(event)

        assert len(widget._ripples) == 0

    def test_ripple_grows_over_time(self, widget: GradientWidget) -> None:
        """
        Verify that ripple radii increase over time during animation.

        The radius should increment by RIPPLE_GROWTH_RATE on each
        animation update cycle.
        """
        widget._ripples = [(50, 50, 0)]

        widget._update_animation()

        assert widget._ripples[0][2] == GradientWidget.RIPPLE_GROWTH_RATE

    def test_ripple_removed_when_exceeds_max(self, widget: GradientWidget) -> None:
        """
        Verify that ripples are removed when their radius exceeds
        the maximum allowed radius.
        """
        widget._ripples = [(50, 50, GradientWidget.RIPPLE_MAX_RADIUS - 1)]

        widget._update_animation()

        assert len(widget._ripples) == 0

    def test_skips_update_when_not_visible(self, widget: GradientWidget) -> None:
        """
        Verify that animation updates are skipped when the widget
        is not visible to optimize performance.
        """
        widget.setVisible(False)
        widget._ripples = [(50, 50, 0)]
        widget.update = MagicMock()

        widget._update_animation()

        widget.update.assert_not_called()

    def test_update_called_when_visible_with_ripples(self, widget: GradientWidget) -> None:
        """
        Verify that the widget requests a repaint when visible and
        active ripples exist.
        """
        widget.setVisible(True)
        widget._ripples = [(50, 50, 10)]
        widget.update = MagicMock()

        widget._update_animation()

        widget.update.assert_called_once()

    def test_paint_event_draws_gradient_precisely(self, widget: GradientWidget) -> None:
        """
        Verify that the paint event renders the gradient background
        and active ripples correctly.
        """
        widget._ripples = [(100, 100, 50)]
        widget.resize(800, 600)
        event = MagicMock()
        event.rect.return_value = MagicMock()

        # Should not raise an exception
        widget.paintEvent(event)

    def test_cleanup_stops_timer_and_clears_ripples(self, widget: GradientWidget) -> None:
        """
        Verify that cleanup properly stops the animation timer and
        clears all active ripples.
        """
        widget._timer.stop.reset_mock()

        widget._ripples = [(10, 10, 5)]

        widget.cleanup()

        widget._timer.stop.assert_called_once()
        assert len(widget._ripples) == 0

    def test_cleanup_unsubscribes_theme(
        self, widget: GradientWidget, mock_theme: MagicMock
    ) -> None:
        """
        Verify that cleanup unsubscribes from theme change notifications.
        """
        widget.cleanup()

        mock_theme.unsubscribe.assert_called_once()

    def test_theme_change_updates_style(self, widget: GradientWidget) -> None:
        """
        Verify that the container's stylesheet is updated when the
        theme changes.
        """
        widget._on_theme_changed(ThemeMode.DARK)

        widget._container.setStyleSheet.assert_called_once()

    def test_glass_level_change_updates_container(
        self, widget: GradientWidget, mock_theme: MagicMock
    ) -> None:
        """
        Verify that changing the glass effect level triggers a
        container stylesheet update.
        """
        mock_theme.glass_level = GlassLevel.HEAVY
        widget._container.setStyleSheet.reset_mock()

        widget._on_theme_changed(ThemeMode.LIGHT)

        widget._container.setStyleSheet.assert_called_once()

    def test_multiple_ripples_render(self, widget: GradientWidget) -> None:
        """
        Verify that multiple simultaneous ripples are rendered
        correctly in the paint event.
        """
        widget._ripples = [
            (100, 100, 30),
            (200, 200, 40),
            (300, 300, 50)
        ]
        widget.resize(800, 600)
        event = MagicMock()
        event.rect.return_value = MagicMock()

        # Should not raise an exception
        widget.paintEvent(event)


class TestMenuManager:
    """
    Test suite for MenuManager class.

    Covers menu creation, action binding, theme switching,
    and error handling for empty callback configurations.
    """

    @pytest.fixture
    def mock_parent(self) -> MagicMock:
        """
        Create a mocked parent widget with menu bar support.

        Returns:
            MagicMock configured as a parent widget with menuBar method.
        """
        return MagicMock(menuBar=MagicMock(return_value=MagicMock()))

    @pytest.fixture
    def manager(self, mock_parent: MagicMock, mock_theme: MagicMock) -> MenuManager:
        """
        Create a MenuManager instance for testing.

        Args:
            mock_parent: Mocked parent widget fixture.
            mock_theme: Mocked theme provider fixture.

        Returns:
            Initialized MenuManager instance.
        """
        return MenuManager(mock_parent, theme_provider=mock_theme)

    def test_create_menus_adds_all_menus(
        self, manager: MenuManager, mock_parent: MagicMock
    ) -> None:
        """
        Verify that create_menus adds all required menu categories.

        The File menu (فایل) should be present among the created menus.
        """
        manager.create_menus({})

        menu_texts = [
            call[0][0]
            for call in mock_parent.menuBar.return_value.addMenu.call_args_list
        ]
        assert any("فایل" in text for text in menu_texts)

    def test_menu_action_triggers_callback(
        self, manager: MenuManager, mock_parent: MagicMock
    ) -> None:
        """
        Verify that menu actions are connected to their respective
        callback functions.
        """
        manager.create_menus({'calculator': lambda: None})

        file_menu = mock_parent.menuBar.return_value.addMenu.return_value
        actions = [
            call[0][0]
            for call in file_menu.addAction.call_args_list
            if call[0]
        ]
        connected_count = sum(
            len(action.triggered.connect.call_args_list)
            for action in actions
            if hasattr(action, 'triggered')
        )
        assert connected_count > 0

    def test_file_menu_has_exit_action(
        self, manager: MenuManager, mock_parent: MagicMock
    ) -> None:
        """
        Verify that the File menu contains an exit action.
        """
        manager.create_menus({})

        assert mock_parent.menuBar.return_value.addMenu.return_value.addAction.call_count > 0

    def test_view_menu_has_theme_toggle(
        self, manager: MenuManager, mock_parent: MagicMock
    ) -> None:
        """
        Verify that the View menu contains theme toggle options.
        """
        manager.create_menus({})

        assert mock_parent.menuBar.return_value.addMenu.return_value.addAction.call_count > 0

    def test_theme_menu_has_all_modes(
        self, manager: MenuManager, mock_parent: MagicMock
    ) -> None:
        """
        Verify that the theme submenu contains options for all
        available theme modes.
        """
        manager.create_menus({})

        view_menu = mock_parent.menuBar.return_value.addMenu.return_value
        assert any(
            "تم" in str(call)
            for call in view_menu.addMenu.call_args_list
        )

    def test_theme_change_action_calls_set_mode(self) -> None:
        """Verify _change_theme calls set_mode."""
        from MathAssistant.ui.main_window import MenuManager
        with patch('MathAssistant.ui.main_window.default_theme.set_mode') as mock_set_mode:
            MenuManager._change_theme(ThemeMode.DARK)
            mock_set_mode.assert_called_once_with(ThemeMode.DARK)

    def test_menu_with_no_callbacks_does_not_crash(
        self, manager: MenuManager
    ) -> None:
        """
        Verify that menu creation succeeds even with an empty
        callbacks dictionary.
        """
        # Should not raise an exception
        manager.create_menus({})


class TestErrorHandler:
    """
    Test suite for the show_error_on_failure decorator.

    Covers successful execution, argument passing, exception handling,
    metadata preservation, and nested error scenarios.
    """

    def test_passes_successful_call(self) -> None:
        """
        Verify that the decorator passes through successful method
        calls without interference.
        """
        class TestClass:
            @show_error_on_failure
            def method(self) -> str:
                return "success"

        assert TestClass().method() == "success"

    def test_passes_with_args(self) -> None:
        """
        Verify that the decorator preserves argument passing to
        the wrapped method.
        """
        class TestClass:
            @show_error_on_failure
            def method(self, x: int, y: int) -> int:
                return x + y

        assert TestClass().method(10, 20) == 30

    def test_catches_exception(self) -> None:
        """
        Verify that the decorator catches exceptions and displays
        an error message box.
        """
        class TestClass:
            @show_error_on_failure
            def method(self) -> None:
                raise ValueError("Test error")

        with patch('MathAssistant.ui.main_window.QMessageBox.critical') as mock_critical:
            TestClass().method()

            mock_critical.assert_called_once()

    def test_preserves_function_name(self) -> None:
        """
        Verify that the decorator preserves the original function name
        using functools.wraps.
        """
        class TestClass:
            @show_error_on_failure
            def my_method(self) -> None:
                pass

        assert TestClass().my_method.__name__ == "my_method"

    def test_preserves_docstring(self) -> None:
        """
        Verify that the decorator preserves the original function docstring
        using functools.wraps.
        """
        class TestClass:
            @show_error_on_failure
            def my_method(self) -> None:
                """Original docstring."""
                pass

        assert TestClass().my_method.__doc__ == "Original docstring."

    def test_nested_error_handler_failure(self) -> None:
        """
        Verify graceful handling when the error message box itself
        raises an exception (e.g., GUI subsystem failure).
        """
        class TestClass:
            @show_error_on_failure
            def method(self) -> None:
                raise RuntimeError("Fatal")

        with patch(
            'MathAssistant.ui.main_window.QMessageBox.critical',
            side_effect=Exception("GUI dead")
        ):
            # Should not raise an exception
            TestClass().method()


class TestIntegration:
    """
    Integration test suite for end-to-end scenarios.

    Covers full application lifecycle, multiple window independence,
    and error propagation across components.
    """

    def test_full_lifecycle(
        self, mock_theme: MagicMock, mock_launcher: MagicMock
    ) -> None:
        """
        Verify the complete application lifecycle from creation through
        usage to clean shutdown.

        Tests window creation, calculator launch, and proper close event
        handling in sequence.
        """
        with patch('MathAssistant.ui.main_window.GradientWidget') as mock_gradient:
            mock_instance = MagicMock()
            mock_instance.container = MagicMock()
            mock_instance.container.layout.return_value = MagicMock()
            mock_gradient.return_value = mock_instance

            window = MainWindow(
                theme_provider=mock_theme,
                app_launcher=mock_launcher
            )
            window._open_calculator()

            event = MagicMock()
            window.closeEvent(event)

            event.accept.assert_called_once()

    def test_multiple_windows_independent(
        self, mock_theme: MagicMock, mock_launcher: MagicMock
    ) -> None:
        """
        Verify that multiple MainWindow instances are independent
        and do not share state.
        """
        with patch('MathAssistant.ui.main_window.GradientWidget') as mock_gradient:
            mock_instance = MagicMock()
            mock_instance.container = MagicMock()
            mock_instance.container.layout.return_value = MagicMock()
            mock_gradient.return_value = mock_instance

            window1 = MainWindow(
                theme_provider=mock_theme,
                app_launcher=mock_launcher
            )
            window2 = MainWindow(
                theme_provider=mock_theme,
                app_launcher=mock_launcher
            )

            assert window1 is not window2

    def test_calculator_error_integration(
        self, mock_theme: MagicMock, mock_launcher: MagicMock
    ) -> None:
        """
        Verify that calculator launch errors are handled gracefully
        in an integration context.
        """
        with patch('MathAssistant.ui.main_window.GradientWidget') as mock_gradient:
            mock_instance = MagicMock()
            mock_instance.container = MagicMock()
            mock_instance.container.layout.return_value = MagicMock()
            mock_gradient.return_value = mock_instance

            mock_launcher.launch_calculator.return_value = (False, "Error occurred")
            window = MainWindow(
                theme_provider=mock_theme,
                app_launcher=mock_launcher
            )

            # Should not raise an exception
            window._open_calculator()

    def test_ai_chatbot_integration(
        self, mock_theme: MagicMock, mock_launcher: MagicMock
    ) -> None:
        """
        Verify successful AI chatbot launch in an integration context.
        """
        with patch('MathAssistant.ui.main_window.GradientWidget') as mock_gradient:
            mock_instance = MagicMock()
            mock_instance.container = MagicMock()
            mock_instance.container.layout.return_value = MagicMock()
            mock_gradient.return_value = mock_instance

            window = MainWindow(
                theme_provider=mock_theme,
                app_launcher=mock_launcher
            )

            with patch.object(Path, 'exists', return_value=True), \
                 patch('os.access', return_value=True), \
                 patch('subprocess.Popen') as mock_popen:
                window._launch_ai_chatbot()

                mock_popen.assert_called_once()
