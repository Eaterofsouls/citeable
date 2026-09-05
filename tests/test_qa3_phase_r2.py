import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from areos.kb.build_kb import parse_jsonl
from areos.auditors.scoring import LAYER_DEDUCTIONS
from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
from areos.db.connection import get_connection, get_db_path
from areos.kb.router import _rag_search


def test_missing_check_codes_mapped_in_json():
    """Verify all 8 previously unmapped codes exist in check_code_to_knowledge_map.json."""
    with open("areos/kb/check_code_to_knowledge_map.json", "r", encoding="utf-8") as f:
        cc_map = json.load(f)
    
    expected_codes = [
        "MULTI_PAGE_SCHEMA_GAPS",
        "MULTI_PAGE_THIN_CONTENT",
        "NEAR_DUPLICATE_PAGES",
        "COMPETITOR_SCHEMA_ADVANTAGE",
        "COMPETITOR_CONTENT_ADVANTAGE",
        "JS_CRITICAL_CONTENT_GATED",
        "CLOAKING_FETCH_FAILED",
        "PAGE_FETCH_FAILED",
    ]
    for code in expected_codes:
        assert code in cc_map, f"Missing check code in map: {code}"
        assert cc_map[code].get("guidance_record") is not None


def test_no_dangling_kt_records_in_map():
    """Verify every guidance and backing record KID in check map exists in knowledge.jsonl."""
    knowledge = parse_jsonl(Path("areos/kb/corpus/knowledge.jsonl"))
    valid_kids = {k["kid"] for k in knowledge}

    with open("areos/kb/check_code_to_knowledge_map.json", "r", encoding="utf-8") as f:
        cc_map = json.load(f)

    for code, entry in cc_map.items():
        g = entry.get("guidance_record")
        if g:
            assert g in valid_kids, f"Dangling guidance KID in {code}: {g}"
        for b in entry.get("backing_records", []):
            assert b in valid_kids, f"Dangling backing KID in {code}: {b}"


def test_layer_deductions_coverage_complete():
    """Verify all newly added auditor check codes exist in LAYER_DEDUCTIONS."""
    expected_codes = [
        "MULTI_PAGE_SCHEMA_GAPS",
        "MULTI_PAGE_THIN_CONTENT",
        "NEAR_DUPLICATE_PAGES",
        "COMPETITOR_SCHEMA_ADVANTAGE",
        "COMPETITOR_CONTENT_ADVANTAGE",
        "JS_CRITICAL_CONTENT_GATED",
        "CLOAKING_FETCH_FAILED",
        "PAGE_FETCH_FAILED",
    ]
    for code in expected_codes:
        assert code in LAYER_DEDUCTIONS, f"Missing {code} in LAYER_DEDUCTIONS"
        layer, pts = LAYER_DEDUCTIONS[code]
        assert layer in ("access", "schema", "content", "citation", "authority")
        assert pts > 0


def test_action_snippets_coverage_complete():
    """Verify all newly added auditor check codes exist in ACTION_SNIPPETS."""
    expected_codes = [
        "MULTI_PAGE_SCHEMA_GAPS",
        "MULTI_PAGE_THIN_CONTENT",
        "NEAR_DUPLICATE_PAGES",
        "COMPETITOR_SCHEMA_ADVANTAGE",
        "COMPETITOR_CONTENT_ADVANTAGE",
        "JS_CRITICAL_CONTENT_GATED",
        "CLOAKING_FETCH_FAILED",
        "PAGE_FETCH_FAILED",
    ]
    for code in expected_codes:
        assert code in ACTION_SNIPPETS, f"Missing {code} in ACTION_SNIPPETS"
        assert len(ACTION_SNIPPETS[code]) > 10


def test_kb_meta_schema_unification():
    """Verify kb_meta table contains structured columns."""
    conn = get_connection(get_db_path())
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(kb_meta)").fetchall()]
    assert "id" in cols
    assert "kb_version" in cols
    assert "last_updated" in cols
    assert "total_claims" in cols
    assert "updated_by" in cols


def test_kb_metrics_table_created():
    """Verify kb_metrics table holds key-value pairs."""
    conn = get_connection(get_db_path())
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(kb_metrics)").fetchall()]
    assert "key" in cols
    assert "value" in cols
    row = conn.execute("SELECT value FROM kb_metrics WHERE key = 'record_count'").fetchone()
    assert row is not None
    assert int(row["value"]) > 0


def test_rag_search_query_truncation_50k():
    """Verify _rag_search truncates query strings longer than 10,000 characters."""
    conn = get_connection(get_db_path())
    long_query = "apple " * 5000  # 30,000 characters

    with patch("areos.kb.router.embed", return_value=[0.1] * 768) as mock_embed:
        _rag_search(long_query, conn, client_keys=None, threshold=0.70, top_k=5)
        mock_embed.assert_called_once()
        passed_query = mock_embed.call_args[0][0]
        assert len(passed_query) <= 10000


def test_evidence_sources_orphan_check():
    """Verify 100% of records in evidence.jsonl and sources.jsonl link to valid parents."""
    knowledge = parse_jsonl(Path("areos/kb/corpus/knowledge.jsonl"))
    kids = {k["kid"] for k in knowledge}

    evidence = parse_jsonl(Path("areos/kb/corpus/evidence.jsonl"))
    sources = parse_jsonl(Path("areos/kb/corpus/sources.jsonl"))
    sids = {s["sid"] for s in sources}

    for e in evidence:
        kid = e.get("kid")
        if kid:
            assert kid in kids, f"Evidence {e['eid']} references non-existent kid {kid}"
        sid = e.get("sid")
        if sid:
            assert sid in sids, f"Evidence {e['eid']} references non-existent sid {sid}"
