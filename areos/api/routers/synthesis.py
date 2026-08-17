# areos/api/routers/synthesis.py
#
# CRUD for the three LLM synthesis step prompts.
# Prompts are runtime-auditable: GET to read, PUT to update, POST /reset to restore defaults.
# All writes tracked in the changelog via write_as().

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from areos.api.dependencies import get_db, verify_admin
from areos.db.context import write_as
from areos.util.clock import utc_today_iso

router = APIRouter(prefix="/api/v1")

LEGAL_STEPS = {"synthesizer", "red_teamer", "grounder"}


class PromptUpdate(BaseModel):
    system_prompt: str


@router.get("/synthesis/prompts")
def get_synthesis_prompts(conn=Depends(get_db), _=Depends(verify_admin)):
    """Return all three synthesis step prompts."""
    rows = conn.execute(
        "SELECT step, system_prompt, updated_at, updated_by FROM synthesis_prompts"
    ).fetchall()
    return {
        "prompts": [
            {
                "step":          r["step"],
                "system_prompt": r["system_prompt"],
                "updated_at":    r["updated_at"],
                "updated_by":    r["updated_by"],
            }
            for r in rows
        ]
    }


@router.put("/synthesis/prompts/{step}")
def update_synthesis_prompt(
    step: str,
    payload: PromptUpdate,
    conn=Depends(get_db),
    _=Depends(verify_admin),
):
    """Update a single synthesis step prompt. Tracked in the changelog."""
    if step not in LEGAL_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"step must be one of {sorted(LEGAL_STEPS)}",
        )
    if not payload.system_prompt.strip():
        raise HTTPException(status_code=400, detail="system_prompt cannot be empty")

    with write_as(
        conn,
        actor="api:update_synthesis_prompt",
        reason=f"Admin updated synthesis prompt for step '{step}'",
    ):
        conn.execute(
            "UPDATE synthesis_prompts "
            "SET system_prompt=?, updated_at=?, updated_by='admin' "
            "WHERE step=?",
            (payload.system_prompt.strip(), utc_today_iso(), step),
        )

    return {"ok": True, "step": step}


@router.post("/synthesis/prompts/reset/{step}")
def reset_synthesis_prompt(
    step: str,
    conn=Depends(get_db),
    _=Depends(verify_admin),
):
    """Reset a synthesis step prompt to its hardcoded default. Tracked in changelog."""
    if step not in LEGAL_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"step must be one of {sorted(LEGAL_STEPS)}",
        )

    from areos.llm.synthesis_pipeline import (
        _DEFAULT_GROUNDER_PROMPT,
        _DEFAULT_RED_TEAMER_PROMPT,
        _DEFAULT_SYNTHESIZER_PROMPT,
    )

    defaults = {
        "synthesizer": _DEFAULT_SYNTHESIZER_PROMPT,
        "red_teamer":  _DEFAULT_RED_TEAMER_PROMPT,
        "grounder":    _DEFAULT_GROUNDER_PROMPT,
    }

    with write_as(
        conn,
        actor="api:reset_synthesis_prompt",
        reason=f"Admin reset synthesis prompt for step '{step}' to default",
    ):
        conn.execute(
            "UPDATE synthesis_prompts "
            "SET system_prompt=?, updated_at=?, updated_by='system:default' "
            "WHERE step=?",
            (defaults[step], utc_today_iso(), step),
        )

    return {"ok": True, "step": step, "reset_to": "default"}
