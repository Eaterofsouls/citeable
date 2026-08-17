---
card_id: C077
stage: STAGE-20/22
automatability: Partial
check_name: "Sentiment and Framing Analysis"
claim_statement: "Sentiment/framing analysis is partially automatable with classifiers; nuanced framing (e.g., damning with faint praise, technically-accurate-but-unflattering comparisons) needs a human read."
---

# C077 — Sentiment & Framing Analysis

## What AREOS Does Automatically
- Runs a basic positive/neutral/negative sentiment classifier over AI-generated answers that mention the brand.
- Flags answers classified as `negative`.

## What You Must Do Manually

The automated classifier catches obvious cases. Your job is to catch the nuanced ones.

### Step 1 — Read every AI answer that mentions the brand
Collect AI answers from the citation sampling runs. Read each one. Don't just check the classifier's verdict.

### Step 2 — Identify soft framing issues the classifier misses
Look for these specific patterns:

**Damning with faint praise:**
> *"[Brand] offers a basic set of tools suitable for small businesses."*
(The word "basic" is negative in context, but a classifier may score this as neutral.)

**Technically accurate but unflattering positioning:**
> *"[Brand] is a smaller alternative to [Dominant Competitor]."*
(Technically true, but positions the brand as inferior by default.)

**Omission-as-criticism:**
> *"Top options for [category] include [Competitor A], [Competitor B], and [Competitor C]."*
(Brand not mentioned at all, which in itself is a statement about its standing.)

**Inconsistent attribution:**
> *"[Brand] specializes in [service they don't actually lead on], while [Competitor] is known for [Brand's actual specialty]."*

### Step 3 — Rate the framing
- **Positive**: Brand is described as a leader or strong option for the user's need.
- **Neutral-accurate**: Described fairly, neither elevated nor diminished.
- **Neutral-diminishing**: Technically accurate but inadvertently positions the brand as secondary.
- **Negative**: Actively unflattering or inaccurate in a harmful direction.

### Step 4 — Identify the content fix
For framing issues, the fix is always **upstream content**, not a code change:
- What page or piece of content, if it existed, would cause the LLM to describe the brand differently?
- Is there a specific claim (e.g., a case study, an award, a data stat) that, if prominently stated on the site, would shift the framing?

Document this as a content gap in the report.
