# areos/auditors/multipage_auditor.py
#
# Phase 6: Limited Multi-Page Crawl (C010 / C041)
#
# Crawls top 10 URLs from sitemap with strict timeouts, checking schema presence,
# content density, duplicate content, and reachability.

from __future__ import annotations

import re
import html
import difflib
import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from urllib.parse import urlparse

from areos.util.ssrf import safe_get, validate_domain_ssrf

logger = logging.getLogger(__name__)


@dataclass
class MultiPageIssue:
    severity: str        # "error" | "warning" | "info"
    code: str            # machine-readable check code
    message: str
    url: str = ""


@dataclass
class MultiPageAuditResult:
    urls_crawled: list[str] = field(default_factory=list)
    issues: list[MultiPageIssue] = field(default_factory=list)
    page_count: int = 0
    duplicate_pairs: list[tuple[str, str, float]] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self) -> list[dict]:
        """Convert issues to finding dictionaries suitable for findings_to_claims wiring."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": issue.url or (self.urls_crawled[0] if self.urls_crawled else ""),
                "check_type": "multipage",
            }
            for issue in self.issues
        ]


def _extract_page_text(html_text: str) -> str:
    if not html_text:
        return ""
    from areos.util.html_cleaner import clean_html_text
    return clean_html_text(html_text, remove_media=True, remove_head=True)


def audit_multi_page(
    urls: list[str],
    clean_domain: str,
    robots_result: Any = None,
    max_pages: int = 10,
    per_page_timeout: int = 4,
) -> MultiPageAuditResult:
    """
    Crawl up to max_pages URLs and perform cross-page consistency, schema gap,
    thin content, and near-duplicate detection.
    """
    crawled_urls: list[str] = []
    issues: list[MultiPageIssue] = []
    duplicate_pairs: list[tuple[str, str, float]] = []

    target_urls = [u for u in urls if clean_domain in u][:max_pages]
    if not target_urls:
        target_urls = urls[:max_pages]

    page_texts: dict[str, str] = {}
    schema_missing_count = 0
    thin_content_count = 0
    unreachable_count = 0

    for url in target_urls:
        parsed = urlparse(url)
        path = parsed.path or "/"

        # Check robots exclusion
        if robots_result and hasattr(robots_result, "effective_policy"):
            policy = robots_result.effective_policy("GPTBot") or robots_result.effective_policy("*")
            if policy and any(path.startswith(dis) for dis in policy.disallowed_paths if dis):
                continue

        try:
            resp = safe_get(url, timeout=per_page_timeout)
            if not resp or resp.status_code >= 400:
                unreachable_count += 1
                continue
            html = resp.text
            crawled_urls.append(url)
        except Exception as e:
            logger.warning("Failed to fetch multi-page URL %s: %s", url, e)
            unreachable_count += 1
            continue

        # Check schema presence
        has_schema = bool(re.search(r'<script[^>]+type=["\']application/ld\+json["\']', html, re.IGNORECASE))
        if not has_schema:
            schema_missing_count += 1

        # Check content density
        text = _extract_page_text(html)
        words = text.split()
        if len(words) < 30:
            thin_content_count += 1

        page_texts[url] = text

    # Deduplication check across crawled pages
    url_list = list(page_texts.keys())
    for i in range(len(url_list)):
        for j in range(i + 1, len(url_list)):
            u1, u2 = url_list[i], url_list[j]
            t1, t2 = page_texts[u1], page_texts[u2]
            if len(t1) > 100 and len(t2) > 100:
                # True sequence similarity ratio
                ratio = difflib.SequenceMatcher(None, t1[:1500], t2[:1500]).ratio()
                if ratio > 0.85:
                    duplicate_pairs.append((u1, u2, ratio))

    # Evaluate aggregate findings
    if unreachable_count > 0:
        issues.append(MultiPageIssue(
            severity="warning",
            code="SITEMAP_PAGES_UNREACHABLE",
            message=f"{unreachable_count} of {len(target_urls)} tested sitemap URLs were unreachable (HTTP error or timeout).",
        ))

    if schema_missing_count > 0 and len(crawled_urls) > 1:
        issues.append(MultiPageIssue(
            severity="warning",
            code="MULTI_PAGE_SCHEMA_GAPS",
            message=f"{schema_missing_count} of {len(crawled_urls)} crawled pages lack JSON-LD structured data.",
        ))

    if thin_content_count > 0:
        issues.append(MultiPageIssue(
            severity="warning",
            code="MULTI_PAGE_THIN_CONTENT",
            message=f"{thin_content_count} of {len(crawled_urls)} crawled pages contain thin content (< 30 words).",
        ))

    if duplicate_pairs:
        issues.append(MultiPageIssue(
            severity="warning",
            code="NEAR_DUPLICATE_PAGES",
            message=f"Detected {len(duplicate_pairs)} pairs of near-duplicate pages (similarity > 85%).",
        ))

    if not any(i.severity in ("error", "warning") for i in issues) and len(crawled_urls) > 0:
        issues.append(MultiPageIssue(
            severity="info",
            code="MULTI_PAGE_OK",
            message=f"Multi-page crawl across {len(crawled_urls)} URLs completed with healthy schema and distinct content.",
        ))

    return MultiPageAuditResult(
        urls_crawled=crawled_urls,
        issues=issues,
        page_count=len(crawled_urls),
        duplicate_pairs=duplicate_pairs,
    )
