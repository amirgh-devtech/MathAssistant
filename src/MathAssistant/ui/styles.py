"""
ماژول مدیریت تم و استایل پیشرفته MathAssistant

این ماژول مسئولیت مدیریت تمام استایل‌ها، فونت‌ها، رنگ‌ها،
و پوسته‌های برنامه را بر عهده دارد.

فقط از ویژگی‌های واقعاً پشتیبانی‌شده Qt استفاده می‌کند.
همه افکت‌ها (Glass, Shadow, Neumorphism, Gradient) با روش‌های native Qt پیاده‌سازی شده‌اند.

Features:
- تشخیص خودکار نسخه ویندوز و انتخاب Qt مناسب
- ۸ تم رنگی: Light, Dark, High Contrast, Ocean, Forest, Sunset, Midnight, Aurora
- Glassmorphism با QGraphicsEffect
- Shadow System با QGraphicsDropShadowEffect
- Neumorphism با ترکیب gradient و shadow
- Gradient Generator (Linear, Radial, Conic)
- انیمیشن‌ها با QPropertyAnimation و QTimer
- فونت‌های فارسی و انگلیسی با fallback هوشمند
- استایل‌های آماده برای ۳۰+ نوع ویجت
- پشتیبانی از Responsive Design با breakpoint
- رعایت استانداردهای WCAG 2.1 Accessibility
- Hot-reload تم در زمان اجرا
- سیستم Grid و Spacing استاندارد
- Border Radius System
- Export/Import تنظیمات تم

Design Patterns:
- Singleton: ThemeManager, QtAdapter
- Factory: PaletteFactory
- Builder: StyleBuilder
- Observer: ThemeChangeNotifier
- Strategy: ShadowStrategy, GlassStrategy

Architecture: کاملاً مجزا از منطق و UI - فقط استایل

Author: AmirMohammad Ghasemzadeh
Version: 4.0.0 - Production Ready
"""

import re
import sys
import os
import platform
import logging
import math
import json
import threading
from enum import Enum, auto
from typing import Dict, Optional, Tuple, Union, Any, List, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for performance
HEX_COLOR_PATTERN = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')
RGBA_PATTERN = re.compile(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$')
GRADIENT_PATTERN = re.compile(r'^q(lineargradient|radialgradient|conicalgradient)\(')

# ============================================================================
# Type Aliases
# ============================================================================

HexColor = str
RGBATuple = Tuple[int, int, int, float]
StyleSheet = str
FontFamily = str
Pixels = int
ColorStop = Tuple[float, str]  # (position 0.0-1.0, color)


# ============================================================================
# Base Enums
# ============================================================================

class QtVersion(Enum):
    """نسخه‌های Qt پشتیبانی شده."""
    PYQT5 = auto()
    PYQT6 = auto()
    PYSIDE6 = auto()


class WindowsVersion(Enum):
    """نسخه‌های سیستم عامل."""
    WIN_7 = auto()
    WIN_8 = auto()
    WIN_8_1 = auto()
    WIN_10 = auto()
    WIN_11 = auto()
    LINUX = auto()
    MACOS = auto()
    UNKNOWN = auto()


class ThemeMode(Enum):
    """۸ تم رنگی برنامه."""
    LIGHT = auto()          # روشن کلاسیک
    DARK = auto()           # تاریک کلاسیک
    HIGH_CONTRAST = auto()  # کنتراست بالا (Accessibility)
    OCEAN = auto()          # اقیانوس (آبی-فیروزه‌ای)
    FOREST = auto()         # جنگل (سبز-قهوه‌ای)
    SUNSET = auto()         # غروب (نارنجی-قرمز-بنفش)
    MIDNIGHT = auto()       # نیمه‌شب (مشکی-بنفش تیره)
    AURORA = auto()         # شفق قطبی (سبز-بنفش-آبی روشن)


class GlassLevel(Enum):
    """سطوح شفافیت Glassmorphism - با QGraphicsOpacityEffect."""
    NONE = 0       # بدون شفافیت (opacity: 1.0)
    LIGHT = 1      # شفافیت کم (opacity: 0.95)
    MEDIUM = 2     # شفافیت متوسط (opacity: 0.90)
    HEAVY = 3      # شفافیت زیاد (opacity: 0.80)
    EXTREME = 4    # شفافیت فوق‌العاده (opacity: 0.70)


class ShadowElevation(Enum):
    """سطوح ارتفاع سایه - با QGraphicsDropShadowEffect."""
    NONE = 0        # بدون سایه
    LOW = 1         # کارت‌های معمولی (blur: 4, offset: 2)
    MEDIUM = 2      # دکمه‌های شناور (blur: 8, offset: 4)
    HIGH = 3        # منوها، دیالوگ‌ها (blur: 16, offset: 6)
    EXTREME = 4     # مودال‌ها (blur: 24, offset: 10)


class FontSize(Enum):
    """سایزهای استاندارد فونت (بر اساس پیکسل)."""
    CAPTION = 8
    TINY = 10
    SMALL = 12
    NORMAL = 14
    MEDIUM = 16
    LARGE = 20
    XL = 24
    XXL = 28
    TITLE = 32
    HERO = 40
    DISPLAY = 48
    GIANT = 56
    MASSIVE = 64


class Spacing(Enum):
    """فاصله‌های استاندارد (بر اساس 4px grid system)."""
    NONE = 0
    MICRO = 2
    TINY = 4
    SMALL = 8
    NORMAL = 12
    MEDIUM = 16
    LARGE = 24
    XL = 32
    XXL = 48
    HUGE = 64
    MASSIVE = 96
    GIANT = 128


class BorderRadius(Enum):
    """شعاع گوشه‌ها."""
    NONE = 0
    TINY = 2
    SMALL = 4
    NORMAL = 8
    MEDIUM = 12
    LARGE = 16
    XL = 24
    XXL = 32
    ROUND = 9999


class AnimationDuration(Enum):
    """مدت زمان انیمیشن‌ها (میلی‌ثانیه)."""
    INSTANT = 0
    FAST = 100
    NORMAL = 200
    SLOW = 300
    VERY_SLOW = 500
    GLACIAL = 1000
    ETERNAL = 2000


class Breakpoint(Enum):
    """نقاط شکست برای Responsive Design."""
    MOBILE_S = 320
    MOBILE_M = 375
    MOBILE_L = 425
    TABLET = 768
    LAPTOP = 1024
    LAPTOP_L = 1440
    DESKTOP = 1920
    DESKTOP_4K = 2560


class GradientType(Enum):
    """انواع گرادیانت."""
    LINEAR = auto()
    RADIAL = auto()
    CONIC = auto()
    SWEEP = auto()


class IconSize(Enum):
    """سایز آیکون‌ها."""
    TINY = 12
    SMALL = 16
    NORMAL = 24
    MEDIUM = 32
    LARGE = 48
    XL = 64
    XXL = 96


# ============================================================================
# Utility Functions
# ============================================================================

class LRUCache:
    """پیاده‌سازی LRU Cache با محدودیت سایز و پشتیبانی کامل از dict interface."""

    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Optional[str]:
        """دریافت مقدار از کش. None اگر وجود نداشته باشد."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: str):
        """ذخیره مقدار در کش با سیاست LRU."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if self._max_size <= 0:
                return
            if len(self._cache) >= self._max_size:
                if len(self._cache) > 0:
                    self._cache.popitem(last=False)
        self._cache[key] = value

    def __getitem__(self, key: str) -> str:
        """دسترسی با براکت. KeyError اگر وجود نداشته باشد."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: str):
        """ذخیره با براکت."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """بررسی وجود کلید با `in` operator."""
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self):
        """پاک کردن کامل کش."""
        self._cache.clear()

    def remove(self, key: str):
        """حذف یک کلید خاص."""
        if key in self._cache:
            del self._cache[key]

    def keys(self):
        """لیست کلیدهای موجود."""
        return list(self._cache.keys())

    def values(self):
        """لیست مقادیر موجود."""
        return list(self._cache.values())

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def max_size(self) -> int:
        return self._max_size

def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """تبدیل رنگ hex به rgba برای Qt."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {round(alpha * 255)})"  # round به‌جای int
    if len(hex_color) == 8:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = int(hex_color[6:8], 16) / 255
        return f"rgba({r}, {g}, {b}, {round(a * alpha * 255)})"  # round
    return hex_color


def hex_to_qcolor(hex_color: str, alpha: int = 255):
    """تبدیل hex به QColor (در زمان اجرا با QtAdapter)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 0
    g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 0
    b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 0
    return (r, g, b, alpha)


def lighten_color(hex_color: str, amount: float = 0.1) -> str:
    """روشن‌تر کردن یک رنگ hex."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    if len(hex_color) < 6:
        return f"#{hex_color}"
    r = min(255, int(int(hex_color[0:2], 16) * (1 + amount)))
    g = min(255, int(int(hex_color[2:4], 16) * (1 + amount)))
    b = min(255, int(int(hex_color[4:6], 16) * (1 + amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color: str, amount: float = 0.1) -> str:
    """تیره‌تر کردن یک رنگ hex."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    if len(hex_color) < 6:
        return f"#{hex_color}"
    r = max(0, int(int(hex_color[0:2], 16) * (1 - amount)))
    g = max(0, int(int(hex_color[2:4], 16) * (1 - amount)))
    b = max(0, int(int(hex_color[4:6], 16) * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def mix_colors(color1: str, color2: str, ratio: float = 0.5) -> str:
    """ترکیب دو رنگ با نسبت مشخص."""
    c1 = color1.lstrip('#')
    c2 = color2.lstrip('#')
    if len(c1) == 3: c1 = ''.join(c * 2 for c in c1)
    if len(c2) == 3: c2 = ''.join(c * 2 for c in c2)
    if len(c1) < 6 or len(c2) < 6:
        return color1
    r = round(int(c1[0:2], 16) * (1 - ratio) + int(c2[0:2], 16) * ratio)
    g = round(int(c1[2:4], 16) * (1 - ratio) + int(c2[2:4], 16) * ratio)
    b = round(int(c1[4:6], 16) * (1 - ratio) + int(c2[4:6], 16) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """محدود کردن مقدار بین min و max."""
    return max(min_val, min(max_val, value))


def luminosity(hex_color: str) -> float:
    """محاسبه روشنایی نسبی یک رنگ (برای accessibility)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    if len(hex_color) < 6:
        return 0.5
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r_srgb = r / 255
    g_srgb = g / 255
    b_srgb = b / 255
    r_lin = r_srgb / 12.92 if r_srgb <= 0.03928 else ((r_srgb + 0.055) / 1.055) ** 2.4
    g_lin = g_srgb / 12.92 if g_srgb <= 0.03928 else ((g_srgb + 0.055) / 1.055) ** 2.4
    b_lin = b_srgb / 12.92 if b_srgb <= 0.03928 else ((b_srgb + 0.055) / 1.055) ** 2.4
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1: str, color2: str) -> float:
    """محاسبه نسبت کنتراست بین دو رنگ (WCAG 2.1)."""
    l1 = luminosity(color1)
    l2 = luminosity(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_accessible(text_color: str, bg_color: str, level: str = "AA") -> bool:
    """بررسی accessibility بر اساس WCAG."""
    ratio = contrast_ratio(text_color, bg_color)
    if level == "AAA":
        return ratio >= 7.0 if ratio >= 4.5 else False
    elif level == "AA_LARGE":
        return ratio >= 3.0
    return ratio >= 4.5


# ============================================================================
# Data Classes
# ============================================================================

@dataclass(frozen=True)
class ColorPalette:
    """
    پالت رنگی جامع برای یک تم.

    شامل ۴۰+ رنگ مختلف برای تمام حالت‌های UI.
    همه رنگ‌ها با فرمت hex ذخیره می‌شوند.
    """
    # === Primary Colors ===
    primary: str
    primary_light: str
    primary_dark: str

    # === Secondary Colors ===
    secondary: str
    secondary_light: str
    secondary_dark: str

    # === Tertiary Colors ===
    tertiary: str = ""
    tertiary_light: str = ""
    tertiary_dark: str = ""

    # === Accent Colors ===
    accent: str = ""
    accent_light: str = ""
    accent_dark: str = ""

    # === Status Colors ===
    success: str = "#10B981"
    success_light: str = "#6EE7B7"
    success_dark: str = "#059669"
    warning: str = "#F59E0B"
    warning_light: str = "#FCD34D"
    warning_dark: str = "#D97706"
    error: str = "#EF4444"
    error_light: str = "#FCA5A5"
    error_dark: str = "#DC2626"
    info: str = "#3B82F6"
    info_light: str = "#93C5FD"
    info_dark: str = "#1D4ED8"

    # === Neutral Colors ===
    neutral_50: str = "#F8FAFC"
    neutral_100: str = "#F1F5F9"
    neutral_200: str = "#E2E8F0"
    neutral_300: str = "#CBD5E1"
    neutral_400: str = "#94A3B8"
    neutral_500: str = "#64748B"
    neutral_600: str = "#475569"
    neutral_700: str = "#334155"
    neutral_800: str = "#1E293B"
    neutral_900: str = "#0F172A"

    # === Background Colors ===
    background: str = "#F8FAFC"
    background_alt: str = "#F1F5F9"
    background_elevated: str = "#FFFFFF"
    surface: str = "#FFFFFF"
    surface_hover: str = "#E2E8F0"
    surface_pressed: str = "#CBD5E1"
    surface_selected: str = "#DBEAFE"
    overlay: str = "rgba(0, 0, 0, 0.5)"
    overlay_light: str = "rgba(0, 0, 0, 0.3)"
    overlay_dark: str = "rgba(0, 0, 0, 0.7)"

    # === Text Colors ===
    text_primary: str = "#1E293B"
    text_secondary: str = "#64748B"
    text_tertiary: str = "#94A3B8"
    text_disabled: str = "#CBD5E1"
    text_on_primary: str = "#FFFFFF"
    text_on_primary_secondary: str = "#E2E8F0"
    text_on_dark: str = "#F1F5F9"
    text_on_dark_secondary: str = "#94A3B8"
    text_link: str = "#2563EB"
    text_link_hover: str = "#1D4ED8"

    # === Border Colors ===
    border: str = "#CBD5E1"
    border_light: str = "#E2E8F0"
    border_focus: str = "#2563EB"
    border_hover: str = "#94A3B8"
    border_error: str = "#EF4444"
    border_success: str = "#10B981"

    # === Gradient Colors ===
    gradient_start: str = ""
    gradient_mid: str = ""
    gradient_end: str = ""
    gradient_accent: str = ""
    gradient_secondary_start: str = ""
    gradient_secondary_end: str = ""

    # === Special Effect Colors ===
    glass_overlay: str = "rgba(255, 255, 255, 0.15)"
    glass_border: str = "rgba(255, 255, 255, 0.25)"
    shimmer: str = "#E2E8F0"
    shimmer_dark: str = "#334155"
    ripple_light: str = "rgba(255, 255, 255, 0.4)"
    ripple_dark: str = "rgba(255, 255, 255, 0.1)"

    # === Data Visualization Colors ===
    chart_1: str = "#2563EB"
    chart_2: str = "#10B981"
    chart_3: str = "#F59E0B"
    chart_4: str = "#EF4444"
    chart_5: str = "#8B5CF6"
    chart_6: str = "#EC4899"
    chart_7: str = "#06B6D4"
    chart_8: str = "#F97316"

    # === Alpha-derived colors (auto-calculated) ===
    primary_alpha_10: str = field(init=False)
    primary_alpha_20: str = field(init=False)
    primary_alpha_30: str = field(init=False)

    def __post_init__(self):
        """اعتبارسنجی رنگ‌ها و محاسبه alpha variants."""
        for field_name in self.__dataclass_fields__:
            if field_name.startswith('primary_alpha_'):
                continue

            value = getattr(self, field_name)
            if value is None or value == "":
                continue

            # Check gradient patterns
            if GRADIENT_PATTERN.match(value):
                continue

            # Check rgba
            if value.startswith('rgba'):
                if not RGBA_PATTERN.match(value):
                    logger.warning(f"Invalid rgba: {field_name}={value}")
                continue

            # Check hex
            if value.startswith('#'):
                if not HEX_COLOR_PATTERN.match(value):
                    logger.warning(f"Invalid hex: {field_name}={value}")
                continue

            # Unknown format
            logger.warning(f"Unexpected color format: {field_name}={value}")

        # محاسبه alpha variants
        object.__setattr__(self, 'primary_alpha_10', hex_to_rgba(self.primary, 0.1))
        object.__setattr__(self, 'primary_alpha_20', hex_to_rgba(self.primary, 0.2))
        object.__setattr__(self, 'primary_alpha_30', hex_to_rgba(self.primary, 0.3))

@dataclass(frozen=True)
class FontConfig:
    """تنظیمات جامع فونت با fallback."""
    # Persian/Arabic fonts
    family_fa: str = "B Nazanin"
    family_fa_fallback: List[str] = field(default_factory=lambda: ["Vazir", "Iran Sans", "Tahoma", "Arial"])

    # English fonts
    family_en: str = "Segoe UI"
    family_en_fallback: List[str] = field(default_factory=lambda: ["Helvetica Neue", "Arial", "sans-serif"])

    # Monospace fonts
    family_mono: str = "Cascadia Code"
    family_mono_fallback: List[str] = field(default_factory=lambda: ["Consolas", "Courier New", "monospace"])

    # Math fonts
    family_math: str = "Times New Roman"
    family_math_fallback: List[str] = field(default_factory=lambda: ["Cambria Math", "Georgia", "serif"])

    # Icon font
    family_icon: str = "Segoe Fluent Icons"

    # Base sizes (px)
    size_caption: int = 8
    size_tiny: int = 10
    size_small: int = 12
    size_normal: int = 14
    size_medium: int = 16
    size_large: int = 20
    size_xl: int = 24
    size_xxl: int = 28
    size_title: int = 32
    size_hero: int = 40
    size_display: int = 48
    size_giant: int = 56
    size_massive: int = 64

    # Line heights (multiplier)
    line_height_tight: float = 1.2
    line_height_normal: float = 1.5
    line_height_loose: float = 1.8
    line_height_paragraph: float = 1.6

    # Letter spacing (px)
    letter_spacing_tight: float = -0.5
    letter_spacing_normal: float = 0.0
    letter_spacing_wide: float = 0.5
    letter_spacing_title: float = 1.0


@dataclass
class ShadowParams:
    """پارامترهای سایه برای QGraphicsDropShadowEffect."""
    offset_x: float = 0.0
    offset_y: float = 2.0
    blur_radius: float = 4.0
    color: Tuple[int, int, int, int] = (0, 0, 0, 60)


@dataclass
class GlassParams:
    """پارامترهای Glass Effect."""
    opacity: float = 0.90
    bg_color: Tuple[int, int, int, int] = (255, 255, 255, 230)
    border_color: Tuple[int, int, int, int] = (255, 255, 255, 60)
    border_width: int = 1


@dataclass
class GradientStop:
    """یک توقف در گرادیانت."""
    position: float  # 0.0 تا 1.0
    color: str       # hex color


@dataclass
class GradientConfig:
    """تنظیمات گرادیانت."""
    stops: List[GradientStop] = field(default_factory=list)
    gradient_type: GradientType = GradientType.LINEAR
    start_point: Tuple[float, float] = (0.0, 0.0)
    end_point: Tuple[float, float] = (1.0, 1.0)
    center_point: Tuple[float, float] = (0.5, 0.5)
    radius: float = 0.5
    angle: float = 0.0


# ============================================================================
# Shadow System (Native Qt)
# ============================================================================

class ShadowSystem:
    """
    سیستم تولید سایه با QGraphicsDropShadowEffect.

    هر ویجت می‌تواند یک shadow effect دریافت کند.
    سایه‌ها با QGraphicsDropShadowEffect پیاده‌سازی می‌شوند
    که در Qt به صورت native پشتیبانی می‌شود.
    """

    # نگاشت elevation به پارامترهای سایه
    ELEVATION_MAP = {
        ShadowElevation.NONE: ShadowParams(0, 0, 0, (0, 0, 0, 0)),
        ShadowElevation.LOW: ShadowParams(0, 1, 3, (0, 0, 0, 30)),
        ShadowElevation.MEDIUM: ShadowParams(0, 4, 8, (0, 0, 0, 50)),
        ShadowElevation.HIGH: ShadowParams(0, 8, 24, (0, 0, 0, 80)),
        ShadowElevation.EXTREME: ShadowParams(0, 16, 48, (0, 0, 0, 120)),
    }

    # نگاشت elevation برای تم تاریک
    ELEVATION_MAP_DARK = {
        ShadowElevation.NONE: ShadowParams(0, 0, 0, (0, 0, 0, 0)),
        ShadowElevation.LOW: ShadowParams(0, 1, 3, (255, 255, 255, 15)),
        ShadowElevation.MEDIUM: ShadowParams(0, 4, 8, (255, 255, 255, 25)),
        ShadowElevation.HIGH: ShadowParams(0, 8, 24, (255, 255, 255, 40)),
        ShadowElevation.EXTREME: ShadowParams(0, 16, 48, (255, 255, 255, 60)),
    }

    @staticmethod
    def get_shadow_params(
        elevation: ShadowElevation,
        is_dark: bool = False
    ) -> ShadowParams:
        """
        دریافت پارامترهای سایه بر اساس elevation و تم.

        Args:
            elevation: سطح ارتفاع
            is_dark: آیا تم تاریک است؟

        Returns:
            ShadowParams برای استفاده در QGraphicsDropShadowEffect
        """
        if is_dark:
            return ShadowSystem.ELEVATION_MAP_DARK.get(
                elevation, ShadowSystem.ELEVATION_MAP_DARK[ShadowElevation.NONE]
            )
        return ShadowSystem.ELEVATION_MAP.get(
            elevation, ShadowSystem.ELEVATION_MAP[ShadowElevation.NONE]
        )

    @staticmethod
    def create_shadow_effect(
        elevation: ShadowElevation,
        is_dark: bool = False,
        adapter=None
    ) -> Any:
        """
        ایجاد یک QGraphicsDropShadowEffect.

        Args:
            elevation: سطح ارتفاع
            is_dark: تم تاریک؟
            adapter: QtAdapter برای دسترسی به کلاس‌های Qt

        Returns:
            QGraphicsDropShadowEffect یا None
        """
        if elevation == ShadowElevation.NONE:
            return None

        params = ShadowSystem.get_shadow_params(elevation, is_dark)

        try:
            if adapter and hasattr(adapter, '_QtWidgets'):
                effect = adapter._QtWidgets.QGraphicsDropShadowEffect()
                effect.setOffset(params.offset_x, params.offset_y)
                effect.setBlurRadius(params.blur_radius)
                r, g, b, a = params.color
                effect.setColor(adapter.QColor(r, g, b, a))
                return effect
        except Exception as e:
            logger.warning(f"Could not create shadow effect: {e}")

        return None

    @staticmethod
    def apply_shadow(
        widget: Any,
        elevation: ShadowElevation,
        is_dark: bool = False,
        adapter=None
    ):
        """
        اعمال سایه به یک ویجت.

        Args:
            widget: ویجت Qt
            elevation: سطح ارتفاع
            is_dark: تم تاریک؟
            adapter: QtAdapter
        """
        effect = ShadowSystem.create_shadow_effect(elevation, is_dark, adapter)
        if effect and widget:
            widget.setGraphicsEffect(effect)

    @staticmethod
    def get_shadow_style_sheet(
        elevation: ShadowElevation,
        is_dark: bool = False
    ) -> str:
        """
        تولید استایل تقریبی سایه برای StyleSheet.
        توجه: Qt StyleSheet از box-shadow پشتیبانی کامل نمی‌کند.
        این متد یک تقریب با border و padding ارائه می‌دهد.
        برای سایه واقعی، از apply_shadow استفاده کنید.
        """
        if elevation == ShadowElevation.NONE:
            return ""

        params = ShadowSystem.get_shadow_params(elevation, is_dark)
        r, g, b, a = params.color
        blur = params.blur_radius

        # تقریب سایه با border تیره‌تر
        return f"""
            border-bottom: {max(1, int(blur/4))}px solid rgba({r}, {g}, {b}, {min(255, a*2)});
            border-right: {max(1, int(blur/4))}px solid rgba({r}, {g}, {b}, {min(255, int(a*1.5))});
        """


# ============================================================================
# Glassmorphism System (Native Qt)
# ============================================================================

class GlassmorphismSystem:
    """
    سیستم تولید افکت شیشه‌ای با QGraphicsOpacityEffect.

    Glassmorphism با ترکیبی از:
    1. QGraphicsOpacityEffect برای شفافیت
    2. پس‌زمینه نیمه‌شفاف
    3. حاشیه روشن
    پیاده‌سازی می‌شود.
    """

    # نگاشت level به opacity
    OPACITY_MAP = {
        GlassLevel.NONE: 1.0,
        GlassLevel.LIGHT: 0.95,
        GlassLevel.MEDIUM: 0.88,
        GlassLevel.HEAVY: 0.78,
        GlassLevel.EXTREME: 0.65,
    }

    # نگاشت level به alpha پس‌زمینه
    BG_ALPHA_MAP = {
        GlassLevel.NONE: 255,
        GlassLevel.LIGHT: 240,
        GlassLevel.MEDIUM: 220,
        GlassLevel.HEAVY: 195,
        GlassLevel.EXTREME: 165,
    }

    @staticmethod
    def get_glass_params(
        level: GlassLevel,
        base_color: Tuple[int, int, int, int] = (255, 255, 255, 220)
    ) -> GlassParams:
        """
        دریافت پارامترهای glass effect.

        Args:
            level: سطح شفافیت
            base_color: رنگ پایه (R, G, B, A)

        Returns:
            GlassParams
        """
        opacity = GlassmorphismSystem.OPACITY_MAP.get(level, 1.0)
        bg_alpha = GlassmorphismSystem.BG_ALPHA_MAP.get(level, 255)
        r, g, b, _ = base_color

        return GlassParams(
            opacity=opacity,
            bg_color=(r, g, b, bg_alpha),
            border_color=(r, g, b, min(255, bg_alpha + 35)),
            border_width=1 if level != GlassLevel.NONE else 0,
        )

    @staticmethod
    def create_glass_effect(
        level: GlassLevel,
        base_color: Tuple[int, int, int, int] = (255, 255, 255, 220),
        adapter=None
    ) -> Any:
        """
        ایجاد QGraphicsOpacityEffect برای glass effect.

        Args:
            level: سطح شفافیت
            base_color: رنگ پایه
            adapter: QtAdapter

        Returns:
            QGraphicsOpacityEffect یا None
        """
        if level == GlassLevel.NONE:
            return None

        params = GlassmorphismSystem.get_glass_params(level, base_color)

        try:
            if adapter and hasattr(adapter, '_QtWidgets'):
                effect = adapter._QtWidgets.QGraphicsOpacityEffect()
                effect.setOpacity(params.opacity)
                return effect
        except Exception as e:
            logger.warning(f"Could not create glass effect: {e}")

        return None

    @staticmethod
    def apply_glass(
        widget: Any,
        level: GlassLevel,
        base_color: Tuple[int, int, int, int] = (255, 255, 255, 220),
        adapter=None
    ):
        """
        اعمال glass effect به یک ویجت.

        Args:
            widget: ویجت Qt
            level: سطح شفافیت
            base_color: رنگ پایه
            adapter: QtAdapter
        """
        effect = GlassmorphismSystem.create_glass_effect(level, base_color, adapter)
        if effect and widget:
            widget.setGraphicsEffect(effect)

    @staticmethod
    def get_glass_style_sheet(
        level: GlassLevel,
        base_color: Tuple[int, int, int, int] = (255, 255, 255, 220),
        border_radius: int = 12
    ) -> str:
        """
        تولید استایل StyleSheet برای glass effect.

        این متد با رنگ‌های نیمه‌شفاف، افکت شیشه‌ای را
        در StyleSheet شبیه‌سازی می‌کند.
        """
        if level == GlassLevel.NONE:
            return ""

        params = GlassmorphismSystem.get_glass_params(level, base_color)
        r, g, b, bg_a = params.bg_color
        br, bg_b, bb, border_a = params.border_color

        return f"""
            background-color: rgba({r}, {g}, {b}, {bg_a});
            border: {params.border_width}px solid rgba({br}, {bg_b}, {bb}, {border_a});
            border-radius: {border_radius}px;
        """


# ============================================================================
# Gradient Generator
# ============================================================================

class GradientGenerator:
    """
    تولید گرادیانت‌های پیشرفته با QLinearGradient و QRadialGradient.

    همه گرادیانت‌ها با کلاس‌های native Qt ساخته می‌شوند.
    """

    @staticmethod
    def linear(
        stops: List[ColorStop],
        start_point: Tuple[float, float] = (0.0, 0.0),
        end_point: Tuple[float, float] = (1.0, 1.0),
        adapter=None
    ) -> Any:
        """
        ایجاد QLinearGradient.

        Args:
            stops: لیست توقف‌های رنگی [(position, color), ...]
            start_point: نقطه شروع (x, y) به صورت نسبی (0 تا 1)
            end_point: نقطه پایان (x, y)
            adapter: QtAdapter

        Returns:
            QLinearGradient
        """
        try:
            if adapter and hasattr(adapter, '_QtGui'):
                gradient = adapter._QtGui.QLinearGradient(
                    start_point[0], start_point[1],
                    end_point[0], end_point[1]
                )
                for position, color in stops:
                    gradient.setColorAt(position, adapter.QColor(color))
                return gradient
        except Exception as e:
            logger.warning(f"Could not create linear gradient: {e}")
        return None

    @staticmethod
    def radial(
        stops: List[ColorStop],
        center: Tuple[float, float] = (0.5, 0.5),
        radius: float = 0.5,
        focal_point: Tuple[float, float] = None,
        adapter=None
    ) -> Any:
        """
        ایجاد QRadialGradient.

        Args:
            stops: لیست توقف‌های رنگی
            center: مرکز (x, y)
            radius: شعاع
            focal_point: نقطه کانونی (x, y)، اگر None باشد = center
            adapter: QtAdapter

        Returns:
            QRadialGradient
        """
        try:
            if adapter and hasattr(adapter, '_QtGui'):
                if focal_point is None:
                    focal_point = center
                gradient = adapter._QtGui.QRadialGradient(
                    center[0], center[1], radius,
                    focal_point[0], focal_point[1]
                )
                for position, color in stops:
                    gradient.setColorAt(position, adapter.QColor(color))
                return gradient
        except Exception as e:
            logger.warning(f"Could not create radial gradient: {e}")
        return None

    @staticmethod
    def get_gradient_style_sheet(
        stops: List[ColorStop],
        gradient_type: GradientType = GradientType.LINEAR,
        start: Tuple[float, float] = (0.0, 0.0),
        end: Tuple[float, float] = (1.0, 1.0),
    ) -> str:
        """
        تولید استایل گرادیانت برای StyleSheet.

        Qt StyleSheet از qlineargradient و qradialgradient پشتیبانی می‌کند.
        """
        if not stops:
            return ""

        stop_strs = []
        for pos, color in stops:
            stop_strs.append(f"stop:{pos:.2f} {color}")

        if gradient_type == GradientType.RADIAL:
            return f"background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, {' '.join(stop_strs)});"

        return (
            f"background: qlineargradient("
            f"x1:{start[0]:.2f}, y1:{start[1]:.2f}, "
            f"x2:{end[0]:.2f}, y2:{end[1]:.2f}, "
            f"{' '.join(stop_strs)});"
        )

    @staticmethod
    def create_preset_gradient(
        preset: str,
        adapter=None
    ) -> Any:
        """
        ایجاد گرادیانت از پیش‌تنظیم‌های آماده.

        Presets:
        - "primary": primary -> primary_dark
        - "sunset": orange -> red -> purple
        - "ocean": cyan -> blue -> indigo
        - "forest": green -> lime -> amber
        - "aurora": teal -> purple -> blue
        """
        presets = {
            "primary": [
                (0.0, "#4A90E2"), (0.5, "#6A52B5"), (1.0, "#8E44AD")
            ],
            "sunset": [
                (0.0, "#F59E0B"), (0.5, "#DC2626"), (1.0, "#7C3AED")
            ],
            "ocean": [
                (0.0, "#06B6D4"), (0.5, "#0EA5E9"), (1.0, "#6366F1")
            ],
            "forest": [
                (0.0, "#16A34A"), (0.5, "#65A30D"), (1.0, "#D97706")
            ],
            "aurora": [
                (0.0, "#14B8A6"), (0.33, "#6366F1"), (0.66, "#8B5CF6"), (1.0, "#3B82F6")
            ],
        }

        stops = presets.get(preset, presets["primary"])
        return GradientGenerator.linear(stops, adapter=adapter)


# ============================================================================
# Palette Factory
# ============================================================================

class PaletteFactory:
    """کارخانه تولید پالت‌های رنگی برای ۸ تم."""

    @staticmethod
    def create(mode: ThemeMode) -> ColorPalette:
        """ایجاد پالت مناسب بر اساس تم."""
        factories = {
            ThemeMode.LIGHT: PaletteFactory._light,
            ThemeMode.DARK: PaletteFactory._dark,
            ThemeMode.HIGH_CONTRAST: PaletteFactory._high_contrast,
            ThemeMode.OCEAN: PaletteFactory._ocean,
            ThemeMode.FOREST: PaletteFactory._forest,
            ThemeMode.SUNSET: PaletteFactory._sunset,
            ThemeMode.MIDNIGHT: PaletteFactory._midnight,
            ThemeMode.AURORA: PaletteFactory._aurora,
        }
        return factories.get(mode, PaletteFactory._light)()

    @staticmethod
    def _light() -> ColorPalette:
        return ColorPalette(
            primary="#2563EB", primary_light="#60A5FA", primary_dark="#1D4ED8",
            secondary="#7C3AED", secondary_light="#A78BFA", secondary_dark="#6D28D9",
            tertiary="#06B6D4", tertiary_light="#67E8F9", tertiary_dark="#0891B2",
            accent="#F59E0B", accent_light="#FBBF24", accent_dark="#D97706",
            background="#F8FAFC", background_alt="#F1F5F9", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#E2E8F0", surface_pressed="#CBD5E1",
            surface_selected="#DBEAFE",
            text_primary="#1E293B", text_secondary="#64748B",
            text_tertiary="#94A3B8", text_disabled="#CBD5E1",
            text_on_primary="#FFFFFF", text_on_dark="#F1F5F9", text_link="#2563EB",
            text_link_hover="#1D4ED8",
            border="#64748B", border_light="#CBD5E1", border_focus="#2563EB",
            border_hover="#64748B", border_error="#EF4444", border_success="#10B981",
            gradient_start="#4A90E2", gradient_mid="#6A52B5", gradient_end="#8E44AD",
            gradient_accent="#F59E0B",
        )

    @staticmethod
    def _dark() -> ColorPalette:
        return ColorPalette(
            primary="#3B82F6", primary_light="#93C5FD", primary_dark="#1D4ED8",
            secondary="#8B5CF6", secondary_light="#C4B5FD", secondary_dark="#7C3AED",
            tertiary="#22D3EE", tertiary_light="#67E8F9", tertiary_dark="#06B6D4",
            accent="#FBBF24", accent_light="#FDE68A", accent_dark="#F59E0B",
            background="#0F172A", background_alt="#1E293B", background_elevated="#1E293B",
            surface="#1E293B", surface_hover="#334155", surface_pressed="#475569",
            surface_selected="#1E3A5F",
            text_primary="#F1F5F9", text_secondary="#94A3B8",
            text_tertiary="#64748B", text_disabled="#475569",
            text_on_primary="#0F172A", text_on_dark="#F1F5F9", text_link="#60A5FA",
            text_link_hover="#93C5FD",
            border="#64748B", border_light="#475569", border_focus="#3B82F6",
            border_hover="#94A3B8", border_error="#F87171", border_success="#34D399",
            gradient_start="#1E3A5F", gradient_mid="#2D1B4E", gradient_end="#3B0A45",
            gradient_accent="#FBBF24",
        )

    @staticmethod
    def _high_contrast() -> ColorPalette:
        return ColorPalette(
            primary="#0000FF", primary_light="#4444FF", primary_dark="#0000CC",
            secondary="#800080", secondary_light="#AA44AA", secondary_dark="#660066",
            tertiary="#008080", tertiary_light="#44AAAA", tertiary_dark="#006666",
            accent="#FF8C00", accent_light="#FFAA44", accent_dark="#CC7000",
            background="#FFFFFF", background_alt="#F0F0F0", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#E0E0E0", surface_pressed="#CCCCCC",
            surface_selected="#CCCCFF",
            text_primary="#000000", text_secondary="#333333",
            text_tertiary="#555555", text_disabled="#888888",
            text_on_primary="#FFFFFF", text_on_dark="#FFFFFF", text_link="#0000FF",
            text_link_hover="#0000CC",
            border="#000000", border_light="#888888", border_focus="#0000FF",
            border_hover="#444444", border_error="#FF0000", border_success="#008000",
        )

    @staticmethod
    def _ocean() -> ColorPalette:
        return ColorPalette(
            primary="#0284C7", primary_light="#0EA5E9", primary_dark="#0369A1",
            secondary="#06B6D4", secondary_light="#22D3EE", secondary_dark="#0891B2",
            tertiary="#6366F1", tertiary_light="#818CF8", tertiary_dark="#4F46E5",
            accent="#14B8A6", accent_light="#5EEAD4", accent_dark="#0D9488",
            success="#10B981", warning="#F59E0B", error="#EF4444", info="#0EA5E9",
            background="#F0F9FF", background_alt="#E0F2FE", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#BAE6FD", surface_pressed="#7DD3FC",
            surface_selected="#DBEAFE",
            text_primary="#0C4A6E", text_secondary="#0369A1",
            text_tertiary="#0EA5E9", text_disabled="#BAE6FD",
            text_on_primary="#FFFFFF", text_on_dark="#E0F2FE", text_link="#0284C7",
            text_link_hover="#0EA5E9",
            border="#0EA5E9", border_light="#7DD3FC", border_focus="#0EA5E9",
            border_hover="#38BDF8", border_error="#EF4444", border_success="#10B981",
            gradient_start="#0EA5E9", gradient_mid="#06B6D4", gradient_end="#6366F1",
            gradient_accent="#14B8A6",
        )

    @staticmethod
    def _forest() -> ColorPalette:
        return ColorPalette(
            primary="#16A34A", primary_light="#4ADE80", primary_dark="#166534",
            secondary="#65A30D", secondary_light="#A3E635", secondary_dark="#4D7C0F",
            tertiary="#78350F", tertiary_light="#A16207", tertiary_dark="#451A03",
            accent="#D97706", accent_light="#FBBF24", accent_dark="#B45309",
            success="#16A34A", warning="#D97706", error="#DC2626", info="#16A34A",
            background="#F7FEE7", background_alt="#ECFCCB", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#D9F99D", surface_pressed="#A3E635",
            surface_selected="#DCFCE7",
            text_primary="#14532D", text_secondary="#166534",
            text_tertiary="#65A30D", text_disabled="#86EFAC",
            text_on_primary="#FFFFFF", text_on_dark="#ECFCCB", text_link="#16A34A",
            text_link_hover="#4ADE80",
            border="#16A34A", border_light="#86EFAC", border_focus="#16A34A",
            border_hover="#22C55E", border_error="#DC2626", border_success="#16A34A",
            gradient_start="#16A34A", gradient_mid="#65A30D", gradient_end="#D97706",
            gradient_accent="#78350F",
        )

    @staticmethod
    def _sunset() -> ColorPalette:
        return ColorPalette(
            primary="#EA580C", primary_light="#FB923C", primary_dark="#C2410C",
            secondary="#DC2626", secondary_light="#F87171", secondary_dark="#B91C1C",
            tertiary="#7C3AED", tertiary_light="#A78BFA", tertiary_dark="#6D28D9",
            accent="#F59E0B", accent_light="#FCD34D", accent_dark="#D97706",
            success="#10B981", warning="#F59E0B", error="#DC2626", info="#EA580C",
            background="#FFF7ED", background_alt="#FFEDD5", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#FED7AA", surface_pressed="#FDBA74",
            surface_selected="#FEF3C7",
            text_primary="#7C2D12", text_secondary="#9A3412",
            text_tertiary="#C2410C", text_disabled="#FDBA74",
            text_on_primary="#FFFFFF", text_on_dark="#FFEDD5", text_link="#EA580C",
            text_link_hover="#FB923C",
            border="#F97316", border_light="#FDBA74", border_focus="#EA580C",
            border_hover="#FB923C", border_error="#DC2626", border_success="#10B981",
            gradient_start="#EA580C", gradient_mid="#DC2626", gradient_end="#7C3AED",
            gradient_accent="#F59E0B",
        )

    @staticmethod
    def _midnight() -> ColorPalette:
        """تم نیمه‌شب - مشکی عمیق با accent بنفش."""
        return ColorPalette(
            primary="#8B5CF6", primary_light="#C4B5FD", primary_dark="#6D28D9",
            secondary="#6366F1", secondary_light="#A5B4FC", secondary_dark="#4F46E5",
            tertiary="#EC4899", tertiary_light="#FBCFE8", tertiary_dark="#DB2777",
            accent="#F59E0B", accent_light="#FCD34D", accent_dark="#D97706",
            success="#34D399", warning="#FBBF24", error="#F87171", info="#8B5CF6",
            background="#020617", background_alt="#0F172A", background_elevated="#1E1B4B",
            surface="#111827", surface_hover="#1F2937", surface_pressed="#374151",
            surface_selected="#2D1B4E",
            text_primary="#F8FAFC", text_secondary="#94A3B8",
            text_tertiary="#64748B", text_disabled="#374151",
            text_on_primary="#FFFFFF", text_on_dark="#E2E8F0", text_link="#C4B5FD",
            text_link_hover="#8B5CF6",
            border="#4B5563", border_light="#374151", border_focus="#8B5CF6",
            border_hover="#6B7280", border_error="#F87171", border_success="#34D399",
            gradient_start="#020617", gradient_mid="#1E1B4B", gradient_end="#2D1B4E",
            gradient_accent="#F59E0B",
        )

    @staticmethod
    def _aurora() -> ColorPalette:
        """تم شفق قطبی - سبز-بنفش-آبی روشن."""
        return ColorPalette(
            primary="#106D66", primary_light="#14B8A6", primary_dark="#115E59",
            secondary="#8B5CF6", secondary_light="#C4B5FD", secondary_dark="#6D28D9",
            tertiary="#3B82F6", tertiary_light="#93C5FD", tertiary_dark="#1D4ED8",
            accent="#F59E0B", accent_light="#FCD34D", accent_dark="#D97706",
            success="#10B981", warning="#F59E0B", error="#EF4444", info="#14B8A6",
            background="#ECFEFF", background_alt="#CFFAFE", background_elevated="#FFFFFF",
            surface="#FFFFFF", surface_hover="#A5F3FC", surface_pressed="#67E8F9",
            surface_selected="#D1FAE5",
            text_primary="#022C22", text_secondary="#0D9488",
            text_tertiary="#14B8A6", text_disabled="#A5F3FC",
            text_on_primary="#FFFFFF", text_on_dark="#ECFEFF", text_link="#0D9488",
            text_link_hover="#5EEAD4",
            border="#0D9488", border_light="#5EEAD4", border_focus="#14B8A6",
            border_hover="#5EEAD4", border_error="#EF4444", border_success="#10B981",
            gradient_start="#14B8A6", gradient_mid="#8B5CF6", gradient_end="#3B82F6",
            gradient_accent="#F59E0B",
        )


# ============================================================================
# System Detector
# ============================================================================

class SystemDetector:
    """تشخیص‌دهنده هوشمند سیستم عامل و نسخه Qt."""

    @staticmethod
    def get_os_type() -> str:
        if sys.platform == "win32": return "windows"
        elif sys.platform == "darwin": return "macos"
        elif sys.platform.startswith("linux"): return "linux"
        return "unknown"

    @staticmethod
    def get_windows_version() -> WindowsVersion:
        os_type = SystemDetector.get_os_type()
        if os_type == "linux": return WindowsVersion.LINUX
        if os_type == "macos": return WindowsVersion.MACOS
        if os_type != "windows": return WindowsVersion.UNKNOWN

        try:
            release = platform.release()
            build = int(platform.version().split('.')[-1]) if platform.version() else 0
            if build >= 22000: return WindowsVersion.WIN_11
            if build >= 10240: return WindowsVersion.WIN_10
            if release == "8.1" or release.startswith("6.3"): return WindowsVersion.WIN_8_1
            if release == "8" or release.startswith("6.2"): return WindowsVersion.WIN_8
            if release == "7" or release.startswith("6.1"): return WindowsVersion.WIN_7
            return WindowsVersion.UNKNOWN
        except Exception as e:
            logger.warning(f"Windows detection error: {e}")
            return WindowsVersion.UNKNOWN

    @staticmethod
    def get_windows_version_name() -> str:
        names = {
            WindowsVersion.WIN_7: "Windows 7", WindowsVersion.WIN_8: "Windows 8",
            WindowsVersion.WIN_8_1: "Windows 8.1", WindowsVersion.WIN_10: "Windows 10",
            WindowsVersion.WIN_11: "Windows 11", WindowsVersion.LINUX: "Linux",
            WindowsVersion.MACOS: "macOS", WindowsVersion.UNKNOWN: "Unknown",
        }
        return names.get(SystemDetector.get_windows_version(), "Unknown")

    @staticmethod
    def is_windows_10_or_newer() -> bool:
        v = SystemDetector.get_windows_version()
        return v in (WindowsVersion.WIN_10, WindowsVersion.WIN_11)

    @staticmethod
    def get_recommended_qt_version() -> QtVersion:
        if sys.platform != "win32": return QtVersion.PYQT6
        return QtVersion.PYQT6 if SystemDetector.is_windows_10_or_newer() else QtVersion.PYQT5

    @staticmethod
    def check_qt_availability(qt_version: QtVersion) -> bool:
        try:
            if qt_version == QtVersion.PYQT6: import PyQt6; return True
            elif qt_version == QtVersion.PYQT5: import PyQt5; return True
            elif qt_version == QtVersion.PYSIDE6: import PySide6; return True
        except ImportError: return False
        return False

    @staticmethod
    def get_available_qt_version() -> QtVersion:
        rec = SystemDetector.get_recommended_qt_version()
        if SystemDetector.check_qt_availability(rec):
            logger.info(f"Using Qt: {rec.name}")
            return rec
        fallback = QtVersion.PYQT5 if rec == QtVersion.PYQT6 else QtVersion.PYQT6
        if SystemDetector.check_qt_availability(fallback):
            logger.warning(f"Fallback Qt: {fallback.name}")
            return fallback
        raise ImportError("No PyQt installed. pip install PyQt6 or PyQt5")

    @staticmethod
    def get_dpi_scale() -> float:
        """تشخیص DPI Scaling Factor با fallback امن."""
        try:
            if SystemDetector.check_qt_availability(QtVersion.PYQT6):
                from PyQt6.QtWidgets import QApplication
            else:
                from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                logger.debug("QApplication not yet created, cannot detect DPI")
                return 1.0

            screen = app.primaryScreen()
            if screen is None:
                logger.debug("No primary screen found")
                return 1.0

            if hasattr(screen, 'devicePixelRatio'):
                return screen.devicePixelRatio()
            elif hasattr(screen, 'logicalDotsPerInch'):
                return screen.logicalDotsPerInch() / 96.0
        except Exception as e:
            logger.warning(f"Failed to detect DPI: {e}")

        return 1.0

    @staticmethod
    def get_system_memory_gb() -> float:
        """تشخیص مقدار RAM سیستم (GB). با fallback امن."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            logger.debug("psutil not installed, cannot detect RAM")
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to detect RAM: {e}")
            return 0.0

    @staticmethod
    def get_cpu_count() -> int:
        """تعداد هسته‌های CPU."""
        return os.cpu_count() or 4


# ============================================================================
# Qt Adapter
# ============================================================================

class QtAdapter:
    """آداپتور یکسان‌سازی API بین PyQt5 و PyQt6."""

    _instance: Optional['QtAdapter'] = None
    _lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> 'QtAdapter':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if QtAdapter._initialized:
            return

        with QtAdapter._lock:
            if QtAdapter._initialized:
                return

            self._qt_version = SystemDetector.get_available_qt_version()
            self._import_modules()
            self._setup_enums()
            self._setup_high_dpi()

            QtAdapter._initialized = True
            logger.info(f"QtAdapter ready: {self._qt_version.name}")

    def _import_modules(self):
        if self._qt_version == QtVersion.PYQT6:
            from PyQt6 import QtWidgets, QtGui, QtCore
            from PyQt6.QtCore import (
                Qt, QTimer, QPointF, QEvent, pyqtSignal, QSize, QRect,
                QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
            )
            from PyQt6.QtGui import (
                QPainter, QLinearGradient, QColor, QRadialGradient, QFont,
                QKeySequence, QDoubleValidator, QPixmap, QTransform,
                QFontDatabase, QIntValidator, QAction, QPalette, QBrush,
                QPen, QConicalGradient, QShortcut
            )
            from PyQt6.QtWidgets import (
                QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout,
                QPushButton, QGridLayout, QDialog, QLineEdit, QMessageBox,
                QHBoxLayout, QTextEdit, QListWidget, QCheckBox, QListWidgetItem,
                QAbstractItemView, QMenuBar, QGraphicsView,
                QGraphicsScene, QGraphicsPixmapItem, QFrame, QDesktopWidget,
                QTabWidget, QScrollArea, QFontDialog, QComboBox, QSpinBox,
                QSlider, QProgressBar, QToolTip, QTableWidget, QHeaderView,
                QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                QGraphicsBlurEffect, QGraphicsColorizeEffect
            )
        else:
            from PyQt5 import QtWidgets, QtGui, QtCore
            from PyQt5.QtCore import (
                Qt, QTimer, QPointF, QEvent, pyqtSignal, QSize, QRect,
                QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
            )
            from PyQt5.QtGui import (
                QPainter, QLinearGradient, QColor, QRadialGradient, QFont,
                QKeySequence, QDoubleValidator, QPixmap, QTransform,
                QFontDatabase, QIntValidator, QPalette, QBrush,
                QPen, QConicalGradient
            )
            from PyQt5.QtWidgets import (
                QApplication, QMainWindow, QAction, QWidget, QLabel, QVBoxLayout,
                QPushButton, QGridLayout, QDialog, QLineEdit, QMessageBox,
                QHBoxLayout, QTextEdit, QListWidget, QCheckBox, QListWidgetItem,
                QAbstractItemView, QShortcut, QMenuBar, QGraphicsView,
                QGraphicsScene, QGraphicsPixmapItem, QFrame, QDesktopWidget,
                QTabWidget, QScrollArea, QFontDialog, QComboBox, QSpinBox,
                QSlider, QProgressBar, QToolTip, QTableWidget, QHeaderView,
                QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                QGraphicsBlurEffect, QGraphicsColorizeEffect
            )

        # Store module references
        self._QtWidgets = QtWidgets
        self._QtGui = QtGui
        self._QtCore = QtCore

        # QtGui classes
        self.QAction = QAction
        self.QKeySequence = QKeySequence
        self.QPainter = QPainter
        self.QLinearGradient = QLinearGradient
        self.QRadialGradient = QRadialGradient
        self.QConicalGradient = QConicalGradient
        self.QPen = QPen
        self.QBrush = QBrush
        self.QTransform = QTransform
        self.QDoubleValidator = QDoubleValidator
        self.QIntValidator = QIntValidator

        # QtWidgets classes
        self.QApplication = QApplication
        self.QMainWindow = QMainWindow
        self.QWidget = QWidget
        self.QLabel = QLabel
        self.QVBoxLayout = QVBoxLayout
        self.QHBoxLayout = QHBoxLayout
        self.QGridLayout = QGridLayout
        self.QPushButton = QPushButton
        self.QLineEdit = QLineEdit
        self.QTextEdit = QTextEdit
        self.QDialog = QDialog
        self.QMessageBox = QMessageBox
        self.QListWidget = QListWidget
        self.QCheckBox = QCheckBox
        self.QComboBox = QComboBox
        self.QSpinBox = QSpinBox
        self.QSlider = QSlider
        self.QProgressBar = QProgressBar
        self.QTableWidget = QTableWidget
        self.QTabWidget = QTabWidget
        self.QScrollArea = QScrollArea
        self.QFrame = QFrame
        self.QMenuBar = QMenuBar
        self.QShortcut = QShortcut
        self.QGraphicsView = QGraphicsView
        self.QGraphicsScene = QGraphicsScene
        self.QGraphicsPixmapItem = QGraphicsPixmapItem
        self.QDesktopWidget = QDesktopWidget
        self.QFontDialog = QFontDialog
        self.QToolTip = QToolTip
        self.QHeaderView = QHeaderView

        # QtCore classes
        self.Qt = Qt
        self.QTimer = QTimer
        self.QSize = QSize
        self.QRect = QRect
        self.QPointF = QPointF
        self.QEvent = QEvent
        self.pyqtSignal = pyqtSignal
        self.QPropertyAnimation = QPropertyAnimation
        self.QEasingCurve = QEasingCurve
        self.QParallelAnimationGroup = QParallelAnimationGroup

        # QtGui classes
        self.QFont = QFont
        self.QColor = QColor
        self.QPixmap = QPixmap
        self.QFontDatabase = QFontDatabase
        self.QPalette = QPalette

        # Effects
        self.QGraphicsDropShadowEffect = QGraphicsDropShadowEffect
        self.QGraphicsOpacityEffect = QGraphicsOpacityEffect
        self.QGraphicsBlurEffect = QGraphicsBlurEffect
        self.QGraphicsColorizeEffect = QGraphicsColorizeEffect

    def _setup_enums(self):
        if self._qt_version == QtVersion.PYQT6:
            self.AlignCenter = self.Qt.AlignmentFlag.AlignCenter
            self.AlignRight = self.Qt.AlignmentFlag.AlignRight
            self.AlignLeft = self.Qt.AlignmentFlag.AlignLeft
            self.AlignTop = self.Qt.AlignmentFlag.AlignTop
            self.AlignBottom = self.Qt.AlignmentFlag.AlignBottom
            self.ItemIsUserCheckable = self.Qt.ItemFlag.ItemIsUserCheckable
            self.Unchecked = self.Qt.CheckState.Unchecked
            self.Checked = self.Qt.CheckState.Checked
            self.PartiallyChecked = self.Qt.CheckState.PartiallyChecked
            self.NoFrame = self._QtWidgets.QFrame.Shape.NoFrame
            self.RichText = self.Qt.TextFormat.RichText
            self.PlainText = self.Qt.TextFormat.PlainText
            self.MultiSelection = self._QtWidgets.QAbstractItemView.SelectionMode.MultiSelection
            self.ExtendedSelection = self._QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
            self.NoSelection = self._QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        else:
            self.AlignCenter = self.Qt.AlignCenter
            self.AlignRight = self.Qt.AlignRight
            self.AlignLeft = self.Qt.AlignLeft
            self.AlignTop = self.Qt.AlignTop
            self.AlignBottom = self.Qt.AlignBottom
            self.ItemIsUserCheckable = self.Qt.ItemIsUserCheckable
            self.Unchecked = self.Qt.Unchecked
            self.Checked = self.Qt.Checked
            self.PartiallyChecked = self.Qt.PartiallyChecked
            self.NoFrame = self._QtWidgets.QFrame.NoFrame
            self.RichText = self.Qt.RichText
            self.PlainText = self.Qt.PlainText
            self.MultiSelection = self._QtWidgets.QAbstractItemView.MultiSelection
            self.ExtendedSelection = self._QtWidgets.QAbstractItemView.ExtendedSelection
            self.NoSelection = self._QtWidgets.QAbstractItemView.NoSelection

    def _setup_high_dpi(self):
        if self._qt_version != QtVersion.PYQT6:
            try:
                self.QApplication.setAttribute(self.Qt.AA_EnableHighDpiScaling, True)
                self.QApplication.setAttribute(self.Qt.AA_UseHighDpiPixmaps, True)
            except Exception: pass

    @property
    def qt_version(self) -> QtVersion:
        return self._qt_version

    @property
    def is_pyqt6(self) -> bool:
        return self._qt_version == QtVersion.PYQT6


# ============================================================================
# Theme Manager (Singleton)
# ============================================================================

class ThemeManager:
    """
    مدیریت تم و استایل پیشرفته برنامه.

    نسخه 4.0: Production Ready
    - همه افکت‌ها با native Qt
    - ۸ تم رنگی
    - Observer pattern برای اعلان تغییرات
    - Export/Import تنظیمات
    """

    _instance: Optional['ThemeManager'] = None
    _initialized: bool = False
    _observers: List[Callable[[ThemeMode], None]] = []
    _instance_lock = threading.Lock()
    _observers_lock = threading.Lock()  # Class-level lock

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ThemeManager._initialized:
            return

        with ThemeManager._instance_lock:
            if ThemeManager._initialized:
                return

            self._system = SystemDetector()
            self._adapter = QtAdapter()
            self._qt_version = self._adapter.qt_version

            self._mode = ThemeMode.LIGHT
            self._palette = PaletteFactory.create(self._mode)
            self._font_config = FontConfig()
            self._glass_level = GlassLevel.NONE
            self._shadow_elevation = ShadowElevation.LOW
            self._border_radius = BorderRadius.NORMAL
            self._animation_duration = AnimationDuration.NORMAL

            self._available_fonts: Optional[List[str]] = None
            self._fonts_checked: bool = False
            self._style_cache = LRUCache(max_size=500)

            ThemeManager._initialized = True
            logger.info(
                f"ThemeManager v4.0: {self._system.get_windows_version_name()}, "
                f"{self._qt_version.name}, {self._mode.name}"
            )

    @property
    def available_fonts(self) -> List[str]:
        """Lazy loading فونت‌ها."""
        if self._available_fonts is None:
            self._load_fonts()
        return self._available_fonts


    def _load_fonts(self):
        """بارگذاری تنبل فونت‌ها."""
        try:
            self._available_fonts = self._adapter.QFontDatabase().families()
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
            self._available_fonts = ["Arial"]

        # حالا که فونت‌ها رو داریم، fallback ها رو چک کن
        self._check_available_fonts()


    def _check_available_fonts(self):
        """بررسی و تنظیم فونت‌های fallback."""
        if not self._available_fonts or self._fonts_checked:
            return

        fc = self._font_config

        if fc.family_fa not in self._available_fonts:
            for f in fc.family_fa_fallback:
                if f in self._available_fonts:
                    object.__setattr__(fc, 'family_fa', f)
                    break

        if fc.family_en not in self._available_fonts:
            for f in fc.family_en_fallback:
                if f in self._available_fonts:
                    object.__setattr__(fc, 'family_en', f)
                    break

        if fc.family_mono not in self._available_fonts:
            for f in fc.family_mono_fallback:
                if f in self._available_fonts:
                    object.__setattr__(fc, 'family_mono', f)
                    break

        self._fonts_checked = True

    # ----- Observer Pattern -----

    def subscribe(self, callback: Callable[[ThemeMode], None]):
        with ThemeManager._observers_lock:
            if callback not in self._observers:
                self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[ThemeMode], None]):
        with ThemeManager._observers_lock:
            if callback in self._observers:
                self._observers.remove(callback)

    def _notify_observers(self):
        with ThemeManager._observers_lock:
            observers_copy = list(self._observers)  # Thread-safe copy

        for cb in observers_copy:
            try:
                cb(self._mode)
            except Exception as e:
                logger.error(f"Observer error: {e}")

    # ----- Properties -----

    @property
    def mode(self) -> ThemeMode: return self._mode
    @property
    def palette(self) -> ColorPalette: return self._palette
    @property
    def is_dark(self) -> bool: return self._mode in (ThemeMode.DARK, ThemeMode.MIDNIGHT)
    @property
    def qt_version(self) -> QtVersion: return self._qt_version
    @property
    def is_pyqt6(self) -> bool: return self._adapter.is_pyqt6
    @property
    def windows_version(self) -> str: return self._system.get_windows_version_name()
    @property
    def glass_level(self) -> GlassLevel: return self._glass_level
    @property
    def shadow_elevation(self) -> ShadowElevation: return self._shadow_elevation
    @property
    def adapter(self) -> QtAdapter: return self._adapter

    # ----- Theme Management -----

    def set_mode(self, mode: ThemeMode):
        self._mode = mode
        self._palette = PaletteFactory.create(mode)
        self._style_cache.clear()
        self._notify_observers()
        logger.info(f"Theme → {mode.name}")

    def toggle_dark_light(self):
        self.set_mode(ThemeMode.DARK if self._mode == ThemeMode.LIGHT else ThemeMode.LIGHT)

    def cycle_theme(self):
        themes = list(ThemeMode)
        idx = themes.index(self._mode)
        self.set_mode(themes[(idx + 1) % len(themes)])

    def set_glass_level(self, level: GlassLevel):
        self._glass_level = level
        self._style_cache.clear()

    def set_shadow_elevation(self, elevation: ShadowElevation):
        self._shadow_elevation = elevation
        self._style_cache.clear()

    def set_border_radius(self, radius: BorderRadius):
        self._border_radius = radius
        self._style_cache.clear()

    def _get_all_contrast_ratios(self) -> List[float]:
        """محاسبه همه نسبت‌های کنتراست مهم."""
        p = self._palette
        ratios = []

        # Primary checks
        ratios.append(contrast_ratio(p.text_primary, p.background))
        ratios.append(contrast_ratio(p.text_secondary, p.background))
        ratios.append(contrast_ratio(p.text_on_primary, p.primary))
        ratios.append(contrast_ratio(p.text_on_dark, p.primary_dark))

        # Border checks
        ratios.append(contrast_ratio(p.border, p.background))
        ratios.append(contrast_ratio(p.border_focus, p.background))

        return ratios

    def check_accessibility(self) -> dict:
        """
        بررسی accessibility تم فعلی بر اساس WCAG 2.1.

        Returns:
            dict with:
                - passes: bool - آیا همه بررسی‌ها پاس شدن؟
                - level: str - سطح WCAG ("AAA", "AA", "FAIL")
                - issues: list - مشکلات یافت شده
                - ratios: dict - نسبت‌های کنتراست
        """
        p = self._palette
        issues = []
        ratio_details = {}

        # Check 1: Text primary on background
        r1 = contrast_ratio(p.text_primary, p.background)
        ratio_details['text_primary/bg'] = round(r1, 2)
        if r1 < 4.5:
            issues.append(f"متن اصلی روی پس‌زمینه: {r1:.1f}:1 (حداقل 4.5:1 نیاز است)")

        # Check 2: Text secondary on background
        r2 = contrast_ratio(p.text_secondary, p.background)
        ratio_details['text_secondary/bg'] = round(r2, 2)
        if r2 < 3.0:
            issues.append(f"متن فرعی روی پس‌زمینه: {r2:.1f}:1 (حداقل 3.0:1 نیاز است)")

        # Check 3: Text on primary
        r3 = contrast_ratio(p.text_on_primary, p.primary)
        ratio_details['text_on_primary'] = round(r3, 2)
        if r3 < 4.5:
            issues.append(f"متن روی دکمه اصلی: {r3:.1f}:1 (حداقل 4.5:1 نیاز است)")

        # Check 4: Border on background
        r4 = contrast_ratio(p.border, p.background)
        ratio_details['border/bg'] = round(r4, 2)
        if r4 < 3.0:
            issues.append(f"حاشیه روی پس‌زمینه: {r4:.1f}:1 (حداقل 3.0:1 نیاز است)")

        # Check 5: Link text
        r5 = contrast_ratio(p.text_link, p.background)
        ratio_details['link/bg'] = round(r5, 2)
        if r5 < 3.0:
            issues.append(f"لینک روی پس‌زمینه: {r5:.1f}:1 (حداقل 3.0:1 نیاز است)")

        # Determine WCAG level
        all_ratios = list(ratio_details.values())
        if all(r >= 7.0 for r in all_ratios):
            level = "AAA"
        elif all(r >= 4.5 for r in all_ratios):
            level = "AA"
        elif all(r >= 3.0 for r in all_ratios):
            level = "AA (Large Text)"
        else:
            level = "FAIL"

        return {
            "passes": len(issues) == 0,
            "level": level,
            "issues": issues,
            "ratios": ratio_details,
            "theme": self._mode.name,
        }

    def print_accessibility_report(self):
        """نمایش گزارش accessibility در کنسول."""
        report = self.check_accessibility()
        print(f"\n{'='*50}")
        print(f"♿ Accessibility Report - {report['theme']} Theme")
        print(f"{'='*50}")
        print(f"Status: {'✅ PASS' if report['passes'] else '❌ FAIL'}")
        print(f"WCAG Level: {report['level']}")
        print(f"\nContrast Ratios:")
        for name, ratio in report['ratios'].items():
            status = "✅" if ratio >= 4.5 else ("⚠️" if ratio >= 3.0 else "❌")
            print(f"  {status} {name}: {ratio}:1")
        if report['issues']:
            print(f"\nIssues Found:")
            for issue in report['issues']:
                print(f"  • {issue}")
        print(f"{'='*50}\n")
        return report

    @contextmanager
    def temporary_theme(self, mode: ThemeMode):
        """
        تغییر موقت تم.

        Usage:
            with theme.temporary_theme(ThemeMode.DARK):
                # اینجا تم Dark هست
                show_dark_dialog()
            # اینجا تم به حالت قبل برمیگرده
        """
        old_mode = self._mode
        self.set_mode(mode)
        try:
            yield
        finally:
            self.set_mode(old_mode)

    @contextmanager
    def temporary_glass(self, level: GlassLevel):
        """تغییر موقت سطح glass."""
        old_level = self._glass_level
        self.set_glass_level(level)
        try:
            yield
        finally:
            self.set_glass_level(old_level)

    # ----- Font Methods -----

    def _get_fallback_font(self, family: str) -> str:
        """پیدا کردن اولین فونت fallback موجود."""
        fallback_map = {
            self._font_config.family_fa: self._font_config.family_fa_fallback,
            self._font_config.family_en: self._font_config.family_en_fallback,
            self._font_config.family_mono: self._font_config.family_mono_fallback,
            self._font_config.family_math: self._font_config.family_math_fallback,
        }

        fallbacks = fallback_map.get(family, ["Arial"])
        for fallback in fallbacks:
            if isinstance(fallback, str) and fallback in self._available_fonts:
                return fallback

        # Last resort
        if self._available_fonts:
            return self._available_fonts[0]
        return "Arial"

    def get_font(self, size: Union[int, FontSize] = FontSize.NORMAL,
                 bold: bool = False, mono: bool = False, math: bool = False,
                 rtl: bool = True, italic: bool = False) -> Any:
        if isinstance(size, FontSize):
            size = size.value

        family = (
            self._font_config.family_math if math else
            self._font_config.family_mono if mono else
            self._font_config.family_fa if rtl else
            self._font_config.family_en
        )

        # Validate font exists, use fallback if not
        if self._available_fonts and family not in self._available_fonts:
            family = self._get_fallback_font(family)

        try:
            font = self._adapter.QFont(family, size)
            font.setBold(bold)
            font.setItalic(italic)
            return font
        except Exception as e:
            logger.error(f"Failed to create font {family}: {e}")
            # Ultimate fallback
            font = self._adapter.QFont("Arial", size)
            font.setBold(bold)
            font.setItalic(italic)
            return font

    def get_app_font(self): return self.get_font(size=FontSize.NORMAL)
    def get_title_font(self): return self.get_font(size=FontSize.TITLE, bold=True)
    def get_hero_font(self): return self.get_font(size=FontSize.HERO, bold=True)
    def get_mono_font(self, size: int = 12): return self.get_font(size=size, mono=True, rtl=False)
    def get_math_font(self, size: int = 14): return self.get_font(size=size, math=True, rtl=False)

    # ----- Color Methods -----

    def color(self, name: str) -> str:
        return getattr(self._palette, name, '#000000')

    def qcolor(self, name: str, alpha: int = 255) -> Any:
        hex_color = self.color(name)
        r, g, b, a = hex_to_qcolor(hex_color, alpha)
        return self._adapter.QColor(r, g, b, a)

    # ----- Shadow & Glass Helpers -----

    def apply_shadow(self, widget: Any, elevation: ShadowElevation = None):
        elev = elevation or self._shadow_elevation
        ShadowSystem.apply_shadow(widget, elev, self.is_dark, self._adapter)

    def apply_glass(self, widget: Any, level: GlassLevel = None):
        lvl = level or self._glass_level
        base = (255, 255, 255, 220) if not self.is_dark else (30, 30, 50, 200)
        GlassmorphismSystem.apply_glass(widget, lvl, base, self._adapter)

    # =========================================================================
    # Style Sheet Builders (۳۰+ متد)
    # =========================================================================

    def get_button_style(
        self,
        variant: str = "primary",
        size: str = "normal",
        full_width: bool = False,
        rounded: bool = False,
        disabled: bool = False,
        glass: bool = False,
        custom_bg: Optional[str] = None,
        custom_text_color: Optional[str] = None,
    ) -> str:
        """
        تولید استایل QPushButton با پشتیبانی از variant‌های مختلف.

        Args:
            variant: نوع دکمه
                - "primary": دکمه اصلی با رنگ primary
                - "secondary": دکمه فرعی با رنگ secondary
                - "tertiary": دکمه سطح سوم
                - "accent": دکمه تأکیدی
                - "danger": دکمه خطر (قرمز)
                - "success": دکمه موفقیت (سبز)
                - "warning": دکمه هشدار (نارنجی)
                - "info": دکمه اطلاعات (آبی)
                - "ghost": دکمه شفاف
                - "outline": دکمه خط‌دار
                - "link": دکمه لینک
                - "custom": دکمه سفارشی (نیاز به custom_bg)
            size: سایز دکمه - "tiny", "small", "normal", "large", "xl"
            full_width: آیا تمام عرض والد را بگیرد؟
            rounded: آیا کاملاً گرد (pill shape) باشد؟
            disabled: آیا غیرفعال باشد؟
            glass: آیا افکت شیشه‌ای داشته باشد؟
            custom_bg: رنگ پس‌زمینه سفارشی (برای variant="custom")
            custom_text_color: رنگ متن سفارشی

        Returns:
            stylesheet string برای QPushButton

        Example:
            >>> theme.get_button_style("primary", "large")
            >>> theme.get_button_style("danger", full_width=True)
            >>> theme.get_button_style("custom", custom_bg="#FF5733")
            >>> theme.get_button_style("outline", rounded=True, glass=True)
        """
        # Build cache key
        cache_key = (
            f"btn_{variant}_{size}_{int(full_width)}_{int(rounded)}_"
            f"{int(disabled)}_{int(glass)}_{custom_bg}_{custom_text_color}"
        )

        cached = self._style_cache.get(cache_key)
        if cached is not None:
            return cached

        p = self._palette
        fc = self._font_config

        # ========================================================================
        # Define variant color mappings
        # ========================================================================
        variant_map = {
            "primary": {
                "bg": p.primary,
                "bg_hover": p.primary_dark,
                "bg_pressed": darken_color(p.primary_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "secondary": {
                "bg": p.secondary,
                "bg_hover": p.secondary_dark,
                "bg_pressed": darken_color(p.secondary_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "tertiary": {
                "bg": p.tertiary or p.primary,
                "bg_hover": p.tertiary_dark or p.primary_dark,
                "bg_pressed": darken_color(p.tertiary_dark or p.primary_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "accent": {
                "bg": p.accent or "#F59E0B",
                "bg_hover": p.accent_dark or "#D97706",
                "bg_pressed": darken_color(p.accent_dark or "#D97706", 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "danger": {
                "bg": p.error,
                "bg_hover": p.error_dark,
                "bg_pressed": darken_color(p.error_dark, 0.15),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_error,
            },
            "success": {
                "bg": p.success,
                "bg_hover": p.success_dark,
                "bg_pressed": darken_color(p.success_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_success,
            },
            "warning": {
                "bg": p.warning,
                "bg_hover": p.warning_dark,
                "bg_pressed": darken_color(p.warning_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": "#000000",
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "info": {
                "bg": p.info,
                "bg_hover": p.info_dark,
                "bg_pressed": darken_color(p.info_dark, 0.1),
                "bg_disabled": p.text_disabled,
                "text": p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "ghost": {
                "bg": "transparent",
                "bg_hover": p.surface_hover,
                "bg_pressed": p.surface_pressed,
                "bg_disabled": "transparent",
                "text": p.text_primary,
                "text_disabled": p.text_disabled,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
            "outline": {
                "bg": "transparent",
                "bg_hover": p.primary_alpha_10 if hasattr(p, 'primary_alpha_10') else hex_to_rgba(p.primary, 0.1),
                "bg_pressed": p.primary_alpha_20 if hasattr(p, 'primary_alpha_20') else hex_to_rgba(p.primary, 0.2),
                "bg_disabled": "transparent",
                "text": p.primary,
                "text_disabled": p.text_disabled,
                "border": f"2px solid {p.primary}",
                "border_hover": f"2px solid {p.primary_dark}",
                "border_focus": f"2px solid {p.border_focus}",
            },
            "link": {
                "bg": "transparent",
                "bg_hover": "transparent",
                "bg_pressed": "transparent",
                "bg_disabled": "transparent",
                "text": p.text_link,
                "text_disabled": p.text_disabled,
                "border": "none",
                "border_hover": "none",
                "border_focus": f"1px dashed {p.border_focus}",
            },
            "custom": {
                "bg": custom_bg or p.primary,
                "bg_hover": darken_color(custom_bg or p.primary, 0.1),
                "bg_pressed": darken_color(custom_bg or p.primary, 0.2),
                "bg_disabled": p.text_disabled,
                "text": custom_text_color or p.text_on_primary,
                "text_disabled": p.text_tertiary,
                "border": "none",
                "border_hover": "none",
                "border_focus": p.border_focus,
            },
        }

        variant_config = variant_map.get(variant, variant_map["primary"])

        # Override text color if custom_text_color provided
        if custom_text_color and variant != "custom":
            variant_config["text"] = custom_text_color

        # ========================================================================
        # Size mappings
        # ========================================================================
        size_config = {
            "tiny": {
                "padding": "3px 8px",
                "font_size": fc.size_caption,
                "min_width": "40px",
                "min_height": "20px",
            },
            "small": {
                "padding": "5px 12px",
                "font_size": fc.size_tiny,
                "min_width": "60px",
                "min_height": "26px",
            },
            "normal": {
                "padding": "8px 18px",
                "font_size": fc.size_normal,
                "min_width": "80px",
                "min_height": "32px",
            },
            "large": {
                "padding": "12px 24px",
                "font_size": fc.size_large,
                "min_width": "100px",
                "min_height": "40px",
            },
            "xl": {
                "padding": "16px 32px",
                "font_size": fc.size_xl,
                "min_width": "120px",
                "min_height": "48px",
            },
        }

        size_data = size_config.get(size, size_config["normal"])

        # ========================================================================
        # Border radius
        # ========================================================================
        if rounded:
            border_radius = "24px"
        elif size == "tiny":
            border_radius = "3px"
        elif size == "small":
            border_radius = "4px"
        elif size == "large":
            border_radius = "10px"
        elif size == "xl":
            border_radius = "12px"
        else:
            border_radius = f"{self._border_radius.value}px"

        # ========================================================================
        # Glass effect (with native Qt approximation)
        # ========================================================================
        glass_style = ""
        if glass and self._glass_level != GlassLevel.NONE:
            glass_params = GlassmorphismSystem.get_glass_params(
                self._glass_level,
                (255, 255, 255, 220) if not self.is_dark else (30, 30, 50, 200)
            )
            r, g, b, bg_a = glass_params.bg_color
            br, bg_b, bb, border_a = glass_params.border_color
            glass_style = f"""
                background-color: rgba({r}, {g}, {b}, {bg_a});
                border: {glass_params.border_width}px solid rgba({br}, {bg_b}, {bb}, {border_a});
            """
            # Override default border if glass is enabled
            if variant not in ("outline",):
                variant_config["border"] = f"{glass_params.border_width}px solid rgba({br}, {bg_b}, {bb}, {border_a})"

        # ========================================================================
        # Width style
        # ========================================================================
        width_style = "width: 100%;" if full_width else ""

        # ========================================================================
        # Disabled state overrides
        # ========================================================================
        if disabled:
            variant_config["bg"] = variant_config["bg_disabled"]
            variant_config["text"] = variant_config["text_disabled"]

        # ========================================================================
        # Build the stylesheet
        # ========================================================================
        style = f"""
            QPushButton {{
                /* Layout */
                padding: {size_data['padding']};
                min-width: {size_data['min_width']};
                min-height: {size_data['min_height']};
                {width_style}

                /* Colors */
                background-color: {variant_config['bg']};
                color: {variant_config['text']};

                /* Border */
                border: {variant_config['border']};
                border-radius: {border_radius};

                /* Typography */
                font-family: '{fc.family_fa}';
                font-size: {size_data['font_size']}px;
                font-weight: 600;

                /* Spacing */
                margin: 2px;

                /* Glass effect */
                {glass_style}
            }}

            QPushButton:hover {{
                background-color: {variant_config['bg_hover']};
                border: {variant_config['border_hover']};
            }}

            QPushButton:pressed {{
                background-color: {variant_config['bg_pressed']};
            }}

            QPushButton:disabled {{
                background-color: {variant_config['bg_disabled']};
                color: {variant_config['text_disabled']};
                border: {variant_config['border']};
            }}

            QPushButton:focus {{
                border: {variant_config['border_focus']};
                outline: none;
            }}

            QPushButton:focus-visible {{
                border: 2px solid {p.border_focus};
            }}
        """

        # Add link-specific underline
        if variant == "link":
            style += f"""
            QPushButton {{
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {p.text_link_hover};
            }}
            """

        # Cache and return
        self._style_cache.set(cache_key, style)
        return style

    def get_input_style(self, size: str = "normal", variant: str = "default",
                        glass: bool = False) -> str:
        p = self._palette
        font_size = {"small": "12px", "normal": "14px", "large": "16px"}.get(size, "14px")
        glass_style = GlassmorphismSystem.get_glass_style_sheet(
            self._glass_level, (255, 255, 255, 220) if not self.is_dark else (30, 30, 50, 200)
        ) if glass else ""

        error_style = ""
        if variant == "error":
            error_style = f"border-color: {p.border_error};"

        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {p.surface};
                color: {p.text_primary};
                border: 2px solid {p.border};
                border-radius: 8px;
                padding: 10px 14px;
                font-family: '{self._font_config.family_fa}';
                font-size: {font_size};
                selection-background-color: {p.primary_light if hasattr(p, 'primary_light') else p.primary};
                selection-color: {p.text_on_primary};
                {error_style}
                {glass_style}
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {p.border_focus};
            }}
            QLineEdit:hover {{ border-color: {p.border_hover}; }}
            QLineEdit:disabled {{ background-color: {p.background_alt}; color: {p.text_disabled}; }}
            QLineEdit::placeholder {{ color: {p.text_tertiary}; font-style: italic; }}
            QLineEdit:read-only {{ background-color: {p.background_alt}; }}
        """

    def get_label_style(self, variant: str = "normal") -> str:
        p = self._palette
        variants = {
            "normal": f"color: {p.text_primary};",
            "secondary": f"color: {p.text_secondary};",
            "tertiary": f"color: {p.text_tertiary};",
            "disabled": f"color: {p.text_disabled};",
            "title": f"color: {p.text_primary}; font-size: {self._font_config.size_title}px; font-weight: bold;",
            "hero": f"color: {p.primary}; font-size: {self._font_config.size_hero}px; font-weight: bold;",
            "display": f"color: {p.primary}; font-size: {self._font_config.size_display}px; font-weight: 300;",
            "link": f"color: {p.text_link}; text-decoration: underline;",
            "error": f"color: {p.error};",
            "success": f"color: {p.success};",
            "warning": f"color: {p.warning};",
            "code": f"color: {p.text_primary}; font-family: '{self._font_config.family_mono}'; background-color: {p.background_alt}; padding: 4px 8px; border-radius: 4px;",
        }
        base = variants.get(variant, variants["normal"])
        return f"""QLabel {{ {base} font-family: '{self._font_config.family_fa}'; padding: 2px; }}"""

    def get_frame_style(self, variant: str = "default", glass: bool = False) -> str:
        p = self._palette
        radius = self._border_radius.value
        glass_style = GlassmorphismSystem.get_glass_style_sheet(
            self._glass_level if glass else GlassLevel.NONE,
            (255, 255, 255, 220) if not self.is_dark else (30, 30, 50, 200)
        ) if glass else ""

        if variant == "card":
            return f"""QFrame {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: {radius}px; padding: 16px; {glass_style} }}"""
        elif variant == "elevated":
            return f"""QFrame {{ background-color: {p.background_elevated}; border: 1px solid {p.border}; border-radius: {radius}px; padding: 24px; }}"""
        elif variant == "flat":
            return f"""QFrame {{ background-color: {p.background_alt}; border: none; border-radius: {radius}px; padding: 12px; }}"""
        elif variant == "bordered":
            return f"""QFrame {{ background-color: transparent; border: 2px solid {p.border}; border-radius: {radius}px; padding: 12px; }}"""
        elif variant == "highlight":
            return f"""QFrame {{ background-color: {p.surface_selected}; border: 1px solid {p.primary}; border-radius: {radius}px; padding: 16px; }}"""
        return f"""QFrame {{ background-color: transparent; border: none; }}"""

    def get_scroll_area_style(self) -> str:
        p = self._palette
        return f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ background-color: {p.background_alt}; width: 8px; border-radius: 4px; margin: 0; }}
            QScrollBar::handle:vertical {{ background-color: {p.text_tertiary}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background-color: {p.text_secondary}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            QScrollBar:horizontal {{ background-color: {p.background_alt}; height: 8px; border-radius: 4px; }}
            QScrollBar::handle:horizontal {{ background-color: {p.text_tertiary}; border-radius: 4px; min-width: 30px; }}
            QScrollBar::handle:horizontal:hover {{ background-color: {p.text_secondary}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        """

    def get_tab_widget_style(self) -> str:
        p = self._palette
        return f"""
            QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 8px; background-color: {p.surface}; top: -1px; }}
            QTabWidget::tab-bar {{ alignment: left; }}
            QTabBar::tab {{ background-color: {p.background_alt}; color: {p.text_secondary}; padding: 10px 24px; margin: 2px 4px; border: none; border-radius: 6px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QTabBar::tab:selected {{ background-color: {p.surface}; color: {p.primary}; font-weight: bold; border-bottom: 3px solid {p.primary}; }}
            QTabBar::tab:hover:!selected {{ background-color: {p.surface_hover}; }}
            QTabBar::tab:disabled {{ color: {p.text_disabled}; }}
            QTabBar::close-button {{ image: none; }}
        """

    def get_list_widget_style(self) -> str:
        p = self._palette
        return f"""
            QListWidget {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 4px; outline: none; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; color: {p.text_primary}; }}
            QListWidget::item {{ padding: 10px 14px; border-radius: 4px; margin: 1px 0; }}
            QListWidget::item:selected {{ background-color: {p.surface_selected}; color: {p.text_primary}; }}
            QListWidget::item:hover:!selected {{ background-color: {p.surface_hover}; }}
            QListWidget::item:alternate {{ background-color: {p.background_alt}; }}
            QListWidget:focus {{ border-color: {p.border_focus}; }}
        """

    def get_menu_bar_style(self) -> str:
        p = self._palette
        return f"""
            QMenuBar {{ background-color: {p.surface}; color: {p.text_primary}; border-bottom: 1px solid {p.border}; padding: 4px 8px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QMenuBar::item {{ padding: 8px 16px; border-radius: 4px; margin: 2px; }}
            QMenuBar::item:selected {{ background-color: {p.surface_hover}; }}
            QMenuBar::item:pressed {{ background-color: {p.surface_pressed}; }}
            QMenu {{ background-color: {p.surface}; color: {p.text_primary}; border: 1px solid {p.border}; border-radius: 12px; padding: 8px; }}
            QMenu::item {{ padding: 10px 36px 10px 20px; border-radius: 6px; }}
            QMenu::item:selected {{ background-color: {p.surface_selected}; }}
            QMenu::item:disabled {{ color: {p.text_disabled}; }}
            QMenu::separator {{ height: 1px; background-color: {p.border_light}; margin: 6px 12px; }}
            QMenu::indicator {{ width: 16px; height: 16px; }}
        """

    def get_dialog_style(self, glass: bool = False) -> str:
        p = self._palette
        glass_style = GlassmorphismSystem.get_glass_style_sheet(
            self._glass_level if glass else GlassLevel.NONE
        )
        return f"""QDialog {{ background-color: {p.surface}; border-radius: 12px; {glass_style} font-family: '{self._font_config.family_fa}'; color: {p.text_primary}; }}"""

    def get_checkbox_style(self) -> str:
        p = self._palette
        return f"""
            QCheckBox {{ color: {p.text_primary}; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; spacing: 10px; padding: 4px 0; }}
            QCheckBox::indicator {{ width: 20px; height: 20px; border: 2px solid {p.border}; border-radius: 4px; background-color: {p.surface}; }}
            QCheckBox::indicator:unchecked:hover {{ border-color: {p.primary}; }}
            QCheckBox::indicator:checked {{ background-color: {p.primary}; border-color: {p.primary}; }}
            QCheckBox::indicator:disabled {{ background-color: {p.text_disabled}; border-color: {p.text_disabled}; }}
        """

    def get_radio_button_style(self) -> str:
        p = self._palette
        return f"""
            QRadioButton {{ color: {p.text_primary}; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; spacing: 10px; padding: 4px 0; }}
            QRadioButton::indicator {{ width: 20px; height: 20px; border: 2px solid {p.border}; border-radius: 10px; background-color: {p.surface}; }}
            QRadioButton::indicator:unchecked:hover {{ border-color: {p.primary}; }}
            QRadioButton::indicator:checked {{ background-color: {p.primary}; border-color: {p.primary}; }}
        """

    def get_tooltip_style(self) -> str:
        p = self._palette
        return f"""QToolTip {{ background-color: {p.text_primary}; color: {p.background}; border: none; border-radius: 8px; padding: 10px 16px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_tiny}px; }}"""

    def get_message_box_style(self) -> str:
        p = self._palette
        return f"""
            QMessageBox {{ background-color: {p.background}; font-family: '{self._font_config.family_fa}'; color: {p.text_primary}; }}
            QMessageBox QLabel {{ color: {p.text_primary}; font-size: {self._font_config.size_normal}px; }}
            QMessageBox QPushButton {{ background-color: {p.primary}; color: {p.text_on_primary}; border: none; border-radius: 6px; padding: 8px 24px; min-width: 100px; font-size: {self._font_config.size_normal}px; }}
            QMessageBox QPushButton:hover {{ background-color: {p.primary_dark}; }}
        """

    def get_combo_box_style(self) -> str:
        p = self._palette
        return f"""
            QComboBox {{ background-color: {p.surface}; color: {p.text_primary}; border: 2px solid {p.border}; border-radius: 8px; padding: 8px 14px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; min-width: 120px; }}
            QComboBox:hover {{ border-color: {p.border_hover}; }}
            QComboBox:focus {{ border-color: {p.border_focus}; }}
            QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border: none; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{ background-color: {p.surface}; color: {p.text_primary}; selection-background-color: {p.surface_selected}; border: 1px solid {p.border}; border-radius: 4px; padding: 4px; }}
            QComboBox::item {{ padding: 8px 16px; }}
            QComboBox::item:selected {{ background-color: {p.surface_selected}; }}
        """

    def get_spin_box_style(self) -> str:
        p = self._palette
        return f"""
            QSpinBox, QDoubleSpinBox {{ background-color: {p.surface}; color: {p.text_primary}; border: 2px solid {p.border}; border-radius: 8px; padding: 8px 12px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {p.border_hover}; }}
            QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {p.border_focus}; }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{ border: none; border-left: 1px solid {p.border}; border-bottom: 1px solid {p.border}; border-top-right-radius: 4px; }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{ border: none; border-left: 1px solid {p.border}; border-bottom-right-radius: 4px; }}
        """

    def get_slider_style(self) -> str:
        p = self._palette
        return f"""
            QSlider::groove:horizontal {{ background-color: {p.background_alt}; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background-color: {p.primary}; width: 20px; height: 20px; margin: -7px 0; border-radius: 10px; border: 2px solid {p.surface}; }}
            QSlider::handle:horizontal:hover {{ background-color: {p.primary_light}; }}
            QSlider::handle:horizontal:pressed {{ background-color: {p.primary_dark}; }}
            QSlider::sub-page:horizontal {{ background-color: {p.primary}; border-radius: 3px; }}
        """

    def get_progress_bar_style(self) -> str:
        p = self._palette
        return f"""
            QProgressBar {{ background-color: {p.background_alt}; border: none; border-radius: 8px; height: 8px; text-align: center; font-size: {self._font_config.size_tiny}px; color: {p.text_secondary}; }}
            QProgressBar::chunk {{ background-color: {p.primary}; border-radius: 8px; }}
        """

    def get_table_style(self) -> str:
        p = self._palette
        return f"""
            QTableWidget {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; gridline-color: {p.border_light}; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QTableWidget::item {{ padding: 10px 14px; border-bottom: 1px solid {p.border_light}; }}
            QTableWidget::item:selected {{ background-color: {p.surface_selected}; color: {p.text_primary}; }}
            QTableWidget::item:hover {{ background-color: {p.surface_hover}; }}
            QHeaderView::section {{ background-color: {p.background_alt}; color: {p.text_primary}; padding: 12px 14px; border: none; border-bottom: 2px solid {p.border}; font-weight: bold; }}
            QHeaderView::section:hover {{ background-color: {p.surface_hover}; }}
        """

    def get_tree_widget_style(self) -> str:
        p = self._palette
        return f"""
            QTreeWidget {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; color: {p.text_primary}; }}
            QTreeWidget::item {{ padding: 8px 4px; }}
            QTreeWidget::item:selected {{ background-color: {p.surface_selected}; }}
            QTreeWidget::item:hover {{ background-color: {p.surface_hover}; }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{ border-image: none; }}
        """

    def get_group_box_style(self) -> str:
        p = self._palette
        return f"""
            QGroupBox {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; margin-top: 24px; padding: 20px 16px 16px 16px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 4px 16px; background-color: {p.primary}; color: {p.text_on_primary}; border-radius: 6px; margin-left: 12px; }}
        """

    def get_splitter_style(self) -> str:
        p = self._palette
        return f"""
            QSplitter::handle {{ background-color: {p.border}; width: 2px; height: 2px; }}
            QSplitter::handle:hover {{ background-color: {p.primary}; }}
            QSplitter::handle:pressed {{ background-color: {p.primary_dark}; }}
        """

    def get_status_bar_style(self) -> str:
        p = self._palette
        return f"""
            QStatusBar {{ background-color: {p.surface}; color: {p.text_secondary}; border-top: 1px solid {p.border}; padding: 4px 12px; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_small}px; }}
            QStatusBar::item {{ border: none; }}
        """

    def get_dock_widget_style(self) -> str:
        p = self._palette
        return f"""
            QDockWidget {{ background-color: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; font-family: '{self._font_config.family_fa}'; }}
            QDockWidget::title {{ background-color: {p.background_alt}; padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
        """

    def get_global_stylesheet(self) -> str:
        p = self._palette
        return f"""
            QMainWindow {{ background-color: {p.background}; }}
            QWidget {{ color: {p.text_primary}; font-family: '{self._font_config.family_fa}'; font-size: {self._font_config.size_normal}px; }}
            QScrollBar:vertical {{ background-color: {p.background_alt}; width: 8px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background-color: {p.text_tertiary}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background-color: {p.text_secondary}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{ background-color: {p.text_primary}; color: {p.background}; border: none; border-radius: 8px; padding: 10px 16px; font-size: {self._font_config.size_tiny}px; }}
            *::selection {{ background-color: {p.surface_selected}; color: {p.text_primary}; }}
            QSplitter::handle {{ background-color: {p.border}; }}
        """

    def apply_to_application(self, app):
        app.setStyleSheet(self.get_global_stylesheet())
        app.setFont(self.get_app_font())
        logger.info("Global stylesheet applied")

    def invalidate_cache(self):
        self._style_cache.clear()
        logger.debug("Style cache invalidated")

    def get_spacing(self, spacing: Spacing) -> int:
        return spacing.value

    def get_system_info(self) -> dict:
        return {
            "os": self._system.get_windows_version_name(),
            "qt_version": self._qt_version.name,
            "theme": self._mode.name,
            "glass_level": self._glass_level.name,
            "shadow_elevation": self._shadow_elevation.name,
            "python": sys.version.split()[0],
            "dpi": f"{self._system.get_dpi_scale():.1f}x",
            "ram_gb": f"{self._system.get_system_memory_gb():.1f}",
            "cpu_cores": self._system.get_cpu_count(),
        }

    def export_theme_config(self, filepath: str = None) -> dict:
        """خروجی تنظیمات تم به صورت دیکشنری."""
        config = {
            "version": "4.0.0",
            "mode": self._mode.name,
            "glass_level": self._glass_level.name,
            "shadow_elevation": self._shadow_elevation.name,
            "border_radius": self._border_radius.name,
            "animation_duration": self._animation_duration.name,
        }
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Theme config exported to {filepath}")
        return config

    def import_theme_config(self, config: Union[dict, str]):
        """بارگذاری تنظیمات تم از دیکشنری یا فایل."""
        if isinstance(config, str):
            with open(config, 'r', encoding='utf-8') as f:
                config = json.load(f)

        if "mode" in config:
            self.set_mode(ThemeMode[config["mode"]])
        if "glass_level" in config:
            self.set_glass_level(GlassLevel[config["glass_level"]])
        if "shadow_elevation" in config:
            self.set_shadow_elevation(ShadowElevation[config["shadow_elevation"]])
        if "border_radius" in config:
            self.set_border_radius(BorderRadius[config["border_radius"]])
        logger.info("Theme config imported")


# ============================================================================
# Global Instance
# ============================================================================

theme = ThemeManager()
