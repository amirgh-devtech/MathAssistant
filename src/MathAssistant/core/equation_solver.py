# ./src/MathAssistant/core/equation_solver.py

"""
موتور حل معادلات با قابلیت توضیح گام‌به‌گام هوشمند

این ماژول معادلات ریاضی را به صورت نمادین حل کرده و فرآیند حل را
با استفاده از قالب‌های از پیش تعریف شده، به صورت گام‌به‌گام توضیح می‌دهد.

ویژگی‌ها:
- تحلیل هوشمند نوع معادله
- توضیح گام‌به‌گام با 40+ قالب آماده
- پردازش موازی معادلات چندگانه
- بهینه‌سازی با NumPy و Pandas
- کاملاً آفلاین - بدون نیاز به اینترنت یا LLM

Author: AmirMohammad Ghasemzadeh
Version: 1.3.0 - Production Ready
"""

import re
import math
import logging
import hashlib
from enum import Enum, auto
from typing import List, Tuple, Dict, Any, Optional, Union, Set, Callable
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

import numpy as np
import pandas as pd
from sympy import (
    Eq, solve, symbols, Symbol, sympify, expand, factor, simplify,
    collect, apart, together, cancel, diff, integrate, limit,
    series, roots, solveset, S, oo, zoo, nan, sqrt, Rational,
    SympifyError, Poly, degree, LC, nroots, nsolve, checkodesol,
    Function, dsolve, Derivative
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
from sympy.calculus.util import continuous_domain, function_range

logger = logging.getLogger(__name__)

# ============================================================================
# Enums و Types
# ============================================================================

class SafeDict(dict):
    """دیکشنری که به‌جای KeyError، خود placeholder رو برمیگردونه."""
    def __missing__(self, key):
        return f'{{{key}}}'

class EquationType(Enum):
    """انواع معادلات قابل حل توسط سیستم."""
    LINEAR = auto()           # معادله خطی: ax + b = 0
    QUADRATIC = auto()        # معادله درجه دوم: ax² + bx + c = 0
    CUBIC = auto()            # معادله درجه سوم
    QUARTIC = auto()          # معادله درجه چهارم
    POLYNOMIAL = auto()       # چندجمله‌ای عمومی
    RATIONAL = auto()         # معادله گویا (کسری)
    RADICAL = auto()          # معادله رادیکالی (ریشه‌ای)
    EXPONENTIAL = auto()      # معادله نمایی
    LOGARITHMIC = auto()      # معادله لگاریتمی
    TRIGONOMETRIC = auto()    # معادله مثلثاتی
    SYSTEM = auto()           # دستگاه معادلات
    DIFFERENTIAL = auto()     # معادله دیفرانسیل
    UNKNOWN = auto()          # نوع نامشخص

class SolutionMethod(Enum):
    """روش‌های حل معادله."""
    DIRECT_SOLVE = auto()
    FACTORING = auto()
    QUADRATIC_FORMULA = auto()
    COMPLETING_SQUARE = auto()
    SUBSTITUTION = auto()
    ELIMINATION = auto()
    GRAPHICAL = auto()
    NUMERICAL = auto()
    SEPARATION_OF_VARIABLES = auto()

class DifficultyLevel(Enum):
    """سطح دشواری معادله."""
    BASIC = auto()        # پایه (کلاس 7-9)
    INTERMEDIATE = auto() # متوسط (کلاس 10-11)
    ADVANCED = auto()     # پیشرفته (کلاس 12 و دانشگاه)
    EXPERT = auto()       # تخصصی (المپیاد و دانشگاه پیشرفته)

@dataclass
class EquationAnalysis:
    """نتیجه تحلیل یک معادله."""
    equation_type: EquationType
    difficulty: DifficultyLevel
    variables: List[str]
    degree: int
    is_homogeneous: bool
    has_fractions: bool
    has_radicals: bool
    term_count: int
    complexity_score: float  # 0.0 تا 1.0

@dataclass
class SolutionStep:
    """یک گام از فرآیند حل."""
    step_number: int
    title: str
    description: str
    mathematical_expression: Optional[str] = None
    explanation: Optional[str] = None
    hint: Optional[str] = None
    step_type: str = "calculation"  # calculation, explanation, verification

@dataclass
class EquationSolution:
    """نتیجه کامل حل یک معادله."""
    original_equation: str
    processed_equation: str
    analysis: EquationAnalysis
    steps: List[SolutionStep]
    solutions: List[Any]
    numeric_solutions: Optional[List[complex]] = None
    solution_count: int = 0
    verification_result: Optional[bool] = None
    domain: Optional[str] = None
    alternative_methods: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

# ============================================================================
# سیستم قالب‌های هوشمند (40+ قالب)
# ============================================================================

class ExplanationTemplates:
    """
    سیستم قالب‌های توضیح گام‌به‌گام.

    شامل 40+ قالب آماده که بر اساس نوع معادله و روش حل،
    به صورت هوشمند انتخاب می‌شوند.
    """

    # ----- قالب‌های معرفی و شروع (6 قالب) -----
    INTRO_TEMPLATES = [
        "🎯 بیایید معادله «{equation}» را گام به گام حل کنیم. این یک معادله {type_name} است.",
        "📝 معادله ما: {equation} | نوع: {type_name} | متغیرها: {variables}",
        "🔍 تحلیل اولیه: معادله {type_name} با {term_count} جمله و متغیرهای {variables}",
        "💡 راهبرد حل: ابتدا معادله را استاندارد می‌کنیم، سپس با روش {method} حل می‌کنیم.",
        "📚 این معادله از نوع {type_name} است. سطح دشواری: {difficulty}",
        "🧮 شروع حل گام‌به‌گام برای معادله: {equation}",
    ]

    # ----- قالب‌های استانداردسازی (5 قالب) -----
    STANDARDIZE_TEMPLATES = [
        "🔄 گام {step}: استانداردسازی معادله\n• تبدیل توان‌ها: {power_conversions}\n• معادله استاندارد: {standard_form}",
        "📐 گام {step}: مرتب‌سازی جملات\n• انتقال همه جملات به یک طرف:\n{standard_form} = 0",
        "🔧 گام {step}: ساده‌سازی اولیه\n• ترکیب جملات مشابه: {like_terms}\n• نتیجه: {result}",
        "⚙️ گام {step}: آماده‌سازی برای حل\n• تشخیص الگو: {pattern}\n• فرم نهایی: {final_form}",
        "📋 گام {step}: بازنویسی معادله\n• فرم اولیه: {original}\n• فرم استاندارد: {standard}",
    ]

    # ----- قالب‌های معادلات خطی (6 قالب) -----
    LINEAR_TEMPLATES = [
        "➡️ گام {step}: حل معادله خطی\n• {equation}\n• انتقال {term} به طرف دیگر: {step_expr}\n• نتیجه: {result}",
        "📏 گام {step}: ایزوله کردن متغیر\n• تقسیم دو طرف بر {coefficient}:\n• {step_expr}\n• {variable} = {result}",
        "🔢 گام {step}: محاسبه نهایی\n• {step_expr}\n• ساده‌سازی: {result}",
        "✅ گام {step}: تأیید جواب\n• جایگذاری {result} در معادله اصلی:\n• {verification}\n• ✓ درست است!",
        "🎯 گام {step}: جواب نهایی\n• {variable} = {result}\n• این جواب یکتاست زیرا معادله خطی است.",
        "📊 گام {step}: تفسیر هندسی\n• این معادله خطی نمایانگر یک خط است.\n• جواب {variable} = {result} نقطه تقاطع با محور X است.",
    ]

    # ----- قالب‌های معادلات درجه دوم (8 قالب) -----
    QUADRATIC_TEMPLATES = [
        "📐 گام {step}: تشخیص معادله درجه دوم\n• فرم استاندارد: ax² + bx + c = 0\n• a = {a}, b = {b}, c = {c}",
        "🔺 گام {step}: محاسبه دلتا (Δ)\n• Δ = b² - 4ac = ({b})² - 4({a})({c})\n• Δ = {delta}",
        "📈 گام {step}: تحلیل دلتا\n• Δ = {delta}\n• {delta_interpretation}",
        "📝 گام {step}: فرمول دلتا (راه حل عمومی)\n• x = (-b ± √Δ) / (2a)\n• x = (-({b}) ± √{delta}) / (2({a}))\n• x = {result}",
        "🔲 گام {step}: تجزیه به عوامل\n• {factored_form}\n• {factor_explanation}",
        "⬛ گام {step}: مربع کامل\n• {equation}\n• {completing_square_steps}\n• نتیجه: {result}",
        "📉 گام {step}: رسم سهمی\n• رأس سهمی: ({vertex_x}, {vertex_y})\n• جهت: {direction}\n• نقاط تقاطع با محور X: {roots}",
        "✨ گام {step}: جواب‌های نهایی\n• x₁ = {x1}\n• x₂ = {x2}\n• {nature_of_roots}",
    ]

    # ----- قالب‌های معادلات کسری (5 قالب) -----
    FRACTION_TEMPLATES = [
        "🍕 گام {step}: تشخیص معادله کسری\n• مخرج‌ها: {denominators}\n• محدودیت دامنه: {restrictions}",
        "🔗 گام {step}: یافتن مخرج مشترک\n• ک.م.م مخرج‌ها: {lcm}\n• ضرب دو طرف در مخرج مشترک: {step_expr}",
        "✂️ گام {step}: حذف مخرج‌ها\n• پس از ضرب و ساده‌سازی:\n• {result}",
        "⚡ گام {step}: حل معادله ساده شده\n• {solving_steps}",
        "🛡️ گام {step}: بررسی جواب‌های اضافی\n• جواب‌های یافت شده: {solutions}\n• بررسی در محدودیت‌ها: {domain_check}\n• جواب‌های معتبر: {valid_solutions}",
    ]

    # ----- قالب‌های دستگاه معادلات (6 قالب) -----
    SYSTEM_TEMPLATES = [
        "🔗 گام {step}: تحلیل دستگاه\n• تعداد معادلات: {eq_count}\n• تعداد مجهول‌ها: {var_count}\n• روش پیشنهادی: {method}",
        "🔄 گام {step}: روش حذفی\n• انتخاب معادله برای حذف {variable}\n• {elimination_steps}",
        "↔️ گام {step}: روش جایگزینی\n• از معادله اول: {var1} = {expr1}\n• جایگذاری در معادله دوم:\n• {substitution_steps}",
        "📊 گام {step}: فرم ماتریسی\n• AX = B\n• ماتریس ضرایب A:\n{matrix_a}\n• ماتریس جواب‌ها B:\n{matrix_b}",
        "🔢 گام {step}: حل با روش کرامر\n• det(A) = {determinant}\n• {cramer_steps}",
        "✅ گام {step}: جواب نهایی دستگاه\n• {solutions}\n• تأیید: {verification}",
    ]

    # ----- قالب‌های عمومی و نکات (5 قالب) -----
    GENERAL_TEMPLATES = [
        "💭 نکته آموزشی: {tip}",
        "⚠️ توجه: {warning}",
        "🌟 روش جایگزین: {alternative}",
        "📚 منبع: این روش بر اساس {theory} است.",
        "🎓 نکته پیشرفته: {advanced_tip}",
    ]

    # ----- قالب‌های جمع‌بندی (4 قالب) -----
    CONCLUSION_TEMPLATES = [
        "🏁 جمع‌بندی:\n• معادله: {equation}\n• جواب‌ها: {solutions}\n• روش حل: {method}",  # حذف {time}
        "✅ حل کامل شد! 🎉\n{solutions}",  # حذف {verification_summary}
        "📋 گزارش حل:\n• نوع معادله: {type}\n• تعداد جواب: {count}\n• جواب‌ها: {solutions}\n• روش: {method}",
        "🎯 نتیجه نهایی:\nمعادله {equation} دارای {count} جواب است:\n{solutions}",
    ]

    # ----- دیکشنری تفسیر دلتا -----
    DELTA_INTERPRETATIONS = {
        "positive": "Δ > 0: دو ریشه حقیقی و متمایز داریم.",
        "zero": "Δ = 0: یک ریشه مضاعف (دو ریشه برابر) داریم.",
        "negative": "Δ < 0: دو ریشه مختلط (غیرحقیقی) داریم.",
    }

    # ----- دیکشنری نوع ریشه‌ها -----
    ROOT_NATURE = {
        "real_distinct": "دو ریشه حقیقی و متفاوت 📊",
        "real_equal": "ریشه مضاعف (هر دو ریشه برابر) 🔵",
        "complex_conjugate": "دو ریشه مختلط مزدوج 🔮",
        "rational": "ریشه‌های گویا 🎯",
        "irrational": "ریشه‌های گنگ (رادیکالی) 🔢",
    }

    @classmethod
    def get_intro(cls, **kwargs) -> str:
        template = cls._select_template(cls.INTRO_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_standardize_step(cls, step_num: int, **kwargs) -> str:
        kwargs['step'] = step_num
        template = cls._select_template(cls.STANDARDIZE_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_linear_step(cls, step_num: int, **kwargs) -> str:
        kwargs['step'] = step_num
        template = cls._select_template(cls.LINEAR_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_quadratic_step(cls, step_num: int, **kwargs) -> str:
        kwargs['step'] = step_num
        template = cls._select_template(cls.QUADRATIC_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_fraction_step(cls, step_num: int, **kwargs) -> str:
        kwargs['step'] = step_num
        template = cls._select_template(cls.FRACTION_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_system_step(cls, step_num: int, **kwargs) -> str:
        kwargs['step'] = step_num
        template = cls._select_template(cls.SYSTEM_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @classmethod
    def get_conclusion(cls, **kwargs) -> str:
        template = cls._select_template(cls.CONCLUSION_TEMPLATES, kwargs)
        return template.format_map(SafeDict(kwargs))

    @staticmethod
    def _select_template(templates: List[str], context: Dict) -> str:
        """انتخاب هوشمند قالب بر اساس context (با هش کردن ساده)."""
        # برای تنوع، بر اساس ویژگی‌های context قالب انتخاب می‌کنیم
        if 'equation_type' in context:
            idx = hash(context['equation_type']) % len(templates)
        elif 'step' in context:
            idx = context['step'] % len(templates)
        else:
            idx = hash(str(context)) % len(templates)
        return templates[abs(idx)]


# ============================================================================
# تحلیلگر هوشمند معادلات
# ============================================================================

class EquationAnalyzer:
    """
    تحلیلگر هوشمند معادلات.

    نوع معادله، سطح دشواری، و ویژگی‌های آن را تشخیص می‌دهد.
    """

    # الگوهای تشخیص نوع معادله (کامپایل شده برای سرعت)
    PATTERNS = {
        EquationType.TRIGONOMETRIC: re.compile(
            r'\b(sin|cos|tan|cot|sec|csc|arcsin|arccos|arctan)\b', re.IGNORECASE
        ),
        EquationType.EXPONENTIAL: re.compile(
            r'\b(exp|e\^|\d+\^[a-zA-Z]|[a-zA-Z]\^\{?\d+)\b', re.IGNORECASE
        ),
        EquationType.LOGARITHMIC: re.compile(
            r'\b(log|ln|log10|log2)\b', re.IGNORECASE
        ),
        EquationType.RADICAL: re.compile(
            r'\b(sqrt|√|root|\\sqrt)', re.IGNORECASE
        ),
    }

    @staticmethod
    @lru_cache(maxsize=256)
    def analyze(equation_str: str, variables: Tuple[str, ...]) -> EquationAnalysis:
        """
        تحلیل معادله با استفاده از SymPy و الگوهای regex.

        از lru_cache برای کش کردن نتایج تحلیل‌های تکراری استفاده می‌شود.
        """
        start = time.perf_counter()
        standardized = EquationParser._standardize(equation_str)
        # تبدیل به عبارت SymPy
        try:
            if '=' in standardized:
                lhs, rhs = standardized.split('=', 1)
                expr_str = f"({lhs}) - ({rhs})"
            else:
                expr_str = standardized

            expr = parse_expr(expr_str, transformations=EquationParser.TRANSFORMATIONS)
        except SympifyError as e:
            logger.debug(f"Sympy parse error for '{standardized}': {e}")
            return EquationAnalysis(
                equation_type=EquationType.UNKNOWN,
                difficulty=DifficultyLevel.INTERMEDIATE,
                variables=list(variables) if variables else [],
                degree=0,
                is_homogeneous=False,
                has_fractions=False,
                has_radicals=False,
                term_count=0,
                complexity_score=0.5
            )

        # تشخیص نوع
        equation_type = EquationAnalyzer._detect_type(equation_str, expr)

        # محاسبه degree
        degree_val = EquationAnalyzer._calculate_degree(expr, variables) if variables else 0

        # تشخیص ویژگی‌ها
        has_fractions = '/' in equation_str or '÷' in equation_str
        has_radicals = bool(EquationAnalyzer.PATTERNS[EquationType.RADICAL].search(equation_str)) if EquationType.RADICAL in EquationAnalyzer.PATTERNS else 'sqrt' in equation_str or '√' in equation_str

        # شمارش جملات
        term_count = EquationAnalyzer._count_terms(expr)

        # محاسبه امتیاز پیچیدگی
        complexity = EquationAnalyzer._compute_complexity(
            equation_type, degree_val, term_count,
            has_fractions, has_radicals, len(variables) if variables else 0
        )

        # تعیین سطح دشواری
        difficulty = EquationAnalyzer._determine_difficulty(
            equation_type, degree_val, complexity
        )

        return EquationAnalysis(
            equation_type=equation_type,
            difficulty=difficulty,
            variables=list(variables) if variables else [],
            degree=degree_val,
            is_homogeneous=EquationAnalyzer._is_homogeneous(expr, variables) if variables else False,
            has_fractions=has_fractions,
            has_radicals=has_radicals,
            term_count=term_count,
            complexity_score=complexity
        )

    @staticmethod
    def _detect_type(equation_str: str, expr) -> EquationType:
        """تشخیص نوع معادله."""
        # بررسی الگوهای خاص
        if '=' in equation_str and equation_str.count('=') > 1:
            return EquationType.SYSTEM

        for eq_type, pattern in EquationAnalyzer.PATTERNS.items():
            if pattern.search(equation_str):
                return eq_type

        # تشخیص از روی ساختار
        if EquationAnalyzer._contains_derivative(expr):
            return EquationType.DIFFERENTIAL

        if '/' in equation_str:
            return EquationType.RATIONAL

        # تشخیص بر اساس درجه
        try:
            poly = expr.as_poly()
            if poly is not None:
                deg = poly.total_degree()
                if deg == 1:
                    return EquationType.LINEAR
                elif deg == 2:
                    return EquationType.QUADRATIC
                elif deg == 3:
                    return EquationType.CUBIC
                elif deg == 4:
                    return EquationType.QUARTIC
                elif deg > 4:
                    return EquationType.POLYNOMIAL
        except:
            pass

        return EquationType.UNKNOWN

    @staticmethod
    def _calculate_degree(expr, variables: Tuple[str, ...]) -> int:
        """محاسبه درجه معادله."""
        try:
            syms = symbols(variables)
            poly = Poly(expr, *syms)
            return poly.total_degree()
        except:
            return 0

    @staticmethod
    def _count_terms(expr) -> int:
        """شمارش جملات عبارت."""
        try:
            if hasattr(expr, 'as_ordered_terms'):
                return len(expr.as_ordered_terms())
        except:
            pass
        return 1

    @staticmethod
    def _is_homogeneous(expr, variables: Tuple[str, ...]) -> bool:
        """بررسی همگن بودن معادله."""
        try:
            syms = symbols(variables)
            poly = Poly(expr, *syms)
            return poly.is_homogeneous
        except:
            return False

    @staticmethod
    def _contains_derivative(expr) -> bool:
        """بررسی وجود مشتق در عبارت."""
        try:
            return expr.has(Derivative)
        except:
            return False

    @staticmethod
    def _compute_complexity(
        eq_type: EquationType, degree: int, terms: int,
        has_fractions: bool, has_radicals: bool, var_count: int
    ) -> float:
        """محاسبه امتیاز پیچیدگی (0.0 تا 1.0)."""
        score = 0.0

        # مشارکت نوع معادله
        type_weights = {
            EquationType.LINEAR: 0.1,
            EquationType.QUADRATIC: 0.2,
            EquationType.CUBIC: 0.35,
            EquationType.QUARTIC: 0.5,
            EquationType.POLYNOMIAL: 0.6,
            EquationType.RATIONAL: 0.5,
            EquationType.RADICAL: 0.55,
            EquationType.EXPONENTIAL: 0.7,
            EquationType.LOGARITHMIC: 0.65,
            EquationType.TRIGONOMETRIC: 0.75,
            EquationType.SYSTEM: 0.8,
            EquationType.DIFFERENTIAL: 0.9,
            EquationType.UNKNOWN: 0.5,
        }
        score += type_weights.get(eq_type, 0.5) * 0.4

        # مشارکت درجه
        score += min(degree / 10.0, 1.0) * 0.2

        # مشارکت تعداد جملات
        score += min(terms / 10.0, 1.0) * 0.15

        # مشارکت ویژگی‌های خاص
        if has_fractions:
            score += 0.15
        if has_radicals:
            score += 0.15
        score += min(var_count / 5.0, 1.0) * 0.1

        return min(score, 1.0)

    @staticmethod
    def _determine_difficulty(
        eq_type: EquationType, degree: int, complexity: float
    ) -> DifficultyLevel:
        """تعیین سطح دشواری."""
        if complexity < 0.25:
            return DifficultyLevel.BASIC
        elif complexity < 0.5:
            return DifficultyLevel.INTERMEDIATE
        elif complexity < 0.75:
            return DifficultyLevel.ADVANCED
        else:
            return DifficultyLevel.EXPERT


# ============================================================================
# پارسر معادلات (با کش)
# ============================================================================

class EquationParser:
    """پارس و استانداردسازی معادلات."""

    # قوانین جایگزینی (با regex برای سرعت بیشتر)
    REPLACEMENTS = [
        # اولویت: کاراکترهای یونیکد توان
        (re.compile(r'²'), '**2'),
        (re.compile(r'³'), '**3'),
        (re.compile(r'⁴'), '**4'),
        (re.compile(r'⁵'), '**5'),
        (re.compile(r'⁶'), '**6'),
        (re.compile(r'⁷'), '**7'),
        (re.compile(r'⁸'), '**8'),
        (re.compile(r'⁹'), '**9'),
        (re.compile(r'⁰'), '**0'),
        # توان با ^
        (re.compile(r'(\w+|\))\s*\^\s*(\w+|\([^)]+\)|\d+)'), r'\1**\2'),
        # نمادهای ریاضی
        (re.compile(r'×'), '*'),
        (re.compile(r'÷'), '/'),
        (re.compile(r'√'), 'sqrt'),
        (re.compile(r'π'), 'pi'),
        # e ثابت (نه به عنوان متغیر)
        (re.compile(r'(?<![a-zA-Z])e(?![a-zA-Z])'), 'E'),
        # حذف فاصله‌ها
        (re.compile(r'\s+'), ''),
    ]

    TRANSFORMATIONS = (
        standard_transformations +
        (implicit_multiplication_application, convert_xor)
    )

    @classmethod
    @lru_cache(maxsize=512)
    def parse(cls, equation_str: str) -> Tuple[str, List[str], Optional[Eq]]:
        """
        پارس معادله و استخراج متغیرها و عبارت SymPy.

        از lru_cache برای کش کردن نتایج استفاده می‌شود.
        """
        # استانداردسازی
        standardized = cls._standardize(equation_str)

        # جداسازی دو طرف معادله
        if '=' not in standardized:
            raise ValueError("معادله باید شامل علامت '=' باشد.")

        parts = standardized.split('=')
        if len(parts) > 2:
            # دستگاه معادلات
            equations = []
            for part in parts:
                if '=' in part:
                    left, right = part.rsplit('=', 1)
                else:
                    left, right = part, '0'
                equations.append(f"({left}) - ({right})")
            standardized = '=0, '.join(equations) + '=0'

        # استخراج متغیرها
        variables = cls._extract_variables(standardized)

        # ساخت عبارت SymPy
        try:
            sympy_eq = cls._create_sympy_equation(standardized)
        except:
            sympy_eq = None

        return standardized, variables, sympy_eq

    @classmethod
    def _standardize(cls, equation: str) -> str:
        result = equation.strip()

        # جایگزینی مستقیم کاراکترهای یونیکد
        unicode_map = {'²': '**2', '³': '**3', '⁴': '**4', '⁵': '**5', '⁶': '**6', '⁷': '**7', '⁸': '**8', '⁹': '**9', '⁰': '**0',}
        for old, new in unicode_map.items():
            result = result.replace(old, new)

        # اعمال regexها
        for pattern, replacement in cls.REPLACEMENTS:
            result = pattern.sub(replacement, result)

        return result

    @classmethod
    def _extract_variables(cls, equation: str) -> List[str]:
        """استخراج متغیرها از معادله."""
        # حذف توابع شناخته شده
        cleaned = re.sub(
            r'\b(sin|cos|tan|cot|sec|csc|log|ln|sqrt|exp|abs|pi|E)\b',
            '', equation
        )
        # پیدا کردن کلمات (متغیرها)
        var_matches = re.findall(r'([a-zA-Z]+)', cleaned)
        # فیلتر کردن متغیرهای تک‌حرفی (رایج در ریاضیات)
        single_letter_vars = set()
        for match in var_matches:
            if len(match) == 1 and match.isalpha():
                single_letter_vars.add(match)

        # اگر متغیر تک‌حرفی نیست، همه کلمات را برگردان
        if not single_letter_vars:
            single_letter_vars = set(var_matches)

        return sorted(list(single_letter_vars))

    @classmethod
    def _create_sympy_equation(cls, equation: str) -> Optional[Eq]:
        """ساخت معادله SymPy - اصلاح‌شده."""
        try:
            if '=' in equation:
                lhs_str, rhs_str = equation.split('=', 1)
                lhs = parse_expr(lhs_str, transformations=cls.TRANSFORMATIONS)
                rhs = parse_expr(rhs_str, transformations=cls.TRANSFORMATIONS)
                return Eq(lhs, rhs)
        except Exception as e:
            logger.debug(f"Error creating sympy equation: {e}")
        return None


# ============================================================================
# حل‌کننده اصلی با توضیح گام‌به‌گام
# ============================================================================

class StepByStepSolver:
    """
    حل‌کننده گام‌به‌گام معادلات.

    معادلات را حل کرده و هر گام را با استفاده از قالب‌های هوشمند توضیح می‌دهد.

    Features:
    - تشخیص هوشمند نوع معادله
    - حل گام‌به‌گام با توضیحات فارسی
    - 40+ قالب توضیح آماده
    - محاسبه جواب‌های عددی با NumPy
    - مدیریت خطای جامع با بازگشت graceful

    Design Patterns:
    - Strategy Pattern (روش‌های حل مختلف بر اساس نوع معادله)
    - Template Method (ساختار ثابت solve با مراحل متغیر)
    """

    def __init__(self):
        self.templates = ExplanationTemplates()
        self.analyzer = EquationAnalyzer()
        self.parser = EquationParser()

    def _create_sympy_eq_safe(self, equation_str: str) -> Optional[Eq]:
        """
        ساخت امن معادله SymPy با جداسازی lhs و rhs قبل از parse.

        مشکل اصلی: SymPy نمی‌تواند علامت '=' را مستقیماً parse کند.
        راه‌حل: ابتدا رشته را به lhs و rhs تقسیم کرده،
        سپس هر بخش را جداگانه parse می‌کنیم.

        Args:
            equation_str: رشته معادله (مثلاً "x + 5 = 10")

        Returns:
            Eq object یا None در صورت خطا
        """
        try:
            if '=' in equation_str:
                lhs, rhs = equation_str.split('=', 1)
                lhs_expr = parse_expr(
                    lhs.strip(),
                    transformations=EquationParser.TRANSFORMATIONS
                )
                rhs_expr = parse_expr(
                    rhs.strip(),
                    transformations=EquationParser.TRANSFORMATIONS
                )
                return Eq(lhs_expr, rhs_expr)
            else:
                expr = parse_expr(
                    equation_str.strip(),
                    transformations=EquationParser.TRANSFORMATIONS
                )
                return Eq(expr, 0)
        except Exception as e:
            logger.error(f"Cannot create sympy equation from '{equation_str}': {e}")
            return None

    # ========================================================================
    # متد اصلی حل
    # ========================================================================

    def solve(
        self,
        equation_str: str,
        show_numeric: bool = True
    ) -> EquationSolution:
        """
        حل معادله با توضیح گام‌به‌گام.

        Args:
            equation_str: رشته معادله (مثلاً "x² - 5x + 6 = 0")
            show_numeric: آیا جواب‌های عددی هم محاسبه شوند؟

        Returns:
            EquationSolution با تمام گام‌ها، جواب‌ها و تحلیل
        """
        start_time = time.perf_counter()
        steps = []

        try:
            # ----- گام 0: پارس و استانداردسازی -----
            standardized, variables, _ = self.parser.parse(equation_str)

            # ساخت معادله SymPy با متد امن
            sympy_eq = self._create_sympy_eq_safe(standardized)

            if not variables:
                return self._create_error_solution(
                    equation_str,
                    "هیچ متغیری در معادله یافت نشد.",
                    start_time
                )

            # ----- تحلیل معادله -----
            analysis = self.analyzer.analyze(standardized, tuple(variables))

            # ----- گام 1: معرفی -----
            steps.append(SolutionStep(
                step_number=1,
                title="🔍 تحلیل و معرفی معادله",
                description=self.templates.get_intro(
                    equation=equation_str,
                    type_name=self._get_type_name(analysis.equation_type),
                    variables=', '.join(variables),
                    term_count=analysis.term_count,
                    difficulty=self._get_difficulty_name(analysis.difficulty),
                    method=self._suggest_method(analysis)
                ),
                step_type="explanation"
            ))

            # ----- گام 2: استانداردسازی (در صورت نیاز) -----
            if equation_str != standardized:
                steps.append(SolutionStep(
                step_number=2,
                title="📐 استانداردسازی معادله",
                description=self.templates.get_standardize_step(
                    2,
                    original=equation_str,
                    standard=standardized,
                    power_conversions=self._get_power_conversions(equation_str),
                    like_terms="جملات مشابه ترکیب شدند",
                    result=standardized,
                    pattern="استاندارد",
                    final_form=standardized
                ),
                mathematical_expression=standardized,
                step_type="calculation"
            ))
                current_step = 3
            else:
                current_step = 2

            # ----- گام‌های حل بر اساس نوع معادله -----
            solving_steps, solutions = self._solve_by_type(
                standardized, variables, analysis, sympy_eq, current_step
            )
            steps.extend(solving_steps)

            # ----- گام آخر: تأیید و جمع‌بندی -----
            verification = None

            if solutions:
                verification = (
                    self._verify_solutions(sympy_eq, solutions, variables)
                    if sympy_eq is not None else None
                )
                steps.append(SolutionStep(
                    step_number=len(steps) + 1,
                    title="✅ تأیید و جمع‌بندی",
                    description=self.templates.get_conclusion(
                        equation=equation_str,
                        solutions=self._format_solutions(solutions),
                        method=self._suggest_method(analysis),
                        count=len(solutions),
                        type=self._get_type_name(analysis.equation_type)
                    ),
                    step_type="verification"
                ))

            # ---------- محاسبه جواب‌های عددی ----------
            numeric_solutions = None
            if show_numeric and solutions:
                numeric_solutions = self._compute_numeric_solutions(
                    standardized, variables
                )

            execution_time = (time.perf_counter() - start_time) * 1000

            return EquationSolution(
                original_equation=equation_str,
                processed_equation=standardized,
                analysis=analysis,
                steps=steps,
                solutions=solutions,
                numeric_solutions=numeric_solutions,
                solution_count=len(solutions) if solutions else 0,
                verification_result=verification,  # <-- حالا همیشه تعریف شده
                domain=self._get_domain(analysis),
                alternative_methods=self._get_alternative_methods(analysis),
                execution_time_ms=execution_time
            )

        except Exception as e:
            logger.error(f"خطا در حل معادله '{equation_str}': {str(e)}")
            return self._create_error_solution(
                equation_str,
                f"خطا در حل: {str(e)}",
                start_time
            )

    # ========================================================================
    # متدهای حل بر اساس نوع معادله
    # ========================================================================

    def _solve_by_type(
        self,
        equation: str,
        variables: List[str],
        analysis: EquationAnalysis,
        sympy_eq: Optional[Eq],
        start_step: int
    ) -> Tuple[List[SolutionStep], List[Any]]:
        """
        مسیریابی حل بر اساس نوع معادله.

        Strategy Pattern: انتخاب استراتژی حل بر اساس equation_type.
        """
        steps = []
        solutions = []

        try:
            syms = symbols(variables)

            # اگر sympy_eq وجود نداشت، دوباره تلاش برای ساخت
            if sympy_eq is None:
                sympy_eq = self._create_sympy_eq_safe(equation)

            if sympy_eq is None:
                return steps, solutions

            # انتخاب استراتژی حل بر اساس نوع معادله
            solver_map = {
                EquationType.QUADRATIC: self._solve_quadratic_detailed,
                EquationType.LINEAR: self._solve_linear_detailed,
            }

            solver_method = solver_map.get(analysis.equation_type)

            if analysis.equation_type == EquationType.SYSTEM:
                result_steps, solutions = self._solve_system_detailed(
                    equation, variables, syms, start_step
                )
            elif solver_method is not None:
                result_steps, solutions = solver_method(
                    sympy_eq, variables, syms, start_step
                )
            else:
                # Fallback برای انواع ناشناخته (CUBIC, POLYNOMIAL, ...)
                result_steps, solutions = self._solve_general(
                    sympy_eq, variables, syms, analysis, start_step
                )

            steps.extend(result_steps)
            return steps, solutions

        except Exception as e:
            logger.warning(f"خطا در حل نوع خاص '{analysis.equation_type}': {e}")
            # Fallback: تلاش برای حل عمومی
            try:
                if sympy_eq is not None:
                    solutions = solve(sympy_eq, syms, dict=True)
                    if not solutions and syms:
                        solutions = list(solveset(sympy_eq, syms[0]))
            except Exception:
                solutions = []

            return steps, solutions

    # ========================================================================
    # حل معادلات خطی
    # ========================================================================

    def _solve_linear_detailed(
        self,
        eq: Eq,
        variables: List[str],
        syms: List[Symbol],
        start_step: int
    ) -> Tuple[List[SolutionStep], List[Any]]:
        """
        حل گام‌به‌گام معادله خطی ax + b = 0.

        مراحل:
        1. استانداردسازی به فرم ax + b = 0
        2. انتقال b به طرف دیگر
        3. تقسیم بر a
        """
        steps = []
        var = syms[0]

        # استانداردسازی
        expanded = expand(eq.lhs - eq.rhs)

        # استخراج ضرایب
        try:
            poly = Poly(expanded, var)
            a = poly.coeff_monomial(var)
            b = poly.coeff_monomial(1)
        except Exception:
            a = expanded.coeff(var, 1) if hasattr(expanded, 'coeff') else 0
            b = expanded.coeff(var, 0) if hasattr(expanded, 'coeff') else 0

        step_num = start_step

        # گام: تشخیص ساختار
        steps.append(SolutionStep(
            step_number=step_num,
            title="📏 تشخیص معادله خطی",
            description=self.templates.get_linear_step(
                step_num,
                equation=f"{expanded} = 0",
                term=str(b),
                step_expr=f"ax + b = 0 با a={a}, b={b}",
                result=f"x = {-b}/{a}" if a != 0 else "بدون جواب یا بی‌نهایت جواب",
                coefficient=a,
                variable=str(var)
            ),
            mathematical_expression=f"{expanded} = 0",
            step_type="explanation"
        ))
        step_num += 1

        # گام: حل
        if a != 0:
            solution = -b / a
            steps.append(SolutionStep(
                step_number=step_num,
                title="🔢 محاسبه جواب",
                description=self.templates.get_linear_step(
                    2,
                    equation=f"{var} = -({b}) / ({a})",
                    term="",
                    step_expr=f"{var} = {-b}/{a}",
                    result=str(solution),
                    coefficient=a,
                    variable=str(var)
                ),
                mathematical_expression=f"{var} = {solution}",
                step_type="calculation"
            ))
            solutions = [{var: solution}]
        elif b == 0:
            solutions = [{var: 'any'}]  # بی‌نهایت جواب
        else:
            solutions = []  # بدون جواب

        return steps, solutions

    # ========================================================================
    # حل معادلات درجه دوم
    # ========================================================================

    def _solve_quadratic_detailed(
        self,
        eq: Eq,
        variables: List[str],
        syms: List[Symbol],
        start_step: int
    ) -> Tuple[List[SolutionStep], List[Any]]:
        """
        حل گام‌به‌گام معادله درجه دوم ax² + bx + c = 0.

        مراحل:
        1. تشخیص ضرایب a, b, c
        2. محاسبه دلتا (Δ = b² - 4ac)
        3. تحلیل دلتا
        4. اعمال فرمول دلتا یا روش جایگزین
        5. نمایش جواب‌های نهایی
        """
        steps = []
        var = syms[0]
        step_num = start_step
        delta = 0

        expanded = expand(eq.lhs - eq.rhs)

        try:
            poly = Poly(expanded, var)
            a = poly.coeff_monomial(var**2) if poly.has(var**2) else 0
            b = poly.coeff_monomial(var) if poly.has(var) else 0
            c = poly.coeff_monomial(1)
        except Exception:
            a = expanded.coeff(var, 2) if hasattr(expanded, 'coeff') else 0
            b = expanded.coeff(var, 1) if hasattr(expanded, 'coeff') else 0
            c = expanded.coeff(var, 0) if hasattr(expanded, 'coeff') else 0

        # گام 1: نمایش ضرایب
        steps.append(SolutionStep(
            step_number=step_num,
            title="📐 تشخیص معادله درجه دوم",
            description=self.templates.get_quadratic_step(
                1, a=a, b=b, c=c,
                equation=f"{expanded} = 0"
            ),
            mathematical_expression=f"a={a}, b={b}, c={c}",
            step_type="explanation"
        ))
        step_num += 1

        # گام 2: محاسبه دلتا
        delta = b**2 - 4*a*c
        delta_str = f"Δ = ({b})² - 4({a})({c}) = {delta}"

        if delta > 0:
            delta_interp = self.templates.DELTA_INTERPRETATIONS["positive"]
            root_nature = "real_distinct"
        elif delta == 0:
            delta_interp = self.templates.DELTA_INTERPRETATIONS["zero"]
            root_nature = "real_equal"
        else:
            delta_interp = (
                f"{self.templates.DELTA_INTERPRETATIONS['negative']}\n"
                f"• |Δ| = {abs(delta)}\n"
                f"• √Δ = {round(math.sqrt(-delta), 4)}i"
            )
            root_nature = "complex_conjugate"

        steps.append(SolutionStep(
            step_number=step_num,
            title="🔺 محاسبه دلتا (Δ)",
            description=self.templates.get_quadratic_step(
                2,
                delta=delta,
                delta_interpretation=delta_interp,
                b=b, a=a, c=c
            ),
            mathematical_expression=delta_str,
            step_type="calculation"
        ))
        step_num += 1

        # گام 3: اعمال فرمول
        if a != 0:
            if delta >= 0:
                sqrt_delta = math.sqrt(delta)
                x1 = (-b + sqrt_delta) / (2*a)
                x2 = (-b - sqrt_delta) / (2*a)

                x1_simplified = self._simplify_rational(float(x1))
                x2_simplified = self._simplify_rational(float(x2))

                formula_step = (
                    f"x = (-b ± √Δ) / (2a)\n"
                    f"x = (-({b}) ± √{delta}) / (2({a}))\n"
                    f"x₁ = (-({b}) + {sqrt_delta}) / {2*a} = {x1_simplified}\n"
                    f"x₂ = (-({b}) - {sqrt_delta}) / {2*a} = {x2_simplified}"
                )

                steps.append(SolutionStep(
                    step_number=step_num,
                    title="📝 اعمال فرمول دلتا",
                    description=formula_step,
                    mathematical_expression=f"x₁ = {x1_simplified}, x₂ = {x2_simplified}",
                    step_type="calculation"
                ))
                step_num += 1

                # گام 4: جواب‌های نهایی
                nature = self.templates.ROOT_NATURE.get(root_nature, "ریشه‌های محاسبه شده")
                steps.append(SolutionStep(
                    step_number=step_num,
                    title="✨ جواب‌های نهایی",
                    description=self.templates.get_quadratic_step(
                        8,
                        x1=x1_simplified,
                        x2=x2_simplified,
                        nature_of_roots=nature
                    ),
                    mathematical_expression=f"x₁ = {x1_simplified}, x₂ = {x2_simplified}",
                    step_type="verification"
                ))

                solutions = [
                    {var: x1_simplified},
                    {var: x2_simplified}
                ]
            else:
                # دلتای منفی: استفاده از solve مستقیم SymPy
                solutions = solve(eq, var, dict=True)
                if not solutions:
                    solutions = list(solveset(eq, var))
        else:
            # a = 0: معادله خطی شده
            solutions = solve(eq, var, dict=True)
            if not solutions:
                solutions = list(solveset(eq, var))

        return steps, solutions

    # ========================================================================
    # حل دستگاه معادلات
    # ========================================================================

    def _solve_system_detailed(
        self,
        equations_str: str,
        variables: List[str],
        syms: List[Symbol],
        start_step: int
    ) -> Tuple[List[SolutionStep], List[Any]]:
        """حل گام‌به‌گام دستگاه معادلات."""
        steps = []
        step_num = start_step

        # جداسازی معادلات
        eq_strings = [e.strip() for e in equations_str.split(',') if e.strip()]

        steps.append(SolutionStep(
            step_number=step_num,
            title="🔗 تشخیص دستگاه معادلات",
            description=(
                f"تعداد معادلات: {len(eq_strings)}\n"
                f"تعداد مجهول‌ها: {len(variables)}\n"
                f"معادلات:\n" + "\n".join(f"  {i+1}) {eq}" for i, eq in enumerate(eq_strings))
            ),
            step_type="explanation"
        ))
        step_num += 1

        # ساخت معادلات SymPy
        eqs = []
        for eq_str in eq_strings:
            sympy_eq = self._create_sympy_eq_safe(eq_str)
            if sympy_eq is not None:
                eqs.append(sympy_eq)

        if not eqs:
            return steps, []

        # نمایش ماتریسی (برای دستگاه 2×2)
        if len(variables) == 2 and len(eqs) == 2:
            try:
                matrix_a = []
                matrix_b = []
                for eq in eqs:
                    expanded = expand(eq.lhs - eq.rhs)
                    row = [
                        float(expanded.coeff(var, 1))
                        for var in syms
                    ]
                    const = float(-expanded.coeff(syms[0], 0))
                    matrix_a.append(row)
                    matrix_b.append(const)

                det = matrix_a[0][0] * matrix_a[1][1] - matrix_a[0][1] * matrix_a[1][0]

                steps.append(SolutionStep(
                    step_number=step_num,
                    title="📊 فرم ماتریسی",
                    description=self.templates.get_system_step(
                        4,
                        matrix_a=str(matrix_a),
                        matrix_b=str(matrix_b),
                        determinant=det
                    ),
                    step_type="calculation"
                ))
                step_num += 1
            except Exception:
                pass

        # حل دستگاه
        try:
            solutions = solve(eqs, syms, dict=True)
            if solutions:
                steps.append(SolutionStep(
                    step_number=step_num,
                    title="✅ جواب نهایی دستگاه",
                    description=self._format_solutions(solutions),
                    step_type="verification"
                ))
        except Exception:
            solutions = []

        return steps, solutions

    # ========================================================================
    # حل عمومی (Fallback)
    # ========================================================================

    def _solve_general(
        self,
        eq: Eq,
        variables: List[str],
        syms: List[Symbol],
        analysis: EquationAnalysis,
        start_step: int
    ) -> Tuple[List[SolutionStep], List[Any]]:
        """حل عمومی برای انواع دیگر معادلات."""
        steps = []
        step_num = start_step

        # گام: تشخیص نوع خاص
        if analysis.equation_type == EquationType.RATIONAL:
            steps.append(SolutionStep(
                step_number=step_num,
                title="🍕 تشخیص معادله کسری",
                description="تحلیل معادله کسری و یافتن محدودیت‌های دامنه...",
                step_type="explanation"
            ))
            step_num += 1

        # حل نمادین
        try:
            solutions = solve(eq, syms, dict=True)
            if not solutions and syms:
                solutions = list(solveset(eq, syms[0]))
        except Exception as e:
            solutions = []
            steps.append(SolutionStep(
                step_number=step_num,
                title="⚠️ خطا در حل نمادین",
                description=f"حل نمادین ناموفق بود: {str(e)}",
                step_type="explanation"
            ))

        # نمایش جواب‌ها
        if solutions:
            formatted = self._format_solutions(solutions)
            steps.append(SolutionStep(
                step_number=step_num + 1,
                title="🎯 جواب‌ها",
                description=f"جواب‌های یافت شده:\n{formatted}",
                step_type="verification"
            ))

        return steps, solutions

    # ========================================================================
    # متدهای کمکی
    # ========================================================================

    def _verify_solutions(
        self,
        eq: Optional[Eq],
        solutions: List[Any],
        variables: List[str]
    ) -> Optional[bool]:
        """تأیید جواب‌ها با جایگذاری در معادله اصلی."""
        if eq is None:
            return None

        try:
            syms = symbols(variables)
            for sol in solutions:
                if isinstance(sol, dict):
                    substituted = eq
                    for var, val in sol.items():
                        if hasattr(val, 'is_real') or hasattr(val, 'is_number'):
                            substituted = substituted.subs(var, val)
                    if hasattr(substituted, 'lhs') and hasattr(substituted, 'rhs'):
                        try:
                            if abs(float(substituted.lhs - substituted.rhs)) > 1e-10:
                                return False
                        except (TypeError, ValueError):
                            pass
            return True
        except Exception:
            return None

    def _compute_numeric_solutions(
        self,
        equation: str,
        variables: List[str]
    ) -> Optional[List[complex]]:
        """محاسبه جواب‌های عددی با nroots."""
        try:
            if '=' in equation:
                lhs, rhs = equation.split('=', 1)
                expr_str = f"({lhs}) - ({rhs})"
            else:
                expr_str = equation

            sympy_expr = parse_expr(
                expr_str,
                transformations=EquationParser.TRANSFORMATIONS
            )

            if variables:
                numeric_roots = nroots(sympy_expr, n=15)
                return [
                    complex(float(x)) if x.is_real else complex(x)
                    for x in numeric_roots
                ]
        except Exception:
            pass

        return None

    # ----- متدهای استاتیک کمکی -----

    @staticmethod
    def _get_type_name(eq_type: EquationType) -> str:
        """نام فارسی نوع معادله."""
        names = {
            EquationType.LINEAR: "خطی (درجه اول)",
            EquationType.QUADRATIC: "درجه دوم",
            EquationType.CUBIC: "درجه سوم",
            EquationType.QUARTIC: "درجه چهارم",
            EquationType.POLYNOMIAL: "چندجمله‌ای",
            EquationType.RATIONAL: "گویا (کسری)",
            EquationType.RADICAL: "رادیکالی",
            EquationType.EXPONENTIAL: "نمایی",
            EquationType.LOGARITHMIC: "لگاریتمی",
            EquationType.TRIGONOMETRIC: "مثلثاتی",
            EquationType.SYSTEM: "دستگاه معادلات",
            EquationType.DIFFERENTIAL: "دیفرانسیل",
            EquationType.UNKNOWN: "نامشخص",
        }
        return names.get(eq_type, "نامشخص")

    @staticmethod
    def _get_difficulty_name(diff: DifficultyLevel) -> str:
        """نام فارسی سطح دشواری."""
        names = {
            DifficultyLevel.BASIC: "پایه 📘",
            DifficultyLevel.INTERMEDIATE: "متوسط 📙",
            DifficultyLevel.ADVANCED: "پیشرفته 📗",
            DifficultyLevel.EXPERT: "تخصصی 📕",
        }
        return names.get(diff, "متوسط")

    @staticmethod
    def _suggest_method(analysis: EquationAnalysis) -> str:
        """پیشنهاد روش حل بر اساس نوع معادله."""
        methods = {
            EquationType.LINEAR: "انتقال و ساده‌سازی",
            EquationType.QUADRATIC: "فرمول دلتا / تجزیه / مربع کامل",
            EquationType.CUBIC: "فرمول کاردانو / تجزیه",
            EquationType.SYSTEM: "حذفی یا جایگزینی",
            EquationType.RATIONAL: "ضرب در مخرج مشترک",
            EquationType.RADICAL: "توان‌رسانی دو طرف",
            EquationType.EXPONENTIAL: "لگاریتم‌گیری",
            EquationType.LOGARITHMIC: "خروج از لگاریتم",
            EquationType.TRIGONOMETRIC: "اتحادهای مثلثاتی",
        }
        return methods.get(analysis.equation_type, "حل مستقیم")

    @staticmethod
    def _get_domain(analysis: EquationAnalysis) -> str:
        """تعیین دامنه معادله."""
        if analysis.has_fractions:
            return "ℝ - {مقادیر صفرکننده مخرج}"
        elif analysis.has_radicals:
            return "زیر رادیکال ≥ 0"
        return "ℝ (همه اعداد حقیقی)"

    @staticmethod
    def _get_alternative_methods(analysis: EquationAnalysis) -> List[str]:
        """روش‌های جایگزین حل."""
        alternatives = {
            EquationType.QUADRATIC: [
                "تجزیه به عوامل",
                "مربع کامل کردن",
                "روش هندسی (رسم سهمی)"
            ],
            EquationType.SYSTEM: [
                "روش ماتریسی (معکوس ماتریس)",
                "روش کرامر",
                "روش حذفی گاوسی"
            ],
            EquationType.LINEAR: [
                "روش نموداری (رسم خط)"
            ],
        }
        return alternatives.get(analysis.equation_type, [])

    @staticmethod
    def _format_solutions(solutions: List[Any]) -> str:
        """فرمت‌بندی زیبای جواب‌ها."""
        if not solutions:
            return "❌ جوابی یافت نشد."

        if isinstance(solutions[0], dict):
            parts = []
            for i, sol in enumerate(solutions, 1):
                for var, val in sol.items():
                    parts.append(f"  {var} = {val}")
            return '\n'.join(parts)

        return ', '.join(str(s) for s in solutions)

    @staticmethod
    def _get_power_conversions(original: str) -> str:
        """تشخیص تبدیلات توان در استانداردسازی."""
        conversions = []
        if '²' in original:
            conversions.append("² → **2")
        if '³' in original:
            conversions.append("³ → **3")
        if '⁴' in original:
            conversions.append("⁴ → **4")
        if '^' in original:
            conversions.append("^ → **")
        return ', '.join(conversions) if conversions else "بدون تغییر"

    @staticmethod
    def _simplify_rational(
        value: float,
        tolerance: float = 1e-9
    ) -> Union[float, str]:
        """
        ساده‌سازی اعداد گویا برای نمایش بهتر.

        اعداد صحیح را بدون اعشار و کسرها را به صورت a/b نمایش می‌دهد.
        """
        # بررسی عدد صحیح
        if abs(value - round(value)) < tolerance:
            return round(value)

        # تلاش برای نمایش به صورت کسر
        from fractions import Fraction
        try:
            frac = Fraction(value).limit_denominator(1000)
            if abs(float(frac) - value) < tolerance:
                return str(frac)
        except Exception:
            pass

        return round(value, 6)

    def _create_error_solution(
        self,
        equation: str,
        error_msg: str,
        start_time: float
    ) -> EquationSolution:
        """ساخت نتیجه استاندارد برای حالت خطا."""
        execution_time = (time.perf_counter() - start_time) * 1000

        return EquationSolution(
            original_equation=equation,
            processed_equation=equation,
            analysis=EquationAnalysis(
                equation_type=EquationType.UNKNOWN,
                difficulty=DifficultyLevel.INTERMEDIATE,
                variables=[],
                degree=0,
                is_homogeneous=False,
                has_fractions=False,
                has_radicals=False,
                term_count=0,
                complexity_score=0.5
            ),
            steps=[SolutionStep(
                step_number=1,
                title="❌ خطا",
                description=error_msg,
                step_type="explanation"
            )],
            solutions=[],
            solution_count=0,
            execution_time_ms=execution_time
        )

# ============================================================================
# پردازش موازی برای حل چند معادله همزمان
# ============================================================================

class ParallelEquationSolver:
    """
    حل‌کننده موازی برای پردازش همزمان چند معادله.

    از ThreadPoolExecutor برای اجرای موازی استفاده می‌کند.
    """

    def __init__(self, max_workers: int = None):
        """
        Args:
            max_workers: تعداد worker threadها (پیش‌فرض: تعداد CPUها)
        """
        import os
        self.max_workers = max_workers or os.cpu_count() or 4
        self.solver = StepByStepSolver()

    def solve_batch(
        self, equations: List[str], show_progress: bool = False
    ) -> pd.DataFrame:
        """
        حل دسته‌ای چند معادله به صورت موازی.

        Args:
            equations: لیست معادلات
            show_progress: نمایش پیشرفت

        Returns:
            DataFrame حاوی نتایج همه معادلات
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_eq = {
                executor.submit(self.solver.solve, eq): eq
                for eq in equations
            }

            completed = 0
            total = len(equations)

            for future in as_completed(future_to_eq):
                eq = future_to_eq[future]
                try:
                    result = future.result()
                    results.append({
                        'equation': eq,
                        'type': result.analysis.equation_type.name,
                        'difficulty': result.analysis.difficulty.name,
                        'solutions': str(result.solutions),
                        'solution_count': result.solution_count,
                        'steps_count': len(result.steps),
                        'time_ms': round(result.execution_time_ms, 2),
                        'success': (result.solution_count > 0 and
            result.analysis.equation_type != EquationType.UNKNOWN)
                    })
                except Exception as e:
                    results.append({
                        'equation': eq,
                        'type': 'ERROR',
                        'difficulty': 'N/A',
                        'solutions': str(e),
                        'solution_count': 0,
                        'steps_count': 0,
                        'time_ms': 0,
                        'success': False
                    })

                completed += 1
                if show_progress:
                    logger.info(f"Progress: {completed}/{total}")

        return pd.DataFrame(results)


# ============================================================================
# کلاس Facade
# ============================================================================

class EquationSolverEngine:
    """
    Facade برای کل سیستم حل معادلات.

    API ساده برای استفاده در UI یا سایر بخش‌ها.
    """

    def __init__(self):
        self._solver = StepByStepSolver()
        self._parallel = ParallelEquationSolver()

    def solve(self, equation: str, detailed: bool = True) -> EquationSolution:
        """
        حل یک معادله.

        Args:
            equation: رشته معادله
            detailed: آیا گام‌های حل ارائه شود؟

        Returns:
            EquationSolution با تمام اطلاعات حل
        """
        return self._solver.solve(equation)

    def solve_quick(self, equation: str) -> List[Any]:
        """
        حل سریع (فقط جواب نهایی، بدون گام).

        Args:
            equation: رشته معادله

        Returns:
            لیست جواب‌ها
        """
        result = self._solver.solve(equation)
        return result.solutions

    def solve_batch(self, equations: List[str]) -> pd.DataFrame:
        """
        حل دسته‌ای چند معادله.

        Args:
            equations: لیست معادلات

        Returns:
            DataFrame نتایج
        """
        return self._parallel.solve_batch(equations)

    def analyze(self, equation: str) -> EquationAnalysis:
        """
        تحلیل یک معادله بدون حل کامل.

        Args:
            equation: رشته معادله

        Returns:
            EquationAnalysis
        """
        _, variables, _ = EquationParser.parse(equation)
        if not variables:
            variables = ['x']
        return EquationAnalyzer.analyze(equation, tuple(variables))
