# areos/services/run_state.py
#
# UX audit §5.2 / §5.3 — before this module, "is manual review complete for
# this run?" was answered only client-side, from counters in studio.js that
# reset on page reload. The server never knew how many manual review cards
# a run was expected to have; it only accumulated individual verdict rows.
#
# select_triggered_cards() is a pure function of the run's stored
# automated_findings — the same input audit_orchestrator.py used to compute
# wizard cards at scan time. So the expected card set can be recomputed
# server-side at any time from data already persisted in audit_runs,
# without any new columns for "expected cards" and without touching the
# claims schema.

from __future__ import annotations

import json
from typing import Any

from areos.auditors.audit_orchestrator import MANUAL_CARD_GUIDANCE
from areos.cli.report import AuditRunSummary, select_triggered_cards


def get_wizard_cards_for_run(run: dict) -> list[dict]:
    """Recompute the manual-review wizard card list for a stored run,
    identically to how audit_orchestrator.py computed it at scan time."""
    findings = json.loads(run["automated_findings"])
    stages = json.loads(run["audited_stages"])
    codes_fired = list({f.get("code") for f in findings if f.get("code")})

    summary = AuditRunSummary(
        target_domain=run["target_domain"],
        audited_stages=stages,
        check_codes_fired=codes_fired,
        automated_findings=findings,
        run_date=run.get("run_date", ""),
    )
    triggered_cards = select_triggered_cards(summary)

    wizard_cards = []
    for c in triggered_cards:
        guidance = MANUAL_CARD_GUIDANCE.get(c.card_id, MANUAL_CARD_GUIDANCE["DEFAULT"])
        wizard_cards.append({
            "card_id": c.card_id,
            "check_name": c.check_name,
            "reason": c.reason,
            "title": guidance["title"],
            "what_to_look_for": guidance["what_to_look_for"],
            "how_to_fill": guidance["how_to_fill"],
        })
    return wizard_cards


def get_run_completeness(conn, run_id: str, wizard_cards: list[dict] | None = None) -> dict[str, Any]:
    """
    Derives run status live from ground truth (stored findings + submitted
    verdicts + persisted synthesis) instead of trusting a stored `status`
    string that three different routers used to write inconsistently.

    Returns:
      total_wizard_cards, completed_wizard_cards, wizard_complete,
      has_synthesis, status (one of: awaiting_review | ready_for_synthesis | complete)
    """
    if wizard_cards is None:
        row = conn.execute("SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
        wizard_cards = get_wizard_cards_for_run(dict(row)) if row else []

    total = len(wizard_cards)

    completed_row = conn.execute(
        "SELECT COUNT(DISTINCT card_id) AS n FROM manual_verdicts WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    completed = completed_row["n"] if completed_row else 0
    # A run can have more completed cards than currently-triggered ones if
    # findings were re-evaluated; never show a completed count above total.
    completed = min(completed, total) if total else completed

    wizard_complete = (total == 0) or (completed >= total)

    synth_row = conn.execute(
        "SELECT run_id FROM audit_synthesis WHERE run_id = ?", (run_id,)
    ).fetchone()
    has_synthesis = synth_row is not None

    if has_synthesis:
        status = "complete"
    elif wizard_complete:
        status = "ready_for_synthesis"
    else:
        status = "awaiting_review"

    return {
        "total_wizard_cards": total,
        "completed_wizard_cards": completed,
        "wizard_complete": wizard_complete,
        "has_synthesis": has_synthesis,
        "status": status,
    }


def get_persisted_synthesis(conn, run_id: str) -> dict[str, Any] | None:
    """Reads back a previously-persisted synthesis result in the same shape
    the frontend already expects from POST /synthesize's response, so
    renderSynthesisTab() in studio.js works unmodified for both paths."""
    row = conn.execute(
        "SELECT * FROM audit_synthesis WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return None
    r = dict(row)
    return {
        "llm_synthesis_used": True,
        "narrative": r.get("narrative", ""),
        "draft": r.get("draft", ""),
        "flags": json.loads(r.get("flags_json") or "[]"),
        "flags_resolved": r.get("flags_resolved", 0),
        "provider_log": json.loads(r.get("provider_log_json") or "[]"),
        "manual_verdicts_merged": r.get("manual_verdicts_merged", 0),
    }


def persist_synthesis(conn, run_id: str, result: dict[str, Any]) -> None:
    """Upserts a synthesis result. Caller must already be inside a
    write_as(...) block so the changelog attributes this write correctly."""
    conn.execute(
        "INSERT INTO audit_synthesis "
        "(run_id, narrative, draft, flags_json, flags_resolved, provider_log_json, manual_verdicts_merged, created_at) "  # noqa: E501
        "VALUES (?,?,?,?,?,?,?, datetime('now')) "
        "ON CONFLICT(run_id) DO UPDATE SET "
        "narrative=excluded.narrative, draft=excluded.draft, flags_json=excluded.flags_json, "
        "flags_resolved=excluded.flags_resolved, provider_log_json=excluded.provider_log_json, "
        "manual_verdicts_merged=excluded.manual_verdicts_merged, created_at=excluded.created_at",
        (
            run_id,
            result.get("narrative", ""),
            result.get("draft", ""),
            json.dumps(result.get("flags", [])),
            result.get("flags_resolved", 0),
            json.dumps(result.get("provider_log", [])),
            result.get("manual_verdicts_merged", 0),
        ),
    )
