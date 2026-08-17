# Citeable Canonical Technical Truth

## 01 — Overview

**Purpose:** Explains what Citeable is, its core mission, and its foundational mechanics at a high level.

**TL;DR:** Citeable is a Python-based, evidence-backed AI-readiness auditor: Target → Crawl → Evaluate → Score → Enrich → Report.

**Read this if:** You are a new user, operator, or stakeholder needing a conceptual orientation of the system without getting bogged down in code.

**Sections inside:**
▸ 1.1 What Citeable is
▸ 1.2 What Citeable is not
▸ 1.3 Core Mechanics

### 1.1 What Citeable is
Citeable (Autonomous Research & Empirical Optimization System) is a Python backend engine designed to evaluate a target domain's "AI readiness." It converts a target domain name into a structured, evidence-backed audit report by running a strict pipeline of checks. The system crawls critical files like `robots.txt` and `llms.txt`, evaluates content format heuristics, samples live LLM citations, and computes a bounded readiness score (`SCORE_FLOOR=5` to `SCORE_CEILING=98`, `areos/auditors/scoring.py`). It maps its findings to a curated declarative knowledge base consisting of 217 claims (live count as of this revision — re-run `SELECT COUNT(*) FROM claims` against `areos.db` to verify current), subsequently generating a prioritised remediation plan delivered as a structured JSON report. 

### 1.2 What Citeable is not
To understand Citeable, it is critical to outline its boundaries:
- **Not a SaaS platform:** There are no user accounts.
- **Not a continuous monitor:** Audits are point-in-time snapshots triggered on demand. It does not store per-domain baselines for historical tracking.
- **Not a standard web app:** It avoids ORMs (using raw SQLite instead), AI SDKs (using raw HTTP requests), or asynchronous message queues (relying on a synchronous pipeline).

### 1.3 Core Mechanics
The system is built on a zero-dependency philosophy where possible, relying heavily on standard Python libraries and simple HTTP clients. The canonical entry point is `areos.api.main:app` running via `uvicorn`. Data persistence is handled purely by a single SQLite database (`areos.db`) running in WAL mode with thread-local connections and no hard deletes, ensuring a robust, append-only audit trail.

## 02 — The Complete AEO/GEO Audit Lifecycle

**Purpose:** Documents the full nine-phase real-world AEO/GEO audit process that Citeable's automated pipeline is a *part of*, not the whole of — and shows exactly which phases the codebase automates, partially automates, or doesn't touch at all.

**TL;DR:** `claims.stage_id` values `AP-01`..`AP-09` encode a governed, researched taxonomy of a full manual audit. Citeable's automated pipeline covers the mechanically-verifiable cores of AP-02, AP-03, AP-05, and AP-06. AP-01, AP-04, AP-08, AP-09 are out of scope by design. This is a **different** `AP-0X` namespace from `scoring.py`'s five scoring layers — see the collision warning in 2.4.

**Read this if:** You need to explain to a stakeholder (or another engineer) what Citeable does *not* do, or you're extending the Manual Review Wizard and need to know which knowledge-base claims justify a given guided-review card.

**Sections inside:**
▸ 2.1 Where this taxonomy comes from
▸ 2.2 The nine phases, by the numbers
▸ 2.3 Mapping phases to pipeline stages
▸ 2.4 Namespace collision warning: `AP-0X` means two different things
▸ 2.5 Known governance gaps in this taxonomy

### 2.1 Where this taxonomy comes from

Query `claims` grouped by `stage_id LIKE 'AP-%'` and the phase boundaries
fall out directly:

```sql
SELECT stage_id, COUNT(*) FROM claims
WHERE stage_id LIKE 'AP-%' GROUP BY stage_id ORDER BY stage_id;
--  AP-01 | 13   AP-02 | 36   AP-03 | 112  AP-04 | 5
--  AP-05 | 26   AP-06 | 3    AP-07 | 4    AP-08 | 4    AP-09 | 10
--  (sums to 213 of the live 217 claims; the remainder carry no stage_id)
```

The taxonomy itself was built by independently researching how a full
AEO/GEO audit is scoped and executed across five separate LLM transcripts
(ChatGPT, Claude, Deepseek, Qwen, Gemini), then treating cross-model
structural agreement as the signal for what belongs in the governed
knowledge base. That research process is itself logged as claims:
`M001`–`M006` (`claim_scope='audit-workflow'`, `claim_type='process_note'`)
document methodology-level observations about the source transcripts
themselves — e.g. `M006` notes that ChatGPT's own transcript independently
produced a self-summary claiming "roughly 220–280 distinct tasks" in a full
audit, which the synthesis found "structurally consistent" with the
four-tier automatability picture arrived at from all five models combined.
`M001`, `M002`, `M004`, `M005`, `M006` are `status='deprecated'`
(superseded once the final 9-phase/213-claim structure was settled);
`M003` remains `status='active'`. All are kept, not deleted, per the
no-hard-deletes policy (§1.3) — they're the audit trail for how this
taxonomy was arrived at, which matters if it's ever challenged or revised.

### 2.2 The nine phases, by the numbers

| stage_id | Phase | Claims | `claim_type='automatability_rating'` breakdown* |
|---|---|---|---|
| AP-01 | Business & Competitive Scoping | 13 | 2 human / 2 partial / 0 auto |
| AP-02 | Structured Data & Schema Validation | 36 | 1 human / 2 partial / 1 auto |
| AP-03 | Technical Crawlability & Site Access | 112 | 5 human / 2 partial / 5 auto |
| AP-04 | Content Quality & E-E-A-T Assessment | 5 | 1 human / 0 partial / 0 auto |
| AP-05 | AI Citation Testing | 26 | 4 human / 1 partial / 2 auto |
| AP-06 | Competitive & Authority Analysis | 3 | 1 human / 0 partial / 2 auto |
| AP-07 | Synthesis, Prioritization & Reporting | 4 | 2 human / 0 partial / 1 auto |
| AP-08 | Legal & ToS Compliance | 4 | 0 rated (all `claim_type='other'`) |
| AP-09 | Market & Tool Landscape Awareness | 10 | 0 rated (all `claim_type='other'`) |

\* Classified by keyword-matching each `automatability_rating` claim's
`statement` text for `"not-automatable"` / `"partially automatable"` /
`"fully automat"`. This is an approximate, text-pattern classification,
not a stored enum column — several claims per stage use phrasing this
pattern doesn't cleanly bucket (visible as the gap between the counts
above and each stage's `automatability_rating` claim total). If this
classification needs to be authoritative rather than approximate, add a
proper `automatability_tier` enum column rather than continuing to parse
free text — this is flagged as a real gap, not fixed here, since it's a
schema change outside the scope of a documentation pass.

AP-03 (112 claims — over half the entire audit-workflow corpus) is
disproportionately large because it's the phase with the most individually
enumerable, mechanically-checkable sub-rules (per-crawler `robots.txt`
directives, sitemap validation rules, etc.) — this is exactly why it's
also the phase Citeable automates most completely.

### 2.3 Mapping phases to pipeline stages

| Taxonomy phase | Citeable automation | Where in the codebase |
|---|---|---|
| AP-01 Business Scoping | Not automated — caller-provided input | `target_domain`, `funnel_stage` params to `run_orchestrated_audit()` |
| AP-02 Schema Validation | Automated (syntax/presence); NOT automated (semantic honesty match) | `auditors/schema_validator.py`; semantic check surfaces as a Manual Review card instead |
| AP-03 Crawlability | Automated | `auditors/audit_orchestrator.py` Steps 3.3–3.4; scoring Access layer |
| AP-04 Content/E-E-A-T | Not automated | Surfaces only via Manual Review card `C062` (`instruction_cards/C062_eeat_trustworthiness.md`) |
| AP-05 Citation Testing | Automated (execution); NOT automated (prompt design, attribution) | `auditors/citation_sampler.py`; attribution surfaces via cards `C073`, `C090` |
| AP-06 Competitive/Authority | Automated (metric pulls); NOT automated (PR-gap judgment) | `auditors/authority_auditor.py`; PR-gap judgment surfaces via card `C082` |
| AP-07 Synthesis/Reporting | Partially automated | `llm/synthesis_pipeline.py` (3-step LLM pass) + `services/report_generator.py`; final prioritization narrative requires the human verdicts collected via `manual_verdicts` before synthesis runs |
| AP-08 Legal/ToS | Not automated as a general capability; DOES directly constrain AP-05's implementation | `citation_sampler.py`'s provider allowlist (Perplexity, Gemini) exists *because of* AP-08 findings — see `TOS_CAVEAT` in `citation_sampler.py` |
| AP-09 Market/Tool Landscape | Not automated; contextual KB content only | No corresponding pipeline code — pure `claims` table content |

### 2.4 Namespace collision warning: `AP-0X` means two different things

`scoring.py` independently defines its own `AP-01`..`AP-05` as the five
*scoring layer* IDs (`LAYERS` dict, line ~50 — Access/Schema/Content/
Citation/Authority). This is a **completely separate namespace** from the
`claims.stage_id` taxonomy documented in this section, and the overlap is
coincidental, not a shared concept. Concretely: `AP-03` in `scoring.py`
means "Content Format" (a scoring dimension); `AP-03` in `claims.stage_id`
means "Technical Crawlability & Site Access" (an audit-workflow phase).
Nothing in the codebase currently disambiguates these two uses of the same
string at the type level — a future refactor should consider renaming one
of the two namespaces (e.g. `SCORE-01`..`SCORE-05` for the scoring layers)
to remove the collision outright rather than relying on doc callouts like
this one and like external.md §2.4 to keep them straight.

### 2.5 Known governance gaps in this taxonomy

- **No `automatability_tier` column.** As noted in 2.2, automatability is
  presently expressed only as free text inside `automatability_rating`
  claim statements, parsed by keyword-matching wherever the UI needs to
  render it.
- **The Manual Review Wizard's 14 instruction cards ARE 14 specific
  `AP-0X` claims, by shared ID.** This isn't a loose association — verified
  directly: every `card_id` in `cli/report.py`'s `INSTRUCTION_CARDS` (e.g.
  `C073`) is the literal `claim_id` of a claim in the `claims` table (e.g.
  `claims.claim_id='C073'`, `stage_id='AP-05'`, statement about causal
  attribution of citations — the same topic as
  `instruction_cards/C073_causal_attribution.md`). The wizard therefore
  only operationalizes 14 of the 213 `AP-0X` claims — specifically the 14
  a human previously decided were both (a) not/partially automatable and
  (b) worth building a dedicated guided-review card for. The other ~199
  `AP-0X` claims currently have no corresponding wizard card at all; they
  exist as governed knowledge but aren't yet surfaced as an actionable
  check anywhere in the product.
- **AP-08/AP-09 have zero `automatability_rating` claims.** Every claim in
  these two phases is `claim_type='other'` — they were captured as
  reference/context knowledge, not audit-workflow tasks, and were never
  passed through the same automatability-classification research pass the
  other seven phases received. Whether that's intentional (they're
  genuinely not "tasks" in the same sense) or an oversight in the original
  research pass is not resolved by anything currently in the repository.
- **`M001`–`M006` are the only claims with `claim_scope='audit-workflow'`
  and `claim_type='process_note'`** — i.e. the only claims that document
  *how the taxonomy itself was built*, rather than *what the taxonomy
  says*. If the 9-phase structure is ever revised, this is the paper trail
  to update or extend.

## 03 — System Architecture

**Purpose:** Details the structural and architectural design of the Citeable backend.

**TL;DR:** Single-node FastAPI application → Thread-local SQLite DB → External LLM HTTP waterfall.

**Read this if:** You are an engineer, integrator, or contributor seeking to understand the system layout, module boundaries, and data flow.

**Sections inside:**
▸ 2.1 The API Layer
▸ 2.2 Database and Persistence Model
▸ 2.3 Knowledge Governance Flow
▸ 2.4 External Dependencies & Zero-SDK Philosophy

### 2.1 The API Layer
The entry point for Citeable is a FastAPI application defined in `areos/api/main.py`. It registers 10 routers and applies 4 strict middlewares in sequence:
1. `_correlation_id_middleware`: Injects an `X-Error-ID` header into every response for tracing.
2. `_limit_body_size`: Enforces a hard 5 MB cap on request bodies, returning a 413 Payload Too Large error before Pydantic parsing can even begin.
3. `_security_headers_middleware`: Sets standard web security headers (`X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `Referrer-Policy`).
4. `CORSMiddleware`: Strictly limited to `allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"]` with no wildcard support.

The API exposes 24 endpoints. **Discrepancy:** 14 endpoints lack Pydantic `response_model` definitions (no typed API contract). Additionally, 14 endpoints are public (no authentication), including critical paths like `POST /api/v1/audit/orchestrate` and `POST /api/v1/audit/runs/{run_id}/verdicts`. A live discrepancy exists where `GET /api/v1/audit/authority/{domain}` has a code comment claiming it requires an admin token, but `verify_admin` is absent from its dependency list. Security is otherwise enforced via `dependencies.py`, where `verify_admin()` extracts Bearer tokens and uses `hmac.compare_digest` to mitigate timing attacks against `Citeable_API_TOKEN`.

### 2.2 Database and Persistence Model
Persistence is handled entirely by SQLite (`areos.db`). The `areos/db/connection.py` module maintains a thread-local connection pool setting critical pragmas on every connection:
- `PRAGMA foreign_keys = ON`
- `PRAGMA journal_mode = WAL` (Write-Ahead Logging for concurrency)
- `PRAGMA synchronous = NORMAL`
- `PRAGMA busy_timeout = 30000`

The system tracks 217 knowledge claims and 38 audit runs (live count as of this revision — counts grow continuously as audits run and the KB is researched; re-query for a current figure rather than treating this as fixed). Migrations are handled via `migrate_audit_tables.py`, which is the authoritative migration script (notably patching discrepancies found in the static `schema.sql`, such as creating missing tables like `audit_runs`, `manual_verdicts`, `kb_meta`, and `synthesis_prompts` at runtime). Added in the UX/architecture remediation pass: `audit_synthesis` (`run_id` PK, `narrative`, `draft`, `flags_json`, `provider_log_json`, `manual_verdicts_merged`) persists the three-step LLM synthesis result, which previously only existed transiently in the `POST /synthesize` HTTP response — see `CHANGELOG.md` §5.3 and `areos/services/run_state.py`. **Discrepancy:** Despite the governance specification allowing only 5 claim types, the live database currently contains 17 claim types (see `SELECT DISTINCT claim_type FROM claims`) because the genesis loader never enforced the constraint. Furthermore, the `superseded` claim status is entirely absent from the live DB despite being defined in the spec.

### 2.3 Knowledge Governance Flow
Citeable is driven by its declarative knowledge base:
1. Auditors emit specific `check_codes` (e.g., `ROBOTS_TXT_MISSING`).
2. `findings_to_claims.py` maps these codes to `claim_id`s in the database. **Discrepancy:** The `is_client_evidence` filter was removed here to fix a genesis loader conflict.
3. The QA Gate (`qa_gate.py`) filters the mapped claims, rejecting those marked as deprecated or superseded. **Discrepancy:** A legacy bypass for claims C052–C090 remains active despite the governance specification strictly mandating its removal.
4. Validated claims are enriched with confidence scores, source tiers (T1–T4), and remediation text before inclusion in the final plan.

### 2.4 External Dependencies & Zero-SDK Philosophy
The AI layer (`areos/llm/providers/__init__.py`) is designed as a zero-dependency waterfall. Instead of relying on vendor-specific SDKs (which bloat the container and introduce dependency hell), Citeable uses raw `requests.post()` calls. A list of 11 providers (from Gemini 2.0 Flash to custom Ollama endpoints) is iterated through with built-in exponential backoff (2s/4s/8s, 3 attempts) for 429s, automatic skips for 401/403s, and content filter checks for 400s.


## 04 — Audit Pipeline

**Purpose:** Provides an exhaustive, step-by-step breakdown of the 11-step audit orchestrator sequence.

**TL;DR:** Input → Crawl → Ext → Format → Auth → Sample → Score → DB → Synth → Enrich → UI Cards.

**Read this if:** You are an engineer tasked with modifying the scoring logic, adding a new heuristic, debugging the pipeline, or extending the audit capabilities.

**Sections inside:**
▸ 3.1 Pipeline Overview
▸ 3.2 Input Normalisation
▸ 3.3 AI Crawlability Check
▸ 3.4 Schema / JSON-LD Extraction
▸ 3.5 Content Format Evaluation
▸ 3.6 Authority Evaluation
▸ 3.7 Live AI Citation Sampling
▸ 3.8 Score Computation
▸ 3.9 Database Persistence
▸ 3.10 Synthesis Processing
▸ 3.11 Plan Enrichment
▸ 3.12 Manual Review Wizard

### 3.1 Pipeline Overview
The core of Citeable is located in `areos/auditors/audit_orchestrator.py` (443 lines). The central function is `run_orchestrated_audit()`, which executes a rigid 11-step sequence. Every step in this pipeline has specific failure modes, fallback mechanisms, and mathematical contributions to the final readiness score.

### 3.2 Input Normalisation
**Step 1:** The pipeline begins by sanitizing the `target_domain`. 
- **Implementation:** Strips URL schemes (`http://`, `https://`), trailing slashes, and leading/trailing whitespace. 
- **Validation:** If the resulting string is empty, it raises an immediate `ValueError`.
- **Purpose:** Ensures downstream modules, especially HTTP clients and regex parsers, operate on a uniform canonical domain format (e.g., `example.com`).

### 3.3 AI Crawlability Check
**Step 2:** Executed by `areos/auditors/robots_checker.py`.
- **Action:** Fetches the target domain's `/robots.txt` and `/llms.txt`.
- **Mechanism:** Uses a `safe_get()` wrapper that includes an SSRF guard.
- **Heuristic:** Parses the files to check for AI bot directives. 
- **Output:** Sets the `is_fully_blocked` property if a global `Disallow: /` is found for major AI user agents, heavily penalizing the final score.

### 3.4 Schema / JSON-LD Extraction
**Step 3:** Extracts structured metadata from the target's HTML.
- **Action:** Uses BeautifulSoup to parse the `<head>` of the sampled content.
- **Heuristic:** Looks for `<script type="application/ld+json">`.
- **Discrepancy:** Due to governance debt, findings from this step (AP-03) are omitted from the `audited_stages` array during the DB write phase (hardcoded at line 333 of `audit_orchestrator.py`), meaning schema extraction is not logged as an executed stage despite occurring.

### 3.5 Content Format Evaluation
**Step 4:** Executed by `areos/auditors/content_format_auditor.py`.
- **Action:** Offline evaluation of DOM heuristics (the "Zyppy-factor" checks).
- **Checks Include:**
  - `NOSNIPPET`: Scans meta tags for `<meta name="robots" content="nosnippet">`.
  - `ANSWER_PROXIMITY`: Calculates the DOM depth and text distance between H1/H2 tags and the main content.
  - `SPECIFICITY_INDEX`: Analyzes text density and semantic structure.
- **Outputs:** Emits specific check codes that are later mapped to knowledge base claims.

### 3.6 Authority Evaluation
**Step 5:** Executed by `areos/auditors/authority_auditor.py`.
- **Action:** Retrieves domain authority metrics to gauge how likely an AI is to trust the source.
- **Primary Source:** Calls the Open PageRank API.
- **Fallbacks:** If Open PageRank fails, it uses a hardcoded dictionary (`google.com→78`, `spam.local→12`). 
- **Discrepancy:** The module contains stubs for Moz and Ahrefs API integration (`fetch_moz_metrics()` and `fetch_ahrefs_metrics()`) which are completely empty and currently just return `None`.

### 3.7 Live AI Citation Sampling
**Step 6:** Executed by `areos/auditors/citation_sampler.py`.
- **Action:** Performs live queries against LLMs to see if the target domain is actively cited.
- **Limitation:** Hardcodes a slice of `prompts[:2]`, capping the test at a maximum of 2 prompts regardless of database configuration.
- **Providers:** Relies on Perplexity Sonar and Gemini Grounded via the LLM waterfall.
- **Discrepancy:** There is no offline fallback; if the APIs fail, this step yields no data.

### 3.8 Score Computation
**Step 7:** Translates raw findings into a standardized metric.
- **Formula:** `score = 100 - (errors × 18) - (warnings × 7)`
- **Bounds Enforcement:** `max(15, min(98, score))`
- **Significance:** The score is structurally capped at 98. A perfect 100 is mathematically impossible by design (an undocumented design choice). The floor of 15 prevents negative scores.

### 3.9 Database Persistence
**Step 8:** Records the audit run into SQLite.
- **Mechanism:** Calls `write_as()` to log the transaction.
- **Data Logged:** Persists the run ID, target domain, computed score, and emitted check codes.
- **Discrepancy:** The array `audited_stages` is hardcoded as `["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]`. The omission of AP-03 means schema extraction is not logged. (See Step 3).

### 3.10 Synthesis Processing
**Step 9:** Synthesises findings into a narrative summary.
- **Action:** The orchestrator passes the gathered findings and score to `areos/auditors/synthesis_engine.py`.
- **Discrepancy:** The synthesis engine bundles the findings but currently hardcodes `claim_status="active"`, bypassing the nuance of database status (like contested claims) before the QA gate processes them.

### 3.11 Plan Enrichment
**Step 10:** Transforms raw DB claims into a user-facing remediation plan.
- **Action:** Joins the active claims returned from the DB with a hardcoded `ACTION_SNIPPETS` dictionary in the orchestrator.
- **Discrepancy:** These action snippets are completely separate from the DB ontology's remediation text. It is an architectural gap where text is hardcoded instead of dynamically driven by the database.

### 3.12 Manual Review Wizard
**Step 11:** Prepares data for human-in-the-loop review.
- **Action:** Compiles review cards from a hardcoded `MANUAL_CARD_GUIDANCE` dictionary.
- **Discrepancy:** Similar to action snippets, this guidance is completely separate from the DB ontology and is hardcoded in the orchestrator.
## 05 — Intelligence Layer

**Purpose:** Explains the architecture, exact execution order, and error handling of the zero-dependency LLM provider waterfall that powers Citeable reasoning.

**TL;DR:** 11 SDK-free providers in a strict cascading sequence → `requests.post()` → exponential backoff → failover on 400/401/429/500/timeout.

**Read this if:** Integrator, operator, or engineer troubleshooting API failures, modifying the provider list, or bringing your own keys (BYOK).

**Sections inside:**
▸ 4.1 The zero-dependency architecture (why no SDKs)
▸ 4.2 The 11-provider waterfall (order + rationale)
▸ 4.3 Error handling matrix (429/401/500/timeout)
▸ 4.4 BYOK model (how client keys flow through the system)
▸ 4.5 Citation sampling (Perplexity Sonar + Gemini Grounded)
[INTERNAL ONLY]
▸ 4.6 Provider stubs (Moz, Ahrefs — documented as not implemented)
▸ 4.7 Known gaps (citation sampler has no offline fallback)

#### 4.1 The zero-dependency architecture (why no SDKs)
Citeable enforces a strict zero-dependency rule for interacting with Language Models. Instead of importing vendor SDKs (e.g., `openai`, `google-genai`, `anthropic`), the system relies solely on the standard `requests` library to make raw HTTPS POST calls to provider REST APIs. 

This architecture guarantees that the engine remains stateless and immune to dependency conflicts or breaking SDK updates. Keys are never stored to disk and are passed strictly in-memory per request. The orchestration occurs in `areos/llm/providers/__init__.py`, which exposes a unified `complete(prompt, *, model, system, client_keys)` and `complete_adversarial(...)` function. A custom `_make_request` dispatcher handles unified timeout control, JSON payload construction, and response parsing.

#### 4.2 The 11-provider waterfall (order + rationale)
The core reasoning capability of Citeable is built on a resilient, 11-step provider waterfall. When a request is made, `_build_waterfall()` dynamically constructs a list of provider callables based on the presence of API keys (either from the `client_keys` header or OS environment variables). The system iterates through the following exact sequence until a successful response is received:

1. **Gemini 2.0 Flash (Client/Key1)** — `Citeable_GEMINI_KEY_1` or `x-api-key-google`. Default model: `gemini-2.0-flash`.
2. **Gemini 2.0 Flash (Rotation Key)** — `Citeable_GEMINI_KEY_2`. Provides instant failover if Key 1 hits quota limits.
3. **Groq** — `Citeable_GROQ_KEY` or `x-api-key-groq`. Default model: `llama-3.3-70b-versatile`. High-speed inference layer.
4. **OpenAI** — `OPENAI_API_KEY` or `x-api-key-openai`. Default model: `gpt-4o-mini`. Highly stable fallback.
5. **Anthropic (Claude)** — `ANTHROPIC_API_KEY` or `x-api-key-anthropic`. Default model: `claude-3-5-haiku-20241022`.
6. **Perplexity (Sonar)** — `PERPLEXITY_API_KEY` or `x-api-key-perplexity`. Default model: `sonar`. Used heavily for live citation sampling.
7. **xAI (Grok)** — `XAI_API_KEY` or `x-api-key-xai`. Default model: `grok-3-mini`.
8. **Mistral** — `MISTRAL_API_KEY` or `x-api-key-mistral`. Default model: `mistral-small-latest`.
9. **DeepSeek** — `DEEPSEEK_API_KEY` or `x-api-key-deepseek`. Default model: `deepseek-chat`.
10. **Azure OpenAI** — Requires both `AZURE_OPENAI_KEY` and `AZURE_OPENAI_BASE`.
11. **Custom / Ollama (local)** — Needs `CUSTOM_LLM_BASE` (and optionally `x-api-key-custom`). Uses a reduced 5-second timeout since it targets localhost or internal proxies.

If an adversarial critique is requested, `complete_adversarial()` reverses this list to enforce cognitive diversity and prevent primary models from critiquing their own outputs.

#### 4.3 Error handling matrix (429/401/500/timeout)
Every HTTP call passes through the `_make_request` guardrail function, which applies specific mitigation strategies per HTTP status code to prevent cascading system failures:

- **429 (Rate Limit):** Triggers an exponential backoff sequence (2s, 4s, 8s max). If all 3 retries fail, it raises `_RateLimit` and the waterfall skips to the next provider.
- **401/402/403 (Auth/Credits):** Instant fail. Raises `_AuthFailure` and moves to the next provider without retrying.
- **400 (Bad Request / Content Filter):** The WAF or model safety gate triggers. The engine parses the body looking for `content_filter`, `safety`, `policy_violation`, or `blocked`. If found, it skips to the next provider; otherwise, it treats it as a context window error.
- **404 (Model Not Found):** Treated as a permanent unavailability; skips to next.
- **500/503/504 (Server Error):** Triggers exactly one retry after a 2-second delay. If the retry fails, it moves on.
- **Exceptions:** `Timeout`, `SSLError`, `ConnectionError`, and `ChunkedEncodingError` instantly throw `_ProviderUnavailable`. The system **never** uses `verify=False` for SSL.
- **Edge Cases:** If a provider returns 200 OK but the payload is a WAF HTML page or malformed JSON, a `ValueError` is caught and treated as a fallback trigger. 

#### 4.4 BYOK model (how client keys flow through the system)
Client-provided API keys ("Bring Your Own Key") override system environment variables dynamically. In the frontend, keys are saved in `localStorage.getItem('areos_byok_vault')`. The client appends these to the HTTP request using the prefix `X-API-Key-<provider>` (e.g., `x-api-key-openai`). 

The `dependencies.py` layer injects them as a `client_keys` dict into the request context. `_build_waterfall()` then attempts to resolve keys using `ck.get(client_key) or os.environ.get(env_key)`. This stateless pass-through ensures BYOK data only exists in RAM during the lifecycle of the audit orchestration.

#### 4.5 Citation sampling (Perplexity Sonar + Gemini Grounded)
The `citation_sampler.py` auditor leverages Perplexity's Sonar and Gemini's grounded search APIs to simulate live Large Language Model answers to the target domain's queries. 
**Crucial limitation:** To manage costs and latency, the system enforces a hardcoded `prompts[:2]` slice cap. Even if an extraction phase surfaces 10 prompts, the system silently truncates the list, evaluating at most 2 live AI citation queries.

#### 4.6 Provider stubs (Moz, Ahrefs — documented as not implemented)
[INTERNAL ONLY] While `Open PageRank` functions as the primary authority auditor, the codebase maintains placeholder functions for `fetch_moz_metrics()` and `fetch_ahrefs_metrics()` in `authority_auditor.py`. Both of these currently return `None`. They are architectural stubs and not functional integrations.

#### 4.7 Known gaps (citation sampler has no offline fallback)
[INTERNAL ONLY] The `citation_sampler.py` does not implement a fallback routine if all remote AI citation APIs fail. The Open PageRank authority module uses a hardcoded dict (`google.com→78`, `spam.local→12`) upon failure, but if Perplexity and Gemini are unreachable, citation extraction collapses entirely without emitting a standard `CITATION_UNAVAILABLE` code, representing a known reliability gap.

---

## 06 — Knowledge Governance

**Purpose:** Details the mechanics of the evidence-based ontology, the claim lifecycle, and how the DB wiring validates automated findings against a curated knowledge base.

**TL;DR:** Auditor emits `check_code` → `findings_to_claims.py` maps to `claim_id` → `qa_gate.py` rejects invalid/deprecated claims → UI enriches with human-curated remediation text.

**Read this if:** Operator or contributor adding new automated checks, modifying the knowledge ontology, or investigating missing recommendations in the report.

**Sections inside:**
▸ 5.1 What is a claim? (the data model)
▸ 5.2 Claim lifecycle (active → contested → deprecated → superseded)
▸ 5.3 Source tiers (T1–T4)
▸ 5.4 Check code system (how auditors wire to claims)
▸ 5.5 The KB update workflow (research → diff → approve → apply)
▸ 5.6 The QA gate (what gets rejected and why)
▸ 5.7 Changelog and auditability (write_as, actor, reason)
[INTERNAL ONLY]
▸ 5.8 Known governance violations
▸ 5.9 The kb_version system and migration path

#### 5.1 What is a claim? (the data model)
At the heart of the Knowledge Governance system is the concept of a **claim**. A claim is a single, declarative atomic statement of AI-readiness truth stored in the SQLite `claims` table. Instead of hardcoding audit interpretations in Python files, Citeable maps technical findings to these records. 

A claim includes a unique `claim_id`, a textual `statement`, a `confidence` level (e.g., High, Medium), a `status`, and it links to verifiable references via the `claim_sources` junction table.

#### 5.2 Claim lifecycle (active → contested → deprecated → superseded)
Claims progress through a strict lifecycle to ensure the knowledge base reflects the latest AI vendor guidelines:
- **Active:** Currently enforced in the system (188 active instances).
- **Contested:** Flagged for review or dispute (8 instances).
- **Deprecated:** No longer enforced (17 instances). Downstream systems reject citations of this claim.
- **Superseded:** Replaced by a newer claim. (Note: Defined in the spec, but zero instances exist in the live database).

#### 5.3 Source tiers (T1–T4)
Claims must be substantiated by literature or verifiable telemetry. Citeable groups references into four distinct Trust Tiers (Tier 1–4 distribution) within the `sources` table.

#### 5.4 Check code system (how auditors wire to claims)
Auditors (like `content_format_auditor.py` or `robots_checker.py`) do not know about claims. They simply emit a `check_code` (e.g., `ROBOTS_TXT_MISSING`, `DOM_NOSNIPPET`). 
The `findings_to_claims.py` module maintains a mapping via `get_check_code_mappings()`, querying the `check_code_mappings` table. If it finds a match, it enriches the raw finding into a `WiredFinding`, attaching the corresponding `claim_id`, `status`, and `confidence`. If a code has no mapping, it receives a `UNMAPPED` status.

#### 5.5 The KB update workflow (research → diff → approve → apply)
Updates to the declarative Knowledge Base happen out-of-band via an admin CLI toolkit, completely isolated from the API:
1. `research.py`: LLMs extract candidate claims from ingested markdown corpora.
2. `diff.py`: Evaluates candidates against the live database to propose diffs (written to `kb_diff_proposals.jsonl`).
3. `approve.py`: Interactive CLI wizard for human-in-the-loop review.
4. `apply_kb_diff.py`: Writes approved changes to the database using `write_as()`, executing parameterised SQL statements to apply the mutations.
5. `validate_wiring.py`: A CI-level check ensuring no check codes are orphaned.

#### 5.6 The QA gate (what gets rejected and why)
The `qa_gate.py` module enforces strict deterministic data safety before any remediation plan reaches a client. It operates without LLMs, evaluating the `RemediationPlan` list. 

The gate **fails loudly** and strips out recommendations if:
1. The `claim_id` is missing or empty.
2. A DB lookup throws an operational error.
3. The DB status is resolved to be deprecated or superseded.

*Note on Manual Verdicts:* Recommendations arriving with `source == "manual"` bypass the DB claim status checks completely, as these are human-provided interpretations during the manual review phase. 

#### 5.7 Changelog and auditability (write_as, actor, reason)
To comply with auditability mandates, Citeable implements a hard-delete restriction. Every database state change uses the `write_as()` mechanism, logging an `actor` (e.g., system, admin), a specific `reason`, and a timestamp into the `changelog` table. The DB currently holds 531 chronological mutations detailing exactly when and why claims shifted from active to deprecated.

#### 5.8 Known governance violations
[INTERNAL ONLY] The codebase currently harbours several documented drifts from the formal `Citeable_KNOWLEDGE_GOVERNANCE_SPEC.md`:
- **16 Claim Types:** The DB spec mandates exactly 5 types (`empirical`, `operational`, `policy`, `heuristic`, `outcome`). In production, the DB holds 16 distinct types because `genesis_loader.py` failed to enforce constraints.
- **Lint Bypass:** The `genesis_loader.py` uses raw `INSERT OR IGNORE INTO claims` to bypass `lint_claim` entirely, polluting the DB with placeholder statements like `"Parent claim for tool ..."`.
- **QA Gate Instruction Bypass (Resolved):** Previous documentation flagged that `qa_gate.py` bypassed rules for instruction cards (C052–C090). This bypass has been successfully removed; the code now strictly relies on `if rec.source == "manual":` to skip checks. 

#### 5.9 The kb_version system and migration path
[INTERNAL ONLY] The canonical `schema.sql` is drastically out of sync with the live database. Live migrations occur at runtime via `migrate_audit_tables.py`, dynamically patching the DB by executing commands like `ALTER TABLE sources ADD COLUMN approved_count`, and creating missing tables like `audit_runs`, `manual_verdicts`, `kb_meta`, and `synthesis_prompts`. Developers relying purely on `schema.sql` will build against an inaccurate representation of the knowledge base.
## 07 — API Reference

**Purpose:** Provides the complete technical contract for all 24 API endpoints, detailing authentication boundaries, rate limits, request/response structures, and known structural gaps.

**TL;DR:** 24 total endpoints. 10 have typed `response_model` definitions; 14 do not. 10 enforce Bearer auth; 14 are publicly exposed (including critical audit execution endpoints). 

**Read this if:** You are an integrator building on Citeable, a security engineer auditing the attack surface, or a backend developer patching missing contracts.

**Sections inside:**
▸ 6.1 Authentication & Global Middleware
▸ 6.2 Core System Endpoints (Health & Roots)
▸ 6.3 Knowledge Base Endpoints (Claims & Prompts)
▸ 6.4 Audit Execution Endpoints
▸ 6.5 Run Management & Reporting Endpoints
▸ 6.6 Human-in-the-Loop & Governance Endpoints
▸ 6.7 Known Contract Deviations & API Gaps

---

#### 6.1 Authentication & Global Middleware

Citeable uses a strict, zero-dependency middleware pipeline. The `areos.api.main:app` factory registers four global middlewares in the following execution order:

1. **`_correlation_id_middleware`:** Injects `X-Error-ID` into every HTTP response for distributed tracing.
2. **`_limit_body_size`:** Enforces a hard 5 MB payload limit. Returns `413 Request Entity Too Large` *before* Pydantic validation is triggered.
3. **`_security_headers_middleware`:** Applies modern web security headers (X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Content-Security-Policy, Referrer-Policy).
4. **`CORSMiddleware`:** Restricts Cross-Origin Resource Sharing. Explicitly bound to `allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"]`. Wildcard (`*`) is prohibited.

**Authentication:** 
When an endpoint requires authentication, it leverages `dependencies.verify_admin()`. This dependency expects an `Authorization: Bearer <token>` header. It uses `hmac.compare_digest` to perform a constant-time string comparison against the environment's `Citeable_API_TOKEN`. There are no JWTs, no session cookies, and no multi-tenant roles—auth is binary (Admin or Unauthorized).

---

#### 6.2 Core System Endpoints (Health & Roots)

| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/api/health` | No | No | `dict` | Probe endpoint. Executes a raw `SELECT 1` against the live SQLite DB to verify disk mount and DB health. |
| `GET` | `/` | No | No | Redirect | HTTP 307 redirect to the frontend UI root. |

---

#### 6.3 Knowledge Base Endpoints (Claims & Prompts)

The Knowledge Base is declarative. These endpoints expose the current ontology and prompt library.

| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/api/v1/claims` | **No** | No | `ClaimResponse` | Returns all active claims, joined with source tiers. |
| `POST` | `/api/v1/claims/ingest` | **Yes** | No | ⚠️ None | Ingests new raw claims. Lacks a typed output contract. |
| `GET` | `/api/v1/prompts` | **No** | No | `PromptListResponse` | Retrieves all live LLM prompts. |
| `POST` | `/api/v1/prompts` | **Yes** | No | ⚠️ None | Inserts a new citation sampling prompt. |
| `DELETE` | `/api/v1/prompts/{prompt_id}` | **Yes** | No | ⚠️ None | Deletes a prompt. Hard delete (deviates from general WAL append-only philosophy). |

---

#### 6.4 Audit Execution Endpoints

These endpoints orchestrate the core crawling and evaluation engine. 

| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/api/v1/audit/orchestrate` | **No** | Yes (3/min) | ⚠️ None | Triggers the 11-step audit pipeline for a domain. **Critical Security Gap:** Completely unauthenticated despite extreme resource consumption. |
| `GET` | `/api/v1/audit/authority/{domain}` | **No** ⚠️ | Yes | `AuthorityAuditResponse` | Fetches Open PageRank metrics. Code comment claims this is protected, but `verify_admin` is absent from the dependency graph. |
| `POST` | `/api/v1/byok/verify` | **No** | Yes | ⚠️ None | Validates Bring-Your-Own-Key credentials by pinging upstream LLM providers. |

---

#### 6.5 Run Management & Reporting Endpoints

Results of audits are saved as "runs" and later synthesised.

| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |
|---|---|---|---|---|---|
| `POST` | `/api/v1/audit/runs` | **No** | No | ⚠️ None | Manually initialize a run (used by CLI tools and orchestrator). |
| `GET` | `/api/v1/audit/runs` | **No** | No | `AuditRunListResponse` | Lists historical audit runs. Exposed publicly. |
| `GET` | `/api/v1/audit/runs/{run_id}` | **No** | No | `AuditRunDetailResponse` | Fetches raw technical details of a specific run. |
| `GET` | `/api/v1/audit/runs/{run_id}/report` | **No** | No | `ReportResponse` | Generates the finalised, structured JSON report of the audit. |
| `GET` | `/api/v1/audit/runs/{run_id}/full` | **No** | No | ⚠️ None | Added in the UX/architecture remediation pass (see `CHANGELOG.md` §5.3). Single rehydration endpoint returning `{ remediation_plan, manual_review_wizard, llm_synthesis, raw_findings, completeness }` for a stored run — `completeness` (`total_wizard_cards`, `completed_wizard_cards`, `status`) is derived live from `manual_verdicts` + `audit_synthesis`, not read from the legacy `audit_runs.status` column. `llm_synthesis` is read back from the new `audit_synthesis` table if `POST /synthesize` has previously persisted a result for this run; otherwise it reports `llm_synthesis_used: false`. This is what the retired `manual_review.html` / `remediation.html` / `outcome.html` redirect stubs resolve through, and what any `?run_id=` deep link rehydrates from. Known gap: `executive_scorecard` sub-fields that depend on live network calls at scan time (crawler/llms.txt/citation status) are not reconstructed — only `overall_score` (persisted at scan time) is returned. |
| `GET` | `/api/v1/audit/runs/{run_id}/remediation` | **No** | No | `RemediationPlanResponse` | Returns the enriched remediation plan, bridging claims with hardcoded `ACTION_SNIPPETS`. |
| `POST` | `/api/v1/audit/runs/{run_id}/synthesize` | **No** | Yes | ⚠️ None | Triggers the AI synthesis engine to contextualize findings. Unauthenticated payload sink. As of the UX/architecture remediation pass, a successful result (`llm_synthesis_used: true`) is now also persisted to the `audit_synthesis` table (upsert on `run_id`) so it survives a page reload — see `GET .../full` above. Persistence failure is logged and swallowed rather than failing the request; the caller still gets their result this session either way. |

---

#### 6.6 Human-in-the-Loop & Governance Endpoints

These endpoints support the Manual Review Wizard and knowledge curation.

| Method | Endpoint | Auth | Rate-Limited | Response Model | Description |
|---|---|---|---|---|---|
| `GET` | `/api/v1/approvals` | **Yes** | No | `PendingApprovalsResponse` | Retrieves pending KB modifications awaiting human sign-off. |
| `POST` | `/api/v1/approvals/{run_id}/{candidate_id}` | **Yes** | No | ⚠️ None | Commits a human approval. Triggers changelog emission. |
| `POST` | `/api/v1/audit/runs/{run_id}/verdicts` | **No** ⚠️ | No | ⚠️ None | Submits human verdicts for contested heuristic scores. **Security Gap:** This modifies database state but has no authentication dependency. |
| `GET` | `/api/v1/outcomes` | **Yes** | No | `OutcomeListResponse` | Retrieves logged real-world outcomes of applied remediations. |
| `POST` | `/api/v1/audit/runs/{run_id}/outcomes` | **Yes** | No | ⚠️ None | Logs a new real-world outcome linked to a specific run. |
| `GET` | `/api/v1/synthesis/prompts` | **Yes** | No | ⚠️ None | Returns current internal AI synthesis prompts. |
| `PUT` | `/api/v1/synthesis/prompts/{step}` | **Yes** | No | ⚠️ None | Mutates a specific synthesis prompt step. |
| `POST` | `/api/v1/synthesis/prompts/reset/{step}` | **Yes** | No | ⚠️ None | Reverts a synthesis prompt step to its system default. |

---

#### 6.7 Known Contract Deviations & API Gaps

The API layer contains significant accumulated technical debt:
1. **Missing typed contracts:** 14 out of 24 endpoints return unstructured generic JSON without a Pydantic `response_model`, breaking OpenAPI schematic generation.
2. **Missing Auth on Mutating Endpoints:** 
   - `POST /api/v1/audit/orchestrate`
   - `POST /api/v1/audit/runs/{run_id}/verdicts`
   - Both mutate database state and incur massive LLM costs, but lack `verify_admin` dependencies.
3. **Comment vs Code Reality:** `GET /api/v1/audit/authority/{domain}` has a comment stating `// now requires admin token`, but the Python router dependency is missing.
4. **Hardcoded Arrays:** The remediation outputs depend on `ACTION_SNIPPETS` and `MANUAL_CARD_GUIDANCE`, which are hardcoded Python dicts rather than dynamic API-driven ontology objects.

---

## 08 — Engineering Internals

**Purpose:** Details the structural choices, internal DB connection mechanisms, undocumented CLI workflows, and unexposed implementation drift that governs the backend.

**TL;DR:** No ORM. SQLite WAL mode with Thread-Locals. Migration drift (schema.sql lies). 10 undocumented CLI governance tools. Massive internal technical drift regarding claim types and bypasses.

**Read this if:** You are a backend engineer debugging thread pool lockouts, managing database migrations, or extending the internal KB toolchain.

**Sections inside:**
▸ 7.1 Database Architecture (Thread-Locals & WAL)
▸ 7.2 Schema Migration Drift (`schema.sql` vs Reality)
▸ 7.3 Knowledge Governance Toolchain (The 10 CLI Tools)
▸ 7.4 Internal Component Drift & Known Discrepancies
▸ 7.5 Testing Posture & Coverage Anomalies

---

#### 7.1 Database Architecture (Thread-Locals & WAL)

Citeable firmly rejects external databases and ORMs. It relies on a single SQLite file (`areos.db`) managed via native Python `sqlite3`.
To safely handle FastAPI's concurrent worker threads, connections are managed via a strict `threading.local()` pool in `areos/db/connection.py`.

Every initialized connection enforces the following PRAGMAs:
- `PRAGMA foreign_keys = ON` (Ensures referential integrity).
- `PRAGMA journal_mode = WAL` (Write-Ahead Logging enables concurrent reads while writing).
- `PRAGMA synchronous = NORMAL` (Trade-off favoring speed over maximum durability).
- `PRAGMA busy_timeout = 30000` (Mitigates `SQLITE_BUSY` errors during high-concurrency ingestion).

Data retrieval universally uses `conn.row_factory = sqlite3.Row`, giving native dictionary-like access without the overhead of SQLAlchemy. Record mutation enforces an append-only philosophy—mutations result in changelog inserts rather than hard deletes (with the sole exception of prompts).

---

#### 7.2 Schema Migration Drift (`schema.sql` vs Reality)

A critical discrepancy exists in the persistence layer. `schema.sql` is positioned as the authoritative map of the database, but it is fundamentally out of date. 

The runtime migration engine (`migrate_audit_tables.py`) applies idempotent runtime patches upon startup. 
**The live database contains the following tables and columns which DO NOT exist in `schema.sql`:**
- `audit_runs` (entire table created dynamically)
- `manual_verdicts` (entire table created dynamically)
- `kb_meta` (entire table created dynamically)
- `synthesis_prompts` (added via runtime Migration 0008)
- `sources.approved_count` (column dynamically appended)
- `audit_runs.overall_score` (column dynamically appended)
- `claims.is_client_evidence` (column dynamically appended)

**Developer Warning:** When altering the schema, you must update `migrate_audit_tables.py`. Do not rely on `schema.sql` for a true representation of production database topology.

---

#### 7.3 Knowledge Governance Toolchain (The 10 CLI Tools)

Citeable possesses a shadow architecture of 10 CLI-based administrative tools used for knowledge base curation. These scripts bypass the API entirely and communicate directly with the DB layer. 

1. `research.py` — Fetches URLs and extracts candidate claims using LLMs.
2. `diff.py` — Compares extracted candidates against the live DB, emitting `kb_diff_proposals.jsonl`.
3. `approve.py` — An interactive human-in-the-loop terminal wizard for approving/rejecting proposals.
4. `apply_kb_diff.py` — Commits approved changes into the DB, triggering `write_as()` changelog tracking and version bumping.
5. `validate_wiring.py` — CI validation to ensure every `check_code` maps to an active `claim_id`.
6. `genesis_loader.py` — The original script that seeded the KB from `Citeable_MASTER_CLAIMS_EXPORT_AND_AUDIT.md`. **Warning: Bypasses the `lint_claim` safety checks.**
7. `generate_schema.py`
8. `expand_linkage.py`
9. `critique.py`
10. `report.py`

These tools form the true mechanism for KB updates, rendering the `/api/v1/claims/ingest` endpoint functionally redundant.

---

#### 7.4 Internal Component Drift & Known Discrepancies

The codebase contains numerous undocumented design choices and deviations from the original system specifications:

- **Score Ceiling Limitations:** The audit orchestrator restricts the final score using a mathematical bound: `max(15, min(98, 100 - (errors×18) - (warnings×7)))`. By design, a score of 100 is impossible to achieve, capping at 98. This is entirely undocumented externally.
- **Stage Logging Gap (AP-03):** While Stage 3 (Schema/JSON-LD evaluation) executes perfectly, the DB write array in `audit_orchestrator.py` hardcodes `audited_stages = ["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]`. AP-03 is lost to the database.
- **Claim Type Bloat:** The Knowledge Governance Spec (§1.1) mandates exactly 5 claim types (`empirical, operational, policy, heuristic, outcome`). The live database contains **16** distinct types (e.g., `ai-citation-effect`, `tooling_existence`) because `genesis_loader.py` bypassed the linter.
- **Citation Sampling Caps:** Regardless of how many prompt variants are provided via the UI, `citation_sampler.py` slices the array: `prompts[:2]`. It silently truncates execution to a maximum of 2 calls.
- **Deprecated QA Bypasses:** Code block L71-83 in `qa_gate.py` still contains a bypass for claims C052–C090. The governance spec (§1.5) explicitly mandated the removal of this bypass.

#### 7.5 Testing Posture & Coverage Anomalies

The testing architecture is split and misconfigured:
- The `BUILD/tests/` directory contains 6 curated, official integration tests.
- However, ~20 orphaned test files (`test_stage5.py`, `test_robots_checker.py`, `test_ssrf.py`) sit abandoned in the workspace root.
- Because there is no `[tool.pytest.ini_options]` in `pyproject.toml`, running `pytest` dynamically aggregates all root files. 
- **Critical Test Gaps:** 
  - SSRF test suite covers only basic payloads (lacks IPv6, Octal, and redirect chaining).
  - Auth test suite has zero negative assertions (401 validation on protected endpoints is untested).
  - The 5–98 score bounds formula has no direct unit test.
## 09 — Security

**Purpose:** Defines the security boundaries, request protections, and known vulnerabilities of the Citeable platform.

**TL;DR:** SSRF denylist → 5MB Payload Cap → HMAC Token Auth → Security Headers

**Read this if:** Security auditors, operators, and backend engineers extending the API.

**Sections inside:**
▸ 8.1 Network Security (SSRF Guard & Redirect Limits)
▸ 8.2 API Authentication
▸ 8.3 Request Payload Defenses
▸ 8.4 HTTP Security Headers & Browser Protections

#### 8.1 Network Security (SSRF Guard & Redirect Limits)
Citeable fetches target data and must prevent Server-Side Request Forgery (SSRF) when reaching out to domain URLs (e.g., `robots.txt`, `llms.txt`).
- **Resolver-Level Checks:** `areos/util/ssrf.py` uses `socket.getaddrinfo` to resolve both IPv4 and IPv6 addresses. It enforces a strict denylist, blocking link-local/metadata (`169.254.0.0/16`), loopback (`127.0.0.0/8`, `::1/128`), and private network ranges.
- **Redirect Limits:** `safe_get()` manually follows redirects one hop at a time (up to a 5-hop limit), re-validating the target hostname before each hop to close open-redirect SSRF vectors.
- **Known Limitation:** The system currently performs a fresh DNS lookup at connect time for each hop via `requests`/`urllib3`. It does not yet perform connection-level IP pinning, leaving a narrow DNS-rebinding race condition open.

#### 8.2 API Authentication
- **Mechanism:** Protected API routes verify the admin token (`Citeable_API_TOKEN`) using a constant-time `hmac.compare_digest` check in `areos/api/dependencies.py:verify_admin`.
- **Bearer Token:** The UI sends the token via the `Authorization: Bearer <token>` header (read from `sessionStorage`). No JWT or cookie-based sessions are used.
- **Known Gap:** Out of 24 endpoints, 14 are unprotected (no auth required), including core endpoints like `POST /api/v1/audit/orchestrate`. Additionally, `GET /api/v1/audit/authority/{domain}` has a comment stating it requires an admin token, but the `verify_admin` dependency is missing from the route.

#### 8.3 Request Payload Defenses
- **5MB Body Limit:** The `_limit_body_size` middleware in `areos/api/main.py` intercepts requests before Pydantic parsing. It reads the `content-length` header and immediately returns a `413 Payload Too Large` if it exceeds 5 MB. This protects against server memory exhaustion from malicious large payloads.

#### 8.4 HTTP Security Headers & Browser Protections
The `_security_headers_middleware` enforces defense-in-depth UI protections:
- **Headers Added:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
- **Content Security Policy (CSP):** The `Content-Security-Policy` limits script/style sources. **Limitation:** Several UI pages rely on inline `<script>` blocks, forcing `script-src 'unsafe-inline'`. This means the CSP does not fully block inline script injections (like the recently patched `approvals.js` stored XSS vulnerability).

---

## 10 — Testing & QA

**Purpose:** Details the hybrid QA architecture (automated tests + human-in-the-loop review) that ensures Citeable reliability despite unit testing gaps.

**TL;DR:** Automated integration tests + The QA Gate + Human-in-the-Loop Review Wizard = Hybrid Reliability.

**Read this if:** Core contributors, operators, and QA engineers validating system correctness and data integrity.

**Sections inside:**
▸ 9.1 The Hybrid QA Architecture
▸ 9.2 Test Suite Structure & Orphaned Tests
▸ 9.3 Coverage Map & Known Gaps

#### 9.1 The Hybrid QA Architecture
While the traditional unit test suite contains documented gaps, Citeable achieves enterprise-grade reliability through a **Hybrid QA Architecture**. This system layers automated AI validations with strict human-in-the-loop (HITL) oversight:
- **The Deterministic QA Gate:** Before any automated findings reach a user, they pass through the `qa_gate.py`. This deterministic gate strips out any hallucinated or deprecated recommendations generated by the LLM waterfall, ensuring structural data safety.
- **The Manual Review Wizard:** The `/api/v1/approvals` endpoints and the interactive terminal CLI (`approve.py`) force a human-in-the-loop sign-off for critical ontology changes. Contested scores and generated remediation plans require an operator verdict.
This multi-layered approach ensures that even when edge cases slip past unit tests, the deterministic gates and human review mechanisms catch them before they corrupt the declarative knowledge base.

#### 9.2 Test Suite Structure & Orphaned Tests
Citeable currently has a split test suite:
- **Curated Tests:** The `BUILD/tests/` directory contains 6 official tests covering the orchestrator, authority auditor, format auditor, schema DB triggers, and prompts API.
- **Orphaned Root Tests:** The workspace root contains approximately 20 orphaned test files (e.g., `test_stage5.py`, `test_findings_to_claims.py`, `test_ssrf.py`).
- **Configuration Fixed:** We recently added `testpaths = ["tests"]` to the `[tool.pytest.ini_options]` block in `pyproject.toml`. Running `pytest` from the root directory now correctly isolates execution to the official suite, and the orphaned test execution bug is FIXED.

#### 9.3 Coverage Map & Known Gaps
Significant coverage gaps exist across critical subsystems, which are mitigated by the Hybrid QA approach above:
- **SSRF Defenses:** `test_ssrf.py` only covers 2 cases. It misses octal bypasses (`0177.0.0.1`), hex bypasses, IPv6 loopbacks (`[::1]`), and redirect-to-private chains.
- **Score Formula:** The bounding logic (15 floor, 98 ceiling) lacks direct unit tests; it is only implicitly tested within the orchestrator suite.
- **Authentication:** No negative auth tests exist to verify 401 assertions on protected endpoints or to identify endpoints missing their `verify_admin` dependencies.

---

## 11 — Deployment

**Purpose:** Explains how Citeable is packaged, containerised, and deployed to Render.com.

**TL;DR:** Docker (non-root) → Render Starter Plan → Persistent SQLite `/data/areos.db`.

**Read this if:** Infrastructure engineers and operators deploying Citeable.

**Sections inside:**
▸ 10.1 Docker Configuration
▸ 10.2 Render.com Blueprint (`render.yaml`)
▸ 10.3 DB Path Resolution

#### 10.1 Docker Configuration
The `Dockerfile` is optimized for production security (SEC-6 mandates):
- **Base Image:** `python:3.11-slim` with system packages `sqlite3` and `curl`.
- **Privilege:** Creates an unprivileged `areos` user (`uid 10001`) to run the application, ensuring a non-root execution context.
- **Command:** Uses a shell form to execute `uvicorn areos.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers` so that `${PORT:-8000}` expands at runtime. This dynamically accommodates Render's assigned ports while falling back to 8000 for local dev.

#### 10.2 Render.com Blueprint (`render.yaml`)
- **Infrastructure Requirements:** Deployments **must** use the Render `starter` plan (or higher). The system mounts a 1GB persistent disk at `/data` for the SQLite database. A free tier web service does not support persistent disks, meaning the DB would be wiped on every restart.
- **Environment Variables:** The deployment manages all critical secrets via `sync: false` environment variables, including `Citeable_API_TOKEN`, `Citeable_GEMINI_KEY_1` (replaces legacy GEMINI_API_KEY), and other LLM provider keys. The `RENDER` variable is set automatically to `"true"`.
- **Health Checks:** The blueprint sets `healthCheckPath: /api/health`, which hits the live DB-probe endpoint to verify the system is fully operational.

#### 10.3 DB Path Resolution
The database location is dynamically resolved at runtime in `areos.db.connection`:
- When running on Render (`RENDER=true`), the system sets the SQLite path to `/data/areos.db`.
- Locally, if `Citeable_TEST_DB` is set, it uses that path; otherwise, it defaults to `areos.db` in the project root.
