# Hostile Review of Implementation Plans

## 1. Missing `MANUAL_REMEDIATION_TEXT` Dictionary
- **Classification:** `WILL_BREAK`
- **Location:** `areos/auditors/synthesis_engine.py` (L382/389)
- **Doc claim vs code reality:** Forensic audit claims `MANUAL_REMEDIATION_TEXT` dictionary is missing, causing hard failures when manual findings are processed. I verified this in the code; the dictionary is indeed missing.
- **Production failure scenario:** If a manual finding triggers this code path, the synthesis engine will throw a `NameError` or `KeyError` and crash the pipeline.
- **The fix:** Define the `MANUAL_REMEDIATION_TEXT` dictionary mapping manual check codes to remediation text, or remove the reference and use the DB.

## 2. Exception Swallowing in Router
- **Classification:** `WILL_DEGRADE`
- **Location:** `areos/kb/router.py` (L157-160, L229-234)
- **Doc claim vs code reality:** Plan says exceptions are swallowed. Code uses `except Exception: pass` which masks JSON decoding and datetime parsing errors.
- **Production failure scenario:** Malformed data in the database will silently return empty or incorrect results, hiding critical bugs and degrading RAG retrieval quality.
- **The fix:** Log the exceptions and handle them explicitly. Fail fast where appropriate.

## 3. Legacy `check_code_mappings` Dependency
- **Classification:** `ASSUMPTION_WRONG` / `WILL_BREAK`
- **Location:** `areos/auditors/findings_to_claims.py` (L42-65, 130-144)
- **Doc claim vs code reality:** Implementation plan assumes we can delete legacy fallback paths. However, `findings_to_claims.py` heavily relies on `check_code_mappings` table as a fallback.
- **Production failure scenario:** If the legacy table is dropped or paths deleted without fully populating the V2 `kb_check_code_map`, findings will be UNMAPPED and report generation will be severely impacted.
- **The fix:** Ensure full migration of all mappings to `kb_check_code_map` before deleting legacy paths.

## 4. Citation Sampler Truncation
- **Classification:** `PERFORMANCE` / `WILL_DEGRADE`
- **Location:** `areos/auditors/citation_sampler.py`
- **Doc claim vs code reality:** Documentation says answers are truncated at 300 characters. Verified in code.
- **Production failure scenario:** If brand mentions occur after the 300-character mark in an AI response, they will be missed by the citation observation logic, resulting in false negatives.
- **The fix:** Increase the truncation limit or use a smarter extraction mechanism for brand mentions.

## 5. Render Free Tier Ephemeral Disk
- **Classification:** `ASSUMPTION_WRONG` / `WILL_BREAK`
- **Location:** `areos/db/connection.py`, `schema.sql`
- **Doc claim vs code reality:** The app relies on SQLite for state (findings, manual verdicts, syntheses).
- **Production failure scenario:** Render's free tier uses ephemeral disks. Upon every deployment or inactivity restart, the SQLite database will be wiped, destroying all audit history and knowledge base data.
- **The fix:** Use an attached disk (requires paid tier) or migrate to a managed PostgreSQL instance for production.

## 6. SSRF Vulnerability in URL Fetching
- **Classification:** `SECURITY`
- **Location:** Orchestrator / Competitor analyzer fetching URLs.
- **Doc claim vs code reality:** `audit_orchestrator.py` and potentially others fetch arbitrary URLs based on user input.
- **Production failure scenario:** Attackers could force the server to fetch internal network resources (AWS metadata, local ports), leading to an SSRF (Server-Side Request Forgery) breach.
- **The fix:** Implement strict URL validation, enforce scheme (http/https), block internal IP ranges, and set tight timeouts.

## 7. Race Condition: Manual Verdicts During Synthesis
- **Classification:** `ORDERING_VIOLATION`
- **Location:** `areos/ui/studio.js`, `areos/ui/guided_review.js`
- **Doc claim vs code reality:** `guided_review.js` allows submitting manual verdicts asynchronously. Synthesis pipeline is triggered after automated steps or when the wizard completes.
- **Production failure scenario:** If a user submits a manual verdict right as synthesis starts, or if they reload the page, the synthesis might run with incomplete data, or overwrite the manual findings.
- **The fix:** Ensure synthesis only runs when explicitly requested and all manual verdicts are locked, or re-run synthesis automatically when verdicts are updated.

## 8. XSS via Unescaped Notes/Claims
- **Classification:** `SECURITY`
- **Location:** `areos/ui/studio.js`, `areos/ui/guided_review.js`
- **Doc claim vs code reality:** While `escapeHtml` is used in some places, `renderUserText` in `studio.js` performs naive escaping and regex replacements which might be bypassed.
- **Production failure scenario:** Malicious findings or notes could inject scripts into the dashboard, stealing session tokens.
- **The fix:** Use a robust HTML sanitizer library (like DOMPurify) instead of custom regex replacements.
