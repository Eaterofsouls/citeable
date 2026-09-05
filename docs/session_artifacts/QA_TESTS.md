# QA REMEDIATION — EXHAUSTIVE TEST SPECIFICATION

> **Session:** QA Remediation Pass (1 September 2026)
> **Rule:** Every phase checkpoint has ≥8 tests. Tests cover happy paths, negative paths, edge cases, error paths, and regression.
> **Strategy:** Python backend tests use pytest + TestClient. Frontend logic tests use pytest with mock DOM patterns (no browser needed). KB tests use data-driven parametrization.

---

## Test File: `tests/test_qa_phase_q1.py`
**Phase Q1: Unblock Core Features**

### test_synthesize_endpoint_returns_200
- **What:** POST `/api/v1/audit/runs/{run_id}/synthesize` returns 200 after fixing NameError.
- **Assertions:** Status 200; response JSON contains `narrative` key with non-empty string.
- **Mocks:** TestClient, mock LLM provider returning canned response. Pre-insert audit_run with mock findings.
- **Type:** NEW. Tests QA-C03 fix.

### test_synthesize_endpoint_with_empty_observations
- **What:** Synthesis works when zero human observations exist (automated-only report).
- **Assertions:** Status 200; response contains automated findings section; `merged_human_count` is 0.
- **Mocks:** TestClient. Pre-insert audit_run WITHOUT observations or legacy verdicts.
- **Type:** NEW. Edge case for QA-C03.

### test_synthesize_endpoint_with_legacy_verdicts
- **What:** Synthesis correctly falls back to legacy `manual_verdicts` table.
- **Assertions:** Status 200; response contains legacy verdict context; `merged_human_count` equals verdict count.
- **Mocks:** TestClient. Pre-insert audit_run with legacy verdicts but NO observations.
- **Type:** NEW. Negative path for QA-C03 branch logic.

### test_synthesize_endpoint_malformed_run_id
- **What:** POST with non-existent `run_id` returns proper error.
- **Assertions:** Status 404; response contains error message.
- **Mocks:** TestClient with random UUID run_id.
- **Type:** NEW. Error path.

### test_full_report_endpoint_returns_findings
- **What:** GET `/full-report` returns findings from `audit_runs.automated_findings` JSON column.
- **Assertions:** Status 200; returned list matches inserted findings exactly.
- **Mocks:** TestClient. Pre-insert audit_run with known findings JSON.
- **Type:** NEW. Tests QA-C05 fix.

### test_full_report_endpoint_empty_run
- **What:** GET `/full-report` for run with no findings returns empty list.
- **Assertions:** Status 200; findings list is empty.
- **Mocks:** TestClient. Pre-insert audit_run with `automated_findings = '[]'`.
- **Type:** NEW. Edge case for QA-C05.

### test_full_report_endpoint_missing_run
- **What:** GET `/full-report` for non-existent run_id returns 404.
- **Assertions:** Status 404.
- **Mocks:** TestClient with random UUID.
- **Type:** NEW. Error path.

### test_enrichCodeSnippet_removed_no_crash
- **What:** The `enrichCodeSnippet` call no longer exists in studio.js (verified by grep).
- **Assertions:** `grep -r "enrichCodeSnippet" areos/ui/` returns zero matches.
- **Mocks:** None (file-level check).
- **Type:** NEW. Regression guard for QA-C02.

### test_routes_array_defined_in_nav
- **What:** `ROUTES` is defined in nav.js (verified by grep).
- **Assertions:** `grep "const ROUTES" areos/ui/nav.js` returns exactly 1 match.
- **Mocks:** None (file-level check).
- **Type:** NEW. Regression guard for QA-C06.

### test_audit_result_wired_to_context
- **What:** `window.AreosContext.auditResult` assignment exists in studio.js.
- **Assertions:** `grep "AreosContext.auditResult" areos/ui/studio.js` returns ≥1 match.
- **Mocks:** None (file-level check).
- **Type:** NEW. Regression guard for QA-C01.

### EXISTING REGRESSION (must still pass):
- test_phase0_fixes (20 tests)
- test_track_b_manual_review (21 tests)
- test_synthesis_enrichment (all tests)

---

## Test File: `tests/test_qa_phase_q2.py`
**Phase Q2: Fix Boot Crash**

### test_migrate_handles_claims_view
- **What:** `migrate()` succeeds when `claims` already exists as a VIEW.
- **Assertions:** No OperationalError. All other tables created. `claims` remains a VIEW.
- **Mocks:** In-memory SQLite. Pre-create `claims` as VIEW before running `migrate()`.
- **Type:** NEW. Tests QA-C04 fix.

### test_migrate_handles_fresh_db
- **What:** `migrate()` succeeds on a completely empty database.
- **Assertions:** All tables exist in `sqlite_master`. `claims` is a TABLE.
- **Mocks:** In-memory SQLite (empty).
- **Type:** NEW. Regression guard.

### test_migrate_idempotent_three_runs
- **What:** Running `migrate()` three times consecutively doesn't crash.
- **Assertions:** No errors on any run. Schema unchanged between runs 2 and 3.
- **Mocks:** In-memory SQLite.
- **Type:** NEW. Idempotency guard.

### test_build_kb_then_migrate_sequence
- **What:** Running `build_kb.build()` then `migrate()` doesn't crash (the exact production sequence).
- **Assertions:** No OperationalError. `claims` is a VIEW. Knowledge table populated.
- **Mocks:** In-memory SQLite + temp knowledge.jsonl with 3 records.
- **Type:** NEW. Integration test for QA-C04.

### test_build_kb_duplicate_kid_logged
- **What:** Duplicate KIDs in knowledge.jsonl are handled gracefully.
- **Assertions:** Build completes. Warning logged. Second record's data overwrites first.
- **Mocks:** Temp knowledge.jsonl with 2 entries sharing same KID but different content.
- **Type:** NEW. Tests QA-C07 fix.

### test_build_kb_malformed_jsonl_line
- **What:** A corrupted line in knowledge.jsonl doesn't abort the build.
- **Assertions:** Build completes. Valid records inserted. Malformed line skipped with warning.
- **Mocks:** Temp knowledge.jsonl with 1 valid + 1 `{corrupted` line.
- **Type:** NEW. Edge case.

### test_build_kb_empty_files
- **What:** Empty corpus files don't crash the build.
- **Assertions:** Build completes. Zero records inserted. No errors.
- **Mocks:** Temp empty knowledge.jsonl.
- **Type:** NEW. Edge case.

### test_kb_meta_v2_schema_insert
- **What:** `kb_meta` INSERT works with V2 key-value schema.
- **Assertions:** `SELECT value FROM kb_meta WHERE key='schema_version'` returns expected value.
- **Mocks:** In-memory SQLite with V2 schema.
- **Type:** NEW. Tests D-QA-004.

### EXISTING REGRESSION:
- test_rag (all tests)
- test_kb_parity (all tests)
- test_phase3_kb_scoring (13 tests)

---

## Test File: `tests/test_qa_phase_q3.py`
**Phase Q3: High Priority Fixes**

### test_auditor_crash_injects_finding
- **What:** A crashed auditor phase injects AUDIT_PHASE_CRASHED into findings.
- **Assertions:** Findings list contains item with `code='AUDIT_PHASE_CRASHED'` and `severity='error'`.
- **Mocks:** Monkeypatch one auditor function to `raise RuntimeError("test crash")`.
- **Type:** NEW. Tests QA-H03.

### test_auditor_crash_doesnt_abort_remaining_phases
- **What:** Remaining auditor phases still execute after one crashes.
- **Assertions:** Findings from non-crashed phases are present. Total finding count > 1.
- **Mocks:** Same as above; verify other phase findings exist.
- **Type:** NEW. Error path for QA-H03.

### test_safe_get_enforces_5mb_limit
- **What:** Response exceeding 5MB raises ValueError.
- **Assertions:** `ValueError("exceeds 5MB")` raised. Connection closed.
- **Mocks:** `responses` library returning 10MB of `b'x' * 10_000_000`.
- **Type:** NEW. Tests QA-H04.

### test_safe_get_normal_response_passes
- **What:** Sub-5MB response is returned correctly (regression guard).
- **Assertions:** Response text matches expected content. No errors.
- **Mocks:** `responses` library returning 1KB of valid HTML.
- **Type:** NEW. Regression for QA-H04.

### test_safe_get_empty_response
- **What:** Empty response (0 bytes) is handled correctly.
- **Assertions:** Returns empty string. No errors.
- **Mocks:** `responses` returning empty body.
- **Type:** NEW. Edge case.

### test_authority_auditor_urllib_import_exists
- **What:** `urllib.parse` is imported in authority_auditor.py.
- **Assertions:** `import urllib.parse` found via grep. `urllib.parse.quote("test.com")` doesn't raise NameError.
- **Type:** NEW. Tests QA-H06.

### test_schema_validator_graph_null
- **What:** JSON-LD with `"@graph": null` doesn't crash.
- **Assertions:** Validator returns findings without TypeError. May emit INVALID_STRUCTURE.
- **Mocks:** Feed blocks with `{"@graph": null}`.
- **Type:** NEW. Tests QA-H07.

### test_schema_validator_graph_single_dict
- **What:** JSON-LD with `"@graph": {"@type": "Person", "name": "Test"}` is normalized and validated.
- **Assertions:** Validator processes the single dict. No crash. Findings generated for the Person type.
- **Mocks:** Feed blocks with `{"@graph": {"@type": "Person"}}`.
- **Type:** NEW. Tests D-QA-008 normalization.

### test_schema_validator_string_in_mainentity
- **What:** FAQPage with `"mainEntity": ["https://example.com/q1", {"@type": "Question"}]` doesn't crash.
- **Assertions:** String URL skipped. Dict item validated. No AttributeError.
- **Mocks:** Feed FAQPage block with mixed mainEntity.
- **Type:** NEW. Tests QA-H08.

### test_check_codes_not_mapped_to_deprecated
- **What:** No active check code in LAYER_DEDUCTIONS maps to a deprecated KID.
- **Assertions:** For each code in LAYER_DEDUCTIONS, resolve via knowledge map → verify backing KIDs have `status != 'deprecated'`.
- **Mocks:** Load actual knowledge.jsonl and check_code_to_knowledge_map.json.
- **Type:** NEW. Data-driven test for QA-H11.

### EXISTING REGRESSION:
- test_phase2_auditors (26 tests)
- test_phase4_enhancements (9 tests)
- test_rendering_auditor (7 tests)

---

## Test File: `tests/test_qa_phase_q4.py`
**Phase Q4: Medium Priority**

### test_observation_severity_validation
- **What:** Invalid severity values rejected by Pydantic.
- **Assertions:** POST with `severity="critical"` returns 422. POST with `severity="error"` returns 200.
- **Mocks:** TestClient.
- **Type:** NEW. Tests QA-M09.

### test_manual_observations_upsert
- **What:** Second observation for same (run_id, question_id) updates, not duplicates.
- **Assertions:** After two inserts, SELECT returns exactly 1 row with latest data.
- **Mocks:** Direct SQLite with test schema.
- **Type:** NEW. Tests QA-M08.

### test_manual_observations_concurrent_upsert
- **What:** Two concurrent upserts don't deadlock.
- **Assertions:** Both complete without SQLITE_BUSY. Final state is consistent.
- **Mocks:** Threading with 2 concurrent inserts.
- **Type:** NEW. Concurrency test for QA-M08.

### test_ip_rate_limiter_cleans_stale_ips
- **What:** Stale IP entries are evicted from `_ip_buckets`.
- **Assertions:** After advancing time past window, dict key is deleted.
- **Mocks:** Freezegun or manual time manipulation.
- **Type:** NEW. Tests QA-M10.

### test_router_excludes_deprecated_records
- **What:** `resolve()` skips deprecated KIDs in deterministic lookups.
- **Assertions:** Deprecated KID not in returned resolution. Active KID returned instead.
- **Mocks:** Test DB with both active and deprecated records.
- **Type:** NEW. Tests QA-M12.

### test_content_format_explicit_zero_preserved
- **What:** `list_item_count=0` is not re-parsed from HTML.
- **Assertions:** Finding reflects count=0 exactly. HTML not re-scanned.
- **Mocks:** Signals dict with explicit `list_item_count: 0`.
- **Type:** NEW. Tests QA-M11.

### test_all_deductions_have_action_snippets
- **What:** Every code in LAYER_DEDUCTIONS has an ACTION_SNIPPETS entry.
- **Assertions:** `LAYER_DEDUCTIONS.keys() - ACTION_SNIPPETS.keys()` is empty (excluding DEFAULT).
- **Mocks:** Import both dicts directly.
- **Type:** NEW. Data integrity test for 16 missing snippets.

### test_defusedxml_rejects_xml_bomb
- **What:** Billion-laughs XML payload is rejected by defusedxml.
- **Assertions:** `defusedxml.common.EntitiesForbidden` raised (or equivalent).
- **Mocks:** Hand-crafted XML bomb string.
- **Type:** NEW. Tests QA-M15.

### test_sitemap_url_count_limit
- **What:** Sitemaps with >50,000 URLs are truncated.
- **Assertions:** Returned URL list has exactly 50,000 entries.
- **Mocks:** Generate mock XML with 60,000 `<loc>` elements.
- **Type:** NEW. Resource bound test.

### EXISTING REGRESSION:
- test_phase3_kb_scoring (13 tests)
- test_track_b_manual_review (21 tests)

---

## Test File: `tests/test_qa_phase_q5.py`
**Phase Q5: Cleanup**

### test_shared_html_stripping_matches_originals
- **What:** Extracted `areos.util.html_utils.strip_html()` produces identical output to original inline functions.
- **Assertions:** For 5 test HTML strings, output matches original `_extract_page_text` exactly.
- **Mocks:** Direct function comparison.
- **Type:** NEW. Regression guard for QA-L02.

### test_multipage_constants_unchanged
- **What:** Replacing magic numbers with named constants doesn't change behavior.
- **Assertions:** `THIN_CONTENT_WORD_THRESHOLD == 30`, `DUPLICATE_RATIO_THRESHOLD == 0.85`.
- **Mocks:** Import constants and verify values.
- **Type:** NEW. Regression guard for QA-L03.

### test_media_blindness_constants_unchanged
- **What:** Named constants match original magic numbers.
- **Assertions:** `MAX_IFRAME_COUNT == 3`, `MAX_MISSING_ALT_RATIO == 0.30`, `MIN_BODY_WORD_COUNT == 50`.
- **Mocks:** Import constants and verify values.
- **Type:** NEW. Regression guard for QA-L04.

### test_robots_checker_fragment_preserved
- **What:** Sitemap URLs with `#` fragments are not truncated by comment stripping.
- **Assertions:** `parse_robots_txt()` returns URL with fragment intact.
- **Mocks:** Mock robots.txt with `Sitemap: https://example.com/sitemap.xml#section`.
- **Type:** NEW. Tests QA-L05.

### test_robots_checker_inline_comment_stripped
- **What:** Inline comments after directives are still stripped.
- **Assertions:** `Sitemap: https://example.com/sitemap.xml # main` → URL without ` # main`.
- **Mocks:** Mock robots.txt.
- **Type:** NEW. Regression guard — comment stripping still works for actual comments.

### test_unused_imports_removed
- **What:** `validate_domain_ssrf` is no longer imported in sitemap/multipage/competitor files.
- **Assertions:** `grep "validate_domain_ssrf" areos/auditors/{sitemap,multipage,competitor}*.py` returns 0 matches.
- **Type:** NEW. Cleanup verification for QA-L01.

### test_duplicate_commit_removed
- **What:** `ingest_claims.py` no longer has consecutive `conn.commit()` calls.
- **Assertions:** Count of `conn.commit()` in file reduced by 1.
- **Type:** NEW. Cleanup verification for QA-L09.

### test_dom_js_loaded_once
- **What:** `dom.js` is loaded only once per HTML file.
- **Assertions:** `grep 'dom.js' areos/ui/index.html` returns exactly 1 match.
- **Type:** NEW. Cleanup verification for QA-L07.

### EXISTING REGRESSION:
- ALL previous tests (~224+) must pass
- Full suite: `python -m pytest tests/ -v`
