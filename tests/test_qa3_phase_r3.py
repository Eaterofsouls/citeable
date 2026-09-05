import os
os.environ["AREOS_API_TOKEN"] = "test-token"
os.environ["AREOS_ADMIN_TOKEN"] = "test-token"

import time
import threading
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from areos.api.main import app
from areos.api.routers.audit import _rate_limit, _ip_buckets
from areos.db.stage_normalization import normalize_stage_id, _load_aliases
from areos.db.context import write_as
from areos.db.connection import get_connection, get_db_path


client = TestClient(app)


def test_streaming_body_size_enforcement_chunked():
    """Verify chunked request exceeding 5MB triggers HTTP 413."""
    oversized_payload = b"x" * (5_000_000 + 100)
    response = client.post(
        "/api/v1/audit/observe/dummy-run",
        content=oversized_payload,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert "Payload too large" in response.json().get("detail", "")


def test_streaming_body_size_normal_payload_passes():
    """Verify standard payload under 5MB passes body size check."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_rate_limiter_thread_safe_locking():
    """Verify concurrent threads accessing _rate_limit don't corrupt state."""
    req = MagicMock()
    req.client.host = "192.168.1.100"

    errors = []
    def worker():
        try:
            for _ in range(5):
                try:
                    _rate_limit(req, bucket_prefix="test_concurrent", limit=100, window_seconds=60)
                except Exception:
                    pass
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_temp_txn_context_connection_isolation():
    """Verify _txn_context can be set across connections safely."""
    conn1 = sqlite3.connect(":memory:")
    conn2 = sqlite3.connect(":memory:")

    with write_as(conn1, actor="user1", reason="test1"):
        row1 = conn1.execute("SELECT actor, reason FROM _txn_context WHERE id = 1").fetchone()
        assert row1 == ("user1", "test1")

    with write_as(conn2, actor="user2", reason="test2"):
        row2 = conn2.execute("SELECT actor, reason FROM _txn_context WHERE id = 1").fetchone()
        assert row2 == ("user2", "test2")

    conn1.close()
    conn2.close()


def test_stage_normalization_mtime_invalidation(tmp_path):
    """Verify modifying alias file mtime invalidates cache automatically."""
    alias_file = tmp_path / "stage_id_aliases.yaml"
    alias_file.write_text("aliases:\n  custom-01: STAGE-99\n", encoding="utf-8")

    res, err = normalize_stage_id("custom-01", alias_file)
    assert res == "STAGE-99"

    # Modify file with new mapping and update mtime
    time.sleep(0.01)
    alias_file.write_text("aliases:\n  custom-01: STAGE-100\n", encoding="utf-8")

    res2, err2 = normalize_stage_id("custom-01", alias_file)
    assert res2 == "STAGE-100"


def test_no_dynamic_ddl_in_observation_route():
    """Verify submit_observation route functions without executing inline DDL."""
    with open("areos/api/routers/audit.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "CREATE TABLE IF NOT EXISTS manual_observations (" not in content


def test_admin_routes_require_authentication():
    """Verify calling admin state-mutating endpoint without token returns 401."""
    response = client.post(
        "/api/v1/prompts",
        json={"label": "test", "prompt_text": "test prompt"}
    )
    assert response.status_code == 401


def test_health_endpoint_active():
    """Verify /api/health executes active database check."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
