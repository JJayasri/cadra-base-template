"""Contract tests for POST /ask endpoint (Slice 1 — hardcoded skeleton)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app

BASE_URL = "http://test"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        yield ac


VALID_INTENTS = {"WHAT", "WHY", "WHAT_TO_DO", "OUT_OF_DOMAIN"}
VALID_STATUSES = {"OK", "PENDING_APPROVAL", "ABSTAINED"}


@pytest.mark.asyncio
async def test_ask_valid_question_returns_200(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ask_valid_question_has_all_required_fields(client):
    resp = await client.post("/ask", json={"question": "test"})
    body = resp.json()
    assert "answer" in body
    assert "intent" in body
    assert "citations" in body
    assert "confidence" in body
    assert "status" in body


@pytest.mark.asyncio
async def test_ask_valid_question_answer_is_string(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert isinstance(resp.json()["answer"], str)


@pytest.mark.asyncio
async def test_ask_valid_question_intent_is_valid(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert resp.json()["intent"] in VALID_INTENTS


@pytest.mark.asyncio
async def test_ask_valid_question_citations_is_list(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert isinstance(resp.json()["citations"], list)


@pytest.mark.asyncio
async def test_ask_valid_question_confidence_is_float(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert isinstance(resp.json()["confidence"], (int, float))


@pytest.mark.asyncio
async def test_ask_valid_question_confidence_in_range(client):
    resp = await client.post("/ask", json={"question": "test"})
    c = resp.json()["confidence"]
    assert 0.0 <= c <= 1.0


@pytest.mark.asyncio
async def test_ask_valid_question_status_is_valid(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert resp.json()["status"] in VALID_STATUSES


@pytest.mark.asyncio
async def test_ask_valid_question_content_type(client):
    resp = await client.post("/ask", json={"question": "test"})
    assert resp.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_ask_missing_question_returns_422(client):
    resp = await client.post("/ask", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_null_question_returns_422(client):
    resp = await client.post("/ask", json={"question": None})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_empty_string_question_returns_422(client):
    resp = await client.post("/ask", json={"question": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_whitespace_question_returns_422(client):
    resp = await client.post("/ask", json={"question": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_non_string_question_returns_422(client):
    resp = await client.post("/ask", json={"question": 42})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ask_malformed_json_returns_400(client):
    resp = await client.post("/ask", content=b"not json", headers={"content-type": "application/json"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ask_errors_are_json(client):
    resp = await client.post("/ask", json={})
    assert resp.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_ask_method_not_allowed(client):
    resp = await client.get("/ask")
    assert resp.status_code == 405