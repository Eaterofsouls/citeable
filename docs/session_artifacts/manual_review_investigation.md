# Manual Review Investigation — Citeable AEOGEO Workflow

---

## 1. Current Manual-Review Architecture

### How It Actually Works

The manual review is a **wizard walkthrough** integrated into Citeable Studio. The flow is:

```
Automated audit completes
  → orchestrator calls select_triggered_cards()
  → cards appear in the Studio "Guided Review" wizard
  → user reviews each card: reads guidance → selects PASS/WARN/FAIL/N/A → optionally adds notes
  → verdict saved to manual_verdicts table via POST /api/v1/audit/runs/{run_id}/verdicts
  → after all cards: "Compile Final Report" triggers LLM synthesis
  → synthesis merges automated findings + manual verdicts → generates narrative report
```

### Components

| Component | File | Role |
|-----------|------|------|
| Card registry | [report.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/cli/report.py) L32–132 | 14 instruction cards with trigger conditions |
| Card trigger logic | [report.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/cli/report.py) L159–204 | `select_triggered_cards()` — matches stages OR check codes |
| Wizard UI | [guided_review.js](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js) | Per-card guidance, verdict buttons, inline submission |
| Verdict API | [verdicts.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/api/routers/verdicts.py) | `POST .../verdicts` — writes to `manual_verdicts` table |
| Verdict DB schema | [artifacts.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/db/schema/artifacts.py) L267–285 | `manual_verdicts(id, run_id, card_id, page_url, verdict, severity, notes, submitted_at)` |
| Manual finding model | [manual_findings_template.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/manual_findings_template.py) | `ManualFinding` dataclass with `card_id, verdict, severity, notes, claim_ids` |
| Remediation merge | [synthesis_engine.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py) L371–417 | `_build_manual_recommendations()` — **BROKEN** (NameError) |
| Report assembly | [report_generator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/services/report_generator.py) L378–401 | `assemble_markdown_report()` — appends flat verdict text |
| LLM synthesis | [audit.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/api/routers/audit.py) L527–564 | Injects manual verdict notes into enriched_recs for LLM context |

### Where Output Goes

```
manual_verdicts table
  ├─→ assemble_markdown_report() — flat append to gap report markdown
  ├─→ _build_manual_recommendations() — CRASHES (NameError) ← never reaches remediation
  └─→ synthesize endpoint L527–564 — injects into LLM context as "human_review_notes"
```

The LLM synthesis path works: it reads manual verdicts from the DB and injects them as `[Human review — PASS] notes` strings into the enriched recommendations. The structured remediation path does NOT work: `_build_manual_recommendations()` crashes at line 382 referencing undefined `MANUAL_REMEDIATION_TEXT`.

---

## 2. Manual AEOGEO Requirements

From Study B's 60 canonical claims, **14 are classified as "Not Automatable"** and **17 as "Partially Automatable"** (where the human supplies judgment after automation collects data). These define what the human must actually do.

### Not-Automatable Activities Requiring Human Verification

| Study B Claim | What the Human Must Actually Do | Why Automation Can't |
|---|---|---|
| **C053** Semantic honesty | Compare JSON-LD claims against visible page text. Flag schema statements the page doesn't back up. | Automation can detect missing fields but cannot judge if a claim like "award-winning" is true |
| **C062** E-E-A-T assessment | Judge whether content shows genuine expertise, first-hand experience, named authorship, and verifiable claims | No algorithmic proxy measures actual expertise quality |
| **C072** Prompt set design | Validate that the citation test prompts match how real customers actually query AI about this brand/category | Requires domain knowledge about the client's customer base |
| **C073** Causal attribution | Explain WHY a page wasn't cited — compare against cited competitor pages to diagnose the gap | Requires cross-referencing automated signals with human judgment about what caused the omission |
| **C074** Hallucination fact-check | Ask AI about the brand and fact-check the answers against ground truth | Requires knowledge of what's actually true about the brand |
| **C078** Zero-click threat | Assess whether AI answers fully satisfy user queries without needing to click through | Requires judgment about user intent and business model implications |
| **C082** Digital PR gap | Identify which third parties win citations instead and devise a PR strategy to close the gap | Requires competitive/strategic analysis |
| **C090** Root cause diagnosis | Synthesize all findings into one coherent narrative explaining what to fix first and why | Requires causal reasoning across all diagnostic layers |

### Partially-Automatable Activities Requiring Human Judgment Component

| Study B Claim | What Automation Does | What the Human Must Add |
|---|---|---|
| **C036** Cloaking | Automation detects content diff between UAs | Human judges if the diff is intentional/legitimate (e.g., geo-targeting) |
| **C052** JS/asset blocking | Automation detects blocked paths | Human judges if those blocked assets actually break content visibility |
| **C056** Entity disambiguation | Automation checks sameAs links exist | Human asks AI "what does [brand] do?" and confirms identity accuracy |
| **C057** NER vs schema | Automation compares entity names | Human judges if mismatches are meaningful or cosmetic |
| **C058** Embedded media | Automation counts iframes/missing alt | Human judges if the embedded content is critical (pricing table) or decorative (map) |
| **C061** Layout effectiveness | Automation measures extractability | Human judges if the layout would produce clean AI citations |
| **C077** Sentiment/framing | Automation can do basic NLP | Human reads AI answers for subtle diminishing framing ("a basic option") |
| **C079** Speakable schema | Automation checks speakable markup exists | Human reads the speakable text aloud and judges voice-readiness |

---

## 3. Coverage Comparison

### The 14 Current Instruction Cards vs Requirements

| Card | Study B Claim | Triggers Correctly? | Coverage Status |
|------|--------------|---------------------|----------------|
| C052 JS blocking | C052 | ✅ Via check codes | Covered when `CRAWLER_PARTIAL`/`CRAWLER_FULLY_BLOCKED` fires |
| C053 Semantic honesty | C053 | ✅ Via check codes | Covered when schema issues fire |
| C056 Entity disambiguation | C056 | ❌ **DEAD** — triggers on STAGE-11, never matches | **Never shown to user** |
| C058 Media blindness | C058 | ⚠️ Via check codes only | Only triggers if `EXTRACTABILITY_LOW`/`NONE` fires |
| C061 Layout effectiveness | C061 | ⚠️ Via check codes only | Only triggers if `EXTRACTABILITY_MEDIUM`/`LOW` fires |
| C062 E-E-A-T | C062 | ❌ **DEAD** — triggers on STAGE-09/20, never matches | **Never shown to user** |
| C072 Prompt set design | C072 | ❌ **DEAD** — triggers on STAGE-22, never matches | **Never shown to user** |
| C074 Hallucination | C074 | ❌ **DEAD** — triggers on STAGE-20, never matches | **Never shown to user** |
| C073 Causal attribution | C073 | ✅ Via `CITATION_NOT_OBSERVED` | Covered when citations aren't found |
| C077 Sentiment/framing | C077 | ✅ Via `CITATION_OBSERVED` | Covered when citations ARE found |
| C078 Zero-click threat | C078 | ✅ Via `CITATION_OBSERVED` | Covered when citations ARE found |
| C079 Speakable | C079 | ❌ **DEAD** — triggers on STAGE-21, never matches | **Never shown to user** |
| C082 Digital PR gap | C082 | ✅ Via `CITATION_NOT_OBSERVED` | Covered when citations aren't found |
| C090 Root cause | C090 | ✅ `always_trigger: True` | Always shown |

> [!CAUTION]
> ### 5 Instruction Cards Are Dead Code
>
> The orchestrator sends `audited_stages = ["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]` (AP-xx naming). But instruction cards trigger on `STAGE-xx` naming (`STAGE-03`, `STAGE-05`, etc.). These namespaces **never intersect**. Stage-based triggering is completely broken.
>
> Cards that rely solely on stage matching (empty `trigger_on_codes`) **can never trigger:**
> - **C056** Entity Disambiguation
> - **C062** E-E-A-T & Trustworthiness Assessment
> - **C072** Citation Prompt Set Design
> - **C074** Hallucination Fact-Checking
> - **C079** Speakable Schema / Voice Readiness
>
> These include the **three most important human judgment calls** in the entire AEOGEO lifecycle: E-E-A-T assessment, hallucination fact-checking, and entity disambiguation.

### What's Missing Entirely (No Card Exists)

| Requirement | Study B Claim | Status |
|---|---|---|
| Cloaking legitimacy judgment | C036 | No card — new automated check needs human follow-up for ambiguous cases |
| Content strategy prioritization | C085–C089 | No card — strategic planning is delegated to the root cause card (C090) which tries to cover too much |
| Brand narrative accuracy review | C074 extension | Hallucination card exists but is dead (never triggers) |

---

## 4. Confirmed Problems

### CRITICAL-001: 5 Dead Manual Review Cards

**Root cause:** [audit_orchestrator.py L391](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py#L391) sends `audited_stages=["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]`. [report.py L32–132](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/cli/report.py#L32-L132) defines `trigger_on_stages` using `STAGE-xx`. These namespaces never match.

**Impact:** The user never sees the E-E-A-T card, the hallucination card, the entity disambiguation card, the prompt design card, or the speakable card. These are the checks that require the most sophisticated human judgment.

**Fix:** Either remap `trigger_on_stages` to use `AP-xx`, or change the orchestrator to send `STAGE-xx` stages, or (better) add check codes that trigger these cards reliably regardless of stage naming.

### CRITICAL-002: Manual Remediation Pipeline Crashes

**Root cause:** [synthesis_engine.py L382](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py#L382) references `MANUAL_REMEDIATION_TEXT` which doesn't exist.

**Impact:** Any manual verdict with `warn` or `fail` that reaches `_build_manual_recommendations()` causes a NameError crash. The entire remediation pipeline for manual findings is non-functional.

### HIGH-001: Triple-Layer Guidance Fragmentation

Three separate systems provide guidance for the same cards:

1. **MANUAL_CARD_GUIDANCE** in [audit_orchestrator.py L67–98](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py#L67-L98) — only covers 5 cards (C052, C053, C073, C077, C090) + a generic DEFAULT
2. **CARD_GUIDANCE** in [guided_review.js L94–227](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js#L94-L227) — covers all 14 cards with question/steps/example (the best guidance)
3. **Instruction card .md files** in [instruction_cards/](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/instruction_cards) — the most detailed guidance, but **never shown in the UI**

The UI actually shows `CARD_GUIDANCE` (the JS version). The .md files are never rendered to the user. `MANUAL_CARD_GUIDANCE` is sent from the backend but only used as fallback text in an older code path. These three sources can drift out of sync.

### MEDIUM-001: Notes Auto-Fill Enables Zero-Evidence Verdicts

In [guided_review.js L264](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js#L264), if the user doesn't type notes:
```javascript
const notes = notesEl && notesEl.value.trim() ? notesEl.value.trim() : 
  `Human qualitative verification recorded as ${verdict.toUpperCase()}`;
```

A user can click PASS → Submit with zero actual investigation, and the system records it as a verified human verdict. The auto-generated notes provide no evidence and no diagnostic value.

### MEDIUM-002: Skip Without Distinction

The wizard has a "Skip →" button. Skipped cards produce no row in `manual_verdicts`. The system cannot distinguish:
- "Haven't reviewed yet" (no verdict)
- "Reviewed and determined N/A" (verdict = na)
- "Deliberately skipped" (no verdict — same as not reviewed)

### LOW-001: page_url Is Meaningless for Most Cards

In [guided_review.js L267](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js#L267), `pageUrl` is auto-derived from the domain input or defaults to `"https://domain.com"`. Every verdict for a run gets the same page_url, regardless of whether the card is about schema, citations, entity identity, or hallucinations. The field carries no real information.

---

## 5. False-Confidence Risks

These are scenarios where the system produces a clean result but the underlying condition is NOT satisfied.

### Risk 1: E-E-A-T Never Assessed (CRITICAL)

**Scenario:** Automated checks find valid schema, good extractability, no crawler blocks. Content scores high. Citation sampling finds the brand is cited 3/5 times. Score: 85/100.

**Reality:** The page content is generic marketing fluff with no named author, no first-hand expertise, no verifiable claims. A human reviewer would flag this as E-E-A-T weak.

**Why it happens:** The C062 E-E-A-T card never triggers (dead code). No human is ever asked to assess content quality. The system reports a high score that does not reflect the actual trustworthiness weakness.

### Risk 2: AI Hallucinating About the Brand (CRITICAL)

**Scenario:** Brand has good technical signals. Citations observed. Score is strong.

**Reality:** When a user asks ChatGPT "What does [Brand] do?", it describes a completely different company. Or it states the brand was "founded in 2015" when it was founded in 2010. Or it attributes a competitor's product to this brand.

**Why it happens:** The C074 hallucination card never triggers (dead code). Nobody fact-checks what AI actually says about this brand. The audit reports the brand is "cited" without verifying that the citation is accurate.

### Risk 3: Wrong Entity, Right Citations (HIGH)

**Scenario:** Citation sampling finds the domain is cited. Score is high.

**Reality:** The AI is actually confusing this brand with a similarly-named entity. The citations are technically present but describe the wrong company.

**Why it happens:** The C056 entity disambiguation card never triggers (dead code). Nobody asks AI "what does [Brand] do?" to verify identity accuracy.

### Risk 4: Zero-Click PASS Without Investigation (MEDIUM)

**Scenario:** A user clicks PASS on every card in 30 seconds without reading anything.

**Reality:** No actual verification occurred. Notes contain auto-generated text like "Human qualitative verification recorded as PASS."

**Why it happens:** No minimum-evidence requirement. No notes validation for PASS verdicts. The system accepts button clicks as evidence.

### Risk 5: Prompt Set Not Validated (MEDIUM)

**Scenario:** Citation sampling uses default prompts. Results show low citation rate. System recommends content improvements.

**Reality:** The prompts don't match what real customers actually ask. The brand IS cited for the right questions, but the audit tested the wrong questions.

**Why it happens:** The C072 prompt set design card never triggers (dead code). Nobody validates that the test prompts are representative.

---

## 6. User-Burden Analysis

### What's Unnecessary or Could Be Simplified

| Current Burden | Assessment |
|---|---|
| **14 instruction cards total** | Too many — several overlap, several are dead. The active cards that fire range from 3–8 depending on audit results |
| **page_url input per card** | Useless — auto-filled with domain, same for every card. Remove it. |
| **Notes text area** | Important but misused — auto-fill defeats the purpose. Should be required for FAIL, optional for PASS |
| **MANUAL_CARD_GUIDANCE from backend** | Redundant — guided_review.js already has better guidance. Remove the backend copy |
| **Instruction card .md files** | Never shown to users — either surface them or remove them |
| **Separate manual_review.html** | Dead page — redirects to Studio. Can be deleted |

### What's Actually Valuable

| Element | Value |
|---|---|
| **CARD_GUIDANCE questions** (guided_review.js) | Excellent — "If you strip away JavaScript, is your content still there?" is clear, specific, and actionable |
| **"Try it yourself" examples** with real domain name | High value — "Ask ChatGPT: What does {{domain}} do?" gives concrete, executable verification steps |
| **4-button verdict (PASS/WARN/FAIL/N/A)** | Right level of granularity — simple enough to not burden, specific enough to be meaningful |
| **Keyboard shortcuts (1/2/3/4)** | Good UX for power users |
| **Progress bar** | Provides clear completion signal |

### The Actual Minimum User Burden

The guided_review.js CARD_GUIDANCE is genuinely well-designed. Each card reads like an interview question, not a diagnostic checklist. The problem is not that the manual review is too complex — it's that the **right cards never appear** and the **evidence pipeline is broken**.

---

## 7. Evidence / Data Model Assessment

### Current Model

```sql
manual_verdicts (
  id            INTEGER PRIMARY KEY,
  run_id        TEXT NOT NULL,
  card_id       TEXT NOT NULL,
  page_url      TEXT DEFAULT '',     -- meaningless (auto-filled)
  verdict       TEXT NOT NULL,       -- pass/warn/fail/na
  severity      TEXT NOT NULL,       -- derived from verdict
  notes         TEXT DEFAULT '',     -- often auto-generated
  submitted_at  TEXT                 -- timestamp
)
```

### Assessment

| Dimension | Current State | Problem |
|---|---|---|
| **What was verified** | `card_id` only | No record of which specific condition was checked |
| **What evidence was found** | `notes` (free text) | Often auto-generated "recorded as PASS" — no structured evidence |
| **What AI said** | Not captured | Hallucination and entity checks require querying AI, but the response is never stored |
| **Confidence** | Not captured | "I'm fairly sure" vs "I verified this thoroughly" are recorded identically |
| **What was compared** | Not captured | Causal attribution requires comparing against competitors, but comparison details aren't stored |
| **Relationship to KB claims** | `claim_ids = [card_id]` | Card IDs are NOT claim IDs — this mapping is fake. `card_id = "C074"` maps to `claim_ids = ["C074"]` which doesn't exist in the claims table |

### Critical Data Model Gap

The `claim_ids` field in `ManualFinding` is populated with `[card_id]` at [manual_findings_template.py L150](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/manual_findings_template.py#L150) and [L190](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/manual_findings_template.py#L190). The comment says "card_id == claim_id in AREOS" but this is false. Card IDs like `C074` do not correspond to claim IDs in the KB claims table. The claim_ids wiring for manual findings is entirely fake.

### What the Data Model Should Capture

For each manual verdict, the minimum useful evidence is:

```
card_id        — which check was performed
verdict        — pass/warn/fail/na
notes          — what the human actually observed (REQUIRED for warn/fail)
evidence_type  — "ai_query_result" | "visual_inspection" | "source_comparison" | "configuration_check"
```

Optional but valuable for specific cards:
```
ai_query_text    — the prompt they asked (for C074, C056, C073)
ai_response_text — what the AI said back (for hallucination/entity checks)
comparison_url   — competitor page compared against (for C073, C082)
```

The current free-text notes field is actually sufficient IF notes are required for actionable verdicts (warn/fail). The main issue is not the schema — it's that notes are optional and auto-filled.

---

## 8. Knowledge / Claims / Remediation Implications

### Current State

1. **Manual verdicts → KB claims:** The mapping is fake. `claim_ids = [card_id]` where `card_id = "C074"` is not a real claim ID. The remediation engine tries to look up `C074` in the claims table and finds nothing.

2. **Manual verdicts → remediation:** Crashes at `MANUAL_REMEDIATION_TEXT` NameError. Even if it didn't crash, the function at L389–415 uses a hardcoded proxy check code (`MISSING_REQUIRED_FIELD`) for all manual findings, which means the KB wiring (`wire_finding()`) always resolves to the same claim regardless of what was manually reviewed.

3. **Manual verdicts → LLM synthesis:** Works. The synthesize endpoint at [audit.py L527–564](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/api/routers/audit.py#L527-L564) injects verdict notes as `human_review_notes` into enriched recommendations. The LLM can read these when generating the narrative report.

### What Should Change

Each instruction card should map to one or more KB knowledge concepts. The existing `check_code_to_knowledge_map.json` pattern should extend to manual cards:

```json
{
  "C062": {
    "guidance_record": "KT-300",
    "backing_records": ["KT-301", "KT-302"],
    "claim_scope": "content-quality"
  },
  "C074": {
    "guidance_record": "KT-310",
    "backing_records": ["KT-311"],
    "claim_scope": "brand-accuracy"
  }
}
```

This way, when a manual verdict of FAIL comes in for C074 (hallucination), the remediation engine can:
1. Look up `KT-310` for the specific guidance text
2. Pull backing evidence from `KT-311`
3. Generate a remediation recommendation grounded in the KB

The `_build_manual_recommendations()` function should be rewritten to use this map instead of the deleted `MANUAL_REMEDIATION_TEXT` dict.

---

## 9. Recommended Manual-Review Design

### Design Principles

1. **Fix the trigger mechanism** — don't redesign the questions, fix the bug that prevents them from appearing
2. **Require notes for FAIL verdicts** — prevent zero-evidence failures
3. **Keep the question format** — the CARD_GUIDANCE questions in guided_review.js are excellent
4. **Remove dead weight** — eliminate redundant guidance layers, unused page_url field
5. **Add the missing cards** — cloaking legitimacy judgment needs a card

### The 7-Question Manual Review

After fixing the trigger bug, the active manual review should consistently present these cards:

| # | Card | Question | When It Triggers | What Human Uniquely Provides |
|---|------|----------|-----------------|------------------------------|
| 1 | **C062** E-E-A-T | "Would a stranger believe the author knows what they're talking about?" | **Always** (most important human check) | Subject-matter judgment about content depth, expertise, authorship quality |
| 2 | **C074** Hallucination | "When you ask AI about your brand, does it get the facts right?" | **Always** (second most important) | Ground-truth comparison — only the brand owner knows what's actually true |
| 3 | **C053** Schema honesty | "Does your structured data say what the page actually says?" | When schema issues fire | Judgment about whether schema claims are truthful |
| 4 | **C056** Entity disambiguation | "When you ask AI who you are, does it know?" | **Always** (identity is fundamental) | Direct observation of AI's brand knowledge |
| 5 | **C073** / **C082** Causal attribution + PR gap | "For pages AI isn't citing, why? Who's getting cited instead?" | When `CITATION_NOT_OBSERVED` fires | Competitive analysis, causal reasoning |
| 6 | **C078** Zero-click threat | "If AI already gave the full answer, would anyone visit your site?" | When `CITATION_OBSERVED` fires | Business-model judgment about traffic risk |
| 7 | **C090** Root cause | "Looking at everything, what's the real reason?" | **Always** (synthesis card) | Holistic causal reasoning across all layers |

### Cards to Merge or Demote

| Card | Recommendation | Reason |
|------|---------------|--------|
| **C052** JS blocking | Merge into automated — the new rendering_auditor (Phase 5) covers this mechanically | If Playwright is available, this check becomes fully automated |
| **C058** Media blindness | Merge into automated — the new media_blindness_auditor covers this mechanically | User judgment about "is this decorative?" can be handled by the root cause card |
| **C061** Layout effectiveness | Merge into automated — content format auditor with real HTML covers this | Extractability metrics with real input are sufficient |
| **C072** Prompt set design | Keep but make it a pre-audit configuration step, not a post-audit review card | The prompt set should be validated BEFORE the citation sampling runs, not after |
| **C077** Sentiment/framing | Keep as-is but add automated sentiment pre-analysis | The human still needs to read for subtle framing |
| **C079** Speakable | Demote to optional — extremely low adoption of speakable schema | Keep the card but don't trigger it by default |

### Minimum Viable Manual Review (3 cards for express audits)

For users who want the fastest possible audit:

1. **C062 E-E-A-T** — "Would a stranger trust this content?"
2. **C074 Hallucination** — "Does AI get the facts right about you?"
3. **C090 Root cause** — "What's the real reason?"

These three cards represent the irreducible human contribution. Everything else is either automatable or derivable from these three.

---

## 10. Prioritized Implementation Plan

### P0: Fix What's Broken (Blocks Everything)

**1. Fix the dead card trigger mechanism** — [audit_orchestrator.py L391](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py#L391)

Change `audited_stages` to use STAGE-xx naming to match the instruction card definitions, OR (better) add check codes that trigger the always-needed cards:

```python
# Option A: Add always-fire codes
INSTRUCTION_CARDS entries for C062, C074, C056 get: "always_trigger": True
# C072 gets: trigger_on_codes: ["CITATION_OBSERVED", "CITATION_NOT_OBSERVED"]
# C079 gets: trigger_on_codes: ["SCHEMA_VALID", "MISSING_REQUIRED_FIELD"]
```

Option A is better because it's independent of the stage naming convention entirely.

**2. Fix MANUAL_REMEDIATION_TEXT crash** — [synthesis_engine.py L382](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py#L382)

Replace the deleted `MANUAL_REMEDIATION_TEXT` dict lookup with KB-backed guidance resolution:

```python
# New: load from check_code_to_knowledge_map.json extended with manual card entries
# Fallback: generate title/description from the ManualFinding fields
if finding.card_id not in manual_kb_map:
    title = f"Manual Review: {finding.check_name}"
    description = finding.notes
else:
    guidance = load_guidance_from_kb(manual_kb_map[finding.card_id], db_path)
    title = guidance.get("title", finding.check_name)
    description = guidance.get("remediation_text", finding.notes)
```

**3. Require notes for FAIL verdicts** — [guided_review.js L262–265](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js#L262-L265)

```javascript
// Before submitting, require notes for fail/warn verdicts
if ((verdict === 'fail' || verdict === 'warn') && (!notesEl || !notesEl.value.trim())) {
  AreosAPI.notify("Please describe what you found before submitting a Warn or Fail verdict.");
  return;
}
```

### P1: Improve Evidence Quality

**4. Add manual card entries to check_code_to_knowledge_map.json**

Map each instruction card to KB knowledge records so manual verdicts can wire to the same KB infrastructure as automated findings.

**5. Fix claim_ids wiring**

Replace `claim_ids=[card_id]` with actual KB claim lookups. When a manual verdict comes in, resolve the card_id through the knowledge map to get real claim IDs.

**6. Remove page_url from the wizard UI**

It's auto-filled and meaningless. Remove the input field from [guided_review.js](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/guided_review.js) and [manual_review.js](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/manual_review.js). Keep the DB column (harmless).

### P2: Consolidate Guidance

**7. Single source of truth for card guidance**

Move CARD_GUIDANCE from guided_review.js into the backend (or into the instruction card .md files, parsed at startup). Eliminate the MANUAL_CARD_GUIDANCE dict from audit_orchestrator.py. The instruction card .md files should be the canonical source; the UI should render their content.

**8. Make C062, C074, C056 always-trigger**

These are the three most important manual checks and should appear in every audit regardless of what codes fire.

### P3: Optional Improvements

**9. Record skip vs not-reviewed**

Add a `skipped` verdict option or a separate `card_reviews` table that records which cards were presented but skipped.

**10. Add pre-audit prompt validation step**

Move C072 (prompt set design) from a post-audit review card to a pre-audit configuration step in the Studio workflow. The user should validate prompts BEFORE citations are sampled.

### What Should Remain Untouched

| Element | Why |
|---|---|
| The 4-button verdict model (PASS/WARN/FAIL/N/A) | Right level of simplicity |
| The CARD_GUIDANCE question format | Excellent — clear, specific, layman-friendly |
| The "Try it yourself" examples with real domain | High user value |
| Keyboard shortcuts | Power-user efficiency |
| The guided wizard modal UX | Well-designed interaction pattern |
| The LLM synthesis injection path | Works correctly — manual notes reach the LLM |

---

## Final Answer

> **Does the current manual review represent the minimum necessary human intervention needed to complete the non-automatable AEOGEO lifecycle, while producing sufficiently structured evidence for the rest of Citeable to generate reliable findings and remediation?**

**No. The current manual review is architecturally broken in three ways:**

1. **5 of 14 instruction cards can never trigger** due to a stage naming mismatch — including the three most critical human judgment calls (E-E-A-T, hallucination, entity disambiguation). The manual review is missing its most important questions.

2. **The remediation pipeline crashes** for all actionable manual verdicts (warn/fail) due to a NameError in synthesis_engine.py. Manual findings with remediation value never reach the recommendation engine.

3. **Evidence capture allows zero-evidence verdicts** — a user can PASS every card in seconds without investigating anything, producing auto-generated notes that provide no diagnostic value.

**However, the manual review design is close to right.** The CARD_GUIDANCE questions in guided_review.js are well-crafted, the 4-button verdict model is appropriate, and the wizard UX is clean. The problems are bugs and wiring failures, not design failures.

**Fix the 3 P0 bugs (trigger mechanism, NameError, notes requirement) and the manual review goes from broken to functional.** The remaining improvements (KB wiring, guidance consolidation, prompt validation) are genuine quality improvements but not blockers.
