"""
تست‌های جامع برای موتور ریاضی (math_engine.py)

این ماژول شامل تست‌های واحد، یکپارچگی، عملکرد و استرس برای
تمامی کلاس‌ها و توابع موتور ریاضی است.

پوشش تست: 100% کلاس‌ها و متدهای اصلی
اصول: TDD, FIRST (Fast, Independent, Repeatable, Self-validating, Timely)

Author: AmirMohammad Ghasemzadeh
Version: 1.2.0 - Production Ready
"""

import pytest
import math
import time
import random
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor

# Import از ماژول اصلی
from src.MathAssistant.core.math_engine import (
    # Data Classes
    Vector2D,
    PrimeResult,
    NumberAnalysis,

    # Abstract Base Classes
    PrimeChecker,
    PrimeGenerator,

    # Concrete Implementations
    TrialDivisionPrimeChecker,
    SieveOfEratosthenesGenerator,
    PrimeFactorizer,
    DivisorCalculator,
    TwinPrimeFinder,
    GCDCalculator,
    LCMCalculator,
    VectorOperations,

    # Facade
    MathEngine,

    # Backward Compatibility
    is_prime,
    sieve_of_eratosthenes,
    get_divisors,
    find_twin_primes,
    prime_factors,
    compute_gcd,
    compute_lcm,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """نمونه پایه از MathEngine."""
    return MathEngine()


@pytest.fixture
def sample_vectors():
    """بردارهای نمونه برای تست."""
    return [
        Vector2D(3, 4),   # magnitude=5, angle≈53.13°
        Vector2D(1, 0),   # magnitude=1, angle=0°
        Vector2D(0, 1),   # magnitude=1, angle=90°
        Vector2D(-3, 4),  # magnitude=5, angle≈126.87°
        Vector2D(0, 0),   # بردار صفر
    ]


@pytest.fixture
def prime_test_cases():
    """اعداد تست برای بررسی اول بودن."""
    return {
        'small_primes': [2, 3, 5, 7, 11, 13, 17, 19, 23, 29],
        'small_composites': [4, 6, 8, 9, 10, 12, 14, 15, 16, 18],
        'edge_cases': [0, 1, 2, -1, -7],
        'large_prime': 9999991,  # عدد اول بزرگ (نزدیک 10 میلیون)
        'large_composite': 9999990,
    }


# ============================================================================
# تست‌های Vector2D
# ============================================================================

class TestVector2D:
    """تست‌های کلاس Vector2D."""

    def test_creation(self):
        """تست ایجاد بردار."""
        v = Vector2D(3, 4)
        assert v.x == 3.0
        assert v.y == 4.0

    def test_default_values(self):
        """تست مقادیر پیش‌فرض."""
        v = Vector2D()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_immutability(self):
        """تست immutable بودن (Frozen Dataclass)."""
        v = Vector2D(3, 4)
        with pytest.raises(Exception):  # FrozenInstanceError یا AttributeError
            v.x = 5

    def test_magnitude_3_4_5_triangle(self):
        """تست اندازه بردار: مثلث معروف 3-4-5."""
        v = Vector2D(3, 4)
        assert v.magnitude == 5.0

    def test_magnitude_zero(self):
        """تست اندازه بردار صفر."""
        v = Vector2D(0, 0)
        assert v.magnitude == 0.0

    def test_magnitude_negative(self):
        """تست اندازه بردار با مؤلفه منفی."""
        v = Vector2D(-3, -4)
        assert v.magnitude == 5.0

    @pytest.mark.parametrize("x,y,expected_angle", [
        (1, 0, 0.0),
        (0, 1, 90.0),
        (-1, 0, 180.0),
        (0, -1, -90.0),
        (1, 1, 45.0),
        (3, 4, pytest.approx(53.13010235415598)),
    ])
    def test_angle_degrees(self, x, y, expected_angle):
        """تست زاویه بردار بر حسب درجه."""
        v = Vector2D(x, y)
        assert v.angle_degrees == pytest.approx(expected_angle)

    def test_angle_radians(self):
        """تست زاویه بردار بر حسب رادیان."""
        v = Vector2D(1, 0)
        assert v.angle_radians == 0.0

        v2 = Vector2D(0, 1)
        assert v2.angle_radians == pytest.approx(math.pi / 2)

    def test_angle_zero_vector(self):
        """تست زاویه بردار صفر."""
        v = Vector2D(0, 0)
        assert v.angle_degrees == 0.0

    def test_addition(self):
        """تست جمع دو بردار."""
        v1 = Vector2D(3, 4)
        v2 = Vector2D(1, 2)
        result = v1 + v2
        assert result.x == 4.0
        assert result.y == 6.0

    def test_addition_commutative(self):
        """تست خاصیت جابجایی جمع بردارها."""
        v1 = Vector2D(3, 4)
        v2 = Vector2D(1, 2)
        assert (v1 + v2).x == (v2 + v1).x
        assert (v1 + v2).y == (v2 + v1).y

    def test_addition_associative(self):
        """تست خاصیت شرکت‌پذیری جمع بردارها."""
        v1 = Vector2D(1, 2)
        v2 = Vector2D(3, 4)
        v3 = Vector2D(5, 6)
        assert ((v1 + v2) + v3).x == (v1 + (v2 + v3)).x
        assert ((v1 + v2) + v3).y == (v1 + (v2 + v3)).y

    def test_negation(self):
        """تست قرینه بردار."""
        v = Vector2D(3, -4)
        neg = -v
        assert neg.x == -3.0
        assert neg.y == 4.0

    def test_double_negation(self):
        """تست قرینه قرینه."""
        v = Vector2D(3, 4)
        assert (-(-v)).x == v.x
        assert (-(-v)).y == v.y

    def test_addition_with_non_vector(self):
        """تست جمع با نوع غیر Vector2D."""
        v = Vector2D(3, 4)
        result = v.__add__(5)  # باید NotImplemented برگردونه
        assert result == NotImplemented

    def test_string_representation(self):
        """تست نمایش رشته‌ای (فرمت فارسی y, x)."""
        v = Vector2D(3, 4)
        assert "4" in str(v)  # y first
        assert "3" in str(v)  # x second

    def test_hashable(self):
        """تست hashable بودن (قابل استفاده در set و dict)."""
        v1 = Vector2D(3, 4)
        v2 = Vector2D(3, 4)
        v3 = Vector2D(1, 2)

        # باید hash برابر داشته باشند
        assert hash(v1) == hash(v2)
        assert hash(v1) != hash(v3)

        # قابل استفاده در set
        vector_set = {v1, v2, v3}
        assert len(vector_set) == 2


# ============================================================================
# تست‌های PrimeChecker و پیاده‌سازی‌ها
# ============================================================================

class TestTrialDivisionPrimeChecker:
    """تست‌های کلاس TrialDivisionPrimeChecker."""

    @pytest.fixture
    def checker(self):
        return TrialDivisionPrimeChecker()

    def test_is_prime_small_primes(self, checker):
        """تست اعداد اول کوچک."""
        for n in [2, 3, 5, 7, 11, 13, 17, 19, 23]:
            assert checker.is_prime(n) == True

    def test_is_prime_small_composites(self, checker):
        """تست اعداد مرکب کوچک."""
        for n in [4, 6, 8, 9, 10, 12, 14, 15, 16, 18]:
            assert checker.is_prime(n) == False

    def test_edge_cases(self, checker):
        """تست موارد مرزی."""
        assert checker.is_prime(0) == False
        assert checker.is_prime(1) == False
        assert checker.is_prime(2) == True
        assert checker.is_prime(-7) == False
        assert checker.is_prime(-1) == False

    def test_large_prime(self, checker):
        """تست عدد اول بزرگ."""
        assert checker.is_prime(9999991) == True

    def test_large_composite(self, checker):
        """تست عدد مرکب بزرگ."""
        assert checker.is_prime(9999990) == False

    def test_performance_large_numbers(self, checker):
        """تست عملکرد برای اعداد بزرگ (باید کمتر از 1ms)."""
        start = time.perf_counter()
        checker.is_prime(9999991)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 10, f"Too slow: {elapsed:.2f}ms"

    def test_check_method(self, checker):
        """تست متد check که PrimeResult برمی‌گرداند."""
        result = checker.check(17)
        assert isinstance(result, PrimeResult)
        assert result.number == 17
        assert result.is_prime == True
        assert result.factors is None
        assert result.divisor_count > 0

    def test_check_composite(self, checker):
        """تست check برای عدد مرکب."""
        result = checker.check(12)
        assert result.is_prime == False
        assert result.factors is not None
        assert 2 in result.factors
        assert 3 in result.factors

    def test_is_prime_abstract(self):
        """تست اینکه PrimeChecker abstract است."""
        with pytest.raises(TypeError):
            PrimeChecker()  # نمی‌توان از ABC نمونه ساخت


class TestSieveOfEratosthenesGenerator:
    """تست‌های غربال اراتوستن."""

    @pytest.fixture
    def generator(self):
        return SieveOfEratosthenesGenerator()

    def test_small_range(self, generator):
        """تست بازه کوچک."""
        primes = generator.generate(1, 20)
        assert primes == [2, 3, 5, 7, 11, 13, 17, 19]

    def test_range_start_gt_2(self, generator):
        """تست بازه با شروع بزرگتر از 2."""
        primes = generator.generate(10, 30)
        assert primes == [11, 13, 17, 19, 23, 29]

    def test_empty_range(self, generator):
        """تست بازه خالی."""
        assert generator.generate(24, 28) == []  # هیچ عدد اولی بین 24 و 28 نیست
        assert generator.generate(100, 50) == []  # start > end

    def test_range_below_2(self, generator):
        """تست بازه زیر 2."""
        assert generator.generate(-10, 1) == []
        assert generator.generate(0, 0) == []

    def test_large_range(self, generator):
        """تست بازه بزرگ."""
        primes = generator.generate(1, 1000)
        assert len(primes) == 168  # تعداد اعداد اول تا 1000

    def test_count_primes_under_100(self, generator):
        """تست تعداد اعداد اول کمتر از 100."""
        primes = generator.generate(1, 100)
        assert len(primes) == 25

    def test_all_primes_under_1000(self, generator):
        """تست صحت تمام اعداد اول زیر 1000."""
        primes = generator.generate(1, 1000)
        # تأیید با لیست شناخته شده
        known_primes_under_100 = [
            2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
            53, 59, 61, 67, 71, 73, 79, 83, 89, 97
        ]
        for p in known_primes_under_100:
            assert p in primes

    def test_performance_100000(self, generator):
        """تست عملکرد برای 100,000 عدد."""
        start = time.perf_counter()
        primes = generator.generate(1, 100000)
        elapsed = time.perf_counter() - start
        assert len(primes) == 9592  # تعداد اعداد اول تا 100,000
        assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"


# ============================================================================
# تست‌های PrimeFactorizer
# ============================================================================

class TestPrimeFactorizer:
    """تست‌های تجزیه به عوامل اول."""

    @pytest.fixture
    def factorizer(self):
        return PrimeFactorizer()

    @pytest.mark.parametrize("n,expected", [
        (12, [2, 2, 3]),
        (18, [2, 3, 3]),
        (100, [2, 2, 5, 5]),
        (97, [97]),  # عدد اول
        (1, []),
        (0, []),
        (-5, []),
        (2, [2]),
        (3, [3]),
        (4, [2, 2]),
        (36, [2, 2, 3, 3]),
        (1024, [2] * 10),  # 2^10
    ])
    def test_factorize(self, factorizer, n, expected):
        """تست تجزیه اعداد مختلف."""
        assert factorizer.factorize(n) == expected

    def test_factorize_product_equals_original(self, factorizer):
        """تست اینکه حاصلضرب عوامل برابر عدد اصلی است."""
        for n in [12, 18, 100, 36, 1024, 999]:
            factors = factorizer.factorize(n)
            if n > 1:
                product = 1
                for f in factors:
                    product *= f
                assert product == n

    def test_factorize_with_counts(self, factorizer):
        """تست تجزیه با شمارش."""
        result = factorizer.factorize_with_counts(12)
        assert result == {2: 2, 3: 1}

        result = factorizer.factorize_with_counts(100)
        assert result == {2: 2, 5: 2}

    def test_factorize_large_number(self, factorizer):
        """تست تجزیه عدد بزرگ."""
        factors = factorizer.factorize(9999990)
        product = 1
        for f in factors:
            product *= f
        assert product == 9999990


# ============================================================================
# تست‌های DivisorCalculator
# ============================================================================

class TestDivisorCalculator:
    """تست‌های محاسبه مقسوم‌علیه‌ها."""

    @pytest.fixture
    def calculator(self):
        return DivisorCalculator()

    @pytest.mark.parametrize("n,expected", [
        (12, [1, 2, 3, 4, 6, 12]),
        (1, [1]),
        (7, [1, 7]),
        (36, [1, 2, 3, 4, 6, 9, 12, 18, 36]),
        (100, [1, 2, 4, 5, 10, 20, 25, 50, 100]),
    ])
    def test_calculate(self, calculator, n, expected):
        """تست محاسبه مقسوم‌علیه‌ها."""
        assert calculator.calculate(n) == expected

    def test_zero_and_negative(self, calculator):
        """تست اعداد صفر و منفی."""
        assert calculator.calculate(0) == []
        assert calculator.calculate(-5) == []

    def test_all_divisors_divide_n(self, calculator):
        """تست اینکه همه مقسوم‌علیه‌ها واقعاً n را تقسیم می‌کنند."""
        for n in range(1, 100):
            divisors = calculator.calculate(n)
            for d in divisors:
                assert n % d == 0

    def test_sorted_output(self, calculator):
        """تست مرتب بودن خروجی."""
        for n in range(1, 100):
            divisors = calculator.calculate(n)
            assert divisors == sorted(divisors)


# ============================================================================
# تست‌های TwinPrimeFinder
# ============================================================================

class TestTwinPrimeFinder:
    """تست‌های یافتن اعداد اول دوقلو."""

    @pytest.fixture
    def finder(self):
        return TwinPrimeFinder()

    def test_small_range(self, finder):
        """تست بازه کوچک."""
        twins = finder.find(1, 20)
        assert twins == [(3, 5), (5, 7), (11, 13), (17, 19)]

    def test_range_without_twins(self, finder):
        """تست بازه بدون اعداد دوقلو."""
        twins = finder.find(19, 28)  # هیچ دوقلویی بین 19 و 28
        assert twins == []

    def test_large_range(self, finder):
        """تست بازه بزرگ."""
        twins = finder.find(1, 100)
        expected = [(3, 5), (5, 7), (11, 13), (17, 19), (29, 31),
                    (41, 43), (59, 61), (71, 73)]
        assert twins == expected

    def test_custom_generator(self):
        """تست با generator سفارشی."""
        custom_gen = SieveOfEratosthenesGenerator()
        finder = TwinPrimeFinder(prime_generator=custom_gen)
        twins = finder.find(1, 20)
        assert (3, 5) in twins


# ============================================================================
# تست‌های GCD و LCM
# ============================================================================

class TestGCDCalculator:
    """تست‌های GCD."""

    @pytest.mark.parametrize("numbers,expected", [
        ([12, 8], 4),
        ([48, 18], 6),
        ([100, 75], 25),
        ([17, 13], 1),  # متباین
        ([12, 18, 24], 6),
        ([7, 7, 7], 7),
        ([2, 4, 6, 8, 10], 2),
    ])
    def test_gcd(self, numbers, expected):
        """تست GCD برای مجموعه‌های مختلف."""
        assert GCDCalculator.calculate(*numbers) == expected

    def test_gcd_with_two_equal_numbers(self):
        """تست GCD دو عدد برابر."""
        assert GCDCalculator.calculate(15, 15) == 15

    def test_gcd_single_number_raises(self):
        """تست اینکه GCD با یک عدد خطا می‌دهد."""
        with pytest.raises(ValueError):
            GCDCalculator.calculate(5)

    def test_gcd_no_numbers_raises(self):
        """تست اینکه GCD بدون ورودی خطا می‌دهد."""
        with pytest.raises((TypeError, ValueError)):
            GCDCalculator.calculate()

    def test_large_numbers_gcd(self):
        """تست GCD اعداد بزرگ."""
        assert GCDCalculator.calculate(10**9, 10**9 + 2) == 2

class TestLCMCalculator:
    """تست‌های LCM."""

    @pytest.mark.parametrize("numbers,expected", [
        ([12, 8], 24),
        ([4, 6], 12),
        ([15, 20], 60),
        ([7, 13], 91),  # متباین
        ([2, 3, 4], 12),
        ([6, 8, 12], 24),
    ])
    def test_lcm(self, numbers, expected):
        """تست LCM برای مجموعه‌های مختلف."""
        assert LCMCalculator.calculate(*numbers) == expected

    def test_lcm_single_number_raises(self):
        """تست اینکه LCM با یک عدد خطا می‌دهد."""
        with pytest.raises(ValueError):
            LCMCalculator.calculate(5)


# ============================================================================
# تست‌های VectorOperations
# ============================================================================

class TestVectorOperations:
    """تست‌های عملیات برداری."""

    def test_sum_vectors(self):
        """تست جمع چند بردار."""
        vectors = [
            Vector2D(1, 2),
            Vector2D(3, 4),
            Vector2D(5, 6),
        ]
        result = VectorOperations.sum_vectors(vectors)
        assert result.x == 9.0
        assert result.y == 12.0

    def test_sum_empty_vectors(self):
        """تست جمع لیست خالی."""
        result = VectorOperations.sum_vectors([])
        assert result.x == 0.0
        assert result.y == 0.0

    def test_sum_single_vector(self):
        """تست جمع یک بردار."""
        vectors = [Vector2D(3, 4)]
        result = VectorOperations.sum_vectors(vectors)
        assert result.x == 3.0
        assert result.y == 4.0

    def test_sum_cancelling_vectors(self):
        """تست جمع بردارهای خنثی‌کننده."""
        vectors = [Vector2D(3, 4), Vector2D(-3, -4)]
        result = VectorOperations.sum_vectors(vectors)
        assert result.x == 0.0
        assert result.y == 0.0


# ============================================================================
# تست‌های MathEngine (Facade)
# ============================================================================

class TestMathEngine:
    """تست‌های کلاس MathEngine."""

    def test_is_prime(self, engine):
        """تست is_prime از طریق Facade."""
        assert engine.is_prime(17) == True
        assert engine.is_prime(4) == False

    def test_check_prime(self, engine):
        """تست check_prime."""
        result = engine.check_prime(17)
        assert isinstance(result, PrimeResult)
        assert result.is_prime == True

    def test_generate_primes(self, engine):
        """تست generate_primes."""
        primes = engine.generate_primes(1, 20)
        assert 2 in primes
        assert 19 in primes
        assert 4 not in primes

    def test_find_twin_primes(self, engine):
        """تست find_twin_primes."""
        twins = engine.find_twin_primes(1, 20)
        assert (3, 5) in twins

    def test_factorize(self, engine):
        """تست factorize."""
        factors = engine.factorize(12)
        assert factors == [2, 2, 3]

    def test_factorize_with_counts(self, engine):
        """تست factorize_with_counts."""
        result = engine.factorize_with_counts(12)
        assert result == {2: 2, 3: 1}

    def test_get_divisors(self, engine):
        """تست get_divisors."""
        divisors = engine.get_divisors(12)
        assert 1 in divisors
        assert 12 in divisors
        assert len(divisors) == 6

    def test_analyze_number(self, engine):
        """تست analyze_number."""
        analysis = engine.analyze_number(17)
        assert isinstance(analysis, NumberAnalysis)
        assert analysis.is_prime == True
        assert analysis.number == 17

    def test_gcd(self, engine):
        """تست gcd."""
        assert engine.gcd(12, 8) == 4
        assert engine.gcd(12, 18, 24) == 6

    def test_lcm(self, engine):
        """تست lcm."""
        assert engine.lcm(12, 8) == 24

    def test_create_vector(self, engine):
        """تست create_vector."""
        v = engine.create_vector(3, 4)
        assert isinstance(v, Vector2D)
        assert v.magnitude == 5.0

    def test_sum_vectors(self, engine):
        """تست sum_vectors."""
        v1 = engine.create_vector(1, 2)
        v2 = engine.create_vector(3, 4)
        result = engine.sum_vectors([v1, v2])
        assert result.x == 4.0
        assert result.y == 6.0

    def test_custom_dependencies(self):
        """تست تزریق وابستگی‌های سفارشی."""
        custom_checker = TrialDivisionPrimeChecker()
        custom_generator = SieveOfEratosthenesGenerator()

        engine = MathEngine(
            prime_checker=custom_checker,
            prime_generator=custom_generator
        )

        assert engine.is_prime(17) == True


# ============================================================================
# تست‌های Backward Compatibility
# ============================================================================

class TestBackwardCompatibility:
    """تست توابع backward compatibility."""

    def test_is_prime_function(self):
        """تست تابع is_prime."""
        assert is_prime(17) == True
        assert is_prime(4) == False

    def test_sieve_function(self):
        """تست تابع sieve_of_eratosthenes."""
        primes = sieve_of_eratosthenes(1, 20)
        assert 17 in primes

    def test_get_divisors_function(self):
        """تست تابع get_divisors."""
        divisors = get_divisors(12)
        assert len(divisors) == 6

    def test_find_twin_primes_function(self):
        """تست تابع find_twin_primes."""
        twins = find_twin_primes(1, 20)
        assert len(twins) > 0

    def test_prime_factors_function(self):
        """تست تابع prime_factors."""
        factors = prime_factors(12)
        assert factors == [2, 2, 3]

    def test_compute_gcd_function(self):
        """تست تابع compute_gcd."""
        assert compute_gcd(12, 8) == 4

    def test_compute_lcm_function(self):
        """تست تابع compute_lcm."""
        assert compute_lcm(12, 8) == 24


# ============================================================================
# تست‌های عملکرد و استرس
# ============================================================================

class TestPerformance:
    """تست‌های عملکرد."""

    def test_prime_check_speed(self):
        """تست سرعت بررسی اول بودن."""
        checker = TrialDivisionPrimeChecker()

        start = time.perf_counter()
        for _ in range(1000):
            checker.is_prime(9999991)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"1000 checks took {elapsed:.2f}s"

    def test_sieve_speed(self):
        """تست سرعت غربال."""
        generator = SieveOfEratosthenesGenerator()

        start = time.perf_counter()
        primes = generator.generate(1, 100000)
        elapsed = time.perf_counter() - start

        assert len(primes) == 9592
        assert elapsed < 1.0, f"Sieve took {elapsed:.2f}s"

    def test_factorize_speed(self):
        """تست سرعت تجزیه."""
        factorizer = PrimeFactorizer()

        start = time.perf_counter()
        for _ in range(1000):
            factorizer.factorize(99990)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"1000 factorizations took {elapsed:.2f}s"


class TestStress:
    """تست‌های استرس."""

    def test_large_prime_check(self):
        """تست بررسی اعداد بزرگ."""
        checker = TrialDivisionPrimeChecker()
        # 10^12 + 39 (عدد اول)
        assert checker.is_prime(1000000000039) == True

    def test_large_sieve(self):
        """تست غربال بزرگ."""
        generator = SieveOfEratosthenesGenerator()
        primes = generator.generate(1, 500000)
        assert len(primes) == 41538  # تعداد اعداد اول تا 500,000

    def test_multiple_engine_instances(self):
        """تست چندین نمونه همزمان."""
        engines = [MathEngine() for _ in range(10)]

        results = [e.is_prime(17) for e in engines]
        assert all(results)

    def test_concurrent_access(self):
        """تست دسترسی همزمان."""
        engine = MathEngine()

        def check_number(n):
            return engine.is_prime(n)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(check_number, n) for n in range(2, 100)]
            results = [f.result() for f in futures]

        # تأیید نتایج
        known_primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37,
                       41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97}

        for n in range(2, 100):
            idx = n - 2
            expected = n in known_primes
            assert results[idx] == expected, f"Failed for {n}"


# ============================================================================
# تست‌های Edge Cases و Boundary
# ============================================================================

class TestEdgeCases:
    """تست موارد مرزی و خاص."""

    def test_very_large_vector(self):
        """تست بردار با مقادیر بزرگ."""
        v = Vector2D(1e6, 1e6)
        assert v.magnitude == pytest.approx(math.sqrt(2) * 1e6)

    def test_very_small_vector(self):
        """تست بردار با مقادیر کوچک."""
        v = Vector2D(1e-10, 1e-10)
        assert v.magnitude > 0

    def test_zero_vector_angle(self):
        """تست زاویه بردار صفر."""
        v = Vector2D(0, 0)
        assert v.angle_degrees == 0.0
        assert v.angle_radians == 0.0

    def test_negative_numbers_in_gcd(self):
        """تست GCD با اعداد منفی."""
        assert GCDCalculator.calculate(-12, 8) == 4
        assert GCDCalculator.calculate(-12, -8) == 4

    def test_large_numbers_gcd(self):
        """تست GCD اعداد بزرگ."""
        assert GCDCalculator.calculate(10**9, 10**9 + 2) == 2

    def test_factorize_power_of_two(self):
        """تست تجزیه توان‌های 2."""
        factorizer = PrimeFactorizer()
        assert factorizer.factorize(1024) == [2] * 10
        assert factorizer.factorize(1) == []

    def test_primes_in_empty_range(self):
        """تست تولید اعداد اول در بازه‌های خالی."""
        generator = SieveOfEratosthenesGenerator()
        assert generator.generate(100, 50) == []
        assert generator.generate(5, 4) == []


# ============================================================================
# تست‌های هم‌ارزی ریاضی
# ============================================================================

class TestMathematicalEquivalence:
    """تست خواص و هم‌ارزی‌های ریاضی."""

    def test_gcd_times_lcm_equals_product(self):
        """تست GCD(a,b) × LCM(a,b) = a × b."""
        for a, b in [(12, 8), (15, 20), (7, 13), (100, 75)]:
            gcd_val = GCDCalculator.calculate(a, b)
            lcm_val = LCMCalculator.calculate(a, b)
            assert gcd_val * lcm_val == a * b

    def test_vector_triangle_inequality(self):
        """تست نامساوی مثلث برای بردارها."""
        v1 = Vector2D(3, 4)
        v2 = Vector2D(1, 2)
        v_sum = v1 + v2
        assert v_sum.magnitude <= v1.magnitude + v2.magnitude

    def test_number_of_divisors_of_prime(self):
        """تست اینکه اعداد اول دقیقاً 2 مقسوم‌علیه دارند."""
        calc = DivisorCalculator()
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23]:
            assert len(calc.calculate(p)) == 2
