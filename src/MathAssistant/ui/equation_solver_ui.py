# src/MathAssistant/ui/equation_solver_ui.py
"""
MathAssistant Pro - نسخه نهایی با تمام باگ‌ها رفع شده

Author: AmirMohammad Ghasemzadeh
Version: 12.0.0 - Fully Fixed
"""

import sys
import json
import io
import base64
import re
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QScrollArea, QFrame,
    QApplication, QMessageBox, QFileDialog,
    QSizePolicy, QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QThread, QSettings
)
from PyQt6.QtGui import (
    QFont, QColor, QPixmap
)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

warnings.filterwarnings('ignore')

rcParams['mathtext.fontset'] = 'stix'
rcParams['font.family'] = 'serif'
rcParams['mathtext.default'] = 'regular'
rcParams['text.usetex'] = False

from sympy import latex as sympy_latex, Symbol, sympify
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)

try:
    from ..core.equation_solver import EquationSolverEngine, EquationSolution, SolutionStep
except ImportError:
    from equation_solver import EquationSolverEngine, EquationSolution, SolutionStep # type: ignore

TRANSFORMATIONS = (
    standard_transformations +
    (implicit_multiplication_application, convert_xor)
)

DEBUG = False  # False برای نسخه نهایی


def debug_log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")


# ============================================================================
# توابع
# ============================================================================

def has_persian(text):
    if not text:
        return False
    return bool(re.search(
        r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff'
        r'\ufb50-\ufdff\ufe70-\ufeff'
        r'\u0621-\u063a\u0641-\u064a\u0660-\u0669]',
        text
    ))


def has_math(text):
    if not text:
        return False
    patterns = [
        r'\d', r'=', r'\+', r'-', r'\*', r'/', r'\^',
        r'sqrt', r'sin', r'cos', r'tan', r'log', r'ln', r'exp',
        r'pi', r'Delta', r'alpha', r'beta', r'gamma', r'theta',
        r'[xyznXYZn]', r'[\(\)\[\]]',
        r'[≤≥≠±×÷√∞πΔ]', r'[²³⁴⁵⁶⁷⁸⁹⁰¹₀₁₂₃₄₅₆₇₈₉]',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def clean_unicode(text):
    """تبدیل یونیکد به ASCII - فقط کاراکترهایی که SymPy نمیفهمه"""
    if not text:
        return ""
    t = text

    # حذف کاراکترهای مزاحم
    t = re.sub(r'[•●○◆◇►→←⇒⇐\u200b-\u200f\u2026\u201c\u201d\u2018\u2019]', '', t)
    t = re.sub(r'[−–—―\u2010-\u2015]', '-', t)

    # تبدیل یونیکد ریاضی
    replacements = [
        # زیرنویس‌ها (SymPy نمیفهمه)
        ('₁', '_1'), ('₂', '_2'), ('₃', '_3'), ('₄', '_4'), ('₅', '_5'),
        ('₆', '_6'), ('₇', '_7'), ('₈', '_8'), ('₉', '_9'), ('₀', '_0'),
        # توان‌ها
        ('²', '^2'), ('³', '^3'), ('⁴', '^4'), ('⁵', '^5'),
        ('⁶', '^6'), ('⁷', '^7'), ('⁸', '^8'), ('⁹', '^9'),
        ('⁰', '^0'), ('¹', '^1'),
        # عملگرها
        ('×', '*'), ('÷', '/'), ('±', '+-'),
        # نمادها
        ('√', 'sqrt('),  # باز کردن پرانتز برای sqrt
        ('∞', 'oo'), ('π', 'pi'),
        ('≤', '<='), ('≥', '>='), ('≠', '!='),
        # یونانی
        ('Δ', 'Delta'), ('Ω', 'Omega'), ('Σ', 'Sigma'), ('Π', 'Pi'),
        ('α', 'alpha'), ('β', 'beta'), ('γ', 'gamma'), ('δ', 'delta'),
        ('θ', 'theta'), ('λ', 'lambda'), ('μ', 'mu'),
        ('σ', 'sigma'), ('φ', 'phi'), ('ω', 'omega'),
    ]

    for old, new in replacements:
        t = t.replace(old, new)

    # بستن پرانتز sqrt اگر باز مونده
    # sqrt( -> باید پرانتزش بسته بشه
    t = re.sub(r'sqrt\(([^)]*)$', r'sqrt(\1)', t)

    t = re.sub(r'\s+', ' ', t).strip()
    return t


def split_by_equals(text):
    """تقسیم هوشمند متن بر اساس = (فقط اولین = معادله)"""
    if '=' not in text:
        return text, None

    # اگر چند تا = داره (مثل a=1, b=5)
    # فقط اولین = رو به عنوان معادله در نظر بگیر
    parts = text.split('=', 1)
    return parts[0].strip(), parts[1].strip() if len(parts) > 1 else None


# ============================================================================
# فونت و رنگ
# ============================================================================

class FontManager:
    @classmethod
    def math(cls, size=12, bold=False):
        f = QFont("Consolas", size)
        f.setBold(bold)
        f.setStyleHint(QFont.StyleHint.Monospace)
        return f

    @classmethod
    def ui(cls, size=12, bold=False):
        f = QFont("B Nazanin", size)
        f.setBold(bold)
        f.setStyleHint(QFont.StyleHint.SansSerif)
        return f


class Colors:
    DARK = {
        'bg': '#0d1117', 'surface': '#161b22', 'surface_raised': '#1c2129',
        'border': '#30363d', 'text': '#e6edf3', 'text_secondary': '#8b949e',
        'text_muted': '#6e7681', 'accent': '#7c6ff7', 'accent_hover': '#9488ff',
        'accent_text': '#ffffff', 'success': '#3fb950', 'error': '#f85149',
        'input_bg': '#0d1117', 'input_border': '#30363d', 'input_focus': '#7c6ff7',
        'scrollbar_handle': '#30363d', 'latex_bg': '#1a1f2e',
        'shadow': QColor(0,0,0,80),
    }
    LIGHT = {
        'bg': '#f6f8fa', 'surface': '#ffffff', 'surface_raised': '#f6f8fa',
        'border': '#d0d7de', 'text': '#1f2328', 'text_secondary': '#656d76',
        'text_muted': '#8b949e', 'accent': '#6355d8', 'accent_hover': '#7c6ff7',
        'accent_text': '#ffffff', 'success': '#1a7f37', 'error': '#cf222e',
        'input_bg': '#ffffff', 'input_border': '#d0d7de', 'input_focus': '#6355d8',
        'scrollbar_handle': '#d0d7de', 'latex_bg': '#fafbfc',
        'shadow': QColor(0,0,0,30),
    }


def stylesheet(c):
    return f"""
    QWidget {{ background: {c['bg']}; color: {c['text']}; font-size: 13px; }}
    QTextEdit {{
        background: {c['input_bg']}; color: {c['text']};
        border: 2px solid {c['input_border']}; border-radius: 8px;
        padding: 10px 14px; font: 14px 'Consolas',monospace;
        selection-background-color: {c['accent']}; selection-color: {c['accent_text']};
    }}
    QTextEdit:focus {{ border-color: {c['input_focus']}; }}
    QPushButton {{
        background: {c['surface_raised']}; color: {c['text']};
        border: 2px solid {c['border']}; border-radius: 7px;
        padding: 8px 16px; font: bold 13px 'B Nazanin'; min-height: 28px;
    }}
    QPushButton:hover {{ background: {c['border']}; border-color: {c['accent']}; }}
    QPushButton:pressed {{ background: {c['accent']}; color: {c['accent_text']}; }}
    QPushButton:disabled {{ background: {c['surface']}; color: {c['text_muted']}; }}
    QPushButton#accentBtn {{
        background: {c['accent']}; color: {c['accent_text']}; border: none;
        font-size: 14px; padding: 12px 24px; border-radius: 8px;
    }}
    QPushButton#accentBtn:hover {{ background: {c['accent_hover']}; }}
    QPushButton#iconBtn {{
        background: transparent; border: 1px solid {c['border']};
        border-radius: 6px; padding: 4px; min-width: 30px; min-height: 30px; font-size: 15px;
    }}
    QPushButton#iconBtn:hover {{ background: {c['border']}; }}
    QPushButton#toggleBtn {{
        background: {c['surface']}; color: {c['text_muted']};
        border: 1px solid {c['border']}; border-radius: 6px;
        padding: 4px 8px; font-size: 16px; min-width: 30px; min-height: 30px;
    }}
    QPushButton#toggleBtn:hover {{ background: {c['border']}; color: {c['text']}; }}
    QPushButton#toggleBtn[active="true"] {{
        background: {c['accent']}; color: {c['accent_text']}; border-color: {c['accent']};
    }}
    QPushButton#historyItem {{
        background: {c['surface']}; color: {c['text']};
        border: none; border-left: 3px solid {c['accent']};
        border-radius: 0; padding: 5px 8px; font: 10px 'Consolas',monospace;
        text-align: left; min-height: 22px;
    }}
    QPushButton#historyItem:hover {{ background: {c['surface_raised']}; border-left-width: 5px; }}
    QPushButton#historyItem[success="true"] {{ border-left-color: {c['success']}; }}
    QPushButton#historyItem[success="false"] {{ border-left-color: {c['error']}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 7px; }}
    QScrollBar::handle:vertical {{ background: {c['scrollbar_handle']}; border-radius: 3px; min-height: 25px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ height: 0; }}
    QFrame#card {{ background: {c['surface']}; border: 2px solid {c['border']}; border-radius: 10px; }}
    QLabel#titleLabel {{ color: {c['accent']}; font: bold 14px 'B Nazanin'; }}
    QLabel#statusLabel {{
        color: {c['text_secondary']}; font: 11px 'B Nazanin';
        padding: 5px 10px; background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 5px;
    }}
    QLabel#mathImage {{ background: transparent; border: none; padding: 0; }}
    QSplitter::handle {{ background: {c['border']}; width: 2px; }}
    """


# ============================================================================
# رندرر کاملاً بازنویسی شده
# ============================================================================

class MathRenderer:
    _cache = {}

    @classmethod
    def render(cls, text, text_color='#e6edf3', bg_color='#1a1f2e', font_size=13, dpi=150):
        if not text or not str(text).strip():
            return None

        original = str(text).strip()

        if has_persian(original) or not has_math(original):
            return None

        key = f"{original}|{text_color}|{bg_color}|{font_size}|{dpi}"
        if key in cls._cache:
            return cls._cache[key]

        # تمیز کردن یونیکد
        clean = clean_unicode(original)
        debug_log(f"render: '{original[:60]}' -> clean: '{clean[:60]}'")

        # تبدیل به LaTeX
        latex_str = cls._to_latex_safe(clean)
        if not latex_str:
            debug_log(f"render: _to_latex_safe returned None")
            return None

        debug_log(f"render: LaTeX = '{latex_str[:100]}'")

        # رندر
        result = cls._render_png(latex_str, text_color, bg_color, font_size, dpi)

        if result:
            if len(cls._cache) >= 100:
                cls._cache.pop(next(iter(cls._cache)))
            cls._cache[key] = result

        return result

    @classmethod
    def _to_latex_safe(cls, expr):
        """
        تبدیل امن به LaTeX.
        خطاهای regex رو catch میکنه و fallback میده.
        """
        # اول مطمئن شو که expr معتبره
        if not expr or not expr.strip():
            return None

        expr = expr.strip()

        # روش ۱: SymPy
        try:
            latex_str = cls._sympy_convert(expr)
            if latex_str:
                debug_log(f"_to_latex_safe: SymPy success")
                return latex_str
        except Exception as e:
            debug_log(f"_to_latex_safe: SymPy failed ({str(e)[:80]})")

        # روش ۲: تبدیل دستی امن
        try:
            latex_str = cls._manual_convert(expr)
            if latex_str:
                debug_log(f"_to_latex_safe: manual success")
                return latex_str
        except Exception as e:
            debug_log(f"_to_latex_safe: manual failed ({str(e)[:80]})")

        # روش ۳: فقط escape کاراکترهای خاص و نمایش
        try:
            safe = expr
            # فقط کاراکترهای خطرناک رو escape کن
            safe = safe.replace('\\', '\\backslash ')
            safe = safe.replace('{', '\\{')
            safe = safe.replace('}', '\\}')
            safe = safe.replace('_', '\\_')
            safe = safe.replace('&', '\\&')
            safe = safe.replace('%', '\\%')
            safe = safe.replace('$', '\\$')
            safe = safe.replace('#', '\\#')
            debug_log(f"_to_latex_safe: fallback escape -> '{safe[:80]}'")
            return safe
        except Exception:
            return None

    @classmethod
    def _sympy_convert(cls, expr):
        """تبدیل با SymPy - با مدیریت خطای بهتر"""
        # اگه چند تا = داره (مثل a=1, b=5)، فقط اولی رو معادله بگیر
        if expr.count('=') == 1:
            parts = expr.split('=', 1)
            lhs_str = parts[0].strip()
            rhs_str = parts[1].strip()

            if not lhs_str:
                return None

            try:
                lhs = parse_expr(lhs_str, transformations=TRANSFORMATIONS)
                rhs = parse_expr(rhs_str if rhs_str else '0', transformations=TRANSFORMATIONS)
                result = f"{sympy_latex(lhs)} = {sympy_latex(rhs)}"
                # تبدیل Delta و بقیه
                result = result.replace('Delta', '\\Delta')
                result = result.replace('alpha', '\\alpha')
                result = result.replace('beta', '\\beta')
                result = result.replace('gamma', '\\gamma')
                result = result.replace('theta', '\\theta')
                result = result.replace('lambda', '\\lambda')
                result = result.replace('mu', '\\mu')
                result = result.replace('sigma', '\\sigma')
                result = result.replace('phi', '\\phi')
                result = result.replace('omega', '\\omega')
                result = result.replace('pi', '\\pi')
                return result
            except Exception:
                pass

        # بدون = یا با چندتا = : تلاش برای parse کل عبارت
        try:
            parsed = parse_expr(expr, transformations=TRANSFORMATIONS)
            result = sympy_latex(parsed)
            result = result.replace('Delta', '\\Delta')
            result = result.replace('alpha', '\\alpha')
            result = result.replace('beta', '\\beta')
            result = result.replace('gamma', '\\gamma')
            result = result.replace('theta', '\\theta')
            result = result.replace('lambda', '\\lambda')
            result = result.replace('mu', '\\mu')
            result = result.replace('sigma', '\\sigma')
            result = result.replace('phi', '\\phi')
            result = result.replace('omega', '\\omega')
            result = result.replace('pi', '\\pi')
            return result
        except Exception:
            return None

    @classmethod
    def _manual_convert(cls, expr):
        """تبدیل دستی - با regex امن"""
        result = expr

        # این ترتیب مهمه!

        # 1. sqrt(expr) -> \\sqrt{expr}
        result = re.sub(r'sqrt\(([^()]*(?:\([^()]*\)[^()]*)*)\)', r'\\sqrt{\1}', result)
        result = re.sub(r'sqrt(\d+)', r'\\sqrt{\1}', result)
        result = re.sub(r'sqrt([a-zA-Z])', r'\\sqrt{\1}', result)

        # 2. توان‌ها
        result = re.sub(r'\^(\d+)', r'^{\1}', result)
        result = re.sub(r'\^([a-zA-Z])', r'^{\1}', result)

        # 3. توابع
        for func in ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'exp', 'abs']:
            result = re.sub(rf'\b({func})\b', rf'\\{func}', result)

        # 4. کسر
        result = re.sub(r'(\w+)\s*/\s*(\w+)', r'\\frac{\1}{\2}', result)

        # 5. یونانی (با \\ نه \D که regex رو خراب میکنه)
        greek_map = {
            'Delta': '\\\\Delta', 'Gamma': '\\\\Gamma', 'Theta': '\\\\Theta',
            'alpha': '\\\\alpha', 'beta': '\\\\beta', 'gamma': '\\\\gamma',
            'delta': '\\\\delta', 'theta': '\\\\theta', 'lambda': '\\\\lambda',
            'mu': '\\\\mu', 'sigma': '\\\\sigma', 'phi': '\\\\phi',
            'omega': '\\\\omega', 'pi': '\\\\pi', 'Sigma': '\\\\Sigma',
            'Omega': '\\\\Omega', 'Pi': '\\\\Pi', 'epsilon': '\\\\epsilon',
        }
        for word, latex_cmd in greek_map.items():
            result = re.sub(rf'\b{word}\b', latex_cmd, result)

        # 6. پرانتز
        result = result.replace('[', '{').replace(']', '}')

        # 7. بستن آکولادهای باز
        open_count = result.count('{')
        close_count = result.count('}')
        if open_count > close_count:
            result += '}' * (open_count - close_count)

        return result

    @classmethod
    def _render_png(cls, latex_str, text_color, bg_color, font_size, dpi):
        """رندر LaTeX به PNG"""
        try:
            fig, ax = plt.subplots(figsize=(6, 0.5), dpi=dpi, facecolor=bg_color, edgecolor='none')
            ax.set_facecolor(bg_color)
            ax.axis('off')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)

            math_str = f"${latex_str}$"

            text_obj = ax.text(
                0.5, 0.5, math_str,
                fontsize=font_size, color=text_color,
                ha='center', va='center',
                fontfamily='serif', math_fontfamily='stix'
            )

            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

            try:
                bbox = text_obj.get_tightbbox(renderer)
            except:
                bbox = text_obj.get_window_extent(renderer)

            if bbox is None or bbox.width == 0 or bbox.height == 0:
                plt.close(fig)
                return None

            bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

            w = max(0.3, bbox_inches.width * 1.1)
            h = max(0.2, bbox_inches.height * 1.2)
            fig.set_size_inches(w, h)

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.05,
                       facecolor=bg_color, edgecolor='none')
            plt.close(fig)

            buf.seek(0)
            return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

        except Exception:
            return None

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()


# ============================================================================
# ویجت‌ها
# ============================================================================

class MathImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mathImage")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(20)
        self._orig = None
        self._last_w = 0

    def set_image(self, b64):
        if not b64:
            self.hide()
            return
        try:
            data = b64.split(',',1)[1] if ',' in b64 else b64
            pix = QPixmap()
            if pix.loadFromData(base64.b64decode(data), 'PNG') and not pix.isNull():
                self._orig = pix
                self._last_w = 0
                self._scale()
                self.show()
        except:
            self.hide()

    def _scale(self):
        if not self._orig:
            return
        avail = max(50, self.width() - 12)
        ow = self._orig.width()
        target = min(avail, int(ow * 1.2))
        if abs(target - self._last_w) < 8:
            return
        scaled = self._orig.scaledToWidth(target, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
        self._last_w = target
        self.setFixedHeight(scaled.height() + 6)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._orig:
            self._scale()


class MathInput(QTextEdit):
    equationSubmitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(FontManager.math(14))
        self.setPlaceholderText("x^2 - 5x + 6 = 0")
        self.setMaximumHeight(48)
        self.setMinimumHeight(42)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Return and not e.modifiers():
            t = self.toPlainText().strip()
            if t:
                self.equationSubmitted.emit(t)
            return
        super().keyPressEvent(e)


class StepWidget(QFrame):
    def __init__(self, step, colors, num, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        c = colors

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setOffset(0, 1)
        shadow.setColor(c['shadow'])
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        num_lbl = QLabel(str(num))
        num_lbl.setFixedSize(26, 26)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_lbl.setFont(FontManager.math(11, True))
        num_lbl.setStyleSheet(f"background:{c['accent']};color:{c['accent_text']};border-radius:13px;")
        layout.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(4)
        content.setContentsMargins(0, 0, 0, 0)

        title = QLabel(step.title)
        title.setFont(FontManager.ui(13, True))
        title.setStyleSheet(f"color:{c['accent']};")
        content.addWidget(title)

        if step.mathematical_expression:
            self._show(content, str(step.mathematical_expression), c, True)

        self._show(content, step.description, c, False)

        layout.addLayout(content, 1)

    def _show(self, layout, text, c, is_primary):
        if not text or not text.strip():
            return

        if has_persian(text):
            self._add_label(layout, text, c, is_primary)
            return

        if has_math(text):
            b64 = MathRenderer.render(
                text,
                c['text'] if is_primary else c['text_secondary'],
                c['latex_bg'],
                13 if is_primary else 11,
                150 if is_primary else 130
            )
            if b64:
                img = MathImageLabel()
                img.set_image(b64)
                layout.addWidget(img)
                return

        self._add_label(layout, text, c, is_primary)

    def _add_label(self, layout, text, c, is_primary):
        lbl = QLabel(text)
        if is_primary:
            lbl.setFont(FontManager.math(12, True))
            lbl.setStyleSheet(f"color:{c['accent']};background:{c['latex_bg']};padding:4px 8px;border-radius:3px;border-left:2px solid {c['accent']};")
        else:
            lbl.setFont(FontManager.math(11))
            lbl.setStyleSheet(f"color:{c['text_secondary']};")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)


class HistoryPanel(QWidget):
    equationSelected = pyqtSignal(str)

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.setMinimumWidth(180)
        self.setMaximumWidth(240)
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0,0,0,0)
        hdr = QHBoxLayout()
        title = QLabel("📜 تاریخچه")
        title.setObjectName("titleLabel")
        title.setFont(FontManager.ui(13, True))
        hdr.addWidget(title, 1)
        clear_btn = QPushButton("🗑️")
        clear_btn.setObjectName("iconBtn")
        clear_btn.setFixedSize(26, 26)
        clear_btn.clicked.connect(self._clear)
        hdr.addWidget(clear_btn)
        layout.addLayout(hdr)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(2)
        self.list_layout.setContentsMargins(0,0,0,0)
        self.list_layout.addStretch()
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def add(self, equation, result, success):
        while self.list_layout.count() > 51:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        btn = QPushButton(equation[:26] + ("…" if len(equation) > 26 else ""))
        btn.setObjectName("historyItem")
        btn.setProperty("success", "true" if success else "false")
        btn.setFont(FontManager.math(10))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.equationSelected.emit(equation))
        self.list_layout.insertWidget(self.list_layout.count() - 1, btn)

    def _clear(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ============================================================================
# پنجره اصلی
# ============================================================================

class EquationSolverWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("حل کننده معادلات")

        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            w, h = max(1000, int(g.width()*0.7)), max(650, int(g.height()*0.7))
        else:
            w, h = 1050, 700
        self.setMinimumSize(900, 600)
        self.resize(w, h)

        self.settings = QSettings("MathAssistant", "FixedV12")
        self.is_dark = self.settings.value("dark_mode", True, type=bool)
        self.colors = Colors.DARK if self.is_dark else Colors.LIGHT
        self.engine = EquationSolverEngine()
        self.solution_cache = None
        self._history_visible = False

        self._build()
        self._connect()
        self._apply_theme()
        self._init_history_state()

        g = self.settings.value("geometry")
        if g:
            self.restoreGeometry(g)

    def _init_history_state(self):
        self.history.setVisible(False)
        self.toggle_btn.setProperty("active", "false")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        self.main_splitter.setSizes([0, 820, 160])
        self.main_splitter.updateGeometry()
        self.update()
        QApplication.processEvents()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 8, 12, 8)

        hdr = QHBoxLayout()
        self.toggle_btn = QPushButton("📜")
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.setFixedSize(32, 32)
        hdr.addWidget(self.toggle_btn)
        title = QLabel("🧮 حل کننده معادلات پیشرفته")
        title.setObjectName("titleLabel")
        title.setFont(FontManager.ui(16, True))
        hdr.addWidget(title, 1)
        help_btn = QPushButton("❓")
        help_btn.setObjectName("iconBtn")
        help_btn.setFixedSize(30, 30)
        help_btn.clicked.connect(self._help)
        hdr.addWidget(help_btn)
        self.theme_btn = QPushButton("🌙" if self.is_dark else "☀️")
        self.theme_btn.setObjectName("iconBtn")
        self.theme_btn.setFixedSize(30, 30)
        hdr.addWidget(self.theme_btn)
        root.addLayout(hdr)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        self.history = HistoryPanel(self.colors)
        self.main_splitter.addWidget(self.history)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setSpacing(8)
        cl.setContentsMargins(0,0,0,0)
        cl.addWidget(self._input_card())
        cl.addWidget(self._output_card(), 1)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self._stats_card())
        self.main_splitter.setSizes([0, 820, 160])
        root.addWidget(self.main_splitter, 1)

        self.status = QLabel("👋 آماده...")
        self.status.setObjectName("statusLabel")
        self.status.setFont(FontManager.ui(11))
        root.addWidget(self.status)

    def _input_card(self):
        card = QFrame()
        card.setObjectName("card")
        l = QVBoxLayout(card)
        l.setSpacing(8)
        l.setContentsMargins(12, 10, 12, 10)
        hdr = QHBoxLayout()
        t = QLabel("✏️ معادله")
        t.setObjectName("titleLabel")
        t.setFont(FontManager.ui(14, True))
        hdr.addWidget(t, 1)
        clr = QPushButton("✕")
        clr.setObjectName("iconBtn")
        clr.setFixedSize(26, 26)
        clr.clicked.connect(self._clear_input)
        hdr.addWidget(clr)
        l.addLayout(hdr)
        self.input = MathInput()
        l.addWidget(self.input)
        btns = QHBoxLayout()
        self.solve_btn = QPushButton("🚀 حل معادله")
        self.solve_btn.setObjectName("accentBtn")
        self.solve_btn.setFont(FontManager.ui(14, True))
        self.solve_btn.setMinimumHeight(40)
        self.export_btn = QPushButton("📤 ذخیره")
        self.export_btn.setFont(FontManager.ui(13, True))
        self.export_btn.setMinimumHeight(40)
        self.export_btn.setEnabled(False)
        btns.addWidget(self.solve_btn, 3)
        btns.addWidget(self.export_btn, 1)
        l.addLayout(btns)
        return card

    def _output_card(self):
        card = QFrame()
        card.setObjectName("card")
        l = QVBoxLayout(card)
        l.setSpacing(6)
        l.setContentsMargins(10, 8, 10, 8)
        hdr = QHBoxLayout()
        t = QLabel("📝 گام‌های حل")
        t.setObjectName("titleLabel")
        t.setFont(FontManager.ui(14, True))
        hdr.addWidget(t, 1)
        self.stat_summary = QLabel("")
        self.stat_summary.setFont(FontManager.ui(11))
        self.stat_summary.setStyleSheet(f"color:{self.colors['text_secondary']};")
        hdr.addWidget(self.stat_summary)
        l.addLayout(hdr)
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.steps_widget = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_widget)
        self.steps_layout.setSpacing(4)
        self.steps_layout.setContentsMargins(0,0,0,0)
        self.steps_layout.addStretch()
        self.steps_scroll.setWidget(self.steps_widget)
        l.addWidget(self.steps_scroll, 1)
        return card

    def _stats_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(150)
        card.setMaximumWidth(185)
        l = QVBoxLayout(card)
        l.setSpacing(5)
        l.setContentsMargins(8, 8, 8, 8)
        t = QLabel("📊 آمار")
        t.setObjectName("titleLabel")
        t.setFont(FontManager.ui(14, True))
        l.addWidget(t)
        self.stats = {}
        for key in ['type','time','count','degree','complex']:
            lbl = QLabel("—")
            lbl.setFont(FontManager.ui(11))
            lbl.setStyleSheet(f"color:{self.colors['text_secondary']};")
            lbl.setWordWrap(True)
            l.addWidget(lbl)
            self.stats[key] = lbl
        l.addStretch()
        return card

    def _connect(self):
        self.input.equationSubmitted.connect(self._solve)
        self.solve_btn.clicked.connect(lambda: self._solve(self.input.toPlainText().strip()))
        self.export_btn.clicked.connect(self._export)
        self.toggle_btn.clicked.connect(self._toggle_history)
        self.history.equationSelected.connect(self._load_history)
        self.theme_btn.clicked.connect(self._toggle_theme)

    @pyqtSlot(str)
    def _solve(self, eq):
        if not eq:
            return
        self.solve_btn.setEnabled(False)
        self.solve_btn.setText("⏳ ...")
        self.status.setText("⏳ در حال حل...")
        QApplication.processEvents()
        self._thread = SolveThread(self.engine, eq)
        self._thread.finished.connect(self._done)
        self._thread.error.connect(self._err)
        self._thread.start()

    @pyqtSlot(EquationSolution)
    def _done(self, sol):
        self.solve_btn.setEnabled(True)
        self.solve_btn.setText("🚀 حل معادله")
        self.export_btn.setEnabled(True)
        self.solution_cache = sol

        while self.steps_layout.count() > 1:
            item = self.steps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        MathRenderer.clear_cache()

        for i, step in enumerate(sol.steps, 1):
            w = StepWidget(step, self.colors, i)
            self.steps_layout.insertWidget(self.steps_layout.count() - 1, w)

        names = {'LINEAR':'خطی','QUADRATIC':'درجه۲','CUBIC':'درجه۳','POLYNOMIAL':'چندجمله‌ای','RATIONAL':'گویا','SYSTEM':'دستگاه'}
        a = sol.analysis
        t = names.get(a.equation_type.name, 'نامشخص')
        self.stats['type'].setText(f"نوع: {t}")
        self.stats['time'].setText(f"زمان: {sol.execution_time_ms:.0f}ms")
        self.stats['count'].setText(f"جواب: {sol.solution_count}")
        self.stats['degree'].setText(f"درجه: {a.degree}")
        self.stats['complex'].setText(f"پیچیدگی: {a.complexity_score:.0%}")
        self.stat_summary.setText(f"{t} | {str(sol.solutions)[:25]}")
        self.history.add(sol.original_equation, str(sol.solutions)[:40], sol.solution_count > 0)
        self.status.setText(f"✅ حل شد — {sol.solution_count} جواب | {sol.execution_time_ms:.0f}ms")
        self.steps_scroll.verticalScrollBar().setValue(0)

    @pyqtSlot(str)
    def _err(self, msg):
        self.solve_btn.setEnabled(True)
        self.solve_btn.setText("🚀 حل معادله")
        self.status.setText(f"❌ {msg}")

    def _clear_input(self):
        self.input.clear()
        self.input.setFocus()

    @pyqtSlot(str)
    def _load_history(self, eq):
        self.input.setPlainText(eq)
        self.input.setFocus()

    def _toggle_history(self):
        self._history_visible = not self._history_visible
        self.history.setVisible(self._history_visible)
        self.toggle_btn.setProperty("active", "true" if self._history_visible else "false")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        self.main_splitter.setSizes([200, 620, 160] if self._history_visible else [0, 820, 160])
        self.main_splitter.updateGeometry()
        self.update()
        QApplication.processEvents()

    def _export(self):
        if not self.solution_cache:
            QMessageBox.information(self, "توجه", "ابتدا حل کنید.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره", "", "Text (*.txt);;JSON (*.json)")
        if not path:
            return
        try:
            s = self.solution_cache
            if path.endswith('.json'):
                json.dump({'equation':s.original_equation,'solutions':str(s.solutions),'steps':[{'title':st.title,'description':st.description} for st in s.steps]}, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
            else:
                with open(path,'w',encoding='utf-8') as f:
                    f.write(f"معادله: {s.original_equation}\n\n")
                    for i,st in enumerate(s.steps,1):
                        f.write(f"گام {i}: {st.title}\n{st.description}\n\n")
                    f.write(f"جواب: {s.solutions}\n")
            self.status.setText("✅ ذخیره شد")
        except Exception as e:
            QMessageBox.critical(self,"خطا",str(e))

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.colors = Colors.DARK if self.is_dark else Colors.LIGHT
        self.theme_btn.setText("🌙" if self.is_dark else "☀️")
        self.settings.setValue("dark_mode", self.is_dark)
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(stylesheet(self.colors))
        self.stat_summary.setStyleSheet(f"color:{self.colors['text_secondary']};")
        for lbl in self.stats.values():
            lbl.setStyleSheet(f"color:{self.colors['text_secondary']};")
        self.history.colors = self.colors

    def _help(self):
        QMessageBox.information(self,"راهنما","📚 نحوه وارد کردن:\n\n• x^2 - 5x + 6 = 0\n• 2x + 5 = 10\n• sin(x) + cos(x) = 1\n\n📜 تاریخچه: باز/بسته\n⌨️ Enter: حل")

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(e)


class SolveThread(QThread):
    finished = pyqtSignal(EquationSolution)
    error = pyqtSignal(str)

    def __init__(self, engine, equation):
        super().__init__()
        self.engine = engine
        self.equation = equation

    def run(self):
        try:
            self.finished.emit(self.engine.solve(self.equation))
        except Exception as e:
            self.error.emit(str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MathAssistant Pro")
    app.setFont(FontManager.ui(11))
    app.setStyle('Fusion')
    w = EquationSolverWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
