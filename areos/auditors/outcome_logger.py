# areos/auditors/outcome_logger.py
#
# Task 6a: Outcome Logging
#
# CONTRACT:
#   - Logs a post-remediation outcome as a NEW CLAIM in the claims table.
#   - source_tier_value is hardcoded to "outcome-log" (the only legal value for system_native outcomes).
#   - Every outcome must trace back to the run_id that generated the remediation plan.
#   - Outcome claims are real claims: they go through the same changelog + approval workflow.
#   - This closes the knowledge loop: audit → remediation → outcome → new claim → future audits.
#
# OUTCOME CLAIM SHAPE:
#   claim_type  = "outcome"
#   source_tier_vocab = "system_native"
#   source_tier_value = "outcome-log"  (hardcoded — the ONLY legal value per lint.py)
#   status      = "contested"  (pending review — outcomes need time to mature)
#   stage_id    = derived from the check_code that the remediation addressed
#   statement   = structured sentence: "After [fix], [metric] changed from [before] to [after]."

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from areos.db.connection import get_connection
from areos.db.context import write_as
from areos.db.lint import lint_claim
from areos.util.clock import utc_now_iso, utc_today_iso

# Source tier is HARDCODED — this is a policy constraint, not a parameter
_HARDCODED_SOURCE_TIER_VOCAB = "system_native"
_HARDCODED_SOURCE_TIER_VALUE = "outcome-log"  # MUST match lint.py LEGAL_SOURCE_TIER_COMBINATIONS

# Outcome claims start as contested — they need time to mature before being trusted
_INITIAL_STATUS = "contested"


class OutcomeLogError(ValueError):
    """Raised when an outcome log entry is invalid."""


@dataclass
class OutcomeEntry:
    """Structured representation of a post-remediation outcome."""
    run_id:          str
    remediation_id:  str
    fix_description: str
    metric_name:     str
    metric_before:   str
    metric_after:    str
    page_url:        str = ""
    notes:           str = ""

    def validate(self):
        if not self.run_id.strip():
            raise OutcomeLogError("run_id is required")
        if not self.remediation_id.strip():
            raise OutcomeLogError("remediation_id is required")
        if not self.fix_description.strip():
            raise OutcomeLogError("fix_description is required")
        if not self.metric_name.strip():
            raise OutcomeLogError("metric_name is required")
        if not self.metric_before.strip():
            raise OutcomeLogError("metric_before is required")
        if not self.metric_after.strip():
            raise OutcomeLogError("metric_after is required")

    def to_claim_statement(self) -> str:
        page_ref = f" on {self.page_url}" if self.page_url else ""
        return (
            f"After implementing '{self.fix_description}'{page_ref}, "
            f"{self.metric_name} changed from '{self.metric_before}' to '{self.metric_after}'. "
            f"Remediation ID: {self.remediation_id}. Run ID: {self.run_id}."
            + (f" Notes: {self.notes}" if self.notes else "")
        )


# ── Stage ID derivation ───────────────────────────────────────────────────────

_REMEDIATION_TO_STAGE: dict[str, str] = {
    "CRAWLER_FULLY_BLOCKED":     "STAGE-01",
    "LLMS_TXT_MISSING":          "STAGE-02",
    "JSON_PARSE_FAILURE":        "STAGE-05",
    "MISSING_TYPE":              "STAGE-05",
    "MISSING_REQUIRED_FIELD":    "STAGE-05",
    "EXTRACTABILITY_NONE":       "STAGE-09",
    "EXTRACTABILITY_LOW":        "STAGE-09",
    "EXTRACTABILITY_MEDIUM":     "STAGE-14",
    "CITATION_NOT_OBSERVED":     "STAGE-22",
    "CITATION_OBSERVED":         "STAGE-22",
    "MISSING_RECOMMENDED_FIELD": "STAGE-05",
    "C052": "STAGE-03",
    "C053": "STAGE-05",
    "C056": "STAGE-11",
    "C058": "STAGE-09",
    "C061": "STAGE-14",
    "C062": "STAGE-09",
    "C072": "STAGE-22",
    "C073": "STAGE-22",
    "C074": "STAGE-20",
    "C077": "STAGE-20",
    "C078": "STAGE-22",
    "C079": "STAGE-21",
    "C082": "STAGE-22",
    "C090": "STAGE-22",
}

def _derive_stage_id(remediation_id: str) -> str:
    return _REMEDIATION_TO_STAGE.get(remediation_id, "STAGE-99")


# ── Next claim ID generator ───────────────────────────────────────────────────

def _next_claim_id(conn) -> str:
    row = conn.execute(
        "SELECT claim_id FROM claims WHERE claim_id LIKE 'C%' ORDER BY CAST(SUBSTR(claim_id,2) AS INTEGER) DESC LIMIT 1"
    ).fetchone()
    if row:
        try:
            num = int(row["claim_id"][1:]) + 1
            return f"C{num}"
        except ValueError:
            pass
    return "C200"


# ── Core logging function ─────────────────────────────────────────────────────

def log_outcome(entry: OutcomeEntry, db_path: Path) -> str:
    """Log a post-remediation outcome as a new claim. Returns the new claim_id."""
    entry.validate()

    conn = get_connection(db_path)
    try:
        # Verify the run exists
        run_row = conn.execute(
            "SELECT target_domain FROM audit_runs WHERE run_id = ?", (entry.run_id,)
        ).fetchone()
        if not run_row:
            raise OutcomeLogError(f"Audit run '{entry.run_id}' not found in database")

        domain = run_row["target_domain"]
        claim_id   = _next_claim_id(conn)
        stage_id   = _derive_stage_id(entry.remediation_id)
        statement  = entry.to_claim_statement()
        source_url = entry.page_url or f"https://{domain}"
        today      = utc_today_iso()

        # Build the row dict and validate with lint_claim()
        claim_row = {
            "claim_id": claim_id,
            "stage_id": stage_id,
            "claim_type": "outcome",
            "claim_scope": "audit-workflow",
            "statement": statement,
            "status": _INITIAL_STATUS,
            "source_tier_vocab": _HARDCODED_SOURCE_TIER_VOCAB,
            "source_tier_value": _HARDCODED_SOURCE_TIER_VALUE,
            "source_url": source_url,
            "source_date": today,
        }
        lint_errors = lint_claim(claim_row)
        if lint_errors:
            raise OutcomeLogError(
                f"Claim failed lint validation: {'; '.join(lint_errors)}"
            )

        # Use write_as() for proper changelog triggering
        with write_as(conn, actor="outcome-logger", reason=f"outcome from run {entry.run_id}"):
            conn.execute(
                """INSERT INTO claims
                   (claim_id, stage_id, claim_type, claim_scope, statement,
                    status, confidence, source_url, source_tier_vocab, source_tier_value, source_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    claim_id,
                    stage_id,
                    "outcome",
                    "audit-workflow",
                    statement,
                    _INITIAL_STATUS,
                    None,
                    source_url,
                    _HARDCODED_SOURCE_TIER_VOCAB,
                    _HARDCODED_SOURCE_TIER_VALUE,
                    today,
                )
            )
        # write_as() handles commit
        return claim_id
    except OutcomeLogError:
        raise
    except Exception as e:
        raise OutcomeLogError(f"Database error: {e}") from e


def list_outcomes(db_path: Path, run_id: Optional[str] = None) -> list[dict]:
    """List all logged outcome claims, optionally filtered by run_id."""
    conn = get_connection(db_path)
    if run_id:
        rows = conn.execute(
            "SELECT * FROM claims WHERE claim_type='outcome' AND statement LIKE ?",
            (f"%Run ID: {run_id}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM claims WHERE claim_type='outcome' ORDER BY claim_id DESC"
        ).fetchall()
    return [dict(r) for r in rows]
