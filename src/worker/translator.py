import time

import structlog

from src.worker.model_cache import ModelCache

log = structlog.get_logger()

MAX_INPUT_TOKENS = 512
EOS_TOKEN = "</s>"

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


def _chunk_tokens(tokens: list[str], max_tokens: int) -> list[list[str]]:
    """Split a source token sequence into chunks the model can accept.

    The tokenizer puts EOS at the end of the sequence. A naive split would
    leave that marker on the final chunk only, so it is detached first and
    re-appended to every chunk.
    """
    if len(tokens) <= max_tokens:
        return [tokens]

    has_eos = bool(tokens) and tokens[-1] == EOS_TOKEN
    body = tokens[:-1] if has_eos else tokens
    # Reserve a slot for the EOS token that gets re-appended below.
    limit = max_tokens - 1 if has_eos else max_tokens

    chunks = []
    for i in range(0, len(body), limit):
        chunk = body[i : i + limit]
        chunks.append([*chunk, EOS_TOKEN] if has_eos else chunk)
    return chunks


def _translate_direct(
    model_cache: ModelCache,
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    translator, tokenizer = model_cache.get_translator(source_lang, target_lang)

    # CTranslate2 does not implicitly append EOS for Transformers-converted
    # models, so the source tokens must come from the HuggingFace tokenizer,
    # which adds it. Going through convert_ids_to_tokens also guarantees the
    # pieces match the vocabulary the model was converted against.
    tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))

    translated_parts = []
    for chunk in _chunk_tokens(tokens, MAX_INPUT_TOKENS):
        results = translator.translate_batch(
            [chunk],
            beam_size=4,
            max_decoding_length=512,
        )
        hypothesis = results[0].hypotheses[0]
        translated_parts.append(
            tokenizer.decode(
                tokenizer.convert_tokens_to_ids(hypothesis),
                skip_special_tokens=True,
            )
        )

    return " ".join(translated_parts)
