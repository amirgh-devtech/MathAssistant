# tests/conftest.py
"""
Fixtures مشترک برای تست Theme Module - نسخه کامل و بینقص

این فایل:
- Qt رو قبل از import ماژول Mock می‌کنه
- تمام Singletonها رو مدیریت می‌کنه
- Fixtureهای جامع برای همه بخش‌ها داره
- از تست‌های Unit تا Accessibility رو پوشش میده
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

# ============================================================================
# مرحله ۰: تنظیم مسیر پروژه
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

# ============================================================================
# مرحله ۱: Mock کردن Qt قبل از هر import
# ============================================================================

def _mock_qt_modules():
    """Mock کامل همه ماژول‌های Qt قبل از import styles.py"""

    # --- PyQt6 Mocks ---
    _mock_pyqt6_core = MagicMock()
    _mock_pyqt6_gui = MagicMock()
    _mock_pyqt6_widgets = MagicMock()

    # --- PyQt5 Mocks ---
    _mock_pyqt5_core = MagicMock()
    _mock_pyqt5_gui = MagicMock()
    _mock_pyqt5_widgets = MagicMock()

    # ========================================================================
    # QtCore Mock
    # ========================================================================
    for _mock_core in [_mock_pyqt6_core, _mock_pyqt5_core]:
        # QTimer
        _mock_core.QTimer = MagicMock()
        _mock_core.QTimer.singleShot = MagicMock()

        # QPropertyAnimation
        _mock_core.QPropertyAnimation = MagicMock()

        # QEasingCurve
        _mock_core.QEasingCurve = MagicMock()
        _mock_core.QEasingCurve.Type = MagicMock()
        _mock_core.QEasingCurve.OutCubic = 1
        _mock_core.QEasingCurve.InOutCubic = 2
        _mock_core.QEasingCurve.Linear = 3

        # QParallelAnimationGroup
        _mock_core.QParallelAnimationGroup = MagicMock()

        # Qt Enums (مهم!)
        _mock_core.Qt = MagicMock()
        _mock_core.Qt.AlignCenter = 0x0004
        _mock_core.Qt.AlignRight = 0x0002
        _mock_core.Qt.AlignLeft = 0x0001
        _mock_core.Qt.AlignTop = 0x0020
        _mock_core.Qt.AlignBottom = 0x0040
        _mock_core.Qt.ItemIsUserCheckable = 0x1000
        _mock_core.Qt.Unchecked = 0
        _mock_core.Qt.Checked = 2
        _mock_core.Qt.PartiallyChecked = 1
        _mock_core.Qt.RichText = 1
        _mock_core.Qt.PlainText = 0
        _mock_core.Qt.AA_EnableHighDpiScaling = 1
        _mock_core.Qt.AA_UseHighDpiPixmaps = 2

        # AlignmentFlag (PyQt6)
        _mock_core.Qt.AlignmentFlag = MagicMock()
        _mock_core.Qt.AlignmentFlag.AlignCenter = 0x0004
        _mock_core.Qt.AlignmentFlag.AlignRight = 0x0002
        _mock_core.Qt.AlignmentFlag.AlignLeft = 0x0001
        _mock_core.Qt.AlignmentFlag.AlignTop = 0x0020
        _mock_core.Qt.AlignmentFlag.AlignBottom = 0x0040

        # ItemFlag (PyQt6)
        _mock_core.Qt.ItemFlag = MagicMock()
        _mock_core.Qt.ItemFlag.ItemIsUserCheckable = 0x1000

        # CheckState (PyQt6)
        _mock_core.Qt.CheckState = MagicMock()
        _mock_core.Qt.CheckState.Unchecked = 0
        _mock_core.Qt.CheckState.Checked = 2
        _mock_core.Qt.CheckState.PartiallyChecked = 1

        # TextFormat (PyQt6)
        _mock_core.Qt.TextFormat = MagicMock()
        _mock_core.Qt.TextFormat.RichText = 1
        _mock_core.Qt.TextFormat.PlainText = 0

        # Signal
        _mock_core.pyqtSignal = MagicMock(return_value=MagicMock())

        # Other
        _mock_core.QPointF = MagicMock()
        _mock_core.QEvent = MagicMock()
        _mock_core.QSize = MagicMock()
        _mock_core.QRect = MagicMock()

    # ========================================================================
    # QtGui Mock
    # ========================================================================
    for _mock_gui in [_mock_pyqt6_gui, _mock_pyqt5_gui]:
        # QFont
        _mock_font = MagicMock()
        _mock_font.setBold = MagicMock()
        _mock_font.setItalic = MagicMock()
        _mock_font.setPointSize = MagicMock()
        _mock_font.setFamily = MagicMock()
        _mock_gui.QFont = MagicMock(return_value=_mock_font)

        # QColor - IMPORTANT: Must return a MagicMock instance, not a function
        # ThemeManager uses QColor in many places and needs it to behave like a class.
        # We create a callable MagicMock that returns a properly configured mock.
        def _create_qcolor_factory():
            """Returns a callable that creates QColor mocks with proper attributes."""
            def _make_qcolor(r=0, g=0, b=0, a=255):
                mock_color = MagicMock()
                mock_color.red.return_value = r
                mock_color.green.return_value = g
                mock_color.blue.return_value = b
                mock_color.alpha.return_value = a
                mock_color.name.return_value = f"#{r:02x}{g:02x}{b:02x}"
                mock_color.getRgb.return_value = (r, g, b, a)
                mock_color.rgba.return_value = (a << 24) | (r << 16) | (g << 8) | b
                # CRITICAL: Make equality and hashing work for StrEnum comparisons
                mock_color.__eq__ = lambda self, other: True
                mock_color.__hash__ = lambda self: hash((r, g, b, a))
                return mock_color
            return MagicMock(side_effect=_make_qcolor)

        _mock_gui.QColor = _create_qcolor_factory()

        # QFontDatabase
        _mock_font_db = MagicMock()
        _mock_font_db.families.return_value = [
            "Arial", "B Nazanin", "Tahoma", "Segoe UI",
            "Consolas", "Courier New", "Times New Roman",
            "Cambria Math", "Georgia", "Vazir", "Iran Sans",
            "Helvetica Neue", "sans-serif", "monospace", "serif",
            "Segoe Fluent Icons",
        ]
        _mock_gui.QFontDatabase = MagicMock(return_value=_mock_font_db)

        # QPixmap
        _mock_gui.QPixmap = MagicMock()

        # QPainter
        _mock_gui.QPainter = MagicMock()

        # QLinearGradient
        _mock_gui.QLinearGradient = MagicMock()

        # QRadialGradient
        _mock_gui.QRadialGradient = MagicMock()

        # QConicalGradient
        _mock_gui.QConicalGradient = MagicMock()

        # QPalette
        _mock_gui.QPalette = MagicMock()

        # QBrush
        _mock_gui.QBrush = MagicMock()

        # QPen
        _mock_gui.QPen = MagicMock()

        # QTransform
        _mock_gui.QTransform = MagicMock()

        # Validators
        _mock_gui.QDoubleValidator = MagicMock()
        _mock_gui.QIntValidator = MagicMock()

        # QKeySequence
        _mock_gui.QKeySequence = MagicMock()

        # QAction (PyQt5)
        _mock_gui.QAction = MagicMock()

    # ========================================================================
    # QtWidgets Mock
    # ========================================================================
    for _mock_widgets in [_mock_pyqt6_widgets, _mock_pyqt5_widgets]:
        # QApplication - IMPORTANT: instance() returns None
        _mock_app = MagicMock()
        _mock_app.instance.return_value = None
        _mock_app.primaryScreen.return_value = None
        _mock_app.setAttribute = MagicMock()
        _mock_app.setStyleSheet = MagicMock()
        _mock_app.setFont = MagicMock()
        _mock_widgets.QApplication = _mock_app

        # QGraphicsDropShadowEffect
        _mock_shadow = MagicMock()
        _mock_shadow.setOffset = MagicMock()
        _mock_shadow.setBlurRadius = MagicMock()
        _mock_shadow.setColor = MagicMock()
        _mock_widgets.QGraphicsDropShadowEffect = MagicMock(return_value=_mock_shadow)

        # QGraphicsOpacityEffect
        _mock_opacity = MagicMock()
        _mock_opacity.setOpacity = MagicMock()
        _mock_widgets.QGraphicsOpacityEffect = MagicMock(return_value=_mock_opacity)

        # QGraphicsBlurEffect
        _mock_blur = MagicMock()
        _mock_blur.setBlurRadius = MagicMock()
        _mock_widgets.QGraphicsBlurEffect = MagicMock(return_value=_mock_blur)

        # QGraphicsColorizeEffect
        _mock_widgets.QGraphicsColorizeEffect = MagicMock()

        # Widget Classes - ALL must be Callable MagicMocks (return MagicMock on instantiation)
        _mock_widgets.QMainWindow = MagicMock(return_value=MagicMock())
        _mock_widgets.QWidget = MagicMock(return_value=MagicMock())
        _mock_widgets.QLabel = MagicMock(return_value=MagicMock())
        _mock_widgets.QVBoxLayout = MagicMock(return_value=MagicMock())
        _mock_widgets.QHBoxLayout = MagicMock(return_value=MagicMock())
        _mock_widgets.QGridLayout = MagicMock(return_value=MagicMock())
        _mock_widgets.QPushButton = MagicMock(return_value=MagicMock())
        _mock_widgets.QLineEdit = MagicMock(return_value=MagicMock())
        _mock_widgets.QTextEdit = MagicMock(return_value=MagicMock())
        _mock_widgets.QDialog = MagicMock(return_value=MagicMock())
        _mock_widgets.QMessageBox = MagicMock(return_value=MagicMock())
        _mock_widgets.QListWidget = MagicMock(return_value=MagicMock())
        _mock_widgets.QCheckBox = MagicMock(return_value=MagicMock())
        _mock_widgets.QComboBox = MagicMock(return_value=MagicMock())
        _mock_widgets.QSpinBox = MagicMock(return_value=MagicMock())
        _mock_widgets.QSlider = MagicMock(return_value=MagicMock())
        _mock_widgets.QProgressBar = MagicMock(return_value=MagicMock())
        _mock_widgets.QTableWidget = MagicMock(return_value=MagicMock())
        _mock_widgets.QTabWidget = MagicMock(return_value=MagicMock())
        _mock_widgets.QScrollArea = MagicMock(return_value=MagicMock())
        _mock_widgets.QFrame = MagicMock(return_value=MagicMock())
        _mock_widgets.QMenuBar = MagicMock(return_value=MagicMock())
        _mock_widgets.QListWidgetItem = MagicMock()
        _mock_widgets.QShortcut = MagicMock(return_value=MagicMock())
        _mock_widgets.QGraphicsView = MagicMock(return_value=MagicMock())
        _mock_widgets.QGraphicsScene = MagicMock(return_value=MagicMock())
        _mock_widgets.QGraphicsPixmapItem = MagicMock()
        _mock_widgets.QDesktopWidget = MagicMock(return_value=MagicMock())
        _mock_widgets.QFontDialog = MagicMock(return_value=MagicMock())
        _mock_widgets.QToolTip = MagicMock()
        _mock_widgets.QHeaderView = MagicMock()

        # QFrame.Shape
        _mock_widgets.QFrame.Shape = MagicMock()
        _mock_widgets.QFrame.Shape.NoFrame = 0
        _mock_widgets.QFrame.NoFrame = 0  # PyQt5 fallback

        # QAbstractItemView.SelectionMode
        _mock_widgets.QAbstractItemView = MagicMock()
        _mock_widgets.QAbstractItemView.SelectionMode = MagicMock()
        _mock_widgets.QAbstractItemView.SelectionMode.MultiSelection = 2
        _mock_widgets.QAbstractItemView.SelectionMode.ExtendedSelection = 3
        _mock_widgets.QAbstractItemView.SelectionMode.NoSelection = 0
        _mock_widgets.QAbstractItemView.MultiSelection = 2  # PyQt5 fallback
        _mock_widgets.QAbstractItemView.ExtendedSelection = 3  # PyQt5 fallback
        _mock_widgets.QAbstractItemView.NoSelection = 0  # PyQt5 fallback

        # CRITICAL FIX: SystemDetector mock
        # SystemDetector methods that return numbers must return actual numbers,
        # not MagicMocks, because they're used in f-strings and format() calls.
        # We'll set these via patch in fixtures instead.

    # ========================================================================
    # ثبت ماژول‌های Mock در sys.modules
    # ========================================================================
    sys.modules['PyQt6'] = MagicMock()
    sys.modules['PyQt6.QtCore'] = _mock_pyqt6_core
    sys.modules['PyQt6.QtGui'] = _mock_pyqt6_gui
    sys.modules['PyQt6.QtWidgets'] = _mock_pyqt6_widgets

    sys.modules['PyQt5'] = MagicMock()
    sys.modules['PyQt5.QtCore'] = _mock_pyqt5_core
    sys.modules['PyQt5.QtGui'] = _mock_pyqt5_gui
    sys.modules['PyQt5.QtWidgets'] = _mock_pyqt5_widgets

# اجرای Mock قبل از هر چیز
_mock_qt_modules()

# ============================================================================
# مرحله ۲: Import ماژول
# ============================================================================

import pytest

# حالا می‌تونیم بدون خطا import کنیم
from MathAssistant.ui.styles import (
    # --- Classes ---
    ThemeManager,
    ColorPalette,
    PaletteFactory,
    FontConfig,
    ShadowSystem,
    GlassmorphismSystem,
    GradientGenerator,
    SystemDetector,
    QtAdapter,
    LRUCache,

    # --- Enums ---
    ThemeMode,
    GlassLevel,
    ShadowElevation,
    BorderRadius,
    FontSize,
    Spacing,
    AnimationDuration,
    Breakpoint,
    GradientType,
    IconSize,
    QtVersion,
    WindowsVersion,

    # --- Data Classes ---
    ShadowParams,
    GlassParams,
    GradientStop,
    GradientConfig,

    # --- Utility Functions ---
    hex_to_rgba,
    hex_to_qcolor,
    lighten_color,
    darken_color,
    mix_colors,
    clamp,
    luminosity,
    contrast_ratio,
    is_accessible,

    # --- Global Instance ---
    theme,

    # --- Regex Patterns ---
    HEX_COLOR_PATTERN,
    RGBA_PATTERN,
    GRADIENT_PATTERN,
)


# ============================================================================
# مرحله ۳: Fixtureهای جامع
# ============================================================================

# ۳.۱ --- Singleton Reset (autouse) ---

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    ریست کامل ماژول‌های MathAssistant بین تست‌ها.

    مشکل اصلی: ThemeManager._mode از یه Enum هست که توی یه module
    دیگه تعریف شده. وقتی ماژول styles.py ریست میشه، Enumها دوباره
    ساخته میشن و is/== با Enumهای قبلی fail میشه.

    راه‌حل: کل sys.modules رو برای MathAssistant پاک کن. این باعث میشه
    همه Enumها و Singletonها از نو ساخته بشن و equality درست کار کنه.
    """
    to_delete = [k for k in sys.modules if k.startswith('MathAssistant')]
    for k in to_delete:
        del sys.modules[k]

    if hasattr(QtAdapter, '_instance'):
        QtAdapter._instance = None
    if hasattr(QtAdapter, '_initialized'):
        QtAdapter._initialized = False

    yield

    to_delete = [k for k in sys.modules if k.startswith('MathAssistant')]
    for k in to_delete:
        del sys.modules[k]


# ۳.۲ --- ColorPalette Fixtures ---
@pytest.fixture
def light_palette() -> ColorPalette:
    """پالت تم Light - کاملاً immutable"""
    return PaletteFactory.create(ThemeMode.LIGHT)


@pytest.fixture
def dark_palette() -> ColorPalette:
    """پالت تم Dark"""
    return PaletteFactory.create(ThemeMode.DARK)


@pytest.fixture
def high_contrast_palette() -> ColorPalette:
    """پالت High Contrast - مناسب accessibility"""
    return PaletteFactory.create(ThemeMode.HIGH_CONTRAST)


@pytest.fixture
def ocean_palette() -> ColorPalette:
    """پالت Ocean"""
    return PaletteFactory.create(ThemeMode.OCEAN)


@pytest.fixture
def forest_palette() -> ColorPalette:
    """پالت Forest"""
    return PaletteFactory.create(ThemeMode.FOREST)


@pytest.fixture
def sunset_palette() -> ColorPalette:
    """پالت Sunset"""
    return PaletteFactory.create(ThemeMode.SUNSET)


@pytest.fixture
def midnight_palette() -> ColorPalette:
    """پالت Midnight"""
    return PaletteFactory.create(ThemeMode.MIDNIGHT)


@pytest.fixture
def aurora_palette() -> ColorPalette:
    """پالت Aurora"""
    return PaletteFactory.create(ThemeMode.AURORA)


@pytest.fixture(params=[
    ThemeMode.LIGHT,
    ThemeMode.DARK,
    ThemeMode.HIGH_CONTRAST,
    ThemeMode.OCEAN,
    ThemeMode.FOREST,
    ThemeMode.SUNSET,
    ThemeMode.MIDNIGHT,
    ThemeMode.AURORA,
])
def all_palettes(request) -> ColorPalette:
    """
    Parametrized fixture - هر ۸ تم رو تست می‌کنه.
    هر تستی که از این استفاده کنه، ۸ بار اجرا میشه.
    """
    return PaletteFactory.create(request.param)


@pytest.fixture(params=[
    ThemeMode.LIGHT,
    ThemeMode.DARK,
])
def light_dark_palettes(request) -> ColorPalette:
    """فقط Light و Dark - برای تست‌های سریع"""
    return PaletteFactory.create(request.param)


# ۳.۳ --- ThemeManager Fixtures (WITH SystemDetector patches) ---
@pytest.fixture
def theme_manager():
    """
    ThemeManager تازه و ایزوله برای هر تست.
    به دلیل autouse reset_singletons، هر بار instance جدید می‌گیریم.

    CRITICAL: SystemDetector methods are patched to return real numbers,
    not MagicMocks, because ThemeManager.get_system_info() uses f-strings
    that call __format__ on these values.
    """
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.WIN_11), \
         patch.object(SystemDetector, 'get_dpi_scale', return_value=1.0), \
         patch.object(SystemDetector, 'get_system_memory_gb', return_value=16.0), \
         patch.object(SystemDetector, 'get_cpu_count', return_value=8):
        return ThemeManager()


@pytest.fixture
def theme_manager_light(theme_manager) -> ThemeManager:
    """ThemeManager با تم Light از پیش تنظیم شده"""
    theme_manager.set_mode(ThemeMode.LIGHT)
    return theme_manager


@pytest.fixture
def theme_manager_dark(theme_manager) -> ThemeManager:
    """ThemeManager با تم Dark از پیش تنظیم شده"""
    theme_manager.set_mode(ThemeMode.DARK)
    return theme_manager


@pytest.fixture
def theme_manager_high_contrast(theme_manager) -> ThemeManager:
    """ThemeManager با تم High Contrast"""
    theme_manager.set_mode(ThemeMode.HIGH_CONTRAST)
    return theme_manager


@pytest.fixture(params=[
    ThemeMode.LIGHT,
    ThemeMode.DARK,
    ThemeMode.HIGH_CONTRAST,
    ThemeMode.OCEAN,
    ThemeMode.FOREST,
    ThemeMode.SUNSET,
    ThemeMode.MIDNIGHT,
    ThemeMode.AURORA,
])
def theme_manager_all_modes(request) -> ThemeManager:
    """ThemeManager با تمام تم‌ها - parametrized"""
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.WIN_11), \
         patch.object(SystemDetector, 'get_dpi_scale', return_value=1.0), \
         patch.object(SystemDetector, 'get_system_memory_gb', return_value=16.0), \
         patch.object(SystemDetector, 'get_cpu_count', return_value=8):
        tm = ThemeManager()
        tm.set_mode(request.param)
        return tm


# ۳.۴ --- Font Fixtures ---
@pytest.fixture
def font_config() -> FontConfig:
    """تنظیمات فونت پیش‌فرض"""
    return FontConfig()


@pytest.fixture
def font_config_custom() -> FontConfig:
    """تنظیمات فونت سفارشی برای تست"""
    return FontConfig(
        family_fa="Vazir",
        family_en="Helvetica Neue",
        family_mono="Consolas",
        family_math="Cambria Math",
        size_normal=16,
        size_title=36,
    )


# ۳.۵ --- Shadow/Glass Fixtures ---
@pytest.fixture(params=[
    ShadowElevation.NONE,
    ShadowElevation.LOW,
    ShadowElevation.MEDIUM,
    ShadowElevation.HIGH,
    ShadowElevation.EXTREME,
])
def all_shadow_elevations(request) -> ShadowElevation:
    """تمام سطوح سایه"""
    return request.param


@pytest.fixture(params=[
    GlassLevel.NONE,
    GlassLevel.LIGHT,
    GlassLevel.MEDIUM,
    GlassLevel.HEAVY,
    GlassLevel.EXTREME,
])
def all_glass_levels(request) -> GlassLevel:
    """تمام سطوح glass"""
    return request.param


# ۳.۶ --- Sample Data Fixtures ---
@pytest.fixture
def sample_hex_colors() -> list:
    """نمونه رنگ‌های hex معتبر برای تست validation"""
    return [
        # ۶ رقمی
        "#FFFFFF", "#000000", "#FF0000", "#00FF00", "#0000FF",
        "#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
        # ۳ رقمی
        "#FFF", "#000", "#F00", "#0F0", "#00F",
        # ۸ رقمی (با alpha)
        "#FF000080", "#000000FF", "#FFFFFF00",
    ]


@pytest.fixture
def invalid_hex_colors() -> list:
    """نمونه رنگ‌های hex نامعتبر"""
    return [
        # فرمت اشتباه
        "#GGG", "#ZZZZZZ", "invalid", "",
        # طول اشتباه
        "#1", "#12", "#1234", "#12345", "#1234567",
        # فرمت‌های دیگر
        "rgb(255,0,0)", "hsl(0,100%,50%)",
        # کاراکترهای غیرمجاز
        "#-12345", "#12 345",
    ]


@pytest.fixture
def sample_rgba_colors() -> list:
    """نمونه rgba های معتبر"""
    return [
        "rgba(255, 255, 255, 1.0)",
        "rgba(0, 0, 0, 0.5)",
        "rgba(37, 99, 235, 0.8)",
        "rgba(255, 0, 0, 0.0)",
        "rgba(0, 255, 0, 0.25)",
        "rgba(128, 128, 128, 0.75)",
    ]


@pytest.fixture
def invalid_rgba_colors() -> list:
    """نمونه rgba های نامعتبر"""
    return [
        "rgba(256, 0, 0, 1.0)",     # R > 255
        "rgba(-1, 0, 0, 0.5)",      # R < 0
        "rgba(0, 0, 0, 2.0)",       # Alpha > 1
        "rgba(0, 0, 0, -0.5)",      # Alpha < 0
        "rgb(255, 0, 0)",           # rgb نه rgba
        "rgba(0, 0, 0)",            # کمبود پارامتر
        "rgba(255, 255, 255)",      # کمبود alpha
        "",                          # خالی
        "rgba(255, 255, 255, 1.0",  # پرانتز بسته نشده
    ]


@pytest.fixture
def sample_color_stops() -> list:
    """نمونه ColorStop برای تست گرادیانت"""
    return [
        (0.0, "#FF0000"),
        (0.25, "#FFFF00"),
        (0.5, "#00FF00"),
        (0.75, "#00FFFF"),
        (1.0, "#0000FF"),
    ]


# ۳.۷ --- Style Fixtures ---
@pytest.fixture
def expected_button_variants() -> set:
    """لیست variantهای معتبر دکمه"""
    return {
        "primary", "secondary", "tertiary", "accent",
        "danger", "success", "warning", "info",
        "ghost", "outline", "link", "custom",
    }


@pytest.fixture
def expected_button_sizes() -> set:
    """لیست سایزهای معتبر دکمه"""
    return {"tiny", "small", "normal", "large", "xl"}


# ۳.۸ --- Accessibility Fixtures ---
@pytest.fixture
def wcag_aa_minimum() -> float:
    """حداقل نسبت کنتراست برای AA"""
    return 4.5


@pytest.fixture
def wcag_aa_large_minimum() -> float:
    """حداقل نسبت کنتراست برای AA Large"""
    return 3.0


@pytest.fixture
def wcag_aaa_minimum() -> float:
    """حداقل نسبت کنتراست برای AAA"""
    return 7.0


# ۳.۹ --- System Info Fixtures ---
@pytest.fixture
def mock_windows_10():
    """Mock کردن سیستم به عنوان Windows 10"""
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.WIN_10):
        with patch.object(SystemDetector, 'get_os_type', return_value='windows'):
            yield


@pytest.fixture
def mock_windows_11():
    """Mock کردن سیستم به عنوان Windows 11"""
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.WIN_11):
        with patch.object(SystemDetector, 'get_os_type', return_value='windows'):
            yield


@pytest.fixture
def mock_linux():
    """Mock کردن سیستم به عنوان Linux"""
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.LINUX):
        with patch.object(SystemDetector, 'get_os_type', return_value='linux'):
            yield


@pytest.fixture
def mock_macos():
    """Mock کردن سیستم به عنوان macOS"""
    with patch.object(SystemDetector, 'get_windows_version', return_value=WindowsVersion.MACOS):
        with patch.object(SystemDetector, 'get_os_type', return_value='macos'):
            yield


# ۳.۱۰ --- Cache Fixtures ---
@pytest.fixture
def empty_cache() -> LRUCache:
    """LRU Cache خالی"""
    return LRUCache(max_size=10)


@pytest.fixture
def filled_cache() -> LRUCache:
    """LRU Cache با داده"""
    cache = LRUCache(max_size=5)
    for i in range(5):
        cache[f"key{i}"] = f"value{i}"
    return cache


@pytest.fixture
def full_cache() -> LRUCache:
    """LRU Cache پر (در آستانه eviction)"""
    cache = LRUCache(max_size=3)
    cache["a"] = "1"
    cache["b"] = "2"
    cache["c"] = "3"
    return cache


# ============================================================================
# Utility Functions برای تست
# ============================================================================

def assert_valid_stylesheet(style: str, selector: str = None):
    """
    بررسی می‌کنه که یه stylesheet معتبر باشه.

    Args:
        style: رشته stylesheet
        selector: (اختیاری) selector مورد انتظار
    """
    assert isinstance(style, str), "Stylesheet must be a string"
    assert len(style) > 0, "Stylesheet must not be empty"
    assert "{" in style, "Stylesheet must contain curly braces"
    assert "}" in style, "Stylesheet must contain closing curly braces"
    if selector:
        assert selector in style, f"Stylesheet must contain selector: {selector}"


def assert_color_is_valid_hex(color: str):
    """بررسی hex color معتبر"""
    assert HEX_COLOR_PATTERN.match(color), f"Invalid hex color: {color}"


def assert_color_is_valid_rgba(color: str):
    """بررسی rgba معتبر"""
    assert RGBA_PATTERN.match(color), f"Invalid rgba: {color}"


def assert_contrast_meets_wcag(
    color1: str,
    color2: str,
    level: str = "AA"
):
    """
    بررسی می‌کنه که کنتراست دو رنگ استاندارد WCAG رو پاس کنه.

    Args:
        color1: رنگ اول
        color2: رنگ دوم
        level: "AA", "AA_LARGE", یا "AAA"
    """
    ratio = contrast_ratio(color1, color2)
    minimums = {"AA": 4.5, "AA_LARGE": 3.0, "AAA": 7.0}
    minimum = minimums.get(level, 4.5)
    assert ratio >= minimum, \
        f"Contrast ratio {ratio:.1f}:1 < {minimum}:1 (WCAG {level})"


# ============================================================================
# pytest Configuration
# ============================================================================

def pytest_configure(config):
    """تنظیمات اضافی pytest"""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "qt: marks tests that need real Qt (skip with '-m \"not qt\"')"
    )
    config.addinivalue_line(
        "markers",
        "accessibility: marks accessibility tests"
    )
    config.addinivalue_line(
        "markers",
        "visual: marks visual regression tests"
    )


def pytest_collection_modifyitems(config, items):
    """اضافه کردن marker خودکار به تست‌ها"""
    for item in items:
        if "accessibility" in str(item.fspath):
            item.add_marker(pytest.mark.accessibility)
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.qt)
