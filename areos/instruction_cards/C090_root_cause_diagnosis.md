---
card_id: C090
stage: unmapped
automatability: Not
check_name: "Root Cause Diagnosis"
claim_statement: "Cross-referencing technical findings with citation-performance data to diagnose root causes is causal reasoning across disparate data sources that no single tool synthesizes."
---

# C090 — Root Cause Diagnosis

## What AREOS Does Automatically
- Produces a list of technical findings (schema errors, robot blocks, low extractability scores).
- Produces citation observation data (cited / not cited per prompt).
- Wires each finding to its governing claim ID.

## What You Must Do Manually

This is the auditor's core analytical work. Everything AREOS has done leads to this step.

### Step 1 — Build the findings matrix
Create a two-axis table:

| Page / Topic | Technical findings (from 3b, 3c, 3d) | Citation result (from 3e) |
|---|---|---|
| Homepage | Schema: MISSING_RECOMMENDED_FIELD (description) | Cited in 1/5 runs |
| Services page | Robots: CRAWLER_FULLY_BLOCKED (GPTBot) | Cited in 0/5 runs |
| Blog post | Extractability: medium | Cited in 3/5 runs |

### Step 2 — Look for convergent evidence
Strong root cause hypotheses emerge when multiple signals point at the same cause:

- Page blocked in robots.txt AND extractability is low AND citation is 0/5 → **High confidence: the block is the primary cause**.
- Page not blocked, schema passes, extractability is high, but citation is still 0/5 → **Mysterious case**: the cause is upstream of the technical layer (content quality, E-E-A-T, prompt design, or market awareness).

### Step 3 — Apply the three-layer diagnostic framework
For each not-cited page, work through these layers in order:

1. **Access layer** (Stages 1–4): Can the crawler even reach and render the page?
   → Check: robots.txt, llms.txt, JS rendering, blocked assets.

2. **Content layer** (Stages 5–17): If it can be reached, is the content good enough to be extracted and trusted?
   → Check: schema validity, extractability score, E-E-A-T, freshness, entity recognition.

3. **Authority layer** (Stages 18–22): If the content is good and accessible, is the brand authoritative enough on this topic?
   → Check: citation share-of-voice, third-party mentions, backlink profile, brand entity strength.

Diagnose at the *lowest layer first*. There is no point fixing authority-layer issues if access-layer issues prevent the crawler from reading the page.

### Step 4 — Write the diagnosis
For each key page or topic, write one diagnostic paragraph:
> *"[Page URL] scored 0/5 citation observations for the prompt '[Prompt X]'. Root cause diagnosis: (1) primary — GPTBot is fully blocked via robots.txt (STAGE-01 failure); fixing this is prerequisite to all other improvements. (2) secondary — even if unblocked, the page's average paragraph length of 210 words indicates poor chunking for AI extraction (STAGE-14, extractability: low). Recommended fix sequence: unblock GPTBot, then restructure page into headed sections with shorter paragraphs and an FAQ schema block."*

### Deliverable
One diagnostic paragraph per failing page, added to the final remediation report. This narrative is the primary output the client pays for.
