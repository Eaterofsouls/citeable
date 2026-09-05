# areos/kb/router.py
#
# Knowledge Router — deterministic routing + 3-tier BYOK-native RAG.
#
# D-005: Deterministic routing via kb_check_code_map table.
# D-010: Three RAG tiers (Primary, Enrichment, Cross-Phase).
# D-011: Cosine similarity thresholds (0.82 primary, 0.70 enrichment).
# D-012: "Insufficient knowledge" is a valid response.
# D-014: Graceful degradation without BYOK key.

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from areos.db.connection import get_connection, get_db_path
from areos.kb.embeddings import (
    EmbeddingUnavailable,
    cosine_similarity,
    embed,
    get_active_model,
)
from areos.kb.models import (
    EvidenceRecord,
    GuidanceDetail,
    KnowledgeRecord,
    Resolution,
    SourceRecord,
)

logger = logging.getLogger(__name__)

# Confidence thresholds (D-011)
THRESHOLD_PRIMARY = 0.82
THRESHOLD_ENRICHMENT = 0.70
THRESHOLD_CROSS_PHASE = 0.75

# Model-specific calibrated thresholds (DEC-16)
MODEL_THRESHOLDS: dict[str, dict[str, float]] = {
    "text-embedding-004": {"primary": 0.82, "enrichment": 0.70, "cross_phase": 0.75},
    "text-embedding-3-small": {"primary": 0.80, "enrichment": 0.68, "cross_phase": 0.73},
    "mistral-embed": {"primary": 0.80, "enrichment": 0.68, "cross_phase": 0.73},
}

def get_thresholds_for_model(model_name: str | None = None) -> tuple[float, float, float]:
    """Return (primary, enrichment, cross_phase) thresholds calibrated for the active embedding model."""
    if model_name and model_name in MODEL_THRESHOLDS:
        t = MODEL_THRESHOLDS[model_name]
        return t["primary"], t["enrichment"], t["cross_phase"]
    return THRESHOLD_PRIMARY, THRESHOLD_ENRICHMENT, THRESHOLD_CROSS_PHASE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve(
    check_code: str,
    description: str = "",
    *,
    client_keys: dict | None = None,
    db_path: str | None = None,
) -> Resolution:
    """
    Route a finding through the Knowledge Router.

    1. Try deterministic lookup via kb_check_code_map
    2. If UNMAPPED, try RAG semantic search (if BYOK key available)
    3. Return Resolution with evidence chain

    Args:
        check_code:  The detector's check code (e.g., "CRAWLER_FULLY_BLOCKED")
        description: Human-readable finding description (used as RAG query)
        client_keys: BYOK API keys dict (from HTTP request headers)
        db_path:     Override DB path (defaults to get_db_path())
    """
    _db = db_path or get_db_path()
    conn = get_connection(_db)

    # Step 1: Deterministic lookup — walk candidate rows until finding an active record (DEC-03)
    rows = conn.execute(
        "SELECT kid, priority_score FROM kb_check_code_map WHERE check_code = ? ORDER BY priority_score DESC",
        (check_code,),
    ).fetchall()

    for row in rows:
        kid = row["kid"]
        priority = row["priority_score"]
        record = _load_record(conn, kid)
        if not record or record.status in ("archived", "deprecated"):
            if record:
                logger.warning("Check code %s candidate %s has status %s, walking next candidate...", check_code, kid, record.status)
            else:
                logger.warning("Check code %s candidate %s not found, walking next candidate...", check_code, kid)
            continue

        resolution = _build_resolution(conn, record, "DETERMINISTIC", priority)

        # RAG Enrichment (tier 2) — find related records
        resolution.enrichment = _rag_enrichment(
            record.statement, conn, client_keys, exclude_kid=kid
        )
        resolution.rag_available = len(resolution.enrichment) > 0
        return resolution

    # Step 2: RAG Primary (tier 1) — semantic search for novel findings
    active_model = get_active_model(client_keys)
    t_prim, t_enrich, t_cross = get_thresholds_for_model(active_model)
    query = f"{check_code}: {description}" if description else check_code
    candidates = _rag_search(query, conn, client_keys, threshold=t_enrich, top_k=5)

    if candidates and candidates[0]["similarity"] >= t_prim:
        best = candidates[0]
        record = _load_record(conn, best["kid"])
        if record:
            resolution = _build_resolution(conn, record, "SEMANTIC", 10)
            resolution.confidence_score = best["similarity"]
            # Also get enrichment from remaining candidates (>= THRESHOLD_ENRICHMENT)
            resolution.enrichment = candidates[1:4]
            resolution.rag_available = True
            return resolution

    # Step 3: Insufficient knowledge
    return Resolution(
        path="INSUFFICIENT",
        rag_available=_has_embeddings(conn, client_keys),
    )


def cross_phase_search(
    all_descriptions: list[str],
    *,
    client_keys: dict | None = None,
    db_path: str | None = None,
    exclude_kids: list[str] | None = None,
) -> list[dict]:
    """
    Cross-Phase Intelligence (tier 3) — find knowledge that bridges
    multiple findings across AEOG phases.

    Called AFTER all individual findings are resolved.
    """
    _db = db_path or get_db_path()
    conn = get_connection(_db)

    query = " | ".join(all_descriptions[:10])  # Cap query length
    active_model = get_active_model(client_keys)
    _, _, t_cross = get_thresholds_for_model(active_model)
    candidates = _rag_search(
        query, conn, client_keys,
        threshold=t_cross, top_k=5,
    )

    if exclude_kids:
        candidates = [c for c in candidates if c["kid"] not in exclude_kids]

    return candidates[:5]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_record(conn, kid: str) -> KnowledgeRecord | None:
    """Load a full KnowledgeRecord from the knowledge table."""
    row = conn.execute("SELECT * FROM knowledge WHERE kid = ?", (kid,)).fetchone()
    if not row:
        return None

    guidance = None
    if row["guidance_json"]:
        try:
            guidance = GuidanceDetail(**json.loads(row["guidance_json"]))
        except Exception as e:
            logger.warning("Malformed guidance_json for kid=%s: %s", row["kid"], e)
            guidance = None

    return KnowledgeRecord(
        kid=row["kid"],
        type=row["type"],
        scope=row["scope"],
        statement=row["statement"],
        context=row["context"],
        status=row["status"],
        confidence=row["confidence"] or "medium",
        support=row["support"] or "partial",
        uncertainty=row["uncertainty"],
        contradiction=row["contradiction"],
        guidance=guidance,
        aeog_phases=json.loads(row["aeog_phases"]) if row["aeog_phases"] else [],
        check_links=json.loads(row["check_links"]) if row["check_links"] else [],
        provenance=json.loads(row["provenance_json"]) if row["provenance_json"] else {},
        priority_score=row["priority_score"],
    )


def _build_resolution(
    conn, record: KnowledgeRecord, path: str, priority: int,
) -> Resolution:
    """Build a full Resolution with evidence chain from a KnowledgeRecord."""
    # Load evidence chain
    ev_rows = conn.execute(
        "SELECT * FROM kb_evidence WHERE kid = ?", (record.kid,)
    ).fetchall()
    evidence = [
        EvidenceRecord(
            eid=r["eid"], kid=r["kid"], sid=r["sid"],
            relationship=r["relationship"] or "supports",
            weight=r["weight"] or "primary",
            note=r["note"] or "",
        )
        for r in ev_rows
    ]

    # Load source citations
    source_ids = list({e.sid for e in evidence})
    sources = []
    for sid in source_ids:
        s_row = conn.execute("SELECT * FROM kb_sources WHERE sid = ?", (sid,)).fetchone()
        if s_row:
            sources.append(SourceRecord(
                sid=s_row["sid"], url=s_row["url"], title=s_row["title"],
                publisher=s_row["publisher"], authority=s_row["authority"] or "T3",
                pub_date=s_row["pub_date"], excerpt=s_row["excerpt"],
                notes=s_row["notes"],
            ))

    # Load backing facts (for GUIDANCE records with rationale)
    backing_facts = []
    if record.guidance and record.guidance.rationale:
        rationale_kid = record.guidance.rationale
        backing = _load_record(conn, rationale_kid)
        if backing:
            backing_facts.append(backing)

    # Contested check (D-019)
    is_contested = record.status == "contested"
    contested_reason = record.contradiction if is_contested else None

    # Staleness check (D-020)
    is_stale = False
    stale_since = None
    review_due = record.provenance.get("review_due")
    if review_due:
        try:
            if date.fromisoformat(review_due) < date.today():
                is_stale = True
                stale_since = review_due
        except ValueError as e:
            logger.warning("Malformed review_due date for kid=%s: %r — %s", record.kid, review_due, e)

    return Resolution(
        path=path,
        primary_kid=record.kid,
        primary_record=record,
        guidance=record.guidance,
        backing_facts=backing_facts,
        evidence_chain=evidence,
        source_citations=sources,
        priority_score=priority,
        is_contested=is_contested,
        contested_reason=contested_reason,
        is_stale=is_stale,
        stale_since=stale_since,
    )


def _rag_search(
    query: str,
    conn,
    client_keys: dict | None,
    threshold: float,
    top_k: int,
) -> list[dict]:
    """
    Embed query, compare against stored corpus vectors, return matches.

    Returns empty list if no BYOK key or no embeddings.
    """
    safe_query = query[:10000] if query else ""
    try:
        query_vector = embed(safe_query, client_keys=client_keys)
    except EmbeddingUnavailable:
        return []

    # Check dimension match
    rows = conn.execute(
        "SELECT e.kid, e.vector_json, e.model, k.statement, k.type, k.status, k.confidence "
        "FROM kb_embeddings e JOIN knowledge k ON e.kid = k.kid "
        "WHERE k.status NOT IN ('archived', 'deprecated')"
    ).fetchall()

    if not rows:
        return []

    # Verify dimension compatibility
    sample_vector = json.loads(rows[0]["vector_json"])
    if len(sample_vector) != len(query_vector):
        server_model = rows[0]["model"]
        logger.warning(
            "Embedding dimension mismatch: query=%d, corpus=%d (model=%s). "
            "Attempting server re-embed fallback.",
            len(query_vector), len(sample_vector), server_model,
        )
        try:
            query_vector = embed(safe_query, client_keys=None)
            threshold = get_thresholds_for_model(server_model)[0]
        except EmbeddingUnavailable:
            return []
        
        if len(sample_vector) != len(query_vector):
            return []

    candidates = []
    for row in rows:
        corpus_vector = json.loads(row["vector_json"])
        sim = cosine_similarity(query_vector, corpus_vector)
        if sim >= threshold:
            candidates.append({
                "kid": row["kid"],
                "similarity": round(sim, 4),
                "statement": row["statement"],
                "type": row["type"],
                "status": row["status"],
                "confidence": row["confidence"],
            })

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates[:top_k]


def _rag_enrichment(
    statement: str,
    conn,
    client_keys: dict | None,
    exclude_kid: str = "",
) -> list[dict]:
    """
    RAG Enrichment (tier 2) — find related records for a known finding.

    Uses the GUIDANCE statement as the query, returns top 3 above 0.70.
    """
    active_model = get_active_model(client_keys)
    _, t_enrich, _ = get_thresholds_for_model(active_model)
    candidates = _rag_search(
        statement, conn, client_keys,
        threshold=t_enrich, top_k=4,
    )
    # Exclude the primary record itself
    return [c for c in candidates if c["kid"] != exclude_kid][:3]


def _has_embeddings(conn, client_keys: dict | None) -> bool:
    """Check if embeddings exist AND a BYOK key is available."""
    try:
        count = conn.execute("SELECT COUNT(*) FROM kb_embeddings").fetchone()[0]
        if count == 0:
            return False
    except Exception:
        return False
    return get_active_model(client_keys) is not None
