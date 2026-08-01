"""Tests for data loader — loads and caches all CSVs at startup."""

import pytest
from src.data.loader import load_all_csvs, get_cached_data


def test_load_all_csvs_returns_dict():
    data = load_all_csvs()
    assert isinstance(data, dict)


def test_load_all_csvs_has_expected_tables():
    data = load_all_csvs()
    expected = {
        "dim_sku", "dim_geo", "dim_distributor", "dim_rep",
        "fact_primary_sales", "fact_targets", "promotions", "stockouts",
    }
    assert expected.issubset(data.keys())


def test_load_all_csvs_dims_not_empty():
    data = load_all_csvs()
    assert len(data["dim_sku"]) > 0
    assert len(data["dim_geo"]) > 0
    assert len(data["dim_distributor"]) > 0
    assert len(data["dim_rep"]) > 0


def test_load_all_csvs_facts_not_empty():
    data = load_all_csvs()
    assert len(data["fact_primary_sales"]) > 0
    assert len(data["fact_targets"]) > 0


def test_caching_returns_same_object():
    first = load_all_csvs()
    second = get_cached_data()
    assert first is second


def test_dim_sku_columns():
    data = load_all_csvs()
    cols = list(data["dim_sku"].columns)
    assert "sku_code" in cols
    assert "brand" in cols
    assert "category" in cols


def test_dim_geo_columns():
    data = load_all_csvs()
    cols = list(data["dim_geo"].columns)
    assert "territory" in cols
    assert "region" in cols


def test_fact_primary_sales_columns():
    data = load_all_csvs()
    cols = list(data["fact_primary_sales"].columns)
    assert "sku_code" in cols
    assert "territory" in cols
    assert "primary_sales_units" in cols
    assert "primary_sales_value" in cols


def test_fact_targets_columns():
    data = load_all_csvs()
    cols = list(data["fact_targets"].columns)
    assert "material_no" in cols
    assert "area" in cols
    assert "target_value" in cols


def test_promotions_columns():
    data = load_all_csvs()
    cols = list(data["promotions"].columns)
    assert "sku" in cols
    assert "promo_type" in cols


def test_stockouts_columns():
    data = load_all_csvs()
    cols = list(data["stockouts"].columns)
    assert "item_code" in cols
    assert "stockout_flag" in cols