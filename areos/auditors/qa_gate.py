# areos/auditors/qa_gate.py
#
# Task 5c: QA Gate
#
# CONTRACT:
#   - Deterministic, NO-LLM gate.
#   - Rejects any recommendation whose claim_id:
#       (a) does not exist in the claims table
#       (b) has status 'deprecated' or 'superseded'
#       (c) is None or empty
#   - MUST be called before any RemediationPlan is shown to a client.
#   - Policy: fail loudly; never silently pass a bad recommendation.

from __future__ import annotations
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from areos.auditors.synthesis_engine import RemediationPlan, Recommendation

logger = logging.getLogger(__name__)

REJECTED_STATUSES = {"deprecated", "superseded", "archived"}


@dataclass
class QAResult:
    passed: list[Recommendation]
    rejected: list[dict]

    @property
    def is_clean(self) -> bool:
        return len(self.rejected) == 0

    def format_summary(self) -> str:
        lines = [
            f"QA Gate Result: {'CLEAN' if self.is_clean else 'FAILURES DETECTED'}",
            f"  Passed:   {len(self.passed)}",
            f"  Rejected: {len(self.rejected)}",
        ]
        for r in self.rejected:
            lines.append(f"  [REJECTED] {r['check_code']}: {r['reason']}")
        return "\n".join(lines)


def _lookup_claim_status(claim_id: str, db_path: Path) -> Optional[str]:
    """Return the claim's status or None if not found."""
    try:
        from areos.db.connection import get_connection
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT status FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        return row["status"] if row else None
    except sqlite3.OperationalError as e:
        logger.error("DB error looking up claim '%s': %s", claim_id, e)
        # Surface the error — do NOT silently return None
        raise
    except Exception as e:
        logger.error("Unexpected error looking up claim '%s': %s", claim_id, e)
        raise


def run_qa_gate(plan: RemediationPlan, db_path: Path) -> QAResult:
    passed = []
    rejected = list(plan.qa_rejected)

    for rec in plan.recommendations:
        # Manual-sourced findings (source='manual') pass without DB lookup —
        # they are human-entered verdicts with no corresponding claim_id in the
        # knowledge base. All other recommendations, including instruction-card
        # IDs (C052–C090), must pass full DB status validation.
        # GOVERNANCE: The previous C0xx pattern-match bypass was removed per
        # AREOS_KNOWLEDGE_GOVERNANCE_SPEC.md §1.5 — claim_id format is not a
        # substitute for an active status in the claims table.
        if rec.source == "manual":
            passed.append(rec)
            continue

        if not rec.claim_id or rec.claim_id.strip() == "":
            rejected.append({
                "check_code": rec.check_code,
                "reason": "claim_id is None or empty — no evidence chain",
            })
            continue

        try:
            status = _lookup_claim_status(rec.claim_id, db_path)
        except sqlite3.OperationalError as e:
            rejected.append({
                "check_code": rec.check_code,
                "reason": "UNKNOWN_DB_ERROR",
            })
            continue
        except Exception as e:
            rejected.append({
                "check_code": rec.check_code,
                "reason": f"DB error looking up claim '{rec.claim_id}': {e}",
            })
            continue

        if status is None:
            rejected.append({
                "check_code": rec.check_code,
                "reason": f"claim_id '{rec.claim_id}' not found in claims table",
            })
            continue

        if status.lower() in REJECTED_STATUSES:
            rejected.append({
                "check_code": rec.check_code,
                "reason": f"claim_id '{rec.claim_id}' has status '{status}' — cannot cite",
            })
            continue

        passed.append(rec)

    return QAResult(passed=passed, rejected=rejected)


def validate_plan(plan: RemediationPlan, db_path: Path) -> RemediationPlan:
    result = run_qa_gate(plan, db_path)
    plan.recommendations = result.passed
    plan.qa_rejected = result.rejected
    return plan
