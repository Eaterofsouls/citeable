# Phase 1 & 2 Infrastructure & Architecture Specification

## Phase 1: The `_fetch_page` Refactor

### 1. The Core Fetch Function (Orchestrator)

Add this function to `areos/auditors/audit_orchestrator.py` to replace `_fetch_and_validate_schema`'s fetching logic.

```python
def _fetch_page(clean_domain: str, page_url: str) -> tuple[str, int, str]:
    """
    Fetch the target page. 
    
    Args:
        clean_domain: The sanitized domain string.
        page_url: The full https:// URL.
        
    Returns:
        tuple[str, int, str]: (page_html, redirect_hop_count, final_url)
        Returns ('', 0, page_url) on fetch failure.
    """
    from areos.util.ssrf import validate_domain_ssrf, safe_get
    import requests
    
    validate_domain_ssrf(clean_domain)
    
    try:
        # safe_get manually follows redirects, so history is not strictly on the final resp.
        # For simplicity, we just count them if safe_get is updated.
        resp = safe_get(page_url, timeout=4)
        if resp.status_code == 200:
            return resp.text, len(resp.history) if hasattr(resp, 'history') else 0, resp.url
        return "", 0, page_url
    except (requests.exceptions.RequestException, ValueError):
        return "", 0, page_url
```

### 2. Schema Validation Refactor

Add `_extract_schema_claims` to `areos/auditors/schema_validator.py`. 

```python
def _extract_schema_claims(blocks: list[dict]) -> list[dict]:
    """Extract human-readable claims from JSON-LD for manual review display."""
    claims = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        schema_type = block.get("@type", "Unknown")
        if isinstance(schema_type, list):
            schema_type = schema_type[0]
            
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

### 3. Changes to `run_orchestrated_audit`

In `areos/auditors/audit_orchestrator.py`, replace the schema validation and format audit sections:

```python
    # NEW: Fetch page once
    page_html, hop_count, final_url = _fetch_page(clean_domain, page_url)
    
    # 2. Schema & JSON-LD Structure
    json_ld_blocks = _extract_json_ld_blocks(page_html) if page_html else []
    
    if not page_html:
        schema_findings = [{
            "code": "SCHEMA_UNVERIFIABLE",
            "severity": "info",
            "message": "Could not fetch the page to validate structured data; result is unverifiable.",
            "page_url": page_url,
        }]
    elif not json_ld_blocks:
        schema_findings = [{"code": "SCHEMA_MISSING", "severity": "warning", "message": "No JSON-LD structured data found on the page.", "page_url": page_url}]
    else:
        results = validate_page_schemas(json_ld_blocks)
        schema_findings = []
        for result in results:
            if not result.issues:
                schema_findings.append({"code": "ANSWER_FORMAT_GOOD", "severity": "info", "message": f"{result.schema_type} schema block is well-formed.", "page_url": page_url})
                continue
            for issue in result.issues:
                schema_findings.append({"code": issue.code, "severity": issue.severity, "message": f"[{result.schema_type}] {issue.message}", "page_url": page_url})
    
    findings.extend(schema_findings)
    
    # Add extracted schema claims to output payload (data contract)
    schema_claims = _extract_schema_claims(json_ld_blocks) if json_ld_blocks else []

    # 3. AI Extractability & Content Formatting
    if page_html:
        fmt_res = audit_page_format(page_url, html=page_html, client_keys=client_keys)
        for iss in fmt_res.issues:
            if iss.code != "ANSWER_FORMAT_GOOD":
                findings.append({
                    "code": iss.code,
                    "severity": iss.severity,
                    "message": iss.message,
                    "page_url": page_url
                })
    else:
        findings.append({
            "code": "PAGE_FETCH_FAILED",
            "severity": "info",
            "message": "Page content could not be retrieved, skipping format checks.",
            "page_url": page_url
        })
```

### 4. Updating `FormatAuditResult`

In `areos/auditors/content_format_auditor.py`:

```python
@dataclass
class FormatAuditResult:
    url: str
    passed: bool
    issues: list[FormatIssue] = field(default_factory=list)
    signals_analyzed: dict = field(default_factory=dict)
    extracted_lead_text: str = ""  # NEW: first ~150 words of main content
```

---

## Phase 2: The 7 New Auditor Modules

### 1. Freshness Auditor
**File:** `areos/auditors/freshness_auditor.py`

**Dataclass:**
```python
from dataclasses import dataclass, field

@dataclass
class FreshnessIssue:
    severity: str
    code: str
    message: str

@dataclass
class FreshnessAuditResult:
    url: str
    passed: bool
    issues: list[FreshnessIssue] = field(default_factory=list)
    
    def as_finding_dicts(self) -> list[dict]:
        return [{"code": i.code, "severity": i.severity, "message": i.message, "page_url": self.url} for i in self.issues]
```

**Signature:**
```python
def audit_freshness(page_url: str, html: str, json_ld_blocks: list[dict]) -> FreshnessAuditResult:
    """Audit datePublished, dateModified, and visible dates."""
```

**Tests (`tests/test_freshness_auditor.py`):**
```python
def test_freshness_stale():
    html = "<meta property='article:published_time' content='2020-01-01'>"
    res = audit_freshness("http://test.com", html, [])
    assert any(i.code == "CONTENT_STALE" for i in res.issues)

def test_freshness_mismatch():
    html = "<html><body>Published on 2025-01-01</body></html>"
    json_ld = [{"@type": "Article", "datePublished": "2020-01-01"}]
    res = audit_freshness("http://test.com", html, json_ld)
    assert any(i.code == "DATE_MISMATCH_SCHEMA_VS_VISIBLE" for i in res.issues)

def test_freshness_no_dates():
    res = audit_freshness("http://test.com", "<html><body>No dates here</body></html>", [])
    assert any(i.code == "NO_PUBLISHED_DATE" for i in res.issues)
```

### 2. Redirect Auditor
**File:** `areos/auditors/redirect_auditor.py`

**Dataclass:**
```python
@dataclass
class RedirectIssue:
    severity: str
    code: str
    message: str

@dataclass
class RedirectAuditResult:
    url: str
    passed: bool
    issues: list[RedirectIssue] = field(default_factory=list)
```

**Signature:**
```python
def audit_redirects_and_access(page_url: str, html: str, hop_count: int, final_url: str) -> RedirectAuditResult:
    """Audit redirect chains, canonical tags, and noindex."""
```

**Tests (`tests/test_redirect_auditor.py`):**
```python
def test_redirect_chain_long():
    res = audit_redirects_and_access("http://test.com", "<html></html>", hop_count=4, final_url="http://test.com/final")
    assert any(i.code == "REDIRECT_CHAIN_LONG" for i in res.issues)

def test_canonical_mismatch():
    html = '<link rel="canonical" href="http://other.com" />'
    res = audit_redirects_and_access("http://test.com", html, 0, "http://test.com")
    assert any(i.code == "CANONICAL_MISMATCH" for i in res.issues)

def test_meta_noindex():
    html = '<meta name="robots" content="noindex">'
    res = audit_redirects_and_access("http://test.com", html, 0, "http://test.com")
    assert any(i.code == "META_NOINDEX" for i in res.issues)
```

### 3. Cloaking Detector
**File:** `areos/auditors/cloaking_detector.py`

**Dataclass:**
```python
@dataclass
class CloakingIssue:
    severity: str
    code: str
    message: str

@dataclass
class CloakingResult:
    url: str
    passed: bool
    issues: list[CloakingIssue] = field(default_factory=list)
    browser_word_count: int = 0
    bot_word_count: int = 0
    missing_elements: list[str] = field(default_factory=list)
    content_diff_summary: str = ""
```

**Signature:**
```python
def audit_cloaking(clean_domain: str, page_url: str, browser_html: str) -> CloakingResult:
    """Fetch with GPTBot UA and diff against normal browser HTML."""
```

**Tests (`tests/test_cloaking_detector.py`):**
```python
def test_cloaking_detected(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 200, 'text': 'Short bot text'})())
    res = audit_cloaking("test.com", "http://test.com", "This is a very long normal browser text with lots of words.")
    assert any(i.code == "CLOAKING_DETECTED" for i in res.issues)

def test_bot_blocked_http(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 403, 'text': ''})())
    res = audit_cloaking("test.com", "http://test.com", "Normal")
    assert any(i.code == "AI_BOT_BLOCKED_HTTP" for i in res.issues)

def test_cloaking_pass(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 200, 'text': 'Normal text'})())
    res = audit_cloaking("test.com", "http://test.com", "Normal text")
    assert res.passed
```

### 4. Entity Verifier
**File:** `areos/auditors/entity_verifier.py`

**Dataclass:**
```python
@dataclass
class EntityIssue:
    severity: str
    code: str
    message: str

@dataclass
class EntityAuditResult:
    url: str
    passed: bool
    issues: list[EntityIssue] = field(default_factory=list)
```

**Signature:**
```python
def audit_entities(page_url: str, html: str, json_ld_blocks: list[dict]) -> EntityAuditResult:
    """Verify sameAs links, wikidata presence, and NER/Schema consistency."""
```

**Tests (`tests/test_entity_verifier.py`):**
```python
def test_sameas_dead_link(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 404})())
    json_ld = [{"@type": "Organization", "sameAs": ["http://dead.link"]}]
    res = audit_entities("http://test.com", "", json_ld)
    assert any(i.code == "SAMEAS_DEAD_LINK" for i in res.issues)

def test_entity_name_mismatch():
    json_ld = [{"@type": "Organization", "name": "SecretCorp"}]
    res = audit_entities("http://test.com", "<html><body>Welcome to PublicCorp</body></html>", json_ld)
    assert any(i.code == "ENTITY_NAME_MISMATCH" for i in res.issues)

def test_wikidata_missing():
    json_ld = [{"@type": "Organization", "sameAs": ["http://twitter.com"]}]
    res = audit_entities("http://test.com", "", json_ld)
    assert any(i.code == "WIKIDATA_LINK_MISSING" for i in res.issues)
```

### 5. Media Blindness Auditor
**File:** `areos/auditors/media_blindness_auditor.py`

**Dataclass:**
```python
@dataclass
class MediaIssue:
    severity: str
    code: str
    message: str

@dataclass
class MediaAuditResult:
    url: str
    passed: bool
    issues: list[MediaIssue] = field(default_factory=list)
```

**Signature:**
```python
def audit_media_blindness(page_url: str, html: str) -> MediaAuditResult:
    """Detect reliance on iframes, canvas, and missing alt text."""
```

**Tests (`tests/test_media_blindness.py`):**
```python
def test_iframe_heavy():
    html = "<iframe></iframe>" * 4
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "IFRAME_HEAVY" for i in res.issues)

def test_images_missing_alt():
    html = "<img src='test.jpg'>"
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "IMAGES_MISSING_ALT" for i in res.issues)

def test_video_no_transcript():
    html = "<video src='test.mp4'></video>"
    res = audit_media_blindness("http://test.com", html)
    assert any(i.code == "VIDEO_NO_TRANSCRIPT" for i in res.issues)
```

### 6. Sitemap Auditor
**File:** `areos/auditors/sitemap_auditor.py`

**Dataclass:**
```python
@dataclass
class SitemapIssue:
    severity: str
    code: str
    message: str

@dataclass
class SitemapAuditResult:
    url: str
    passed: bool
    issues: list[SitemapIssue] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
```

**Signature:**
```python
def audit_sitemap(clean_domain: str, robots_result) -> SitemapAuditResult:
    """Fetch and parse sitemap.xml."""
```

**Tests (`tests/test_sitemap_auditor.py`):**
```python
def test_sitemap_missing(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 404})())
    res = audit_sitemap("test.com", None)
    assert any(i.code == "SITEMAP_MISSING" for i in res.issues)

def test_sitemap_empty(monkeypatch):
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 200, 'text': '<urlset></urlset>'})())
    res = audit_sitemap("test.com", None)
    assert any(i.code == "SITEMAP_EMPTY" for i in res.issues)

def test_sitemap_no_lastmod(monkeypatch):
    xml = "<urlset><url><loc>http://test.com</loc></url></urlset>"
    monkeypatch.setattr("areos.util.ssrf.safe_get", lambda *a, **kw: type('obj', (object,), {'status_code': 200, 'text': xml})())
    res = audit_sitemap("test.com", None)
    assert any(i.code == "SITEMAP_NO_LASTMOD" for i in res.issues)
```

### 7. Citation Analytics Enhancement
**File:** Modify `areos/auditors/citation_sampler.py`

**Changes:**
Add `compute_citation_analytics` function.
Update `CitationObservation` with `full_answer_text`.
Update `_query_perplexity` and `_query_gemini_grounded` to NOT truncate `full_answer_text`.

**Signature:**
```python
def compute_citation_analytics(sample_result: CitationSampleResult) -> dict:
    """Compute share of voice, rates, and competitor domains."""
```

**Tests (`tests/test_citation_analytics.py`):**
```python
def test_share_of_voice():
    # Provide mock CitationSampleResult
    res = compute_citation_analytics(mock_sample_result)
    assert res['share_of_voice'] == 0.5
    
def test_competitor_extraction():
    # Provide mock data with competitor URLs
    res = compute_citation_analytics(mock_sample_result)
    assert "competitor.com" in res['competitor_domains']
```

---

## Architectural Gaps & Mitigations

1. **HTTP 403, 429, 503, Connection Timeouts**
   *Gap:* `safe_get` handles these by raising `RequestException` or returning non-200.
   *Mitigation:* `_fetch_page` will return `""`. Modules receiving empty HTML gracefully emit `PAGE_FETCH_FAILED` or `SCHEMA_UNVERIFIABLE` and skip deeper checks. 

2. **Pages > 10MB**
   *Gap:* `requests.get` loads full response into memory. Huge pages can cause OOM.
   *Mitigation:* Pass `stream=True` to `safe_get` and enforce a content-length check. Truncate reading at 5MB.

3. **Non-UTF-8 Encodings**
   *Gap:* Potential mojibake on `resp.text`.
   *Mitigation:* Ensure `resp.encoding` is explicitly checked. Fallback to `cchardet` or strict utf-8 parsing with `errors='replace'`.

4. **Redirect Loops**
   *Gap:* Caught by `safe_get` max_redirects limit, throwing `ValueError`.
   *Mitigation:* Handled seamlessly in `_fetch_page` try/except block.

5. **Concurrent DB Access**
   *Gap:* SQLite `OperationalError: database is locked`.
   *Mitigation:* Ensure SQLite connection has WAL mode enabled and timeout pragmas set high (e.g., 30s).

6. **External API Rate Limiting (Perplexity, Gemini)**
   *Gap:* High concurrency triggers 429s.
   *Mitigation:* `circuit_breaker` is passed through. We must aggressively capture 429s in `citation_sampler` and trip the breaker.

7. **Import Cycles**
   *Gap:* Modules needing `_extract_json_ld_blocks` from `audit_orchestrator` can cause circular imports.
   *Mitigation:* Move `_extract_json_ld_blocks` into a utility file like `areos/util/schema_utils.py`.

8. **Memory Implications of Full AI Responses**
   *Gap:* Storing 15 full text responses (up to 3KB each) adds 45KB per run to SQLite.
   *Mitigation:* Acceptable for SQLite `TEXT` columns. Compress historical JSON payload if needed in the long run.
