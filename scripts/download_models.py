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
    from transformers import MarianMTModel, MarianTokenizer

    key = f"{src}-{tgt}"
    out_path = output_dir / key

    if out_path.exists():
        print(f"  [skip] {key} already exists at {out_path}")
        return

    print(f"  [download] {model_id} ...")
    tokenizer = MarianTokenizer.from_pretrained(model_id)
    model = MarianMTModel.from_pretrained(model_id)

    # Save PyTorch model temporarily
    tmp_dir = output_dir / f".tmp_{key}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(tmp_dir))
    tokenizer.save_pretrained(str(tmp_dir))

    # Convert to CTranslate2
    print(f"  [convert] {key} -> CTranslate2 ({quantization}) ...")
    converter = ctranslate2.converters.TransformersConverter(str(tmp_dir))
    converter.convert(str(out_path), quantization=quantization)

    # Copy SentencePiece model for tokenization
    for spm_file in tmp_dir.glob("*.spm"):
        shutil.copy2(spm_file, out_path / spm_file.name)

    # Copy tokenizer config for reference
    for json_file in tmp_dir.glob("*.json"):
        shutil.copy2(json_file, out_path / json_file.name)

    # Cleanup temp
    shutil.rmtree(tmp_dir)
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
