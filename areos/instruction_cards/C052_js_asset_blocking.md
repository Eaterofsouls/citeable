---
card_id: C052
stage: STAGE-03
automatability: Partial
check_name: "JS/Asset Blocking Materiality"
claim_statement: "Detecting blocked JS/CSS/image assets in robots.txt is mechanical, but determining if those assets actually matter for the page's rendered answerability requires human judgment."
---

# C052 — JS/Asset Blocking Materiality

## What AREOS Does Automatically
- Fetches `robots.txt` and flags every `Disallow:` rule that blocks JS bundles, CSS files, or image resources.
- Lists the specific paths blocked (e.g., `/static/js/`, `/assets/img/`).
- Calculates what percentage of page resources are blocked.

## What You Must Do Manually

### Step 1 — Review the blocked asset list
Open the automated findings report and locate the `CRAWLER_PARTIAL` findings for this page. Note every blocked path.

### Step 2 — Render the page yourself
Open the URL in your browser. Then open DevTools → Network tab. Filter by JS/CSS. Compare the loaded resources against the blocked paths.

**Ask yourself:** Would removing those JS bundles or CSS files cause the main body text to disappear entirely? Or is the page still readable?

### Step 3 — Render as a text crawler would
Install the browser extension "Web Developer" or run: `curl -s <URL> | python -m html.parser`

Does the visible text content (the parts an AI would read) survive if those blocked assets are missing?

### Step 4 — Verdict
- If the main body text is still present without the blocked assets → **Not a critical block**. Mark as `PASS`.
- If the main body text disappears (fully JS-rendered SPA) → **Critical block**. Flag for remediation.

### Remediation
Add the blocked asset paths to an `Allow:` rule for AI crawlers in `robots.txt`. For SPAs, consider adding a server-side rendered (SSR) or prerendered static version.
