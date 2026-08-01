# Build-Phase AI Chat Transcripts — Suryaa Sales Investigation

## Slice 1: Deployable Skeleton

**User**: implement slice 1 using TDD — write pytest contract tests first, implement minimal FastAPI app, run tests, verify with uvicorn.

**Assistant**: Created:
- `tests/test_contract.py` — 17 tests covering: 200 OK, all 5 response fields present, field types, valid intent/status enums, confidence range 0.0–1.0, content-type JSON, 422 for missing/empty/null/non-string question, 400 for malformed JSON, 405 for GET
- `src/app.py` — FastAPI with `POST /ask`, hardcoded response `{"answer":"Hello from Suryaa AI","intent":"WHAT","citations":[],"confidence":0.5,"status":"OK"}`
- Pydantic `AskRequest` with `@field_validator` for blank rejection
- Custom exception handlers for 400 (malformed JSON) and 422 (validation)
- GET /ask → 405

**Verification**: 17/17 tests passed, curl confirmed 200/422/400/405

---

## Slice 2: Data Loading, Cleaning & Intent Router

**User**: implement slice 2 using TDD — loader, cleaner, router. Use keyword heuristics with clean LLM-swappable interface.

**Assistant**: Created:
- `src/data/loader.py` — `load_all_csvs()` with global cache, loads 8 CSVs
- `src/data/cleaner.py` — multi-stage pipeline: column aliases → date normalization → sentinel cleanup → value cleaning → territory normalization → SKU normalization → tier normalization → distributor ID cleanup → target value normalization
- `src/agents/router.py` — `classify_intent()` with `IntentResult` dataclass, domain keyword gate, pattern scoring
- Updated `src/app.py` — lifespan loads+cleans data, wires router into POST /ask
- 11 loader tests, 34 cleaner tests, 31 router tests

**Key issue encountered**: `primary_sales_units` was stored as strings after `clean_sentinels`, causing `sum()` to concatenate instead of add. Fixed by adding `pd.to_numeric()` in `clean_sentinels`.

**Verification**: 120/120 passed across all 4 test files

---

## Slice 3: WHAT Agent

**User**: implement WHAT agent using TDD — aggregation engine supporting sum, average, target vs actual, month/week/geo/product filtering. Use cleaned data. Include citations. Do not modify existing behavior.

**Assistant**: Created:
- `src/agents/what_agent.py` — `WhatAgent` class with `parse()`, `execute()`, `format_response()`
- Entity extraction: brand, territory, region, category, pack_size, month, year
- Aggregation: sum, target-vs-actual with percentage variance
- Citations: fact_primary_sales, fact_targets, dim_sku, dim_geo
- 21 tests covering parsing, execution, formatting, integration

**Key issue encountered**: Brand name matching failed because "GlucoJoy's" lowercased to "glucojoy's" didn't contain "glucoj" (typo in BRAND_NAMES). Fixed brand name list.

**Value verification**: GlucoJoy North Nov 2025 = INR 861,938.25 (confirmed against cleaned data)

**Verification**: 145/145 tests passed across all 7 test files

---

## Slice 4: WHY Agent

**User**: implement WHY agent using TDD — document retrieval over Data/docs, correlate with sales data, return evidence-grounded explanations with citations.

**Assistant**: Created:
- `src/data/doc_retriever.py` — loads all 30 docs, parses ref/title/content, keyword search with relevance boosts + distractor penalties
- `src/agents/why_agent.py` — parses WHY questions, retrieves docs, correlates with sales data, formats evidence-grounded explanations
- 17 doc retriever tests, 17 WHY agent tests

**Key design decision**: Doc scoring uses phrase matching + relevance boosts (promo → 3x, stockout → 3x, routine → 0.3x) with distractor penalties to suppress irrelevant docs.

**Verification**: 180/180 tests passed

---

## Slice 5: WHAT_TO_DO Agent

**User**: implement WHAT_TO_DO agent using TDD — evidence-based recommendations, reuse existing WHAT/WHY components, every recommendation must include text + evidence + citations + confidence, implement confidence thresholds.

**Assistant**: Created:
- `src/agents/what_to_do_agent.py` — `WhatToDoAgent` class with topic detection (stockout, sales, distributor, promotion, launch), evidence gathering via doc retriever + stockout data + sales data, rule-based recommendation generation
- 24 tests across parsing, evidence, recommendations, confidence thresholds, formatting

**Key design decision**: Recommendations are template-based keyed to detected topics. Each recommendation carries:
- Per-recommendation confidence (0.0–1.0)
- Supporting evidence string
- Citations list
- The agent never invents recommendations — only produces them when matching evidence exists

**Verification**: 212/212 tests passed

---

## Audit Fixes Session

**User**: fix all audit findings — WHAT_TO_DO always returns PENDING_APPROVAL per spec, create RECONCILIATION.md, create chat transcripts, add 500 error handler, complete APPROACH.md and ARTEFACT.md.

**Assistant**: 
- Fixed WHAT_TO_DO agent: removed OK status path, always returns PENDING_APPROVAL
- Created RECONCILIATION.md: national 52-week total (INR 1,525,676,586.94), top 3 fixes by rows affected (distributor IDs: 9,382 rows; value formatting: 9,416 rows; dates: 10,972 rows), returns/unit-mixing rule from SOP, excluded records with reasons
- Created chat transcripts (approach_phase.md + build_phase.md)
- Added `@app.exception_handler(Exception)` returning full API schema on 500
- Completed APPROACH.md with all 4 sections
- Completed ARTEFACT.md and ARTEFACT.html with analytical findings
- Updated solution.py with working uvicorn entry point

**Final verification**: 212/212 tests passed, 11/11 eval passed, all 6 curl endpoints verified