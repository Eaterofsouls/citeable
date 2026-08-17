import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field

from areos.api.dependencies import get_db, verify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

class ClaimModel(BaseModel):
    claim_id: str
    stage_id: Optional[str] = None
    claim_scope: Optional[str] = None
    claim_type: str
    statement: str
    status: str
    confidence: Optional[str] = None
    source_url: Optional[str] = None
    source_tier_vocab: Optional[str] = None
    source_tier_value: Optional[str] = None
    source_date: Optional[str] = None
    last_verified: Optional[str] = None
    superseded_by: Optional[str] = None

class ClaimResponse(BaseModel):
    total_count: int
    claims: list[ClaimModel]

class IngestionPayload(BaseModel):
    action: str  # "INSERT" or "UPDATE"
    claim_id: Optional[str] = None
    statement: str = Field(..., max_length=50000)
    source_url: str = Field(..., max_length=10000)
    confidence: str
    source_tier: str
    notes: Optional[str] = None

@router.get("/claims", response_model=ClaimResponse)
def get_claims(
    search_query: str | None = None,
    status: str | None = None,
    confidence: str | None = None,
    stage_id: str | None = None,
    claim_type: str | None = None,
    claim_id: str | None = None,
    run_id: str | None = None,
    exclude_deprecated: bool = False,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    try:
        base_query = "FROM claims WHERE 1=1"
        params = []

        if search_query:
            # Escape wildcards to prevent broad table scans via LIKE injection
            safe_query = search_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            base_query += " AND statement LIKE ? ESCAPE '\\'"
            params.append(f"%{safe_query}%")
        if claim_id:
            base_query += " AND claim_id = ?"
            params.append(claim_id)
        if status and status != "all":
            base_query += " AND status = ?"
            params.append(status)
        elif exclude_deprecated and (not status or status != "all"):
            base_query += " AND status != 'deprecated'"
        if confidence:
            base_query += " AND confidence = ?"
            params.append(confidence)
        if stage_id:
            base_query += " AND stage_id = ?"
            params.append(stage_id)
        if claim_type:
            base_query += " AND claim_type = ?"
            params.append(claim_type)
        if run_id:
            # Ignore run_id restriction on the global Live Claims Registry so all database assertions remain inspectable
            pass

        # Get total count
        count_query = f"SELECT COUNT(*) {base_query}"
        total_count = conn.execute(count_query, params).fetchone()[0]

        # Get paginated records
        query = f"SELECT * {base_query} ORDER BY claim_id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return {"total_count": total_count, "claims": [dict(r) for r in rows]}
    except Exception as e:
        logger.error("Error fetching claims: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/claims/ingest", dependencies=[Depends(verify_admin)])
def ingest_claim(
    payload: IngestionPayload,
    x_analyst_id: Optional[str] = Header(None),
    conn: sqlite3.Connection = Depends(get_db)
):
    try:
        # Stage changelog candidate for proposed UPDATE / INSERT.
        
        # Let's create a stub changelog entry.
        run_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        candidate_id = f"cand_{uuid.uuid4().hex[:8]}"
        actor = x_analyst_id or "ui:manual"
        
        import json
        from pathlib import Path
        import os
        
        root_dir = Path(__file__).resolve().parents[3]
        changelogs_dir = root_dir / "changelogs"
        changelogs_dir.mkdir(exist_ok=True)
        
        changelog_path = changelogs_dir / f"{run_id}.json"
        
        new_candidate = {
            "candidate_id": candidate_id,
            "action": payload.action,
            "approval_status": "pending",
            "actor": actor,
            "notes": payload.notes,
            "claim_data": {
                "statement": payload.statement,
                "source_url": payload.source_url,
                "confidence": payload.confidence,
                "source_tier_value": payload.source_tier
            }
        }
        if payload.claim_id:
            new_candidate["claim_data"]["claim_id"] = payload.claim_id
            
        changelog = {
            "run_id": run_id,
            "target_domain": "manual_ingestion",
            "run_date": datetime.now().isoformat(),
            "status": "in_review",
            "proposed_changes": [new_candidate]
        }
        
        with open(changelog_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2)
            
        return {"status": "success", "run_id": run_id, "candidate_id": candidate_id}
    except Exception as e:
        logger.error("Error ingesting claim: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")
