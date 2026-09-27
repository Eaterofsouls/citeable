import json
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from starlette.testclient import TestClient
from areos.api.main import app
from areos.api.routers.audit import _ip_buckets
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as
from areos.db.migrate_audit_tables import migrate


@pytest.fixture(autouse=True)
def reset_rate_limits():
    _ip_buckets.clear()
    yield
    _ip_buckets.clear()


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_verdicts.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)
    return TestClient(app)


def test_create_audit_run_returns_run_token(client):
    """POST /api/v1/audit/runs generates and returns run_token, and persists it."""
    payload = {
        "target_domain": "example.com",
        "audited_stages": ["AP-01"],
        "automated_findings": [],
    }
    res = client.post("/api/v1/audit/runs", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert "run_token" in data
    run_id = data["run_id"]
    run_token = data["run_token"]
    assert len(run_token) >= 20

    # Verify persisted in database
    conn = get_connection(get_db_path())
    row = conn.execute("SELECT run_token FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    assert row is not None
    assert row["run_token"] == run_token


def test_submit_verdict_missing_token_returns_401_and_no_row_written(client):
    """POST /audit/runs/{run_id}/verdicts without token returns 401 and writes nothing."""
    conn = get_connection(get_db_path())
    run_id = "run_auth_neg_1"
    token = "secret_token_123"
    with write_as(conn, actor="test", reason="seed"):
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, run_token) VALUES (?,?,?,?,?,?,?)",
            (run_id, "example.com", "2026-09-27", "[]", "[]", "automated_complete", token),
        )

    payload = {
        "card_id": "C050",
        "page_url": "https://example.com",
        "verdict": "pass",
        "severity": "info",
        "notes": "Looks fine",
    }
    res = client.post(f"/api/v1/audit/runs/{run_id}/verdicts", json=payload)
    assert res.status_code == 401

    rows = conn.execute("SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)).fetchall()
    assert len(rows) == 0


def test_submit_verdict_wrong_token_returns_403_and_no_row_written(client):
    """POST /audit/runs/{run_id}/verdicts with wrong token returns 403 and writes nothing."""
    conn = get_connection(get_db_path())
    run_id = "run_auth_neg_2"
    token = "correct_token_xyz"
    with write_as(conn, actor="test", reason="seed"):
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, run_token) VALUES (?,?,?,?,?,?,?)",
            (run_id, "example.com", "2026-09-27", "[]", "[]", "automated_complete", token),
        )

    payload = {
        "card_id": "C050",
        "page_url": "https://example.com",
        "verdict": "fail",
        "severity": "error",
        "notes": "Wrong token test",
    }
    # Wrong header
    res_hdr = client.post(
        f"/api/v1/audit/runs/{run_id}/verdicts",
        json=payload,
        headers={"X-Run-Token": "bad_token_abc"},
    )
    assert res_hdr.status_code == 403

    # Wrong query param
    res_qry = client.post(
        f"/api/v1/audit/runs/{run_id}/verdicts?token=wrong_token",
        json=payload,
    )
    assert res_qry.status_code == 403

    rows = conn.execute("SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)).fetchall()
    assert len(rows) == 0


def test_submit_verdict_correct_token_header_succeeds(client):
    """POST /audit/runs/{run_id}/verdicts with valid X-Run-Token header returns 200 and writes verdict."""
    conn = get_connection(get_db_path())
    run_id = "run_auth_pos_hdr"
    token = "valid_token_789"
    with write_as(conn, actor="test", reason="seed"):
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, run_token) VALUES (?,?,?,?,?,?,?)",
            (run_id, "example.com", "2026-09-27", "[]", "[]", "automated_complete", token),
        )

    payload = {
        "card_id": "C051",
        "page_url": "https://example.com/about",
        "verdict": "pass",
        "severity": "info",
        "notes": "Verified good",
    }
    res = client.post(
        f"/api/v1/audit/runs/{run_id}/verdicts",
        json=payload,
        headers={"X-Run-Token": token},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "run_id": run_id, "card_id": "C051"}

    rows = conn.execute("SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["card_id"] == "C051"
    assert rows[0]["verdict"] == "pass"

    run_row = conn.execute("SELECT status FROM audit_runs WHERE run_id = ?", (run_id,)).fetchone()
    assert run_row["status"] == "in_review"


def test_submit_verdict_correct_token_query_param_succeeds(client):
    """POST /audit/runs/{run_id}/verdicts with valid query param token succeeds."""
    conn = get_connection(get_db_path())
    run_id = "run_auth_pos_qry"
    token = "valid_token_query_456"
    with write_as(conn, actor="test", reason="seed"):
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, automated_findings, status, run_token) VALUES (?,?,?,?,?,?,?)",
            (run_id, "example.com", "2026-09-27", "[]", "[]", "automated_complete", token),
        )

    payload = {
        "card_id": "C052",
        "page_url": "https://example.com/contact",
        "verdict": "warn",
        "severity": "warning",
        "notes": "Warning recorded",
    }
    res = client.post(
        f"/api/v1/audit/runs/{run_id}/verdicts?token={token}",
        json=payload,
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "run_id": run_id, "card_id": "C052"}

    rows = conn.execute("SELECT * FROM manual_verdicts WHERE run_id = ?", (run_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["card_id"] == "C052"
