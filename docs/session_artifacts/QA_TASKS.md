# QA REMEDIATION — ATOMIC TASKS

> **Session:** QA Remediation Pass (1 September 2026)
> **Prerequisite:** Read `QA_DECISIONS.md` BEFORE starting any task.
> **Rule:** After EACH phase, run `python -m pytest tests/ -v` and record result. Do NOT proceed if regressions.
> **Baseline:** 184/184 tests passing.

---

## Phase Q1: Unblock Core Features (CRITICAL Fixes)

### TQ-001: Wire `auditResult` Into Global Context
- **Goal:** Make the manual review wizard load after audit completes.
- **Decision:** D-QA-001
- **Files:** `areos/ui/studio.js`
- **Do:** Find the line `currentAuditData = data;` after the `/api/v1/audit/orchestrate` fetch resolves. Add immediately after:
  ```javascript
  window.AreosContext = window.AreosContext || {};
  window.AreosContext.auditResult = data;
  ```
- **Boundary:** Do NOT modify `guided_review.js`. Do NOT change how `currentAuditData` is used elsewhere.
- **Checkpoint:** `test_guided_review_wizard_loads`, `test_studio_audit_result_assignment`
- **Rollback:** Revert the 2 added lines.

### TQ-002: Remove `enrichCodeSnippet` Crash
- **Goal:** Make Executive Report export work without ReferenceError.
- **Decision:** D-QA-002
- **Files:** `areos/ui/studio.js`
- **Do:** Find `const code = enrichCodeSnippet(rec, domain);`. Replace with `const code = rec.remediation_snippet || '';`. If the next lines use `code` to build markdown, wrap in `if (code) { ... }`.
- **Boundary:** Do NOT create a new function. Do NOT change how remediation_plan is structured.
- **Checkpoint:** `test_export_executive_report_success`, `test_export_report_empty_audit`
- **Rollback:** Revert changed lines.

### TQ-003: Fix `manual_verdicts_context` NameError in Synthesize
- **Goal:** Make `/synthesize` endpoint return synthesized report instead of 500.
- **Decision:** D-QA-003
- **Files:** `areos/api/routers/audit.py`
- **Do:** 
  1. Before the `if observation_rows:` / `else:` conditional, add: `merged_human_count = 0`
  2. Inside the `if observation_rows:` block, add: `merged_human_count = len(observation_rows)`
  3. Inside the `else:` block (legacy path), add: `merged_human_count = len(verdict_rows)`
  4. At ~L786, replace `len(manual_verdicts_context)` with `merged_human_count`
  5. At ~L788 (if `manual_verdicts_context` appears again in the result dict), replace similarly.
- **Boundary:** Do NOT restructure the conditional. Do NOT change the LLM synthesis call.
- **Checkpoint:** `test_synthesize_endpoint_success`, `test_synthesize_endpoint_bad_input`
- **Rollback:** Revert changes to audit.py.

### TQ-004: Fix `audit_findings` Non-Existent Table Query
- **Goal:** Make `/full-report` endpoint return data instead of 500.
- **Decision:** D-QA-005
- **Files:** `areos/api/routers/audit.py`
- **Do:** Find `SELECT * FROM audit_findings WHERE run_id = ?`. Replace with:
  ```python
  row = conn.execute("SELECT automated_findings FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
  findings = json.loads(row[0]) if row and row[0] else []
  ```
- **Boundary:** Do NOT create a new table. Do NOT change the response shape.
- **Checkpoint:** `test_full_report_endpoint_query`
- **Rollback:** Revert SQL change.

### TQ-005: Define `ROUTES` Array in nav.js
- **Goal:** Make Cmd+K Command Palette work.
- **Decision:** D-QA-006
- **Files:** `areos/ui/nav.js`
- **Do:** At the top of the file (after any imports/constants), add:
  ```javascript
  const ROUTES = [
    {label: 'Studio', path: '/', icon: '🔬'},
    {label: 'Knowledge Explorer', path: '/knowledge', icon: '📚'},
    {label: 'Claims Browser', path: '/claims', icon: '📋'},
  ];
  ```
  Source the actual labels and paths from the existing `renderNav()` config in the same file.
- **Boundary:** Do NOT add routes for pages that don't exist.
- **Checkpoint:** `test_command_palette_routes_defined`
- **Rollback:** Remove the `ROUTES` const.

### Q1 Regression Checkpoint (8+ tests)
```
EXISTING (must still pass):
1. test_phase0_fixes — all 20 tests
2. test_track_b_manual_review — all 21 tests
3. test_synthesis_enrichment — all tests

NEW (must pass after Q1):
4. test_guided_review_wizard_loads — wizard init doesn't abort
5. test_studio_audit_result_assignment — AreosContext.auditResult is set
6. test_export_executive_report_success — export generates markdown
7. test_export_report_empty_audit — export handles null audit gracefully
8. test_synthesize_endpoint_success — POST /synthesize returns 200
9. test_synthesize_endpoint_no_observations — synth works with 0 human input
10. test_full_report_endpoint_query — GET /full-report returns findings from JSON column
11. test_command_palette_routes_defined — ROUTES.filter executes without crash
```

---

## Phase Q2: Fix Boot Crash (Schema Architecture)

### TQ-006: Reconcile `migrate_audit_tables.py` With V2 KB
- **Goal:** Prevent guaranteed boot crash after `build_kb.py` runs.
- **Decision:** D-QA-004
- **Files:** `areos/db/migrate_audit_tables.py`
- **Do:**
  1. Before `conn.executescript(schema_sql)`, add a check:
     ```python
     row = conn.execute("SELECT type FROM sqlite_master WHERE name='claims'").fetchone()
     is_v2_kb = row and row[0] == 'view'
     ```
  2. If `is_v2_kb`, filter out `CREATE TABLE ... claims` statements from schema_sql before executing.
  3. Fix `kb_meta` INSERT: detect schema version and use appropriate column names.
- **Boundary:** Do NOT modify `schema.sql`. Do NOT modify `build_kb.py`.
- **Checkpoint:** `test_schema_migration_handles_view_conflict`, `test_boot_sequence_integration`
- **Rollback:** Revert migrate_audit_tables.py.

### TQ-007: Add `INSERT OR REPLACE` in build_kb.py
- **Goal:** Prevent KB build crash on duplicate KIDs.
- **Decision:** D-QA-007
- **Files:** `areos/kb/build_kb.py`
- **Do:** Change `INSERT INTO knowledge` to `INSERT OR REPLACE INTO knowledge`. Add `logger.warning(f"Duplicate KID {kid} replaced")` after the execute.
- **Boundary:** Do NOT change the knowledge.jsonl format. Do NOT change other INSERT statements unless they have the same risk.
- **Checkpoint:** `test_build_kb_duplicate_kid_handling`
- **Rollback:** Revert build_kb.py.

### Q2 Regression Checkpoint (8+ tests)
```
EXISTING (must still pass):
1. test_phase0_fixes — all 20 tests
2. test_phase3_kb_scoring — all 13 tests
3. test_rag — all tests
4. test_kb_parity — all tests

NEW (must pass after Q2):
5. test_schema_migration_handles_view_conflict — migrate handles existing claims VIEW
6. test_boot_sequence_integration — build_kb() then app boot succeeds
7. test_build_kb_duplicate_kid_handling — duplicate KIDs logged and replaced
8. test_migrate_audit_tables_idempotency — 3x consecutive migrations succeed
9. test_app_starts_without_db — fresh boot creates schema correctly
10. test_kb_meta_dual_schema — INSERT works with both V1 (id) and V2 (key/value) formats
```

---

## Phase Q3: High Priority Fixes

### TQ-008: Move Input Locking Before Synthesis Fetch
- **Goal:** Prevent race condition where users modify inputs during synthesis.
- **Files:** `areos/ui/studio.js`
- **Do:** Move the `document.querySelectorAll('#wizard-list input, ...').forEach(el => el.disabled = true)` block to BEFORE the `await AreosAPI.fetch(...)` call in `triggerPostWizardSynthesis()`.
- **Boundary:** Do NOT change what gets disabled. Do NOT change the fetch call.
- **Checkpoint:** `test_studio_input_locking_timing`

### TQ-009: Insert prepopulatedHtml Into Wizard Card
- **Goal:** Show pre-populated audit data in manual review wizard.
- **Files:** `areos/ui/guided_review.js`
- **Do:** In the `wizCard.innerHTML` template literal (~L301-334), insert `${prepopulatedHtml}` above the `<h3 class="gr-card-question">` line.
- **Boundary:** Do NOT change how `prepopulatedHtml` is built. Do NOT change card styling.
- **Checkpoint:** `test_guided_review_prepopulated_html_rendered`

### TQ-010: Inject AUDIT_PHASE_CRASHED Finding on Auditor Exceptions
- **Goal:** Surface auditor crashes to users instead of silently dropping checks.
- **Files:** `areos/auditors/audit_orchestrator.py`
- **Do:** Inside each `except Exception as e:` block in the orchestration loop (~L372-488), append:
  ```python
  findings.append({
      "code": "AUDIT_PHASE_CRASHED",
      "severity": "error",
      "description": f"Audit phase failed: {e}",
      "layer": current_layer_name
  })
  ```
- **Boundary:** Do NOT change the exception handling structure. Do NOT re-raise.
- **Checkpoint:** `test_auditor_crash_injects_finding`

### TQ-011: Add Response Size Limit to `safe_get`
- **Goal:** Prevent OOM from unbounded HTTP responses.
- **Decision:** D-QA-009
- **Files:** `areos/util/ssrf.py`
- **Do:** Change `requests.get(url, ...)` to use `stream=True` with chunked reading and 5MB cap.
- **Boundary:** Do NOT change the function signature. Do NOT change timeout values.
- **Checkpoint:** `test_safe_get_enforces_size_limit`

### TQ-012: Add `import urllib.parse` to authority_auditor.py
- **Goal:** Prevent NameError when Open PageRank API key is configured.
- **Files:** `areos/auditors/authority_auditor.py`
- **Do:** Add `import urllib.parse` at the top of the file alongside existing urllib imports.
- **Boundary:** None. Single-line fix.
- **Checkpoint:** `test_authority_auditor_urllib_import`

### TQ-013: Fix Schema Validator `@graph` and `mainEntity` Crashes
- **Goal:** Prevent TypeError/AttributeError on non-standard JSON-LD structures.
- **Decision:** D-QA-008
- **Files:** `areos/auditors/schema_validator.py`
- **Do:**
  1. `@graph` handling (~L303): Normalize dict to list, skip non-list/non-dict:
     ```python
     graph = block["@graph"]
     if isinstance(graph, dict): graph = [graph]
     if not isinstance(graph, list): continue
     ```
  2. `mainEntity` handling (~L255): Add `if not isinstance(question, dict): continue` before calling `validate_single`.
- **Boundary:** Do NOT change `validate_single` itself.
- **Checkpoint:** `test_schema_validator_graph_null_handling`, `test_schema_validator_string_in_list`

### TQ-014: Remap 8 Check Codes From Deprecated KT-041
- **Goal:** Stop serving stale remediation advice for content format findings.
- **Decision:** D-QA-011
- **Files:** `areos/kb/check_code_to_knowledge_map.json`
- **Do:** Update `backing_records` for `EXTRACTABILITY_LOW`, `EXTRACTABILITY_MEDIUM`, `EXTRACTABILITY_HIGH`, `ANSWER_NOT_NEAR_TOP`, `ANSWER_NOT_SELF_CONTAINED`, `ANSWER_NOT_FACTUALLY_SPECIFIC`, `NO_LIST_OR_TABLE`, `ANSWER_FORMAT_GOOD` to point to active KID(s) instead of deprecated `KT-041`.
- **Boundary:** Do NOT delete KT-041 from knowledge.jsonl. Do NOT change non-content-format mappings.
- **Checkpoint:** `test_check_codes_mapped_to_active_kids`

### Q3 Regression Checkpoint (10+ tests)
```
EXISTING (must still pass):
1. test_phase2_auditors — all 26 tests
2. test_phase4_enhancements — all 9 tests
3. test_multipage_auditor — all 7 tests
4. test_competitor_analyzer — all 8 tests

NEW (must pass after Q3):
5. test_auditor_crash_injects_finding — crashed phase appears in findings
6. test_auditor_crash_doesnt_abort_audit — remaining phases still run
7. test_safe_get_enforces_size_limit — 5MB+ responses rejected
8. test_safe_get_normal_response_works — sub-5MB responses still return correctly
9. test_authority_auditor_urllib_import — quote() works without NameError
10. test_schema_validator_graph_null — @graph:null handled gracefully
11. test_schema_validator_graph_single_dict — @graph:{} normalized to list
12. test_schema_validator_string_in_mainentity — string URLs skipped
13. test_check_codes_mapped_to_active_kids — no active code → deprecated KID
14. test_citation_sampler_exponential_backoff — 429 triggers backoff
```

---

## Phase Q4: Medium Priority Fixes

### TQ-015: Add 16 Missing ACTION_SNIPPETS
- **Decision:** D-QA-010
- **Files:** `areos/auditors/audit_orchestrator.py`
- **Do:** Add remediation text entries for all 16 missing codes to ACTION_SNIPPETS dict.
- **Checkpoint:** `test_all_deductions_have_snippets`

### TQ-016: Add UNIQUE Constraint to `manual_observations`
- **Decision:** D-QA-012
- **Files:** `areos/db/schema.sql`, `areos/api/routers/audit.py`
- **Do:** Add `UNIQUE(run_id, question_id)` to schema. Replace DELETE+INSERT with `ON CONFLICT DO UPDATE`.
- **Checkpoint:** `test_manual_observations_unique_constraint`

### TQ-017: Fix Pydantic `severity` Validation
- **Decision:** D-QA-014
- **Files:** `areos/api/routers/audit.py`
- **Do:** Change `severity: str` to `severity: Literal["error", "warning", "info"]`.
- **Checkpoint:** `test_audit_severity_pydantic_validation`

### TQ-018: Fix Content Format Auditor Zero-Handling
- **Decision:** D-QA-015
- **Files:** `areos/auditors/content_format_auditor.py`
- **Do:** Change `signals.get("list_item_count", 0)` to `signals.get("list_item_count")` with `is None` check.
- **Checkpoint:** `test_content_format_auditor_zero_handling`

### TQ-019: Filter Deprecated Records in Router Lookups
- **Files:** `areos/kb/router.py`
- **Do:** Add `WHERE status NOT IN ('deprecated', 'archived')` to deterministic lookup queries.
- **Checkpoint:** `test_router_filters_deprecated_records`

### TQ-020: Add `defusedxml` for Sitemap XML Parsing
- **Decision:** D-QA-013
- **Files:** `requirements.txt`, `areos/auditors/sitemap_auditor.py`
- **Do:** Add `defusedxml` to requirements. Replace `xml.etree.ElementTree.fromstring` with `defusedxml.ElementTree.fromstring`. Add URL count limit of 50,000.
- **Checkpoint:** `test_sitemap_xml_bomb_protection`

### TQ-021: Fix IP Rate Limiter Memory Leak
- **Files:** `areos/api/routers/audit.py`
- **Do:** After the timestamp filter cleanup, add: `if not _ip_buckets[ip]: del _ip_buckets[ip]`
- **Checkpoint:** `test_ip_rate_limiter_eviction`

### TQ-022: Add `rec.severity` Null Check in Export
- **Files:** `areos/ui/studio.js`
- **Do:** Change `rec.severity.toUpperCase()` to `(rec.severity || 'info').toUpperCase()`.
- **Also fix:** `sc.authority_metrics.authority_score` → `(sc.authority_metrics || {}).authority_score`
- **Checkpoint:** `test_export_handles_missing_severity`

### Q4 Regression Checkpoint (8+ tests)
```
EXISTING (must still pass):
1. test_phase3_kb_scoring — all 13 tests
2. test_track_b_manual_review — all 21 tests

NEW (must pass after Q4):
3. test_all_deductions_have_snippets — every LAYER_DEDUCTION code has ACTION_SNIPPET
4. test_manual_observations_unique_constraint — duplicate inserts don't create dupes
5. test_audit_severity_pydantic_validation — invalid severity rejected with 422
6. test_content_format_auditor_zero_lists — explicit 0 is not re-parsed
7. test_router_filters_deprecated_records — deprecated KIDs excluded from lookups
8. test_sitemap_xml_bomb_protection — billion-laughs XML is rejected
9. test_ip_rate_limiter_eviction — stale IPs cleaned from memory
10. test_export_handles_missing_severity — null severity doesn't crash export
```

---

## Phase Q5: Cleanup

### TQ-023: Extract Shared HTML Stripping Utility
- **Files:** `areos/util/html_utils.py` (NEW), `cloaking_detector.py`, `multipage_auditor.py`, `rendering_auditor.py`
- **Do:** Extract common `_strip_html` / `_extract_page_text` into shared utility. Import in all three auditors.
- **Checkpoint:** `test_html_stripping_utility_shared`

### TQ-024: Replace Magic Numbers With Named Constants
- **Files:** `multipage_auditor.py`, `media_blindness_auditor.py`
- **Do:** Extract `THIN_CONTENT_WORD_THRESHOLD = 30`, `DUPLICATE_RATIO_THRESHOLD = 0.85`, `MAX_IFRAME_COUNT = 3`, `MAX_MISSING_ALT_RATIO = 0.30`, `MIN_BODY_WORD_COUNT = 50`.
- **Checkpoint:** `test_multipage_auditor_constants`, `test_media_blindness_constants`

### TQ-025: Remove Unused Imports and Dead Code
- **Files:** `sitemap_auditor.py`, `multipage_auditor.py`, `competitor_analyzer.py`, `ingest_claims.py`
- **Do:** Remove unused `validate_domain_ssrf` imports. Remove duplicate `conn.commit()` in ingest_claims.
- **Checkpoint:** Existing tests still pass.

### TQ-026: Remove `console.log` in api.js
- **Files:** `areos/ui/api.js`
- **Do:** Remove `console.log("OUTGOING HEADERS:", headers);` at ~L78.
- **Checkpoint:** `test_api_js_no_console_logs`

### TQ-027: Fix `dom.js` Double-Loading
- **Files:** `areos/ui/index.html`, `areos/ui/claims_browser.html`
- **Do:** Remove the duplicate `<script src="dom.js">` tag in each file.
- **Checkpoint:** Visual verification that pages load correctly.

### TQ-028: Fix nav.js Route ID Mismatch
- **Files:** `areos/ui/claims_browser.html`
- **Do:** Change `renderNav('claims')` to `renderNav('knowledge')`.
- **Checkpoint:** Visual verification that nav highlights correctly.

### Q5 Regression Checkpoint (8+ tests)
```
EXISTING (must still pass):
1. ALL 184+ tests from previous phases — full suite green
2. test_multipage_auditor — all 7 tests (regression after constant extraction)
3. test_phase2_auditors — all 26 tests (regression after import cleanup)

NEW (must pass after Q5):
4. test_html_stripping_utility_shared — shared util produces identical output
5. test_multipage_auditor_constants — thresholds unchanged after extraction
6. test_media_blindness_constants — thresholds unchanged after extraction
7. test_sitemap_xml_bomb_protection — defusedxml rejects malicious XML
8. test_robots_checker_fragment_preservation — URLs with # fragments preserved
```

---

## Final Gate Verification Record

- **Command:** `python -m pytest tests/ -v`
- **Result:** **PASSED — 224 / 224 tests passing (100% Green, 0 failures, 0 regressions)**
- **Audit Phases Verified:**
  - Phase Q1: 100% COMPLETE (10/10 dedicated tests pass)
  - Phase Q2: 100% COMPLETE (8/8 dedicated tests pass)
  - Phase Q3: 100% COMPLETE (10/10 dedicated tests pass)
  - Phase Q4: 100% COMPLETE (8/8 dedicated tests pass)
  - Phase Q5: 100% COMPLETE (4/4 dedicated tests pass)
  - Legacy Suites: 100% COMPLETE (184/184 regression tests pass)
- **Status:** All 28 tasks `TQ-001` through `TQ-028` are fully implemented, verified, and locked.
