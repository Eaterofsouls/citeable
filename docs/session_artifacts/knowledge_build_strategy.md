# CITEABLE — MULTI-PHASE KNOWLEDGE BUILD & TARGET ARCHITECTURE

**Version:** 1.0  
**Date:** 2026-08-28  
**Status:** Strategy — Not Yet Executed  
**Author:** Lead Knowledge Architect  
**Supersedes:** Stage 3A ideal architecture, Stage 3B red-team critique (provisional proposals only)

---

## 1. Current Situation

Citeable (formerly AREOS) has accumulated knowledge across four partially-disconnected representations:

| Layer | Contents | Status |
|---|---|---|
| `AEO_GEO_Master_Knowledge_Base_v2.md` | 117 claims: 57 Study A (ranking factors, crawlers, schema, tools, legal) + 60 Study B (audit automatability) | Draft; never formally verified |
| `areos.db` → `claims` table | 213 active rows: 117 MKB-origin + 96 C200–C324 corpus_handbook explainers; 4 deprecated outcome logs | In production; source URLs backfilled; check_code wiring only covers 12 unique claim IDs |
| `synthesis_engine.py` REMEDIATION_TEXT | 36 check codes × (title + description) | In production; authoritative for what users actually see |
| `audit_orchestrator.py` ACTION_SNIPPETS | 12 check codes × action text | In production; seen by LLM |

**Critical defects confirmed by Phase 3 research:**
- `GPTBOT_MISSING` and `GOOGLE_EXTENDED_MISSING` are invalid citation-readiness checks (confirmed by T1 official documentation)
- `LLMS_TXT_MISSING` is scored −6 access points, but three empirical studies (137k, 300k, 10 sites) show zero citation effect from llms.txt
- `PRIORITY_SCORES` (1–13) are heuristic business policy, not evidence-backed rankings
- `sources` table has 0 rows despite 107 named sources in MKB
- Schema → AI citation frequency: best controlled studies lean null-to-negative; vendor statistics have no methodology

**Useful knowledge currently available:** ~44 well-evidenced, ~67 likely useful, ~82 upper bound.

---

## 2. Objective

Produce a **rich, verified, deduplicated, structured, provenance-preserving knowledge corpus** that:

1. Can be ingested into any future Citeable architecture without re-doing the research
2. Supports both deterministic lookup (known checks → known knowledge) and semantic retrieval (novel findings → candidate knowledge)
3. Explicitly represents uncertainty, contradiction, and evidence quality
4. Preserves the full research lineage so future sessions can extend without re-deriving context
5. Is maintainable by browser-based LLM sessions working from a ZIP

The objective is **not** to clean 213 claims. It is to build a corpus that makes the current 213 claims largely irrelevant as a primary reference — the corpus should supersede them.

---

## 3. Target Knowledge Model

The working corpus must represent everything needed to answer:

> *"For this audit finding, what do we know, how confident are we, why do we believe it, what should we tell the user, and what should they do?"*

### 3.1 Concept Types

The corpus uses five canonical concept types. These are mutually exclusive at the record level.

| Type | Meaning | Examples |
|---|---|---|
| `FACT` | An empirically documented or officially stated truth about how AI search systems work | "Google-Extended controls model training only, not AI Overviews" |
| `STANDARD` | A published protocol, specification, or platform requirement | "JSON-LD must be syntactically valid for rich results" |
| `FINDING` | A research result with disclosed methodology | "Ahrefs 2026: generic schema null-to-negative for AI citation" |
| `UNCERTAINTY` | A documented unknown, absence, or absence of official statement | "Citation selection algorithm undisclosed by all platforms" |
| `GUIDANCE` | A recommended action or implementation pattern for a specific check/finding | "How to correctly allow OAI-SearchBot in robots.txt" |

### 3.2 What Each Type Does Not Replace

- `FACT` is not `GUIDANCE` — knowing that Google-Extended doesn't affect AI Overviews is different from knowing what to tell a user
- `FINDING` is not `FACT` — controlled studies inform; they do not establish ground truth
- `UNCERTAINTY` is not absence of a concept — it is a positively recorded gap in knowledge
- `GUIDANCE` should cite the `FACT` or `FINDING` that justifies it

### 3.3 Scope

Every record has one of three scopes:

| Scope | Meaning |
|---|---|
| `crawl-access` | Crawler behavior, robots.txt, rendering, discovery, sitemaps |
| `content-quality` | Schema, extractability, content structure, entity disambiguation |
| `authority-citation` | Brand authority, domain trust, citation measurement, legal/ToS |

---

## 4. Working Data Format

### 4.1 Evaluation of Candidates

| Format | Pros | Cons | Verdict |
|---|---|---|---|
| **SQLite** | Rich queries, relationships, constraints | Requires tooling to inspect; binary diff impossible; hard to hand-edit | ❌ Not suitable for LLM sessions |
| **JSON (single file)** | Human-readable, well-understood | Hard to append incrementally; full file re-writes on update; merge conflicts across sessions | ❌ Too fragile for multi-session |
| **CSV + relationship tables** | Spreadsheet-friendly | Cannot represent nested evidence; relationships awkward; no provenance narrative | ❌ Insufficient richness |
| **YAML** | Human-readable, supports nesting | Large files become unwieldy; tooling less universal | ⚠️ Viable but verbose |
| **JSONL (JSON Lines)** | One record per line; appendable; diff-friendly; each record self-contained; parseable line-by-line | Requires sorted/indexed lookup for deduplication | ✅ **Recommended** |
| **Markdown + machine data** | Excellent for human review; LLMs read it well | Not programmatically queryable without parsing | ✅ For summaries only |

### 4.2 Recommended Format: JSONL + Supporting Files

**Primary corpus:** `knowledge.jsonl` — one knowledge record per line, append-safe, diff-friendly  
**Source registry:** `sources.jsonl` — one source record per line, deduplicated  
**Evidence links:** `evidence.jsonl` — links knowledge IDs to source IDs with support relationship  
**Relationship map:** `relationships.jsonl` — concept-to-concept links  
**AEOG map:** `aeog_coverage.jsonl` — per-phase coverage records  
**Session log:** `research_log.md` — human-readable narrative of changes per session  
**Change log:** `changelog.jsonl` — machine-readable record of all modifications  
**Open queue:** `research_queue.jsonl` — items awaiting verification or research  
**Data dictionary:** `DATA_DICTIONARY.md` — field definitions (never changes unless schema evolves)  
**README:** `README.md` — what this ZIP is, what session just ran, what next session should do

**Why JSONL beats single JSON:** Each session appends lines rather than rewriting the entire file. A new session can scan `knowledge.jsonl` line-by-line to check for duplicates before adding. Git-style diffs are human-readable. A line is never bigger than one record.

**Why not SQLite:** A browser-based Sonnet session cannot reliably read binary SQLite files, cannot run queries, and cannot produce a modified binary file without tooling. JSONL can be read, searched, and written with only text operations.

---

## 5. Canonical Record Structure

### 5.1 Full Knowledge Record Schema

```jsonc
{
  // ─── Identity ───────────────────────────────────────────────────────────────
  "kid":           "KT-001",           // Stable ID. Format: KT-NNN. Never reuse.
  "type":          "FACT",             // FACT | STANDARD | FINDING | UNCERTAINTY | GUIDANCE
  "scope":         "crawl-access",     // crawl-access | content-quality | authority-citation
  
  // ─── Core Content ────────────────────────────────────────────────────────────
  "statement": "Google-Extended is a robots.txt product token that controls whether Google may use site content for Gemini and Vertex AI model training. It has zero impact on Google Search rankings or AI Overview appearances.",
  
  // Context makes the statement interpretable without further lookup
  "context":  "Publishers sometimes block Google-Extended believing it will prevent inclusion in AI Overviews. This is incorrect — AI Overviews are governed by Googlebot and standard meta directives.",
  
  // ─── AEOG Coverage ───────────────────────────────────────────────────────────
  "aeog_phases": ["AP-03"],            // Which AP phases this knowledge addresses
  "stage_ids":   ["STAGE-02"],         // Which technical pipeline stages (if applicable)
  
  // ─── Check Code Relationships ────────────────────────────────────────────────
  "check_links": [
    {
      "check_code":    "GOOGLE_EXTENDED_MISSING",
      "relationship":  "contradicts",     // supports | contradicts | qualifies | informs
      "note":          "This check presents Google-Extended as a citation readiness signal, which official documentation directly contradicts."
    }
  ],
  
  // ─── Epistemic Status ─────────────────────────────────────────────────────────
  "status":     "active",              // active | deprecated | superseded | contested | archived
  "confidence": "high",                // high | medium | low
  "support":    "strong",             // strong | partial | weak | contested | absent
  
  // Evidence IDs reference the evidence.jsonl file
  "evidence_ids": ["EV-001", "EV-002"],
  
  // Explicit uncertainty note (required for anything not "high + strong")
  "uncertainty": null,                 // null if clear; else prose description of the gap
  
  // Contradiction note (required if contradicted by other evidence)
  "contradiction": null,               // null if none; else prose + kid of contradicting concept
  
  // ─── Remediation (GUIDANCE type only, or link to a GUIDANCE record) ───────────
  "remediation_link": null,            // kid of the GUIDANCE record that addresses this fact
  
  // If this IS a GUIDANCE record, these apply:
  "guidance": null,                    // null unless type == GUIDANCE
  // {
  //   "problem":        "...",
  //   "action":         "...",
  //   "rationale":      "kid of the FACT/FINDING that justifies this action",
  //   "tech_context":   ["robots.txt", "meta-tags"],
  //   "examples":       ["User-agent: Google-Extended\nAllow: /"],
  //   "check_codes":    ["GOOGLE_EXTENDED_MISSING"]
  // }
  
  // ─── Relationships ────────────────────────────────────────────────────────────
  "relationships": [
    {
      "target_kid":    "KT-002",
      "rel_type":      "related",   // related | supersedes | superseded_by | part_of | contradicts | instantiates
      "note":          "KT-002 covers the paired concept of Googlebot for search indexing"
    }
  ],
  
  // ─── Legacy Mapping ───────────────────────────────────────────────────────────
  // Maps to prior representations — preserved for lineage, not canonical
  "legacy_ids": ["CLM-026", "C201"],   // Prior claim IDs this concept replaces or derives from
  
  // ─── Provenance ───────────────────────────────────────────────────────────────
  "provenance": {
    "origin":         "MKB_Study_A",   // Origin corpus: MKB_Study_A | MKB_Study_B | C200_corpus | python_remediation | phase3_research | session_N_research
    "created_at":     "2026-08-28",
    "created_by":     "session_1",     // session_1 | session_2 | session_3 | session_4
    "last_verified_at": "2026-08-28",
    "last_verified_by": "phase3_web_research",
    "review_due":     "2027-02-28"    // 6 months for active facts; 12 months for standards
  },
  
  // ─── Change History ───────────────────────────────────────────────────────────
  "history": [
    {
      "at":     "2026-08-28",
      "by":     "session_1",
      "change": "Created from CLM-026 MKB entry",
      "prior_statement": null
    }
  ]
}
```

### 5.2 Field Definitions

| Field | Why it exists | Who populates | Canonical? | Mutable? | Provenance |
|---|---|---|---|---|---|
| `kid` | Stable cross-session reference ID | Session 1 assigns; never changes | Yes | No — immutable | — |
| `type` | Prevents conflation of assertions with guidance | Assigning session | Yes | Session 2+ may correct | History entry |
| `scope` | Enables AEOG filtering and coverage analysis | Assigning session | Yes | Correctable | History entry |
| `statement` | The single falsifiable assertion | Assigning session | Yes | Updatable with history | Full history preserved |
| `context` | Makes the statement interpretable without further lookup | Assigning session | Yes | Updatable | History entry |
| `aeog_phases` | Maps knowledge to audit lifecycle | Assigning session | Derived | Updatable | — |
| `stage_ids` | Maps to technical pipeline taxonomy | Assigning session | Derived | Updatable | — |
| `check_links` | Connects knowledge to runtime check codes | Session 1 (existing); later sessions | Derived | Extendable | — |
| `status` | Lifecycle state | Any session | Yes | Updatable with history | History entry |
| `confidence` | Epistemic confidence | Assigning session | Yes | Updatable | History entry |
| `support` | Evidence support level | Assigning/verifying session | Yes | Updatable | History entry |
| `evidence_ids` | Links to source evidence | Any session | Derived | Extendable | — |
| `uncertainty` | Explicit gap documentation | Any session | Yes | Required when not "high" | — |
| `contradiction` | Conflict record | Any session | Yes | Required when conflicted | — |
| `remediation_link` | Links fact to its guidance record | Session 2+ | Derived | Extendable | — |
| `guidance` | Remediation content (GUIDANCE type only) | Session 2+ | Yes | Updatable with history | History entry |
| `relationships` | Inter-concept connections | Any session | Derived | Extendable | — |
| `legacy_ids` | Prior DB/MKB claim IDs | Session 1 | Lineage only | Append-only | — |
| `provenance` | Origin and verification dates | Session assigning/verifying | Yes | Updatable | Embedded |
| `history` | Full change log | Every modifying session | Yes | Append-only | Embedded |

---

## 6. Source & Evidence Model

### 6.1 Source Record (sources.jsonl)

```jsonc
{
  "sid":         "SRC-001",
  "url":         "https://developers.google.com/search/docs/crawling-indexing/google-extended",
  "title":       "Google-Extended - Search Central Documentation",
  "publisher":   "Google LLC",
  "type":        "official-platform-docs",     // See type taxonomy below
  "authority":   "T1",                          // T1-T4 (see below)
  "pub_date":    "2024-09-01",                  // Best known publication/last-modified date
  "access_date": "2026-08-28",
  "section":     "Overview",
  "excerpt":     "Google-Extended does not impact a site's inclusion or ranking in Google Search, nor does it control AI Overviews.",
  "notes":       "This is the canonical primary doc for Google-Extended behavior. URL stable as of access date.",
  "archived_url": null                          // Wayback Machine URL if primary URL volatile
}
```

### 6.2 Evidence Link Record (evidence.jsonl)

```jsonc
{
  "eid":          "EV-001",
  "kid":          "KT-001",             // Knowledge record this supports/contradicts
  "sid":          "SRC-001",            // Source providing the evidence
  "relationship": "supports",           // supports | contradicts | qualifies | contextualizes
  "weight":       "primary",            // primary | corroborating | contextual
  "note":         "Direct quote from official documentation explicitly stating Google-Extended has no AI Overview impact"
}
```

### 6.3 Source Type Taxonomy

| Type | Description | Examples |
|---|---|---|
| `official-platform-docs` | Platform-published documentation | Google Search Central, OpenAI Platform Docs, Anthropic Support |
| `rfc-standard` | IETF RFC or formal standard | RFC 9309 (robots.txt), RFC 9110 (HTTP semantics) |
| `eu-regulation` | EU legislative/regulatory text | DSM Directive 2019/790 |
| `court-document` | Court ruling or filing | *Google v. SerpApi* dismissal order |
| `primary-research` | Controlled study with disclosed methodology and sample size | Ahrefs 2026 schema study (n=1,885) |
| `preprint` | Self-published research with COI disclosure | Fischman SSRN study |
| `meta-analysis` | Synthesis of multiple studies with disclosed methodology | Zyppy 54-study meta-analysis |
| `practitioner-research` | Third-party empirical analysis with methodology | Wired PerplexityBot investigation |
| `practitioner-advisory` | Practitioner guidance with stated reasoning | Mark Williams-Cook / Candour probe test |
| `api-specification` | API reference docs | Gemini API Additional Terms, Perplexity Sonar API docs |
| `vendor-blog` | Vendor-produced content without methodology | BrightEdge, SE Ranking marketing content |
| `community-spec` | Community-maintained informal spec | llmstxt.org |

### 6.4 Authority Tiers

| Tier | Meaning | Can become canonical? |
|---|---|---|
| **T1** | Primary official source (platform docs, RFC, regulation, court document) | Yes — strongest basis |
| **T2** | Controlled study with disclosed methodology and sample size | Yes — with study notes |
| **T3** | Practitioner research with stated methodology; corroborated empirical observation | Yes — with qualification |
| **T4** | Vendor marketing, single-source claims, speculative | No — must not be promoted to canonical |

---

## 7. Knowledge Relationship Model

Only relationships that serve a functional purpose are defined.

| Relationship | Direction | Meaning | When to use |
|---|---|---|---|
| `supersedes` | A → B | A replaces B; B is archived | New evidence changes the understanding |
| `superseded_by` | A → B | A is replaced by B | Inverse; symmetric |
| `contradicts` | A ↔ B | A and B cannot both be fully true | Conflicting evidence or statements |
| `qualifies` | A → B | A limits or constrains B's applicability | B is true in general; A adds a scope constraint |
| `related` | A ↔ B | A and B cover the same domain area | Navigational — helps readers find adjacent knowledge |
| `part_of` | A → B | A is a sub-aspect of the broader concept B | Decomposition |
| `instantiates` | A → B | A is a specific example of the general principle B | Concrete → abstract |
| `check_contradicts` | knowledge → check_code | This knowledge directly contradicts the premise of a check code | Used to flag invalid checks |
| `check_supports` | knowledge → check_code | This knowledge justifies the existence of a check code | Used to trace rationale |
| `justifies_guidance` | fact/finding → guidance | This fact/finding is the evidential basis for this guidance record | Provenance for recommendations |

**Do not create relationships for elegance.** Create them when they will be used in retrieval, deduplication, or audit.

---

## 8. AEOG Coverage Model

### 8.1 Coverage Record (aeog_coverage.jsonl)

```jsonc
{
  "phase":           "AP-03",
  "name":            "Content Extractability & Crawler Access",
  "kid_count":       18,
  "strong_count":    12,              // confidence=high AND support=strong
  "qualified_count": 4,               // medium confidence or partial support
  "contested_count": 1,
  "gap_count":       1,               // known gaps in this phase
  "check_codes":     ["CRAWLER_FULLY_BLOCKED", "OAI_SEARCHBOT_ALLOWED", ...],
  "gaps": [
    {
      "gap_id":      "GAP-03",
      "description": "Perplexity-User officially ignores robots.txt — no GUIDANCE record yet"
    }
  ],
  "last_updated":    "2026-08-28"
}
```

### 8.2 Coverage update rule

Every time a knowledge record is added or modified, the session must update the corresponding AEOG coverage record. The coverage record is a derived aggregate — never manually curated.

---

## 9. Research Source Policy

### 9.1 Source Hierarchy

**Tier 1 — Use as primary evidence basis:**
- Official platform documentation (Google Search Central, OpenAI Platform, Anthropic Support, Perplexity Docs)
- IETF RFCs and W3C standards
- EU/national legislation and court rulings

**Tier 2 — Use as supporting evidence, document methodology:**
- Controlled studies with disclosed sample size, control group, and statistical methodology
- Meta-analyses with disclosed study selection criteria
- Requires: name of study, n=, methodology note, COI disclosure

**Tier 3 — Use as corroboration, never as sole evidence for a canonical claim:**
- Practitioner research with stated methodology (not just claimed authority)
- Empirical observations with independent corroboration (e.g., Wired + Cloudflare data)
- Named practitioner statements with traceable source (e.g., Fabrice Canel at SMX Munich)
- Requires: source name, date, corroboration count

**Tier 4 — Do NOT use as evidence for canonical knowledge:**
- Vendor blog statistics without disclosed methodology
- Single-source uncorroborated claims from vendor marketing
- LLM-generated summaries or consensus statements
- "Industry practitioners generally agree" without named sources and dates

### 9.2 Hard Rules

1. **LLM consensus is never evidence.** Multiple LLMs agreeing does not constitute a primary source. It may indicate a hypothesis worth investigating.
2. **Vendor statistics without methodology are never canonical.** "X% uplift" claims from vendors who sell the solution are excluded unless independently verified.
3. **Absence of documentation is recordable as `UNCERTAINTY`.** "No platform has officially documented that llms.txt affects citations" is a valid finding.
4. **A claim may be contested without being resolved.** Preserve both sides with their evidence.
5. **Do not promote a claim from lower tier because it is widely repeated.** Repetition is not corroboration.

---

## 10. Deduplication / Update Rules

### 10.1 Decision Flow

Every new piece of knowledge discovered in a research session must go through this exact flow before being written:

```
NEW DISCOVERY
    ↓
SEARCH knowledge.jsonl for matching concept
    ↓
MATCH? (exact same underlying assertion)
    ├── YES → ENRICH: add evidence_ids, update confidence, log history entry
    └── NO → Continue
         ↓
PARTIAL MATCH? (same domain, different scope or specificity)
    ├── YES → Decide: QUALIFY, SPLIT, or RELATE
    └── NO → CREATE new knowledge record
```

### 10.2 Rules by Operation

**ADD** — Create a new `kid` when:
- No existing concept covers the same falsifiable assertion
- The concept has at least one piece of T1-T3 evidence attached
- The concept is useful for at least one AEOG phase or check code

**UPDATE** — Modify an existing record (with history entry) when:
- A better source for the same claim is found (update `sources`, add to `evidence_ids`, log the prior source in history)
- The statement wording can be made more precise without changing the meaning
- A new check_link is discovered
- Confidence/support level should change based on new evidence

**MERGE** — Collapse two records into one when:
- Both express the same underlying assertion (same scope, same platform, same fact)
- Neither has unique evidence that would be lost
- Surviving record inherits all `evidence_ids` and `legacy_ids`

**SPLIT** — Create two records from one when:
- A single record conflates two distinguishable assertions (different scope, different platform, different evidence)
- Example: "Schema aids AI" → split into "Schema aids rich results" (STANDARD) + "Schema aids citation frequency" (FINDING, contested)

**SUPERSEDE** — Mark old record `superseded`, create new record when:
- New evidence substantially changes the meaning (not just wording)
- Old record is linked via `superseded_by` relationship
- Old record preserved in `archived` status — never deleted

**CONTEST** — Add a `contradiction` field and create a contradicting evidence link when:
- Two T1-T3 sources disagree on the same factual question
- Do NOT resolve the contradiction by picking a side; document both with their evidence
- Example: PerplexityBot's official claim vs. observed proxy bypass behavior

**REJECT** — Do not write to corpus when:
- Evidence is only T4 (vendor marketing, LLM consensus, uncorroborated single source)
- The concept is already represented by an existing record
- The concept is not useful for any Citeable AEOG phase or check

**ARCHIVE** — Set status to `archived` when:
- Knowledge is historically accurate but no longer current (e.g., superseded platform behavior)
- Knowledge is process/meta-knowledge (e.g., build log notes from MKB construction)
- Preserve: never delete archived records; they document the lineage

### 10.3 Matching Heuristic

Two records express the same concept if:
1. They refer to the same platform behavior, technical standard, or empirical finding
2. They apply to the same scope (crawl-access / content-quality / authority-citation)
3. The difference in phrasing does not represent a materially different assertion
4. A single future query would retrieve both for the same question

If in doubt: **create a `related` relationship rather than merging.** Merging destroys lineage; relating preserves it.

---

## 11. Versioning / History

### 11.1 Knowledge Record History

Every knowledge record contains an embedded `history` array. Each modification appends an entry:

```jsonc
{
  "at":     "2026-08-28",
  "by":     "session_2",
  "change": "Updated source from CLM-023 URL to confirmed canonical https://platform.openai.com/docs/bots. Prior URL was developers.openai.com/api/docs/bots (migrated).",
  "prior_statement": null   // Include only if the statement itself changed
}
```

### 11.2 Changelog File (changelog.jsonl)

Append-only. One line per modification event across the entire corpus:

```jsonc
{"at": "2026-08-28", "session": "session_1", "op": "CREATE", "kid": "KT-001", "note": "Initial ingestion from CLM-026"}
{"at": "2026-08-28", "session": "session_2", "op": "UPDATE", "kid": "KT-001", "field": "evidence_ids", "note": "Added EV-042 (Google-Extended docs direct access)"}
```

### 11.3 Temporal Knowledge Rules

- Every `FACT` and `STANDARD` record has `review_due` set to 6 months from `last_verified_at`
- Every `FINDING` has `review_due` set to 12 months (research findings change slowly)
- Every `UNCERTAINTY` has `review_due` set to 3 months (platform behavior may be documented)
- The `research_queue.jsonl` is the primary tracking mechanism for overdue reviews
- When a fact is superseded, the new record carries forward the `aeog_phases`, `check_links`, and `legacy_ids` of the old record

---

## 12. FIRST ZIP SPECIFICATION

The first ZIP is assembled from existing project files. Do not include everything — include what Session 1 needs to do its job.

### 12.1 Include

| File | Purpose | Status |
|---|---|---|
| `AEO_GEO_Master_Knowledge_Base_v2.md` | Primary source of MKB Study A + Study B knowledge | Raw input; authoritative for lineage |
| `active_claims.json` (from AREOS_Flagship_Complete_Build.zip/BUILD/) | All 213 claims with IDs, statements, source URLs | Raw input; authoritative for current claim IDs |
| `synthesis_engine.py` (REMEDIATION_TEXT dict, lines 200–310) | All 36 check code remediation texts | Raw input; preserve as-is into GUIDANCE records |
| `audit_orchestrator.py` (ACTION_SNIPPETS dict) | 12 action snippets | Raw input; supplement GUIDANCE records |
| `findings_to_claims.py` (CHECK_CODE_TO_CLAIM_IDS dict) | 36 check code → claim ID mappings | Raw input; used to build check_links |
| `web_verification_report.md` (Phase 3) | Verification status of all major clusters | Authoritative for confidence/support levels and Phase 3 findings |
| `knowledge_reconciliation_freeze.md` (Phase 2.5) | Taxonomy freeze: 88 concept estimate, AP taxonomy, STAGE taxonomy | Authoritative for AEOG mapping |
| `DATA_DICTIONARY.md` (this document, §5) | Field definitions for the working corpus | Canonical reference |
| `README.md` (generated) | What is in this ZIP; Session 1 instructions | Navigation |

### 12.2 Do Not Include

| File | Why excluded |
|---|---|
| `areos.db` (SQLite binary) | Binary; unreadable by LLM; JSONL corpus replaces it |
| `knowledge_census.md`, `knowledge_architecture.md` | Historical research; superseded by `web_verification_report.md` |
| `ideal_knowledge_architecture.md`, `redteam_architecture.md` | Provisional; superseded by this document |
| All ZIP archives | Too large; processed content already extracted |
| All Python auditor code (except the three dict files above) | Implementation detail; not knowledge |
| `issues_stage_0X.json` files | STAGE taxonomy already documented in `knowledge_reconciliation_freeze.md` |
| `GOVERNANCE_SPEC.md`, `INGESTION_SPEC.md` | DB governance for the current system; Session 1 does not need to re-implement |
| `outcome_logger.py`, `outcomes.py` | Deprecated |
| Any UI files | Irrelevant to knowledge building |

### 12.3 Generated Files (Session 1 must create these)

| File | Created by |
|---|---|
| `knowledge.jsonl` | Session 1 |
| `sources.jsonl` | Session 1 |
| `evidence.jsonl` | Session 1 |
| `relationships.jsonl` | Session 1 |
| `aeog_coverage.jsonl` | Session 1 |
| `research_log.md` | Session 1 |
| `changelog.jsonl` | Session 1 |
| `research_queue.jsonl` | Session 1 |
| `DATA_DICTIONARY.md` | Included in first ZIP |

---

## 13. SESSION 1 — EXECUTION PLAN

### Objective
Ingest all existing Citeable knowledge into the structured JSONL corpus. Map every existing claim and remediation text to a structured record. Identify duplicates, gaps, and weak provenance.

### Input ZIP Contents
- `AEO_GEO_Master_Knowledge_Base_v2.md`
- `active_claims.json`
- `synthesis_engine.py` (REMEDIATION_TEXT)
- `audit_orchestrator.py` (ACTION_SNIPPETS)
- `findings_to_claims.py` (CHECK_CODE_TO_CLAIM_IDS)
- `web_verification_report.md`
- `knowledge_reconciliation_freeze.md`
- `DATA_DICTIONARY.md`

---

### SESSION 1 PROMPT (paste directly into browser Sonnet)

```
You are the knowledge architect for Citeable (formerly AREOS), an AI search citation audit tool.

═══════════════════════════════════════════════════════════
WHAT CITEABLE IS
═══════════════════════════════════════════════════════════
Citeable audits websites for AI search citation readiness. It runs technical checks (crawler access, schema validity, content extractability, authority, citation measurement), maps each finding to a check code, and provides evidence-backed remediation guidance.

The tool has accumulated knowledge across multiple representations that need to be unified into a single structured corpus.

═══════════════════════════════════════════════════════════
WHAT THIS ZIP CONTAINS
═══════════════════════════════════════════════════════════
1. AEO_GEO_Master_Knowledge_Base_v2.md — 117 claims from LLM synthesis research (Study A + Study B). Draft; never formally verified. This is your primary raw input.
2. active_claims.json — All 213 current database claims with IDs, statements, source URLs. 117 from MKB + 96 C200-C324 technical explainers.
3. synthesis_engine.py — Contains REMEDIATION_TEXT dict (36 check codes × title + description) and PRIORITY_SCORES. This is what users currently see.
4. audit_orchestrator.py — Contains ACTION_SNIPPETS (12 check codes × action text). This is what the LLM receives.
5. findings_to_claims.py — Contains CHECK_CODE_TO_CLAIM_IDS (36 check codes → claim IDs). This is the current wiring.
6. web_verification_report.md — Phase 3 research results. Contains: verification status for all major knowledge clusters, critical findings about invalid check codes, 19 KT-NNN "Knowledge Truth" records that are the current best understanding.
7. knowledge_reconciliation_freeze.md — Taxonomy: AP-01 through AP-10 phases, STAGE-01 through STAGE-22 pipeline stages, 88-concept estimate.
8. DATA_DICTIONARY.md — Full field definitions for the JSONL corpus you will create.

═══════════════════════════════════════════════════════════
WHAT HAS ALREADY BEEN DONE (DO NOT REDO)
═══════════════════════════════════════════════════════════
- Phase 0: Knowledge census complete
- Phase 2.5: Taxonomy freeze complete; 88 concept estimate established
- Phase 3: Web verification complete; KT-01 through KT-19 represent current verified understanding
- Critical findings confirmed: GPTBOT_MISSING and GOOGLE_EXTENDED_MISSING check codes are invalid; LLMS_TXT_MISSING has no empirical basis as a citation signal; PRIORITY_SCORES are heuristic only

═══════════════════════════════════════════════════════════
YOUR JOB IN THIS SESSION
═══════════════════════════════════════════════════════════
Create the structured JSONL working corpus from all existing material. You are NOT doing web research. You are structuring what already exists.

STEP 1: Read DATA_DICTIONARY.md in full before writing anything.

STEP 2: Create sources.jsonl
- For every named source in the MKB (there are ~107) and every source_url in active_claims.json, create one source record (SRC-NNN).
- Deduplicate: same URL = same record.
- Use source type taxonomy from DATA_DICTIONARY.md.
- Where source URLs are missing, create the record with url=null and note the gap.

STEP 3: Create knowledge.jsonl
Process knowledge in this order:
  a) Start with the 19 KT-NNN records from web_verification_report.md Section 16 (Master Knowledge Truth Set). These are your highest-confidence starting points. Create KT-001 through KT-019 first.
  b) Process remaining Study A claims (CLM-001 to CLM-056) from the MKB. For each, check if it is already represented by KT-001 to KT-019. If yes: add legacy_id and skip. If no: create a new KT-NNN record.
  c) Process Study B claims (C001-C092, M001-M006). These are audit automatability ratings — create FACT records for the ones that describe pipeline-stage automatability. Archive M001-M006 (they are process/build metadata).
  d) Process C200-C324 corpus handbook claims. These are per-STAGE technical explainers. Group them by STAGE and create one FACT record per distinct technical assertion. Do not create 96 individual records if 30 records cover the same knowledge.
  e) For each REMEDIATION_TEXT entry in synthesis_engine.py: create a GUIDANCE record (type=GUIDANCE). Link it to the FACT records it corresponds to via `justifies_guidance` relationship. Flag GOOGLE_EXTENDED_MISSING and GPTBOT_MISSING guidance as check_links with relationship="contradicts" and note the contradiction.
  f) For each ACTION_SNIPPET entry: add it to the corresponding GUIDANCE record's guidance.action field, or create a new GUIDANCE record if no existing one covers it.

STEP 4: Create evidence.jsonl
For each knowledge record with evidence sources: create one EV-NNN evidence link record per (kid, sid) pair.

STEP 5: Create relationships.jsonl
Create explicit relationship records for:
- Any KT record that supersedes a CLM/C/MKB record
- Any two concepts that are closely related (same AEOG phase, adjacent topics)
- Any concept that contradicts a check code premise (use check_contradicts)

STEP 6: Create aeog_coverage.jsonl
For each AP-01 through AP-10 phase: count how many knowledge records address it, how many are strong/qualified/contested, what gaps exist.

STEP 7: Create research_queue.jsonl
For every knowledge record where confidence is NOT high+strong: create a queue entry with what needs to be verified.
Also add the following known gaps from Phase 3: GAP-01 through GAP-10 (from web_verification_report.md Section 12).

STEP 8: Write research_log.md
A brief session narrative: what you found, what choices you made, what was ambiguous.

STEP 9: Write changelog.jsonl
One line per CREATE/UPDATE/MERGE operation. Format per DATA_DICTIONARY.md.

═══════════════════════════════════════════════════════════
DECISION RULES
═══════════════════════════════════════════════════════════
PRESERVE: All source URLs, even if dead-looking. Record them, do not omit.
ADD: Only when a concept is not already represented.
MERGE: When two claims express the same underlying assertion. Surviving record inherits all legacy_ids.
ARCHIVE: M001-M006 (build process notes); deprecated claims (C325-C328).
FLAG: Claims whose source_url is null or a generic homepage. Add to research_queue.
DO NOT: Do web searches. Do not invent provenance. If source is missing, record it as missing.
DO NOT: Create a knowledge record without at least one evidence link (even if the evidence is "claimed in MKB, unverified").

═══════════════════════════════════════════════════════════
EVIDENCE STANDARDS FOR THIS SESSION
═══════════════════════════════════════════════════════════
You are structuring existing knowledge, not verifying it. Assign confidence based on:
- KT-NNN records from Phase 3: use the confidence/support already assigned
- MKB Study A claims: use the status/confidence from the MKB table rows
- MKB Study B claims: these are automatability ratings; confidence reflects the tier (T4=low, T3=medium, T1=high)
- C200-C324: T1 claims are high confidence; T4 claims are low; speculative flags → uncertainty note required
- REMEDIATION_TEXT: mark as GUIDANCE; don't assign confidence to guidance (it's a recommendation, not a fact)

═══════════════════════════════════════════════════════════
WHAT YOU MUST NOT DO
═══════════════════════════════════════════════════════════
- Do not do web research (no new searches in this session)
- Do not invent sources or provenance
- Do not delete anything — archive instead
- Do not create more than one record for the same underlying concept
- Do not accept vendor statistics (BrightEdge, SE Ranking etc.) as evidence — mark their claims as T4/contested

═══════════════════════════════════════════════════════════
OUTPUT — REQUIRED FILES
═══════════════════════════════════════════════════════════
knowledge.jsonl       — All structured knowledge records (KT-NNN IDs)
sources.jsonl         — All source records (SRC-NNN IDs)  
evidence.jsonl        — All evidence links (EV-NNN IDs)
relationships.jsonl   — All concept relationships
aeog_coverage.jsonl   — Per-phase coverage summary
research_queue.jsonl  — Items awaiting verification in Session 2
research_log.md       — Session narrative
changelog.jsonl       — All operations performed

═══════════════════════════════════════════════════════════
COMPLETION CRITERIA
═══════════════════════════════════════════════════════════
Session 1 is complete when:
✓ Every KT-NNN from web_verification_report.md is represented in knowledge.jsonl
✓ Every CLM/C/M record from active_claims.json has either a knowledge record or a legacy_id pointing to one
✓ Every REMEDIATION_TEXT entry has a GUIDANCE knowledge record
✓ Every source URL from active_claims.json appears in sources.jsonl
✓ research_queue.jsonl contains all items with weak provenance or missing sources
✓ aeog_coverage.jsonl has an entry for every AP-01 through AP-10
✓ changelog.jsonl is complete

Package all output files into a ZIP named: CITEABLE_KB_SESSION1.zip
```

---

## 14. SESSION 2 — EXECUTION PLAN

### Objective
Systematically verify weak claims, recover missing provenance, update outdated knowledge, and enrich the corpus with stronger sources. The structured corpus is the primary product — not a report.

### Input ZIP
`CITEABLE_KB_SESSION1.zip` (output of Session 1)

---

### SESSION 2 PROMPT

```
You are the knowledge verification agent for Citeable.

═══════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════
Citeable is an AI search citation audit tool. Its knowledge corpus has just been structured in Session 1.

This ZIP contains:
- knowledge.jsonl — Structured knowledge records (KT-NNN)
- sources.jsonl, evidence.jsonl, relationships.jsonl — Source and link files
- aeog_coverage.jsonl — Per-phase coverage
- research_queue.jsonl — Items awaiting verification
- research_log.md, changelog.jsonl — Session 1 history
- DATA_DICTIONARY.md — Field definitions (READ THIS FIRST)

═══════════════════════════════════════════════════════════
WHAT SESSION 1 DID
═══════════════════════════════════════════════════════════
Session 1 ingested all existing knowledge into the structured corpus. It:
- Created KT-NNN records for all 88ish concepts
- Mapped all 213 claims to knowledge records via legacy_ids
- Created GUIDANCE records for all 36 REMEDIATION_TEXT entries
- Identified items with weak/missing provenance in research_queue.jsonl
- Did NOT do web research

═══════════════════════════════════════════════════════════
YOUR JOB
═══════════════════════════════════════════════════════════
You ARE doing web research in this session.

Your job is to verify, not expand. Work through research_queue.jsonl systematically.

PRIORITY ORDER for verification:
1. Items tagged "check_contradicts" (invalid check codes — highest priority)
2. Items with confidence=low or support=weak or support=contested
3. Items with source_url=null (missing provenance)
4. Items whose source_url points to a generic page rather than the specific relevant section

FOR EACH ITEM IN THE QUEUE:
  a) Read the knowledge record from knowledge.jsonl
  b) Search for the primary source document
  c) Read the actual source
  d) Determine: does the source support the statement? Qualify it? Contradict it?
  e) Update the knowledge record accordingly (see rules below)
  f) Update the source record if a better URL was found
  g) Add the new evidence link to evidence.jsonl
  h) Remove the item from research_queue.jsonl
  i) Add a changelog entry

═══════════════════════════════════════════════════════════
SEARCH STRATEGY
═══════════════════════════════════════════════════════════
Always try primary sources first:
- For Google: developers.google.com/search (Search Central)
- For OpenAI: platform.openai.com/docs/bots (current canonical for bot docs)
- For Anthropic: support.anthropic.com/en/articles/8896518
- For Perplexity: docs.perplexity.ai
- For robots.txt protocol: rfc-editor.org/rfc/rfc9309
- For schema.org: schema.org, then Google Search Central schema docs

If a primary source is found with a relevant passage: record the exact URL, section, and excerpt.
If no primary source is found: record it as UNCERTAINTY with source=null.

Never accept a blog post as primary evidence for a platform behavior claim.

═══════════════════════════════════════════════════════════
DECISION RULES
═══════════════════════════════════════════════════════════
WHEN SOURCE IS FOUND AND SUPPORTS THE CLAIM:
- Update last_verified_at to today
- Update confidence/support if appropriate
- Add EV-NNN entry linking to the source
- Update source record with confirmed URL, section, excerpt
- Add history entry to knowledge record

WHEN SOURCE QUALIFIES THE CLAIM:
- Update the statement to be more precise
- Add a context note
- Log prior statement in history
- Mark support="partial" if appropriate

WHEN SOURCE CONTRADICTS THE CLAIM:
- Do NOT remove or replace the claim
- Add contradiction field to knowledge record
- Create a new evidence link with relationship="contradicts"
- If the contradiction is severe: set status="contested"
- If the claim is simply wrong: set status="superseded", create corrected record

WHEN NO SOURCE IS FOUND:
- Record as UNCERTAINTY type if not already
- Set confidence=low, support=absent
- Update research_queue for Session 3 follow-up

═══════════════════════════════════════════════════════════
SPECIFIC VERIFICATION PRIORITIES
═══════════════════════════════════════════════════════════
The following must be verified in this session (from Phase 3 findings):

1. GPTBOT_MISSING invalidity — verify via platform.openai.com/docs/bots. Confirm OAI-SearchBot is the citation crawler.
2. GOOGLE_EXTENDED_MISSING invalidity — verify via Google-Extended docs. Find exact quote about AI Overviews.
3. LLMS_TXT_MISSING absence of effect — verify via Ahrefs study and any Google Search Central statement.
4. nosnippet affects AI Overviews — find exact quote in Google robots-meta-tag documentation.
5. Schema → AI citation (null-to-negative) — confirm Ahrefs May 2026 study URL and methodology note.
6. PerplexityBot documented official compliance vs. observed proxy bypass — document both sides.
7. Perplexity-User robots.txt exception — find official docs statement.
8. FAQPage deprecation May 7 2026 — confirm Google changelog URL.
9. Gemini API groundingMetadata — confirm structure in Gemini API docs.
10. EU DSM Directive Art. 4 (robots.txt = TDM opt-out) — confirm citation.

═══════════════════════════════════════════════════════════
WHAT YOU MUST NOT DO
═══════════════════════════════════════════════════════════
- Do not create new knowledge records unless you find something significantly missing
- Do not write a research report instead of updating the corpus
- Do not accept vendor statistics without methodology as evidence
- Do not treat LLM output as a primary source
- Do not resolve a genuine contradiction by picking a side — document both

═══════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════
Updated versions of all JSONL files (in-place updates + appends)
research_log.md — append Session 2 section
changelog.jsonl — append all Session 2 operations
research_queue.jsonl — remove verified items, add any new items discovered

Package as: CITEABLE_KB_SESSION2.zip
```

---

## 15. SESSION 3 — EXECUTION PLAN

### Objective
Fill genuine knowledge gaps. Research areas where Citeable currently has thin or absent knowledge. Add new knowledge records only when adequately evidenced.

### Input ZIP
`CITEABLE_KB_SESSION2.zip`

---

### SESSION 3 PROMPT

```
You are the knowledge expansion agent for Citeable.

═══════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════
Citeable is an AI search citation audit tool. This ZIP contains the structured knowledge corpus after two sessions of ingestion (Session 1) and verification (Session 2).

This ZIP contains:
- knowledge.jsonl, sources.jsonl, evidence.jsonl, relationships.jsonl — Updated corpus
- aeog_coverage.jsonl — Current coverage state
- research_queue.jsonl — Remaining items + gaps
- DATA_DICTIONARY.md — READ THIS FIRST

═══════════════════════════════════════════════════════════
YOUR JOB
═══════════════════════════════════════════════════════════
Research genuine knowledge gaps identified in research_queue.jsonl. Add new knowledge records ONLY when:
1. The knowledge materially improves Citeable's audit coverage
2. The evidence is at T1-T3 level
3. The concept does not already exist in knowledge.jsonl

BEFORE ADDING ANYTHING: search knowledge.jsonl for existing records covering the same concept. If found: enrich, don't duplicate.

PRIORITY ORDER for gaps to research:
1. GAP-01: OAI-SearchBot vs GPTBot correct bifurcation (GUIDANCE records for correct robots.txt configuration)
2. GAP-02: Google-Extended correct usage guidance
3. GAP-03: Perplexity-User robots.txt non-compliance guidance
4. GAP-04: Bytespider WAF-level blocking guidance
5. GAP-05: llms.txt correct framing (developer tool, not citation signal)
6. GAP-06: Schema-entity disambiguation — find better sources
7. GAP-07: EU DSM Directive — confirm robots.txt legal status
8. GAP-08: FAQPage deprecation — full timeline
9. GAP-09: Gemini API groundingMetadata structure — document as FACT
10. GAP-10: Core Web Vitals not a documented AI citation signal — confirm

═══════════════════════════════════════════════════════════
WHAT TO RESEARCH BEYOND THE QUEUE
═══════════════════════════════════════════════════════════
Check aeog_coverage.jsonl for phases with gap_count > 0. For each gap:
- Determine if it is researchable from primary sources
- If yes: research and add only if T1-T3 evidence found
- If not: record as UNCERTAINTY and remove from queue

═══════════════════════════════════════════════════════════
EVIDENCE STANDARDS
═══════════════════════════════════════════════════════════
T1 (official docs): Use as primary basis. Record URL, section, excerpt.
T2 (controlled study): Use with methodology note. Record n=, control method, COI.
T3 (practitioner, corroborated): Use with corroboration note. Two independent sources minimum.
T4 (vendor marketing): Do not use. Record existence in uncertainty note if relevant.

═══════════════════════════════════════════════════════════
DO NOT
═══════════════════════════════════════════════════════════
- Do not add knowledge that duplicates existing records
- Do not create low-confidence filler
- Do not write a report instead of updating the corpus
- Do not treat SEO blog posts as primary sources

═══════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════
Updated corpus files + new records
Session 3 section in research_log.md
Appended changelog.jsonl
Package as: CITEABLE_KB_SESSION3.zip
```

---

## 16. SESSION 4 — EXECUTION PLAN

### Objective
Canonicalize, deduplicate, finalize. Produce the final clean corpus and human-readable summary.

### Input ZIP
`CITEABLE_KB_SESSION3.zip`

---

### SESSION 4 PROMPT

```
You are the knowledge canonicalization agent for Citeable.

═══════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════
Citeable is an AI search citation audit tool. Three sessions of work have produced a growing knowledge corpus. This session finalizes it.

═══════════════════════════════════════════════════════════
YOUR JOB
═══════════════════════════════════════════════════════════
STEP 1: DEDUPLICATION PASS
Read all records in knowledge.jsonl. For each pair that may express the same concept:
- If truly the same: merge. Surviving record inherits all legacy_ids, evidence_ids, relationships.
- If meaningfully different: create a `related` relationship and keep both.
- Produce a deduplication log.

STEP 2: COVERAGE COHERENCE
Update aeog_coverage.jsonl to reflect final counts. Every AP-01 through AP-10 phase must have:
- A coverage record
- Accurate kid_count, strong_count, qualified_count, contested_count, gap_count
- Explicit gap descriptions where gap_count > 0

STEP 3: REMEDIATION COHERENCE
Every check code in CHECK_CODE_TO_CLAIM_IDS (from findings_to_claims.py) should have:
- A corresponding GUIDANCE record in knowledge.jsonl
- A check_links entry connecting FACT records to the check code
- For deprecated check codes (GPTBOT_MISSING, GOOGLE_EXTENDED_MISSING): mark the GUIDANCE record status="deprecated" with a note explaining why

STEP 4: UNCERTAINTY COHERENCE
Every contested or low-confidence record must have:
- A non-null uncertainty field
- At least one research_queue entry

STEP 5: PRODUCE FINAL SUMMARY
Write CITEABLE_KNOWLEDGE_SUMMARY.md (human-readable):
- Total counts: FACT/STANDARD/FINDING/UNCERTAINTY/GUIDANCE records
- Per-phase coverage table
- Top 10 highest-confidence facts
- All contested knowledge list
- All deprecated check code guidance with explanation
- All open gaps

STEP 6: PRODUCE ENGINEERING HANDOFF
Write CITEABLE_ENGINEERING_NOTES.md:
- Schema for knowledge.jsonl records
- How to query by aeog_phase, check_code, confidence
- How to retrieve remediation for a check code
- How to build check_code → knowledge_id mappings
- Which records are safe for deterministic lookup
- Which records are candidates for semantic indexing
- Which records should be excluded from runtime (archived, deprecated)

═══════════════════════════════════════════════════════════
FINAL OUTPUT ZIP: CITEABLE_KB_FINAL.zip
═══════════════════════════════════════════════════════════
Must contain:
- knowledge.jsonl (final, deduplicated)
- sources.jsonl (final)
- evidence.jsonl (final)
- relationships.jsonl (final)
- aeog_coverage.jsonl (final)
- research_queue.jsonl (remaining items only — all resolved items removed)
- changelog.jsonl (complete history)
- research_log.md (all 4 session sections)
- CITEABLE_KNOWLEDGE_SUMMARY.md (human-readable)
- CITEABLE_ENGINEERING_NOTES.md (engineering handoff)
- DATA_DICTIONARY.md (unchanged)
```

---

## 17. ZIP Handoff Contract

| ZIP | Produced by | Consumed by | Must contain | Must NOT contain |
|---|---|---|---|---|
| CITEABLE_KB_INPUT.zip | Manual assembly (this document §12) | Session 1 | Raw inputs, DATA_DICTIONARY, session prompt | areos.db binary, compiled ZIPs, UI files |
| CITEABLE_KB_SESSION1.zip | Session 1 | Session 2 | All JSONL corpus files v1, research_log S1, changelog S1 | Web research notes, temporary scratch files |
| CITEABLE_KB_SESSION2.zip | Session 2 | Session 3 | Updated JSONL corpus files, appended logs | Duplicate records, resolved queue items |
| CITEABLE_KB_SESSION3.zip | Session 3 | Session 4 | Expanded JSONL corpus, all logs complete | Low-confidence filler, T4-only records |
| CITEABLE_KB_FINAL.zip | Session 4 | Engineering | Final deduplicated corpus, both summary docs | Temporary files, session scratch work |

**Invariant:** Each ZIP is strictly additive. Later ZIPs contain everything earlier ZIPs contained plus updates. Nothing is silently removed — only status changes.

---

## 18. Final Corpus Specification

`CITEABLE_KB_FINAL.zip` must contain the following:

| File | Contents | Format |
|---|---|---|
| `knowledge.jsonl` | All canonical knowledge records (KT-NNN) | JSONL |
| `sources.jsonl` | All sources with authority, URL, excerpt | JSONL |
| `evidence.jsonl` | All evidence links | JSONL |
| `relationships.jsonl` | All concept relationships | JSONL |
| `aeog_coverage.jsonl` | Per-phase coverage | JSONL |
| `research_queue.jsonl` | Open items for future sessions | JSONL |
| `changelog.jsonl` | Complete audit trail of all operations | JSONL |
| `research_log.md` | Human narrative across all 4 sessions | Markdown |
| `CITEABLE_KNOWLEDGE_SUMMARY.md` | Human-readable corpus overview | Markdown |
| `CITEABLE_ENGINEERING_NOTES.md` | Engineering handoff instructions | Markdown |
| `DATA_DICTIONARY.md` | Field definitions | Markdown |

**Expected final corpus size:**
- Knowledge records: ~80–100 KT-NNN records
- Sources: ~60–90 SRC-NNN records (deduplicated from ~150 raw references)
- Evidence links: ~150–200 EV-NNN records
- GUIDANCE records: ~36–45 (one per check code, plus additional implementation patterns)
- Deprecated/archived: ~20–30 records (build logs, superseded claims, invalid checks)

---

## 19. Target Architecture

### 19.1 Recommended Architecture: Tiered Hybrid

```
┌─────────────────────────────────────────────────────────────┐
│                    AUDIT FINDINGS                           │
│            (check_code + page_url + page_data)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────▼───────────────┐
          │      TIER 1: DETERMINISTIC    │
          │      check_code lookup        │
          │  → knowledge_id              │
          │  → FACT/STANDARD records     │
          │  → GUIDANCE record           │
          │  → source evidence chain     │
          └───────────────┬───────────────┘
                          │ Known check code?
                    ┌─────┴─────┐
                    │ YES       │ NO
                    │           ▼
                    │   ┌────────────────────┐
                    │   │  TIER 2: SEMANTIC   │
                    │   │  Embed finding text  │
                    │   │  → candidate KIDs   │
                    │   │  (confidence scored) │
                    │   └────────┬───────────┘
                    │            │
                    └─────┬──────┘
                          ▼
          ┌───────────────────────────────┐
          │       SYNTHESIS ENGINE        │
          │  knowledge records            │
          │  + evidence chain             │
          │  + confidence level           │
          │  + uncertainty flags          │
          │  + remediation guidance       │
          └───────────────┬───────────────┘
                          ▼
          ┌───────────────────────────────┐
          │        LLM SYNTHESIS          │
          │  Grounded in retrieved        │
          │  knowledge + evidence         │
          │  Cannot hallucinate sources   │
          └───────────────┬───────────────┘
                          ▼
          ┌───────────────────────────────┐
          │         QA GATE               │
          │  Verify: every claim in       │
          │  response traces to a KT-NNN  │
          └───────────────────────────────┘
```

### 19.2 Tier 1: Deterministic Layer

**What it does:** For every known check code, retrieve the exact knowledge record(s), source evidence, and guidance without LLM involvement.

**Built from:** `check_links` in knowledge.jsonl → `kid` → full record → `evidence_ids` → sources → `remediation_link` → GUIDANCE record

**When it applies:** ~36 current check codes. Every known check maps to a knowledge record with deterministic lookup.

**How it's queried:**
```python
# Pseudo-code — actual implementation TBD
def get_knowledge_for_check(check_code: str) -> list[KnowledgeRecord]:
    kid_list = check_code_index[check_code]          # built at startup from check_links
    return [knowledge_store[kid] for kid in kid_list]
```

**Data required from corpus:** `check_links`, `kid`, `statement`, `context`, `confidence`, `support`, `evidence_ids`, `remediation_link`, `guidance`, `status` (must be `active`)

### 19.3 Tier 2: Semantic Layer

**What it does:** For novel findings not covered by known check codes — embedds the finding description and retrieves candidate knowledge records by semantic similarity.

**When it applies:** Novel technical findings, vendor-specific issues, new platform behaviors discovered during audits.

**How it works:**
1. At build time: embed `statement + context` for every active, non-GUIDANCE knowledge record
2. At query time: embed the novel finding → cosine similarity → top-k candidates
3. Filter candidates by: `confidence != low` AND `support != absent` AND `status == active`
4. Return candidates with their evidence chains

**Data required from corpus:** Same fields as Tier 1, plus pre-built vector embeddings (computed at ingest time, not stored in corpus JSONL)

### 19.4 LLM Role

The LLM in the proposed architecture:
- **Receives:** finding context + retrieved knowledge records + evidence excerpts + guidance text
- **Does not:** invent sources, invent facts, generate knowledge
- **Produces:** a synthesized finding report that references only the retrieved `kid` values and their associated source URLs
- **Is constrained by:** a grounding prompt that lists the retrieved records explicitly

### 19.5 QA Gate

Before any recommendation reaches the user:
- Every claim in the synthesis must trace to an active `kid` with `confidence != low`
- Every source citation must be an `sid` in sources.jsonl
- Deprecated check guidance (`GPTBOT_MISSING`, `GOOGLE_EXTENDED_MISSING`) must not be surfaced

---

## 20. Why This Architecture

The architecture emerges directly from the corpus design:

| Corpus Feature | Architecture Consequence |
|---|---|
| Every FACT record has `check_links` | Deterministic routing by check_code is possible |
| Every GUIDANCE record is linked to a FACT | Remediation is evidence-backed, not invented |
| Evidence chain is explicit | LLM cannot hallucinate sources — they're in the retrieved record |
| Confidence + support fields | QA gate can filter low-quality knowledge |
| UNCERTAINTY type | System can tell users "this is unknown" rather than inventing an answer |
| ARCHIVED/DEPRECATED status | Invalid check codes are excluded from deterministic routing |
| Semantic-compatible schema | Embedding statement + context gives a clean semantic signal |

The corpus design enables the architecture. The architecture cannot work without the corpus.

---

## 21. Implementation Boundary

What future engineering will actually need to build (after corpus is final):

| Component | Complexity | Depends on |
|---|---|---|
| Corpus loader | Low | CITEABLE_KB_FINAL.zip |
| check_code index builder | Low | `check_links` in knowledge.jsonl |
| Deterministic retrieval function | Low | check_code index |
| Source retrieval function | Low | evidence.jsonl + sources.jsonl |
| Vector embedding pipeline (Tier 2) | Medium | knowledge.jsonl |
| Semantic retrieval function | Medium | Embeddings + kid index |
| Synthesis engine refactor | Medium | Retrieved knowledge records API |
| QA gate | Low | `kid`, `confidence`, `status` |
| DB migration (current claims → new corpus) | Low-Medium | `legacy_ids` in knowledge records |
| Deprecated check code removal | Low | Confirmed by corpus |

**What engineering does NOT need to rebuild:** The research. The provenance. The source verification. The AEOG coverage mapping. The deduplication. All of that is in the corpus.

---

## 22. Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **Session duplication** — Session 3 creates records Session 1 already made | High | Corpus bloat, inconsistency | Mandatory search-before-add rule; clear kid assignment protocol |
| **Session drops history** — Session overwrites without logging | Medium | Lost lineage | Append-only changelog; history embedded in record |
| **Corpus becomes too large for LLM session** — 100k+ token JSONL files | Medium | Session becomes ineffective | Split corpus by scope (crawl-access.jsonl, content-quality.jsonl, authority-citation.jsonl) if needed |
| **Research finds nothing for a gap** — Session 3 creates low-confidence filler | Medium | Knowledge quality degrades | Reject rule: T4-only evidence → UNCERTAINTY record, not new FACT |
| **Outdated check codes persist** — engineering doesn't update | Low-Medium | Users see invalid advice | Deprecated status in corpus + CITEABLE_ENGINEERING_NOTES explicit list |
| **Platform behavior changes between sessions** — fast-moving field | Medium | Some facts become stale | review_due dates; Session 2 verifies Session 1's claims against live docs |
| **Session 4 over-merges** — loses legitimate variants | Low | Lost specificity | Merge rule: if in doubt, relate rather than merge |

---

## 23. Success Criteria

The knowledge-building program succeeds when `CITEABLE_KB_FINAL.zip` satisfies all of the following:

**Corpus Quality**
- [ ] Every active knowledge record (non-archived) has at least one T1-T3 evidence link
- [ ] No two active records express the same underlying assertion (deduplication complete)
- [ ] All 36 current check codes have a corresponding GUIDANCE record
- [ ] `GPTBOT_MISSING` and `GOOGLE_EXTENDED_MISSING` GUIDANCE records are marked `deprecated` with explanation
- [ ] `LLMS_TXT_MISSING` GUIDANCE record is marked with the empirical refutation and demoted severity
- [ ] Every `confidence=low` record has a non-null `uncertainty` field
- [ ] Every `status=contested` record has a non-null `contradiction` field

**Coverage**
- [ ] Every AP-01 through AP-10 phase has at least one `strong` knowledge record
- [ ] AP-03 (crawlers) correctly distinguishes training vs. search crawlers
- [ ] AP-02 (schema) correctly represents the citation-frequency vs. entity-disambiguation distinction
- [ ] AP-08 (legal) has updated CLM-044 with the SerpApi ruling qualification

**Architecture Readiness**
- [ ] Every knowledge record can be retrieved by `check_code` via `check_links`
- [ ] Every knowledge record can be embedded (`statement + context` is clean, self-contained text)
- [ ] Engineering notes document exactly which records are deterministic-safe and which are semantic-candidate
- [ ] The corpus can be ingested without Citeable's current DB schema

**Human Auditability**
- [ ] `CITEABLE_KNOWLEDGE_SUMMARY.md` is readable by a non-engineer
- [ ] Every knowledge record has a traceable lineage via `legacy_ids` + `provenance`
- [ ] No knowledge disappeared silently — all archived records are present with archive reason
