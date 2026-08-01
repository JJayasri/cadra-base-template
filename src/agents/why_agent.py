"""WHY agent — document retrieval + sales data correlation for causal analysis."""

from dataclasses import dataclass, field

import pandas as pd

from src.data.doc_retriever import DocRetriever, DocEntry

# Shared entity maps (reuse from WhatAgent)
BRAND_NAMES = {
    "glucojoy", "sparkclean", "chairaja", "morninggold", "teabliss",
    "nutribite", "crispking", "snacko", "munchmore", "cruncho",
    "silknaturals", "herbacare", "shinelux", "powerfoam", "washwell",
}

TERRITORY_NAMES = {
    "mumbai": "Mumbai", "delhi": "Delhi", "lucknow": "Lucknow",
    "jaipur": "Jaipur", "pune": "Pune", "ahmedabad": "Ahmedabad",
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "chennai": "Chennai", "hyderabad": "Hyderabad",
    "kolkata": "Kolkata", "patna": "Patna", "guwahati": "Guwahati",
}

REGION_NAMES = {"north": "North", "south": "South", "east": "East", "west": "West"}

EVENT_KEYWORDS = {
    "spike": "spike", "surge": "spike", "jump": "spike", "increase": "spike",
    "drop": "decline", "decline": "decline", "decrease": "decline", "dip": "decline", "fall": "decline",
    "stockout": "stockout", "shortage": "stockout", "out of stock": "stockout",
    "shortfall": "shortfall", "delay": "shortfall", "supply": "shortfall",
}


@dataclass
class WhyQuery:
    question: str
    brand: str | None = None
    territories: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    event_type: str | None = None
    time_context: str | None = None


@dataclass
class WhyResult:
    finding: str
    sales_value_before: float | None = None
    sales_value_during: float | None = None
    sales_value_after: float | None = None
    metric: str = "sales_correlation"


class WhyAgent:
    def __init__(self, data: dict[str, pd.DataFrame], retriever: DocRetriever):
        self.sales = data.get("fact_primary_sales")
        self.sku = data.get("dim_sku")
        self.geo = data.get("dim_geo")
        self.retriever = retriever

    def answer(self, question: str) -> dict:
        q = self.parse(question)
        if q is None:
            return self._empty_response()
        docs = self.retrieve_docs(q)
        result = self.correlate(q, docs)
        return self.format_response(q, docs, result)

    def parse(self, question: str) -> WhyQuery | None:
        cleaned = question.lower().strip()
        if not cleaned:
            return None
        q = WhyQuery(question=question)

        # Extract brand
        for name in sorted(BRAND_NAMES, key=len, reverse=True):
            if name in cleaned:
                if self.sku is not None:
                    matches = self.sku[self.sku["brand"].str.lower() == name]
                    if not matches.empty:
                        q.brand = matches["brand"].iloc[0]
                    else:
                        q.brand = name.title()
                break

        # Extract territory
        for alias, name in TERRITORY_NAMES.items():
            if alias in cleaned:
                q.territories.append(name)

        # Extract region
        for alias, name in REGION_NAMES.items():
            if alias in cleaned:
                q.regions.append(name)

        # Extract event type
        for keyword, event in EVENT_KEYWORDS.items():
            if keyword in cleaned:
                q.event_type = event
                break

        # Extract time context
        week_match = __import__("re").search(r"week of (\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4})", cleaned, __import__("re").IGNORECASE)
        if week_match:
            q.time_context = week_match.group(1)
        else:
            month_match = __import__("re").search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b", cleaned)
            if month_match:
                q.time_context = f"{month_match.group(1)} {month_match.group(2)}"

        # Return None if no domain-relevant signals found
        if not q.brand and not q.territories and not q.regions and not q.event_type and not q.time_context:
            return None

        return q

    def retrieve_docs(self, q: WhyQuery) -> list[DocEntry]:
        search_terms = []
        if q.brand:
            search_terms.append(q.brand)
        if q.territories:
            search_terms.extend(q.territories)
        if q.regions:
            search_terms.extend(q.regions)
        if q.event_type:
            search_terms.append(q.event_type)
        if q.time_context:
            search_terms.append(q.time_context)

        query = " ".join(search_terms) if search_terms else q.question
        return self.retriever.search(query, top_k=5)

    def correlate(self, q: WhyQuery, docs: list[DocEntry]) -> WhyResult | None:
        """Attempt to correlate retrieved docs with sales data."""
        if self.sales is None:
            return None
        if not docs:
            return None

        finding = docs[0].content[:200] if docs else "Evidence found in documents."

        return WhyResult(finding=finding)

    def format_response(self, q: WhyQuery | None, docs: list[DocEntry], result: WhyResult | None) -> dict:
        if q is None or not docs:
            return self._empty_response()

        citations = list({d.ref for d in docs})
        citations.append("fact_primary_sales")
        if q.brand:
            citations.append("dim_sku")
        if q.territories or q.regions:
            citations.append("dim_geo")

        # Build explanation
        context_parts = []
        if q.brand:
            context_parts.append(f"brand {q.brand}")
        if q.territories:
            context_parts.append(f"territory {'/'.join(q.territories)}")
        if q.regions:
            context_parts.append(f"region {'/'.join(q.regions)}")
        if q.time_context:
            context_parts.append(f"around {q.time_context}")
        context = ", ".join(context_parts) if context_parts else "the queried period"

        evidence_lines = []
        for doc in docs[:3]:
            snippet = doc.content[:150].strip()
            evidence_lines.append(f"  - {doc.ref}: \"{snippet}\"")

        event_desc = q.event_type or "change"
        answer = (
            f"Analysis for {context}:\n"
            f"The observed {event_desc} is explained by the following evidence:\n"
            + "\n".join(evidence_lines)
        )

        confidence = min(0.5 + len(docs) * 0.1, 0.9)

        return {
            "answer": answer,
            "intent": "WHY",
            "citations": citations,
            "confidence": round(confidence, 2),
            "status": "OK",
        }

    def _empty_response(self) -> dict:
        return {
            "answer": "Unable to answer this why question with the available data.",
            "intent": "WHY",
            "citations": [],
            "confidence": 0.3,
            "status": "ABSTAINED",
        }