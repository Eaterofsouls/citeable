# CITEABLE V2 — ARCHITECTURAL DECISION LOG

> **Purpose:** Every architectural decision behind the Hybrid Knowledge Architecture, written at a level where a junior developer who has never seen this codebase can implement the correct thing without guessing.
>
> **Rule:** If a decision isn't in this file, it wasn't made. If you're about to write code and you're not sure which approach to take, check here first.

---

## D-001: Knowledge Source of Truth

**Decision:** The governed JSONL corpus (`areos/kb/corpus/*.jsonl`) is the single source of truth for all knowledge. SQLite tables are derived. Never edit SQLite directly.

**Why:** JSONL is human-readable, git-diffable, grep-able, and survives database rebuilds. SQLite is optimized for query, not for human editing or version control.

**Rejected:** Editing knowledge directly in SQLite (fragile, not diffable, loses provenance history). Using a single JSON file (merge conflicts, can't append incrementally).

**Consequence:** Any knowledge change starts by editing a `.jsonl` file, then running `python -m areos.kb.build_kb`. Never `INSERT INTO knowledge` manually.

---

## D-002: Keep SQLite, Don't Migrate to Postgres

**Decision:** SQLite remains the relational database. No Postgres migration.

**Why:** The app runs on Render with a persistent disk. SQLite + WAL handles the read/write concurrency at Citeable's scale (single-digit concurrent users). Postgres would require a managed DB service (\$7+/mo), connection pooling, and migration tooling — all for zero user-facing benefit at current scale.

**Rejected:** Postgres + pgvector (overkill for 202 records; adds operational complexity and cost). Switching to Postgres later is possible but not needed now.

**Consequence:** All new tables (`knowledge`, `kb_evidence`, `kb_sources`, `kb_embeddings`, `kb_check_code_map`) are created in SQLite via `build_kb.py`. Use `json_extract()` for JSON fields, not Postgres `jsonb` operators.

---

## D-003: The `claims` Table Becomes a SQL View

**Decision:** The old `claims` table is replaced by a SQL `VIEW` that maps `knowledge` table columns to the old `claims` schema.

**Why:** The existing `/api/v1/claims` endpoint, the Claims Browser UI (`app.js`), and the Cmd+K palette all query `SELECT * FROM claims`. Creating a view means zero changes to those consumers — they keep working without knowing anything changed underneath.

**Rejected:** Hard cutover (drop old `claims` table, update all consumers) — too risky, too many files to change simultaneously. Keeping both tables in sync — maintenance nightmare, data will drift.

**Consequence:** When writing the view, map: `kid → claim_id`, `scope → claim_scope`, `type → claim_type`. The view must include `source_url` via a subquery join to `kb_evidence` → `kb_sources`. Test: `SELECT count(*) FROM claims` must return 202.

---

## D-004: Five Knowledge Record Types, Not "Claim Types"

**Decision:** Knowledge records use exactly 5 types: `FACT`, `STANDARD`, `FINDING`, `UNCERTAINTY`, `GUIDANCE`. The old 16 "claim types" (empirical, operational, policy, heuristic, etc.) are retired.

**Why:** The old types were never enforced (the genesis loader bypassed lint), resulting in 16 types with no clear semantics. The new 5 types have precise definitions from the knowledge governance spec.

**Rejected:** Keeping the old type names and adding new ones alongside them — confusing, no clean mapping.

**Consequence:** The `knowledge` table has `CHECK(type IN ('FACT','STANDARD','FINDING','UNCERTAINTY','GUIDANCE'))`. The `claims` view maps `type` directly (consumers see the new type names). The UI filter dropdown in Claims Browser changes from "Empirical/Policy" to "FACT/GUIDANCE/FINDING/UNCERTAINTY/STANDARD".

---

## D-005: Deterministic Routing via `kb_check_code_map`

**Decision:** The check-code-to-knowledge mapping lives in a SQLite table (`kb_check_code_map`), populated from `check_code_to_knowledge_map.json` at build time.

**Why:** The old mapping was a hardcoded Python dict in `ingest_claims.py` (35 entries). Changing a mapping required a code deploy. The new table has 50 entries and can be updated by editing the JSONL and rebuilding — no code change, no deploy.

**Rejected:** Keeping mappings in Python dicts (defeats the whole purpose of externalizing knowledge). Putting mappings only in `knowledge.jsonl`'s `check_links` field (works for reading, but querying "which knowledge for check code X?" requires scanning all records — a table with a primary key on `check_code` is O(1)).

**Consequence:** `findings_to_claims.py::wire_finding()` queries `kb_check_code_map` instead of the in-memory dict. The SQL is: `SELECT kid FROM kb_check_code_map WHERE check_code = ?`.

---

## D-006: Priority Scores Come From the Database, Not Python

**Decision:** `PRIORITY_SCORES` (the dict in `synthesis_engine.py` that ranks check codes by severity) is replaced by the `priority_score` column in `kb_check_code_map`.

**Why:** Priority scores are business policy, not code logic. They should be editable without a code deploy. A product person should be able to say "make CRAWLER_FULLY_BLOCKED priority 1 instead of 3" by editing a JSON file and rebuilding.

**Rejected:** Keeping the Python dict alongside the DB table (two sources of truth will drift). Computing priority from confidence level (not the same thing — a high-confidence finding can be low-priority).

**Consequence:** `_load_priority_scores()` returns `{check_code: int}` from a single SQL query. The old `PRIORITY_SCORES` dict is deleted entirely. If a check code is missing from the map, it gets a default priority of 10 (lowest).

---

## D-007: Remediation Text Comes From GUIDANCE Records

**Decision:** `REMEDIATION_TEXT` (the dict in `synthesis_engine.py` with 35 hardcoded `(title, description)` tuples) is replaced by GUIDANCE records in the `knowledge` table.

**Why:** GUIDANCE records have structured fields: `problem`, `action`, `rationale` (kid of a backing FACT), `tech_context`, `examples`, and `check_codes`. This is strictly richer than a `(title, description)` tuple.

**Rejected:** Keeping the dict as a fallback (creates confusion about which source is authoritative). Generating remediation text from FACT records (FACTs describe what IS, not what to DO — that's GUIDANCE's job).

**Consequence:** `_load_remediation_text()` joins `kb_check_code_map` → `knowledge` WHERE `type = 'GUIDANCE'`. The title comes from `statement`, the description from `json_extract(guidance_json, '$.action')`. The old dict is deleted.

---

## D-008: No ChromaDB, No sentence-transformers, No torch

**Decision:** The RAG embedding layer uses API-based embedding (via the BYOK waterfall), not local models. No new Python dependencies are added.

**Why:** `sentence-transformers` requires `torch` (+750MB). ChromaDB adds another dependency. The app currently deploys in <30s with a ~50MB image. Adding 800MB of ML libraries for 202 records is absurd. The BYOK system already has the user's API keys — use them for embeddings too.

**Rejected:** `sentence-transformers` + `chromadb` (+800MB deploy, +200MB RAM, +30s cold start). `sqlite-vec` extension (requires native compilation, breaks on some platforms). `faiss` (still requires numpy/scipy, and Facebook's build system is fragile on ARM).

**Consequence:** `areos/kb/embeddings.py` makes HTTP POST calls to embedding APIs (Google `text-embedding-004`, OpenAI `text-embedding-3-small`, Mistral `mistral-embed`) using the same `requests.post()` pattern as `llm/providers/__init__.py`. Cosine similarity is 5 lines of pure Python math. `requirements.txt` does NOT change.

---

## D-009: Pre-Computed Corpus Embeddings at Build Time

**Decision:** The 202 knowledge record embeddings are computed once at build time and stored in the `kb_embeddings` SQLite table as JSON arrays.

**Why:** The corpus doesn't change per-request. Embedding 202 records costs ~0.001¢ and takes ~3 seconds. Storing the vectors means runtime RAG queries only need to embed the ONE query string (the finding description), not re-embed the whole corpus.

**Rejected:** Embedding at runtime on every request (wasteful, slow, costs 202x more API calls). Shipping pre-computed embeddings as a binary file (not inspectable, tied to a specific model).

**Consequence:** `build_kb.py` has an `--embed` flag (or environment variable `AREOS_EMBED_KEY`) that triggers embedding. The `kb_embeddings` table stores `(kid, vector_json, model, embedded_at)`. If no embedding key is available, the table is empty and RAG is disabled at runtime.

---

## D-010: Three RAG Tiers, Not One

**Decision:** RAG serves three functions: Primary (novel findings), Enrichment (known findings), and Cross-Phase (synthesis). Not just "fallback for unmapped codes."

**Why:** Using RAG only for novel findings wastes the corpus. The LLM currently receives a single claim statement per finding. Even for known check codes, RAG can find 3 related records that give the LLM context to write genuinely insightful narratives instead of generic advice.

**Rejected:** RAG only for novel findings (underuse — the user explicitly flagged this). RAG for everything including deterministic routing (non-deterministic, breaks reproducibility for known codes). Full RAG with no deterministic path (hallucination risk, no traceability).

**Consequence:** The Knowledge Router (`router.py`) calls RAG in three places:
1. **Primary** (check code NOT in map): threshold ≥ 0.82, returns up to 5 candidates
2. **Enrichment** (check code IS in map, AFTER deterministic lookup): threshold ≥ 0.70, returns top 3 related records tagged `enrichment`
3. **Cross-Phase** (after ALL findings resolved): all descriptions concatenated as query, threshold ≥ 0.75, returns up to 5 bridging records

---

## D-011: Cosine Similarity Thresholds

**Decision:** Three fixed thresholds: ≥ 0.82 (use as primary), 0.70–0.82 (flag as "loosely relevant"), < 0.70 (discard).

**Why:** These are conservative. In a product about citation accuracy, false positives (recommending irrelevant knowledge) are worse than false negatives (saying "insufficient knowledge"). The 0.82 threshold was chosen from the original architecture spec and empirical testing on AEO domain text.

**Rejected:** Lower thresholds like 0.60 (too many false positives in domain-specific text). Dynamic thresholds based on corpus size (overengineered for 202 records). No threshold at all (pure top-K) — dangerous, always returns something even for garbage queries.

**Consequence:** These are constants in `router.py`. If a query about "pizza recipes" is run against the AEO corpus, nothing should score above 0.70, and the response should be `INSUFFICIENT`. Test this explicitly.

---

## D-012: "Insufficient Knowledge" Is a Valid Response

**Decision:** When RAG finds nothing above threshold, the system returns a structured `Resolution(path="INSUFFICIENT", message="No sufficiently confident knowledge found. Flagging for human review.")`.

**Why:** Citeable is a product about citation accuracy. Returning a low-confidence guess and presenting it as authoritative advice is worse than saying "we don't know." The LLM synthesis pipeline is instructed to say "This finding could not be matched to governed knowledge" rather than hallucinating a recommendation.

**Rejected:** Always returning the top result regardless of score (defeats the confidence gate). Silently dropping the finding (user never sees it). Letting the LLM freestyle (hallucination).

**Consequence:** The `Resolution` model has a `path` enum: `DETERMINISTIC`, `SEMANTIC`, `INSUFFICIENT`, `DEPRECATED`. The synthesis pipeline handles each path differently.

---

## D-013: BYOK Keys for Embeddings Use the Same Waterfall Pattern

**Decision:** Embedding API calls use the exact same `client_keys` dict extracted from HTTP headers. The embedding waterfall mirrors the LLM waterfall.

**Why:** Consistency. The user already gave us their Google/OpenAI key via the BYOK Vault. That same key works for both text generation AND embeddings. No separate "embedding key" setup. No new UI. No new headers.

**Rejected:** Separate embedding API key (confusing, unnecessary — same key works). Server-side-only embedding key (breaks the BYOK zero-storage model). Different header prefix like `x-embed-key-*` (overengineered — the text gen key IS the embed key).

**Consequence:** `embeddings.py` imports nothing from `llm/providers/`. It has its own `_build_embed_waterfall(client_keys)` that reads the same `client_keys["google"]`, `client_keys["openai"]`, etc. The first provider with a valid key wins.

---

## D-014: Graceful Degradation Without BYOK Key

**Decision:** If no BYOK key is available, RAG enrichment is silently disabled. The system falls back to deterministic-only mode. No error, no crash.

**Why:** RAG is additive. The deterministic path (50 check codes mapped to GUIDANCE records) already provides massively better knowledge than the old 5-claim system. A user who hasn't added a BYOK key still gets a huge upgrade. RAG enrichment is a bonus for users who have keys.

**Rejected:** Requiring a BYOK key for the app to work at all (breaks existing users). Showing an error banner (annoying for users who don't want RAG). Using a server-side key for all users' RAG queries (server operator pays for everyone's embedding costs).

**Consequence:** Every place that calls `embed()` wraps it in a try/except. If `RuntimeError("No embedding provider configured")` is raised, the code path skips RAG and continues with deterministic-only results. The `Resolution` object has a `rag_available: bool` field so the UI can optionally show "🔑 Add an AI key to enable knowledge enrichment."

---

## D-015: Embedding Dimension Mismatch Handling

**Decision:** The `kb_embeddings` table stores a `model` column. At query time, if the client's BYOK key resolves to a different embedding provider than the one used to build the corpus vectors, the system attempts to re-embed the query with the corpus's provider using a server-side fallback key. If neither works, RAG is skipped.

**Why:** Google's `text-embedding-004` produces 768-dim vectors. OpenAI's `text-embedding-3-small` produces 1536-dim. You can't compute cosine similarity between vectors of different dimensions.

**Rejected:** Truncating/padding vectors to match (destroys semantic information). Requiring all users to use the same provider (breaks BYOK flexibility). Storing multiple embedding sets per provider (wastes storage, complex to maintain for 202 records).

**Consequence:** `build_kb.py` writes the model name (e.g., `text-embedding-004`) into every `kb_embeddings` row. `router.py` checks: does the query embedding model match the corpus model? If not, fall back to server key for the matching provider. If no server key for that provider, skip RAG.

---

## D-016: The Claims Browser Becomes Knowledge Explorer

**Decision:** Rename "Claims Browser" to "Knowledge Explorer" and upgrade the detail drawer to show evidence chains, GUIDANCE structure, and contested/stale indicators. Do NOT delete the page or create a new one.

**Why:** The Claims Browser is already well-built (filters, search, drawer, pinning, edit proposals, accessibility). Throwing it away and building from scratch is wasteful. The page structure is perfect — it just needs richer data in the drawer.

**Rejected:** Building a new "Knowledge Explorer" page from scratch (duplicate work, new bugs). Keeping the old Claims Browser unchanged alongside a new page (confusing navigation, two views of the same data). Removing the page entirely (users lose the ability to browse knowledge).

**Consequence:** `claims_browser.html` — change title and header text. `nav.js` — change label string. `app.js` — the detail drawer (`openDrawer()` function) calls the new `/api/v1/knowledge/{kid}` endpoint instead of displaying flat claim fields. The grid rows add type badges and AEOG phase chips.

---

## D-017: `/api/v1/claims` Stays, `/api/v1/knowledge` Is Added

**Decision:** The old `/api/v1/claims` endpoint stays (reads from the `claims` VIEW). A new `/api/v1/knowledge` family of endpoints is added for richer queries.

**Why:** Breaking the old endpoint would break any external integrations, bookmarks, or scripts that use it. The new endpoints provide evidence chains, source citations, and semantic search — things the old `ClaimModel` schema can't express.

**Rejected:** Migrating `/api/v1/claims` to return the new schema (breaking change for consumers). Deprecating `/api/v1/claims` immediately (too aggressive — let it coexist for at least one version).

**Consequence:** `areos/api/routers/claims.py` is unchanged (queries `claims` view). New file `areos/api/routers/knowledge.py` with 6 endpoints. Both routers are registered in `main.py`.

---

## D-018: Evidence Chains in the Remediation Report

**Decision:** The exported Markdown report includes source citations with URLs, rationale from backing FACT/FINDING records, and code examples from GUIDANCE records. Not just "Claim C050."

**Why:** The current report says `Governing Research Basis: Claim ID C050 (high Confidence / internal-playbook)` for every crawler finding. This is useless — the user learns nothing about WHY the recommendation matters. With 202 governed records and 115 cited sources, we can now provide real citations.

**Rejected:** Keeping the thin citation format (wastes the entire corpus). Including full evidence records inline (too verbose — just the statement + source URL + authority tier).

**Consequence:** `studio.js::exportExecutiveReport()` builds each finding section with: knowledge basis (kid + type), rationale (backing FACT statement), source citations (title + URL + authority tier), and code examples. The `_build_synthesizer_input()` function in `synthesis_pipeline.py` includes all of this so the LLM can reference it.

---

## D-019: Contested Knowledge Must Surface Both Sides

**Decision:** When a finding routes to a knowledge record backed by a contested FACT/FINDING, the system MUST include the `contradiction` text in the remediation output. The LLM system prompt requires presenting both sides.

**Why:** Citeable is about citation accuracy. Presenting a contested claim as settled fact is exactly the kind of behavior the product exists to prevent. The 7 contested records (KT-007, KT-034, KT-035, KT-041, KT-063, KT-086, KT-176) have real disagreements that the user needs to know about.

**Rejected:** Hiding contested records from output (dishonest). Letting the LLM decide which side is right (not its job — that's an editorial decision). Marking contested records as deprecated (wrong — they're active but disputed).

**Consequence:** The `Resolution` model has `is_contested: bool` and `contested_reason: str`. The LLM system prompt says: "If a knowledge record is marked contested, present both sides." The QA gate checks: if any contested record was used, does the output contain qualifying language?

---

## D-020: Stale Records Get Warnings, Not Removal

**Decision:** Records past their `review_due` date are flagged with `⚠ Evidence may be stale (last verified {date})` but remain in active use. They are NOT automatically deprecated.

**Why:** A stale record is not necessarily wrong — it just hasn't been re-verified recently. Auto-deprecating would remove valid knowledge. Flagging lets the user know to treat it with appropriate caution.

**Rejected:** Auto-deprecating stale records (too aggressive — may remove correct knowledge). Ignoring `review_due` entirely (wastes the temporal governance data we built). Blocking output that uses stale records (too disruptive).

**Consequence:** `temporal.py::get_stale_records()` queries `WHERE review_due < date('now') AND status = 'active'`. The staleness flag is added to the `Resolution` object and rendered in the remediation card and export.

---

## D-021: `build_kb.py` Is Idempotent

**Decision:** Running `python -m areos.kb.build_kb` multiple times produces identical results. It drops and recreates all `kb_*` tables on every run.

**Why:** The JSONL corpus is the source of truth. The build script is a transform, not an incremental migration. Drop-and-recreate is simpler, safer, and guarantees no stale data.

**Rejected:** Incremental upserts (complex diff logic, risk of stale rows from deleted JSONL records surviving). Append-only (requires tracking what's already loaded, which is the same complexity as a full migration system).

**Consequence:** `build_kb.py` begins with `DROP TABLE IF EXISTS knowledge; DROP TABLE IF EXISTS kb_evidence; ...` then recreates and populates. The `claims` VIEW is recreated too. The old `claims` table data is gone — this is intentional. The `claims` VIEW reads from `knowledge`.

---

## D-022: Backward-Compatible `claims` VIEW Column Mapping

**Decision:** The `claims` VIEW maps columns exactly as old consumers expect: `kid → claim_id`, `scope → claim_scope`, `type → claim_type`, etc. Missing columns get sensible defaults.

**Why:** `app.js` queries `claim.claim_id`, `claim.statement`, `claim.source_url`, `claim.confidence`, `claim.status`, `claim.stage_id`, `claim.source_tier_value`. All of these must resolve from the VIEW or the Claims Browser breaks.

**Specific mappings:**
- `kid` → `claim_id` ✓
- `scope` → `claim_scope` ✓
- `type` → `claim_type` ✓ (but values change: "empirical" → "FACT", "policy" → "STANDARD", etc.)
- `statement` → `statement` ✓
- `status` → `status` ✓
- `confidence` → `confidence` ✓
- `last_verified_at` → `last_verified` ✓
- `NULL` → `superseded_by` (not tracked in new schema at record level)
- `NULL` → `stage_id` (replaced by `aeog_phases` JSON array — not mappable to single value)
- Source URL → subquery: `SELECT s.url FROM kb_evidence e JOIN kb_sources s ON e.sid=s.sid WHERE e.kid=k.kid LIMIT 1`
- Source tier → subquery: `SELECT s.authority FROM kb_evidence e JOIN kb_sources s ...`

**Consequence:** Test every filter in the Claims Browser: search, status, confidence, stage (stage will show "Unmapped" for all records since the VIEW returns NULL — this is acceptable since the new Knowledge Explorer uses AEOG phases instead).

---

## D-023: MANUAL_REMEDIATION_TEXT Becomes GUIDANCE Records

**Decision:** The 14 entries in `MANUAL_REMEDIATION_TEXT` (instruction cards C052–C090) are added to `knowledge.jsonl` as GUIDANCE records, then the Python dict is deleted.

**Why:** Single source of truth. If remediation text is in the corpus, it can be updated without a code deploy, it has evidence chains, and it appears in the Knowledge Explorer.

**Rejected:** Keeping them as a separate dict (two sources of remediation text is confusing). Moving them to a separate JSONL file (unnecessary fragmentation — they're GUIDANCE records like any other).

**Consequence:** Add 14 new records to `knowledge.jsonl` with `type: "GUIDANCE"`, linking to relevant check codes. Delete the `MANUAL_REMEDIATION_TEXT` dict. Verify the manual review wizard still renders correctly.

---

## D-024: The `kb_meta` Table Tracks Corpus Version

**Decision:** A `kb_meta` table stores `{version, rebuilt_at, record_count, source_count, evidence_count, embedding_model, embedding_count}`. Incremented on every `build_kb.py` run.

**Why:** The `/api/v1/kb/status` endpoint needs to report corpus health. The `version` number lets operators know if the corpus has been rebuilt after a JSONL update. The `embedding_count` tells them if embeddings are available (RAG enabled) or not.

**Consequence:** `build_kb.py` writes one row to `kb_meta` after loading. `GET /api/v1/kb/status` reads this row.

---

## D-025: Hot Reload via API and CLI

**Decision:** Two ways to rebuild the corpus: `python -m areos.kb.build_kb` (CLI) and `POST /api/v1/kb/reload` (API, admin-only).

**Why:** CLI is for deploy scripts and local development. API is for production hot-reload without SSH access to the server.

**Rejected:** Auto-reload on file change (complex file watcher, risky in production). Reload on every request (absurd overhead). No reload mechanism (requires full redeploy for knowledge updates).

**Consequence:** The API endpoint calls the same `build_kb.build()` function as the CLI. It requires `verify_admin` (Bearer token). It returns `{status: "ok", version: N, records: 202}`.

---

## D-026: No Hard Deletes in Knowledge Corpus

**Decision:** Knowledge records are never deleted from `knowledge.jsonl`. They are set to `status: "archived"` or `status: "deprecated"`. Archived records are excluded from RAG search and deterministic routing but remain queryable in the Knowledge Explorer.

**Why:** Audit trail. If a record was ever used in a remediation report, removing it from the corpus makes that report non-reproducible.

**Consequence:** All queries that power RAG include `WHERE status NOT IN ('archived', 'deprecated')`. The Knowledge Explorer shows archived records with a visual indicator but doesn't hide them.

---

## D-027: LLM System Prompt Contract

**Decision:** The LLM system prompt explicitly states 7 rules: only assert facts from provided records, present both sides of contested knowledge, flag low-confidence, label deprecated, cite specific sources, flag insufficient knowledge, don't add training-data facts.

**Why:** The LLM is a narrator, not a knowledge source. Every specific claim in its output must trace to a KT record. This is enforceable via the QA gate.

**Consequence:** The system prompt is stored in the `synthesis_prompts` table (editable via Synthesis Prompts page) with the 7 rules as a preamble. The QA gate validates rules 1, 2, 5, and 6 programmatically.

---

## D-028: Enrichment Records Are Optional Context

**Decision:** RAG Enrichment records (tier 2) are passed to the LLM as `"enrichment_context"`, not `"governing_claims"`. The LLM may use them to add depth but is not required to cite them.

**Why:** Enrichment records are related knowledge, not the primary basis for the recommendation. If the LLM mentions them, great. If not, the output is still valid. This prevents over-citation where every paragraph cites 5 records.

**Consequence:** `_build_synthesizer_input()` separates `primary_knowledge` (from deterministic or RAG primary) from `enrichment_context` (from RAG enrichment tier). The system prompt says: "You may reference enrichment context for additional depth, but your recommendations must be grounded in the primary knowledge records."

---

## D-029: UI Text Changes Are String-Only, No Layout Changes

**Decision:** Phase 8 UI text updates (e.g., "Claims Browser" → "Knowledge Explorer") are pure string replacements. No HTML structure changes, no CSS changes, no new components.

**Why:** The UI is "flagship quality" (user's words). Layout and UX are not being redesigned. The knowledge architecture upgrade is an engine change, not a UI redesign. The Knowledge Explorer upgrade (Phase 4) adds data to the existing drawer; it doesn't redesign the page.

**Consequence:** Use find-and-replace. Don't refactor components. Don't change CSS classes. Don't move elements.

---

## D-030: Test Strategy — Parity Tests Before Anything Else

**Decision:** Phase 2 creates `test_kb_parity.py` BEFORE deleting the old dicts. This test asserts that for every check code in the old `PRIORITY_SCORES` dict, the new DB-driven function returns the identical value. Only after this test passes do we delete the old dicts in Phase 7.

**Why:** If the new system produces different priorities or remediation text for any existing check code, that's a regression. The parity test is the safety net that lets us delete old code with confidence.

**Consequence:** The old dicts stay in the codebase (but unused) through Phases 2–6. They're only deleted in Phase 7, after parity tests have been passing for the entire implementation.
