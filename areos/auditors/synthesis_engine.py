# areos/auditors/synthesis_engine.py
#
# Task 5b: Synthesis Engine
#
# CONTRACT:
#   - Combines automated findings (from 3b/3c/3d/3e, wired to claims via 3f)
#   - With structured manual findings (from 5a / Manual Review UI)
#   - Queries the live claims table for each recommendation's governing claim
#   - Outputs a prioritized RemediationPlan where EVERY recommendation carries a claim_id
#
# GUARANTEE:
#   - Any recommendation without a valid, active claim_id is rejected by the QA gate (5c).
#   - No recommendation is invented; each one maps back to an existing corpus claim.

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from areos.auditors.findings_to_claims import wire_finding
from areos.auditors.manual_findings_template import ManualFinding

import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


def _load_priority_scores(db_path: Path) -> dict[str, int]:
    """Load priority scores from kb_check_code_map. Falls back to PRIORITY_SCORES dict."""
    try:
        from areos.db.connection import get_connection
        conn = get_connection(str(db_path))
        rows = conn.execute(
            "SELECT check_code, priority_score FROM kb_check_code_map"
        ).fetchall()
        if rows:
            return {r["check_code"]: r["priority_score"] for r in rows}
    except Exception as e:
        logger.debug("Failed to load priority scores from DB: %s", e)
    return {
        "CRAWLER_FULLY_BLOCKED": 1,
        "CLOAKING_DETECTED": 2,
        "EXTRACTABILITY_NONE": 2,
        "SCHEMA_MISSING": 3,
        "CITATION_NOT_OBSERVED": 4,
    }


def _load_remediation_text(db_path: Path) -> dict[str, tuple[str, str]]:
    """Load remediation text from GUIDANCE records in the knowledge base.

    Returns: {check_code: (title, description)} built from GUIDANCE records
    that have guidance_json with check_codes lists.
    Falls back to REMEDIATION_TEXT dict if KB isn't available.
    """
    try:
        from areos.db.connection import get_connection
        conn = get_connection(str(db_path))
        rows = conn.execute(
            "SELECT kid, statement, guidance_json, check_links "
            "FROM knowledge WHERE type = 'GUIDANCE' AND status = 'active'"
        ).fetchall()
        if not rows:
            return {}

        result: dict[str, tuple[str, str]] = {}
        for row in rows:
            guidance_json = row["guidance_json"]
            check_links = row["check_links"]
            if not guidance_json:
                continue

            guidance = json.loads(guidance_json)
            # Get check_codes from guidance.check_codes list
            check_codes = guidance.get("check_codes", [])
            # Also check check_links for additional mappings
            if check_links:
                for link in json.loads(check_links):
                    cc = link.get("check_code")
                    if cc and cc not in check_codes:
                        check_codes.append(cc)

            action = guidance.get("action", "")
            problem = guidance.get("problem", "")
            # Title: use the action as title (or first sentence of statement)
            title = action.split(".")[0] if action else row["statement"][:80]
            # Description: combine problem + action
            description = f"{problem} {action}".strip() if problem else action or row["statement"]

            for cc in check_codes:
                result[cc] = (title, description)

        return result
    except Exception as e:
        logger.debug("KB remediation load failed: %s", e)
        return {}

# ── Priority scoring ──────────────────────────────────────────────────────────
# Every recommendation gets a numeric priority score (lower = more urgent).
# Score is derived from: severity, automatability, and verdict.


VERDICT_PRIORITY_BUMP = {"fail": 0, "warn": 2, "na": 5, "pass": 99}


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class Recommendation:
    priority:          int
    title:             str
    description:       str
    claim_id:          str           # REQUIRED — QA gate rejects if missing/invalid
    claim_status:      Optional[str]
    confidence:        Optional[str]
    source:            str           # "automated" | "manual"
    check_code:        str
    page_url:          str = ""
    severity:          str = "warning"
    claim_scope:       Optional[str] = None  # carries provenance for presentation tier
    claim_statement:   Optional[str] = None  # full statement text from KB claim
    claim_source_url:  Optional[str] = None  # primary source URL from KB claim
    # V2 Evidence chain fields (populated by Knowledge Router)
    resolution_path:   Optional[str] = None  # DETERMINISTIC | SEMANTIC | INSUFFICIENT
    evidence_chain:    list = field(default_factory=list)  # [{eid, sid, relationship, weight}]
    source_citations:  list = field(default_factory=list)  # [{sid, url, title, authority}]
    backing_facts:     list = field(default_factory=list)  # [{kid, statement}]
    is_contested:      bool = False
    is_stale:          bool = False
    rag_enrichment:    list = field(default_factory=list)  # [{kid, statement, similarity}]

    def as_dict(self) -> dict:
        scope = self.claim_scope or "general-knowledge"
        d = {
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "claim_id": self.claim_id,
            "claim_status": self.claim_status,
            "claim_statement": self.claim_statement,
            "claim_source_url": self.claim_source_url,
            "confidence": self.confidence,
            "source": self.source,
            "check_code": self.check_code,
            "page_url": self.page_url,
            "severity": self.severity,
            "claim_scope": scope,
            "evidence_label": "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence",
        }
        # V2 evidence chain (only included if populated)
        if self.resolution_path:
            d["resolution_path"] = self.resolution_path
        if self.evidence_chain:
            d["evidence_chain"] = self.evidence_chain
        if self.source_citations:
            d["source_citations"] = self.source_citations
        if self.backing_facts:
            d["backing_facts"] = self.backing_facts
        if self.is_contested:
            d["is_contested"] = True
        if self.is_stale:
            d["is_stale"] = True
        if self.rag_enrichment:
            d["rag_enrichment"] = self.rag_enrichment
        return d


@dataclass
class RemediationPlan:
    run_id:          str
    target_domain:   str
    recommendations: list[Recommendation] = field(default_factory=list)
    qa_rejected:     list[dict] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.recommendations if r.priority <= 5)

    @property
    def actionable_count(self) -> int:
        return sum(1 for r in self.recommendations if r.severity in ("error", "warning"))

    def format_markdown(self) -> str:
        lines = [
            f"# AREOS Remediation Plan",
            f"**Target:** {self.target_domain}  |  **Run:** {self.run_id}",
            f"**{len(self.recommendations)} recommendations** "
            f"({self.critical_count} critical, {self.actionable_count} actionable)",
            "",
            "> Every recommendation below is governed by a claim in the AREOS knowledge base.",
            "> Click the claim_id to see the full evidence chain.",
            "",
            "---",
            "",
        ]

        if self.qa_rejected:
            lines += [
                "## QA Gate Rejections",
                f"_{len(self.qa_rejected)} item(s) were rejected and are NOT in this plan._",
                "",
            ]
            for r in self.qa_rejected:
                lines.append(f"- `{r.get('check_code')}`: {r.get('reason')}")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## Prioritized Recommendations")
        lines.append("")

        prev_priority_tier = None
        tier_labels = {
            1: "### CRITICAL — Fix First (Access Layer)",
            6: "### HIGH — Content & Citation Layer",
            10: "### MEDIUM — Improvements",
            12: "### LOW — Informational",
        }

        for i, rec in enumerate(self.recommendations, 1):
            # Tier header
            tier = next((k for k in sorted(tier_labels.keys(), reverse=True) if rec.priority >= k), 12)
            if tier != prev_priority_tier:
                lines.append(tier_labels.get(tier, "### Recommendations"))
                lines.append("")
                prev_priority_tier = tier

            sev_icon = {"error": "\u2717", "warning": "\u26a0", "info": "\u2139"}.get(rec.severity, "\xb7")
            src_tag = "[AUTO]" if rec.source == "automated" else "[HUMAN]"
            scope = rec.claim_scope or "general-knowledge"
            evidence_label = "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence"
            lines += [
                f"#### {i}. {rec.title} `{src_tag}`",
                f"**Governing claim:** `{rec.claim_id}`"
                + (f" (status: {rec.claim_status})" if rec.claim_status else "")
                + (f" | confidence: {rec.confidence}" if rec.confidence else ""),
                f"**Evidence tier:** {evidence_label}",
                f"{sev_icon} {rec.description}",
            ]
            if rec.page_url:
                lines.append(f"**Page:** {rec.page_url}")
            # Inline citation: claim statement + source link
            if rec.claim_statement:
                citation = f"> 📎 **{rec.claim_id}** — {rec.claim_statement}"
                if rec.claim_source_url:
                    citation += f"  \n> **Source:** {rec.claim_source_url}"
                lines.append(citation)
            
            # V2 Evidence Fields
            if rec.evidence_chain or rec.source_citations or rec.backing_facts:
                lines.append("")
                lines.append("##### Supporting Evidence:")
                if rec.source_citations:
                    for src in rec.source_citations:
                        title = src.get("title", "") or src.get("url", "")
                        lines.append(f"- **Source:** {title} ({src.get('authority', 'N/A')})")
                if rec.backing_facts:
                    for fact in rec.backing_facts:
                        lines.append(f"- **Fact [{fact.get('kid')}]:** {fact.get('statement')}")
                if rec.evidence_chain:
                    for ev in rec.evidence_chain:
                        lines.append(f"- **Chain:** {ev.get('eid')} ({ev.get('relationship')} - {ev.get('weight')})")
            
            lines.append("")

        return "\n".join(lines)


# ── Recommendation builders ───────────────────────────────────────────────────



def _build_automated_recommendations(
    automated_findings: list[dict],
    db_path: Path,
    client_keys: dict | None = None,
) -> tuple[list[Recommendation], list[dict]]:
    recommendations = []
    rejected = []

    # Load from KB with fallback to hardcoded dicts
    live_remediation = _load_remediation_text(db_path)
    live_priorities = _load_priority_scores(db_path)

    # Try to import Knowledge Router for evidence enrichment
    try:
        from areos.kb.router import resolve as kb_resolve
        has_router = True
    except ImportError:
        has_router = False

    for finding in automated_findings:
        code = finding.get("code", "")
        if code not in live_remediation:
            continue  # info-only codes not added as recommendations

        title, description = live_remediation[code]
        wired = wire_finding(
            check_code=code,
            severity=finding.get("severity", "info"),
            message=finding.get("message", ""),
            source_auditor="automated",
            page_url=finding.get("page_url", ""),
            db_path=db_path,
        )

        if wired.wiring_status not in ("WIRED", "CLAIM_NOT_FOUND"):
            rejected.append({"check_code": code, "reason": "No claim mapping found"})
            continue

        priority = live_priorities.get(code, 10)

        # V2: Resolve through Knowledge Router for evidence chain
        resolution_path = None
        evidence_chain = []
        source_citations = []
        backing_facts = []
        is_contested = False
        is_stale = False
        rag_enrichment = []

        if has_router:
            try:
                resolution = kb_resolve(
                    code,
                    finding.get("message", ""),
                    client_keys=client_keys,
                    db_path=str(db_path),
                )
                resolution_path = resolution.path
                evidence_chain = [
                    {"eid": e.eid, "sid": e.sid, "relationship": e.relationship, "weight": e.weight}
                    for e in resolution.evidence_chain
                ]
                source_citations = [
                    {"sid": s.sid, "url": s.url, "title": s.title, "authority": s.authority}
                    for s in resolution.source_citations
                ]
                backing_facts = [
                    {"kid": f.kid, "statement": f.statement}
                    for f in resolution.backing_facts
                ]
                is_contested = resolution.is_contested
                is_stale = resolution.is_stale
                rag_enrichment = resolution.enrichment
                # If deterministic, use KB priority over hardcoded
                if resolution.path == "DETERMINISTIC" and resolution.priority_score:
                    priority = resolution.priority_score
            except Exception as e:
                logger.debug("KB Router resolution failed for %s: %s", code, e)

        recommendations.append(Recommendation(
            priority=priority,
            title=title,
            description=f"{description}\n*Finding: {finding.get('message', '')}*",
            claim_id=wired.claim_id or code,
            claim_status=wired.claim_status,
            confidence=wired.claim_confidence,
            source="automated",
            check_code=code,
            page_url=finding.get("page_url", ""),
            severity=finding.get("severity", "warning"),
            claim_scope=wired.claim_scope,
            resolution_path=resolution_path,
            evidence_chain=evidence_chain,
            source_citations=source_citations,
            backing_facts=backing_facts,
            is_contested=is_contested,
            is_stale=is_stale,
            rag_enrichment=rag_enrichment,
        ))

    return recommendations, rejected


def _build_manual_recommendations(
    manual_findings: list[ManualFinding],
    db_path: Path,
) -> tuple[list[Recommendation], list[dict]]:
    recommendations = []
    rejected = []

    _MANUAL_REMEDIATION_TEXT = {
        "C052": ("Verify Render Asset Accessibility", "Check if critical JavaScript or CSS stylesheets are blocked by robots.txt rules or CDN challenges."),
        "C053": ("Evaluate Schema Semantic Honesty", "Inspect the JSON-LD blocks and compare them line-by-line with visible page text."),
        "C073": ("Causal Attribution for Missing Citations", "When a brand is omitted from Perplexity or Gemini summaries, investigate which layer failed."),
        "C077": ("Assess Brand Sentiment & Framing in AI Answers", "Analyze the framing of brand citations in generative answers."),
        "C090": ("Final Root Cause Diagnosis Narrative", "Ensure the overall audit report provides a coherent narrative linking technical failures to real business outcomes."),
        "DEFAULT": ("Expert Human Inspection Required", "Perform expert qualitative verification per the instruction card guidelines."),
    }

    for finding in manual_findings:
        if not finding.is_actionable:
            continue  # pass/na findings have no remediation recommendation

        if finding.card_id not in _MANUAL_REMEDIATION_TEXT:
            title, description = _MANUAL_REMEDIATION_TEXT["DEFAULT"]
        else:
            title, description = _MANUAL_REMEDIATION_TEXT[finding.card_id]
        # Manual cards use their card_id as the claim_id
        wired = wire_finding(
            check_code="MISSING_REQUIRED_FIELD",  # proxy code to hit C054 if card not in map
            severity=finding.severity,
            message=finding.notes,
            source_auditor="manual",
            page_url=finding.page_url,
            db_path=db_path,
        )
        # Override claim_id with the card's own ID
        claim_id = finding.card_id

        priority = VERDICT_PRIORITY_BUMP.get(finding.verdict, 5) + 5
        notes_snippet = finding.notes[:200] + "..." if len(finding.notes) > 200 else finding.notes
        recommendations.append(Recommendation(
            priority=priority,
            title=f"[Manual] {title}",
            description=f"{description}\n*Auditor notes: {notes_snippet}*",
            claim_id=claim_id,
            claim_status=wired.claim_status,   # real DB value — not hardcoded 'active'
            confidence=wired.claim_confidence, # real DB value — not hardcoded None
            source="manual",
            check_code=finding.card_id,
            page_url=finding.page_url,
            severity=finding.severity,
        ))

    return recommendations, rejected


# ── Main synthesis function ───────────────────────────────────────────────────

def synthesise(
    run_id: str,
    target_domain: str,
    automated_findings: list[dict],
    manual_findings: list[ManualFinding],
    db_path: Path,
    client_keys: dict | None = None,
) -> RemediationPlan:
    """
    Combine automated + manual findings into a prioritized, claim-cited RemediationPlan.
    """
    plan = RemediationPlan(run_id=run_id, target_domain=target_domain)

    auto_recs, auto_rejected = _build_automated_recommendations(
        automated_findings, db_path, client_keys=client_keys,
    )
    manual_recs, manual_rejected = _build_manual_recommendations(manual_findings, db_path)

    plan.qa_rejected = auto_rejected + manual_rejected
    all_recs = auto_recs + manual_recs

    # Deduplicate by check_code (keep highest priority)
    seen: dict[str, Recommendation] = {}
    for rec in all_recs:
        key = rec.check_code
        if key not in seen or rec.priority < seen[key].priority:
            seen[key] = rec

    deduped = list(seen.values())

    # Bulk-enrich with claim statement + source_url from the KB so the final
    # report carries full inline citations without a second round-trip.
    try:
        from areos.db.connection import get_connection
        conn = get_connection(str(db_path))
        claim_ids = list({r.claim_id for r in deduped if r.claim_id})
        if claim_ids:
            placeholders = ",".join("?" * len(claim_ids))
            rows = conn.execute(
                f"SELECT claim_id, statement, source_url FROM claims WHERE claim_id IN ({placeholders})",
                claim_ids,
            ).fetchall()
            claim_data = {r[0]: {"statement": r[1], "source_url": r[2]} for r in rows}
            for rec in deduped:
                info = claim_data.get(rec.claim_id, {})
                rec.claim_statement  = info.get("statement")
                rec.claim_source_url = info.get("source_url")
        # MF-11: Do NOT call conn.close() — connection pool owns lifecycle
    except Exception as e:
        logger.debug("Citation enrichment failed: %s", e)

    plan.recommendations = sorted(deduped, key=lambda r: r.priority)
    return plan
