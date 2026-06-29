# src/MathAssistant/ui/equation_solver_ui.py
"""
MathAssistant Pro - نسخه پلاتینیوم نهایی با تست‌های کامل

Author: AmirMohammad Ghasemzadeh
Version: 13.3.1 - Platinum Final Edition (Hotfix)
"""

import sys
import json
import io
import base64
import re
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import OrderedDict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QScrollArea, QFrame,
    QApplication, QMessageBox, QFileDialog,
    QSizePolicy, QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QThread, QSettings,
    QTimer, QMutex, QMutexLocker
)
from PyQt6.QtGui import (
    QFont, QColor, QPixmap, QKeySequence, QShortcut
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

# Import regex with fallback
try:
    import regex as advanced_regex # type: ignore
    HAS_ADVANCED_REGEX = True
except ImportError:
    HAS_ADVANCED_REGEX = False

try:
    from ..core.equation_solver import EquationSolverEngine, EquationSolution, SolutionStep
except ImportError:
    from equation_solver import EquationSolverEngine, EquationSolution, SolutionStep # type: ignore

TRANSFORMATIONS = (
    standard_transformations +
    (implicit_multiplication_application, convert_xor)
)

# تنظیمات امنیتی و عملکردی
MAX_INPUT_LENGTH = 500
REGEX_TIMEOUT = 1.0
MAX_NESTING_DEPTH = 5
MAX_CACHE_SIZE = 200
MAX_HISTORY_ITEMS = 50
SQRT_LIST_THRESHOLD = 100

DEBUG = False


def debug_log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")


# ============================================================================
# تست‌های داخلی - نسخه کامل
# ============================================================================

class MathRendererTests:
    """تست‌های جامع برای توابع تبدیل"""

    @staticmethod
    def run_all():
        """اجرای تمام تست‌ها و بازگشت (passed, failed)"""
        tests = [
            # تست‌های پایه
            MathRendererTests.test_sqrt_simple,
            MathRendererTests.test_sqrt_nested,
            MathRendererTests.test_sqrt_deep_nesting,
            MathRendererTests.test_sqrt_no_sqrt,
            MathRendererTests.test_sqrt_complex,
            MathRendererTests.test_sqrt_edge_cases,

            # تست یکسانی الگوریتم‌ها
            MathRendererTests.test_sqrt_algorithms_identical,

            # تست حروف یونانی
            MathRendererTests.test_greek_letters,
            MathRendererTests.test_greek_mixed,
            MathRendererTests.test_greek_compound_words,

            # تست‌های مرزی
            MathRendererTests.test_empty_inputs,

            # تست اعتبارسنجی ورودی
            MathRendererTests.test_input_validation,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
                debug_log(f"✅ {test.__name__} passed")
            except AssertionError as e:
                failed += 1
                debug_log(f"❌ {test.__name__} FAILED: {str(e)}")
            except Exception as e:
                failed += 1
                debug_log(f"💥 {test.__name__} ERROR: {str(e)}")

        if DEBUG or "--test" in sys.argv:
            print(f"\n📊 Test Results: {passed} passed, {failed} failed")

        return passed, failed

    @staticmethod
    def test_sqrt_simple():
        """تست تبدیل sqrt ساده"""
        result = MathRenderer._convert_sqrt_safe("sqrt(4)")
        assert "\\sqrt{4}" in result, f"Expected \\sqrt{{4}}, got {result}"

    @staticmethod
    def test_sqrt_nested():
        """تست sqrt تو در تو"""
        result = MathRenderer._convert_sqrt_safe("sqrt(sqrt(16))")
        assert "\\sqrt{\\sqrt{16}}" in result, f"Expected nested sqrt, got {result}"

    @staticmethod
    def test_sqrt_deep_nesting():
        """تست sqrt با عمق MAX_NESTING_DEPTH"""
        depth = MAX_NESTING_DEPTH
        # ایجاد عبارت با عمق دقیق
        expr = "sqrt(" * depth + "32" + ")" * depth
        result = MathRenderer._convert_sqrt_safe(expr)
        assert result.count("\\sqrt{") >= depth, \
            f"Expected at least {depth} sqrt, got {result.count('\\sqrt{')}"

    @staticmethod
    def test_sqrt_no_sqrt():
        """تست عبارت بدون sqrt"""
        result = MathRenderer._convert_sqrt_safe("x^2 + 5")
        assert result == "x^2 + 5", f"Expected no change, got {result}"

    @staticmethod
    def test_sqrt_complex():
        """تست عبارت با چند sqrt"""
        result = MathRenderer._convert_sqrt_safe("sqrt(x^2 + 5) + sqrt(9)")
        assert result.count("\\sqrt{") == 2, \
            f"Expected 2 sqrt, got {result.count('\\sqrt{')}"

    @staticmethod
    def test_sqrt_edge_cases():
        """تست موارد مرزی sqrt"""
        # شروع با sqrt
        assert "\\sqrt{x}" in MathRenderer._convert_sqrt_safe("sqrt(x)")

        # چند sqrt با متغیرهای مختلف
        result = MathRenderer._convert_sqrt_safe("sqrt(x) + sqrt(y)")
        assert result.count("\\sqrt{") == 2
        assert "\\sqrt{x}" in result
        assert "\\sqrt{y}" in result

        # بدون sqrt - نباید تغییر کند
        assert MathRenderer._convert_sqrt_safe("no sqrt here") == "no sqrt here"

        # sqrt در انتهای عبارت
        result = MathRenderer._convert_sqrt_safe("x + sqrt(y)")
        assert "\\sqrt{y}" in result

        # عبارت خالی
        assert MathRenderer._convert_sqrt_safe("") == ""

    @staticmethod
    def test_sqrt_algorithms_identical():
        """تست یکسانی خروجی دو الگوریتم"""
        test_cases = [
            "sqrt(x)",
            "sqrt(x+1)",
            "sqrt(sqrt(16))",
            "sqrt(x^2 + 5) + sqrt(9)",
            "x + sqrt(y) + z",
            "sqrt(a) + sqrt(b) + sqrt(c)",
            "sqrt(sqrt(sqrt(8)))",
            "2*sqrt(x) + 3*sqrt(y)",
            "sqrt(x^2 + y^2)",
            "1 + sqrt(4) + sqrt(9) + sqrt(16)",
        ]

        for case in test_cases:
            result_list = MathRenderer._convert_sqrt_list(case, MAX_NESTING_DEPTH)
            result_fast = MathRenderer._convert_sqrt_fast(case, MAX_NESTING_DEPTH)
            assert result_list == result_fast, \
                f"Algorithm mismatch for '{case}':\n  list: '{result_list}'\n  fast: '{result_fast}'"

    @staticmethod
    def test_greek_letters():
        """تست تبدیل حروف یونانی"""
        result = MathRenderer._fix_greek_letters("Delta + alpha + pi")
        assert "\\Delta" in result, f"Expected \\Delta, got {result}"
        assert "\\alpha" in result, f"Expected \\alpha, got {result}"
        assert "\\pi" in result, f"Expected \\pi, got {result}"

    @staticmethod
    def test_greek_mixed():
        """تست حروف یونانی در ترکیب با عبارات"""
        result = MathRenderer._fix_greek_letters("sin(theta) + Delta^2")
        assert "\\theta" in result, f"Expected \\theta, got {result}"
        assert "\\Delta" in result, f"Expected \\Delta, got {result}"

    @staticmethod
    def test_greek_compound_words():
        """تست حروف یونانی در کلمات ترکیبی"""
        # Delta در وسط کلمه نباید تبدیل شود
        result = MathRenderer._fix_greek_letters("myDeltaVar + realDelta")
        assert "\\Delta" not in result, \
            f"Delta in compound word should NOT be converted, got {result}"

        # اما Delta به تنهایی باید تبدیل شود
        result2 = MathRenderer._fix_greek_letters("Delta")
        assert result2 == "\\Delta", f"Standalone Delta should convert, got {result2}"

        # alpha در وسط کلمه
        result3 = MathRenderer._fix_greek_letters("alpha_beta + myalpha")
        assert "\\alpha" in result3, f"Standalone alpha should convert"
        assert result3.count("\\alpha") == 1, \
            f"Only standalone alpha should convert, got {result3}"

    @staticmethod
    def test_empty_inputs():
        """تست ورودی‌های خالی"""
        assert MathRenderer._convert_sqrt_safe("") == ""
        assert MathRenderer._fix_greek_letters("") == ""
        assert MathRenderer._to_latex_safe("") is None
        assert MathRenderer._to_latex_safe(None) is None

    @staticmethod
    def test_input_validation():
        """تست اعتبارسنجی ورودی"""
        # ورودی‌های معتبر
        try:
            InputValidator.validate("x^2 - 5x + 6 = 0")
            InputValidator.validate("2*x + 5 = 10")
            InputValidator.validate("sin(x) + cos(x) = 1")
            InputValidator.validate("sqrt(x^2 + y^2)")
            InputValidator.validate("x + y = 5")
            InputValidator.validate("Delta + alpha = pi")
        except ValueError as e:
            assert False, f"Valid input rejected: {str(e)}"

        # ورودی نامعتبر - طول زیاد
        try:
            InputValidator.validate("x" * (MAX_INPUT_LENGTH + 1))
            assert False, "Should reject long input"
        except ValueError:
            pass


# ============================================================================
# توابع امنیتی و کمکی
# ============================================================================

class InputValidator:
    """اعتبارسنجی امن ورودی‌ها"""

    PERSIAN_WORDS = [
        'معادله', 'جواب', 'حل', 'مساوی', 'برابر', 'بزرگتر', 'کوچکتر',
        'جذر', 'توان', 'ضربدر', 'تقسیم', 'بعلاوه', 'منهای', 'سینوس',
        'کسینوس', 'تانژانت', 'لگاریتم', 'نپر', 'مشتق', 'انتگرال', 'حد'
    ]

    # الگوی کاراکترهای مجاز - فقط کاراکترهای غیرمجاز را پیدا می‌کند
    ALLOWED_CHARS_PATTERN = re.compile(
        r'^[\w\s\+\-\*/\^\(\)\[\]\{\}\.\,\=<>!|&'
        r'°′″‴'
        r'₁₂₃₄₅₆₇₈₉₀²³⁴⁵⁶⁷⁸⁹⁰¹'
        r'αβγδεζηθικλμνξπρστυφχψω'
        r'ΔΘΛΞΠΣΦΨΩ'
        r'×÷±≤≥≠√∞π'
        r'\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff'  # Persian/Arabic
        r'\ufb50-\ufdff\ufe70-\ufeff'
        r']*$'
    )

    DANGEROUS_PATTERNS = [
        (re.compile(r'[\'";`]'), 'کاراکتر کنترلی'),
        (re.compile(r'__(?:import|eval|exec|open|file)__'), 'دسترسی ممنوعه'),
        (re.compile(r'\bos\.'), 'دسترسی سیستمی ممنوع'),
        (re.compile(r'\bsubprocess\b'), 'اجرای کد ممنوع'),
        (re.compile(r'<script'), 'اسکریپت ممنوع'),
    ]

    @classmethod
    def validate(cls, expr: str) -> str:
        """اعتبارسنجی کامل ورودی"""
        if not expr or not expr.strip():
            raise ValueError("ورودی خالی است")

        expr = expr.strip()

        if len(expr) > MAX_INPUT_LENGTH:
            raise ValueError(
                f"عبارت خیلی طولانی است (حداکثر {MAX_INPUT_LENGTH} کاراکتر)\n"
                f"طول فعلی: {len(expr)}"
            )

        cleaned = cls._remove_persian_words(expr)

        # بررسی کاراکترهای نامعتبر با الگوی جدید
        invalid_chars = cls._find_invalid_chars(cleaned)
        if invalid_chars:
            raise ValueError(
                f"کاراکترهای نامعتبر شناسایی شد:\n{', '.join(sorted(invalid_chars))}\n"
                f"فقط کاراکترهای ریاضی مجاز هستند"
            )

        depth = cls._get_nesting_depth(cleaned)
        if depth > MAX_NESTING_DEPTH:
            raise ValueError(
                f"تعداد nested پرانتز بیش از حد مجاز است\n"
                f"حداکثر مجاز: {MAX_NESTING_DEPTH}\n"
                f"عمق فعلی: {depth}"
            )

        for pattern, msg in cls.DANGEROUS_PATTERNS:
            if pattern.search(cleaned):
                raise ValueError(f"الگوی خطرناک شناسایی شد: {msg}")

        return cleaned

    @classmethod
    def _remove_persian_words(cls, expr: str) -> str:
        """حذف کلمات فارسی"""
        result = expr
        for word in cls.PERSIAN_WORDS:
            result = re.sub(rf'\b{word}\b', '', result, flags=re.IGNORECASE)
        return ' '.join(result.split())

    @classmethod
    def _find_invalid_chars(cls, expr: str) -> set:
        """پیدا کردن کاراکترهای نامعتبر - فقط کاراکترهای واقعاً نامعتبر"""
        invalid = set()
        for char in expr:
            # اجازه دادن به کاراکترهای مجاز و فاصله
            if not char.isspace() and not cls._is_allowed_char(char):
                invalid.add(repr(char))
        return invalid

    @classmethod
    def _is_allowed_char(cls, char: str) -> bool:
        """بررسی مجاز بودن یک کاراکتر"""
        # حروف و اعداد
        if char.isalnum():
            return True
        # کاراکترهای ریاضی
        if char in '+-*/^()[]{}.=<>!|&°′″‴':
            return True
        # کاراکترهای یونیکد ریاضی
        if '\u2080' <= char <= '\u2089':  # subscript
            return True
        if '\u00B2' <= char <= '\u00B9':  # superscript
            return True
        # حروف یونانی
        if '\u0391' <= char <= '\u03C9':  # Greek
            return True
        # کاراکترهای خاص ریاضی
        if char in '×÷±≤≥≠√∞π₁₂₃₄₅₆₇₈₉₀²³⁴⁵⁶⁷⁸⁹⁰¹αβγδεζηθικλμνξπρστυφχψωΔΘΛΞΠΣΦΨΩ':
            return True
        # کاراکترهای فارسی/عربی
        if '\u0600' <= char <= '\u06ff' or \
           '\u0750' <= char <= '\u077f' or \
           '\u08a0' <= char <= '\u08ff' or \
           '\ufb50' <= char <= '\ufdff' or \
           '\ufe70' <= char <= '\ufeff':
            return True
        return False

    @classmethod
    def _get_nesting_depth(cls, expr: str) -> int:
        """محاسبه عمق nested"""
        max_depth = 0
        current = 0
        for char in expr:
            if char in '([{':
                current += 1
                max_depth = max(max_depth, current)
            elif char in ')]}':
                if current > 0:
                    current -= 1
        return max_depth


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
    """تبدیل یونیکد به ASCII"""
    if not text:
        return ""
    t = text

    t = re.sub(r'[•●○◆◇►→←⇒⇐\u200b-\u200f\u2026\u201c\u201d\u2018\u2019]', '', t)
    t = re.sub(r'[−–—―\u2010-\u2015]', '-', t)

    replacements = [
        ('₁', '_1'), ('₂', '_2'), ('₃', '_3'), ('₄', '_4'), ('₅', '_5'),
        ('₆', '_6'), ('₇', '_7'), ('₈', '_8'), ('₉', '_9'), ('₀', '_0'),
        ('²', '^2'), ('³', '^3'), ('⁴', '^4'), ('⁵', '^5'),
        ('⁶', '^6'), ('⁷', '^7'), ('⁸', '^8'), ('⁹', '^9'),
        ('⁰', '^0'), ('¹', '^1'),
        ('×', '*'), ('÷', '/'), ('±', '+-'),
        ('√', 'sqrt('),
        ('∞', 'oo'), ('π', 'pi'),
        ('≤', '<='), ('≥', '>='), ('≠', '!='),
        ('Δ', 'Delta'), ('Ω', 'Omega'), ('Σ', 'Sigma'), ('Π', 'Pi'),
        ('α', 'alpha'), ('β', 'beta'), ('γ', 'gamma'), ('δ', 'delta'),
        ('θ', 'theta'), ('λ', 'lambda'), ('μ', 'mu'),
        ('σ', 'sigma'), ('φ', 'phi'), ('ω', 'omega'),
    ]

    for old, new in replacements:
        t = t.replace(old, new)

    t = re.sub(r'sqrt\(([^)]*)$', r'sqrt(\1)', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


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
        'focus_highlight': '#58a6ff'
    }
    LIGHT = {
        'bg': '#f6f8fa', 'surface': '#ffffff', 'surface_raised': '#f6f8fa',
        'border': '#d0d7de', 'text': '#1f2328', 'text_secondary': '#656d76',
        'text_muted': '#8b949e', 'accent': '#6355d8', 'accent_hover': '#7c6ff7',
        'accent_text': '#ffffff', 'success': '#1a7f37', 'error': '#cf222e',
        'input_bg': '#ffffff', 'input_border': '#d0d7de', 'input_focus': '#6355d8',
        'scrollbar_handle': '#d0d7de', 'latex_bg': '#fafbfc',
        'shadow': QColor(0,0,0,30),
        'focus_highlight': '#0969da'
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
    QTextEdit:focus {{
        border-color: {c['input_focus']};
    }}
    QPushButton {{
        background: {c['surface_raised']}; color: {c['text']};
        border: 2px solid {c['border']}; border-radius: 7px;
        padding: 8px 16px; font: bold 13px 'B Nazanin'; min-height: 28px;
        outline: none;
    }}
    QPushButton:hover {{ background: {c['border']}; border-color: {c['accent']}; }}
    QPushButton:pressed {{ background: {c['accent']}; color: {c['accent_text']}; }}
    QPushButton:disabled {{ background: {c['surface']}; color: {c['text_muted']}; }}
    QPushButton:focus {{ outline: none; }}
    QPushButton#accentBtn {{
        background: {c['accent']}; color: {c['accent_text']}; border: none;
        font-size: 14px; padding: 12px 24px; border-radius: 8px;
        outline: none;
    }}
    QPushButton#accentBtn:hover {{ background: {c['accent_hover']}; }}
    QPushButton#accentBtn:focus {{ outline: none; }}
    QPushButton#iconBtn {{
        background: transparent; border: 1px solid {c['border']};
        border-radius: 6px; padding: 4px; min-width: 30px; min-height: 30px; font-size: 15px;
        outline: none;
    }}
    QPushButton#iconBtn:hover {{ background: {c['border']}; }}
    QPushButton#iconBtn:focus {{ outline: none; }}
    QPushButton#toggleBtn {{
        background: {c['surface']}; color: {c['text_muted']};
        border: 1px solid {c['border']}; border-radius: 6px;
        padding: 4px 8px; font-size: 16px; min-width: 30px; min-height: 30px;
        outline: none;
    }}
    QPushButton#toggleBtn:hover {{ background: {c['border']}; color: {c['text']}; }}
    QPushButton#toggleBtn[active="true"] {{
        background: {c['accent']}; color: {c['accent_text']}; border-color: {c['accent']};
    }}
    QPushButton#toggleBtn:focus {{ outline: none; }}
    QPushButton#historyItem {{
        background: {c['surface']}; color: {c['text']};
        border: none; border-left: 3px solid {c['accent']};
        border-radius: 0; padding: 5px 8px; font: 10px 'Consolas',monospace;
        text-align: left; min-height: 22px;
        outline: none;
    }}
    QPushButton#historyItem:hover {{ background: {c['surface_raised']}; border-left-width: 5px; }}
    QPushButton#historyItem:focus {{ outline: none; }}
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
    QToolTip {{
        background: {c['surface_raised']}; color: {c['text']};
        border: 1px solid {c['border']}; padding: 4px; border-radius: 4px;
        font: 11px 'B Nazanin';
    }}
    QMessageBox {{
        background: {c['surface']};
        color: {c['text']};
    }}
    QMessageBox QLabel {{
        color: {c['text']};
        font: 12px 'B Nazanin';
        selection-background-color: {c['accent']};
        selection-color: {c['accent_text']};
    }}
    QMessageBox QPushButton {{
        background: {c['surface_raised']};
        color: {c['text']};
        border: 2px solid {c['border']};
        border-radius: 7px;
        padding: 8px 16px;
        font: bold 13px 'B Nazanin';
        min-height: 28px;
        min-width: 80px;
        outline: none;
    }}
    QMessageBox QPushButton:hover {{
        background: {c['border']};
        border-color: {c['accent']};
    }}
    QMessageBox QPushButton:focus {{
        outline: none;
    }}
    """


# ============================================================================
# QMessageBox با قابلیت انتخاب و کپی متن
# ============================================================================

class CopyableMessageBox(QMessageBox):
    """QMessageBox با قابلیت انتخاب و کپی متن خطا"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName("پیام برنامه")
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                    Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    @classmethod
    def warning(cls, parent, title, text):
        msg = cls(parent)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(title)
        msg.setText(text)
        # تنظیم متن برای قابلیت انتخاب
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                   Qt.TextInteractionFlag.TextSelectableByKeyboard)
        msg.exec()

    @classmethod
    def information(cls, parent, title, text):
        msg = cls(parent)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                   Qt.TextInteractionFlag.TextSelectableByKeyboard)
        msg.exec()

    @classmethod
    def critical(cls, parent, title, text):
        msg = cls(parent)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                   Qt.TextInteractionFlag.TextSelectableByKeyboard)
        msg.exec()


# ============================================================================
# رندرر بهینه‌شده
# ============================================================================

class MathRenderer:
    _cache = OrderedDict()
    _cache_mutex = QMutex()

    # regex کامپایل شده با word boundaries صحیح
    _GREEK_PATTERN = re.compile(
        r'(?<![a-zA-Z])'
        r'(Delta|Gamma|Theta|Lambda|Sigma|Omega|Pi|'
        r'alpha|beta|gamma|delta|theta|lambda|mu|'
        r'sigma|phi|omega|pi|epsilon)'
        r'(?![a-zA-Z])'
    )

    @classmethod
    def render(cls, text, text_color='#e6edf3', bg_color='#1a1f2e', font_size=13, dpi=150):
        if not text or not str(text).strip():
            return None

        original = str(text).strip()

        if has_persian(original) or not has_math(original):
            return None

        key = f"{original}|{text_color}|{bg_color}|{font_size}|{dpi}"

        with QMutexLocker(cls._cache_mutex):
            if key in cls._cache:
                cls._cache.move_to_end(key)
                return cls._cache[key]

        clean = clean_unicode(original)
        debug_log(f"render: '{original[:60]}' -> clean: '{clean[:60]}'")

        latex_str = cls._to_latex_safe(clean)
        if not latex_str:
            return None

        debug_log(f"render: LaTeX = '{latex_str[:100]}'")

        result = cls._render_png(latex_str, text_color, bg_color, font_size, dpi)

        if result:
            with QMutexLocker(cls._cache_mutex):
                while len(cls._cache) >= MAX_CACHE_SIZE:
                    cls._cache.popitem(last=False)
                cls._cache[key] = result

        return result

    @classmethod
    def _to_latex_safe(cls, expr):
        """تبدیل امن به LaTeX"""
        if not expr or not expr.strip():
            return None

        expr = expr.strip()

        # روش ۱: SymPy
        try:
            latex_str = cls._sympy_convert(expr)
            if latex_str:
                return latex_str
        except Exception as e:
            debug_log(f"_to_latex_safe: SymPy failed ({str(e)[:80]})")

        # روش ۲: تبدیل دستی
        try:
            latex_str = cls._manual_convert_safe(expr)
            if latex_str:
                return latex_str
        except Exception as e:
            debug_log(f"_to_latex_safe: manual failed ({str(e)[:80]})")

        # روش ۳: escape ساده
        try:
            safe = expr
            safe = safe.replace('\\', '\\backslash ')
            safe = safe.replace('{', '\\{')
            safe = safe.replace('}', '\\}')
            safe = safe.replace('_', '\\_')
            safe = safe.replace('&', '\\&')
            safe = safe.replace('%', '\\%')
            safe = safe.replace('$', '\\$')
            safe = safe.replace('#', '\\#')
            return safe
        except Exception:
            return None

    @classmethod
    def _sympy_convert(cls, expr):
        """تبدیل با SymPy"""
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
                return cls._fix_greek_letters(result)
            except Exception:
                pass

        try:
            parsed = parse_expr(expr, transformations=TRANSFORMATIONS)
            result = sympy_latex(parsed)
            return cls._fix_greek_letters(result)
        except Exception:
            return None

    @classmethod
    def _fix_greek_letters(cls, latex_str: str) -> str:
        """
        اصلاح حروف یونانی در LaTeX
        فقط کلمات مستقل را تبدیل می‌کند (نه داخل کلمات ترکیبی)
        """
        if not latex_str:
            return latex_str

        def replace_greek(match):
            return f'\\{match.group()}'

        return cls._GREEK_PATTERN.sub(replace_greek, latex_str)

    @classmethod
    def _manual_convert_safe(cls, expr):
        """تبدیل دستی امن و بهینه"""
        result = expr

        # 1. تبدیل sqrt با الگوریتم بهینه
        result = cls._convert_sqrt_safe(result)

        # 2. توان‌ها
        result = re.sub(r'\^(\d+)', r'^{\1}', result)
        result = re.sub(r'\^([a-zA-Z])', r'^{\1}', result)

        # 3. توابع
        for func in ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'exp', 'abs']:
            result = re.sub(rf'\b({func})\b', rf'\\{func}', result)

        # 4. کسر ساده
        result = re.sub(r'(\w+)\s*/\s*(\w+)', r'\\frac{\1}{\2}', result)

        # 5. یونانی
        result = cls._fix_greek_letters(result)

        # 6. پرانتز
        result = result.replace('[', '{').replace(']', '}')

        # 7. بستن آکولادهای باز
        open_count = result.count('{')
        close_count = result.count('}')
        if open_count > close_count:
            result += '}' * (open_count - close_count)

        return result

    @classmethod
    def _convert_sqrt_safe(cls, expr: str, max_depth: int = MAX_NESTING_DEPTH) -> str:
        """
        تبدیل sqrt با مدیریت عمق محدود
        انتخاب خودکار الگوریتم بر اساس طول ورودی
        """
        # Early return اگر sqrt وجود ندارد
        if 'sqrt(' not in expr:
            return expr

        # انتخاب الگوریتم بر اساس طول
        if len(expr) < SQRT_LIST_THRESHOLD:
            return cls._convert_sqrt_list(expr, max_depth)
        else:
            return cls._convert_sqrt_fast(expr, max_depth)

    @classmethod
    def _convert_sqrt_list(cls, expr: str, max_depth: int) -> str:
        """
        الگوریتم مبتنی بر لیست - برای ورودی‌های کوتاه
        مزیت: سادگی و خوانایی
        """
        result = list(expr)
        i = 0
        while i < len(result) - 4:
            if ''.join(result[i:i+5]) == 'sqrt(':
                depth = 1
                j = i + 5
                while j < len(result) and depth > 0:
                    if result[j] == '(':
                        depth += 1
                        if depth > max_depth:
                            break
                    elif result[j] == ')':
                        depth -= 1
                    j += 1

                if depth == 0 and j <= len(result):
                    inner = ''.join(result[i+5:j-1])
                    replacement = list(f'\\sqrt{{{inner}}}')
                    result[i:j] = replacement
                    i += len(replacement)
                else:
                    i += 1
            else:
                i += 1

        return ''.join(result)

    @classmethod
    def _convert_sqrt_fast(cls, expr: str, max_depth: int) -> str:
        """
        الگوریتم سریع مبتنی بر string builder - برای ورودی‌های بلند
        مزیت: عملکرد بهتر برای رشته‌های طولانی
        """
        parts = []
        last_end = 0
        i = 0

        while i < len(expr) - 4:
            if expr[i:i+5] == 'sqrt(':
                # اضافه کردن بخش قبل از sqrt
                if i > last_end:
                    parts.append(expr[last_end:i])

                # پیدا کردن پرانتز متناظر
                depth = 1
                j = i + 5
                while j < len(expr) and depth > 0:
                    if expr[j] == '(':
                        depth += 1
                        if depth > max_depth:
                            break
                    elif expr[j] == ')':
                        depth -= 1
                    j += 1

                if depth == 0:
                    inner = expr[i+5:j-1]
                    parts.append(f'\\sqrt{{{inner}}}')
                    i = j
                    last_end = j
                else:
                    # اگر پرانتز بسته نشد، این بخش را نگه دار
                    parts.append(expr[i:i+5])
                    i += 5
                    last_end = i
            else:
                i += 1

        # اضافه کردن باقی‌مانده
        if last_end < len(expr):
            parts.append(expr[last_end:])

        return ''.join(parts)

    @classmethod
    def _render_png(cls, latex_str, text_color, bg_color, font_size, dpi):
        """رندر LaTeX به PNG"""
        fig = None
        try:
            fig, ax = plt.subplots(
                figsize=(6, 0.5), dpi=dpi,
                facecolor=bg_color, edgecolor='none'
            )

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

            # Fallback زنجیره‌ای برای bbox
            bbox = None
            try:
                bbox = text_obj.get_tightbbox(renderer)
            except Exception:
                pass

            if bbox is None:
                try:
                    bbox = text_obj.get_window_extent(renderer)
                except Exception:
                    pass

            if bbox is None:
                bbox = fig.bbox

            if bbox is None or bbox.width == 0 or bbox.height == 0:
                plt.close(fig)
                return None

            bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

            w = max(0.3, bbox_inches.width * 1.1)
            h = max(0.2, bbox_inches.height * 1.2)
            fig.set_size_inches(w, h)

            buf = io.BytesIO()
            fig.savefig(
                buf, format='png', dpi=dpi,
                bbox_inches='tight', pad_inches=0.05,
                facecolor=bg_color, edgecolor='none'
            )
            plt.close(fig)

            buf.seek(0)
            return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

        except Exception:
            if fig:
                plt.close(fig)
            return None

    @classmethod
    def clear_cache(cls):
        with QMutexLocker(cls._cache_mutex):
            cls._cache.clear()


# ============================================================================
# ویجت‌ها
# ============================================================================

class MathImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mathImage")
        self.setAccessibleName("رندر ریاضی")
        self.setAccessibleDescription("تصویر رندر شده فرمول ریاضی")
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
        self.setAccessibleName("ورودی معادله")
        self.setAccessibleDescription(
            "فیلد ورود معادله ریاضی. معادله را تایپ کرده و Enter بزنید"
        )
        self.setFont(FontManager.math(14))
        self.setPlaceholderText("x^2 - 5x + 6 = 0")
        self.setMaximumHeight(48)
        self.setMinimumHeight(42)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(False)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Return and not e.modifiers():
            t = self.toPlainText().strip()
            if t:
                self.equationSubmitted.emit(t)
            return
        super().keyPressEvent(e)


class StepWidget(QFrame):
    def __init__(self, step, colors, num, total, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setAccessibleName(f"گام {num} از {total}")
        self.setAccessibleDescription(
            f"گام {num}: {step.title} - {step.description[:50]}"
        )
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
        num_lbl.setAccessibleName(f"شماره گام {num}")
        num_lbl.setAccessibleDescription(f"این گام {num} از {total} گام است")
        num_lbl.setFixedSize(26, 26)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_lbl.setFont(FontManager.math(11, True))
        num_lbl.setStyleSheet(f"background:{c['accent']};color:{c['accent_text']};border-radius:13px;")
        layout.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(4)
        content.setContentsMargins(0, 0, 0, 0)

        title = QLabel(step.title)
        title.setAccessibleName(f"عنوان گام {num}: {step.title}")
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
        lbl.setAccessibleName(text[:50])
        if is_primary:
            lbl.setFont(FontManager.math(12, True))
            lbl.setStyleSheet(f"color:{c['accent']};background:{c['latex_bg']};padding:4px 8px;border-radius:3px;border-left:2px solid {c['accent']};")
        else:
            lbl.setFont(FontManager.math(11))
            lbl.setStyleSheet(f"color:{c['text_secondary']};")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl)


class HistoryPanel(QWidget):
    equationSelected = pyqtSignal(str)

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.setAccessibleName("پنل تاریخچه")
        self.setAccessibleDescription("لیست معادلات حل شده قبلی")
        self.colors = colors
        self.setMinimumWidth(180)
        self.setMaximumWidth(240)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0,0,0,0)

        hdr = QHBoxLayout()
        title = QLabel("📜 تاریخچه")
        title.setObjectName("titleLabel")
        title.setAccessibleName("عنوان تاریخچه")
        title.setFont(FontManager.ui(13, True))
        hdr.addWidget(title, 1)

        clear_btn = QPushButton("🗑️")
        clear_btn.setObjectName("iconBtn")
        clear_btn.setAccessibleName("پاک کردن تاریخچه")
        clear_btn.setAccessibleDescription("تمام موارد تاریخچه را حذف می‌کند")
        clear_btn.setToolTip("پاک کردن تاریخچه")
        clear_btn.setFixedSize(26, 26)
        clear_btn.clicked.connect(self._clear)
        hdr.addWidget(clear_btn)
        layout.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setAccessibleName("لیست تاریخچه")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(2)
        self.list_layout.setContentsMargins(0,0,0,0)
        self.list_layout.addStretch()
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self._history_data = []
        self._max_items = MAX_HISTORY_ITEMS

    def add(self, equation, result, success):
        """افزودن به تاریخچه با مدیریت حافظه"""
        self._history_data.append({
            'equation': equation,
            'result': result,
            'success': success
        })

        if len(self._history_data) > self._max_items:
            self._history_data = self._history_data[-self._max_items:]

        while self.list_layout.count() > self._max_items + 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        btn = QPushButton(equation[:26] + ("…" if len(equation) > 26 else ""))
        btn.setObjectName("historyItem")
        btn.setAccessibleName(f"معادله تاریخی: {equation[:26]}")
        btn.setAccessibleDescription(f"معادله: {equation}\nنتیجه: {result}")
        btn.setToolTip(f"{equation}\nنتیجه: {result}")
        btn.setProperty("success", "true" if success else "false")
        btn.setFont(FontManager.math(10))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, eq=equation: self.equationSelected.emit(eq))

        self.list_layout.insertWidget(self.list_layout.count() - 1, btn)

    def _clear(self):
        """پاک کردن کامل تاریخچه"""
        self._history_data.clear()
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
        self.setAccessibleName("حل کننده معادلات پیشرفته")
        self.setAccessibleDescription(
            "برنامه حل معادلات ریاضی با نمایش گام به گام"
        )

        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            w, h = max(1000, int(g.width()*0.7)), max(650, int(g.height()*0.7))
        else:
            w, h = 1050, 700
        self.setMinimumSize(900, 600)
        self.resize(w, h)

        self.settings = QSettings("MathAssistant", "PlatinumV13.3.1")
        self.is_dark = self.settings.value("dark_mode", True, type=bool)
        self.colors = Colors.DARK if self.is_dark else Colors.LIGHT
        self.engine = EquationSolverEngine()
        self.solution_cache = None
        self._history_visible = False
        self._solving = False
        self._thread = None
        self._thread_mutex = QMutex()

        # اجرای تست‌ها در حالت DEBUG یا با --test
        if DEBUG or "--test" in sys.argv:
            MathRendererTests.run_all()

        self._build()
        self._connect()
        self._setup_shortcuts()
        self._apply_theme()
        self._init_history_state()

        g = self.settings.value("geometry")
        if g:
            self.restoreGeometry(g)

        QTimer.singleShot(100, lambda: self.input.setFocus())

    def _setup_shortcuts(self):
        """تنظیم کلیدهای میانبر"""
        shortcut_solve = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_solve.activated.connect(lambda: self._solve(self.input.toPlainText().strip()))

        shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_clear.activated.connect(self._clear_input)

        shortcut_history = QShortcut(QKeySequence("Ctrl+H"), self)
        shortcut_history.activated.connect(self._toggle_history)

        shortcut_export = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_export.activated.connect(self._export)

        shortcut_help = QShortcut(QKeySequence("F1"), self)
        shortcut_help.activated.connect(self._help)

        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(lambda: self.input.setFocus())

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
        self.toggle_btn.setAccessibleName("نمایش/مخفی تاریخچه")
        self.toggle_btn.setAccessibleDescription(
            "کلیک کنید تا پنل تاریخچه معادلات حل شده نمایش داده یا مخفی شود"
        )
        self.toggle_btn.setToolTip("تاریخچه (Ctrl+H)")
        self.toggle_btn.setFixedSize(32, 32)
        hdr.addWidget(self.toggle_btn)

        title = QLabel("🧮 حل کننده معادلات پیشرفته")
        title.setObjectName("titleLabel")
        title.setAccessibleName("عنوان برنامه")
        title.setFont(FontManager.ui(16, True))
        hdr.addWidget(title, 1)

        help_btn = QPushButton("❓")
        help_btn.setObjectName("iconBtn")
        help_btn.setAccessibleName("راهنما")
        help_btn.setAccessibleDescription("نمایش راهنمای برنامه")
        help_btn.setToolTip("راهنما (F1)")
        help_btn.setFixedSize(30, 30)
        help_btn.clicked.connect(self._help)
        hdr.addWidget(help_btn)

        self.theme_btn = QPushButton("🌙" if self.is_dark else "☀️")
        self.theme_btn.setObjectName("iconBtn")
        self.theme_btn.setAccessibleName("تغییر تم")
        self.theme_btn.setAccessibleDescription("تغییر بین تم تاریک و روشن")
        self.theme_btn.setToolTip("تغییر تم")
        self.theme_btn.setFixedSize(30, 30)
        hdr.addWidget(self.theme_btn)
        root.addLayout(hdr)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        self.main_splitter.setAccessibleName("تقسیم‌کننده اصلی")

        self.history = HistoryPanel(self.colors)
        self.main_splitter.addWidget(self.history)

        center = QWidget()
        center.setAccessibleName("پنل مرکزی")
        cl = QVBoxLayout(center)
        cl.setSpacing(8)
        cl.setContentsMargins(0,0,0,0)
        cl.addWidget(self._input_card())
        cl.addWidget(self._output_card(), 1)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self._stats_card())
        self.main_splitter.setSizes([0, 820, 160])
        root.addWidget(self.main_splitter, 1)

        self.status = QLabel("👋 آماده... | Ctrl+Enter حل | F1 راهنما")
        self.status.setObjectName("statusLabel")
        self.status.setAccessibleName("نوار وضعیت")
        self.status.setAccessibleDescription("نمایش وضعیت فعلی برنامه و نتایج حل")
        self.status.setFont(FontManager.ui(11))
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.status)

    def _input_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setAccessibleName("کارت ورودی")
        card.setAccessibleDescription("بخش ورود معادله و دکمه‌های کنترل")

        l = QVBoxLayout(card)
        l.setSpacing(8)
        l.setContentsMargins(12, 10, 12, 10)

        hdr = QHBoxLayout()
        t = QLabel("✏️ معادله")
        t.setObjectName("titleLabel")
        t.setAccessibleName("عنوان ورودی")
        t.setFont(FontManager.ui(14, True))
        hdr.addWidget(t, 1)

        clr = QPushButton("✕")
        clr.setObjectName("iconBtn")
        clr.setAccessibleName("پاک کردن ورودی")
        clr.setAccessibleDescription("پاک کردن فیلد ورود معادله")
        clr.setToolTip("پاک کردن (Ctrl+L)")
        clr.setFixedSize(26, 26)
        clr.clicked.connect(self._clear_input)
        hdr.addWidget(clr)
        l.addLayout(hdr)

        self.input = MathInput()
        self.input.setToolTip("معادله را وارد کنید (Enter برای حل)")
        l.addWidget(self.input)

        btns = QHBoxLayout()
        self.solve_btn = QPushButton("🚀 حل معادله")
        self.solve_btn.setObjectName("accentBtn")
        self.solve_btn.setAccessibleName("دکمه حل")
        self.solve_btn.setAccessibleDescription("حل معادله وارد شده و نمایش گام‌ها")
        self.solve_btn.setToolTip("حل معادله (Enter یا Ctrl+Enter)")
        self.solve_btn.setFont(FontManager.ui(14, True))
        self.solve_btn.setMinimumHeight(40)

        self.export_btn = QPushButton("📤 ذخیره")
        self.export_btn.setAccessibleName("ذخیره نتیجه")
        self.export_btn.setAccessibleDescription("ذخیره نتیجه حل در فایل")
        self.export_btn.setToolTip("ذخیره نتیجه (Ctrl+E)")
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
        card.setAccessibleName("کارت خروجی")
        card.setAccessibleDescription("بخش نمایش گام‌های حل معادله")

        l = QVBoxLayout(card)
        l.setSpacing(6)
        l.setContentsMargins(10, 8, 10, 8)

        hdr = QHBoxLayout()
        t = QLabel("📝 گام‌های حل")
        t.setObjectName("titleLabel")
        t.setAccessibleName("عنوان گام‌ها")
        t.setFont(FontManager.ui(14, True))
        hdr.addWidget(t, 1)

        self.stat_summary = QLabel("")
        self.stat_summary.setAccessibleName("خلاصه آمار")
        self.stat_summary.setFont(FontManager.ui(11))
        self.stat_summary.setStyleSheet(f"color:{self.colors['text_secondary']};")
        self.stat_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hdr.addWidget(self.stat_summary)
        l.addLayout(hdr)

        self.steps_scroll = QScrollArea()
        self.steps_scroll.setAccessibleName("گام‌های حل")
        self.steps_scroll.setAccessibleDescription("لیست گام‌های حل معادله")
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
        card.setAccessibleName("کارت آمار")
        card.setAccessibleDescription("نمایش آمار و اطلاعات معادله حل شده")
        card.setMinimumWidth(150)
        card.setMaximumWidth(185)

        l = QVBoxLayout(card)
        l.setSpacing(5)
        l.setContentsMargins(8, 8, 8, 8)

        t = QLabel("📊 آمار")
        t.setObjectName("titleLabel")
        t.setAccessibleName("عنوان آمار")
        t.setFont(FontManager.ui(14, True))
        l.addWidget(t)

        self.stats = {}
        stat_labels = {
            'type': ('نوع:', 'نوع معادله'),
            'time': ('زمان:', 'زمان اجرا'),
            'count': ('جواب:', 'تعداد جواب'),
            'degree': ('درجه:', 'درجه معادله'),
            'complex': ('پیچیدگی:', 'امتیاز پیچیدگی')
        }
        for key, (label, desc) in stat_labels.items():
            lbl = QLabel(f"{label} —")
            lbl.setAccessibleName(desc)
            lbl.setAccessibleDescription(f"نمایش {desc}")
            lbl.setFont(FontManager.ui(11))
            lbl.setStyleSheet(f"color:{self.colors['text_secondary']};")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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

    def _cleanup_thread(self):
        """پاک‌سازی امن thread قبلی"""
        with QMutexLocker(self._thread_mutex):
            if self._thread and self._thread.isRunning():
                self._thread.requestInterruption()
                if not self._thread.wait(2000):
                    self._thread.terminate()
                    self._thread.wait()
                self._thread.deleteLater()
                self._thread = None

    @pyqtSlot(str)
    def _solve(self, eq):
        if not eq:
            return

        try:
            validated_eq = InputValidator.validate(eq)
        except ValueError as e:
            CopyableMessageBox.warning(self, "خطای ورودی", str(e))
            self.status.setText(f"❌ {str(e).split(chr(10))[0]}")
            self.input.setFocus()
            return

        self._cleanup_thread()

        self._solving = True
        self.solve_btn.setEnabled(False)
        self.solve_btn.setText("⏳ ...")
        self.status.setText("⏳ در حال حل...")
        QApplication.processEvents()

        self._thread = SolveThread(self.engine, validated_eq)
        self._thread.finished.connect(self._done)
        self._thread.error.connect(self._err)
        self._thread.start()

    @pyqtSlot(EquationSolution)
    def _done(self, sol):
        self._solving = False
        self.solve_btn.setEnabled(True)
        self.solve_btn.setText("🚀 حل معادله")
        self.export_btn.setEnabled(True)
        self.solution_cache = sol

        while self.steps_layout.count() > 1:
            item = self.steps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        MathRenderer.clear_cache()

        total_steps = len(sol.steps)
        for i, step in enumerate(sol.steps, 1):
            w = StepWidget(step, self.colors, i, total_steps)
            self.steps_layout.insertWidget(self.steps_layout.count() - 1, w)

        names = {
            'LINEAR':'خطی', 'QUADRATIC':'درجه۲', 'CUBIC':'درجه۳',
            'POLYNOMIAL':'چندجمله‌ای', 'RATIONAL':'گویا', 'SYSTEM':'دستگاه'
        }
        a = sol.analysis
        t = names.get(a.equation_type.name, 'نامشخص')

        self.stats['type'].setText(f"نوع: {t}")
        self.stats['time'].setText(f"زمان: {sol.execution_time_ms:.0f}ms")
        self.stats['count'].setText(f"جواب: {sol.solution_count}")
        self.stats['degree'].setText(f"درجه: {a.degree}")
        self.stats['complex'].setText(f"پیچیدگی: {a.complexity_score:.0%}")
        self.stat_summary.setText(f"{t} | {str(sol.solutions)[:25]}")

        self.history.add(
            sol.original_equation,
            str(sol.solutions)[:40],
            sol.solution_count > 0
        )

        self.status.setText(
            f"✅ حل شد — {sol.solution_count} جواب | {sol.execution_time_ms:.0f}ms"
        )
        self.steps_scroll.verticalScrollBar().setValue(0)
        self.input.setFocus()

    @pyqtSlot(str)
    def _err(self, msg):
        self._solving = False
        self.solve_btn.setEnabled(True)
        self.solve_btn.setText("🚀 حل معادله")
        self.status.setText(f"❌ {msg}")
        self.input.setFocus()

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
        self.main_splitter.setSizes(
            [200, 620, 160] if self._history_visible else [0, 820, 160]
        )
        self.main_splitter.updateGeometry()
        self.update()
        QApplication.processEvents()

    def _export(self):
        if not self.solution_cache:
            CopyableMessageBox.information(self, "توجه", "ابتدا معادله را حل کنید.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره نتیجه", "",
            "متن (*.txt);;JSON (*.json)"
        )
        if not path:
            return

        try:
            s = self.solution_cache
            if path.endswith('.json'):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'equation': s.original_equation,
                        'solutions': str(s.solutions),
                        'steps': [
                            {'title': st.title, 'description': st.description}
                            for st in s.steps
                        ],
                        'export_time': datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(f"معادله: {s.original_equation}\n\n")
                    for i, st in enumerate(s.steps, 1):
                        f.write(f"گام {i}: {st.title}\n{st.description}\n\n")
                    f.write(f"جواب: {s.solutions}\n")

            self.status.setText("✅ نتیجه با موفقیت ذخیره شد")
        except Exception as e:
            CopyableMessageBox.critical(self, "خطا", f"خطا در ذخیره‌سازی:\n{str(e)}")

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.colors = Colors.DARK if self.is_dark else Colors.LIGHT
        self.theme_btn.setText("🌙" if self.is_dark else "☀️")
        self.settings.setValue("dark_mode", self.is_dark)
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(stylesheet(self.colors))

        if hasattr(self, 'stat_summary'):
            self.stat_summary.setStyleSheet(
                f"color:{self.colors['text_secondary']};"
            )

        for lbl in self.stats.values():
            lbl.setStyleSheet(f"color:{self.colors['text_secondary']};")

        self.history.colors = self.colors
        self.update()

    def _help(self):
        help_text = (
            "📚 راهنمای حل کننده معادلات\n\n"
            "📝 نحوه وارد کردن:\n"
            "• x^2 - 5x + 6 = 0\n"
            "• 2x + 5 = 10\n"
            "• sin(x) + cos(x) = 1\n"
            "• x^3 - 3x + 1 = 0\n"
            "• sqrt(x) + sqrt(y) = 5\n\n"
            "⌨️ کلیدهای میانبر:\n"
            "• Enter یا Ctrl+Enter: حل معادله\n"
            "• Ctrl+L: پاک کردن ورودی\n"
            "• Ctrl+H: نمایش/مخفی تاریخچه\n"
            "• Ctrl+E: ذخیره نتیجه\n"
            "• F1: راهنما\n"
            "• Escape: بازگشت به ورودی\n\n"
            "📜 تاریخچه: باز/بسته با دکمه یا Ctrl+H\n\n"
            "⚠️ محدودیت‌ها:\n"
            f"• حداکثر طول عبارت: {MAX_INPUT_LENGTH} کاراکتر\n"
            f"• حداکثر عمق پرانتز: {MAX_NESTING_DEPTH}\n"
            "• از کلمات فارسی در معادله استفاده نکنید\n"
            "• کاراکترهای خاص غیرمجاز شناسایی می‌شوند"
        )

        CopyableMessageBox.information(self, "راهنما", help_text)

    def closeEvent(self, e):
        """پاک‌سازی کامل هنگام بستن برنامه"""
        self._cleanup_thread()
        MathRenderer.clear_cache()
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(e)


class SolveThread(QThread):
    finished = pyqtSignal(EquationSolution)
    error = pyqtSignal(str)

    def __init__(self, engine, equation):
        super().__init__()
        self.engine = engine
        self.equation = equation
        self._mutex = QMutex()

    def run(self):
        try:
            if self.isInterruptionRequested():
                return

            with QMutexLocker(self._mutex):
                if self.isInterruptionRequested():
                    return

                result = self.engine.solve(self.equation)

                if not self.isInterruptionRequested():
                    self.finished.emit(result)

        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


def main():
    # اجرای تست‌ها قبل از شروع GUI اگر --test داده شده
    if "--test" in sys.argv:
        passed, failed = MathRendererTests.run_all()
        sys.exit(0 if failed == 0 else 1)

    app = QApplication(sys.argv)
    app.setApplicationName("MathAssistant Pro Platinum")
    app.setOrganizationName("MathAssistant")
    app.setFont(FontManager.ui(11))
    app.setStyle('Fusion')

    app.setStyleSheet("""
        QToolTip {
            font: 11px 'B Nazanin';
            padding: 4px;
            border-radius: 4px;
        }
    """)

    w = EquationSolverWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
