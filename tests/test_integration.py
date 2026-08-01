"""Integration tests for Slice 3: WHAT agent wired into POST /ask."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.agents.what_agent import WhatAgent
from src.agents.what_to_do_agent import WhatToDoAgent
from src.agents.why_agent import WhyAgent
from src.app import app
from src.data.cleaner import clean_all
from src.data.doc_retriever import DocRetriever
from src.data.loader import load_all_csvs

BASE_URL = "http://test"


@pytest.fixture(scope="session", autouse=True)
def _setup_app_state():
    raw = load_all_csvs()
    cleaned = clean_all(raw)
    retriever = DocRetriever()
    app.state.data = cleaned
    app.state.what_agent = WhatAgent(cleaned)
    app.state.why_agent = WhyAgent(cleaned, retriever)
    app.state.what_to_do_agent = WhatToDoAgent(cleaned, retriever, app.state.what_agent, app.state.why_agent)
    return app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        yield ac


VALID_INTENTS = {"WHAT", "WHY", "WHAT_TO_DO", "OUT_OF_DOMAIN"}
VALID_STATUSES = {"OK", "PENDING_APPROVAL", "ABSTAINED"}


class TestSlice1Unchanged:
    """All Slice 1 contract tests must still pass."""

    @pytest.mark.asyncio
    async def test_valid_question_returns_200(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_has_all_required_fields(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        body = resp.json()
        assert "answer" in body
        assert "intent" in body
        assert "citations" in body
        assert "confidence" in body
        assert "status" in body

    @pytest.mark.asyncio
    async def test_answer_is_string(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert isinstance(resp.json()["answer"], str)

    @pytest.mark.asyncio
    async def test_intent_is_valid(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert resp.json()["intent"] in VALID_INTENTS

    @pytest.mark.asyncio
    async def test_citations_is_list(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert isinstance(resp.json()["citations"], list)

    @pytest.mark.asyncio
    async def test_confidence_is_float(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert isinstance(resp.json()["confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_confidence_in_range(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        c = resp.json()["confidence"]
        assert 0.0 <= c <= 1.0

    @pytest.mark.asyncio
    async def test_status_is_valid(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert resp.json()["status"] in VALID_STATUSES

    @pytest.mark.asyncio
    async def test_content_type(self, client):
        resp = await client.post("/ask", json={"question": "test"})
        assert resp.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_missing_question_returns_422(self, client):
        resp = await client.post("/ask", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_malformed_json_returns_400(self, client):
        resp = await client.post("/ask", content=b"not json", headers={"content-type": "application/json"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_not_allowed(self, client):
        resp = await client.get("/ask")
        assert resp.status_code == 405


class TestSlice2Unchanged:
    """Slice 2 intent routing must still work."""

    @pytest.mark.asyncio
    async def test_why_question_returns_why_intent(self, client):
        resp = await client.post("/ask", json={"question": "Why did SparkClean sales spike in Mumbai?"})
        assert resp.json()["intent"] == "WHY"

    @pytest.mark.asyncio
    async def test_what_to_do_question_returns_what_to_do_intent(self, client):
        resp = await client.post("/ask", json={"question": "What should we do about the stockout?"})
        assert resp.json()["intent"] == "WHAT_TO_DO"

    @pytest.mark.asyncio
    async def test_out_of_domain_returns_out_of_domain(self, client):
        resp = await client.post("/ask", json={"question": "What is the weather today?"})
        assert resp.json()["intent"] == "OUT_OF_DOMAIN"
        assert resp.json()["status"] == "ABSTAINED"


class TestSlice3WhatAgent:
    """WHAT agent produces real data-driven answers."""

    @pytest.mark.asyncio
    async def test_what_returns_what_intent(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert resp.json()["intent"] == "WHAT"

    @pytest.mark.asyncio
    async def test_what_returns_ok_status(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert resp.json()["status"] == "OK"

    @pytest.mark.asyncio
    async def test_what_has_citations(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert len(resp.json()["citations"]) > 0

    @pytest.mark.asyncio
    async def test_what_answer_has_numbers(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert any(c.isdigit() for c in resp.json()["answer"])

    @pytest.mark.asyncio
    async def test_glucojoy_north_nov2025(self, client):
        resp = await client.post("/ask", json={
            "question": "What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?"
        })
        body = resp.json()
        assert body["intent"] == "WHAT"
        assert body["status"] == "OK"
        assert "861,938" in body["answer"]
        assert "1,026,116" in body["answer"]
        assert len(body["citations"]) >= 2

    @pytest.mark.asyncio
    async def test_sparkclean_1kg_mumbai_sep2025(self, client):
        resp = await client.post("/ask", json={
            "question": "What were SparkClean 1kg primary sales in Mumbai in September 2025?"
        })
        body = resp.json()
        assert body["intent"] == "WHAT"
        assert body["status"] == "OK"
        assert "176,779" in body["answer"]

    @pytest.mark.asyncio
    async def test_how_many_units(self, client):
        resp = await client.post("/ask", json={"question": "How many units were sold in July 2025?"})
        body = resp.json()
        assert body["intent"] == "WHAT"
        assert body["status"] == "OK"

    @pytest.mark.asyncio
    async def test_what_confidence_high(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert resp.json()["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_what_question_not_using_placeholder(self, client):
        resp = await client.post("/ask", json={"question": "What were the sales for July 2025?"})
        assert "Slice 3" not in resp.json()["answer"]


class TestSlice4Unchanged:
    """Slice 4 WHY agent must still work."""

    @pytest.mark.asyncio
    async def test_why_question_returns_why_intent(self, client):
        resp = await client.post("/ask", json={"question": "Why did SparkClean sales spike in Mumbai?"})
        assert resp.json()["intent"] == "WHY"

    @pytest.mark.asyncio
    async def test_why_has_citations(self, client):
        resp = await client.post("/ask", json={"question": "Why did SparkClean sales spike in Mumbai?"})
        assert len(resp.json()["citations"]) > 0


class TestSlice5WhatToDo:
    """WHAT_TO_DO agent produces evidence-based recommendations."""

    @pytest.mark.asyncio
    async def test_what_to_do_returns_correct_intent(self, client):
        resp = await client.post("/ask", json={"question": "What should we do about the stockout in Chennai?"})
        assert resp.json()["intent"] == "WHAT_TO_DO"

    @pytest.mark.asyncio
    async def test_what_to_do_has_citations(self, client):
        resp = await client.post("/ask", json={"question": "What should we do about the stockout in Chennai?"})
        assert len(resp.json()["citations"]) > 0

    @pytest.mark.asyncio
    async def test_what_to_do_has_valid_status(self, client):
        resp = await client.post("/ask", json={"question": "What should we do about the stockout in Chennai?"})
        assert resp.json()["status"] == "PENDING_APPROVAL"

    @pytest.mark.asyncio
    async def test_what_to_do_answer_has_content(self, client):
        resp = await client.post("/ask", json={"question": "Recommend actions to improve SparkClean sales"})
        assert len(resp.json()["answer"]) > 0

    @pytest.mark.asyncio
    async def test_what_to_do_unknown_abstains(self, client):
        resp = await client.post("/ask", json={"question": "What should I have for dinner?"})
        assert resp.json()["status"] == "ABSTAINED"