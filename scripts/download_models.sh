#!/bin/bash
# ============================================================
# Download MarianMT translation models
# ============================================================
# Downloads and converts models for local translation.
# Run this AFTER docker compose is up, inside the worker container.
#
# Usage:
#   docker compose -f docker-compose.prod.yml exec worker bash
#   python scripts/download_models.py --output-dir /app/models --pairs en-de de-en en-fr fr-en en-es es-en en-vi vi-en
#
# Or from the host:
#   docker compose -f docker-compose.prod.yml exec worker python scripts/download_models.py \
#     --output-dir /app/models \
#     --pairs en-de de-en en-fr fr-en en-es es-en
#
# NOTE: Each model pair is ~200-400MB. On 8GB RAM, keep 3-4 loaded at once.
# The LRU cache (MODEL_CACHE_SIZE=3) handles swapping automatically.
# ============================================================

set -euo pipefail

echo "DeepLV Model Downloader"
echo "======================="
echo ""
echo "This will download translation models into the worker container."
echo "Each model pair is ~200-400MB."
echo ""

# Default pairs (most common)
DEFAULT_PAIRS="en-de de-en en-fr fr-en en-es es-en en-vi vi-en"

read -p "Language pairs to download [${DEFAULT_PAIRS}]: " PAIRS
PAIRS=${PAIRS:-$DEFAULT_PAIRS}

echo ""
echo "Downloading models for: ${PAIRS}"
echo "This may take 5-15 minutes depending on your connection..."
echo ""

docker compose -f docker-compose.prod.yml exec worker python scripts/download_models.py \
    --output-dir /app/models \
    --pairs ${PAIRS}

echo ""
echo "Done! Models are stored in the 'models' Docker volume."
echo "The worker will load them on-demand (LRU cache)."
