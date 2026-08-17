---
card_id: C078
stage: STAGE-22
automatability: Not
check_name: "Zero-Click Threat Assessment"
claim_statement: "Determining whether an AI answer fully 'absorbs' a query without citing the source requires human interpretation of whether the AI answer actually satisfied user intent."
---

# C078 — Zero-Click Threat Assessment

## What AREOS Does Automatically
- Records citation frequency (was the brand's domain cited as a source?).
- Captures the raw AI answer text.

## What You Must Do Manually

Observing that the brand was "not cited" is not the same as assessing whether the AI answer was good enough that a user would never visit the site anyway. This is the zero-click question, and it requires human judgment.

### Step 1 — For each prompt in the citation sample, read the AI answer
Ask yourself: *"If I were the user who typed this question, would I need to click through to any website to get what I needed?"*

### Step 2 — Classify the answer's completeness
| Classification | Description |
|---|---|
| **Fully absorbed** | The AI answer is so complete that a typical user would not need to visit any source. Zero-click threat is high. |
| **Partially absorbed** | The AI provides a useful overview but leaves the user wanting more details, so they'll likely click through. |
| **Gateway only** | The AI answer is shallow or explicitly refers the user to sources. Click-through is expected. |

### Step 3 — Assess the traffic risk
For each prompt where the answer was **Fully absorbed**:
- Is this a high-volume query (many users likely search this)?
- Was the brand the natural destination for this query (should they be getting this traffic)?
- Is this a query that historically drove significant organic traffic to the site?

High-volume + fully-absorbed + previously-high-traffic = **High zero-click risk for this query**.

### Step 4 — Document the threat with specifics
Do not just write "there is a zero-click risk." Write:
> *"Query '[Prompt X]' was fully absorbed by [Engine] in 4/5 runs. The AI answer included [specific data point] drawn from the client's own page [URL]. This query represented approximately [N]% of organic traffic based on [Analytics tool]. Recommendation: [content strategy or product pivot advice]."*

### Step 5 — Strategic response options
Zero-click is not always bad. For some brands, being the source an AI answers from (even without a click) is valuable for brand presence. The response depends on the client's business model:
- **Lead-gen / SaaS**: Need the click → Restructure content to entice, not fully answer.
- **Topical authority / media**: Being the cited source is the goal → Optimize for citation even if it means zero-clicks.
- **E-commerce**: Need the click to the product page → Add product schema and direct-purchase paths.
