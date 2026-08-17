---
card_id: C058
stage: STAGE-09
automatability: Partial
check_name: "Embedded Media Blindness"
claim_statement: "Detecting reliance on iframes/canvas/embeds is detectable, but judging whether the content's absence breaks the page's answer requires human understanding of page purpose."
---

# C058 — Embedded Media Blindness

## What AREOS Does Automatically
- Detects presence of `<iframe>`, `<canvas>`, `<object>`, `<embed>` elements.
- Flags pages where the majority of body text appears to be inside such elements.
- Checks for the presence of `alt` text on images and transcripts linked from `<video>` elements.

## What You Must Do Manually

### Step 1 — Identify what the embed is
For each embedded element AREOS flagged, answer:
- Is it decorative? (embedded map, social media widget) → probably not a problem.
- Is it the primary content? (an embedded PDF, a data table in an iframe, a Tableau chart) → **critical issue**.

### Step 2 — Test the text extraction
Use this command to see what a text-only crawler sees:
```
curl -s <URL> | python -c "import sys; from html.parser import HTMLParser; p = HTMLParser(); p.feed(sys.stdin.read())"
```

Or paste the URL into [Web Archive's text view](https://web.archive.org). Does the critical information still appear?

### Step 3 — Check for fallback content
- Does the `<iframe>` have a meaningful text description directly after it in the HTML?
- Do `<video>` embeds have `<track kind="captions">` or a visible transcript?
- Does the `<canvas>` chart have an `aria-label` or accompanying prose table?

### Step 4 — Verdict
- Embedded content is decorative, core content is in HTML → **PASS**
- Embedded content is supplementary, partial fallback exists → **WARN: improve fallbacks**
- Core content is embedded with no fallback → **FAIL: AI crawler cannot read this page**

### Remediation
For critical embedded content, always provide a visible HTML alternative:
- Data tables: replicate key data in an `<table>` below the chart.
- PDFs: provide a summary section in HTML above the PDF embed.
- Video: add a text transcript.
