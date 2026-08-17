import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from areos.api.dependencies import get_db, verify_admin
from areos.db.context import write_as
from areos.util.idempotency import with_idempotency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

class PromptSetPayload(BaseModel):
    label: str
    prompt_text: str
    target_domain: str = ""
    funnel_stage: str = ""
    active: int = 1

class PromptListResponse(BaseModel):
    prompts: list[dict[str, Any]]

@router.get("/prompts", response_model=PromptListResponse)
def list_prompts(target_domain: str | None = None, active: int | None = None, conn=Depends(get_db)):
    query = "SELECT * FROM prompt_sets WHERE 1=1"
    params = []
    if target_domain:
        query += " AND (target_domain = ? OR target_domain = '' OR target_domain IS NULL)"
        params.append(target_domain)
    if active is not None:
        query += " AND active = ?"
        params.append(active)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return {"prompts": [dict(r) for r in rows]}


@router.post("/prompts")
def create_prompt(request: Request, payload: PromptSetPayload, _: None = Depends(verify_admin), conn=Depends(get_db)):
    idem_key = request.headers.get("Idempotency-Key")
    
    def handler():
        prompt_id = f"PRM-{str(uuid.uuid4())[:8].upper()}"
        with write_as(conn, actor="api:prompts", reason="create-prompt-set"):
            conn.execute(
                "INSERT INTO prompt_sets (prompt_id, label, prompt_text, target_domain, funnel_stage, active) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    prompt_id, payload.label, payload.prompt_text,
                    payload.target_domain, payload.funnel_stage, payload.active,
                ),
            )
            conn.commit()
        return 200, {"status": "success", "prompt_id": prompt_id}

    status, body = with_idempotency(conn, idem_key, "/api/prompts", handler)
    return JSONResponse(status_code=status, content=body)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: str, _: None = Depends(verify_admin), conn=Depends(get_db)):
    try:
        row = conn.execute(
            "SELECT 1 FROM prompt_sets WHERE prompt_id = ?", (prompt_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prompt set not found")
        with write_as(conn, actor="api:prompts", reason=f"delete-prompt-{prompt_id}"):
            conn.execute("DELETE FROM prompt_sets WHERE prompt_id = ?", (prompt_id,))
            conn.commit()
        return {"status": "success", "prompt_id": prompt_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting prompt set: %s", e, exc_info=True)
        raise
