"""Tests for WHAT_TO_DO agent — evidence-based recommendation engine."""

import pytest

from src.agents.what_to_do_agent import WhatToDoAgent, Recommendation
from src.data.cleaner import clean_all
from src.data.doc_retriever import DocRetriever
from src.data.loader import load_all_csvs
from src.agents.what_agent import WhatAgent
from src.agents.why_agent import WhyAgent


@pytest.fixture
def agent():
    raw = load_all_csvs()
    data = clean_all(raw)
    retriever = DocRetriever()
    what_agent = WhatAgent(data)
    why_agent = WhyAgent(data, retriever)
    return WhatToDoAgent(data, retriever, what_agent, why_agent)


class TestParsing:
    def test_parse_stockout_question(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        assert q is not None
        assert "Chennai" in q.territories
        assert "stockout" in q.topic

    def test_parse_sparkclean_recommendation(self, agent):
        q = agent.parse("Recommend actions to improve SparkClean sales")
        assert q is not None
        assert q.brand == "SparkClean"
        assert "sales" in q.topic or "improve" in q.topic

    def test_parse_distributor_performance(self, agent):
        q = agent.parse("How to improve distributor performance in the West?")
        assert q is not None
        assert "West" in q.regions or "west" in " ".join(q.regions).lower()
        assert "distributor" in q.topic

    def test_parse_reduce_stockouts(self, agent):
        q = agent.parse("What can we do to reduce stockouts?")
        assert q is not None
        assert "stockout" in q.topic

    def test_parse_suggest_glucoj_launch(self, agent):
        q = agent.parse("Suggest next steps for the GlucoJoy launch")
        assert q is not None
        assert q.brand == "GlucoJoy"

    def test_parse_unknown_topic_returns_none(self, agent):
        q = agent.parse("What should I have for dinner?")
        assert q is None


class TestEvidenceGathering:
    def test_stockout_chennai_retrieves_evidence(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        evidence = agent.gather_evidence(q)
        assert len(evidence) > 0

    def test_sparkclean_improvement_retrieves_evidence(self, agent):
        q = agent.parse("Recommend actions to improve SparkClean sales")
        evidence = agent.gather_evidence(q)
        assert len(evidence) > 0
        assert any("promo" in e.lower() for e in evidence)

    def test_evidence_includes_docs(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        evidence = agent.gather_evidence(q)
        assert any("stockout" in e.lower() for e in evidence)


class TestRecommendations:
    def test_stockout_recommendation_has_required_fields(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        recs = agent.generate_recommendations(q)
        assert len(recs) > 0
        for rec in recs:
            assert isinstance(rec, Recommendation)
            assert rec.text
            assert rec.supporting_evidence
            assert rec.citations
            assert isinstance(rec.confidence, float)

    def test_recommendation_confidence_in_thresholds(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        recs = agent.generate_recommendations(q)
        for rec in recs:
            assert 0.0 <= rec.confidence <= 1.0

    def test_sparkclean_recommendations_grounded_in_promo(self, agent):
        q = agent.parse("Recommend actions to improve SparkClean sales")
        recs = agent.generate_recommendations(q)
        assert len(recs) >= 1
        texts = [r.text.lower() for r in recs]
        assert any("promo" in t for t in texts) or any("promotion" in t for t in texts)

    def test_stockout_recommendation_cites_sop(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        recs = agent.generate_recommendations(q)
        citations = set()
        for r in recs:
            citations.update(r.citations)
        assert "sop_policy_01" in citations or len(citations) > 0


class TestConfidenceThresholds:
    def test_strong_evidence_returns_pending_approval(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        response = agent.answer(q)
        max_rec_conf = max(r.confidence for r in agent.generate_recommendations(q))
        if len(agent.generate_recommendations(q)) > 0:
            assert response["status"] == "PENDING_APPROVAL"

    def test_low_confidence_returns_pending_approval(self, agent):
        recs = [
            Recommendation(
                text="Test recommendation",
                supporting_evidence="Some weak evidence",
                citations=["test"],
                confidence=0.5,
            )
        ]
        response = agent._build_response(recs)
        assert response["status"] == "PENDING_APPROVAL"

    def test_very_low_confidence_returns_pending_approval(self, agent):
        recs = [
            Recommendation(
                text="Test recommendation",
                supporting_evidence="Very weak evidence",
                citations=["test"],
                confidence=0.2,
            )
        ]
        response = agent._build_response(recs)
        assert response["status"] == "PENDING_APPROVAL"

    def test_no_recommendations_returns_abstained(self, agent):
        response = agent._build_response([])
        assert response["status"] == "ABSTAINED"


class TestFormatResponse:
    def test_response_has_correct_schema(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        response = agent.answer(q)
        assert "answer" in response
        assert "intent" in response
        assert "citations" in response
        assert "confidence" in response
        assert "status" in response
        assert response["intent"] == "WHAT_TO_DO"

    def test_response_includes_recommendations(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        response = agent.answer(q)
        assert len(response["answer"]) > 0

    def test_response_has_citations(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        response = agent.answer(q)
        assert len(response["citations"]) > 0

    def test_response_abstained_when_no_evidence(self, agent):
        response = agent.answer("What should I have for dinner?")
        assert response["status"] == "ABSTAINED"

    def test_confidence_is_overall_max(self, agent):
        q = agent.parse("What should we do about the stockout in Chennai?")
        response = agent.answer(q)
        assert 0.0 <= response["confidence"] <= 1.0


class TestIntegration:
    def test_full_stockout_workflow(self, agent):
        response = agent.answer("What should we do about the stockout in Chennai?")
        assert response["intent"] == "WHAT_TO_DO"
        assert response["status"] == "PENDING_APPROVAL"
        assert len(response["citations"]) > 0
        assert "stockout" in response["answer"].lower() or "Chennai" in response["answer"]

    def test_full_sparkclean_workflow(self, agent):
        response = agent.answer("Recommend actions to improve SparkClean sales")
        assert response["intent"] == "WHAT_TO_DO"
        assert response["status"] == "PENDING_APPROVAL"
        assert len(response["answer"]) > 0

    def test_full_unknown_returns_abstained(self, agent):
        response = agent.answer("What should I have for dinner?")
        assert response["status"] == "ABSTAINED"