# areos/auditors/sitemap_auditor.py
#
# Task T-206: Sitemap Auditor
#
# CONTRACT:
#   - Audits sitemap.xml presence, robots.txt sitemap directives, XML structure,
#     freshness timestamps (<lastmod>), and URL reachability.
#   - Extracts valid <loc> page URLs for downstream crawl/audit orchestration.
#   - Returns structured, deterministic results.

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Optional
import urllib.parse
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import logging
    logging.critical("defusedxml is missing! Failing loud to prevent XML vulnerabilities.")
    raise ImportError("defusedxml is required for secure XML parsing")

import requests

from areos.util.ssrf import safe_get, validate_domain_ssrf

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class SitemapIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class SitemapAuditResult:
    url: str = ""
    passed: bool = True
    issues: list[SitemapIssue] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    sitemap_url: str = ""

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self, run_id: str = "LOCAL", site_id: str = "AUDIT") -> list[dict[str, Any]]:
        """Convert issues to finding dictionaries suitable for the synthesis engine."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "sitemap_url": self.sitemap_url,
                "check_type": "sitemap",
            }
            for issue in self.issues
        ]


# ── Internal parsing helpers ────────────────────────────────────────────────


def _local_tag(tag: str) -> str:
    """Strip XML namespace prefix from tag name."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _extract_sitemaps_from_robots(robots_result: Any) -> list[str]:
    """Extract sitemap URLs declared in robots.txt or a RobotsResult object."""
    if robots_result is None:
        return []

    sitemaps: list[str] = []

    # If string: check for raw robots.txt or direct URL
    if isinstance(robots_result, str):
        stripped = robots_result.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            sitemaps.append(stripped)
        else:
            for line in stripped.splitlines():
                clean_line = line.strip()
                if clean_line.lower().startswith("sitemap:"):
                    parts = clean_line.split(":", 1)
                    if len(parts) > 1 and parts[1].strip():
                        sitemaps.append(parts[1].strip())
        return sitemaps

    # If dict: check common keys
    if isinstance(robots_result, dict):
        for key in ("sitemaps", "sitemap_urls", "sitemap"):
            val = robots_result.get(key)
            if isinstance(val, list):
                sitemaps.extend(str(item).strip() for item in val if item)
            elif isinstance(val, str) and val.strip():
                sitemaps.append(val.strip())
        if not sitemaps and "raw_text" in robots_result:
            return _extract_sitemaps_from_robots(robots_result["raw_text"])
        return sitemaps

    # If object with attributes (e.g. RobotsResult or custom dataclass)
    for attr in ("sitemaps", "sitemap_urls", "sitemap"):
        if hasattr(robots_result, attr):
            val = getattr(robots_result, attr)
            if isinstance(val, list):
                sitemaps.extend(str(item).strip() for item in val if item)
            elif isinstance(val, str) and val.strip():
                sitemaps.append(val.strip())

    if not sitemaps and hasattr(robots_result, "raw_text"):
        return _extract_sitemaps_from_robots(getattr(robots_result, "raw_text"))

    return sitemaps


def _parse_sitemap_xml(xml_content: str | bytes) -> tuple[list[str], bool]:
    """
    Parse sitemap XML content and extract page URLs along with <lastmod> presence.

    Returns
    -------
    tuple[list[str], bool]
        Extracted list of URLs, and a boolean indicating if at least one <lastmod> was present.
    """
    if isinstance(xml_content, str):
        # Convert to bytes to prevent ElementTree encoding declaration errors
        raw_bytes = xml_content.encode("utf-8")
    else:
        raw_bytes = xml_content

    root = ET.fromstring(raw_bytes)
    urls: list[str] = []
    has_lastmod = False
    max_sitemap_urls = 50000

    # Check for <url> elements (standard sitemap)
    url_elements = [elem for elem in root.iter() if _local_tag(elem.tag).lower() == "url"]
    if url_elements:
        for url_elem in url_elements:
            if len(urls) >= max_sitemap_urls:
                break
            loc_text: Optional[str] = None
            elem_lastmod = False
            for child in url_elem:
                lt = _local_tag(child.tag).lower()
                if lt == "loc" and child.text and child.text.strip():
                    loc_text = child.text.strip()
                elif lt == "lastmod" and child.text and child.text.strip():
                    elem_lastmod = True
            if loc_text:
                urls.append(loc_text)
                if elem_lastmod:
                    has_lastmod = True
        return urls, has_lastmod

    # Check for <sitemap> elements (sitemap index)
    sitemap_elements = [elem for elem in root.iter() if _local_tag(elem.tag).lower() == "sitemap"]
    if sitemap_elements:
        for s_elem in sitemap_elements:
            if len(urls) >= max_sitemap_urls:
                break
            loc_text = None
            elem_lastmod = False
            for child in s_elem:
                lt = _local_tag(child.tag).lower()
                if lt == "loc" and child.text and child.text.strip():
                    loc_text = child.text.strip()
                elif lt == "lastmod" and child.text and child.text.strip():
                    elem_lastmod = True
            if loc_text:
                urls.append(loc_text)
                if elem_lastmod:
                    has_lastmod = True
        return urls, has_lastmod

    # Fallback: check for any direct <loc> elements
    loc_elements = [elem for elem in root.iter() if _local_tag(elem.tag).lower() == "loc"]
    for loc_elem in loc_elements:
        if len(urls) >= max_sitemap_urls:
            break
        if loc_elem.text and loc_elem.text.strip():
            urls.append(loc_elem.text.strip())

    return urls, has_lastmod


def _check_url_reachable(url: str, timeout: float = 2.0) -> bool:
    """Spot-check if a URL is reachable (returns HTTP < 400)."""
    try:
        parsed = urllib.parse.urlsplit(url)
        if not parsed.scheme or not parsed.hostname:
            return False
        resp = safe_get(url, timeout=timeout)
        return resp.status_code < 400
    except Exception:
        return False


# ── Public API ───────────────────────────────────────────────────────────────


def audit_sitemap(
    clean_domain: str,
    robots_result: Any = None,
    spot_check: bool = True,
) -> SitemapAuditResult:
    """
    Audit sitemap presence, XML structure, freshness timestamps, and page reachability.

    Parameters
    ----------
    clean_domain : str
        The target domain hostname (e.g. 'example.com').
    robots_result : Any, optional
        RobotsResult object, dict, or raw robots.txt text containing sitemap directives.
    spot_check : bool, default True
        Whether to spot-check the reachability of the first 5 extracted URLs.

    Returns
    -------
    SitemapAuditResult
        Structured audit result containing detected issues, extracted URLs, and sitemap URL.
    """
    # 1. Clean domain input
    domain = clean_domain.strip().lower()
    if domain.startswith("https://"):
        domain = domain[8:]
    elif domain.startswith("http://"):
        domain = domain[7:]
    domain = domain.split("/")[0].strip()

    if not domain:
        return SitemapAuditResult(
            url=clean_domain,
            passed=False,
            issues=[
                SitemapIssue(
                    severity="warning",
                    code="SITEMAP_MISSING",
                    message="Target domain is empty or invalid; cannot locate sitemap.",
                )
            ],
            urls=[],
            sitemap_url="",
        )

    base_url = f"https://{domain}"
    primary_sitemap_url = f"{base_url}/sitemap.xml"
    robots_sitemaps = _extract_sitemaps_from_robots(robots_result)

    # 2. Fetch sitemap XML (try /sitemap.xml first, then robots.txt candidates)
    sitemap_text: Optional[str] = None
    active_sitemap_url: str = ""

    candidate_urls = [primary_sitemap_url]
    for r_url in robots_sitemaps:
        if r_url not in candidate_urls:
            candidate_urls.append(r_url)

    for target_url in candidate_urls:
        try:
            resp = safe_get(target_url, timeout=4)
            if resp.status_code == 200 and resp.text.strip():
                sitemap_text = resp.text
                active_sitemap_url = target_url
                break
        except Exception as exc:
            logger.debug("Failed fetching sitemap from %s: %s", target_url, exc)
            continue

    if sitemap_text is None:
        return SitemapAuditResult(
            url=base_url,
            passed=False,
            issues=[
                SitemapIssue(
                    severity="warning",
                    code="SITEMAP_MISSING",
                    message=f"No sitemap found at /sitemap.xml or specified in robots.txt for {domain}.",
                )
            ],
            urls=[],
            sitemap_url="",
        )

    # 3. Parse XML
    try:
        urls, has_lastmod = _parse_sitemap_xml(sitemap_text)
    except Exception as exc:
        logger.debug("Failed parsing sitemap XML from %s: %s", active_sitemap_url, exc)
        return SitemapAuditResult(
            url=base_url,
            passed=False,
            issues=[
                SitemapIssue(
                    severity="info",
                    code="SITEMAP_PARSE_ERROR",
                    message=f"Sitemap XML at {active_sitemap_url} could not be parsed: {exc}",
                )
            ],
            urls=[],
            sitemap_url=active_sitemap_url,
        )

    issues: list[SitemapIssue] = []

    # 4. Check if empty
    if not urls:
        issues.append(
            SitemapIssue(
                severity="warning",
                code="SITEMAP_EMPTY",
                message=f"Sitemap found at {active_sitemap_url} but contains no valid URLs.",
            )
        )
    else:
        # 5. Check lastmod presence
        if not has_lastmod:
            issues.append(
                SitemapIssue(
                    severity="warning",
                    code="SITEMAP_NO_LASTMOD",
                    message="Sitemap URLs lack <lastmod> timestamp attributes for freshness tracking.",
                )
            )

        # 6. Check if sitemap was not in robots.txt when robots_result was provided
        if robots_result is not None and not robots_sitemaps:
            issues.append(
                SitemapIssue(
                    severity="warning",
                    code="SITEMAP_NOT_IN_ROBOTS",
                    message="Sitemap is present at /sitemap.xml but not referenced in robots.txt.",
                )
            )

        # 7. Spot-check reachability of first 5 URLs
        if spot_check:
            unreachable: list[str] = []
            for sample_url in urls[:5]:
                if not _check_url_reachable(sample_url, timeout=2.0):
                    unreachable.append(sample_url)

            if unreachable:
                issues.append(
                    SitemapIssue(
                        severity="warning",
                        code="SITEMAP_PAGES_UNREACHABLE",
                        message=(
                            f"{len(unreachable)} of {len(urls[:5])} sampled sitemap URLs "
                            f"returned 4xx/5xx HTTP errors or were unreachable."
                        ),
                    )
                )

        # 8. Emit SITEMAP_OK if no warnings or errors
        if not any(i.severity in ("error", "warning") for i in issues):
            issues.append(
                SitemapIssue(
                    severity="info",
                    code="SITEMAP_OK",
                    message=f"Valid sitemap found at {active_sitemap_url} with {len(urls)} URLs.",
                )
            )

    passed = not any(i.code in ("SITEMAP_MISSING", "SITEMAP_EMPTY") or i.severity == "error" for i in issues)

    return SitemapAuditResult(
        url=base_url,
        passed=passed,
        issues=issues,
        urls=urls,
        sitemap_url=active_sitemap_url,
    )


def format_sitemap_report(result: SitemapAuditResult) -> str:
    """Format a human-readable text report from a SitemapAuditResult."""
    lines = [
        f"Sitemap Audit Report for: {result.url}",
        "=" * 60,
        f"Sitemap URL: {result.sitemap_url or 'None'} | URLs Found: {len(result.urls)} | Passed: {'Yes' if result.passed else 'No'}",
        f"Issues ({len(result.issues)} total: {result.error_count} errors, {result.warning_count} warnings):\n",
    ]
    icon_map = {"error": "✗", "warning": "⚠", "info": "ℹ"}
    for issue in result.issues:
        icon = icon_map.get(issue.severity, "?")
        lines.append(f"  {icon} [{issue.code}] {issue.message}")
    return "\n".join(lines)
