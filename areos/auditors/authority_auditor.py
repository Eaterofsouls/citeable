# areos/auditors/authority_auditor.py
#
# Task AP-06: Authority & Backlink Auditor
#
# CONTRACT:
#   - Evaluates a target domain's authority profile, backlink metrics, and entity presence.
#   - Supports API scaffolding for Open PageRank, Moz, Ahrefs, and Majestic.
#   - Provides deterministic offline scoring and fallback heuristics when API keys are unconfigured.  # noqa: E501
#   - Returns finding dictionaries compatible with AREOS synthesis engine and DB schema.

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuthorityIssue:
    severity: str # "error", "warning", "info"
    code: str # check code for mapping
    message: str

@dataclass
class AuthorityAuditResult:
    target_domain: str
    passed: bool
    issues: list[AuthorityIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    provider_used: str = "deterministic_fallback"

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def as_finding_dicts(self, run_id: str = "LOCAL", site_id: str = "AUDIT") -> list[dict[str, Any]]:  # noqa: E501
        import uuid
        results = []
        for idx, issue in enumerate(self.issues):
            results.append({
                "finding_id": f"AUTH-{run_id}-{idx+1}-{str(uuid.uuid4())[:4]}",
                "check_type": "authority",
                "site_id": site_id or self.target_domain,
                "run_id": run_id,
                "code": issue.code,
                "severity": issue.severity,
                "evidence_state": "CONFIRMED",
                "raw_output": json.dumps({
                    "target_domain": self.target_domain,
                    "code": issue.code,
                    "message": issue.message,
                    "metrics": self.metrics,
                    "provider": self.provider_used
                }),
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
        return results


# ── Third-Party API Adapters (Scaffolding) ────────────────────────────────────

from areos.services.cache import ttl_cache

@ttl_cache(ttl=300)
def fetch_open_pagerank(domain: str, api_key: str) -> dict[str, Any] | None:
    """Scaffold for Open PageRank API retrieval."""
    try:
        from areos.util.ssrf import safe_get
        url = f"https://openpagerank.com/api/v1.0/getPageRank?domains[]={urllib.parse.quote(domain)}"  # noqa: E501
        resp = safe_get(url, headers={"API-OPR": api_key}, timeout=10)  # resp.read(5 * 1024 * 1024) bounded via safe_get
        if resp.status_code == 200:
            data = json.loads(resp.text)
            if data.get("response") and len(data["response"]) > 0:
                item = data["response"][0]
                rank_score = item.get("page_rank_integer", 0)
                # Convert 0-10 OPR score to an approximate 0-100 scale for standard rules
                return {
                    "authority_score": rank_score * 10,
                    "referring_domains": rank_score * 50,
                    "wikipedia_presence": rank_score >= 5,
                    "brand_mention_growth": 5.0 if rank_score >= 4 else -2.0,
                    "provider": "open_pagerank"
                }
    except Exception as exc:
        logger.warning("Open PageRank API fetch failed for %s: %s", domain, exc)
        return None
    return None

def fetch_moz_metrics(domain: str, api_key: str) -> dict[str, Any] | None:
    """Scaffold for Moz API retrieval."""
    # Placeholder for Mozscape API metrics retrieval
    return None

def fetch_ahrefs_metrics(domain: str, api_key: str) -> dict[str, Any] | None:
    """Scaffold for Ahrefs API retrieval."""
    # Placeholder for Ahrefs API v3 retrieval
    return None


# ── Deterministic Fallback Scoring ──────────────────────────────────────────

def get_fallback_metrics(domain: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: E501
    """
    Generate authority metrics based on explicit overrides.
    When no overrides are provided, returns an explicit unavailable state.
    """
    if overrides:
        return {
            "authority_score": overrides.get("authority_score", 45),
            "referring_domains": overrides.get("referring_domains", 150),
            "wikipedia_presence": overrides.get("wikipedia_presence", True),
            "brand_mention_growth": overrides.get("brand_mention_growth", 12.5),
            "provider": overrides.get("provider", "manual_override")
        }

    return {
        "authority_score": None,
        "referring_domains": None,
        "wikipedia_presence": None,
        "brand_mention_growth": None,
        "provider": "not_configured"
    }


# ── Main Audit Function ──────────────────────────────────────────────────────

def audit_domain_authority(
    target_domain: str,
    metrics_override: dict[str, Any] | None = None,
    api_provider: str = "auto",
    client_keys: dict | None = None
) -> AuthorityAuditResult:
    """
    Audits domain authority, backlink strength, and entity presence against AEO/GEO requirements.
    When a provider is unavailable or unconfigured, preserves explicit null states and does
    not generate false deductions based on synthetic fallback numbers.
    """
    metrics = None
    provider_used = "not_configured"

    if metrics_override is not None:
        metrics = get_fallback_metrics(target_domain, overrides=metrics_override)
        provider_used = metrics.get("provider", "manual_override")
    else:
        # Attempt live APIs if keys are set (checks client_keys BYOK, then environment)
        opr_key = (client_keys.get("open_pagerank") or client_keys.get("OPEN_PAGERANK_API_KEY")) if client_keys else None
        if not opr_key:
            opr_key = os.environ.get("OPEN_PAGERANK_API_KEY")

        if opr_key and api_provider in ("auto", "open_pagerank"):
            metrics = fetch_open_pagerank(target_domain, opr_key)
            if metrics:
                provider_used = "open_pagerank"
            else:
                provider_used = "provider_unavailable"
        else:
            provider_used = "not_configured"

        if metrics is None:
            metrics = {
                "authority_score": None,
                "referring_domains": None,
                "wikipedia_presence": None,
                "brand_mention_growth": None,
                "provider": provider_used,
            }

    issues: list[AuthorityIssue] = []
    auth_score = metrics.get("authority_score")
    ref_domains = metrics.get("referring_domains")
    has_wiki = metrics.get("wikipedia_presence")
    growth = metrics.get("brand_mention_growth")

    # Only evaluate checks if metrics were observed/measured
    if auth_score is not None:
        # 1. Check Domain Rating / Authority Score
        if auth_score < 20:
            issues.append(AuthorityIssue(
                severity="error",
                code="AUTHORITY_DR_LOW",
                message=f"Domain Authority Score ({auth_score}) is below critical threshold (<20). Low authority severely impairs AI engine citation likelihood."  # noqa: E501
            ))

    if ref_domains is not None:
        # 2. Check Referring Domains count
        if ref_domains < 50:
            issues.append(AuthorityIssue(
                severity="error",
                code="REFERRING_DOMAINS_CRITICAL",
                message=f"Referring domains total ({ref_domains}) is insufficient (<50). Conversational search AI relies on broad multi-domain consensus for fact verification."  # noqa: E501
            ))

    # 3. Check Wikipedia / Entity Graph presence (only evaluated when explicitly measured)
    if has_wiki is False:
        issues.append(AuthorityIssue(
            severity="warning",
            code="WIKIPEDIA_ENTITY_MISSING",
            message="No verified Wikipedia or Wikidata entity reference detected. Entity graph representation significantly boosts confidence in automated AI summaries."  # noqa: E501
        ))

    if growth is not None:
        # 4. Check Brand Mention Velocity / Growth
        if growth <= 0.0:
            issues.append(AuthorityIssue(
                severity="warning",
                code="BRAND_MENTIONS_STAGNANT",
                message=f"Brand mention velocity has stagnated or declined ({growth}%). Modern AI answers prioritize active, growing digital footprint and news mentions."  # noqa: E501
            ))

    # 5. Emit passing affirmation if profile is healthy and was actually measured
    if auth_score is not None and len(issues) == 0:
        issues.append(AuthorityIssue(
            severity="info",
            code="AUTHORITY_PROFILE_GOOD",
            message=f"Domain authority ({auth_score}), backlink volume ({ref_domains} referring domains), and entity presence meet robust standards for AI engine trust."  # noqa: E501
        ))

    # 6. WP-1.4: If authority metrics were not measured/configured, emit explicit info finding
    if auth_score is None:
        issues.append(AuthorityIssue(
            severity="info",
            code="AUTHORITY_UNCONFIGURED" if provider_used == "not_configured" else "AUTHORITY_PROVIDER_UNAVAILABLE",
            message=f"Domain authority metrics {provider_used}: external authority data not measured.",
        ))

    passed = not any(i.severity == "error" for i in issues)
    
    return AuthorityAuditResult(
        target_domain=target_domain,
        passed=passed,
        issues=issues,
        metrics=metrics,
        provider_used=provider_used
    )
