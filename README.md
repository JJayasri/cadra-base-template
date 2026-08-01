# F1 Capstone Template

Starter repository for the Cadra F1 walking-skeleton capstone. Use OpenCode with the Cadra provider to build your solution, document your approach, and submit a public GitHub repo for evaluation.

## Deployed Endpoint

**HTTPS URL**: `https://fb6f-2405-201-c03a-800a-28f7-8d0a-43fa-e1ea.ngrok-free.app/ask`

See [USAGE.md](USAGE.md) for API examples and curl commands.

## Prerequisites

- Python 3.11+
- [OpenCode](https://opencode.ai) ≥ 1.17.0
- A Cadra JWT (`CADRA_TOKEN`) from the F1 Setup page
- Your Cadra proxy URL (from the F1 Setup page)

## Setup

1. Clone this repo (or use it as a GitHub template).
2. Set the environment variables (both values come from the F1 Setup page):
   ```bash
   export CADRA_PROXY_URL=<your-proxy-url>   # e.g. https://your-proxy.example.com/v1
   export CADRA_TOKEN=<your-cadra-jwt>
   ```
   `opencode.json` reads both via `{env:…}` — no file edits needed.
3. Install OpenCode if not already installed (see [opencode.ai](https://opencode.ai)).
4. Run OpenCode in this directory:
   ```bash
   opencode
   ```
5. Complete `APPROACH.md` and implement your solution in `src/` (start with `src/solution.py`).
6. Push your work to a **public** GitHub repository.
7. Submit your repo URL on the F1 demo page.

## Python environment (optional)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Project layout

```
.
├── opencode.json           # Cadra provider config
├── APPROACH.md             # Approach document (Sections A-D)
├── ARTEFACT.md             # Written deliverable / findings report
├── ARTEFACT.html           # HTML version of deliverable
├── RECONCILIATION.md       # Reconciliation report
├── USAGE.md                # Deployment & API usage guide
├── transcripts/
│   ├── approach_phase.md   # AI chat transcripts (approach)
│   └── build_phase.md      # AI chat transcripts (build)
├── src/
│   ├── app.py              # FastAPI application
│   ├── solution.py         # Entry point (uvicorn runner)
│   ├── agents/
│   │   ├── router.py       # Intent classifier
│   │   ├── what_agent.py   # WHAT aggregation engine
│   │   ├── why_agent.py    # WHY causal analysis
│   │   └── what_to_do_agent.py  # WHAT_TO_DO recommendations
│   └── data/
│       ├── loader.py       # CSV loader + cache
│       ├── cleaner.py      # Data cleaning pipeline
│       └── doc_retriever.py # Document search engine
├── tests/                  # 212 pytest tests
├── evals/run.py            # Evaluation harness (11 cases)
├── Data/                   # Source data (8 CSVs + 30 docs)
└── requirements.txt
```

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/          # 212 tests
python evals/run.py              # 11 eval cases
python -m src.solution           # Start API server
```
