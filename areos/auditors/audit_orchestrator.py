# areos/auditors/audit_orchestrator.py
#
# Full-Spectrum AEO/GEO Automated Orchestrator
# Executes all 6 auditing layers simultaneously, records the audit run in SQLite,
# synthesizes a prioritized step-by-step remediation plan with governing citations,
# and generates an interactive guidance wizard for human manual review cards.

from __future__ import annotations

import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
import logging

from areos.api.error_codes import ErrorCode
from areos.services.cache import ttl_cache

logger = logging.getLogger(__name__)

@ttl_cache(ttl=300)
def _fetch_robots_txt(domain: str) -> str | None:
    try:
        # FIX (Readiness Audit, Critical 2): safe_get validates every hop
        r_resp = safe_get(f"https://{domain}/robots.txt", timeout=4, headers={"User-Agent": "AREOS-Auditor/1.0"})
        if r_resp and r_resp.status_code == 200:
            return r_resp.text
    except Exception as e:
        logger.warning("Failed to fetch robots.txt for domain %s: %s", domain, e)
    return None

from areos.auditors.authority_auditor import audit_domain_authority
from areos.auditors.citation_sampler import (
    TOS_CAVEAT,
    CitationObservation,
    CitationSampleResult,
    load_active_prompt_set,
    sample_citations,
)
from areos.auditors.content_format_auditor import audit_page_format

CITATION_SAMPLE_PROMPT_COUNT = 2
CITATION_SAMPLE_ENGINES = ["perplexity", "gemini"]
from areos.auditors.robots_checker import parse_llms_txt, parse_robots_txt
from areos.auditors.schema_validator import validate_page_schemas
from areos.auditors.synthesis_engine import synthesise
from areos.auditors.scoring import compute_layered_score, count_severity
from areos.cli.report import AuditRunSummary, select_triggered_cards
from areos.db.connection import get_connection
from areos.db.context import write_as
from areos.util.sanitize import sanitize_text
from areos.util.ssrf import safe_get, validate_domain_ssrf

# Actionable code snippets per check code to guide user implementations
ACTION_SNIPPETS = {
    "CRAWLER_FULLY_BLOCKED": "# Add to robots.txt:\nUser-agent: GPTBot\nAllow: /\n\nUser-agent: PerplexityBot\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /",  # noqa: E501
    "LLMS_TXT_MISSING": "# Create /llms.txt at web root:\n# Site Title\n> Primary value proposition and summary for AI assistants.\n\n## Core References\n- [Documentation](https://domain.com/docs): Full product guide.",  # noqa: E501
    "JSON_PARSE_FAILURE": "<!-- Validate JSON-LD syntax -->\n<script type=\"application/ld+json\">\n{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Organization\",\n  \"name\": \"Brand Name\",\n  \"url\": \"https://domain.com\"\n}\n</script>",  # noqa: E501
    "MISSING_REQUIRED_FIELD": "/* Ensure required schema properties are populated */\n\"name\": \"Verified Entity Title\",\n\"description\": \"Concrete, objective definitional description without conversational fluff.\"",  # noqa: E501
    "ANSWER_NOT_NEAR_TOP": "<!-- Move self-contained definition into top 30% of HTML body -->\n<section class=\"ai-direct-answer\">\n  <h2>What is [Brand]?</h2>\n  <p>[Brand] is an enterprise AEO/GEO optimization platform that automates citation tracking and schema compliance...</p>\n</section>",  # noqa: E501
    "ANSWER_NOT_SELF_CONTAINED": "<!-- Replace dangling demonstratives ('This tool...') with explicit entity subjects -->\n<p><strong>AREOS</strong> provides automated crawler policy verification and knowledge graph linkage...</p>",  # noqa: E501
    "ANSWER_NOT_FACTUALLY_SPECIFIC": "<!-- Replace generalities ('many features', 'faster') with concrete metrics -->\n<p>Evaluates 131 scientific search engineering claims across 6 automated diagnostic layers in under 3.5 seconds.</p>",  # noqa: E501
    "NO_LIST_OR_TABLE": "<!-- Add scannable HTML itemization -->\n<ul>\n  <li><strong>AI Crawler Compliance:</strong> Direct verification of robots.txt and llms.txt.</li>\n  <li><strong>Schema Honesty:</strong> 1-to-1 visible text mirroring in JSON-LD.</li>\n</ul>",  # noqa: E501
    "AUTHORITY_DR_LOW": "/* Action Item: Targeted Technical PR */\nAcquire contextual mentions and high-authority referring domain backlinks (>DR 50) to build consensus in algorithmic entity evaluation.",  # noqa: E501
    "REFERRING_DOMAINS_CRITICAL": "/* Action Item: Entity Backlink Expansion */\nExpand independent referring domain count above the minimum threshold of 50 via industry case studies and verifiable open data contributions.",  # noqa: E501
    "WIKIPEDIA_ENTITY_MISSING": "/* Action Item: Wikidata & Open Data Entry */\nEstablish an objective, neutrally cited Wikidata item representing the organization, linking official social and documentation profiles via sameAs attributes.",  # noqa: E501
    "BRAND_MENTIONS_STAGNANT": "/* Action Item: Digital PR Velocity Campaign */\nExecute digital PR outreach to generate fresh unlinked and linked news citations in industry trade publications within the current 90-day indexing window.",  # noqa: E501
    # ── Phase 2-6 additions (T-304) ──────────────────────────────────────
    "SCHEMA_MISSING": '<!-- Add foundational JSON-LD block -->\n<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "Your Brand"\n}\n</script>',  # noqa: E501
    "SCHEMA_UNVERIFIABLE": "/* Ensure the page returns HTTP 200 and does not block the auditor's IP. */",  # noqa: E501
    "ROBOTS_UNVERIFIABLE": "/* Ensure /robots.txt is accessible and returns HTTP 200. */",  # noqa: E501
    "LLMS_UNVERIFIABLE": "/* Ensure /llms.txt is accessible if present. */",  # noqa: E501
    "CONTENT_STALE": '<!-- Update schema dates -->\n"dateModified": "2026-08-31T12:00:00Z"',  # noqa: E501
    "CONTENT_AGING": '<!-- Update schema dates -->\n"dateModified": "2026-08-31T12:00:00Z"',  # noqa: E501
    "DATE_MISSING": '<!-- Add date to schema -->\n"datePublished": "2026-08-01"',  # noqa: E501
    "REDIRECT_CHAIN_LONG": "/* Update internal links to point directly to the final destination URL. */",  # noqa: E501
    "REDIRECT_CHAIN_EXCESSIVE": "/* Eliminate unnecessary redirects — serve content at the canonical URL. */",  # noqa: E501
    "REDIRECT_DOMAIN_CHANGE": "/* Ensure canonical domain is consistent across redirects. */",  # noqa: E501
    "CANONICAL_MISMATCH": '<link rel="canonical" href="https://domain.com/exact-page" />',  # noqa: E501
    "CANONICAL_MISSING": '<link rel="canonical" href="https://domain.com/exact-page" />',  # noqa: E501
    "META_NOINDEX": '<!-- Remove noindex tag if page should be cited -->\n<meta name="robots" content="index, follow">',  # noqa: E501
    "CLOAKING_DETECTED": "/* Serve identical HTML payloads to GPTBot, Anthropic, and standard browsers. */",  # noqa: E501
    "CLOAKING_SUSPECTED": "/* Verify dynamic content injection does not strip core text for bots. */",  # noqa: E501
    "AI_BOT_BLOCKED_HTTP": "/* Whitelist AI User-Agents in WAF/Cloudflare rules. */",  # noqa: E501
    "SAMEAS_DEAD_LINK": "/* Remove or update broken sameAs URLs in schema. */",  # noqa: E501
    "SAMEAS_MISSING": '"sameAs": ["https://en.wikipedia.org/wiki/Brand"]',  # noqa: E501
    "SAMEAS_INCOMPLETE": '"sameAs": ["https://twitter.com/brand", "https://linkedin.com/company/brand", "https://www.wikidata.org/wiki/Q12345"]',  # noqa: E501
    "WIKIDATA_MISSING": '"sameAs": ["https://www.wikidata.org/wiki/Q123456"]',  # noqa: E501
    "ENTITY_NAME_MISSING": '/* Add required name field to Organization/LocalBusiness schema. */\n"name": "Your Brand Name"',  # noqa: E501
    "IFRAME_HEAVY": "/* Extract critical iframe text into native HTML elements. */",  # noqa: E501
    "IMAGES_MISSING_ALT": '<img src="logo.png" alt="Descriptive text for the image" />',  # noqa: E501
    "ALL_CONTENT_IN_MEDIA": "/* Move core content out of iframes/videos into plain HTML text. */",  # noqa: E501
    "VIDEO_NO_TRANSCRIPT": '<track kind="captions" src="transcript.vtt" srclang="en" />',  # noqa: E501
    "SITEMAP_MISSING": "/* Generate and host an XML sitemap at /sitemap.xml */",  # noqa: E501
    "SITEMAP_EMPTY": "/* Populate sitemap with valid <url> entries. */",  # noqa: E501
    "SITEMAP_NO_LASTMOD": "<lastmod>2026-08-31T12:00:00Z</lastmod>",  # noqa: E501
    "SITEMAP_NOT_IN_ROBOTS": "Sitemap: https://domain.com/sitemap.xml",  # noqa: E501
    "SITEMAP_PAGES_UNREACHABLE": "/* Remove 404/500 URLs from the XML sitemap. */",  # noqa: E501
    "CITATION_RATE_LOW": "/* Increase high-DR referring domains and unambiguous schema density. */",  # noqa: E501
    "SHARE_OF_VOICE_LOW": "/* Restructure content to directly answer intent-based questions better than competitors. */",  # noqa: E501
    "PAGE_FETCH_FAILED": "/* Ensure the target page is accessible and returns HTTP 200. */",  # noqa: E501
    "AUDIT_PHASE_CRASHED": "/* An audit sub-phase encountered an unexpected error during execution. Inspect server logs for details. */",  # noqa: E501
    # ── QA-M-SNIPPETS: 16 missing check codes remediation text (TQ-015 / D-QA-010) ──
    "CITATION_NOT_OBSERVED": "/* Improve on-page answer density and entity authority backlinks to earn direct generative AI citations. */",  # noqa: E501
    "CRAWLER_PARTIAL": "# Ensure robots.txt explicitly allows major AI bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended).",  # noqa: E501
    "EXTRACTABILITY_LOW": "<!-- Structure key brand definitions in clean, concise HTML paragraphs near the top of the page. -->",  # noqa: E501
    "EXTRACTABILITY_MEDIUM": "<!-- Refactor long prose paragraphs into clear sections with H2/H3 subheadings and bullet lists. -->",  # noqa: E501
    "EXTRACTABILITY_NONE": "<!-- Add clear, crawlable body text describing your brand, offerings, and direct answers to key queries. -->",  # noqa: E501
    "GOOGLE_EXTENDED_MISSING": "# Add to robots.txt:\nUser-agent: Google-Extended\nAllow: /",  # noqa: E501
    "GPTBOT_MISSING": "# Add to robots.txt:\nUser-agent: GPTBot\nAllow: /",  # noqa: E501
    "INVALID_CRAWL_DELAY": "# Remove excessive Crawl-delay from robots.txt or set to standard \u22642 seconds for search engines.",  # noqa: E501
    "LLMS_TXT_EMPTY_CONTENT": "# Populate /llms.txt with core site overview, key URLs, and markdown documentation references.",  # noqa: E501
    "LLMS_TXT_MISSING_SECTION": "# Add standard markdown sections in /llms.txt (e.g. ## Core Documentation, ## Features).",  # noqa: E501
    "LLMS_TXT_NO_LINKS": "# Include absolute markdown links to primary documentation pages in /llms.txt.",  # noqa: E501
    "MISSING_RECOMMENDED_FIELD": "/* Add recommended Schema.org properties (e.g. description, sameAs, logo) to enhance entity graph context. */",  # noqa: E501
    "MISSING_TYPE": "/* Specify the @type property (e.g. 'Organization', 'WebSite') in your JSON-LD block. */",  # noqa: E501
    "NOSNIPPET_BLOCKING_AI": "<!-- Remove nosnippet directive if you want AI engines to extract and cite text passages from this page. -->",  # noqa: E501
    "UNKNOWN_FIELD": "/* Validate Schema.org properties against official vocabulary and remove typo or unsupported keys. */",  # noqa: E501
    "UNKNOWN_SCHEMA_TYPE": "/* Use official Schema.org types (e.g. Organization, Product, Article, FAQPage) for structured data. */",  # noqa: E501
    "LLMS_TXT_MISSING_H1": "# Ensure your /llms.txt starts with a top-level '# Project or Organization Name' H1 heading.",  # noqa: E501
    "MULTI_PAGE_SCHEMA_GAPS": "/* Ensure consistent JSON-LD schema deployment across all template types (e.g., Articles, Products). */",  # noqa: E501
    "MULTI_PAGE_THIN_CONTENT": "<!-- Consolidate or expand thin pages to meet extractability thresholds across the site. -->",  # noqa: E501
    "NEAR_DUPLICATE_PAGES": '<!-- Consolidate near-duplicate pages via rel="canonical" or 301 redirects. -->',  # noqa: E501
    "COMPETITOR_SCHEMA_ADVANTAGE": "/* Upgrade schema markup to match or exceed the property density of top-cited competitors. */",  # noqa: E501
    "COMPETITOR_CONTENT_ADVANTAGE": "<!-- Refactor content structure to directly address entity queries better than competitors. -->",  # noqa: E501
    "JS_CRITICAL_CONTENT_GATED": "<!-- Serve critical text content in the initial HTML payload without requiring JS execution. -->",  # noqa: E501
    "CLOAKING_FETCH_FAILED": "/* Verify the page does not conditionally block AI bot IPs or User-Agents during fetch. */",  # noqa: E501
    "PAGE_FETCH_FAILED": "/* Verify target URL returns 200 OK and is accessible to crawler requests. */",  # noqa: E501
    "CITATION_OBSERVED": "// Domain actively cited in AI engine responses. Maintain content freshness and schema precision to preserve citation share.",  # noqa: E501
    "CITATION_WHY_UNKNOWN": "// Citation observed without specific keyword match. Verify brand mentions and unstructured entity references across citation sources.",  # noqa: E501
    "CRAWLER_ALLOWED": "// AI search crawlers explicitly allowed in robots.txt. Continue monitoring robots.txt for inadvertent block directives.",  # noqa: E501
    "NO_DIRECTIVE": "// No explicit AI bot directives found in robots.txt. Standard search crawler permissions apply.",  # noqa: E501
    "EXTRACTABILITY_HIGH": "// Content extraction efficiency is high. Main text, headings, and structure are cleanly extractable by AI scrapers.",  # noqa: E501
    "ANSWER_FORMAT_GOOD": "// Answer formatting conforms to LLM answer box standards. Maintain concise definition paragraphs and list structures.",  # noqa: E501
    "AUTHORITY_PROFILE_GOOD": "// Strong domain authority profile detected with healthy referring domain count and brand presence.",  # noqa: E501
    "SCHEMA_UNVERIFIABLE": "/* Verify schema validity when full page DOM can be rendered. */",  # noqa: E501
    "ROBOTS_UNVERIFIABLE": "# Verify robots.txt accessibility when domain host is online.",  # noqa: E501
    "LLMS_UNVERIFIABLE": "# Verify /llms.txt file presence when domain host is online.",  # noqa: E501
}

# Guided instructions for manual review wizard cards
MANUAL_CARD_GUIDANCE = {
    "C052": {
        "title": "Verify Render Asset Accessibility",
        "what_to_look_for": "Check if critical JavaScript or CSS stylesheets are blocked by robots.txt rules or CDN challenges, causing AI rendering engines to see a blank page.",  # noqa: E501
        "how_to_fill": "Select 'pass' if the rendered HTML contains full body content. Select 'fail' if core content vanishes when JS/CSS is restricted."  # noqa: E501
    },
    "C053": {
        "title": "Evaluate Schema Semantic Honesty",
        "what_to_look_for": "Inspect the JSON-LD blocks and compare them line-by-line with visible page text. AI engines penalize sites where schema claims features, reviews, or ratings not directly visible to human visitors.",  # noqa: E501
        "how_to_fill": "Select 'pass' if schema matches visible text 1-to-1. Select 'warn' or 'fail' if unsupported marketing statements exist in JSON-LD."  # noqa: E501
    },
    "C073": {
        "title": "Causal Attribution for Missing Citations",
        "what_to_look_for": "When a brand is omitted from Perplexity or Gemini summaries, investigate which layer failed: Access (was crawler blocked?), Content (is description vague or buried?), or Authority (competitors have stronger consensus).",  # noqa: E501
        "how_to_fill": "Document the precise root cause layer in your notes and mark 'warn' so the recommendation engine assigns targeted remediation steps."  # noqa: E501
    },
    "C077": {
        "title": "Assess Brand Sentiment & Framing in AI Answers",
        "what_to_look_for": "Analyze the framing of brand citations in generative answers. Are AI engines describing the brand as 'expensive', 'outdated', or secondary to a rival?",  # noqa: E501
        "how_to_fill": "If sentiment is accurate and authoritative, select 'pass'. If generative answers contain negative or diminishing framing, select 'fail' and describe the misaligned topic in notes."  # noqa: E501
    },
    "C082": {
        "title": "Digital-PR / Third-Party Citation Gap",
        "what_to_look_for": "Identify which third-party websites (review platforms, trade media, aggregators) are being cited instead of your brand, and determine what structural or authority elements they provide that your pages lack.",  # noqa: E501
        "how_to_fill": "Select 'pass' if brand dominates third-party citations. Select 'warn' or 'fail' if third parties outrank or omit the brand, and note target PR publications to pitch."  # noqa: E501
    },
    "C090": {
        "title": "Final Root Cause Diagnosis Narrative",
        "what_to_look_for": "Ensure the overall audit report provides a coherent narrative linking technical failures (e.g. low DR or missing llms.txt) to real business outcomes.",  # noqa: E501
        "how_to_fill": "Summarize the overarching technical and authority diagnosis in the notes field and select 'pass' once documented."  # noqa: E501
    },
    "DEFAULT": {
        "title": "Expert Human Inspection Required",
        "what_to_look_for": "Perform expert qualitative verification per the instruction card guidelines, ensuring empirical standards are met before sign-off.",  # noqa: E501
        "how_to_fill": "Record verifiable observational evidence in the notes field and submit your pass/warn/fail evaluation."  # noqa: E501
    }
}


_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

import logging
_orch_logger = logging.getLogger(__name__)


def _fetch_page(clean_domain: str, page_url: str) -> tuple[str, int, str]:
    """Fetch page HTML exactly once and return (html, redirect_hop_count, final_url).

    On any failure (network, timeout, SSRF block), returns ("", 0, page_url)
    so downstream auditors can degrade gracefully.
    """
    try:
        validate_domain_ssrf(clean_domain)
        resp = safe_get(page_url, timeout=4)
        hop_count = len(resp.history) if hasattr(resp, 'history') else 0
        final_url = str(resp.url) if hasattr(resp, 'url') else page_url
        if resp.status_code != 200:
            _orch_logger.debug("_fetch_page got status %d for %s", resp.status_code, page_url)
            return ("", hop_count, final_url)
        return (resp.text, hop_count, final_url)
    except (requests.exceptions.RequestException, ValueError) as e:
        _orch_logger.debug("_fetch_page failed for %s: %s", page_url, e)
        return ("", 0, page_url)


def _extract_json_ld_blocks(html: str) -> list:
    """
    Pull every <script type="application/ld+json"> block out of raw HTML and
    parse each as JSON. Unparseable blocks are passed through as the raw
    string so schema_validator.validate_page_schemas can flag them as
    JSON_PARSE_FAILURE rather than being silently dropped.
    """
    blocks: list = []
    for raw in _JSON_LD_RE.findall(html):
        raw = raw.strip()
        if not raw:
            continue
        try:
            blocks.append(json.loads(raw))
        except (json.JSONDecodeError, ValueError, RecursionError):
            blocks.append(raw)  # kept as str -> validator reports JSON_PARSE_FAILURE
    return blocks


def _validate_schema_from_html(page_html: str, page_url: str) -> tuple[list[dict], list, list[dict]]:
    """Validate JSON-LD blocks from pre-fetched HTML.

    Returns (findings, json_ld_blocks, schema_claims) so the orchestrator
    can pass blocks and claims to downstream consumers without re-parsing.
    """
    from areos.auditors.schema_validator import _extract_schema_claims

    if not page_html:
        return (
            [{"code": ErrorCode.SCHEMA_UNVERIFIABLE, "severity": "info",
              "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.",  # noqa: E501
              "page_url": page_url}],
            [],
            [],
        )

    json_ld_blocks = _extract_json_ld_blocks(page_html)
    if not json_ld_blocks:
        return (
            [{"code": "SCHEMA_MISSING", "severity": "warning",
              "message": "No JSON-LD structured data found on the page.", "page_url": page_url}],
            [],
            [],
        )

    schema_claims = _extract_schema_claims(json_ld_blocks)
    results = validate_page_schemas(json_ld_blocks)
    findings: list[dict] = []
    for result in results:
        if not result.issues:
            findings.append({"code": "ANSWER_FORMAT_GOOD", "severity": "info", "message": f"{result.schema_type} schema block is well-formed.", "page_url": page_url})  # noqa: E501
            continue
        for issue in result.issues:
            findings.append({"code": issue.code, "severity": issue.severity, "message": f"[{result.schema_type}] {issue.message}", "page_url": page_url})  # noqa: E501
    return (findings, json_ld_blocks, schema_claims)



def run_citation_sampling_loop(
    clean_domain: str,
    prompts: list[str],
    client_keys: dict | None = None,
    circuit_breaker: dict[str, int] | None = None,
) -> CitationSampleResult:
    """Execute citation sampling across CITATION_SAMPLE_ENGINES if keys are present."""
    ck = client_keys or {}
    sampled_prompts = prompts[:CITATION_SAMPLE_PROMPT_COUNT]
    results: list[CitationSampleResult] = []

    for engine in CITATION_SAMPLE_ENGINES:
        if engine == "perplexity":
            has_key = bool(ck.get("perplexity") or os.environ.get("PERPLEXITY_API_KEY"))
        elif engine == "gemini":
            has_key = bool(ck.get("google") or ck.get("gemini") or os.environ.get("AREOS_GEMINI_KEY_1"))
        else:
            has_key = False

        if has_key:
            res = sample_citations(
                target_domain=clean_domain,
                prompt_set=sampled_prompts,
                engine=engine,
                n_runs=1,
                delay_seconds=0.0,
                client_keys=ck,
                circuit_breaker=circuit_breaker,
            )
            results.append(res)

    if not results:
        return CitationSampleResult(
            target_domain=clean_domain,
            prompt_set=sampled_prompts,
            engine="none",
            n_runs=0,
            observations=[],
            tos_caveat=TOS_CAVEAT([]),
        )

    engines_run = [r.engine for r in results]
    merged_obs: list[CitationObservation] = []
    run_idx = 0
    for r in results:
        for obs in r.observations:
            obs.run_index = run_idx
            merged_obs.append(obs)
            run_idx += 1

    total_runs = sum(r.n_runs for r in results)
    return CitationSampleResult(
        target_domain=clean_domain,
        prompt_set=sampled_prompts,
        engine=", ".join(engines_run),
        n_runs=total_runs,
        observations=merged_obs,
        tos_caveat=TOS_CAVEAT(engines_run),
    )


def run_orchestrated_audit(
    target_domain: str,
    db_path: Path,
    sample_content: str = "",
    api_provider: str = "auto",
    client_keys: dict | None = None,
    circuit_breaker: dict[str, int] | None = None
) -> dict[str, Any]:
    if circuit_breaker is None:
        circuit_breaker = defaultdict(int)
    def check_cb(provider):
        return circuit_breaker[provider] >= 2

    run_id = f"RUN-{time.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    run_date = time.strftime("%Y-%m-%d %H:%M:%S")
    findings: list[dict[str, Any]] = []
    
    # Clean domain input — strip scheme, path, and whitespace
    clean_domain = target_domain.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()  # noqa: E501
    if not clean_domain:
        raise ValueError(
            "target_domain resolved to an empty string after normalisation. "
            "Provide a valid hostname such as 'example.com'."
        )

    page_url = f"https://{clean_domain}"

    # 1. AI Crawling & Robots Checker
    robots_ok = True
    llms_ok = True
    try:
        validate_domain_ssrf(clean_domain)
        robots_text = _fetch_robots_txt(clean_domain)
        if robots_text:
            res_rob = parse_robots_txt(robots_text)
            for bot, dir_obj in res_rob.directives.items():
                if dir_obj.is_fully_blocked:
                    findings.append({
                        "code": "CRAWLER_FULLY_BLOCKED",
                        "severity": "error",
                        "message": f"AI Crawler {bot} is explicitly denied in robots.txt.",
                        "page_url": f"https://{clean_domain}/robots.txt"
                    })
                    robots_ok = False
        
    
    except Exception as exc:
        logger.warning("Failed to fetch or parse robots.txt for %s: %s", clean_domain, exc, exc_info=True)
        findings.append({
            "code": ErrorCode.ROBOTS_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch or parse robots.txt; crawler access result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url
        })

    try:
        validate_domain_ssrf(clean_domain)
        l_resp = safe_get(f"https://{clean_domain}/llms.txt", timeout=4)
        if l_resp.status_code == 200:
            res_llm = parse_llms_txt(l_resp.text)
            if not res_llm.has_h1:
                findings.append({
                    "code": "LLMS_TXT_MISSING_H1",
                    "severity": "warning",
                    "message": "llms.txt found but missing required # Site Title H1 heading.",
                    "page_url": f"https://{clean_domain}/llms.txt"
                })
        else:
            findings.append({
                "code": "LLMS_TXT_MISSING",
                "severity": "warning",
                "message": "No llms.txt standard file found at root domain.",
                "page_url": page_url
            })
            llms_ok = False
    except Exception as exc:
        logger.warning("Failed to fetch or parse llms.txt for %s: %s", clean_domain, exc, exc_info=True)
        findings.append({
            "code": ErrorCode.LLMS_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch or parse llms.txt; LLM-specific directives result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url
        })
        llms_ok = False

    # ── Single page fetch (T-101/T-103) ──────────────────────────────────────
    page_html, redirect_hop_count, final_url = _fetch_page(clean_domain, page_url)

    # 2. Schema & JSON-LD Structure — uses pre-fetched HTML
    try:
        schema_findings, json_ld_blocks, schema_claims = _validate_schema_from_html(page_html, page_url)
    except Exception as exc:
        logger.warning("Failed to validate schema for %s: %s", clean_domain, exc, exc_info=True)
        schema_findings = [{
            "code": ErrorCode.SCHEMA_UNVERIFIABLE,
            "severity": "info",
            "message": "Could not fetch the page to validate structured data; result is unverifiable, not a failing score.",  # noqa: E501
            "page_url": page_url,
        }]
        json_ld_blocks = []
        schema_claims = []
    findings.extend(schema_findings)

    # 3. AI Extractability & Content Formatting — uses pre-fetched HTML
    if page_html:
        eval_text = sample_content or page_html
        if len(eval_text.split()) < 30:
            findings.append({
                "code": "EXTRACTABILITY_LOW",
                "severity": "warning",
                "message": "Content density is insufficient for high-confidence AI chunking and fact extraction.",  # noqa: E501
                "page_url": page_url
            })
        try:
            fmt_res = audit_page_format(page_url, html=eval_text, client_keys=client_keys)
        except (KeyError, IndexError, TypeError) as e:
            _orch_logger.warning("Content format audit failed for %s: %s", page_url, e)
            fmt_res = None
    else:
        # Empty HTML → skip downstream content auditors, emit unverifiable findings
        findings.append({
            "code": ErrorCode.PAGE_FETCH_FAILED,
            "severity": "info",
            "message": "Could not fetch page HTML; content format analysis is unverifiable.",
            "page_url": page_url
        })
        eval_text = ""
        fmt_res = None

    if fmt_res:
        for iss in fmt_res.issues:
            if iss.code != "ANSWER_FORMAT_GOOD":
                findings.append({
                    "code": iss.code,
                    "severity": iss.severity,
                    "message": iss.message,
                    "page_url": page_url
                })

    # 4. Authority & Backlinks
    auth_res = audit_domain_authority(clean_domain, api_provider=api_provider, client_keys=client_keys)  # noqa: E501
    for iss in auth_res.issues:
        if iss.code != "AUTHORITY_PROFILE_GOOD":
            findings.append({
                "code": iss.code,
                "severity": iss.severity,
                "message": iss.message,
                "page_url": page_url
            })

    # 5. Redirects & Access Audit
    try:
        from areos.auditors.redirect_auditor import audit_redirects_and_access
        redir_res = audit_redirects_and_access(page_url, page_html, redirect_hop_count, final_url)
        for iss in redir_res.issues:
            if iss.code != "ACCESS_OK":
                findings.append({
                    "code": iss.code,
                    "severity": iss.severity,
                    "message": iss.message,
                    "page_url": page_url
                })
    except Exception as e:
        _orch_logger.warning("Redirect audit failed for %s: %s", page_url, e)
        findings.append({
            "code": "AUDIT_PHASE_CRASHED",
            "severity": "error",
            "message": f"Redirect audit phase failed: {e}",
            "page_url": page_url
        })

    # 6. Content Freshness Audit
    if page_html:
        try:
            from areos.auditors.freshness_auditor import audit_freshness
            fresh_res = audit_freshness(page_url, page_html, json_ld_blocks)
            for iss in fresh_res.issues:
                if iss.code != "FRESHNESS_OK":
                    findings.append({
                        "code": iss.code,
                        "severity": iss.severity,
                        "message": iss.message,
                        "page_url": page_url
                    })
        except Exception as e:
            _orch_logger.warning("Freshness audit failed for %s: %s", page_url, e)
            findings.append({
                "code": "AUDIT_PHASE_CRASHED",
                "severity": "error",
                "message": f"Content freshness audit phase failed: {e}",
                "page_url": page_url
            })

    # 7. Entity Verification & sameAs
    if page_html or json_ld_blocks:
        try:
            from areos.auditors.entity_verifier import audit_entities
            ent_res = audit_entities(page_url, page_html, json_ld_blocks)
            for iss in ent_res.issues:
                if iss.code != "ENTITY_OK":
                    findings.append({
                        "code": iss.code,
                        "severity": iss.severity,
                        "message": iss.message,
                        "page_url": page_url
                    })
        except Exception as e:
            _orch_logger.warning("Entity verification failed for %s: %s", page_url, e)
            findings.append({
                "code": "AUDIT_PHASE_CRASHED",
                "severity": "error",
                "message": f"Entity verification audit phase failed: {e}",
                "page_url": page_url
            })

    # 8. Media Blindness Audit
    if page_html:
        try:
            from areos.auditors.media_blindness_auditor import audit_media_blindness
            med_res = audit_media_blindness(page_url, page_html)
            for iss in med_res.issues:
                if iss.code != "MEDIA_OK":
                    findings.append({
                        "code": iss.code,
                        "severity": iss.severity,
                        "message": iss.message,
                        "page_url": page_url
                    })
        except Exception as e:
            _orch_logger.warning("Media blindness audit failed for %s: %s", page_url, e)
            findings.append({
                "code": "AUDIT_PHASE_CRASHED",
                "severity": "error",
                "message": f"Media blindness audit phase failed: {e}",
                "page_url": page_url
            })

    # 9. Cloaking Detection (GPTBot vs Browser UA)
    if page_html:
        try:
            from areos.auditors.cloaking_detector import audit_cloaking
            cloak_res = audit_cloaking(clean_domain, page_url, page_html)
            for iss in cloak_res.issues:
                if iss.code not in ("CLOAKING_OK", "CLOAKING_FETCH_FAILED"):
                    findings.append({
                        "code": iss.code,
                        "severity": iss.severity,
                        "message": iss.message,
                        "page_url": page_url
                    })
        except Exception as e:
            _orch_logger.warning("Cloaking check failed for %s: %s", page_url, e)
            findings.append({
                "code": "AUDIT_PHASE_CRASHED",
                "severity": "error",
                "message": f"Cloaking detection audit phase failed: {e}",
                "page_url": page_url
            })

    # 10. Sitemap Audit & Phase 6 Multi-Page Crawl
    try:
        from areos.auditors.sitemap_auditor import audit_sitemap
        sitemap_res = audit_sitemap(clean_domain, robots_result=res_rob if 'res_rob' in locals() else None)
        for iss in sitemap_res.issues:
            if iss.code != "SITEMAP_OK":
                findings.append({
                    "code": iss.code,
                    "severity": iss.severity,
                    "message": iss.message,
                    "page_url": f"https://{clean_domain}/sitemap.xml"
                })
        if sitemap_res.urls:
            try:
                from areos.auditors.multipage_auditor import audit_multi_page
                multi_res = audit_multi_page(sitemap_res.urls[:10], clean_domain, robots_result=res_rob if 'res_rob' in locals() else None)
                findings.extend(multi_res.as_finding_dicts())
            except Exception as e:
                _orch_logger.warning("Multi-page crawl failed for %s: %s", clean_domain, e)
                findings.append({
                    "code": "AUDIT_PHASE_CRASHED",
                    "severity": "error",
                    "message": f"Multi-page crawl sub-phase failed: {e}",
                    "page_url": f"https://{clean_domain}/sitemap.xml"
                })
    except Exception as e:
        _orch_logger.warning("Sitemap audit failed for %s: %s", clean_domain, e)
        findings.append({
            "code": "AUDIT_PHASE_CRASHED",
            "severity": "error",
            "message": f"Sitemap audit phase failed: {e}",
            "page_url": f"https://{clean_domain}/sitemap.xml"
        })

    # 11. Phase 5: JS Rendering Diff (Optional)
    if page_html:
        try:
            from areos.auditors.rendering_auditor import audit_js_rendering, PLAYWRIGHT_AVAILABLE
            if PLAYWRIGHT_AVAILABLE:
                render_res = audit_js_rendering(page_url, page_html)
                if not render_res.skipped:
                    for iss in render_res.issues:
                        if iss.code != "RENDERING_OK":
                            findings.append({
                                "code": iss.code,
                                "severity": iss.severity,
                                "message": iss.message,
                                "page_url": page_url
                            })
        except Exception as e:
            _orch_logger.warning("Rendering audit failed for %s: %s", page_url, e)
            findings.append({
                "code": "AUDIT_PHASE_CRASHED",
                "severity": "error",
                "message": f"JS Rendering audit phase failed: {e}",
                "page_url": page_url
            })

    # 12. Live AI Citation Sampling & Phase 7 Competitor Analysis
    prompts = load_active_prompt_set(clean_domain, db_path=str(db_path))
    if not prompts:
        prompts = [
            f"What are the best platforms and tools in the {clean_domain} ecosystem?",
            f"Why choose {clean_domain} over competitor alternatives?",
            f"What are the documented specifications and features of {clean_domain}?"
        ]
    
    sample_res = run_citation_sampling_loop(
        clean_domain=clean_domain,
        prompts=prompts,
        client_keys=client_keys,
        circuit_breaker=circuit_breaker,
    )
    citation_obs = sample_res.observations
    cited_runs = sum(1 for obs in citation_obs if len(obs.cited_urls) > 0)
    total_runs = len(citation_obs) if citation_obs else 1
    citation_rate_str = f"{cited_runs}/{total_runs} runs"

    if cited_runs == 0:
        findings.append({
            "code": "CITATION_NOT_OBSERVED",
            "severity": "warning",
            "message": f"Brand domain {clean_domain} was not explicitly cited across generative AI answers ({citation_rate_str}).",  # noqa: E501
            "page_url": page_url
        })
    else:
        findings.append({
            "code": "CITATION_OBSERVED",
            "severity": "info",
            "message": f"Brand domain actively cited in {citation_rate_str} during real-time generative query sampling.",  # noqa: E501
            "page_url": page_url
        })

    # Citation Analytics & Competitor Extraction
    try:
        from areos.auditors.citation_sampler import compute_citation_analytics
        cit_analytics = compute_citation_analytics(sample_res)
        if cit_analytics.get("citation_rate", 0) < 0.2 and citation_obs:
            findings.append({
                "code": "CITATION_RATE_LOW",
                "severity": "warning",
                "message": f"Brand citation rate is low ({cit_analytics.get('citation_rate', 0):.1%}) across sampled prompts.",
                "page_url": page_url
            })
        if cit_analytics.get("share_of_voice", 0) < 0.1 and citation_obs:
            findings.append({
                "code": "SHARE_OF_VOICE_LOW",
                "severity": "warning",
                "message": f"Brand share of voice is low ({cit_analytics.get('share_of_voice', 0):.1%}) compared to cited competitors.",
                "page_url": page_url
            })

        # Phase 7 Competitor analysis
        comp_domains = cit_analytics.get("competitor_domains", [])
        if comp_domains:
            try:
                from areos.auditors.competitor_analyzer import analyze_competitors
                target_types = [claim.get("value") for claim in schema_claims if isinstance(claim, dict) and claim.get("field") == "@type"]
                comp_res = analyze_competitors(comp_domains, clean_domain, target_types)
                findings.extend(comp_res.as_finding_dicts())
            except Exception as e:
                _orch_logger.warning("Competitor analysis failed for %s: %s", clean_domain, e)
                findings.append({
                    "code": "AUDIT_PHASE_CRASHED",
                    "severity": "error",
                    "message": f"Competitor analysis sub-phase failed: {e}",
                    "page_url": page_url
                })
    except Exception as e:
        _orch_logger.warning("Citation analytics failed for %s: %s", clean_domain, e)
        findings.append({
            "code": "AUDIT_PHASE_CRASHED",
            "severity": "error",
            "message": f"Citation analytics sub-phase failed: {e}",
            "page_url": page_url
        })

    # Compute score with the layered model (B+C) — stored in DB so the
    # run record always carries the score even before the return payload.
    _scorecard_pre = compute_layered_score(findings)
    _overall_score_pre = _scorecard_pre.overall_score

    # Save to SQLite Database
    # FIX (Readiness Audit, Major #1): this used to write directly via
    # conn.execute()+conn.commit(), bypassing write_as() and leaving this
    # run's changelog entry with actor=NULL/reason=NULL.
    run_token = secrets.token_urlsafe(24)
    conn = get_connection(db_path)
    with write_as(conn, actor="orchestrator:run_orchestrated_audit", reason=f"Automated audit run for {clean_domain}"):  # noqa: E501
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, overall_score, run_token) VALUES (?,?,?,?,?,?,?,?)",  # noqa: E501
            (
                run_id,
                clean_domain,
                run_date,
                json.dumps(["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"]),
                json.dumps(findings),
                "automated_complete",
                _overall_score_pre,
                run_token,
            )
        )

    # Synthesize Prioritized Plan with Governing Claims
    plan = synthesise(run_id, clean_domain, findings, [], db_path, client_keys=client_keys)
    
    # Lookup detailed governing claim statement and confidence from SQLite
    conn = get_connection(db_path)
    enriched_recs = []
    for step_idx, rec in enumerate(plan.recommendations, 1):
        claim_row = conn.execute("SELECT statement, confidence, source_tier_value, claim_scope FROM claims WHERE claim_id = ?", (rec.claim_id,)).fetchone()  # noqa: E501
        stmt = claim_row[0] if claim_row else "Governing claim statement from search engineering knowledge base."  # noqa: E501
        conf = claim_row[1] if claim_row else "high"
        tier = claim_row[2] if claim_row else "tier-1"
        scope = claim_row[3] if claim_row else "general-knowledge"
        evidence_label = "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence"
        
        snippet = ACTION_SNIPPETS.get(rec.check_code, "/* Consult AREOS implementation guidelines for targeted code deployment */")  # noqa: E501
        
        enriched_recs.append({
            "step_number": step_idx,
            "priority_score": rec.priority or 0,
            "title": sanitize_text(rec.title) or "Untitled Recommendation",
            "description": sanitize_text(rec.description) or "",
            "check_code": rec.check_code or "UNKNOWN",
            "severity": rec.severity or "warning",  # never None — JS calls .toUpperCase()
            "governing_claim_id": rec.claim_id or "",
            "governing_claim_statement": sanitize_text(stmt) or "",
            "confidence": (conf or "high").upper(),
            "source_tier": (tier or "tier-1").upper(),
            "claim_scope": scope or "general-knowledge",
            "evidence_label": evidence_label,
            "action_snippet": snippet
        })

    # Phase 2: LLM Three-Step Synthesis Pipeline
    # NOT run here. The LLM synthesis deliberately runs AFTER the user
    # completes the manual guided review wizard, so that human verdicts
    # are included alongside automated findings. Triggering synthesis
    # here (on automated data alone) produces generic AI narrative with
    # no human signal — exactly the "suspiciously AI generated" report
    # the user complained about.
    #
    # Synthesis is triggered by the UI calling POST /api/v1/audit/runs/{run_id}/synthesize
    # after GuidedReview.finishAndGoToReport().
    llm_synthesis: dict = {
        "llm_synthesis_used": False,
        "reason": "Pending manual review — complete the Guided Wizard to generate the AI synthesis narrative.",
        "pending": True,
    }

    # Select manual review cards
    codes_fired = list({f.get("code") for f in findings if f.get("code")})
    summary = AuditRunSummary(
        target_domain=clean_domain,
        audited_stages=["AP-01", "AP-02", "AP-03", "AP-04", "AP-05", "AP-06"],
        check_codes_fired=codes_fired,
        automated_findings=findings,
        run_date=run_date
    )
    triggered_cards = select_triggered_cards(summary)
    
    wizard_cards = []
    for c in triggered_cards:
        guidance = MANUAL_CARD_GUIDANCE.get(c.card_id, MANUAL_CARD_GUIDANCE["DEFAULT"])
        wizard_cards.append({
            "card_id": c.card_id,
            "check_name": c.check_name,
            "reason": c.reason,
            "title": guidance["title"],
            "what_to_look_for": guidance["what_to_look_for"],
            "how_to_fill": guidance["how_to_fill"]
        })

    # Calculate Executive Scorecard via layered model (Option B + C)
    scorecard_result = compute_layered_score(findings)
    overall_score    = scorecard_result.overall_score
    error_cnt, warn_cnt = count_severity(findings)

    # Normalise authority_metrics so JS never sees None/missing keys
    raw_metrics = getattr(auth_res, "metrics", None) or {}
    safe_metrics = {
        "authority_score": raw_metrics.get("authority_score") or 0,
        "referring_domains": raw_metrics.get("referring_domains") or 0,
        "trust_flow": raw_metrics.get("trust_flow") or 0,
        "citation_flow": raw_metrics.get("citation_flow") or 0,
    }

    return {
        "status": "success",
        "run_id": run_id,
        "run_token": run_token,
        "run_date": run_date,
        "target_domain": clean_domain,
        "executive_scorecard": {
            "overall_score": overall_score,
            "authority_metrics": safe_metrics,
            "crawler_status": "Restricted" if not robots_ok else "Fully Permitted",
            "llms_txt_status": "Missing / Incomplete" if not llms_ok else "Standard Compliant",
            "observed_citation_rate": citation_rate_str or "0%",
            "error_count": error_cnt,
            "warning_count": warn_cnt,
            # Layered sub-scores — new in B+C model
            "sub_scores": {
                k: v.as_dict()
                for k, v in scorecard_result.sub_scores.items()
            },
            "score_breakdown":      scorecard_result._flat_breakdown(),
            "access_gate_applied":  scorecard_result.access_gate_applied,
            "access_gate_cap":      scorecard_result.access_gate_cap,
        },
        "remediation_plan": enriched_recs,
        "llm_synthesis": llm_synthesis or {"llm_synthesis_used": False, "reason": "No synthesis ran"},
        "manual_review_wizard": wizard_cards or [],
        "raw_findings": findings,
        "tos_caveat": sample_res.tos_caveat or ""
    }
