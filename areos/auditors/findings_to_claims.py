# areos/auditors/findings_to_claims.py
#
# Task 3f: Wire Automated Findings to Claims
#
# CONTRACT:
#   - Receives a finding dict from any Stage 3 auditor.
#   - Resolves the finding to a specific claim_id in the live SQLite claims table.
#   - Returns the claim's current status and confidence alongside the finding.
#   - Every finding in a report MUST pass through this wiring before being shown.

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from areos.db.connection import get_connection, get_db_path

logger = logging.getLogger(__name__)

# Mappings are now governed in the database table `check_code_mappings`.

def _default_db_path() -> Path:
    # FIX (data-quality pass, follow-up to Blocker 3): this used to
    # reimplement its own two-way (AREOS_TEST_DB / repo-root) path logic,
    # missing the RENDER branch that areos.db.connection.get_db_path()
    # has. It was inert in practice only because every real caller
    # (synthesis_engine.py) already passes db_path explicitly, but as a
    # fallback it would have silently pointed at the wrong, ephemeral file
    # on Render. Delegate to the single canonical resolver instead.
    return Path(get_db_path())


def get_check_code_mappings() -> dict[str, list[str]]:
    db_path = _default_db_path()
    res: dict[str, list[str]] = {}
    if db_path.exists():
        try:
            conn = get_connection(db_path)
            rows = conn.execute("SELECT check_code, claim_id FROM check_code_mappings").fetchall()
            for r in rows:
                res.setdefault(r["check_code"] if isinstance(r, sqlite3.Row) else r[0], []).append(r["claim_id"] if isinstance(r, sqlite3.Row) else r[1])  # noqa: E501
        except Exception:
            pass
    return res

CHECK_CODE_TO_CLAIM_IDS = get_check_code_mappings()

@dataclass
class WiredFinding:
    check_code: str
    severity: str
    message: str
    source_auditor: str
    page_url: str = ""
    claim_id: str | None = None
    claim_status: str | None = None
    claim_confidence: str | None = None
    claim_statement: str | None = None
    claim_scope: str | None = None  # NEW: carries provenance through pipeline
    wiring_status: str = "UNMAPPED"


def _lookup_claim(claim_id: str, db_path: Path, conn: sqlite3.Connection | None = None) -> dict | None:  # noqa: E501
    """Look up a claim by ID. Returns a dict or None."""
    try:
        c = conn if conn else get_connection(db_path)
        row = c.execute(
            "SELECT claim_id, status, confidence, statement, claim_scope FROM claims WHERE claim_id = ?",
            (claim_id,)
        ).fetchone()
        if row:
            return {"claim_id": row[0], "status": row[1],
                    "confidence": row[2], "statement": row[3],
                    "claim_scope": row[4]}
    except sqlite3.OperationalError as e:
        logger.error("DB error looking up claim '%s': %s", claim_id, e)
        raise Exception("UNKNOWN_DB_ERROR") from e
    except Exception as e:
        logger.error("Unexpected error looking up claim '%s': %s", claim_id, e)
        raise


def wire_finding(
    check_code: str,
    severity: str,
    message: str,
    source_auditor: str,
    page_url: str = "",
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> WiredFinding:
    if db_path is None:
        db_path = _default_db_path()

    finding = WiredFinding(
        check_code=check_code,
        severity=severity,
        message=message,
        source_auditor=source_auditor,
        page_url=page_url,
    )

    c = conn if conn else get_connection(db_path)
    rows = c.execute("SELECT claim_id FROM check_code_mappings WHERE check_code = ?", (check_code,)).fetchall()  # noqa: E501
    candidate_ids = [r[0] for r in rows]

    if not candidate_ids:
        finding.wiring_status = "UNMAPPED"
        return finding

    for cid in candidate_ids:
        claim = _lookup_claim(cid, db_path, conn)
        if claim:
            # Wire all valid claims regardless of scope.
            # The is_client_evidence gate was here before but blocked every
            # pre-seeded claim on fresh deploy. Scope is carried forward so
            # the presentation layer (orchestrator, report) can label tiers.
            finding.claim_id = claim["claim_id"]
            finding.claim_status = claim["status"]
            finding.claim_confidence = claim["confidence"]
            finding.claim_statement = claim["statement"]
            finding.claim_scope = claim.get("claim_scope")
            finding.wiring_status = "WIRED"
            return finding

    finding.claim_id = candidate_ids[0]
    finding.wiring_status = "CLAIM_NOT_FOUND"
    return finding


def wire_findings_batch(
    findings: list[dict],
    source_auditor: str,
    page_url: str = "",
    db_path: Path | None = None,
) -> list[WiredFinding]:
    if db_path is None:
        db_path = _default_db_path()
        
    wired = []
    conn = get_connection(db_path)
    for f in findings:
        code = f.get("code") or f.get("check_code", "UNKNOWN")
        wired.append(wire_finding(
            check_code=code,
            severity=f.get("severity", "info"),
            message=f.get("message", ""),
            source_auditor=source_auditor,
            page_url=page_url,
            db_path=db_path,
            conn=conn,
        ))
    return wired


def format_wired_report(wired_findings: list[WiredFinding]) -> str:
    lines = ["Wired Findings Report", "=" * 60, ""]

    by_status = {"WIRED": [], "CLAIM_NOT_FOUND": [], "UNMAPPED": []}
    for f in wired_findings:
        by_status.setdefault(f.wiring_status, []).append(f)

    lines.append(
        f"Total: {len(wired_findings)} | "
        f"Wired: {len(by_status['WIRED'])} | "
        f"Claim not found: {len(by_status['CLAIM_NOT_FOUND'])} | "
        f"Unmapped: {len(by_status['UNMAPPED'])}"
    )
    lines.append("")

    for f in wired_findings:
        sev_icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(f.severity, "?")
        lines.append(f"{sev_icon} [{f.check_code}] {f.message}")

        if f.wiring_status == "WIRED":
            lines.append(
                f"   → Claim {f.claim_id} "
                f"(status: {f.claim_status}, confidence: {f.claim_confidence})"
            )
        elif f.wiring_status == "CLAIM_NOT_FOUND":
            lines.append(f"   → Claim {f.claim_id} mapped but not in DB")
        else:
            lines.append("   → No claim mapping for this check code")

        lines.append("")

    return "\n".join(lines)
