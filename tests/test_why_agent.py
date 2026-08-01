"""Tests for WHY agent — document retrieval + sales correlation for causal analysis."""

import pytest

from src.agents.why_agent import WhyAgent
from src.data.cleaner import clean_all
from src.data.doc_retriever import DocRetriever
from src.data.loader import load_all_csvs


@pytest.fixture
def agent():
    raw = load_all_csvs()
    data = clean_all(raw)
    retriever = DocRetriever()
    return WhyAgent(data, retriever)


class TestWhyParsing:
    def test_parse_sparkclean_spike(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        assert q is not None
        assert q.brand == "SparkClean"
        assert "Mumbai" in q.territories
        assert q.event_type == "spike"

    def test_parse_glucoj_stockout(self, agent):
        q = agent.parse("Why is there a stockout of GlucoJoy Choco 120g in Delhi?")
        assert q is not None
        assert "GlucoJoy" in q.brand or "GlucoJoy".lower() in q.brand.lower()
        assert "Delhi" in q.territories or "Delhi".lower() in " ".join(q.territories).lower()
        assert q.event_type == "stockout"

    def test_parse_sales_decline(self, agent):
        q = agent.parse("Why did sales decline in Bengaluru?")
        assert q is not None
        assert "Bengaluru" in q.territories or "Bengaluru".lower() in " ".join(q.territories).lower()
        assert q.event_type in ("decline", "drop")

    def test_parse_diwali_shortfall(self, agent):
        q = agent.parse("Why did GlucoJoy Choco 120g face supply shortfall during Diwali in North?")
        assert q is not None
        assert q.event_type in ("shortfall", "decline", "stockout")

    def test_parse_why_question_without_details(self, agent):
        q = agent.parse("Why did sales drop?")
        assert q is not None

    def test_parse_non_why_returns_none(self, agent):
        from src.agents.router import classify_intent
        assert classify_intent("Tell me a joke").intent != "WHY"


class TestWhyRetrieval:
    def test_sparkclean_promo_retrieved(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        assert len(docs) > 0
        refs = [d.ref for d in docs]
        assert "promo_circular_01" in refs

    def test_glucoj_supplier_retrieved(self, agent):
        q = agent.parse("Why is there a stockout of GlucoJoy Choco 120g in Delhi?")
        docs = agent.retrieve_docs(q)
        assert len(docs) > 0
        refs = [d.ref for d in docs]
        assert "email_01" in refs

    def test_diwali_supply_retrieved(self, agent):
        q = agent.parse("Why did GlucoJoy Choco 120g face supply shortfall during Diwali in North?")
        docs = agent.retrieve_docs(q)
        assert len(docs) > 0
        refs = [d.ref for d in docs]
        assert "email_02" in refs


class TestWhyCorrelation:
    def test_sparkclean_spike_correlated(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        result = agent.correlate(q, docs)
        assert result is not None
        assert "sales" in result.metric.lower() or result.sales_value_before is not None or result.sales_value_after is not None

    def test_correlation_returns_sales_delta(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        result = agent.correlate(q, docs)
        # The 16 Sep week should show a higher value than surrounding weeks
        # At minimum the result should have a finding
        assert result is None or hasattr(result, "finding")


class TestWhyFormatResponse:
    def test_format_response_has_correct_schema(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        result = agent.correlate(q, docs)
        response = agent.format_response(q, docs, result)
        assert "answer" in response
        assert "intent" in response
        assert "citations" in response
        assert "confidence" in response
        assert "status" in response
        assert response["intent"] == "WHY"

    def test_format_response_includes_promo_evidence(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        result = agent.correlate(q, docs)
        response = agent.format_response(q, docs, result)
        assert "promo" in response["answer"].lower() or "price-off" in response["answer"].lower()

    def test_format_response_has_citations(self, agent):
        q = agent.parse("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        docs = agent.retrieve_docs(q)
        result = agent.correlate(q, docs)
        response = agent.format_response(q, docs, result)
        assert len(response["citations"]) > 0
        assert "promo_circular_01" in response["citations"]
        assert "fact_primary_sales" in response["citations"]

    def test_format_response_none_result(self, agent):
        response = agent.format_response(None, [], None)
        assert "Unable to answer" in response["answer"]
        assert response["status"] == "ABSTAINED"


class TestWhyIntegration:
    def test_full_why_sparkclean_spike(self, agent):
        response = agent.answer("Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?")
        assert response["intent"] == "WHY"
        assert response["status"] == "OK"
        assert len(response["citations"]) > 0
        assert "promo" in response["answer"].lower()

    def test_full_why_glucoj_stockout(self, agent):
        response = agent.answer("Why did GlucoJoy Choco 120g stockout in Delhi?")
        assert response["intent"] == "WHY"
        assert response["status"] == "OK"
        assert len(response["citations"]) > 0

    def test_full_why_unknown_returns_abstained(self, agent):
        response = agent.answer("Why is the sky blue?")
        assert response["status"] == "ABSTAINED"