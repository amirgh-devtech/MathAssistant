"""
پنجره اصلی برنامه MathAssistant - نسخه نهایی Production-Ready

این ماژول شامل پنجره اصلی برنامه با معماری کاملاً refactored شده است:

Components:
- GradientWidget: پس‌زمینه گرادیانت متحرک (Dependency Injection, CPU Optimized)
- ChildWindowManager: مدیریت پنجره‌های فرزند (Thread-Safe, No Memory Leak)
- MenuManager: مدیریت منوها (SRP, Dynamic Menu Support)
- MainWindow: Facade با Dependency Injection کامل

Design Patterns:
- Dependency Injection: Theme, AppLauncher, ChildWindowManager
- Singleton: ThemeManager
- Strategy: ChildWindowManager
- Observer: Theme changes
- Facade: MainWindow
- Factory Method: ChildWindowManager.open_or_focus

SOLID Principles:
- S: Single Responsibility (هر کلاس یک وظیفه)
- O: Open/Closed (قابل گسترش بدون تغییر کد موجود)
- L: Liskov Substitution (ThemeProvider Protocol)
- I: Interface Segregation (پروتکل‌های مجزا)
- D: Dependency Inversion (وابستگی به abstraction)

Thread Safety:
- ChildWindowManager: Lock برای open_or_focus
- GradientWidget: QTimer در Main Thread
- Qt Signals: DirectConnection برای پاکسازی فوری

Testability: Full (همه وابستگی‌ها injectable)

Author: AmirMohammad Ghasemzadeh
Version: 4.0.0 - Production Ready
"""

import os
import sys
import math
import logging
import threading
from typing import (
    Optional, List, Tuple, Dict, Callable, Any, Protocol, runtime_checkable
)
from functools import partial, wraps

from MathAssistant.ui.styles import (
    theme as default_theme,
    ThemeMode, GlassLevel, ShadowElevation,
    SystemDetector, QtAdapter, GlassmorphismSystem
)
from MathAssistant.utils.system_tools import (
    SystemToolLauncher as DefaultAppLauncher,
    SystemInfo, ProjectPaths, get_system_report
)

# آداپتور Qt
_adapter = QtAdapter()

# ایمپورت کلاس‌های Qt
QApplication = _adapter.QApplication
QMainWindow = _adapter.QMainWindow
QWidget = _adapter.QWidget
QLabel = _adapter.QLabel
QVBoxLayout = _adapter.QVBoxLayout
QHBoxLayout = _adapter.QHBoxLayout
QGridLayout = _adapter.QGridLayout
QPushButton = _adapter.QPushButton
QFrame = _adapter.QFrame
QMenuBar = _adapter.QMenuBar
QAction = _adapter.QAction
QKeySequence = _adapter.QKeySequence
QShortcut = _adapter.QShortcut
QTimer = _adapter.QTimer
QMessageBox = _adapter.QMessageBox
QSize = _adapter.QSize
QRect = _adapter.QRect
QPixmap = _adapter.QPixmap
QFont = _adapter.QFont
QFontDatabase = _adapter.QFontDatabase
QColor = _adapter.QColor
QPainter = _adapter.QPainter
QLinearGradient = _adapter.QLinearGradient
QRadialGradient = _adapter.QRadialGradient
QGraphicsView = _adapter.QGraphicsView
QGraphicsScene = _adapter.QGraphicsScene
QGraphicsPixmapItem = _adapter.QGraphicsPixmapItem
QTransform = _adapter.QTransform

# Enums
Qt = _adapter.Qt
AlignCenter = _adapter.AlignCenter
AlignRight = _adapter.AlignRight
AlignLeft = _adapter.AlignLeft
RichText = _adapter.RichText
PlainText = _adapter.PlainText

logger = logging.getLogger(__name__)


# ============================================================================
# Protocols (Dependency Inversion)
# ============================================================================

@runtime_checkable
class ThemeProvider(Protocol):
    """پروتکل برای theme provider - قابل تعویض برای تست."""

    @property
    def mode(self) -> ThemeMode: ...
    @property
    def is_dark(self) -> bool: ...
    @property
    def glass_level(self) -> GlassLevel: ...
    @property
    def qt_version(self) -> Any: ...
    @property
    def windows_version(self) -> str: ...

    def color(self, key: str) -> str: ...
    def get_app_font(self) -> Any: ...
    def get_title_font(self) -> Any: ...
    def get_font(self, **kwargs) -> Any: ...
    def get_button_style(self, *args, **kwargs) -> str: ...
    def get_menu_bar_style(self) -> str: ...
    def get_status_bar_style(self) -> str: ...
    def get_message_box_style(self) -> str: ...
    def get_system_info(self) -> Dict[str, Any]: ...
    def set_mode(self, mode: ThemeMode) -> None: ...
    def toggle_dark_light(self) -> None: ...
    def subscribe(self, callback: Callable) -> None: ...
    def unsubscribe(self, callback: Callable) -> None: ...


@runtime_checkable
class AppLauncherProtocol(Protocol):
    """پروتکل برای app launcher - قابل تعویض برای تست."""

    @staticmethod
    def launch_calculator() -> Tuple[bool, str]: ...
    @staticmethod
    def launch_browser(url: str = "") -> Tuple[bool, str]: ...
    @staticmethod
    def launch_file_explorer(path: str = ".") -> Tuple[bool, str]: ...


# ============================================================================
# Error Handling Decorator
# ============================================================================

def show_error_on_failure(func: Callable) -> Callable:
    """
    Decorator برای نمایش خطاهای غیرمنتظره در QMessageBox.

    تمام Exceptionهای پیش‌بینی نشده را catch کرده و
    به کاربر نمایش می‌دهد بدون اینکه برنامه crash کند.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            try:
                QMessageBox.critical(
                    self, "خطای غیرمنتظره",
                    f"متأسفانه خطایی رخ داد:\n\n{str(e)}\n\n"
                    f"لطفاً این خطا را به تیم توسعه گزارش دهید."
                )
            except Exception:
                pass
    return wrapper


# ============================================================================
# Gradient Widget - پس‌زمینه متحرک
# ============================================================================

class GradientWidget(QWidget):
    """
    ویجت پس‌زمینه با گرادیانت چرخشی و ripple effect.

    Design:
    - Dependency Injection برای theme
    - CPU Optimization (visibility check, dirty regions)
    - Cleanup کامل (timer, theme subscription, ripples)
    """

    # ثابت‌های انیمیشن
    ANIMATION_FPS: int = 30
    ANIMATION_INTERVAL: int = 1000 // ANIMATION_FPS
    RIPPLE_GROWTH_RATE: float = 4.0
    RIPPLE_MAX_RADIUS: float = 300.0
    RIPPLE_INITIAL_ALPHA: int = 150
    RIPPLE_ALPHA_DECAY: float = 0.8
    GRADIENT_ROTATION_SPEED: float = 1.0
    GRADIENT_OFFSET_SPEED: float = 0.5

    # رنگ‌های پیش‌فرض (Fallback)
    DEFAULT_COLORS: List[QColor] = [
        QColor(74, 144, 226),
        QColor(106, 82, 181),
        QColor(142, 68, 173),
    ]

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        theme_provider: Optional[ThemeProvider] = None
    ):
        super().__init__(parent)

        self._theme = theme_provider or default_theme

        # State
        self._gradient_offset: float = 0.0
        self._gradient_angle: float = 130.0
        self._ripples: List[Tuple[float, float, float]] = []
        self._is_animating: bool = True

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(self.ANIMATION_INTERVAL)

        # Layout با container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._container = QLabel()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(20, 20, 20, 20)
        self._container.setLayout(container_layout)
        self._container.setAlignment(AlignCenter)

        main_layout.addWidget(self._container)

        self.setMinimumSize(400, 300)
        self._update_container_style()

        # Subscribe به تغییرات تم
        if hasattr(self._theme, 'subscribe'):
            self._theme.subscribe(self._on_theme_changed)

    def _on_theme_changed(self, mode: ThemeMode) -> None:
        """واکنش به تغییر تم."""
        self._update_container_style()
        self.update()

    def _update_container_style(self) -> None:
        """به‌روزرسانی استایل container."""
        try:
            glass = GlassmorphismSystem.get_glass_style_sheet(
                self._theme.glass_level,
                (255, 255, 255, 220) if not self._theme.is_dark else (30, 30, 50, 200)
            )
            self._container.setStyleSheet(f"""
                QLabel {{
                    border: 2px solid rgba(255, 255, 255, 80);
                    border-radius: 15px;
                    background-color: rgba(255, 255, 255, 30);
                    margin: 15px;
                    {glass}
                }}
            """)
        except Exception as e:
            logger.warning(f"Failed to update container style: {e}")

    def _update_animation(self) -> None:
        """به‌روزرسانی فریم انیمیشن."""
        if not self.isVisible():
            return

        self._gradient_offset = (
            self._gradient_offset + self.GRADIENT_OFFSET_SPEED
        ) % 100
        self._gradient_angle = (
            self._gradient_angle + self.GRADIENT_ROTATION_SPEED
        ) % 360

        active_ripples = []
        for x, y, radius in self._ripples:
            new_radius = radius + self.RIPPLE_GROWTH_RATE
            if new_radius < self.RIPPLE_MAX_RADIUS:
                active_ripples.append((x, y, new_radius))
        self._ripples = active_ripples

        if self._ripples or self._is_animating:
            self.update()

    def paintEvent(self, event) -> None:
        """رسم گرادیانت و rippleها."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRect(event.rect())

        angle_rad = math.radians(self._gradient_angle)
        cx, cy = self.width() / 2, self.height() / 2

        x1 = int(cx * (1 + math.cos(angle_rad)))
        y1 = int(cy * (1 - math.sin(angle_rad)))
        x2 = int(cx * (1 - math.cos(angle_rad)))
        y2 = int(cy * (1 + math.sin(angle_rad)))

        gradient = QLinearGradient(x1, y1, x2, y2)

        try:
            colors = [
                QColor(self._theme.color('gradient_start')),
                QColor(self._theme.color('gradient_mid')),
                QColor(self._theme.color('gradient_end')),
            ]
        except Exception:
            colors = self.DEFAULT_COLORS

        for i, color in enumerate(colors):
            pos = (
                self._gradient_offset + i * (100 / len(colors))
            ) % 100 / 100.0
            gradient.setColorAt(pos, color)

        painter.fillRect(self.rect(), gradient)

        for x, y, radius in self._ripples:
            alpha = max(
                0,
                self.RIPPLE_INITIAL_ALPHA - int(radius * self.RIPPLE_ALPHA_DECAY)
            )
            if alpha > 0:
                ripple = QRadialGradient(x, y, radius)
                ripple.setColorAt(0, QColor(255, 255, 255, alpha))
                ripple.setColorAt(1, QColor(255, 255, 255, 0))
                painter.fillRect(self.rect(), ripple)

    def mousePressEvent(self, event) -> None:
        """ثبت کلیک برای ripple effect."""
        if event.button() == Qt.LeftButton:
            self._ripples.append((
                float(event.pos().x()),
                float(event.pos().y()),
                0.0
            ))
        super().mousePressEvent(event)

    def cleanup(self) -> None:
        """پاکسازی کامل منابع."""
        self._timer.stop()
        self._timer.deleteLater()
        self._ripples.clear()
        if hasattr(self._theme, 'unsubscribe'):
            self._theme.unsubscribe(self._on_theme_changed)

    @property
    def container(self) -> QLabel:
        return self._container


# ============================================================================
# Child Window Manager (Thread-Safe)
# ============================================================================

class ChildWindowManager:
    """
    مدیریت پنجره‌های فرزند - Thread-Safe با چرخه حیات کامل.

    Features:
    - Thread-Safe با Lock
    - DirectConnection برای پاکسازی فوری
    - Lazy loading با factory
    - No Memory Leak (destroyed.connect)
    """

    def __init__(self):
        self._windows: Dict[str, Any] = {}
        self._lock = threading.RLock()
        logger.debug("ChildWindowManager initialized")

    def open_or_focus(
        self,
        key: str,
        factory: Callable[[], Any],
        *factory_args,
        **factory_kwargs
    ) -> None:
        """
        باز کردن یا focus کردن پنجره (Thread-Safe).

        Args:
            key: کلید یکتا
            factory: تابع سازنده
            *factory_args, **factory_kwargs: آرگومان‌های factory
        """
        with self._lock:
            # Check existing window
            if key in self._windows:
                try:
                    window = self._windows[key]
                    if hasattr(window, 'isVisible') and not window.isVisible():
                        window.show()
                    window.raise_()
                    window.activateWindow()
                    return
                except RuntimeError:
                    del self._windows[key]

            # Create new window
            try:
                window = factory(*factory_args, **factory_kwargs)
                self._windows[key] = window

                # DirectConnection برای پاکسازی فوری
                if hasattr(window, 'destroyed'):
                    window.destroyed.connect(
                        lambda obj=None, k=key: self._on_window_destroyed(k),
                        Qt.ConnectionType.DirectConnection
                        if hasattr(Qt, 'ConnectionType')
                        else Qt.DirectConnection
                    )

                window.show()
                logger.debug(f"Child window opened: {key}")

            except Exception as e:
                logger.error(f"Failed to create child window '{key}': {e}")
                raise

    def _on_window_destroyed(self, key: str) -> None:
        """Callback پاکسازی فوری."""
        with self._lock:
            if key in self._windows:
                del self._windows[key]
                logger.debug(f"Child window destroyed: {key}")

    def close_window(self, key: str) -> None:
        """بستن یک پنجره."""
        with self._lock:
            if key in self._windows:
                try:
                    self._windows[key].close()
                except RuntimeError:
                    pass
                finally:
                    self._windows.pop(key, None)

    def close_all(self) -> None:
        """بستن همه پنجره‌ها."""
        with self._lock:
            for key in list(self._windows.keys()):
                self.close_window(key)
            logger.debug("All child windows closed")

    @property
    def open_count(self) -> int:
        with self._lock:
            return len(self._windows)

    def has_window(self, key: str) -> bool:
        with self._lock:
            return key in self._windows


# ============================================================================
# Menu Manager (SRP)
# ============================================================================

class MenuManager:
    """مدیریت منوها با مسئولیت واحد."""

    def __init__(
        self,
        parent: QMainWindow,
        theme_provider: Optional[ThemeProvider] = None
    ):
        self._parent = parent
        self._theme = theme_provider or default_theme

    def create_menus(self, callbacks: Dict[str, Callable]) -> None:
        """ایجاد تمام منوها."""
        menubar = self._parent.menuBar()
        menubar.setStyleSheet(self._theme.get_menu_bar_style())

        self._create_file_menu(menubar, callbacks)
        self._create_view_menu(menubar)
        self._create_tools_menu(menubar, callbacks)

    def _create_file_menu(
        self, menubar: Any, callbacks: Dict[str, Callable]
    ) -> None:
        """منوی فایل."""
        file_menu = menubar.addMenu("📁 &فایل")

        items = [
            ("🤖 اجرای دستیار هوش مصنوعی", callbacks.get('ai_chatbot'), "Ctrl+T"),
            ("🔢 باز کردن ماشین حساب", callbacks.get('calculator'), "Ctrl+C"),
            ("📐 پنجره بردارها", callbacks.get('vector'), "Ctrl+V"),
            ("📝 حل معادلات", callbacks.get('equation'), "Ctrl+E"),
            ("🧮 ابزار اعداد اول", callbacks.get('prime'), "Ctrl+P"),
            ("", None, None),
            ("ℹ️ درباره برنامه", callbacks.get('about'), "Ctrl+A"),
            ("", None, None),
            ("🚪 خروج", self._parent.close, "Ctrl+Q"),
        ]

        for text, callback, shortcut in items:
            if not text:
                file_menu.addSeparator()
                continue
            action = QAction(text, self._parent)
            if callback:
                action.triggered.connect(callback)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            file_menu.addAction(action)

    def _create_view_menu(self, menubar: Any) -> None:
        """منوی نمایش."""
        view_menu = menubar.addMenu("🎨 &نمایش")

        themes_menu = view_menu.addMenu("تم رنگی")
        for mode in ThemeMode:
            action = QAction(
                f"  {mode.name.replace('_', ' ').title()}",
                self._parent
            )
            action.triggered.connect(partial(self._change_theme, mode))
            themes_menu.addAction(action)

        view_menu.addSeparator()

        toggle_action = QAction("🌓 تغییر تم روشن/تاریک", self._parent)
        toggle_action.triggered.connect(self._theme.toggle_dark_light)
        toggle_action.setShortcut(QKeySequence("Ctrl+D"))
        view_menu.addAction(toggle_action)

    def _create_tools_menu(
        self, menubar: Any, callbacks: Dict[str, Callable]
    ) -> None:
        """منوی ابزارها."""
        tools_menu = menubar.addMenu("🔧 &ابزارها")

        report_action = QAction("📊 گزارش سیستم", self._parent)
        callback = callbacks.get('system_report')
        if callback:
            report_action.triggered.connect(callback)
        tools_menu.addAction(report_action)

    @staticmethod
    def _change_theme(mode: ThemeMode) -> None:
        """تغییر تم."""
        default_theme.set_mode(mode)


# ============================================================================
# Main Window (Facade)
# ============================================================================

class MainWindow(QMainWindow):
    """
    پنجره اصلی - نسخه ۴.۰.۰.

    Dependency Injection کامل برای testability.
    """

    WINDOW_TITLE: str = "کمک معلم ریاضی | Math Assistant"
    APP_VERSION: str = "4.0.0"

    def __init__(
        self,
        theme_provider: Optional[ThemeProvider] = None,
        app_launcher: Optional[AppLauncherProtocol] = None,
        window_manager: Optional[ChildWindowManager] = None
    ):
        super().__init__()

        # Dependency Injection
        self._theme = theme_provider or default_theme
        self._launcher = app_launcher or DefaultAppLauncher
        self._window_manager = window_manager or ChildWindowManager()

        self._menu_manager = MenuManager(self, self._theme)
        self._ai_chatbot_process: Optional[Any] = None

        self._init_window()
        self._init_ui()
        self._create_menus()
        self._create_status_bar()
        self._setup_shortcuts()

        if hasattr(self._theme, 'subscribe'):
            self._theme.subscribe(self._on_theme_changed)

        logger.info("MainWindow initialized (v4.0.0)")

    def _init_window(self) -> None:
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setFont(self._theme.get_app_font())
        self._apply_window_size()
        self.setMinimumSize(800, 600)

    def _apply_window_size(self) -> None:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                window_size = QSize(
                    int(geometry.width() * 0.7),
                    int(geometry.height() * 0.7)
                )
                self.resize(window_size)
                frame_geometry = self.frameGeometry()
                center_point = geometry.center()
                frame_geometry.moveCenter(center_point)
                self.move(frame_geometry.topLeft())
        except Exception as e:
            logger.warning(f"Failed to set window size: {e}")

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._gradient = GradientWidget(theme_provider=self._theme)
        main_layout.addWidget(self._gradient)

        container_layout = self._gradient.container.layout()

        title_label = QLabel("📐 کمک معلم ریاضی")
        title_label.setFont(self._theme.get_title_font())
        title_label.setAlignment(AlignCenter)
        title_label.setStyleSheet("color: white; margin-bottom: 10px;")
        container_layout.addWidget(title_label)

        version_label = QLabel(f"نسخه {self.APP_VERSION}")
        version_label.setFont(self._theme.get_font(size=10))
        version_label.setAlignment(AlignCenter)
        version_label.setStyleSheet(
            "color: rgba(255, 255, 255, 180); margin-bottom: 20px;"
        )
        container_layout.addWidget(version_label)

        self._setup_buttons(container_layout)

    def _setup_buttons(self, layout: QVBoxLayout) -> None:
        button_grid = QGridLayout()
        button_grid.setContentsMargins(20, 20, 20, 20)
        button_grid.setSpacing(12)

        buttons_data = [
            ("🧮 ابزار اعداد اول", self._open_prime_tools, "Ctrl+P",
             "ابزارهای پیشرفته برای کار با اعداد اول", 0, 0, 1, 3),
            ("🔢 ماشین حساب", self._open_calculator, "Ctrl+C",
             "باز کردن ماشین حساب سیستم", 1, 0, 1, 1),
            ("📐 بردار و مختصات", self._open_vector_window, "Ctrl+V",
             "رسم و محاسبه بردارها", 1, 1, 1, 1),
            ("📝 حل معادلات", self._open_equation_solver, "Ctrl+E",
             "حل گام‌به‌گام معادلات ریاضی", 1, 2, 1, 1),
            ("🤖 دستیار هوش مصنوعی", self._launch_ai_chatbot, "Ctrl+T",
             "اجرای چت‌بات هوش مصنوعی", 2, 0, 1, 3),
            ("ℹ️ درباره برنامه", self._show_about, "Ctrl+A",
             "اطلاعات نسخه و توسعه‌دهنده", 3, 0, 1, 3),
        ]

        for text, callback, shortcut, tooltip, row, col, rs, cs in buttons_data:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            btn.setToolTip(f"{tooltip}\nمیانبر: {shortcut}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                self._theme.get_button_style("primary", "large", full_width=True)
            )
            button_grid.addWidget(btn, row, col, rs, cs)

        layout.addLayout(button_grid)

    def _create_menus(self) -> None:
        callbacks = {
            'ai_chatbot': self._launch_ai_chatbot,
            'calculator': self._open_calculator,
            'vector': self._open_vector_window,
            'equation': self._open_equation_solver,
            'prime': self._open_prime_tools,
            'about': self._show_about,
            'system_report': self._show_system_report,
        }
        self._menu_manager.create_menus(callbacks)

    def _create_status_bar(self) -> None:
        status = self.statusBar()
        try:
            status.setStyleSheet(self._theme.get_status_bar_style())
        except Exception:
            pass
        try:
            info = self._theme.get_system_info()
            status.showMessage(
                f"🖥️ {info['os']} | 🐍 Python {info['python']} | "
                f"🎨 {info['theme']} | 🧵 {info['qt_version']}"
            )
        except Exception:
            status.showMessage("Math Assistant")

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("F11"), self).activated.connect(
            lambda: self.showFullScreen() if not self.isFullScreen()
            else self.showNormal()
        )
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            lambda: self.showNormal() if self.isFullScreen() else None
        )

    def _on_theme_changed(self, mode: ThemeMode) -> None:
        try:
            self._create_status_bar()
        except Exception:
            pass

    # ========================================================================
    # Window Openers
    # ========================================================================

    @show_error_on_failure
    def _open_calculator(self) -> None:
        success, message = self._launcher.launch_calculator()
        if not success:
            QMessageBox.warning(self, "خطا", message)

    @show_error_on_failure
    def _open_vector_window(self) -> None:
        from MathAssistant.ui.vector_window import VectorWindow
        self._window_manager.open_or_focus("vector", VectorWindow)

    @show_error_on_failure
    def _open_equation_solver(self) -> None:
        from MathAssistant.ui.equation_solver_ui import EquationSolverWindow
        self._window_manager.open_or_focus(
            "equation_solver", EquationSolverWindow
        )

    @show_error_on_failure
    def _open_prime_tools(self) -> None:
        from MathAssistant.ui.prime_tools_ui import PrimeToolsWindow
        self._window_manager.open_or_focus("prime_tools", PrimeToolsWindow)

    @show_error_on_failure
    def _launch_ai_chatbot(self) -> None:
        script_path = ProjectPaths.get_root() / "Math-bot.py"

        if not script_path.exists():
            QMessageBox.warning(
                self, "خطا",
                f"فایل Math-bot.py یافت نشد.\nمسیر: {script_path}"
            )
            return

        # Check existing process
        if self._ai_chatbot_process and self._ai_chatbot_process.poll() is None:
            reply = QMessageBox.question(
                self, "در حال اجرا",
                "دستیار هوش مصنوعی در حال اجراست. اجرای مجدد؟",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            try:
                self._ai_chatbot_process.terminate()
                self._ai_chatbot_process.wait(timeout=5)
            except Exception:
                pass

        # Check permissions
        if not os.access(str(script_path), os.R_OK | os.X_OK):
            QMessageBox.warning(self, "خطا", "فایل قابل خواندن یا اجرا نیست.")
            return

        import subprocess
        try:
            self._ai_chatbot_process = subprocess.Popen(
                [sys.executable, str(script_path)],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            QMessageBox.information(self, "اجرا شد", "دستیار هوش مصنوعی اجرا شد.")
        except PermissionError:
            QMessageBox.warning(self, "خطا", "دسترسی کافی برای اجرا نیست.")
        except OSError as e:
            QMessageBox.critical(self, "خطای سیستم", str(e))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای غیرمنتظره: {e}")

    @show_error_on_failure
    def _show_about(self) -> None:
        about_text = f"""
            <div style='text-align: left; direction: rtl; font-size: 12pt;'>
            <h3 style='color: {self._theme.color('primary')};'>
            📐 کمک معلم ریاضی</h3>
            <p><b>نسخه:</b> {self.APP_VERSION}</p>
            <p>مجموعه ابزار ریاضی پیشرفته</p>
            <hr>
            <p><b>🖥️ سیستم:</b><br>
            {self._theme.windows_version} | Qt: {self._theme.qt_version.name}<br>
            Python: {sys.version.split()[0]}</p>
            <hr>
            <p><b>👨‍💻 توسعه‌دهنده:</b> امیرمحمد قاسم‌زاده</p>
            </div>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("درباره برنامه")
        msg.setIcon(QMessageBox.Information)
        msg.setTextFormat(RichText)
        msg.setMinimumSize(450, 400)
        msg.setText(about_text)
        msg.setStyleSheet(self._theme.get_message_box_style())
        msg.exec_()

    @show_error_on_failure
    def _show_system_report(self) -> None:
        import json
        report = get_system_report()
        report_text = json.dumps(report, indent=2, ensure_ascii=False)

        msg = QMessageBox(self)
        msg.setWindowTitle("گزارش سیستم")
        msg.setIcon(QMessageBox.Information)
        msg.setDetailedText(report_text)
        msg.setText(
            f"سیستم‌عامل: {report['os']}\n"
            f"Python: {report['python']['version']}\n"
            f"معماری: {report['architecture']}\n"
            f"برنامه‌های در دسترس: "
            f"{sum(1 for v in report['available_apps'].values() if v)}/"
            f"{len(report['available_apps'])}"
        )
        msg.setStyleSheet(self._theme.get_message_box_style())
        msg.exec_()

    # ========================================================================
    # Window Events
    # ========================================================================

    def closeEvent(self, event) -> None:
        """پاکسازی کامل."""
        logger.info("MainWindow closing...")

        self._window_manager.close_all()

        if self._ai_chatbot_process and self._ai_chatbot_process.poll() is None:
            try:
                self._ai_chatbot_process.terminate()
                self._ai_chatbot_process.wait(timeout=5)
            except Exception:
                try:
                    self._ai_chatbot_process.kill()
                except Exception:
                    pass

        if hasattr(self, '_gradient'):
            self._gradient.cleanup()

        if hasattr(self._theme, 'unsubscribe'):
            self._theme.unsubscribe(self._on_theme_changed)

        event.accept()
        logger.info("MainWindow closed")
