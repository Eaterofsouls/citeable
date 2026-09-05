# areos/auditors/redirect_auditor.py
#
# Task T-202: Redirect & Access Auditor
#
# CONTRACT:
#   - Audits redirect chains, canonical tags, and noindex access controls.
#   - Evaluates hop count thresholds (long vs excessive).
#   - Detects cross-domain redirects and canonical mismatches.
#   - Returns structured, deterministic results — no network requests.

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Optional
import urllib.parse


# ── Data structures ──────────────────────────────────────────────────────────


@dataclass
class RedirectIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class RedirectAuditResult:
    url: str
    issues: list[RedirectIssue] = field(default_factory=list)
    hop_count: int = 0
    final_url: str = ""
    passed: bool = True

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
                "final_url": self.final_url,
                "hop_count": self.hop_count,
                "check_type": "redirect_access",
            }
            for issue in self.issues
        ]


# ── Internal parsing helpers ────────────────────────────────────────────────


def _has_meta_noindex(html: str) -> bool:
    """Check if HTML contains a meta robots noindex directive."""
    if not html:
        return False
    meta_tags = re.findall(r"<meta\b[^>]*>", html, flags=re.IGNORECASE)
    for tag in meta_tags:
        name_match = re.search(
            r'\bname\s*=\s*["\']?(robots|googlebot|bingbot|slurp|msnbot|teoma)["\']?',
            tag,
            flags=re.IGNORECASE,
        )
        if name_match:
            content_match = re.search(
                r'\bcontent\s*=\s*["\']([^"\']*)["\']',
                tag,
                flags=re.IGNORECASE,
            )
            if not content_match:
                content_match = re.search(
                    r'\bcontent\s*=\s*([^\s>]+)',
                    tag,
                    flags=re.IGNORECASE,
                )
            if content_match:
                directives = [
                    d.strip().lower()
                    for d in content_match.group(1).split(",")
                ]
                if any("noindex" in d or "none" in d for d in directives):
                    return True
    return False


def _extract_canonical_href(html: str) -> Optional[str]:
    """Extract canonical link href from HTML head/body."""
    if not html:
        return None
    link_tags = re.findall(r"<link\b[^>]*>", html, flags=re.IGNORECASE)
    for tag in link_tags:
        rel_match = re.search(r'\brel\s*=\s*["\']?canonical["\']?', tag, flags=re.IGNORECASE)
        if rel_match:
            href_match = re.search(r'\bhref\s*=\s*["\']([^"\']*)["\']', tag, flags=re.IGNORECASE)
            if not href_match:
                href_match = re.search(r'\bhref\s*=\s*([^\s>]+)', tag, flags=re.IGNORECASE)
            if href_match:
                return href_match.group(1).strip()
    return None


def _normalize_for_comparison(url_str: str) -> str:
    """Normalize a URL string for equality comparison."""
    parsed = urllib.parse.urlparse(url_str)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{netloc}{path}{query}"


# ── Public API ───────────────────────────────────────────────────────────────


def audit_redirects_and_access(
    page_url: str,
    html: str = "",
    hop_count: int = 0,
    final_url: str = "",
) -> RedirectAuditResult:
    """
    Audit redirect chains, domain changes, canonical tags, and noindex directives.

    Parameters
    ----------
    page_url : str
        The initial request URL.
    html : str
        The raw HTML content of the target page.
    hop_count : int
        The number of redirect hops encountered to reach the destination.
    final_url : str
        The destination URL after following all redirects.

    Returns
    -------
    RedirectAuditResult
        Structured audit result containing detected issues, hop count, and final URL.
    """
    issues: list[RedirectIssue] = []
    effective_final_url = final_url if final_url else page_url

    # 1. Check hop_count thresholds
    if hop_count > 5:
        issues.append(
            RedirectIssue(
                severity="error",
                code="REDIRECT_CHAIN_EXCESSIVE",
                message=f"Excessive redirect chain detected ({hop_count} hops, exceeds limit of 5)",
            )
        )
    elif hop_count > 2:
        issues.append(
            RedirectIssue(
                severity="warning",
                code="REDIRECT_CHAIN_LONG",
                message=f"Long redirect chain detected ({hop_count} hops, threshold > 2)",
            )
        )

    # 2. Compare domains of page_url vs final_url
    page_parsed = urllib.parse.urlparse(page_url)
    final_parsed = urllib.parse.urlparse(effective_final_url)
    page_domain = (page_parsed.netloc or "").lower()
    final_domain = (final_parsed.netloc or "").lower()

    if page_domain and final_domain and page_domain != final_domain:
        issues.append(
            RedirectIssue(
                severity="warning",
                code="REDIRECT_DOMAIN_CHANGE",
                message=f"Redirect changed domain from '{page_domain}' to '{final_domain}'",
            )
        )

    # 3. Parse HTML for meta robots noindex
    if _has_meta_noindex(html):
        issues.append(
            RedirectIssue(
                severity="error",
                code="META_NOINDEX",
                message="Page contains meta robots noindex directive blocking search indexing",
            )
        )

    # 4. Parse HTML for canonical link and compare to final_url
    canonical_href = _extract_canonical_href(html)
    if canonical_href:
        resolved_canonical = urllib.parse.urljoin(effective_final_url, canonical_href)
        if _normalize_for_comparison(resolved_canonical) != _normalize_for_comparison(effective_final_url):
            issues.append(
                RedirectIssue(
                    severity="warning",
                    code="CANONICAL_MISMATCH",
                    message=(
                        f"Canonical URL '{canonical_href}' does not match final target URL "
                        f"'{effective_final_url}'"
                    ),
                )
            )

    # 5. If no issues found, emit ACCESS_OK
    if not issues:
        issues.append(
            RedirectIssue(
                severity="info",
                code="ACCESS_OK",
                message="No redirect chain, domain change, canonical mismatch, or noindex issues detected",
            )
        )

    passed = not any(i.severity == "error" for i in issues)

    return RedirectAuditResult(
        url=page_url,
        issues=issues,
        hop_count=hop_count,
        final_url=effective_final_url,
        passed=passed,
    )


def format_redirect_report(result: RedirectAuditResult) -> str:
    """Format a human-readable text report from a RedirectAuditResult."""
    lines = [
        f"Redirect & Access Report for: {result.url}",
        "=" * 60,
        f"Hops: {result.hop_count} | Final URL: {result.final_url} | Passed: {'Yes' if result.passed else 'No'}",
        f"Issues ({len(result.issues)} total: {result.error_count} errors, {result.warning_count} warnings):\n",
    ]
    icon_map = {"error": "✗", "warning": "⚠", "info": "ℹ"}
    for issue in result.issues:
        icon = icon_map.get(issue.severity, "?")
        lines.append(f"  {icon} [{issue.code}] {issue.message}")
    return "\n".join(lines)
