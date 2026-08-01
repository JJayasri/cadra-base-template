"""Evaluation harness for all intent types on the Suryaa Sales Assistant."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.cleaner import clean_all
from src.data.doc_retriever import DocRetriever
from src.data.loader import load_all_csvs
from src.agents.what_agent import WhatAgent
from src.agents.why_agent import WhyAgent
from src.agents.what_to_do_agent import WhatToDoAgent

WHAT_TEST_CASES = [
    {
        "question": "What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?",
        "expected_intent": "WHAT",
        "expected_sales": 861938.25,
        "expected_target": 1026116.06,
        "tolerance": 0.01,
    },
    {
        "question": "What were SparkClean 1kg primary sales in Mumbai in September 2025?",
        "expected_intent": "WHAT",
        "expected_sales": 176779.0,
        "tolerance": 0.01,
    },
    {
        "question": "How many units were sold in July 2025?",
        "expected_intent": "WHAT",
        "expected_units_min": 1,
    },
    {
        "question": "What were sales in the South region?",
        "expected_intent": "WHAT",
        "expected_sales_min": 1,
    },
    {
        "question": "What were the sales for Detergent?",
        "expected_intent": "WHAT",
        "expected_sales_min": 1,
    },
]

WHY_TEST_CASES = [
    {
        "question": "Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?",
        "expected_intent": "WHY",
        "expected_status": "OK",
        "expected_citation": "promo_circular_01",
    },
    {
        "question": "Why did GlucoJoy Choco 120g stockout in Delhi?",
        "expected_intent": "WHY",
        "expected_status": "OK",
        "expected_citation": "email_01",
    },
    {
        "question": "Why is the sky blue?",
        "expected_intent": "WHY",
        "expected_status": "ABSTAINED",
    },
]

WHAT_TO_DO_TEST_CASES = [
    {
        "question": "What should we do about the stockout in Chennai?",
        "expected_intent": "WHAT_TO_DO",
        "expected_status": "PENDING_APPROVAL",
        "min_citations": 1,
    },
    {
        "question": "Recommend actions to improve SparkClean sales",
        "expected_intent": "WHAT_TO_DO",
        "expected_status": "PENDING_APPROVAL",
        "min_citations": 1,
    },
    {
        "question": "What should I have for dinner?",
        "expected_intent": "WHAT_TO_DO",
        "expected_status": "ABSTAINED",
    },
]


def _evaluate_what(agent, tc):
    q = tc["question"]
    parsed = agent.parse(q)
    if parsed is None:
        return False, {"reason": "parse returned None"}
    result = agent.execute(parsed)
    formatted = agent.format_response(parsed, result)
    checks = []
    checks.append(("intent", formatted["intent"] == tc["expected_intent"]))
    if "expected_sales" in tc:
        tol = tc.get("tolerance", 0.01)
        sales_ok = result is not None and abs(result.sales_value - tc["expected_sales"]) <= tol * tc["expected_sales"]
        checks.append(("sales_value", sales_ok))
    if "expected_target" in tc:
        tol = tc.get("tolerance", 0.01)
        ok = result is not None and result.target_value is not None and abs(result.target_value - tc["expected_target"]) <= tol * tc["expected_target"]
        checks.append(("target_value", ok))
    if "expected_units_min" in tc:
        ok = result is not None and result.sales_units is not None and result.sales_units >= tc["expected_units_min"]
        checks.append(("units >= min", ok))
    if "expected_sales_min" in tc:
        ok = result is not None and result.sales_value is not None and result.sales_value >= tc["expected_sales_min"]
        checks.append(("sales >= min", ok))
    all_ok = all(v for _, v in checks)
    return all_ok, {"intent": formatted["intent"], "checks": dict(checks)}


def _evaluate_why(agent, tc):
    q = tc["question"]
    response = agent.answer(q)
    checks = []
    checks.append(("intent", response["intent"] == tc["expected_intent"]))
    if "expected_status" in tc:
        checks.append(("status", response["status"] == tc["expected_status"]))
    if "expected_citation" in tc:
        checks.append(("citation", tc["expected_citation"] in response["citations"]))
    all_ok = all(v for _, v in checks)
    return all_ok, {"intent": response["intent"], "status": response["status"], "citations": response["citations"], "checks": dict(checks)}


def _evaluate_what_to_do(agent, tc):
    q = tc["question"]
    response = agent.answer(q)
    checks = []
    checks.append(("intent", response["intent"] == tc["expected_intent"]))
    if "expected_status" in tc:
        checks.append(("status", response["status"] == tc["expected_status"]))
    elif "expected_status_in" in tc:
        checks.append(("status", response["status"] in tc["expected_status_in"]))
    if "min_citations" in tc:
        checks.append(("citations >= min", len(response["citations"]) >= tc["min_citations"]))
    all_ok = all(v for _, v in checks)
    return all_ok, {"intent": response["intent"], "status": response["status"], "citations": response["citations"], "checks": dict(checks)}


def evaluate():
    print("=" * 70)
    print("  Suryaa Sales Assistant — Full Evaluation")
    print("=" * 70)

    raw = load_all_csvs()
    data = clean_all(raw)
    retriever = DocRetriever()
    what_agent = WhatAgent(data)
    why_agent = WhyAgent(data, retriever)
    what_to_do_agent = WhatToDoAgent(data, retriever, what_agent, why_agent)

    suites = [
        ("WHAT", WHAT_TEST_CASES, what_agent, _evaluate_what),
        ("WHY", WHY_TEST_CASES, why_agent, _evaluate_why),
        ("WHAT_TO_DO", WHAT_TO_DO_TEST_CASES, what_to_do_agent, _evaluate_what_to_do),
    ]

    total_pass = 0
    total_fail = 0
    total_cases = 0

    for suite_name, cases, agent_fn, eval_fn in suites:
        print(f"\n  ─── {suite_name} ({len(cases)} cases) ───")
        for tc in cases:
            total_cases += 1
            ok, detail = eval_fn(agent_fn, tc)
            if ok:
                total_pass += 1
                print(f"  ✓ [{suite_name}] {tc['question'][:65]}...")
            else:
                total_fail += 1
                print(f"  ✗ [{suite_name}] {tc['question'][:65]}...")
                for k, v in detail.get("checks", {}).items():
                    if not v:
                        print(f"       ⤷ {k}: FAIL")

    print()
    print("=" * 70)
    print(f"  Results: {total_pass}/{total_cases} passed ({total_fail} failed)")
    print("=" * 70)
    return total_pass, total_fail


if __name__ == "__main__":
    evaluate()