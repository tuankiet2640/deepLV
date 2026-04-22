import time
from collections import OrderedDict
from pathlib import Path

import ctranslate2
import sentencepiece as spm
import structlog

log = structlog.get_logger()


class TranslatorEntry:
    __slots__ = ("translator", "tokenizer", "last_used")

    def __init__(self, translator: ctranslate2.Translator, tokenizer: spm.SentencePieceProcessor):
        self.translator = translator
        self.tokenizer = tokenizer
        self.last_used = time.monotonic()


class ModelCache:
    """LRU cache for loaded CTranslate2 translation models."""

    def __init__(self, model_dir: str, max_models: int = 6):
        self._model_dir = Path(model_dir)
        self._max_models = max_models
        self._cache: OrderedDict[str, TranslatorEntry] = OrderedDict()

    def _model_key(self, source_lang: str, target_lang: str) -> str:
        return f"{source_lang}-{target_lang}"

    def _model_path(self, key: str) -> Path:
        return self._model_dir / key

    def get_translator(
        self, source_lang: str, target_lang: str
    ) -> tuple[ctranslate2.Translator, spm.SentencePieceProcessor]:
        key = self._model_key(source_lang, target_lang)

        if key in self._cache:
            entry = self._cache[key]
            entry.last_used = time.monotonic()
            self._cache.move_to_end(key)
            log.debug("model_cache_hit", model=key)
            return entry.translator, entry.tokenizer

        log.info("model_cache_miss", model=key, loading=True)
        return self._load_model(key)

    def _load_model(self, key: str) -> tuple[ctranslate2.Translator, spm.SentencePieceProcessor]:
        if len(self._cache) >= self._max_models:
            evicted_key, _ = self._cache.popitem(last=False)
            log.info("model_evicted", model=evicted_key)

        model_path = self._model_path(key)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        translator = ctranslate2.Translator(
            str(model_path),
            device="cpu",
            compute_type="int8",
            inter_threads=2,
        )

        sp_model_path = model_path / "source.spm"
        tokenizer = spm.SentencePieceProcessor()
        tokenizer.Load(str(sp_model_path))

        entry = TranslatorEntry(translator, tokenizer)
        self._cache[key] = entry

        log.info("model_loaded", model=key, total_loaded=len(self._cache))
        return entry.translator, entry.tokenizer

    @property
    def loaded_models(self) -> list[str]:
        return list(self._cache.keys())

    @property
    def size(self) -> int:
        return len(self._cache)
