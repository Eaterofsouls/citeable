---
card_id: C074
stage: STAGE-20
automatability: Not
check_name: "Hallucination Fact-Checking"
claim_statement: "Detecting factual inaccuracies in how a brand is described by an AI engine requires comparing generated text against ground truth the auditor holds — a human fact-check, not a pattern match."
---

# C074 — Hallucination Fact-Checking

## What AREOS Does Automatically
- Runs citation sampling prompts and captures the AI-generated answer snippet.
- Stores the raw answer text alongside the cited URLs in the observation record.

## What You Must Do Manually

### Step 1 — Collect brand mentions
Run these prompts in ChatGPT, Perplexity, and Gemini:
- *"What does [Brand Name] do?"*
- *"Describe [Brand Name]'s main services."*
- *"What is [Brand Name] known for?"*

Capture the full text of each answer.

### Step 2 — Fact-check against ground truth
You (or someone with deep brand knowledge) must read each AI answer and compare it line by line against:
- The official website homepage and About page.
- The company's own product descriptions.
- Any press releases or official announcements.

Flag every discrepancy, even if it seems minor.

### Step 3 — Classify each discrepancy
| Type | Description | Example |
|---|---|---|
| Factual Error | Wrong data | Wrong founding year, wrong city, wrong CEO name |
| Outdated Information | Previously true, now stale | Old product name, discontinued service still mentioned |
| Misattribution | Correct fact, wrong brand | Describes a competitor's product under this brand's name |
| Fabrication | No basis in reality | Service or award the brand has never had |
| Framing Distortion | Technically accurate but misleading | Technically correct but makes the brand sound less credible |

### Step 4 — Prioritize by harm
- **Critical**: Factual errors, fabrications, misattributions (risk of brand damage or legal issues).
- **Moderate**: Outdated information (risk of confusion or lost sales).
- **Minor**: Framing distortions (risk of suboptimal perception only).

### Step 5 — Verdict and remediation pathway
For each critical or moderate finding, the remediation is not a code fix — it's a **content strategy fix**:
- Ensure the true information is stated clearly, prominently, and early in the page's text.
- Add or update `Organization` schema with accurate `foundingDate`, `description`, and `sameAs` links.
- Seek to have accurate third-party sources (Wikipedia, industry press) describe the brand correctly, so LLMs have higher-confidence sources to train on.
