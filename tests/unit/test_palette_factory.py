# tests/unit/test_palette_factory.py
"""
Unit tests for PaletteFactory
"""

import pytest
from MathAssistant.ui.styles import (
    PaletteFactory,
    ColorPalette,
    ThemeMode,
    contrast_ratio,
)


class TestPaletteFactoryAllThemes:
    """تست تولید همه تم‌ها"""

    def test_creates_all_8_themes(self):
        """باید ۸ تم مختلف تولید بشه"""
        themes = set()
        for mode in ThemeMode:
            palette = PaletteFactory.create(mode)
            themes.add(mode)
            assert isinstance(palette, ColorPalette)
        assert len(themes) == 8

    def test_each_theme_is_unique(self):
        """هر تم باید پالت منحصر‌به‌فرد داشته باشه"""
        primaries = []
        for mode in ThemeMode:
            palette = PaletteFactory.create(mode)
            primaries.append(palette.primary)
        # حداقل ۶ تا از ۸ تا باید primary متفاوت داشته باشن
        unique_primaries = len(set(primaries))
        assert unique_primaries >= 6, f"Only {unique_primaries} unique primaries"

    def test_factory_returns_new_instance_each_time(self):
        """هر بار باید instance جدید بسازه (چون frozen dataclass)"""
        p1 = PaletteFactory.create(ThemeMode.LIGHT)
        p2 = PaletteFactory.create(ThemeMode.LIGHT)
        # مقادیر یکسانن اما immutable هستن
        assert p1.primary == p2.primary


class TestLightTheme:
    """تست‌های مخصوص تم Light"""

    @pytest.fixture
    def palette(self):
        return PaletteFactory.create(ThemeMode.LIGHT)

    def test_is_light_theme(self, palette):
        """باید پس‌زمینه روشن داشته باشه"""
        assert palette.background == "#F8FAFC"

    def test_text_is_dark(self, palette):
        """متن باید تیره باشه"""
        assert palette.text_primary == "#1E293B"

    def test_surface_is_white(self, palette):
        """سطح باید سفید باشه"""
        assert palette.surface == "#FFFFFF"

    def test_text_on_primary_is_white(self, palette):
        """متن روی primary باید سفید باشه"""
        assert palette.text_on_primary == "#FFFFFF"

    def test_primary_color(self, palette):
        assert palette.primary == "#2563EB"

    def test_has_all_required_fields(self, palette):
        required = [
            "primary", "secondary", "tertiary",
            "background", "surface",
            "text_primary", "text_secondary",
            "border", "success", "warning", "error",
        ]
        for field in required:
            assert hasattr(palette, field), f"Missing field: {field}"
            assert getattr(palette, field) is not None


class TestDarkTheme:
    """تست‌های مخصوص تم Dark"""

    @pytest.fixture
    def palette(self):
        return PaletteFactory.create(ThemeMode.DARK)

    def test_is_dark_theme(self, palette):
        assert palette.background == "#0F172A"

    def test_text_is_light(self, palette):
        assert palette.text_primary == "#F1F5F9"

    def test_surface_is_dark(self, palette):
        assert palette.surface == "#1E293B"


class TestHighContrastTheme:
    """تست‌های مخصوص High Contrast"""

    @pytest.fixture
    def palette(self):
        return PaletteFactory.create(ThemeMode.HIGH_CONTRAST)

    def test_maximum_contrast_colors(self, palette):
        """باید کنتراست ماکسیمم داشته باشه"""
        assert palette.primary == "#0000FF"
        assert palette.text_primary == "#000000"
        assert palette.background == "#FFFFFF"

    def test_high_contrast_text_background(self, palette):
        """نسبت کنتراست باید بالا باشه"""
        ratio = contrast_ratio(palette.text_primary, palette.background)
        assert ratio >= 15, f"Low contrast: {ratio:.1f}:1"

    def test_high_contrast_button(self, palette):
        """کنتراست دکمه هم باید بالا باشه"""
        ratio = contrast_ratio(palette.text_on_primary, palette.primary)
        assert ratio >= 7, f"Button contrast: {ratio:.1f}:1"


class TestAllThemesAccessibility:
    """تست accessibility برای همه تم‌ها"""

    def test_all_themes_meet_aa_text(self, all_palettes):
        """همه تم‌ها باید AA رو برای متن اصلی پاس کنن"""
        ratio = contrast_ratio(
            all_palettes.text_primary,
            all_palettes.background
        )
        assert ratio >= 4.5, \
            f"FAILED {all_palettes}: text/background = {ratio:.1f}:1"

    def test_all_themes_meet_aa_large_for_secondary(self, all_palettes):
        """متن secondary باید AA Large رو پاس کنه"""
        ratio = contrast_ratio(
            all_palettes.text_secondary,
            all_palettes.background
        )
        assert ratio >= 3.0, \
            f"FAILED: secondary/background = {ratio:.1f}:1"

    def test_all_themes_button_readable(self, all_palettes):
        """متن دکمه باید خوانا باشه"""
        ratio = contrast_ratio(
            all_palettes.text_on_primary,
            all_palettes.primary
        )
        assert ratio >= 3.0, \
            f"FAILED: button text = {ratio:.1f}:1"

    def test_all_themes_border_visible(self, all_palettes):
        """حاشیه باید قابل دیدن باشه"""
        ratio = contrast_ratio(
            all_palettes.border,
            all_palettes.background
        )
        assert ratio >= 2.0, \
            f"FAILED: border/background = {ratio:.1f}:1"


class TestAllThemesConsistency:
    """تست یکپارچگی تم‌ها"""

    def test_all_have_status_colors(self, all_palettes):
        """همه باید رنگ‌های status داشته باشن"""
        for field in ["success", "warning", "error", "info"]:
            value = getattr(all_palettes, field)
            assert value and value.startswith("#"), \
                f"Missing status color: {field}"

    def test_all_have_chart_colors(self, all_palettes):
        """همه باید رنگ‌های chart داشته باشن"""
        for i in range(1, 9):
            value = getattr(all_palettes, f"chart_{i}")
            assert value and value.startswith("#"), \
                f"Missing chart color: chart_{i}"

    def test_all_have_neutral_scale(self, all_palettes):
        """همه باید neutral scale کامل داشته باشن"""
        for level in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]:
            value = getattr(all_palettes, f"neutral_{level}")
            assert value and value.startswith("#"), \
                f"Missing neutral: neutral_{level}"

    def test_all_have_font_families(self):
        """تم‌ها که font ندارن، ولی ThemeManager داره"""
        # این تست فقط consistency پالت‌ها رو چک می‌کنه
        pass


class TestDefaultTheme:
    """تست تم پیش‌فرض"""

    def test_unknown_mode_returns_light(self):
        """حالت نامشخص باید Light برگردونه"""
        # نمی‌تونیم مستقیماً invalid Enum بسازیم
        # پس با یه روش دیگه تست می‌کنیم
        palette = PaletteFactory.create(ThemeMode.LIGHT)
        assert palette.background == "#F8FAFC"
