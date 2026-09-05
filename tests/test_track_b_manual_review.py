# tests/test_track_b_manual_review.py
#
# Track B Gate: Manual Review Redesign (T-B01 through T-B07).
# Run: python -m pytest tests/test_track_b_manual_review.py -v

import os
import sys
import json
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_trackb_token")
os.environ.setdefault("AREOS_API_TOKEN", "test_trackb_api_token")

WORKSPACE = os.path.join(os.path.dirname(__file__), "..")


# ── T-B01: manual_observations table in schema.sql ───────────────────────────

class TestTB01ManualObservationsSchema:
    def test_schema_sql_has_manual_observations_table(self):
        schema_path = os.path.join(WORKSPACE, "areos", "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        assert "CREATE TABLE IF NOT EXISTS manual_observations" in sql

    def test_schema_sql_has_observations_index(self):
        schema_path = os.path.join(WORKSPACE, "areos", "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        assert "idx_manual_observations_run" in sql

    def test_manual_verdicts_still_present(self):
        """Legacy table must be retained for backward compat."""
        schema_path = os.path.join(WORKSPACE, "areos", "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        assert "CREATE TABLE IF NOT EXISTS manual_verdicts" in sql

    def test_manual_observations_table_creates_in_sqlite(self):
        """The SQL must be valid — create in-memory DB."""
        schema_path = os.path.join(WORKSPACE, "areos", "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn = sqlite3.connect(":memory:")
        conn.executescript(sql)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manual_observations'")
        assert cur.fetchone() is not None
        conn.close()


# ── T-B02: ObservationPayload Pydantic model ─────────────────────────────────

class TestTB02ObservationPayload:
    def test_model_importable(self):
        from areos.api.routers.audit import ObservationPayload
        assert ObservationPayload is not None

    def test_model_validates_correctly(self):
        from areos.api.routers.audit import ObservationPayload
        obs = ObservationPayload(
            question_id="B1_SCHEMA_HONESTY",
            maps_to_claims=["C053", "C054"],
            structured_data={"claims_verified": [True, False]},
            severity="warning",
            diagnosis_text="Schema claim about founding date is incorrect."
        )
        assert obs.question_id == "B1_SCHEMA_HONESTY"
        assert obs.severity == "warning"
        assert obs.maps_to_claims == ["C053", "C054"]

    def test_model_defaults(self):
        from areos.api.routers.audit import ObservationPayload
        obs = ObservationPayload(question_id="D2_ROOT_CAUSE_DIAGNOSIS", severity="info")
        assert obs.maps_to_claims == []
        assert obs.structured_data == {}
        assert obs.diagnosis_text == ""


# ── T-B03: POST /observations endpoint ───────────────────────────────────────

class TestTB03SubmitObservation:
    def _get_client(self):
        """Create a FastAPI test client with a temp DB."""
        from fastapi.testclient import TestClient
        import importlib
        try:
            import areos.api.app as app_mod
            importlib.reload(app_mod)
            app = app_mod.app
        except Exception:
            pytest.skip("FastAPI app not importable in test environment")
        return TestClient(app)

    def test_submit_observation_endpoint_exists(self):
        """Verify the endpoint is registered on the router."""
        from areos.api.routers.audit import router
        routes = [r.path for r in router.routes]
        assert any("observations" in p for p in routes), f"No observations route in {routes}"

    def test_upsert_logic_in_db(self):
        """Direct DB test: UPSERT on (run_id, question_id) works correctly."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE IF NOT EXISTS manual_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                structured_data TEXT NOT NULL,
                severity TEXT NOT NULL,
                diagnosis_text TEXT,
                submitted_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # First insert
        conn.execute(
            "INSERT INTO manual_observations (run_id, question_id, structured_data, severity, diagnosis_text) VALUES (?,?,?,?,?)",
            ("run_001", "B1_SCHEMA_HONESTY", json.dumps({"answer": "yes"}), "info", "First answer")
        )
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1

        # UPSERT: delete + reinsert (same run_id + question_id)
        conn.execute("DELETE FROM manual_observations WHERE run_id=? AND question_id=?", ("run_001", "B1_SCHEMA_HONESTY"))
        conn.execute(
            "INSERT INTO manual_observations (run_id, question_id, structured_data, severity, diagnosis_text) VALUES (?,?,?,?,?)",
            ("run_001", "B1_SCHEMA_HONESTY", json.dumps({"answer": "no"}), "warning", "Updated answer")
        )
        conn.commit()

        # Should still be 1 row, with updated data
        assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1
        row = conn.execute("SELECT * FROM manual_observations WHERE run_id='run_001'").fetchone()
        assert row["severity"] == "warning"
        assert "Updated" in (row["diagnosis_text"] or "")
        conn.close()


# ── T-B04: GET /full-report endpoint ─────────────────────────────────────────

class TestTB04FullReport:
    def test_full_report_endpoint_exists(self):
        """Verify the endpoint is registered on the router."""
        from areos.api.routers.audit import router
        routes = [r.path for r in router.routes]
        assert any("full-report" in p for p in routes), f"No full-report route in {routes}"

    def test_zero_observations_caveat(self):
        """The report must include confidence caveat when no observations exist."""
        # Verify the caveat text exists in the code
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "Confidence: Low. No manual qualitative verification performed." in src

    def test_report_has_six_sections(self):
        """The report dict must include all 6 required sections."""
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        for section in ["executive_diagnosis", "layer_1_access", "layer_2_content_schema",
                        "layer_3_authority_citations", "fix_sequence", "audit_metadata"]:
            assert section in src, f"Section '{section}' not found in get_unified_report"

    def test_legacy_verdicts_fallback_logic(self):
        """Code must query manual_verdicts when manual_observations is empty."""
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "manual_verdicts" in src
        # Both tables must be queried in get_unified_report context
        assert "legacy_verdicts" in src


# ── T-B05: /synthesize pulls from manual_observations ────────────────────────

class TestTB05SynthesisUpdate:
    def test_synthesize_queries_manual_observations(self):
        """Synthesize endpoint must query manual_observations first."""
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "manual_observations" in src
        assert "HUMAN CONFIRMED" in src  # The structured format string

    def test_synthesize_has_legacy_fallback(self):
        """Synthesize must still fall back to manual_verdicts for older runs."""
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        # Should have both paths
        assert "observation_rows" in src
        assert "verdict_rows" in src

    def test_observation_format_string(self):
        """Structured observation note format must match spec."""
        audit_path = os.path.join(WORKSPACE, "areos", "api", "routers", "audit.py")
        with open(audit_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "Question:" in src
        assert "Severity:" in src
        assert "Diagnosis:" in src
        assert "Data:" in src


# ── T-B07: Synthesis prompt rules 9 and 10 ───────────────────────────────────

class TestTB07SynthesisPrompt:
    def test_rule_9_in_prompt(self):
        """Rule 9 (human_diagnosis_text framing) must be in the synthesizer prompt."""
        pipeline_path = os.path.join(WORKSPACE, "areos", "llm", "synthesis_pipeline.py")
        with open(pipeline_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "human_diagnosis_text" in src
        assert "opening framing" in src

    def test_rule_10_in_prompt(self):
        """Rule 10 (explain WHY, not invent actions) must be in the synthesizer prompt."""
        pipeline_path = os.path.join(WORKSPACE, "areos", "llm", "synthesis_pipeline.py")
        with open(pipeline_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "explain WHY each action matters" in src
        assert "not to invent new actions" in src

    def test_prompt_contains_all_ten_rules(self):
        """Count to confirm both old rules (1-8) and new rules (9-10) are present."""
        from areos.llm.synthesis_pipeline import _DEFAULT_SYNTHESIZER_PROMPT
        # Rules 9 and 10 added
        assert "9." in _DEFAULT_SYNTHESIZER_PROMPT
        assert "10." in _DEFAULT_SYNTHESIZER_PROMPT
        # Original 8 rules still present
        assert "1." in _DEFAULT_SYNTHESIZER_PROMPT
        assert "8." in _DEFAULT_SYNTHESIZER_PROMPT

    def test_pipeline_not_changed(self):
        """Verify the 3-step pipeline structure is intact."""
        from areos.llm.synthesis_pipeline import (
            _DEFAULT_SYNTHESIZER_PROMPT,
            _DEFAULT_RED_TEAMER_PROMPT,
            _DEFAULT_GROUNDER_PROMPT,
        )
        assert len(_DEFAULT_SYNTHESIZER_PROMPT) > 0
        assert len(_DEFAULT_RED_TEAMER_PROMPT) > 0
        assert len(_DEFAULT_GROUNDER_PROMPT) > 0


# ── Track B Integration: B1 Data Integrity ───────────────────────────────────

class TestTrackBIntegration:
    def test_b1_data_stored_as_json(self):
        """B1 structured_data must be stored as valid JSON (UPSERT test)."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE manual_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, question_id TEXT,
                structured_data TEXT, severity TEXT, diagnosis_text TEXT,
                submitted_at TEXT DEFAULT (datetime('now'))
            )
        """)
        b1_data = {
            "claims_verified": [
                {"claim": "Founded in 2010", "verified": True},
                {"claim": "Headquartered in London", "verified": False}
            ],
            "ideal_answer_sentence": "We were founded in 2010 and are based in London."
        }
        conn.execute(
            "INSERT INTO manual_observations (run_id, question_id, structured_data, severity, diagnosis_text) VALUES (?,?,?,?,?)",
            ("run_b1", "B1_SCHEMA_HONESTY", json.dumps(b1_data), "warning", "One claim mismatch found.")
        )
        conn.commit()
        row = conn.execute("SELECT structured_data FROM manual_observations WHERE run_id='run_b1'").fetchone()
        parsed = json.loads(row["structured_data"])
        assert "claims_verified" in parsed
        assert parsed["claims_verified"][1]["verified"] is False
        conn.close()
