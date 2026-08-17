# Citeable — AI Retrieval Engineering & Optimization System

Citeable is a diagnostic engine that audits why a website fails to appear in AI-generated answers and citations (ChatGPT, Perplexity, Google AI Overviews, Claude, etc.). It runs a multi-stage audit pipeline — crawler access, authority signals, content extractability, schema/structured data, citation sampling — against a target domain and returns a scored report with a remediation plan.

This README covers the shipped application: the FastAPI backend, the static UI it serves, and how to run or deploy it. It intentionally does **not** duplicate the API reference or architecture deep-dives — those live under `docs/` (see [Further documentation](#further-documentation)).

---

## What's in this repo

```text
areos/
├── api/                 # FastAPI app, routers, request/response models
│   ├── main.py          #   App factory, lifespan (DB migration + shutdown), static mounts
│   ├── dependencies.py  #   Auth (verify_admin), DB path resolution, BYOK key extraction
│   └── routers/         #   claims, approvals, audit, verdicts, reports, outcomes, prompts
├── auditors/            # The actual audit logic (authority, schema, content-format, robots, ...)
├── cli/                 # Command-line tools (approve, critique, diff, report, research)
├── db/                  # Connection pooling + schema migration + KB seeding (ingest_claims.py)
├── jobs/                # Background job runners
├── llm/                 # 11-provider LLM waterfall (Gemini → Groq → OpenAI → ... → Ollama)
├── services/             # Research/backfill services, caching
├── ui/                   # Static frontend served at /ui
└── util/                 # Logging, shared helpers

tests/                   # pytest suite (routers, auditors, schema)
migrations/               # One-off standalone migration scripts (run manually, not on startup)
schema.sql                # Generated DB schema — do not hand-edit, see file header
Dockerfile                 # Production image, targets Render.com
render.yaml                 # Render Blueprint (service, disk, env vars)
requirements.txt / requirements-dev.txt
conftest.py                # pytest bootstrap (sets Citeable_API_TOKEN, isolates test DB)
```

Root-level research notes, crawl datasets, and build scripts used while developing Citeable (the numbered `01_...` through `07_...` directories, and one-off `fix_*.py` / `refactor_*.py` / `update_*.py` scripts) are excluded from git and from the Docker build via `.gitignore` / `.dockerignore`. They're local working material, not part of the shipped app.

---

## Running locally

Requires Python 3.11+.

```bash
pip install -r requirements.txt

# Required — the app refuses to start without this (fail-closed by design)
export Citeable_API_TOKEN="choose-a-real-secret-here"

uvicorn areos.api.main:app --reload --port 8000
```

On startup, `main.py`'s `lifespan` handler runs `migrate()` against the DB (creating `areos.db` in the repo root if it doesn't exist yet) before the app accepts requests.

- UI: `http://localhost:8000/ui/`
- API docs (Swagger): `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/api/health` — verifies the DB is actually reachable, not just that the process is alive
- Static docs mount (if `docs/` exists in the repo root): `http://localhost:8000/docs/`

Every write endpoint requires an `Authorization: Bearer <Citeable_API_TOKEN>` header. Example:

```bash
curl -X POST http://localhost:8000/api/v1/audit/orchestrate \
  -H "Authorization: Bearer $Citeable_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_domain": "example.com", "sample_content": "...", "api_provider": "auto"}'
```

## Running with Docker

```bash
docker build -t areos .
docker run -p 8000:8000 -e Citeable_API_TOKEN="choose-a-real-secret-here" areos
```

The container reads `$PORT` at runtime (defaults to `8000` locally; Render sets this automatically). `RENDER=true` in the environment switches the DB path to `/data/areos.db` (see [Environment variables](#environment-variables)).

## Deploying to Render

This repo ships a ready-to-use `render.yaml` Blueprint:

1. Push the repo to GitHub and create a new **Blueprint** service on Render pointed at it.
2. Render will provision the service on the `starter` plan with a 1 GB persistent disk mounted at `/data` — **do not** downgrade to `free`, since free web services on Render can't attach a persistent disk, and the SQLite database (`/data/areos.db`) would be wiped on every restart/redeploy.
3. In the Render dashboard, set the required secret: `Citeable_API_TOKEN`.
4. Set any optional provider keys you want to enable (see table below) — all are `sync: false`, so they're set once in the dashboard and never touch git history.
5. Deploy. The `lifespan` startup hook applies DB migrations automatically; nothing else to run by hand.

## Environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `Citeable_API_TOKEN` | **Yes** | Admin bearer token. The app raises at import time and refuses to start if this is unset (fail-closed). |
| `OPEN_PAGERANK_API_KEY` | No | Enables live domain-authority lookups. Unset (or a failed call) falls back to deterministic heuristics rather than failing the audit. |
| `RENDER` | Set automatically by Render | Switches the DB path to `/data/areos.db` (the mounted persistent disk). Don't override. |
| `PERPLEXITY_API_KEY`, `Citeable_GEMINI_KEY_1`, `Citeable_GEMINI_KEY_2`, `Citeable_GEMINI_MODEL_1`, `OPENAI_API_KEY`, `Citeable_GROQ_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `AZURE_OPENAI_KEY` + `AZURE_OPENAI_BASE`, `CUSTOM_LLM_BASE` | No | LLM provider waterfall (`areos/llm/providers/__init__.py`) — tried in this order, first configured key wins per call. All optional; leave unset to skip that provider. Azure needs both `AZURE_OPENAI_KEY` and `AZURE_OPENAI_BASE` together or neither is used. |
| `Citeable_JINA_KEY` | No | Jina AI Reader, used by `areos/services/research_service.py` for clean web-content fetching. |

Client requests can also supply BYOK (bring-your-own-key) provider keys per-request via `x-api-key-<provider>` / `x-api-base-<provider>` headers, which take priority over the server-side env vars above (see `get_client_keys` in `areos/api/dependencies.py`).

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

`conftest.py` sets a default `Citeable_API_TOKEN` and pre-migrates an isolated SQLite DB before test collection, so the suite runs clean on a fresh checkout with no manual setup. `pyproject.toml`'s `addopts` excludes a handful of standalone verification scripts (`test_a3.py`, `test_research_command.py`, etc.) that are meant to be run directly with `python <script>.py`, not collected by pytest — most notably `test_research_command.py`, which makes real unmocked network calls and isn't suitable for CI.

A handful of tests that assert on specific `claim_id` wiring (e.g. `MISSING_REQUIRED_FIELD` → `C054`) accept either `WIRED` or `CLAIM_NOT_FOUND` and pass either way — `migrate()` (run automatically on every startup, and by `conftest.py` before the test suite) creates the `claims`/`check_code_mappings` *schema* but does not seed content. On a fresh deploy, the app boots and runs correctly; findings just come back `UNMAPPED` instead of citing a specific claim until the knowledge base is loaded (see below).

## Loading the knowledge base

`claims` and `check_code_mappings` ship empty on a clean checkout by design — seeding is a deliberate, separate step from schema migration:

```bash
python -m areos.db.ingest_claims
```

This loads Citeable's 119-record claims corpus (`active_claims.json`) into `claims`, then wires `check_code_mappings` on top, skipping anything that fails validation or references a claim that doesn't exist rather than fabricating data. Idempotent — safe to re-run. Full detail on what's loaded, what's skipped, and why, is in [`docs/architecture/knowledge-base-seeding.md`](docs/architecture/knowledge-base-seeding.md).

## Further documentation

Architecture notes, migration strategy, and other reference docs live under `docs/` (served at `/docs/` when the app is running) and are out of scope for this README.
