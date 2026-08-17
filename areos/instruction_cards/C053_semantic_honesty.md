---
card_id: C053
stage: STAGE-05
automatability: Not
check_name: "Semantic Honesty of Structured Data"
claim_statement: "A script can check if FAQPage schema exists, but it cannot judge if the schema accurately reflects the visible text without hallucinating or keyword-stuffing."
---

# C053 — Semantic Honesty of Structured Data

## What AREOS Does Automatically
- Detects `FAQPage`, `HowTo`, `Article`, and other schema blocks.
- Validates required and recommended fields are present.
- Flags unparseable or malformed JSON-LD.

## What You Must Do Manually

### Step 1 — Export the schema
Open the page → View Source → find `<script type="application/ld+json">` blocks. Copy the JSON.

Alternatively, paste the URL into [Google's Rich Results Test](https://search.google.com/test/rich-results).

### Step 2 — Cross-check schema text against page text
For each `Question`/`Answer` pair in a `FAQPage` (or each `step` in a `HowTo`):

1. Find the corresponding text visible on the actual page.
2. Confirm they match **word-for-word** or are at minimum an accurate summary.
3. Flag any pair where the schema text includes information **not present on the page** (hallucination risk).

### Step 3 — Check for keyword-stuffing
Read the `name` and `description` fields of `Organization` and `Product` schemas.

**Red flags:**
- Unnatural keyword repetition (e.g., "best SEO tool, top SEO software, leading SEO platform")
- Descriptions longer than the visible page text on the same topic
- Claims the page does not make (e.g., "award-winning" with no visible award mention)

### Step 4 — Verdict
- All schema fields match visible text, no stuffing → **PASS**
- Minor mismatches → **WARN: recommend alignment**
- Schema contains content absent from the page → **FAIL: schema is misleading**

### Remediation
Edit the JSON-LD to exactly mirror visible text. Never include claims in schema that aren't explicitly backed by visible page content.
