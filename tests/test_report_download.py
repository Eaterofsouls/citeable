"""
tests/test_report_download.py

Tests for Markdown report and remediation plan download endpoints:
- GET /api/v1/audit/runs/{run_id}/report/download
- GET /api/v1/audit/runs/{run_id}/remediation/download
"""

import json
import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_report_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from areos.api.main import app
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as
from areos.db.migrate_audit_tables import migrate
from areos.kb import build_kb


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_reports.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)
    build_kb.build(test_db)
    return TestClient(app)


def _seed_run(run_id: str, target_domain: str = "example.com") -> None:
    conn = get_connection(get_db_path())
    with write_as(conn, actor="test", reason="seed_audit_run"):
        conn.execute(
            """
            INSERT INTO audit_runs (
                run_id, target_domain, run_date, audited_stages, automated_findings, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                target_domain,
                "2026-09-27T12:00:00Z",
                json.dumps(["AP-01", "AP-02"]),
                json.dumps([
                    {
                        "code": "CRAWLER_PARTIAL",
                        "severity": "warning",
                        "message": "Some crawlers restricted",
                    }
                ]),
                "automated_complete",
            ),
        )


def test_download_final_report_success(client):
    run_id = "run_report_dl_1"
    _seed_run(run_id, "download-test.com")

    # Call download endpoint
    res = client.get(f"/api/v1/audit/runs/{run_id}/report/download")
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    expected_filename = f'attachment; filename="areos-report-{run_id}.md"'
    assert res.headers.get("content-disposition") == expected_filename
    assert len(res.text) > 0
    assert "download-test.com" in res.text

    # Compare with json endpoint content
    json_res = client.get(f"/api/v1/audit/runs/{run_id}/report")
    assert json_res.status_code == 200
    assert res.text == json_res.json()["report_markdown"]


def test_download_final_report_not_found(client):
    res = client.get("/api/v1/audit/runs/nonexistent_run_id/report/download")
    assert res.status_code == 404
    assert res.json() == {"detail": "Audit run not found"}

    # Must match behavior of get_final_report exactly
    json_res = client.get("/api/v1/audit/runs/nonexistent_run_id/report")
    assert json_res.status_code == 404
    assert json_res.json() == res.json()


def test_download_remediation_plan_success(client):
    run_id = "run_remediation_dl_1"
    _seed_run(run_id, "remediation-test.com")

    # Call download endpoint
    res = client.get(f"/api/v1/audit/runs/{run_id}/remediation/download")
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    expected_filename = f'attachment; filename="areos-remediation-{run_id}.md"'
    assert res.headers.get("content-disposition") == expected_filename
    assert len(res.text) > 0

    # Compare with json endpoint content
    json_res = client.get(f"/api/v1/audit/runs/{run_id}/remediation")
    assert json_res.status_code == 200
    assert res.text == json_res.json()["plan_markdown"]


def test_download_remediation_plan_not_found(client):
    res = client.get("/api/v1/audit/runs/nonexistent_run_id/remediation/download")
    assert res.status_code == 404
    assert res.json() == {"detail": "Audit run not found"}

    # Must match behavior of get_remediation_plan exactly
    json_res = client.get("/api/v1/audit/runs/nonexistent_run_id/remediation")
    assert json_res.status_code == 404
    assert json_res.json() == res.json()
