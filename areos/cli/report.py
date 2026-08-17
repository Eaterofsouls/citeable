# areos/cli/report.py
#
# Task 4b: Manual Gap Report Generator
#
# CONTRACT:
#   - Takes the structured output of a completed automated audit run.
#   - Identifies which pipeline stages were covered.
#   - Matches each Partial/Not-automatable item from the checklist against the
#     stages that were audited.
#   - Outputs a markdown "Manual Action Required" report with links to the
#     appropriate instruction cards.
#
# OUTPUT FORMAT:
#   A markdown document with:
#   1. Executive summary (automated coverage + manual gaps)
#   2. Automated Findings section (wired to claims)
#   3. Manual Action Required section (one section per instruction card triggered)
#   4. Prioritized action list

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Optional
import json
import sys

# ── Instruction card registry ────────────────────────────────────────────────
# Maps card_id to its filename and key metadata.
# A card is "triggered" if the audited stages overlap with the card's stage.

INSTRUCTION_CARDS = [
    {
        "card_id": "C052", "filename": "C052_js_asset_blocking.md",
        "stage": "STAGE-03", "automatability": "Partial",
        "check_name": "JS/Asset Blocking Materiality",
        "trigger_on_stages": ["STAGE-03"],
        "trigger_on_codes": ["CRAWLER_PARTIAL", "CRAWLER_FULLY_BLOCKED"],
    },
    {
        "card_id": "C053", "filename": "C053_semantic_honesty.md",
        "stage": "STAGE-05", "automatability": "Not",
        "check_name": "Semantic Honesty of Structured Data",
        "trigger_on_stages": ["STAGE-05"],
        "trigger_on_codes": ["MISSING_REQUIRED_FIELD", "UNKNOWN_FIELD", "MISSING_TYPE"],
    },
    {
        "card_id": "C056", "filename": "C056_entity_disambiguation.md",
        "stage": "STAGE-11", "automatability": "Partial",
        "check_name": "Entity Disambiguation",
        "trigger_on_stages": ["STAGE-11"],
        "trigger_on_codes": [],  # always triggered if stage covered
    },
    {
        "card_id": "C058", "filename": "C058_embedded_media_blindness.md",
        "stage": "STAGE-09", "automatability": "Partial",
        "check_name": "Embedded Media Blindness",
        "trigger_on_stages": ["STAGE-09"],
        "trigger_on_codes": ["EXTRACTABILITY_LOW", "EXTRACTABILITY_NONE"],
    },
    {
        "card_id": "C061", "filename": "C061_layout_effectiveness.md",
        "stage": "STAGE-14", "automatability": "Partial",
        "check_name": "Layout Effectiveness for AI Extraction",
        "trigger_on_stages": ["STAGE-14"],
        "trigger_on_codes": ["EXTRACTABILITY_MEDIUM", "EXTRACTABILITY_LOW"],
    },
    {
        "card_id": "C062", "filename": "C062_eeat_trustworthiness.md",
        "stage": "STAGE-09/20", "automatability": "Not",
        "check_name": "E-E-A-T & Trustworthiness Assessment",
        "trigger_on_stages": ["STAGE-09", "STAGE-20"],
        "trigger_on_codes": [],  # always triggered
    },
    {
        "card_id": "C072", "filename": "C072_prompt_set_design.md",
        "stage": "STAGE-22", "automatability": "Not",
        "check_name": "Citation Prompt Set Design",
        "trigger_on_stages": ["STAGE-22"],
        "trigger_on_codes": [],  # always triggered when citations run
    },
    {
        "card_id": "C073", "filename": "C073_causal_attribution.md",
        "stage": "STAGE-22", "automatability": "Not",
        "check_name": "Causal Attribution of Citations",
        "trigger_on_stages": ["STAGE-22"],
        "trigger_on_codes": ["CITATION_NOT_OBSERVED"],
    },
    {
        "card_id": "C074", "filename": "C074_hallucination_factcheck.md",
        "stage": "STAGE-20", "automatability": "Not",
        "check_name": "Hallucination Fact-Checking",
        "trigger_on_stages": ["STAGE-20"],
        "trigger_on_codes": [],  # always triggered
    },
    {
        "card_id": "C077", "filename": "C077_sentiment_framing.md",
        "stage": "STAGE-20/22", "automatability": "Partial",
        "check_name": "Sentiment & Framing Analysis",
        "trigger_on_stages": ["STAGE-20", "STAGE-22"],
        "trigger_on_codes": ["CITATION_OBSERVED"],
    },
    {
        "card_id": "C078", "filename": "C078_zero_click_threat.md",
        "stage": "STAGE-22", "automatability": "Not",
        "check_name": "Zero-Click Threat Assessment",
        "trigger_on_stages": ["STAGE-22"],
        "trigger_on_codes": ["CITATION_OBSERVED"],
    },
    {
        "card_id": "C079", "filename": "C079_speakable_schema.md",
        "stage": "STAGE-21", "automatability": "Partial",
        "check_name": "Speakable Schema / Voice-Answer Readiness",
        "trigger_on_stages": ["STAGE-21"],
        "trigger_on_codes": [],
    },
    {
        "card_id": "C082", "filename": "C082_digital_pr_gap.md",
        "stage": "unmapped", "automatability": "Not",
        "check_name": "Digital-PR / Third-Party Citation Gap",
        "trigger_on_stages": ["STAGE-22"],
        "trigger_on_codes": ["CITATION_NOT_OBSERVED"],
    },
    {
        "card_id": "C090", "filename": "C090_root_cause_diagnosis.md",
        "stage": "unmapped", "automatability": "Not",
        "check_name": "Root Cause Diagnosis",
        "trigger_on_stages": [],  # always triggered at end of any audit
        "trigger_on_codes": [],
        "always_trigger": True,
    },
]


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class AuditRunSummary:
    """Simplified summary of what the automated audit produced."""
    target_domain: str
    audited_stages: list[str]
    check_codes_fired: list[str]
    automated_findings: list[dict]
    citation_results: Optional[dict] = None
    run_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class TriggeredCard:
    card_id: str
    check_name: str
    automatability: str
    filename: str
    reason: str


# ── Card triggering logic ─────────────────────────────────────────────────────

def select_triggered_cards(summary: AuditRunSummary) -> list[TriggeredCard]:
    """
    Determine which instruction cards are triggered by this audit run.
    Returns a list of TriggeredCard objects, sorted Not-automatable first.
    """
    triggered = []
    fired_codes_set = set(summary.check_codes_fired)
    audited_stages_set = set(summary.audited_stages)

    for card in INSTRUCTION_CARDS:
        # Always-trigger cards
        if card.get("always_trigger"):
            triggered.append(TriggeredCard(
                card_id=card["card_id"],
                check_name=card["check_name"],
                automatability=card["automatability"],
                filename=card["filename"],
                reason="Always required at the end of any audit.",
            ))
            continue

        # Stage-based trigger
        stage_match = bool(audited_stages_set & set(card["trigger_on_stages"]))
        # Code-based trigger (more specific)
        code_match = bool(fired_codes_set & set(card["trigger_on_codes"]))

        if stage_match or code_match:
            reasons = []
            if stage_match:
                matched = audited_stages_set & set(card["trigger_on_stages"])
                reasons.append(f"Stage(s) audited: {', '.join(matched)}")
            if code_match:
                matched = fired_codes_set & set(card["trigger_on_codes"])
                reasons.append(f"Check code(s) fired: {', '.join(matched)}")

            triggered.append(TriggeredCard(
                card_id=card["card_id"],
                check_name=card["check_name"],
                automatability=card["automatability"],
                filename=card["filename"],
                reason="; ".join(reasons),
            ))

    # Sort: Not-automatable first, then Partial
    triggered.sort(key=lambda c: (0 if c.automatability == "Not" else 1))
    return triggered


# ── Report generator ──────────────────────────────────────────────────────────

def generate_gap_report(
    summary: AuditRunSummary,
    cards_dir: Path,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate the full Manual Gap Report as a markdown string.
    Optionally writes it to output_path.
    """
    triggered = select_triggered_cards(summary)
    not_auto = [c for c in triggered if c.automatability == "Not"]
    partial = [c for c in triggered if c.automatability == "Partial"]

    lines = [
        f"# AREOS Manual Gap Report",
        f"**Target domain:** {summary.target_domain}",
        f"**Audit date:** {summary.run_date}",
        f"**Stages audited:** {', '.join(summary.audited_stages) if summary.audited_stages else 'None'}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"The automated audit covered **{len(summary.audited_stages)} pipeline stage(s)** and "
        f"fired **{len(summary.check_codes_fired)} check codes**.",
        "",
        f"**{len(triggered)} manual action(s) are required** to complete this audit:",
        f"- {len(not_auto)} task(s) are **Not Automatable** — they require specialist human judgment.",
        f"- {len(partial)} task(s) are **Partially Automatable** — AREOS did the data collection; "
        f"you must apply judgment to interpret it.",
        "",
        "> **IMPORTANT**: This audit is NOT complete until all manual actions below are addressed.",
        "> The automated findings alone are insufficient for a trustworthy final report.",
        "",
        "---",
        "",
        "## Automated Findings Summary",
        "",
    ]

    if summary.automated_findings:
        errors = [f for f in summary.automated_findings if f.get("severity") == "error"]
        warnings = [f for f in summary.automated_findings if f.get("severity") == "warning"]
        lines.append(f"**{len(errors)} error(s), {len(warnings)} warning(s)** from automated checks.")
        lines.append("")
        for finding in summary.automated_findings[:15]:  # cap at 15 for brevity
            icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(finding.get("severity", "info"), "?")
            lines.append(f"- {icon} `[{finding.get('code', '?')}]` {finding.get('message', '')}")
        if len(summary.automated_findings) > 15:
            lines.append(f"- _(and {len(summary.automated_findings) - 15} more — see full findings JSON)_")
    else:
        lines.append("_No automated findings recorded for this run._")

    lines += [
        "",
        "---",
        "",
        "## Manual Action Required",
        "",
        "Complete the following tasks in the order listed. "
        "Not-automatable tasks are listed first as they are the highest-value work.",
        "",
    ]

    # ── Not-automatable section ─────────────────────────────────────────
    if not_auto:
        lines += ["### Not Automatable — Specialist Judgment Required", ""]
        for i, card in enumerate(not_auto, 1):
            card_path = cards_dir / card.filename
            card_link = f"[{card.check_name}]({card_path})" if card_path.exists() else card.check_name
            lines += [
                f"#### {i}. {card_link} `({card.card_id})`",
                f"**Triggered by:** {card.reason}",
                "",
                f"_See instruction card for step-by-step guidance._",
                "",
            ]

    # ── Partially automatable section ────────────────────────────────────
    if partial:
        lines += ["### Partially Automatable — Apply Judgment to Automated Data", ""]
        for i, card in enumerate(partial, 1):
            card_path = cards_dir / card.filename
            card_link = f"[{card.check_name}]({card_path})" if card_path.exists() else card.check_name
            lines += [
                f"#### {i}. {card_link} `({card.card_id})`",
                f"**Triggered by:** {card.reason}",
                "",
                f"_AREOS has collected the data. See instruction card for how to interpret it._",
                "",
            ]

    lines += [
        "---",
        "",
        "## Prioritized Action List",
        "",
        "Complete in this order for maximum impact:",
        "",
    ]

    priority_order = [
        ("C052", "Fix confirmed crawler blocks (robots.txt) — prerequisite for everything else."),
        ("C090", "Perform root cause diagnosis — this synthesizes all other findings into a coherent story."),
        ("C073", "Write causal attribution paragraphs for each not-cited page."),
        ("C062", "Assess E-E-A-T. If it's weak, technical fixes alone will not move the needle."),
        ("C072", "Refine the prompt set before re-running citation sampling."),
        ("C053", "Fix schema semantic honesty issues."),
        ("C056", "Resolve any entity disambiguation problems."),
        ("C074", "Fact-check AI brand descriptions for hallucinations."),
        ("C078", "Assess zero-click risk for high-volume queries."),
        ("C082", "Build PR gap map and plan third-party citation strategy."),
        ("C058", "Fix embedded content that blocks AI text extraction."),
        ("C061", "Restructure poorly laid-out pages for better AI chunking."),
        ("C077", "Review brand framing in AI answers; plan content fixes."),
        ("C079", "Optimise or implement speakable schema if voice is a priority channel."),
    ]

    triggered_ids = {c.card_id for c in triggered}
    count = 1
    for card_id, rationale in priority_order:
        if card_id in triggered_ids:
            lines.append(f"{count}. **{card_id}**: {rationale}")
            count += 1

    lines += [
        "",
        "---",
        "",
        "_Report generated by AREOS — AI Retrieval Engineering & Optimization System_",
        "_All manual tasks are documented in `areos/instruction_cards/`_",
    ]

    report = "\n".join(lines)

    if output_path:
        output_path.write_text(report, encoding="utf-8")

    return report


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    import argparse
    import io
    # Reconfigure stdout to utf-8 so emoji/special chars don't crash on Windows cp1252
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="AREOS Manual Gap Report Generator")
    parser.add_argument("--findings", required=True, help="Path to automated findings JSON file")
    parser.add_argument("--domain", required=True, help="Target domain (e.g. example.com)")
    parser.add_argument("--stages", nargs="+", default=[], help="Pipeline stages audited")
    parser.add_argument("--output", default=None, help="Output markdown file path")
    args = parser.parse_args()

    with open(args.findings, encoding="utf-8") as f:
        findings_data = json.load(f)

    findings_list = findings_data if isinstance(findings_data, list) else findings_data.get("findings", [])
    codes_fired = list({f.get("code") for f in findings_list if f.get("code")})

    summary = AuditRunSummary(
        target_domain=args.domain,
        audited_stages=args.stages,
        check_codes_fired=codes_fired,
        automated_findings=findings_list,
    )

    cards_dir = Path(__file__).resolve().parents[1] / "instruction_cards"
    output_path = Path(args.output) if args.output else None

    report = generate_gap_report(summary, cards_dir, output_path)
    print(report)


if __name__ == "__main__":
    main()

