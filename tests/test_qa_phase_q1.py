# tests/test_qa_phase_q1.py
#
# QA Remediation Phase Q1 Test Suite (Core Unblocking Fixes)
# Tests: QA-C01, QA-C02, QA-C03, QA-C05, QA-C06

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from starlette.testclient import TestClient
from areos.api.main import app
from areos.api.routers.audit import _ip_buckets
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as


@pytest.fixture(autouse=True)
def reset_rate_limits():
    _ip_buckets.clear()
    yield
    _ip_buckets.clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_q1.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    from areos.db.migrate_audit_tables import migrate
    migrate(test_db)
    return TestClient(app)


class TestQ1SynthesizeEndpoint:
    """Test synthesis endpoint fixes for QA-C03 (manual_verdicts_context NameError)."""

    def test_synthesize_endpoint_returns_200(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q1_run_01"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([{"code": "CRAWLER_FULLY_BLOCKED", "severity": "error", "message": "Blocked"}]), "automated_complete")
            )
            conn.execute(
                "INSERT INTO manual_observations (run_id, question_id, structured_data, severity, diagnosis_text) VALUES (?,?,?,?,?)",
                (run_id, "B2_CONTENT_ANSWERABILITY", json.dumps({"maps_to_claims": ["C052"]}), "warning", "Content missing lead definition")
            )

        with patch("areos.llm.synthesis_pipeline.run_llm_synthesis") as mock_synth:
            mock_synth.return_value = {
                "llm_synthesis_used": True,
                "provider_used": "mock_llm",
                "narrative": "## Executive Summary\nBrand has good structure.",
            }
            res = client.post(
                f"/api/v1/audit/runs/{run_id}/synthesize",
                headers={"X-API-Key": "test_qa_token", "x-api-key-groq": "gsk_test_key_123"}
            )
            assert res.status_code == 200, res.text
            data = res.json()
            assert data.get("manual_verdicts_merged") == 1
            assert "Executive Summary" in data.get("narrative", "")

    def test_synthesize_endpoint_with_empty_observations(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q1_run_empty_obs"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )

        with patch("areos.llm.synthesis_pipeline.run_llm_synthesis") as mock_synth:
            mock_synth.return_value = {
                "llm_synthesis_used": True,
                "provider_used": "mock_llm",
                "narrative": "Report with 0 observations",
            }
            res = client.post(
                f"/api/v1/audit/runs/{run_id}/synthesize",
                headers={"X-API-Key": "test_qa_token", "x-api-key-groq": "gsk_test_key_123"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data.get("manual_verdicts_merged") == 0

    def test_synthesize_endpoint_with_legacy_verdicts(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q1_run_legacy_verdicts"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )
            conn.execute(
                "INSERT INTO manual_verdicts (card_id, page_url, verdict, severity, notes, run_id) VALUES (?,?,?,?,?,?)",
                ("C052", "https://example.com", "fail", "error", "Legacy verdict note", run_id)
            )

        with patch("areos.llm.synthesis_pipeline.run_llm_synthesis") as mock_synth:
            mock_synth.return_value = {
                "llm_synthesis_used": True,
                "provider_used": "mock_llm",
                "narrative": "Report with legacy fallback",
            }
            res = client.post(
                f"/api/v1/audit/runs/{run_id}/synthesize",
                headers={"X-API-Key": "test_qa_token", "x-api-key-groq": "gsk_test_key_123"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data.get("manual_verdicts_merged") == 1

    def test_synthesize_endpoint_malformed_run_id(self, client):
        res = client.post(
            "/api/v1/audit/runs/non_existent_random_id_9999/synthesize",
            headers={"X-API-Key": "test_qa_token", "x-api-key-groq": "gsk_test_key"}
        )
        assert res.status_code == 404


class TestQ1FullReportEndpoint:
    """Test full report endpoint fixes for QA-C05 (non-existent audit_findings table)."""

    def test_full_report_endpoint_returns_findings(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q1_full_report_01"
        sample_findings = [
            {"code": "ROBOTS_UNVERIFIABLE", "severity": "warning", "message": "Robots unreachable"},
            {"code": "CONTENT_STALE", "severity": "error", "message": "Modified date too old"}
        ]
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01", "AP-03"]), json.dumps(sample_findings), "automated_complete")
            )

        res = client.get(f"/api/v1/audit/runs/{run_id}/full-report")
        assert res.status_code == 200
        data = res.json()
        assert len(data["layer_1_access"]["automated_findings"]) == 1
        assert data["layer_1_access"]["automated_findings"][0]["code"] == "ROBOTS_UNVERIFIABLE"
        assert len(data["layer_2_content_schema"]["automated_findings"]) == 1
        assert data["layer_2_content_schema"]["automated_findings"][0]["code"] == "CONTENT_STALE"

    def test_full_report_endpoint_empty_run(self, client):
        db_path = get_db_path()
        conn = get_connection(db_path)
        run_id = "test_q1_empty_run"
        with write_as(conn, actor="test", reason="seed run"):
            conn.execute(
                "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status) VALUES (?,?,?,?,?,?)",
                (run_id, "example.com", "2026-09-01", json.dumps(["AP-01"]), json.dumps([]), "automated_complete")
            )

        res = client.get(f"/api/v1/audit/runs/{run_id}/full-report")
        assert res.status_code == 200
        data = res.json()
        assert data["layer_1_access"]["automated_findings"] == []
        assert data["layer_2_content_schema"]["automated_findings"] == []

    def test_full_report_endpoint_missing_run(self, client):
        res = client.get("/api/v1/audit/runs/unknown_run_uuid_1234/full-report")
        assert res.status_code == 404


class TestQ1FrontendSanityGuards:
    """Verify frontend code sanity for QA-C01, QA-C02, QA-C06."""

    def test_enrichCodeSnippet_removed_no_crash(self):
        ui_dir = Path(__file__).resolve().parents[1] / "areos" / "ui"
        for js_file in ui_dir.glob("*.js"):
            content = js_file.read_text(encoding="utf-8")
            assert "enrichCodeSnippet" not in content, f"Found undefined enrichCodeSnippet in {js_file.name}"

    def test_routes_array_defined_in_nav(self):
        nav_file = Path(__file__).resolve().parents[1] / "areos" / "ui" / "nav.js"
        content = nav_file.read_text(encoding="utf-8")
        assert "const ROUTES = [" in content
        assert "Audit Studio" in content

    def test_audit_result_wired_to_context(self):
        studio_file = Path(__file__).resolve().parents[1] / "areos" / "ui" / "studio.js"
        content = studio_file.read_text(encoding="utf-8")
        assert "window.AreosContext.auditResult = data;" in content
