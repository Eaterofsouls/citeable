import json
import logging
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from areos.api.dependencies import get_client_keys, get_db, get_db_path, verify_admin
from areos.auditors.audit_orchestrator import run_orchestrated_audit
from areos.auditors.authority_auditor import audit_domain_authority
from areos.cli.report import AuditRunSummary, select_triggered_cards
from areos.db.context import write_as
from areos.services.verdict_service import get_verdicts_by_card
from areos.util.clock import utc_today_iso
from areos.util.idempotency import with_idempotency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

CARDS_DIR = Path(__file__).resolve().parents[3] / "areos" / "instruction_cards"

# --- Models ---
class AuditRunPayload(BaseModel):
    target_domain: str
    audited_stages: list
    automated_findings: list

class OrchestratedAuditPayload(BaseModel):
    target_domain: str
    sample_content: str = Field("", max_length=50000)
    api_provider: str = "auto"

class AuditRunModel(BaseModel):
    run_id: str
    target_domain: str
    run_date: str
    status: str
    overall_score: Optional[float] = None
    created_at: str
    approved_count: Optional[int] = 0
    rejected_count: Optional[int] = 0

class AuditRunListResponse(BaseModel):
    runs: list[AuditRunModel]

class FindingModel(BaseModel):
    claim_id: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
    confidence: Optional[str] = None
    # Fields emitted by the auditor pipeline
    code: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    page_url: Optional[str] = None

class TriggeredCardModel(BaseModel):
    card_id: str
    claim_ids: list[str] = []
    # Fields populated by get_audit_run \u2014 were previously stripped by
    # response_model serialisation because they weren't declared here.
    check_name: Optional[str] = None
    automatability: Optional[str] = None
    reason: Optional[str] = None
    verdicts: list[dict[str, Any]] = []   # manual_verdicts rows for this card
    complete: bool = False                 # True once at least one verdict submitted

class AuditRunDetailResponse(BaseModel):
    run: AuditRunModel
    automated_findings: list[FindingModel]
    triggered_cards: list[TriggeredCardModel]

class AuthorityAuditResponse(BaseModel):
    target_domain: str
    passed: bool
    error_count: int
    warning_count: int
    metrics: dict[str, Any]
    provider_used: str | None
    issues: list[dict[str, Any]]
    findings: list[dict[str, Any]]

# --- Routes ---
@router.post("/audit/runs")
def create_audit_run(
    request: Request,
    payload: AuditRunPayload,
    conn=Depends(get_db)
):
    idem_key = request.headers.get("Idempotency-Key")

    def handler():
        run_id = str(uuid.uuid4())[:8]
        run_date = utc_today_iso()
        # FIX (Readiness Audit, Major #1): this used to write directly via
        # conn.execute()+conn.commit(), bypassing write_as() and leaving the
        # changelog entry for every new audit run with actor=NULL/reason=NULL.
        with write_as(conn, actor="api:create_audit_run", reason=f"New audit run for {payload.target_domain}"):  # noqa: E501
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",  # noqa: E501
                (
                    run_id, payload.target_domain, run_date,
                    json.dumps(payload.audited_stages),
                    json.dumps(payload.automated_findings),
                    "automated_complete",
                ),
            )

        codes_fired = list({f.get("code") for f in payload.automated_findings if f.get("code")})
        summary = AuditRunSummary(
            target_domain=payload.target_domain,
            audited_stages=payload.audited_stages,
            check_codes_fired=codes_fired,
            automated_findings=payload.automated_findings,
            run_date=run_date,
        )
        triggered = select_triggered_cards(summary)

        return 200, {
            "run_id": run_id,
            "triggered_cards": [
                {
                    "card_id": c.card_id,
                    "check_name": c.check_name,
                    "automatability": c.automatability,
                    "reason": c.reason,
                }
                for c in triggered
            ],
        }

    status, body = with_idempotency(conn, idem_key, "/api/audit/runs", handler)
    return JSONResponse(status_code=status, content=body)


@router.get("/audit/runs", response_model=AuditRunListResponse)
def list_audit_runs(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT run_id, target_domain, run_date, status, overall_score, created_at FROM audit_runs ORDER BY created_at DESC"
    ).fetchall()
    return {"runs": [dict(r) for r in rows]}


@router.get("/audit/runs/{run_id}", response_model=AuditRunDetailResponse)
def get_audit_run(run_id: str, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    run = dict(row)
    findings = json.loads(run["automated_findings"])
    stages = json.loads(run["audited_stages"])
    codes_fired = list({f.get("code") for f in findings if f.get("code")})

    summary = AuditRunSummary(
        target_domain=run["target_domain"],
        audited_stages=stages,
        check_codes_fired=codes_fired,
        automated_findings=findings,
    )
    triggered = select_triggered_cards(summary)

    # Use MF-4 extracted service
    verdicts_by_card = get_verdicts_by_card(conn, run_id)

    # Build a lookup: card_id -> list of claim_ids via check_code_mappings
    def _claim_ids_for_card(card_obj) -> list[str]:
        """Look up claim IDs from check_code_mappings for codes that trigger this card."""
        from areos.cli.report import INSTRUCTION_CARDS
        card_def = next((cd for cd in INSTRUCTION_CARDS if cd["card_id"] == card_obj.card_id), None)
        if not card_def or not card_def.get("trigger_on_codes"):
            return []
        claim_ids = []
        for code in card_def["trigger_on_codes"]:
            rows = conn.execute(
                "SELECT claim_id FROM check_code_mappings WHERE check_code = ?", (code,)
            ).fetchall()
            for row in rows:
                cid = row[0]
                if cid not in claim_ids:
                    claim_ids.append(cid)
        return claim_ids

    cards_out = []
    for c in triggered:
        cards_out.append(
            {
                "card_id": c.card_id,
                "check_name": c.check_name,
                "automatability": c.automatability,
                "reason": c.reason,
                "claim_ids": _claim_ids_for_card(c),
                "verdicts": verdicts_by_card.get(c.card_id, []),
                "complete": bool(verdicts_by_card.get(c.card_id)),
            }
        )

    return {
        "run": {k: v for k, v in run.items() if k not in ("automated_findings",)},
        "automated_findings": findings,
        "triggered_cards": cards_out,
    }


@router.get("/audit/runs/{run_id}/full")
def get_full_run_report(run_id: str, conn=Depends(get_db)):
    """
    UX audit §5.3/§5.7 — the single rehydration endpoint that lets any
    Studio tab reload a past run's state: manual review progress, the
    remediation plan, and a persisted AI synthesis narrative if one exists.
    Used by the retired standalone pages' redirects (manual_review.html,
    remediation.html, outcome.html — see CHANGELOG.md §3.8) and by
    bookmarked ?run_id= links generally.

    Known scope limit: executive_scorecard's crawler/llms.txt/citation
    sub-fields were computed from live network calls at scan time and
    aren't independently reconstructable from stored findings without
    re-crawling — this endpoint returns overall_score (persisted at scan
    time) but leaves those specific sub-fields for the frontend to treat
    as unavailable on a reload, rather than guess. This does not affect a
    run's first, live view — only revisiting an old run_id later.
    """
    row = conn.execute("SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    run = dict(row)
    findings = json.loads(run["automated_findings"])

    from areos.services.run_state import (
        get_persisted_synthesis,
        get_run_completeness,
        get_wizard_cards_for_run,
    )

    wizard_cards = get_wizard_cards_for_run(run)
    completeness = get_run_completeness(conn, run_id, wizard_cards)
    synthesis = get_persisted_synthesis(conn, run_id)

    # Best-effort remediation plan rebuild — reuses the same claim-lookup
    # logic already proven in POST /synthesize (check_code -> claim_id via
    # check_code_mappings), since the original AuditPlan object from the
    # live orchestrate call isn't persisted, only the raw findings are.
    from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
    from areos.util.sanitize import sanitize_text

    enriched_recs = []
    for step_idx, f in enumerate(findings, 1):
        check_code = f.get("code") or f.get("check_code", "UNKNOWN")
        claim_row = conn.execute(
            "SELECT claim_id, statement, confidence, source_tier_value, claim_scope "
            "FROM claims WHERE claim_id = (SELECT claim_id FROM check_code_mappings WHERE check_code = ? LIMIT 1)",  # noqa: E501
            (check_code,),
        ).fetchone()
        if not claim_row:
            claim_row = conn.execute(
                "SELECT claim_id, statement, confidence, source_tier_value, claim_scope "
                "FROM claims WHERE claim_id IN (SELECT claim_id FROM check_code_mappings WHERE check_code = ?) LIMIT 1",  # noqa: E501
                (check_code,),
            ).fetchone()

        claim_id = claim_row[0] if claim_row else "C000"
        stmt = claim_row[1] if claim_row else "Search engineering best practice."
        conf = claim_row[2] if claim_row else "high"
        tier = claim_row[3] if claim_row else "tier-1"
        scope = claim_row[4] if claim_row else "general-knowledge"
        evidence_label = "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence"
        snippet = ACTION_SNIPPETS.get(check_code, "/* Consult AREOS implementation guidelines */")

        enriched_recs.append({
            "step_number": step_idx,
            "priority_score": f.get("priority", step_idx * 3),
            "title": sanitize_text(f.get("message", check_code)) or check_code,
            "description": sanitize_text(f.get("message", "")) or "",
            "check_code": check_code,
            "severity": f.get("severity", "warning"),
            "governing_claim_id": claim_id,
            "governing_claim_statement": sanitize_text(stmt) or "",
            "confidence": (conf or "high").upper(),
            "source_tier": (tier or "tier-1").upper(),
            "claim_scope": scope or "general-knowledge",
            "evidence_label": evidence_label,
            "action_snippet": snippet,
        })

    return {
        "run_id": run_id,
        "run_date": run.get("run_date"),
        "target_domain": run["target_domain"],
        "overall_score": run.get("overall_score"),
        "remediation_plan": enriched_recs,
        "llm_synthesis": synthesis or {"llm_synthesis_used": False, "reason": "No synthesis ran", "pending": not completeness["wizard_complete"]},  # noqa: E501
        "manual_review_wizard": wizard_cards,
        "raw_findings": findings,
        "completeness": completeness,
    }


# In-memory IP rate limiter, shared by any endpoint that can trigger real
# outbound/paid work (orchestrated audits, authority lookups).
#
# FIX (Readiness Audit, Major #4): this used to key on the raw
# X-Forwarded-For request header directly, which is fully attacker-supplied
# unless a trusted proxy strips and re-sets it — any client could rotate the
# header value per request to get a "fresh" bucket every time, defeating the
# limiter entirely. request.client.host is what Starlette/uvicorn resolves
# the connecting peer to (honoring --forwarded-allow-ips for a *trusted*
# proxy, per the Dockerfile's uvicorn invocation), so it isn't something an
# arbitrary client can simply overwrite with its own header.
_ip_buckets = defaultdict(list)


def _rate_limit(request: Request, bucket_prefix: str, limit: int = 10, window_seconds: int = 60) -> None:
    ip = request.client.host if request.client else "unknown"
    key = f"{bucket_prefix}:{ip}"
    now = time.time()
    recent = [t for t in _ip_buckets[key] if now - t < window_seconds]
    if len(recent) >= limit:
        _ip_buckets[key] = recent
        raise HTTPException(status_code=429, detail="Too many requests")
    recent.append(now)
    _ip_buckets[key] = recent


def check_rate_limit(request: Request):
    _rate_limit(request, bucket_prefix="orchestrate", limit=3, window_seconds=60)


def check_authority_rate_limit(request: Request):
    _rate_limit(request, bucket_prefix="authority", limit=3, window_seconds=60)


@router.get(
    "/audit/authority/{target_domain}",
    response_model=AuthorityAuditResponse,
    dependencies=[Depends(check_authority_rate_limit)],
)
def get_authority_audit(target_domain: str, api_provider: str = "auto"):
    # NOTE: This endpoint is rate-limited (3/min per IP) but does NOT require
    # the admin token — it is intentionally public so clients can check domain
    # authority without authentication. The rate-limit protects the server's
    # OPEN_PAGERANK_API_KEY quota against abuse.
    res = audit_domain_authority(target_domain, api_provider=api_provider)
    return {
        "target_domain": res.target_domain,
        "passed": res.passed,
        "error_count": res.error_count,
        "warning_count": res.warning_count,
        "metrics": res.metrics,
        "provider_used": res.provider_used,
        "issues": [
            {"severity": i.severity, "code": i.code, "message": i.message} for i in res.issues
        ],
        "findings": res.as_finding_dicts(),
    }


@router.post("/audit/orchestrate", dependencies=[Depends(check_rate_limit)])
def execute_orchestrated_audit(
    payload: OrchestratedAuditPayload,
    client_keys: Annotated[dict, Depends(get_client_keys)],
):
    db_path = get_db_path()
    return run_orchestrated_audit(
        target_domain=payload.target_domain,
        db_path=Path(db_path),
        sample_content=payload.sample_content,
        api_provider=payload.api_provider,
        client_keys=client_keys,
    )


@router.post("/audit/runs/{run_id}/synthesize", dependencies=[Depends(check_rate_limit)])
def synthesize_audit_run(
    run_id: str,
    request: Request,
    client_keys: Annotated[dict, Depends(get_client_keys)],
    conn=Depends(get_db),
):
    """
    POST /api/v1/audit/runs/{run_id}/synthesize

    Runs the three-step LLM synthesis pipeline for a completed audit run.
    MUST be called AFTER the Guided Manual Review wizard is complete so that
    human verdicts are merged with automated findings before synthesis.

    The LLM receives:
      - enriched_recs from the stored audit run (automated deterministic data)
      - manual_verdicts from the DB (human review signal)

    This is the correct trigger point. Synthesis intentionally does NOT run
    during /audit/orchestrate to avoid generic AI output with no human context.
    """
    # 1. Load the audit run
    row = conn.execute(
        "SELECT * FROM audit_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit run not found")

    run = dict(row)
    target_domain = run["target_domain"]

    # 2. Rebuild enriched_recs from the stored audit via the orchestrator's
    #    enrichment logic. We need the full claim-wired records, not just raw findings.
    #    Re-run the deterministic enrichment (no network calls, DB-only).
    db_path_str = get_db_path()
    db_path = Path(db_path_str)

    from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
    from areos.util.sanitize import sanitize_text
    from areos.db.connection import get_connection as _get_conn

    raw_findings = json.loads(run["automated_findings"])

    # Wire findings → claims to rebuild enriched_recs
    _conn = _get_conn(db_path)
    enriched_recs = []
    for step_idx, f in enumerate(raw_findings, 1):
        check_code = f.get("code") or f.get("check_code", "UNKNOWN")
        # Look up a governing claim for this check_code
        claim_row = _conn.execute(
            "SELECT claim_id, statement, confidence, source_tier_value, claim_scope "
            "FROM claims WHERE claim_id = (SELECT claim_id FROM check_code_mappings WHERE check_code = ? LIMIT 1)",
            (check_code,),
        ).fetchone()
        if not claim_row:
            # Fallback: find any claim mentioning this code
            claim_row = _conn.execute(
                "SELECT claim_id, statement, confidence, source_tier_value, claim_scope "
                "FROM claims WHERE claim_id IN (SELECT claim_id FROM check_code_mappings WHERE check_code = ?) LIMIT 1",
                (check_code,),
            ).fetchone()

        claim_id = claim_row[0] if claim_row else "C000"
        stmt = claim_row[1] if claim_row else "Search engineering best practice."
        conf = claim_row[2] if claim_row else "high"
        tier = claim_row[3] if claim_row else "tier-1"
        scope = claim_row[4] if claim_row else "general-knowledge"
        evidence_label = "Knowledge Base Principle" if scope == "general-knowledge" else "Site-Specific Evidence"
        snippet = ACTION_SNIPPETS.get(check_code, "/* Consult AREOS implementation guidelines */")

        enriched_recs.append({
            "step_number": step_idx,
            "priority_score": f.get("priority", step_idx * 3),
            "title": sanitize_text(f.get("message", check_code)) or check_code,
            "description": sanitize_text(f.get("message", "")) or "",
            "check_code": check_code,
            "severity": f.get("severity", "warning"),
            "governing_claim_id": claim_id,
            "governing_claim_statement": sanitize_text(stmt) or "",
            "confidence": (conf or "high").upper(),
            "source_tier": (tier or "tier-1").upper(),
            "claim_scope": scope or "general-knowledge",
            "evidence_label": evidence_label,
            "action_snippet": snippet,
        })

    # 3. Load manual verdicts and append them as human context signals
    verdict_rows = conn.execute(
        "SELECT card_id, page_url, verdict, severity, notes, submitted_at "
        "FROM manual_verdicts WHERE run_id = ? ORDER BY submitted_at",
        (run_id,),
    ).fetchall()

    manual_verdicts_context = [
        {
            "card_id": v["card_id"],
            "page_url": v["page_url"],
            "verdict": v["verdict"],
            "severity": v["severity"],
            "notes": v["notes"],
            "submitted_at": v["submitted_at"],
        }
        for v in verdict_rows
    ]

    # Inject manual verdict notes into enriched_recs where card_id ↔ check_code matches
    # This enriches the LLM input with human observations
    verdict_notes_by_card = {}
    for v in manual_verdicts_context:
        cid = v["card_id"]
        if cid not in verdict_notes_by_card:
            verdict_notes_by_card[cid] = []
        if v["notes"]:
            verdict_notes_by_card[cid].append(f"[Human review — {v['verdict'].upper()}] {v['notes']}")

    for rec in enriched_recs:
        code = rec["check_code"]
        if code in verdict_notes_by_card:
            rec["human_review_notes"] = " | ".join(verdict_notes_by_card[code])
        # Also check card_id pattern (manual cards use M- prefix)
        for card_id, notes in verdict_notes_by_card.items():
            if code.lower() in card_id.lower():
                rec.setdefault("human_review_notes", " | ".join(notes))

    # 4. Run the three-step LLM synthesis with full context
    from areos.llm.providers import check_any_provider_configured
    from areos.llm.synthesis_pipeline import run_llm_synthesis

    if not check_any_provider_configured(client_keys):
        return {
            "llm_synthesis_used": False,
            "reason": "No LLM provider configured — supply an API key via BYOK headers",
        }

    try:
        result = run_llm_synthesis(
            enriched_recs=enriched_recs,
            target_domain=target_domain,
            client_keys=client_keys,
            db_path=db_path,
        )
        logger.info(
            "Post-manual-review synthesis complete for run %s — %d manual verdicts merged",
            run_id, len(manual_verdicts_context),
        )
        result["manual_verdicts_merged"] = len(manual_verdicts_context)

        # UX audit §5.3: persist the result. Previously this only existed in
        # the HTTP response — a page reload silently lost the "final report"
        # the whole hybrid flow builds toward. This is what GET
        # /audit/runs/{run_id}/full reads back for rehydration.
        if result.get("llm_synthesis_used"):
            try:
                from areos.services.run_state import persist_synthesis
                with write_as(conn, actor="api:synthesize_audit_run", reason=f"Persisted AI synthesis for {run_id}"):  # noqa: E501
                    persist_synthesis(conn, run_id, result)
            except Exception as persist_exc:  # noqa: BLE001
                # Don't fail the user-facing synthesis response over a
                # persistence hiccup — they still get their report this
                # session, they just won't be able to reload and see it.
                logger.warning("Failed to persist synthesis for run %s: %s", run_id, persist_exc)

        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("Synthesis failed for run %s: %s", run_id, exc)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {exc}") from exc
