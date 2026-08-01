"""Data cleaner — normalizes column names, dates, sentinel values, and territory names."""

import re

import pandas as pd

# Column alias maps: (table_name, source_column) -> target_column
COLUMN_ALIASES: dict[tuple[str, str], str] = {
    ("fact_targets", "material_no"): "sku_code",
    ("fact_targets", "area"): "territory",
    ("stockouts", "item_code"): "sku_code",
    ("promotions", "sku"): "sku_code",
}

# Date columns per table
DATE_COLUMNS: dict[str, list[str]] = {
    "fact_primary_sales": ["week_start"],
    "fact_targets": ["month"],
    "stockouts": ["week_start"],
    "promotions": ["week_start"],
}

# Territory name normalizations
TERRITORY_ALIASES: dict[str, str] = {
    "BLR": "Bengaluru",
    "Bombay": "Mumbai",
}

# Region name normalizations
REGION_ALIASES: dict[str, str] = {
    "S": "South",
    "E": "East",
    "East": "East",
}

# Sentinel values to replace with NaN
SENTINEL_VALUES = {"#N/A", "NA", "N/A", "null", "NULL", ""}

# Sentinel numeric values for numeric columns
SENTINEL_NUMBERS = {-1, 9999}

# Columns that should have leading-zero prefix cleaned from distributor IDs
DISTRIBUTOR_ID_COLS = {"distributor_id"}


def normalize_column_names(df: pd.DataFrame, table: str) -> pd.DataFrame:
    df = df.copy()
    for (tbl, src), target in COLUMN_ALIASES.items():
        if tbl == table and src in df.columns:
            df.rename(columns={src: target}, inplace=True)
    return df


def _parse_date_flexible(series: pd.Series) -> pd.Series:
    def try_parse(val):
        if pd.isna(val) or not isinstance(val, str):
            return pd.NaT
        val = val.strip()
        # YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
            return pd.to_datetime(val, format="%Y-%m-%d", errors="coerce")
        # MM/DD/YY
        if re.match(r"^\d{2}/\d{2}/\d{2}$", val):
            return pd.to_datetime(val, format="%m/%d/%y", errors="coerce")
        # DD Mon YYYY
        if re.match(r"^\d{2} [A-Z][a-z]{2} \d{4}$", val):
            return pd.to_datetime(val, format="%d %b %Y", errors="coerce")
        # DD-MM-YYYY
        if re.match(r"^\d{2}-\d{2}-\d{4}$", val):
            return pd.to_datetime(val, format="%d-%m-%Y", errors="coerce")
        # YYYY-MM (month column in targets)
        if re.match(r"^\d{4}-\d{2}$", val):
            return pd.to_datetime(val + "-01", format="%Y-%m-%d", errors="coerce")
        return pd.to_datetime(val, errors="coerce")
    return series.apply(try_parse)


def normalize_dates(df: pd.DataFrame, table: str) -> pd.DataFrame:
    df = df.copy()
    for col in DATE_COLUMNS.get(table, []):
        if col in df.columns:
            df[col] = _parse_date_flexible(df[col])
    return df


def clean_sentinels(df: pd.DataFrame, table: str) -> pd.DataFrame:
    df = df.copy()
    numeric_cols = {
        "primary_sales_units",
        "target_value", "stockout_flag", "stockout_days",
        "promo_discount_pct",
    }
    for col in df.columns:
        if col in numeric_cols:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(SENTINEL_VALUES, pd.NA)
            for sentinel in SENTINEL_NUMBERS:
                df[col] = df[col].replace(str(sentinel), pd.NA)
            df[col] = df[col].replace(sentinel, pd.NA)
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def clean_primary_sales_value(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.upper() in ("#N/A", "NA", "N/A", "NULL"):
        return None
    # Remove "Rs " prefix, quotes, commas
    s = re.sub(r'^["\']?Rs\s*', "", s, flags=re.IGNORECASE)
    s = s.strip('"').strip("'").strip()
    s = s.replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _normalize_primary_sales_value_column(df: pd.DataFrame) -> pd.DataFrame:
    if "primary_sales_value" in df.columns:
        df = df.copy()
        df["primary_sales_value"] = df["primary_sales_value"].apply(clean_primary_sales_value)
        df["primary_sales_value"] = pd.to_numeric(df["primary_sales_value"], errors="coerce")
    return df


def _normalize_target_value_column(df: pd.DataFrame) -> pd.DataFrame:
    if "target_value" in df.columns:
        df = df.copy()
        df["target_value"] = df["target_value"].astype(str).str.strip()
        df["target_value"] = df["target_value"].replace(SENTINEL_VALUES, pd.NA)
        for sentinel in SENTINEL_NUMBERS:
            df["target_value"] = df["target_value"].replace(str(sentinel), pd.NA)
        df["target_value"] = pd.to_numeric(df["target_value"], errors="coerce")
    return df


def _clean_distributor_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in DISTRIBUTOR_ID_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            # Remove leading zero before territory prefix: 0DEL-D1 -> DEL-D1
            df[col] = df[col].str.replace(r"^0([A-Z]{3}-)", r"\1", regex=True)
    return df


def _normalize_sku_codes(df: pd.DataFrame) -> pd.DataFrame:
    sku_cols = [c for c in df.columns if c == "sku_code"]
    if not sku_cols:
        return df
    df = df.copy()
    for col in sku_cols:
        df[col] = df[col].astype(str).str.strip().str.upper()
    return df


def _normalize_tier_column(df: pd.DataFrame) -> pd.DataFrame:
    if "tier" not in df.columns:
        return df
    df = df.copy()
    tier_map = {
        "VAL": "Value",
        "value": "Value",
        "Value": "Value",
        "mainstream": "Mainstream",
        "Mainstream": "Mainstream",
        "premium": "Premium",
        "Premium": "Premium",
        "PREM": "Premium",
    }
    df["tier"] = df["tier"].astype(str).str.strip().replace(tier_map)
    return df


def normalize_territory_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "territory" in df.columns:
        df["territory"] = df["territory"].astype(str).str.strip()
        df["territory"] = df["territory"].replace(TERRITORY_ALIASES)
    if "region" in df.columns:
        df["region"] = df["region"].astype(str).str.strip()
        df["region"] = df["region"].replace(REGION_ALIASES)
    df = _clean_distributor_ids(df)
    return df


def clean_dataframe(df: pd.DataFrame, table: str) -> pd.DataFrame:
    df = normalize_column_names(df, table)
    df = normalize_dates(df, table)
    df = clean_sentinels(df, table)
    df = _normalize_primary_sales_value_column(df)
    df = _normalize_target_value_column(df)
    df = normalize_territory_names(df)
    df = _normalize_sku_codes(df)
    df = _normalize_tier_column(df)
    return df


def clean_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: clean_dataframe(df, name) for name, df in raw.items()}