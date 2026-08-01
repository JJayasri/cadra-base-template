# Suryaa Sales Investigation — Multi-Agent FMCG Assistant

Starter repository for the Cadra F1 walking-skeleton capstone. Implements a production-grade multi-agent assistant answering WHAT / WHY / WHAT_TO_DO questions over 8 CSV tables and 30 unstructured documents from Suryaa Consumer Products Ltd (Indian FMCG).

**Repository**: https://github.com/JJayasri/cadra-base-template
**Live HTTPS endpoint**: `https://cadra-base-template.onrender.com/ask`

---

## Grader Verification Checklist

Follow these steps in order to verify all submission requirements.

### Step 1: File Existence & Completeness

```bash
# Verify all required deliverables exist
echo "=== Deliverable Files ==="
for f in \
  src/solution.py src/app.py \
  APPROACH.md ARTEFACT.md ARTEFACT.html RECONCILIATION.md USAGE.md \
  transcripts/approach_phase.md transcripts/build_phase.md \
  evals/run.py pytest.ini requirements.txt opencode.json; do
  [ -f "$f" ] && echo "  OK $f" || echo "  MISSING $f"
done
```

### Step 2: Read APPROACH.md (Sections A-D)

Verify the approach document contains all four required sections:

```bash
echo "Section A:"; grep -c "Problem Decomposition" APPROACH.md
echo "Section B:"; grep -c "Agentic Construct Design" APPROACH.md
echo "Section C:"; grep -c "Data Interaction Design" APPROACH.md
echo "Section D:"; grep -c "Risk Awareness" APPROACH.md
```

### Step 3: Read ARTEFACT.md / ARTEFACT.html

Verify the analytical findings report includes GlucoJoy North Nov analysis, SparkClean Mumbai promo-spike analysis, GlucoJoy Delhi stockout analysis, and data quality observations.

### Step 4: Read RECONCILIATION.md

Verify it contains: national 52-week primary sales total (INR ~1.5B), top-3 data-quality fixes ranked by rows affected, returns/unit-mixing rule, excluded records with reasons.

### Step 5: Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 6: Run Full Test Suite

```bash
python -m pytest tests/ -v --tb=short
```

Expected: **212 passed, 0 failed**

### Step 7: Run Evaluation Harness

```bash
python evals/run.py
```

Expected: **11/11 passed** (5 WHAT + 3 WHY + 3 WHAT_TO_DO)

### Step 8: Start Server & Verify API

```bash
python -m src.solution &
sleep 4
```

Test each endpoint:

```bash
# 8a — Schema: all 5 fields (answer, intent, citations, confidence, status)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"test"}' | python3 -m json.tool

# 8b — WHAT query (aggregated sales)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What were GlucoJoy'\''s monthly primary sales vs target in the North region in November 2025?"}'

# 8c — WHY query (non-empty citations required)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?"}'

# 8d — WHAT_TO_DO (must return status=PENDING_APPROVAL)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What should we do about the stockout in Chennai?"}'

# 8e — OUT_OF_DOMAIN (must return status=ABSTAINED)
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the weather today?"}'

# 8f — 422 on missing question
curl -s -w '\nHTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -d '{}'

# 8g — 405 on GET
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ask
```

### Step 9: Verify HTTPS Deployed Endpoint

Repeat Step 8 using the live HTTPS URL:

```bash
BASE="https://cadra-base-template.onrender.com"
curl -s -X POST "$BASE/ask" -H 'Content-Type: application/json' \
  -d '{"question":"What were the sales for July 2025?"}'
```

### Step 10: Verify Chat Transcripts

```bash
echo "Approach phase: $(wc -l < transcripts/approach_phase.md) lines"
echo "Build phase:    $(wc -l < transcripts/build_phase.md) lines"
```

### Step 11: Verify Solution Entry Point

```bash
python3 -c "from src.solution import main; print('solution.py loads OK')"
```

---

## API Contract

`POST /ask` with `{"question": "..."}` returns:

```json
{
  "answer": "string",
  "intent": "WHAT | WHY | WHAT_TO_DO | OUT_OF_DOMAIN",
  "citations": ["string"],
  "confidence": 0.85,
  "status": "OK | PENDING_APPROVAL | ABSTAINED"
}
```

**Status rules**:
- WHAT/WHY with strong evidence -> OK
- WHAT_TO_DO (always, per spec) -> PENDING_APPROVAL
- Unanswerable / false premise -> ABSTAINED

---

## Repository Structure

```
.
├── APPROACH.md                  # Approach doc (Sections A-D)
├── ARTEFACT.md                  # Analytical findings report
├── ARTEFACT.html                # HTML version
├── RECONCILIATION.md            # Reconciliation report
├── USAGE.md                     # Deployment & API usage
├── opencode.json                # Cadra provider config
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest config
├── evals/run.py                 # Evaluation harness (11 cases)
├── transcripts/
│   ├── approach_phase.md        # Approach AI chat transcripts
│   └── build_phase.md           # Build AI chat transcripts
├── src/
│   ├── solution.py              # Entry point
│   ├── app.py                   # FastAPI application
│   ├── agents/
│   │   ├── router.py            # Intent classifier
│   │   ├── what_agent.py        # WHAT aggregation engine
│   │   ├── why_agent.py         # WHY causal analysis
│   │   └── what_to_do_agent.py  # WHAT_TO_DO recommendations
│   └── data/
│       ├── loader.py            # CSV loader
│       ├── cleaner.py           # Data cleaning pipeline
│       └── doc_retriever.py     # Document search
├── tests/                       # 212 pytest tests
│   ├── test_contract.py         # API contract (17 tests)
│   ├── test_loader.py           # Data loader (11 tests)
│   ├── test_cleaner.py          # Data cleaning (34 tests)
│   ├── test_router.py           # Intent router (31 tests)
│   ├── test_doc_retriever.py    # Doc search (17 tests)
│   ├── test_what_agent.py       # WHAT agent (21 tests)
│   ├── test_why_agent.py        # WHY agent (17 tests)
│   ├── test_what_to_do_agent.py # WHAT_TO_DO agent (24 tests)
│   └── test_integration.py      # Integration (40 tests)
├── Data/
│   ├── dim_*.csv                # 4 dimension tables
│   ├── fact_*.csv               # 2 fact tables
│   ├── promotions.csv           # Promotions calendar
│   ├── stockouts.csv            # Stockout events
│   └── docs/                    # 30 unstructured documents
└── problem_statement.txt        # Original assignment brief
```