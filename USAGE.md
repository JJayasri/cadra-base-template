# Suryaa Sales Assistant — Deployment & Usage Guide

## Live Endpoint (ngrok)

**Base URL**: `https://cadra-base-template.onrender.com`

**Note**: This is a permanent Render deployment. No tunnel setup needed.

---

## How to Use

### 1. Quick test (any terminal)

```bash
curl -s -X POST "https://cadra-base-template.onrender.com/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"test"}'
```

Expected output:
```json
{"answer":"This question is outside the scope...","intent":"OUT_OF_DOMAIN","citations":[],"confidence":0.8,"status":"ABSTAINED"}
```

### 2. WHAT query (aggregated sales data)

```bash
curl -s -X POST "https://cadra-base-template.onrender.com/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"What were GlucoJoy'\''s monthly primary sales vs target in the North region in November 2025?"}'
```

### 3. WHY query (causal analysis)

```bash
curl -s -X POST "https://cadra-base-template.onrender.com/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?"}'
```

### 4. WHAT_TO_DO query (recommendations)

```bash
curl -s -X POST "https://cadra-base-template.onrender.com/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"What should we do about the stockout in Chennai?"}'
```

---

## API Contract

| Field | Type | Values |
|---|---|---|
| `answer` | string | Natural-language answer |
| `intent` | string | `WHAT` / `WHY` / `WHAT_TO_DO` / `OUT_OF_DOMAIN` |
| `citations` | string[] | Source table names and document references |
| `confidence` | number | 0.0 – 1.0 |
| `status` | string | `OK` / `PENDING_APPROVAL` / `ABSTAINED` |

---

## Error Codes

| HTTP Code | Meaning |
|---|---|
| 200 | Success (valid response) |
| 400 | Malformed JSON body |
| 422 | Missing or empty `question` field |
| 405 | Wrong HTTP method (use POST) |
| 500 | Internal error (returns `ABSTAINED` schema) |

---

## Running Locally

```bash
source .venv/bin/activate
python -m src.solution
# Server starts at http://127.0.0.1:8000
```

## Running Tests & Eval

```bash
# Full test suite (212 tests)
python -m pytest tests/

# Evaluation harness (11 cases)
python evals/run.py
```