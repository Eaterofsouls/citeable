# Forensic Engineering Audit: Gemini V2 Knowledge Architecture Changes

## 1. Executive Verdict

**Gemini's implementation has 3 critical production-breaking bugs, 2 high-severity regressions, and several medium architectural concerns.**

The overall architecture is sound — the migration from hardcoded Python dicts to a governed JSONL corpus with deterministic routing is a strong design decision. However, Gemini executed the cleanup phase (Phase 7) carelessly: it deleted the old dictionaries without verifying that **all references** to them were updated. This left behind dangling `NameError` bombs that **will crash the manual review pipeline** and silently degrade the automated recommendation pipeline under specific conditions.

The V2 Knowledge Router, build system, models, and API layer are well-designed and functional for the happy path. The test suite, however, is dangerously shallow — all 30 tests pass despite the confirmed production bugs.

---

## 2. What Gemini Changed

### Architecture (Created)
- `areos/kb/` module: `__init__.py`, `models.py`, `build_kb.py`, `router.py`, `embeddings.py`
- `areos/kb/corpus/`: `knowledge.jsonl` (216 records), `evidence.jsonl`, `sources.jsonl`, and mapping JSON
- `areos/api/routers/knowledge.py`: New REST API for the Knowledge Explorer
- `areos/ui/knowledge_explorer.html` + `.js`: New UI replacing Claims Browser
- Tests: `test_kb_parity.py`, `test_rag.py`, `test_knowledge_api.py`, `test_synthesis_enrichment.py`

### Integration (Modified)
- `areos/api/routers/audit.py`: Added V2 Knowledge Router calls in `synthesize_audit_run`
- `areos/auditors/synthesis_engine.py`: Added `_load_priority_scores()`, `_load_remediation_text()`; updated `RemediationPlan.format_markdown()` and `_build_automated_recommendations()` for V2 evidence
- `areos/llm/synthesis_pipeline.py`: Updated synthesizer input to include V2 fields
- `areos/ui/studio.js`: Updated evidence rendering and contested/stale badges
- `areos/ui/nav.js`: Replaced Claims Browser with Knowledge Explorer

### Cleanup (Deleted — Phase 7)
- Deleted `REMEDIATION_TEXT`, `MANUAL_REMEDIATION_TEXT`, and `PRIORITY_SCORES` dicts from `synthesis_engine.py`
- Emptied `_CHECK_CODE_MAPPINGS` in `areos/db/ingest_claims.py`

### Documentation
- `CHANGELOG.md`, `DECISIONS.md`, `CHECK_CODE_REGISTRY.md`, `GOVERNANCE_RULES.md`
- Updated `internal.md` and `external.md` (with corruption issues)

---

## 3. What Gemini Did Well

1. **The KB architecture itself is solid.** The JSONL → SQLite → Router pipeline is clean, well-separated, and idempotent (with caveats). The Pydantic models are well-defined with `extra='ignore'` for forward compatibility.
2. **BYOK embedding waterfall** is elegantly designed — Google → OpenAI → Mistral fallback with graceful degradation when no keys are available.
3. **The deterministic-first routing strategy** is correct. Avoiding LLM dependency for known check codes is the right design.
4. **The `claims` VIEW** provides backwards compatibility while the underlying data model is new. This is a good migration pattern.
5. **The DECISIONS.md** document is genuinely useful for onboarding and captures architectural rationale well.
6. **Error handling in `synthesis_pipeline.py`** is excellent — each LLM stage degrades gracefully and independently.

---

## 4. Confirmed Defects

### CRITICAL-001: `MANUAL_REMEDIATION_TEXT` NameError Crashes Manual Review Pipeline
- **Severity: Critical**
- **File:** [synthesis_engine.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py#L382-L389)
- **Reproduction:** Any `ManualFinding` with `verdict='fail'` or `verdict='warn'` crashes with `NameError: name 'MANUAL_REMEDIATION_TEXT' is not defined`
- **Verified:** Yes — see `scratch/test_manual_crash.py`
- **Impact:** The entire manual review synthesis pipeline is broken. Human-reviewed audit findings cannot be processed into recommendations.
- **Root cause:** Gemini deleted the `MANUAL_REMEDIATION_TEXT` dict (Phase 7 cleanup) without updating lines 382 and 389 that still reference it.

### CRITICAL-002: `REMEDIATION_TEXT` NameError — Latent Crash in `_load_remediation_text()`
- **Severity: Critical (latent)**
- **File:** [synthesis_engine.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py#L59)
- **Reproduction:** When the `knowledge` table exists but has zero active GUIDANCE records, line 59 (`return REMEDIATION_TEXT`) triggers a `NameError`. Currently masked by the outer `try/except` on line 89, which catches it and returns `{}`.
- **Impact:** Silent total failure — `_build_automated_recommendations` at line 289 skips every finding when `live_remediation` is empty, producing **zero** recommendations. No error is logged. The audit appears to complete successfully with an empty remediation plan.
- **Root cause:** Same as CRITICAL-001 — the dict was deleted but the fallback reference was left behind.

### HIGH-001: `build_kb.py` `claims_legacy` Rename Not Idempotent
- **Severity: High**
- **File:** [build_kb.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/build_kb.py#L91-L93)
- **Reproduction:** Run `build_kb.build()` → then run `ingest_claims.ingest()` (which creates a real `claims` table) → then run `build_kb.build()` again. The second build crashes with `sqlite3.OperationalError: table claims_legacy already exists`.
- **Impact:** On Render (ephemeral disk), this is mitigated because the DB is rebuilt fresh each deploy. On any persistent-disk deployment, this breaks the startup sequence.
- **Root cause:** `handle_claims_view` at line 93 does `ALTER TABLE claims RENAME TO claims_legacy` without checking if `claims_legacy` already exists.

### MEDIUM-001: `internal.md` Documentation Corruption
- **Severity: Medium**
- **File:** [internal.md](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/docs/internal.md#L98-L115)
- **Verified:** Yes — lines 98-100 begin a sentence about AP-03, then lines 102-113 inject the new §11 content mid-sentence, and line 114 has an orphaned continuation fragment.
- **Impact:** The internal technical documentation is structurally broken. A reader encounters an incomplete sentence flowing directly into a new section header.
- **Root cause:** Gemini's `replace_file_content` targeted a line number range incorrectly and injected the new section in the middle of an existing paragraph.

---

## 5. Likely Defects

### LIKELY-001: `ROUTES` Undefined in `nav.js` Cmd+K Palette
- **Severity: Medium**
- **File:** [nav.js](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/nav.js#L101)
- **Evidence:** `ROUTES` is used at line 101 but never defined anywhere in the UI codebase (verified via codebase-wide grep). If the Cmd+K palette existed before Gemini's changes, `ROUTES` may have been defined in a file Gemini removed or renamed.
- **Impact:** Typing into the Cmd+K palette throws `ReferenceError: ROUTES is not defined`. The feature crashes silently in the browser console.
- **Classification:** Likely (may predate Gemini's changes — needs git history to confirm attribution).

---

## 6. Long-term Architectural Risks

### RISK-001: RAG Search Loads All Embeddings Into Memory
- **Severity: Medium → High at scale**
- **File:** [router.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/router.py#L270-L274)
- **Description:** `_rag_search()` fetches ALL embedding vectors from SQLite into Python memory on every call. With 216 records this is fine. With 2,000+ records and 1536-dimensional vectors, each call loads ~12MB of JSON-encoded floats. During audit synthesis, this is called once per finding (30+ times).
- **Mitigation needed before:** Corpus exceeds ~500 records.

### RISK-002: Hardcoded API Token in `build_kb.py` 
- **Severity: High (Security)**
- **File:** [build_kb.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/build_kb.py#L8)
- **Description:** `os.environ.setdefault('AREOS_API_TOKEN', 'build_kb_token')` sets a trivially guessable default token. Because `build_kb.py` is imported transitively whenever `areos.kb` is loaded (which happens on every request via `findings_to_claims.py`), the token may be set before the real deployment token is configured.
- **Impact:** Any deployment where `AREOS_API_TOKEN` isn't set before `areos.kb` is first imported will have its admin API protected by the known string `'build_kb_token'`.

### RISK-003: Exception Swallowing in Critical Paths
- Multiple `except Exception: pass` blocks silently hide failures:
  - `router.py` line 159: Malformed `guidance_json` silently produces `None` guidance
  - `router.py` line 234: Malformed `review_due` date silently disables staleness checking  
  - `synthesis_engine.py` line 89: The outer except catches the NameError on line 59 and returns `{}` instead of failing loudly

### RISK-004: XSS in Knowledge Explorer
- **Severity: Medium**
- **File:** [knowledge_explorer.js](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/knowledge_explorer.js#L234-L240)
- **Description:** `formatText()` applies markdown-style regex replacements but does not escape HTML first. Content from `rec.statement` is inserted directly into innerHTML. Since the JSONL corpus is developer-maintained, this is self-XSS, but it violates defense-in-depth.

---

## 7. Data/State/Integration Risks

### DATA-001: Legacy `check_code_mappings` Table Now Empty
- **File:** [ingest_claims.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/db/ingest_claims.py#L62)
- Gemini emptied `_CHECK_CODE_MAPPINGS` to `{}`, so `ingest_claims.py` no longer populates the legacy `check_code_mappings` table. Multiple consumers still fall back to this table (audit.py lines 258, 264, 487; findings_to_claims.py lines 55-58). If the V2 `kb_check_code_map` fails to load, all fallback paths return nothing.

### DATA-002: `_load_priority_scores` Returns Empty Dict on Failure
- Previously returned 45 hardcoded priority scores. Now returns `{}` if the DB query fails. Every check code defaults to priority 10 (lowest urgency), meaning the prioritization of the remediation plan is **inverted** — critical findings like `CRAWLER_FULLY_BLOCKED` (was priority 1) are now treated the same as informational findings.

---

## 8. Performance/Scalability Risks

- **RISK-001** (above): O(n) brute-force vector search in Python
- **N+1 Queries in `_build_resolution`:** For each source citation, a separate `SELECT * FROM kb_sources WHERE sid = ?` query is executed (lines 202-210). Minor at current scale.

---

## 9. Security/Reliability Concerns

- **RISK-002** (above): Hardcoded default API token
- **RISK-004** (above): XSS in Knowledge Explorer
- **CHANGELOG.md** has mixed line endings (1 CRLF in 438 LF lines) from PowerShell `Set-Content`

---

## 10. Regression Risks

- Manual review synthesis pipeline is **completely broken** (CRITICAL-001)
- Automated recommendations silently return empty if GUIDANCE records are missing (CRITICAL-002)
- Legacy `check_code_mappings` fallback path now returns nothing (DATA-001)
- Priority ordering of recommendations may be wrong if DB is unavailable (DATA-002)

---

## 11. Things That Look Suspicious But Are Actually Safe

1. **Variable `f` shadowing in `audit.py` line 474:** The list comprehension `for f in res.backing_facts` shadows the outer `f` from `for step_idx, f in enumerate(...)`. In Python 3, list comprehension iteration variables are scoped to the comprehension and do **not** leak into the enclosing scope. The outer `f` retains its value after the comprehension. This is cosmetically bad but functionally correct.

2. **`safeUrl()` in `studio.js`:** Referenced but not defined in `studio.js`. It is correctly defined in `dom.js` (line 64) and loaded globally via script tag before `studio.js`.

3. **`CHECK_CODE_TO_CLAIM_IDS` import in `synthesis_engine.py`:** Unused import, but doesn't cause harm. Just dead code.

---

## 12. Things That Should Be Fixed Immediately

| Priority | Issue | Fix |
|---|---|---|
| 🔴 **P0** | CRITICAL-001: `MANUAL_REMEDIATION_TEXT` NameError | Load manual remediation text from KB (same pattern as `_load_remediation_text`), or define a `_load_manual_remediation_text()` function |
| 🔴 **P0** | CRITICAL-002: `REMEDIATION_TEXT` fallback NameError | Change line 59 from `return REMEDIATION_TEXT` to `return {}` |
| 🔴 **P0** | RISK-002: Hardcoded API token | Remove `os.environ.setdefault` from `build_kb.py` line 8; require explicit token configuration |

---

## 13. Things That Can Wait

| Priority | Issue |
|---|---|
| P1 | HIGH-001: `claims_legacy` rename idempotency |
| P1 | MEDIUM-001: `internal.md` document corruption |
| P1 | DATA-001: Empty legacy `check_code_mappings` fallback |
| P2 | LIKELY-001: `ROUTES` undefined in nav.js |
| P2 | RISK-003: Silent exception swallowing |
| P2 | RISK-004: XSS in Knowledge Explorer |
| P2 | DATA-002: Empty priority scores fallback |
| P3 | RISK-001: RAG search scalability |
| P3 | Mixed line endings in CHANGELOG.md |
| P3 | Unused `CHECK_CODE_TO_CLAIM_IDS` import |

---

## 14. Recommended Remediation Order

1. **Fix CRITICAL-001 + CRITICAL-002 immediately.** These are production-breaking and affect the core audit pipeline. ~30 minutes of work.
2. **Fix RISK-002 (hardcoded token).** Security issue. ~5 minutes.
3. **Fix HIGH-001 (claims_legacy idempotency).** Add `DROP TABLE IF EXISTS claims_legacy` before the rename. ~5 minutes.
4. **Repair `internal.md` corruption.** Remove the misplaced §11 content and re-insert it at the end. ~15 minutes.
5. **Add a `_load_manual_remediation_text()` function** that queries GUIDANCE records with card-ID check_codes, replacing the deleted dict. ~30 minutes.
6. **Add targeted tests** for the bugs found. The current test suite gave false confidence — all 30 tests passed despite 3 critical bugs. Add: a test that calls `_build_manual_recommendations` with an actionable finding; a test that calls `_load_remediation_text` against a DB with no GUIDANCE records. ~30 minutes.
7. **Address remaining P2/P3 items** as normal maintenance.

