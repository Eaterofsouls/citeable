---
card_id: C056
stage: STAGE-11
automatability: Partial
check_name: "Entity Disambiguation"
claim_statement: "Extracting sameAs/@id links is scriptable, but resolving disambiguation issues (e.g., an LLM confusing your company with a similarly-named one) requires human investigation."
---

# C056 — Entity Disambiguation

## What AREOS Does Automatically
- Extracts `sameAs` and `@id` fields from all JSON-LD blocks.
- Checks whether `sameAs` targets are reachable (HTTP 200) and point to Wikipedia, Wikidata, Crunchbase, or LinkedIn.
- Flags when `sameAs` is missing entirely.

## What You Must Do Manually

### Step 1 — Check Wikidata
Go to [wikidata.org](https://www.wikidata.org) and search for the brand/entity name.

- Does a Wikidata entity exist for this brand?
- If yes, does the `sameAs` in the page's schema link to the correct Wikidata Q-identifier?
- If no Wikidata entity exists, that's a gap — consider if one should be created.

### Step 2 — Test LLM knowledge of the entity
Ask ChatGPT or Gemini: *"What does [Brand Name] do?"*

Read the response carefully:
- Is the description accurate?
- Does the model confuse this brand with another similarly-named entity?
- Does the model say "I'm not sure" or describe a completely different company?

### Step 3 — Investigate ambiguity sources
If the LLM is confused or incorrect, identify likely causes:
- Is there a more famous entity with the same name? (e.g., "Apollo" = NASA mission + many companies)
- Is the brand name a common dictionary word?
- Is there no Wikipedia/Wikidata anchor for the model to latch onto?

### Step 4 — Verdict
- LLM describes the correct entity accurately → **PASS**
- LLM hedges but gets it right → **WARN: entity could be stronger**
- LLM describes a different entity → **FAIL: disambiguation crisis**

### Remediation
- Add or correct `sameAs` links in schema to point to the canonical Wikidata/Wikipedia/LinkedIn identifiers.
- Consider creating a Wikipedia or Wikidata stub if the brand lacks one.
- Add an `About` page with clear, structured brand descriptor prose.
