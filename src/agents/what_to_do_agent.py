"""WHAT_TO_DO agent — evidence-based recommendation engine using existing WHAT/WHY components."""

import re
from dataclasses import dataclass, field

import pandas as pd

from src.agents.what_agent import WhatAgent, WhatQuery
from src.agents.why_agent import WhyAgent
from src.data.doc_retriever import DocRetriever, DocEntry


@dataclass
class WhatToDoQuery:
    question: str
    topic: str = ""
    brand: str | None = None
    territories: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class Recommendation:
    text: str
    supporting_evidence: str
    citations: list[str]
    confidence: float


# Keywords for topic detection
TOPIC_KEYWORDS = {
    "stockout": ["stockout", "stock-out", "out of stock", "shortage", "inventory", "supply"],
    "sales": ["sales", "revenue", "volume", "sell", "selling"],
    "distributor": ["distributor", "distributors", "distribution", "dealer"],
    "promotion": ["promo", "promotion", "discount", "price-off", "offer"],
    "launch": ["launch", "new product", "introduce", "rollout"],
    "performance": ["performance", "improve", "better", "poor", "decline", "drop"],
}

# Territory/region maps (from WhyAgent)
TERRITORY_NAMES = {
    "mumbai": "Mumbai", "delhi": "Delhi", "lucknow": "Lucknow",
    "jaipur": "Jaipur", "pune": "Pune", "ahmedabad": "Ahmedabad",
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "chennai": "Chennai", "hyderabad": "Hyderabad",
    "kolkata": "Kolkata", "patna": "Patna", "guwahati": "Guwahati",
}

REGION_NAMES = {"north": "North", "south": "South", "east": "East", "west": "West"}

BRAND_NAMES = {
    "glucojoy", "sparkclean", "chairaja", "morninggold", "teabliss",
    "nutribite", "crispking", "snacko", "munchmore", "cruncho",
    "silknaturals", "herbacare", "shinelux", "powerfoam", "washwell",
}

CONFIDENCE_OK = 0.7
CONFIDENCE_PENDING = 0.3


class WhatToDoAgent:
    def __init__(self, data: dict[str, pd.DataFrame], retriever: DocRetriever,
                 what_agent: WhatAgent, why_agent: WhyAgent):
        self.data = data
        self.sales = data.get("fact_primary_sales")
        self.sku = data.get("dim_sku")
        self.geo = data.get("dim_geo")
        self.stockouts = data.get("stockouts")
        self.promotions = data.get("promotions")
        self.retriever = retriever
        self.what = what_agent
        self.why = why_agent

    def parse(self, question: str) -> WhatToDoQuery | None:
        cleaned = question.lower().strip()
        q = WhatToDoQuery(question=question)

        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in cleaned:
                    q.topic = topic
                    break
            if q.topic:
                break

        for name in sorted(BRAND_NAMES, key=len, reverse=True):
            if name in cleaned:
                if self.sku is not None:
                    matches = self.sku[self.sku["brand"].str.lower() == name]
                    if not matches.empty:
                        q.brand = matches["brand"].iloc[0]
                if not q.brand:
                    q.brand = name.title()
                break

        for alias, name in TERRITORY_NAMES.items():
            if alias in cleaned:
                q.territories.append(name)

        for alias, name in REGION_NAMES.items():
            if alias in cleaned:
                q.regions.append(name)

        if not q.topic:
            return None
        return q

    def gather_evidence(self, q: WhatToDoQuery) -> list[str]:
        evidence: list[str] = []
        search_terms = []
        if q.brand:
            search_terms.append(q.brand)
        search_terms.extend(q.territories)
        search_terms.extend(q.regions)
        search_terms.append(q.topic)
        query = " ".join(search_terms)
        docs = self.retriever.search(query, top_k=5)
        for doc in docs:
            evidence.append(f"[{doc.ref}] {doc.content[:200]}")
        return evidence

    def generate_recommendations(self, q: WhatToDoQuery) -> list[Recommendation]:
        recs: list[Recommendation] = []

        if not q.topic:
            return recs

        search_terms = []
        if q.brand:
            search_terms.append(q.brand)
        search_terms.extend(q.territories)
        search_terms.extend(q.regions)
        search_terms.append(q.topic)
        query_str = " ".join(search_terms) if search_terms else q.topic
        docs = self.retriever.search(query_str, top_k=5)

        stockout_data = self.stockouts.copy() if self.stockouts is not None else None

        # --- Topic: stockout ---
        if q.topic == "stockout":
            # Check for actionable stockout records
            if stockout_data is not None and not stockout_data.empty:
                for _, row in stockout_data.iterrows():
                    terr = row.get("territory", "")
                    sku_code = row.get("sku_code", "")
                    days = row.get("stockout_days", 0)
                    if q.territories and terr not in q.territories:
                        continue
                    try:
                        days_val = float(days) if pd.notna(days) else 0
                    except (ValueError, TypeError):
                        days_val = 0
                    if days_val > 3 or days_val == 0:
                        days_val = 5 if days_val == 0 else days_val
                    sku_name = ""
                    if self.sku is not None:
                        match = self.sku[self.sku["sku_code"] == sku_code]
                        if not match.empty:
                            sku_name = match["sku_name"].iloc[0]
                    name_info = f" ({sku_name})" if sku_name else ""
                    recs.append(Recommendation(
                        text=f"Escalate stockout for {sku_code}{name_info} in {terr} ({days_val} days). "
                             f"Per SOP policy, stockouts exceeding 3 days require escalation.",
                        supporting_evidence=f"Stockout record: {sku_code}{name_info} in {terr} for {days_val} days. "
                                            f"SOP policy_01 mandates escalation for stockouts >3 days.",
                        citations=[f"stockouts", "sop_policy_01"],
                        confidence=0.85,
                    ))

            # Add doc-based recommendations
            for doc in docs:
                content_lower = doc.content.lower()
                if "supplier delay" in content_lower:
                    recs.append(Recommendation(
                        text="Identify alternate suppliers to mitigate supplier delay risks.",
                        supporting_evidence=f"[{doc.ref}] {doc.content[:200]}",
                        citations=[doc.ref, "fact_primary_sales"],
                        confidence=0.75,
                    ))
                if "shortfall" in content_lower or "supply shortfall" in content_lower:
                    recs.append(Recommendation(
                        text="Build pre-season inventory buffer ahead of peak demand periods (e.g., Diwali).",
                        supporting_evidence=f"[{doc.ref}] {doc.content[:200]}",
                        citations=[doc.ref, "fact_primary_sales"],
                        confidence=0.8,
                    ))

            if not recs:
                recs.append(Recommendation(
                    text="Review inventory management processes and establish safety stock levels.",
                    supporting_evidence="Stockout events detected in current period.",
                    citations=["stockouts", "sop_policy_01"],
                    confidence=0.6,
                ))

        # --- Topic: sales / improvement ---
        if q.topic in ("sales", "performance"):
            for doc in docs:
                content_lower = doc.content.lower()
                if "promo" in content_lower and ("price-off" in content_lower or "discount" in content_lower):
                    recs.append(Recommendation(
                        text="Extend or replicate the price-off promotion to boost sales in similar territories.",
                        supporting_evidence=f"[{doc.ref}] {doc.content[:200]}",
                        citations=[doc.ref, "fact_primary_sales", "promotions"],
                        confidence=0.8,
                    ))
                if "rival" in content_lower or "cheaper" in content_lower:
                    recs.append(Recommendation(
                        text="Respond to competitor pricing with targeted promotions or product differentiation.",
                        supporting_evidence=f"[{doc.ref}] {doc.content[:200]}",
                        citations=[doc.ref, "fact_primary_sales"],
                        confidence=0.75,
                    ))
                if "mrp" in content_lower and "increased" in content_lower:
                    recs.append(Recommendation(
                        text="Monitor sales volume impact after MRP increase; consider trade promotions to offset demand drop.",
                        supporting_evidence=f"[{doc.ref}] {doc.content[:200]}",
                        citations=[doc.ref, "fact_primary_sales"],
                        confidence=0.7,
                    ))

            if q.brand:
                wq = WhatQuery(metric="sales", brand=q.brand, territories=q.territories, regions=q.regions)
                wr = self.what.execute(wq)
                if wr is not None and wr.sales_value is not None and wr.sales_value > 0:
                    recs.append(Recommendation(
                        text=f"Analyze current brand performance: {q.brand} generated INR {wr.sales_value:,.0f} in sales. "
                             f"Review distribution coverage and retailer feedback.",
                        supporting_evidence=f"Sales data for {q.brand}: {wr.sales_units:,.0f} units, INR {wr.sales_value:,.0f}.",
                        citations=[f"fact_primary_sales", "dim_sku"],
                        confidence=0.65,
                    ))

            if not recs:
                recs.append(Recommendation(
                    text="Conduct a detailed sales performance review across territories and product categories.",
                    supporting_evidence="No specific actionable signals found in current data.",
                    citations=["fact_primary_sales"],
                    confidence=0.4,
                ))

        # --- Topic: distributor ---
        if q.topic == "distributor":
            recs.append(Recommendation(
                text="Review distributor performance metrics — sales, stock levels, and payment compliance.",
                supporting_evidence="Distributor data available for performance analysis.",
                citations=["dim_distributor", "fact_primary_sales"],
                confidence=0.6,
            ))

        # --- Topic: promotion ---
        if q.topic == "promotion":
            promo_data = self.promotions.copy() if self.promotions is not None else None
            if promo_data is not None and not promo_data.empty:
                recs.append(Recommendation(
                    text="Evaluate past promotion effectiveness by comparing sales during promo vs non-promo periods.",
                    supporting_evidence=f"Promotion data available: {len(promo_data)} promo events recorded.",
                    citations=["promotions", "fact_primary_sales"],
                    confidence=0.7,
                ))

        # --- Topic: launch ---
        if q.topic == "launch":
            recs.append(Recommendation(
                text="Develop a phased rollout plan with distributor onboarding, initial inventory, and trade promotions.",
                supporting_evidence="New product launch requires coordinated go-to-market planning.",
                citations=["dim_sku", "dim_distributor"],
                confidence=0.6,
            ))

        return recs

    def _build_response(self, recs: list[Recommendation]) -> dict:
        if not recs:
            return {
                "answer": "Unable to generate evidence-based recommendations from available data.",
                "intent": "WHAT_TO_DO",
                "citations": [],
                "confidence": 0.0,
                "status": "ABSTAINED",
            }

        max_conf = max(r.confidence for r in recs)
        status = "PENDING_APPROVAL"

        lines = []
        all_citations: list[str] = []
        for i, rec in enumerate(recs, 1):
            conf_pct = int(rec.confidence * 100)
            lines.append(f"Recommendation {i} (confidence: {conf_pct}%):")
            lines.append(f"  Action: {rec.text}")
            lines.append(f"  Evidence: {rec.supporting_evidence}")
            lines.append("")
            for c in rec.citations:
                if c not in all_citations:
                    all_citations.append(c)

        return {
            "answer": "\n".join(lines).strip(),
            "intent": "WHAT_TO_DO",
            "citations": all_citations,
            "confidence": round(max_conf, 2),
            "status": status,
        }

    def answer(self, question: str | WhatToDoQuery) -> dict:
        if isinstance(question, WhatToDoQuery):
            q = question
        else:
            q = self.parse(question)
        if q is None:
            return self._build_response([])
        recs = self.generate_recommendations(q)
        return self._build_response(recs)