# areos/auditors/freshness_auditor.py
#
# Task T-201: Content Freshness Auditor
#
# CONTRACT:
#   - Extracts dateModified and datePublished from JSON-LD blocks.
#   - Scans HTML for <meta property="article:modified_time">, <time datetime="...">, and related date tags.
#   - Evaluates content freshness against age thresholds:
#       >365 days -> CONTENT_STALE (error)
#       >180 days -> CONTENT_AGING (warning)
#       <=180 days -> FRESHNESS_OK (info)
#       No dates  -> DATE_MISSING (warning)
#   - Deterministic offline scoring — mechanical dates only, no LLM, no network requests.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class FreshnessIssue:
    """Represents a specific content freshness finding."""

    severity: str  # "error", "warning", "info"
    code: str  # "CONTENT_STALE", "CONTENT_AGING", "DATE_MISSING", "FRESHNESS_OK"
    message: str


@dataclass
class FreshnessAuditResult:
    """Encapsulates the result of a page freshness audit."""

    url: str
    issues: list[FreshnessIssue] = field(default_factory=list)
    dates_found: list[str] = field(default_factory=list)
    most_recent_date: str | None = None
    age_days: int | None = None

    @property
    def passed(self) -> bool:
        """Returns True if there are no error-level issues."""
        return self.error_count == 0

    @property
    def error_count(self) -> int:
        """Count of error-severity issues."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-severity issues."""
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self) -> list[dict[str, Any]]:
        """Convert issues to finding dictionaries compatible with the AREOS synthesis engine."""
        return [
            {
                "code": issue.code,
                "check_code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "url": self.url,
                "check_type": "freshness",
            }
            for issue in self.issues
        ]


def parse_date_string(raw: str) -> date | None:
    """Parse a date string to a datetime.date object.

    Tries ISO 8601 parsing first, then common date string formats.
    Returns None if parsing fails.
    """
    if not raw or not isinstance(raw, str):
        return None

    cleaned = raw.strip()
    if not cleaned:
        return None

    # Handle standard ISO 8601 strings
    # Normalizing trailing Z to +00:00 for cross-version compatibility
    iso_candidate = cleaned
    if iso_candidate.endswith("Z") or iso_candidate.endswith("z"):
        iso_candidate = iso_candidate[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(iso_candidate)
        return dt.date()
    except (ValueError, TypeError):
        pass

    # Try extracting leading YYYY-MM-DD
    if len(cleaned) >= 10 and cleaned[4] == "-" and cleaned[7] == "-":
        try:
            return date.fromisoformat(cleaned[:10])
        except (ValueError, TypeError):
            pass

    # Common fallback formats
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.date()
        except (ValueError, TypeError):
            continue

    return None


def extract_dates_from_json_ld(json_ld_blocks: list[dict[str, Any]]) -> list[str]:
    """Recursively extract dateModified and datePublished values from JSON-LD blocks."""
    if not json_ld_blocks:
        return []

    dates: list[str] = []
    target_keys = {"datemodified", "datepublished", "datecreated", "uploaddate"}

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and k.lower() in target_keys:
                    if isinstance(v, str) and v.strip():
                        dates.append(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                dates.append(item.strip())
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(json_ld_blocks)
    return dates


def extract_dates_from_html(html: str) -> list[str]:
    """Scan HTML for date metadata tags and <time> elements."""
    if not html:
        return []

    # Cap to 2MB to prevent regex stalling on enormous payloads
    html_scan = html[:2000000]
    dates: list[str] = []

    # 1. <time datetime="...">
    time_matches = re.finditer(
        r'<time[^>]*\bdatetime=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
        html_scan,
        flags=re.IGNORECASE,
    )
    for m in time_matches:
        val = m.group(1) or m.group(2) or m.group(3)
        if val and val.strip():
            dates.append(val.strip())

    # 2. <meta ...> tags
    target_props = {
        "article:modified_time",
        "article:published_time",
        "og:updated_time",
        "last-modified",
        "date",
        "pubdate",
        "datemodified",
        "datepublished",
        "sailthru.date",
        "parsely-pub-date",
    }

    meta_tags = re.findall(r"<meta\b[^>]*>", html_scan, flags=re.IGNORECASE)
    for tag in meta_tags:
        # Extract property / name / itemprop / http-equiv
        name_m = re.search(
            r'\b(?:property|name|itemprop|http-equiv)=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
            tag,
            flags=re.IGNORECASE,
        )
        content_m = re.search(
            r'\bcontent=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
            tag,
            flags=re.IGNORECASE,
        )
        if name_m and content_m:
            prop_name = (name_m.group(1) or name_m.group(2) or name_m.group(3) or "").strip().lower()
            prop_val = (content_m.group(1) or content_m.group(2) or content_m.group(3) or "").strip()
            if prop_name in target_props and prop_val:
                dates.append(prop_val)

    return dates


def audit_freshness(
    page_url: str,
    html: str = "",
    json_ld_blocks: list[dict[str, Any]] | None = None,
    reference_date: date | None = None,
) -> FreshnessAuditResult:
    """Audit content freshness by extracting dates from JSON-LD and HTML markup.

    Args:
        page_url: The URL of the audited page.
        html: Raw HTML content of the page.
        json_ld_blocks: List of JSON-LD dictionary blocks extracted from the page.
        reference_date: Optional reference date for comparison (defaults to date.today()).

    Returns:
        FreshnessAuditResult with discovered dates, most recent date, and issues.
    """
    if json_ld_blocks is None:
        json_ld_blocks = []

    ref_date = reference_date if reference_date is not None else date.today()

    # 1. Extract dates from JSON-LD
    json_ld_dates = extract_dates_from_json_ld(json_ld_blocks)

    # 2. Extract dates from HTML
    html_dates = extract_dates_from_html(html)

    # Deduplicate while preserving order of discovery
    raw_dates = json_ld_dates + html_dates
    seen: set[str] = set()
    dates_found: list[str] = []
    for d in raw_dates:
        if d not in seen:
            seen.add(d)
            dates_found.append(d)

    # Parse discovered dates
    parsed_entries: list[tuple[date, str]] = []
    for d_str in dates_found:
        parsed = parse_date_string(d_str)
        if parsed is not None:
            parsed_entries.append((parsed, d_str))

    issues: list[FreshnessIssue] = []

    # 3. Handle no dates found
    if not parsed_entries:
        issues.append(
            FreshnessIssue(
                severity="warning",
                code="DATE_MISSING",
                message="No dateModified or datePublished found in JSON-LD or HTML markup.",
            )
        )
        return FreshnessAuditResult(
            url=page_url,
            issues=issues,
            dates_found=dates_found,
            most_recent_date=None,
            age_days=None,
        )

    # 4. Find the most recent date
    most_recent_parsed, most_recent_str = max(parsed_entries, key=lambda x: x[0])
    age_days = (ref_date - most_recent_parsed).days

    # 5. Evaluate freshness thresholds
    if age_days > 365:
        issues.append(
            FreshnessIssue(
                severity="error",
                code="CONTENT_STALE",
                message=(
                    f"Content date ({most_recent_str}) is {age_days} days old "
                    f"(exceeds 365-day freshness threshold)."
                ),
            )
        )
    elif age_days > 180:
        issues.append(
            FreshnessIssue(
                severity="warning",
                code="CONTENT_AGING",
                message=(
                    f"Content date ({most_recent_str}) is {age_days} days old "
                    f"(exceeds 180-day freshness threshold)."
                ),
            )
        )
    else:
        issues.append(
            FreshnessIssue(
                severity="info",
                code="FRESHNESS_OK",
                message=(
                    f"Content is fresh ({age_days} days old, most recent date: {most_recent_str})."
                ),
            )
        )

    return FreshnessAuditResult(
        url=page_url,
        issues=issues,
        dates_found=dates_found,
        most_recent_date=most_recent_str,
        age_days=age_days,
    )
