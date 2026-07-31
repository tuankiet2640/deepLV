import time

import structlog

from src.worker.model_cache import ModelCache

log = structlog.get_logger()

SUPPORTED_PAIRS: set[tuple[str, str]] = set()
_LANG_CODES = ["en", "de", "fr", "es", "zh", "ja", "vi", "ko", "pt", "ru"]
for lang in _LANG_CODES:
    if lang != "en":
        SUPPORTED_PAIRS.add(("en", lang))
        SUPPORTED_PAIRS.add((lang, "en"))


def translate_text(
    model_cache: ModelCache,
    text: str,
    source_lang: str,
    target_lang: str,
) -> dict:
    """Translate text using the appropriate model.

    Handles pivot translation for non-English pairs.
    """
    start = time.monotonic()

    if source_lang == target_lang:
        return {
            "translated_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "pivoted": False,
            "latency_ms": 0,
        }

    direct_pair = (source_lang, target_lang)
    if direct_pair in SUPPORTED_PAIRS:
        result = _translate_direct(model_cache, text, source_lang, target_lang)
        elapsed = (time.monotonic() - start) * 1000
        return {
            "translated_text": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "pivoted": False,
            "latency_ms": round(elapsed, 1),
        }

    # Pivot through English
    if source_lang != "en" and target_lang != "en":
        log.info("pivot_translation", source=source_lang, target=target_lang)
        intermediate = _translate_direct(model_cache, text, source_lang, "en")
        result = _translate_direct(model_cache, intermediate, "en", target_lang)
        elapsed = (time.monotonic() - start) * 1000
        return {
            "translated_text": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "pivoted": True,
            "latency_ms": round(elapsed, 1),
        }

    raise ValueError(f"Unsupported language pair: {source_lang} -> {target_lang}")


def _translate_direct(
    model_cache: ModelCache,
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    translator, tokenizer = model_cache.get_translator(source_lang, target_lang)

    tokens = tokenizer.Encode(text, out_type=str)
    results = translator.translate_batch(
        [tokens],
        beam_size=4,
        max_decoding_length=512,
    )
    translated_tokens = results[0].hypotheses[0]
    return tokenizer.Decode(translated_tokens)
