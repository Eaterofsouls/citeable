import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from areos.api.dependencies import get_db, verify_admin
from areos.db.context import write_as

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

class ManualVerdictPayload(BaseModel):
    card_id: str
    page_url: str = ""
    verdict: Literal["pass", "warn", "fail", "na"]
    severity: Literal["error", "warning", "info"]
    notes: str = ""

@router.post("/audit/runs/{run_id}/verdicts")
def submit_verdict(
    run_id: str,
    payload: ManualVerdictPayload,
    conn=Depends(get_db)
):
    row = conn.execute("SELECT run_id FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    # FIX (Readiness Audit, Major #1): this wrote directly via conn.execute()
    # + conn.commit(), bypassing write_as() — forbidden per db/context.py's
    # own architecture rule, since it leaves changelog rows with
    # actor=NULL/reason=NULL for what should be a clearly-attributed manual
    # review action.
    with write_as(conn, actor="api:submit_verdict", reason=f"Manual verdict '{payload.verdict}' on {payload.card_id} for {run_id}"):  # noqa: E501
        conn.execute(
            "INSERT INTO manual_verdicts (run_id, card_id, page_url, verdict, severity, notes) VALUES (?,?,?,?,?,?)",  # noqa: E501
            (
                run_id,
                payload.card_id,
                payload.page_url,
                payload.verdict,
                payload.severity,
                payload.notes,
            ),
        )
        conn.execute("UPDATE audit_runs SET status = ? WHERE run_id = ?", ("in_review", run_id))

    return {"status": "ok", "run_id": run_id, "card_id": payload.card_id}
