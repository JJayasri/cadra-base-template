"""FastAPI application for Suryaa Sales Investigation."""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.agents.router import classify_intent
from src.agents.what_agent import WhatAgent
from src.agents.what_to_do_agent import WhatToDoAgent
from src.agents.why_agent import WhyAgent
from src.data.cleaner import clean_all
from src.data.doc_retriever import DocRetriever
from src.data.loader import load_all_csvs, get_cached_data

INTENT_RESPONSES = {
    "OUT_OF_DOMAIN": "This question is outside the scope of the Suryaa Sales data.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    raw = load_all_csvs()
    cleaned = clean_all(raw)
    app.state.data = cleaned
    retriever = DocRetriever()
    app.state.what_agent = WhatAgent(cleaned)
    app.state.why_agent = WhyAgent(cleaned, retriever)
    app.state.what_to_do_agent = WhatToDoAgent(cleaned, retriever, app.state.what_agent, app.state.why_agent)
    yield


app = FastAPI(title="Suryaa Sales Assistant", version="0.2.0", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("question must be a non-blank string")
        return stripped


class AskResponse(BaseModel):
    answer: str
    intent: str
    citations: list[str]
    confidence: float
    status: str


@app.post("/ask")
async def ask(body: AskRequest, request: Request) -> AskResponse:
    result = classify_intent(body.question)

    if result.intent == "OUT_OF_DOMAIN":
        return AskResponse(
            answer=INTENT_RESPONSES["OUT_OF_DOMAIN"],
            intent="OUT_OF_DOMAIN",
            citations=[],
            confidence=result.confidence,
            status="ABSTAINED",
        )

    if result.intent == "WHAT":
        agent: WhatAgent = request.app.state.what_agent
        query = agent.parse(body.question)
        if query is not None:
            exec_result = agent.execute(query)
            response = agent.format_response(query, exec_result)
            return AskResponse(
                answer=response["answer"],
                intent="WHAT",
                citations=response["citations"],
                confidence=response["confidence"],
                status=response["status"],
            )

    if result.intent == "WHY":
        agent: WhyAgent = request.app.state.why_agent
        response = agent.answer(body.question)
        return AskResponse(
            answer=response["answer"],
            intent="WHY",
            citations=response["citations"],
            confidence=response["confidence"],
            status=response["status"],
        )

    if result.intent == "WHAT_TO_DO":
        agent: WhatToDoAgent = request.app.state.what_to_do_agent
        response = agent.answer(body.question)
        return AskResponse(
            answer=response["answer"],
            intent="WHAT_TO_DO",
            citations=response["citations"],
            confidence=response["confidence"],
            status=response["status"],
        )

    return AskResponse(
        answer=INTENT_RESPONSES.get(result.intent, "Unable to process this question."),
        intent=result.intent,
        citations=[],
        confidence=result.confidence,
        status="OK",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for err in exc.errors():
        if err.get("type") in ("json_invalid", "value_error.jsondecode"):
            return JSONResponse(status_code=400, content={"detail": "Malformed JSON"})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "answer": "An internal error occurred while processing your request.",
            "intent": "OUT_OF_DOMAIN",
            "citations": [],
            "confidence": 0.0,
            "status": "ABSTAINED",
        },
    )


@app.get("/ask")
async def ask_get():
    raise HTTPException(status_code=405, detail="Method Not Allowed")


@app.get("/health")
async def health():
    return {"status": "ok"}