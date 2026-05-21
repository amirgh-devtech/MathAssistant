# tests/unit/test_colors.py
"""
Unit tests for ColorPalette and color utility functions
"""

import pytest
import re
from MathAssistant.ui.styles import (
    ColorPalette,
    hex_to_rgba,
    hex_to_qcolor,
    lighten_color,
    darken_color,
    mix_colors,
    luminosity,
    contrast_ratio,
    is_accessible,
    HEX_COLOR_PATTERN,
    RGBA_PATTERN,
)


class TestHexToRgba:
    """تست تبدیل hex به rgba"""

    def test_six_digit_hex(self):
        """تست hex شش رقمی"""
        assert hex_to_rgba("#FF0000", 1.0) == "rgba(255, 0, 0, 255)"
        assert hex_to_rgba("#00FF00", 0.5) == "rgba(0, 255, 0, 128)"
        assert hex_to_rgba("#0000FF", 0.0) == "rgba(0, 0, 255, 0)"

    def test_three_digit_hex(self):
        """تست hex سه رقمی"""
        assert hex_to_rgba("#F00", 1.0) == "rgba(255, 0, 0, 255)"
        assert hex_to_rgba("#0F0", 1.0) == "rgba(0, 255, 0, 255)"

    def test_hex_without_hash(self):
        """تست hex بدون #"""
        assert hex_to_rgba("FF0000", 1.0) == "rgba(255, 0, 0, 255)"

    def test_eight_digit_hex(self):
        """تست hex هشت رقمی (با alpha)"""
        result = hex_to_rgba("#FF000080", 1.0)
        assert "rgba(255, 0, 0, 128)" == result


class TestColorValidation:
    """تست اعتبارسنجی رنگ‌ها"""

    def test_valid_hex_colors(self, sample_hex_colors):
        """همه hex های معتبر باید قبول بشن"""
        for color in sample_hex_colors:
            assert HEX_COLOR_PATTERN.match(color), f"Should be valid: {color}"

    def test_invalid_hex_colors(self):
        """hex های نامعتبر باید reject بشن"""
        invalid = ["#GGG", "#12345", "invalid", "", "#1234567"]
        for color in invalid:
            assert not HEX_COLOR_PATTERN.match(color), f"Should be invalid: {color}"

    def test_valid_rgba(self, sample_rgba_colors):
        """rgba های معتبر باید قبول بشن"""
        for color in sample_rgba_colors:
            assert RGBA_PATTERN.match(color), f"Should be valid: {color}"

    def test_palette_creation_validates_colors(self):
        """ایجاد پالت باید رنگ‌ها رو اعتبارسنجی کنه"""
        palette = ColorPalette(
            primary="#2563EB",
            primary_light="#60A5FA",
            primary_dark="#1D4ED8",
            secondary="#7C3AED",
            secondary_light="#A78BFA",
            secondary_dark="#6D28D9",
        )
        assert palette.primary == "#2563EB"

    def test_palette_auto_calculates_alpha_variants(self):
        """پالت باید alpha variants رو خودکار محاسبه کنه"""
        palette = ColorPalette(
            primary="#2563EB",
            primary_light="#60A5FA",
            primary_dark="#1D4ED8",
            secondary="#7C3AED",
            secondary_light="#A78BFA",
            secondary_dark="#6D28D9",
        )
        assert palette.primary_alpha_10.startswith("rgba")
        assert palette.primary_alpha_20.startswith("rgba")
        assert palette.primary_alpha_30.startswith("rgba")

    def test_palette_is_frozen(self):
        """پالت باید immutable باشه"""
        palette = ColorPalette(
            primary="#2563EB",
            primary_light="#60A5FA",
            primary_dark="#1D4ED8",
            secondary="#7C3AED",
            secondary_light="#A78BFA",
            secondary_dark="#6D28D9",
        )
        with pytest.raises(Exception):
            palette.primary = "#FF0000"


class TestLightenDarken:
    """تست روشن/تیره کردن رنگ"""

    def test_lighten(self):
        """تست lighten_color"""
        assert lighten_color("#808080", 0.5) != "#808080"
        # سفید نباید از 255 بیشتر بشه
        result = lighten_color("#FFFFFF", 0.5)
        assert all(int(result[i:i+2], 16) <= 255 for i in (1, 3, 5))

    def test_darken(self):
        """تست darken_color"""
        assert darken_color("#808080", 0.5) != "#808080"
        # مشکی نباید از 0 کمتر بشه
        result = darken_color("#000000", 0.5)
        assert result == "#000000"

    def test_mix_colors(self):
        """تست mix_colors"""
        mixed = mix_colors("#FF0000", "#0000FF", 0.5)
        assert mixed == "#800080"  # بنفش


class TestAccessibility:
    """تست توابع accessibility"""

    def test_contrast_ratio_black_white(self):
        """کنتراست سیاه و سفید باید 21:1 باشه"""
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert 20 <= ratio <= 22  # حدود 21

    def test_contrast_ratio_same_color(self):
        """کنتراست دو رنگ یکسان باید 1:1 باشه"""
        ratio = contrast_ratio("#808080", "#808080")
        assert 0.9 <= ratio <= 1.1

    def test_is_accessible_aa(self):
        """تست سطح AA"""
        assert is_accessible("#000000", "#FFFFFF", "AA")
        assert not is_accessible("#CCCCCC", "#FFFFFF", "AA")

    def test_is_accessible_aaa(self):
        """تست سطح AAA"""
        assert is_accessible("#000000", "#FFFFFF", "AAA")  # 21:1 ✓
        # رنگ تیره‌تر برای AAA واقعی
        assert not is_accessible("#767676", "#FFFFFF", "AAA")  # حدود 4.5:1
        # یا
        assert is_accessible("#1A1A1A", "#FFFFFF", "AAA")  # حدود 12:1
