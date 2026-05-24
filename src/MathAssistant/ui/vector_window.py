# src/MathAssistant/ui/vector_window.py
"""
Vector & Graph Tools - ابزارهای بردار، مختصات و رسم نمودار
کاملاً فارسی | RTL | Ultra High Contrast | Multi-Graph | Animated

Author: AmirMohammad Ghasemzadeh
Version: 9.3.0 - Multi-Graph & Animated
"""

import sys
import io
import base64
import re
import logging
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass, field

import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QThread, QPoint, QRectF
)
from PyQt6.QtGui import (
    QFont, QDoubleValidator, QKeySequence,
    QShortcut, QColor, QPainter, QPixmap,
    QPainterPath, QPen, QBrush, QAction
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QTabWidget, QTabBar,
    QMessageBox, QApplication, QFrame,
    QSizePolicy, QGraphicsOpacityEffect, QStackedWidget,
    QGridLayout, QGroupBox, QFileDialog, QDialog,
    QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QColorDialog, QComboBox,
    QStyleFactory, QCheckBox, QSlider
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

# High-contrast color palette for multiple graphs
GRAPH_COLORS = [
    '#ff6b6b', '#4ecdc4', '#ffe66d', '#a78bfa', '#34d399',
    '#f472b6', '#60a5fa', '#fbbf24', '#818cf8', '#fb923c',
    '#22d3ee', '#f87171', '#a3e635', '#e879f9', '#38bdf8',
    '#facc15', '#2dd4bf', '#fb7185', '#8b5cf6', '#f97316',
]


# ============================================================================
# Ultra High Contrast Theme
# ============================================================================

class UltraHighContrastTheme(NeumorphicTheme):
    DARK = {
        **NeumorphicTheme.DARK,
        'text_primary': '#ffffff', 'text_secondary': '#d0d4e0',
        'text_muted': '#a8acb8', 'text_accent': '#c4c8ff',
        'bg_root': '#000000', 'bg_primary': '#080810',
        'bg_card': '#0c0c18', 'bg_input': '#050510',
        'border_light': '#2a2a40', 'border_dark': '#000000',
        'accent': '#8b7cf7', 'accent_hover': '#a094ff',
        'tab_inactive_bg': '#0c0c18', 'tab_inactive_text': '#a8acb8',
        'tab_active_bg': '#141428', 'tab_active_text': '#c4c8ff',
        'tab_hover_bg': '#101020', 'tab_border_active': '#8b7cf7',
        'tab_shadow_light': '#2a2a40', 'tab_shadow_dark': '#000000',
        'scrollbar_handle': '#2a2a40', 'shadow_dark': QColor(0,0,0,200),
        'shadow_light': QColor(40,40,60,180),
    }

    LIGHT = {
        **NeumorphicTheme.LIGHT,
        'text_primary': '#000000', 'text_secondary': '#1a1a2e',
        'text_muted': '#3a3a50', 'text_accent': '#3020a0',
        'bg_root': '#ffffff', 'bg_primary': '#f8f8fc',
        'bg_card': '#ffffff', 'bg_input': '#fdfdfe',
        'border_light': '#d0d0d8', 'border_dark': '#b8b8c0',
        'accent': '#6d5ed8', 'accent_hover': '#5a4cc0',
        'tab_inactive_bg': '#f0f0f5', 'tab_inactive_text': '#3a3a50',
        'tab_active_bg': '#ffffff', 'tab_active_text': '#3020a0',
        'tab_hover_bg': '#f8f8fc', 'tab_border_active': '#6d5ed8',
        'tab_shadow_light': '#ffffff', 'tab_shadow_dark': '#b8b8c0',
        'scrollbar_handle': '#c0c0c8', 'shadow_dark': QColor(180,180,190,200),
        'shadow_light': QColor(255,255,255,200),
    }

    def __init__(self, mode=ThemeMode.DARK):
        super().__init__(mode)
        self.colors = self.DARK if mode == ThemeMode.DARK else self.LIGHT

    def toggle(self):
        super().toggle()
        self.colors = self.DARK if self.mode == ThemeMode.DARK else self.LIGHT
        return self.mode


# ============================================================================
# Compact RTL Stylesheet
# ============================================================================

def compact_rtl_stylesheet(c: dict) -> str:
    return f"""
    * {{ font-family: 'B Nazanin', 'Tahoma', sans-serif; }}
    QWidget {{ background-color: {c['bg_root']}; color: {c['text_primary']}; font-size: 14px; }}

    QLineEdit {{
        background-color: {c['bg_input']}; color: {c['text_primary']};
        border: 2px solid {c['border_light']}; border-radius: 5px;
        padding: 5px 8px; font-family: 'Arial', 'B Nazanin', sans-serif;
        font-size: 13px; selection-background-color: {c['accent']}; selection-color: white;
    }}
    QLineEdit:focus {{ border-color: {c['accent']}; }}

    QTextEdit {{
        background-color: {c['bg_card']}; color: {c['text_primary']};
        border: 2px solid {c['border_light']}; border-radius: 5px;
        padding: 5px; font-family: 'Consolas', 'Arial', sans-serif; font-size: 12px;
    }}

    QPushButton {{
        background-color: {c['bg_primary']}; color: {c['text_primary']};
        border: 1px solid {c['border_light']}; border-radius: 5px;
        padding: 4px 10px; font-family: 'B Nazanin', sans-serif;
        font-size: 14px; font-weight: bold; min-height: 20px;
    }}
    QPushButton:hover {{ background-color: {c['bg_card']}; border-color: {c['accent']}; }}
    QPushButton:pressed {{ background-color: {c['accent']}; color: white; }}

    QPushButton#accentBtn {{
        background-color: {c['accent']}; color: white; border: none;
        font-size: 15px; padding: 6px 14px; border-radius: 5px; min-height: 24px;
    }}
    QPushButton#accentBtn:hover {{ background-color: {c['accent_hover']}; }}

    QPushButton#dangerBtn {{ background-color: #dc2626; color: white; border: none; }}
    QPushButton#dangerBtn:hover {{ background-color: #ef4444; }}

    QPushButton#iconBtn {{
        background: transparent; border: 1px solid {c['border_light']};
        border-radius: 5px; padding: 2px; min-width: 28px; min-height: 28px; font-size: 14px;
    }}
    QPushButton#iconBtn:hover {{ background: {c['bg_card']}; }}

    QGroupBox {{
        font-family: 'B Nazanin', sans-serif; font-size: 14px; font-weight: bold;
        color: {c['text_accent']}; border: 1px solid {c['border_light']};
        border-radius: 5px; margin-top: 6px; padding-top: 12px;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; right: 10px; padding: 0 4px; }}

    QListWidget {{
        background-color: {c['bg_input']}; color: {c['text_primary']};
        border: 2px solid {c['border_light']}; border-radius: 5px;
        font-family: 'Arial', 'B Nazanin', sans-serif; font-size: 12px;
    }}
    QListWidget::item {{ padding: 3px 6px; border-radius: 2px; }}
    QListWidget::item:selected {{ background-color: {c['accent']}; color: white; }}
    QListWidget::item:hover {{ background-color: {c['bg_card']}; }}

    QComboBox {{
        background-color: {c['bg_input']}; color: {c['text_primary']};
        border: 2px solid {c['border_light']}; border-radius: 5px;
        padding: 5px 10px; font-family: 'B Nazanin', sans-serif; font-size: 13px;
    }}
    QComboBox:hover {{ border-color: {c['accent']}; }}
    QComboBox QAbstractItemView {{
        background: {c['bg_card']}; color: {c['text_primary']};
        border: 1px solid {c['border_light']}; selection-background-color: {c['accent']};
    }}

    QCheckBox {{
        font-family: 'B Nazanin', sans-serif; font-size: 13px;
        color: {c['text_primary']}; spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border-radius: 3px;
        border: 2px solid {c['border_light']};
    }}
    QCheckBox::indicator:checked {{ background-color: {c['accent']}; border-color: {c['accent']}; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 5px; margin: 1px; }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar_handle']}; border-radius: 2px; min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ height: 0; }}

    QMenu {{ background: {c['bg_card']}; border: 1px solid {c['border_light']}; border-radius: 5px; padding: 3px; }}
    QMenu::item {{ padding: 5px 16px; border-radius: 3px; font-family: 'B Nazanin', sans-serif; font-size: 13px; }}
    QMenu::item:selected {{ background: {c['accent']}; color: white; }}

    QToolTip {{ background: {c['bg_card']}; color: {c['text_primary']}; border: 1px solid {c['border_light']}; border-radius: 4px; padding: 3px 6px; font-size: 12px; }}
    QMessageBox {{ background: {c['bg_card']}; }}
    QMessageBox QLabel {{ color: {c['text_primary']}; font-family: 'B Nazanin', sans-serif; }}
    QDialog {{ background: {c['bg_root']}; }}
    """


# ============================================================================
# Canvas Frame
# ============================================================================

class CanvasFrame(QFrame):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self.setContentsMargins(4, 4, 4, 4)

    def update_theme(self, theme):
        self._theme = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._theme.colors
        r = self.rect()
        o = QRectF(float(r.x())+2, float(r.y())+2, float(r.width())-4, float(r.height())-4)

        sp = QPainterPath(); sp.addRoundedRect(o.translated(2, 2), 8.0, 8.0)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c['shadow_dark']); p.drawPath(sp)
        sp = QPainterPath(); sp.addRoundedRect(o.translated(-1, -1), 8.0, 8.0)
        p.setBrush(c['shadow_light']); p.drawPath(sp)
        sp = QPainterPath(); sp.addRoundedRect(o, 8.0, 8.0)
        p.setBrush(QColor(c['bg_card'])); p.drawPath(sp)
        inner = QRectF(o.x()+1, o.y()+1, o.width()-2, o.height()-2)
        bp = QPainterPath(); bp.addRoundedRect(inner, 7.0, 7.0)
        p.setPen(QPen(QColor(c['border_light']), 1))
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(bp)


# ============================================================================
# Interactive Vector Canvas
# ============================================================================

class InteractiveVectorCanvas(FigureCanvas):
    vector_clicked = pyqtSignal(int)
    vector_right_clicked = pyqtSignal(int)

    def __init__(self, theme, parent=None, width=5, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self._theme = theme
        self._vectors = []
        self._resultant = None
        self._selected = -1
        self._apply_theme()
        self.fig.tight_layout(pad=1.5)
        self.setMinimumSize(300, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mpl_connect('button_press_event', self._on_click)

    def _apply_theme(self):
        c = self._theme.colors
        self.ax.set_facecolor(c['bg_card'])
        self.fig.patch.set_facecolor(c['bg_card'])
        self.ax.grid(True, linestyle='--', alpha=0.3, color=c['border_light'])
        self.ax.tick_params(colors=c['text_secondary'], labelsize=8)
        for s in self.ax.spines.values():
            s.set_color(c['text_secondary'])

    def update_theme(self, theme):
        self._theme = theme
        self._apply_theme()
        self.draw_idle()

    def set_data(self, vectors, resultant=None, selected=-1):
        self._vectors = vectors
        self._resultant = resultant
        self._selected = selected
        self._redraw()

    def _redraw(self):
        self.ax.clear()
        self._apply_theme()
        n = max(len(self._vectors), 1)
        colors = plt.cm.viridis(np.linspace(0.15, 0.85, n))
        max_val = 1.0

        for i, v in enumerate(self._vectors):
            max_val = max(max_val, abs(v.x), abs(v.y))
            sel = (i == self._selected)
            color = '#ffcc00' if sel else colors[i]
            w = 0.016 if sel else 0.01
            hw = 6 if sel else 4
            self.ax.quiver(0, 0, v.x, v.y, angles='xy', scale_units='xy', scale=1,
                          color=color, width=w, headwidth=hw, headlength=hw+1,
                          label=f'v{i+1}', picker=True, pickradius=6)
            self.ax.plot(v.x, v.y, 'o', color=color, markersize=10 if sel else 6,
                        markeredgecolor='white' if sel else color,
                        markeredgewidth=1.5 if sel else 0)

        if self._resultant and (self._resultant.x != 0 or self._resultant.y != 0):
            max_val = max(max_val, abs(self._resultant.x), abs(self._resultant.y))
            self.ax.quiver(0, 0, self._resultant.x, self._resultant.y,
                          angles='xy', scale_units='xy', scale=1,
                          color='#ff4444', width=0.018, headwidth=7, headlength=8, label='S')

        if self._vectors:
            self.ax.legend(loc='upper right', fontsize=6, framealpha=0.5)
        limit = max(max_val * 1.3, 2.0)
        self.ax.set_xlim(-limit, limit); self.ax.set_ylim(-limit, limit)
        self.ax.set_aspect('equal')
        self.ax.axhline(0, color='gray', linewidth=0.5, alpha=0.3)
        self.ax.axvline(0, color='gray', linewidth=0.5, alpha=0.3)
        self.draw_idle()

    def _on_click(self, event):
        if event.inaxes != self.ax or event.button is None:
            return
        min_dist, closest = float('inf'), -1
        for i, v in enumerate(self._vectors):
            d = np.sqrt((event.xdata - v.x)**2 + (event.ydata - v.y)**2)
            if d < min_dist and d < 0.7:
                min_dist, closest = d, i
        if closest >= 0:
            if event.button == 1:
                self._selected = closest; self._redraw(); self.vector_clicked.emit(closest)
            elif event.button == 3:
                self.vector_right_clicked.emit(closest)

    def to_base64(self, dpi=DEFAULT_GRAPH_DPI):
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                        pad_inches=0.06, facecolor=self.fig.get_facecolor())
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')


# ============================================================================
# Multi-Graph Canvas
# ============================================================================

@dataclass
class GraphItem:
    """یک آیتم نمودار (تابع، خط، یا نقطه)."""
    type: str  # 'function', 'line', 'point'
    label: str
    color: str
    data: dict = field(default_factory=dict)
    visible: bool = True


class MultiGraphCanvas(FigureCanvas):
    """Canvas پیشرفته برای رسم چندین نمودار همزمان."""

    def __init__(self, theme, parent=None, width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self._theme = theme
        self._items: List[GraphItem] = []
        self._apply_theme()
        self.fig.tight_layout(pad=1.5)
        self.setMinimumSize(350, 300)

    def _apply_theme(self):
        c = self._theme.colors
        self.ax.set_facecolor(c['bg_card'])
        self.fig.patch.set_facecolor(c['bg_card'])
        self.ax.grid(True, linestyle='--', alpha=0.3, color=c['border_light'])
        self.ax.tick_params(colors=c['text_secondary'], labelsize=8)
        for s in self.ax.spines.values():
            s.set_color(c['text_secondary'])
        self.ax.axhline(0, color=c['text_secondary'], linewidth=0.3, alpha=0.2)
        self.ax.axvline(0, color=c['text_secondary'], linewidth=0.3, alpha=0.2)

    def update_theme(self, theme):
        self._theme = theme
        self._apply_theme()
        self.draw_idle()

    def add_item(self, item: GraphItem):
        self._items.append(item)
        self._redraw_all()

    def remove_item(self, index: int):
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self._redraw_all()

    def toggle_item(self, index: int):
        if 0 <= index < len(self._items):
            self._items[index].visible = not self._items[index].visible
            self._redraw_all()

    def clear_items(self):
        self._items.clear()
        self._redraw_all()

    def get_items(self) -> List[GraphItem]:
        return self._items

    def _redraw_all(self):
        self.ax.clear()
        self._apply_theme()

        for item in self._items:
            if not item.visible:
                continue

            try:
                if item.type == 'function':
                    self._draw_function(item)
                elif item.type == 'line':
                    self._draw_line(item)
                elif item.type == 'point':
                    self._draw_point(item)
            except Exception:
                continue

        if self._items:
            self.ax.legend(loc='upper right', fontsize=6, framealpha=0.5)

        self.draw_idle()

    def _draw_function(self, item: GraphItem):
        func_str = item.data.get('function', '')
        if not func_str:
            return
        x = np.linspace(-10, 10, GRAPH_RESOLUTION)
        safe = {"x": x, "np": np, "sin": np.sin, "cos": np.cos, "tan": np.tan,
               "log": np.log, "exp": np.exp, "sqrt": np.sqrt, "abs": np.abs,
               "pi": np.pi, "e": np.e}
        y = np.clip(eval(func_str.replace('^', '**'), {"__builtins__": {}}, safe), -1e6, 1e6)
        self.ax.plot(x, y, color=item.color, linewidth=2, label=item.label)

    def _draw_line(self, item: GraphItem):
        m = item.data.get('slope', 0)
        b = item.data.get('intercept', 0)
        x = np.array([-10, 10])
        self.ax.plot(x, m*x+b, color=item.color, linewidth=2, label=item.label)

    def _draw_point(self, item: GraphItem):
        x = item.data.get('x', 0)
        y = item.data.get('y', 0)
        self.ax.plot(x, y, 'o', color=item.color, markersize=10, label=item.label)

    def to_pixmap(self, dpi=DEFAULT_GRAPH_DPI):
        buf = io.BytesIO()
        self.fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                        pad_inches=0.06, facecolor=self.fig.get_facecolor())
        buf.seek(0)
        pix = QPixmap()
        pix.loadFromData(buf.read(), 'PNG')
        return pix


# ============================================================================
# Graph Generator Thread
# ============================================================================

class GraphGeneratorThread(QThread):
    graph_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, code, theme, parent=None):
        super().__init__(parent)
        self._code = code
        self._theme = theme

    def run(self):
        try:
            plt.close('all')
            c = self._theme.colors
            plt.style.use('seaborn-v0_8-darkgrid' if self._theme.is_dark else 'seaborn-v0_8-whitegrid')
            plt.rcParams.update({'axes.facecolor': c['bg_card'], 'figure.facecolor': c['bg_card'],
                                'text.color': c['text_secondary'], 'axes.edgecolor': c['text_secondary'],
                                'figure.figsize': (7, 5), 'figure.dpi': DEFAULT_GRAPH_DPI})
            plt.ioff()
            fig, ax = plt.subplots()
            m = re.search(r'```(?:python_graph|python)\n(.*?)```', self._code, re.DOTALL)
            if not m:
                raise ValueError("بلوک کد پیدا نشد")
            exec(m.group(1).strip(), {'plt': plt, 'np': np, 'ax': ax, 'fig': fig, '__builtins__': __builtins__})
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.06, facecolor=c['bg_card'])
            buf.seek(0)
            self.graph_ready.emit(base64.b64encode(buf.read()).decode('utf-8'))
            buf.close()
            plt.close(fig)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================================
# Preview Dialog
# ============================================================================

class PreviewDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self.setWindowTitle("پیش‌نمایش نمودار")
        self.setMinimumSize(450, 380)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        l = QVBoxLayout(self); l.setContentsMargins(8, 8, 8, 8)
        lbl = QLabel()
        lbl.setPixmap(pixmap.scaled(650, 450, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = QScrollArea(); s.setWidget(lbl); l.addWidget(s)
        b = QDialogButtonBox(); b.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        save_btn = QPushButton("💾 ذخیره تصویر")
        save_btn.setFont(QFont("B Nazanin", 12, QFont.Weight.Bold))
        save_btn.clicked.connect(self._save)
        b.addButton(save_btn, QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = QPushButton("بستن")
        close_btn.setFont(QFont("B Nazanin", 12, QFont.Weight.Bold))
        close_btn.clicked.connect(self.close)
        b.addButton(close_btn, QDialogButtonBox.ButtonRole.RejectRole)
        l.addWidget(b)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره", "نمودار.png", "PNG (*.png)")
        if path:
            self._pixmap.save(path, 'PNG')
            QMessageBox.information(self, "موفقیت", "تصویر ذخیره شد.")


# ============================================================================
# Vector Tab
# ============================================================================

class VectorTab(QWidget):
    def __init__(self, engine, theme, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._theme = theme
        self._vectors: List[Vector2D] = []
        self._resultant = None
        self._selected = -1
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()

    def _build_ui(self):
        l = QHBoxLayout(); l.setContentsMargins(6, 4, 6, 4); l.setSpacing(6)
        ctrl = QFrame(); ctrl.setObjectName("card"); ctrl.setMinimumWidth(260); ctrl.setMaximumWidth(320)
        ctrl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl = QVBoxLayout(ctrl); cl.setContentsMargins(8, 6, 8, 6); cl.setSpacing(5)

        t = QLabel("🎯 مدیریت بردارها")
        t.setFont(QFont("B Nazanin", 17, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {self._theme.colors['text_accent']}; padding: 2px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(t)

        ig = QGroupBox("مختصات بردار جدید"); ig.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        ig.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        gl = QGridLayout(ig); gl.setSpacing(3)
        gl.addWidget(QLabel("طول:"), 0, 0)
        self._x = self._inp(); self._x.returnPressed.connect(lambda: self._y.setFocus())
        gl.addWidget(self._x, 0, 1)
        gl.addWidget(QLabel("عرض:"), 1, 0)
        self._y = self._inp(); self._y.returnPressed.connect(self._add)
        gl.addWidget(self._y, 1, 1)
        cl.addWidget(ig)

        bg = QGridLayout(); bg.setSpacing(3)
        bg.addWidget(self._btn("➕ افزودن", self._add, True), 0, 0)
        bg.addWidget(self._btn("🔗 برآیند", self._sum, True), 0, 1)
        bg.addWidget(self._btn("✏️ ویرایش", self._edit), 1, 0)
        bg.addWidget(self._btn("🗑️ حذف", self._delete, False, "dangerBtn"), 1, 1)
        bg.addWidget(self._btn("🔄 پاک کردن همه", self._clear), 2, 0, 1, 2)
        cl.addLayout(bg)

        self._list = QListWidget(); self._list.setMaximumHeight(110)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._list.itemClicked.connect(self._on_list_click)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_list_menu)
        cl.addWidget(self._list)

        self._info = QLabel("بدون بردار")
        self._info.setFont(QFont("B Nazanin", 10)); self._info.setWordWrap(True)
        self._info.setStyleSheet(f"color: {self._theme.colors['text_secondary']}; padding: 2px;")
        cl.addWidget(self._info)
        cl.addWidget(self._btn("📥 ذخیره تصویر", self._export))
        cl.addStretch()
        l.addWidget(ctrl)

        cf = CanvasFrame(self._theme); cv = QVBoxLayout(cf); cv.setContentsMargins(3, 3, 3, 3)
        self._canvas = InteractiveVectorCanvas(self._theme, self)
        self._canvas.vector_clicked.connect(self._on_canvas_click)
        self._canvas.vector_right_clicked.connect(self._on_canvas_right_click)
        cv.addWidget(self._canvas); l.addWidget(cf, 1)
        self.setLayout(l); self._refresh()

    def _inp(self):
        f = QLineEdit(); f.setValidator(QDoubleValidator(-MAX_VECTOR_VALUE, MAX_VECTOR_VALUE, 2))
        f.setFont(QFont("Arial", 13)); f.setAlignment(Qt.AlignmentFlag.AlignRight)
        f.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        return f

    def _btn(self, text, cb, accent=False, obj=""):
        b = QPushButton(text)
        if accent: b.setObjectName("accentBtn")
        elif obj: b.setObjectName(obj)
        b.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor); b.setMinimumHeight(26)
        b.clicked.connect(cb)
        return b

    def _add(self):
        try:
            x = float(self._x.text() or 0); y = float(self._y.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مقادیر عددی معتبر وارد کنید!"); return
        if abs(x) > MAX_VECTOR_VALUE or abs(y) > MAX_VECTOR_VALUE:
            QMessageBox.warning(self, "خطا", f"محدوده مجاز: ±{MAX_VECTOR_VALUE}"); return
        if len(self._vectors) >= MAX_VECTOR_COUNT:
            QMessageBox.warning(self, "خطا", f"حداکثر {MAX_VECTOR_COUNT} بردار"); return
        self._vectors.append(self._engine.create_vector(x, y))
        self._resultant = None; self._selected = -1
        self._x.clear(); self._y.clear(); self._x.setFocus(); self._refresh()

    def _sum(self):
        if not self._vectors:
            QMessageBox.information(self, "توجه", "برداری وجود ندارد!"); return
        self._resultant = self._engine.sum_vectors(self._vectors); self._refresh()

    def _edit(self):
        if self._selected < 0 or self._selected >= len(self._vectors):
            QMessageBox.information(self, "توجه", "ابتدا یک بردار را انتخاب کنید!"); return
        v = self._vectors[self._selected]
        self._x.setText(str(v.x)); self._y.setText(str(v.y)); self._delete_selected()

    def _delete(self):
        if self._selected < 0 or self._selected >= len(self._vectors):
            QMessageBox.information(self, "توجه", "ابتدا یک بردار را انتخاب کنید!"); return
        self._delete_selected()

    def _delete_selected(self):
        if 0 <= self._selected < len(self._vectors):
            self._vectors.pop(self._selected); self._resultant = None
            self._selected = -1; self._refresh()

    def _clear(self):
        if not self._vectors: return
        if QMessageBox.question(self, "تأیید", "همه بردارها پاک شوند؟",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) == QMessageBox.StandardButton.Yes:
            self._vectors.clear(); self._resultant = None; self._selected = -1; self._refresh()

    def _on_canvas_click(self, idx): self._selected = idx; self._refresh()
    def _on_canvas_right_click(self, idx):
        self._selected = idx; self._refresh()
        m = QMenu(self); m.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        m.addAction("✏️ ویرایش", self._edit); m.addAction("🗑️ حذف", self._delete)
        m.exec(self._canvas.mapToGlobal(self._canvas.rect().center()))

    def _on_list_click(self, item): self._selected = self._list.row(item); self._refresh()
    def _on_list_menu(self, pos):
        item = self._list.itemAt(pos)
        if item:
            self._selected = self._list.row(item); self._refresh()
            m = QMenu(self); m.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            m.addAction("✏️ ویرایش", self._edit); m.addAction("🗑️ حذف", self._delete)
            m.exec(self._list.mapToGlobal(pos))

    def _refresh(self):
        self._list.clear()
        for i, v in enumerate(self._vectors):
            item = QListWidgetItem(
                f"بردار {i+1}: طول={v.y:.2f}، عرض={v.x:.2f} | "
                f"اندازه={v.magnitude:.2f} | زاویه={v.angle_degrees:.1f}°"
            )
            item.setFont(QFont("Arial", 12)); item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            if i == self._selected: item.setSelected(True)
            self._list.addItem(item)
        if self._resultant:
            r = self._resultant
            self._info.setText(
                f"برآیند: طول={r.y:.2f}، عرض={r.x:.2f} | "
                f"اندازه={r.magnitude:.2f} | زاویه={r.angle_degrees:.1f}° | {len(self._vectors)} بردار"
            )
        else:
            self._info.setText(f"تعداد: {len(self._vectors)} بردار | برای برآیند کلیک کنید")
        self._canvas.set_data(self._vectors, self._resultant, self._selected)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره", "نمودار_بردارها.png", "PNG (*.png)")
        if path:
            try:
                QPixmap().loadFromData(base64.b64decode(self._canvas.to_base64()), 'PNG').save(path, 'PNG')
                QMessageBox.information(self, "موفقیت", "تصویر ذخیره شد.")
            except Exception as e: QMessageBox.critical(self, "خطا", str(e))

    def update_theme(self, theme):
        self._theme = theme; self._canvas.update_theme(theme)
        if isinstance(self._canvas.parent(), CanvasFrame): self._canvas.parent().update_theme(theme)


# ============================================================================
# Graph Tab - Multi-Graph
# ============================================================================

class GraphTab(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._thread = None
        self._pixmap = None
        self._color_index = 0
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()

    def _next_color(self) -> str:
        color = GRAPH_COLORS[self._color_index % len(GRAPH_COLORS)]
        self._color_index += 1
        return color

    def _build_ui(self):
        l = QHBoxLayout(); l.setContentsMargins(6, 4, 6, 4); l.setSpacing(6)
        ctrl = QFrame(); ctrl.setObjectName("card"); ctrl.setMinimumWidth(270); ctrl.setMaximumWidth(330)
        ctrl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl = QVBoxLayout(ctrl); cl.setContentsMargins(8, 6, 8, 6); cl.setSpacing(5)

        t = QLabel("📈 رسم چند نمودار")
        t.setFont(QFont("B Nazanin", 17, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {self._theme.colors['text_accent']}; padding: 2px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(t)

        # === تابع ===
        fg = QGroupBox("📉 افزودن تابع f(x)"); fg.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        fg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        fl = QVBoxLayout(fg); fl.setSpacing(3)
        self._func = QLineEdit()
        self._func.setPlaceholderText("sin(x) | x^2 + 2x + 1 | x^3 - x")
        self._func.setFont(QFont("Arial", 13)); self._func.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._func.returnPressed.connect(self._add_function)
        fl.addWidget(self._func)
        fl.addWidget(self._btn("📈 افزودن تابع", self._add_function, True))
        cl.addWidget(fg)

        # === خط ===
        lg = QGroupBox("📏 افزودن خط y = mx + b"); lg.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        lg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        ll = QGridLayout(lg); ll.setSpacing(3)
        ll.addWidget(QLabel("شیب:"), 0, 0)
        self._m = QLineEdit("1"); self._m.setValidator(QDoubleValidator(-100, 100, 2))
        self._m.setFont(QFont("Arial", 13)); self._m.setAlignment(Qt.AlignmentFlag.AlignRight)
        ll.addWidget(self._m, 0, 1)
        ll.addWidget(QLabel("عرض:"), 1, 0)
        self._b = QLineEdit("0"); self._b.setValidator(QDoubleValidator(-100, 100, 2))
        self._b.setFont(QFont("Arial", 13)); self._b.setAlignment(Qt.AlignmentFlag.AlignRight)
        ll.addWidget(self._b, 1, 1)
        ll.addWidget(self._btn("📏 افزودن خط", self._add_line, True), 2, 0, 1, 2)
        cl.addWidget(lg)

        # === نقطه ===
        pg = QGroupBox("📍 افزودن نقطه"); pg.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        pg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        pl = QGridLayout(pg); pl.setSpacing(3)
        pl.addWidget(QLabel("طول:"), 0, 0)
        self._px = QLineEdit(); self._px.setValidator(QDoubleValidator(-100, 100, 2))
        self._px.setFont(QFont("Arial", 13)); self._px.setAlignment(Qt.AlignmentFlag.AlignRight)
        pl.addWidget(self._px, 0, 1)
        pl.addWidget(QLabel("عرض:"), 1, 0)
        self._py = QLineEdit(); self._py.setValidator(QDoubleValidator(-100, 100, 2))
        self._py.setFont(QFont("Arial", 13)); self._py.setAlignment(Qt.AlignmentFlag.AlignRight)
        pl.addWidget(self._py, 1, 1)
        pl.addWidget(self._btn("📍 افزودن نقطه", self._add_point, True), 2, 0, 1, 2)
        cl.addWidget(pg)

        # === لیست نمودارها ===
        lg2 = QGroupBox("📋 نمودارهای رسم شده")
        lg2.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        lg2.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        lgl = QVBoxLayout(lg2); lgl.setSpacing(3)
        self._graph_list = QListWidget()
        self._graph_list.setMaximumHeight(100)
        self._graph_list.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._graph_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._graph_list.customContextMenuRequested.connect(self._on_graph_menu)
        lgl.addWidget(self._graph_list)
        gr = QHBoxLayout(); gr.setSpacing(4)
        gr.addWidget(self._btn("👁️ نمایش/مخفی", self._toggle_selected))
        gr.addWidget(self._btn("🗑️ حذف انتخاب", self._remove_selected, False, "dangerBtn"))
        gr.addWidget(self._btn("🔄 پاک کردن همه", self._clear_graphs))
        lgl.addLayout(gr)
        cl.addWidget(lg2)

        # === کد ===
        cg = QGroupBox("💻 کد پایتون"); cg.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        cg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cv = QVBoxLayout(cg); cv.setSpacing(3)
        self._code = QTextEdit()
        self._code.setPlaceholderText("import matplotlib.pyplot as plt\n...")
        self._code.setFont(QFont("Consolas", 10)); self._code.setMaximumHeight(70)
        self._code.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        cv.addWidget(self._code)
        self._run = self._btn("▶️ اجرای کد", self._run_code, True)
        cv.addWidget(self._run)
        cl.addWidget(cg)

        ar = QHBoxLayout(); ar.setSpacing(3)
        ar.addWidget(self._btn("📥 ذخیره", self._export))
        ar.addWidget(self._btn("🔍 پیش‌نمایش", self._preview, True))
        cl.addLayout(ar)

        self._status = QLabel(""); self._status.setFont(QFont("B Nazanin", 10))
        self._status.setStyleSheet(f"color: {self._theme.colors['success']};"); self._status.hide()
        cl.addWidget(self._status)
        cl.addStretch()
        l.addWidget(ctrl)

        cf = CanvasFrame(self._theme); cv2 = QVBoxLayout(cf); cv2.setContentsMargins(3, 3, 3, 3)
        self._canvas = MultiGraphCanvas(self._theme, self)
        cv2.addWidget(self._canvas); l.addWidget(cf, 1)
        self.setLayout(l)

    def _btn(self, text, cb, accent=False, obj=""):
        b = QPushButton(text)
        if accent: b.setObjectName("accentBtn")
        elif obj: b.setObjectName(obj)
        b.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        b.setCursor(Qt.CursorShape.PointingHandCursor); b.setMinimumHeight(26)
        b.clicked.connect(cb)
        return b

    def _show(self, msg):
        self._status.setText(msg); self._status.show()
        QTimer.singleShot(2500, self._status.hide)

    def _add_function(self):
        f = self._func.text().strip()
        if not f: QMessageBox.warning(self, "خطا", "تابع را وارد کنید!"); return
        color = self._next_color()
        item = GraphItem(type='function', label=f'f(x)={f}', color=color, data={'function': f})
        self._canvas.add_item(item)
        self._refresh_list()
        self._func.clear()
        self._show(f"✅ تابع {f} افزوده شد")

    def _add_line(self):
        try:
            m = float(self._m.text() or 0); b = float(self._b.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مقادیر عددی وارد کنید!"); return
        color = self._next_color()
        item = GraphItem(type='line', label=f'y={m}x+{b}', color=color, data={'slope': m, 'intercept': b})
        self._canvas.add_item(item)
        self._refresh_list()
        self._show(f"✅ خط y={m}x+{b} افزوده شد")

    def _add_point(self):
        try:
            x = float(self._px.text() or 0); y = float(self._py.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "خطا", "مقادیر عددی وارد کنید!"); return
        color = self._next_color()
        item = GraphItem(type='point', label=f'({x},{y})', color=color, data={'x': x, 'y': y})
        self._canvas.add_item(item)
        self._refresh_list()
        self._show(f"✅ نقطه ({x},{y}) افزوده شد")

    def _refresh_list(self):
        self._graph_list.clear()
        for i, item in enumerate(self._canvas.get_items()):
            prefix = "👁️ " if item.visible else "🚫 "
            text = f"{prefix}{item.label}"
            list_item = QListWidgetItem(text)
            list_item.setFont(QFont("Arial", 11))
            # Set color indicator
            list_item.setForeground(QColor(item.color))
            list_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self._graph_list.addItem(list_item)

    def _toggle_selected(self):
        row = self._graph_list.currentRow()
        if row >= 0:
            self._canvas.toggle_item(row)
            self._refresh_list()

    def _remove_selected(self):
        row = self._graph_list.currentRow()
        if row >= 0:
            self._canvas.remove_item(row)
            self._refresh_list()

    def _clear_graphs(self):
        if self._canvas.get_items():
            self._canvas.clear_items()
            self._refresh_list()
            self._show("🧹 همه نمودارها پاک شدند")

    def _on_graph_menu(self, pos):
        row = self._graph_list.currentRow()
        if row >= 0:
            self._graph_list.setCurrentRow(row)
            m = QMenu(self); m.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            m.addAction("👁️ نمایش/مخفی", self._toggle_selected)
            m.addAction("🗑️ حذف", self._remove_selected)
            m.exec(self._graph_list.mapToGlobal(pos))

    def _run_code(self):
        c = self._code.toPlainText().strip()
        if not c: QMessageBox.warning(self, "خطا", "کد را وارد کنید!"); return
        self._run.setEnabled(False); self._run.setText("⏳ ...")
        self._thread = GraphGeneratorThread(f"```python_graph\n{c}\n```", self._theme, self)
        self._thread.graph_ready.connect(self._on_ready)
        self._thread.error_occurred.connect(self._on_error)
        self._thread.start()

    def _on_ready(self, b64):
        self._run.setEnabled(True); self._run.setText("▶️ اجرای کد")
        self._pixmap = QPixmap(); self._pixmap.loadFromData(base64.b64decode(b64), 'PNG')
        if not self._pixmap.isNull(): self._show("✅ نمودار آماده"); self._preview()

    def _on_error(self, e):
        self._run.setEnabled(True); self._run.setText("▶️ اجرای کد")
        QMessageBox.critical(self, "خطا", f"خطا:\n{e}")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره", "نمودار.png", "PNG (*.png)")
        if path:
            try:
                (self._pixmap or self._canvas.to_pixmap()).save(path, 'PNG')
                QMessageBox.information(self, "موفقیت", "ذخیره شد.")
            except Exception as e: QMessageBox.critical(self, "خطا", str(e))

    def _preview(self):
        pix = self._pixmap or self._canvas.to_pixmap()
        if pix and not pix.isNull(): PreviewDialog(pix, self).exec()
        else: QMessageBox.information(self, "توجه", "نموداری موجود نیست.")

    def update_theme(self, theme):
        self._theme = theme; self._canvas.update_theme(theme)
        if isinstance(self._canvas.parent(), CanvasFrame): self._canvas.parent().update_theme(theme)


# ============================================================================
# Animated Tab Widget - چسبیده به هدر
# ============================================================================

class AnimatedTabWidget(QTabWidget):
    """
    QTabWidget با انیمیشن fade بین تب‌ها.
    هر دو تب همزمان ساخته میشن و همیشه آماده هستن.
    """

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._animating = False
        self._prev_index = 0

        self.setFont(QFont("B Nazanin", 14, QFont.Weight.Bold))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setDocumentMode(True)

        # اتصال به سیگنال currentChanged برای انیمیشن
        self.currentChanged.connect(self._animate_transition)

    def _animate_transition(self, new_index: int):
        """انیمیشن fade بین تب‌ها."""
        if self._animating:
            return

        old_widget = self.widget(self._prev_index)
        new_widget = self.widget(new_index)

        if old_widget and new_widget and old_widget != new_widget:
            self._animating = True

            # Fade out old tab
            fade_out = QGraphicsOpacityEffect()
            old_widget.setGraphicsEffect(fade_out)
            anim_out = QPropertyAnimation(fade_out, b"opacity")
            anim_out.setDuration(120)
            anim_out.setStartValue(1.0)
            anim_out.setEndValue(0.0)
            anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

            def on_fade_out_done():
                old_widget.setGraphicsEffect(None)

                # Fade in new tab
                fade_in = QGraphicsOpacityEffect()
                new_widget.setGraphicsEffect(fade_in)
                anim_in = QPropertyAnimation(fade_in, b"opacity")
                anim_in.setDuration(150)
                anim_in.setStartValue(0.0)
                anim_in.setEndValue(1.0)
                anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

                def on_fade_in_done():
                    new_widget.setGraphicsEffect(None)
                    self._animating = False

                anim_in.finished.connect(on_fade_in_done)
                anim_in.start()

            anim_out.finished.connect(on_fade_out_done)
            anim_out.start()

        self._prev_index = new_index

    def update_theme(self, theme):
        self._theme = theme
        c = theme.colors
        self.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: {c['tab_inactive_bg']};
                color: {c['tab_inactive_text']};
                padding: 5px 18px; margin: 0px 1px;
                border: 1px solid {c['tab_shadow_light']};
                border-bottom: 1px solid {c['tab_shadow_dark']};
                border-radius: 5px 5px 0 0;
                font: bold 14px 'B Nazanin'; min-width: 130px;
            }}
            QTabBar::tab:selected {{
                background: {c['tab_active_bg']};
                color: {c['tab_active_text']};
                border-bottom: 3px solid {c['tab_border_active']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {c['tab_hover_bg']};
                color: {c['text_primary']};
            }}
        """)



# ============================================================================
# Main Window
# ============================================================================

class VectorWindow(QWidget):
    """پنجره اصلی - تب‌های چسبیده به هدر، انیمیشن، Multi-Graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 بردار، مختصات و رسم نمودار")
        self.setMinimumSize(950, 620)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._engine = MathEngine()
        self._theme = UltraHighContrastTheme(ThemeMode.DARK)

        self._init_ui()
        self._init_shortcuts()
        self._apply_theme()
        self._center()

        logger.info("پنجره بردار و نمودار نسخه ۹.۳.۱ راه‌اندازی شد")

    def _init_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(6, 2, 6, 4)
        root.setSpacing(0)

        # Header با TabBar چسبیده
        h = QHBoxLayout()
        h.setContentsMargins(4, 4, 4, 0)
        h.setSpacing(6)

        t = QLabel("🎯 ابزارهای بردار و رسم نمودار")
        t.setFont(QFont("B Nazanin", 17, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {self._theme.colors['accent']};")
        h.addWidget(t)
        h.addStretch()

        self._tb = QPushButton("🌙")
        self._tb.setObjectName("iconBtn")
        self._tb.setFixedSize(28, 28)
        self._tb.setToolTip("تغییر تم (Ctrl+T)")
        self._tb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tb.clicked.connect(self._toggle_theme)
        h.addWidget(self._tb)

        root.addLayout(h)

        # Animated Tab Widget - هر دو تب همزمان ساخته میشن
        self._tabs = AnimatedTabWidget(self._theme)

        # ساخت هر دو تب قبل از addTab
        self._vt = VectorTab(self._engine, self._theme)
        self._gt = GraphTab(self._theme)

        self._tabs.addTab(self._vt, "🎯 بردار و مختصات")
        self._tabs.addTab(self._gt, "📈 رسم نمودار")

        root.addWidget(self._tabs, 1)

        # Status
        s = QLabel("Ctrl+1 بردار | Ctrl+2 نمودار | Ctrl+T تم | Ctrl+Q خروج")
        s.setFont(QFont("B Nazanin", 9))
        s.setStyleSheet(f"color: {self._theme.colors['text_muted']}; padding: 1px;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(s)

        self.setLayout(root)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(lambda: self._tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(lambda: self._tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self._toggle_theme)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    def _toggle_theme(self):
        self._theme.toggle()
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(compact_rtl_stylesheet(self._theme.colors))
        self._tb.setText("🌙" if self._theme.is_dark else "☀️")
        self._tabs.update_theme(self._theme)
        self._vt.update_theme(self._theme)
        self._gt.update_theme(self._theme)

    def _center(self):
        s = self.screen().availableGeometry()
        w, h = min(s.width(), 1050), min(s.height(), 660)
        self.resize(int(w * 0.8), int(h * 0.8))
        f = self.frameGeometry()
        f.moveCenter(s.center())
        self.move(f.topLeft())


if __name__ == "__main__":
    import sys as _s
    a = QApplication(_s.argv)
    FontSystem.setup(a)
    w = VectorWindow()
    w.show()
    _s.exit(a.exec())
