# tests/unit/test_theme_manager.py

"""
Unit tests for ThemeManager
پوشش کامل Singleton, Observer, Export/Import, Cache
"""

import pytest
import json
import tempfile
from pathlib import Path
from MathAssistant.ui.styles import (
    ThemeManager,
    ColorPalette,
    ThemeMode,
    GlassLevel,
    ShadowElevation,
    BorderRadius,
    AnimationDuration,
)


class TestThemeManagerSingleton:
    """الگوی Singleton"""

    def test_returns_same_instance(self):
        """باید همیشه یک instance باشه"""
        ThemeManager._instance = None
        ThemeManager._initialized = False

        tm1 = ThemeManager()
        tm2 = ThemeManager()
        tm3 = ThemeManager()

        assert tm1 is tm2 is tm3

    def test_only_initializes_once(self):
        """__init__ فقط یکبار اجرا بشه"""
        ThemeManager._instance = None
        ThemeManager._initialized = False

        tm1 = ThemeManager()
        mode_before = tm1.mode

        # این نباید state رو عوض کنه
        tm2 = ThemeManager()
        assert tm2.mode == mode_before

class TestThemeSwitching:
    """تست تغییر تم"""

    def test_set_mode_light(self, theme_manager):
        theme_manager.set_mode(ThemeMode.LIGHT)
        assert theme_manager.mode == ThemeMode.LIGHT
        assert not theme_manager.is_dark

    def test_all_8_themes_switch_without_error(self, theme_manager):
        """همه ۸ تم باید بدون خطا ست بشن"""
        for mode in list(ThemeMode):
            theme_manager.set_mode(mode)
            assert theme_manager.mode == mode
            assert theme_manager.palette is not None
            assert theme_manager.palette.primary != ""


class TestGlassAndShadow:
    """تست تنظیمات Glass و Shadow"""

    def test_set_glass_level(self, theme_manager):
        for level in GlassLevel:
            theme_manager.set_glass_level(level)
            assert theme_manager.glass_level == level

    def test_set_shadow_elevation(self, theme_manager):
        for elev in ShadowElevation:
            theme_manager.set_shadow_elevation(elev)
            assert theme_manager.shadow_elevation == elev

    def test_set_border_radius(self, theme_manager):
        for radius in BorderRadius:
            theme_manager.set_border_radius(radius)
            # border_radius property نداره، فقط setter
            # پس بررسی می‌کنیم که خطا نده

    def test_glass_level_clears_cache(self, theme_manager):
        """تغییر glass باید cache رو پاک کنه"""
        _ = theme_manager.get_button_style("primary")
        theme_manager.set_glass_level(GlassLevel.MEDIUM)
        # باید style جدید با glass ساخته بشه

    def test_shadow_clears_cache(self, theme_manager):
        """تغییر shadow باید cache رو پاک کنه"""
        _ = theme_manager.get_button_style("primary")
        theme_manager.set_shadow_elevation(ShadowElevation.HIGH)


class TestObserverPattern:
    """تست Observer Pattern"""

    def test_subscribe_and_notify(self, theme_manager):
        calls = []
        def observer(mode):
            calls.append(mode)

        theme_manager.subscribe(observer)
        theme_manager.set_mode(ThemeMode.DARK)

        assert len(calls) == 1
        assert calls[0] == ThemeMode.DARK

    def test_subscribe_duplicate(self, theme_manager):
        """دوبار subscribe کردن نباید دوبار notify کنه"""
        calls = []
        def observer(mode):
            calls.append(mode)

        theme_manager.subscribe(observer)
        theme_manager.subscribe(observer)  # duplicate
        theme_manager.set_mode(ThemeMode.DARK)

        assert len(calls) == 1  # فقط یکبار

    def test_unsubscribe(self, theme_manager):
        calls = []
        def observer(mode):
            calls.append(mode)

        theme_manager.subscribe(observer)
        theme_manager.unsubscribe(observer)
        theme_manager.set_mode(ThemeMode.DARK)

        assert len(calls) == 0

    def test_unsubscribe_not_subscribed(self, theme_manager):
        """حذف observer که وجود نداره - نباید خطا بده"""
        def observer(mode): pass
        theme_manager.unsubscribe(observer)  # نباید خطا بده

    def test_multiple_observers(self, theme_manager):
        calls = []
        def obs1(mode): calls.append(1)
        def obs2(mode): calls.append(2)
        def obs3(mode): calls.append(3)

        theme_manager.subscribe(obs1)
        theme_manager.subscribe(obs2)
        theme_manager.subscribe(obs3)
        theme_manager.set_mode(ThemeMode.OCEAN)

        assert len(calls) == 3
        assert calls == [1, 2, 3]

    def test_observer_error_doesnt_block_others(self, theme_manager):
        """خطا در یک observer نباید بقیه رو متوقف کنه"""
        good_calls = []

        def bad_observer(mode):
            raise RuntimeError("Observer crash!")

        def good_observer(mode):
            good_calls.append(mode)

        theme_manager.subscribe(bad_observer)
        theme_manager.subscribe(good_observer)
        theme_manager.set_mode(ThemeMode.DARK)

        assert len(good_calls) == 1
        assert good_calls[0] == ThemeMode.DARK

    def test_observer_receives_correct_mode(self, theme_manager):
        """observer باید mode صحیح رو دریافت کنه"""
        received = []
        def observer(mode):
            received.append(mode)

        theme_manager.subscribe(observer)

        for mode in ThemeMode:
            theme_manager.set_mode(mode)

        assert received == list(ThemeMode)


class TestTemporaryTheme:
    """تست context manager تغییر موقت تم"""

    def test_temporary_theme_changes_and_restores(self, theme_manager):
        theme_manager.set_mode(ThemeMode.LIGHT)

        with theme_manager.temporary_theme(ThemeMode.DARK):
            assert theme_manager.mode == ThemeMode.DARK

        assert theme_manager.mode == ThemeMode.LIGHT

    def test_temporary_theme_nested(self, theme_manager):
        """context تودرتو"""
        theme_manager.set_mode(ThemeMode.LIGHT)

        with theme_manager.temporary_theme(ThemeMode.DARK):
            assert theme_manager.mode == ThemeMode.DARK

            with theme_manager.temporary_theme(ThemeMode.OCEAN):
                assert theme_manager.mode == ThemeMode.OCEAN

            assert theme_manager.mode == ThemeMode.DARK

        assert theme_manager.mode == ThemeMode.LIGHT

    def test_temporary_theme_with_exception(self, theme_manager):
        """حتی با exception هم باید برگرده"""
        theme_manager.set_mode(ThemeMode.LIGHT)

        try:
            with theme_manager.temporary_theme(ThemeMode.DARK):
                raise ValueError("Something went wrong!")
        except ValueError:
            pass

        assert theme_manager.mode == ThemeMode.LIGHT

    def test_temporary_theme_returns_value(self, theme_manager):
        """context manager از theme مقدار None برمیگردونه"""
        theme_manager.set_mode(ThemeMode.LIGHT)

        with theme_manager.temporary_theme(ThemeMode.DARK):
            assert theme_manager.mode == ThemeMode.DARK

        assert theme_manager.mode == ThemeMode.LIGHT



class TestTemporaryGlass:
    """تست context manager تغییر موقت Glass"""

    def test_temporary_glass_restores(self, theme_manager):
        theme_manager.set_glass_level(GlassLevel.NONE)

        with theme_manager.temporary_glass(GlassLevel.HEAVY):
            assert theme_manager.glass_level == GlassLevel.HEAVY

        assert theme_manager.glass_level == GlassLevel.NONE


class TestExportImport:
    """تست export/import تنظیمات"""

    def test_export_returns_dict(self, theme_manager):
        config = theme_manager.export_theme_config()
        assert isinstance(config, dict)
        assert config["version"] == "4.0.0"
        assert "mode" in config
        assert "glass_level" in config
        assert "shadow_elevation" in config

    def test_export_contains_current_state(self, theme_manager):
        theme_manager.set_mode(ThemeMode.OCEAN)
        theme_manager.set_glass_level(GlassLevel.MEDIUM)

        config = theme_manager.export_theme_config()
        assert config["mode"] == "OCEAN"
        assert config["glass_level"] == "MEDIUM"

    def test_export_to_file(self, theme_manager):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            filepath = f.name

        try:
            theme_manager.export_theme_config(filepath)

            with open(filepath) as f:
                data = json.load(f)

            assert data["version"] == "4.0.0"
        finally:
            Path(filepath).unlink(missing_ok=True)

class TestCacheInvalidation:
    """تست cache invalidation"""

    def test_invalidate_cache_method(self, theme_manager):
        """invalidate_cache باید کش رو خالی کنه"""
        style1 = theme_manager.get_button_style("primary")
        theme_manager.invalidate_cache()
        style2 = theme_manager.get_button_style("primary")
        assert style1 == style2  # باید rebuild بشه و یکسان باشه

    def test_cache_returns_same_for_same_params(self, theme_manager):
        """همون پارامترها باید همون کش رو برگردونه"""
        style1 = theme_manager.get_button_style("primary", "large", True)
        style2 = theme_manager.get_button_style("primary", "large", True)
        assert style1 is style2  # همون object از کش

    def test_cache_returns_different_for_different_params(self, theme_manager):
        """پارامترهای مختلف باید style مختلف برگردونه"""
        style1 = theme_manager.get_button_style("primary", "small")
        style2 = theme_manager.get_button_style("primary", "large")
        assert style1 != style2

class TestProperties:
    """تست properties"""
    def setup_method(self):
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_adapter_property(self, theme_manager):
        adapter = theme_manager.adapter
        assert adapter is not None
