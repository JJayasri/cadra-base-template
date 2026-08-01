"""Tests for data cleaner — column aliases, date normalization, sentinel handling."""

import pandas as pd
import pytest

from src.data.cleaner import (
    normalize_column_names,
    normalize_dates,
    clean_sentinels,
    clean_primary_sales_value,
    normalize_territory_names,
    clean_dataframe,
    clean_all,
)


class TestNormalizeColumnNames:
    def test_fact_targets_columns_mapped(self):
        df = pd.DataFrame({"month": [], "material_no": [], "area": [], "target_value": []})
        result = normalize_column_names(df, "fact_targets")
        assert "sku_code" in result.columns
        assert "territory" in result.columns
        assert "material_no" not in result.columns
        assert "area" not in result.columns

    def test_stockouts_columns_mapped(self):
        df = pd.DataFrame({"week_start": [], "item_code": [], "territory": [], "stockout_flag": [], "stockout_days": []})
        result = normalize_column_names(df, "stockouts")
        assert "sku_code" in result.columns
        assert "item_code" not in result.columns

    def test_promotions_columns_mapped(self):
        df = pd.DataFrame({"week_start": [], "sku": [], "territory": [], "promo_type": [], "promo_discount_pct": []})
        result = normalize_column_names(df, "promotions")
        assert "sku_code" in result.columns
        assert "sku" not in result.columns

    def test_unknown_table_passes_through(self):
        df = pd.DataFrame({"foo": [], "bar": []})
        result = normalize_column_names(df, "unknown")
        assert list(result.columns) == ["foo", "bar"]

    def test_dim_sku_unchanged(self):
        df = pd.DataFrame({"sku_code": [], "brand": [], "tier": []})
        result = normalize_column_names(df, "dim_sku")
        assert list(result.columns) == ["sku_code", "brand", "tier"]


class TestNormalizeDates:
    def test_iso_date(self):
        df = pd.DataFrame({"week_start": ["2025-07-01"]})
        result = normalize_dates(df, "fact_primary_sales")
        assert pd.api.types.is_datetime64_any_dtype(result["week_start"])

    def test_us_style_date(self):
        df = pd.DataFrame({"week_start": ["07/01/25"]})
        result = normalize_dates(df, "fact_primary_sales")
        assert pd.api.types.is_datetime64_any_dtype(result["week_start"])

    def test_dd_mon_yyyy_date(self):
        df = pd.DataFrame({"week_start": ["01 Jul 2025"]})
        result = normalize_dates(df, "fact_primary_sales")
        assert pd.api.types.is_datetime64_any_dtype(result["week_start"])

    def test_dd_mm_yyyy_date(self):
        df = pd.DataFrame({"week_start": ["01-07-2025"]})
        result = normalize_dates(df, "fact_primary_sales")
        assert pd.api.types.is_datetime64_any_dtype(result["week_start"])

    def test_month_column(self):
        df = pd.DataFrame({"month": ["2025-07"]})
        result = normalize_dates(df, "fact_targets")
        assert pd.api.types.is_datetime64_any_dtype(result["month"])

    def test_no_date_column_unchanged(self):
        df = pd.DataFrame({"sku_code": ["GJ-001"]})
        result = normalize_dates(df, "dim_sku")
        assert result["sku_code"].iloc[0] == "GJ-001"


class TestCleanSentinels:
    def test_na_string_replaced(self):
        df = pd.DataFrame({"primary_sales_units": ["#N/A", "NA", "100"]})
        result = clean_sentinels(df, "fact_primary_sales")
        assert pd.isna(result["primary_sales_units"].iloc[0])
        assert pd.isna(result["primary_sales_units"].iloc[1])
        assert result["primary_sales_units"].iloc[2] == 100.0

    def test_negative_one_replaced(self):
        df = pd.DataFrame({"primary_sales_units": ["-1", "100"]})
        result = clean_sentinels(df, "fact_primary_sales")
        assert pd.isna(result["primary_sales_units"].iloc[0])
        assert result["primary_sales_units"].iloc[1] == 100.0

    def test_9999_sentinel_replaced(self):
        df = pd.DataFrame({"primary_sales_units": ["9999", "100"]})
        result = clean_sentinels(df, "fact_primary_sales")
        assert pd.isna(result["primary_sales_units"].iloc[0])
        assert result["primary_sales_units"].iloc[1] == 100.0

    def test_empty_string_replaced(self):
        df = pd.DataFrame({"primary_sales_units": ["", "100"]})
        result = clean_sentinels(df, "fact_primary_sales")
        assert pd.isna(result["primary_sales_units"].iloc[0])
        assert result["primary_sales_units"].iloc[1] == 100.0

    def test_target_value_sentinels(self):
        df = pd.DataFrame({"target_value": ["#N/A", "5000"]})
        result = clean_sentinels(df, "fact_targets")
        assert pd.isna(result["target_value"].iloc[0])
        assert result["target_value"].iloc[1] == 5000.0

    def test_non_numeric_cols_not_affected(self):
        df = pd.DataFrame({"sku_code": ["#N/A", "GJ-001"]})
        result = clean_sentinels(df, "fact_primary_sales")
        assert result["sku_code"].iloc[0] == "#N/A"


class TestCleanPrimarySalesValue:
    def test_plain_number(self):
        result = clean_primary_sales_value("3753.75")
        assert result == 3753.75

    def test_comma_separated(self):
        result = clean_primary_sales_value("4,792")
        assert result == 4792.0

    def test_rs_prefix(self):
        result = clean_primary_sales_value("Rs 4,582")
        assert result == 4582.0

    def test_quoted_rs(self):
        result = clean_primary_sales_value('"Rs 3,589"')
        assert result == 3589.0

    def test_na_value(self):
        result = clean_primary_sales_value("#N/A")
        assert result is None

    def test_empty_string(self):
        result = clean_primary_sales_value("")
        assert result is None

    def test_none(self):
        result = clean_primary_sales_value(None)
        assert result is None


class TestNormalizeTerritoryNames:
    def test_blr_to_bengaluru(self):
        df = pd.DataFrame({"territory": ["BLR"]})
        result = normalize_territory_names(df)
        assert result["territory"].iloc[0] == "Bengaluru"

    def test_unknown_territory_unchanged(self):
        df = pd.DataFrame({"territory": ["Delhi"]})
        result = normalize_territory_names(df)
        assert result["territory"].iloc[0] == "Delhi"

    def test_distributor_id_cleaned(self):
        df = pd.DataFrame({"distributor_id": ["0DEL-D1", "MUM-D1"]})
        result = normalize_territory_names(df)
        assert result["distributor_id"].iloc[0] == "DEL-D1"
        assert result["distributor_id"].iloc[1] == "MUM-D1"


class TestCleanDataFrame:
    def test_integration_on_primary_sales(self):
        df = pd.DataFrame({
            "week_start": ["2025-07-01"],
            "sku_code": ["CK-001"],
            "territory": ["BLR"],
            "distributor_id": ["0BEN-D1"],
            "primary_sales_units": ["100"],
            "primary_sales_value": ["Rs 4,582"],
        })
        result = clean_dataframe(df, "fact_primary_sales")
        assert result["territory"].iloc[0] == "Bengaluru"
        assert result["distributor_id"].iloc[0] == "BEN-D1"
        assert result["primary_sales_value"].iloc[0] == 4582.0
        assert pd.api.types.is_datetime64_any_dtype(result["week_start"])

    def test_integration_on_targets(self):
        df = pd.DataFrame({
            "month": ["2025-07"],
            "material_no": ["CK-001"],
            "area": ["Delhi"],
            "target_value": ["5000"],
        })
        result = clean_dataframe(df, "fact_targets")
        assert "sku_code" in result.columns
        assert "territory" in result.columns
        assert result["sku_code"].iloc[0] == "CK-001"
        assert result["territory"].iloc[0] == "Delhi"
        assert pd.api.types.is_datetime64_any_dtype(result["month"])


class TestCleanAll:
    def test_returns_dict_with_all_tables(self):
        from src.data.loader import load_all_csvs
        raw = load_all_csvs()
        cleaned = clean_all(raw)
        expected = {
            "dim_sku", "dim_geo", "dim_distributor", "dim_rep",
            "fact_primary_sales", "fact_targets", "promotions", "stockouts",
        }
        assert expected.issubset(cleaned.keys())

    def test_primary_sales_dates_are_datetime(self):
        from src.data.loader import load_all_csvs
        raw = load_all_csvs()
        cleaned = clean_all(raw)
        assert pd.api.types.is_datetime64_any_dtype(cleaned["fact_primary_sales"]["week_start"])

    def test_primary_sales_value_is_numeric(self):
        from src.data.loader import load_all_csvs
        raw = load_all_csvs()
        cleaned = clean_all(raw)
        assert pd.api.types.is_float_dtype(cleaned["fact_primary_sales"]["primary_sales_value"])

    def test_targets_sku_code_exists(self):
        from src.data.loader import load_all_csvs
        raw = load_all_csvs()
        cleaned = clean_all(raw)
        assert "sku_code" in cleaned["fact_targets"].columns

    def test_geo_region_normalized(self):
        from src.data.loader import load_all_csvs
        raw = load_all_csvs()
        cleaned = clean_all(raw)
        regions = cleaned["dim_geo"]["region"].unique()
        assert "S" not in regions
        assert "E" not in regions