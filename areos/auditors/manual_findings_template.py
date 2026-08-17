# areos/auditors/manual_findings_template.py
#
# Task 5a: Structured Manual Findings Template + Parser
#
# CONTRACT:
#   - Defines the canonical shape for a human auditor's findings for a single audit run.
#   - A YAML template is generated (per run) with one entry per triggered card.
#   - parse_manual_findings() validates and returns typed ManualFinding objects.
#   - Any missing required fields raise ParseError — no silent gaps.
#
# FLOW:
#   1. Auditor opens the generated template.
#   2. Auditor fills in verdict + notes for each card (or uses the Manual Review UI).
#   3. parse_manual_findings() is called by the synthesis engine (Task 5b).

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

VALID_VERDICTS  = {"pass", "warn", "fail", "na"}
VALID_SEVERITIES = {"error", "warning", "info"}


class ParseError(ValueError):
    """Raised when a manual findings file fails validation."""


@dataclass
class ManualFinding:
    card_id:    str
    check_name: str
    verdict:    str        # "pass" | "warn" | "fail" | "na"
    severity:   str        # "error" | "warning" | "info"
    notes:      str
    page_url:   str = ""
    claim_ids:  list[str] = field(default_factory=list)  # wired from CHECK_CODE_TO_CLAIM_IDS

    @property
    def is_actionable(self) -> bool:
        return self.verdict in ("warn", "fail")


# ── Template generator ────────────────────────────────────────────────────────

def generate_template(
    run_id: str,
    target_domain: str,
    triggered_cards: list[dict],
    output_path: Path | None = None,
) -> str:
    """
    Generate a YAML template with one stub entry per triggered card.
    The auditor fills in verdict, severity, notes, and optionally page_url.
    """
    lines = [
        f"# AREOS Manual Findings — {target_domain}",
        f"# Run ID: {run_id}",
        "# Instructions: fill in 'verdict' and 'notes' for each card.",
        "# verdict: one of  pass | warn | fail | na",
        "# severity: one of error | warning | info",
        "",
        f"run_id: \"{run_id}\"",
        f"target_domain: \"{target_domain}\"",
        "findings:",
    ]

    for card in triggered_cards:
        auto_label = "Not Automatable" if card.get("automatability") == "Not" else "Partial"
        lines += [
            "",
            f"  - card_id: \"{card['card_id']}\"",
            f"    check_name: \"{card['check_name']}\"",
            f"    automatability: \"{auto_label}\"",
            f"    triggered_by: \"{card.get('reason', '')}\"",
            "    page_url: \"\"              # optional: specific page URL this finding applies to",
            "    verdict: \"\"               # REQUIRED: pass | warn | fail | na",
            "    severity: \"\"              # REQUIRED: error | warning | info",
            "    notes: |                  # REQUIRED: your notes for this check",
            "      ",
        ]

    content = "\n".join(lines)
    if output_path:
        output_path.write_text(content, encoding="utf-8")
    return content


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_manual_findings(yaml_path: Path) -> tuple[str, str, list[ManualFinding]]:
    """
    Parse a filled-in manual findings YAML file.
    Returns (run_id, target_domain, findings_list).
    Raises ParseError on validation failure.
    """
    try:
        import yaml
    except ImportError as err:
        raise ImportError("PyYAML required: pip install pyyaml") from err

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ParseError("YAML root must be a mapping")

    run_id = data.get("run_id", "").strip()
    target_domain = data.get("target_domain", "").strip()
    raw_findings = data.get("findings", [])

    if not run_id:
        raise ParseError("Missing 'run_id'")
    if not target_domain:
        raise ParseError("Missing 'target_domain'")
    if not isinstance(raw_findings, list):
        raise ParseError("'findings' must be a list")

    findings = []
    for i, entry in enumerate(raw_findings):
        card_id = (entry.get("card_id") or "").strip()
        check_name = (entry.get("check_name") or "").strip()
        verdict = (entry.get("verdict") or "").strip().lower()
        severity = (entry.get("severity") or "").strip().lower()
        notes = (entry.get("notes") or "").strip()
        page_url = (entry.get("page_url") or "").strip()

        if not card_id:
            raise ParseError(f"findings[{i}]: missing 'card_id'")
        if verdict not in VALID_VERDICTS:
            raise ParseError(
                f"findings[{i}] ({card_id}): invalid verdict '{verdict}'. "
                f"Must be one of {VALID_VERDICTS}"
            )
        if severity not in VALID_SEVERITIES:
            raise ParseError(
                f"findings[{i}] ({card_id}): invalid severity '{severity}'. "
                f"Must be one of {VALID_SEVERITIES}"
            )
        if not notes:
            raise ParseError(f"findings[{i}] ({card_id}): 'notes' is required and must not be empty")  # noqa: E501

        findings.append(ManualFinding(
            card_id=card_id,
            check_name=check_name,
            verdict=verdict,
            severity=severity,
            notes=notes,
            page_url=page_url,
            claim_ids=[card_id],  # card_id == claim_id in AREOS
        ))

    return run_id, target_domain, findings


def parse_from_db(run_id: str, db_path: Path) -> tuple[str, str, list[ManualFinding]]:
    """
    Load manual verdicts directly from the SQLite DB (submitted via UI).
    Same return shape as parse_manual_findings().
    """
    from areos.db.connection import get_connection
    conn = get_connection(db_path)
    run_row = conn.execute(
        "SELECT target_domain FROM audit_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not run_row:
        raise ParseError(f"Audit run '{run_id}' not found in database")

    target_domain = run_row["target_domain"]
    rows = conn.execute(
        "SELECT card_id, page_url, verdict, severity, notes FROM manual_verdicts WHERE run_id = ?",
        (run_id,)
    ).fetchall()

    findings = []
    for r in rows:
        v = r["verdict"].strip().lower()
        s = r["severity"].strip().lower()
        if v not in VALID_VERDICTS:
            v = "na"
        if s not in VALID_SEVERITIES:
            s = "info"
        findings.append(ManualFinding(
            card_id=r["card_id"],
            check_name=r["card_id"],  # name not stored in DB; card_id is sufficient for synthesis
            verdict=v,
            severity=s,
            notes=r["notes"] or "",
            page_url=r["page_url"] or "",
            claim_ids=[r["card_id"]],
        ))

    return run_id, target_domain, findings
