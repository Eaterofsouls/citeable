# AEOGEO Lifecycle vs Citeable Diagnostic Architecture — Forensic Assessment

> **Central Question:** *Given the parts of the AEOGEO lifecycle that are actually automatable, does Citeable's current diagnostic/checking architecture make sufficiently good use of that automation potential?*
>
> **Answer: No. Citeable is leaving meaningful automation potential on the table.** The existing architecture covers roughly 40-50% of the automatable lifecycle responsibilities identified in Study B. The most critical gap is not missing features but a **fundamental input problem**: the content-format checks evaluate fake placeholder text instead of real crawled HTML, which invalidates an entire scoring layer. Beyond that, several fully-automatable checks identified by 5/5 model consensus in Study B have no implementation at all.

---

## 1. Bird's-Eye System Understanding

### What Citeable Is

Citeable is a **point-in-time AEO/GEO readiness auditor** that measures whether a website can be found, correctly parsed, and cited by AI answer engines. It runs automated diagnostics, combines them with human manual review, and produces a scored remediation plan backed by a governed knowledge base.

### Architecture Layers

```
┌───────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE (studio.js)                    │
├───────────────────────────────────────────────────────────────────┤
│                      API LAYER (FastAPI)                          │
│   POST /orchestrate → POST /runs/{id}/synthesize → GET /full     │
├───────────────────────────────────────────────────────────────────┤
│              ORCHESTRATOR (audit_orchestrator.py)                 │
│  Runs 6 diagnostic layers → findings[] → score → wizard cards    │
├─────────┬──────────┬────────────┬───────────┬──────────┬─────────┤
│ Layer 1 │ Layer 2  │  Layer 3   │  Layer 4  │ Layer 5  │ Layer 6 │
│ Access  │ Schema   │  Content   │ Authority │ Citation │  Score  │
│ robots  │ JSON-LD  │  Format    │ DR/Links  │ Live AI  │ Layered │
│ llms    │ validate │ Zyppy      │ Wiki/PR   │ Sample   │ 100pts  │
├─────────┴──────────┴────────────┴───────────┴──────────┴─────────┤
│              FINDINGS → wire_finding() → WiredFinding             │
├───────────────────────────────────────────────────────────────────┤
│         KNOWLEDGE ROUTER (V2 kb_check_code_map → RAG)            │
├───────────────────────────────────────────────────────────────────┤
│    SYNTHESIS ENGINE → RemediationPlan → LLM 3-step Pipeline       │
├───────────────────────────────────────────────────────────────────┤
│    KNOWLEDGE BASE (JSONL corpus → SQLite → claims VIEW)           │
│    216 records, 50 check codes mapped, 42 GUIDANCE entries        │
└───────────────────────────────────────────────────────────────────┘
```

### How Diagnostics Fit

The orchestrator ([audit_orchestrator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py)) is the **single entry point** for all automated checks. It calls 5 specialized auditor modules in sequence, collects findings as `{code, severity, message, page_url}` dicts, computes a layered score, stores results in SQLite, and selects manual review wizard cards. The findings then flow through `wire_finding()` into the knowledge-base resolution pipeline.

### The Data Flow

```
Target Domain
  → robots_checker.parse_robots_txt() → Access findings
  → robots_checker.parse_llms_txt() → llms.txt findings
  → _fetch_and_validate_schema() → Schema findings
  → content_format_auditor.audit_page_format() → Content findings [⚠️ uses fake text]
  → authority_auditor.audit_domain_authority() → Authority findings
  → citation_sampler.sample_citations() → Citation findings
  → scoring.compute_layered_score() → 5-layer score
  → synthesis_engine.synthesise() → RemediationPlan
  → wire_finding() per code → kb_check_code_map lookup → Resolution
  → Format markdown → UI rendering
```

---

## 2. AEOGEO Automation Coverage Map

Study B identifies **60 canonical claims** (C001–C092 + M-series). Of these, **48 are `automatability_rating` claims** about specific audit activities. I classify each by its Study B automatability verdict and map it against Citeable's current implementation.

### Legend
- ✅ = Citeable covers this
- ⚠️ = Citeable partially covers or covers incorrectly
- ❌ = Citeable does not cover this
- 🚫 = Study B says NOT automatable (correct to skip)

### Fully Automatable Activities (Study B: "fully automatable")

| Claim | Activity | Citeable | Assessment |
|-------|----------|----------|------------|
| C010 | Full-site crawl + sitemap validation | ❌ | **Not implemented.** Citeable does not crawl beyond the homepage or validate sitemaps. |
| C011 | robots.txt per-crawler AI-bot parsing | ✅ | **Implemented well.** [robots_checker.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/robots_checker.py) tracks 13 AI crawlers. Generates `CRAWLER_FULLY_BLOCKED`, `CRAWLER_PARTIAL`, `GPTBOT_MISSING`, etc. |
| C016 | llms.txt existence + syntax check | ✅ | **Implemented.** Checks HTTP 200 status, H1 heading, sections, links. But Study B's own runtime-engineer pass flags this as *automatable but possibly not worth automating* given zero measurable effect (C017/C018). |
| C019 | Server access log parsing for AI crawl hits | ❌ | **Not implemented.** Citeable has no log ingestion capability. |
| C030 | Raw HTML vs rendered DOM diffing | ❌ | **Not implemented.** Study B calls this "one of the cleanest, most mature checks." Citeable could diff headless-rendered vs raw HTML but does not. |
| C040 | Redirect chains, canonicals, HTTP status codes | ❌ | **Not implemented.** Citeable does not follow redirect chains or validate canonical tags. |
| C041 | Duplicate/near-duplicate content detection | ❌ | **Not implemented.** |
| C050 | Structural content checks (headings, lists, paragraph length, boilerplate ratio) | ⚠️ | **Partially implemented but on wrong input.** [content_format_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/content_format_auditor.py) checks heading hierarchy, lists, tables, paragraph structure — but is fed `sample_content` (a hardcoded string from studio.js), NOT the actual page HTML. |
| C053 | JSON-LD syntax validation + required properties | ✅ | **Implemented well.** [schema_validator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/schema_validator.py) validates @type, required/recommended fields, JSON parse errors. Fetches real page HTML. |
| C060 | Freshness/update-cadence checks | ❌ | **Not implemented.** No date comparison, stale content detection, or schema date validation. |
| C071 | Execute fixed prompt set across AI engines | ✅ | **Implemented.** [citation_sampler.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/citation_sampler.py) queries Perplexity + Gemini APIs with ToS compliance. |
| C075 | Citation frequency/share-of-voice computation | ⚠️ | **Minimal.** Citeable reports cited/not-cited binary. No share-of-voice, no competitive benchmarking, no trend tracking. |
| C092 | Ongoing monitoring/alerting on regressions | ❌ | **Not implemented.** Citeable is point-in-time only; no scheduled scans. |

### Partially Automatable Activities (Study B: "partially automatable")

| Claim | Activity | Citeable | Assessment |
|-------|----------|----------|------------|
| C002 | Selecting in-scope AI engines | 🚫 | Correct to skip — human judgment. Citeable hardcodes Perplexity + Gemini. |
| C003 | Identifying competitor set | ❌ | Not implemented. Could extract competitor mentions from AI answers. |
| C014 | Cross-check robots.txt vs actual crawler behavior | ❌ | Not implemented — requires log access. |
| C015 | Crawler authenticity via reverse-DNS | ❌ | Not implemented. |
| C021 | CDN/WAF bot-blocking detection | ❌ | Not implemented. |
| C033 | Test lazy-loaded/hidden content for AI visibility | ❌ | Not implemented. |
| C036 | Cloaking detection (spoofed UA diffing) | ❌ | Not implemented. |
| C055 | Structured data vs Rich Results policy | ⚠️ | Partial — schema_validator checks fields but not Google-specific eligibility rules. |
| C056 | Entity verification (sameAs, Wikipedia, Wikidata) | ⚠️ | authority_auditor checks `WIKIPEDIA_ENTITY_MISSING` but does NOT verify sameAs links or Wikidata entries. |
| C057 | NER extraction vs Schema.org consistency | ❌ | Not implemented. |
| C058 | Embedded media blindness detection (iframes, canvas) | ❌ | Not implemented. |
| C061 | Content-type classification | ❌ | Not implemented. |
| C070 | nosnippet/X-Robots-Tag/noai directive detection | ✅ | **Implemented.** content_format_auditor detects `nosnippet`, `max-snippet:0`, `data-nosnippet`. Generates `NOSNIPPET_BLOCKING_AI`. |
| C077 | Sentiment/framing analysis of brand mentions | ❌ | Not implemented. Citation sampler captures raw answer text but does not analyze sentiment. |
| C079 | Speakable schema audit | ❌ | Not implemented. |
| C080 | Competitor technical comparison | ❌ | Not implemented. |
| C081 | Backlink/mention profile analysis | ⚠️ | authority_auditor checks domain rating and referring domain count via Open PageRank API — but no topical authority judgment, no backlink quality analysis. |

### Not-Automatable Activities (Study B says skip — human judgment required)

| Claim | Activity | Citeable Correctly Skips? |
|-------|----------|--------------------------|
| C001 | Business goals/KPIs | 🚫 Yes — correctly out of scope |
| C005 | Roadmap prioritization by business impact | 🚫 Yes — human judgment |
| C012 | Correct robots.txt policy decisions | 🚫 Yes — human judgment |
| C020 | Why pages aren't crawled | 🚫 Yes — causal reasoning |
| C032 | Which JS-gated content is "critical" | 🚫 Yes — content priority judgment |
| C052 | Answerability judgment | 🚫 Yes — editorial quality |
| C054 | Schema semantic honesty | 🚫 Yes — addressed by manual card C053 |
| C062 | E-E-A-T assessment | 🚫 Yes — addressed by manual card C062 |
| C072 | Prompt set design | 🚫 Yes — addressed by manual card C072 |
| C073 | Causal attribution of citations | 🚫 Yes — addressed by manual card C073 |
| C074 | Hallucination detection | 🚫 Yes — addressed by manual card C074 |
| C078 | Zero-click threat assessment | 🚫 Yes — addressed by manual card C078 |
| C082 | Digital PR gap analysis | 🚫 Yes — addressed by manual card C082 |
| C090 | Root cause cross-referencing | 🚫 Yes — addressed by manual card C090 |

### Coverage Summary

| Category | Count | Citeable Covers | Gap |
|----------|-------|----------------|-----|
| Fully automatable | 14 | 4 fully + 2 partial | **8 missing or weak** |
| Partially automatable | 17 | 3 partial | **14 missing** |
| Not automatable | 14 | 14 (correctly delegated to manual cards) | ✅ Well covered |

---

## 3. Coverage Gaps

### CONFIRMED Gap 1: Content Format Checks Run on Fake Text, Not Real HTML
- **Severity: Critical**
- **Study B claims: C050, C051**
- **Evidence:** [audit_orchestrator.py line 255](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py#L255): `eval_text = sample_content or f"Welcome to {clean_domain}..."`. The `sample_content` comes from [studio.js line 103](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/ui/studio.js#L103): a hardcoded marketing blurb.
- **Impact:** The entire Content Format layer (20 points / AP-03) evaluates a **fake paragraph**, not the actual page's content structure. Every content finding (`ANSWER_NOT_NEAR_TOP`, `ANSWER_NOT_SELF_CONTAINED`, `ANSWER_NOT_FACTUALLY_SPECIFIC`, `NO_LIST_OR_TABLE`) is fundamentally unreliable.
- **Irony:** The Schema layer (AP-02) already fetches the real page HTML at [line 133](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py#L133). The fetched HTML is available but never passed to the content format auditor.

### CONFIRMED Gap 2: No Raw-HTML vs Rendered-DOM Diffing
- **Study B claims: C030, C031, C033**
- **Evidence:** No headless browser rendering exists anywhere in the codebase. `content_format_auditor` and `extractability_judge` both operate on text/HTML strings, but never compare raw fetch vs rendered output.
- **Impact:** Study B rates this as "one of the cleanest, most mature checks in the entire audit" (C030) with 5/5 model consensus. This is the highest-value fully-automatable check that Citeable completely lacks.

### CONFIRMED Gap 3: No Full-Site Crawl or Sitemap Validation
- **Study B claim: C010**
- **Evidence:** Citeable audits only the homepage URL. No sitemap.xml fetch, no multi-page crawl, no orphan page detection.
- **Impact:** C010 is 5/5 consensus fully automatable. All findings are limited to a single URL, preventing content-level coverage across the site.

### CONFIRMED Gap 4: No Content Freshness Checks
- **Study B claim: C060**
- **Evidence:** No date parsing, no published/modified comparison, no stale-content detection. The knowledge base *has* freshness infrastructure (staleness checking in router.py), but the diagnostic layer doesn't emit freshness findings.
- **Impact:** C060 is 5/5 consensus fully automatable. Content staleness is a well-known factor in AI citation eligibility.

### CONFIRMED Gap 5: No Redirect/Canonical/HTTP-Status Checks
- **Study B claim: C040**
- **Evidence:** No redirect chain following, no canonical tag validation, no 404/5xx enumeration.
- **Impact:** C040 is 5/5 consensus fully automatable with mature tooling.

### CONFIRMED Gap 6: No Duplicate Content Detection
- **Study B claim: C041**
- **Evidence:** No text-similarity or embedding-based duplicate detection.
- **Impact:** C041 is 5/5 consensus fully automatable.

### CONFIRMED Gap 7: No Entity Verification Beyond Wikipedia Existence
- **Study B claim: C056, C057**
- **Evidence:** `authority_auditor` checks `WIKIPEDIA_ENTITY_MISSING` (boolean) but does NOT verify `sameAs` links, Wikidata entries, or cross-check NER extraction against Schema.org markup.

### CONFIRMED Gap 8: Citation Sampling Produces Only Binary Output
- **Study B claim: C075**
- **Evidence:** Citation sampler reports `CITATION_OBSERVED` / `CITATION_NOT_OBSERVED`. No frequency tracking, no share-of-voice computation, no competitive benchmarking, no trend analysis.

---

## 4. Quality of Existing Automation

### Content Format Auditor (C050) — CONFIRMED: Wrong Input
The [content_format_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/content_format_auditor.py) is actually well-designed as an algorithm — it checks answer position (Zyppy 9.2), nosnippet blocking (9.0), self-containment (8.8), factual specificity (8.5), and list/table presence (8.0). **But it evaluates fake text.** The real page HTML is fetched by `_fetch_and_validate_schema` at line 133 of the orchestrator but never shared with the content auditor.

### Schema Validator (C053) — CONFIRMED: Strong
The [schema_validator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/schema_validator.py) is the most reliable automated check. It fetches real HTML, parses JSON-LD blocks, validates @type, required fields, recommended fields, and unknown properties. This aligns perfectly with C053's "fully automatable, deterministic, spec-based" rating.

### Robots Checker (C011) — CONFIRMED: Good with Maintenance Risk
Tracks 13 AI crawlers. Study B's runtime-engineer pass (line 131) warns: *"a 'fully automatable' robots.txt checker built once and never updated will silently miss new crawlers within months."* The crawler list in [robots_checker.py line 32-36](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/robots_checker.py#L32-L36) is hardcoded, not configurable. This is a **confirmed maintenance risk** per Study B's explicit flag.

### Citation Sampler (C071) — CONFIRMED: Good but Shallow
Well-designed for ToS compliance (Perplexity + Gemini only). But output is binary (cited/not-cited). Study B says frequency computation (C075) is "fully automatable arithmetic/aggregation over already-collected data" — the raw data is already captured in `CitationObservation.cited_urls` but never analyzed beyond the binary check.

### Authority Auditor — CONFIRMED: Adequate
Checks domain rating, referring domains, Wikipedia entity presence, brand mention velocity. Uses Open PageRank API with fallback. Produces `AUTHORITY_DR_LOW`, `REFERRING_DOMAINS_CRITICAL`, `WIKIPEDIA_ENTITY_MISSING`, `BRAND_MENTIONS_STAGNANT`. Reasonable coverage of the automatable portion of C056/C081.

### Scoring Model — CONFIRMED: Well-Designed
The 5-layer weighted model with access gate is architecturally sound. The deduction table maps check codes to layers correctly. The access gate (cap at 25 for fully blocked, 65 for partial) is a good design decision.

However, given that Layer 3 (Content Format, 20 points) evaluates fake text, **20% of the score is unreliable**.

---

## 5. Automation Opportunities

Ordered by value-to-effort ratio:

### 1. Feed Real Page HTML to Content Format Auditor [Must Fix]
- **Value:** Extremely high — fixes the foundational input problem
- **Effort:** Low — the HTML is already fetched at line 133
- **Change:** Pass `resp.text` from `_fetch_and_validate_schema` to `audit_page_format`
- **Study B anchor:** C050, C051

### 2. Add Raw HTML vs Rendered DOM Diff [Strong Improvement]
- **Value:** Very high — Study B's "cleanest, most mature check"
- **Effort:** Medium — requires headless browser (Playwright/Puppeteer)
- **Checks unlocked:** `JS_CONTENT_DEPENDENCY`, `CRITICAL_CONTENT_JS_GATED`, `LAZY_LOAD_HIDDEN`
- **Study B anchor:** C030, C031, C033

### 3. Enrich Citation Data Beyond Binary [Strong Improvement]
- **Value:** High — turns observation into analytics
- **Effort:** Low — data already captured, just needs computation
- **Checks unlocked:** Citation frequency, competitor share-of-voice, per-prompt success rate
- **Study B anchor:** C075

### 4. Add Content Freshness Checks [Strong Improvement]
- **Value:** High — automatable, well-understood factor
- **Effort:** Low — parse published/modified dates from meta tags and Schema.org
- **Checks unlocked:** `CONTENT_STALE`, `DATE_MISMATCH_SCHEMA_VS_VISIBLE`
- **Study B anchor:** C060

### 5. Add Redirect Chain / Canonical / HTTP Status Checks [Worth Considering]
- **Value:** Medium — standard technical audit
- **Effort:** Low — follow redirects and check headers
- **Checks unlocked:** `REDIRECT_CHAIN_LONG`, `CANONICAL_MISMATCH`, `SOFT_404`
- **Study B anchor:** C040

### 6. Add Cloaking Detection [Worth Considering]
- **Value:** Medium — detects configuration problems
- **Effort:** Low — fetch with different UAs and diff
- **Study B anchor:** C036

### 7. Add Sitemap Validation [Worth Considering]
- **Value:** Medium — useful for multi-page coverage
- **Effort:** Medium — multi-page crawling is a significant architectural addition
- **Study B anchor:** C010

### 8. Make AI Crawler List Configurable [Worth Considering]
- **Value:** Medium (maintenance reduction)
- **Effort:** Low — move to config file or KB
- **Study B anchor:** C011 runtime-engineer caveat

---

## 6. Knowledge-Architecture Interaction

### Current State
The knowledge architecture and diagnostic layer interact through [findings_to_claims.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/findings_to_claims.py)'s `wire_finding()` function, which maps check codes to knowledge records via `kb_check_code_map`. The mapping covers **50 check codes** in [check_code_to_knowledge_map.json](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/check_code_to_knowledge_map.json).

### Findings Granularity
**CONFIRMED: Current findings are at the right granularity for the knowledge structure.** Each finding carries `{code, severity, message, page_url}`. The knowledge base maps check codes to `KnowledgeRecord`s with `GUIDANCE` type containing remediation instructions. This 1-code-to-1-guidance mapping is clean.

### Opportunities from the Knowledge Architecture

1. **Study B claims ARE in the knowledge base.** The ZIP searcher confirmed that Study B's C0-series claims were ingested into the corpus via `changelog.jsonl` as `claim_type='automatability_rating'`. This means the KB already knows *which activities are automatable*. **New automated checks can leverage this metadata** — e.g., before adding a check, verify its claim_id maps to a `fully_automatable` or `partially_automatable` rating.

2. **Missing check codes in the map.** Several check codes emitted by the orchestrator are NOT in `check_code_to_knowledge_map.json`:
   - `SCHEMA_MISSING` — falls through to RAG or INSUFFICIENT
   - `SCHEMA_UNVERIFIABLE` — falls through
   - `ROBOTS_UNVERIFIABLE` — falls through
   - `LLMS_UNVERIFIABLE` — falls through
   These should be explicitly mapped to GUIDANCE records for reliable remediation.

3. **New checks should carry richer metadata.** If we add the proposed checks (JS-rendering diff, freshness, redirect chains), each new check code needs:
   - An entry in `LAYER_DEDUCTIONS` (scoring.py)
   - An entry in `check_code_to_knowledge_map.json`
   - A GUIDANCE record in `knowledge.jsonl`
   - Evidence and source records in `evidence.jsonl` / `sources.jsonl`

### Should checks carry additional metadata?

**LIKELY: Yes.** Currently findings carry only `{code, severity, message, page_url}`. Adding the following would improve claim resolution:
- `check_phase`: Which AEOGEO phase this check covers (e.g., "AP-01", "STAGE-02")
- `evidence_url`: The specific URL that was checked (distinct from `page_url`)
- `raw_value`: The actual measured value (e.g., word count, redirect count, response time)

This would let the knowledge router produce more targeted resolutions and let the remediation plan include more specific evidence.

---

## 7. Remediation Impact

### Proposed Change: Feed Real HTML to Content Auditor
- **Finding impact:** Findings will change — real pages may produce different content-format findings than fake text
- **Claim resolution:** No change — same check codes map to same knowledge records
- **Remediation planning:** Plans become **more accurate** — recommendations based on actual deficiencies
- **Existing mappings:** No change — check codes are unchanged
- **Risk:** Some existing audit runs stored in DB will have been scored with fake-text findings; new runs will score differently. This is a **one-time regression in score consistency** that is actually an improvement in accuracy.

### Proposed Change: Add JS-Rendering Diff
- **Finding impact:** New check codes needed: `JS_CONTENT_DEPENDENCY`, `JS_RENDERING_REQUIRED`, `LAZY_LOAD_INVISIBLE`
- **Claim resolution:** New entries needed in `check_code_to_knowledge_map.json`
- **Remediation planning:** New GUIDANCE records needed; these checks feed into the Access layer (AP-01) scoring
- **Existing mappings:** No breaking changes — additive only
- **Risk:** Headless browser adds deployment complexity (Playwright binary on Render). May need to be gated behind a `HEADLESS_AVAILABLE` config flag.

### Proposed Change: Add Freshness Checks
- **Finding impact:** New check codes: `CONTENT_STALE`, `DATE_MISMATCH`
- **Claim resolution:** Can map to existing freshness-related knowledge records
- **Remediation planning:** Feeds into a new scoring layer or extends Content layer
- **Existing mappings:** Additive — no breaks
- **Risk:** Low.

---

## 8. Architectural Risks

### Risk 1: Headless Browser Dependency for JS-Rendering
Adding Playwright/Puppeteer creates a deployment dependency. On Render free tier (no persistent disk, limited memory), headless Chromium may exceed memory limits. **Mitigation:** Make headless checks optional via environment variable; degrade gracefully when unavailable.

### Risk 2: Score Inconsistency After Fixing Content Input
Fixing the content format auditor to use real HTML will change scores for previously-audited domains. Historical comparisons will show apparent regressions that are actually accuracy improvements. **Mitigation:** Add a `scoring_version` field to audit runs; document the change in CHANGELOG.

### Risk 3: Scope Creep from Multi-Page Crawling
Adding sitemap validation and multi-page crawling (C010) would fundamentally change Citeable from a "single-page point-in-time snapshot" to a "site-wide audit." This has major implications for execution time, storage, and pricing. **Recommendation:** Defer C010 to a future version; focus on improving single-page depth first.

### Risk 4: Knowledge Base Schema Changes for New Check Codes
Adding 5-10 new check codes requires corresponding GUIDANCE records, evidence links, and check_code_map entries. If these are added inconsistently, the QA gate will reject recommendations or the remediation plan will have gaps. **Mitigation:** Add new check codes in coordinated batches with full KB wiring.

### Risk 5: Duplicated Logic Between Orchestrator and Auditors
The orchestrator already contains some inline checks (e.g., `EXTRACTABILITY_LOW` at line 256-262) that overlap with what `extractability_judge.py` does more thoroughly. Adding more inline checks would increase this duplication. **Mitigation:** All new checks should live in dedicated auditor modules, not inline in the orchestrator.

---

## 9. Recommended Target Architecture

After improvements, the automated checking layer should look like this:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (unchanged)                   │
│   Coordinates modules, collects findings, computes score     │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ ACCESS       │ STRUCTURE    │ CONTENT      │ OBSERVATION    │
│ (AP-01)      │ (AP-02)      │ (AP-03)      │ (AP-04/05)     │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ robots.txt   │ JSON-LD      │ Real HTML    │ Domain         │
│ per-crawler  │ validation   │ format audit │ authority      │
│              │              │ (FIXED)      │                │
│ llms.txt     │ Redirect/    │              │ Citation       │
│ syntax       │ canonical    │ Freshness/   │ frequency +    │
│              │ checks (NEW) │ dates (NEW)  │ share-of-voice │
│ nosnippet    │              │              │ (ENHANCED)     │
│ detection    │ Entity       │ JS-rendering │                │
│              │ sameAs       │ diff         │ Sentiment      │
│ Cloaking     │ verify (NEW) │ (NEW, opt.)  │ analysis       │
│ detect (NEW) │              │              │ (NEW, opt.)    │
├──────────────┴──────────────┴──────────────┴────────────────┤
│            UNCHANGED BELOW THIS LINE                         │
│  wire_finding → KB Router → Remediation → LLM Synthesis      │
└─────────────────────────────────────────────────────────────┘
```

Key principles:
1. **Every check fetches real data.** No more placeholder text.
2. **New checks are additive.** They add new check codes; existing codes are unchanged.
3. **Optional checks are gated.** Headless browser checks degrade gracefully when unavailable.
4. **Every new check code gets full KB wiring** before shipping (GUIDANCE record + evidence + map entry + scoring deduction).
5. **Manual review cards stay for judgment calls.** C052, C054, C062, C073, C074, C078, C082, C090 remain human-only, exactly as Study B prescribes.

---

## 10. Prioritized Action Plan

### Must Fix (breaks trust in current output)

| # | Action | Study B Ref | Effort |
|---|--------|-------------|--------|
| 1 | **Feed real page HTML to content format auditor** — pass `resp.text` from `_fetch_and_validate_schema` to `audit_page_format` | C050, C051 | ~1 hour |
| 2 | **Map missing check codes in knowledge base** — add `SCHEMA_MISSING`, `SCHEMA_UNVERIFIABLE`, `ROBOTS_UNVERIFIABLE`, `LLMS_UNVERIFIABLE` to `check_code_to_knowledge_map.json` with corresponding GUIDANCE records | — | ~2 hours |
| 3 | **Fix the forensic-audit CRITICAL bugs first** — `MANUAL_REMEDIATION_TEXT` NameError, `REMEDIATION_TEXT` NameError, hardcoded API token (see [forensic_audit_report.md](file:///C:/Users/drc16/.gemini/antigravity/brain/d301feb9-84d4-4339-8c2f-0d922cd53a9b/forensic_audit_report.md)) | — | ~1 hour |

### Strong Improvement (materially increases audit value)

| # | Action | Study B Ref | Effort |
|---|--------|-------------|--------|
| 4 | **Add content freshness checks** — parse `<meta>` dates, Schema.org `datePublished`/`dateModified`, flag stale content | C060 | ~4 hours |
| 5 | **Enrich citation data** — compute per-prompt frequency, competitor share-of-voice from existing `CitationObservation` data | C075 | ~4 hours |
| 6 | **Add redirect chain / canonical / HTTP status checks** — follow redirects, validate canonical, flag 404/5xx | C040 | ~4 hours |
| 7 | **Add cloaking detection** — fetch with different UAs (AI bot vs browser), diff responses | C036 | ~4 hours |

### Worth Considering (valuable but higher effort or lower urgency)

| # | Action | Study B Ref | Effort |
|---|--------|-------------|--------|
| 8 | **Add JS-rendering diff** — requires headless browser; gated behind config flag | C030, C033 | ~2 days |
| 9 | **Add entity verification** — sameAs link validation, Wikidata cross-check | C056, C057 | ~1 day |
| 10 | **Add embedded media blindness detection** — iframe/canvas/video text-alternative checks | C058 | ~4 hours |
| 11 | **Make AI crawler list configurable** — move from hardcoded to config/KB | C011 caveat | ~2 hours |
| 12 | **Add sentiment analysis of citation answers** — classify brand framing from raw answer snippets | C077 | ~1 day |

### Leave As-Is (correct design decisions)

| # | Decision | Rationale |
|---|----------|-----------|
| — | No full-site crawl (C010) | Architectural scope change; focus on single-page depth first |
| — | No duplicate content detection (C041) | Requires multi-page crawl infrastructure |
| — | No server log ingestion (C019) | Requires client data access; out of SaaS scope |
| — | No speakable schema audit (C079) | Low value relative to effort |
| — | No continuous monitoring (C092) | Point-in-time architecture is intentional |
| — | All not-automatable items (C001, C005, C012, C020, C032, C052, C054, C062, C072-74, C078, C082, C090) | Correctly delegated to manual review cards |

---

## Final Answer

> **Is Citeable currently making good enough use of the automatable AEOGEO lifecycle, or is the existing diagnostic architecture leaving meaningful automation potential on the table?**

**Citeable is leaving meaningful automation potential on the table.**

The most damaging finding is not a missing feature — it's that the content format layer (**20% of the total score**) evaluates fabricated text instead of real page content. This is a foundational input error that undermines the reliability of every audit Citeable produces. Fixing this requires changing one argument in one function call.

Beyond that, Study B identifies 14 fully-automatable activities. Citeable covers 4 well and 2 partially. Eight are completely absent, including the single highest-value check in the entire Study B corpus: **raw HTML vs rendered DOM diffing** (C030), which every model rated as fully automatable and the Study B runtime engineer specifically called out as "one of the cleanest, most mature checks."

The existing architecture is well-designed for what it does — the scoring model is sound, the knowledge routing is sophisticated, the manual review delegation is correct. **The problem is not the architecture's quality but its coverage.** The diagnostic layer implements a narrow slice of what Study B establishes as the automatable frontier, and then fills the gap with a placeholder instead of actual data.

The recommended remediation is not a rewrite but a **deepening**: feed real inputs to existing checks, add the highest-value missing checks as new modules, wire them through the existing KB infrastructure, and let the already-sound scoring and remediation pipeline do its job with better data.

