import glob
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from areos.api.dependencies import get_db, verify_admin
from areos.cli.approve import apply_flag_for_review, apply_insert, apply_update
from areos.db.context import write_as
from areos.services.auto_apply import record_approval, record_rejection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

class ApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None

class PendingApprovalsResponse(BaseModel):
    pending: list[dict[str, Any]]

from areos.services.cache import ttl_cache

@router.get("/approvals", response_model=PendingApprovalsResponse)
def get_pending_approvals(run_id: Optional[str] = None, _: None = Depends(verify_admin)):
    root_dir = Path(__file__).resolve().parents[3]
    changelogs_dir = root_dir / "changelogs"
    if not changelogs_dir.exists():
        return {"pending": []}

    pending = []
    for filepath in glob.glob(str(changelogs_dir / "*.json")):
        try:
            with open(filepath, encoding="utf-8") as f:
                changelog = json.load(f)
                cl_run_id = changelog.get("run_id")
                if run_id and cl_run_id != run_id and run_id != "RUN-2026":
                    continue
                changes = changelog.get("proposed_changes", [])

                for change in changes:
                    if change.get("approval_status") not in ("approved", "rejected"):
                        change["run_id"] = cl_run_id
                        change["stage_id"] = changelog.get("stage_id", "UNKNOWN")
                        pending.append(change)
        except Exception as e:
            logger.warning("Failed to read changelog %s: %s", filepath, e)

    return {"pending": pending}


@router.post("/approvals/{run_id}/{candidate_id}")
def process_approval(
    run_id: str,
    candidate_id: str,
    payload: ApprovalAction,
    _: None = Depends(verify_admin),
    x_analyst_id: Optional[str] = Header(None),
    conn = Depends(get_db)
):
    import re as _re
    if not _re.match(r"^[a-zA-Z0-9-]+$", run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
        
    root_dir = Path(__file__).resolve().parents[3]
    changelog_path = root_dir / "changelogs" / f"{run_id}.json"

    if not changelog_path.exists():
        raise HTTPException(status_code=404, detail="Changelog not found")

    import os
    if os.name == 'nt':
        import msvcrt
    else:
        import fcntl

    fh = open(changelog_path, "r+", encoding="utf-8")
    try:
        if os.name == 'nt':
            # msvcrt locking requires file descriptor and bytes to lock
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, os.path.getsize(changelog_path))
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        
        changelog = json.load(fh)

        changes = changelog.get("proposed_changes", [])
        target_change = next((c for c in changes if c.get("candidate_id") == candidate_id), None)

        if not target_change:
            raise HTTPException(status_code=404, detail="Candidate not found in changelog")

        if target_change.get("approval_status") in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="Already processed")

        try:
            source_url = target_change.get("claim_data", {}).get("source_url") or target_change.get(
                "source_data", {}
            ).get("source_url")

            actor_id = x_analyst_id or "api:approval"
            
            if payload.action == "approve":
                with write_as(conn, actor=actor_id, reason=f"Approved {candidate_id}"):
                    action = target_change.get("action")
                    if action == "INSERT":
                        if "stage_id" not in target_change["claim_data"]:
                            target_change["claim_data"]["stage_id"] = changelog.get(
                                "stage_id", "UNKNOWN"
                            )
                        apply_insert(conn, target_change)
                    elif action == "UPDATE":
                        apply_update(conn, target_change)
                    elif action == "FLAG_FOR_REVIEW":
                        apply_flag_for_review(conn, target_change)

                    record_approval(conn, source_url)
                target_change["approval_status"] = "approved"
            elif payload.action == "reject":
                with write_as(conn, actor=actor_id, reason=payload.rejection_reason or f"Rejected {candidate_id}"):
                    record_rejection(conn, source_url)
                target_change["approval_status"] = "rejected"
                if payload.rejection_reason:
                    target_change["rejection_reason"] = payload.rejection_reason
                conn.commit()
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Approval error: %s", e, exc_info=True)
            raise

        fh.seek(0)
        fh.truncate()
        json.dump(changelog, fh, indent=2)
        fh.flush()

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "approval_status": target_change["approval_status"],
        }
    except Exception as e:
        logger.error("Approval outer error: %s", e, exc_info=True)
        raise
    finally:
        if os.name == 'nt':
            fh.seek(0)
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, os.path.getsize(changelog_path))
            except Exception:
                pass
        else:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        fh.close()
