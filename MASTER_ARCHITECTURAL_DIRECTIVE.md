# MASTER ARCHITECTURAL DIRECTIVE & REMEDIATION PLAN
**System:** Citeable AEOGEO Autonomous Audit & Knowledge Platform
**Persona:** Elena, Chief Technology Officer & Principal Systems Architect — Master Convergence Pass
**Operating Directive:** Strict Karpathy Principles (think before coding, simplicity first, surgical changes, goal-driven execution with deterministic tests)
**Inputs converged:** `AUDIT_PROMPT_INSTRUCTIONS.md`, `REPORT_1` (UI/UX), `REPORT_2` (Code Sanity & Dependency Graph), `REPORT_3` (Deployment & CI/CD), `REPORT_4` (KB/RAG Semantic Parity), `REPORT_5` (API Security & Concurrency), and the full `areos/` source tree + `areos.db` shipped in this package.
**Companion documents:** `decisions.md` (12 ADRs), `tasks.md` (21 atomic tasks)

---

## 1. Executive Synthesis & Reality Verification Matrix

### 1.1 Verification methodology (this pass)
Per the Forensic Grounding & Reality Verification Gate mandate, every P0/P1 claim and a representative sample of P2/P3 claims across all 5 reports were independently re-verified against the actual delivered source tree before being accepted into this directive — not re-summarized from the reports' prose alone. Concretely, this pass:
- Extracted and installed the full `areos/` package (`pip install -r requirements.txt`) in a clean environment.
- **Ran the full test suite live:** `pytest -q` → **332 passed, 2 failed**, 3.70s (see §4 for the two failures and why neither is a code regression).
- **Ran the semantic-parity gate live:** `python scripts/verify_kb_semantic_parity.py` → **PASS, 77/77 check codes synchronized**, exit 0.
- Directly grepped/read source for every finding cited below as "Verified" — file paths, line numbers, and function bodies were opened and inspected, not assumed from report prose.
- Confirmed the full directory tree of the delivered package against each report's stated scope (this is where the one scope correction below originates).

Findings not individually re-executed (e.g., REPORT_3's `black`/`flake8` counts, REPORT_5's live chunked-upload reproduction) are accepted on **report authority** — each of those reports documented a transparent, reproducible methodology, and every claim from the same reports that *was* independently re-checked in this pass turned out to be accurate on direct inspection (9 for 9 across all five reports, detailed below). This is stated plainly rather than silently assumed, consistent with the mandate to reject hallucination but not to manufacture false precision about what was and wasn't re-executed in this specific pass.

### 1.2 Per-report verification status

| Report | Domain | Top finding | Verification status |
|---|---|---|---|
| REPORT_1 | UI/UX | §2.1 — hamburger nav unreachable on 4/9 pages below 768px | **Verified.** Direct grep confirms `byok.html`, `case_study.html`, `docs.html`, `index.html` have no `class="topbar"`; `nav.js:281-282` gates hamburger injection entirely on `topbar`'s presence. |
| REPORT_2 | Code Sanity | R-01 — `kb_meta` schema collision, `build_kb.py` vs `migrate_audit_tables.py` | **Verified.** Confirmed both independent `CREATE TABLE kb_meta` definitions, the `DROP TABLE IF EXISTS kb_meta;` in `build_kb.py`, and the mismatched `key`/`value` version-read query against the actual `INSERT INTO kb_meta (id, kb_version, ...)` column shape. **Scope note REJECTED as applied to this package** — see §1.3. |
| REPORT_3 | Deployment/CI/CD | No CI/CD pipeline exists; 334 tests never run automatically | **Verified.** Confirmed no `.github/`, `.gitlab-ci.yml`, or pre-commit config; confirmed 38 test files / 334 test functions by direct count, matching this pass's own `pytest` run exactly. |
| REPORT_4 | KB/RAG | 8 deprecated check codes still scored/deducted/remediated live, contradicting the KB's own governance registry | **Verified.** Confirmed all 8 codes marked `⛔ DEPRECATED` in `CHECK_CODE_REGISTRY.md` and confirmed all 8 still appear as live emissions in `robots_checker.py`/`authority_auditor.py` and as live deductions in `scoring.py:LAYER_DEDUCTIONS`. Confirmed the parity gate passes 77/77 today (re-run directly) and structurally cannot catch this class of defect, exactly as reported. |
| REPORT_5 | Security/Concurrency | Critical, unauthenticated SSRF via BYOK `custom_base`/`azure_base` in the live LLM waterfall | **Verified.** Confirmed zero `ssrf` import anywhere in `areos/llm/`; confirmed `_azure_call`/`_custom_call` reach raw `_requests.post()`; confirmed `azure_base`/`custom_base` are sourced directly and unvalidated from caller-supplied `client_keys`; confirmed `/audit/orchestrate` and `/audit/runs/{id}/synthesize` carry no `verify_admin` dependency. Also independently verified the iframe `sandbox="allow-same-origin allow-scripts"` finding at `app.js:334` and the middleware registration order underlying the chunked-upload finding. |

**Net result: 9 for 9 direct spot-checks across all five reports came back Verified True**, including every P0-severity claim in the corpus. No finding surfaced in any of the 5 reports was rejected as hallucinated or unreproducible during this pass.

### 1.3 One scope correction (not a rejection of any finding)

REPORT_2's own scope note states that `areos/ui/`, `areos/llm/`, `areos/services/`, `areos/util/`, and `tests/` were **absent** from the package it audited. Directly verified against the package delivered for **this** convergence pass: **all five directories are present** (`ui/`: 33 files; `llm/`: 2 files; `services/`: 8 files; `util/`: 5 files; `tests/`: 38 files / 334 test functions, all executed directly in §4 below). This is not an error in REPORT_2 — it is independently corroborated by the codebase's own `CHANGELOG.md`, which records, in an entry predating REPORT_2's pass, that "a `tests/` directory the README describes... isn't present in this export." REPORT_2 was accurately describing an earlier, narrower snapshot than the superset package delivered here. **Correction applied:** REPORT_2's specific in-scope findings (everything inside `auditors/`, `api/`, `db/`, `kb/`, `cli/`) are unaffected and remain fully valid; its architectural dependency matrix framing those five directories as "external" is superseded — see DEC-12 for the full resolution and the related, already-self-documented README env-var drift (`Citeable_API_TOKEN` vs. the actual `AREOS_API_TOKEN`).

### 1.4 Consolidated & de-duplicated finding count

Across the 5 reports, one finding was independently caught twice under different names and is counted **once** in `tasks.md`: the duplicate `"AUDIT_PHASE_CRASHED": ("access", 5)` entry in `scoring.py:LAYER_DEDUCTIONS` (REPORT_2's R-08 and REPORT_4's Finding 3 both cite the identical line pair). No other cross-report duplication was found. Final classification, using this master directive's own P0–P3 rubric (Blocker = security/data-corruption/runtime-crash; High = semantic-parity/accessibility/concurrency; Medium = visual/copy/CI-gate gaps; Polish = refactor/cleanup) rather than each individual report's own internal severity labels:

| Priority | Count | Examples |
|---|---|---|
| **P0 Blocker** | 2 | SSRF via BYOK custom/Azure endpoints (DEC-03); `kb_meta` schema collision / data-corruption pathway (DEC-08) |
| **P1 High** | 7 | Mobile-nav accessibility lockout (DEC-01) *reclassified down from each source report's own "P0" label — see note below*; deprecated check-code semantic-honesty gap (DEC-07); synchronous long-running audit endpoint (DEC-06); chunked-upload middleware ordering (DEC-05); BYOK verify-oracle sign-off (DEC-04); no CI/CD pipeline (DEC-09); Docker DB seeding contradiction + missing backup/DR (DEC-10) |
| **P2 Medium** | 5 | Batched UI visual-polish defects (DEC-02); test-infra network-dependency (new, this pass); `conftest.py` fast-follow; R-16 shadowed snippet values; raw-`urllib` architectural inconsistency |
| **P3 Polish** | 6 | Dead code deletions; duplicate imports/statements; complexity refactors C-01–C-06 |
| **Info / doc-only** | 2 | README env-var correction; scope-note governance record |

**Reclassification note:** REPORT_1 labels its mobile-nav finding "P0" using its own screen-level rubric ("Responsiveness: D"). Under *this* master directive's stricter, security/corruption/crash-anchored P0 definition, it is classified **P1 High** (broken accessibility) instead — the underlying finding and its verified severity are unchanged; only the label mapping is corrected for consistency with how P0 is used everywhere else in this document. This is exactly the kind of competing-severity-scheme reconciliation the convergence pass exists to perform.

---

## 2. Architecture Decision Records

See **`decisions.md`** for the full text of DEC-01 through DEC-12, covering Frontend (DEC-01, DEC-02), Backend/Security (DEC-03, DEC-04), Concurrency/Protocol (DEC-05, DEC-06), KB/RAG (DEC-07, DEC-08), DevOps (DEC-09, DEC-10), Code Sanity (DEC-11), and Governance (DEC-12). Each ADR states its Context & Problem (with re-verified file/line evidence), Decision Taken, Trade-offs & Alternatives Considered, Systemic Consequences, and Regression Gate.

---

## 3. Master Atomic Implementation Task Registry

See **`tasks.md`** for the full table of 21 atomic tasks (TASK-01 through TASK-19, plus TASK-09b/TASK-10b), each with Target Files, Dedicated QA Test File, and Regression Verification Checkpoint & Acceptance Criteria. Summary:

- **2 P0 Blocker tasks** (TASK-03: SSRF fix; TASK-08: `kb_meta` schema fix) — **must land before production sign-off**, per §5 below.
- **7 P1 High tasks**, **5 P2 Medium tasks**, **6 P3 Polish tasks**, **2 Info/doc-only tasks**.

---

## 4. Master Test Suite & Semantic Parity Verification (live execution log, this pass)

### 4.1 Full test suite
```
$ export AREOS_API_TOKEN=<test-value>   # not required by most files — 28/38 self-set it
$ python -m pytest -q
........................................................................ [ 21%]
................F....................................................... [ 43%]
........................................................................ [ 64%]
..............................F......................................... [ 86%]
..............................................                           [100%]
2 failed, 332 passed, 3 warnings in 3.70s
```

**Both failures are environment-dependent, not application regressions:**

1. `tests/test_phase1_fetch.py::test_fetch_page_failure_returns_empty` — expects fetching a nonexistent domain to return the original URL unchanged. In this sandbox, the network egress layer resolves *any* disallowed domain to a fallback proxy IP rather than raising a DNS failure, so the function under test correctly follows a "resolved" address that doesn't exist in a normal internet-connected environment. This is a property of this execution sandbox's egress proxy, not of `_fetch_page`'s logic.
2. `tests/test_qa_phase_q3.py::test_auditor_crash_injects_finding` — the freshness-auditor crash-injection path is gated behind `if page_html:` (`audit_orchestrator.py:431`), and `page_html` here comes from a **real** `_fetch_page(clean_domain, page_url)` call against `"example.com"` (line 345) — not from the test's `sample_content` parameter, which only feeds a *different* downstream `eval_text` computation (line 364). In a network-restricted sandbox where `example.com` isn't reachable, `page_html` is empty, the gate is skipped, and the patched crash never fires.

Both are logged as **TASK-19** (new finding, this pass): recommend mocking `_fetch_page`/DNS resolution in both tests so the suite is fully hermetic regardless of the CI runner's network egress policy — directly relevant to TASK-09's CI rollout, since a CI runner's network rules could produce the same nondeterminism REPORT_3 already flagged as a general test-isolation risk (§3.2b of REPORT_3, re: `AREOS_TEST_DB`).

**Test count reconciliation:** 334 total test functions (332 + 2) matches REPORT_3's independently-stated count (334 tests, 38 files) exactly — direct confirmation that this pass's live run and REPORT_3's audit are describing the same test corpus.

### 4.2 Semantic parity gate
```
$ python scripts/verify_kb_semantic_parity.py
[PASS] Semantic Parity Gate PASSED: 77 check codes fully synchronized across KB, scoring, and remediation snippets.
```
Confirms REPORT_4's stated baseline (77/77 codes present and synchronized) exactly. As detailed in DEC-07/TASK-07, this gate's **current** scope (existence-only, not status-aware) is precisely why it cannot catch the 8-deprecated-code defect — the gate is correctly reported as passing today, and passing today is not in tension with the defect existing; they are orthogonal facts, both true simultaneously, exactly as REPORT_4 characterizes them.

### 4.3 What "100% regression convergence" means for this release
Per the mission's stated sign-off bar ("Confirm full test suite convergence across all 36 test modules... Confirm 100% check code semantic parity across all 77 codes"): the **77/77 check-code parity bar is met today**, confirmed live. The **test-suite convergence bar is not yet fully clean** in the strict sense of "0 unexplained failures" — 2 of 334 fail in this specific sandboxed execution environment for reasons fully explained and attributed to environment/network conditions rather than application logic in §4.1 above, and TASK-19 exists specifically to close that gap by making both tests hermetic. This is stated directly rather than rounded up to a false "100% green," consistent with the Reality Verification Gate's zero-hallucination mandate — a sign-off certificate that claimed a clean 334/334 without this caveat would itself be a fabrication this document is charged with rejecting.

---

## 5. Official CTO Production Release Sign-Off Certificate

**System:** Citeable AEOGEO Autonomous Audit & Knowledge Platform
**Assessment date:** This convergence pass, cross-referencing 5 domain audits against the delivered source tree and a live test/parity-gate execution.
**Signed:** Elena, Chief Technology Officer & Principal Systems Architect

### Determination: **CONDITIONAL SIGN-OFF — NOT YET CLEARED FOR PRODUCTION**

Release is **withheld pending TASK-03 and TASK-08** (both P0 Blocker, both independently verified against live source in this pass):

1. **TASK-03 — Unauthenticated SSRF via BYOK `custom_base`/`azure_base`.** An anonymous, unauthenticated caller can direct the production server to issue arbitrary outbound POST requests against internal/private network ranges (including cloud metadata endpoints) through `/api/v1/audit/orchestrate`, with no admin token required. This is a live, exploitable, unauthenticated vulnerability in the shipped code today, not a theoretical risk. **This alone is sufficient grounds to withhold sign-off** regardless of any other finding's status.
2. **TASK-08 — `kb_meta` schema collision causing silent, permanent version-tracking corruption on every KB rebuild**, plus a live pathway for a future edit to either competing schema definition to diverge further with no test currently guarding against it.

**Everything else in this directive — the 7 P1 High items, 5 P2 Medium items, and 6 P3 Polish items — does not block this determination** and may ship on a normal remediation cadence per `tasks.md`'s priority ordering, **with two exceptions called out explicitly rather than silently deferred:**
- **TASK-07** (deprecated check-code suppression) is flagged as release-blocking **specifically because the mission's own stated sign-off criterion is "100% check code semantic parity across all 77 codes,"** and while the *existence*-parity bar is met (77/77, confirmed live), the *semantic-honesty* parity the platform's own governance registry demands is not — 8 codes are simultaneously "present and synchronized" and "actively contradicting the platform's own declared research." Whether this blocks release is ultimately a product-policy call, not a purely technical one; it is surfaced here explicitly rather than resolved unilaterally.
- **DEC-04** (BYOK verify-oracle) requires an explicit product/security sign-off decision before this certificate can be considered complete — the code behaves exactly as designed, but "as designed" has not yet received a recorded risk-acceptance decision, which this directive cannot manufacture on its own authority.

### Conditions for full, unconditional sign-off:
1. TASK-03 and TASK-08 merged, with their respective new adversarial/integrity tests passing.
2. TASK-07 merged, or an explicit, recorded product decision that partial semantic-parity (existence-only) satisfies the release bar for this cycle.
3. DEC-04's sign-off decision recorded (accept-as-is or hardened — either resolves this condition).
4. Full `pytest` suite green including TASK-19's hermeticity fixes, run inside the CI pipeline established by TASK-09 (not just locally) — the pipeline's own first green run against `main` is the actual acceptance evidence for this condition, not a local re-run.
5. `python scripts/verify_kb_semantic_parity.py` — updated per TASK-07 to check `status`, not just existence — passing at 77/77 with the deprecated-status check active.

### What this pass explicitly did NOT do (scope boundary, stated per the Reality Verification Gate's own honesty requirement):
No code in the shipped package was modified during this convergence pass. This document is a **plan**, not a changelog — `tasks.md`'s "Status: Open" on every row reflects that accurately. REPORT_5's own independently-verified live patch-and-rerun (for the chunked-upload middleware ordering fix) is the one exception where a fix was actually applied and re-tested by a source report rather than by this pass, and is cited as such rather than re-claimed as this pass's own work.

---
*End of Master Architectural Directive. See `decisions.md` and `tasks.md` for full supporting detail.*
