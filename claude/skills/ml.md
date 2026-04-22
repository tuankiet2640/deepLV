---
skill: ml
---

# Machine Learning / NLP

- **Transformer models** — encoder-decoder architecture for sequence-to-sequence translation
- **Pretrained models** — Helsinki-NLP/Opus-MT (MarianMT) via HuggingFace, no training required
- **Tokenization** — SentencePiece (unigram/BPE) built into MarianMT tokenizers
- **Inference optimization** — CTranslate2 for quantized INT8 inference, batched decoding
- **Model serving** — dedicated model worker process, decoupled from API server
- **Language detection** — fasttext-langdetect for automatic source language identification
- **Beam search** — configurable beam width for translation quality vs latency tradeoff
