"""Fetches the Olist Brazilian E-commerce dataset into data/raw/.

Idempotent: if the CSVs already exist, exits without re-downloading.

Usage:
    python scripts/download_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

DATASET_SLUG = "olistbr/brazilian-ecommerce"
RAW_DIR = Path("data/raw")
EXPECTED_CSV_PREFIX = "olist_"


def already_downloaded() -> bool:
    if not RAW_DIR.exists():
        return False
    csvs = list(RAW_DIR.glob(f"{EXPECTED_CSV_PREFIX}*.csv"))
    return len(csvs) >= 8  # The dataset has 9 CSVs; tolerate 1 missing


def main() -> int:
    if already_downloaded():
        print(f"[skip] CSVs already present in {RAW_DIR}/. Delete them to force re-download.")
        return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Import here so the script gives a clear error if kaggle isn't installed.
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("ERROR: 'kaggle' package not installed. Run: pip install -e .[dev]", file=sys.stderr)
        return 1

    api = KaggleApi()
    api.authenticate()

    print(f"[download] {DATASET_SLUG} → {RAW_DIR}/")
    api.dataset_download_files(DATASET_SLUG, path=str(RAW_DIR), unzip=True)

    csvs = sorted(RAW_DIR.glob("*.csv"))
    total_mb = sum(p.stat().st_size for p in csvs) / (1024 * 1024)
    print(f"[done] {len(csvs)} CSV files, {total_mb:.1f} MB total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
