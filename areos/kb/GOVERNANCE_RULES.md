# GOVERNANCE RULES — Citeable Knowledge Corpus

These rules govern every research session. They exist because previous sessions
made specific errors when they were not explicit. Read them carefully.

## Source Authority Hierarchy

| Tier | Type | Examples | Use for |
|---|---|---|---|
| T1 | Official platform documentation | Google Search Central, OpenAI docs, RFC | Stated policy and specifications |
| T2 | Controlled independent research | Ahrefs studies, SSRN preprints with methodology | Observed behavior and causal claims |
| T3 | Reputable practitioner research | Search Engine Land, Cloudflare reports | Observed patterns; check COI |
| T4 | Vendor blog / marketing material | BrightEdge, SE Ranking blog posts | Product data; NOT efficacy claims |
| T5 | LLM synthesis / generated content | Claude answer, GPT-4 summary | Never independent evidence |

**Critical distinctions:**
- A T1 source is authoritative about its **own stated policy**, NOT about **observed behavior by others**
- A T4 vendor source may be accurate about its **own product data** but is suspect for **causal efficacy claims**
- T5 (LLM agreement) is NEVER independent evidence. Multi-model consensus is still T5.
- A URL existing does not validate the claim. You must verify the source content supports the claim.

## The Five Session 9 Errors — Never Repeat These

| Error Made | Correct Rule |
|---|---|
| "Queue is empty → knowledge is verified" | Queue empty = items were processed. Each must be individually resolved. |
| "Vendor states policy → behavior is confirmed" | Record as T4 stated policy; note any independent behavioral evidence |
| "No evidence found → proven false" | Write: "No evidence found to support X as of [date]" |
| "Correlation found → causation proven" | Write: "Correlation observed; controlled experiments [do/do not] support causal link" |
| "URL recovered → claim validated" | A valid URL is not validated evidence. Verify source content matches claim. |

## Knowledge Record Rules

### When to CREATE a new record
- The assertion is NOT represented by any existing record
- The assertion is ATOMIC (one thing — no "and" joining two independent facts)
- At least one T1–T3 source supports it
- It is relevant to Citeable's audit scope

### When to ENRICH an existing record
- New evidence supports or refines the existing assertion
- A better source is found
- Temporal information changes (a check was deprecated on a specific date)
- Confidence changes — only if new evidence justifies it

### When to SPLIT a record
- Statement uses "and" to assert two independent facts
- Statement contains both a fact and a recommendation
- Statement conflates correlation and causation

### When to MARK a contradiction
- Two active records make conflicting claims about the same subject
- A new source contradicts an existing record
- Official policy contradicts observed behavior (preserve BOTH sides)

### When to DEPRECATE
- A check code was definitively shown to be conceptually wrong
- A platform changed its policy and the old guidance is now misleading

### When to ARCHIVE
- A record is superseded by a newer, more precise one
- A duplicate is merged into a stronger record

### When to REJECT (do not create)
- Source is T5 only (LLM answer with no citable backing)
- Assertion is too broad to be actionable
- Duplicates an existing concept with different wording

## Confidence Rules

| confidence | Meaning |
|---|---|
| high | Strong T1 or T2 evidence; no material contradictions |
| medium | T2–T3 evidence; OR T1 but with unresolved complication |
| low | T3–T4 only; OR methodology concerns; OR contested |

**Never change confidence without adding new evidence. Never change confidence because one newer source was found.**

## Excerpt Rules

Every source added must have `excerpt_type` set:
- `verbatim` — exact copy of text from source
- `paraphrase` — accurate rewording, labeled as such
- `interpretive-summary` — your synthesis of the source content

Do not allow interpretive summaries to masquerade as verbatim quotes.

## Atomic Statement Rule

A knowledge record must assert exactly ONE thing.

BAD: "PerplexityBot respects robots.txt but Perplexity-User ignores it and there have been bypass reports."
GOOD (record 1): "PerplexityBot officially claims robots.txt compliance for indexing purposes."
GOOD (record 2): "Perplexity-User (user-triggered fetches) is documented by Perplexity to generally ignore robots.txt."
GOOD (record 3): "Cloudflare (August 2025) documented proxy-based bypass behavior inconsistent with PerplexityBot's stated policy."

## Temporal Rules

Every record must have:
- `provenance.last_verified_at` — when was this last checked
- `provenance.review_due` — when should it next be checked

When updating temporal information:
- Preserve old date in `history`
- Update `last_verified_at` to today
- Record what changed and when in `history`
- Do NOT present historical facts as current facts

## Contested Knowledge Rule

If two credible sources disagree, BOTH sides must be preserved.
The `status` becomes `contested`.
The `contradiction` field names the disagreement.
Neither side is silently dropped.
The architecture will present both sides to the user.

## Change Logging Rule

Every corpus change — no matter how small — must create a `changelog.jsonl` entry with:
- `at`: today's date
- `session`: "session_NN"
- `op`: the operation type
- `kid`: the affected record ID (or null for metadata changes)
- `note`: what changed and why
