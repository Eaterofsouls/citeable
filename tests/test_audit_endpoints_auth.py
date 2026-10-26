"""
tests/test_audit_endpoints_auth.py
==================================
WP-0.1: Test authentication coverage across audit-read and reports endpoints:
- GET /api/v1/audit/runs (admin token required)
- GET /api/v1/audit/runs/{run_id} (run_token required)
- GET /api/v1/audit/runs/{run_id}/full (run_token required)
- GET /api/v1/audit/runs/{run_id}/report (run_token required)
- GET /api/v1/audit/runs/{run_id}/report/download (run_token required)
- GET /api/v1/audit/runs/{run_id}/remediation (run_token required)
- GET /api/v1/audit/runs/{run_id}/remediation/download (run_token required)
"""

import json
import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from areos.api.dependencies import _API_TOKEN
from areos.api.main import app
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as
from areos.db.migrate_audit_tables import migrate
from areos.kb import build_kb


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_auth_endpoints.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)
    build_kb.build(test_db)
    return TestClient(app)


def _seed_run(run_id: str, token: str = "secret_run_token_999") -> None:
    conn = get_connection(get_db_path())
    with write_as(conn, actor="test", reason="seed_run"):
        conn.execute(
            """
            INSERT INTO audit_runs (
                run_id, target_domain, run_date, audited_stages, automated_findings, status, run_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "authtest.com",
                "2026-10-25T12:00:00Z",
                json.dumps(["AP-01"]),
                json.dumps([]),
                "automated_complete",
                token,
            ),
        )


def test_list_runs_requires_admin_token(client):
    """GET /api/v1/audit/runs requires admin Bearer token."""
    # Unauthenticated
    res = client.get("/api/v1/audit/runs")
    assert res.status_code == 401

    # Invalid admin token
    res = client.get("/api/v1/audit/runs", headers={"Authorization": "Bearer wrong_token"})
    assert res.status_code == 401

    # Valid admin token
    res = client.get("/api/v1/audit/runs", headers={"Authorization": f"Bearer {_API_TOKEN}"})
    assert res.status_code == 200
    assert "runs" in res.json()


def test_get_run_detail_auth(client):
    """GET /api/v1/audit/runs/{run_id} requires valid run_token."""
    run_id = "run_detail_auth_1"
    token = "tok_detail_abc"
    _seed_run(run_id, token)

    # 401 without token
    res = client.get(f"/api/v1/audit/runs/{run_id}")
    assert res.status_code == 401

    # 403 with wrong token
    res = client.get(f"/api/v1/audit/runs/{run_id}", headers={"X-Run-Token": "bad_token"})
    assert res.status_code == 403

    # 200 with X-Run-Token header
    res = client.get(f"/api/v1/audit/runs/{run_id}", headers={"X-Run-Token": token})
    assert res.status_code == 200
    assert res.json()["run"]["run_id"] == run_id

    # 200 with ?token= query param
    res = client.get(f"/api/v1/audit/runs/{run_id}", params={"token": token})
    assert res.status_code == 200

    # 200 with ?run_token= query param
    res = client.get(f"/api/v1/audit/runs/{run_id}", params={"run_token": token})
    assert res.status_code == 200


def test_get_run_full_auth(client):
    """GET /api/v1/audit/runs/{run_id}/full requires valid run_token."""
    run_id = "run_full_auth_1"
    token = "tok_full_xyz"
    _seed_run(run_id, token)

    # 401 without token
    res = client.get(f"/api/v1/audit/runs/{run_id}/full")
    assert res.status_code == 401

    # 403 with wrong token
    res = client.get(f"/api/v1/audit/runs/{run_id}/full", headers={"X-Run-Token": "wrong"})
    assert res.status_code == 403

    # 200 with valid token
    res = client.get(f"/api/v1/audit/runs/{run_id}/full", headers={"X-Run-Token": token})
    assert res.status_code == 200
    assert res.json()["run_id"] == run_id


def test_reports_endpoints_auth(client):
    """All reports endpoints reject without token, reject wrong token, succeed with token."""
    run_id = "run_reports_auth_1"
    token = "tok_report_456"
    _seed_run(run_id, token)

    endpoints = [
        f"/api/v1/audit/runs/{run_id}/report",
        f"/api/v1/audit/runs/{run_id}/report/download",
        f"/api/v1/audit/runs/{run_id}/remediation",
        f"/api/v1/audit/runs/{run_id}/remediation/download",
    ]

    for ep in endpoints:
        # 401 missing
        r_unauth = client.get(ep)
        assert r_unauth.status_code == 401, f"Expected 401 on {ep}"

        # 403 wrong
        r_wrong = client.get(ep, headers={"X-Run-Token": "invalid_tok"})
        assert r_wrong.status_code == 403, f"Expected 403 on {ep}"

        # 200 valid
        r_ok = client.get(ep, headers={"X-Run-Token": token})
        assert r_ok.status_code == 200, f"Expected 200 on {ep}"
