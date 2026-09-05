# areos/api/routers/knowledge.py
#
# Knowledge API — exposes the V2 knowledge architecture via REST endpoints.
# Backward-compatible: the existing /api/v1/claims endpoint still works
# via the claims VIEW. These endpoints add richer knowledge access.

import json
import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from areos.api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# ── Response Models ───────────────────────────────────────────────────────────

class KnowledgeItem(BaseModel):
    kid: str
    type: str
    scope: Optional[str] = None
    statement: str
    context: Optional[str] = None
    status: str = "active"
    confidence: str = "medium"
    support: str = "partial"
    priority_score: Optional[int] = None
    guidance_json: Optional[str] = None
    aeog_phases: Optional[str] = None
    check_links: Optional[str] = None
    review_due: Optional[str] = None
    created_at: Optional[str] = None
    last_verified_at: Optional[str] = None


class EvidenceItem(BaseModel):
    eid: str
    kid: str
    sid: str
    relationship: str = "supports"
    weight: str = "primary"
    note: Optional[str] = None


class SourceItem(BaseModel):
    sid: str
    url: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    authority: str = "T3"


class KnowledgeDetail(BaseModel):
    """Full knowledge record with evidence chain and source citations."""
    record: KnowledgeItem
    evidence: list[EvidenceItem] = []
    sources: list[SourceItem] = []
    related_check_codes: list[str] = []


class KnowledgeListResponse(BaseModel):
    total_count: int
    records: list[KnowledgeItem]


class KBStatsResponse(BaseModel):
    knowledge_count: int
    evidence_count: int
    source_count: int
    check_code_count: int
    embedding_count: int
    embedding_model: str
    version: str
    rebuilt_at: str
    types: dict
    statuses: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=KnowledgeListResponse)
def list_knowledge(
    search_query: str | None = None,
    type: str | None = None,
    status: str | None = None,
    confidence: str | None = None,
    scope: str | None = None,
    kid: str | None = None,
    exclude_archived: bool = True,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """List knowledge records with filtering and search."""
    try:
        base = "FROM knowledge WHERE 1=1"
        params = []

        if kid:
            base += " AND kid = ?"
            params.append(kid)
        if type:
            base += " AND type = ?"
            params.append(type)
        if status:
            base += " AND status = ?"
            params.append(status)
        elif exclude_archived:
            base += " AND status NOT IN ('archived', 'deprecated')"
        if confidence:
            base += " AND confidence = ?"
            params.append(confidence)
        if scope:
            base += " AND (scope LIKE ? OR aeog_phases LIKE ?)"
            params.extend([f"%{scope}%", f"%{scope}%"])
        if search_query:
            base += " AND (statement LIKE ? OR context LIKE ? OR kid LIKE ?)"
            q = f"%{search_query}%"
            params.extend([q, q, q])

        count = conn.execute(f"SELECT count(*) {base}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * {base} ORDER BY kid LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

        records = [KnowledgeItem(**dict(r)) for r in rows]
        return KnowledgeListResponse(total_count=count, records=records)

    except Exception as e:
        logger.error("Knowledge list failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=KBStatsResponse)
def get_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Get knowledge base statistics."""
    try:
        meta = {}
        try:
            for r in conn.execute("SELECT key, value FROM kb_metrics").fetchall():
                meta[r["key"]] = r["value"]
        except sqlite3.OperationalError:
            for r in conn.execute("SELECT key, value FROM kb_meta").fetchall():
                meta[r["key"]] = r["value"]

        types = {}
        for r in conn.execute("SELECT type, count(*) c FROM knowledge GROUP BY type").fetchall():
            types[r["type"]] = r["c"]

        statuses = {}
        for r in conn.execute("SELECT status, count(*) c FROM knowledge GROUP BY status").fetchall():
            statuses[r["status"]] = r["c"]

        return KBStatsResponse(
            knowledge_count=int(meta.get("record_count", "0")),
            evidence_count=int(meta.get("evidence_count", "0")),
            source_count=int(meta.get("source_count", "0")),
            check_code_count=int(meta.get("check_code_count", "0")),
            embedding_count=int(meta.get("embedding_count", "0")),
            embedding_model=meta.get("embedding_model", ""),
            version=meta.get("version", "0"),
            rebuilt_at=meta.get("rebuilt_at", ""),
            types=types,
            statuses=statuses,
        )
    except sqlite3.OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base not built. Run: python -m areos.kb.build_kb",
        )


@router.get("/{kid}", response_model=KnowledgeDetail)
def get_knowledge_detail(
    kid: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get a single knowledge record with full evidence chain."""
    try:
        row = conn.execute("SELECT * FROM knowledge WHERE kid = ?", (kid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Knowledge record {kid} not found")

        record = KnowledgeItem(**dict(row))

        # Evidence chain
        ev_rows = conn.execute("SELECT * FROM kb_evidence WHERE kid = ?", (kid,)).fetchall()
        evidence = [EvidenceItem(**dict(r)) for r in ev_rows]

        # Sources from evidence
        source_ids = list({e.sid for e in evidence})
        sources = []
        for sid in source_ids:
            s_row = conn.execute("SELECT * FROM kb_sources WHERE sid = ?", (sid,)).fetchone()
            if s_row:
                sources.append(SourceItem(**dict(s_row)))

        # Related check codes
        cc_rows = conn.execute(
            "SELECT check_code FROM kb_check_code_map WHERE kid = ?", (kid,)
        ).fetchall()
        check_codes = [r["check_code"] for r in cc_rows]

        return KnowledgeDetail(
            record=record,
            evidence=evidence,
            sources=sources,
            related_check_codes=check_codes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Knowledge detail failed for %s: %s", kid, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{kid}/evidence")
def get_evidence_chain(
    kid: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get the evidence chain for a knowledge record."""
    ev_rows = conn.execute("SELECT * FROM kb_evidence WHERE kid = ?", (kid,)).fetchall()
    if not ev_rows:
        return {"evidence": [], "sources": []}

    evidence = [dict(r) for r in ev_rows]

    source_ids = list({e["sid"] for e in evidence})
    placeholders = ",".join("?" * len(source_ids))
    s_rows = conn.execute(
        f"SELECT * FROM kb_sources WHERE sid IN ({placeholders})", source_ids
    ).fetchall()
    sources = [dict(r) for r in s_rows]

    return {"evidence": evidence, "sources": sources}


@router.get("/check-code/{check_code}")
def get_by_check_code(
    check_code: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Look up knowledge records mapped to a check code."""
    rows = conn.execute(
        "SELECT m.kid, m.priority_score, k.type, k.statement, k.status, k.confidence "
        "FROM kb_check_code_map m JOIN knowledge k ON m.kid = k.kid "
        "WHERE m.check_code = ?",
        (check_code,),
    ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No knowledge mapped to {check_code}")

    return {
        "check_code": check_code,
        "records": [dict(r) for r in rows],
    }
