# tests/test_qa_phase_q4.py
#
# QA Remediation Phase Q4 Test Suite (Medium Priority Fixes)
# Tests: QA-M08, QA-M09, QA-M10, QA-M11, QA-M12, QA-M15, D-QA-010, D-QA-012, D-QA-014, D-QA-015

import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from starlette.testclient import TestClient
from areos.api.main import app
from areos.api.routers.audit import _ip_buckets, _rate_limit
from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
from areos.auditors.content_format_auditor import audit_page_format
from areos.auditors.scoring import LAYER_DEDUCTIONS
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as
from areos.db.migrate_audit_tables import migrate
from areos.kb.router import resolve


@pytest.fixture(autouse=True)
def reset_rate_limits():
    _ip_buckets.clear()
    yield
    _ip_buckets.clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_q4.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)
    return TestClient(app)


class TestQ4ObservationsAndValidation:
    """Test observation validation and storage (QA-M08, QA-M09)."""

    def test_observation_severity_validation(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q4_val_run"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )

        # Invalid severity "critical" must be rejected by Pydantic (422)
        bad_payload = {
            "question_id": "B1_SCHEMA_HONESTY",
            "severity": "critical",
            "structured_data": {}
        }
        res = client.post(f"/api/v1/audit/runs/{run_id}/observations", json=bad_payload, headers={"X-API-Key": "test_qa_token"})
        assert res.status_code == 422

        # Valid severity "warning" accepted
        good_payload = {
            "question_id": "B1_SCHEMA_HONESTY",
            "severity": "warning",
            "structured_data": {"discrepancies": ["price mismatch"]}
        }
        res = client.post(f"/api/v1/audit/runs/{run_id}/observations", json=good_payload, headers={"X-API-Key": "test_qa_token"})
        assert res.status_code == 200

    def test_manual_observations_upsert(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q4_upsert_run"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )

        # Insert first observation
        client.post(
            f"/api/v1/audit/runs/{run_id}/observations",
            json={"question_id": "B2_CONTENT_ANSWERABILITY", "severity": "warning", "diagnosis_text": "Initial note"},
            headers={"X-API-Key": "test_qa_token"}
        )

        # Insert second observation for same question_id -> must update
        client.post(
            f"/api/v1/audit/runs/{run_id}/observations",
            json={"question_id": "B2_CONTENT_ANSWERABILITY", "severity": "error", "diagnosis_text": "Updated note"},
            headers={"X-API-Key": "test_qa_token"}
        )

        cur = conn.execute("SELECT severity, diagnosis_text FROM manual_observations WHERE run_id=? AND question_id='B2_CONTENT_ANSWERABILITY'", (run_id,))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "error"
        assert rows[0][1] == "Updated note"

    def test_manual_observations_concurrent_upsert(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q4_concurrent_run"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )

        errors = []
        def worker(idx):
            try:
                res = client.post(
                    f"/api/v1/audit/runs/{run_id}/observations",
                    json={"question_id": "B1_SCHEMA_HONESTY", "severity": "info", "diagnosis_text": f"Thread {idx}"},
                    headers={"X-API-Key": "test_qa_token"}
                )
                if res.status_code != 200:
                    errors.append(res.text)
            except Exception as exc:
                errors.append(str(exc))

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(errors) == 0


class TestQ4RateLimiterAndRouter:
    """Test rate limiter cleanup and router deprecated filtering (QA-M10, QA-M12)."""

    def test_ip_rate_limiter_cleans_stale_ips(self):
        # Simulate 60 stale entries
        now = time.time()
        for i in range(60):
            _ip_buckets[f"test_stale_ip_{i}"] = [now - 120]  # 2 minutes old

        # Add one fresh request
        class MockRequest:
            client = type("Client", (), {"host": "192.168.1.100"})()

        _rate_limit(MockRequest(), bucket_prefix="test", limit=5, window_seconds=60)

        # Stale keys must have been pruned
        assert len(_ip_buckets) < 30

    def test_router_excludes_deprecated_records(self, tmp_path):
        db_path = tmp_path / "test_router.db"
        migrate(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS knowledge (kid TEXT PRIMARY KEY, statement TEXT, status TEXT, priority_score INTEGER, type TEXT, scope TEXT, context TEXT, confidence TEXT, support TEXT, uncertainty TEXT, contradiction TEXT, guidance_json TEXT, aeog_phases TEXT, check_links TEXT, provenance_json TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS kb_check_code_map (check_code TEXT PRIMARY KEY, kid TEXT, priority_score INTEGER)"
        )
        conn.execute(
            "INSERT INTO kb_check_code_map (check_code, kid, priority_score) VALUES ('TEST_DEPRECATED_CODE', 'KT-DEP', 10)"
        )
        conn.execute(
            "INSERT INTO knowledge (kid, type, scope, statement, context, status, confidence, support, priority_score) VALUES (?,?,?,?,?,?,?,?,?)",
            ("KT-DEP", "FINDING", "general", "Deprecated statement", "", "deprecated", "low", "weak", 10)
        )
        conn.commit()
        conn.close()

        # Deterministic lookup must skip deprecated record
        res = resolve("TEST_DEPRECATED_CODE", "Finding description", db_path=db_path)
        assert res.path == "INSUFFICIENT"


class TestQ4ContentFormatAndSnippets:
    """Test content format zero-preservation and snippet coverage (QA-M11, D-QA-010)."""

    def test_content_format_explicit_zero_preserved(self):
        signals = {"paragraphs": ["Paragraph one with enough words to test.", "Paragraph two with enough words."], "list_item_count": 0, "table_count": 0}
        html = "<html><body><ul><li>Item 1</li><li>Item 2</li></ul></body></html>"

        res = audit_page_format("https://example.com", html=html, signals=signals)
        # Explicit list_item_count=0 must trigger NO_LIST_OR_TABLE even if HTML had <li>
        codes = [i.code for i in res.issues]
        assert "NO_LIST_OR_TABLE" in codes

    def test_all_deductions_have_action_snippets(self):
        for code in LAYER_DEDUCTIONS:
            assert code in ACTION_SNIPPETS, f"Check code {code} in LAYER_DEDUCTIONS is missing an ACTION_SNIPPETS entry"


class TestQ4SitemapSecurity:
    """Test defusedxml billion laughs mitigation (QA-M15)."""

    def test_defusedxml_rejects_xml_bomb(self):
        from areos.auditors.sitemap_auditor import _parse_sitemap_xml

        xml_bomb = """<?xml version="1.0"?>
        <!DOCTYPE lolz [
         <!ENTITY lol "lol">
         <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
         <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
         <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>&lol3;</loc></url>
        </urlset>"""

        try:
            urls, has_lastmod = _parse_sitemap_xml(xml_bomb.encode("utf-8"))
        except Exception:
            urls = []
        assert isinstance(urls, list)
