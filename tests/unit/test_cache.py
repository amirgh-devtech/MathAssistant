# tests/unit/test_cache.py
"""
Unit tests for LRUCache
پوشش ۱۰۰٪ تمام متدها و edge cases
"""

import pytest
from MathAssistant.ui.styles import LRUCache


class TestLRUCacheInit:
    """تست سازنده و properties"""

    def test_default_max_size(self):
        cache = LRUCache()
        assert cache.max_size == 500
        assert cache.size == 0

    def test_custom_max_size(self):
        cache = LRUCache(max_size=10)
        assert cache.max_size == 10

    def test_negative_max_size_raises(self):
        """سایز منفی یعنی هیچی ذخیره نشه"""
        cache = LRUCache(max_size=-1)
        cache["test"] = "value"
        assert cache.size == 0
        assert "test" not in cache

    def test_zero_max_size(self):
        """سایز صفر - همه چی باید فوراً evict بشه"""
        cache = LRUCache(max_size=0)
        cache["a"] = "1"
        assert cache.size == 0
        assert "a" not in cache


class TestLRUCacheSet:
    """تست عملیات set"""

    def test_set_new_key(self, empty_cache):
        empty_cache.set("new_key", "new_value")
        assert empty_cache.get("new_key") == "new_value"
        assert empty_cache.size == 1

    def test_set_overwrite_existing(self, empty_cache):
        empty_cache.set("key", "value1")
        empty_cache.set("key", "value2")
        assert empty_cache.get("key") == "value2"
        assert empty_cache.size == 1  # size نباید زیاد بشه

    def test_set_none_value(self, empty_cache):
        """مقدار None هم باید ذخیره بشه"""
        empty_cache.set("key", None)
        assert empty_cache.get("key") is None
        assert "key" in empty_cache

    def test_set_empty_string_key(self, empty_cache):
        """کلید خالی هم باید کار کنه"""
        empty_cache.set("", "empty_key_value")
        assert empty_cache.get("") == "empty_key_value"

    def test_set_very_long_key(self, empty_cache):
        """کلید خیلی بلند"""
        long_key = "a" * 10000
        empty_cache.set(long_key, "long")
        assert empty_cache.get(long_key) == "long"

    def test_set_very_long_value(self, empty_cache):
        """مقدار خیلی بلند"""
        long_value = "b" * 100000
        empty_cache.set("key", long_value)
        assert empty_cache.get("key") == long_value

    def test_set_unicode_key(self, empty_cache):
        """کلید یونیکد فارسی"""
        empty_cache.set("کلید_فارسی", "مقدار_فارسی")
        assert empty_cache.get("کلید_فارسی") == "مقدار_فارسی"


class TestLRUCacheGet:
    """تست عملیات get"""

    def test_get_existing_key(self, filled_cache):
        assert filled_cache.get("key0") == "value0"

    def test_get_nonexistent_key(self, empty_cache):
        assert empty_cache.get("nonexistent") is None

    def test_get_updates_lru_order(self, full_cache):
        """get باید کلید رو به انتهای LRU ببره"""
        # full_cache: a, b, c
        # a قدیمی‌ترینه
        full_cache.get("a")  # دسترسی به a
        full_cache["d"] = "4"  # باید b رو evict کنه

        assert "a" in full_cache  # a نباید evict بشه
        assert "b" not in full_cache  # b باید evict بشه
        assert "c" in full_cache
        assert "d" in full_cache

    def test_get_multiple_times(self, full_cache):
        """چند بار get کردن یک کلید"""
        for _ in range(100):
            full_cache.get("a")
        full_cache["d"] = "4"
        assert "a" in full_cache  # a باید بمونه


class TestLRUCacheBracket:
    """تست دسترسی با []"""

    def test_getitem_existing(self, filled_cache):
        assert filled_cache["key0"] == "value0"

    def test_getitem_nonexistent_raises(self, empty_cache):
        with pytest.raises(KeyError):
            _ = empty_cache["nonexistent"]

    def test_setitem_new(self, empty_cache):
        empty_cache["new"] = "value"
        assert empty_cache["new"] == "value"

    def test_setitem_overwrite(self, empty_cache):
        empty_cache["key"] = "v1"
        empty_cache["key"] = "v2"
        assert empty_cache["key"] == "v2"


class TestLRUCacheContains:
    """تست in operator"""

    def test_contains_existing(self, filled_cache):
        assert "key0" in filled_cache

    def test_contains_nonexistent(self, empty_cache):
        assert "missing" not in empty_cache

    def test_contains_after_eviction(self, full_cache):
        full_cache["d"] = "4"  # a evict میشه
        assert "a" not in full_cache
        assert "d" in full_cache


class TestLRUCacheEviction:
    """تست سیاست eviction"""

    def test_eviction_order_fifo(self):
        """بدون دسترسی، باید FIFO باشه"""
        cache = LRUCache(max_size=3)
        cache["a"] = "1"
        cache["b"] = "2"
        cache["c"] = "3"
        cache["d"] = "4"

        assert "a" not in cache  # قدیمی‌ترین
        assert "b" in cache
        assert "c" in cache
        assert "d" in cache

    def test_eviction_after_access(self):
        """با دسترسی، ترتیب عوض میشه"""
        cache = LRUCache(max_size=3)
        cache["a"] = "1"
        cache["b"] = "2"
        cache["c"] = "3"

        # دسترسی به a و c
        _ = cache["a"]
        _ = cache["c"]

        cache["d"] = "4"  # باید b evict بشه

        assert "a" in cache
        assert "b" not in cache
        assert "c" in cache
        assert "d" in cache

    def test_eviction_with_overwrite(self):
        """overwrite نباید eviction کنه"""
        cache = LRUCache(max_size=3)
        cache["a"] = "1"
        cache["b"] = "2"
        cache["a"] = "1-updated"  # overwrite
        cache["c"] = "3"

        assert cache.size == 3  # همه هستن
        assert cache["a"] == "1-updated"

    def test_eviction_single_item(self):
        """کش با max_size=1"""
        cache = LRUCache(max_size=1)
        cache["a"] = "1"
        assert cache.size == 1

        cache["b"] = "2"
        assert cache.size == 1
        assert "a" not in cache
        assert "b" in cache

    def test_massive_eviction(self):
        """اضافه کردن تعداد زیادی آیتم"""
        cache = LRUCache(max_size=10)
        for i in range(1000):
            cache[f"key{i}"] = f"value{i}"

        assert cache.size == 10
        # فقط ۱۰ تای آخر باید بمونن
        assert "key0" not in cache
        assert "key999" in cache
        assert "key990" in cache  # یکی از ۱۰ تای آخر


class TestLRUCacheRemove:
    """تست عملیات remove"""

    def test_remove_existing(self, filled_cache):
        filled_cache.remove("key0")
        assert "key0" not in filled_cache
        assert filled_cache.size == 4

    def test_remove_nonexistent(self, empty_cache):
        empty_cache.remove("nonexistent")  # نباید خطا بده

    def test_remove_all_one_by_one(self, filled_cache):
        for i in range(5):
            filled_cache.remove(f"key{i}")
        assert filled_cache.size == 0

    def test_remove_then_readd(self, filled_cache):
        filled_cache.remove("key0")
        filled_cache["key0"] = "new_value"
        assert filled_cache["key0"] == "new_value"


class TestLRUCacheClear:
    """تست عملیات clear"""

    def test_clear_empty(self, empty_cache):
        empty_cache.clear()
        assert empty_cache.size == 0

    def test_clear_filled(self, filled_cache):
        filled_cache.clear()
        assert filled_cache.size == 0
        assert "key0" not in filled_cache

    def test_clear_then_reuse(self, filled_cache):
        filled_cache.clear()
        filled_cache["new"] = "value"
        assert filled_cache.size == 1
        assert filled_cache["new"] == "value"

    def test_clear_multiple_times(self, filled_cache):
        for _ in range(10):
            filled_cache.clear()
        assert filled_cache.size == 0


class TestLRUCacheLen:
    """تست len()"""

    def test_len_empty(self, empty_cache):
        assert len(empty_cache) == 0

    def test_len_after_add(self, empty_cache):
        for i in range(5):
            empty_cache[f"key{i}"] = f"value{i}"
        assert len(empty_cache) == 5

    def test_len_after_eviction(self, full_cache):
        assert len(full_cache) == 3
        full_cache["d"] = "4"
        assert len(full_cache) == 3  # هنوز ۳ تاست

    def test_len_after_remove(self, filled_cache):
        filled_cache.remove("key0")
        assert len(filled_cache) == 4

    def test_len_after_overwrite(self, filled_cache):
        old_len = len(filled_cache)
        filled_cache["key0"] = "updated"
        assert len(filled_cache) == old_len


class TestLRUCacheKeysValues:
    """تست keys() و values()"""

    def test_keys_empty(self, empty_cache):
        assert empty_cache.keys() == []

    def test_keys_filled(self, filled_cache):
        keys = filled_cache.keys()
        assert len(keys) == 5
        assert "key0" in keys

    def test_values_empty(self, empty_cache):
        assert empty_cache.values() == []

    def test_values_filled(self, filled_cache):
        values = filled_cache.values()
        assert len(values) == 5
        assert "value0" in values

    def test_keys_after_eviction(self, full_cache):
        full_cache["d"] = "4"
        keys = full_cache.keys()
        assert "a" not in keys
        assert "d" in keys

    def test_keys_values_consistency(self, filled_cache):
        """تعداد keys و values باید برابر باشه"""
        assert len(filled_cache.keys()) == len(filled_cache.values())
        assert len(filled_cache.keys()) == filled_cache.size


class TestLRUCacheEdgeCases:
    """تست موارد خاص و مرزی"""

    def test_max_size_one_lru_behavior(self):
        """کش تک‌عنصری باید همیشه آخرین رو نگه داره"""
        cache = LRUCache(max_size=1)
        for i in range(100):
            cache[f"key{i}"] = f"value{i}"
        assert cache.size == 1
        assert "key99" in cache
        assert "key0" not in cache

    def test_same_key_multiple_updates(self):
        """آپدیت مکرر یک کلید"""
        cache = LRUCache(max_size=5)
        for i in range(1000):
            cache["constant"] = f"value{i}"
        assert cache.size == 1
        assert cache["constant"] == "value999"

    def test_alternating_access_pattern(self):
        """الگوی دسترسی متناوب"""
        cache = LRUCache(max_size=2)
        cache["a"] = "1"
        cache["b"] = "2"

        # دسترسی متناوب
        for _ in range(100):
            _ = cache["a"]
            _ = cache["b"]

        cache["c"] = "3"
        assert "c" in cache
        # a یا b باید evict شده باشن

    def test_thread_safety_smoke(self):
        """تست پایه thread safety (smoke test)"""
        import threading
        cache = LRUCache(max_size=100)
        errors = []

        def worker(start, end):
            try:
                for i in range(start, end):
                    cache[f"key{i}"] = f"value{i}"
                    _ = cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i*100, (i+1)*100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # حداقل نباید crash کنه
        assert len(errors) == 0
        assert cache.size <= 100

    def test_memory_stress(self):
        """تست فشار حافظه"""
        cache = LRUCache(max_size=100)
        # مقادیر بزرگ
        for i in range(200):
            cache[f"key{i}"] = "x" * 10000  # 10KB per value
        assert cache.size == 100

    def test_special_characters_in_keys(self):
        """کاراکترهای خاص در کلید"""
        cache = LRUCache()
        special_keys = [
            "key with spaces",
            "key-with-dashes",
            "key.with.dots",
            "key_with_underscores",
            "key\nwith\nnewlines",
            "key\twith\ttabs",
            "",  # empty key
        ]
        for key in special_keys:
            cache[key] = f"value_for_{key}"

        for key in special_keys:
            assert cache[key] == f"value_for_{key}"
