# CITEABLE — CURRENT KNOWLEDGE CENSUS
**Investigation Date:** 2026-08-28  
**Status:** Read-only. No modifications made.  
**Scope:** All knowledge sources across MKB, DB, Python dicts, prompts, and ZIPs.

---

## 1. Master Knowledge Base Discovery

**CONFIRMED.** The Master Knowledge Base was found at:

- `vone_finale_codebase.zip → New folder/AEO_GEO_Master_Knowledge_Base_v2.md` (197,925 chars, 1,140 lines)
- Identical copy in `AREOS_Stable_Release_Two_FIXED.zip → stable_release_two/New folder/AEO_GEO_Master_Knowledge_Base_v2.md`

### MKB Structure

The MKB (`AEO_GEO_Master_Knowledge_Base_v2.md`) merges **four source documents**:

| Source | Content | Claims |
|---|---|---|
| `AEO_GEO_Knowledge_Base_Synthesis.md` | **Study A** — 5-model LLM synthesis on AEO/GEO *ranking factors*, schema, crawler behavior, citation-tracking tools, legal constraints | CLM-001–CLM-057 (57 claims) |
| `AEO_GEO_Synthesis_Report.md` | **Study B** — 5-model LLM synthesis on *audit-task automatability*: what can be scripted vs. requires human judgment | C001–C092, M001–M006 (60 claims) |
| `aeo_geo_claims_master.csv` | Machine-readable export of Study B (verified: 0 mismatches against the synthesis report) | Same as Study B |
| `AEO_GEO_Research_Update_and_Source_Directory.md` | 2026-07-28 live-search pass chasing primary sources + 107-source directory | Edits to 6 claims; CLM-057 split |

**Total MKB claims: 117** (57 Study A + 60 Study B, post-split).

### MKB Status at Last Edit (2026-07-28)

The MKB is marked **"DRAFT FOR HUMAN REVIEW"** — no item is auto-approved.  
Status breakdown across both studies:
- **active**: 91 claims
- **unverified**: 12 claims
- **contested**: 8 claims (including CLM-007 "leaning null-to-negative")
- **mixed status** (compound states): 6 claims

### How MKB Relates to the 213 Current DB Claims

**CONFIRMED.** The MKB is the *origin document* from which claims were programmatically ingested into `areos.db`. The MKB itself designed the routing:

| MKB Routing Destination | Count | What Happened |
|---|---|---|
| `claims` table (stage_id corrected) | 9 | Mistagged claims fixed and ingested |
| `audit_phase` table | 12 | Study B workflow claims routed there |
| `tool_landscape` table | 8 | Vendor tool data (CLM-035–CLM-042) |
| `policy_constraints` table | 4 | ToS/legal claims (CLM-043–CLM-046) |
| `sources.yaml` / source-trust criteria | 2 | CLM-021, CLM-022 |
| `claims` table, stage_id = unmapped (correct) | 2 | CLM-008, CLM-020 |
| Build log only (not a claims table) | 6 | M001–M006 process notes |

### What Was Lost in Translation

**STRONGLY INFERRED.** The current DB has 217 rows vs 117 MKB claims — the extra 100 rows are the **C200–C324 series**: a large body of stage-by-stage technical explainers (crawling, rendering, canonicalization, entity recognition, etc.) that appear to have been added in a *subsequent* ingestion pass, likely from a separate AREOS stage-specification document not found in the MKB itself. Their provenance is labeled `official-platform-doc (Documented/T1)` but their *specific origin document* is not tracked in the DB.

**Knowledge lost in transition (CONFIRMED):**
- The MKB's `status` and `confidence` fields (active/contested/unverified, high/medium/low) were **not preserved** in the DB claims table
- The MKB's `source_tier` per-claim vocabulary was partially preserved but normalized inconsistently (Study A uses named tiers; Study B uses T1–T5; both appear in DB with no normalization)
- The 107-source directory from the Research Update is not reflected in the `sources` DB table (which has 0 rows)
- The `claim_scope` routing logic from MKB §0.5 is partially implemented but `audit_phase` rows have null descriptions

---

## 2. Knowledge Source Inventory

| Source | Location | Format | Items | Notes |
|---|---|---|---|---|
| **Master Knowledge Base v2** | `vone_finale_codebase.zip` | Markdown, 1,140 lines | 117 claims | Origin document; DRAFT FOR HUMAN REVIEW |
| **DB `claims` table** | `areos.db` | SQLite | 217 rows | 188 active, 21 deprecated, 8 contested |
| **DB `check_code_mappings`** | `areos.db` | SQLite | 36 mappings | Links 36 check_codes → 6 unique claim IDs |
| **DB `tool_landscape`** | `areos.db` | SQLite | 8 rows | CLM-035–CLM-042, vendor tool data |
| **DB `policy_constraints`** | `areos.db` | SQLite | 4 rows | CLM-043–CLM-046, ToS/legal |
| **DB `audit_phase`** | `areos.db` | SQLite | 33 rows | STAGE-01–22 + AP-01–AP-10; descriptions mostly null |
| **DB `sources`** | `areos.db` | SQLite | 0 rows | Table exists; empty |
| **`REMEDIATION_TEXT`** | `areos/auditors/synthesis_engine.py` | Python dict | 36 entries | One per check_code; the actual fix text |
| **`PRIORITY_SCORES`** | `areos/auditors/synthesis_engine.py` | Python dict | 36 entries | Integer 1–13 per check_code |
| **`ACTION_SNIPPETS`** | `areos/auditors/audit_orchestrator.py` | Python dict | 12 entries | Code/config snippets for subset of checks |
| **`MANUAL_CARD_GUIDANCE`** | `areos/auditors/audit_orchestrator.py` | Python dict | 6 entries | Manual review guidance for C052, C053, C073, C077, C090, DEFAULT |
| **LLM prompts** | `areos/llm/synthesis_pipeline.py` | Python/Jinja | ~5 prompts | Domain knowledge embedded in prompt text |
| **AREOS_KNOWLEDGE_GOVERNANCE_SPEC.md** | ZIP | Markdown, 348 lines | Rules | Claim quality floor, lifecycle rules |
| **AREOS_KNOWLEDGE_INGESTION_SPEC.md** | ZIP | Markdown | Ingestion rules | How claims are loaded; lint rules |
| **MASTER_INVENTORY_REPORT.md** | ZIP | Markdown, 59KB | Report | Historical inventory of the ingestion |
| **MKB Source Directory (§6)** | ZIP (in MKB) | Markdown table | 107 sources | Tier-tagged; NOT in DB sources table |

---

## 3. AEOG / AREOS Stage System

### CONFIRMED: Two Overlapping Stage Systems

The DB `audit_phase` table reveals **two parallel taxonomies** that were never fully unified:

**System 1: STAGE-01 through STAGE-22** (22 technical audit stages, descriptions all NULL in DB)
These correspond to the original AREOS retrieval-pipeline stages used in `check_code_mappings`. Claims from Study B were tagged to these stages (C010→STAGE-01, C011→STAGE-02, etc.).

**System 2: AP-01 through AP-10** (10 business-facing audit phases, some with descriptions)

| Phase | Name | Description |
|---|---|---|
| AP-01 | Business Scoping & Strategy | Goals, KPIs, engine scope, competitor set |
| AP-02 | Schema & JSON-LD Structure | (no description in DB) |
| AP-03 | Content Extractability | (no description in DB) |
| AP-04 | Authority & Backlinks | (no description in DB) |
| AP-05 | Citation Measurement | Prompt set design and AI citation measurement |
| AP-06 | Competitive Intelligence | Competitor comparison, backlink/mention profile |
| AP-07 | Reporting & Remediation | Prioritization, report production, monitoring setup |
| AP-08 | Legal & Policy Compliance Review | ToS, Gemini API terms, SerpApi case law |
| AP-09 | Competitive & Tool Landscape Review | Citation monitoring tools (Profound, Otterly, etc.) |
| AP-10 | Remediation Planning & Prioritisation | Synthesise AP-01 through AP-09 into roadmap |

**CONFIRMED: The 213 active DB claims are tagged to AP-phases, not STAGE-xx phases.** The check_code_mappings still use STAGE-xx internally, but the claims were re-tagged to AP-xx during a migration. This creates a **broken join**: check_code → claim_id works, but claim.stage_id = "AP-03" while check_code_mappings was built for STAGE-xx logic. The technical pipeline works only because it looks up claim by claim_id, not by stage.

---

## 4. The 217 Claims — Classification Overview

### By Claim Type (from DB)

| Claim Type | Count | What It Means |
|---|---|---|
| `stage-technical-fact` | 48 | C200–C324 series: factual statements about how crawling/rendering/indexing works |
| `automatability_rating` | 48 | Study B: what can vs. cannot be automated in an AEO/GEO audit |
| `stage-technical-explainer` | 21 | C200–C324: conceptual overviews of pipeline stages |
| `other` | 21 | Miscellaneous from Study A (ranking factors, tool landscape items, etc.) |
| `crawler-behavior` | 12 | CLM-019–CLM-031: documented AI crawler behavior |
| `stage-technical-explanation` | 9 | Additional C2xx explainers |
| `stage-official-evidence` | 9 | Official source citations in the C2xx series |
| `stage-industry-consensus` | 9 | Industry consensus statements in C2xx series |
| `ranking-factor` | 9 | Study A: does X affect AI citation? |
| `ai-citation-effect` | 8 | Study A: empirical data on schema/content vs. citation |
| `process_note` | 5 | M001–M006 + extras: research methodology notes |
| `empirical_stat` | 5 | Statistical findings (C017, C018, C051, C076, etc.) |
| `schema-validity` | 4 | Study A CLM-007, CLM-005, etc. |
| `outcome` | 4 | C325–C328: deprecated outcome logs |
| `serp-feature` | 3 | CLM-001–CLM-003: FAQ rich results deprecation |
| `tooling_existence` | 1 | M003: aeojs.org existence |
| `claim_type_caveat` | 1 | C013: robots.txt voluntary convention caveat |

### By Claim Scope

| Scope | Count | What It Is |
|---|---|---|
| `retrieval-pipeline` | 179 | Claims in the runtime retrieval pipeline |
| `audit-workflow` | 22 | Non-automatable workflow/strategy claims |
| `general-knowledge` | 16 | Tool landscape, legal/policy, source-trust criteria |

### By Status

| Status | Count |
|---|---|
| `active` | 188 |
| `deprecated` | 21 |
| `contested` | 8 |

**Note:** 21 deprecated rows include C325–C328 (outcome logs) + ~17 others from prior ingestion passes with placeholder statements.

---

## 5. Hardcoded Python Knowledge Inventory

### REMEDIATION_TEXT (synthesis_engine.py) — 36 entries

All 36 entries exactly mirror the 36 check_code_mappings. This is the **"why it matters"** text the LLM receives.

| Check Code | Claim Backed | Topic Area |
|---|---|---|
| CRAWLER_FULLY_BLOCKED | C050 ✓ | Robots.txt / AI crawler access |
| CRAWLER_PARTIAL | C050 ✓ | Robots.txt / AI crawler access |
| CRAWLER_ALLOWED | C050 ✓ | Robots.txt (positive signal) |
| NO_DIRECTIVE | C050 ✓ | Robots.txt missing directive |
| GPTBOT_MISSING | C050 ✓ | GPTBot not explicitly allowed |
| GOOGLE_EXTENDED_MISSING | C050 ✓ | Google-Extended missing |
| INVALID_CRAWL_DELAY | C050 ✓ | Crawl-delay too high |
| LLMS_TXT_MISSING | C051 ✓ | llms.txt not present |
| LLMS_TXT_EMPTY_CONTENT | C051 ✓ | llms.txt exists but empty |
| LLMS_TXT_MISSING_H1 | C051 ✓ | llms.txt missing heading |
| LLMS_TXT_MISSING_SECTION | C051 ✓ | llms.txt missing section |
| LLMS_TXT_NO_LINKS | C051 ✓ | llms.txt has no links |
| JSON_PARSE_FAILURE | C054 ✓ | Schema.org JSON-LD malformed |
| MISSING_TYPE | C054 ✓ | Schema missing @type |
| MISSING_REQUIRED_FIELD | C054 ✓ | Schema missing required field |
| MISSING_RECOMMENDED_FIELD | C054 ✓ | Schema missing recommended field |
| UNKNOWN_FIELD | C054 ✓ | Schema has unknown field |
| UNKNOWN_SCHEMA_TYPE | C054 ✓ | Schema type not recognised |
| EXTRACTABILITY_NONE | C058 ✓ | Content not extractable |
| EXTRACTABILITY_LOW | C058 ✓ | Content hard to extract |
| EXTRACTABILITY_MEDIUM | C061 ✓ | Content partially extractable |
| EXTRACTABILITY_HIGH | C057 ✓ | Content well-structured |
| NO_LIST_OR_TABLE | C050 ✓ | Missing list/table formatting |
| ANSWER_NOT_NEAR_TOP | C051 ✓ | Answer not near top of page |
| ANSWER_NOT_SELF_CONTAINED | C057 ✓ | Answer requires context |
| ANSWER_NOT_FACTUALLY_SPECIFIC | C061 ✓ | Answer lacks specifics |
| ANSWER_FORMAT_GOOD | C050 ✓ | Positive: format good |
| NOSNIPPET_BLOCKING_AI | C310 ✓ | nosnippet blocking AI |
| CITATION_NOT_OBSERVED | C071 ✓ | Not cited in AI response |
| CITATION_OBSERVED | C071 ✓ | Cited in AI response |
| CITATION_WHY_UNKNOWN | C073 ✓ | Citation reason unclear |
| WIKIPEDIA_ENTITY_MISSING | C284 ✓ | Entity not on Wikipedia |
| AUTHORITY_DR_LOW | C292 ✓ | Low domain rating |
| AUTHORITY_PROFILE_GOOD | C293 ✓ | Good authority profile |
| BRAND_MENTIONS_STAGNANT | C293 ✓ | Brand mentions not growing |
| REFERRING_DOMAINS_CRITICAL | C292 ✓ | Critical referring domain issue |

**Key finding:** All 36 REMEDIATION_TEXT entries map to only **6 unique claim IDs**: C050, C051, C054, C057, C058, C061 (+ C071, C073, C284, C292, C293, C310). That is **6 claims doing the citation work for 36 checks**.

### ACTION_SNIPPETS (audit_orchestrator.py) — 12 entries

Code/config implementation guidance for a subset of checks:

| Check Code | Content Type |
|---|---|
| CRAWLER_FULLY_BLOCKED | robots.txt config snippet |
| LLMS_TXT_MISSING | llms.txt template |
| JSON_PARSE_FAILURE | JSON-LD structure example |
| MISSING_REQUIRED_FIELD | Schema field completion guide |
| NO_LIST_OR_TABLE | HTML formatting example |
| ANSWER_NOT_NEAR_TOP | Content restructuring guidance |
| ANSWER_NOT_SELF_CONTAINED | Content completeness guidance |
| ANSWER_NOT_FACTUALLY_SPECIFIC | Content specificity guidance |
| AUTHORITY_DR_LOW | Link-building strategy |
| REFERRING_DOMAINS_CRITICAL | Domain authority strategy |
| BRAND_MENTIONS_STAGNANT | Brand mention strategy |
| WIKIPEDIA_ENTITY_MISSING | Wikipedia entity creation guide |

### MANUAL_CARD_GUIDANCE (audit_orchestrator.py) — 6 entries

Guidance for manual review cards (bypasses check_code_mappings entirely):

| Card ID | Purpose |
|---|---|
| C052 | Manual content quality / depth assessment |
| C053 | Manual JSON-LD semantic match assessment |
| C073 | Manual citation attribution investigation |
| C077 | Manual sentiment/framing review |
| C090 | Manual root cause correlation analysis |
| DEFAULT | Fallback guidance for any unrecognised manual card |

### PRIORITY_SCORES (synthesis_engine.py) — 36 entries

Integer scores 1–13 for each check_code. **1 = most urgent, 13 = least urgent** (CRAWLER_FULLY_BLOCKED = 1; NO_DIRECTIVE = 13).

---

## 6. Knowledge Clusters and Duplication Map

The 36 check codes resolve to just **6 underlying claim IDs**. This is the most important structural finding:

### Cluster 1: AI Crawler Access (C050)
**Underlying concept:** AI crawlers must be explicitly allowed access via robots.txt/directives.
- **DB claims:** C050 (statement), C011, C012, C013, C014, C015, C021 (context claims)
- **Check codes backed:** CRAWLER_FULLY_BLOCKED, CRAWLER_PARTIAL, CRAWLER_ALLOWED, NO_DIRECTIVE, GPTBOT_MISSING, GOOGLE_EXTENDED_MISSING, INVALID_CRAWL_DELAY, NO_LIST_OR_TABLE, ANSWER_FORMAT_GOOD (9 checks → 1 claim)
- **Python remediation:** 9 REMEDIATION_TEXT entries + 1 ACTION_SNIPPET
- **MKB basis:** Study B C011–C021, Study A CLM-019–CLM-031
- **Duplication:** MKB Study A + Study B both cover crawlers from different angles; Python has 9 variants of essentially the same fix

### Cluster 2: llms.txt Completeness (C051)
**Underlying concept:** A well-formed llms.txt helps AI systems understand site content.
- **DB claims:** C051
- **Check codes backed:** LLMS_TXT_MISSING, LLMS_TXT_EMPTY_CONTENT, LLMS_TXT_MISSING_H1, LLMS_TXT_MISSING_SECTION, LLMS_TXT_NO_LINKS, ANSWER_NOT_NEAR_TOP (6 checks → 1 claim)
- **MKB basis:** C016, C017, C018 (llms.txt existence and adoption stats)

### Cluster 3: Schema.org Validity (C054)
**Underlying concept:** Valid JSON-LD schema markup is required for structured data features.
- **DB claims:** C054
- **Check codes backed:** JSON_PARSE_FAILURE, MISSING_TYPE, MISSING_REQUIRED_FIELD, MISSING_RECOMMENDED_FIELD, UNKNOWN_FIELD, UNKNOWN_SCHEMA_TYPE (6 checks → 1 claim)
- **MKB basis:** Study A CLM-005, CLM-007, CLM-014, CLM-052, CLM-057

### Cluster 4: Content Extractability (C057, C058, C061)
**Underlying concept:** AI systems need to extract clean, structured answers from pages.
- **DB claims:** C057 (answer structure), C058 (JS/iframe blocking), C061 (content type)
- **Check codes:** EXTRACTABILITY_NONE, EXTRACTABILITY_LOW, EXTRACTABILITY_MEDIUM, EXTRACTABILITY_HIGH, ANSWER_NOT_SELF_CONTAINED, ANSWER_NOT_FACTUALLY_SPECIFIC
- **MKB basis:** Study B C030–C036, C052, C058, C061

### Cluster 5: AI Citation Observation (C071, C073)
**Underlying concept:** Whether and why a site appears in AI-generated responses.
- **DB claims:** C071, C073
- **Check codes:** CITATION_NOT_OBSERVED, CITATION_OBSERVED, CITATION_WHY_UNKNOWN
- **MKB basis:** Study B C071–C078, Study A CLM-010–CLM-017

### Cluster 6: Entity & Authority (C284, C292, C293, C310)
**Underlying concept:** Domain authority, entity recognition, and snippet control.
- **DB claims:** C284, C292, C293, C310
- **Check codes:** WIKIPEDIA_ENTITY_MISSING, AUTHORITY_DR_LOW, REFERRING_DOMAINS_CRITICAL, AUTHORITY_PROFILE_GOOD, BRAND_MENTIONS_STAGNANT, NOSNIPPET_BLOCKING_AI

---

## 7. AEOG Coverage Map by AP Phase

| Phase | DB Claims | Check Codes | Python Remediation | Coverage | Key Gap |
|---|---|---|---|---|---|
| AP-01: Business Scoping | 13 | 0 | 0 | WEAK | No runtime checks; all human-judgment claims |
| AP-02: Schema & JSON-LD | 36 | 6 | 6 remediation + 1 snippet | MODERATE | Many C2xx claims unreachable; only 6 checks active |
| AP-03: Content Extractability | 112 | 7 | 7 remediation + 4 snippets | STRONG | Largest claim volume; well-covered by checks |
| AP-04: Authority & Backlinks | 5 | 3 | 3 remediation + 2 snippets | WEAK | Few checks, limited remediation depth |
| AP-05: Citation Measurement | 26 | 3 | 3 remediation | WEAK | Complex topic, very few checks; CLM-series unmapped |
| AP-06: Competitive Intelligence | 3 | 0 | 0 | MISSING | Claims exist, no checks or remediation |
| AP-07: Reporting & Remediation | 4 | 0 | 0 | MISSING | Human workflow, not automated |
| AP-08: Legal & Policy | 4 | 0 | 0 | LATENT | policy_constraints table populated but not used by runtime |
| AP-09: Tool Landscape | 10 | 0 | 0 | LATENT | tool_landscape table populated but not used by runtime |
| AP-10: Remediation Planning | 0 | 0 | 0 | MISSING | Not represented anywhere |

---

## 8. Knowledge Quality Buckets

| Bucket | Count (approx.) | Description |
|---|---|---|
| **CANONICAL CANDIDATE** | ~60 | Well-supported, active-status, mapped to checks or retrievable; primarily C050, C051, C054, C057–C061, C071, C073, C284, C292, C293, C310, and the well-sourced CLM-series crawler behavior claims |
| **NEEDS VERIFICATION** | ~35 | Active in DB but MKB marks as `unverified` or single-source; CLM-011–CLM-015, CLM-018, CLM-020, C034–C035, and parts of the C2xx series without inline source tags |
| **NEEDS RECONCILIATION** | ~8 | Contested in MKB: CLM-007, CLM-050, CLM-051, CLM-052, CLM-054 (qualitative part) |
| **DUPLICATE** | ~40 | C200–C324 series largely repeats Study A/B substance in different phrasing; multiple C2xx claims say the same thing about crawling/rendering |
| **PROCESS / METADATA** | ~11 | M001–M006 + audit_phase claims without runtime role |
| **HISTORICAL** | ~25 | C325–C328 (deprecated outcomes) + ~21 other deprecated rows |
| **TOOL LANDSCAPE** | 8 | CLM-035–CLM-042 in `tool_landscape` table; correct destination but not productized |
| **LEGAL/POLICY** | 4 | CLM-043–CLM-046 in `policy_constraints` table; correct destination but not productized |
| **UNKNOWN** | ~26 | AP-06/AP-07 workflow claims with no runtime connection; general-knowledge scope items |

---

## 9. Latent Knowledge (Exists but Runtime-Unreachable)

| Knowledge | Location | Why Unreachable |
|---|---|---|
| C200–C324 (~100 claims) | `claims` table | No entry in `check_code_mappings`; no semantic fallback |
| CLM-001–CLM-057 (Study A) | `claims` table, mostly | Only CLM-057→STAGE-12 and a few others have check mappings; most CLM-series is unmapped |
| C001–C005, C072, C080–C092 (AP-01/AP-06/AP-07) | `claims` table | Tagged audit-workflow; no check codes exist for these |
| Tool landscape (CLM-035–CLM-042) | `tool_landscape` table | Table not queried by any runtime path |
| Policy constraints (CLM-043–CLM-046) | `policy_constraints` table | Table not queried by any runtime path |
| 107 sources (MKB §6 Research Update) | ZIP only | `sources` table in DB is empty; never ingested |
| MANUAL_CARD_GUIDANCE (C052, C053, C073, C077, C090) | Python dict | Accessed by manual review path only; bypasses `check_code_mappings` entirely |

---

## 10. True Knowledge Count

### Raw Records
| Source | Count |
|---|---|
| DB `claims` active | 188 |
| DB `claims` deprecated | 21 |
| DB `claims` contested | 8 |
| DB `tool_landscape` | 8 |
| DB `policy_constraints` | 4 |
| DB `audit_phase` | 33 |
| `REMEDIATION_TEXT` Python entries | 36 |
| `ACTION_SNIPPETS` Python entries | 12 |
| `MANUAL_CARD_GUIDANCE` Python entries | 6 |
| `PRIORITY_SCORES` Python entries | 36 |
| MKB source directory (not in DB) | 107 |
| **Total raw records** | **~459** |

### Distinct Knowledge Concepts (Estimated)

After deduplication across MKB ↔ DB ↔ Python:

| Estimate | Count | Basis |
|---|---|---|
| **Conservative** | ~55 | Only the 6 claim-backed check clusters + well-evidenced CLM-series |
| **Likely** | ~90 | Adding well-sourced C2xx technical facts + uncontested Study A/B claims |
| **Upper** | ~130 | Including uncertain/single-source items that could be verified |

**The MKB itself has 117 claims, but many overlap conceptually.** The C2xx series (100 DB claims not in MKB) adds ~30–40 distinct technical facts about crawling/indexing.

### Currently Operational (Runtime-Active)
**36 check codes → 12 distinct claim IDs** are what actually power today's audit reports. That is the entire productized knowledge corpus.

---

## 11. Source Census

### Sources Confirmed Across All Knowledge Materials

| Source Type | Count in MKB § 6 | Count in DB sources table | Status |
|---|---|---|---|
| Official platform docs (Google Search Central, OpenAI, Anthropic, Perplexity, W3C) | ~40 | 0 | Not ingested to DB |
| Primary research (Ahrefs, academic papers) | ~20 | 0 | Not ingested to DB |
| Reputable practitioners (named researchers, major publications) | ~25 | 0 | Not ingested to DB |
| Vendor blogs / forum posts | ~15 | 0 | Not ingested to DB |
| Internal/n/a (no external source) | ~7 | 0 | — |

**CONFIRMED: The `sources` DB table has 0 rows.** All 107 sources from the MKB Research Update exist only in the ZIP file. They were never loaded.

### Claim-Level Source URLs (in `claims.source_url`)
All 217 DB claims have `source_url` values (backfilled from `AREOS_Stable_Release_Final.zip` in an earlier session). These are claim-level URLs, not a normalized sources table. Duplicate URLs exist across claims (same Google Search Central page backing many claims).

---

## 12. Knowledge Conflicts (Identified in MKB)

| Conflict | Claims | Nature |
|---|---|---|
| Schema.org → AI citation volume | CLM-007, CLM-052 | MKB marks "contested, leaning null-to-negative" — schema may not increase citation frequency |
| Schema → entity identification | CLM-057 vs CLM-052 | Split claim: schema *does* help entity disambiguation even if citation volume is contested |
| robots.txt / PerplexityBot compliance | C013 | Updated 2026-07-28: Cloudflare report confirms bots evade robots.txt — voluntary convention without enforcement |
| Google Consumer ToS enforcement | CLM-044 | Materially changed: DMCA theory dismissed July 20 2026; enforcement path now uncertain |
| AI-citation-effect of structured data | CLM-010–CLM-015 | Multiple studies, conflicting results, mixed COI issues |
| Page speed / Core Web Vitals → AI citation | CLM-055 | No evidence link confirmed; active but weak |

---

## 13. Knowledge Gaps by Phase

### Clearly Missing
- **AP-10 (Remediation Planning):** No claims, no checks, no remediation. The synthesis step itself has no knowledge backing.
- **Competitive analysis automation (AP-06):** Claims exist (C080–C082) but no checks or remediation.
- **Content freshness / update cadence:** C060 exists but unmapped; no check for it.
- **Heading hierarchy / semantic HTML structure (C050):** Partially covered; no dedicated structured check.
- **Multi-engine citation sampling methodology:** C071–C078 exist but 3 of 8 unmapped.

### Probably Missing
- **JavaScript rendering detection:** C030, C034 exist but no active check for JS-specific rendering failures.
- **Canonicalization issues:** C040 unmapped; redirect chains not covered by active checks.
- **Duplicate content detection:** C041 unmapped.
- **Backlink quality vs. quantity distinction:** C081 unmapped; only domain rating covered.

### Unknown
- Whether STAGE-01 through STAGE-22 ever had named descriptions (descriptions are NULL in DB).
- Whether a separate stage specification document exists (separate from the MKB) that defined those 22 stages.

---

## 14. Items Requiring Future Web Verification

Items the current system actively uses with weak or contested provenance:

| Item | Check Code | Issue |
|---|---|---|
| C050 statement re: AI crawlers | CRAWLER_FULLY_BLOCKED etc. | Statement correct but source_url is a general Google Search Central page, not the specific AI-crawler guidance |
| C051 re: llms.txt | LLMS_TXT_MISSING etc. | MKB marks C016–C018 as showing llms.txt has "no measurable effect" — contradicts remediation urgency |
| CLM-013 / C013 | robots.txt caveat | PerplexityBot/Bytespider reported to evade robots.txt — changes the remediation advice |
| CLM-044 | Policy constraints | Court ruling changes the legal landscape; claim needs update |
| CLM-050, CLM-051 | Citation ranking | Cyrus Shepard meta-analysis noted in MKB but not fetched |
| PRIORITY_SCORES | All checks | Scores (1–13) have no evidential basis documented; entirely heuristic |

---

## 15. Final Plain-Language Summary

### What Citeable knows today
Two independent 5-model LLM research studies (117 claims total in the MKB), plus a large body of stage-by-stage technical explainers about how AI search works (the C200–C324 series, ~100 claims), plus hardcoded remediation text and code snippets for 36 specific audit checks.

### Where that knowledge lives
Fragmented across: the MKB document (ZIP, never fully ingested), the DB claims table (217 rows), four separate DB tables (tool_landscape, policy_constraints, audit_phase, sources—the last empty), and Python dicts in synthesis_engine.py and audit_orchestrator.py.

### How much is genuinely distinct
**~90 distinct concepts** (likely estimate). The MKB has 117, but ~30 overlap conceptually between Study A and B. The C2xx series adds ~30–40 new technical facts.

### How much is duplicated
**High duplication.** The same crawling/robots.txt concept is represented in: Study B C011–C021 (11 claims), Study A CLM-019–CLM-031 (13 claims), 9 REMEDIATION_TEXT Python entries, 1 ACTION_SNIPPET, and 1 primary DB claim (C050). That is at least 35 representations of one core concept.

### How much is currently operational
**36 check codes → 12 claim IDs.** Everything else is latent. This is a tiny fraction of the total knowledge.

### How much is latent
**~170+ claims** are in the DB but never reached by the runtime system. The 107 source records from the MKB Research Update were never loaded. The `policy_constraints` and `tool_landscape` tables are populated but never queried.

### How much is uncertain
**~35 claims** are either marked unverified, contested, or are single-source. The PRIORITY_SCORES have no evidential basis. The C2xx series has source URLs but no passage-level evidence.

### Which AEOG phases are strong
**AP-03 (Content Extractability)** — 112 claims, 7 active checks, well-covered.

### Which AEOG phases are weak
**AP-05, AP-06, AP-07, AP-08, AP-09, AP-10** — minimal or zero runtime coverage despite having claims.

### What we need to verify
The llms.txt efficacy (does it actually help?), robots.txt voluntary-only status, schema vs. citation volume (contested), PRIORITY_SCORES basis, CLM-044 legal situation.

### What we need to research
Stage names for STAGE-01 through STAGE-22 (descriptions are null), content freshness checks, JavaScript rendering detection gaps, canonicalization checks, multi-engine citation methodology.

### What we still do not know
The exact origin document for the C200–C324 series. Whether the 22 STAGE-xx descriptions exist somewhere. Whether the 107 MKB sources have been verified since the 2026-07-28 research pass.
