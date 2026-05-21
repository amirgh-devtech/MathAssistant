# tests/accessibility/test_wcag.py
"""
WCAG 2.1 Accessibility Tests
"""

import pytest
from MathAssistant.ui.styles import contrast_ratio

class TestWCAGContrast:
    """تست استانداردهای کنتراست WCAG 2.1"""

    def test_all_themes_text_contrast_aa(self, all_palettes):
        """متن اصلی باید حداقل AA باشه (4.5:1)"""
        ratio = contrast_ratio(
            all_palettes.text_primary,
            all_palettes.background
        )
        assert ratio >= 4.5, \
            f"{all_palettes}: text/background = {ratio:.1f}:1"

    def test_all_themes_button_text_contrast(self, all_palettes):
        """متن روی دکمه باید خوانا باشه"""
        ratio = contrast_ratio(
            all_palettes.text_on_primary,
            all_palettes.primary
        )
        assert ratio >= 3.0, \
            f"{all_palettes}: button text = {ratio:.1f}:1"

    def test_borders_have_minimum_contrast(self, all_palettes):
        """حاشیه‌ها باید حداقل کنتراست رو داشته باشن"""
        ratio = contrast_ratio(
            all_palettes.border,
            all_palettes.background
        )
        assert ratio >= 2.5, \
            f"{all_palettes}: border/background = {ratio:.1f}:1"
