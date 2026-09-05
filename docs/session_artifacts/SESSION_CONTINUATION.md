# CITEABLE SESSION CONTINUATION — Act 9 Complete

> **For any new agent picking up this work: READ THIS FIRST, then read `DECISIONS_AND_TASKS.md`.**

---

## What Was Done (Acts 1-9)

### Acts 1-5 (Sessions 1-12)
- Forensic audit of entire codebase → found 8 critical bugs
- AEOGEO Lifecycle Assessment → mapped 60 Study B claims to coverage gaps (~40% covered)
- Knowledge architecture built → 216 records, V2 JSON map, RAG router
- Implementation plan → 8-phase plan, approved by user
- Pre-implementation completeness audit → 3 gaps closed

### Acts 6-7 (Session 12)
- Manual review investigation → found 5 dead cards
- Manual review product design v2 → 11 expert-grade questions, 4 phases, Express/Full mode
- Pre-implementation completeness audit → verified readiness

### Act 8 (Session 13)
- 6 specialist agents (5 builders + 1 hostile reviewer) each read source code AND session docs
- Produced 6 implementation specs with exact function signatures, dataclasses, test code
- Hostile engineer found 8 production failure scenarios

### Act 9 (Session 13 continued — THIS SESSION)
- **Karpathy Three-File System created:**
  - `DECISIONS_AND_TASKS.md` (37KB) — 24 decisions (D-001→D-024), ~50 atomic tasks, hardcoded reference data, dependency DAG, phase gates with mandatory failure protocol, rollback plans, architectural risks with terminology bridge
  - `CHANGELOG.md` (8KB) — Pre-populated changelog template for implementation
  - `FORECAST.md` (10KB) — 8 deferred items, 10 future work items, regression risk register
- **Terminology collision discovered and resolved** — C0xx card IDs vs A1/B1/B2 question IDs vs KT-xxx vs KG-xxx. Three decisions (D-022/23/24) + bridging task T-B00 + risk section added.
- **Track B tasks expanded** from shallow 1-liners to exhaustive multi-step specifications covering all 10 gaps found during cross-check against manual_review_product_design.md
- **Coverage proof written** — every Study B claim traced to a task ID (automated) or manual review question (not-automatable)

---

## File Locations

### Primary Implementation Files (START HERE)
All at `D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE\docs\session_artifacts\`:

| File | What | Size |
|------|------|------|
| **`DECISIONS_AND_TASKS.md`** | **THE master file.** All decisions, all tasks, all reference data, phase gates, rollback plans, risks. | 37KB |
| `CHANGELOG.md` | Agent fills this in during implementation | 8KB |
| `FORECAST.md` | Deferred items, future work, discovery log | 10KB |

### Supporting Specs (Read if a task needs more detail)
| File | What |
|------|------|
| `phase0_deep_spec.md` | Exact current/replacement code for all Phase 0 bugs |
| `phases1_2_infrastructure_spec.md` | _fetch_page refactor, 7 module signatures, architecture gaps |
| `phases3_4_kb_scoring_spec.md` | All 38 KB entries, all LAYER_DEDUCTIONS, mathematical verification |
| `track_b_manual_review_spec.md` | SQL, API, UI, synthesis pipeline for Track B |
| `master_integration_spec.md` | DAG, phase gates, regression test files |
| `hostile_review.md` | 8 kill-list items |
| `manual_review_product_design.md` | The 11 expert questions with full structured outputs |
| `implementation_plan.md` | Original 8-phase plan (user-approved) |
| `aeogeo_lifecycle_assessment.md` | 60-claim coverage map (before vs after) |

### README
`docs/session_artifacts/README.md` — Updated through Act 9. Contains chronology and reading order.

---

## What To Do Next

### THE IMPLEMENTATION. Execute DECISIONS_AND_TASKS.md.

**Execution order:**
1. Phase 0 (T-001→T-014): Bug fixes. Gate: `pytest tests/test_phase0_fixes.py -v`
2. Phase 1 (T-101→T-104): Page fetch refactor. Gate: `pytest tests/test_phase1_fetch.py -v`
3. Phase 2 (T-201→T-208): 7 new auditor modules. Gate: individual module tests
4. Phase 3 (T-301→T-305): KB wiring + scoring. Gate: `pytest tests/test_kb_parity_extended.py -v`
5. Track B (T-B00→T-B07): Manual review redesign. Gate: `pytest tests/test_manual_review_api.py -v`
6. Phases 4-7 (T-401→T-701): Enhancement + optional modules
7. Final: `pytest tests/ -v` — ALL tests pass

**Phase Gate Failure Protocol:** If ANY gate fails, agent MUST deploy 3 subagents (Diagnostician, Fix Strategist, Regression Guardian). See DECISIONS_AND_TASKS.md Section D.

**Karpathy Principles:**
- Read the skill at `C:\Users\drc16\.gemini\config\skills\karpathy-principles\SKILL.md`
- Principle 1: Think before coding (every decision is explicit)
- Principle 2: Simplicity first (minimum code that solves the problem)
- Principle 3: Surgical changes (touch ONLY listed files, respect boundaries)
- Principle 4: Goal-driven execution (every task has a verifiable checkpoint)

---

## Critical Knowledge for New Agent

### Product Name
**Citeable** (not Siteable).

### Workspace
`D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE`

### Key Architecture Facts
- **Content format auditor** currently evaluates FAKE placeholder text, not real HTML. Phase 1 fixes this.
- **Citation sampler** truncates responses to 300 chars. Phase 2 fixes this.
- **Orchestrator** fetches page HTML in schema validation then DISCARDS it. Phase 1 fetches once and shares.
- **KB map JSON** has TWO record schemas (automated: `{guidance_record, backing_records}` vs manual: `{knowledge_ids, priority}`). Do NOT unify. Router handles both.
- **KB map JSON is not read at runtime** — `build_kb.py` loads it into SQLite. Must re-run build after adding entries.
- **C0xx IDs** are RETIRING from wizard UI → replaced by A1/B1/B2/etc. But C0xx→KG mappings in the JSON map are RETAINED.
- **knowledge.jsonl** has 14 duplicate GUIDANCE records (KT-160→KT-173 AND KG-001→KG-014). Both needed.

### User Preferences
- "Do not modify prematurely. First investigate and understand."
- "put new docs here AREOS_COMPLETE_WORKSPACE/docs/session_artifacts/ and update the read me"
- "use the karpathy-principles skill"
- User wants adversarial review and exhaustive coverage

### Conversation History
Previous conversation ID: `d301feb9-84d4-4339-8c2f-0d922cd53a9b`
Transcript: `C:\Users\drc16\.gemini\antigravity\brain\d301feb9-84d4-4339-8c2f-0d922cd53a9b\.system_generated\logs\transcript.jsonl`
