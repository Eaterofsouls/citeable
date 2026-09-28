import json, os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")
from starlette.testclient import TestClient
from areos.api.main import app
from areos.api.routers.audit import _parse_score_detail
from areos.auditors.scoring import compute_layered_score
from areos.db.connection import get_connection, get_db_path
from areos.db.context import write_as
from areos.db.migrate_audit_tables import migrate

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "score_detail.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(db))
    monkeypatch.setenv("AREOS_DB_PATH", str(db))
    migrate(db)
    return TestClient(app)

def _insert_run(run_id, detail_json):
    conn = get_connection(get_db_path())
    with write_as(conn, actor="test", reason="score detail test"):
        conn.execute(
            "INSERT INTO audit_runs (run_id, target_domain, run_date, audited_stages, "
            "automated_findings, status, overall_score, run_token, score_detail_json) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, "example.com", "2026-09-28", "[]", "[]", "automated_complete", 77, "tok", detail_json),
        )

def test_full_run_returns_stored_score_detail(client):
    card = compute_layered_score([])
    detail = {
        "sub_scores": {k: v.as_dict() for k, v in card.sub_scores.items()},
        "score_breakdown": card._flat_breakdown(),
        "access_gate_applied": card.access_gate_applied,
        "access_gate_cap": card.access_gate_cap,
        "authority_metrics": {"authority_score": 12, "referring_domains": 3, "trust_flow": 0, "citation_flow": 0},
    }
    _insert_run("run-with-detail", json.dumps(detail))
    body = client.get("/api/v1/audit/runs/run-with-detail/full").json()
    assert body["overall_score"] == 77
    assert body["score_detail"] == detail

def test_legacy_row_has_null_detail_and_no_crash(client):
    _insert_run("run-legacy", None)
    r = client.get("/api/v1/audit/runs/run-legacy/full")
    assert r.status_code == 200 and r.json()["score_detail"] is None

@pytest.mark.parametrize("raw", [None, "", "not json", "[1, 2]"])
def test_parse_score_detail_rejects_bad_input(raw):
    assert _parse_score_detail(raw) is None

def test_orchestrator_saves_score_detail_column():
    src = (ROOT / "areos" / "auditors" / "audit_orchestrator.py").read_text(encoding="utf-8")
    assert "run_token, score_detail_json) VALUES (?,?,?,?,?,?,?,?,?)" in src
    assert "_score_detail_json," in src

def test_schema_and_migration_define_score_detail_json():
    assert "score_detail_json" in (ROOT / "areos" / "db" / "schema.sql").read_text(encoding="utf-8")
    assert "score_detail_json" in (ROOT / "areos" / "db" / "migrate_audit_tables.py").read_text(encoding="utf-8")
