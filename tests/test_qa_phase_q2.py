# tests/test_qa_phase_q2.py
#
# QA Remediation Phase Q2 Test Suite (Boot Crash & Migration Fixes)
# Tests: QA-C04, QA-C07, D-QA-004

import json
import os
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from areos.db.migrate_audit_tables import migrate
from areos.kb.build_kb import build as build_kb


class TestQ2MigrationAndBoot:
    """Test database schema migrations and boot crash prevention."""

    def test_migrate_handles_claims_view(self, tmp_path):
        db_path = tmp_path / "test_claims_view.db"
        conn = sqlite3.connect(db_path)
        # Simulate V2 KB where claims is created as a VIEW
        conn.execute("CREATE TABLE knowledge (kid TEXT PRIMARY KEY, statement TEXT)")
        conn.execute("CREATE VIEW claims AS SELECT kid, statement FROM knowledge")
        conn.commit()
        conn.close()

        # Running migrate() must not crash with "Cannot add a column to a view"
        migrate(db_path)

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT type FROM sqlite_master WHERE name='claims'").fetchone()
        assert row[0] == "view"
        conn.close()

    def test_migrate_handles_fresh_db(self, tmp_path):
        db_path = tmp_path / "test_fresh.db"
        migrate(db_path)

        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "audit_runs" in tables
        assert "manual_observations" in tables
        assert "sources" in tables
        conn.close()

    def test_migrate_idempotent_three_runs(self, tmp_path):
        db_path = tmp_path / "test_idempotent.db"
        migrate(db_path)
        migrate(db_path)
        migrate(db_path)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        assert count > 5
        conn.close()

    def test_build_kb_duplicate_kid_logged(self, tmp_path):
        db_path = tmp_path / "test_duplicate_kid.db"
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        record1 = {
            "kid": "KT-999", "type": "FACT", "scope": "crawl-access",
            "statement": "First statement", "context": "", "status": "active",
            "confidence": "high", "support": "strong", "evidence_ids": [],
            "guidance": None, "relationships": [], "legacy_ids": [],
            "provenance": {"origin": "test"}
        }
        record2 = {
            "kid": "KT-999", "type": "FACT", "scope": "crawl-access",
            "statement": "Updated statement", "context": "", "status": "active",
            "confidence": "high", "support": "strong", "evidence_ids": [],
            "guidance": None, "relationships": [], "legacy_ids": [],
            "provenance": {"origin": "test"}
        }

        (corpus_dir / "knowledge.jsonl").write_text(
            json.dumps(record1) + "\n" + json.dumps(record2) + "\n",
            encoding="utf-8"
        )
        (corpus_dir / "sources.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "evidence.jsonl").write_text("", encoding="utf-8")

        build_kb(db_path, corpus_dir=corpus_dir)

        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT statement FROM knowledge WHERE kid='KT-999'").fetchone()
        assert row is not None
        assert row[0] == "Updated statement"
        conn.close()

    def test_build_kb_malformed_jsonl_line(self, tmp_path):
        db_path = tmp_path / "test_malformed.db"
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        valid_rec = {
            "kid": "KT-001", "type": "FACT", "scope": "crawl-access",
            "statement": "Valid record", "context": "", "status": "active",
            "confidence": "high", "support": "strong", "evidence_ids": [],
            "guidance": None, "relationships": [], "legacy_ids": [],
            "provenance": {"origin": "test"}
        }

        (corpus_dir / "knowledge.jsonl").write_text(
            json.dumps(valid_rec) + "\n{CORRUPTED_JSON_NOT_VALID\n",
            encoding="utf-8"
        )
        (corpus_dir / "sources.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "evidence.jsonl").write_text("", encoding="utf-8")

        build_kb(db_path, corpus_dir=corpus_dir)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        assert count == 1
        conn.close()

    def test_build_kb_empty_files(self, tmp_path):
        db_path = tmp_path / "test_empty.db"
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        (corpus_dir / "knowledge.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "sources.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "evidence.jsonl").write_text("", encoding="utf-8")

        build_kb(db_path, corpus_dir=corpus_dir)

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        assert count == 0
        conn.close()

    def test_build_kb_then_migrate_sequence(self, tmp_path):
        db_path = tmp_path / "test_lifecycle.db"
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        record = {
            "kid": "KT-001", "type": "FACT", "scope": "crawl-access",
            "statement": "Valid record", "context": "", "status": "active",
            "confidence": "high", "support": "strong", "evidence_ids": [],
            "guidance": None, "relationships": [], "legacy_ids": [],
            "provenance": {"origin": "test"}
        }

        (corpus_dir / "knowledge.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
        (corpus_dir / "sources.jsonl").write_text("", encoding="utf-8")
        (corpus_dir / "evidence.jsonl").write_text("", encoding="utf-8")

        # Step 1: Initial migration
        migrate(db_path)
        # Step 2: KB build
        build_kb(db_path, corpus_dir=corpus_dir)
        # Step 3: Second migration (server restart)
        migrate(db_path)

        conn = sqlite3.connect(db_path)
        assert conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0] == 1
        conn.close()

    def test_kb_meta_v2_schema_insert(self, tmp_path):
        db_path = tmp_path / "test_meta.db"
        migrate(db_path)

        conn = sqlite3.connect(db_path)
        # Ensure kb_meta exists and accepts key-value or row 1
        row = conn.execute("SELECT * FROM kb_meta WHERE id=1").fetchone()
        assert row is not None
        conn.close()
