# QA REMEDIATION — DECISIONS REGISTER

> **Session:** QA Remediation Pass (1 September 2026)
> **Principle:** Every low-level decision is pre-made so the implementing agent cannot deviate.
> **Source:** 5 exhaustive auditor subagents × 3 rounds, verified by Fix Verification Auditor.

---

## D-QA-001: `window.AreosContext.auditResult` Assignment (QA-C01)
- **Decision:** Add the assignment in `studio.js` AFTER the audit orchestration fetch completes.
- **Exact code:** `window.AreosContext = window.AreosContext || {}; window.AreosContext.auditResult = data;`
- **Why not just assign directly?** Fix Verification Auditor confirmed that `window.AreosContext` may be undefined at that point. The `|| {}` guard is MANDATORY.
- **Location:** Inside the `.then()` or after `await` of the `/api/v1/audit/orchestrate` fetch call, immediately after `currentAuditData = data;`.
- **Do NOT:** Create a new function. Do NOT move existing code. Just add 2 lines.

## D-QA-002: `enrichCodeSnippet` Resolution (QA-C02)
- **Decision:** REMOVE the call entirely and inline the snippet lookup.
- **Why not define it?** The function was never implemented, and the export logic already has `rec.check_code` available. The ACTION_SNIPPETS lookup should happen server-side (already does in orchestrator).
- **Exact change:** Replace `const code = enrichCodeSnippet(rec, domain);` and the subsequent markdown block with: `const code = rec.remediation_snippet || '';` and conditionally append it only if non-empty.
- **Do NOT:** Create a new global function. Do NOT import from another file.

## D-QA-003: `manual_verdicts_context` NameError (QA-C03)
- **Decision:** Define `merged_human_count = 0` BEFORE the conditional branches. Update it in each branch.
- **Why not rename to `observation_rows`?** Fix Verification Auditor confirmed: `verdict_rows` is only defined inside the `else` block. Using `observation_rows` reports 0 when legacy path runs. Neither works as a direct replacement.
- **Exact pattern:**
  ```python
  merged_human_count = 0
  if observation_rows:
      # ... existing new-system logic ...
      merged_human_count = len(observation_rows)
  else:
      # ... existing legacy logic ...
      merged_human_count = len(verdict_rows)
  ```
  Then replace `len(manual_verdicts_context)` at L786 with `merged_human_count`.
- **Do NOT:** Rename the variable. Do NOT restructure the conditional.

## D-QA-004: Schema Migration `claims` TABLE/VIEW Conflict (QA-C04)
- **Decision:** Fix in `migrate_audit_tables.py`, NOT in `schema.sql` or `build_kb.py`.
- **Why?** Changing schema.sql breaks fresh installs. Changing build_kb.py breaks the V2 KB architecture.
- **Exact fix in `migrate_audit_tables.py`:** Before running `schema.sql`, check if `claims` is a view:
  ```python
  row = conn.execute("SELECT type FROM sqlite_master WHERE name='claims'").fetchone()
  if row and row[0] == 'view':
      # Skip CREATE TABLE claims — V2 KB view already exists
      # Run schema.sql but filter out the claims table creation
      filtered = [stmt for stmt in schema_sql.split(';') 
                  if 'CREATE TABLE' not in stmt or 'claims' not in stmt]
      conn.executescript(';'.join(filtered))
  else:
      conn.executescript(schema_sql)
  ```
- **Also fix `kb_meta` INSERT:** Change to: `conn.execute("INSERT OR IGNORE INTO kb_meta (key, value) VALUES ('schema_version', '1')")` when V2 KB is detected (key-value schema), OR keep the old `INSERT INTO kb_meta (id) VALUES (1)` when legacy schema is present.
- **Do NOT:** Delete or rename `claims` from schema.sql. Do NOT change build_kb.py's view logic.

## D-QA-005: `audit_findings` Non-Existent Table (QA-C05)
- **Decision:** Replace `SELECT * FROM audit_findings WHERE run_id = ?` with extraction from `audit_runs.automated_findings` JSON column.
- **Exact pattern:**
  ```python
  row = conn.execute("SELECT automated_findings FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
  findings = json.loads(row[0]) if row and row[0] else []
  ```
- **Do NOT:** Create a new `audit_findings` table. The JSON column IS the canonical store.

## D-QA-006: `ROUTES` Array in nav.js (QA-C06)
- **Decision:** Define `ROUTES` at the top of `nav.js` by extracting from the existing nav config.
- **Pattern:** `const ROUTES = [{label: 'Studio', path: '/studio'}, {label: 'Knowledge Explorer', path: '/knowledge'}, ...]`
- **Source the routes from:** The existing `renderNav()` configuration that already defines page labels and paths.
- **Do NOT:** Hardcode URLs that don't match actual HTML files.

## D-QA-007: `build_kb.py` Duplicate KID Handling (QA-C07)
- **Decision:** Use `INSERT OR REPLACE INTO knowledge` instead of plain `INSERT INTO knowledge`.
- **Also add:** `logger.warning(f"Duplicate KID {kid} replaced")` to track occurrences.
- **Do NOT:** Use `INSERT OR IGNORE` (that silently drops updates). `REPLACE` ensures latest data wins.

## D-QA-008: `@graph` Non-List Handling (QA-H07)
- **Decision:** Normalize to list, don't just skip.
- **Why?** Fix Verification Auditor confirmed `@graph` can legitimately be a single dict (valid schema.org).
- **Exact code:**
  ```python
  if "@graph" in block:
      graph = block["@graph"]
      if isinstance(graph, dict):
          graph = [graph]
      if not isinstance(graph, list):
          continue
      for sub_idx, sub_block in enumerate(graph):
          ...
  ```
- **Do NOT:** Simply add `isinstance(block["@graph"], list)` as the only guard — that drops valid single-object graphs.

## D-QA-009: `safe_get` Response Size Limit (QA-H04)
- **Decision:** Add `stream=True` and chunked reading with 5MB cap.
- **Exact pattern:**
  ```python
  resp = requests.get(url, ..., stream=True)
  content = b""
  for chunk in resp.iter_content(chunk_size=8192):
      content += chunk
      if len(content) > 5 * 1024 * 1024:
          resp.close()
          raise ValueError("Response exceeds 5MB limit")
  ```
- **Also update:** Return `content.decode('utf-8', errors='replace')` instead of `resp.text`.
- **Do NOT:** Change the function signature or return type.

## D-QA-010: ACTION_SNIPPETS for 16 Missing Check Codes (QA-M-SNIPPETS)
- **Decision:** Add remediation text for each code. Use the existing guidance records from `knowledge.jsonl` as source material.
- **Codes to add:** `CITATION_NOT_OBSERVED`, `CRAWLER_PARTIAL`, `EXTRACTABILITY_LOW`, `EXTRACTABILITY_MEDIUM`, `EXTRACTABILITY_NONE`, `GOOGLE_EXTENDED_MISSING`, `GPTBOT_MISSING`, `INVALID_CRAWL_DELAY`, `LLMS_TXT_EMPTY_CONTENT`, `LLMS_TXT_MISSING_SECTION`, `LLMS_TXT_NO_LINKS`, `MISSING_RECOMMENDED_FIELD`, `MISSING_TYPE`, `NOSNIPPET_BLOCKING_AI`, `UNKNOWN_FIELD`, `UNKNOWN_SCHEMA_TYPE`
- **Do NOT:** Add snippets for informational/positive codes (e.g., `CRAWLER_ALLOWED`, `ANSWER_FORMAT_GOOD`).

## D-QA-011: Deprecated KID Remapping (QA-H11)
- **Decision:** Update `check_code_to_knowledge_map.json` to point the 8 content-format codes from deprecated `KT-041` to an active replacement.
- **Target KID:** Find the active KID covering content format guidance (likely `KT-033` or create `KT-250` if none exists).
- **Codes to remap:** `EXTRACTABILITY_LOW`, `EXTRACTABILITY_MEDIUM`, `EXTRACTABILITY_HIGH`, `ANSWER_NOT_NEAR_TOP`, `ANSWER_NOT_SELF_CONTAINED`, `ANSWER_NOT_FACTUALLY_SPECIFIC`, `NO_LIST_OR_TABLE`, `ANSWER_FORMAT_GOOD`
- **Do NOT:** Delete the deprecated KT-041 record from knowledge.jsonl.

## D-QA-012: `manual_observations` UNIQUE Constraint (QA-M08)
- **Decision:** Add `UNIQUE(run_id, question_id)` to the CREATE TABLE in `schema.sql`. Use `INSERT ... ON CONFLICT(run_id, question_id) DO UPDATE SET ...` in `audit.py`.
- **Remove:** The inline `CREATE TABLE IF NOT EXISTS` check from the request handler — table should only be created by `schema.sql`.
- **Remove:** The `DELETE` + `INSERT` pattern — replaced by `ON CONFLICT DO UPDATE`.

## D-QA-013: `defusedxml` for Sitemap Parsing (QA-M15)
- **Decision:** Add `defusedxml` to `requirements.txt`. Replace `xml.etree.ElementTree.fromstring` with `defusedxml.ElementTree.fromstring` in `sitemap_auditor.py`.
- **Also add:** URL count limit of 50,000 in `_parse_sitemap_xml`.
- **Do NOT:** Change the XML parsing logic itself — only swap the parser.

## D-QA-014: Pydantic `severity` Literal (QA-M09)
- **Decision:** Change `severity: str` to `severity: Literal["error", "warning", "info"]` in `ObservationPayload`.
- **Add import:** `from typing import Literal`
- **Do NOT:** Change the DB column type. The constraint is API-layer only.

## D-QA-015: Content Format Auditor Zero-Handling (QA-M11)
- **Decision:** Change `signals.get("list_item_count", 0)` to `signals.get("list_item_count")` and compare with `is None`.
- **Pattern:** `list_item_count = signals.get("list_item_count"); if list_item_count is None and html:`
- **Same fix for:** `table_count`.
