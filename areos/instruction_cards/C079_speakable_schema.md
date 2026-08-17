---
card_id: C079
stage: STAGE-21
automatability: Partial
check_name: "Speakable Schema / Voice-Answer Readiness"
claim_statement: "Markup presence is checkable; whether the text designated as speakable is actually a good, complete, well-toned spoken answer is human editorial judgment (a 'listen test')."
---

# C079 — Speakable Schema / Voice-Answer Readiness

## What AREOS Does Automatically
- Checks for `speakable` property in `WebPage` or `Article` schema.
- Validates that `cssSelector` or `xPath` values are syntactically valid.
- Checks that the designated CSS selector exists in the page's DOM.

## What You Must Do Manually

### Step 1 — Extract the speakable text
Find the `speakable` block in the page's JSON-LD. Note the CSS selector or XPath it points to.

Open the page, locate that element in DevTools, and copy its inner text.

### Step 2 — Do the "listen test"
Read the extracted text aloud (or use text-to-speech). Ask:
- Does it sound natural when spoken? Or is it clearly written for a screen?
- Does it directly answer a question a user might ask a smart speaker?
- Does it make sense without the visual context of the rest of the page?
- Is it an appropriate length? (Google recommends speakable passages be short and standalone — not a 400-word paragraph.)

### Step 3 — Check for common speakable anti-patterns
| Anti-pattern | Problem |
|---|---|
| Selected text starts mid-sentence | Sounds nonsensical when read aloud |
| Passage refers to "the image above" or "see chart below" | Impossible context in a voice response |
| Passage is a bulleted list | May not translate well to speech without visual formatting |
| Passage is > 200 words | Too long for a practical voice answer |
| Passage is a promotional headline | Not informational; fails the "did this answer my question?" test |

### Step 4 — Verdict
- Speakable text is short, standalone, directly answers a common question, sounds natural aloud → **PASS**
- Present but with minor issues (too long, minor visual references) → **WARN**
- Not present, or present but deeply unsuitable for speech → **FAIL** / **NOT APPLICABLE** (if voice search is not a priority channel for this client)

### Remediation
- Write a 50–100 word introductory paragraph for key pages that directly answers the page's core question in plain spoken language.
- Apply `speakable` pointing to that paragraph's CSS selector.
- Re-run the listen test after changes.
