# Approach-Phase AI Chat Transcripts — Suryaa Sales Investigation

## Session 1: Problem Analysis & Architecture Design

**User**: read the readme, requirements file, solution.py, approach.md, artefact.md, Data folder to understand the data, docs present in it, data related to it. write no implementation code, produce: 1. api contract as a table 2. evaluation criteria 3. file tree 4. vertical slices in build order 5. per slice verification commands

**Assistant**: [Analyzed all files. Produced comprehensive API contract table, evaluation criteria, file tree with 22 files across src/data, src/agents, src/llm, and tests/ directories, 5 vertical slices from deployable skeleton through WHAT_TO_DO agent, and verification commands per slice.]

**Key decisions made**:
- FastAPI as the web framework (async, production-grade, Pydantic contract validation)
- Keyword-heuristic routing (deterministic, testable, replaceable with LLM later)
- pandas-based data loading and cleaning
- 5 vertical slices: Skeleton → Router/Data → WHAT → WHY → WHAT_TO_DO
- Chose 0.0–1.0 confidence range (standard ML convention)

---

## Session 2: Data Exploration & Quality Assessment

**User**: examine all 8 CSV files and 30 unstructured documents in Data/docs/. Identify all data quality issues.

**Assistant**: Found 10+ data quality issues:
1. Date format inconsistencies (4 formats in same column)
2. Column name inconsistencies (material_no, item_code, sku, sku_code)
3. Sentinel values (#N/A, NA, -1, 9999, blank)
4. Currency formatting (plain, comma-separated, Rs-prefixed, quoted)
5. Territory aliases (BLR→Bengaluru, Bombay→Mumbai)
6. Distributor ID leading zero (0DEL-D1)
7. Duplicate SKU entries (gj-001 / GJ-001)
8. Region naming inconsistency (S vs South, E vs East)
9. Tier column casing inconsistency (VAL, value, Value, PREM, Premium)
10. Promotions data has "North" as territory (should be region-level)

**Red herrings identified**:
- `promo_note_redherring_02b.txt` (claims false attribution)
- `hr_note_14.txt` (expense claims — irrelevant)
- `distributor_note_13.txt` (no impact on current sales)
- 16 routine notes (17–34) with no actionable content

---

## Session 3: Intent Router Design

**User**: design the intent router. Must handle WHAT, WHY, WHAT_TO_DO, OUT_OF_DOMAIN. Clean interface for LLM swap.

**Assistant**: Designed `router.py` with:
- `IntentResult` dataclass (intent + confidence)
- Domain keyword gate (40+ FMCG/sales terms)
- Pattern-based scoring (WHAT: "what were", "how many"; WHY: "why did", "what caused"; WHAT_TO_DO: "what should", "recommend")
- Weighted by pattern phrase length
- Default WHAT (0.5) when no pattern matches but domain keywords present

---

## Session 4: Data Cleaner Design

**User**: design the data cleaning pipeline. Must handle all identified quality issues.

**Assistant**: Designed table-aware cleaner with:
- `normalize_column_names()` — aliases per table
- `normalize_dates()` — 4 date format parser + month column
- `clean_sentinels()` — #N/A, -1, 9999, blank → NaN
- `clean_primary_sales_value()` — Rs/comma/quote stripping
- `normalize_territory_names()` — BLR→Bengaluru, Bombay→Mumbai
- `_normalize_sku_codes()` — uppercase + strip
- `_normalize_tier_column()` — VAL→Value, PREM→Premium, etc.
- `_clean_distributor_ids()` — strip leading 0
- `_normalize_target_value_column()` — numeric conversion

---

## Session 5: Vertical Slice Planning

**User**: plan 5 vertical slices with TDD approach.

**Assistant**: 
- Slice 1: FastAPI skeleton, POST /ask, hardcoded response, 17 contract tests
- Slice 2: Data loader + cleaner + router, 76 tests
- Slice 3: WHAT agent (sum, target-vs-actual, filters), 21 tests
- Slice 4: Doc retriever + WHY agent (doc-based explanations), 34 tests
- Slice 5: WHAT_TO_DO agent (evidence-based recommendations), 24 tests

---

## Session 6: Confidence Threshold Design

**User**: define confidence thresholds for the three status levels.

**Assistant**: 
- OK: confidence ≥ 0.7 (strong evidence, reliable answer) — used for WHAT and WHY
- PENDING_APPROVAL: confidence 0.3–0.7 (moderate evidence, human review needed) — used for WHAT_TO_DO always per spec
- ABSTAINED: confidence < 0.3 (insufficient evidence, cannot answer)

Per spec: WHAT_TO_DO always returns PENDING_APPROVAL (recommendations require human approval).