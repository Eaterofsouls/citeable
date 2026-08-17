import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from areos.api.dependencies import get_db, get_db_path, verify_admin
from areos.auditors.outcome_logger import OutcomeEntry, OutcomeLogError, list_outcomes, log_outcome

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

class OutcomePayload(BaseModel):
    remediation_id: str
    fix_description: str
    metric_name: str
    metric_before: str
    metric_after: str
    page_url: str = ""
    notes: str = ""

class OutcomeListResponse(BaseModel):
    outcomes: list[dict[str, Any]]

@router.post("/audit/runs/{run_id}/outcomes")
def submit_outcome(
    run_id: str,
    payload: OutcomePayload,
    _: None = Depends(verify_admin)
):
    # db_path requires the get_db_path resolver to use the outcome_logger functions properly
    db_path = get_db_path()
    entry = OutcomeEntry(
        run_id=run_id,
        remediation_id=payload.remediation_id,
        fix_description=payload.fix_description,
        metric_name=payload.metric_name,
        metric_before=payload.metric_before,
        metric_after=payload.metric_after,
        page_url=payload.page_url,
        notes=payload.notes,
    )
    try:
        new_claim_id = log_outcome(entry, db_path)
        return {"status": "success", "claim_id": new_claim_id, "run_id": run_id}
    except OutcomeLogError as e:
        raise HTTPException(status_code=400, detail="Invalid request") from e
    except Exception as e:
        logger.error("Outcome logging error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error") from e

@router.get("/outcomes", response_model=OutcomeListResponse)
def get_outcomes(run_id: str = None, _: None = Depends(verify_admin)):
    db_path = get_db_path()
    try:
        outcomes = list_outcomes(db_path, run_id=run_id)
        return {"outcomes": outcomes}
    except Exception as e:
        logger.error("Error listing outcomes: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error") from e
