# src/MathAssistant/ui/prime_tools_ui.py
"""
Prime Tools Suite - ابزارهای پیشرفته اعداد اول
طراحی نئومورفیسم/گلس‌مورفیسم کامل | کنتراست WCAG AAA+ | فونت تفکیک‌شده

Author: AmirMohammad Ghasemzadeh
Version: 9.1.0 - Thread-Safe Production Edition
"""

import logging
import re
from typing import Optional, List, Tuple, Type, Dict, Any, Callable
from enum import Enum, auto
from threading import Event
from dataclasses import dataclass

from PyQt6.QtCore import (
    Qt, QTimer, QSize, pyqtSignal, QRunnable, QThreadPool,
    QObject, pyqtSlot, QMetaObject, Q_ARG
)
from PyQt6.QtGui import (
    QFont, QIntValidator, QKeySequence, QAction, QShortcut,
    QColor, QPalette, QFontDatabase, QActionGroup, QPainter,
    QBrush, QPen, QPainterPath, QLinearGradient, QCursor
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QTabWidget, QTabBar,
    QMenuBar, QMenu, QMessageBox, QApplication, QFrame,
    QSizePolicy, QGraphicsDropShadowEffect, QStyleFactory,
    QProgressBar
)

from ..core.math_engine import MathEngine

logger = logging.getLogger(__name__)

# ============================================================================
# Constants - Optimized for Production
# ============================================================================
QT_MAX_INT32: int = 2_147_483_647
SIEVE_MAX_RANGE: int = 5_000_000
RESULT_CHUNK_SIZE: int = 100
RESULT_CLEAR_TIMEOUT_MS: int = 25_000
PRIMALITY_MAX: int = 10 ** 15

# آستانه‌های حافظه برای هشدار (تخمین تقریبی)
MEMORY_WARNING_THRESHOLD: int = 500_000   # تعداد نتایج برای هشدار
MEMORY_CRITICAL_THRESHOLD: int = 1_000_000  # تعداد نتایج بحرانی


# ============================================================================
# Data Classes for Results
# ============================================================================

@dataclass
class CalculationResult:
    """نتیجه کامل یک محاسبه شامل متادیتا."""
    data: Any
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============================================================================
# Cancellation Token System
# ============================================================================

class CancellationToken:
    """توکن لغو عملیات برای کنترل thread-safe محاسبات."""

    def __init__(self):
        self._event = Event()
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        """لغو عملیات."""
        self._cancelled = True
        self._event.set()

    def wait(self, timeout: float = None) -> bool:
        """منتظر ماندن برای سیگنال لغو."""
        return self._event.wait(timeout)

    def reset(self):
        """بازنشانی توکن برای استفاده مجدد."""
        self._cancelled = False
        self._event.clear()


# ============================================================================
# Theme System - Production Ready (Fixed RGBA)
# ============================================================================

class ThemeMode(Enum):
    DARK = auto()
    LIGHT = auto()


class NeumorphicTheme:
    """سیستم تم نئومورفیسم + گلس‌مورفیسم کامل با مقادیر CSS-valid."""

    DARK = {
        'bg_root': '#080c18',
        'bg_primary': '#0d1124',
        'bg_secondary': '#11162b',
        'bg_tertiary': '#151b32',
        'bg_card': '#0f1428',
        'bg_input': '#0b0f1e',
        'bg_input_focus': '#0d1226',
        'bg_glass': 'rgba(13, 17, 36, 0.88)',
        'bg_raised': '#181e38',
        'text_primary': '#f2f3f8',
        'text_secondary': '#c4c8d8',
        'text_muted': '#9da2b8',
        'text_accent': '#b4bfff',
        'accent': '#8b7cf7',
        'accent_hover': '#a094ff',
        'accent_pressed': '#6d5ed8',
        'accent_text': '#ffffff',
        'accent_glow': 'rgba(139, 124, 247, 0.25)',
        'success': '#4ade80',
        'success_bg': '#052e16',
        'success_text': '#bbf7d0',
        'error': '#f87171',
        'error_bg': '#450a0a',
        'error_text': '#fecaca',
        'warning': '#fbbf24',
        'warning_bg': '#451a03',
        'warning_text': '#fde68a',
        'info': '#60a5fa',
        'info_bg': '#172554',
        'info_text': '#bfdbfe',
        'border_light': '#1d2340',
        'border_dark': '#060810',
        'border_input': '#0f1428',
        'border_focus': '#8b7cf7',
        'border_card': '#181e38',
        # Fixed: RGBA with proper alpha values (0-1 range)
        'shadow_light': 'rgba(25, 30, 55, 0.71)',
        'shadow_dark': 'rgba(3, 5, 12, 0.78)',
        'shadow_card': 'rgba(0, 0, 0, 0.24)',
        'glass_border': 'rgba(255, 255, 255, 0.04)',
        'glass_highlight': 'rgba(255, 255, 255, 0.03)',
        'scrollbar_bg': 'transparent',
        'scrollbar_handle': '#252b48',
        'scrollbar_hover': '#8b7cf7',
        'tab_inactive_bg': '#0f1428',
        'tab_inactive_text': '#9da2b8',
        'tab_active_bg': '#181e38',
        'tab_active_text': '#b4bfff',
        'tab_hover_bg': '#131830',
        'tab_border_active': '#8b7cf7',
        'tab_shadow_light': '#1d2340',
        'tab_shadow_dark': '#060810',
        'hover_overlay': 'rgba(139, 124, 247, 0.1)',
        'pressed_overlay': 'rgba(139, 124, 247, 0.2)',
        'cancel_btn_bg': '#dc2626',
        'cancel_btn_hover': '#ef4444',
    }

    LIGHT = {
        'bg_root': '#e2e6ed',
        'bg_primary': '#e8ebf2',
        'bg_secondary': '#edf0f5',
        'bg_tertiary': '#f2f4f8',
        'bg_card': '#ffffff',
        'bg_input': '#f7f8fb',
        'bg_input_focus': '#ffffff',
        'bg_glass': 'rgba(255, 255, 255, 0.85)',
        'bg_raised': '#f5f6fa',
        'text_primary': '#0d1124',
        'text_secondary': '#2d3142',
        'text_muted': '#4a5068',
        'text_accent': '#242050',
        'accent': '#6d5ed8',
        'accent_hover': '#7c6ff7',
        'accent_pressed': '#5a4cc0',
        'accent_text': '#ffffff',
        'accent_glow': 'rgba(109, 94, 216, 0.2)',
        'success': '#16a34a',
        'success_bg': '#dcfce7',
        'success_text': '#052e16',
        'error': '#dc2626',
        'error_bg': '#fee2e2',
        'error_text': '#450a0a',
        'warning': '#d97706',
        'warning_bg': '#fef3c7',
        'warning_text': '#451a03',
        'info': '#2561e4',
        'info_bg': '#dbeafe',
        'info_text': '#172554',
        'border_light': '#ffffff',
        'border_dark': '#c8ccd6',
        'border_input': '#d5d8e0',
        'border_focus': '#6d5ed8',
        'border_card': '#e0e3ea',
        # Fixed: RGBA with proper alpha values (0-1 range)
        'shadow_light': 'rgba(255, 255, 255, 0.78)',
        'shadow_dark': 'rgba(170, 178, 190, 0.71)',
        'shadow_card': 'rgba(0, 0, 0, 0.10)',
        'glass_border': 'rgba(255, 255, 255, 0.6)',
        'glass_highlight': 'rgba(255, 255, 255, 0.4)',
        'scrollbar_bg': 'transparent',
        'scrollbar_handle': '#c5c9d4',
        'scrollbar_hover': '#6d5ed8',
        'tab_inactive_bg': '#edf0f5',
        'tab_inactive_text': '#2d3142',
        'tab_active_bg': '#ffffff',
        'tab_active_text': '#221f42',
        'tab_hover_bg': '#f2f4f8',
        'tab_border_active': '#6d5ed8',
        'tab_shadow_light': '#ffffff',
        'tab_shadow_dark': '#c8ccd6',
        'hover_overlay': 'rgba(109, 94, 216, 0.08)',
        'pressed_overlay': 'rgba(109, 94, 216, 0.15)',
        'cancel_btn_bg': '#dc2626',
        'cancel_btn_hover': '#ef4444',
    }

    def __init__(self, mode: ThemeMode = ThemeMode.DARK):
        self.mode = mode
        self.colors = self.DARK if mode == ThemeMode.DARK else self.LIGHT

    def toggle(self) -> ThemeMode:
        self.mode = ThemeMode.LIGHT if self.mode == ThemeMode.DARK else ThemeMode.DARK
        self.colors = self.DARK if self.mode == ThemeMode.DARK else self.LIGHT
        return self.mode

    @property
    def is_dark(self) -> bool:
        return self.mode == ThemeMode.DARK

    def neumorphic_shadow(self, blur: int = 10, offset: int = 4) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset)
        shadow.setColor(QColor(0, 0, 0, 35 if self.is_dark else 20))
        return shadow

    def neumorphic_inset_shadow(self, blur: int = 6) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 50 if self.is_dark else 30))
        return shadow

    def stylesheet(self) -> str:
        c = self.colors
        return f"""
        QWidget {{
            background-color: {c['bg_root']};
            color: {c['text_primary']};
            font-family: 'B Nazanin', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        QLineEdit {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 2px solid {c['border_input']};
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 14px;
            selection-background-color: {c['accent']};
            selection-color: {c['accent_text']};
        }}
        QLineEdit:focus {{
            border-color: {c['border_focus']};
            background-color: {c['bg_input_focus']};
        }}
        QLineEdit::placeholder {{
            color: {c['text_muted']};
        }}
        QTextEdit {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 2px solid {c['border_card']};
            border-radius: 14px;
            padding: 14px;
            font-size: 14px;
            selection-background-color: {c['accent']};
            selection-color: {c['accent_text']};
        }}
        QPushButton {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
            border: 1px solid {c['border_light']};
            border-bottom: 1px solid {c['border_dark']};
            border-radius: 10px;
            padding: 8px 16px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 15px;
            font-weight: bold;
            min-height: 28px;
        }}
        QPushButton:hover {{
            background-color: {c['bg_raised']};
            border-color: {c['accent']};
        }}
        QPushButton:pressed {{
            background-color: {c['accent']};
            color: {c['accent_text']};
            border-color: {c['accent']};
        }}
        QPushButton:disabled {{
            background-color: {c['bg_secondary']};
            color: {c['text_muted']};
            border-color: {c['border_input']};
        }}
        QPushButton#accentBtn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent']}, stop:1 {c['accent_hover']});
            color: {c['accent_text']};
            border: none;
            font-size: 16px;
            padding: 10px 24px;
            border-radius: 12px;
            min-height: 32px;
        }}
        QPushButton#accentBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent_hover']}, stop:1 {c['accent']});
        }}
        QPushButton#accentBtn:pressed {{
            background-color: {c['accent_pressed']};
        }}
        QPushButton#cancelBtn {{
            background-color: {c['cancel_btn_bg']};
            color: white;
            border: none;
            font-size: 14px;
            padding: 8px 20px;
            border-radius: 10px;
            font-weight: bold;
        }}
        QPushButton#cancelBtn:hover {{
            background-color: {c['cancel_btn_hover']};
        }}
        QPushButton#iconBtn {{
            background-color: transparent;
            border: 1px solid {c['border_light']};
            border-bottom: 1px solid {c['border_dark']};
            border-radius: 9px;
            padding: 4px;
            min-width: 36px;
            min-height: 36px;
            font-size: 15px;
        }}
        QPushButton#iconBtn:hover {{
            background-color: {c['bg_raised']};
            border-color: {c['accent']};
        }}
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar::tab {{
            background-color: {c['tab_inactive_bg']};
            color: {c['tab_inactive_text']};
            padding: 10px 20px;
            margin: 4px 3px;
            border: 1px solid {c['tab_shadow_light']};
            border-bottom: 1px solid {c['tab_shadow_dark']};
            border-radius: 10px 10px 0 0;
            font-family: 'B Nazanin', sans-serif;
            font-size: 14px;
            font-weight: bold;
            min-width: 90px;
        }}
        QTabBar::tab:selected {{
            background-color: {c['tab_active_bg']};
            color: {c['tab_active_text']};
            border-bottom: 3px solid {c['tab_border_active']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {c['tab_hover_bg']};
            color: {c['text_primary']};
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {c['scrollbar_bg']};
            width: 8px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['scrollbar_handle']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['scrollbar_hover']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            height: 0;
        }}
        QMenuBar {{
            background-color: {c['bg_secondary']};
            border-bottom: 1px solid {c['border_dark']};
            padding: 4px 8px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 14px;
            color: {c['text_primary']};
        }}
        QMenuBar::item {{
            padding: 6px 12px;
            border-radius: 7px;
        }}
        QMenuBar::item:selected {{
            background-color: {c['accent']};
            color: {c['accent_text']};
        }}
        QMenu {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border_card']};
            border-radius: 12px;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 7px;
            font-family: 'B Nazanin', sans-serif;
        }}
        QMenu::item:selected {{
            background-color: {c['accent']};
            color: {c['accent_text']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {c['border_card']};
            margin: 4px 12px;
        }}
        QToolTip {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border_card']};
            border-radius: 10px;
            padding: 6px 12px;
            font-size: 12px;
        }}
        QMessageBox {{
            background-color: {c['bg_card']};
        }}
        QMessageBox QLabel {{
            color: {c['text_primary']};
            font-family: 'B Nazanin', sans-serif;
        }}
        QProgressBar {{
            border: 2px solid {c['border_card']};
            border-radius: 10px;
            text-align: center;
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: {c['accent']};
            border-radius: 8px;
        }}
        QLabel#memoryWarning {{
            color: {c['warning_text']};
            background-color: {c['warning_bg']};
            border: 1px solid {c['warning']};
            border-radius: 8px;
            padding: 8px;
            font-weight: bold;
        }}
        """


# ============================================================================
# Font System
# ============================================================================

class NumberFontMode(Enum):
    ENGLISH = "english"
    PERSIAN = "persian"


class FontSystem:
    PERSIAN_FONT = "B Nazanin"
    ENGLISH_NUMBER_FONT = "Arial"
    PERSIAN_NUMBER_FONT = "B Nazanin"
    MONO_FONT = "Consolas"

    _number_mode: NumberFontMode = NumberFontMode.ENGLISH

    @classmethod
    def setup(cls, app: QApplication):
        font = QFont(cls.PERSIAN_FONT, 12)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        app.setFont(font)
        app.setStyle("Fusion")
        logger.info(f"Font system initialized. Mode: {cls._number_mode.value}")

    @classmethod
    def set_number_mode(cls, mode: NumberFontMode):
        cls._number_mode = mode
        logger.info(f"Number font mode changed to: {mode.value}")

    @classmethod
    def get_number_mode(cls) -> NumberFontMode:
        return cls._number_mode

    @classmethod
    def _number_font_name(cls) -> str:
        return cls.ENGLISH_NUMBER_FONT if cls._number_mode == NumberFontMode.ENGLISH else cls.PERSIAN_NUMBER_FONT

    @classmethod
    def _make_font(cls, family: str, size: int, bold: bool = False) -> QFont:
        font = QFont(family, size)
        font.setBold(bold)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        return font

    @classmethod
    def persian_title(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 21, True)
    @classmethod
    def persian_subtitle(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 17, False)
    @classmethod
    def persian_button(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 16, True)
    @classmethod
    def persian_tab(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 15, True)
    @classmethod
    def persian_menu(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 14, False)
    @classmethod
    def persian_status(cls) -> QFont: return cls._make_font(cls.PERSIAN_FONT, 11, False)
    @classmethod
    def number_input(cls) -> QFont: return cls._make_font(cls._number_font_name(), 13, False)
    @classmethod
    def number_result(cls) -> QFont: return cls._make_font(cls._number_font_name(), 13, False)
    @classmethod
    def number_big(cls) -> QFont: return cls._make_font(cls._number_font_name(), 16, True)


# ============================================================================
# Thread-Safe Calculation System
# ============================================================================

class CalculationSignals(QObject):
    """سیگنال‌های Thread-Safe برای ارتباط worker با UI."""
    finished = pyqtSignal(object)      # CalculationResult
    error = pyqtSignal(str)
    progress = pyqtSignal(int)


class CalculationWorker(QRunnable):
    """
    Worker Thread با پشتیبانی از CancellationToken.
    """

    def __init__(self, fn: Callable, *args, cancellation_token: Optional[CancellationToken] = None, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.cancellation_token = cancellation_token or CancellationToken()
        self.signals = CalculationSignals()
        self._is_running = False

    @pyqtSlot()
    def run(self):
        """اجرای محاسبه با پشتیبانی از لغو."""
        if self.cancellation_token.is_cancelled:
            return

        self._is_running = True
        try:
            # ارسال cancellation_token به تابع اگر آن را پشتیبانی کند
            if 'cancellation_token' in self.fn.__code__.co_varnames:
                self.kwargs['cancellation_token'] = self.cancellation_token

            result = self.fn(*self.args, **self.kwargs)

            if not self.cancellation_token.is_cancelled:
                self.signals.finished.emit(result)
        except Exception as e:
            if not self.cancellation_token.is_cancelled:
                logger.exception("CalculationWorker failed")
                self.signals.error.emit(str(e))
        finally:
            self._is_running = False

    def cancel(self):
        """درخواست لغو عملیات."""
        if self._is_running:
            self.cancellation_token.cancel()


# ============================================================================
# Custom Neumorphic Widgets
# ============================================================================

class NeumorphicInput(QLineEdit):
    def __init__(self, placeholder="", vrange=None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.update_font()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        if vrange:
            lo, hi = vrange
            lo, hi = max(lo, -QT_MAX_INT32), min(hi, QT_MAX_INT32)
            if lo < hi:
                self.setValidator(QIntValidator(lo, hi))

    def update_font(self):
        self.setFont(FontSystem.number_input())


class NeumorphicButton(QPushButton):
    def __init__(self, text: str, accent: bool = False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("accentBtn" if accent else "")
        self.setFont(FontSystem.persian_button())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

    def update_font(self):
        self.setFont(FontSystem.persian_button())


class NeumorphicResultArea(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.update_font()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def update_font(self):
        self.setFont(FontSystem.number_result())


class NeumorphicResultLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_font()
        self.setWordWrap(True)
        self.setMinimumHeight(50)
        self.hide()

    def update_font(self):
        self.setFont(FontSystem.number_big())


# ============================================================================
# Thread-Safe Base Tab with Memory Management
# ============================================================================

class BasePrimeTab(QWidget):
    """کلاس پایه با مدیریت پیشرفته Threading، حافظه و لغو عملیات."""

    def __init__(self, engine: MathEngine, theme: NeumorphicTheme, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.theme = theme
        self.setFont(FontSystem.persian_subtitle())
        self._number_widgets: List[QWidget] = []
        self._progress_bar: Optional[QProgressBar] = None
        self._cancel_btn: Optional[QPushButton] = None
        self._memory_warning: Optional[QLabel] = None
        self._thread_pool = QThreadPool.globalInstance()

        # Thread-Safe state management
        self._is_calculating: bool = False
        self._active_worker: Optional[CalculationWorker] = None
        self._cancellation_token: Optional[CancellationToken] = None

        self._build_ui()

    def _build_ui(self):
        raise NotImplementedError

    def update_theme(self, theme: NeumorphicTheme):
        self.theme = theme

    def refresh_fonts(self):
        for widget in self._number_widgets:
            if hasattr(widget, 'update_font'):
                widget.update_font()

    def _register_number_widget(self, widget: QWidget):
        self._number_widgets.append(widget)

    def _title_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(FontSystem.persian_title())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {self.theme.colors['text_accent']}; padding: 8px;")
        return lbl

    def _desc_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(FontSystem.persian_subtitle())
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {self.theme.colors['text_secondary']};")
        lbl.setWordWrap(True)
        return lbl

    def _create_input(self, placeholder="", vrange=None) -> NeumorphicInput:
        inp = NeumorphicInput(placeholder, vrange)
        inp.setGraphicsEffect(self.theme.neumorphic_inset_shadow())
        self._register_number_widget(inp)
        return inp

    def _create_button(self, text: str, callback, accent: bool = False) -> NeumorphicButton:
        btn = NeumorphicButton(text, accent)
        btn.setGraphicsEffect(self.theme.neumorphic_shadow(8, 3))
        btn.clicked.connect(callback)
        return btn

    def _create_result_area(self) -> NeumorphicResultArea:
        area = NeumorphicResultArea()
        area.setGraphicsEffect(self.theme.neumorphic_shadow(8, 3))
        self._register_number_widget(area)
        return area

    def _create_result_label(self) -> NeumorphicResultLabel:
        lbl = NeumorphicResultLabel()
        self._register_number_widget(lbl)
        return lbl

    def _create_progress_with_cancel(self) -> QHBoxLayout:
        """ایجاد نوار پیشرفت با دکمه لغو."""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # Indeterminate
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar, 1)

        self._cancel_btn = QPushButton("✕ لغو")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setFont(FontSystem.persian_button())
        self._cancel_btn.clicked.connect(self._cancel_calculation)
        layout.addWidget(self._cancel_btn)

        return layout

    def _create_memory_warning(self) -> QLabel:
        """ایجاد لیبل هشدار حافظه."""
        lbl = QLabel()
        lbl.setObjectName("memoryWarning")
        lbl.setVisible(False)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "⚠️ خطا", msg)

    def _check_memory_threshold(self, estimated_count: int) -> bool:
        """
        بررسی آستانه حافظه و نمایش هشدار.
        Returns True اگر کاربر تأیید کند.
        """
        if estimated_count > MEMORY_CRITICAL_THRESHOLD:
            estimated_mb = (estimated_count * 28) / (1024 * 1024)  # تخمین تقریبی
            reply = QMessageBox.question(
                self,
                "⚠️ هشدار مصرف حافظه",
                f"این عملیات تقریباً {estimated_count:,} نتیجه تولید می‌کند\n"
                f"و ممکن است تا {estimated_mb:.0f} MB حافظه مصرف کند.\n\n"
                "ادامه می‌دهید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        elif estimated_count > MEMORY_WARNING_THRESHOLD:
            estimated_mb = (estimated_count * 28) / (1024 * 1024)
            reply = QMessageBox.question(
                self,
                "💡 هشدار حافظه",
                f"این عملیات {estimated_count:,} نتیجه تولید می‌کند\n"
                f"و حدود {estimated_mb:.0f} MB حافظه مصرف می‌کند.\n\n"
                "ادامه می‌دهید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            return reply == QMessageBox.StandardButton.Yes
        return True

    def _start_calculation(self, fn: Callable, *args,
                          finished_callback=None,
                          estimated_result_count: int = 0):
        """
        شروع محاسبه Thread-Safe با مدیریت Race Condition.
        """
        # جلوگیری از اجرای همزمان
        if self._is_calculating:
            logger.warning("Calculation already in progress, ignoring new request")
            return

        # بررسی حافظه
        if estimated_result_count > 0:
            if not self._check_memory_threshold(estimated_result_count):
                return

        # تنظیم وضعیت
        self._is_calculating = True
        self._set_ui_enabled(False)

        # نمایش progress و دکمه لغو
        if self._progress_bar:
            self._progress_bar.setVisible(True)
        if self._cancel_btn:
            self._cancel_btn.setVisible(True)

        # ایجاد cancellation token جدید
        self._cancellation_token = CancellationToken()

        # ایجاد worker
        worker = CalculationWorker(fn, *args, cancellation_token=self._cancellation_token)

        if finished_callback:
            worker.signals.finished.connect(finished_callback)
        worker.signals.error.connect(self._on_calculation_error)
        worker.signals.finished.connect(lambda _: self._on_calculation_finished())

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _cancel_calculation(self):
        """لغو عملیات در حال اجرا."""
        if self._active_worker and self._is_calculating:
            logger.info("User requested calculation cancellation")
            self._active_worker.cancel()
            if self._cancel_btn:
                self._cancel_btn.setEnabled(False)
                self._cancel_btn.setText("⏳ در حال لغو...")

    def _on_calculation_error(self, error_msg: str):
        """مدیریت خطای Thread-Safe."""
        self._reset_calculation_state()
        self._show_error(f"خطای سیستمی: {error_msg}")
        logger.error(f"Calculation error: {error_msg}")

    def _on_calculation_finished(self):
        """پاکسازی بعد از اتمام محاسبه."""
        self._reset_calculation_state()

    def _reset_calculation_state(self):
        """بازنشانی وضعیت محاسبه."""
        self._is_calculating = False
        self._active_worker = None
        self._cancellation_token = None
        self._set_ui_enabled(True)

        if self._progress_bar:
            self._progress_bar.setVisible(False)
        if self._cancel_btn:
            self._cancel_btn.setVisible(False)
            self._cancel_btn.setEnabled(True)
            self._cancel_btn.setText("✕ لغو")

    def _set_ui_enabled(self, enabled: bool):
        """مدیریت cursor و وضعیت UI."""
        if enabled:
            QApplication.restoreOverrideCursor()
        else:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    @staticmethod
    def _fmt(n: int) -> str:
        return f"{n:,}"

    @staticmethod
    def _parse_numbers(text: str) -> List[int]:
        """پارس اعداد با پشتیبانی از فرمت‌های مختلف."""
        persian_arabic_digits = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
        english_digits = "01234567890123456789"
        translation_table = str.maketrans(persian_arabic_digits, english_digits)
        cleaned = text.translate(translation_table)
        cleaned = re.sub(r'[،,;؛\s]+', ' ', cleaned)
        cleaned = cleaned.replace("٫", ".")
        parts = cleaned.split()
        return [int(p) for p in parts if p]

    @staticmethod
    def _build_html_list(items: List, formatter: Callable = str,
                        chunk_size: int = RESULT_CHUNK_SIZE,
                        separator: str = "، ") -> List[str]:
        """ساخت لیست HTML بهینه."""
        html_parts = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            html_parts.append(separator.join(formatter(item) for item in chunk))
        return html_parts

    def _copy_to_clipboard(self, data: List, formatter: Callable = str):
        """کپی نتایج به کلیپبورد با فرمت CSV استاندارد."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        for item in data:
            writer.writerow([formatter(item)])

        clipboard = QApplication.clipboard()
        clipboard.setText(output.getvalue())
        logger.info(f"Copied {len(data)} items to clipboard")


# ============================================================================
# Tab Implementations - Thread-Safe
# ============================================================================

class PrimeCheckerTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(18)

        l.addWidget(self._title_label("🔍 تشخیص عدد اول"))
        l.addWidget(self._desc_label("عدد خود را وارد کنید تا اول بودن آن بررسی شود."))

        self.inp = self._create_input("عدد (مثال: 9999991)...")
        self.inp.returnPressed.connect(self._check)
        l.addWidget(self.inp)

        l.addWidget(self._create_button("🔍 بررسی کن", self._check, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.res = self._create_result_label()
        l.addWidget(self.res)

        self._tmr = QTimer()
        self._tmr.timeout.connect(self._hide_result)
        self._result_type: Optional[str] = None
        l.addStretch(1)
        self.setLayout(l)

    def _check(self):
        t = self.inp.text().strip()
        if not t:
            return self._show_error("عددی وارد کنید!")
        try:
            parsed = self._parse_numbers(t)
            if not parsed:
                return self._show_error("عدد صحیح معتبر!")
            n = parsed[0]

            if n < 1:
                return self._show_error("بزرگتر از ۰!")
            if n > PRIMALITY_MAX:
                return self._show_error(f"حداکثر: {self._fmt(PRIMALITY_MAX)}")

            if n > 10**12:
                self._start_calculation(
                    self.engine.check_prime, n,
                    finished_callback=self._display_result
                )
            else:
                # سریع - مستقیم اجرا می‌شود
                result = self.engine.check_prime(n)
                self._display_result(result)

        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in PrimeCheckerTab")
            self._show_error(f"خطای سیستمی: {e}")

    def _display_result(self, r):
        n = r.number if hasattr(r, 'number') else 0
        c = self.theme.colors
        self._tmr.stop()

        if r.is_prime:
            self.res.setText(f"✅ {self._fmt(n)} عدد اول است! ({r.divisor_count} مقسوم‌علیه)")
            self._result_type = 'success'
        else:
            fs = " × ".join(map(str, r.factors)) if r.factors else "—"
            self.res.setText(
                f"❌ {self._fmt(n)} اول نیست!\nعوامل: {fs}\nمقسوم‌علیه‌ها: {r.divisor_count}"
            )
            self._result_type = 'error'

        self._apply_result_style()
        self.res.show()
        self.inp.clear()
        self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)

    def _apply_result_style(self):
        c = self.theme.colors
        if self._result_type == 'success':
            self.res.setStyleSheet(
                f"color:{c['success_text']}; font-size:16px; font-weight:bold; "
                f"padding:20px; background:{c['success_bg']}; "
                f"border-radius:12px; border:2px solid {c['border_card']};"
            )
        elif self._result_type == 'error':
            self.res.setStyleSheet(
                f"color:{c['error_text']}; font-size:15px; font-weight:bold; "
                f"padding:20px; background:{c['error_bg']}; "
                f"border-radius:12px; border:2px solid {c['border_card']};"
            )

    def _hide_result(self):
        self._tmr.stop()
        self.res.hide()
        self._result_type = None

    def update_theme(self, theme):
        super().update_theme(theme)
        if self.res.isVisible():
            self._apply_result_style()


class SieveTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(14)

        l.addWidget(self._title_label("🧹 غربال اراتستن"))
        l.addWidget(self._desc_label(f"اعداد اول در بازه مشخص را بیابید. (حداکثر: {self._fmt(SIEVE_MAX_RANGE)})"))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.sf = self._create_input("حد پایین (پیش‌فرض: ۱)", (0, SIEVE_MAX_RANGE))
        self.sf.returnPressed.connect(lambda: self.ef.setFocus())
        self.ef = self._create_input("حد بالا (الزامی)", (2, SIEVE_MAX_RANGE))
        self.ef.returnPressed.connect(self._gen)
        row.addWidget(self.sf)
        row.addWidget(self.ef)
        l.addLayout(row)

        l.addWidget(self._create_button("🧹 اجرا", self._gen, True), 0, Qt.AlignmentFlag.AlignHCenter)

        # Progress bar with cancel button
        l.addLayout(self._create_progress_with_cancel())

        # Memory warning label
        self._memory_warning = self._create_memory_warning()
        l.addWidget(self._memory_warning)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.ra = self._create_result_area()
        sc.setWidget(self.ra)
        l.addWidget(sc, 1)
        self.setLayout(l)

    def _gen(self):
        st = self.sf.text().strip()
        et = self.ef.text().strip()

        try:
            s_parsed = self._parse_numbers(st) if st else [1]
            e_parsed = self._parse_numbers(et)
            if not e_parsed:
                return self._show_error("حد بالا را وارد کنید!")

            s = s_parsed[0]
            e = e_parsed[0]

            if e < 2:
                return self._show_error("حد بالا ≥ ۲!")
            if s > e:
                return self._show_error("حد پایین > حد بالا!")
            if e > SIEVE_MAX_RANGE:
                return self._show_error(f"حداکثر: {self._fmt(SIEVE_MAX_RANGE)}")

            # تخمین تعداد نتایج برای هشدار حافظه
            estimated = int((e - s) / 6)  # تقریب تراکم اعداد اول
            self._start_calculation(
                self.engine.generate_primes, s, e,
                finished_callback=self._display_primes,
                estimated_result_count=estimated
            )
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in SieveTab")
            self._show_error(f"خطای سیستمی: {e}")

    def _display_primes(self, primes):
        c = self.theme.colors
        self.ra.clear()

        if not primes:
            self.ra.setHtml(f"<p style='color:{c['warning_text']};'>⚠️ عدد اولی یافت نشد.</p>")
            return

        # نمایش کامل همه نتایج
        html = [
            f"<h4 style='color:{c['text_accent']};'>🔢 {self._fmt(len(primes))} عدد اول</h4>",
            f"<p style='color:{c['text_muted']}; font-size:12px;'>"
            f"💡 راهنما: Ctrl+A انتخاب همه | Ctrl+C کپی | برای CSV استاندارد از منوی ابزارها استفاده کنید</p>"
            f"<hr>"
        ]
        html.extend(self._build_html_list(primes))
        self.ra.setHtml("<br><br>".join(html))
        self.sf.clear()
        self.ef.clear()


class DivisorsTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(18)

        l.addWidget(self._title_label("📊 شمارنده‌ها"))
        l.addWidget(self._desc_label("همه مقسوم‌علیه‌های عدد را بیابید."))

        self.inp = self._create_input("عدد...", (1, QT_MAX_INT32))
        self.inp.returnPressed.connect(self._calc)
        l.addWidget(self.inp)

        l.addWidget(self._create_button("📊 محاسبه", self._calc, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.ra = self._create_result_area()
        self.ra.hide()
        l.addWidget(self.ra)

        self._tmr = QTimer()
        self._tmr.timeout.connect(lambda: (self.ra.hide(), self._tmr.stop()))
        l.addStretch(1)
        self.setLayout(l)

    def _calc(self):
        t = self.inp.text().strip()
        if not t:
            return self._show_error("عددی وارد کنید!")
        try:
            parsed = self._parse_numbers(t)
            if not parsed:
                return self._show_error("عدد صحیح معتبر!")
            n = parsed[0]
            if n < 1:
                return self._show_error("بزرگتر از ۰!")

            if n > 10**9:
                # Worker شامل is_prime هم می‌شود
                self._start_calculation(
                    self._calculate_divisors_with_metadata, n,
                    finished_callback=self._display_divisors_result
                )
            else:
                result = self._calculate_divisors_with_metadata(n)
                self._display_divisors_result(result)
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in DivisorsTab")
            self._show_error(f"خطای سیستمی: {e}")

    def _calculate_divisors_with_metadata(self, n: int) -> CalculationResult:
        """محاسبه کامل در worker شامل is_prime."""
        divs = self.engine.get_divisors(n)
        is_prime = self.engine.is_prime(n)
        return CalculationResult(
            data={'divisors': divs, 'n': n, 'is_prime': is_prime},
            metadata={'count': len(divs)}
        )

    def _display_divisors_result(self, result: CalculationResult):
        """نمایش نتیجه کامل."""
        c = self.theme.colors
        self.ra.clear()
        self._tmr.stop()

        data = result.data
        divs = data['divisors']
        n = data['n']
        is_prime = data['is_prime']

        html_content = [
            f"<h3 style='color:{c['text_accent']};'>نتایج برای عدد {n}</h3>",
            f"<p>تعداد شمارنده‌ها: <b>{len(divs)}</b></p>"
        ]
        if is_prime:
            html_content.append(f"<p style='color:{c['success_text']};'>✨ این عدد اول است.</p>")

        html_content.append("<h4>شمارنده‌ها:</h4>")
        html_content.extend(self._build_html_list(divs))

        self.ra.setHtml("".join(html_content))
        self.ra.show()
        self.inp.clear()
        self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)


class TwinPrimesTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(14)

        l.addWidget(self._title_label("👯 اعداد اول دوقلو"))
        l.addWidget(self._desc_label("جفت اعداد اول با اختلاف ۲."))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.sf = self._create_input("حد پایین (پیش‌فرض: ۱)", (0, SIEVE_MAX_RANGE))
        self.sf.returnPressed.connect(lambda: self.ef.setFocus())
        self.ef = self._create_input("حد بالا", (2, SIEVE_MAX_RANGE))
        self.ef.returnPressed.connect(self._find)
        row.addWidget(self.sf)
        row.addWidget(self.ef)
        l.addLayout(row)

        l.addWidget(self._create_button("👯 پیدا کن", self._find, True), 0, Qt.AlignmentFlag.AlignHCenter)

        l.addLayout(self._create_progress_with_cancel())
        self._memory_warning = self._create_memory_warning()
        l.addWidget(self._memory_warning)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.ra = self._create_result_area()
        sc.setWidget(self.ra)
        l.addWidget(sc, 1)
        self.setLayout(l)

    def _find(self):
        st = self.sf.text().strip()
        et = self.ef.text().strip()
        try:
            s_parsed = self._parse_numbers(st) if st else [1]
            e_parsed = self._parse_numbers(et)
            if not e_parsed:
                return self._show_error("حد بالا را وارد کنید!")

            s = s_parsed[0]
            e = e_parsed[0]

            if e < 2:
                return self._show_error("حد بالا ≥ ۲!")
            if s > e:
                return self._show_error("حد پایین > حد بالا!")

            estimated = int((e - s) / 100)  # تقریب تراکم دوقلوها
            self._start_calculation(
                self.engine.find_twin_primes, s, e,
                finished_callback=self._display_twins,
                estimated_result_count=estimated
            )
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in TwinPrimesTab")
            self._show_error(f"خطای سیستمی: {e}")

    def _display_twins(self, twins):
        c = self.theme.colors
        self.ra.clear()

        html_content = [f"<h4 style='color:{c['text_accent']};'>{self._fmt(len(twins))} جفت یافت شد</h4><hr>"]
        if not twins:
            html_content.append(f"<p style='color:{c['warning_text']};'>⚠️ جفتی یافت نشد.</p>")
        else:
            html_content.extend(
                self._build_html_list(twins, formatter=lambda x: f"({x[0]}, {x[1]})")
            )

        self.ra.setHtml("<br>".join(html_content))
        self.sf.clear()
        self.ef.clear()


class PrimeFactorsTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(18)

        l.addWidget(self._title_label("🔬 عوامل اول"))
        l.addWidget(self._desc_label("تجزیه به عوامل اول با توان."))

        self.inp = self._create_input("عدد...", (2, QT_MAX_INT32))
        self.inp.returnPressed.connect(self._factor)
        l.addWidget(self.inp)

        l.addWidget(self._create_button("🔬 تجزیه", self._factor, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.ra = self._create_result_area()
        self.ra.hide()
        l.addWidget(self.ra)

        self._tmr = QTimer()
        self._tmr.timeout.connect(lambda: (self.ra.hide(), self._tmr.stop()))
        l.addStretch(1)
        self.setLayout(l)

    def _factor(self):
        t = self.inp.text().strip()
        if not t:
            return self._show_error("عددی وارد کنید!")
        try:
            parsed = self._parse_numbers(t)
            if not parsed:
                return self._show_error("عدد صحیح معتبر!")
            n = parsed[0]
            if n < 2:
                return self._show_error("بزرگتر از ۱!")

            self._start_calculation(
                self.engine.factorize_with_counts, n,
                finished_callback=self._display_factors
            )
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in PrimeFactorsTab")
            self._show_error(f"خطای سیستمی: {e}")

    def _display_factors(self, fc):
        c = self.theme.colors
        self.ra.clear()
        self._tmr.stop()

        html = [f"<h3 style='color:{c['text_accent']};'>🔬 نتایج تجزیه</h3>"]
        if len(fc) == 1 and list(fc.values())[0] == 1:
            html.append(f"<p style='color:{c['success_text']};'>✨ عدد اول!</p>")
        else:
            fs = " × ".join(
                f"{f}<sup>{cnt}</sup>" if cnt > 1 else str(f)
                for f, cnt in sorted(fc.items())
            )
            html.append(f"<p style='font-size:18px; color:{c['accent']};'>{fs}</p>")

        self.ra.setHtml("".join(html))
        self.ra.show()
        self.inp.clear()
        self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)


class GCDTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(18)

        l.addWidget(self._title_label("🔗 ب.م.م"))
        l.addWidget(self._desc_label("بزرگترین مقسوم‌علیه مشترک. اعداد را با کاما جدا کنید."))

        self.inp = self._create_input("مثال: 12, 18, 24")
        self.inp.returnPressed.connect(self._calc)
        l.addWidget(self.inp)

        l.addWidget(self._create_button("🔗 محاسبه", self._calc, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.res = self._create_result_label()
        l.addWidget(self.res)
        l.addStretch(1)
        self.setLayout(l)

    def _calc(self):
        t = self.inp.text().strip()
        if not t:
            return self._show_error("اعداد را وارد کنید!")
        try:
            nums = self._parse_numbers(t)
            if len(nums) < 2:
                return self._show_error("حداقل دو عدد!")

            r = self.engine.gcd(*nums)
            c = self.theme.colors
            self.res.setText(f"🔗 ب.م.م: {self._fmt(r)}")
            self.res.setStyleSheet(
                f"color:{c['accent']}; font-size:20px; font-weight:bold; "
                f"padding:20px; background:{c['bg_card']}; "
                f"border-radius:12px; border:2px solid {c['border_card']};"
            )
            self.res.show()
            self.inp.clear()
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in GCDTab")
            self._show_error(f"خطای سیستمی: {e}")


class LCMTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(18)

        l.addWidget(self._title_label("📏 ک.م.م"))
        l.addWidget(self._desc_label("کوچکترین مضرب مشترک. اعداد را با کاما جدا کنید."))

        self.inp = self._create_input("مثال: 6, 8, 12")
        self.inp.returnPressed.connect(self._calc)
        l.addWidget(self.inp)

        l.addWidget(self._create_button("📏 محاسبه", self._calc, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.res = self._create_result_label()
        l.addWidget(self.res)
        l.addStretch(1)
        self.setLayout(l)

    def _calc(self):
        t = self.inp.text().strip()
        if not t:
            return self._show_error("اعداد را وارد کنید!")
        try:
            nums = self._parse_numbers(t)
            if len(nums) < 2:
                return self._show_error("حداقل دو عدد!")

            r = self.engine.lcm(*nums)
            c = self.theme.colors
            self.res.setText(f"📏 ک.م.م: {self._fmt(r)}")
            self.res.setStyleSheet(
                f"color:{c['accent']}; font-size:20px; font-weight:bold; "
                f"padding:20px; background:{c['bg_card']}; "
                f"border-radius:12px; border:2px solid {c['border_card']};"
            )
            self.res.show()
            self.inp.clear()
        except (ValueError, IndexError):
            self._show_error("عدد صحیح معتبر!")
        except Exception as e:
            logger.exception("Unexpected error in LCMTab")
            self._show_error(f"خطای سیستمی: {e}")


# ============================================================================
# Production-Ready Main Window
# ============================================================================

class PrimeToolsWindow(QWidget):
    TAB_NAMES = [
        "🔍 تشخیص", "🧹 غربال", "📊 شمارنده‌ها",
        "👯 دوقلوها", "🔬 عوامل", "🔗 ب.م.م", "📏 ک.م.م",
    ]

    TAB_CLASSES = [
        PrimeCheckerTab, SieveTab, DivisorsTab, TwinPrimesTab,
        PrimeFactorsTab, GCDTab, LCMTab,
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = MathEngine()
        self.theme = NeumorphicTheme(ThemeMode.DARK)
        self._tabs: List[BasePrimeTab] = []
        self._tab_widget = None
        self._theme_btn = None
        self._font_actions: Dict[str, QAction] = {}

        self._init_ui()
        self._init_menu()
        self._init_shortcuts()
        self._apply_theme()
        self._center()

        logger.info("PrimeToolsWindow v9.1.0 Thread-Safe initialized successfully.")

    def _init_ui(self):
        self.setWindowTitle("🧮 ابزار اعداد اول")
        self.setMinimumSize(940, 660)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(16, 10, 16, 10)
        hdr.setSpacing(12)

        title = QLabel("🧮 ابزار اعداد اول")
        title.setFont(FontSystem.persian_title())
        title.setStyleSheet(f"color: {self.theme.colors['accent']};")
        hdr.addWidget(title)
        hdr.addStretch()

        help_btn = QPushButton("❓")
        help_btn.setObjectName("iconBtn")
        help_btn.setFixedSize(36, 36)
        help_btn.setToolTip("راهنما (F1)")
        help_btn.clicked.connect(self._help)
        hdr.addWidget(help_btn)

        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setObjectName("iconBtn")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip("تغییر تم (Ctrl+T)")
        self._theme_btn.clicked.connect(self._toggle_theme)
        hdr.addWidget(self._theme_btn)

        root.addLayout(hdr)

        self._tab_widget = QTabWidget()
        self._tab_widget.setFont(FontSystem.persian_tab())
        self._tab_widget.setDocumentMode(True)

        for name, cls in zip(self.TAB_NAMES, self.TAB_CLASSES):
            tab = cls(self.engine, self.theme)
            self._tabs.append(tab)
            self._tab_widget.addTab(tab, name)

        root.addWidget(self._tab_widget, 1)

        status = QLabel("Ctrl+1..7 انتخاب تب | Ctrl+T تم | F1 راهنما | Ctrl+C کپی نتایج")
        status.setFont(FontSystem.persian_status())
        status.setStyleSheet(f"color: {self.theme.colors['text_muted']}; padding: 6px;")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(status)

        self.setLayout(root)

    def _init_menu(self):
        mb = QMenuBar()
        mb.setFont(FontSystem.persian_menu())

        fm = mb.addMenu("📁 فایل")
        tm = fm.addMenu("📑 انتخاب تب")
        for i, n in enumerate(self.TAB_NAMES):
            a = QAction(f"  {n}", self)
            a.triggered.connect(lambda _, idx=i: self._tab_widget.setCurrentIndex(idx))
            tm.addAction(a)

        fm.addSeparator()

        ta = QAction("🎨 تغییر تم دارک/لایت", self)
        ta.setShortcut(QKeySequence("Ctrl+T"))
        ta.triggered.connect(self._toggle_theme)
        fm.addAction(ta)

        fm.addSeparator()

        font_menu = fm.addMenu("🔤 فونت اعداد")
        font_group = QActionGroup(self)
        font_group.setExclusive(True)

        eng_action = QAction("🔢 اعداد انگلیسی (Arial)", self)
        eng_action.setCheckable(True)
        eng_action.setChecked(True)
        eng_action.triggered.connect(lambda: self._set_number_font(NumberFontMode.ENGLISH))
        font_group.addAction(eng_action)
        font_menu.addAction(eng_action)
        self._font_actions['english'] = eng_action

        fa_action = QAction("🔢 اعداد فارسی (B Nazanin)", self)
        fa_action.setCheckable(True)
        fa_action.setChecked(False)
        fa_action.triggered.connect(lambda: self._set_number_font(NumberFontMode.PERSIAN))
        font_group.addAction(fa_action)
        font_menu.addAction(fa_action)
        self._font_actions['persian'] = fa_action

        fm.addSeparator()

        ea = QAction("🚪 خروج", self)
        ea.setShortcut(QKeySequence("Ctrl+Q"))
        ea.triggered.connect(self.close)
        fm.addAction(ea)

        hm = mb.addMenu("❓ راهنما")
        aa = QAction("📖 درباره ابزار اعداد اول", self)
        aa.triggered.connect(self._help)
        hm.addAction(aa)

        self.layout().setMenuBar(mb)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            lambda: self._tab_widget.setCurrentIndex((self._tab_widget.currentIndex() - 1) % len(self.TAB_NAMES))
        )
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            lambda: self._tab_widget.setCurrentIndex((self._tab_widget.currentIndex() + 1) % len(self.TAB_NAMES))
        )
        for i in range(len(self.TAB_NAMES)):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self).activated.connect(
                lambda idx=i: self._tab_widget.setCurrentIndex(idx)
            )
        QShortcut(QKeySequence("F1"), self).activated.connect(self._help)

    def _set_number_font(self, mode: NumberFontMode):
        FontSystem.set_number_mode(mode)
        self._font_actions['english'].setChecked(mode == NumberFontMode.ENGLISH)
        self._font_actions['persian'].setChecked(mode == NumberFontMode.PERSIAN)
        for tab in self._tabs:
            tab.refresh_fonts()

    def _toggle_theme(self):
        self.theme.toggle()
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(self.theme.stylesheet())
        self._theme_btn.setText("🌙" if self.theme.is_dark else "☀️")
        for tab in self._tabs:
            tab.update_theme(self.theme)

    def _help(self):
        c = self.theme.colors
        QMessageBox.information(self, "📖 راهنما",
            f"<h3 style='color:{c['accent']};'>🧮 Prime Tools Suite v9.1</h3>"
            f"<p><b>۷ ابزار جامع ریاضی با پشتیبانی Thread-Safe:</b></p>"
            f"<ol>"
            f"<li>🔍 تشخیص عدد اول</li><li>🧹 غربال اراتستن (با قابلیت لغو)</li>"
            f"<li>📊 شمارنده‌ها</li><li>👯 اعداد دوقلو (با قابلیت لغو)</li>"
            f"<li>🔬 عوامل اول</li><li>🔗 ب.م.م</li><li>📏 ک.م.م</li>"
            f"</ol>"
            f"<hr><p><b>⌨️ کلیدهای میانبر:</b></p>"
            f"<ul>"
            f"<li><b>Ctrl+1..7</b> — پرش مستقیم</li>"
            f"<li><b>Ctrl+T</b> — تغییر تم</li>"
            f"<li><b>Ctrl+Q</b> — خروج</li>"
            f"<li><b>F1</b> — راهنما</li>"
            f"<li><b>Esc</b> — لغو عملیات</li>"
            f"</ul>"
        )

    def _center(self):
        s = self.screen().availableGeometry()
        w, h = min(s.width(), 1100), min(s.height(), 740)
        self.resize(int(w * 0.84), int(h * 0.84))
        f = self.frameGeometry()
        f.moveCenter(s.center())
        self.move(f.topLeft())

    def keyPressEvent(self, event):
        """پشتیبانی از کلید Esc برای لغو عملیات."""
        if event.key() == Qt.Key.Key_Escape:
            current_tab = self._tabs[self._tab_widget.currentIndex()]
            if hasattr(current_tab, '_cancel_calculation'):
                current_tab._cancel_calculation()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """پاکسازی ایمن."""
        self.cleanup()
        super().closeEvent(event)

    def cleanup(self):
        """پاکسازی همه منابع."""
        for t in self._tabs:
            if hasattr(t, '_tmr'):
                t._tmr.stop()
            if hasattr(t, '_cancel_calculation'):
                t._cancel_calculation()

        # Wait for all threads to finish
        QThreadPool.globalInstance().waitForDone(2000)


if __name__ == "__main__":
    import sys as _sys
    app = QApplication(_sys.argv)
    FontSystem.setup(app)
    w = PrimeToolsWindow()
    w.show()
    _sys.exit(app.exec())
