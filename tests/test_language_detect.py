"""Test language detection service."""

from src.api.services.language_detect import SUPPORTED_LANGUAGES, detect_language


def test_detect_english():
    result = detect_language("Hello, how are you today?")
    assert result == "en"


def test_detect_german():
    result = detect_language("Guten Tag, wie geht es Ihnen?")
    assert result == "de"


def test_detect_french():
    result = detect_language("Bonjour, comment allez-vous aujourd'hui?")
    assert result == "fr"


def test_detect_returns_supported_language():
    result = detect_language("This is a test sentence in English.")
    assert result in SUPPORTED_LANGUAGES


def test_detect_empty_string_fallback():
    result = detect_language("")
    # Should fallback to "en" without crashing
    assert result in SUPPORTED_LANGUAGES
