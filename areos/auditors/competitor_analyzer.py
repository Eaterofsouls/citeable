# areos/auditors/competitor_analyzer.py
#
# Phase 7: Competitor Extraction & Technical Gap Analysis (C080)
#
# Crawls competitor homepages derived from AI citations and mechanically compares
# schema types and content structures against the target domain.

from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Any

from areos.util.ssrf import safe_get, validate_domain_ssrf

logger = logging.getLogger(__name__)


@dataclass
class CompetitorIssue:
    severity: str        # "error" | "warning" | "info"
    code: str            # machine-readable check code
    message: str
    domain: str = ""


@dataclass
class CompetitorAnalysisResult:
    competitors_analyzed: list[str] = field(default_factory=list)
    issues: list[CompetitorIssue] = field(default_factory=list)
    competitor_stats: dict[str, dict] = field(default_factory=dict)

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
                "competitor_domain": issue.domain,
                "check_type": "competitor_analysis",
            }
            for issue in self.issues
        ]


def _extract_schema_types_from_html(html: str) -> list[str]:
    types: list[str] = []
    if not html:
        return types
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    for block in matches:
        try:
            data = json.loads(block.strip())
            if isinstance(data, dict):
                t = data.get("@type")
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend(str(item) for item in t)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        t = item["@type"]
                        if isinstance(t, str):
                            types.append(t)
                        elif isinstance(t, list):
                            types.extend(str(x) for x in t)
        except Exception:
            continue
    return list(set(types))


def analyze_competitors(
    competitor_domains: list[str],
    target_domain: str,
    target_schema_types: Optional[list[str]] = None,
    max_competitors: int = 3,
    per_domain_timeout: int = 4,
) -> CompetitorAnalysisResult:
    """
    Fetch top competitor homepages and compare schema and content markers.
    """
    target_types = set(target_schema_types or [])
    analyzed: list[str] = []
    issues: list[CompetitorIssue] = []
    stats: dict[str, dict] = {}

    clean_competitors = [
        d.strip().lower() for d in competitor_domains
        if d.strip().lower() and target_domain.lower() not in d.strip().lower()
    ][:max_competitors]

    for comp in clean_competitors:
        url = f"https://{comp}/"
        try:
            resp = safe_get(url, timeout=per_domain_timeout)
            if not resp or resp.status_code >= 400:
                logger.warning("Competitor URL %s returned non-200 status: %s", url, getattr(resp, "status_code", "None"))
                continue
            html = resp.text
            analyzed.append(comp)
        except Exception as e:
            logger.warning("Failed to fetch competitor URL %s: %s", url, e)
            continue

        comp_types = _extract_schema_types_from_html(html)
        has_lists = bool(re.search(r'<[ou]l[^>]*>', html, re.IGNORECASE))
        has_tables = bool(re.search(r'<table[^>]*>', html, re.IGNORECASE))

        stats[comp] = {
            "schema_types": comp_types,
            "has_structured_markup": bool(comp_types),
            "has_lists": has_lists,
            "has_tables": has_tables,
        }

        # Check for schema advantages
        advantage_types = set(comp_types) - target_types
        if advantage_types:
            types_str = ", ".join(sorted(advantage_types)[:3])
            issues.append(CompetitorIssue(
                severity="info",
                code="COMPETITOR_SCHEMA_ADVANTAGE",
                domain=comp,
                message=f"Competitor {comp} implements schema types not found on your site: [{types_str}].",
            ))

        # Check for structured content advantage
        if (has_lists or has_tables) and not target_types:
            issues.append(CompetitorIssue(
                severity="info",
                code="COMPETITOR_CONTENT_ADVANTAGE",
                domain=comp,
                message=f"Competitor {comp} uses structured lists/tables and rich schema to facilitate AI extraction.",
            ))

    if not issues and analyzed:
        issues.append(CompetitorIssue(
            severity="info",
            code="COMPETITOR_ANALYSIS_OK",
            message=f"Analyzed {len(analyzed)} competitor domains — your technical schema coverage is competitive.",
        ))

    return CompetitorAnalysisResult(
        competitors_analyzed=analyzed,
        issues=issues,
        competitor_stats=stats,
    )
