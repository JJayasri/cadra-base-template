# Approach: Suryaa Sales Investigation — Multi-Agent Assistant

## Problem Summary

Build a production-grade multi-agent assistant that answers What / Why / What-to-do questions over structured (8 CSV tables) and unstructured (30 text documents) data from Suryaa Consumer Products Ltd, an Indian FMCG company. The system exposes a single `POST /ask` endpoint with a fixed JSON contract. The two canonical questions are: (1) "Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?" and (2) "What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?"

### Key constraints
- No LLM calls for inference (keyword-heuristic routing only; architecture is LLM-swappable)
- All answers must be grounded in the provided data files
- Response must follow the exact contract: `{answer, intent, citations, confidence, status}`

---

## Section A — Problem Decomposition

The solution supports four analytical question types, each with a specific structured output:

| Question Type | Example | Structured Output |
|---|---|---|
| **WHAT** | "What were GlucoJoy's monthly sales vs target in North in Nov 2025?" | Aggregated numeric result (sum, avg, target-vs-actual) with time grain (month/week), dimensional filters (brand, territory, region, category), and source table citations |
| **WHY** | "Why did SparkClean 1kg sales spike in Mumbai in week of 16 Sep 2025?" | Causal explanation grounded in retrieved documents, plus correlation with sales data; includes document references and table citations |
| **WHAT_TO_DO** | "What should we do about the stockout in Chennai?" | Evidence-based recommendation list where each item has: action text, supporting evidence, citations, and per-recommendation confidence score |
| **OUT_OF_DOMAIN** | "What is the weather today?" | ABSTAINED status with a message that the question is outside scope; empty citations |

### Structured output each should produce

- **WHAT**: `{sales_value, sales_units, target_value, metric, currency}` — computed from cleaned DataFrames
- **WHY**: `{finding, sales_value_before, sales_value_during, sales_value_after}` — correlated with sales data and doc evidence
- **WHAT_TO_DO**: `list[Recommendation{text, supporting_evidence, citations, confidence}]` — each grounded in data/docs
- **OUT_OF_DOMAIN**: Empty/ABSTAINED — no computation attempted

---

## Section B — Solution & Agentic Construct Design

### Methods chosen and why

**Keyword-heuristic routing** was chosen over LLM-based routing for reliability, determinism, and zero cost per inference. The three-layer architecture (router → agent → executor) makes it straightforward to swap any component for an LLM call later via the `IntentResult` / `WhatQuery` / `WhyQuery` / `WhatToDoQuery` dataclass interfaces.

**Data cleaning** uses pandas pipelines. The raw CSV data contains multiple date formats, sentinel values (#N/A, -1, 9999), inconsistent column names (material_no vs sku_code vs item_code), territory aliases (BLR→Bengaluru, Bombay→Mumbai), and value formatting issues (Rs prefix, comma separators). A table-aware cleaning pipeline normalizes all these.

**Document retrieval** uses keyword scoring with relevance boosts and distractor penalties — no embeddings needed for the small (30-document) corpus.

### Agentic construct — named steps

#### Intent Router (Slice 2)
- **Input**: Raw question string
- **Process**: Lowercase → domain keyword gate → pattern scoring (WHAT/WHY/WHAT_TO_DO patterns, weighted by phrase length)
- **Output**: `IntentResult{intent, confidence}`
- **Handoff**: Routes to WHAT agent, WHY agent, WHAT_TO_DO agent, or returns OUT_OF_DOMAIN
- **Failure path**: Empty domain match → OUT_OF_DOMAIN with 0.8 confidence

#### WHAT Agent (Slice 3)
- **Input**: `IntentResult{WHAT}`, cleaned data dict
- **Process**: Parse question for entities (brand, territory, region, category, pack_size, month, year) → build `WhatQuery` → filter sales DataFrame → aggregate (sum, target-vs-actual) → format response
- **Output**: `AskResponse{answer, intent="WHAT", citations, confidence, status}`
- **Handoff**: Returns directly as API response
- **Failure path**: Empty result set → ABSTAINED with 0.3 confidence

#### WHY Agent (Slice 4)
- **Input**: `IntentResult{WHY}`, cleaned data dict, `DocRetriever`
- **Process**: Parse question → search docs via `DocRetriever.search()` → correlate docs with sales context → format explanation with citations
- **Output**: `AskResponse{answer, intent="WHY", citations, confidence, status}`
- **Handoff**: Returns directly as API response
- **Failure path**: No relevant docs found → ABSTAINED

#### WHAT_TO_DO Agent (Slice 5)
- **Input**: `IntentResult{WHAT_TO_DO}`, cleaned data dict, `DocRetriever`, WHAT agent, WHY agent
- **Process**: Parse question → gather evidence from docs + stockout data + sales data → generate evidence-grounded recommendations with per-recommendation confidence → aggregate into response
- **Output**: `AskResponse{answer, intent="WHAT_TO_DO", citations, confidence, status}`
- **Handoff**: Returns directly as API response
- **Failure path**: No evidence found → ABSTAINED

### Confidence / Status mapping

| Confidence Range | Status | Meaning |
|---|---|---|
| ≥ 0.7 | OK | Strong evidence, answer is reliable |
| 0.3 – 0.7 | PENDING_APPROVAL | Moderate evidence, human review recommended |
| < 0.3 | ABSTAINED | Insufficient evidence, cannot answer |

---

## Section C — Data Interaction Design

### Dataset access

All 8 CSV files are loaded once at application startup via the `lifespan` context manager and cached in `app.state.data`. Each agent accesses the cleaned DataFrames by table name.

### Schema awareness

The cleaner normalizes all tables to a consistent schema:

| Canonical Column | Source Tables | Normalization Applied |
|---|---|---|
| `sku_code` | fact_primary_sales, fact_targets, stockouts, promotions, dim_sku | Uppercased, whitespace stripped; aliased from material_no, item_code, sku |
| `territory` | fact_primary_sales, fact_targets, dim_geo, dim_distributor, stockouts, promotions | Aliased from area; BLR→Bengaluru, Bombay→Mumbai |
| `region` | dim_geo | S→South, E→East |
| `week_start` | fact_primary_sales, stockouts, promotions | Parsed from 4+ date formats to datetime |
| `month` | fact_targets | Parsed from YYYY-MM format to datetime |
| `primary_sales_value` | fact_primary_sales | Rs prefix stripped, commas removed, cast to float |
| `target_value` | fact_targets | Cast to float |
| `primary_sales_units` | fact_primary_sales | Cast to float; sentinel values (-1, 9999) set to NaN |

### Aggregations

- **Time grain**: Weekly (fact_primary_sales) is aggregated to monthly via `dt.month` / `dt.year` extraction for month-level queries; day-level via `dt.isocalendar().week` for weekly queries
- **Dimensional hierarchy**: territory → region (via dim_geo join); SKU → brand/category/tier/pack_size (via dim_sku join)
- **Metric derivation**: Sales vs Target computed as `(sales - target) / target * 100` for percentage variance

---

## Section D — Risk Awareness & Trade-Off Reasoning

### Risk 1: Incorrect query generation
**Risk**: The keyword-heuristic question parser may misidentify entities (e.g., "SparkClean" matching as both brand and territory search term).
**Mitigation**: Entity extraction is layered — brand lookup via dim_sku table gives exact brand name; territory lookup uses a curated alias map; unknown terms are silently dropped rather than guessed. The WHAT agent's query result is never hallucinated; it only filters existing data.

### Risk 2: Hallucinated responses
**Risk**: The WHAT_TO_DO agent could generate recommendations not supported by data.
**Mitigation**: Every recommendation explicitly cites its evidence (doc ref, table name, or both). The `generate_recommendations` method only produces recommendations when it finds matching evidence in data or documents. If no evidence is found, the agent returns ABSTAINED.

### Risk 3: Data misinterpretation
**Risk**: `primary_sales_value` contains mixed formats (plain numbers, comma-separated, Rs-prefixed, quoted) so naive parsing could produce wrong aggregates.
**Mitigation**: A dedicated `clean_primary_sales_value()` function handles all observed formats. After cleaning, values are verified to be numeric via `pd.to_numeric(..., errors='coerce')`. Any unparseable values become NaN and are excluded from aggregation.

### Design trade-off: Keyword heuristics vs LLM
**Trade-off**: Keyword-based routing and entity extraction are less accurate than LLM-based approaches for nuanced language, but they are deterministic, zero-cost, and trivially testable. The clean `IntentResult` and `WhatQuery` dataclass interfaces mean that swapping to an LLM for any component requires changing only the function body, not the callers. This was chosen over building a full LLM pipeline because the problem emphasizes production-grade behavior (determinism, testability, no API costs) over conversational flexibility.

---

## AI Tool Usage

This solution was developed using OpenCode with the Cadra provider in a turn-constrained environment. The implementation followed a strict vertical-slice TDD approach:
- Slice 1: API contract skeleton (FastAPI + hardcoded response)
- Slice 2: Data loading/cleaning + intent router
- Slice 3: WHAT agent (aggregation engine)
- Slice 4: WHY agent (document retrieval + correlation)
- Slice 5: WHAT_TO_DO agent (evidence-based recommendations)

Each slice began with failing pytest tests, followed by implementation, then verification that all prior tests still pass. The development process is captured in the build-phase AI chat transcripts submitted alongside this document.

## Trade-offs & Limitations

1. **Keyword-based entity extraction** may miss subtle formulations or multi-word brand names with unusual casing.
2. **Document retrieval** uses simple keyword scoring; it may rank less relevant docs higher if they share common terms.
3. **WHY correlation** is primarily document-based; it does not compute explicit before/during/after sales deltas for statistical significance.
4. **WHAT_TO_DO recommendations** are rule-based templates keyed to detected topics; they cover the most common scenarios but may not address all edge cases.
5. **No authentication or rate limiting** — the API is open; these would be needed for production deployment.