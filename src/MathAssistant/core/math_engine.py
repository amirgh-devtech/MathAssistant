# ./src/MathAssistant/core/math_engine.py

"""
ماژول موتور ریاضی (Math Engine)

این ماژول هسته محاسباتی برنامه است و تمام منطق ریاضی را به صورت خالص
و بدون هیچ وابستگی به رابط کاربری یا فریم‌ورک‌های خارجی پیاده‌سازی می‌کند.

این ماژول طوری طراحی شده که:
- کاملاً تست‌پذیر باشد
- از اصول SOLID پیروی کند
- برای استفاده در محیط‌های مختلف (CLI, GUI, Web) مناسب باشد

Author: AmirMohammad Ghasemzadeh
Version: 1.3.8 - Production Ready
"""

import math
import logging
from abc import ABC, abstractmethod
from functools import reduce
from math import gcd as math_gcd
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Union, Iterator, Set
from numbers import Real

# تنظیم logger برای این ماژول
logger = logging.getLogger(__name__)


# ============================================================================
# تعریف انواع داده‌های سفارشی (Custom Data Types)
# ============================================================================

@dataclass(frozen=True)  # immutable - thread-safe
class Vector2D:
    """
    یک بردار دو بعدی با مختصات دکارتی.

    این کلاس immutable است و پس از ساخته شدن، مقادیر آن تغییر نمی‌کنند.
    این ویژگی آن را thread-safe می‌کند و از عوارض جانبی جلوگیری می‌کند.

    Attributes:
        x (float): مؤلفه X بردار
        y (float): مؤلفه Y بردار

    Example:
        >>> v = Vector2D(3, 4)
        >>> v.magnitude
        5.0
        >>> v.angle_degrees
        53.13010235415598
    """
    x: float = 0.0
    y: float = 0.0

    @property
    def magnitude(self) -> float:
        """اندازه (طول) بردار را محاسبه می‌کند."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    @property
    def angle_radians(self) -> float:
        """زاویه بردار را بر حسب رادیان برمی‌گرداند."""
        return math.atan2(self.y, self.x)

    @property
    def angle_degrees(self) -> float:
        """زاویه بردار را بر حسب درجه برمی‌گرداند."""
        return math.degrees(self.angle_radians)

    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        """جمع دو بردار."""
        if not isinstance(other, Vector2D):
            return NotImplemented
        return Vector2D(self.x + other.x, self.y + other.y)

    def __neg__(self) -> 'Vector2D':
        """قرینه بردار."""
        return Vector2D(-self.x, -self.y)

    def __str__(self) -> str:
        """نمایش فارسی بردار: (y, x)"""
        return f"({self.y}, {self.x})"


@dataclass(frozen=True)
class PrimeResult:
    """
    نتیجه بررسی یک عدد اول.

    Attributes:
        number: عدد بررسی شده
        is_prime: آیا عدد اول است؟
        factors: عوامل اول (برای اعداد غیر اول)
        divisor_count: تعداد مقسوم‌علیه‌ها
    """
    number: int
    is_prime: bool
    factors: Optional[Tuple[int, ...]] = None
    divisor_count: int = 0


@dataclass(frozen=True)
class NumberAnalysis:
    """
    تحلیل جامع یک عدد.

    شامل بررسی اول بودن، عوامل، مقسوم‌علیه‌ها و غیره.
    """
    number: int
    is_prime: bool
    divisors: Tuple[int, ...]
    prime_factors: Tuple[int, ...]
    divisor_count: int


# ============================================================================
# اینترفیس‌های انتزاعی (Abstract Base Classes) - اصل ISP و OCP
# ============================================================================

class PrimeChecker(ABC):
    """
    اینترفیس انتزاعی برای الگوریتم‌های بررسی اول بودن اعداد.

    با استفاده از این الگو، می‌توان الگوریتم‌های مختلف بررسی اول بودن
    را بدون تغییر در کد مصرف‌کننده، جایگزین کرد. (اصل Open/Closed)
    """

    @abstractmethod
    def is_prime(self, n: int) -> bool:
        """بررسی می‌کند که آیا عدد n اول است."""
        pass

    def check(self, n: int) -> PrimeResult:
        """بررسی کامل یک عدد و برگرداندن نتیجه جامع."""
        prime = self.is_prime(n)
        factors = None if prime else tuple(
            PrimeFactorizer().factorize(n)
        )
        divisor_count = len(DivisorCalculator().calculate(n))
        return PrimeResult(
            number=n,
            is_prime=prime,
            factors=factors,
            divisor_count=divisor_count
        )


class PrimeGenerator(ABC):
    """اینترفیس انتزاعی برای تولید اعداد اول در یک بازه."""

    @abstractmethod
    def generate(self, start: int, end: int) -> List[int]:
        """اعداد اول بین start و end را تولید می‌کند."""
        pass


# ============================================================================
# پیاده‌سازی‌های Concrete
# ============================================================================

class TrialDivisionPrimeChecker(PrimeChecker):
    """
    بررسی اول بودن با استفاده از الگوریتم تقسیم آزمایشی بهینه‌شده.

    پیچیدگی زمانی: O(√n)
    این الگوریتم برای اعداد تا سقف 10^12 کارایی خوبی دارد.
    """

    def is_prime(self, n: int) -> bool:
        """بررسی اول بودن با الگوریتم تقسیم آزمایشی بهینه."""
        if n <= 1:
            return False
        if n <= 3:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False

        # بهینه‌سازی: بررسی اعداد به فرم 6k ± 1
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6

        return True


class SieveOfEratosthenesGenerator(PrimeGenerator):
    """
    تولید اعداد اول با الگوریتم غربال اراتوستن.

    پیچیدگی زمانی: O(n log log n)
    پیچیدگی حافظه: O(n)

    برای بازه‌های بزرگ (تا سقف حدود 10^7) مناسب است.
    """

    def generate(self, start: int, end: int) -> List[int]:
        """اعداد اول بین start و end را تولید می‌کند."""
        if end < 2:
            logger.debug(f"بازه [{start}, {end}] هیچ عدد اولی ندارد (end < 2)")
            return []

        # اطمینان از اینکه start حداقل 2 است
        start = max(start, 2)

        # غربال
        sieve = [True] * (end + 1)
        sieve[0] = sieve[1] = False

        limit = int(end ** 0.5) + 1
        for i in range(2, limit):
            if sieve[i]:
                # علامت‌گذاری مضارب i به عنوان غیر اول
                start_mark = max(i * i, ((start + i - 1) // i) * i)
                sieve[start_mark:end + 1:i] = [False] * len(
                    range(start_mark, end + 1, i)
                )

        # استخراج نتایج
        return [i for i in range(start, end + 1) if sieve[i]]


class PrimeFactorizer:
    """
    تجزیه یک عدد به عوامل اول.

    از ترکیب تقسیم بر 2 و الگوریتم تقسیم آزمایشی برای اعداد فرد استفاده می‌کند.
    """

    def factorize(self, n: int) -> List[int]:
        """
        عدد n را به عوامل اولش تجزیه می‌کند.

        Returns:
            لیست عوامل اول (با تکرار)
        """
        if n <= 1:
            return []

        factors = []

        # استخراج عوامل 2
        while n % 2 == 0:
            factors.append(2)
            n //= 2

        # استخراج عوامل فرد
        i = 3
        limit = int(math.sqrt(n)) + 1
        while i <= limit and n > 1:
            while n % i == 0:
                factors.append(i)
                n //= i
            i += 2

        # اگر n خودش یک عامل اول بزرگتر است
        if n > 2:
            factors.append(n)

        return factors

    def factorize_with_counts(self, n: int) -> Dict[int, int]:
        """تجزیه به عوامل اول با شمارش توان‌ها."""
        factors = self.factorize(n)
        return dict(sorted(
            ((factor, factors.count(factor)) for factor in set(factors)),
            key=lambda x: x[0]
        ))


class DivisorCalculator:
    """محاسبه مقسوم‌علیه‌های یک عدد."""

    def calculate(self, n: int) -> List[int]:
        """
        تمام مقسوم‌علیه‌های عدد n را به صورت مرتب شده برمی‌گرداند.

        پیچیدگی زمانی: O(√n)
        """
        if n < 1:
            return []

        divisors = set()
        limit = int(n ** 0.5) + 1

        for i in range(1, limit):
            if n % i == 0:
                divisors.add(i)
                divisors.add(n // i)

        return sorted(divisors)


class TwinPrimeFinder:
    """یافتن اعداد اول دوقلو در یک بازه."""

    def __init__(self, prime_generator: Optional[PrimeGenerator] = None):
        """
        Args:
            prime_generator: الگوریتم تولید اعداد اول.
                           اگر None باشد از SieveOfEratosthenes استفاده می‌شود.
        """
        self._prime_generator = prime_generator or SieveOfEratosthenesGenerator()

    def find(self, start: int, end: int) -> List[Tuple[int, int]]:
        """
        جفت‌های اعداد اول دوقلو را در بازه [start, end] پیدا می‌کند.

        اعداد اول دوقلو اعداد اولی هستند که اختلافشان دقیقاً 2 است.
        مثال: (3, 5), (11, 13)
        """
        primes = self._prime_generator.generate(start, end)

        if len(primes) < 2:
            return []

        twins = []
        for i in range(len(primes) - 1):
            if primes[i + 1] - primes[i] == 2:
                twins.append((primes[i], primes[i + 1]))

        return twins


# ============================================================================
# کلاس‌های خدماتی (Service Classes)
# ============================================================================

class GCDCalculator:
    """
    محاسبه بزرگترین مقسوم‌علیه مشترک (GCD).

    از الگوریتم اقلیدسی استفاده می‌کند و قابلیت محاسبه برای چند عدد را دارد.
    """

    @staticmethod
    def calculate(*numbers: int) -> int:
        """
        بزرگترین مقسوم‌علیه مشترک اعداد را محاسبه می‌کند.

        Args:
            *numbers: اعداد ورودی (حداقل 2 عدد)

        Returns:
            GCD اعداد
        """
        if len(numbers) < 2:
            raise ValueError("حداقل دو عدد برای محاسبه GCD لازم است")

        return reduce(math_gcd, numbers)


class LCMCalculator:
    """
    محاسبه کوچکترین مضرب مشترک (LCM).
    """

    @staticmethod
    def calculate(*numbers: int) -> int:
        """
        کوچکترین مضرب مشترک اعداد را محاسبه می‌کند.

        Args:
            *numbers: اعداد ورودی (حداقل 2 عدد)

        Returns:
            LCM اعداد
        """
        if len(numbers) < 2:
            raise ValueError("حداقل دو عدد برای محاسبه LCM لازم است")

        def _lcm(a: int, b: int) -> int:
            return a * b // math_gcd(a, b)

        return reduce(_lcm, numbers)


class VectorOperations:
    """عملیات روی بردارها (استاتیک)."""

    @staticmethod
    def sum_vectors(vectors: List[Vector2D]) -> Vector2D:
        """
        محاسبه بردار برآیند از مجموع چند بردار.

        Args:
            vectors: لیست بردارهای ورودی

        Returns:
            بردار برآیند
        """
        if not vectors:
            return Vector2D(0, 0)

        total_x = sum(v.x for v in vectors)
        total_y = sum(v.y for v in vectors)
        return Vector2D(total_x, total_y)


# ============================================================================
# کلاس Facade - ارائه یک API ساده و یکپارچه
# ============================================================================

class MathEngine:
    """
    Facade برای کل موتور ریاضی.

    این کلاس یک API ساده و یکپارچه برای تمام عملیات ریاضی فراهم می‌کند
    و پیچیدگی‌های داخلی را مخفی می‌کند. (الگوی Facade از Design Patterns)

    Usage:
        engine = MathEngine()

        # بررسی اعداد اول
        result = engine.check_prime(17)

        # محاسبات برداری
        v1 = Vector2D(3, 4)
        v2 = Vector2D(1, 2)
        sum_v = engine.sum_vectors([v1, v2])

        # تولید اعداد اول
        primes = engine.generate_primes(1, 100)
    """

    def __init__(
        self,
        prime_checker: Optional[PrimeChecker] = None,
        prime_generator: Optional[PrimeGenerator] = None
    ):
        """
        Args:
            prime_checker: الگوریتم بررسی اول بودن
            prime_generator: الگوریتم تولید اعداد اول
        """
        self._prime_checker = prime_checker or TrialDivisionPrimeChecker()
        self._prime_generator = prime_generator or SieveOfEratosthenesGenerator()
        self._factorizer = PrimeFactorizer()
        self._divisor_calc = DivisorCalculator()
        self._twin_finder = TwinPrimeFinder(self._prime_generator)
        self._gcd_calc = GCDCalculator()
        self._lcm_calc = LCMCalculator()
        self._vector_ops = VectorOperations()

    # ----- عملیات اعداد اول -----

    def check_prime(self, n: int) -> PrimeResult:
        """بررسی کامل یک عدد (اول بودن، عوامل، مقسوم‌علیه‌ها)."""
        logger.debug(f"بررسی عدد {n}")
        return self._prime_checker.check(n)

    def is_prime(self, n: int) -> bool:
        """بررسی سریع اول بودن یک عدد."""
        return self._prime_checker.is_prime(n)

    def generate_primes(self, start: int, end: int) -> List[int]:
        """تولید اعداد اول در بازه [start, end]."""
        logger.debug(f"تولید اعداد اول در بازه [{start}, {end}]")
        return self._prime_generator.generate(start, end)

    def find_twin_primes(self, start: int, end: int) -> List[Tuple[int, int]]:
        """یافتن اعداد اول دوقلو در بازه [start, end]."""
        logger.debug(f"یافتن اعداد اول دوقلو در بازه [{start}, {end}]")
        return self._twin_finder.find(start, end)

    def factorize(self, n: int) -> List[int]:
        """تجزیه عدد به عوامل اول."""
        return self._factorizer.factorize(n)

    def factorize_with_counts(self, n: int) -> Dict[int, int]:
        """تجزیه عدد به عوامل اول با شمارش."""
        return self._factorizer.factorize_with_counts(n)

    def get_divisors(self, n: int) -> List[int]:
        """محاسبه تمام مقسوم‌علیه‌های یک عدد."""
        return self._divisor_calc.calculate(n)

    def analyze_number(self, n: int) -> NumberAnalysis:
        """تحلیل جامع یک عدد."""
        logger.debug(f"تحلیل جامع عدد {n}")
        return NumberAnalysis(
            number=n,
            is_prime=self.is_prime(n),
            divisors=tuple(self.get_divisors(n)),
            prime_factors=tuple(self.factorize(n)),
            divisor_count=len(self.get_divisors(n))
        )

    # ----- عملیات GCD و LCM -----

    def gcd(self, *numbers: int) -> int:
        """محاسبه GCD چند عدد."""
        return self._gcd_calc.calculate(*numbers)

    def lcm(self, *numbers: int) -> int:
        """محاسبه LCM چند عدد."""
        return self._lcm_calc.calculate(*numbers)

    # ----- عملیات برداری -----

    def create_vector(self, x: float, y: float) -> Vector2D:
        """ایجاد یک بردار جدید."""
        return Vector2D(x, y)

    def sum_vectors(self, vectors: List[Vector2D]) -> Vector2D:
        """محاسبه بردار برآیند."""
        return self._vector_ops.sum_vectors(vectors)


# ============================================================================
# توابع کمکی برای backward compatibility (اختیاری)
# ============================================================================

# یک نمونه سراسری از MathEngine برای استفاده راحت‌تر
_engine = MathEngine()

# توابع میانبر برای حفظ سازگاری با کد قدیمی
# (می‌توان در فاز بعدی حذف کرد)

def is_prime(n: int) -> bool:
    """میانبر backward-compatible برای بررسی اول بودن."""
    return _engine.is_prime(n)

def sieve_of_eratosthenes(start: int, end: int) -> List[int]:
    """میانبر backward-compatible برای غربال اراتوستن."""
    return _engine.generate_primes(start, end)

def get_divisors(n: int) -> List[int]:
    """میانبر backward-compatible برای مقسوم‌علیه‌ها."""
    return _engine.get_divisors(n)

def find_twin_primes(start: int, end: int) -> List[Tuple[int, int]]:
    """میانبر backward-compatible برای اعداد اول دوقلو."""
    return _engine.find_twin_primes(start, end)

def prime_factors(n: int) -> List[int]:
    """میانبر backward-compatible برای عوامل اول."""
    return _engine.factorize(n)

def compute_gcd(*numbers: int) -> int:
    """میانبر backward-compatible برای GCD."""
    return _engine.gcd(*numbers)

def compute_lcm(*numbers: int) -> int:
    """میانبر backward-compatible برای LCM."""
    return _engine.lcm(*numbers)
