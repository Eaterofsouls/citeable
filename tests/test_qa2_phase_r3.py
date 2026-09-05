"""Phase R3 Regression Suite: API, Database & Concurrency Safety (TR-301 to TR-305)."""
import os
os.environ.setdefault("AREOS_API_TOKEN", "test-token")

import sqlite3
import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError

from areos.api.dependencies import get_db, get_client_keys
from areos.api.routers.audit import AuditRunPayload, _rate_limit, _ip_buckets
from areos.db.migrate_audit_tables import migrate
from areos.db.ingest_claims import ingest


class TestR3DBAndDependencies:
    """Tests for FastAPI dependency lifecycle and rollback."""

    def test_get_db_rolls_back_on_route_exception(self, tmp_path, monkeypatch):
        """Verify get_db performs rollback if generator context raises with open transaction."""
        db_path = tmp_path / "dep_test.db"
        monkeypatch.setenv("AREOS_TEST_DB", str(db_path))
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (x INT)")
        conn.commit()
        conn.close()

        gen = get_db()
        db_conn = next(gen)
        # Start transaction
        db_conn.execute("BEGIN IMMEDIATE")
        db_conn.execute("INSERT INTO t VALUES (42)")
        assert db_conn.in_transaction is True

        # Simulate route exception
        try:
            gen.throw(RuntimeError("Simulated route error"))
        except RuntimeError:
            pass

        assert db_conn.in_transaction is False

    def test_subsequent_request_inherits_clean_connection(self, tmp_path, monkeypatch):
        """Verify second get_db caller receives clean non-transactional connection."""
        db_path = tmp_path / "dep_test2.db"
        monkeypatch.setenv("AREOS_TEST_DB", str(db_path))
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (x INT)")
        conn.commit()
        conn.close()

        # Request 1: fails
        gen1 = get_db()
        c1 = next(gen1)
        c1.execute("BEGIN IMMEDIATE")
        try:
            gen1.throw(RuntimeError("fail"))
        except RuntimeError:
            pass

        # Request 2: clean
        gen2 = get_db()
        c2 = next(gen2)
        assert c2.in_transaction is False
        c2.execute("INSERT INTO t VALUES (100)")
        c2.commit()

    def test_get_client_keys_lowercases_provider(self):
        """Verify get_client_keys normalizes headers to lowercase provider keys."""
        mock_req = MagicMock()
        mock_req.headers = {
            "X-API-Key-OpenAI": "sk-12345",
            "x-api-key-GROQ": "gsk-67890",
            "x-api-base-azure": "https://azure.com",
            "Content-Type": "application/json"
        }
        keys = get_client_keys(mock_req)
        assert keys.get("openai") == "sk-12345"
        assert keys.get("groq") == "gsk-67890"
        assert keys.get("x_api_base_azure") == "https://azure.com"


class TestR3MigrationAndSchema:
    """Tests for schema migration when claims is a view."""

    def test_migration_succeeds_when_claims_is_view(self, tmp_path):
        """Verify migrate() does not fail on foreign key constraints when claims is a view."""
        db_path = tmp_path / "view_mig_test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE knowledge (kid TEXT PRIMARY KEY)")
        conn.execute("CREATE VIEW claims AS SELECT kid as claim_id FROM knowledge")
        conn.commit()
        conn.close()

        # Run migrate
        migrate(db_path=db_path)
        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "audit_runs" in tables


class TestR3PayloadValidationAndRateLimit:
    """Tests for AuditRunPayload regex and rate limit memory bounds."""

    def test_audit_payload_valid_domain_passes(self):
        """Verify valid domain passes AuditRunPayload validation."""
        payload = AuditRunPayload(target_domain="example.com")
        assert payload.target_domain == "example.com"
        assert payload.audited_stages == []
        assert payload.automated_findings == []

    def test_audit_payload_invalid_domain_fails(self):
        """Verify invalid domain (protocol or bad format) fails regex."""
        with pytest.raises(ValidationError):
            AuditRunPayload(target_domain="https://example.com")

        with pytest.raises(ValidationError):
            AuditRunPayload(target_domain="invalid domain")

    def test_rate_limiter_bounds_memory_under_ddos(self):
        """Verify _rate_limit prunes dictionary when keys exceed upper bound."""
        _ip_buckets.clear()
        mock_req = MagicMock()
        import time
        now = time.time()
        # Seed 10500 entries
        for i in range(10500):
            _ip_buckets[f"test:{i}"] = [now - (i % 30)]

        mock_req.client.host = "1.2.3.4"
        _rate_limit(mock_req, bucket_prefix="test", limit=100)
        assert len(_ip_buckets) <= 10000


class TestR3SeedAuditContext:
    """Tests for ingest_claims write_as context."""

    def test_ingest_claims_records_write_as_context(self, tmp_path):
        """Verify ingest writes audit changelog with actor and reason."""
        db_path = tmp_path / "ingest_test.db"
        migrate(db_path=db_path)

        dummy_claims = tmp_path / "test_claims.json"
        import json
        data = [{
            "claim_id": "C999",
            "stage_id": "STAGE-01",
            "claim_scope": "audit-workflow",
            "claim_type": "policy",
            "statement": "Seed test claim statement",
            "status": "active",
            "confidence": "high",
            "source_url": "https://example.com",
            "source_tier_vocab": "system_native",
            "source_tier_value": "internal-playbook",
            "source_date": "2026-01-01",
            "last_verified": "2026-01-01",
            "superseded_by": None
        }]
        dummy_claims.write_text(json.dumps(data), encoding="utf-8")

        res = ingest(db_path=db_path, source_path=dummy_claims, verbose=False)
        assert res["claims_inserted"] > 0

        conn = sqlite3.connect(str(db_path))
        logs = conn.execute("SELECT actor, reason FROM changelog WHERE entity_table = 'claims'").fetchall()
        conn.close()
        assert len(logs) > 0
        assert logs[0][0] == "ingest_claims"

