"""WHAT agent — aggregation engine for WHAT queries over cleaned FMCG data."""

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class WhatQuery:
    metric: str
    brand: str | None = None
    territories: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    pack_size: str | None = None
    month: int | None = None
    year: int | None = None
    time_grain: str = "total"
    compare_target: bool = False
    metric_type: str = "sales_value"


@dataclass
class WhatResult:
    sales_value: float | None = None
    sales_units: float | None = None
    target_value: float | None = None
    metric: str = "sales"
    currency: str = "INR"
    row_count: int = 0


BRAND_NAMES = {
    "glucojoy",
    "sparkclean", "spark clean",
    "chairaja", "chai raja",
    "morninggold", "morning gold",
    "teabliss", "tea bliss",
    "nutribite", "nutri bite",
    "crispking", "crisp king",
    "snacko",
    "munchmore", "munch more",
    "cruncho",
    "silknaturals", "silk naturals",
    "herbacare", "herba care",
    "shinelux", "shine lux",
    "powerfoam", "power foam",
    "washwell", "wash well",
}

CATEGORY_NAMES = {
    "biscuit": "Biscuits",
    "biscuits": "Biscuits",
    "tea": "Tea",
    "detergent": "Detergent",
    "shampoo": "Shampoo",
    "snack": "Snacks",
    "snacks": "Snacks",
}

REGION_NAMES = {
    "north": "North", "south": "South", "east": "East", "west": "West",
}

TERRITORY_NAMES = {
    "mumbai": "Mumbai", "bombay": "Mumbai",
    "delhi": "Delhi", "lucknow": "Lucknow", "jaipur": "Jaipur",
    "pune": "Pune", "ahmedabad": "Ahmedabad",
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru",
    "chennai": "Chennai", "hyderabad": "Hyderabad",
    "kolkata": "Kolkata", "patna": "Patna", "guwahati": "Guwahati",
}

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class WhatAgent:
    def __init__(self, data: dict[str, pd.DataFrame]):
        self.data = data
        self.sales = data.get("fact_primary_sales")
        self.targets = data.get("fact_targets")
        self.sku = data.get("dim_sku")
        self.geo = data.get("dim_geo")

    def parse(self, question: str) -> WhatQuery | None:
        cleaned = question.lower().strip()
        if not cleaned:
            return None

        q = WhatQuery(metric="sales")

        q.brand = self._extract_brand(cleaned)
        q.categories = self._extract_categories(cleaned)
        q.territories = self._extract_territories(cleaned)
        q.regions = self._extract_regions(cleaned)
        q.pack_size = self._extract_pack_size(cleaned)

        month_num = self._extract_month(cleaned)
        year_num = self._extract_year(cleaned)
        q.month = month_num
        q.year = year_num

        if "weekly" in cleaned or "week of" in cleaned or "week" in cleaned:
            q.time_grain = "weekly"
        elif "monthly" in cleaned or "month" in cleaned:
            q.time_grain = "monthly"

        if "target" in cleaned or "vs" in cleaned or "versus" in cleaned:
            q.compare_target = True

        if "unit" in cleaned:
            q.metric_type = "units"
        elif "revenue" in cleaned or "value" in cleaned or "sales" in cleaned:
            q.metric_type = "sales_value"

        return q

    def execute(self, query: WhatQuery) -> WhatResult | None:
        if self.sales is None:
            return None

        df = self.sales.copy()

        if query.brand and self.sku is not None:
            sku_codes = self.sku[self.sku["brand"].str.lower() == query.brand.lower()]["sku_code"].unique()
            if len(sku_codes) > 0:
                df = df[df["sku_code"].isin(sku_codes)]

        if query.categories and self.sku is not None:
            sku_codes = self.sku[self.sku["category"].isin(query.categories)]["sku_code"].unique()
            if len(sku_codes) > 0:
                df = df[df["sku_code"].isin(sku_codes)]

        if query.pack_size and self.sku is not None:
            ps = query.pack_size.lower().replace(" ", "")
            sku_codes = self.sku[self.sku["pack_size"].astype(str).str.lower().str.replace(" ", "") == ps]["sku_code"].unique()
            if len(sku_codes) > 0:
                df = df[df["sku_code"].isin(sku_codes)]

        if query.territories:
            df = df[df["territory"].isin(query.territories)]

        if query.regions and self.geo is not None:
            territories = self.geo[self.geo["region"].isin(query.regions)]["territory"].unique()
            df = df[df["territory"].isin(territories)]

        if query.year is not None:
            df = df[df["week_start"].dt.year == query.year]

        if query.month is not None:
            df = df[df["week_start"].dt.month == query.month]

        if df.empty:
            return None

        sales_value = float(df["primary_sales_value"].sum()) if "primary_sales_value" in df.columns else None
        sales_units = float(df["primary_sales_units"].sum()) if "primary_sales_units" in df.columns else None

        target_value = None
        if query.compare_target and self.targets is not None:
            target_df = self.targets.copy()

            if query.brand and self.sku is not None:
                sku_codes = self.sku[self.sku["brand"].str.lower() == query.brand.lower()]["sku_code"].unique()
                if len(sku_codes) > 0:
                    target_df = target_df[target_df["sku_code"].isin(sku_codes)]

            if query.categories and self.sku is not None:
                sku_codes = self.sku[self.sku["category"].isin(query.categories)]["sku_code"].unique()
                if len(sku_codes) > 0:
                    target_df = target_df[target_df["sku_code"].isin(sku_codes)]

            if query.territories:
                target_df = target_df[target_df["territory"].isin(query.territories)]

            if query.regions and self.geo is not None:
                territories = self.geo[self.geo["region"].isin(query.regions)]["territory"].unique()
                target_df = target_df[target_df["territory"].isin(territories)]

            if query.year is not None:
                target_df = target_df[target_df["month"].dt.year == query.year]

            if query.month is not None:
                target_df = target_df[target_df["month"].dt.month == query.month]

            if not target_df.empty and "target_value" in target_df.columns:
                target_value = float(target_df["target_value"].sum())

        metric = "sales_vs_target" if query.compare_target else "sales"
        return WhatResult(
            sales_value=sales_value,
            sales_units=sales_units,
            target_value=target_value,
            metric=metric,
            row_count=len(df),
        )

    def format_response(self, query: WhatQuery, result: WhatResult | None) -> dict:
        if result is None:
            return {
                "answer": "Unable to answer this question with the available data.",
                "intent": "WHAT",
                "citations": [],
                "confidence": 0.3,
                "status": "ABSTAINED",
            }

        parts = []
        if result.sales_value is not None:
            parts.append(f"primary sales value of INR {result.sales_value:,.2f}")
        if result.sales_units is not None:
            parts.append(f"{result.sales_units:,.0f} units")

        if query.compare_target and result.target_value is not None:
            parts.append(f"against a target of INR {result.target_value:,.2f}")
            if result.sales_value and result.target_value > 0:
                pct = ((result.sales_value - result.target_value) / result.target_value) * 100
                if pct >= 0:
                    parts.append(f"({pct:+.1f}% vs target)")
                else:
                    parts.append(f"({pct:+.1f}% vs target)")

        filters = []
        if query.brand:
            filters.append(f"brand {query.brand}")
        if query.territories:
            filters.append(f"territory {'/'.join(query.territories)}")
        if query.regions:
            filters.append(f"region {'/'.join(query.regions)}")
        if query.month and query.year:
            filters.append(f"{query.month:02d}/{query.year}")
        elif query.year:
            filters.append(f"{query.year}")

        context = ", ".join(filters) if filters else "the period"

        answer = f"For {context}: {' and '.join(parts)}."

        citations = ["fact_primary_sales"]
        if query.compare_target:
            citations.append("fact_targets")
        if query.brand or query.categories:
            citations.append("dim_sku")
        if query.regions or query.territories:
            citations.append("dim_geo")

        confidence = 0.85 if result.row_count > 0 else 0.5

        return {
            "answer": answer,
            "intent": "WHAT",
            "citations": citations,
            "confidence": confidence,
            "status": "OK",
        }

    def _extract_brand(self, cleaned: str) -> str | None:
        for name in sorted(BRAND_NAMES, key=len, reverse=True):
            if name in cleaned:
                # Return the properly cased version
                # Find the original brand name from dim_sku
                if self.sku is not None:
                    matches = self.sku[self.sku["brand"].str.lower().str.replace(" ", "") == name.replace(" ", "")]
                    if not matches.empty:
                        return matches["brand"].iloc[0]
                return name.title()
        return None

    def _extract_categories(self, cleaned: str) -> list[str]:
        for alias, cat in CATEGORY_NAMES.items():
            if alias in cleaned:
                return [cat]
        return []

    def _extract_territories(self, cleaned: str) -> list[str]:
        found = []
        for alias, name in TERRITORY_NAMES.items():
            if alias in cleaned:
                found.append(name)
        return found

    def _extract_regions(self, cleaned: str) -> list[str]:
        found = []
        for alias, name in REGION_NAMES.items():
            if alias in cleaned:
                found.append(name)
        return found

    def _extract_pack_size(self, cleaned: str) -> str | None:
        m = re.search(r"(\d+)\s*(kg|g|ml|gm)\b", cleaned, re.IGNORECASE)
        if m:
            return f"{m.group(1)}{m.group(2)}"
        return None

    def _extract_month(self, cleaned: str) -> int | None:
        for name, num in MONTH_NAMES.items():
            if name in cleaned:
                return num
        return None

    def _extract_year(self, cleaned: str) -> int | None:
        m = re.search(r"\b(202[4-9]|203[0-9])\b", cleaned)
        if m:
            return int(m.group(1))
        return None