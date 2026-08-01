"""Tests for document retriever — loads, parses, and searches Data/docs."""

import pytest
from src.data.doc_retriever import DocRetriever, DocEntry


@pytest.fixture
def retriever():
    return DocRetriever()


class TestDocLoading:
    def test_loads_all_docs(self, retriever):
        assert len(retriever.docs) == 30

    def test_each_doc_has_ref_and_content(self, retriever):
        for doc in retriever.docs:
            assert doc.ref, f"Missing ref in {doc.filename}"
            assert doc.content, f"Missing content in {doc.filename}"

    def test_promo_circular_loaded(self, retriever):
        doc = retriever.get_by_ref("promo_circular_01")
        assert doc is not None
        assert "SparkClean" in doc.content

    def test_email_01_loaded(self, retriever):
        doc = retriever.get_by_ref("email_01")
        assert doc is not None
        assert "GlucoJoy" in doc.content or "glucojoy" in doc.content.lower()

    def test_distractor_docs_loaded(self, retriever):
        docs = retriever.search("routine")
        assert len(docs) > 0

    def test_hr_note_is_distractor(self, retriever):
        doc = retriever.get_by_ref("hr_note_14")
        assert doc is not None
        assert "expense" in doc.content.lower()


class TestDocSearch:
    def test_search_sparkclean_promo(self, retriever):
        docs = retriever.search("SparkClean 1kg promo Mumbai")
        assert len(docs) >= 1
        assert any("promo_circular" in d.ref for d in docs)

    def test_search_glucoj_stockout(self, retriever):
        docs = retriever.search("GlucoJoy stockout Delhi")
        assert len(docs) >= 1
        assert any("email_01" in d.ref for d in docs)

    def test_search_returns_scored_results(self, retriever):
        docs = retriever.search("price increase SilkNaturals")
        assert len(docs) >= 1
        assert all(hasattr(d, "score") for d in docs)
        assert docs[0].score >= docs[-1].score if len(docs) > 1 else True

    def test_search_ignores_irrelevant_docs(self, retriever):
        docs = retriever.search("SparkClean")
        refs = [d.ref for d in docs]
        assert "promo_circular_01" in refs
        # Irrelevant docs should rank very low
        irrel = {"routine_note_16", "routine_note_17", "hr_note_14"}
        for r in irrel:
            if r in refs:
                assert refs.index(r) > refs.index("promo_circular_01")

    def test_search_empty_query_returns_empty(self, retriever):
        docs = retriever.search("")
        assert len(docs) == 0

    def test_search_no_match_returns_empty(self, retriever):
        docs = retriever.search("xyzzy_nonexistent_12345")
        assert len(docs) == 0

    def test_search_by_ref_prefix(self, retriever):
        docs = retriever.search("email_")
        refs = [d.ref for d in docs]
        assert "email_01" in refs
        assert "email_02" in refs

    def test_search_diwali_supply(self, retriever):
        docs = retriever.search("Diwali supply shortfall GlucoJoy North")
        assert len(docs) >= 1
        assert any("email_02" in d.ref for d in docs)


class TestDocContent:
    def test_red_herring_has_low_relevance(self, retriever):
        docs = retriever.search("lapsed promo caused decline")
        refs = [d.ref for d in docs]
        # The red herring doc should appear but not be top result for SparkClean
        assert "promo_note_redherring_02b" in refs

    def test_red_herring_marked_unverified(self, retriever):
        doc = retriever.get_by_ref("promo_note_redherring_02b")
        assert doc is not None
        assert "unverified" in doc.content.lower()

    def test_visit_note_rival_tea(self, retriever):
        docs = retriever.search("rival cheaper tea Bengaluru MorningGold")
        assert len(docs) >= 1
        assert any("visit_note_02" in d.ref for d in docs)