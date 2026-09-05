# VERIFICATION PROMPT — Paste This Into New Conversation

---

Read `D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE\docs\session_artifacts\SESSION_CONTINUATION.md` first to understand the full project context.

Then deploy 9 subagents simultaneously. Each subagent reads ONE session doc and cross-references it against `D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE\docs\session_artifacts\DECISIONS_AND_TASKS.md` to find anything missing, inconsistent, or incomplete.

**Each subagent must:**
1. Read its assigned session doc IN FULL
2. Read DECISIONS_AND_TASKS.md IN FULL
3. For EVERY requirement, decision, function signature, check code, data structure, edge case, and test case in its session doc, verify it appears in DECISIONS_AND_TASKS.md (in a task, decision, reference data section, or risk section)
4. Report back with:
   - **FOUND:** Items correctly captured (brief list)
   - **MISSING:** Items NOT in DECISIONS_AND_TASKS.md (detailed — include the exact content that should be added)
   - **INCONSISTENT:** Items where the session doc says one thing but DECISIONS_AND_TASKS.md says something different
   - **IMPROVEMENT:** Anything the session doc implies but never states explicitly that would strengthen the implementation plan

**Subagent assignments:**

| # | Role | Session Doc to Check |
|---|------|---------------------|
| 1 | Phase 0 Verifier | `phase0_deep_spec.md` — verify every bug fix, every exact code replacement, every regression test assertion, every newly discovered bug is captured as a task |
| 2 | Infrastructure Verifier | `phases1_2_infrastructure_spec.md` — verify every function signature, every dataclass field, every module, every architecture gap is captured |
| 3 | KB Scoring Verifier | `phases3_4_kb_scoring_spec.md` — verify every LAYER_DEDUCTION entry, every KB map entry (KT-200 to KT-238), every ACTION_SNIPPET, every GUIDANCE text, every data integrity gap |
| 4 | Manual Review Verifier | `track_b_manual_review_spec.md` — verify SQL schema, API signatures, UI changes, synthesis pipeline changes, all 6 edge cases, all 4 regression tests |
| 5 | Manual Review Design Verifier | `manual_review_product_design.md` — verify ALL 11 questions with their exact structured outputs, conditional logic rules, Express/Full mode, data pipeline, remediation signal mappings, report structure, v1-vs-v2 comparison items |
| 6 | Integration Verifier | `master_integration_spec.md` — verify the Mermaid DAG, phase gate commands, all pytest file contents, rollback plans, all 6 integration gaps |
| 7 | Hostile Review Verifier | `hostile_review.md` — verify all 8 kill-list items have a corresponding fix task or explicit deferral in DECISIONS_AND_TASKS.md |
| 8 | Lifecycle Verifier | `aeogeo_lifecycle_assessment.md` — verify every confirmed gap (Gaps 1-8), every automation opportunity (items 1-12), every architectural risk (Risks 1-5), and every "Must Fix" / "Strong Improvement" item has a task |
| 9 | Implementation Plan Verifier | `implementation_plan.md` — verify every phase, every deliverable, every acceptance criterion from the user-approved plan is present in DECISIONS_AND_TASKS.md |

All docs are at: `D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE\docs\session_artifacts\`

**After all 9 report back:**
1. Compile a single consolidated list of ALL missing items, inconsistencies, and improvements
2. Deduplicate (multiple agents may flag the same gap)
3. For each MISSING item: draft the exact text to add to DECISIONS_AND_TASKS.md (which section, where, exact wording)
4. For each INCONSISTENT item: determine which source is correct and draft the fix
5. For each IMPROVEMENT: evaluate if it's worth adding (Karpathy Principle 2 — only if it prevents a real problem)
6. Apply all changes to DECISIONS_AND_TASKS.md in a single surgical update
7. Report what was added, what was inconsistent and how it was resolved, and what improvements were adopted vs rejected

Do NOT modify any source code. This is a verification and document improvement task only.
