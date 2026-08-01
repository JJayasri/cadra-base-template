"""Data loader — loads and caches all CSVs from the Data directory at startup."""

import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "Data"

_cache: dict[str, pd.DataFrame] | None = None

CSV_FILES = [
    "dim_sku",
    "dim_geo",
    "dim_distributor",
    "dim_rep",
    "fact_primary_sales",
    "fact_targets",
    "promotions",
    "stockouts",
]


def load_all_csvs() -> dict[str, pd.DataFrame]:
    global _cache
    if _cache is not None:
        return _cache
    _cache = {}
    for name in CSV_FILES:
        path = DATA_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
        _cache[name] = pd.read_csv(path, dtype_backend="numpy_nullable", low_memory=False)
    return _cache


def get_cached_data() -> dict[str, pd.DataFrame] | None:
    return _cache