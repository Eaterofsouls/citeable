# DECISIONS.md — Master Architecture Decision Records
**System:** Citeable AEOGEO Autonomous Audit & Knowledge Platform
**Author:** Elena, CTO & Principal Architect — Master Convergence Pass
**Grounding basis:** Every ADR below cites the exact file/line evidence re-verified directly against the shipped `citeable_audit_pkg_6_principal_architect_master.zip` source tree during this pass (see `MASTER_ARCHITECTURAL_DIRECTIVE.md §1` for the verification log). Source report attributions are given so provenance is traceable.

---

## DEC-01 — Decouple mobile navigation from `.topbar` presence
**Domain:** Frontend · **Priority:** P1 High (accessibility) · **Source:** REPORT_1 §2.1

**Context & Problem.** `nav.js::renderNav()` injects the mobile hamburger button, its click handler, and the run-context chip **entirely inside** `if (topbar && …)`. Re-verified directly: `byok.html`, `case_study.html`, `docs.html`, and `index.html` contain no `class="topbar"` element (`index.html` only has `results-topbar`, a results-tab-only element). On these four of the app's nine in-scope pages, the hamburger is never created and the sidebar's only open-trigger is never wired — on a viewport under 768px the sidebar is permanently unreachable with no fallback (the ⌘K palette is keyboard-only, see DEC-02).

**Decision Taken.** Inject the mobile menu button unconditionally from `renderNav()`, fixed-position at the top of `.main-content`, independent of `.topbar`. Keep the existing chip/breadcrumb injection gated on `topbar` (those are cosmetic enhancements, not navigation-critical).

**Trade-offs & Alternatives Considered.**
- *Add `.topbar` to the 4 missing pages instead* — rejected: larger diff across 4 page layouts for a fix that belongs in the one shared script that already owns this responsibility.
- *Ship a separate mobile-only nav component* — rejected: violates Karpathy Principle #2 (unjustified new abstraction) when the existing hamburger logic only needs its gating condition removed.

**Systemic Consequences.** Zero behavior change on the 5 pages that already have `.topbar`. Restores baseline mobile navigability on 4 pages. No backend impact.

**Regression Gate:** New Playwright/manual check at 375/414/768px on all 9 pages confirming a tappable, functioning hamburger exists and opens the sidebar. See TASK-01.

---

## DEC-02 — Consolidate the Guided Review / BYOK / Docs / outbound-link visual-polish defects into one UI remediation pass
**Domain:** Frontend · **Priority:** P2 Medium · **Source:** REPORT_1 §2.2–2.8, §3

**Context & Problem.** Five independently small but real defects share a root cause class ("a redesign or a11y pass touched some, not all, of a component family"): the verdict-button `border-color !important` override half-applies a redesign (§2.2, re-verified: `index.css` sets only `border-color` against inline `background`/`color`); the BYOK eye-toggle button ships with no icon content (§2.4, re-verified: `<button id="byok-toggle-eye" …></button>` is empty in `byok.js`); the docs error state uses the same near-white grey as the loading state (§2.3); one of two adjacent outbound claim links in `app.js` is missing `rel="noopener noreferrer"` (§2.5, re-verified at the two cited line pairs); and `--neon-cyan`/`--neon-emerald`/`--neon-green` are referenced with no fallback and never defined in `:root` (§2.8), silently collapsing three data-forward UI elements to inherited body-text color.

**Decision Taken.** Ship all five as one batched UI-polish PR using the exact diffs REPORT_1 §5.1–§5.6 already supplies (they are minimal, self-contained, and independently verified against the correct call sites). Also fold in the two P3 items (⌘K entry point, onboarding tour scoped to one page — §2.6/2.7) and the Historical-Delta subtext bug (§3, `studio.js:241`, the copy claims an "upward trend" even when the score demonstrably declined) into the same pass, since they touch the same files.

**Trade-offs & Alternatives Considered.** Splitting into 8 separate PRs was considered and rejected — each diff is 1–15 lines against a different file with no shared risk surface, so the review overhead of 8 PRs exceeds the benefit; one PR with 8 clearly labeled commits preserves bisectability without the process tax.

**Systemic Consequences.** Pure CSS/JS/copy changes, zero API or schema surface. The Historical-Delta fix (conditional subtext) is the one item here with real executive-trust stakes — a dashboard currently capable of asserting "citation velocity trending up" beside a red, declining number is a credibility risk independent of severity grading.

**Regression Gate:** Visual snapshot diff on the 4 touched screens + a unit assertion that `studio.js`'s delta subtext branches on `diff >= 0`. See TASK-02.

---

## DEC-03 — Route BYOK custom/Azure LLM endpoints through `resolve_and_validate()` and require auth on the routes that reach them
**Domain:** Backend / Security · **Priority:** P0 Blocker (unauthenticated SSRF) · **Source:** REPORT_5 §2.2

**Context & Problem.** Re-verified directly, three independent facts converge into a critical, unauthenticated SSRF:
1. `areos/llm/providers/__init__.py` has **no import of `areos.util.ssrf`** anywhere in the module (confirmed by grep) — `_azure_call`/`_custom_call` → `_make_request()` issue raw `_requests.post(url, …)` with zero validation.
2. `_build_waterfall()` (lines 268–280) builds `azure_base`/`custom_base` directly from `ck.get("azure_base")` / `ck.get("custom_base")` — i.e., directly from the caller-supplied `client_keys` dict, no default, no allowlist.
3. `POST /api/v1/audit/orchestrate` and `POST /api/v1/audit/runs/{run_id}/synthesize` accept this dict behind only a rate limiter (`Depends(check_rate_limit)`) — **no `verify_admin`** on either route (confirmed by reading every dependency on both routes).

The result: an anonymous, unauthenticated caller can supply `X-Api-Base-Custom: http://169.254.169.254/latest/meta-data/` (or any internal host) and the server will issue an outbound POST to it on the caller's behalf. Response bodies aren't echoed to the caller (synthesis-pipeline `RuntimeError` handling degrades gracefully — verified in `llm/synthesis_pipeline.py`), but up to 200 chars of the internal response land in server logs (`_make_request`'s `r.text[:200]`), and the primitive itself (arbitrary POST, attacker-chosen body, against an attacker-chosen internal destination) is severe independent of response echo.

Notably, `routers/byok.py::verify_api_key` **already** declines to probe `azure`/`custom`/`ollama` "to prevent SSRF against internal/private endpoints" (verified at `byok.py`'s `_offline` branch) — the mitigation exists in the codebase's own design vocabulary, it just wasn't applied to the code path that actually matters (the real LLM waterfall used during a live audit run), only to the lower-stakes diagnostic verify endpoint.

**Decision Taken.**
1. Validate `custom_base`/`azure_base` through `resolve_and_validate()` (the same function `safe_get()` already uses) before constructing any outbound URL in `_azure_call`/`_custom_call`, rejecting private/link-local/loopback/metadata ranges exactly as `ssrf.py` already does for target-domain audits.
2. Require `verify_admin` — or, if anonymous self-serve audits are a hard product requirement, a materially stricter per-key/per-session rate limit plus mandatory server-side opt-in — on `/audit/orchestrate` and `/audit/runs/{id}/synthesize`.
3. If genuine self-hosted/Ollama use is required, gate that specific bypass behind an explicit **server-operator** environment flag (`CUSTOM_LLM_BASE` already exists as an env-var-only path for this — see `providers/__init__.py:277`) rather than a client-supplied header, so an operator, not an anonymous caller, decides whether local-network reachability is acceptable for their deployment.

**Trade-offs & Alternatives Considered.** Simply removing client-supplied `custom_base`/`azure_base` entirely was considered — rejected because it removes a legitimate BYOK product feature (self-hosted/local model support) rather than fixing the actual defect (missing validation).

**Systemic Consequences.** This is a genuine security regression fix with no scoring/API-contract change for well-formed requests; it only rejects requests whose supplied base URL resolves to a disallowed IP range. Requires a new unit test asserting `_azure_call`/`_custom_call` raise on private-range targets, matching the existing `ssrf.py` test pattern.

**Regression Gate:** New adversarial test (`test_ssrf_byok_llm_endpoints.py`) sending `custom_base`/`azure_base` values pointed at `127.0.0.1`, `169.254.169.254`, and an internal-range literal against `/audit/orchestrate`, asserting rejection before any outbound request is attempted. See TASK-03 (P0, blocks release).

---

## DEC-04 — Explicit sign-off on the BYOK verify-endpoint credential-oracle pattern
**Domain:** Backend / Security · **Priority:** P1 High · **Source:** REPORT_5 §2.3

**Context & Problem.** `routers/byok.py::verify_api_key` has no `verify_admin` dependency, only a 15/min/IP rate limit, and performs live auth pings against real providers (OpenAI, Anthropic, Groq, Gemini, etc.) using a caller-supplied key, anonymizing the checking request's origin from the provider's perspective. This is documented in the endpoint's own docstring as an intentional "zero credential retention" design, but it functions as an anonymous, IP-rate-limited credential-validation oracle, a known target for credential-stuffing tooling. This is a **product/risk decision**, not a code defect — the code does exactly what its own design intends.

**Decision Taken.** Accept the feature as-is for this release **conditional on** an explicit, documented sign-off from product/security ownership (not a silent pass), plus one hardening measure that doesn't change the zero-retention promise: tighten the rate limit key from per-IP to per-IP **and** require a lightweight proof-of-origin (e.g., a short-lived session token issued to the browser session, not tied to any account) to raise the cost of IP rotation-based abuse without adding account requirements or key retention.

**Trade-offs & Alternatives Considered.** Requiring `verify_admin` was rejected — it would break the anonymous, no-signup BYOK onboarding flow this endpoint exists to support. Silently accepting the current 15/min/IP limit without escalation was also rejected — the master gate's job is exactly to force this kind of decision into a recorded ADR rather than let it pass by default.

**Systemic Consequences.** No schema or route change if the sign-off is granted as-is; a minor addition (session-token dependency) if the hardening is adopted.

**Regression Gate:** No code gate if accepted as-is beyond documenting the decision; if hardened, a new test asserting the session-token dependency rejects requests without one. See TASK-04.

---

## DEC-05 — Reorder `BodySizeLimitMiddleware` to the outermost position in the ASGI stack
**Domain:** Backend / Concurrency & Protocol Robustness · **Priority:** P1 High (per-request crash, not process-wide) · **Source:** REPORT_5 §4.2–4.4

**Context & Problem.** Re-verified the registration order directly in `areos/api/main.py`: `_correlation_id_middleware` and `_security_headers_middleware` are registered via `@app.middleware("http")` (Starlette `BaseHTTPMiddleware`, backed by `anyio` task groups) **before** `app.add_middleware(BodySizeLimitMiddleware)`. `_PayloadTooLarge` is deliberately a `BaseException` subclass so it survives Starlette's `ExceptionMiddleware` (which only catches `Exception`) — but the two outer `BaseHTTPMiddleware` layers' task-group machinery intercepts it first, re-raising as a `BaseExceptionGroup` that `BodySizeLimitMiddleware`'s own `try/except _PayloadTooLarge` never gets a clean shot at. Net effect, specifically for **true chunked/streamed uploads with no declared `Content-Length`**: the client gets a broken connection with no response at all (not the documented `413`), while declared-length oversized requests are handled correctly. REPORT_5 verified a live fix (reordering middleware registration so `BodySizeLimitMiddleware` is outermost) restores the clean `413` with no regressions across the adversarial and DOM-sweep suites.

**Decision Taken.** Adopt REPORT_5's verified fix: register `app.add_middleware(BodySizeLimitMiddleware)` before the two `@app.middleware("http")` decorators run, making it the outermost user middleware.

**Trade-offs & Alternatives Considered.** Catching `BaseExceptionGroup` inside the two `BaseHTTPMiddleware` layers instead was considered — rejected as a more invasive, error-prone change touching two unrelated middlewares to fix a problem that has a one-line ordering fix at its actual source.

**Systemic Consequences.** None for declared-length requests (already correct). Chunked/streamed oversized requests now fail cleanly with `413` instead of a broken connection.

**Regression Gate:** Fix `tests/test_adversarial_stream_fuzzing.py::test_streaming_chunked_boundary_exceeded` to actually construct an undeclared-length body (it currently sends `bytes`, which `TestClient`/`httpx` auto-attach `Content-Length` to, so it never exercises this path — confirmed directly) and correct its target URL from the nonexistent `/api/v1/audit/observe/test-run` to the real `POST /api/v1/audit/runs/{run_id}/observations`. See TASK-05.

---

## DEC-06 — Move long-running audit orchestration off the request/response cycle
**Domain:** Backend / Concurrency & Scalability · **Priority:** P1 High · **Source:** REPORT_3 §2.3 (Finding S-1)

**Context & Problem.** `POST /api/audit/orchestrate` is a synchronous (`def`, not `async def`) handler running the full `run_orchestrated_audit()` pipeline inline — page fetches, multiple auditor passes, one or more outbound LLM calls — with no background-job abstraction (`areos/jobs/__init__.py` is a confirmed 0-byte placeholder). Confirmed: **all 34 route handlers in the app are synchronous**, so every one is dispatched through AnyIO's default threadpool (cap 40), including `/api/health`. Two concrete risks: (1) on Render `SIGTERM` during redeploy, an in-flight audit cannot be gracefully cancelled — the request is simply dropped once the grace window elapses, with no resumption; (2) under a burst of concurrent audits, the threadpool can be exhausted, starving `/api/health` itself and causing Render to restart a container that was merely busy.

**Decision Taken.** Unify the existing `POST /audit/runs` enqueue-and-return-`run_id` pattern (already present at `audit.py:99` per REPORT_3's own note) with `/audit/orchestrate`, moving execution behind an explicit job dispatch so the HTTP handler returns immediately and the client polls `GET /audit/runs/{run_id}` (or the existing `audit_runs.status` column) for completion.

**Trade-offs & Alternatives Considered.** Introducing a full task-queue dependency (Celery/RQ/arq) was considered and rejected for this pass — the codebase's own "zero-dependency architecture" convention (already stated for the LLM waterfall) and the modest current scale don't justify the operational overhead; an in-process background-task pattern (FastAPI `BackgroundTasks` or a lightweight thread-per-run with DB-backed status) is the minimal sufficient fix and keeps `areos/jobs/` as the natural home for it, consistent with the README's own stated (if currently unimplemented) intent for that package.

**Systemic Consequences.** This is the single highest-leverage change in the entire deployment-readiness domain per REPORT_3's own assessment — it simultaneously fixes graceful-shutdown safety and threadpool starvation risk. It does change the client contract for `/audit/orchestrate` (synchronous response → `run_id` + poll), so this requires a UI change in `studio.js`'s run-trigger flow and should ship together with DEC-01/DEC-02's UI batch or immediately after.

**Regression Gate:** New test asserting `/audit/orchestrate` returns within a fixed short bound (e.g. <500ms) regardless of pipeline duration, plus a polling-completion test against a mocked slow pipeline. See TASK-06.

---

## DEC-07 — Enforce deprecated-status suppression consistently across the deterministic router, scoring table, and remediation snippets
**Domain:** KB / RAG Semantic Integrity · **Priority:** P1 High (semantic-honesty / governance gap) · **Source:** REPORT_4 (Executive Summary, Finding 1, Finding 2)

**Context & Problem.** Re-verified directly: `areos/kb/CHECK_CODE_REGISTRY.md` marks 8 check codes `⛔ DEPRECATED` (`LLMS_TXT_MISSING`, `LLMS_TXT_MISSING_SECTION`, `LLMS_TXT_NO_LINKS`, `LLMS_TXT_EMPTY_CONTENT`, `GOOGLE_EXTENDED_MISSING`, `GPTBOT_MISSING`, `AUTHORITY_DR_LOW`, plus one more per the registry) with explicit stated reasons (e.g. "conflates training crawler with search crawler," "references Moz DR, not used by any AI platform"). Yet `robots_checker.py`, `authority_auditor.py`, and `scoring.py:LAYER_DEDUCTIONS` still emit these as live findings and subtract real score points (confirmed by direct grep: all 8 codes appear as live `RobotsIssue`/`AuthorityIssue` emissions and `LAYER_DEDUCTIONS` entries). The one place this is accidentally suppressed — `router.py`'s deterministic resolver — does so as a **side effect of a bug** (single-row fetch with no status check, falling through to RAG and landing on `INSUFFICIENT`), not by design, and the automated `verify_kb_semantic_parity.py` gate (re-run directly during this pass: **PASS, 77/77 codes synchronized**) only checks that a mapped KID *exists*, never that its `status` is `active` — so it structurally cannot catch this defect class.

**Decision Taken.**
1. **Root cause (upstream):** retire the 8 deprecated codes from `robots_checker.py`, `authority_auditor.py`, and `scoring.py:LAYER_DEDUCTIONS` in lockstep with their KB status — either stop emitting them as findings entirely, or emit them as informational-only (no score deduction, no remediation snippet) with a `superseded_by`/rationale pointer, consistent with `DECISIONS.md`'s own stated invariant that RAG queries filter `status NOT IN ('archived','deprecated')` (currently true only for the RAG tier).
2. **Gate fix:** extend `verify_kb_semantic_parity.py` to fail if any mapped KID's `status` is `archived`/`deprecated`, per the exact fix REPORT_4 already drafted (`if knowledge_by_kid[g]["status"] in ("archived","deprecated"): errors.append(...)`).
3. **Router fix:** make the deterministic tier's status check explicit and status-aware rather than relying on the incidental RAG-fallback path, so a deprecated code produces a clear, intentional "retired check" result instead of an accidental "insufficient knowledge" one.

**Trade-offs & Alternatives Considered.** Leaving the 8 codes live "because they're currently accidentally suppressed anyway" was rejected — the suppression is a bug in one code path (`router.py`) and does not touch the three code paths (scoring, robots checker, orchestrator snippets) that actually drive user-facing scores and remediation advice today; those users are being told something is broken that the platform's own research says isn't.

**Systemic Consequences.** Score outputs for any site currently penalized by these 8 codes will improve (correctly) once deployed; this is a scoring-behavior change and should be called out in release notes / the next scorecard-methodology update, not silently shipped.

**Regression Gate:** Update `verify_kb_semantic_parity.py` per the drafted fix (now a required, not advisory, CI gate step — see DEC-09/TASK-19); add unit tests asserting none of the 8 codes appear in a fresh `run_orchestrated_audit()` result for a fixture site that would previously have triggered them. See TASK-07 (P1, blocks release per the master's own "100% check code semantic parity" sign-off requirement in §3.D below).

---

## DEC-08 — Resolve the `kb_meta` schema collision between `build_kb.py` and `migrate_audit_tables.py`
**Domain:** KB / Data Integrity · **Priority:** P0 Blocker (data corruption risk) · **Source:** REPORT_2 R-01

**Context & Problem.** Re-verified directly: `migrate_audit_tables.py` creates `kb_meta(id INTEGER PRIMARY KEY CHECK (id=1), kb_version TEXT NOT NULL DEFAULT '2026.01.01.0', …)`. `build_kb.py` independently `DROP TABLE IF EXISTS kb_meta;` then `CREATE TABLE kb_meta (…)` with a **weaker** schema (no `CHECK`, no `NOT NULL DEFAULT`), and its final `staging_conn.backup(conn)` copies that weaker table — and its data — back over the live one on every KB rebuild, silently discarding the constraints `migrate_audit_tables.py` established. Independently, `build()`'s version-read query (`SELECT value FROM kb_meta WHERE key='version'`) targets a `key`/`value` column shape that belongs to the *other* table `build_kb.py` also creates (`kb_metrics`), not `kb_meta` — confirmed by the actual `INSERT INTO kb_meta (id, kb_version, last_updated, total_claims, updated_by) VALUES (...)` statement at `build_kb.py:349`, which has no `key`/`value` columns at all. The query therefore always raises `sqlite3.OperationalError`, is masked by a bare `except Exception: pass`, and `current_version` is permanently stuck at 0 — every rebuild silently reports itself as "version 1" regardless of actual history.

**Decision Taken.** `kb_meta` becomes exclusively owned by `migrate_audit_tables.py`/`kb_version.py`, matching what the existing code comments already claim should be true:
1. Delete the `DROP TABLE IF EXISTS kb_meta;` / `CREATE TABLE kb_meta (…)` block from `build_kb.py`'s `SCHEMA_SQL` entirely.
2. Change the version-read query to target `kb_metrics` (its actual `key`/`value` shape), or call `kb_version.get_kb_version()` directly instead of hand-rolling a second read path.
3. Narrow the swallowing `except Exception: pass` to `except sqlite3.OperationalError: pass` at minimum, so an unrelated future failure isn't silently masked the same way this one was.

**Trade-offs & Alternatives Considered.** Making `build_kb.py`'s schema the canonical one (dropping the `CHECK`/`NOT NULL DEFAULT` constraints from `migrate_audit_tables.py` instead) was rejected — those constraints are the correctness guarantee, and weakening them to match the accidental collision is fixing the symptom in the wrong direction.

**Systemic Consequences.** Once fixed, `kb_meta.kb_version` will begin incrementing correctly on rebuild instead of being permanently stuck — this is a visible, expected behavior change in any KB-version-reporting UI surface (worth a release note, not a silent fix, since an operator watching that field for the first time post-fix will see it move for the first time).

**Regression Gate:** New test asserting `build_kb.build()` followed by `kb_version.get_kb_version()` returns a version string that increments on a second rebuild call, and that the `CHECK (id=1)` constraint survives a rebuild (attempt an `id=2` insert post-rebuild and assert it's rejected). See TASK-08 (P0, blocks release — this is a live data-corruption pathway on every KB rebuild, not a theoretical one).

---

## DEC-09 — Stand up a CI/CD pipeline with staged, non-blocking-then-blocking gates
**Domain:** DevOps · **Priority:** P1 High · **Source:** REPORT_3 §3

**Context & Problem.** Confirmed directly: no `.github/`, `.gitlab-ci.yml`, `Jenkinsfile`, or pre-commit config exists anywhere in the repository. 334 real, passing test functions across 38 files, and a working semantic-parity gate, currently run **zero times automatically** — `render.yaml` deploys straight from `branch: main` on every push, so the only gate between a broken commit and a production redeploy is whether a human happened to run `pytest` locally first. Two pre-existing conditions must be accounted for or a naive pipeline is red on its first run: (a) the codebase has never been run through `black`/`flake8` (confirmed: 104/122 files would reformat under `black --check`; ~770 `flake8` findings at a 120-char line limit); (b) only 4 of 38 test files reference the `AREOS_TEST_DB` isolation override, there is no `conftest.py`, and `pytest.ini` sets no environment — so an un-isolated `pytest` run falls through to the real committed `areos.db`.

**Decision Taken.** Adopt REPORT_3's drafted `.github/workflows/ci.yml` (already present in this audit package at `report3/ci.yml`) as the starting pipeline, with the same staged-gate design it specifies: `lint` job (black/flake8/mypy) runs **advisory** (`continue-on-error: true`) until a one-time normalization commit lands, then flips to blocking; `test` job forces `AREOS_TEST_DB` to a disposable per-run path at the CI-environment level (closing gap (b) without waiting on a `conftest.py` migration) and runs `pytest -v` followed by `python scripts/verify_kb_semantic_parity.py` (updated per DEC-07) as a **blocking** step; `docker` job builds the image and Trivy-scans it, gated on `test` passing first, with a container-boot smoke test against `/api/health`.

**Trade-offs & Alternatives Considered.** Making lint blocking from day one was rejected — REPORT_3's own empirical finding (104/122 files, 770 findings) means a same-day-blocking lint gate would be red on the very next unrelated commit, training engineers to ignore CI red, "the worst possible outcome for a new pipeline." Rejecting the disposable-test-DB CI env var in favor of waiting for a proper `conftest.py` fixture was also rejected — the env-var-level fix (DEC-09's `test` job) closes the isolation gap immediately, and `conftest.py` (TASK-09b) can land as a fast-follow without blocking the pipeline's introduction.

**Systemic Consequences.** This is process infrastructure, not application code — zero runtime behavior change. It is, however, the precondition for every other ADR's "regression gate" in this document actually running automatically rather than depending on a human remembering to.

**Regression Gate:** The pipeline's own first green run against `main`, plus a deliberate `black .` normalization commit landing within one sprint of pipeline introduction (tracked separately, not blocking pipeline launch). See TASK-09.

---

## DEC-10 — Reconcile Docker image database seeding intent and add a real backup/DR mechanism
**Domain:** DevOps · **Priority:** P1 High · **Source:** REPORT_3 §2.1 (D-1), §2.2, §5

**Context & Problem.** `.dockerignore` contains a comment claiming dev/test SQLite databases were fixed to no longer ship in the image, but **no `*.db`/`*.db-shm`/`*.db-wal` glob pattern actually exists in the file** (confirmed: `grep -n db .dockerignore` returns only prose). `areos.db` (2.4 MB) + WAL/SHM siblings ship into every image via `COPY . .`. This is not just hygiene: `get_db_path()`'s Render branch auto-seeds a fresh `/data/areos.db` from whatever `areos.db` shipped in the image — meaning the `.dockerignore` comment ("don't ship it") and the runtime logic ("we depend on it for seeding") describe two contradictory intents, and any real audit-run data accumulated in the committed `areos.db` by commit time ships to every new deployment's first boot as if it were canonical seed data. Separately, **no backup or disaster-recovery mechanism exists anywhere** — a lost or corrupted Render disk means total data loss with no recovery path beyond whatever `areos.db` happens to be checked into git.

**Decision Taken.**
1. Replace image-embedded DB seeding with an explicit, reviewed seed artifact: run `build_kb.py` once against the empty disk on first boot (the KB build pipeline is already idempotent — confirmed), and add the missing `.dockerignore` entries so `areos.db`/`-wal`/`-shm` stop shipping in the image at all.
2. Add `scripts/backup_db.py` (SQLite online-backup API, safe under concurrent WAL writers — code already drafted in REPORT_3 §5.2) as a scheduled Render Cron job or GitHub Actions workflow, retaining 7 daily + 4 weekly snapshots to off-Render object storage.
3. Document the restore runbook (REPORT_3 §5.4) as an actual ops playbook, not just an audit artifact.

**Trade-offs & Alternatives Considered.** Keeping image-embedded seeding and just fixing the misleading `.dockerignore` comment was considered as the minimal fix — rejected in favor of the explicit-seed-artifact approach because it's the only option of the two that makes "what data ships to a fresh environment" a reviewable, versioned artifact instead of a binary blob's incidental contents at commit time, and because it's what's needed to make D-4/`nonexistent.db` cleanup (TASK-10c) meaningful rather than cosmetic.

**Systemic Consequences.** First-boot latency increases slightly (KB build runs once instead of a file copy), acceptable given the KB corpus size (216/199/114 records across the three main JSONL files). RPO/RTO with daily backups: ≈24h / ≈10–15min per REPORT_3 §5.5 — flag for explicit sign-off if the product's actual audit-run volume needs a tighter RPO (hourly snapshots are cheap at this data scale if so).

**Regression Gate:** CI `docker` job (DEC-09) confirms the built image contains no `*.db*` files; a scheduled backup-job dry-run confirms `backup_db.py` produces a valid, openable snapshot. See TASK-10.

---

## DEC-11 — Batch dead-code, duplicate-definition, and complexity-refactor cleanup
**Domain:** Code Sanity / Maintainability · **Priority:** P2–P3 · **Source:** REPORT_2 §3 (R-01…R-16), §4 (C-01…C-06)

**Context & Problem.** REPORT_2 catalogs 16 discrete redundancy/dead-code items and 6 complexity-refactor proposals, each independently re-verifiable and each low-risk in isolation (duplicate imports, a genuinely dead 280-line outcome-logging subsystem confirmed unregistered in `main.py`, four duplicate `ACTION_SNIPPETS` dict keys with **different** shadowed values — confirmed at the cited line pairs — a triplicated claim-enrichment code path across 3 call sites, etc.). R-01 (the `kb_meta` collision) and the `AUDIT_PHASE_CRASHED` duplicate-key item (R-08, independently re-flagged by REPORT_4 Finding 3 at the identical line pair — **merged, single task, not double-counted**) are broken out into DEC-08 and TASK-08/TASK-11 respectively given their higher severity; everything else in this ADR is genuine but non-blocking.

**Decision Taken.** Ship as a single "Code Sanity" cleanup PR, sequenced by blast radius: (1) delete dead code first (R-04 outcome-logger + router, R-05/R-12/R-13 orphaned schema-generator module) since deletion carries the least regression risk and immediately shrinks the diff surface for everything after it; (2) fix duplicate-definition bugs (R-02, R-03, R-11, R-16 — the four shadowed `ACTION_SNIPPETS` values are the only one of this group with a *behavioral* difference between the shadowed and live value, so it gets its own explicit before/after snippet-text diff in the PR description); (3) apply the six complexity refactors (C-01…C-06) as pure refactors with no behavior change, each backed by the existing test suite as the regression net.

**Trade-offs & Alternatives Considered.** Doing this as 16+ micro-PRs was rejected as disproportionate process overhead for changes this size and this well-isolated; one PR with clearly separated, individually-revertable commits achieves the same bisectability at a fraction of the review cost — consistent with Karpathy Principle #3 (surgical, traceable, but not artificially fragmented).

**Systemic Consequences.** None behavior-visible if done correctly — this is exactly why the existing 334-test suite (once CI-gated per DEC-09) is the right acceptance mechanism rather than new test authorship for most items; C-01 through C-06 specifically should ship with **zero** new test files and a green existing suite as the acceptance bar.

**Regression Gate:** Full existing `pytest` suite green (see §4 of the master directive for the current baseline) both before and after the PR merges, with no test file additions required for the refactor-only commits. See TASK-11 through TASK-16.

---

## DEC-12 — Correct the scope framing inherited from REPORT_2 and record the pre-existing, deliberately-untouched documentation drift
**Domain:** Governance / Documentation · **Priority:** Info (no code change) · **Source:** Master convergence pass, cross-referencing REPORT_2 §0 against the actual delivered package and `CHANGELOG.md`

**Context & Problem.** REPORT_2's own scope note states that `areos/ui/`, `areos/llm/`, `areos/services/`, `areos/util/`, and `tests/` were **absent** from the package it audited, and frames its dependency matrix accordingly (listing them under `EXT["External (not in this package)"]`). Directly re-verified against the actual delivered `citeable_audit_pkg_6_principal_architect_master.zip`: **all five directories are present** — `areos/ui/` (33 files), `areos/llm/` (2 files), `areos/services/` (8 files), `areos/util/` (5 files), and `tests/` (38 files, 334 test functions, executed directly during this pass — see §4 of the master directive). This is independently corroborated by the codebase's own `CHANGELOG.md`, which explicitly notes, in an entry predating REPORT_2, that "a `tests/` directory the README describes... isn't present in this export" — confirming REPORT_2 was run against an earlier, narrower export than the one delivered for this convergence pass, not that REPORT_2 made an error.

Separately, and already self-documented by the codebase: `README.md` prescribes `export Citeable_API_TOKEN=...` and describes a `conftest.py`/`pyproject.toml` that do not exist in this export, while the actual required variable (confirmed directly: `dependencies.py:9`) is `AREOS_API_TOKEN`. `CHANGELOG.md` itself records this as pre-existing drift, deliberately left alone by whoever wrote that changelog entry rather than guessed at. 28 of the 38 test files self-set `AREOS_API_TOKEN` at the module level, which is why the suite runs cleanly today despite the README's incorrect instruction — but a new contributor following the README verbatim would hit the fail-fast `RuntimeError` on their first run.

**Decision Taken.** (1) Re-scope REPORT_2's architectural dependency matrix as **internal, in-repo** for `ui/`, `llm/`, `services/`, `util/`, and `tests/` in all downstream planning — REPORT_2's specific per-file findings inside `auditors/`, `api/`, `db/`, `kb/`, `cli/` remain valid and are unaffected by this correction, since those directories were genuinely in scope both times. (2) Fix the README's `Citeable_API_TOKEN` → `AREOS_API_TOKEN` naming (a 7-line, zero-risk doc-only diff) and remove or clearly mark the `conftest.py`/`pyproject.toml` references as aspirational rather than present, since leaving a known-wrong quickstart command in the primary README actively breaks new-contributor onboarding for zero benefit — this is the one piece of "pre-existing drift" from `CHANGELOG.md` worth actually closing in this pass, distinct from drift that's genuinely ambiguous about which side is correct.

**Trade-offs & Alternatives Considered.** Leaving the README drift untouched, matching the prior changelog author's stated caution, was considered — rejected specifically for the `Citeable_API_TOKEN` item because this one is **not ambiguous** (the code path is unambiguous and directly confirmed), unlike genuinely unclear drift elsewhere; the prior author's caution was appropriate when it wasn't clear which side was stale, but a master convergence pass with direct source access is exactly positioned to resolve it.

**Systemic Consequences.** None to runtime behavior. Improves new-contributor onboarding correctness.

**Regression Gate:** None required beyond the doc diff itself; optionally, a lightweight CI doc-lint step could `grep` the README for `Citeable_API_TOKEN` post-fix to prevent regression, but this is optional polish, not a blocking gate. See TASK-17.
