# Gap Closures + Deeper Pre-Implementation Audit

---

## PART 1: Closing the 3 Critical Gaps

---

### Gap C1 — CLOSED: RAG Decision

**Decision: RAG is ON.** Per `rag_byok_integration.md`.

`areos/kb/embeddings.py` already exists and is fully implemented with a BYOK waterfall:
1. Google `text-embedding-004` (768 dims, free tier)
2. OpenAI `text-embedding-3-small` (1536 dims)
3. Mistral `mistral-embed` (1024 dims)

The code includes graceful degradation (raises `EmbeddingUnavailable` if no provider configured), pure-Python cosine similarity (no numpy), and dimension mismatch detection.

**Implications for new check codes:**
- All ~28 new check codes get GUIDANCE records in the KB
- Each GUIDANCE record gets pre-computed embeddings via `build_kb.py`
- At runtime, `router.py` resolves findings through deterministic lookup first (`check_code_to_knowledge_map.json`), then RAG semantic search as enrichment
- Manual review observations use deterministic template selection (question_id × structured_answer → KB GUIDANCE ID), NOT RAG. RAG only enriches automated findings.

**What this means for `router.py` exception swallowing (RISK-003):** With RAG on, a malformed `guidance_json` silently returns `guidance=None`, which means the RAG enrichment path (`evidence_chain`, `source_citations`, `backing_facts`) may silently degrade. This makes fixing RISK-003 more urgent, not less.

---

### Gap B1 — CLOSED: Expanded Phase 0 Bug Fixes

Add these to Phase 0 of `implementation_plan.md`:

#### Fix RISK-003: Silent Exception Swallowing in `router.py`

**File:** `areos/kb/router.py`

**Location 1 — Line 157-160:**
```python
# CURRENT (broken):
try:
    guidance = GuidanceDetail(**json.loads(row["guidance_json"]))
except Exception:
    pass

# FIX:
try:
    guidance = GuidanceDetail(**json.loads(row["guidance_json"]))
except (json.JSONDecodeError, TypeError, KeyError) as e:
    logger.warning("Malformed guidance_json for kid=%s: %s", row["kid"], e)
    guidance = None
```

**Location 2 — Line 229-234:**
```python
# CURRENT (broken):
try:
    if date.fromisoformat(review_due) < date.today():
        is_stale = True
        stale_since = review_due
except ValueError:
    pass

# FIX:
try:
    if date.fromisoformat(review_due) < date.today():
        is_stale = True
        stale_since = review_due
except ValueError as e:
    logger.warning("Malformed review_due date for kid=%s: %r — %s", record.kid, review_due, e)
```

**Why:** When ~28 new GUIDANCE records are added, any malformed JSON will silently produce `guidance=None`, causing remediation plans to silently lack guidance text. With logging, build-time KB validation (`build_kb.py`) can catch these before deploy.

#### Fix DATA-001: Empty `_CHECK_CODE_MAPPINGS` in `ingest_claims.py`

**File:** `areos/db/ingest_claims.py` (line 62)

**Current:** `_CHECK_CODE_MAPPINGS: dict[str, list[str]] = {}`

**The `check_code_mappings` DB table is queried in 6 runtime locations:**
- `audit.py` lines 172, 174, 182, 248, 258, 264, 487
- `findings_to_claims.py` lines 22, 39, 55, 58, 138, 140

All return empty results because the table is never populated.

**Two options:**

**Option A (recommended): Delete the legacy fallback paths.** The V2 system uses `check_code_to_knowledge_map.json` as the primary lookup. Remove all `SELECT ... FROM check_code_mappings` queries in `audit.py` and `findings_to_claims.py`. Replace with the JSON map lookup that already exists in `wire_finding()`.

**Option B: Repopulate the dict.** Generate `_CHECK_CODE_MAPPINGS` from the JSON map at build time. More backward-compatible but maintains two parallel systems.

**Recommendation:** Option A. Kill the legacy path. The V2 JSON map is the canonical source. Having two lookup systems (one always empty) is a bug factory.

#### Fix DATA-002: Priority Score Fallback

**File:** `areos/auditors/synthesis_engine.py` (line ~93)

**Current:** `_load_priority_scores()` returns `{}` on DB failure → all check codes default to priority 10 (lowest) → remediation plan ordering is inverted.

**Fix:** Add a hardcoded baseline priority map as fallback:
```python
_BASELINE_PRIORITIES = {
    "CRAWLER_FULLY_BLOCKED": 1,
    "CLOAKING_DETECTED": 2,
    "EXTRACTABILITY_NONE": 2,
    "SCHEMA_MISSING": 3,
    "CITATION_NOT_OBSERVED": 4,
    # ... all existing codes with sane defaults
}

def _load_priority_scores(db_path):
    try:
        # ... existing DB load
    except Exception:
        logger.warning("Priority scores DB load failed; using baseline defaults")
        return dict(_BASELINE_PRIORITIES)
```

---

### Gap A1 — CLOSED: Integration Spec (Auditor → Manual Review Data Contracts)

Each auditor module must export **intermediate data** beyond just findings, so the manual review UI can display it.

#### Data Contract 1: Schema Validator → B1 (Schema Honesty)

**Current problem:** `schema_validator.py` returns `list[ValidationResult]` containing `SchemaIssue` objects (code + message). It does NOT return the parsed JSON-LD field values (name, description, foundingDate, etc.). The raw blocks are parsed by `_extract_json_ld_blocks()` in the orchestrator but discarded after validation.

**Required change:** The orchestrator must RETAIN the raw JSON-LD blocks and pass them to the API response.

```python
# In refactored orchestrator:
page_html, hop_count, final_url = _fetch_page(clean_domain, page_url)
json_ld_blocks = _extract_json_ld_blocks(page_html)
schema_findings = _validate_schema_from_html(json_ld_blocks)

# NEW: Store raw blocks for manual review
audit_data["schema_claims"] = _extract_schema_claims(json_ld_blocks)
```

**New helper function:**
```python
def _extract_schema_claims(blocks: list[dict]) -> list[dict]:
    """Extract human-readable claims from JSON-LD for manual review display."""
    claims = []
    for block in blocks:
        schema_type = block.get("@type", "Unknown")
        for key, value in block.items():
            if key.startswith("@"):
                continue
            if isinstance(value, (str, int, float, bool)):
                claims.append({
                    "schema_type": schema_type,
                    "field": key,
                    "value": str(value),
                })
    return claims
```

**API contract:** The audit run response includes `schema_claims: list[{schema_type, field, value}]` alongside findings.

---

#### Data Contract 2: Content Format Auditor → B2 (Answerability)

**Current problem:** `audit_page_format()` accepts `html` param (confirmed — it already works) and returns `FormatAuditResult` with issues. But it does NOT expose the extracted "first 150 words" fragment the manual review needs to display.

**Required change:** `FormatAuditResult` must include the extracted text fragment.

```python
# In content_format_auditor.py, add to FormatAuditResult:
@dataclass
class FormatAuditResult:
    issues: list[FormatIssue]
    extracted_lead_text: str = ""  # NEW: first ~150 words of main content
```

**API contract:** The audit run response includes `extracted_lead_text: str` for B2 display.

---

#### Data Contract 3: Cloaking Detector → B3 (Cloaking Intent)

**Required from the NEW module** (doesn't exist yet — defined in implementation plan):

```python
@dataclass
class CloakingResult:
    findings: list[dict]
    browser_word_count: int        # NEW: for UI display
    bot_word_count: int            # NEW: for UI display
    missing_elements: list[str]    # NEW: what's missing from bot view
    content_diff_summary: str      # NEW: human-readable diff description
```

**API contract:** The audit run response includes `cloaking_diff: {browser_words, bot_words, missing_elements, diff_summary}` for B3 display. Only present when a content difference is detected.

---

#### Data Contract 4: Citation Sampler → C1 (Brand Accuracy Multi-Engine)

**Current problem:** `CitationObservation.raw_answer_snippet` is **truncated to 300 characters** (confirmed: `answer[:300]` at lines 142 and 178). The C1 manual review question needs the FULL AI response to display side-by-side.

**Required change:**
```python
# In citation_sampler.py:
@dataclass
class CitationObservation:
    run_index: int
    prompt: str
    engine: str
    cited_urls: list[str] = field(default_factory=list)
    raw_answer_snippet: str = ""    # Keep for backward compat (truncated)
    full_answer_text: str = ""      # NEW: full response for manual review
    error: str | None = None
```

**Also update the query functions:**
```python
# _query_perplexity():
return citations, answer  # was: answer[:300]
# Store full in full_answer_text, truncated in raw_answer_snippet

# _query_gemini_grounded():
return cited, answer  # was: answer[:300]
```

**API contract:** The audit run response includes `ai_responses: list[{engine, prompt, full_text, cited_urls}]` for C1 display.

**Storage consideration:** Full responses may be 500-2000 chars each. With 3 engines × 5 prompts = 15 responses, this adds ~15-30KB per audit run. Acceptable for SQLite.

---

#### Data Contract 5: Competitor Analyzer → C4 (Competitive Gap)

**Required from the NEW module** (implementation plan Phase 7):

```python
@dataclass
class CompetitorProfile:
    domain: str
    schema_types_found: list[str]
    has_faq_schema: bool
    first_paragraph_quality: str  # "definitional" | "marketing" | "absent"
    word_count: int
    referring_domains: int | None  # from authority API if available
```

**API contract:** The audit run response includes `competitor_profiles: list[CompetitorProfile]` for C4 display.

---

#### Data Contract 6: Prompt Set → A1 (Prompt Validation)

**Current state:** Prompts are constructed in `citation_sampler.py` or passed from the UI. The manual review A1 question needs to show the prompt set BEFORE the audit runs.

**Required change:** The audit creation endpoint must accept and return the prompt set:
```python
# POST /api/v1/audit/runs (create)
# Request body gains: prompt_set: list[str] (optional, uses defaults if absent)
# Response gains: prompt_set: list[str] (what will be/was tested)
```

**Default prompts must be externalized** from citation_sampler into a config or KB lookup, so they can be displayed, modified, and stored per run.

---

## PART 2: Deeper Completeness Audit — 11 NEW Findings

These are code-level findings the first audit missed, discovered by reading actual function signatures, return types, and data models.

---

### NEW-1: No ChatGPT API in Citation Sampler [HIGH]

**Discovery:** `citation_sampler.py` has exactly two query functions: `_query_perplexity()` and `_query_gemini_grounded()`. There is no ChatGPT/OpenAI query function.

**Impact:** The manual review C1 (Brand Accuracy) displays "ChatGPT, Perplexity, Google AI Mode" side by side. But the system can only query 2 of these 3.

**Options:**
1. **Add ChatGPT query function** — OpenAI API with web browsing/search. Requires `OPENAI_API_KEY` which is already in `render.yaml`.
2. **Adjust C1 to show only available engines** — Dynamic: show whichever engines have API keys configured. Labels show actual engine names, not hardcoded 3.

**Recommendation:** Option 2. The manual review should show "Engines tested: [list]" dynamically based on configured keys. Add ChatGPT query function as a new Phase 2 addition to the implementation plan.

---

### NEW-2: AP-03 (Content) Missing from `audited_stages` [MEDIUM]

**Discovery:** `audit_orchestrator.py` line 391:
```python
audited_stages=["AP-01", "AP-02", "AP-04", "AP-05", "AP-06"]
```

AP-03 (Content) is absent. This means any manual review card with `trigger_on_stages: ["AP-03"]` would never trigger. Currently no card uses AP-03, but the implementation plan adds content-layer checks. If any future card is tied to AP-03, it will be dead on arrival.

**Fix:** Add `"AP-03"` to the list. This is a one-token fix.

---

### NEW-3: Scoring Layer Caps Hide Findings [MEDIUM]

**Discovery:** The scoring system has layer caps:
- Access: max 20 pts deduction
- Schema: max 15 pts
- Content: max 20 pts
- Citation: max 30 pts
- Authority: max 15 pts

But the CURRENT deduction values already exceed caps:
- Access codes sum to 54 pts (cap 20) — 34 pts of deductions are invisible
- Schema codes sum to 37 pts (cap 15) — 22 pts invisible
- Content codes sum to 51 pts (cap 20) — 31 pts invisible

Adding ~28 more codes will make this worse. Many new findings will have zero score impact because their layer is already maxed out.

**Impact:** This isn't a bug — it's by design (prevents a single bad layer from tanking the whole score). But the remediation report should show ALL findings regardless of score impact. Currently, findings that don't affect the score may be deprioritized.

**Action needed:** Verify that the report rendering shows all findings, not just score-impacting ones. The scoring model itself is fine.

---

### NEW-4: No API Endpoint for Manual Observations [HIGH]

**Discovery:** The existing verdicts API is:
```
POST /api/v1/audit/runs/{run_id}/verdicts
Body: { card_id, page_url, verdict, severity, notes }
```

The new manual review needs:
```
POST /api/v1/audit/runs/{run_id}/observations
Body: {
  question_id: "B1_SCHEMA_HONESTY",
  maps_to_claims: ["C054", "C053"],
  structured_data: { claims_verified: [...], ... },
  severity: "error",
  diagnosis_text: "..."
}
```

This is a new API endpoint. Neither plan mentions it.

**Action needed:** Add to the UI/UX implementation spec. The old verdicts endpoint stays for backward compatibility.

---

### NEW-5: Wizard Completion Trigger at 100% [MEDIUM]

**Discovery:** `studio.js` line 554-589: `updateShieldProgress()` tracks wizard completion percentage. At 100%, it auto-triggers `triggerPostWizardSynthesis()`.

With the new 11-question design (Express mode: 4 questions, Full: 11), the completion tracking logic needs updating:
- Express mode: 100% = 4/4 questions answered
- Full mode: 100% = 11/11 questions answered
- Conditional questions (B3, C3, C4, C5, D1) may not appear — completion must be calculated against SHOWN questions, not total possible

**Action needed:** Track `answered / shown` not `answered / total`.

---

### NEW-6: Three Separate Report Endpoints [HIGH]

**Discovery:** The current system has 3 report outputs served from 3 different endpoints:
1. `GET /api/v1/audit/runs/{run_id}/report` → gap report markdown
2. `GET /api/v1/audit/runs/{run_id}/remediation` → structured remediation plan
3. `POST /api/v1/audit/runs/{run_id}/synthesize` → LLM narrative

The redesigned unified report needs a SINGLE endpoint that combines all three into the 3-layer diagnostic report.

**Options:**
1. **New endpoint** `GET /api/v1/audit/runs/{run_id}/full-report` — returns the unified report
2. **Modify existing** `/report` endpoint — breaking change for any consumers

**Recommendation:** Option 1. New endpoint. Old endpoints stay for backward compatibility.

---

### NEW-7: `_extract_json_ld_blocks` is Private to Orchestrator [LOW]

**Discovery:** The function that parses JSON-LD from HTML exists in `audit_orchestrator.py` as a module-level function. The schema validator imports from the orchestrator. For the integration spec (Data Contract 1), this function needs to be accessible to the refactored pipeline.

**Fix:** Move to a shared utility module or make the orchestrator's refactored `_fetch_page()` return the blocks alongside HTML.

---

### NEW-8: No Prompt Set Storage [MEDIUM]

**Discovery:** The citation sampler receives prompts at call time. There is no storage of which prompts were used for a given audit run. For A1 (Prompt Validation), the user's modified prompts need to be:
1. Stored with the audit run (so the report can show "Prompts tested")
2. Retrievable for re-runs with the same prompt set

**Current `audit_runs` table** doesn't have a `prompt_set` column.

**Action needed:** Either add a `prompt_set_json TEXT` column to `audit_runs`, or store prompts in a separate `audit_prompts` table.

---

### NEW-9: Frontend Has No Build Step [INFO — Actually Good]

**Discovery:** All JS is served raw via FastAPI's StaticFiles. No webpack, no bundler, no package.json.

**Impact on implementation:** This is actually GOOD for the manual review redesign. New JS can be added as `manual_review.js` and loaded via a new `<script>` tag. No build tooling to configure.

**Risk:** No module system means all new code shares global scope via `window.*` namespace. Follow the existing pattern (`window.GuidedReview`, `window.AreosContext`).

---

### NEW-10: Render Free Plan + Playwright [MEDIUM]

**Discovery:** `render.yaml` uses `plan: free`. The implementation plan proposes Playwright (headless Chromium) for JS rendering diff. Chromium requires ~400MB disk + ~200MB RAM.

Render free tier has limited memory and no persistent disk. Chromium may not fit.

**The render.yaml does NOT have `AREOS_ENABLE_PLAYWRIGHT`** environment variable. The implementation plan mentions gating behind this flag but the config doesn't include it.

**Action needed:** Add `AREOS_ENABLE_PLAYWRIGHT` to render.yaml as `value: "0"` (default off). The rendering_auditor should check this at startup and skip gracefully.

---

### NEW-11: LLM Prompt Needs Only Targeted Update, Not Rewrite [LOW]

**Discovery:** The current synthesizer prompt already says:
- "Group findings into root causes using exactly three layers: Access Layer, Content Layer, Authority Layer" ✓
- "Reference ONLY the claim_ids provided in the input JSON" ✓
- "Do NOT invent percentages, timelines, or metrics" ✓
- "If human_review_notes are provided, MUST explicitly integrate" ✓

This already matches the manual review product design's "LLM narrates, doesn't decide" architecture reasonably well. The prompt doesn't need a rewrite — it needs two additions:

```
# ADD:
"9. If a human_diagnosis_text is provided, use it as the opening framing of your "
"narrative. Do not contradict or replace it — expand on it with supporting evidence "
"from the findings.\n"
"10. The structured remediation actions have already been determined. Your job is to "
"explain WHY each action matters, not to invent new actions.\n"
```

---

## Summary: Complete Pre-Implementation Gap Status

### Previously Identified (12 gaps)

| # | Gap | Status |
|---|-----|--------|
| A1 | Integration Spec | **CLOSED** — data contracts defined above |
| A2 | `manual_observations` DB table | Open — create during Track B |
| A3 | Verdict → KB template mapping | Open — create during Track B |
| B1 | 6 unfixed bugs | **CLOSED** — RISK-003, DATA-001, DATA-002 added to Phase 0 |
| C1 | RAG vs Deterministic | **CLOSED** — RAG ON |
| C2 | STAGE-xx vs AP-xx | Partial — AP-03 added (NEW-2), full taxonomy deferred |
| D1 | ~28 GUIDANCE record contents | Open — draft in parallel with coding |
| D2 | UI/UX implementation spec | Open — create during Track B |
| D3 | Scoring model rebalancing | **RESOLVED** — layer caps prevent overflow (NEW-3) |
| D4 | Manual review test strategy | Open — create during Track B |
| D5 | LLM synthesizer prompt | **RESOLVED** — targeted 2-line addition needed (NEW-11) |

### Newly Discovered (11 findings)

| # | Finding | Severity | When to Fix |
|---|---------|----------|-------------|
| NEW-1 | No ChatGPT API in citation sampler | High | Phase 2 or 3 — add query function |
| NEW-2 | AP-03 missing from audited_stages | Medium | Phase 0 — one-token fix |
| NEW-3 | Scoring layer caps hide findings | Medium | No fix needed — by design. Verify report shows all |
| NEW-4 | No API endpoint for observations | High | Track B — new endpoint |
| NEW-5 | Wizard completion 100% trigger | Medium | Track B — update progress tracking |
| NEW-6 | 3 separate report endpoints | High | Track B — new unified endpoint |
| NEW-7 | `_extract_json_ld_blocks` is private | Low | Phase 1 — move during refactor |
| NEW-8 | No prompt set storage | Medium | Phase 2 or Track B — add storage |
| NEW-9 | No frontend build step | Info | Good — no action needed |
| NEW-10 | Render free plan + Playwright | Medium | Phase 5 — add env var to render.yaml |
| NEW-11 | LLM prompt needs 2-line addition | Low | Track B — minimal change |

### Revised Phase 0 (Expanded)

The original Phase 0 had 4 fixes. Now it has 8:

| # | Fix | Source |
|---|-----|--------|
| 1 | CRITICAL-001: `MANUAL_REMEDIATION_TEXT` NameError | Original plan |
| 2 | CRITICAL-002: `REMEDIATION_TEXT` NameError | Original plan |
| 3 | RISK-002: Hardcoded API token | Original plan |
| 4 | HIGH-001: `claims_legacy` idempotency | Original plan |
| 5 | **RISK-003: Silent exception swallowing in `router.py`** | **NEW — Gap B1** |
| 6 | **DATA-001: Delete legacy `check_code_mappings` fallback paths** | **NEW — Gap B1** |
| 7 | **DATA-002: Priority score fallback map** | **NEW — Gap B1** |
| 8 | **AP-03 missing from `audited_stages`** | **NEW — finding NEW-2** |

### Remaining Open Items (Create During Implementation)

**Track A (automation) needs these created in parallel:**
- ~28 GUIDANCE record texts (D1)
- ChatGPT query function in citation sampler (NEW-1)
- Prompt set externalization and storage (NEW-8)
- `AREOS_ENABLE_PLAYWRIGHT` env var in render.yaml (NEW-10)

**Track B (manual review) needs these before coding starts:**
- `manual_observations` DB table + migration (A2)
- Verdict → KB template mapping spec (A3)
- UI/UX implementation spec including new `manual_review.js` (D2)
- New API endpoint for observations (NEW-4)
- New unified report endpoint (NEW-6)
- Wizard progress tracking update (NEW-5)
- LLM prompt 2-line addition (NEW-11)
- Test strategy for manual review changes (D4)
