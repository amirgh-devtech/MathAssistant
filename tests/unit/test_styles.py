# tests/unit/test_styles.py
"""
Unit tests for Style Sheet Builders
"""

import pytest
from MathAssistant.ui.styles import ThemeManager, ThemeMode


class TestButtonStyles:
    """تست get_button_style"""

    @pytest.fixture
    def tm(self):
        return ThemeManager()

    def test_all_variants_return_string(self, tm, expected_button_variants):
        """همه variantها باید string برگردونن"""
        for variant in expected_button_variants:
            style = tm.get_button_style(variant)
            assert isinstance(style, str)
            assert len(style) > 0

    def test_all_sizes_return_string(self, tm, expected_button_sizes):
        """همه سایزها باید string برگردونن"""
        for size in expected_button_sizes:
            style = tm.get_button_style("primary", size)
            assert isinstance(style, str)
            assert len(style) > 0

    def test_primary_button_contains_colors(self, tm):
        style = tm.get_button_style("primary")
        assert "QPushButton" in style
        assert "background-color" in style

    def test_outline_button_has_border(self, tm):
        style = tm.get_button_style("outline")
        assert "border" in style
        assert "solid" in style

    def test_link_button_has_underline(self, tm):
        style = tm.get_button_style("link")
        assert "text-decoration" in style.lower()

    def test_full_width_button(self, tm):
        style = tm.get_button_style("primary", full_width=True)
        assert "width: 100%" in style

    def test_rounded_button(self, tm):
        style = tm.get_button_style("primary", rounded=True)
        assert "border-radius: 24px" in style

    def test_disabled_button(self, tm):
        style = tm.get_button_style("primary", disabled=True)
        assert "QPushButton:disabled" in style

    def test_custom_button(self, tm):
        style = tm.get_button_style("custom", custom_bg="#FF5733", custom_text_color="#FFFFFF")
        assert "#FF5733" in style
        assert "#FFFFFF" in style

    def test_caching_works(self, tm):
        style1 = tm.get_button_style("primary", "large", True, False, False, False)
        style2 = tm.get_button_style("primary", "large", True, False, False, False)
        assert style1 is style2  # از کش


class TestInputStyles:
    """تست get_input_style"""

    @pytest.fixture
    def tm(self):
        return ThemeManager()

    def test_default_input(self, tm):
        style = tm.get_input_style()
        assert "QLineEdit" in style
        assert "QTextEdit" in style

    def test_error_variant(self, tm):
        style = tm.get_input_style(variant="error")
        assert "border-color" in style

    def test_sizes(self, tm):
        for size in ["small", "normal", "large"]:
            style = tm.get_input_style(size=size)
            assert "font-size" in style


class TestLabelStyles:
    """تست get_label_style"""

    @pytest.fixture
    def tm(self):
        return ThemeManager()

    def test_all_variants(self, tm):
        variants = [
            "normal", "secondary", "tertiary", "disabled",
            "title", "hero", "display", "link",
            "error", "success", "warning", "code",
        ]
        for variant in variants:
            style = tm.get_label_style(variant)
            assert isinstance(style, str)
            assert "QLabel" in style


class TestFrameStyles:
    """تست get_frame_style"""

    @pytest.fixture
    def tm(self):
        return ThemeManager()

    def test_all_variants(self, tm):
        variants = ["default", "card", "elevated", "flat", "bordered", "highlight"]
        for variant in variants:
            style = tm.get_frame_style(variant)
            assert isinstance(style, str)
            assert "QFrame" in style


class TestGlobalStylesheet:
    """تست get_global_stylesheet"""

    @pytest.fixture
    def tm(self):
        return ThemeManager()

    def test_global_stylesheet_is_string(self, tm):
        style = tm.get_global_stylesheet()
        assert isinstance(style, str)
        assert len(style) > 100

    def test_contains_main_window(self, tm):
        style = tm.get_global_stylesheet()
        assert "QMainWindow" in style

    def test_changes_with_theme(self, tm):
        style_light = tm.get_global_stylesheet()
        tm.set_mode(ThemeMode.DARK)
        style_dark = tm.get_global_stylesheet()
        assert style_light != style_dark
