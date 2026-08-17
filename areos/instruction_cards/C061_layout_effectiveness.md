---
card_id: C061
stage: STAGE-14
automatability: Partial
check_name: "Layout Effectiveness for AI Extraction"
claim_statement: "Content-type classification (FAQ, listicle) is automatable; judging whether the layout actually serves AI extraction well ('would ChatGPT pull this?') is subjective."
---

# C061 — Layout Effectiveness for AI Extraction

## What AREOS Does Automatically
- Classifies the page's content type (definition, FAQ, listicle, how-to, comparison, essay).
- Counts headings, paragraph lengths, list items, and FAQ indicators.
- Flags pages where the average paragraph is >150 words (poor chunking) or where there are no headings.

## What You Must Do Manually

### Step 1 — Read the page as if you're ChatGPT
Open the page. Ask yourself: *"If a user asked me 'What is [topic of this page]?', could I pull a single, clean, citable answer from this page's text?"*

Indicators of **good extractability:**
- The first paragraph directly answers the page's core topic in 2–3 sentences.
- Headings clearly signal what each section covers.
- Lists and bullets contain short, discrete facts.
- There's an FAQ section at the bottom.

Indicators of **poor extractability:**
- The page starts with a marketing hero statement ("We're the best in class...") and takes 3 scrolls to reach actual substance.
- All information is buried in long paragraphs with no headings.
- Key facts are only stated visually in an infographic.

### Step 2 — Manually test with Perplexity
Go to [perplexity.ai](https://perplexity.ai) and search for the page's main topic + brand name.
- Does this specific page appear as a source?
- If cited, does the snippet Perplexity extracted make sense?
- If not cited, is a competitor page cited instead for the same question?

### Step 3 — Verdict
- Clean answer extractable from top of page, good structure → **PASS**
- Content is there but buried or poorly structured → **WARN: restructure for chunking**
- No extractable answer; primarily visual/marketing → **FAIL**

### Remediation
- Add an explicit "What is X?" or definition section near the top.
- Convert long prose blocks into headed sections.
- Add an FAQ schema at the bottom of the page with the 3–5 most common questions.
