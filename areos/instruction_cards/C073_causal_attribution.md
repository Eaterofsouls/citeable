---
card_id: C073
stage: STAGE-22
automatability: Not
check_name: "Causal Attribution of Citations"
claim_statement: "Explaining *why* an LLM cited (or ignored) a particular source is not-automatable. Causal attribution cannot be deterministically inferred from outside a probabilistic model."
---

# C073 — Causal Attribution of Citations

## What AREOS Does Automatically
- Records which pages were or were not cited in a given prompt run.
- Tracks citation frequency across multiple runs.
- Flags pages with low citation frequency (e.g., 0/5 runs).

## What AREOS Cannot Do
AREOS **cannot tell you why** a page was cited or not cited. No tool can — AI providers do not expose their retrieval/ranking logic. This check is your job.

## What You Must Do Manually

### Step 1 — For each not-cited page, build a hypothesis list
Look at the automated findings for that page. Gather all the signals:
- Was the page blocked in `robots.txt`?
- Did it fail schema validation?
- Was the extractability score `low` or `none`?
- Was the page content thin or not directly answering the prompt?

These are candidate *causes*, not confirmed causes. Document them as hypotheses.

### Step 2 — Identify which cited competitor pages are doing differently
Go to the AI engine and run the same prompt that failed to cite this page. Look at what **was** cited.

Open those competitor pages and compare against the failing page:
- Is the competitor's page structured more clearly?
- Does the competitor have FAQPage schema that this page lacks?
- Is the competitor's content more comprehensive?
- Does the competitor have higher E-E-A-T signals?

### Step 3 — Cross-reference hypotheses with competitor differences
Match your hypotheses from Step 1 against the competitor differences from Step 2.

Where a hypothesis is *confirmed by a competitor pattern*, mark it as **Likely Cause** in your notes.

### Step 4 — Write the root cause diagnosis
Document your reasoning in plain language:
- *"Page X is not cited because: (1) robots.txt blocks GPTBot, (2) the core service description is rendered in a JS component that crawlers cannot read. Evidence: the cited competitor page [URL] delivers the same information in HTML."*

### Deliverable
One paragraph of root-cause narrative per failing page, added to the final audit report. This is the auditor's core analytical work — its quality is the main differentiator between a useful report and a checklist.
