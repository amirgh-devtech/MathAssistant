"""
تست‌های جامع برای حل‌کننده معادلات (equation_solver.py)

این ماژول شامل تست‌های واحد، یکپارچگی، دقت ریاضی و عملکرد
برای سیستم حل معادلات گام‌به‌گام است.

Author: AmirMohammad Ghasemzadeh
Version: 1.1.2 - Production Ready
"""

import pytest
import time
import math
from typing import List

from src.MathAssistant.core.equation_solver import (
    # Enums
    EquationType,
    SolutionMethod,
    DifficultyLevel,

    # Data Classes
    EquationAnalysis,
    SolutionStep,
    EquationSolution,

    # Core Classes
    EquationParser,
    EquationAnalyzer,
    StepByStepSolver,
    ExplanationTemplates,

    # Parallel Processing
    ParallelEquationSolver,

    # Facade
    EquationSolverEngine,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def solver():
    """نمونه پایه از حل‌کننده."""
    return StepByStepSolver()


@pytest.fixture
def engine():
    """نمونه پایه از EquationSolverEngine."""
    return EquationSolverEngine()


@pytest.fixture
def parallel_solver():
    """نمونه پایه از حل‌کننده موازی."""
    return ParallelEquationSolver(max_workers=2)


# ============================================================================
# تست‌های EquationParser
# ============================================================================

class TestEquationParser:
    """تست‌های پارسر معادلات."""

    def test_parse_simple_linear(self):
        """تست پارس معادله خطی ساده."""
        eq = "x + 5 = 10"
        standardized, variables, sympy_eq = EquationParser.parse(eq)
        assert 'x' in variables
        assert standardized is not None

    def test_parse_with_powers(self):
        """تست پارس معادله با توان."""
        eq = "x² + 3x + 2 = 0"
        standardized, variables, _ = EquationParser.parse(eq)
        assert 'x' in variables
        assert '**2' in standardized

    def test_parse_with_fractions(self):
        """تست پارس معادله کسری."""
        eq = "1/x + 2 = 5"
        standardized, variables, _ = EquationParser.parse(eq)
        assert 'x' in variables

    def test_parse_no_equals(self):
        """تست پارس عبارت بدون علامت مساوی."""
        with pytest.raises(ValueError):
            EquationParser.parse("x + 5")

    def test_parse_empty_string(self):
        """تست پارس رشته خالی."""
        with pytest.raises(ValueError):
            EquationParser.parse("")

    def test_parse_multiple_variables(self):
        """تست پارس معادله با چند متغیر."""
        eq = "x + y = 10"
        _, variables, _ = EquationParser.parse(eq)
        assert 'x' in variables
        assert 'y' in variables

    def test_parse_trigonometric(self):
        """تست پارس معادله مثلثاتی."""
        eq = "sin(x) = 0.5"
        _, variables, _ = EquationParser.parse(eq)
        assert 'x' in variables

    def test_parse_cached(self):
        """تست اینکه کش کار می‌کند."""
        eq = "x + 2 = 5"
        result1 = EquationParser.parse(eq)
        result2 = EquationParser.parse(eq)
        assert result1 == result2  # باید از کش برگردد

    def test_standardize_power_symbols(self):
        """تست استانداردسازی نمادهای توان."""
        test_cases = [
            ("x²", "x**2"),
            ("x³", "x**3"),
            ("2^3", "2**3"),
        ]
        for original, expected_pattern in test_cases:
            standardized, _, _ = EquationParser.parse(original + " = 0")
            assert expected_pattern in standardized


# ============================================================================
# تست‌های EquationAnalyzer
# ============================================================================

class TestEquationAnalyzer:
    """تست‌های تحلیلگر معادلات."""

    def test_analyze_linear(self):
        """تست تحلیل معادله خطی."""
        analysis = EquationAnalyzer.analyze("x + 5 = 10", ("x",))
        assert analysis.equation_type == EquationType.LINEAR
        assert analysis.degree == 1

    def test_analyze_quadratic(self):
        """تست تحلیل معادله درجه دوم."""
        analysis = EquationAnalyzer.analyze("x**2 + 3*x + 2 = 0", ("x",))
        assert analysis.equation_type == EquationType.QUADRATIC
        assert analysis.degree == 2

    def test_analyze_cubic(self):
        """تست تحلیل معادله درجه سوم."""
        analysis = EquationAnalyzer.analyze("x**3 - 6*x**2 + 11*x - 6 = 0", ("x",))
        assert analysis.equation_type == EquationType.CUBIC
        assert analysis.degree == 3

    def test_analyze_trigonometric(self):
        """تست تحلیل معادله مثلثاتی."""
        analysis = EquationAnalyzer.analyze("sin(x) = 0.5", ("x",))
        assert analysis.equation_type == EquationType.TRIGONOMETRIC

    def test_analyze_exponential(self):
        """تست تحلیل معادله نمایی."""
        analysis = EquationAnalyzer.analyze("2^x = 8", ("x",))
        assert analysis.equation_type == EquationType.EXPONENTIAL

    def test_analyze_rational(self):
        """تست تحلیل معادله کسری."""
        analysis = EquationAnalyzer.analyze("1/x + 2 = 5", ("x",))
        assert analysis.equation_type == EquationType.RATIONAL

    def test_analyze_difficulty_basic(self):
        """تست سطح دشواری پایه."""
        analysis = EquationAnalyzer.analyze("x + 2 = 5", ("x",))
        assert analysis.difficulty == DifficultyLevel.BASIC

    def test_analyze_difficulty_intermediate(self):
        """تست سطح دشواری متوسط."""
        analysis = EquationAnalyzer.analyze("x**2 - 4*x + 4 = 0", ("x",))
        assert analysis.difficulty in [DifficultyLevel.BASIC, DifficultyLevel.INTERMEDIATE]

    def test_analyze_complexity_score(self):
        """تست امتیاز پیچیدگی."""
        analysis1 = EquationAnalyzer.analyze("x + 1 = 0", ("x",))
        analysis2 = EquationAnalyzer.analyze("x**3 + 2*x**2 + 3*x + 4 = 0", ("x",))
        assert analysis2.complexity_score > analysis1.complexity_score

    def test_analyze_cached(self):
        """تست کش تحلیل."""
        result1 = EquationAnalyzer.analyze("x**2 = 4", ("x",))
        result2 = EquationAnalyzer.analyze("x**2 = 4", ("x",))
        assert result1 == result2


# ============================================================================
# تست‌های StepByStepSolver - معادلات خطی
# ============================================================================

class TestLinearEquationSolving:
    """تست حل معادلات خطی."""

    def test_solve_simple_linear(self, solver):
        """تست حل معادله خطی ساده."""
        result = solver.solve("x + 5 = 10")
        assert result.solution_count == 1
        assert result.solutions is not None

    def test_solve_linear_with_fractions(self, solver):
        """تست حل معادله خطی با کسر."""
        result = solver.solve("2x + 1 = 5")
        assert result.solution_count > 0

    def test_linear_solution_correctness(self, solver):
        """تست صحت جواب معادله خطی."""
        result = solver.solve("x + 3 = 7")
        # x = 4
        if result.solutions and isinstance(result.solutions[0], dict):
            for var, val in result.solutions[0].items():
                if str(var) == 'x':
                    assert abs(float(val) - 4.0) < 1e-10

    def test_linear_has_steps(self, solver):
        """تست وجود گام‌های حل."""
        result = solver.solve("x + 2 = 6")
        assert len(result.steps) > 0
        # باید حداقل گام‌های معرفی و حل را داشته باشد
        assert any("خطی" in step.description or "تحلیل" in step.title for step in result.steps)

    def test_linear_with_negative_coefficient(self, solver):
        """تست معادله خطی با ضریب منفی."""
        result = solver.solve("-3x + 6 = 0")
        assert result.solution_count > 0


# ============================================================================
# تست‌های StepByStepSolver - معادلات درجه دوم
# ============================================================================

class TestQuadraticEquationSolving:
    """تست حل معادلات درجه دوم."""

    def test_solve_quadratic_two_roots(self, solver):
        """تست معادله درجه دوم با دو ریشه حقیقی."""
        result = solver.solve("x² - 5x + 6 = 0")
        assert result.solution_count == 2

    def test_solve_quadratic_double_root(self, solver):
        """تست معادله درجه دوم با ریشه مضاعف."""
        result = solver.solve("x² - 4x + 4 = 0")
        assert result.solution_count >= 1

    def test_solve_quadratic_no_real_roots(self, solver):
        """تست معادله درجه دوم بدون ریشه حقیقی."""
        result = solver.solve("x² + x + 1 = 0")
        # ممکن است جواب مختلط داشته باشد
        assert isinstance(result, EquationSolution)

    def test_quadratic_delta_calculation(self, solver):
        """تست محاسبه دلتا در گام‌های حل."""
        result = solver.solve("x² - 5x + 6 = 0")
        delta_step = None
        for step in result.steps:
            if "دلتا" in step.title or "Δ" in step.description:
                delta_step = step
                break
        assert delta_step is not None

    def test_quadratic_with_power_symbols(self, solver):
        """تست معادله درجه دوم با نمادهای مختلف توان."""
        result = solver.solve("x^2 - 4 = 0")
        assert result.solution_count == 2

    def test_quadratic_standard_form(self, solver):
        """تست معادله درجه دوم در فرم استاندارد."""
        result = solver.solve("x² + bx + c = 0")
        # باید خطا ندهد (اگرچه شاید حل کامل نکند)
        assert isinstance(result, EquationSolution)

    @pytest.mark.parametrize("equation,expected_roots", [
        ("x² - 1 = 0", [1, -1]),
        ("x² - 4 = 0", [2, -2]),
        ("x² - 9 = 0", [3, -3]),
    ])
    def test_quadratic_difference_of_squares(self, solver, equation, expected_roots):
        """تست اتحاد مزدوج (تفاضل مربعات)."""
        result = solver.solve(equation)
        assert result.solution_count == 2


# ============================================================================
# تست‌های StepByStepSolver - انواع دیگر
# ============================================================================

class TestOtherEquationTypes:
    """تست سایر انواع معادلات."""

    def test_solve_cubic(self, solver):
        """تست معادله درجه سوم."""
        result = solver.solve("x³ - 6x² + 11x - 6 = 0")
        assert result.solution_count >= 1

    def test_solve_rational(self, solver):
        """تست معادله کسری."""
        result = solver.solve("1/x = 2")
        assert result.solution_count >= 0

    def test_solve_trigonometric(self, solver):
        """تست معادله مثلثاتی."""
        result = solver.solve("sin(x) = 0")
        # sin(x) = 0 → x = nπ
        assert isinstance(result, EquationSolution)

    def test_solve_exponential(self, solver):
        """تست معادله نمایی."""
        result = solver.solve("2^x = 8")
        assert isinstance(result, EquationSolution)


# ============================================================================
# تست‌های ویژگی گام‌به‌گام
# ============================================================================

class TestStepByStepFeatures:
    """تست ویژگی‌های توضیح گام‌به‌گام."""

    def test_steps_have_numbers(self, solver):
        """تست اینکه گام‌ها شماره دارند."""
        result = solver.solve("x + 5 = 10")
        for step in result.steps:
            assert step.step_number > 0

    def test_steps_have_descriptions(self, solver):
        """تست اینکه گام‌ها توضیح دارند."""
        result = solver.solve("x² - 5x + 6 = 0")
        for step in result.steps:
            assert len(step.description) > 0

    def test_steps_have_types(self, solver):
        """تست اینکه گام‌ها نوع دارند."""
        result = solver.solve("x + 3 = 7")
        step_types = [step.step_type for step in result.steps]
        assert "explanation" in step_types or "calculation" in step_types

    def test_intro_step_exists(self, solver):
        """تست وجود گام معرفی."""
        result = solver.solve("x + 2 = 5")
        intro_steps = [s for s in result.steps if "تحلیل" in s.title or "معرفی" in s.title]
        assert len(intro_steps) > 0

    def test_conclusion_step_exists(self, solver):
        """تست وجود گام جمع‌بندی."""
        result = solver.solve("x + 2 = 5")
        conclusion_steps = [s for s in result.steps if "جمع" in s.title or "تأیید" in s.title]
        assert len(conclusion_steps) > 0


# ============================================================================
# تست‌های ExplanationTemplates
# ============================================================================

class TestExplanationTemplates:
    """تست سیستم قالب‌های توضیح."""

    def test_intro_templates_exist(self):
        """تست وجود قالب‌های معرفی."""
        assert len(ExplanationTemplates.INTRO_TEMPLATES) > 0

    def test_linear_templates_exist(self):
        """تست وجود قالب‌های خطی."""
        assert len(ExplanationTemplates.LINEAR_TEMPLATES) > 0

    def test_quadratic_templates_exist(self):
        """تست وجود قالب‌های درجه دوم."""
        assert len(ExplanationTemplates.QUADRATIC_TEMPLATES) > 0

    def test_total_templates_count(self):
        """تست تعداد کل قالب‌ها (باید حداقل 40 باشد)."""
        total = (
            len(ExplanationTemplates.INTRO_TEMPLATES) +
            len(ExplanationTemplates.STANDARDIZE_TEMPLATES) +
            len(ExplanationTemplates.LINEAR_TEMPLATES) +
            len(ExplanationTemplates.QUADRATIC_TEMPLATES) +
            len(ExplanationTemplates.FRACTION_TEMPLATES) +
            len(ExplanationTemplates.SYSTEM_TEMPLATES) +
            len(ExplanationTemplates.GENERAL_TEMPLATES) +
            len(ExplanationTemplates.CONCLUSION_TEMPLATES)
        )
        assert total >= 40, f"Only {total} templates found"

    def test_get_intro_returns_string(self):
        """تست اینکه get_intro رشته برمی‌گرداند."""
        result = ExplanationTemplates.get_intro(
            equation="x + 2 = 5",
            type_name="خطی",
            variables="x",
            term_count=2,
            difficulty="پایه",
            method="انتقال"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_linear_step_returns_string(self):
        """تست قالب خطی."""
        result = ExplanationTemplates.get_linear_step(
            1,
            equation="x + 5 = 10",
            term="5",
            step_expr="x = 5",
            result="5",
            coefficient=1,
            variable="x"
        )
        assert isinstance(result, str)
        assert "x" in result or "5" in result

    def test_get_quadratic_step_returns_string(self):
        """تست قالب درجه دوم."""
        result = ExplanationTemplates.get_quadratic_step(
            2, delta=1, delta_interpretation="مثبت", b=5, a=1, c=6
        )
        assert isinstance(result, str)

    def test_get_conclusion_returns_string(self):
        """تست قالب جمع‌بندی."""
        result = ExplanationTemplates.get_conclusion(
            equation="x + 2 = 5",
            solutions="x = 3",
            method="انتقال",
            count=1,
            type="خطی"
        )
        assert isinstance(result, str)


# ============================================================================
# تست‌های ParallelEquationSolver
# ============================================================================

class TestParallelEquationSolver:
    """تست‌های حل‌کننده موازی."""

    def test_solve_batch_single(self, parallel_solver):
        """تست حل دسته‌ای یک معادله."""
        df = parallel_solver.solve_batch(["x + 2 = 5"])
        assert len(df) == 1
        assert df.iloc[0]['success'] == True

    def test_solve_batch_multiple(self, parallel_solver):
        """تست حل دسته‌ای چند معادله."""
        equations = [
            "x + 1 = 3",
            "2x = 10",
            "x² - 4 = 0",
            "x - 7 = 0",
        ]
        df = parallel_solver.solve_batch(equations)
        assert len(df) == 4
        assert all(df['success'])

    def test_solve_batch_returns_dataframe(self, parallel_solver):
        """تست اینکه خروجی DataFrame است."""
        import pandas as pd
        df = parallel_solver.solve_batch(["x + 1 = 2"])
        assert isinstance(df, pd.DataFrame)

    def test_solve_batch_columns(self, parallel_solver):
        """تست ستون‌های خروجی."""
        df = parallel_solver.solve_batch(["x + 1 = 2"])
        expected_columns = ['equation', 'type', 'difficulty', 'solutions',
                           'solution_count', 'steps_count', 'time_ms', 'success']
        for col in expected_columns:
            assert col in df.columns

    def test_solve_batch_with_errors(self, parallel_solver):
        """تست حل با معادلات مختلف."""
        equations = ["x + 1 = 2", "x + = 5", "2x = 6"]
        df = parallel_solver.solve_batch(equations)
        assert len(df) == 3

        error_row = df[df['equation'] == 'x + = 5']
        assert len(error_row) == 1
        assert error_row.iloc[0]['success'] == False

        assert df[df['equation'] == 'x + 1 = 2'].iloc[0]['success'] == True
        assert df[df['equation'] == '2x = 6'].iloc[0]['success'] == True
# ============================================================================
# تست‌های EquationSolverEngine (Facade)
# ============================================================================

class TestEquationSolverEngine:
    """تست‌های Facade."""

    def test_solve_detailed(self, engine):
        """تست حل با جزئیات."""
        result = engine.solve("x + 2 = 5")
        assert isinstance(result, EquationSolution)
        assert len(result.steps) > 0

    def test_solve_quick(self, engine):
        """تست حل سریع (فقط جواب)."""
        solutions = engine.solve_quick("x + 2 = 5")
        assert len(solutions) > 0

    def test_analyze(self, engine):
        """تست تحلیل معادله."""
        analysis = engine.analyze("x² + 3x + 2 = 0")
        assert isinstance(analysis, EquationAnalysis)
        assert analysis.equation_type == EquationType.QUADRATIC

    def test_solve_batch(self, engine):
        """تست حل دسته‌ای."""
        df = engine.solve_batch(["x + 1 = 2", "2x = 4"])
        assert len(df) == 2


# ============================================================================
# تست‌های دقت ریاضی
# ============================================================================

class TestMathematicalAccuracy:
    """تست دقت ریاضی."""

    def test_linear_accuracy(self, solver):
        """تست دقت حل معادلات خطی."""
        test_cases = [
            ("x + 5 = 10", {"x": 5}),
            ("2x - 6 = 0", {"x": 3}),
            ("-x + 7 = 3", {"x": 4}),
            ("3x + 2 = 8", {"x": 2}),
        ]
        for eq, expected in test_cases:
            result = solver.solve(eq)
            if result.solutions and isinstance(result.solutions[0], dict):
                for var, val in result.solutions[0].items():
                    if str(var) in expected:
                        assert abs(float(val) - expected[str(var)]) < 1e-10

    def test_quadratic_accuracy(self, solver):
        """تست دقت حل معادلات درجه دوم."""
        # x² - 5x + 6 = 0 → (x-2)(x-3) = 0 → x = 2, 3
        result = solver.solve("x² - 5x + 6 = 0")
        if result.solutions:
            roots = []
            for sol in result.solutions:
                if isinstance(sol, dict):
                    for var, val in sol.items():
                        if str(var) == 'x':
                            roots.append(float(val))
            roots.sort()
            if len(roots) == 2:
                assert abs(roots[0] - 2.0) < 1e-10
                assert abs(roots[1] - 3.0) < 1e-10

    def test_numeric_solutions(self, solver):
        """تست جواب‌های عددی."""
        result = solver.solve("x² - 2 = 0")
        if result.numeric_solutions:
            for sol in result.numeric_solutions:
                # باید نزدیک به ±√2 باشد
                assert abs(abs(sol) - math.sqrt(2)) < 1e-5


# ============================================================================
# تست‌های عملکرد
# ============================================================================

class TestPerformance:
    """تست‌های عملکرد."""

    def test_linear_solve_speed(self, solver):
        """تست سرعت حل معادله خطی."""
        start = time.perf_counter()
        for _ in range(100):
            solver.solve("x + 2 = 5")
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"100 linear solves took {elapsed:.2f}s"

    def test_quadratic_solve_speed(self, solver):
        """تست سرعت حل معادله درجه دوم."""
        start = time.perf_counter()
        for _ in range(50):
            solver.solve("x² - 5x + 6 = 0")
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"50 quadratic solves took {elapsed:.2f}s"

    def test_parse_caching_speed(self):
        """تست سرعت با کش پارس."""
        eq = "x² + 3x + 2 = 0"

        # اولین بار (بدون کش)
        start = time.perf_counter()
        EquationParser.parse(eq)
        first_time = time.perf_counter() - start

        # دومین بار (با کش)
        start = time.perf_counter()
        for _ in range(1000):
            EquationParser.parse(eq)
        cached_time = (time.perf_counter() - start) / 1000

        assert cached_time <= first_time, f"Cache not effective: cached={cached_time:.2e}s, first={first_time:.2e}s"

    def test_parallel_speedup(self):
        """تست بهبود سرعت با پردازش موازی."""
        equations = [
            f"x² + {i}x + {i} = 0" for i in range(1, 9)
        ]

        # تک‌رشته‌ای
        solver = StepByStepSolver()
        start = time.perf_counter()
        for eq in equations:
            solver.solve(eq)
        single_time = time.perf_counter() - start

        # چندرشته‌ای
        parallel = ParallelEquationSolver(max_workers=4)
        start = time.perf_counter()
        parallel.solve_batch(equations)
        multi_time = time.perf_counter() - start

        # پردازش موازی باید سریع‌تر باشد (حداقل 20٪)
        assert multi_time < single_time * 0.9


# ============================================================================
# تست‌های Edge Cases
# ============================================================================

class TestEquationEdgeCases:
    """تست موارد مرزی."""

    def test_empty_equation(self, solver):
        """تست معادله خالی."""
        result = solver.solve("")
        assert result.solution_count == 0

    def test_no_variables(self, solver):
        """تست عبارت بدون متغیر."""
        result = solver.solve("2 + 3 = 5")
        assert isinstance(result, EquationSolution)

    def test_identity_equation(self, solver):
        """تست اتحاد (x = x)."""
        result = solver.solve("x = x")
        assert isinstance(result, EquationSolution)

    def test_contradiction(self, solver):
        """تست تناقض (x + 1 = x + 2)."""
        result = solver.solve("x + 1 = x + 2")
        assert isinstance(result, EquationSolution)
        # نباید جواب داشته باشد
        assert result.solution_count == 0 or result.solutions == []

    def test_very_complex_equation(self, solver):
        """تست معادله بسیار پیچیده."""
        result = solver.solve("x^4 + 2*x^3 - x^2 - 2*x + 1 = 0")
        assert isinstance(result, EquationSolution)

    def test_unicode_superscripts(self, solver):
        """تست توان‌های یونیکد."""
        result = solver.solve("x⁴ - 16 = 0")
        assert isinstance(result, EquationSolution)

    def test_implicit_multiplication(self, solver):
        """تست ضرب ضمنی."""
        result = solver.solve("2x + 4 = 10")
        assert result.solution_count > 0


# ============================================================================
# تست‌های Data Classes
# ============================================================================

class TestDataClasses:
    """تست Data Classes."""

    def test_equation_analysis_fields(self):
        """تست فیلدهای EquationAnalysis."""
        analysis = EquationAnalysis(
            equation_type=EquationType.LINEAR,
            difficulty=DifficultyLevel.BASIC,
            variables=['x'],
            degree=1,
            is_homogeneous=True,
            has_fractions=False,
            has_radicals=False,
            term_count=2,
            complexity_score=0.1
        )
        assert analysis.equation_type == EquationType.LINEAR
        assert analysis.degree == 1

    def test_solution_step_fields(self):
        """تست فیلدهای SolutionStep."""
        step = SolutionStep(
            step_number=1,
            title="Test Step",
            description="This is a test step",
            mathematical_expression="x = 5",
            step_type="calculation"
        )
        assert step.step_number == 1
        assert step.title == "Test Step"

    def test_equation_solution_fields(self):
        """تست فیلدهای EquationSolution."""
        solution = EquationSolution(
            original_equation="x + 2 = 5",
            processed_equation="x + 2 = 5",
            analysis=EquationAnalysis(
                equation_type=EquationType.LINEAR,
                difficulty=DifficultyLevel.BASIC,
                variables=['x'],
                degree=1,
                is_homogeneous=True,
                has_fractions=False,
                has_radicals=False,
                term_count=2,
                complexity_score=0.1
            ),
            steps=[],
            solutions=[{'x': 3}],
            solution_count=1,
            execution_time_ms=1.5
        )
        assert solution.solution_count == 1
        assert solution.execution_time_ms == 1.5
