# CITEABLE — KNOWLEDGE BUILD PROGRAM & TARGET HYBRID ARCHITECTURE

*Authored after reading all prior session artifacts, the governed knowledge corpus, the forensic architecture investigation, the governance audit, and the live codebase.*  
*Date: 2026-08-29*

---

## PART A — PROJECT BASELINE

### What all prior sessions established

**From the forensic investigation (knowledge_architecture.md):**

The live Citeable system operates as follows:
1. Audit detectors (`auditors/`) produce check codes (e.g. `CRAWLER_FULLY_BLOCKED`, `MISSING_REQUIRED_FIELD`)
2. `synthesis_engine.py` maps check codes → claim IDs using `CHECK_CODE_TO_CLAIM_IDS` (a hardcoded Python dict; 35 check codes → 12 claim IDs)
3. Claims are retrieved from the SQLite `claims` table (217 rows)
4. `synthesis_engine.py` also owns `PRIORITY_SCORES` (35 entries — heuristic business policy, not evidence-based) and `REMEDIATION_TEXT` (hardcoded prose)
5. `audit_orchestrator.py` owns `ACTION_SNIPPETS` (12 check codes → code snippets)
6. An LLM receives the claims + check outputs and produces a narrative synthesis
7. No embedding, no vector store, no semantic retrieval exists today

**The current system's knowledge is split across four locations — and they are not in sync:**
- `claims` table in SQLite (217 rows; 16 claim types, only 5 are per-spec)
- `REMEDIATION_TEXT` dict in Python (hardcoded prose per check code)
- `ACTION_SNIPPETS` dict in Python (12 hardcoded code snippets)
- `check_code_mappings` table (36 rows; 12 distinct claim IDs referenced)

**Critical design debt identified:**
- `PRIORITY_SCORES` are heuristic, not evidence-backed. Ordering `LLMS_TXT_MISSING: 2` (second-highest priority) has no epistemic basis.
- `GOOGLE_EXTENDED_MISSING` and `GPTBOT_MISSING` are conceptually wrong checks — they conflate training crawlers with search crawlers.
- `AUTHORITY_DR_LOW` references a third-party metric (Moz Domain Rating) that no AI platform uses for citation.
- 60 of 173 knowledge records have no AEOG phase mapping.

**From the web verification report:**
- Three check codes are invalid in concept: `GPTBOT_MISSING`, `GOOGLE_EXTENDED_MISSING`, `LLMS_TXT_MISSING`
- Robots.txt blocks training crawlers (GPTBot) but does not block AI search crawlers (OAI-SearchBot, GoogleBot)
- llms.txt: 3 independent large-scale studies (Ahrefs 137k domains, SE Ranking 300k domains, SEL field study) find zero correlation with AI citation frequency

**From the governance audit and corrections:**
- KT-004 (Perplexity robots.txt compliance) remains genuinely contested
- KT-007 (Schema → AI citation causation) remains genuinely contested
- Vendor research must not be used as primary causal evidence
- The "amplifier" framing for schema is editorial, not empirical

### Current governed corpus state

| Metric | Value |
|---|---|
| Knowledge records | 173 |
| Sources | 114 |
| Evidence links | 178 |
| Active records | 151 |
| Contested records | 7 |
| Deprecated records | 9 |
| Archived records | 6 |
| High-confidence records | 78 |
| Medium-confidence | 79 |
| Low-confidence | 16 |
| Records without AEOG mapping | 60 (35%) |
| AEOG phases covered | AP-01, 02, 03, 04, 05, 06, 08, 10 |
| AEOG phases not covered | AP-07, AP-09, and all inner stages |
| Governance backlog items | 8 (2 high-priority URL verifications) |

---

## PART B — REMAINING PROBLEM

The project has two remaining problems:

**Problem 1: The governed corpus is architecturally disconnected from the live system.**
The 173 knowledge records exist as JSONL on disk. The live system reads from a SQLite DB and Python dicts. Nothing links the two. Building the architecture means defining the bridge.

**Problem 2: The corpus has real gaps that prevent it from being the system's single source of truth.**

Specifically:
- **60 records have no AEOG phase** — the architecture cannot route them to audit stages
- **AP-07 and AP-09 are completely uncovered** — no knowledge exists for entire audit phases
- **Remediation knowledge is incomplete** — GUIDANCE records exist for 50 check codes, but the full remediation path (why → what → how → example) is not fully structured for all of them
- **Contested knowledge (7 records) has no handling spec** — what does the runtime do when it encounters a contested fact?
- **The check-code-to-knowledge mapping is not yet in the corpus** — the GUIDANCE records link knowledge to check codes, but the inverse map (check code → all relevant knowledge, not just GUIDANCE) doesn't exist
- **Source URL verification is incomplete** — GB-001 and GB-002 remain

---

## PART C — TARGET KNOWLEDGE CORPUS

The finished corpus must be able to answer:

1. For any check code: what is the underlying knowledge, why does this check matter, what should the user do, how should they do it, what's the evidence, and how confident are we?
2. For any AEOG phase: what do we know, what are we uncertain about, what has no coverage?
3. For any knowledge item: what are its sources, what is the confidence, is it contested, when was it verified, when should it be re-verified?
4. For any contested item: what is the disagreement, what are both sides, what would resolve it?
5. For any deprecated check: why was it deprecated, what should replace it?

The corpus is NOT trying to be an exhaustive encyclopedia of AEO/GEO research. It is the **minimum canonical knowledge required for Citeable to make defensible, evidence-backed audit findings and remediations.**

---

## PART D — DATA CONTRACT

### Primary Format: JSONL (retained and improved)

**Why JSONL over alternatives:**
- JSONL is append-friendly, diff-able, grep-able, and trivially parseable by Python, Node, and any LLM
- SQLite: better for production query, worse for a research session to modify safely
- JSON (single file): loses the ability to append incrementally; merge conflicts are catastrophic
- Markdown: excellent for human reading, terrible for programmatic mutation
- Relational export: correct for the final architecture ingest, wrong for the research handoff medium

JSONL is the **research transport format**. The final architecture will have its own production storage (SQLite or Postgres). The JSONL corpus is the canonical input to that database, not the database itself.

### Canonical Objects

#### `knowledge.jsonl` — one record per knowledge item

```jsonc
{
  "kid":          "KT-NNN",           // stable, never reused
  "type":         "FACT|STANDARD|FINDING|UNCERTAINTY|GUIDANCE",
  "scope":        "crawl-access|content-quality|authority-citation",
  "aeog_phases":  ["AP-NN"],          // empty = not yet mapped
  "stage_ids":    ["STAGE-NNN"],      // sub-phase granularity (future)
  "check_links":  [                   // relationship to check codes
    {
      "check_code":   "STRING",
      "relationship": "supports|contradicts|informs",
      "note":         "STRING"
    }
  ],
  "statement":    "STRING",           // the single atomic assertion
  "context":      "STRING",           // interpretive scaffolding (not the assertion)
  "status":       "active|contested|deprecated|archived",
  "confidence":   "high|medium|low",
  "support":      "strong|partial|weak|contested",
  "evidence_ids": ["EV-NNN"],
  "uncertainty":  "STRING|null",      // only if uncertain; explains what is unknown
  "contradiction":"STRING|null",      // only if contradicted; names the disagreement
  "remediation_link": "KT-NNN|null",  // points to a GUIDANCE record if applicable
  "guidance": {                       // only on GUIDANCE type records
    "problem":      "STRING",
    "action":       "STRING",
    "rationale":    "KT-NNN",
    "tech_context": ["STRING"],
    "examples":     ["STRING"],
    "check_codes":  ["STRING"]
  },
  "relationships": [
    {
      "target_kid": "KT-NNN",
      "rel_type":   "supports|refines|contradicts|supersedes|related",
      "note":       "STRING"
    }
  ],
  "legacy_ids":   ["CLM-NNN"],        // backward compat with DB claims
  "provenance": {
    "origin":           "STRING",
    "created_at":       "YYYY-MM-DD",
    "created_by":       "session_N",
    "last_verified_at": "YYYY-MM-DD",
    "last_verified_by": "STRING",
    "review_due":       "YYYY-MM-DD"
  },
  "history": [                        // append-only, never edit
    {
      "at":              "YYYY-MM-DD",
      "by":              "session_N",
      "change":          "STRING",
      "prior_statement": "STRING|null"
    }
  ]
}
```

#### `sources.jsonl` — one record per source document/URL

```jsonc
{
  "sid":         "SRC-NNN",
  "url":         "STRING|null",
  "title":       "STRING",
  "publisher":   "STRING",
  "type":        "official-platform-docs|standard|legal|practitioner-research|vendor-blog|...",
  "authority":   "T1|T2|T3|T4|T5",   // see governance §K
  "pub_date":    "YYYY-MM-DD|YYYY-MM|null",
  "access_date": "YYYY-MM-DD",
  "section":     "STRING|null",
  "excerpt":     "STRING",            // must be exact quote or labeled "paraphrase"
  "excerpt_type":"verbatim|paraphrase|interpretive-summary",
  "notes":       "STRING|null",
  "archived_url":"STRING|null"
}
```

#### `evidence.jsonl` — one record per knowledge-source link

```jsonc
{
  "eid":          "EV-NNN",
  "kid":          "KT-NNN",
  "sid":          "SRC-NNN",
  "relationship": "supports|contradicts|contextualizes|partially-supports",
  "weight":       "primary|corroborating|contextual",
  "note":         "STRING"
}
```

#### `governance_backlog.jsonl` — open questions

```jsonc
{
  "gid":              "GB-NNN",
  "priority":         "high|medium|low",
  "category":         "source-verification|knowledge-resolution|structural|review-schedule",
  "kid":              "KT-NNN|null",
  "description":      "STRING",
  "blocks_canonical": true|false,
  "added_by":         "session_N",
  "added_at":         "YYYY-MM-DD"
}
```

#### `changelog.jsonl` — append-only, never edited

```jsonc
{
  "at":      "YYYY-MM-DD",
  "session": "session_N",
  "op":      "CREATE|UPDATE|DEPRECATE|ARCHIVE|SPLIT|MERGE|ADD_SOURCE|ADD_EVIDENCE|QUEUE_UPDATE|GOVERNANCE_CORRECTION",
  "kid":     "KT-NNN|null",
  "note":    "STRING"
}
```

### Atomicity Rule

**Every knowledge record must assert exactly one thing.** If a statement requires "and" or "however" to capture two independent assertions, split it into two records linked by a `relationship`.

---

## PART E — FIRST ZIP SPECIFICATION

The first ZIP must stand alone. A fresh session must open it and immediately understand what Citeable is, what work has been done, and what to do next.

### Directory structure

```
CITEABLE_KB_S10/
├── MISSION_CONTROL.md          ← master checklist (living doc, mark items as done)
├── SESSION_INSTRUCTIONS.md     ← what this specific session must do
├── DATA_DICTIONARY.md          ← schema reference
├── README.md                   ← what Citeable is in ≤ 300 words
├── CHANGELOG.md                ← human-readable summary of changes per session
│
├── corpus/
│   ├── knowledge.jsonl         ← 173 governed records (governance-corrected)
│   ├── sources.jsonl           ← 114 sources
│   ├── evidence.jsonl          ← 178 evidence links
│   ├── relationships.jsonl     ← 73 relationship records
│   ├── governance_backlog.jsonl← 8 open governance items
│   └── changelog.jsonl         ← full operation log
│
├── context/
│   ├── AEOG_TAXONOMY.md        ← AP-01 through AP-12 definitions
│   ├── CHECK_CODE_REGISTRY.md  ← all 35+ check codes with current status
│   ├── ARCHITECTURE_SUMMARY.md ← brief forensic summary of the live system
│   └── GOVERNANCE_RULES.md     ← evidence, provenance, contradiction, uncertainty rules
│
├── research/
│   ├── GOVERNANCE_AUDIT.md     ← the audit findings (what Session 9 got wrong and why)
│   ├── OPEN_QUESTIONS.md       ← the 8 governance backlog items expanded
│   └── COMPLETED_RESEARCH.md   ← what has already been researched (do not re-research)
│
└── archive/
    └── SESSION_LOG.md          ← append-only session notes
```

### What NOT to include
- Full Python source files from the Citeable repo (too noisy; ARCHITECTURE_SUMMARY.md is enough)
- The raw MKB HTML/markdown (superseded; relevant knowledge is already in knowledge.jsonl)
- The individual session driver scripts (session_9_driver.py etc.) — these are implementation artifacts, not knowledge
- Any knowledge that was deprecated or archived — it is in knowledge.jsonl marked as such; no need for separate files

---

## PART F — SESSION 10 (FIRST EXTERNAL SESSION)

**Purpose: Normalize, map, and fill the AEOG coverage gaps.**

This session does NOT do broad new research. It fixes structural problems in the existing corpus.

### Deliverables

1. **AEOG phase mapping for all 60 unmapped records** — read each record, determine which AP phase it belongs to, update `aeog_phases` field
2. **AP-07 and AP-09 coverage** — are there genuinely no checks in these phases? Verify by reading the CHECK_CODE_REGISTRY and AEOG_TAXONOMY. If checks exist, research the knowledge. If no checks exist, record that explicitly.
3. **Verify GB-001 and GB-002** — confirm live URLs for SRC-111 (Perplexity) and SRC-112 (Ahrefs schema study). Use browser tools. If confirmed, update `authority` and remove governance flag. If still 403/404, find the correct URL.
4. **Resolve SRC-048** (SALT.agency 403) — find correct slug for the "Backlinks Aren't Dead" study
5. **Atomicity audit** — identify all COMPOUND statements (38 flagged). For each: decide whether to split or keep. If a compound statement genuinely captures one concept with a caveat, it may stay. If it asserts two independent facts, split it.

### Research rules for this session
- Only do targeted web research for the above tasks
- Do not add new knowledge topics — this is a normalization session
- Every change must be logged in changelog.jsonl

### Quality gate
Session succeeds if:
- `aeog_phases` is populated for ≥ 95% of records
- GB-001 and GB-002 are resolved (URL confirmed or best-available documented)
- ≥ 10 compound statements are split into atomic records
- 0 new compound statements introduced

---

## PART G — SESSION 11 (SECOND EXTERNAL SESSION)

**Purpose: Deep knowledge expansion — fill the gaps the corpus knows it has.**

This session does targeted research to answer the known open questions.

### Assigned research targets

**Cluster 1: Contested claims — gather more evidence, do not resolve artificially**
- KT-004 (Perplexity): find any post-2025 independent behavioral testing of PerplexityBot compliance
- KT-007 (Schema): find the Ahrefs study's actual confirmed URL; find any 2026 replication or refutation
- KT-041 (Content structure): find a controlled study measuring "answerable chunk" format vs. citation rate

**Cluster 2: Remediation knowledge — what's structurally missing**
For each active GUIDANCE record without a `rationale` KT-NNN link, trace back to the underlying FACT/STANDARD/FINDING that justifies the guidance and create the link. This ensures the full chain: check code → GUIDANCE → underlying knowledge → evidence → source.

**Cluster 3: Missing check code coverage**
The live system has 35 check codes in PRIORITY_SCORES. The corpus has GUIDANCE records for ~20 of them. Research the remaining 15 and either:
- Create a new GUIDANCE record with the backing FACT/FINDING, OR
- Create an UNCERTAINTY record explaining why evidence is absent for this check

**Cluster 4: Temporal refresh**
- KT-015 (FAQ rich results deprecated): verify current status as of research date
- KT-040 (content freshness): is the 17M-citation Ahrefs study still the primary reference, or is there a 2026 update?
- KT-108 (INP as Core Web Vital): confirm it is still active as of research date

### Research rules for this session
- For each new knowledge item: CREATE or ENRICH, not both
- Every source must have `excerpt_type` field
- Contested findings must preserve both sides of the disagreement
- No vendor study becomes "primary evidence" for causal claims

### Quality gate
- ≥ 5 contested/weak records enriched with new evidence
- ≥ 10 new GUIDANCE records with complete rationale chains
- ≥ 5 new non-GUIDANCE records (FACT/FINDING/STANDARD)
- 0 false confidence upgrades
- All new sources have `excerpt_type` set

---

## PART H — SESSION 12 (THIRD EXTERNAL SESSION)

**Purpose: Reconciliation, deduplication, and check-code alignment.**

### Assigned tasks

**Deduplication pass**
The corpus grew across 9 sessions. Identify cases where two records assert the same underlying fact. For each duplicate pair:
- If one is stronger (better sourced, more precise): archive the weaker, enrich the stronger
- If they are genuinely different aspects: create a `related` relationship between them
- Never delete — only archive with `history` entry explaining the merge

**Check-code alignment**
Build and include in the ZIP a new file: `check_code_to_knowledge_map.json` — for every check code in the live system, which KT-NNN records are relevant (not just the GUIDANCE record, but the underlying FACT/FINDING/STANDARD that explain *why* the check exists).

**Confidence reconciliation**
The MKB July 30, 2026 Human Rulings rated some knowledge high-confidence that the Phase-3 research rated medium. These disagreements are currently flagged in uncertainty fields. This session should explicitly resolve each disagreement by:
- Reading both assessments
- Looking at the evidence
- Picking the rating that the evidence actually supports
- Logging the resolution decision in history

**Remediation completeness check**
For every active GUIDANCE record: verify it has a complete remediation chain:
- problem statement ✓
- recommended action ✓
- rationale (KT-NNN link) ✓
- tech_context ✓
- at least one example ← this is commonly missing

Add examples where missing. Examples should be concrete (e.g., a robots.txt snippet, a JSON-LD block).

### Quality gate
- check_code_to_knowledge_map.json produced and correct
- ≥ 5 duplicate pairs resolved
- All confidence disagreements documented with resolution decision
- ≥ 80% of GUIDANCE records have at least one example

---

## PART I — SESSION 13 (FOURTH EXTERNAL SESSION)

**Purpose: Final canonicalization and architecture-readiness validation.**

### Assigned tasks

**Full corpus validation**
Run the validator against every record and produce a report of:
- Records with broken source links (404/403 in sources.jsonl)
- Records with evidence_ids pointing to non-existent EV records
- Records with review_due dates in the past
- Records with no evidence_ids (structural orphans)
- Records with empty statement fields

Fix all structural problems found.

**Architecture readiness documentation**
Produce `CORPUS_ARCHITECTURE_HANDOFF.md` containing:
1. The exact check-code → knowledge mapping (how to go from a check code to all relevant KT records)
2. The AEOG phase coverage map (which phases have strong/weak/no knowledge)
3. The contested knowledge register (what the architecture must treat as uncertain)
4. The deprecated check code register (what the architecture must retire)
5. The confidence distribution and what it means for the architecture

**Governance sign-off**
Produce `CORPUS_GOVERNANCE_SIGNOFF.md` stating:
- Number of records by status/confidence
- Open governance backlog items (resolved/unresolved)
- Items that remain uncertain and why
- Explicit statement that this is the canonical input to architecture

### Quality gate
- 0 structural validation errors
- All review_due dates updated
- CORPUS_ARCHITECTURE_HANDOFF.md complete
- CORPUS_GOVERNANCE_SIGNOFF.md signed with timestamp

---

## PART J — ZIP HANDOFF CONTRACT

Every ZIP handoff must follow this protocol:

### What the outgoing session packages

```
CITEABLE_KB_SNN/
├── corpus/              ← UPDATED files (knowledge, sources, evidence, etc.)
├── context/             ← UNCHANGED from previous ZIP (only update if something changed)
├── research/            ← UPDATE COMPLETED_RESEARCH.md with what this session did
│   └── OPEN_QUESTIONS.md  ← UPDATE with resolved/remaining items
├── archive/
│   └── SESSION_LOG.md   ← APPEND this session's entry
├── SESSION_INSTRUCTIONS.md  ← REPLACE with next session's instructions
├── MISSION_CONTROL.md   ← UPDATE checkboxes
└── CHANGELOG.md         ← APPEND this session's change summary
```

### What the session log entry must contain

```markdown
## Session NN — YYYY-MM-DD

### What was done
[List of specific changes made to the corpus]

### Items completed from MISSION_CONTROL checklist
[checkbox list]

### New knowledge added
[KT-NNN: brief description]

### Knowledge enriched
[KT-NNN: what was enriched]

### Sources added
[SRC-NNN: URL and title]

### Governance items resolved
[GB-NNN: how resolved]

### What remains for next session
[Specific items with enough context to continue]

### First action for next session
[The single first thing the next session should do]
```

### Rule: The ZIP must be self-contained
The next session must be able to operate from the ZIP alone, without reading any external transcript, without access to this conversation, and without any briefing beyond what is in the ZIP.

---

## PART K — RESEARCH GOVERNANCE

### Source Authority Hierarchy

| Tier | Type | Examples | Notes |
|---|---|---|---|
| T1 | Official platform documentation | Google Search Central, OpenAI docs, RFC | Authoritative about stated policy; not about effectiveness of own product |
| T2 | Controlled independent research | Ahrefs studies, SSRN preprints with disclosed methodology | T1 for observed behavior; only as strong as their methodology |
| T3 | Reputable practitioner research | SEL, Search Engine Journal, Cloudflare reports | Good for observed patterns; check COI |
| T4 | Vendor research / vendor blog | BrightEdge, SE Ranking blog posts | Authoritative about product data; suspect for efficacy claims |
| T5 | LLM synthesis / generated content | Claude summary, GPT-4 answer, multi-model consensus | Never independent evidence; may corroborate if sources are cited |

**Critical distinctions:**
- A T1 source is authoritative about **its own stated policy**, not about **observed behavior by other parties**
- A T4 vendor source may be accurate about **its own product's data** but is suspect for **comparative or causal claims**
- T5 (LLM agreement) is never independent evidence. If three LLMs all say "X is true," that's correlation of training data, not verification.

### When to CREATE a new knowledge record
- The assertion is genuinely not represented by any existing record
- The assertion is atomic (one thing)
- At least one T1-T3 source supports it
- It is relevant to Citeable's audit scope (AI search citation readiness)

### When to ENRICH an existing record
- New evidence supports or refines the existing assertion
- A better source is found for an existing claim
- Temporal information is updated (e.g., a check was deprecated on a specific date)
- The confidence changes because of new evidence (never change confidence without adding evidence)

### When to ADD new evidence only
- A second source confirms an existing claim
- A corroborating study is found
- A contradicting source is found (add as `contradicts` relationship)

### When to SPLIT a record
- The statement uses "and" to assert two independent facts
- The statement contains both a fact and a recommendation
- The statement conflates correlation and causation

### When to MARK a contradiction
- Two active records make conflicting claims about the same subject
- A new source contradicts an existing record
- An official source contradicts observed behavior (preserve both, mark the gap)

### When to SUPERSEDE
- A newer version of a standard replaces an older version
- A platform officially changes its policy (old policy becomes archived with note "superseded by KT-NNN")

### When to ARCHIVE
- A record is superseded
- A record was duplicated and the weaker version is retired
- A deprecated check code's associated GUIDANCE is no longer actionable

### When to REJECT (do not create)
- The source is T5 only (LLM-generated with no citable backing)
- The assertion is too broad to be actionable ("AI search is growing")
- It duplicates an existing concept with different wording
- The source is a vendor making causal efficacy claims for its own product

### Epistemic discipline rules (the Session 9 failures become explicit rules)

| NEVER DO | CORRECT FRAMING |
|---|---|
| "queue is empty → knowledge is verified" | Queue empty means items were processed; each must be individually resolved |
| "vendor states X → X is universally true" | "Vendor states X as its own policy (T4 for efficacy claims)" |
| "no evidence found → proven false" | "No evidence found to support X as of [date]" |
| "correlation found → causation proven" | "Correlation observed; controlled experiments [do/do not] support causal link" |
| "URL recovered → claim validated" | "Source URL found; claim support must be verified against source content" |
| "one newer source found → contested claim resolved" | "New source added as evidence; disagreement persists until weight of evidence shifts" |
| "confidence: high because two sources agree" | Verify sources are independent; LLM agreement ≠ independent sources |

---

## PART L — FINAL CORPUS

The finished corpus (after Session 13) must contain:

| Component | Minimum |
|---|---|
| Active knowledge records | ~200 (growth from 151 via expansion) |
| Source coverage | All evidence_ids point to confirmed URLs |
| AEOG phase mapping | ≥ 95% of records |
| Check-code coverage | Every active check code has ≥ 1 GUIDANCE + ≥ 1 backing FACT/FINDING |
| Remediation completeness | Every GUIDANCE has problem, action, rationale, tech_context, example |
| Contested knowledge | Explicitly documented; not suppressed |
| Deprecated checks | Explicitly documented with replacement guidance |
| Temporal validity | All records have review_due dates |
| Architecture handoff | CORPUS_ARCHITECTURE_HANDOFF.md complete |

---

## PART M — TARGET HYBRID ARCHITECTURE

### Design rationale

The corpus has three distinct knowledge categories that require different runtime handling:

1. **Determinate knowledge** — facts with high confidence, clear check-code links, uncontested (e.g., "GPTBot is a training crawler, not a search crawler"). These should be served deterministically.

2. **Structured uncertain knowledge** — medium/contested confidence, or knowledge that applies to a check code but requires contextual judgment (e.g., schema vs. citation effects, content structure guidance). These require structured retrieval with confidence flagging.

3. **Novel findings** — the audit finds something not in any existing check code. No GUIDANCE record exists. The system must discover relevant knowledge or acknowledge it cannot.

The architecture must handle all three cases without collapsing them into each other.

### Architecture overview

```
┌─────────────────────────────────────────────────────────┐
│                    AUDIT ENGINE                          │
│  (reads site, runs detectors, produces check codes)      │
└────────────────────────┬────────────────────────────────┘
                         │ check_codes[]
                         ▼
┌─────────────────────────────────────────────────────────┐
│              KNOWLEDGE ROUTER                            │
│                                                          │
│  for each check_code:                                    │
│    ┌─────────────────────┐   ┌────────────────────────┐ │
│    │  KNOWN CHECK PATH   │   │  NOVEL CHECK PATH      │ │
│    │  (check_code in     │   │  (check_code NOT in    │ │
│    │   deterministic     │   │   knowledge base)      │ │
│    │   map)              │   │                        │ │
│    └──────────┬──────────┘   └──────────┬─────────────┘ │
└───────────────┼──────────────────────────┼───────────────┘
                │                          │
     ┌──────────▼──────────┐    ┌──────────▼──────────────┐
     │  DETERMINISTIC      │    │  SEMANTIC RETRIEVAL      │
     │  KNOWLEDGE LAYER    │    │  LAYER                   │
     │                     │    │                          │
     │  Exact lookup:      │    │  Vector similarity over  │
     │  check_code →       │    │  corpus embeddings       │
     │  GUIDANCE + FACT +  │    │  → candidate KT records  │
     │  FINDING records    │    │  → confidence gate       │
     │                     │    │  → citation check        │
     └──────────┬──────────┘    └──────────┬───────────────┘
                │                          │
                └────────────┬─────────────┘
                             │ knowledge_candidates[]
                             ▼
                ┌────────────────────────┐
                │  EVIDENCE RESOLVER     │
                │                        │
                │  • attach sources      │
                │  • flag confidence     │
                │  • flag contested      │
                │  • load remediation    │
                │  • load examples       │
                └────────────┬───────────┘
                             │ enriched_knowledge[]
                             ▼
                ┌────────────────────────┐
                │  LLM SYNTHESIS         │
                │                        │
                │  Allowed to:           │
                │  • combine knowledge   │
                │  • produce narrative   │
                │  • explain tradeoffs   │
                │  • format output       │
                │                        │
                │  NOT allowed to:       │
                │  • add facts           │
                │  • change confidence   │
                │  • cite non-corpus     │
                │    knowledge           │
                └────────────┬───────────┘
                             │
                ┌────────────▼───────────┐
                │  QA GATE               │
                │                        │
                │  • every claim in      │
                │    output must trace   │
                │    to a KT record      │
                │  • contested knowledge │
                │    must be flagged     │
                │  • no unreferenced     │
                │    statistics allowed  │
                └────────────────────────┘
```

---

## PART N — DETERMINISTIC PATH

The deterministic path handles any check code that has a GUIDANCE record in the corpus.

### Lookup procedure

```python
def resolve_check_code(check_code: str, corpus: KnowledgeCorpus) -> Resolution:
    # 1. Find the GUIDANCE record
    guidance = corpus.get_guidance_for_check(check_code)
    if guidance is None:
        return Resolution(path="SEMANTIC", check_code=check_code)

    # 2. Check if deprecated
    if guidance.status == "deprecated":
        return Resolution(
            path="DEPRECATED",
            check_code=check_code,
            message=f"Check code deprecated. See {guidance.uncertainty}",
            replacement_guidance=guidance.relationships
        )

    # 3. Retrieve the backing knowledge chain
    backing_kid = guidance.guidance.rationale  # the KT-NNN it points to
    backing_record = corpus.get(backing_kid)

    # 4. Retrieve evidence
    evidence = corpus.get_evidence_for(guidance.kid) + corpus.get_evidence_for(backing_kid)

    # 5. Flag confidence
    confidence = min(guidance.confidence, backing_record.confidence)
    contested = (backing_record.status == "contested")

    return Resolution(
        path="DETERMINISTIC",
        check_code=check_code,
        guidance=guidance,
        backing=backing_record,
        evidence=evidence,
        confidence=confidence,
        contested=contested,
        examples=guidance.guidance.examples
    )
```

### What deterministic lookup guarantees
- The remediation advice always traces to a specific KT record
- The KT record always traces to specific evidence
- Confidence is the minimum of the chain (conservative)
- Contested knowledge is always flagged to the LLM and to the user
- Deprecated checks are surfaced as deprecated, not silently dropped

---

## PART O — SEMANTIC / RAG PATH

### When it activates
Only when `check_code` is not in the deterministic map — i.e., a novel finding from an audit detector that doesn't match any existing GUIDANCE record.

### What it does NOT do
- It does not generate knowledge. It retrieves candidate knowledge items.
- It does not override contested status. Retrieved items preserve their `status` field.
- It does not cite sources not in the corpus. All citations must trace to SRC records.

### Implementation

```
check_code (novel)
    │
    ▼
Embed the check_code + finding description
    │
    ▼
ANN search over embedded knowledge corpus
(FAISS, pgvector, or similar)
    │
    ▼
Top-K candidates (K=5)
    │
    ▼
CONFIDENCE GATE:
  - cosine similarity ≥ 0.82 → use
  - 0.70–0.82 → flag as "loosely relevant"
  - < 0.70 → discard
    │
    ▼
CITATION CHECK:
  - candidate must have ≥ 1 evidence_id
  - candidate must not be deprecated
  - if contested: include both sides
    │
    ▼
Return: ranked candidates with confidence flags
```

### The vector index is derived. The structured corpus is canonical.

The embedding index is **rebuilt from the JSONL corpus on every corpus update**. It is never edited directly. The corpus JSONL is the source of truth. Embeddings are a retrieval mechanism, not a storage mechanism.

If retrieval finds nothing above the confidence threshold, the system returns:
> "No sufficiently confident knowledge found for this finding. Flagging for human review."

This is a correct and useful answer. It is not a failure.

---

## PART P — LLM BOUNDARY

### What the LLM is allowed to do

- **Combine** multiple knowledge items into a coherent narrative
- **Explain** the rationale behind a recommendation (using the backing FACT/FINDING)
- **Adapt** examples to the specific site context (e.g., substituting the user's actual domain)
- **Explain tradeoffs** when multiple guidance options exist
- **Flag uncertainty** when the backing knowledge is `contested` or `low` confidence
- **Synthesize** a prioritized action plan from multiple findings

### What the LLM is explicitly NOT allowed to do

- **Add new factual claims** not present in the knowledge corpus
- **Cite statistics** not traceable to a KT/SRC record
- **Change confidence ratings** — if the corpus says `medium`, the output must not imply `high`
- **Resolve contested knowledge** — if two knowledge items disagree, the LLM must present both, not pick one
- **Hallucinate sources** — every cited fact must link to an SRC record with a URL
- **Suppress deprecated checks** silently — deprecated checks must be explicitly noted as such

### LLM system prompt contract (required elements)

```
You are Citeable's knowledge synthesis engine.
You have been provided with a structured set of knowledge records, each with:
  - a statement (the fact or guidance)
  - a confidence level (high/medium/low)
  - a status (active/contested/deprecated)
  - evidence records with source citations

Rules:
1. Only assert facts that appear in the provided knowledge records.
2. If a knowledge record is marked contested, present both sides.
3. If a knowledge record is marked low-confidence, say so.
4. If a knowledge record is deprecated, tell the user it is deprecated and why.
5. Every specific statistic or claim you state must be attributable to a specific source.
6. If you cannot find a relevant knowledge record for a finding, say so.
7. Do not add facts from your training data unless they are also in the provided records.
```

---

## PART Q — QA / GROUNDING

The QA gate runs on every LLM output before it reaches the user.

### Checks performed

1. **Claim extraction**: parse the LLM narrative and extract every specific factual claim
2. **Corpus lookup**: for each extracted claim, verify it traces to a KT record
3. **Citation check**: for each KT record used, verify it has at least one EV link
4. **Confidence consistency**: if output says "definitively" or "strongly", the backing KT must be `high/strong`
5. **Contested flag check**: if backing KT is `contested`, the output must contain qualifying language
6. **Deprecated check**: if any deprecated check code is present in output, it must be labeled `[DEPRECATED]`

### Failure handling

| Failure | Action |
|---|---|
| Claim with no corpus backing | Remove claim; add note "removed: no corpus backing" |
| Claim backed by deprecated record | Relabel as deprecated in output |
| Contested knowledge without qualification | Inject qualification: "note: this finding is disputed" |
| LLM invents a statistic | Remove; add note "removed: statistic not in knowledge corpus" |
| No candidates found above threshold | Return structured "insufficient knowledge" response |

---

## PART R — MIGRATION PLAN

Citeable already works. The architecture must be migratable without a big-bang rewrite.

### Phase A — Compatibility (V1.0 behavior preserved)

- No changes to detection logic
- No changes to synthesis_engine.py
- No changes to the SQLite schema
- **New:** Export the governed JSONL corpus into the existing `claims` table format
- **New:** Run side-by-side: old synthesis vs. new knowledge-backed synthesis on the same audit runs
- **New:** Log discrepancies — where does new synthesis differ from old?

Acceptance: New synthesis produces output that is at least as accurate as old on 10 test sites.

### Phase B — Knowledge Extraction (move ownership)

- Retire `REMEDIATION_TEXT` and `ACTION_SNIPPETS` Python dicts
- Replace with lookups into the knowledge corpus (loaded at startup from JSONL or SQLite)
- `PRIORITY_SCORES` becomes a database field (`guidance.priority`) on GUIDANCE records, editable without a code deploy
- All 36 check-code mappings now resolve through the corpus, not Python

Acceptance: No regression on test sites. Priority scores can be edited without code change.

### Phase C — Structured Retrieval (corpus → runtime path)

- Connect the deterministic path: check_code → GUIDANCE → FACT → evidence → LLM context
- Add the QA gate
- Add contested knowledge flagging in output
- Add deprecated check detection

Acceptance: Every finding in output traces to a KT record. No unsourced statistics in output.

### Phase D — Semantic Fallback (RAG for novel findings)

- Build the embedding index from the corpus
- Activate the novel finding path with the confidence gate
- Add the "insufficient knowledge" structured response
- Add human review queue for low-confidence novel findings

Acceptance: Novel findings are either confidently answered or explicitly flagged for review.

### Phase E — Retirement (clean up legacy)

- Remove `CHECK_CODE_TO_CLAIM_IDS` dict from `findings_to_claims.py`
- Remove hardcoded `PRIORITY_SCORES` and `REMEDIATION_TEXT` dicts
- Remove hardcoded `ACTION_SNIPPETS`
- Remove deprecated check codes from the detector suite (or suppress them at the router)

Acceptance: No knowledge is in Python source files. All knowledge is in the corpus.

---

## PART S — IMPLEMENTATION STAGING

### V1.0 (current)
- Deterministic check codes → Python dicts → LLM synthesis
- No corpus integration
- Hardcoded priorities and remediation text

### V1.5 (Phase A + B)
- Corpus replaces Python dicts
- PRIORITY_SCORES, REMEDIATION_TEXT, ACTION_SNIPPETS served from corpus
- Deprecated checks surfaced explicitly
- QA gate added

### V2.0 (Phase C + D)
- Full deterministic path through corpus
- Contested knowledge flagged in output
- Semantic fallback for novel findings
- Human review queue for low-confidence discoveries

### V3.0 (Phase E)
- All legacy Python knowledge pathways retired
- Corpus is the sole knowledge source
- Research ingestion pipeline exists for adding new knowledge

---

## PART T — ARCHITECTURAL RISKS

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Corpus URL rot — sources go 404 | High (over 12 months) | Medium — sourcing breaks | Quarterly URL verification job; archive.org fallback |
| Confidence inflation by LLM | Medium | High — false confidence | QA gate + system prompt constraints |
| Corpus-to-reality lag — AI platforms change policy | High | Medium — stale guidance | review_due fields; regular re-verification sessions |
| Semantic retrieval false positives | Medium | High — wrong guidance | Conservative threshold (0.82) + human review queue |
| Knowledge explosion — corpus grows without governance | Medium | Medium — quality degrades | Session quality gates; editorial review per session |
| Contested knowledge suppression | Low (now explicit) | High — hidden uncertainty | Contested records must be visible in UI |
| Single corpus format dependency | Low | Low — JSONL is portable | Corpus is format-agnostic content; migration is a build step |

---

## PART U — SUCCESS CRITERIA

### Knowledge program succeeds when

1. Every active check code in the live system has a complete GUIDANCE record with problem, action, rationale, evidence, and example
2. ≥ 95% of knowledge records have an AEOG phase mapping
3. All evidence_ids point to sources with confirmed URLs (or explicitly noted as unverified)
4. Contested knowledge is explicitly preserved and documented, not suppressed
5. The check-code-to-knowledge map is complete and correct
6. CORPUS_ARCHITECTURE_HANDOFF.md is produced and reviewed

### Architecture succeeds when

1. Every audit finding that reaches the user traces to a specific KT record
2. Every specific statistic in the output traces to a specific SRC record
3. Contested knowledge is visibly flagged in the output
4. Deprecated check codes are labeled as deprecated
5. Novel findings either produce a confident structured answer (with sources) or produce a structured "insufficient knowledge" response — never a confabulated one
6. Priority scores can be changed without a code deploy
7. A new knowledge item can be added to the corpus and appears in the next audit without a code change

---

## APPENDIX: ARCHITECTURAL OPTIONS COMPARISON

| Criterion | Deterministic Only | Hybrid (Recommended) | Full RAG |
|---|---|---|---|
| Determinism | ✅ Perfect | ✅ For known checks | ❌ Non-deterministic |
| Traceability | ✅ Every claim has a source | ✅ With QA gate | ❌ Hallucination risk |
| Citation integrity | ✅ | ✅ With citation check | ❌ Hard to guarantee |
| Novel finding support | ❌ Cannot handle | ✅ Semantic fallback | ✅ But with low precision |
| Operational complexity | Low | Medium | High |
| Debugging | Easy | Easy (deterministic) / Medium (RAG) | Hard |
| Research integration | Manual | Structured pipeline | Rebuild index |
| Failure behavior | Silent gap | Explicit "insufficient knowledge" | Hallucination |
| Maintenance | Low | Medium | High |
| Cost | Low | Medium (embedding API) | High |
| **Verdict** | Too limiting | **Correct for Citeable** | Inappropriate |

**Recommendation: Hybrid.** The deterministic path handles the majority of audit findings (known check codes with strong knowledge). The semantic fallback handles genuinely novel findings. The QA gate enforces citation integrity on both paths. This gives Citeable the reliability of a deterministic system with the extensibility of a semantic one, without the hallucination risk of a pure RAG approach.

The key design principle: **RAG is a retrieval mechanism, not a knowledge source.** Knowledge comes from the governed corpus. RAG finds the right knowledge for novel inputs. It never creates new knowledge.

---

*This document is the architectural specification. The next action is to build the first ZIP (Session 10) and begin the external knowledge program.*
