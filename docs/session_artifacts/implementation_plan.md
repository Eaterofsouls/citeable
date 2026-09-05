# Implementation Plan — Maximum AEOGEO Automation Coverage

> **Goal:** Push Citeable's diagnostic architecture from ~40% to ~95% coverage of the automatable AEOGEO lifecycle. Every Study B automatable claim is implemented except server log parsing (requires client data we cannot access).

> [!IMPORTANT]
> This plan does NOT modify the manual review flow, does NOT modify the UI/UX, and does NOT break any existing check codes or scoring. All changes are additive to the diagnostic layer + wiring.

---

## Phase 0 — Fix Critical Bugs (Forensic Audit)

Fix the 3 confirmed bugs that will crash production before we add anything.

### [MODIFY] [synthesis_engine.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/synthesis_engine.py)

**Bug CRITICAL-001 (line 382, 389):** `MANUAL_REMEDIATION_TEXT` NameError — the dict was deleted by Gemini in Phase 7 cleanup but references at lines 382 and 389 were not updated.

- **Fix:** Replace `MANUAL_REMEDIATION_TEXT` lookups with `_load_remediation_text(db_path)` calls, which already exist and load from KB GUIDANCE records. If no GUIDANCE record exists for a manual card, generate fallback text from the `ManualFinding` fields instead of crashing.

**Bug CRITICAL-002 (line 59):** `REMEDIATION_TEXT` NameError — `_load_remediation_text()` falls back to undefined `REMEDIATION_TEXT` when no KB rows found.

- **Fix:** Replace `return REMEDIATION_TEXT` at line 59 with `return {}` (empty dict triggers downstream fallback logic, not a crash).

### [MODIFY] [build_kb.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/build_kb.py)

**Bug RISK-002 (line 8):** Hardcoded API token `'build_kb_token'`.

- **Fix:** Replace with `os.environ.get('AREOS_ADMIN_TOKEN', 'dev-build-kb')` to use environment variable in production.

**Bug HIGH-001 (line 93):** `claims_legacy` rename not idempotent.

- **Fix:** Wrap the ALTER TABLE in a check: only rename if `claims_legacy` doesn't already exist.

---

## Phase 1 — Fix Content Format Input (The Foundational Fix)

### [MODIFY] [audit_orchestrator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py)

**Problem:** Content format checks evaluate fake placeholder text (line 255), not real HTML. The schema validator already fetches the real page HTML (line 133) but discards it.

**Changes:**

1. **Refactor `_fetch_and_validate_schema()`** → `_fetch_page()`  that fetches the page ONCE and returns the raw HTML, plus a new `_validate_schema_from_html()` that takes pre-fetched HTML:

   ```python
   def _fetch_page(clean_domain: str, page_url: str) -> tuple[str, int, str]:
       """Fetch the target page. Returns (html, hop_count, final_url).
       Returns ('', 0, page_url) on failure."""

   def _validate_schema_from_html(page_html: str, page_url: str) -> tuple[list[dict], list]:
       """Validate JSON-LD from already-fetched HTML.
       Returns (schema_findings, json_ld_blocks)."""
   ```

2. **Single fetch, multiple consumers** — the orchestrator fetches the page once and passes `page_html` to every auditor that needs it:
   ```python
   page_html, hop_count, final_url = _fetch_page(clean_domain, page_url)

   # Schema (existing) — uses real HTML
   schema_findings, json_ld_blocks = _validate_schema_from_html(page_html, page_url)
   findings.extend(schema_findings)

   # Content Format (FIXED) — uses real HTML
   fmt_res = audit_page_format(page_url, html=page_html, client_keys=client_keys)

   # All new Phase 2 modules — use real HTML
   ```

3. **Fallback:** If page fetch fails, content/freshness/media checks are skipped (they emit `info`-severity unverifiable findings), just like schema already does.

---

## Phase 2 — New Automated Auditor Modules

Seven new modules, each following the existing pattern: dataclass result → finding dicts → check codes.

---

### [NEW] [freshness_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/freshness_auditor.py)

**Study B:** C060 — "Freshness/update-cadence checks are fully mechanical and automatable." (5/5 consensus, high confidence)

**What it checks:**
- Parse `datePublished` and `dateModified` from JSON-LD schema blocks
- Parse `<meta property="article:published_time">` and `<meta property="article:modified_time">` from HTML
- Parse visible date patterns in first 5 text blocks (regex: `YYYY-MM-DD`, `Month DD, YYYY`, etc.)
- Compare schema dates vs visible dates — flag mismatches
- Flag content older than 18 months with no `dateModified`

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `CONTENT_STALE` | warning | content | 4 |
| `DATE_MISMATCH_SCHEMA_VS_VISIBLE` | warning | schema | 3 |
| `NO_PUBLISHED_DATE` | info | content | 2 |

---

### [NEW] [redirect_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/redirect_auditor.py)

**Study B:** C040 — "Redirect-chain following, canonical-tag auditing, and HTTP status-code/crawl-error enumeration are fully mechanical." (5/5 consensus)

**What it checks:**
- Count redirect hops (from the page fetch — `safe_get` already follows manually)
- Extract `<link rel="canonical">` from HTML — compare against final URL
- Detect `<meta name="robots" content="noindex">`

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `REDIRECT_CHAIN_LONG` | warning | access | 3 |
| `CANONICAL_MISMATCH` | warning | schema | 4 |
| `CANONICAL_MISSING` | info | schema | 2 |
| `META_NOINDEX` | error | access | 8 |

---

### [NEW] [cloaking_detector.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/cloaking_detector.py)

**Study B:** C036 — "Fetching pages with spoofed AI-crawler user-agent strings and diffing the response is mechanically scriptable." (2/5 partial)

**What it checks:**
- Fetch page with normal browser UA (already done — reuse `page_html`)
- Fetch page with `GPTBot/1.0` UA (second fetch)
- Compare: >20% text delta → cloaking. HTTP 403/451 for bot UA → blocked.

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `CLOAKING_DETECTED` | error | access | 10 |
| `AI_BOT_BLOCKED_HTTP` | error | access | 8 |
| `CLOAKING_MINOR` | warning | access | 3 |

---

### [NEW] [entity_verifier.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/entity_verifier.py)

**Study B:** C056 (5/5) + C057 (2/5) — Entity verification and NER-vs-Schema consistency.

**What it checks:**
- Extract `sameAs` URLs from Organization/LocalBusiness JSON-LD
- Validate each `sameAs` URL returns HTTP 200 (dead link check)
- Check if any `sameAs` links to Wikidata/Wikipedia
- Extract `name`/`alternateName` from Schema — check if they appear in visible page content

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `SAMEAS_DEAD_LINK` | warning | authority | 3 |
| `SAMEAS_MISSING` | info | authority | 2 |
| `ENTITY_NAME_MISMATCH` | warning | schema | 3 |
| `WIKIDATA_LINK_MISSING` | info | authority | 2 |

---

### [NEW] [media_blindness_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/media_blindness_auditor.py)

**Study B:** C058 — "Detecting reliance on iframes, canvas/image-only text, or embed-only content is mechanically detectable." (2/5 partial)

**What it checks:**
- Count `<iframe>` tags — flag if >3
- Detect `<canvas>` tags
- Check `<img>` tags for missing `alt` attributes
- Check `<video>` tags for missing `<track>` (transcript)

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `IFRAME_HEAVY` | warning | content | 4 |
| `IMAGES_MISSING_ALT` | warning | content | 3 |
| `VIDEO_NO_TRANSCRIPT` | info | content | 2 |

---

### [NEW] [sitemap_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/sitemap_auditor.py)

**Study B:** C010 — "Sitemap parsing/validation is fully automatable." (5/5 consensus)

**What it checks:**
- Fetch `https://{domain}/sitemap.xml` (SSRF-protected)
- Parse XML — count URLs, check `<lastmod>` presence
- Check if sitemap is referenced in `robots.txt`
- **Return parsed URL list** for Phase 6 multi-page crawl

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `SITEMAP_MISSING` | warning | access | 3 |
| `SITEMAP_EMPTY` | warning | access | 2 |
| `SITEMAP_NO_LASTMOD` | info | content | 2 |
| `SITEMAP_NOT_IN_ROBOTS` | info | access | 1 |

---

### [MODIFY] [citation_sampler.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/citation_sampler.py)

**Study B:** C075 — "Citation frequency, share-of-voice, competitive benchmarking is fully automatable arithmetic over already-collected data." (5/5 consensus)

**Add `compute_citation_analytics()`** — takes existing `CitationSampleResult`, returns:
- `citation_rate`: float (0.0–1.0)
- `per_prompt_rates`: dict per prompt → rate
- `competitor_domains`: list of other domains cited
- `share_of_voice`: target citations / total citations
- `unique_cited_urls`: count of distinct cited URLs

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `CITATION_RATE_LOW` | warning | citation | 15 |
| `SHARE_OF_VOICE_LOW` | warning | citation | 10 |
| `COMPETITOR_DOMINATES` | info | citation | 0 |

---

## Phase 3 — Wiring (Scoring + KB + Orchestrator)

### [MODIFY] [scoring.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/scoring.py)

Add all new check codes to `LAYER_DEDUCTIONS` and `ACCESS_GATE`:

```python
# ── Phase 2 additions ──────────────────────────────────────────────────
# AP-01 Access
"REDIRECT_CHAIN_LONG":             ("access",    3),
"META_NOINDEX":                    ("access",    8),
"CLOAKING_DETECTED":               ("access",   10),
"AI_BOT_BLOCKED_HTTP":             ("access",    8),
"CLOAKING_MINOR":                  ("access",    3),
"SITEMAP_MISSING":                 ("access",    3),
"SITEMAP_EMPTY":                   ("access",    2),
"SITEMAP_NOT_IN_ROBOTS":           ("access",    1),
# AP-02 Schema
"CANONICAL_MISMATCH":              ("schema",    4),
"CANONICAL_MISSING":               ("schema",    2),
"DATE_MISMATCH_SCHEMA_VS_VISIBLE": ("schema",    3),
"ENTITY_NAME_MISMATCH":            ("schema",    3),
# AP-03 Content
"CONTENT_STALE":                   ("content",   4),
"NO_PUBLISHED_DATE":               ("content",   2),
"SITEMAP_NO_LASTMOD":              ("content",   2),
"IFRAME_HEAVY":                    ("content",   4),
"IMAGES_MISSING_ALT":              ("content",   3),
"VIDEO_NO_TRANSCRIPT":             ("content",   2),
# AP-04 Citation
"CITATION_RATE_LOW":               ("citation", 15),
"SHARE_OF_VOICE_LOW":              ("citation", 10),
# AP-05 Authority
"SAMEAS_DEAD_LINK":                ("authority",  3),
"SAMEAS_MISSING":                  ("authority",  2),
"WIKIDATA_LINK_MISSING":           ("authority",  2),
# Phase 5 JS-rendering
"JS_CONTENT_DEPENDENCY":           ("content",   6),
"JS_CRITICAL_CONTENT_GATED":       ("content",   8),
# Phase 6 Multi-page
"MULTI_PAGE_SCHEMA_GAPS":          ("schema",    3),
"MULTI_PAGE_FRESHNESS_ISSUE":      ("content",   3),
```

New access gates:
```python
"CLOAKING_DETECTED":  35,
"META_NOINDEX":       15,
```

### [MODIFY] [check_code_to_knowledge_map.json](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/kb/check_code_to_knowledge_map.json)

Add entries for:
- 4 previously-missing existing codes: `SCHEMA_MISSING`, `SCHEMA_UNVERIFIABLE`, `ROBOTS_UNVERIFIABLE`, `LLMS_UNVERIFIABLE`
- All ~28 new check codes from Phases 2, 5, 6, 7 — each mapped to a new `KT-2xx` GUIDANCE record

### [MODIFY] [audit_orchestrator.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/audit_orchestrator.py)

- Integrate all new modules into the orchestration flow (single page fetch → fan out to all auditors)
- Add new `ACTION_SNIPPETS` entries for all new check codes
- Fix `audited_stages` to include `"AP-03"` (currently missing)
- Import all new modules

### [MODIFY] [error_codes.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/api/error_codes.py)

Add `PAGE_FETCH_FAILED` error code.

---

## Phase 4 — Enhance Existing Modules

### [MODIFY] [content_format_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/content_format_auditor.py)

Now that real HTML flows in, enhance the answer position check to match the Indig/Bright Data finding (Study B C051): check if substantive content is in the first 30% of page content, not just first 3 blocks.

### [MODIFY] [robots_checker.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/robots_checker.py)

Extract `Sitemap:` directive URLs from robots.txt and expose via the `RobotsResult` dataclass (needed by `sitemap_auditor` to check `SITEMAP_NOT_IN_ROBOTS`).

---

## Phase 5 — JS-Rendering Diff (Optional Playwright)

**Study B:** C030 — "Diffing raw HTML against a headless-browser-rendered DOM is fully mechanical and one of the cleanest, most mature checks." (5/5 consensus, high confidence) + C031, C033.

### [NEW] [rendering_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/rendering_auditor.py)

**Architecture:**
- Import Playwright inside a `try/except ImportError` — if not installed, the module exposes a no-op stub that returns an empty result
- If available: launch headless Chromium, navigate to `page_url`, wait for network idle, extract `document.body.innerText`
- Diff raw-HTML-extracted text vs rendered text using `difflib.SequenceMatcher`
- Ratio < 0.8 → significant JS dependency
- Also detect: lazy-loaded elements (`data-src`, `loading="lazy"`), accordion/tab hidden content (`display:none`, `aria-expanded="false"`)

**Graceful degradation:**
```python
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def audit_js_rendering(page_url: str, raw_html: str) -> RenderingAuditResult:
    if not PLAYWRIGHT_AVAILABLE:
        return RenderingAuditResult(skipped=True, reason="playwright not installed")
    ...
```

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `JS_CONTENT_DEPENDENCY` | warning | content | 6 |
| `JS_CRITICAL_CONTENT_GATED` | error | content | 8 |
| `LAZY_LOAD_HIDDEN` | info | content | 2 |
| `HIDDEN_CONTENT_DEFAULT` | warning | content | 3 |

**Orchestrator integration:**
```python
# Phase 5 — JS rendering diff (optional)
from areos.auditors.rendering_auditor import audit_js_rendering, PLAYWRIGHT_AVAILABLE
if PLAYWRIGHT_AVAILABLE and page_html:
    try:
        render_res = audit_js_rendering(page_url, page_html)
        if not render_res.skipped:
            findings.extend(render_res.as_finding_dicts())
    except Exception:
        pass  # best-effort — never crash the audit
```

### [MODIFY] [requirements.txt](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/requirements.txt)

Add as optional dependency (comment-documented, not installed by default):
```
# Optional: JS-rendering diff (C030/C031/C033)
# pip install playwright && playwright install chromium
# playwright==1.52.0
```

### [MODIFY] [render.yaml](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/render.yaml)

Add optional buildCommand for Playwright Chromium if environment var `AREOS_ENABLE_PLAYWRIGHT=1` is set:
```yaml
buildCommand: |
  pip install -r requirements.txt
  if [ "$AREOS_ENABLE_PLAYWRIGHT" = "1" ]; then
    pip install playwright && playwright install --with-deps chromium
  fi
```

---

## Phase 6 — Limited Multi-Page Crawl

**Study B:** C010 — "Full-site crawling to build a page/URL inventory is fully automatable." (5/5 consensus) + C041 duplicate detection (5/5)

### [NEW] [multipage_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/multipage_auditor.py)

**Architecture:**
- Takes the URL list from `sitemap_auditor` (parsed from sitemap.xml)
- Crawls **top 10 pages** (sorted by `<lastmod>` recency, falling back to sitemap order)
- For each page: runs a lightweight version of the single-page checks (schema validation, freshness, content density)
- Aggregates findings across all pages into summary check codes
- Respects `robots.txt` directives for crawled paths
- Uses `safe_get` for SSRF protection on every URL
- Timeout per page: 4s. Total phase timeout: 45s. If timeout reached, report what was collected.

**What it checks per page:**
- Schema presence (JSON-LD exists? @type present?)
- Content density (word count > 30?)
- Published/modified dates (stale content?)
- Deduplication: compare page text via `difflib.SequenceMatcher` against previously-crawled pages — flag near-duplicates (ratio > 0.85)

**Aggregate check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `MULTI_PAGE_SCHEMA_GAPS` | warning | schema | 3 |
| `MULTI_PAGE_FRESHNESS_ISSUE` | warning | content | 3 |
| `MULTI_PAGE_THIN_CONTENT` | warning | content | 3 |
| `NEAR_DUPLICATE_PAGES` | warning | content | 4 |
| `SITEMAP_PAGES_UNREACHABLE` | warning | access | 2 |

**Orchestrator integration:**
```python
# Phase 6 — Multi-page crawl from sitemap (best-effort)
if sitemap_res.urls:
    try:
        multi_res = audit_multi_page(
            sitemap_res.urls[:10], clean_domain, robots_result=res_rob
        )
        findings.extend(multi_res.as_finding_dicts())
    except Exception:
        pass  # best-effort — single-page results are always valid
```

---

## Phase 7 — Competitor Extraction from Citation Data

**Study B:** C080 — "Crawling competitor sites and mechanically comparing their schema coverage, technical implementation, and content-feature presence against your own is fully automatable." (3/5 consensus)

### [MODIFY] [citation_sampler.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/citation_sampler.py)

**What to add to `compute_citation_analytics()`:**
- Extract all unique domains from `cited_urls` across all observations
- Filter out the target domain itself
- Rank competitor domains by citation frequency
- For the **top 3 competitor domains**: fetch their homepage, run `_validate_schema_from_html()` and `audit_page_format()` to compare schema coverage and content structure

### [NEW] [competitor_analyzer.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/areos/auditors/competitor_analyzer.py)

**What it checks:**
- Takes the top 3 competitor domains from citation analytics
- For each: fetch homepage → extract JSON-LD → count schema types → check content format
- Compare against target domain's results:
  - Competitor has schema types target doesn't? Flag.
  - Competitor has better content structure? Flag.

**New check codes:**

| Code | Severity | Layer | Deduction |
|------|----------|-------|-----------|
| `COMPETITOR_SCHEMA_ADVANTAGE` | info | schema | 0 |
| `COMPETITOR_CONTENT_ADVANTAGE` | info | content | 0 |
| `COMPETITOR_DOMINATES` | info | citation | 0 |

> [!NOTE]
> Competitor checks are **info-only** — they don't deduct score points. They provide strategic intelligence in the remediation plan, not penalty. The competitor data is already being captured by the citation sampler; we're just extracting value from it.

**Orchestrator integration:**
```python
# Phase 7 — Competitor extraction (best-effort, info-only)
if citation_obs and cited_runs > 0:
    try:
        comp_res = analyze_competitors(
            sample_res, clean_domain, page_html, json_ld_blocks
        )
        findings.extend(comp_res.as_finding_dicts())
    except Exception:
        pass
```

---

## Phase 8 — Tests

### New test files

| File | What it tests |
|------|---------------|
| [test_freshness_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_freshness_auditor.py) | Stale content, date mismatches, no dates |
| [test_redirect_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_redirect_auditor.py) | Redirect chains, canonical mismatch, noindex |
| [test_cloaking_detector.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_cloaking_detector.py) | UA-based content diff, HTTP 403 for bots |
| [test_entity_verifier.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_entity_verifier.py) | sameAs validation, name consistency |
| [test_media_blindness.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_media_blindness.py) | iframe count, missing alt, missing transcript |
| [test_sitemap_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_sitemap_auditor.py) | Missing sitemap, empty sitemap, lastmod checks |
| [test_citation_analytics.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_citation_analytics.py) | Share-of-voice, citation rate, competitor extraction |
| [test_rendering_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_rendering_auditor.py) | JS diff (with Playwright mocked), graceful skip |
| [test_multipage_auditor.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_multipage_auditor.py) | Multi-page crawl, duplicate detection, timeout |
| [test_competitor_analyzer.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_competitor_analyzer.py) | Competitor schema/content comparison |

### Modified test files

- **[test_kb_parity.py](file:///D:/07%20Transfer-20260727T165431Z-1-001/Antigravity%2026-07%20Transfer/AREOS_COMPLETE_WORKSPACE/tests/test_kb_parity.py):** Add check that every code in `LAYER_DEDUCTIONS` has a corresponding entry in `check_code_to_knowledge_map.json`.
- **Existing tests:** Run full suite to verify no regressions.

---

## Final Coverage Summary

### Before vs After

| Metric | Before | After |
|--------|--------|-------|
| Check codes | ~30 | **~58** |
| Study B fully-automatable items covered (of 14) | 4 | **13** |
| Study B partially-automatable mechanical parts covered (of 17) | 3 | **13** |
| Not-automatable correctly delegated to manual (of 14) | 14 | **14** |
| Score based on real data | 80% | **100%** |
| Overall AEOGEO lifecycle coverage | ~40% | **~95%** |

### Study B Coverage Map After Implementation

| Claim | Status |
|-------|--------|
| C010 Sitemap/crawl | ✅ Sitemap validation + limited multi-page crawl |
| C011 robots.txt | ✅ Already implemented (13 crawlers) |
| C016 llms.txt | ✅ Already implemented |
| C030 HTML vs DOM diff | ✅ Optional Playwright rendering auditor |
| C033 Lazy-loaded content | ✅ Part of rendering auditor |
| C036 Cloaking detection | ✅ NEW cloaking_detector |
| C040 Redirects/canonical | ✅ NEW redirect_auditor |
| C041 Duplicate detection | ✅ Part of multipage_auditor |
| C050 Structural content | ✅ FIXED (real HTML now) |
| C053 JSON-LD validation | ✅ Already implemented |
| C056 Entity verification | ✅ NEW entity_verifier |
| C057 NER vs Schema | ✅ Part of entity_verifier |
| C058 Media blindness | ✅ NEW media_blindness_auditor |
| C060 Freshness checks | ✅ NEW freshness_auditor |
| C070 nosnippet/noai | ✅ Already implemented |
| C071 Citation sampling | ✅ Already implemented |
| C075 Citation analytics | ✅ NEW citation analytics enhancement |
| C077 Sentiment analysis | ⚠️ Deferred — best done with an LLM classifier, orthogonal to this plan |
| C079 Speakable schema | ⚠️ Low value — very few sites use it |
| C080 Competitor comparison | ✅ NEW competitor_analyzer |
| C092 Monitoring | ❌ Point-in-time architecture — intentional |

### Only Excluded

| Item | Reason |
|------|--------|
| C019 Server log parsing | Requires client-provided data we genuinely cannot access |
| C077 Sentiment analysis | Requires LLM classifier inference — adds API cost and latency. Orthogonal to the diagnostic layer; better as a post-synthesis step |
| C079 Speakable schema | Extremely low adoption — no measurable ROI |
| C092 Continuous monitoring | Citeable is architecturally point-in-time by design; monitoring would be a separate product |

---

## Execution Order

| Step | Phase | What | Est. Time |
|------|-------|------|-----------|
| 1 | 0 | Fix critical bugs (synthesis_engine, build_kb) | 15 min |
| 2 | 1 | Fix content input (refactor page fetch, share HTML) | 25 min |
| 3 | 2a | freshness_auditor.py | 20 min |
| 4 | 2b | redirect_auditor.py | 20 min |
| 5 | 2c | cloaking_detector.py | 20 min |
| 6 | 2d | entity_verifier.py | 20 min |
| 7 | 2e | media_blindness_auditor.py | 15 min |
| 8 | 2f | sitemap_auditor.py | 15 min |
| 9 | 2g | Citation analytics enhancement | 15 min |
| 10 | 3 | Scoring + KB wiring + orchestrator integration | 35 min |
| 11 | 4 | Enhance existing modules | 10 min |
| 12 | 5 | rendering_auditor.py (Playwright optional) | 25 min |
| 13 | 6 | multipage_auditor.py | 25 min |
| 14 | 7 | competitor_analyzer.py | 20 min |
| 15 | 8 | Tests for all new modules | 40 min |
| **Total** | | | **~5 hours** |

## Verification Plan

### Automated Tests
```bash
cd "D:\07 Transfer-20260727T165431Z-1-001\Antigravity 26-07 Transfer\AREOS_COMPLETE_WORKSPACE"
python -m pytest tests/ -v
```

### Manual Verification
1. Run a live audit against `madmarketers.com` and verify:
   - All new check codes appear in findings where applicable
   - Score reflects real page content
   - Remediation plan includes new recommendations
   - No existing UI breaks
2. Run with Playwright disabled → verify graceful degradation (no crash, skip message)
3. Verify the 4 previously-missing check codes now resolve to GUIDANCE records
