# src/MathAssistant/ui/vector_window.py
"""
Vector & Graph Tools - ابزارهای بردار، مختصات و رسم نمودار
کاملاً فارسی | RTL | Ultra High Contrast | Multi-Graph | Animated

Author: AmirMohammad Ghasemzadeh
Version: 10.1.2 - Fixed Quiver.set_width & GroupBox title clipping
"""

import sys
import io
import base64
import re
import ast
import logging
from typing import Optional, List, Tuple, Dict, Any, Set, Callable
from dataclasses import dataclass, field

import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    FigureCanvasAgg
)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.quiver import Quiver

from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QThread, QPoint, QRectF, QSize,
    pyqtSlot, QObject, QEvent
)
from PyQt6.QtGui import (
    QFont, QDoubleValidator, QKeySequence,
    QShortcut, QColor, QPixmap, QIcon,
    QPainterPath, QPen, QBrush, QPainter,
    QValidator, QPalette
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QTabWidget, QTabBar,
    QMessageBox, QApplication, QFrame, QToolTip,
    QSizePolicy, QGraphicsOpacityEffect, QStackedWidget,
    QGridLayout, QGroupBox, QFileDialog, QDialog,
    QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QColorDialog, QComboBox,
    QStyleFactory, QCheckBox, QSlider, QLayout, QSplitter
)

from ..core.math_engine import MathEngine, Vector2D
from .prime_tools_ui import NeumorphicTheme, FontSystem, ThemeMode

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================
MAX_VECTOR_VALUE: int = 1000
MAX_VECTOR_COUNT: int = 25
GRAPH_RESOLUTION: int = 500
DEFAULT_GRAPH_DPI: int = 150
ANIMATION_DURATION: int = 120
TOOLTIP_DELAY: int = 2000

# UI Spacing Constants
CONTROL_PANEL_MIN_WIDTH: int = 280
CONTROL_PANEL_MAX_WIDTH: int = 340
BUTTON_MIN_HEIGHT: int = 32
BUTTON_PADDING: int = 6
GROUP_SPACING: int = 8
SECTION_SPACING: int = 6

# High-contrast color palette for multiple graphs
GRAPH_COLORS: List[str] = [
    '#ff6b6b', '#4ecdc4', '#ffe66d', '#a78bfa', '#34d399',
    '#f472b6', '#60a5fa', '#fbbf24', '#818cf8', '#fb923c',
    '#22d3ee', '#f87171', '#a3e635', '#e879f9', '#38bdf8',
    '#facc15', '#2dd4bf', '#fb7185', '#8b5cf6', '#f97316',
]

# Safe functions whitelist for eval
SAFE_FUNCTIONS: Set[str] = {
    'sin', 'cos', 'tan', 'log', 'exp', 'sqrt', 'abs',
    'pi', 'e', 'x', 'np', 'linspace', 'array', 'arange',
    'sum', 'mean', 'max', 'min', 'clip', 'where', 'concatenate',
}

# Dangerous imports to filter
BLACKLIST_IMPORTS: Set[str] = {
    'os', 'sys', 'subprocess', 'shutil', 'importlib',
    '__import__', 'eval', 'exec', 'compile', 'open',
    'file', 'input', 'raw_input', 'getattr', 'setattr',
    'delattr', 'hasattr', 'globals', 'locals', 'vars',
    'dir', 'type', 'object', 'super', 'classmethod',
    'staticmethod', 'property', '__builtins__', '__builtin__',
}


def safe_disconnect(signal: pyqtSignal) -> None:
    """قطع ایمن تمام اتصالات یک سیگنال برای جلوگیری از Memory Leak."""
    try:
        signal.disconnect()
    except (TypeError, RuntimeError):
        pass


# ============================================================================
# Secure Code Parser
# ============================================================================

class SecureCodeValidator(ast.NodeVisitor):
    """اعتبارسنجی امن کد پایتون برای جلوگیری از اجرای کدهای مخرب."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.allowed_imports: Set[str] = {'numpy', 'matplotlib'}
        self.allowed_functions: Set[str] = SAFE_FUNCTIONS

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split('.')[0] not in self.allowed_imports:
                self.errors.append(f"ماژول '{alias.name}' مجاز نیست")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            if node.module.split('.')[0] not in self.allowed_imports:
                self.errors.append(f"ماژول '{node.module}' مجاز نیست")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in BLACKLIST_IMPORTS:
                self.errors.append(f"تابع '{node.func.id}' غیرمجاز است")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in BLACKLIST_IMPORTS:
                self.errors.append(f"متد '{node.func.attr}' غیرمجاز است")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in BLACKLIST_IMPORTS:
            self.errors.append(f"نام '{node.id}' غیرمجاز است")
        self.generic_visit(node)


def validate_code_safety(code: str) -> Tuple[bool, str]:
    """اعتبارسنجی امنیتی کد پایتون."""
    try:
        tree = ast.parse(code)
        validator = SecureCodeValidator()
        validator.visit(tree)

        if validator.errors:
            return False, "\n".join(validator.errors)
        return True, ""
    except SyntaxError as e:
        return False, f"خطای نحوی: {str(e)}"
    except Exception as e:
        return False, f"خطا در اعتبارسنجی: {str(e)}"


# ============================================================================
# Ultra High Contrast Theme
# ============================================================================

class UltraHighContrastTheme(NeumorphicTheme):
    """تم با کنتراست فوق‌العاده بالا برای دسترسی‌پذیری بهتر."""

    DARK: Dict[str, Any] = {
        **NeumorphicTheme.DARK,
        'text_primary': '#ffffff',
        'text_secondary': '#d0d4e0',
        'text_muted': '#a8acb8',
        'text_accent': '#c4c8ff',
        'bg_root': '#000000',
        'bg_primary': '#080810',
        'bg_card': '#0c0c18',
        'bg_input': '#050510',
        'border_light': '#2a2a40',
        'border_dark': '#000000',
        'accent': '#8b7cf7',
        'accent_hover': '#a094ff',
        'tab_inactive_bg': '#0c0c18',
        'tab_inactive_text': '#a8acb8',
        'tab_active_bg': '#141428',
        'tab_active_text': '#c4c8ff',
        'tab_hover_bg': '#101020',
        'tab_border_active': '#8b7cf7',
        'tab_shadow_light': '#2a2a40',
        'tab_shadow_dark': '#000000',
        'scrollbar_handle': '#2a2a40',
        'shadow_dark': QColor(0, 0, 0, 200),
        'shadow_light': QColor(40, 40, 60, 180),
        'success': '#34d399',
        'error': '#f87171',
        'warning': '#fbbf24',
        'input_error_bg': '#1a0000',
        'input_error_border': '#ff4444',
        'tooltip_bg': '#1a1a2e',
        'tooltip_text': '#e0e0e0',
    }

    LIGHT: Dict[str, Any] = {
        **NeumorphicTheme.LIGHT,
        'text_primary': '#000000',
        'text_secondary': '#1a1a2e',
        'text_muted': '#3a3a50',
        'text_accent': '#3020a0',
        'bg_root': '#ffffff',
        'bg_primary': '#f8f8fc',
        'bg_card': '#ffffff',
        'bg_input': '#fdfdfe',
        'border_light': '#d0d0d8',
        'border_dark': '#b8b8c0',
        'accent': '#6d5ed8',
        'accent_hover': '#5a4cc0',
        'tab_inactive_bg': '#f0f0f5',
        'tab_inactive_text': '#3a3a50',
        'tab_active_bg': '#ffffff',
        'tab_active_text': '#3020a0',
        'tab_hover_bg': '#f8f8fc',
        'tab_border_active': '#6d5ed8',
        'tab_shadow_light': '#ffffff',
        'tab_shadow_dark': '#b8b8c0',
        'scrollbar_handle': '#c0c0c8',
        'shadow_dark': QColor(180, 180, 190, 200),
        'shadow_light': QColor(255, 255, 255, 200),
        'success': '#059669',
        'error': '#dc2626',
        'warning': '#d97706',
        'input_error_bg': '#fff5f5',
        'input_error_border': '#dc2626',
        'tooltip_bg': '#f8f8fc',
        'tooltip_text': '#1a1a2e',
    }

    def __init__(self, mode: ThemeMode = ThemeMode.DARK) -> None:
        super().__init__(mode)
        self.colors: Dict[str, Any] = self.DARK if mode == ThemeMode.DARK else self.LIGHT

    def toggle(self) -> ThemeMode:
        super().toggle()
        self.colors = self.DARK if self.mode == ThemeMode.DARK else self.LIGHT
        return self.mode

    @property
    def is_dark(self) -> bool:
        return self.mode == ThemeMode.DARK


# ============================================================================
# Compact RTL Stylesheet - Fixed GroupBox title clipping
# ============================================================================

def build_stylesheet(colors: Dict[str, Any]) -> str:
    """ساخت استایل‌شیت RTL با رفع بریدگی عنوان GroupBox."""

    parts: List[str] = [
        # Base styles
        "* { font-family: 'B Nazanin', 'Tahoma', sans-serif; }",
        f"""
        QWidget {{
            background-color: {colors['bg_root']};
            color: {colors['text_primary']};
            font-size: 14px;
        }}

        /* Input fields */
        QLineEdit {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_light']};
            border-radius: 6px;
            padding: 8px 12px;
            font-family: 'Arial', 'B Nazanin', sans-serif;
            font-size: 13px;
            selection-background-color: {colors['accent']};
            selection-color: white;
            min-height: 20px;
        }}
        QLineEdit:focus {{
            border-color: {colors['accent']};
        }}
        QLineEdit[valid="false"] {{
            background-color: {colors['input_error_bg']};
            border-color: {colors['input_error_border']};
        }}

        /* Text editor */
        QTextEdit {{
            background-color: {colors['bg_card']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_light']};
            border-radius: 6px;
            padding: 8px;
            font-family: 'Consolas', 'Arial', sans-serif;
            font-size: 12px;
        }}

        /* Buttons - General */
        QPushButton {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_light']};
            border-radius: 6px;
            padding: {BUTTON_PADDING}px 14px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 14px;
            font-weight: bold;
            min-height: {BUTTON_MIN_HEIGHT}px;
        }}
        QPushButton:hover {{
            background-color: {colors['bg_card']};
            border-color: {colors['accent']};
        }}
        QPushButton:pressed {{
            background-color: {colors['accent']};
            color: white;
        }}

        /* Accent button */
        QPushButton#accentBtn {{
            background-color: {colors['accent']};
            color: white;
            border: none;
            font-size: 15px;
            padding: 8px 16px;
            border-radius: 6px;
            min-height: {BUTTON_MIN_HEIGHT + 4}px;
        }}
        QPushButton#accentBtn:hover {{
            background-color: {colors['accent_hover']};
        }}

        /* Danger button */
        QPushButton#dangerBtn {{
            background-color: #dc2626;
            color: white;
            border: none;
            min-height: {BUTTON_MIN_HEIGHT}px;
        }}
        QPushButton#dangerBtn:hover {{
            background-color: #ef4444;
        }}

        /* Icon button */
        QPushButton#iconBtn {{
            background: transparent;
            border: 1px solid {colors['border_light']};
            border-radius: 6px;
            padding: 4px;
            min-width: 32px;
            min-height: 32px;
            font-size: 14px;
        }}
        QPushButton#iconBtn:hover {{
            background: {colors['bg_card']};
        }}

        /* Group box - Fixed title clipping with proper padding */
        QGroupBox {{
            font-family: 'B Nazanin', sans-serif;
            font-size: 14px;
            font-weight: bold;
            color: {colors['text_accent']};
            border: 1px solid {colors['border_light']};
            border-radius: 8px;
            margin-top: 20px;
            padding: 24px 8px 10px 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top right;
            right: 12px;
            top: 2px;
            padding: 2px 8px;
            background-color: {colors['bg_card']};
            border-radius: 4px;
        }}

        /* List widget */
        QListWidget {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_light']};
            border-radius: 6px;
            font-family: 'Arial', 'B Nazanin', sans-serif;
            font-size: 12px;
            padding: 2px;
        }}
        QListWidget::item {{
            padding: 4px 8px;
            border-radius: 3px;
            min-height: 24px;
        }}
        QListWidget::item:selected {{
            background-color: {colors['accent']};
            color: white;
        }}
        QListWidget::item:hover {{
            background-color: {colors['bg_card']};
        }}

        /* Combo box */
        QComboBox {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_light']};
            border-radius: 6px;
            padding: 6px 12px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 13px;
            min-height: 20px;
        }}
        QComboBox:hover {{
            border-color: {colors['accent']};
        }}
        QComboBox QAbstractItemView {{
            background: {colors['bg_card']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_light']};
            selection-background-color: {colors['accent']};
        }}

        /* Check box */
        QCheckBox {{
            font-family: 'B Nazanin', sans-serif;
            font-size: 13px;
            color: {colors['text_primary']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid {colors['border_light']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['accent']};
            border-color: {colors['accent']};
        }}

        /* Scroll area */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}

        /* Scroll bars */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {colors['scrollbar_handle']};
            border-radius: 4px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors['accent']};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            height: 0;
        }}

        /* Menu */
        QMenu {{
            background: {colors['bg_card']};
            border: 1px solid {colors['border_light']};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 4px;
            font-family: 'B Nazanin', sans-serif;
            font-size: 13px;
        }}
        QMenu::item:selected {{
            background: {colors['accent']};
            color: white;
        }}

        /* Tooltip */
        QToolTip {{
            background: {colors['tooltip_bg']};
            color: {colors['tooltip_text']};
            border: 1px solid {colors['border_light']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: 'B Nazanin', sans-serif;
        }}

        /* Message box */
        QMessageBox {{
            background: {colors['bg_card']};
        }}
        QMessageBox QLabel {{
            color: {colors['text_primary']};
            font-family: 'B Nazanin', sans-serif;
        }}

        /* Dialog */
        QDialog {{
            background: {colors['bg_root']};
        }}

        /* Frame */
        QFrame#card {{
            background-color: {colors['bg_card']};
            border: 1px solid {colors['border_light']};
            border-radius: 10px;
            padding: 8px;
        }}
        """
    ]

    return "\n".join(parts)


# ============================================================================
# Canvas Frame
# ============================================================================

class CanvasFrame(QFrame):
    """فریم نئومورفیک برای Canvas‌ها."""

    def __init__(self, theme: UltraHighContrastTheme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme: UltraHighContrastTheme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.setContentsMargins(6, 6, 6, 6)

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = self._theme.colors
        rect = self.rect()
        outer_rect = QRectF(
            float(rect.x()) + 3,
            float(rect.y()) + 3,
            float(rect.width()) - 6,
            float(rect.height()) - 6,
        )

        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(outer_rect.translated(3, 3), 10.0, 10.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(colors['shadow_dark'])
        painter.drawPath(shadow_path)

        light_path = QPainterPath()
        light_path.addRoundedRect(outer_rect.translated(-1, -1), 10.0, 10.0)
        painter.setBrush(colors['shadow_light'])
        painter.drawPath(light_path)

        card_path = QPainterPath()
        card_path.addRoundedRect(outer_rect, 10.0, 10.0)
        painter.setBrush(QColor(colors['bg_card']))
        painter.drawPath(card_path)

        inner_rect = QRectF(
            outer_rect.x() + 1,
            outer_rect.y() + 1,
            outer_rect.width() - 2,
            outer_rect.height() - 2,
        )
        border_path = QPainterPath()
        border_path.addRoundedRect(inner_rect, 9.0, 9.0)
        painter.setPen(QPen(QColor(colors['border_light']), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)


# ============================================================================
# Interactive Vector Canvas - Fixed Quiver.set_width
# ============================================================================

class InteractiveVectorCanvas(FigureCanvas):
    """Canvas تعاملی برای نمایش بردارها با مدیریت بهینه Artist‌ها."""

    vector_clicked = pyqtSignal(int)
    vector_right_clicked = pyqtSignal(int)

    def __init__(
        self,
        theme: UltraHighContrastTheme,
        parent: Optional[QWidget] = None,
        width: float = 5,
        height: float = 5,
        dpi: int = 100,
    ) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        self._theme: UltraHighContrastTheme = theme
        self._vectors: List[Vector2D] = []
        self._resultant: Optional[Vector2D] = None
        self._selected: int = -1

        # Cache for artists
        self._vector_artists: List[Dict[str, Any]] = []
        self._resultant_artist: Optional[Dict[str, Any]] = None
        self._grid_artists: Dict[str, Optional[Line2D]] = {
            'hline': None,
            'vline': None,
        }

        self._apply_theme()
        self._setup_grid_artists()
        self.fig.tight_layout(pad=1.5)

        self.setMinimumSize(300, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mpl_connect('button_press_event', self._on_click)

    def _apply_theme(self) -> None:
        colors = self._theme.colors
        self.ax.set_facecolor(colors['bg_card'])
        self.fig.patch.set_facecolor(colors['bg_card'])
        self.ax.tick_params(colors=colors['text_secondary'], labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(colors['text_secondary'])
        self.ax.set_aspect('equal')

    def _setup_grid_artists(self) -> None:
        """
        راه‌اندازی المان‌های ثابت نمودار.
        استفاده از متد remove() خود artist به جای ArtistList.remove()
        """
        colors = self._theme.colors

        for key, artist in self._grid_artists.items():
            if artist is not None:
                try:
                    artist.remove()
                except (ValueError, AttributeError):
                    pass
            self._grid_artists[key] = None

        self._grid_artists['hline'] = self.ax.axhline(
            0, color=colors['text_secondary'],
            linewidth=0.5, alpha=0.3,
        )
        self._grid_artists['vline'] = self.ax.axvline(
            0, color=colors['text_secondary'],
            linewidth=0.5, alpha=0.3,
        )

        self.ax.grid(True, linestyle='--', alpha=0.3, color=colors['border_light'])

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        self._apply_theme()
        self._setup_grid_artists()
        self._full_redraw()
        self.draw_idle()

    def set_data(
        self,
        vectors: List[Vector2D],
        resultant: Optional[Vector2D] = None,
        selected: int = -1,
    ) -> None:
        old_count = len(self._vector_artists)
        new_count = len(vectors)

        self._vectors = vectors
        self._resultant = resultant
        self._selected = selected

        # Always do full redraw when selection changes (for proper visual feedback)
        # or when vector count changes
        if new_count != old_count or selected != self._selected:
            self._full_redraw()
        else:
            self._update_all_artists()
            self._update_limits()

    def _remove_artist_safe(self, artist: Any) -> None:
        """حذف ایمن یک artist از نمودار."""
        if artist is not None:
            try:
                artist.remove()
            except (ValueError, AttributeError):
                pass

    def _full_redraw(self) -> None:
        """بازرسم کامل (در صورت تغییر تعداد بردارها یا انتخاب)."""
        # Remove old vector artists
        for artist_dict in self._vector_artists:
            for artist in artist_dict.values():
                self._remove_artist_safe(artist)

        # Remove old resultant artist
        if self._resultant_artist:
            for artist in self._resultant_artist.values():
                self._remove_artist_safe(artist)

        self._vector_artists.clear()
        self._resultant_artist = None

        # Create new artists
        self._create_vector_artists()
        self._create_resultant_artist()
        self._update_limits()
        self.draw_idle()

    def _create_vector_artists(self) -> None:
        """ایجاد Artist‌های جدید برای بردارها."""
        num_vectors = max(len(self._vectors), 1)
        colors = plt.cm.viridis(np.linspace(0.15, 0.85, num_vectors))

        for i, vector in enumerate(self._vectors):
            is_selected = (i == self._selected)
            color = '#ffcc00' if is_selected else colors[i]
            line_width = 0.016 if is_selected else 0.01
            head_width = 6 if is_selected else 4

            quiver = self.ax.quiver(
                0, 0, vector.x, vector.y,
                angles='xy', scale_units='xy', scale=1,
                color=color, width=line_width,
                headwidth=head_width, headlength=head_width + 1,
                picker=True, pickradius=6,
            )

            point = self.ax.plot(
                vector.x, vector.y, 'o',
                color=color,
                markersize=10 if is_selected else 6,
                markeredgecolor='white' if is_selected else color,
                markeredgewidth=1.5 if is_selected else 0,
            )[0]

            self._vector_artists.append({
                'quiver': quiver,
                'point': point,
                'color': color,
            })

    def _create_resultant_artist(self) -> None:
        """ایجاد Artist برای بردار برآیند."""
        if self._resultant and (self._resultant.x != 0 or self._resultant.y != 0):
            quiver = self.ax.quiver(
                0, 0, self._resultant.x, self._resultant.y,
                angles='xy', scale_units='xy', scale=1,
                color='#ff4444', width=0.018,
                headwidth=7, headlength=8,
            )
            self._resultant_artist = {'quiver': quiver}

    def _update_all_artists(self) -> None:
        """
        به‌روزرسانی تمام Artist‌ها بدون حذف کامل.
        فقط برای تغییرات کوچک در داده‌ها (بدون تغییر انتخاب).
        """
        for i, (artist_dict, vector) in enumerate(zip(self._vector_artists, self._vectors)):
            if 'quiver' in artist_dict and artist_dict['quiver'] is not None:
                quiver = artist_dict['quiver']
                quiver.set_UVC(vector.x, vector.y)

            if 'point' in artist_dict and artist_dict['point'] is not None:
                point = artist_dict['point']
                point.set_data([vector.x], [vector.y])

        if self._resultant and self._resultant_artist:
            artist = self._resultant_artist.get('quiver')
            if artist is not None:
                artist.set_UVC(self._resultant.x, self._resultant.y)

    def _update_limits(self) -> None:
        max_val = 1.0
        for v in self._vectors:
            max_val = max(max_val, abs(v.x), abs(v.y))
        if self._resultant:
            max_val = max(max_val, abs(self._resultant.x), abs(self._resultant.y))

        limit = max(max_val * 1.3, 2.0)
        self.ax.set_xlim(-limit, limit)
        self.ax.set_ylim(-limit, limit)

    def _on_click(self, event) -> None:
        if event.inaxes != self.ax or event.button is None:
            return

        min_dist: float = float('inf')
        closest: int = -1

        for i, vector in enumerate(self._vectors):
            distance = np.sqrt(
                (event.xdata - vector.x) ** 2 + (event.ydata - vector.y) ** 2
            )
            if distance < min_dist and distance < 0.7:
                min_dist = distance
                closest = i

        if closest >= 0:
            if event.button == 1:  # Left click
                self._selected = closest
                self._full_redraw()
                self.vector_clicked.emit(closest)
            elif event.button == 3:  # Right click
                self.vector_right_clicked.emit(closest)

    def to_base64(self, dpi: int = DEFAULT_GRAPH_DPI) -> str:
        buffer = io.BytesIO()
        self.fig.savefig(
            buffer, format='png', dpi=dpi,
            bbox_inches='tight', pad_inches=0.06,
            facecolor=self.fig.get_facecolor(),
        )
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')

    def cleanup(self) -> None:
        safe_disconnect(self.vector_clicked)
        safe_disconnect(self.vector_right_clicked)
        plt.close(self.fig)


# ============================================================================
# Multi-Graph Canvas
# ============================================================================

@dataclass
class GraphItem:
    """یک آیتم نمودار (تابع، خط، یا نقطه)."""
    type: str
    label: str
    color: str
    data: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    artist: Optional[Line2D] = None


class MultiGraphCanvas(FigureCanvas):
    """Canvas پیشرفته برای رسم چندین نمودار همزمان با مدیریت Artist."""

    def __init__(
        self,
        theme: UltraHighContrastTheme,
        parent: Optional[QWidget] = None,
        width: float = 6,
        height: float = 5,
        dpi: int = 100,
    ) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        self._theme: UltraHighContrastTheme = theme
        self._items: List[GraphItem] = []

        self._apply_theme()
        self.fig.tight_layout(pad=1.5)
        self.setMinimumSize(350, 300)

    def _apply_theme(self) -> None:
        colors = self._theme.colors
        self.ax.set_facecolor(colors['bg_card'])
        self.fig.patch.set_facecolor(colors['bg_card'])
        self.ax.grid(True, linestyle='--', alpha=0.3, color=colors['border_light'])
        self.ax.tick_params(colors=colors['text_secondary'], labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(colors['text_secondary'])
        self.ax.axhline(0, color=colors['text_secondary'], linewidth=0.3, alpha=0.2)
        self.ax.axvline(0, color=colors['text_secondary'], linewidth=0.3, alpha=0.2)

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        self._apply_theme()
        for item in self._items:
            if item.artist is not None:
                try:
                    item.artist.remove()
                except (ValueError, AttributeError):
                    pass
                item.artist = None
        self._redraw_all()

    def add_item(self, item: GraphItem) -> None:
        self._items.append(item)
        self._draw_single_item(item)
        self.draw_idle()

    def remove_item(self, index: int) -> None:
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            if item.artist is not None:
                try:
                    item.artist.remove()
                except (ValueError, AttributeError):
                    pass
            self.draw_idle()

    def toggle_item(self, index: int) -> None:
        if 0 <= index < len(self._items):
            item = self._items[index]
            item.visible = not item.visible
            if item.artist is not None:
                item.artist.set_visible(item.visible)
            self.draw_idle()

    def clear_items(self) -> None:
        for item in self._items:
            if item.artist is not None:
                try:
                    item.artist.remove()
                except (ValueError, AttributeError):
                    pass
        self._items.clear()
        self.draw_idle()

    def get_items(self) -> List[GraphItem]:
        return self._items

    def _draw_single_item(self, item: GraphItem) -> None:
        if not item.visible:
            return
        try:
            if item.type == 'function':
                item.artist = self._create_function_artist(item)
            elif item.type == 'line':
                item.artist = self._create_line_artist(item)
            elif item.type == 'point':
                item.artist = self._create_point_artist(item)
        except Exception as e:
            logger.warning(f"خطا در رسم {item.label}: {e}")

    def _redraw_all(self) -> None:
        self.ax.clear()
        self._apply_theme()

        for item in self._items:
            self._draw_single_item(item)

        if self._items:
            self.ax.legend(loc='upper right', fontsize=6, framealpha=0.5)

        self.draw_idle()

    @staticmethod
    def _safe_eval_function(func_str: str) -> Optional[np.ndarray]:
        try:
            x = np.linspace(-10, 10, GRAPH_RESOLUTION)
            safe_namespace: Dict[str, Any] = {
                "x": x,
                "np": np,
                "sin": np.sin,
                "cos": np.cos,
                "tan": np.tan,
                "log": np.log,
                "exp": np.exp,
                "sqrt": np.sqrt,
                "abs": np.abs,
                "pi": np.pi,
                "e": np.e,
            }
            sanitized = func_str.replace('^', '**')
            y = eval(sanitized, {"__builtins__": {}}, safe_namespace)
            return np.clip(np.asarray(y, dtype=np.float64), -1e6, 1e6)
        except Exception as e:
            logger.error(f"خطا در ارزیابی تابع '{func_str}': {e}")
            return None

    def _create_function_artist(self, item: GraphItem) -> Optional[Line2D]:
        func_str = item.data.get('function', '')
        if not func_str:
            return None

        y = self._safe_eval_function(func_str)
        if y is not None:
            x = np.linspace(-10, 10, GRAPH_RESOLUTION)
            return self.ax.plot(x, y, color=item.color, linewidth=2,
                              label=item.label)[0]
        return None

    def _create_line_artist(self, item: GraphItem) -> Optional[Line2D]:
        slope = item.data.get('slope', 0)
        intercept = item.data.get('intercept', 0)
        x = np.array([-10, 10])
        return self.ax.plot(
            x, slope * x + intercept,
            color=item.color, linewidth=2, label=item.label,
        )[0]

    def _create_point_artist(self, item: GraphItem) -> Optional[Line2D]:
        x_coord = item.data.get('x', 0)
        y_coord = item.data.get('y', 0)
        return self.ax.plot(
            x_coord, y_coord, 'o',
            color=item.color, markersize=10, label=item.label,
        )[0]

    def to_pixmap(self, dpi: int = DEFAULT_GRAPH_DPI) -> QPixmap:
        buffer = io.BytesIO()
        self.fig.savefig(
            buffer, format='png', dpi=dpi,
            bbox_inches='tight', pad_inches=0.06,
            facecolor=self.fig.get_facecolor(),
        )
        buffer.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.read(), 'PNG')
        return pixmap

    def cleanup(self) -> None:
        self.clear_items()
        plt.close(self.fig)


# ============================================================================
# Graph Generator Thread
# ============================================================================

class GraphGeneratorThread(QThread):
    """تولید نمودار در Thread جداگانه با اعتبارسنجی امنیتی."""

    graph_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        code: str,
        theme: UltraHighContrastTheme,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._code: str = code
        self._theme: UltraHighContrastTheme = theme

    def run(self) -> None:
        try:
            match = re.search(
                r'```(?:python_graph|python)\n(.*?)```',
                self._code,
                re.DOTALL,
            )
            if not match:
                raise ValueError(
                    "بلوک کد پیدا نشد. لطفاً کد را داخل ```python_graph ... ``` قرار دهید."
                )

            user_code = match.group(1).strip()

            is_safe, error_message = validate_code_safety(user_code)
            if not is_safe:
                raise ValueError(f"کد نامعتبر است:\n{error_message}")

            colors = self._theme.colors

            fig = Figure(figsize=(7, 5), dpi=DEFAULT_GRAPH_DPI)
            fig.patch.set_facecolor(colors['bg_card'])
            ax = fig.add_subplot(111)
            ax.set_facecolor(colors['bg_card'])
            ax.tick_params(colors=colors['text_secondary'], labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(colors['text_secondary'])

            safe_namespace: Dict[str, Any] = {
                'np': np,
                'ax': ax,
                'fig': fig,
                'linspace': np.linspace,
                'array': np.array,
                'arange': np.arange,
                'sin': np.sin,
                'cos': np.cos,
                'tan': np.tan,
                'log': np.log,
                'exp': np.exp,
                'sqrt': np.sqrt,
                'abs': np.abs,
                'pi': np.pi,
                'e': np.e,
            }

            exec(user_code, {"__builtins__": {}}, safe_namespace)

            canvas_agg = FigureCanvasAgg(fig)
            canvas_agg.draw()

            buffer = io.BytesIO()
            fig.savefig(
                buffer, format='png',
                bbox_inches='tight', pad_inches=0.06,
                facecolor=colors['bg_card'],
            )
            buffer.seek(0)
            b64_data = base64.b64encode(buffer.read()).decode('utf-8')
            buffer.close()

            plt.close(fig)

            self.graph_ready.emit(b64_data)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def cleanup(self) -> None:
        safe_disconnect(self.graph_ready)
        safe_disconnect(self.error_occurred)


# ============================================================================
# Validated Input with Tooltip Feedback
# ============================================================================

class ValidatedLineEdit(QLineEdit):
    """فیلد ورودی با اعتبارسنجی لحظه‌ای و نمایش Tooltip."""

    validation_changed = pyqtSignal(bool, str)

    def __init__(
        self,
        min_val: float = -MAX_VECTOR_VALUE,
        max_val: float = MAX_VECTOR_VALUE,
        decimals: int = 2,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._min_val = min_val
        self._max_val = max_val
        self._is_valid = True

        validator = QDoubleValidator(min_val, max_val, decimals)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(validator)

        self.setFont(QFont("Arial", 13))
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumHeight(28)

        self.textChanged.connect(self._validate)
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._hide_tooltip)

    def _validate(self, text: str) -> None:
        if not text or text in ('-', '+', '.'):
            self._set_valid(True)
            return

        try:
            value = float(text)
            if self._min_val <= value <= self._max_val:
                self._set_valid(True)
            else:
                self._set_valid(
                    False,
                    f"مقدار باید بین {self._min_val} و {self._max_val} باشد"
                )
        except ValueError:
            self._set_valid(False, "لطفاً یک عدد معتبر وارد کنید")

    def _set_valid(self, valid: bool, message: str = "") -> None:
        if valid != self._is_valid:
            self._is_valid = valid
            self.setProperty("valid", str(valid).lower())
            self.style().unpolish(self)
            self.style().polish(self)
            self.validation_changed.emit(valid, message)

            if not valid and message:
                self._show_tooltip(message)

    def _show_tooltip(self, message: str) -> None:
        QToolTip.showText(
            self.mapToGlobal(QPoint(0, self.height() + 5)),
            message,
            self,
        )
        self._tooltip_timer.start(TOOLTIP_DELAY)

    def _hide_tooltip(self) -> None:
        QToolTip.hideText()

    def is_valid(self) -> bool:
        return self._is_valid

    def cleanup(self) -> None:
        safe_disconnect(self.validation_changed)
        self._tooltip_timer.stop()


# ============================================================================
# Preview Dialog
# ============================================================================

class PreviewDialog(QDialog):
    """دیالوگ پیش‌نمایش و ذخیره نمودار."""

    def __init__(self, pixmap: QPixmap, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap = pixmap
        self.setWindowTitle("پیش‌نمایش نمودار")
        self.setMinimumSize(480, 400)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        image_label = QLabel()
        scaled_pixmap = self._pixmap.scaled(
            700, 500,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll_area = QScrollArea()
        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)

        button_box = QDialogButtonBox()
        button_box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        save_button = QPushButton("💾 ذخیره تصویر")
        save_button.setFont(QFont("B Nazanin", 13, QFont.Weight.Bold))
        save_button.setMinimumHeight(36)
        save_button.clicked.connect(self._save)
        button_box.addButton(save_button, QDialogButtonBox.ButtonRole.ActionRole)

        close_button = QPushButton("بستن")
        close_button.setFont(QFont("B Nazanin", 13, QFont.Weight.Bold))
        close_button.setMinimumHeight(36)
        close_button.clicked.connect(self.close)
        button_box.addButton(close_button, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره تصویر", "نمودار.png", "PNG (*.png)",
        )
        if path:
            self._pixmap.save(path, 'PNG')
            QMessageBox.information(self, "موفقیت", "تصویر با موفقیت ذخیره شد.")


# ============================================================================
# Vector Tab - با ScrollArea و Tooltip و فاصله‌گذاری بهبود یافته
# ============================================================================

class VectorTab(QWidget):
    """تب مدیریت بردارها و برآیند با UX بهبود یافته و فاصله‌گذاری مناسب."""

    def __init__(
        self,
        engine: MathEngine,
        theme: UltraHighContrastTheme,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._engine: MathEngine = engine
        self._theme: UltraHighContrastTheme = theme
        self._vectors: List[Vector2D] = []
        self._resultant: Optional[Vector2D] = None
        self._selected: int = -1

        self._cleanup_callbacks: List[Callable] = []

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()

    def _create_button(
        self,
        text: str,
        callback,
        accent: bool = False,
        obj_name: str = "",
    ) -> QPushButton:
        button = QPushButton(text)
        if accent:
            button.setObjectName("accentBtn")
        elif obj_name:
            button.setObjectName(obj_name)
        button.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(BUTTON_MIN_HEIGHT + 4)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        button.clicked.connect(callback)
        return button

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(10)

        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        control_scroll.setMinimumWidth(CONTROL_PANEL_MIN_WIDTH)
        control_scroll.setMaximumWidth(CONTROL_PANEL_MAX_WIDTH)
        control_scroll.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        control_scroll.setFrameShape(QFrame.Shape.NoFrame)

        control_frame = QFrame()
        control_frame.setObjectName("card")
        control_frame.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(GROUP_SPACING)

        # عنوان
        title = QLabel("🎯 مدیریت بردارها")
        title.setFont(QFont("B Nazanin", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self._theme.colors['text_accent']}; padding: 4px 0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(title)

        # گروه مختصات - با padding مناسب برای عدم بریدگی عنوان
        input_group = QGroupBox("مختصات بردار جدید")
        input_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        input_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        grid = QGridLayout(input_group)
        grid.setSpacing(8)
        grid.setContentsMargins(10, 24, 10, 10)

        grid.addWidget(QLabel("طول:"), 0, 0)
        self._x_input = ValidatedLineEdit(parent=self)
        self._x_input.returnPressed.connect(lambda: self._y_input.setFocus())
        self._cleanup_callbacks.append(self._x_input.cleanup)
        grid.addWidget(self._x_input, 0, 1)

        grid.addWidget(QLabel("عرض:"), 1, 0)
        self._y_input = ValidatedLineEdit(parent=self)
        self._y_input.returnPressed.connect(self._add_vector)
        self._cleanup_callbacks.append(self._y_input.cleanup)
        grid.addWidget(self._y_input, 1, 1)

        control_layout.addWidget(input_group)

        # دکمه‌های عملیات
        button_grid = QGridLayout()
        button_grid.setSpacing(6)
        button_grid.setContentsMargins(0, 4, 0, 4)

        button_grid.addWidget(
            self._create_button("➕ افزودن", self._add_vector, accent=True),
            0, 0,
        )
        button_grid.addWidget(
            self._create_button("🔗 برآیند", self._calculate_resultant, accent=True),
            0, 1,
        )
        button_grid.addWidget(
            self._create_button("✏️ ویرایش", self._edit_vector),
            1, 0,
        )
        button_grid.addWidget(
            self._create_button("🗑️ حذف", self._delete_vector, obj_name="dangerBtn"),
            1, 1,
        )
        button_grid.addWidget(
            self._create_button("🔄 پاک کردن همه", self._clear_vectors),
            2, 0, 1, 2,
        )
        control_layout.addLayout(button_grid)

        # لیست بردارها
        self._vector_list = QListWidget()
        self._vector_list.setMaximumHeight(120)
        self._vector_list.setMinimumHeight(60)
        self._vector_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._vector_list.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._vector_list.itemClicked.connect(self._on_list_clicked)
        self._vector_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._vector_list.customContextMenuRequested.connect(self._on_list_context_menu)
        control_layout.addWidget(self._vector_list)

        # اطلاعات
        self._info_label = QLabel("بدون بردار")
        self._info_label.setFont(QFont("B Nazanin", 11))
        self._info_label.setWordWrap(True)
        self._info_label.setMinimumHeight(36)
        self._info_label.setStyleSheet(
            f"color: {self._theme.colors['text_secondary']}; padding: 4px;",
        )
        control_layout.addWidget(self._info_label)

        # دکمه ذخیره
        control_layout.addWidget(
            self._create_button("📥 ذخیره تصویر", self._export_image),
        )
        control_layout.addStretch()

        control_scroll.setWidget(control_frame)
        main_layout.addWidget(control_scroll)

        # Canvas
        canvas_frame = CanvasFrame(self._theme)
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        self._canvas = InteractiveVectorCanvas(self._theme, self)
        self._canvas.vector_clicked.connect(self._on_canvas_clicked)
        self._canvas.vector_right_clicked.connect(self._on_canvas_right_clicked)
        self._cleanup_callbacks.append(self._canvas.cleanup)
        canvas_layout.addWidget(self._canvas)

        main_layout.addWidget(canvas_frame, 1)
        self.setLayout(main_layout)

        self._refresh_ui()

    def _add_vector(self) -> None:
        if not self._x_input.is_valid() or not self._y_input.is_valid():
            return

        try:
            x = float(self._x_input.text() or 0)
            y = float(self._y_input.text() or 0)
        except ValueError:
            return

        if len(self._vectors) >= MAX_VECTOR_COUNT:
            QToolTip.showText(
                self._x_input.mapToGlobal(QPoint(0, self._x_input.height() + 5)),
                f"حداکثر {MAX_VECTOR_COUNT} بردار مجاز است",
                self._x_input,
            )
            return

        self._vectors.append(self._engine.create_vector(x, y))
        self._resultant = None
        self._selected = -1

        self._x_input.clear()
        self._y_input.clear()
        self._x_input.setFocus()

        self._refresh_ui()

    def _calculate_resultant(self) -> None:
        if not self._vectors:
            QMessageBox.information(self, "توجه", "برداری برای محاسبه وجود ندارد!")
            return

        self._resultant = self._engine.sum_vectors(self._vectors)
        self._refresh_ui()

    def _edit_vector(self) -> None:
        if self._selected < 0 or self._selected >= len(self._vectors):
            QMessageBox.information(self, "توجه", "ابتدا یک بردار را انتخاب کنید!")
            return

        vector = self._vectors[self._selected]
        self._x_input.setText(str(vector.x))
        self._y_input.setText(str(vector.y))
        self._delete_selected()

    def _delete_vector(self) -> None:
        if self._selected < 0 or self._selected >= len(self._vectors):
            QMessageBox.information(self, "توجه", "ابتدا یک بردار را انتخاب کنید!")
            return

        self._delete_selected()

    def _delete_selected(self) -> None:
        if 0 <= self._selected < len(self._vectors):
            self._vectors.pop(self._selected)
            self._resultant = None
            self._selected = -1
            self._refresh_ui()

    def _clear_vectors(self) -> None:
        if not self._vectors:
            return

        reply = QMessageBox.question(
            self, "تأیید",
            "آیا از پاک کردن همه بردارها اطمینان دارید؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._vectors.clear()
            self._resultant = None
            self._selected = -1
            self._refresh_ui()

    def _on_canvas_clicked(self, index: int) -> None:
        self._selected = index
        self._refresh_ui()

    def _on_canvas_right_clicked(self, index: int) -> None:
        self._selected = index
        self._refresh_ui()

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.addAction("✏️ ویرایش", self._edit_vector)
        menu.addAction("🗑️ حذف", self._delete_vector)
        menu.exec(self._canvas.mapToGlobal(self._canvas.rect().center()))

    def _on_list_clicked(self, item: QListWidgetItem) -> None:
        self._selected = self._vector_list.row(item)
        self._refresh_ui()

    def _on_list_context_menu(self, position: QPoint) -> None:
        item = self._vector_list.itemAt(position)
        if item is None:
            return

        self._selected = self._vector_list.row(item)
        self._refresh_ui()

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.addAction("✏️ ویرایش", self._edit_vector)
        menu.addAction("🗑️ حذف", self._delete_vector)
        menu.exec(self._vector_list.mapToGlobal(position))

    def _refresh_ui(self) -> None:
        self._vector_list.clear()

        for i, vector in enumerate(self._vectors):
            item_text = (
                f"بردار {i + 1}: طول={vector.y:.2f}، عرض={vector.x:.2f} | "
                f"اندازه={vector.magnitude:.2f} | زاویه={vector.angle_degrees:.1f}°"
            )
            item = QListWidgetItem(item_text)
            item.setFont(QFont("Arial", 12))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            if i == self._selected:
                item.setSelected(True)
            self._vector_list.addItem(item)

        if self._resultant:
            resultant = self._resultant
            self._info_label.setText(
                f"برآیند: طول={resultant.y:.2f}، عرض={resultant.x:.2f} | "
                f"اندازه={resultant.magnitude:.2f} | زاویه={resultant.angle_degrees:.1f}° | "
                f"{len(self._vectors)} بردار"
            )
        else:
            self._info_label.setText(
                f"تعداد: {len(self._vectors)} بردار | برای محاسبه برآیند کلیک کنید",
            )

        self._canvas.set_data(self._vectors, self._resultant, self._selected)

    def _export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره تصویر", "نمودار_بردارها.png", "PNG (*.png)",
        )
        if path:
            try:
                pixmap = QPixmap()
                pixmap.loadFromData(
                    base64.b64decode(self._canvas.to_base64()), 'PNG',
                )
                pixmap.save(path, 'PNG')
                QMessageBox.information(self, "موفقیت", "تصویر با موفقیت ذخیره شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", str(e))

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        self._canvas.update_theme(theme)
        canvas_parent = self._canvas.parent()
        if isinstance(canvas_parent, CanvasFrame):
            canvas_parent.update_theme(theme)

    def cleanup(self) -> None:
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception:
                pass


# ============================================================================
# Graph Tab
# ============================================================================

class GraphTab(QWidget):
    """تب رسم چندین نمودار همزمان با مدیریت حافظه بهبود یافته و فاصله‌گذاری مناسب."""

    def __init__(
        self,
        theme: UltraHighContrastTheme,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._theme: UltraHighContrastTheme = theme
        self._thread: Optional[GraphGeneratorThread] = None
        self._pixmap: Optional[QPixmap] = None
        self._color_index: int = 0

        self._cleanup_callbacks: List[Callable] = []

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()

    def _next_color(self) -> str:
        color = GRAPH_COLORS[self._color_index % len(GRAPH_COLORS)]
        self._color_index += 1
        return color

    def _create_button(
        self,
        text: str,
        callback,
        accent: bool = False,
        obj_name: str = "",
    ) -> QPushButton:
        button = QPushButton(text)
        if accent:
            button.setObjectName("accentBtn")
        elif obj_name:
            button.setObjectName(obj_name)
        button.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(BUTTON_MIN_HEIGHT + 4)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        button.clicked.connect(callback)
        return button

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(10)

        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        control_scroll.setMinimumWidth(CONTROL_PANEL_MIN_WIDTH)
        control_scroll.setMaximumWidth(CONTROL_PANEL_MAX_WIDTH)
        control_scroll.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        control_scroll.setFrameShape(QFrame.Shape.NoFrame)

        control_frame = QFrame()
        control_frame.setObjectName("card")
        control_frame.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(GROUP_SPACING)

        # عنوان
        title = QLabel("📈 رسم چند نمودار")
        title.setFont(QFont("B Nazanin", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self._theme.colors['text_accent']}; padding: 4px 0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.addWidget(title)

        # گروه تابع
        func_group = QGroupBox("📉 افزودن تابع f(x)")
        func_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        func_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        func_layout = QVBoxLayout(func_group)
        func_layout.setSpacing(8)
        func_layout.setContentsMargins(10, 24, 10, 10)

        self._func_input = QLineEdit()
        self._func_input.setPlaceholderText("sin(x) | x^2 + 2x + 1 | x^3 - x")
        self._func_input.setFont(QFont("Arial", 13))
        self._func_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._func_input.setMinimumHeight(28)
        self._func_input.returnPressed.connect(self._add_function)
        func_layout.addWidget(self._func_input)

        func_layout.addWidget(
            self._create_button("📈 افزودن تابع", self._add_function, accent=True),
        )
        control_layout.addWidget(func_group)

        # گروه خط
        line_group = QGroupBox("📏 افزودن خط y = mx + b")
        line_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        line_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        line_layout = QGridLayout(line_group)
        line_layout.setSpacing(8)
        line_layout.setContentsMargins(10, 24, 10, 10)

        line_layout.addWidget(QLabel("شیب:"), 0, 0)
        self._slope_input = ValidatedLineEdit(-100, 100, parent=self)
        self._slope_input.setText("1")
        self._cleanup_callbacks.append(self._slope_input.cleanup)
        line_layout.addWidget(self._slope_input, 0, 1)

        line_layout.addWidget(QLabel("عرض از مبدأ:"), 1, 0)
        self._intercept_input = ValidatedLineEdit(-100, 100, parent=self)
        self._intercept_input.setText("0")
        self._cleanup_callbacks.append(self._intercept_input.cleanup)
        line_layout.addWidget(self._intercept_input, 1, 1)

        line_layout.addWidget(
            self._create_button("📏 افزودن خط", self._add_line, accent=True),
            2, 0, 1, 2,
        )
        control_layout.addWidget(line_group)

        # گروه نقطه
        point_group = QGroupBox("📍 افزودن نقطه")
        point_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        point_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        point_layout = QGridLayout(point_group)
        point_layout.setSpacing(8)
        point_layout.setContentsMargins(10, 24, 10, 10)

        point_layout.addWidget(QLabel("طول (x):"), 0, 0)
        self._point_x_input = ValidatedLineEdit(-100, 100, parent=self)
        self._cleanup_callbacks.append(self._point_x_input.cleanup)
        point_layout.addWidget(self._point_x_input, 0, 1)

        point_layout.addWidget(QLabel("عرض (y):"), 1, 0)
        self._point_y_input = ValidatedLineEdit(-100, 100, parent=self)
        self._cleanup_callbacks.append(self._point_y_input.cleanup)
        point_layout.addWidget(self._point_y_input, 1, 1)

        point_layout.addWidget(
            self._create_button("📍 افزودن نقطه", self._add_point, accent=True),
            2, 0, 1, 2,
        )
        control_layout.addWidget(point_group)

        # لیست نمودارها
        list_group = QGroupBox("📋 نمودارهای رسم شده")
        list_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        list_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        list_layout = QVBoxLayout(list_group)
        list_layout.setSpacing(8)
        list_layout.setContentsMargins(10, 24, 10, 10)

        self._graph_list = QListWidget()
        self._graph_list.setMaximumHeight(110)
        self._graph_list.setMinimumHeight(50)
        self._graph_list.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._graph_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._graph_list.customContextMenuRequested.connect(self._on_graph_menu)
        list_layout.addWidget(self._graph_list)

        list_buttons = QHBoxLayout()
        list_buttons.setSpacing(6)
        list_buttons.addWidget(
            self._create_button("👁️ نمایش/مخفی", self._toggle_selected),
        )
        list_buttons.addWidget(
            self._create_button("🗑️ حذف انتخاب", self._remove_selected, obj_name="dangerBtn"),
        )
        list_layout.addLayout(list_buttons)

        list_layout.addWidget(
            self._create_button("🔄 پاک کردن همه", self._clear_graphs),
        )
        control_layout.addWidget(list_group)

        # گروه کد
        code_group = QGroupBox("💻 کد پایتون")
        code_group.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        code_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        code_layout = QVBoxLayout(code_group)
        code_layout.setSpacing(8)
        code_layout.setContentsMargins(10, 24, 10, 10)

        self._code_editor = QTextEdit()
        self._code_editor.setPlaceholderText(
            "import numpy as np\n"
            "x = np.linspace(-10, 10, 500)\n"
            "ax.plot(x, np.sin(x), color='red', label='sin(x)')\n"
            "ax.legend()"
        )
        self._code_editor.setFont(QFont("Consolas", 10))
        self._code_editor.setMaximumHeight(80)
        self._code_editor.setMinimumHeight(50)
        self._code_editor.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        code_layout.addWidget(self._code_editor)

        self._run_button = self._create_button(
            "▶️ اجرای کد", self._run_code, accent=True,
        )
        code_layout.addWidget(self._run_button)
        control_layout.addWidget(code_group)

        # دکمه‌های پایین
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)
        action_layout.addWidget(
            self._create_button("📥 ذخیره تصویر", self._export_image),
        )
        action_layout.addWidget(
            self._create_button("🔍 پیش‌نمایش", self._preview, accent=True),
        )
        control_layout.addLayout(action_layout)

        # وضعیت
        self._status_label = QLabel("")
        self._status_label.setFont(QFont("B Nazanin", 11))
        self._status_label.setMinimumHeight(24)
        self._status_label.setStyleSheet(
            f"color: {self._theme.colors['success']};",
        )
        self._status_label.hide()
        control_layout.addWidget(self._status_label)

        control_layout.addStretch()
        control_scroll.setWidget(control_frame)
        main_layout.addWidget(control_scroll)

        # Canvas
        canvas_frame = CanvasFrame(self._theme)
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(4, 4, 4, 4)

        self._canvas = MultiGraphCanvas(self._theme, self)
        self._cleanup_callbacks.append(self._canvas.cleanup)
        canvas_layout.addWidget(self._canvas)

        main_layout.addWidget(canvas_frame, 1)
        self.setLayout(main_layout)

    def _show_status(self, message: str, is_error: bool = False) -> None:
        self._status_label.setText(message)
        self._status_label.setStyleSheet(
            f"color: {self._theme.colors['error' if is_error else 'success']};",
        )
        self._status_label.show()
        QTimer.singleShot(2500, self._status_label.hide)

    def _add_function(self) -> None:
        func_text = self._func_input.text().strip()
        if not func_text:
            QToolTip.showText(
                self._func_input.mapToGlobal(QPoint(0, self._func_input.height() + 5)),
                "لطفاً یک تابع معتبر وارد کنید",
                self._func_input,
            )
            return

        test_result = MultiGraphCanvas._safe_eval_function(func_text)
        if test_result is None:
            QToolTip.showText(
                self._func_input.mapToGlobal(QPoint(0, self._func_input.height() + 5)),
                "تابع نامعتبر است! لطفاً عبارت را بررسی کنید",
                self._func_input,
            )
            return

        color = self._next_color()
        item = GraphItem(
            type='function',
            label=f'f(x)={func_text}',
            color=color,
            data={'function': func_text},
        )
        self._canvas.add_item(item)
        self._refresh_list()
        self._func_input.clear()
        self._show_status(f"✅ تابع {func_text} افزوده شد")

    def _add_line(self) -> None:
        if not self._slope_input.is_valid() or not self._intercept_input.is_valid():
            return

        try:
            slope = float(self._slope_input.text() or 0)
            intercept = float(self._intercept_input.text() or 0)
        except ValueError:
            return

        color = self._next_color()
        item = GraphItem(
            type='line',
            label=f'y={slope}x+{intercept}',
            color=color,
            data={'slope': slope, 'intercept': intercept},
        )
        self._canvas.add_item(item)
        self._refresh_list()
        self._show_status(f"✅ خط y={slope}x+{intercept} افزوده شد")

    def _add_point(self) -> None:
        if not self._point_x_input.is_valid() or not self._point_y_input.is_valid():
            return

        try:
            x = float(self._point_x_input.text() or 0)
            y = float(self._point_y_input.text() or 0)
        except ValueError:
            return

        color = self._next_color()
        item = GraphItem(
            type='point',
            label=f'({x},{y})',
            color=color,
            data={'x': x, 'y': y},
        )
        self._canvas.add_item(item)
        self._refresh_list()
        self._show_status(f"✅ نقطه ({x},{y}) افزوده شد")

    def _refresh_list(self) -> None:
        self._graph_list.clear()
        for item in self._canvas.get_items():
            prefix = "👁️ " if item.visible else "🚫 "
            text = f"{prefix}{item.label}"
            list_item = QListWidgetItem(text)
            list_item.setFont(QFont("Arial", 11))
            list_item.setForeground(QColor(item.color))
            list_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self._graph_list.addItem(list_item)

    def _toggle_selected(self) -> None:
        row = self._graph_list.currentRow()
        if row >= 0:
            self._canvas.toggle_item(row)
            self._refresh_list()

    def _remove_selected(self) -> None:
        row = self._graph_list.currentRow()
        if row >= 0:
            self._canvas.remove_item(row)
            self._refresh_list()

    def _clear_graphs(self) -> None:
        if self._canvas.get_items():
            self._canvas.clear_items()
            self._refresh_list()
            self._show_status("🧹 همه نمودارها پاک شدند")

    def _on_graph_menu(self, position: QPoint) -> None:
        row = self._graph_list.currentRow()
        if row < 0:
            return

        self._graph_list.setCurrentRow(row)
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.addAction("👁️ نمایش/مخفی", self._toggle_selected)
        menu.addAction("🗑️ حذف", self._remove_selected)
        menu.exec(self._graph_list.mapToGlobal(position))

    def _run_code(self) -> None:
        code = self._code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "خطا", "لطفاً کد را وارد کنید!")
            return

        is_safe, error_message = validate_code_safety(code)
        if not is_safe:
            QMessageBox.critical(
                self, "کد نامعتبر",
                f"کد شما حاوی موارد غیرمجاز است:\n\n{error_message}"
            )
            return

        self._run_button.setEnabled(False)
        self._run_button.setText("⏳ در حال اجرا...")

        if self._thread is not None:
            self._thread.cleanup()
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait()

        wrapped_code = f"```python_graph\n{code}\n```"
        self._thread = GraphGeneratorThread(wrapped_code, self._theme, self)
        self._thread.graph_ready.connect(self._on_graph_ready)
        self._thread.error_occurred.connect(self._on_graph_error)
        self._thread.start()

    @pyqtSlot(str)
    def _on_graph_ready(self, b64_data: str) -> None:
        self._run_button.setEnabled(True)
        self._run_button.setText("▶️ اجرای کد")

        self._pixmap = QPixmap()
        self._pixmap.loadFromData(base64.b64decode(b64_data), 'PNG')

        if not self._pixmap.isNull():
            self._show_status("✅ نمودار آماده است")
            self._preview()

    @pyqtSlot(str)
    def _on_graph_error(self, error_message: str) -> None:
        self._run_button.setEnabled(True)
        self._run_button.setText("▶️ اجرای کد")
        QMessageBox.critical(
            self, "خطا در اجرای کد",
            f"متأسفانه خطایی رخ داد:\n\n{error_message}",
        )

    def _export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره تصویر", "نمودار.png", "PNG (*.png)",
        )
        if path:
            try:
                pixmap = self._pixmap or self._canvas.to_pixmap()
                pixmap.save(path, 'PNG')
                QMessageBox.information(self, "موفقیت", "تصویر با موفقیت ذخیره شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", str(e))

    def _preview(self) -> None:
        pixmap = self._pixmap or self._canvas.to_pixmap()
        if pixmap and not pixmap.isNull():
            PreviewDialog(pixmap, self).exec()
        else:
            QMessageBox.information(self, "توجه", "نموداری برای پیش‌نمایش موجود نیست.")

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        self._canvas.update_theme(theme)
        canvas_parent = self._canvas.parent()
        if isinstance(canvas_parent, CanvasFrame):
            canvas_parent.update_theme(theme)

    def cleanup(self) -> None:
        if self._thread is not None:
            self._thread.cleanup()
            if self._thread.isRunning():
                self._thread.quit()
                self._thread.wait()

        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception:
                pass


# ============================================================================
# Animated Tab Widget
# ============================================================================

class AnimatedTabWidget(QTabWidget):
    """QTabWidget با انیمیشن fade بین تب‌ها."""

    def __init__(
        self,
        theme: UltraHighContrastTheme,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._theme: UltraHighContrastTheme = theme
        self._animating: bool = False
        self._previous_index: int = 0

        self.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setDocumentMode(True)

        self.currentChanged.connect(self._animate_transition)

    def _animate_transition(self, new_index: int) -> None:
        if self._animating:
            return

        old_widget = self.widget(self._previous_index)
        new_widget = self.widget(new_index)

        if not old_widget or not new_widget or old_widget == new_widget:
            self._previous_index = new_index
            return

        self._animating = True

        fade_out_effect = QGraphicsOpacityEffect()
        old_widget.setGraphicsEffect(fade_out_effect)

        anim_out = QPropertyAnimation(fade_out_effect, b"opacity")
        anim_out.setDuration(ANIMATION_DURATION)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        def on_fade_out_finished() -> None:
            old_widget.setGraphicsEffect(None)

            fade_in_effect = QGraphicsOpacityEffect()
            new_widget.setGraphicsEffect(fade_in_effect)

            anim_in = QPropertyAnimation(fade_in_effect, b"opacity")
            anim_in.setDuration(ANIMATION_DURATION + 30)
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

            def on_fade_in_finished() -> None:
                new_widget.setGraphicsEffect(None)
                self._animating = False

            anim_in.finished.connect(on_fade_in_finished)
            anim_in.start()

        anim_out.finished.connect(on_fade_out_finished)
        anim_out.start()

        self._previous_index = new_index

    def update_theme(self, theme: UltraHighContrastTheme) -> None:
        self._theme = theme
        colors = theme.colors
        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {colors['tab_inactive_bg']};
                color: {colors['tab_inactive_text']};
                padding: 8px 24px;
                margin: 4px 2px 0px 2px;
                border: 1px solid {colors['tab_shadow_light']};
                border-bottom: 1px solid {colors['tab_shadow_dark']};
                border-radius: 8px 8px 0 0;
                font: bold 14px 'B Nazanin';
                min-width: 140px;
            }}
            QTabBar::tab:selected {{
                background: {colors['tab_active_bg']};
                color: {colors['tab_active_text']};
                border-bottom: 3px solid {colors['tab_border_active']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {colors['tab_hover_bg']};
                color: {colors['text_primary']};
            }}
        """)


# ============================================================================
# Main Window
# ============================================================================

class VectorWindow(QWidget):
    """پنجره اصلی برنامه با مدیریت پیشرفته حافظه و UX بهبود یافته."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎯 بردار، مختصات و رسم نمودار")
        self.setMinimumSize(980, 640)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._engine = MathEngine()
        self._theme = UltraHighContrastTheme(ThemeMode.DARK)

        self._init_ui()
        self._init_shortcuts()
        self._apply_theme()
        self._center_on_screen()

        logger.info("پنجره بردار و نمودار نسخه ۱۰.۱.۲ راه‌اندازی شد")

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(10, 6, 10, 8)
        root_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 8, 8, 4)
        header_layout.setSpacing(10)

        title_label = QLabel("🎯 ابزارهای بردار و رسم نمودار")
        title_label.setFont(QFont("B Nazanin", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self._theme.colors['accent']};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self._theme_button = QPushButton("🌙")
        self._theme_button.setObjectName("iconBtn")
        self._theme_button.setFixedSize(36, 36)
        self._theme_button.setToolTip("تغییر تم (Ctrl+T)")
        self._theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_button.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self._theme_button)

        root_layout.addLayout(header_layout)

        self._tab_widget = AnimatedTabWidget(self._theme)

        self._vector_tab = VectorTab(self._engine, self._theme)
        self._graph_tab = GraphTab(self._theme)

        self._tab_widget.addTab(self._vector_tab, "🎯 بردار و مختصات")
        self._tab_widget.addTab(self._graph_tab, "📈 رسم نمودار")

        root_layout.addWidget(self._tab_widget, 1)

        status_label = QLabel(
            "Ctrl+1 بردار | Ctrl+2 نمودار | Ctrl+T تم | Ctrl+Q خروج"
        )
        status_label.setFont(QFont("B Nazanin", 9))
        status_label.setStyleSheet(
            f"color: {self._theme.colors['text_muted']}; padding: 2px;",
        )
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(status_label)

        self.setLayout(root_layout)

    def _init_shortcuts(self) -> None:
        QShortcut(
            QKeySequence("Ctrl+1"), self,
        ).activated.connect(lambda: self._tab_widget.setCurrentIndex(0))

        QShortcut(
            QKeySequence("Ctrl+2"), self,
        ).activated.connect(lambda: self._tab_widget.setCurrentIndex(1))

        QShortcut(
            QKeySequence("Ctrl+T"), self,
        ).activated.connect(self._toggle_theme)

        QShortcut(
            QKeySequence("Ctrl+Q"), self,
        ).activated.connect(self.close)

    def _toggle_theme(self) -> None:
        self._theme.toggle()
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self._theme.colors))
        self._theme_button.setText("🌙" if self._theme.is_dark else "☀️")
        self._tab_widget.update_theme(self._theme)
        self._vector_tab.update_theme(self._theme)
        self._graph_tab.update_theme(self._theme)

    def _center_on_screen(self) -> None:
        screen_geometry = self.screen().availableGeometry()
        target_width = min(screen_geometry.width(), 1100)
        target_height = min(screen_geometry.height(), 700)
        self.resize(int(target_width * 0.82), int(target_height * 0.82))

        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen_geometry.center())
        self.move(frame_geometry.topLeft())

    def closeEvent(self, event) -> None:
        self._vector_tab.cleanup()
        self._graph_tab.cleanup()
        event.accept()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    FontSystem.setup(app)

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    window = VectorWindow()
    window.show()
    sys.exit(app.exec())
