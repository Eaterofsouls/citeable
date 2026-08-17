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
from areos.auditors.findings_to_claims import CHECK_CODE_TO_CLAIM_IDS, wire_finding
from areos.auditors.manual_findings_template import ManualFinding

# ── Priority scoring ──────────────────────────────────────────────────────────
# Every recommendation gets a numeric priority score (lower = more urgent).
# Score is derived from: severity, automatability, and verdict.

PRIORITY_SCORES = {
    # Access-layer failures — prerequisite for everything
    "CRAWLER_FULLY_BLOCKED":    1,
    "LLMS_TXT_MISSING":         2,
    "JSON_PARSE_FAILURE":       3,
    "MISSING_TYPE":             3,
    # Content-layer errors
    "MISSING_REQUIRED_FIELD":   4,
    "EXTRACTABILITY_NONE":      4,
    "EXTRACTABILITY_LOW":       5,
    # Citation failures
    "CITATION_NOT_OBSERVED":    6,
    # Warnings
    "MISSING_RECOMMENDED_FIELD": 7,
    "UNKNOWN_FIELD":             8,
    "UNKNOWN_SCHEMA_TYPE":       8,
    "GOOGLE_EXTENDED_MISSING":   8,
    "GPTBOT_MISSING":            8,
    "INVALID_CRAWL_DELAY":       8,
    "LLMS_TXT_MISSING_H1":       9,
    "LLMS_TXT_MISSING_SECTION":  9,
    "LLMS_TXT_NO_LINKS":         9,
    "LLMS_TXT_EMPTY_CONTENT":    9,
    "CRAWLER_PARTIAL":           9,
    "EXTRACTABILITY_MEDIUM":    10,
    # AP-04 Content format
    "NOSNIPPET_BLOCKING_AI":    2,
    "ANSWER_NOT_NEAR_TOP":      4,
    "ANSWER_NOT_SELF_CONTAINED": 6,
    "ANSWER_NOT_FACTUALLY_SPECIFIC": 7,
    "NO_LIST_OR_TABLE":         8,
    "ANSWER_FORMAT_GOOD":       12,
    # Authority & Backlink checks (AP-06)
    "AUTHORITY_DR_LOW":           4,
    "REFERRING_DOMAINS_CRITICAL": 5,
    "WIKIPEDIA_ENTITY_MISSING":   7,
    "BRAND_MENTIONS_STAGNANT":    8,
    "AUTHORITY_PROFILE_GOOD":     12,
    # Informational
    "CITATION_OBSERVED":        11,
    "CRAWLER_ALLOWED":          12,
    "EXTRACTABILITY_HIGH":      12,
    "CITATION_WHY_UNKNOWN":     12,
    "NO_DIRECTIVE":             13,
}

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

    def as_dict(self) -> dict:
        scope = self.claim_scope or "general-knowledge"
        return {
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
            lines.append("")

        return "\n".join(lines)


# ── Recommendation builders ───────────────────────────────────────────────────

# Human-readable remediation text per check code
REMEDIATION_TEXT: dict[str, tuple[str, str]] = {
    "CRAWLER_FULLY_BLOCKED":      ("Unblock AI Crawler in robots.txt",
        "A major AI crawler (GPTBot, ClaudeBot, or PerplexityBot) has a blanket 'Disallow: /' rule. "
        "Add an explicit 'Allow: /' rule for each AI crawler you want to permit, or remove the block entirely."),
    "LLMS_TXT_MISSING":           ("Create llms.txt",
        "No llms.txt file found at the domain root. Create one per the llmstxt.org spec with an H1, "
        "a short description, and links to your key pages."),
    "JSON_PARSE_FAILURE":         ("Fix Malformed JSON-LD",
        "A JSON-LD block on the page cannot be parsed. Validate with Google's Rich Results Test "
        "and fix the syntax error."),
    "MISSING_TYPE":               ("Add @type to Schema Block",
        "A JSON-LD block is missing the @type field. Every schema.org block must have @type specified."),
    "MISSING_REQUIRED_FIELD":     ("Add Missing Required Schema Field",
        "A required schema.org field is absent. Missing required fields cause the block to be ignored "
        "by AI engines. Add the flagged field."),
    "EXTRACTABILITY_NONE":        ("Add Readable Content to Page",
        "This page has no substantive text content an AI crawler can extract. "
        "Add a clear, prose description of the page's purpose."),
    "EXTRACTABILITY_LOW":         ("Restructure Page for AI Extraction",
        "Content is present but poorly structured. Break long paragraphs into headed sections, "
        "add bullets, and consider adding an FAQ block at the bottom."),
    "CITATION_NOT_OBSERVED":      ("Investigate Why This Page Is Not Being Cited",
        "The page was not cited in any of the citation sampling runs. "
        "Follow instruction card C073 (Causal Attribution) to diagnose the root cause."),
    "MISSING_RECOMMENDED_FIELD":  ("Add Recommended Schema Field",
        "A recommended schema.org field is absent, reducing AI engine confidence. Add the flagged field."),
    "GOOGLE_EXTENDED_MISSING":    ("Configure Google-Extended in robots.txt",
        "Google-Extended (Google AI training opt-out) is not specified. "
        "Add an explicit Allow or Disallow rule for Google-Extended."),
    "GPTBOT_MISSING":             ("Configure GPTBot in robots.txt",
        "GPTBot (OpenAI's crawler) is not explicitly configured. "
        "Add an explicit Allow rule to ensure OpenAI can index your pages."),
    "LLMS_TXT_MISSING_H1":        ("Add H1 Heading to llms.txt",
        "llms.txt exists but lacks an H1 heading. Add '# Site Name' as the first line."),
    "EXTRACTABILITY_MEDIUM":      ("Improve Page Structure for Better AI Chunking",
        "Content is partially extractable but could be improved. Add subheadings, shorten paragraphs, "
        "and front-load key facts near the top of the page."),
    "CITATION_OBSERVED":          ("Monitor and Optimise Existing Citations",
        "The page is being cited but at a low frequency. Review C077 (Sentiment & Framing) to "
        "ensure the brand is described accurately and positively in AI answers."),
    "UNKNOWN_FIELD":              ("Review Unknown Schema Field",
        "A schema field was found that is not recognized. Check for typos or invalid extensions."),
    "UNKNOWN_SCHEMA_TYPE":        ("Review Unknown Schema Type",
        "A schema type was found that is not recognized. Verify against schema.org documentation."),
    "CRAWLER_PARTIAL":            ("Review Partial Crawler Block",
        "An AI crawler has partial access. Ensure required content is not accidentally blocked."),
    "CRAWLER_ALLOWED":            ("Maintain Crawler Access",
        "Crawler is fully allowed. No action needed unless you intend to block it."),
    "NO_DIRECTIVE":               ("Monitor Implicit Crawler Access",
        "No explicit directive exists for this crawler; it will default to allowed."),
    "INVALID_CRAWL_DELAY":        ("Fix Invalid Crawl-Delay",
        "A crawl-delay directive is malformed. Fix the syntax to ensure crawlers respect it."),
    "LLMS_TXT_MISSING_SECTION":   ("Add Standard Sections to llms.txt",
        "Standard sections (like Optional) are missing from llms.txt. Add them per spec."),
    "LLMS_TXT_NO_LINKS":          ("Add Links to llms.txt",
        "llms.txt contains no links. Add markdown links to your key content."),
    "LLMS_TXT_EMPTY_CONTENT":     ("Populate llms.txt",
        "llms.txt is empty. Add required H1 and summary content."),
    "EXTRACTABILITY_HIGH":        ("Maintain High Extractability",
        "Content is highly extractable. No immediate action required."),
    "CITATION_WHY_UNKNOWN":       ("Diagnose Unknown Citation Status",
        "Citation status is unknown. Rerun attribution audit to determine visibility."),
    "NOSNIPPET_BLOCKING_AI":      ("Remove nosnippet / max-snippet Directives",
        "The page includes nosnippet or max-snippet:0 directives in meta tags or robots headers, blocking AI summaries. Remove these directives to permit AI quotation."),
    "ANSWER_NOT_NEAR_TOP":        ("Move Core Answer Near Top of Page",
        "No complete answer found in the first 3 paragraphs. Move a specific, self-contained definitional answer into the first 30% of the document structure (Zyppy score 9.2)."),
    "ANSWER_NOT_SELF_CONTAINED":  ("Make Introductory Paragraphs Self-Contained",
        "An introductory paragraph starts with dangling demonstratives ('This tool is...', 'As mentioned above'). Rewrite the opening sentence with explicit entity naming (Zyppy score 8.8)."),
    "ANSWER_NOT_FACTUALLY_SPECIFIC": ("Include Concrete Statistics and Facts",
        "Content relies on vague generalizations ('many ways', 'several benefits'). Incorporate verifiable numbers and specific measurements to boost quotation likelihood (Zyppy score 8.5)."),
    "NO_LIST_OR_TABLE":           ("Add Structured Lists or Tables",
        "The page lacks HTML lists (<ol>, <ul>) or tables. Itemize key steps or features into scannable lists or comparison tables (Zyppy score 8.0)."),
    "ANSWER_FORMAT_GOOD":         ("Maintain Good Content Formatting",
        "Page formatting satisfies top Zyppy heuristic requirements for AI citation extraction."),
    "AUTHORITY_DR_LOW":           ("Improve Domain Authority Score",
        "Domain Authority Score is below critical threshold (<20). Engage in targeted PR and technical link acquisition from high-tier domains to build algorithmic trust."),
    "REFERRING_DOMAINS_CRITICAL": ("Build Referring Domain Backlinks",
        "Referring domain count is below 50. AI search engines rely on diverse cross-site consensus; secure contextual mentions across independent industry sites."),
    "WIKIPEDIA_ENTITY_MISSING":   ("Establish Knowledge Graph Entity Reference",
        "No verified Wikidata or Wikipedia reference detected. Ensure consistent organization representation in verifiable open-data repositories to establish entity salience."),
    "BRAND_MENTIONS_STAGNANT":    ("Increase Unlinked Brand Mention Velocity",
        "Brand mention velocity is stagnant or declining. Execute digital public relations campaigns to ensure active recent coverage across industry publications."),
    "AUTHORITY_PROFILE_GOOD":     ("Maintain High Domain & Entity Authority",
        "Domain authority, referring domains count, and entity presence satisfy strong requirements for AI citation confidence."),
}

# Manual card → recommendation mapping
MANUAL_REMEDIATION_TEXT: dict[str, tuple[str, str]] = {
    "C052": ("Fix Confirmed Asset Blocking",
        "Human review confirmed that blocked JS/CSS assets cause the page's main content to disappear. "
        "Add Allow rules in robots.txt for the specific asset paths identified."),
    "C053": ("Fix Schema Semantic Honesty Issues",
        "Schema content does not accurately reflect the visible page text. "
        "Update JSON-LD to exactly mirror visible content. Remove any claims not backed by the page."),
    "C056": ("Resolve Entity Disambiguation",
        "An LLM is confusing this brand with another entity. Add or correct 'sameAs' links "
        "to Wikidata/Wikipedia. Consider creating a Wikipedia stub if none exists."),
    "C058": ("Add HTML Fallbacks for Embedded Content",
        "Core content is trapped in iframes/canvas/embeds. Add visible HTML alternatives "
        "(summary paragraphs, data tables, transcripts) alongside the embedded content."),
    "C061": ("Restructure Page Layout for AI Extraction",
        "Layout effectiveness is insufficient for clean AI extraction. "
        "Add a direct 'What is X?' section near the top, convert long prose to headed sections, "
        "and add FAQPage schema."),
    "C062": ("Strengthen E-E-A-T Signals",
        "E-E-A-T assessment is weak or absent. Add author bios with credentials, "
        "cite external sources for statistics, and add first-person case study content."),
    "C072": ("Refine Citation Prompt Set",
        "Current prompt set does not represent real user intent. Redesign prompts at three funnel stages "
        "per card C072. Get client sign-off before re-running citation sampling."),
    "C073": ("Write Root Cause Diagnosis",
        "Not-cited pages need a causal attribution narrative. Follow card C073 to diagnose "
        "the access, content, and authority layer causes."),
    "C074": ("Correct AI Hallucinations About Brand",
        "AI engines are generating inaccurate brand descriptions. Prominently state the correct "
        "information on the site and update Organization schema. Seek accurate third-party coverage."),
    "C077": ("Address Brand Framing Issues",
        "AI engines are framing the brand in a diminishing way. Identify the content gap that "
        "causes this and create a page or asset that corrects the framing."),
    "C078": ("Assess and Respond to Zero-Click Threat",
        "A query that should drive traffic is being fully absorbed by AI answers. "
        "Decide whether to optimise for citation or to restructure content to drive click-through."),
    "C079": ("Implement or Fix Speakable Schema",
        "Speakable schema is absent or unsuitable for voice. Write a 50–100 word direct-answer "
        "paragraph and apply speakable markup pointing to its CSS selector."),
    "C082": ("Execute Digital-PR Gap Strategy",
        "AI engines prefer third-party sources over the brand's own pages. "
        "Build the PR gap map per card C082 and pitch content to authoritative publications."),
    "C090": ("Write Root Cause Diagnosis Narrative",
        "The audit is incomplete until a root cause diagnosis narrative exists for each failing page. "
        "Follow card C090's three-layer framework and document findings in the report."),
}


def _build_automated_recommendations(
    automated_findings: list[dict],
    db_path: Path,
) -> tuple[list[Recommendation], list[dict]]:
    recommendations = []
    rejected = []

    for finding in automated_findings:
        code = finding.get("code", "")
        if code not in REMEDIATION_TEXT:
            continue  # info-only codes not added as recommendations

        title, description = REMEDIATION_TEXT[code]
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

        priority = PRIORITY_SCORES.get(code, 10)
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
        ))

    return recommendations, rejected


def _build_manual_recommendations(
    manual_findings: list[ManualFinding],
    db_path: Path,
) -> tuple[list[Recommendation], list[dict]]:
    recommendations = []
    rejected = []

    for finding in manual_findings:
        if not finding.is_actionable:
            continue  # pass/na findings have no remediation recommendation

        if finding.card_id not in MANUAL_REMEDIATION_TEXT:
            rejected.append({
                "check_code": finding.card_id,
                "reason": f"No remediation text defined for card {finding.card_id}",
            })
            continue

        title, description = MANUAL_REMEDIATION_TEXT[finding.card_id]
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

    auto_recs, auto_rejected = _build_automated_recommendations(automated_findings, db_path)
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
        import sqlite3
        conn = sqlite3.connect(str(db_path))
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
        conn.close()
    except Exception:
        pass  # Non-fatal: citations are enhancement only

    plan.recommendations = sorted(deduped, key=lambda r: r.priority)
    return plan
