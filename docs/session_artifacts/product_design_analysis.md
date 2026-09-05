# Citeable Hybrid Architecture — Product Design Analysis

## The Core Problem You're Seeing

Today, Citeable's entire knowledge impact runs through **5 claim IDs** (`C050`, `C051`, `C054`, `C057`, `C058`) mapped via 35 check codes. That's it. 217 claims sit in the database, but only 5 do any actual work. The user sees:

- A remediation card saying `[Claim ID: C050]` with `(high Confidence / internal-playbook)`
- A link to the Claims Browser showing a flat text statement with no evidence, no sources, no rationale

We've built a **202-record governed corpus** with full evidence chains, 115 cited sources, and structured GUIDANCE records. If we pipe this through the same 5-claim bottleneck, we've wasted 14 sessions of work.

---

## What the User Actually Sees Today (Product Audit)

### 1. Audit Studio (main page — `index.html`)

The user journey is:
1. Enter a domain → Run Audit
2. See automated findings as expandable cards
3. Each card shows: Title, Check Code, Severity, Description
4. At the bottom of each card: a **"View Governing Research Basis"** link that shows `[Claim ID: C050] (high Confidence / internal-playbook)` and a statement

**Problem:** Every crawler finding links to C050. Every schema finding links to C054. The "governing research basis" is the same 80-word statement regardless of whether the issue is a blocked GPTBot, a missing JSON-LD type, or a broken crawl-delay. There's no differentiation. The user gets zero insight into *why* the recommendation matters.

### 2. Claims Browser (`claims_browser.html`)

A full-featured page with:
- Search, filter by Phase/Status/Confidence/Type/Scope
- Grid of claim rows → click to open detail drawer
- Detail drawer shows: claim_id, statement, source_url (with iframe preview), stage, confidence, source tier
- "Propose Edit" modal for submitting claim changes
- Pinning system (per-analyst localStorage)
- Admin: "+ Add Claim" button

**Problem:** The Claims Browser shows the old flat `claims` table — no evidence chains, no source citations, no AEOG phase, no guidance structure. It's a spreadsheet view of 217 mostly-unused claims. After migration, this page becomes either the **most powerful feature in the product** or completely broken, depending on how we handle it.

### 3. Remediation Report (exported Markdown)

The export (`exportExecutiveReport()` in `studio.js`) produces:
```markdown
- **Governing Research Basis**: *Claim ID C050* (high Confidence / internal-playbook):
  "GPTBot is OpenAI's crawler for training..."
```

**Problem:** Every finding gets the same thin citation. No source URLs. No evidence quality. No rationale. No "why this matters." The report looks authoritative on the surface but is empty underneath.

### 4. LLM Synthesis Narrative

The 3-step pipeline receives `governing_claim_statement` — a single sentence from one of 5 claims — and tries to write a coherent remediation narrative from it.

**Problem:** The LLM has almost no substantive context. It's forced to hallucinate specifics or produce generic advice because the "knowledge" it receives is a single claim statement, not a chain of evidence.

### 5. Command Palette (Cmd+K)

Searches claims via API. Results link to Claims Browser.

**Problem:** After migration, this needs to search the `knowledge` table, not `claims`.

### 6. Documentation (`docs.html` → `internal.md`)

Extensive internal documentation covering all features, API endpoints, architecture.

**Problem:** All references to "claims", the claims table schema, the ingestion pipeline, and the knowledge architecture are outdated after migration.

---

## The Expanded Role of RAG

You're right that RAG only for novel findings is underuse. Here's why, and what it should actually do:

### Current Plan (Too Narrow)
```
Known check code → Deterministic lookup
Unknown check code → RAG fallback
```

### Better Design: RAG as Context Enrichment Layer

RAG should serve **three distinct functions**:

#### 1. Deterministic + RAG Enrichment (for KNOWN check codes)

Even when we have a deterministic GUIDANCE record for `CRAWLER_FULLY_BLOCKED`, the LLM would benefit from receiving **contextually related** knowledge that the deterministic map doesn't link. Example:

- Deterministic: `KT-124` (GUIDANCE: "Unblock AI Crawler") + `KT-033` (backing FACT)
- RAG enrichment: Also retrieve `KT-001` (Google-Extended is training-only), `KT-002` (crawler categories), `KT-004` (Perplexity stealth crawling, contested)

This gives the LLM richer context to write a genuinely insightful narrative, not just parrot the GUIDANCE record's action field.

**Implementation:** After deterministic resolution, run a "related knowledge" RAG query using the GUIDANCE statement as the query. Return top-3 above 0.70 threshold, tagged as `enrichment` (not `primary`). The LLM can weave these in, but they're optional context, not governing claims.

#### 2. Cross-Phase Intelligence (for remediation planning)

When multiple findings fire across different AEOG phases, RAG can find knowledge that connects them. Example: a site has both `CRAWLER_FULLY_BLOCKED` (AP-03) and `CITATION_NOT_OBSERVED` (AP-05). RAG could surface `KT-033` which explains *why* blocked crawlers lead to missing citations — creating a root-cause narrative instead of isolated recommendations.

**Implementation:** After all findings are resolved individually, run a "synthesis" RAG query using all finding descriptions concatenated. Return up to 5 records that bridge multiple findings.

#### 3. Novel Finding Fallback (existing design, unchanged)

Unknown check codes → semantic search → confidence gate → "insufficient knowledge" if nothing matches.

### Updated Architecture

```
                   check_code
                       │
            ┌──────────┴──────────┐
            │                     │
     KNOWN (in map)        UNKNOWN (not in map)
            │                     │
    Deterministic            RAG Primary
    GUIDANCE lookup          Search (≥0.82)
            │                     │
            ▼                     ▼
    ┌───────────────┐    ┌───────────────┐
    │ Primary       │    │ Best          │
    │ Resolution    │    │ Candidate     │
    │ (GUIDANCE +   │    │ or            │
    │  backing FACT)│    │ INSUFFICIENT  │
    └───────┬───────┘    └───────┬───────┘
            │                     │
            └────────┬────────────┘
                     │
              ┌──────▼──────┐
              │ RAG         │
              │ Enrichment  │
              │ (≥0.70,     │
              │  top-3)     │
              └──────┬──────┘
                     │
              ┌──────▼──────────┐
              │ Cross-Phase     │
              │ Intelligence    │
              │ (≥0.75, top-5,  │
              │  post-synthesis)│
              └──────┬──────────┘
                     │
              enriched_knowledge[]
```

---

## What Happens to the Claims Browser

The Claims Browser is already well-built (filters, drawer, search, pinning, edit proposals). It should **evolve** into a **Knowledge Explorer**, not die. Here's the migration:

### Before (current)
| Feature | Shows |
|---|---|
| Grid rows | claim_id, statement (truncated), status badge |
| Detail drawer | statement, source_url (iframe preview), stage, confidence, source tier |
| Filters | Phase, Status, Confidence, Type, Scope |
| Actions | Pin, Propose Edit |

### After (upgraded)

| Feature | Shows |
|---|---|
| Grid rows | kid, type badge (FACT/GUIDANCE/FINDING), statement, AEOG phase chips, confidence badge |
| Detail drawer | **Full evidence chain**: statement → evidence links → source citations with URLs, publisher, authority tier |
| Detail drawer | **For GUIDANCE records**: problem → action → rationale (linked to backing FACT) → code examples |
| Detail drawer | **Contested badge**: if contested, show contradiction text and both sides |
| Detail drawer | **Staleness indicator**: if review_due is past, show ⚠ |
| Detail drawer | **Related knowledge**: RAG-powered "Related Records" section |
| Filters | AEOG Phase (AP-01–AP-10), Status, Confidence, **Type** (FACT/GUIDANCE/FINDING/UNCERTAINTY), Scope |
| Actions | Pin, Propose Edit, **"Show Evidence Chain"** expand |
| New section | **Governance Dashboard**: open backlog items, stale records count, contested register |

### API Changes for Claims Browser

The `/api/v1/claims` endpoint currently queries the `claims` table. After migration:

| Approach | Effort | Risk |
|---|---|---|
| Keep old endpoint, add new `/api/v1/knowledge` | Low | Two parallel APIs to maintain |
| **Migrate `/api/v1/claims` to read from `knowledge` via view** | Medium | **Recommended** — backwards compatible |
| Add `/api/v1/knowledge` with full evidence/source joins | Medium | Best UX — new features need new data |

**Recommended**: Do both. The existing `/api/v1/claims` reads from the `claims` view (backwards compat). A new `/api/v1/knowledge/{kid}` endpoint returns the full record with evidence and sources joined. The Claims Browser JS calls the new endpoint when opening the detail drawer.

---

## Maximizing the 202-Record Corpus

### Problem: Only 5 claims do work today

| Old Claim | Check Codes Mapped | Records in New Corpus |
|---|---|---|
| C050 | 7 crawler codes | KT-001, KT-002, KT-003, KT-004, KT-033 + 8 GUIDANCE records |
| C051 | 5 llms.txt codes | KT-034, KT-035 + 6 GUIDANCE records |
| C054 | 6 schema codes | KT-006, KT-007 + 10 GUIDANCE records |
| C057 | 2 extractability codes | KT-041 + 3 GUIDANCE records |
| C058 | 2 extractability codes | KT-041 + 3 GUIDANCE records |

The new corpus has **42 active GUIDANCE records** mapped to **50 check codes**, each backed by specific FACT/FINDING records with real source citations. Instead of one C050 statement governing all crawler findings, each check code now gets its own specialized GUIDANCE with:
- A specific **problem** description
- A specific **action** (what to do)
- A specific **rationale** (kid → backing FACT with evidence)
- **Code examples** (actual robots.txt rules, JSON-LD snippets)
- **Source citations** with URLs (RFC 9309, Google docs, OpenAI docs)

### Where Knowledge Should Appear (New Touchpoints)

Today knowledge appears in **1 place** (the citation box in the remediation card). After migration, it should appear in **6 places**:

1. **Remediation Card Citation Box** — upgraded with evidence chain, source URL, rationale
2. **LLM Synthesis Narrative** — enriched context produces genuinely insightful text
3. **Knowledge Explorer** (née Claims Browser) — full evidence chains, related records
4. **Exported Report** — inline source citations with URLs, confidence ratings, contested warnings
5. **Cmd+K Palette** — searches across all 202 records, shows type badges
6. **Audit Studio Hero** — "202 Governed Knowledge Records" (not "217 claims")

### The Remediation Report Upgrade

The exported report should go from:

```markdown
### 1. Unblock AI Crawler in robots.txt [AUTO]
**Governing claim:** C050 (status: active) | confidence: high
**Evidence tier:** Knowledge Base Principle
⚠ A major AI crawler has a blanket 'Disallow: /' rule...
> 📎 **C050** — GPTBot is OpenAI's web crawler...
```

To:

```markdown
### 1. Unblock AI Crawler in robots.txt [AUTO]
**Knowledge Basis:** KT-124 (GUIDANCE) | Confidence: High
**Rationale:** KT-033 — "AI search crawlers (OAI-SearchBot, Claude-SearchBot)
  operate independently of training crawlers and cannot be blocked via robots.txt
  Disallow rules for GPTBot/ClaudeBot."
**Sources:**
  - [OpenAI Crawlers Documentation](https://openai.com/bot/) (T1: Official)
  - [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309) (T1: Standard)
**Code Example:**
  ```
  User-agent: GPTBot
  Allow: /
  ```
⚠ A major AI crawler has a blanket 'Disallow: /' rule...

> **Related Context:** KT-001 — Google-Extended is a training-data control
> token, not a crawler. It has zero impact on AI Overviews. (High confidence,
> Source: Google Search Central)
```

---

## Documentation Updates Needed

### `internal.md` — Major sections requiring update

| Section | Current | After |
|---|---|---|
| Claims table schema | Documents `claims` table columns | Must document `knowledge` table + evidence/sources/relationships |
| API table | Documents `/api/v1/claims` | Must add `/api/v1/knowledge/{kid}`, `/api/v1/kb/status`, `/api/v1/kb/reload` |
| Knowledge ingestion | Documents `ingest_claims.py` + `active_claims.json` | Must document `build_kb.py` + JSONL corpus |
| Claim types | "5 types: empirical, operational, policy, heuristic, outcome" | "5 types: FACT, STANDARD, FINDING, UNCERTAINTY, GUIDANCE" |
| Check code mappings | Documents `_CHECK_CODE_MAPPINGS` dict | Must document `kb_check_code_map` table + `check_code_to_knowledge_map.json` |
| LLM synthesis | Documents 3-step pipeline with thin context | Must document enriched context with evidence chains |
| Architecture diagram | Shows claims → synthesis flow | Must show Knowledge Router with deterministic + RAG paths |
| Claims Browser | Documents current flat view | Must document Knowledge Explorer with evidence chains |

### New documentation to create

| Document | Purpose |
|---|---|
| `areos/kb/README.md` | Developer onboarding for the knowledge layer |
| `context/GOVERNANCE_RULES.md` (copy from corpus) | How to add/modify knowledge records |
| `ARCHITECTURE_HANDOFF.md` (copy from corpus) | Check code mapping strategy |

---

## Implementation Plan Updates

Based on this analysis, the implementation plan needs these additions:

### Phase 2.5 — New `/api/v1/knowledge` Endpoints (after wiring engine)

```python
# New endpoints
GET  /api/v1/knowledge                    # List/search knowledge records
GET  /api/v1/knowledge/{kid}              # Full record with evidence + sources
GET  /api/v1/knowledge/{kid}/evidence     # Evidence chain for a record
GET  /api/v1/kb/status                    # Corpus version, counts, stale count
POST /api/v1/kb/reload                    # Rebuild from JSONL (admin-only)
GET  /api/v1/knowledge/search?q=...       # Semantic search (RAG query)
```

### Phase 3 — RAG Expanded (three tiers, not one)

1. **Primary Resolution** (novel findings, ≥0.82 threshold) — already planned
2. **Enrichment** (known findings, ≥0.70 threshold, top-3 related) — **NEW**
3. **Cross-Phase Intelligence** (all findings combined, ≥0.75, top-5) — **NEW**

### Phase 4.5 — Claims Browser → Knowledge Explorer (UI upgrade)

1. Update `app.js` to call `/api/v1/knowledge/{kid}` for the detail drawer
2. Add evidence chain rendering (EV → SRC with URLs)
3. Add type badges (FACT/GUIDANCE/FINDING chips)
4. Add AEOG phase chips
5. Add contested/stale indicators
6. Add "Related Records" section (RAG-powered)
7. Rename page title from "Live Claims Registry" to "Knowledge Explorer"
8. Update nav label from "Claims Browser" to "Knowledge Explorer"

### Phase 4.75 — Remediation Report Upgrade

1. Update `exportExecutiveReport()` to include source citations with URLs
2. Update `renderRecItems()` to show evidence tier and source citations in the card
3. Add rationale text from backing FACT/FINDING records
4. Add code examples from GUIDANCE records
5. Add contested/stale warnings inline

### Phase 6 — Documentation Pass

1. Update `internal.md` (all sections listed above)
2. Copy governance docs from corpus into `areos/kb/`
3. Update `external.md` if user-facing docs reference claims

---

## Summary of Decisions

| Question | Decision |
|---|---|
| RAG scope | **Three tiers**: primary (novel), enrichment (known), cross-phase (synthesis) |
| Claims Browser | **Evolves** into Knowledge Explorer with evidence chains, not deprecated |
| Claims API | Keep `/api/v1/claims` via view + add new `/api/v1/knowledge` endpoints |
| Report quality | **Major upgrade**: source citations, rationale, code examples, contested warnings |
| Documentation | Full update pass on `internal.md` + new `areos/kb/README.md` |
| Cmd+K | Searches `knowledge` table instead of `claims` |
| Hero stat | Changes from "217 claims" to "202 Knowledge Records" |
| MANUAL_REMEDIATION_TEXT | Add as GUIDANCE records in the corpus (single source of truth) |
