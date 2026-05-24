# src/MathAssistant/ui/prime_tools_ui.py
"""
Prime Tools Suite - ابزارهای پیشرفته اعداد اول
طراحی نئومورفیسم/گلس‌مورفیسم کامل | کنتراست WCAG AAA+ | فونت تفکیک‌شده

Author: AmirMohammad Ghasemzadeh
Version: 8.0.0 - Ultimate Neumorphic Edition
"""

import logging
from typing import Optional, List, Tuple, Type, Dict
from enum import Enum, auto

from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import (
    QFont, QIntValidator, QKeySequence, QAction, QShortcut,
    QColor, QPalette, QFontDatabase, QActionGroup, QPainter,
    QBrush, QPen, QPainterPath, QLinearGradient
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QTabWidget, QTabBar,
    QMenuBar, QMenu, QMessageBox, QApplication, QFrame,
    QSizePolicy, QGraphicsDropShadowEffect, QStyleFactory
)

from ..core.math_engine import MathEngine

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================
QT_MAX_INT32: int = 2_147_483_647
SIEVE_MAX_RANGE: int = 10_000_000
RESULT_CHUNK_SIZE: int = 100
RESULT_CLEAR_TIMEOUT_MS: int = 25_000
PRIMALITY_MAX: int = 10 ** 15


# ============================================================================
# Theme System - Ultimate Neumorphic + Glassmorphism
# ============================================================================

class ThemeMode(Enum):
    DARK = auto()
    LIGHT = auto()


class NeumorphicTheme:
    """
    سیستم تم نئومورفیسم + گلس‌مورفیسم کامل.

    اصول طراحی:
    - سایه‌های دوگانه (تیره + روشن) برای عمق نئومورفیسم
    - پس‌زمینه‌های نیمه‌شفاف با blur برای گلس‌مورفیسم
    - کنتراست WCAG AAA+ (حداقل 7:1 برای متن معمولی، 4.5:1 برای بزرگ)
    - پالت رنگی هماهنگ با saturation کنترل شده
    """

    # ========================================================================
    # پالت دارک - Deep Space
    # ========================================================================
    DARK = {
        # پس‌زمینه‌ها - گرادیان ملایم از تیره به تیره‌تر
        'bg_root': '#080c18',
        'bg_primary': '#0d1124',
        'bg_secondary': '#11162b',
        'bg_tertiary': '#151b32',
        'bg_card': '#0f1428',
        'bg_input': '#0b0f1e',
        'bg_input_focus': '#0d1226',
        'bg_glass': 'rgba(13, 17, 36, 0.88)',
        'bg_raised': '#181e38',

        # متن‌ها - کنتراست فوق‌العاده بالا
        'text_primary': '#f2f3f8',      # 17.2:1 روی bg_root
        'text_secondary': '#c4c8d8',    # 12.8:1
        'text_muted': '#9da2b8',        # 8.5:1
        'text_accent': '#b4bfff',       # بنفش روشن

        # Accent - بنفش vibrant
        'accent': '#8b7cf7',
        'accent_hover': '#a094ff',
        'accent_pressed': '#6d5ed8',
        'accent_text': '#ffffff',
        'accent_glow': 'rgba(139, 124, 247, 0.25)',

        # Semantic colors
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

        # Borders - نئومورفیسم
        'border_light': '#1d2340',      # سایه روشن (بالا-چپ)
        'border_dark': '#060810',       # سایه تیره (پایین-راست)
        'border_input': '#0f1428',
        'border_focus': '#8b7cf7',
        'border_card': '#181e38',

        # سایه‌های نئومورفیسم
        'shadow_light': QColor(25, 30, 55, 180),
        'shadow_dark': QColor(3, 5, 12, 200),
        'shadow_card': QColor(0, 0, 0, 60),

        # Glass effect
        'glass_border': 'rgba(255, 255, 255, 0.04)',
        'glass_highlight': 'rgba(255, 255, 255, 0.03)',

        # Scrollbar
        'scrollbar_bg': 'transparent',
        'scrollbar_handle': '#252b48',
        'scrollbar_hover': '#8b7cf7',

        # Tab colors
        'tab_inactive_bg': '#0f1428',
        'tab_inactive_text': '#9da2b8',
        'tab_active_bg': '#181e38',
        'tab_active_text': '#b4bfff',
        'tab_hover_bg': '#131830',
        'tab_border_active': '#8b7cf7',
        'tab_shadow_light': '#1d2340',
        'tab_shadow_dark': '#060810',

        # Overlay
        'hover_overlay': 'rgba(139, 124, 247, 0.1)',
        'pressed_overlay': 'rgba(139, 124, 247, 0.2)',
    }

    # ========================================================================
    # پالت لایت - Soft Cloud
    # ========================================================================
    LIGHT = {
        # پس‌زمینه‌ها
        'bg_root': '#e2e6ed',
        'bg_primary': '#e8ebf2',
        'bg_secondary': '#edf0f5',
        'bg_tertiary': '#f2f4f8',
        'bg_card': '#ffffff',
        'bg_input': '#f7f8fb',
        'bg_input_focus': '#ffffff',
        'bg_glass': 'rgba(255, 255, 255, 0.85)',
        'bg_raised': '#f5f6fa',

        # متن‌ها - کنتراست فوق‌العاده بالا
        'text_primary': '#0d1124',      # 16.8:1 روی bg_root
        'text_secondary': "#121212",    # 9.5:1
        'text_muted': "#171922",        # 7.2:1
        'text_accent': "#242050",       # بنفش تیره

        # Accent
        'accent': "#3e3a5e",
        'accent_hover': '#7c6ff7',
        'accent_pressed': '#5a4cc0',
        'accent_text': '#ffffff',
        'accent_glow': 'rgba(109, 94, 216, 0.2)',

        # Semantic colors
        'success': '#16a34a',
        'success_bg': '#dcfce7',
        'success_text': '#052e16',
        'error': '#dc2626',
        'error_bg': '#fee2e2',
        'error_text': '#450a0a',
        'warning': '#d97706',
        'warning_bg': '#fef3c7',
        'warning_text': '#451a03',
        'info': "#2561e4",
        'info_bg': '#dbeafe',
        'info_text': '#172554',

        # Borders - نئومورفیسم
        'border_light': '#ffffff',       # سایه روشن
        'border_dark': '#c8ccd6',        # سایه تیره
        'border_input': '#d5d8e0',
        'border_focus': '#6d5ed8',
        'border_card': '#e0e3ea',

        # سایه‌های نئومورفیسم
        'shadow_light': QColor(255, 255, 255, 200),
        'shadow_dark': QColor(170, 178, 190, 180),
        'shadow_card': QColor(0, 0, 0, 25),

        # Glass effect
        'glass_border': 'rgba(255, 255, 255, 0.6)',
        'glass_highlight': 'rgba(255, 255, 255, 0.4)',

        # Scrollbar
        'scrollbar_bg': 'transparent',
        'scrollbar_handle': '#c5c9d4',
        'scrollbar_hover': '#6d5ed8',

        # Tab colors
        'tab_inactive_bg': '#edf0f5',
        'tab_inactive_text': "#2d2d2d",
        'tab_active_bg': '#ffffff',
        'tab_active_text': "#221f42",
        'tab_hover_bg': '#f2f4f8',
        'tab_border_active': '#6d5ed8',
        'tab_shadow_light': '#ffffff',
        'tab_shadow_dark': '#c8ccd6',

        # Overlay
        'hover_overlay': 'rgba(109, 94, 216, 0.08)',
        'pressed_overlay': 'rgba(109, 94, 216, 0.15)',
    }

    def __init__(self, mode: ThemeMode = ThemeMode.DARK):
        self.mode = mode
        self.colors = self.DARK if mode == ThemeMode.DARK else self.LIGHT

    def toggle(self):
        self.mode = ThemeMode.LIGHT if self.mode == ThemeMode.DARK else ThemeMode.DARK
        self.colors = self.DARK if self.mode == ThemeMode.DARK else self.LIGHT
        return self.mode

    @property
    def is_dark(self) -> bool:
        return self.mode == ThemeMode.DARK

    def neumorphic_shadow(self, blur=10, offset=4) -> QGraphicsDropShadowEffect:
        """سایه نئومورفیسم با عمق."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset)
        shadow.setColor(QColor(0, 0, 0, 35 if self.is_dark else 20))
        return shadow

    def neumorphic_inset_shadow(self, blur=6) -> QGraphicsDropShadowEffect:
        """سایه داخلی نئومورفیسم (برای ورودی‌ها)."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 50 if self.is_dark else 30))
        return shadow

    def stylesheet(self) -> str:
        c = self.colors
        return f"""
        /* ==================== ROOT ==================== */
        QWidget {{
            background-color: {c['bg_root']};
            color: {c['text_primary']};
            font-family: 'B Nazanin', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}

        /* ==================== INPUTS ==================== */
        QLineEdit {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 2px solid {c['border_input']};
            border-radius: 12px;
            padding: 15px 20px;
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

        /* ==================== TEXT EDIT ==================== */
        QTextEdit {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 2px solid {c['border_card']};
            border-radius: 14px;
            padding: 18px;
            font-size: 14px;
            selection-background-color: {c['accent']};
            selection-color: {c['accent_text']};
        }}

        /* ==================== BUTTONS - Neumorphic ==================== */
        QPushButton {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
            border: 1px solid {c['border_light']};
            border-bottom: 1px solid {c['border_dark']};
            border-radius: 10px;
            padding: 9px 18px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 15px;
            font-weight: bold;
            min-height: 24px;
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

        /* Accent Button - Gradient */
        QPushButton#accentBtn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent']}, stop:1 {c['accent_hover']});
            color: {c['accent_text']};
            border: none;
            font-size: 16px;
            padding: 11px 26px;
            border-radius: 12px;
            min-height: 28px;
        }}
        QPushButton#accentBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {c['accent_hover']}, stop:1 {c['accent']});
        }}
        QPushButton#accentBtn:pressed {{
            background-color: {c['accent_pressed']};
        }}

        /* Icon Button */
        QPushButton#iconBtn {{
            background-color: transparent;
            border: 1px solid {c['border_light']};
            border-bottom: 1px solid {c['border_dark']};
            border-radius: 9px;
            padding: 4px;
            min-width: 34px;
            min-height: 34px;
            font-size: 15px;
        }}
        QPushButton#iconBtn:hover {{
            background-color: {c['bg_raised']};
            border-color: {c['accent']};
        }}

        /* ==================== TABS - Neumorphic ==================== */
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}

        QTabBar::tab {{
            background-color: {c['tab_inactive_bg']};
            color: {c['tab_inactive_text']};
            padding: 11px 22px;
            margin: 4px 3px;
            border: 1px solid {c['tab_shadow_light']};
            border-bottom: 1px solid {c['tab_shadow_dark']};
            border-radius: 10px 10px 0 0;
            font-family: 'B Nazanin', sans-serif;
            font-size: 14px;
            font-weight: bold;
            min-width: 88px;
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

        /* ==================== SCROLLBARS ==================== */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {c['scrollbar_bg']};
            width: 7px;
            margin: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['scrollbar_handle']};
            border-radius: 4px;
            min-height: 32px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['scrollbar_hover']};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            height: 0;
        }}

        /* ==================== MENUS ==================== */
        QMenuBar {{
            background-color: {c['bg_secondary']};
            border-bottom: 1px solid {c['border_dark']};
            padding: 3px 8px;
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
            padding: 8px 26px;
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

        /* ==================== TOOLTIP ==================== */
        QToolTip {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border_card']};
            border-radius: 10px;
            padding: 7px 12px;
            font-size: 12px;
        }}

        /* ==================== MESSAGEBOX ==================== */
        QMessageBox {{
            background-color: {c['bg_card']};
        }}
        QMessageBox QLabel {{
            color: {c['text_primary']};
            font-family: 'B Nazanin', sans-serif;
        }}
        """


# ============================================================================
# Font System - کاملاً بازنویسی شده با fix فونت اعداد
# ============================================================================

class NumberFontMode(Enum):
    ENGLISH = "english"
    PERSIAN = "persian"


class FontSystem:
    """
    سیستم فونت تفکیک شده.

    اندازه‌های نهایی:
    - فارسی عنوان: 21pt bold
    - فارسی توضیح: 17pt
    - فارسی دکمه: 16pt bold
    - فارسی تب: 15pt bold
    - فارسی منو: 14pt
    - انگلیسی اعداد ورودی: 13pt
    - انگلیسی اعداد نتیجه: 13pt
    - انگلیسی اعداد بزرگ: 16pt bold

    fix: فونت اعداد مستقیماً روی هر ویجت set میشه،
    نه از طریق stylesheet. اینجوری قطعاً کار میکنه.
    """

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
        logger.info(f"Font system initialized. Number mode: {cls._number_mode.value}")

    @classmethod
    def set_number_mode(cls, mode: NumberFontMode):
        cls._number_mode = mode
        logger.info(f"Number font mode changed to: {mode.value}")

    @classmethod
    def get_number_mode(cls) -> NumberFontMode:
        return cls._number_mode

    @classmethod
    def _number_font_name(cls) -> str:
        """نام فونت فعلی برای اعداد - مستقیماً با if/else"""
        if cls._number_mode == NumberFontMode.ENGLISH:
            return cls.ENGLISH_NUMBER_FONT
        else:
            return cls.PERSIAN_NUMBER_FONT

    @classmethod
    def _make_font(cls, family: str, size: int, bold: bool = False) -> QFont:
        """ساخت QFont با family مشخص."""
        font = QFont(family, size)
        font.setBold(bold)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        return font

    # ========================================================================
    # فونت‌های فارسی
    # ========================================================================

    @classmethod
    def persian_title(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 21, True)

    @classmethod
    def persian_subtitle(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 17, False)

    @classmethod
    def persian_button(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 16, True)

    @classmethod
    def persian_tab(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 15, True)

    @classmethod
    def persian_menu(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 14, False)

    @classmethod
    def persian_status(cls) -> QFont:
        return cls._make_font(cls.PERSIAN_FONT, 11, False)

    # ========================================================================
    # فونت‌های اعداد - این‌ها مستقیماً استفاده میشن
    # ========================================================================

    @classmethod
    def number_input(cls) -> QFont:
        """فونت ورودی اعداد - مستقیماً روی QLineEdit.setFont"""
        return cls._make_font(cls._number_font_name(), 13, False)

    @classmethod
    def number_result(cls) -> QFont:
        """فونت نتیجه عددی - مستقیماً روی QTextEdit.setFont"""
        return cls._make_font(cls._number_font_name(), 13, False)

    @classmethod
    def number_big(cls) -> QFont:
        """فونت نتیجه بزرگ - مستقیماً روی QLabel.setFont"""
        return cls._make_font(cls._number_font_name(), 16, True)

    @classmethod
    def mono(cls, size=12) -> QFont:
        return cls._make_font(cls.MONO_FONT, size, False)


# ============================================================================
# ویجت‌های سفارشی نئومورفیسم
# ============================================================================

class NeumorphicInput(QLineEdit):
    """ورودی با طراحی نئومورفیسم - سایه داخلی."""

    def __init__(self, placeholder="", vrange=None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFont(FontSystem.number_input())
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        if vrange:
            lo, hi = vrange
            lo, hi = max(lo, -QT_MAX_INT32), min(hi, QT_MAX_INT32)
            if lo < hi:
                self.setValidator(QIntValidator(lo, hi))

    def update_font(self):
        """به‌روزرسانی فونت بعد از تغییر حالت."""
        self.setFont(FontSystem.number_input())


class NeumorphicButton(QPushButton):
    """دکمه با طراحی نئومورفیسم - سایه خارجی و gradient."""

    def __init__(self, text: str, accent: bool = False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("accentBtn" if accent else "")
        self.setFont(FontSystem.persian_button())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

    def update_font(self):
        self.setFont(FontSystem.persian_button())


class NeumorphicResultArea(QTextEdit):
    """ناحیه نمایش نتیجه با طراحی نئومورفیسم."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(FontSystem.number_result())
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def update_font(self):
        self.setFont(FontSystem.number_result())


class NeumorphicResultLabel(QLabel):
    """لیبل نتیجه با قابلیت به‌روزرسانی فونت."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(FontSystem.number_big())
        self.setWordWrap(True)
        self.setMinimumHeight(50)
        self.hide()

    def update_font(self):
        self.setFont(FontSystem.number_big())


# ============================================================================
# Base Tab - کاملاً بازنویسی شده
# ============================================================================

class BasePrimeTab(QWidget):
    """کلاس پایه برای تمام تب‌ها."""

    def __init__(self, engine: MathEngine, theme: NeumorphicTheme, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.theme = theme
        self.setFont(FontSystem.persian_subtitle())
        self._number_widgets: List = []  # ویجت‌هایی که فونت عددی دارن
        self._build_ui()

    def _build_ui(self):
        raise NotImplementedError

    def update_theme(self, theme: NeumorphicTheme):
        self.theme = theme

    def refresh_fonts(self):
        """به‌روزرسانی فونت‌های عددی بعد از تغییر حالت."""
        for widget in self._number_widgets:
            if hasattr(widget, 'update_font'):
                widget.update_font()

    def _register_number_widget(self, widget):
        """ثبت ویجت عددی برای به‌روزرسانی فونت."""
        self._number_widgets.append(widget)

    # ========================================================================
    # Factory Methods
    # ========================================================================

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

    # ========================================================================
    # Utilities
    # ========================================================================

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "⚠️ خطا", msg)

    @staticmethod
    def _fmt(n: int) -> str:
        return f"{n:,}"

    @staticmethod
    def _parse_numbers(text: str) -> List[int]:
        text = text.replace("،", ",").replace("؛", ";").replace("٫", ".")
        parts = text.replace(",", " ").split()
        return [int(p) for p in parts if p]


# ============================================================================
# Tab 1: تشخیص عدد اول
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
        self._tmr.timeout.connect(lambda: (self.res.hide(), self._tmr.stop()))
        l.addStretch(1)
        self.setLayout(l)

    def _check(self):
        t = self.inp.text().strip()
        if not t: return self._show_error("عددی وارد کنید!")
        try:
            n = int(t)
            if n < 1: return self._show_error("بزرگتر از ۰!")
            if n > PRIMALITY_MAX: return self._show_error(f"حداکثر: {self._fmt(PRIMALITY_MAX)}")

            r = self.engine.check_prime(n)
            c = self.theme.colors

            if r.is_prime:
                self.res.setText(f"✅ {self._fmt(n)} عدد اول است! ({r.divisor_count} مقسوم‌علیه)")
                self.res.setStyleSheet(
                    f"color:{c['success_text']}; font-size:16px; font-weight:bold; "
                    f"padding:20px; background:{c['success_bg']}; "
                    f"border-radius:12px; border:2px solid {c['border_card']};"
                )
            else:
                fs = " × ".join(map(str, r.factors)) if r.factors else "—"
                self.res.setText(
                    f"❌ {self._fmt(n)} اول نیست!\nعوامل: {fs}\nمقسوم‌علیه‌ها: {r.divisor_count}"
                )
                self.res.setStyleSheet(
                    f"color:{c['error_text']}; font-size:15px; font-weight:bold; "
                    f"padding:20px; background:{c['error_bg']}; "
                    f"border-radius:12px; border:2px solid {c['border_card']};"
                )

            self.res.show()
            self.inp.clear()
            self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)
        except ValueError:
            self._show_error("عدد صحیح معتبر!")

    def update_theme(self, theme):
        super().update_theme(theme)
        if self.res.isVisible():
            c = self.theme.colors
            prefix = "✅" if "✅" in self.res.text() else "❌"
            if prefix == "✅":
                self.res.setStyleSheet(
                    f"color:{c['success_text']}; font-size:16px; font-weight:bold; "
                    f"padding:20px; background:{c['success_bg']}; "
                    f"border-radius:12px; border:2px solid {c['border_card']};"
                )
            else:
                self.res.setStyleSheet(
                    f"color:{c['error_text']}; font-size:15px; font-weight:bold; "
                    f"padding:20px; background:{c['error_bg']}; "
                    f"border-radius:12px; border:2px solid {c['border_card']};"
                )


# ============================================================================
# Tab 2: غربال
# ============================================================================

class SieveTab(BasePrimeTab):
    def _build_ui(self):
        l = QVBoxLayout()
        l.setContentsMargins(36, 28, 36, 28)
        l.setSpacing(14)

        l.addWidget(self._title_label("🧹 غربال اراتستن"))
        l.addWidget(self._desc_label("اعداد اول در بازه مشخص را بیابید."))

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
        s = int(st) if st else 1
        if not et: return self._show_error("حد بالا را وارد کنید!")
        try:
            e = int(et)
            if e < 2: return self._show_error("حد بالا ≥ ۲!")
            if s > e: return self._show_error("حد پایین > حد بالا!")
            if e > SIEVE_MAX_RANGE: return self._show_error(f"حداکثر: {self._fmt(SIEVE_MAX_RANGE)}")

            primes = self.engine.generate_primes(s, e)
            c = self.theme.colors
            self.ra.clear()
            self.ra.append(
                f"<h4 style='color:{c['text_accent']};'>"
                f"🔢 {self._fmt(len(primes))} عدد اول بین {s} تا {e}</h4><hr>"
            )
            for i in range(0, len(primes), RESULT_CHUNK_SIZE):
                self.ra.append("، ".join(map(str, primes[i:i+RESULT_CHUNK_SIZE])))

            self.sf.clear()
            self.ef.clear()
        except ValueError:
            self._show_error("عدد صحیح معتبر!")


# ============================================================================
# Tab 3: شمارنده‌ها
# ============================================================================

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

        # دکمه با استایل accent
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
        if not t: return self._show_error("عددی وارد کنید!")
        try:
            n = int(t)
            if n < 1: return self._show_error("بزرگتر از ۰!")

            divs = self.engine.get_divisors(n)
            c = self.theme.colors
            self.ra.clear()
            self.ra.append(
                f"<h3 style='color:{c['text_accent']};'>نتایج برای عدد {n}</h3>"
                f"<p>تعداد شمارنده‌ها: <b>{len(divs)}</b></p>"
            )
            if self.engine.is_prime(n):
                self.ra.append(f"<p style='color:{c['success_text']};'>✨ این عدد اول است.</p>")
            self.ra.append("<h4>شمارنده‌ها:</h4>")
            for i in range(0, len(divs), RESULT_CHUNK_SIZE):
                self.ra.append("، ".join(map(str, divs[i:i+RESULT_CHUNK_SIZE])))

            self.ra.show()
            self.inp.clear()
            self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)
        except ValueError:
            self._show_error("عدد صحیح معتبر!")


# ============================================================================
# Tab 4: دوقلوها
# ============================================================================

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
        s = int(st) if st else 1
        if not et: return self._show_error("حد بالا را وارد کنید!")
        try:
            e = int(et)
            if e < 2: return self._show_error("حد بالا ≥ ۲!")
            if s > e: return self._show_error("حد پایین > حد بالا!")

            twins = self.engine.find_twin_primes(s, e)
            c = self.theme.colors
            self.ra.clear()
            self.ra.append(
                f"<h4 style='color:{c['text_accent']};'>"
                f"👯 {self._fmt(len(twins))} جفت بین {s} تا {e}</h4><hr>"
            )
            if not twins:
                self.ra.append(f"<p style='color:{c['warning_text']};'>⚠️ جفتی یافت نشد.</p>")
            else:
                for i in range(0, len(twins), RESULT_CHUNK_SIZE):
                    self.ra.append("، ".join(f"({p1}, {p2})" for p1, p2 in twins[i:i+RESULT_CHUNK_SIZE]))

            self.sf.clear()
            self.ef.clear()
        except ValueError:
            self._show_error("عدد صحیح معتبر!")


# ============================================================================
# Tab 5: عوامل اول
# ============================================================================

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
        if not t: return self._show_error("عددی وارد کنید!")
        try:
            n = int(t)
            if n < 2: return self._show_error("بزرگتر از ۱!")

            fc = self.engine.factorize_with_counts(n)
            c = self.theme.colors
            self.ra.clear()
            self.ra.append(f"<h3 style='color:{c['text_accent']};'>🔬 {self._fmt(n)}</h3>")
            if len(fc) == 1 and list(fc.values())[0] == 1:
                self.ra.append(f"<p style='color:{c['success_text']};'>✨ عدد اول!</p>")
            else:
                fs = " × ".join(
                    f"{f}<sup>{cnt}</sup>" if cnt > 1 else str(f)
                    for f, cnt in sorted(fc.items())
                )
                self.ra.append(f"<p style='font-size:18px; color:{c['accent']};'>{fs}</p>")

            self.ra.show()
            self.inp.clear()
            self._tmr.start(RESULT_CLEAR_TIMEOUT_MS)
        except ValueError:
            self._show_error("عدد صحیح معتبر!")


# ============================================================================
# Tab 6: ب.م.م
# ============================================================================

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

        # دکمه با استایل accent
        l.addWidget(self._create_button("🔗 محاسبه", self._calc, True), 0, Qt.AlignmentFlag.AlignHCenter)

        self.res = self._create_result_label()
        l.addWidget(self.res)
        l.addStretch(1)
        self.setLayout(l)

    def _calc(self):
        t = self.inp.text().strip()
        if not t: return self._show_error("اعداد را وارد کنید!")
        try:
            nums = self._parse_numbers(t)
            if len(nums) < 2: return self._show_error("حداقل دو عدد!")

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
        except ValueError:
            self._show_error("فرمت نامعتبر!")


# ============================================================================
# Tab 7: ک.م.م
# ============================================================================

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
        if not t: return self._show_error("اعداد را وارد کنید!")
        try:
            nums = self._parse_numbers(t)
            if len(nums) < 2: return self._show_error("حداقل دو عدد!")

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
        except ValueError:
            self._show_error("فرمت نامعتبر!")


# ============================================================================
# پنجره اصلی - Ultimate Neumorphic
# ============================================================================

class PrimeToolsWindow(QWidget):
    """
    Prime Tools Suite v8.0 - Ultimate Neumorphic Edition.

    ویژگی‌ها:
    - نئومورفیسم کامل با سایه‌های دوگانه
    - گلس‌مورفیسم با پس‌زمینه‌های نیمه‌شفاف
    - کنتراست WCAG AAA+ (17:1)
    - فونت تفکیک‌شده با fix کامل فونت اعداد
    """

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

        logger.info("PrimeToolsWindow v8.0.0 (Ultimate Neumorphic) initialized")

    def _init_ui(self):
        self.setWindowTitle("🧮 ابزار اعداد اول")
        self.setMinimumSize(920, 640)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
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
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.clicked.connect(self._help)
        hdr.addWidget(help_btn)

        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setObjectName("iconBtn")
        self._theme_btn.setFixedSize(36, 36)
        self._theme_btn.setToolTip("تغییر تم (Ctrl+T)")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)
        hdr.addWidget(self._theme_btn)

        root.addLayout(hdr)

        # Tabs
        self._tab_widget = QTabWidget()
        self._tab_widget.setFont(FontSystem.persian_tab())
        self._tab_widget.setDocumentMode(True)

        for name, cls in zip(self.TAB_NAMES, self.TAB_CLASSES):
            tab = cls(self.engine, self.theme)
            self._tabs.append(tab)
            self._tab_widget.addTab(tab, name)

        root.addWidget(self._tab_widget, 1)

        # Status bar
        status = QLabel("Ctrl+S تب بعد | Ctrl+Shift+S تب قبل | Ctrl+1..7 تب مستقیم | Ctrl+T تم | F1 راهنما")
        status.setFont(FontSystem.persian_status())
        status.setStyleSheet(f"color: {self.theme.colors['text_muted']}; padding: 5px;")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(status)

        self.setLayout(root)

    def _init_menu(self):
        mb = QMenuBar()
        mb.setFont(FontSystem.persian_menu())

        # فایل
        fm = mb.addMenu("📁 فایل")

        # تب‌ها
        tm = fm.addMenu("📑 انتخاب تب")
        for i, n in enumerate(self.TAB_NAMES):
            a = QAction(f"  {n}", self)
            a.triggered.connect(lambda _, idx=i: self._tab_widget.setCurrentIndex(idx))
            tm.addAction(a)

        fm.addSeparator()

        # تغییر تم
        ta = QAction("🎨 تغییر تم دارک/لایت", self)
        ta.setShortcut(QKeySequence("Ctrl+T"))
        ta.triggered.connect(self._toggle_theme)
        fm.addAction(ta)

        fm.addSeparator()

        # فونت اعداد
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

        # راهنما
        hm = mb.addMenu("❓ راهنما")
        aa = QAction("📖 درباره ابزار اعداد اول", self)
        aa.triggered.connect(self._help)
        hm.addAction(aa)

        self.layout().setMenuBar(mb)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            lambda: self._tab_widget.setCurrentIndex((self._tab_widget.currentIndex() + 1) % 7)
        )
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            lambda: self._tab_widget.setCurrentIndex((self._tab_widget.currentIndex() - 1) % 7)
        )
        for i in range(7):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self).activated.connect(
                lambda idx=i: self._tab_widget.setCurrentIndex(idx)
            )
        QShortcut(QKeySequence("F1"), self).activated.connect(self._help)

    def _set_number_font(self, mode: NumberFontMode):
        """تغییر فونت اعداد و اعمال روی همه ویجت‌ها."""
        FontSystem.set_number_mode(mode)

        # به‌روزرسانی چکمارک‌ها
        self._font_actions['english'].setChecked(mode == NumberFontMode.ENGLISH)
        self._font_actions['persian'].setChecked(mode == NumberFontMode.PERSIAN)

        # به‌روزرسانی همه تب‌ها
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
            f"<h3 style='color:{c['accent']};'>🧮 Prime Tools Suite v8.0</h3>"
            f"<p><b>۷ ابزار قدرتمند برای اعداد اول:</b></p>"
            f"<ol>"
            f"<li>🔍 تشخیص عدد اول</li><li>🧹 غربال اراتستن</li>"
            f"<li>📊 شمارنده‌ها</li><li>👯 اعداد دوقلو</li>"
            f"<li>🔬 عوامل اول</li><li>🔗 ب.م.م</li><li>📏 ک.م.م</li>"
            f"</ol>"
            f"<hr><p><b>⌨️ شورتکات‌ها:</b></p>"
            f"<ul>"
            f"<li><b>Ctrl+S</b> — تب بعد</li>"
            f"<li><b>Ctrl+Shift+S</b> — تب قبل</li>"
            f"<li><b>Ctrl+1..7</b> — تب مستقیم</li>"
            f"<li><b>Ctrl+T</b> — تغییر تم</li>"
            f"<li><b>Ctrl+Q</b> — خروج</li>"
            f"<li><b>F1</b> — راهنما</li>"
            f"</ul>"
        )

    def _center(self):
        s = self.screen().availableGeometry()
        w, h = min(s.width(), 1100), min(s.height(), 740)
        self.resize(int(w * 0.84), int(h * 0.84))
        f = self.frameGeometry()
        f.moveCenter(s.center())
        self.move(f.topLeft())

    def cleanup(self):
        for t in self._tabs:
            if hasattr(t, '_tmr'):
                t._tmr.stop()


if __name__ == "__main__":
    import sys as _sys
    app = QApplication(_sys.argv)
    FontSystem.setup(app)
    w = PrimeToolsWindow()
    w.show()
    _sys.exit(app.exec())
