# Phases 3-4: KB Wiring & Scoring Spec

## Phase 3: KB Wiring (check_code_to_knowledge_map.json & ACTION_SNIPPETS)

The following entries map new and previously unmapped check codes to Knowledge Base GUIDANCE records (KT-2xx series) and actionable remediation snippets.

### 1. The 4 Previously Missing Existing Check Codes
These are currently checked by the orchestrator but fail to map.

**`SCHEMA_MISSING`**
- **Map Entry:** `{"guidance_record": "KT-200", "backing_records": ["KT-179"]}`
- **Guidance Text:** "The page lacks any JSON-LD structured data. Without it, generative engines struggle to confidently extract entities and properties, falling back to heuristic parsing which is error-prone."
- **Action Snippet:** `"SCHEMA_MISSING": "<!-- Add foundational JSON-LD block -->\n<script type=\"application/ld+json\">\n{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Organization\",\n  \"name\": \"Your Brand\"\n}\n</script>"`

**`SCHEMA_UNVERIFIABLE`**
- **Map Entry:** `{"guidance_record": "KT-201", "backing_records": []}`
- **Guidance Text:** "The page could not be fetched by the schema validator, rendering its structured data unverifiable."
- **Action Snippet:** `"SCHEMA_UNVERIFIABLE": "/* Ensure the page returns HTTP 200 and does not block the auditor's IP. */"`

**`ROBOTS_UNVERIFIABLE`**
- **Map Entry:** `{"guidance_record": "KT-202", "backing_records": []}`
- **Guidance Text:** "The robots.txt file could not be fetched or parsed, leaving AI access rules unknown."
- **Action Snippet:** `"ROBOTS_UNVERIFIABLE": "/* Ensure /robots.txt is accessible and returns HTTP 200. */"`

**`LLMS_UNVERIFIABLE`**
- **Map Entry:** `{"guidance_record": "KT-203", "backing_records": []}`
- **Guidance Text:** "The llms.txt file could not be fetched or parsed."
- **Action Snippet:** `"LLMS_UNVERIFIABLE": "/* Ensure /llms.txt is accessible if present. */"`

### 2. New Phase 2 Check Codes (Freshness, Redirects, Cloaking, Entities, Media, Sitemaps, Citation)

**`CONTENT_STALE`**
- **Map Entry:** `{"guidance_record": "KT-204", "backing_records": []}`
- **Guidance Text:** "Content appears older than 18 months without modification. AI engines deprioritize stale entity descriptions in favor of recently verified sources."
- **Action Snippet:** `"CONTENT_STALE": "<!-- Update schema dates -->\n\"dateModified\": \"2026-08-31T12:00:00Z\""`

**`DATE_MISMATCH_SCHEMA_VS_VISIBLE`**
- **Map Entry:** `{"guidance_record": "KT-205", "backing_records": []}`
- **Guidance Text:** "The published/modified dates in the JSON-LD schema contradict the visible dates in the HTML text, reducing crawler trust."
- **Action Snippet:** `"DATE_MISMATCH_SCHEMA_VS_VISIBLE": "<!-- Ensure visible date matches schema -->\n<p>Last updated: August 31, 2026</p>"`

**`NO_PUBLISHED_DATE`**
- **Map Entry:** `{"guidance_record": "KT-206", "backing_records": []}`
- **Guidance Text:** "No explicit publication or modification date was found. Dates help AI engines gauge the recency and relevance of the information."
- **Action Snippet:** `"NO_PUBLISHED_DATE": "<!-- Add date to schema -->\n\"datePublished\": \"2026-08-01\""`

**`REDIRECT_CHAIN_LONG`**
- **Map Entry:** `{"guidance_record": "KT-207", "backing_records": []}`
- **Guidance Text:** "The URL passes through a long redirect chain. AI crawlers often abandon chains after 3-5 hops, leading to de-indexing."
- **Action Snippet:** `"REDIRECT_CHAIN_LONG": "/* Update internal links to point directly to the final destination URL. */"`

**`CANONICAL_MISMATCH`**
- **Map Entry:** `{"guidance_record": "KT-208", "backing_records": []}`
- **Guidance Text:** "The canonical URL tag points to a different URL than the one served, potentially confusing entity attribution."
- **Action Snippet:** `"CANONICAL_MISMATCH": "<link rel=\"canonical\" href=\"https://domain.com/exact-page\" />"`

**`CANONICAL_MISSING`**
- **Map Entry:** `{"guidance_record": "KT-209", "backing_records": []}`
- **Guidance Text:** "The page lacks a canonical tag, which can dilute citation credit if duplicate content exists."
- **Action Snippet:** `"CANONICAL_MISSING": "<link rel=\"canonical\" href=\"https://domain.com/exact-page\" />"`

**`META_NOINDEX`**
- **Map Entry:** `{"guidance_record": "KT-210", "backing_records": []}`
- **Guidance Text:** "The page explicitly requests not to be indexed via meta robots, completely preventing AI ingestion."
- **Action Snippet:** `"META_NOINDEX": "<!-- Remove noindex tag if page should be cited -->\n<meta name=\"robots\" content=\"index, follow\">"`

**`CLOAKING_DETECTED`**
- **Map Entry:** `{"guidance_record": "KT-211", "backing_records": []}`
- **Guidance Text:** "The content served to AI bot User-Agents drastically differs from human browsers. This violates transparency guidelines and risks a full domain ban from LLM corpuses."
- **Action Snippet:** `"CLOAKING_DETECTED": "/* Serve identical HTML payloads to GPTBot, Anthropic, and standard browsers. */"`

**`AI_BOT_BLOCKED_HTTP`**
- **Map Entry:** `{"guidance_record": "KT-212", "backing_records": []}`
- **Guidance Text:** "The server returns HTTP 403/451 when queried by AI bot User-Agents (e.g. GPTBot). This blocks LLM crawling at the firewall/WAF layer."
- **Action Snippet:** `"AI_BOT_BLOCKED_HTTP": "/* Whitelist AI User-Agents in WAF/Cloudflare rules. */"`

**`CLOAKING_MINOR`**
- **Map Entry:** `{"guidance_record": "KT-213", "backing_records": []}`
- **Guidance Text:** "Minor differences exist between the bot-rendered and human-rendered page. Ensure no critical factual content is missing."
- **Action Snippet:** `"CLOAKING_MINOR": "/* Verify dynamic content injection does not strip core text for bots. */"`

**`SAMEAS_DEAD_LINK`**
- **Map Entry:** `{"guidance_record": "KT-214", "backing_records": []}`
- **Guidance Text:** "A sameAs property in the JSON-LD points to a broken or dead URL, damaging trust in the entity's authority."
- **Action Snippet:** `"SAMEAS_DEAD_LINK": "/* Remove or update broken sameAs URLs in schema. */"`

**`SAMEAS_MISSING`**
- **Map Entry:** `{"guidance_record": "KT-215", "backing_records": []}`
- **Guidance Text:** "No sameAs properties found. These are critical for linking the brand to external knowledge graphs like Wikipedia or Crunchbase."
- **Action Snippet:** `"SAMEAS_MISSING": "\"sameAs\": [\"https://en.wikipedia.org/wiki/Brand\"]"`

**`ENTITY_NAME_MISMATCH`**
- **Map Entry:** `{"guidance_record": "KT-216", "backing_records": []}`
- **Guidance Text:** "The entity name in the schema does not match the visible name on the page, introducing ambiguity."
- **Action Snippet:** `"ENTITY_NAME_MISMATCH": "/* Ensure schema 'name' exactly mirrors the visible H1 brand name. */"`

**`WIKIDATA_LINK_MISSING`**
- **Map Entry:** `{"guidance_record": "KT-217", "backing_records": []}`
- **Guidance Text:** "No Wikidata or Wikipedia link found in the sameAs property. Connecting to open knowledge bases anchors the entity for AI."
- **Action Snippet:** `"WIKIDATA_LINK_MISSING": "\"sameAs\": [\"https://www.wikidata.org/wiki/Q123456\"]"`

**`IFRAME_HEAVY`**
- **Map Entry:** `{"guidance_record": "KT-218", "backing_records": []}`
- **Guidance Text:** "The page relies heavily on iframes. Most AI crawlers do not index iframe contents, making the text invisible to them."
- **Action Snippet:** `"IFRAME_HEAVY": "/* Extract critical iframe text into native HTML elements. */"`

**`IMAGES_MISSING_ALT`**
- **Map Entry:** `{"guidance_record": "KT-219", "backing_records": []}`
- **Guidance Text:** "Images lack descriptive alt text. Multimodal models rely on text descriptions for context."
- **Action Snippet:** `"IMAGES_MISSING_ALT": "<img src=\"logo.png\" alt=\"Descriptive text for the image\" />"`

**`VIDEO_NO_TRANSCRIPT`**
- **Map Entry:** `{"guidance_record": "KT-220", "backing_records": []}`
- **Guidance Text:** "Videos lack an embedded transcript track, hiding their content from text-first AI crawlers."
- **Action Snippet:** `"VIDEO_NO_TRANSCRIPT": "<track kind=\"captions\" src=\"transcript.vtt\" srclang=\"en\" />"`

**`SITEMAP_MISSING`**
- **Map Entry:** `{"guidance_record": "KT-221", "backing_records": []}`
- **Guidance Text:** "No sitemap.xml found. Sitemaps are the primary discovery mechanism for AI agent crawlers."
- **Action Snippet:** `"SITEMAP_MISSING": "/* Generate and host an XML sitemap at /sitemap.xml */"`

**`SITEMAP_EMPTY`**
- **Map Entry:** `{"guidance_record": "KT-222", "backing_records": []}`
- **Guidance Text:** "The sitemap.xml is empty or malformed."
- **Action Snippet:** `"SITEMAP_EMPTY": "/* Populate sitemap with valid <url> entries. */"`

**`SITEMAP_NO_LASTMOD`**
- **Map Entry:** `{"guidance_record": "KT-223", "backing_records": []}`
- **Guidance Text:** "Sitemap URLs lack the <lastmod> attribute, preventing crawlers from prioritizing fresh content."
- **Action Snippet:** `"SITEMAP_NO_LASTMOD": "<lastmod>2026-08-31T12:00:00Z</lastmod>"`

**`SITEMAP_NOT_IN_ROBOTS`**
- **Map Entry:** `{"guidance_record": "KT-224", "backing_records": []}`
- **Guidance Text:** "The sitemap is not referenced in robots.txt, making it harder for crawlers to discover."
- **Action Snippet:** `"SITEMAP_NOT_IN_ROBOTS": "Sitemap: https://domain.com/sitemap.xml"`

**`CITATION_RATE_LOW`**
- **Map Entry:** `{"guidance_record": "KT-225", "backing_records": []}`
- **Guidance Text:** "The brand is cited in fewer than 20% of relevant generative queries. This signifies low entity salience in LLM weighting."
- **Action Snippet:** `"CITATION_RATE_LOW": "/* Increase high-DR referring domains and unambiguous schema density. */"`

**`SHARE_OF_VOICE_LOW`**
- **Map Entry:** `{"guidance_record": "KT-226", "backing_records": []}`
- **Guidance Text:** "Competitors dominate the generative responses. The brand's share of voice is insufficient."
- **Action Snippet:** `"SHARE_OF_VOICE_LOW": "/* Restructure content to directly answer intent-based questions better than competitors. */"`

### 3. Phase 5 & 6 Check Codes (JS Render, Multipage, Competitor)

**`JS_CONTENT_DEPENDENCY`**
- **Map Entry:** `{"guidance_record": "KT-227", "backing_records": []}`
- **Guidance Text:** "Significant text is injected via JavaScript. Lightweight crawlers (like standard GPTBot) may miss this content."
- **Action Snippet:** `"JS_CONTENT_DEPENDENCY": "/* Implement Server-Side Rendering (SSR) for core content. */"`

**`JS_CRITICAL_CONTENT_GATED`**
- **Map Entry:** `{"guidance_record": "KT-228", "backing_records": []}`
- **Guidance Text:** "The primary definitional content is entirely missing in the raw HTML payload."
- **Action Snippet:** `"JS_CRITICAL_CONTENT_GATED": "<!-- Move critical description into static HTML body -->"`

**`LAZY_LOAD_HIDDEN`**
- **Map Entry:** `{"guidance_record": "KT-229", "backing_records": []}`
- **Guidance Text:** "Important elements rely on lazy-loading. Many bots do not execute scroll events."
- **Action Snippet:** `"LAZY_LOAD_HIDDEN": "<!-- Ensure text content is not tied to scroll event listeners -->"`

**`HIDDEN_CONTENT_DEFAULT`**
- **Map Entry:** `{"guidance_record": "KT-230", "backing_records": []}`
- **Guidance Text:** "Core text is hidden behind accordions or 'display: none'. Search engines often deprioritize hidden text."
- **Action Snippet:** `"HIDDEN_CONTENT_DEFAULT": "<!-- Make critical descriptions visible by default. -->"`

**`MULTI_PAGE_SCHEMA_GAPS`**
- **Map Entry:** `{"guidance_record": "KT-231", "backing_records": []}`
- **Guidance Text:** "Schema coverage is inconsistent across the site's top pages."
- **Action Snippet:** `"MULTI_PAGE_SCHEMA_GAPS": "/* Audit site templates to ensure schema injection on all major pages. */"`

**`MULTI_PAGE_FRESHNESS_ISSUE`**
- **Map Entry:** `{"guidance_record": "KT-232", "backing_records": []}`
- **Guidance Text:** "A significant portion of indexed pages appear stale."
- **Action Snippet:** `"MULTI_PAGE_FRESHNESS_ISSUE": "/* Schedule routine content audits and update modification dates. */"`

**`MULTI_PAGE_THIN_CONTENT`**
- **Map Entry:** `{"guidance_record": "KT-233", "backing_records": []}`
- **Guidance Text:** "Many pages suffer from low text density."
- **Action Snippet:** `"MULTI_PAGE_THIN_CONTENT": "/* Consolidate thin pages or expand them with substantive text. */"`

**`NEAR_DUPLICATE_PAGES`**
- **Map Entry:** `{"guidance_record": "KT-234", "backing_records": []}`
- **Guidance Text:** "Multiple pages contain highly similar content, diluting entity focus."
- **Action Snippet:** `"NEAR_DUPLICATE_PAGES": "/* Use canonical tags or merge duplicate pages. */"`

**`SITEMAP_PAGES_UNREACHABLE`**
- **Map Entry:** `{"guidance_record": "KT-235", "backing_records": []}`
- **Guidance Text:** "URLs listed in the sitemap return errors when fetched."
- **Action Snippet:** `"SITEMAP_PAGES_UNREACHABLE": "/* Remove 404/500 URLs from the XML sitemap. */"`

**Competitor codes (Info only)**
- `COMPETITOR_SCHEMA_ADVANTAGE` -> `KT-236`
- `COMPETITOR_CONTENT_ADVANTAGE` -> `KT-237`
- `COMPETITOR_DOMINATES` -> `KT-238`

*(All of the above should be formatted appropriately in `check_code_to_knowledge_map.json` and added to `audit_orchestrator.py:ACTION_SNIPPETS`)*

---

## Phase 4: Scoring Additions & Mathematical Verification

### LAYER_DEDUCTIONS Additions (`areos/auditors/scoring.py`)
```python
# AP-01 Access
"REDIRECT_CHAIN_LONG":             ("access",    3),
"META_NOINDEX":                    ("access",    8),
"CLOAKING_DETECTED":               ("access",   10),
"AI_BOT_BLOCKED_HTTP":             ("access",    8),
"CLOAKING_MINOR":                  ("access",    3),
"SITEMAP_MISSING":                 ("access",    3),
"SITEMAP_EMPTY":                   ("access",    2),
"SITEMAP_NOT_IN_ROBOTS":           ("access",    1),
"SITEMAP_PAGES_UNREACHABLE":       ("access",    2),
# AP-02 Schema
"CANONICAL_MISMATCH":              ("schema",    4),
"CANONICAL_MISSING":               ("schema",    2),
"DATE_MISMATCH_SCHEMA_VS_VISIBLE": ("schema",    3),
"ENTITY_NAME_MISMATCH":            ("schema",    3),
"MULTI_PAGE_SCHEMA_GAPS":          ("schema",    3),
# AP-03 Content
"CONTENT_STALE":                   ("content",   4),
"NO_PUBLISHED_DATE":               ("content",   2),
"SITEMAP_NO_LASTMOD":              ("content",   2),
"IFRAME_HEAVY":                    ("content",   4),
"IMAGES_MISSING_ALT":              ("content",   3),
"VIDEO_NO_TRANSCRIPT":             ("content",   2),
"JS_CONTENT_DEPENDENCY":           ("content",   6),
"JS_CRITICAL_CONTENT_GATED":       ("content",   8),
"LAZY_LOAD_HIDDEN":                ("content",   2),
"HIDDEN_CONTENT_DEFAULT":          ("content",   3),
"MULTI_PAGE_FRESHNESS_ISSUE":      ("content",   3),
"MULTI_PAGE_THIN_CONTENT":         ("content",   3),
"NEAR_DUPLICATE_PAGES":            ("content",   4),
# AP-04 Citation
"CITATION_RATE_LOW":               ("citation", 15),
"SHARE_OF_VOICE_LOW":              ("citation", 10),
# AP-05 Authority
"SAMEAS_DEAD_LINK":                ("authority",  3),
"SAMEAS_MISSING":                  ("authority",  2),
"WIKIDATA_LINK_MISSING":           ("authority",  2),
```

### ACCESS_GATE Additions
```python
"CLOAKING_DETECTED":  35,
"META_NOINDEX":       15,
```

### Mathematical Verification & Cap Adjustment
* Current Layer Maximums vs Deductions:
  - **Access (Max 20):** Old deduction sum = 54. New sum = 54 + 40 = 94.
  - **Schema (Max 15):** Old deduction sum = 37. New sum = 37 + 15 = 52.
  - **Content (Max 20):** Old deduction sum = 51. New sum = 51 + 46 = 97.
  - **Citation (Max 30):** Old deduction sum = 30. New sum = 30 + 25 = 55.
  - **Authority (Max 15):** Old deduction sum = 19. New sum = 19 + 7 = 26.
* **Findings vs Caps:** The deduction model is strictly additive up to the cap (each layer's score is floored at 0). This is functioning as designed. If an auditor wants more granularity to differentiate a "slightly broken" site from a "massively broken" site, layer caps could be adjusted, but doing so would fundamentally alter the "out of 100" scale balance. **Recommendation: Maintain current caps.** The UI/report simply needs to ensure that 0-impact deductions (where the layer is already at 0) are still displayed as findings.
* **Regression Tests:**
  - `test_every_check_code_in_map`: Ensure `set(LAYER_DEDUCTIONS.keys()).issubset(set(CHECK_CODE_TO_KNOWLEDGE_MAP.keys()))`
  - `test_every_action_snippet_in_layers`: Ensure `set(ACTION_SNIPPETS.keys()).issubset(set(LAYER_DEDUCTIONS.keys()))`
  - `test_score_floor_enforcement`: Run `compute_layered_score` with a payload of every possible check code and ensure `overall_score >= 5` and each layer score is 0.

---

## Data Integrity Gaps (Foundational Fixes)

1. **Missing Mapping for Existing Code (`SCHEMA_MISSING`)**
   - **Gap:** `SCHEMA_MISSING` exists in `LAYER_DEDUCTIONS` and is checked for by `audit_orchestrator.py`, but has no entry in `check_code_to_knowledge_map.json`.
   - **Fix:** Add to the map (see Phase 3 above).
2. **Missing Action Snippets**
   - **Gap:** Some existing check codes (e.g. `CRAWLER_PARTIAL`, `EXTRACTABILITY_NONE`, `MISSING_TYPE`) are in `LAYER_DEDUCTIONS` but have no entries in `ACTION_SNIPPETS`.
   - **Fix:** Add corresponding snippets for every code in `LAYER_DEDUCTIONS`.
3. **Router Exception Swallowing (`RISK-003`)**
   - **Gap:** In `areos/kb/router.py`, `_load_record()` does a `try/except Exception: pass` when parsing `guidance_json`. If a GUIDANCE record's JSON is malformed, it silently sets `guidance = None`, causing remediation text to disappear with no logs.
   - **Fix:** Catch specific JSON decode errors and log a warning.
4. **Dimension Mismatch Re-embedding**
   - **Gap:** `build_kb.py` pre-computes embeddings with the server's API key. At query time, `router.py` `_rag_search()` checks for dimension compatibility. If the dimensions differ (e.g., Gemini vs OpenAI models), it logs a warning and returns `[]`. It **does not** automatically re-embed the query or corpus to rectify the mismatch.
   - **Fix:** Update `_rag_search` to fall back to deterministic lookup or re-embed the query using the server's fallback API key model if dimensions clash.
5. **Orphaned Knowledge Records**
   - The knowledge corpus contains ~200 items, but only a subset are mapped. The unmapped items act as semantic enrichment for RAG, but they are never deterministically reached. This is acceptable under the V2 RAG design, provided the semantic search confidence thresholds remain robust.
