import structlog
from ftlangdetect import detect

log = structlog.get_logger()

SUPPORTED_LANGUAGES = {"en", "de", "fr", "es", "zh", "ja", "vi", "ko", "pt", "ru"}

LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "zh": "Chinese",
    "ja": "Japanese",
    "vi": "Vietnamese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
}


def detect_language(text: str) -> str:
    """Detect the language of input text. Returns ISO 639-1 code."""
    try:
        result = detect(text, low_memory=True)
        lang = result["lang"]
        confidence = result["score"]
        log.debug("language_detected", lang=lang, confidence=round(confidence, 3))
        if lang in SUPPORTED_LANGUAGES:
            return lang
        # Fallback to English for unsupported detected languages
        log.info("unsupported_detected_language", detected=lang, fallback="en")
        return "en"
    except Exception:
        log.warning("language_detection_failed", exc_info=True)
        return "en"
