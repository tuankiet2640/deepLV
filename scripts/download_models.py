"""Download and convert MarianMT models to CTranslate2 INT8 format."""

import argparse
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


def _write_decoder_yml(tmp_dir: Path, model) -> None:
    """Generate decoder.yml required by OpusMTConverter.

    Helsinki-NLP OPUS-MT models need this file for CTranslate2 conversion.
    The file describes the Marian NMT architecture parameters.
    """
    vocab_size = model.config.vocab_size
    dec_depth = model.config.decoder_layers
    enc_depth = model.config.encoder_layers
    dim_emb = model.config.d_model

    content = (
        f"- dec-depth: {dec_depth}\n"
        f"  dec-cell: ssru\n"
        f"  enc-depth: {enc_depth}\n"
        f"  enc-cell: gru\n"
        f"  tied-embeddings-all: true\n"
        f"  dim-emb: {dim_emb}\n"
        f"  dim-vocabs:\n"
        f"    - {vocab_size}\n"
        f"    - {vocab_size}\n"
    )

    decoder_yml_path = tmp_dir / "decoder.yml"
    with open(decoder_yml_path, "w") as f:
        f.write(content)


def download_and_convert(
    src: str, tgt: str, model_id: str, output_dir: Path, quantization: str = "int8"
) -> None:
    from transformers import MarianTokenizer

    key = f"{src}-{tgt}"
    out_path = output_dir / key

    if out_path.exists():
        print(f"  [skip] {key} already exists at {out_path}")
        return

    # TransformersConverter is the supported conversion path for MarianMT, and
    # it accepts the HuggingFace model ID directly.
    #
    # Do NOT switch to OpusMTConverter: that converter is for upstream Marian
    # checkpoints and expects a decoder.yml listing Marian .npz weight files
    # plus vocabularies. A directory produced by HuggingFace save_pretrained()
    # holds PyTorch weights instead, so OpusMTConverter cannot read it however
    # the decoder.yml is shaped.
    print(f"  [convert] {model_id} -> CTranslate2 ({quantization}) ...")
    converter = ctranslate2.converters.TransformersConverter(model_id)
    converter.convert(str(out_path), quantization=quantization)

    # Save the tokenizer alongside the converted model. The runtime loads it
    # with MarianTokenizer.from_pretrained(<model dir>), which needs the full
    # set of tokenizer files (source.spm, target.spm, vocab.json,
    # tokenizer_config.json) rather than the .spm files alone.
    #
    # This must run after convert(): CTranslate2 refuses to write into a
    # directory that already contains files.
    print(f"  [tokenizer] downloading {model_id} tokenizer ...")
    tokenizer = MarianTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(str(out_path))

    _verify_model_dir(out_path, key)

    print(f"  [done] {key}")


def _verify_model_dir(out_path: Path, key: str) -> None:
    """Fail the build early if a converted model is missing required files.

    Catching this here is much cheaper than shipping an image whose worker
    raises at translation time.
    """
    required = ["model.bin", "source.spm", "target.spm", "vocab.json"]
    missing = [name for name in required if not (out_path / name).exists()]
    if missing:
        raise RuntimeError(f"{key}: converted model is missing {', '.join(missing)} in {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and convert translation models")
    parser.add_argument("--output-dir", type=str, default="./models", help="Output directory")
    parser.add_argument("--pairs", type=str, nargs="*", help="Specific pairs (e.g., en-de de-en)")
    parser.add_argument(
        "--quantization", type=str, default="int8", choices=["int8", "float16", "float32"]
    )
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
