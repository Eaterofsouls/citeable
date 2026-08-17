import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from areos.api.dependencies import get_db, get_db_path, verify_admin
from areos.auditors.qa_gate import run_qa_gate
from areos.auditors.synthesis_engine import synthesise
from areos.cli.report import AuditRunSummary, generate_gap_report
from areos.db.context import write_as
from areos.services.report_generator import assemble_markdown_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

CARDS_DIR = Path(__file__).resolve().parents[3] / "areos" / "instruction_cards"

VALID_VERDICTS = {"pass", "warn", "fail", "na"}
VALID_SEVERITIES = {"error", "warning", "info"}

# Redefine ManualFinding locally or import if exposed; it was in main.py
from areos.auditors.synthesis_engine import ManualFinding

class ReportResponse(BaseModel):
    run_id: str
    target_domain: str
    manual_verdicts_count: int
    report_markdown: str

class RemediationPlanResponse(BaseModel):
    run_id: str
    target_domain: str
    total_recommendations: int
    critical_count: int
    qa_rejections: int
    recommendations: list[dict[str, Any]]
    qa_rejected: list[dict[str, Any]]
    plan_markdown: str

@router.get("/audit/runs/{run_id}/report", response_model=ReportResponse)
def get_final_report(run_id: str, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    run = dict(row)
    findings = json.loads(run["automated_findings"])
    stages = json.loads(run["audited_stages"])

    verdicts = conn.execute(
        "SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)
    ).fetchall()
    verdicts_list = [dict(v) for v in verdicts]

    codes_fired = list({f.get("code") for f in findings if f.get("code")})
    summary = AuditRunSummary(
        target_domain=run["target_domain"],
        audited_stages=stages,
        check_codes_fired=codes_fired,
        automated_findings=findings,
    )

    base_report_md = generate_gap_report(summary, CARDS_DIR)
    final_markdown = assemble_markdown_report(base_report_md, verdicts_list)

    # FIX (Readiness Audit, Minor #1 / Major #1): this was a bare
    # conn.execute()+conn.commit() inside a GET handler — a status-mutating
    # side effect hiding in a nominally read-only route, and (per the
    # project's own architecture rule in db/context.py) a write happening
    # outside write_as(), so the changelog would record this write with
    # actor=NULL/reason=NULL. Route it through write_as() for correct
    # attribution; the GET-with-a-side-effect API design itself is left as
    # documented behavior (regenerating the report is what marks a run
    # "report_generated") rather than restructured in this pass.
    with write_as(conn, actor="api:get_final_report", reason=f"Report viewed/regenerated for {run_id}"):  # noqa: E501
        conn.execute(
            "UPDATE audit_runs SET status = ? WHERE run_id = ?", ("report_generated", run_id)
        )

    return {
        "run_id": run_id,
        "target_domain": run["target_domain"],
        "manual_verdicts_count": len(verdicts_list),
        "report_markdown": final_markdown,
    }

@router.get("/audit/runs/{run_id}/remediation", response_model=RemediationPlanResponse)
def get_remediation_plan(run_id: str, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    run = dict(row)
    findings = json.loads(run["automated_findings"])
    verdicts = conn.execute(
        "SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)
    ).fetchall()
    verdicts_data = [dict(v) for v in verdicts]

    manual_findings = []
    for v in verdicts_data:
        verd = v.get("verdict", "na").strip().lower()
        sev = v.get("severity", "info").strip().lower()
        if verd not in VALID_VERDICTS:
            verd = "na"
        if sev not in VALID_SEVERITIES:
            sev = "info"
        manual_findings.append(
            ManualFinding(
                card_id=v["card_id"],
                check_name=v["card_id"],
                verdict=verd,
                severity=sev,
                notes=v.get("notes", ""),
                page_url=v.get("page_url", ""),
                claim_ids=[v["card_id"]],
            )
        )

    db_path = get_db_path() # Required by synthesise, could adapt to pass conn later
    
    plan = synthesise(
        run_id=run_id,
        target_domain=run["target_domain"],
        automated_findings=findings,
        manual_findings=manual_findings,
        db_path=db_path,
    )

    qa_result = run_qa_gate(plan, db_path)
    plan.recommendations = qa_result.passed
    plan.qa_rejected = qa_result.rejected

    return {
        "run_id": run_id,
        "target_domain": run["target_domain"],
        "total_recommendations": len(plan.recommendations),
        "critical_count": plan.critical_count,
        "qa_rejections": len(plan.qa_rejected),
        "recommendations": [r.as_dict() for r in plan.recommendations],
        "qa_rejected": plan.qa_rejected,
        "plan_markdown": plan.format_markdown(),
    }
