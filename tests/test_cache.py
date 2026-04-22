"""Test translation cache key generation."""

from src.api.services.cache import _cache_key


def test_cache_key_deterministic():
    k1 = _cache_key("en", "de", "Hello world")
    k2 = _cache_key("en", "de", "Hello world")
    assert k1 == k2


def test_cache_key_different_for_different_pairs():
    k1 = _cache_key("en", "de", "Hello")
    k2 = _cache_key("en", "fr", "Hello")
    assert k1 != k2


def test_cache_key_normalizes_whitespace():
    k1 = _cache_key("en", "de", "Hello  world")
    k2 = _cache_key("en", "de", "Hello world")
    assert k1 == k2


def test_cache_key_strips_whitespace():
    k1 = _cache_key("en", "de", "  Hello world  ")
    k2 = _cache_key("en", "de", "Hello world")
    assert k1 == k2


def test_cache_key_has_prefix():
    key = _cache_key("en", "de", "test")
    assert key.startswith("translate:")
