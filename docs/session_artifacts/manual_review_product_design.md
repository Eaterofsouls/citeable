# Citeable Manual Review — Expert-Grade Product Design (v2)

> **What changed from v1:** The previous 5-question design optimized for speed (3 minutes). An AEO/GEO expert reviewing it would call out 8 critical gaps. This version is designed by someone who takes the AEOGEO lifecycle seriously — every not-automatable judgment from Study B is either covered or explicitly justified as out-of-scope.

---

## What the v1 Design Missed (Expert Critique)

| Gap | Study B Claim | Expert Objection |
|-----|--------------|------------------|
| **Schema Semantic Honesty** | C054 — 5/5 consensus not-automatable | v1 dropped this entirely. Automation validates JSON-LD syntax. Whether schema claims match visible page reality is THE classic schema spam vector — validators explicitly do not check it. |
| **Content Answerability** | C052 — the single most emphasized not-automatable judgment | v1 has no question about whether content actually answers a question in a citable way. Extractability (auto) ≠ answerability (human). |
| **Prompt Set Validation** | C072 — the single highest-leverage judgment call | v1 treated this as optional. Study B is explicit: a bad prompt set invalidates everything measured downstream. |
| **Multi-Engine Comparison** | C071 context | v1 showed ONE AI response. Different engines describe brands differently. The variance itself is diagnostic data. |
| **Cloaking Intent** | C036 — partially automatable | The automation plan adds cloaking detection. But interpreting whether a content diff is malicious cloaking vs legitimate geo-targeting is a human judgment. |
| **Competitive Content Analysis** | C080 + C082 | v1 was too vague. An expert compares the cited page actual content structure against the client. |
| **llms.txt Content Quality** | C016 human portion | Automation checks existence. Judging whether the curated content usefully represents the business is human. |
| **Voice Listen Test** | C079 | v1 demoted this. For brands that care about voice, reading speakable text aloud is a real test no automation can do. |

---

## The Expert-Grade Manual Review: 4 Phases, 11 Questions

### Design Principles

1. **Show, don't ask blind** — Every question shows the user what automation already found, then asks for human judgment on top of it
2. **Structured answers → KB templates** — Each answer directly selects which remediation actions fire
3. **Pre-audit validation before post-audit review** — Validate inputs before trusting outputs
4. **Multi-engine, not single-engine** — Show how different AI engines describe the brand
5. **Tiered depth** — Express mode (4 essential questions, ~8 min) or Full Expert mode (all 11, ~25 min)

---

## Phase A: Pre-Audit Validation (Before automation runs)

### A1. Prompt Set Validation [C072]

**Question:** "Are these the right questions to test your brand with?"

Study B (5/5 consensus): *"Designing the actual prompt set — phrasing questions the way real users/customers actually ask them — is not-automatable and repeatedly described as the single highest-leverage judgment call in the whole citation-measurement phase; a bad prompt set invalidates everything measured downstream."*

**What the user sees:**
- The default prompt set the system will use
- Sub-question A: "Do these match what your real customers actually ask?" (Yes / Mostly / No)
- Sub-question B: "What questions should we add or change?" (free text for real customer queries)
- Sub-question C: "What funnel stage matters most?" (Awareness / Consideration / Decision / All)

**Structured output:**
```json
{
  "question": "A1_PROMPT_VALIDATION",
  "maps_to": ["C072"],
  "prompt_match": "mostly",
  "custom_queries": "My customers ask best CRM for startups under 50 people",
  "funnel_focus": "consideration",
  "remediation_signal": "prompt_set_adjusted"
}
```

**How this feeds remediation:** If "No — wrong questions," citation findings get flagged with a confidence caveat: *"Note: Citation results may not reflect real customer queries. Brand owner identified a prompt-set gap. Re-run with adjusted prompts before acting on citation findings."*

---

## Phase B: Automation-Assisted Verification (After automation runs)

These questions show what automation found and ask: "Is this actually a problem?"

### B1. Schema Honesty Check [C054]

**Question:** "We found these claims in your structured data. Do they match what the page actually says?"

Study B (5/5 consensus): *"Verifying that structured-data claims semantically match the actual visible page content is not-automatable: it is reading comprehension and a known deliberate/accidental spam vector, and validators explicitly do not check it."*

**What the user sees:**
- Schema claims extracted by automation (e.g., Organization description: "Award-winning enterprise platform", FAQPage answers, foundingDate)
- Link to open the actual page
- Per-claim verification: "Does the visible page back this up?" (Yes / No / Not mentioned on page)
- Free text for additional issues

**Key design decision:** System pre-populates schema claims from automated output. User confirms/denies each one. Fast AND structured. Each false claim becomes a specific remediation item: "Remove 'award-winning' from schema OR add award details to visible page."

**Structured output:**
```json
{
  "question": "B1_SCHEMA_HONESTY",
  "maps_to": ["C054", "C053"],
  "claims_verified": [
    {"claim": "award-winning", "field": "description", "verified": false, "issue": "not_on_page"},
    {"claim": "foundingDate: 2018", "verified": true},
    {"claim": "$49/mo 14-day trial", "field": "FAQPage.answer", "verified": "price_changed"}
  ],
  "severity": "error",
  "remediation_signal": "schema_honesty_violations"
}
```

---

### B2. Content Answerability [C052]

**Question:** "Here is what AI would extract from your page. Is this actually a good answer?"

Study B (5/5 consensus, #1 most-emphasized): *"Determining whether a passage 'directly answers' a likely user question in a self-contained, citable way ('answerability') is the single most emphasized not-automatable judgment across the whole corpus."*

**What the user sees:**
- The actual text fragment automation extracted from the first 150 words of the page
- Sub-question A: "Does this fragment clearly state what you do?" (Yes-specific / No-marketing-language / No-wrong-thing)
- Sub-question B: "If you had to write one sentence for AI to quote about what your company does, what would it be?" (**REQUIRED** free text — this is the golden input)
- Sub-question C: "Does your page have this clear sentence somewhere?" (Near top / Buried far down / Never written that clearly)

**This is the highest-value question in the entire manual review.** The user's one-sentence answer literally becomes the recommended H1 / opening paragraph in the remediation report. The system doesn't guess what the brand does — the brand owner wrote it.

**Structured output:**
```json
{
  "question": "B2_CONTENT_ANSWERABILITY",
  "maps_to": ["C052"],
  "current_fragment_quality": "marketing_not_answer",
  "ideal_answer_sentence": "Example Corp is a project management tool for engineering teams...",
  "sentence_exists_on_page": "not_written",
  "severity": "error",
  "remediation_signal": "answerability_rewrite_needed",
  "recommended_copy": "Example Corp is a project management tool for engineering teams..."
}
```

**How this feeds remediation:**

> **ACTION:** Replace opening paragraph with the brand owner's definition:
> *"[Their sentence from B2]"*
>
> Also update: Organization schema description, meta description tag, llms.txt summary line.

---

### B3. Cloaking Intent [C036] *(Only when cloaking_auditor finds a content diff)*

**Question:** "We found a difference between what browsers see and what AI bots see. Is this on purpose?"

**What the user sees:**
- The content difference (e.g., "Browser: 847 words with pricing. Bot: 312 words, NO pricing")
- Missing elements listed (pricing table, testimonials, interactive widget)
- "Is this intentional?" (Yes-intentional / No-unexpected / Partially-JS-expected)
- "Is the missing content important for AI?" (Critical-pricing-specs / Nice-to-have / Decorative-only)

**Severity derivation:** "Unintentional" + "Critical" = error priority. "Intentional" + "Decorative" = info.

---

## Phase C: Human-Only Judgment (Things only a human can answer)

### C1. Brand Accuracy Across AI Engines [C074 + C056]

**Question:** "Here is what AI says about you. We asked three different engines."

**Key change from v1:** Show ALL engines side by side, not just one.

**What the user sees:**
- ChatGPT response, Perplexity response, Google AI Mode response — all visible simultaneously
- Sub-question A: "Overall accuracy" (All accurate / Some accurate some wrong / All contain errors / Wrong company entirely)
- Sub-question B: "What is wrong?" (checkboxes: wrong product category, wrong founding date/location, wrong features/integrations, competitor attribution, outdated info, wrong company confusion, false awards, wrong pricing)
- Sub-question C: "What should AI actually say?" (**REQUIRED** if errors found — the ground truth correction)
- Sub-question D: "Do all three know who you are, or does any confuse you with a different company?"

**Multi-engine diagnostic patterns:**
- ALL engines wrong the same way → **content problem** (your page says the wrong thing, all engines extract the same wrong answer)
- Engines DISAGREE with each other → **entity disambiguation problem** (AI is not sure which company you are)
- ONE engine right, others wrong → **training data freshness** (one engine has more recent data)

Each pattern triggers a different remediation path from the KB.

---

### C2. Content Trustworthiness / E-E-A-T [C062]

**Question:** "Would a stranger trust that the author of this page actually knows what they're talking about?"

Study B (5/5 consensus): *"Assessing content depth, factual accuracy, first-hand expertise, and overall E-E-A-T / YMYL trustworthiness is not-automatable: it requires subject-matter expertise and accountability that no classifier or 'authority score' proxy actually measures."*

**What the user sees:**
- Automated extractability/readability scores shown for context: "Automation says content is technically extractable (72/100) — but is it actually GOOD? That is on you."
- Sub-question A: Named author? (With visible credentials/bio / Name only / No byline or just Admin)
- Sub-question B: First-hand experience? (Yes-specific examples, case studies, original data / Somewhat / No-could-be-written-about-any-company)
- Sub-question C: Claims sourced? (Yes / Partially / No-stated-without-sources)
- Sub-question D: Overall expertise rating (Strong-deep domain expertise / Adequate-generic / Weak-surface-level)

Each sub-answer maps to a specific remediation action. "Name only" → "Add author bio with credentials + LinkedIn." "Unsourced" → "Cite sources for all statistical claims."

---

### C3. Citation Framing + Zero-Click [C077 + C078] *(Only when citations ARE observed)*

**Question:** "AI mentioned you. Here is how it positioned you across engines."

**What the user sees:**
- The AI citation text with brand mention highlighted
- Sub-question A: Positioning (Favorable / Neutral-accurate / Diminishing / Negative / Not mentioned)
- Sub-question B: Zero-click: "After reading this AI answer, would a user still visit your site?" (Yes / Maybe / No-fully-answered)
- Sub-question C: Business impact: "Does this matter for your business?" (A lot-need-click / Somewhat / Not much-awareness-enough)
- Free text: "If positioning is wrong, what should AI say instead?"

Business impact gates whether zero-click becomes a remediation priority or informational. "A lot" + "No, fully answered" → CRITICAL zero-click finding. "Not much" → info only.

---

### C4. Citation Gap + Competitive Analysis [C073 + C082 + C080] *(Only when citations NOT observed for some prompts)*

**Question:** "Your brand was not cited for some questions. Here is who was — and let us figure out why."

**Key addition:** Show automated competitive extraction data alongside the question. User sees real numbers, not guessing blind.

**What the user sees:**
- Competitor analysis showing: their schema coverage, first-paragraph quality, referring domains count, FAQ schema presence — compared against user's site (e.g., "competitor.com: 127 referring domains vs your 23")
- Which third-party sites were cited (G2, Wikipedia, Forbes, review sites)
- Sub-question A: "Why do you think AI chose them?" (checkboxes: clearer content, stronger authority, review/comparison content we lack, no relevant page exists, vague marketing language, third-party sites outrank us, genuinely don't know)
- Sub-question B: "Which gap is biggest?" (Content / Authority / Technical / Page doesn't exist)
- Sub-question C: "If you have content that SHOULD answer this question, paste URL"

Structured gap type → specific KB template. "Authority gap" triggers Digital PR template. "Content gap" triggers content creation template. "Page doesn't exist" triggers content strategy template.

---

### C5. Speakable / Voice Readiness [C079] *(Optional — only if speakable markup exists)*

**Question:** "Read this out loud. Does it work as a spoken answer?"

Study B: *"Whether the designated text is actually a good, complete, well-toned spoken answer is human editorial judgment (a 'listen test')."*

**What the user sees:**
- The speakable text extracted from schema markup
- Instruction: "Read it out loud. (Really — say it to yourself.)"
- Sub-question A: "Makes sense spoken with no visual context?" (Yes / Almost-but-references-visual / No-too-long-corporate)
- Sub-question B: "Under ~100 words?" (Yes / No)

---

## Phase D: Synthesis (Connecting everything)

### D1. llms.txt Content Review [C016] *(Only if llms.txt exists)*

**Question:** "Your llms.txt file exists. Does it actually represent your business well?"

Study B: *"Judging whether its curated content usefully represents the business is not [automatable]."*

**What the user sees:**
- The actual llms.txt content displayed
- "Does the summary line accurately describe your business?" (Yes / No-vague-wrong-outdated)
- "Are the linked pages the ones you would want AI to read?" (Yes / No-missing-important-pages / Some-links-broken)
- Free text: "If wrong, what should the summary say?"

---

### D2. Root Cause Diagnosis [C090]

**Question:** "Looking at everything — automated findings AND what you just verified — what is the real problem?"

Study B (5/5 consensus): *"Cross-referencing technical findings with citation-performance data to diagnose root causes is not-automatable causal reasoning across disparate data sources that no single tool synthesizes; it is described as the auditor's core analytical work."*

**What the user sees:**
- Full audit summary: automated findings (errors/warnings/info counts + top issues) PLUS the user's own earlier observations from B1, B2, C1, C2, C4
- Sub-question A: "Primary root cause" (Access / Content / Honesty / Identity / Authority / Multiple)
- Sub-question B: "What should we fix FIRST?" (Content / Schema / Identity / Authority / Not sure — that is what I need the report to tell me)
- Sub-question C: "Your diagnosis — this becomes the executive summary" (**REQUIRED** free text — write as you would explain to a colleague)

The user's free text becomes the executive summary's human-authored diagnosis. The LLM synthesizer references it but does not replace it.

---

## Express Mode vs Full Expert Mode

### Express Mode (~8 minutes, 4 questions)

| Question | Why essential |
|----------|--------------|
| B2 Content Answerability | #1 human judgment in Study B. Gets the ideal answer sentence. |
| C1 Brand Accuracy (multi-engine) | Only the brand owner knows ground truth. |
| C2 E-E-A-T Assessment | Expertise cannot be automated. |
| D2 Root Cause Diagnosis | Connects everything into one diagnosis. |

Skipped questions marked in report with confidence caveat.

### Full Expert Mode (~25 minutes, all 11 questions)

All questions in order: A1 → B1 → B2 → B3 → C1 → C2 → C3 → C4 → C5 → D1 → D2

Recommended for first-time audits or when the brand owner is personally doing the review.

---

## How All 11 Questions Feed the Remediation Report

### Data Pipeline

```
Phase A (pre-audit):
  A1 prompt validation → confidence modifier on ALL citation findings
                       → if wrong questions: caveat on entire report

Phase B (automation-assisted):
  B1 schema honesty   → per-claim remediation items
                       → "Remove X from schema" or "Add X to visible page"
  B2 answerability     → recommended opening paragraph (brand's own words)
                       → "Rewrite H1 and opening paragraph to: [their sentence]"
  B3 cloaking intent   → severity modifier on cloaking finding
                       → "Unintentional" = error priority, "Intentional" = info

Phase C (human-only):
  C1 brand accuracy    → error-type-specific KB templates
                       → wrong_products → "Update schema description"
                       → confuses_entity → "Establish Wikidata entry"
                       → outdated → "Update all date references"
  C2 E-E-A-T          → sub-question-specific templates
                       → no_bio → "Add author bio with credentials"
                       → unsourced → "Cite sources for statistics"
  C3 citation framing  → positioning-specific templates
                       → diminishing → "Create comparison page"
                       → zero_click + high_impact → "Add unique value not in AI answer"
  C4 competitive gap   → gap-type-specific templates
                       → content_gap → "Create [topic] page"
                       → authority_gap → "Digital PR campaign targeting [sources]"
  C5 speakable        → "Rewrite speakable text: remove visual references, shorten"

Phase D (synthesis):
  D1 llms.txt content → "Update llms.txt summary to: [their text]"
  D2 root cause       → executive summary text
                       → fix-sequence priority (what to do first)
```

### Key Architecture Decision: LLM Narrates, Does Not Decide

```
DETERMINISTIC LAYER (no LLM):
  1. Automated findings → KB claim resolution → recommendations
  2. Manual observations → KB template selection → recommendations
  3. Merge + deduplicate + priority sort → final recommendation list
  4. Group by 3-layer hierarchy (Access → Content → Authority)
  Output: Structured recommendation plan (JSON)

LLM SYNTHESIS LAYER (narrative only):
  Input: The deterministic plan + human diagnosis text from D2
  Step 1: Write narrative connecting the dots
  Step 2: Red Team checks for hallucinations
  Step 3: Ground — remove anything not in the input
  Output: Narrative that EXPLAINS the plan (not the plan itself)
```

The report combines the deterministic plan (reliable, reproducible) with the LLM narrative (readable, explanatory). The LLM cannot make up recommendations — it can only explain the ones the KB selected.

### Remediation Report Structure

Single unified deliverable:

1. **Executive Diagnosis** — Human-authored from D2, woven with LLM narrative
2. **Layer 1: Access** — Fully automated findings (robots.txt, llms.txt, crawling, rendering)
3. **Layer 2: Content and Schema** — Automated + human findings integrated inline
4. **Layer 3: Authority and Citations** — Authority metrics + human competitive analysis + citation data
5. **Fix Sequence** — Week-by-week action plan ordered by diagnostic layer
6. **Transparency** — Audit metadata: checks run, questions answered, mode, engines tested, pipeline steps, flags

### Report Finding Cards

Each finding integrates auto + manual:

```
Source tag: [AUTO] | [HUMAN] | [AUTO + HUMAN CONFIRMED]
Title + severity icon
Automated detail (what the scanner found)
Human observation (what the reviewer confirmed/added)
Evidence: Governing claim [Cxxx] — statement — source
ACTION: Specific, concrete fix with exact text/code
Priority: CRITICAL / HIGH / MEDIUM / LOW
```

"AUTO + HUMAN CONFIRMED" = strongest finding type. Automation detected it AND human verified it. Highest remediation priority.

---

## Summary: v1 vs v2

| Dimension | v1 (5 questions, 3 min) | v2 (11 questions, 25 min) |
|-----------|------------------------|--------------------------|
| Study B coverage | Missed C054, C052, C072, C036, C079, C016, C080 | All not-automatable claims covered |
| Schema honesty | Not asked | B1 — pre-populated from automation, user confirms each claim |
| Content answerability | Not asked | B2 — THE most important question. Gets the brand own ideal sentence |
| Prompt validation | Afterthought | A1 — gates the entire audit. Bad prompts = caveat on all results |
| Multi-engine | Single response | C1 — three engines side by side. Variance pattern is diagnostic |
| Competitive data | Vague | C4 — shows automated competitor metrics alongside human judgment |
| Answer becomes remediation | Some | ALL — every structured answer selects specific KB templates |
| Express option | N/A | 4-question express mode for time-constrained users |
| Report integration | Verdicts appended at bottom | Human observations integrated inline with findings |
| LLM role | Invents recommendations | Narrates deterministic recommendations. Cannot invent. |
