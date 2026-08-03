"""Download and convert MarianMT models to CTranslate2 INT8 format."""

import argparse
import shutil
from pathlib import Path

import ctranslate2

MODEL_PAIRS = [
    ("en", "de", "Helsinki-NLP/opus-mt-en-de"),
    ("de", "en", "Helsinki-NLP/opus-mt-de-en"),
    ("en", "fr", "Helsinki-NLP/opus-mt-en-fr"),
    ("fr", "en", "Helsinki-NLP/opus-mt-fr-en"),
    ("en", "es", "Helsinki-NLP/opus-mt-en-es"),
    ("es", "en", "Helsinki-NLP/opus-mt-es-en"),
    ("en", "zh", "Helsinki-NLP/opus-mt-en-zh"),
    ("zh", "en", "Helsinki-NLP/opus-mt-zh-en"),
    ("en", "ja", "Helsinki-NLP/opus-mt-en-jap"),
    ("ja", "en", "Helsinki-NLP/opus-mt-jap-en"),
    ("en", "vi", "Helsinki-NLP/opus-mt-en-vi"),
    ("vi", "en", "Helsinki-NLP/opus-mt-vi-en"),
    ("en", "ko", "Helsinki-NLP/opus-mt-en-ko"),
    ("ko", "en", "Helsinki-NLP/opus-mt-ko-en"),
    ("en", "pt", "Helsinki-NLP/opus-mt-en-ROMANCE"),
    ("pt", "en", "Helsinki-NLP/opus-mt-ROMANCE-en"),
    ("en", "ru", "Helsinki-NLP/opus-mt-en-ru"),
    ("ru", "en", "Helsinki-NLP/opus-mt-ru-en"),
]


def download_and_convert(
    src: str, tgt: str, model_id: str, output_dir: Path, quantization: str = "int8"
) -> None:
    import tempfile

    from transformers import MarianTokenizer

    key = f"{src}-{tgt}"
    out_path = output_dir / key

    if out_path.exists():
        print(f"  [skip] {key} already exists at {out_path}")
        return

    # Convert directly from HuggingFace model ID using TransformersConverter.
    # Passing the model ID string (not a local path) lets the converter
    # download and handle the conversion correctly without null config issues.
    print(f"  [convert] {model_id} -> CTranslate2 ({quantization}) ...")
    converter = ctranslate2.converters.TransformersConverter(model_id)
    converter.convert(str(out_path), quantization=quantization)

    # Download tokenizer to a temp directory and copy .spm files to the
    # output model directory. The runtime (model_cache.py) needs source.spm
    # for SentencePiece tokenization.
    print(f"  [tokenizer] downloading {model_id} tokenizer ...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tokenizer = MarianTokenizer.from_pretrained(model_id)
        tokenizer.save_pretrained(tmp_dir)

        tmp_path = Path(tmp_dir)
        for spm_file in tmp_path.glob("*.spm"):
            shutil.copy2(spm_file, out_path / spm_file.name)

    print(f"  [done] {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and convert translation models")
    parser.add_argument("--output-dir", type=str, default="./models", help="Output directory")
    parser.add_argument("--pairs", type=str, nargs="*", help="Specific pairs (e.g., en-de de-en)")
    parser.add_argument("--quantization", type=str, default="int8", choices=["int8", "float16", "float32"])
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pairs_to_download = MODEL_PAIRS
    if args.pairs:
        requested = set(args.pairs)
        pairs_to_download = [(s, t, m) for s, t, m in MODEL_PAIRS if f"{s}-{t}" in requested]

    print(f"Downloading {len(pairs_to_download)} model(s) to {output_dir}")
    for src, tgt, model_id in pairs_to_download:
        download_and_convert(src, tgt, model_id, output_dir, args.quantization)

    print(f"\nDone. {len(pairs_to_download)} models ready in {output_dir}")


if __name__ == "__main__":
    main()
