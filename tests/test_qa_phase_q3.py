# tests/test_qa_phase_q3.py
#
# QA Remediation Phase Q3 Test Suite (High Priority Fixes)
# Tests: QA-H03, QA-H04, QA-H06, QA-H07, QA-H08, QA-H11

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from areos.util.ssrf import safe_get
from areos.auditors.schema_validator import validate_page_schemas, validate_single
from areos.auditors.audit_orchestrator import run_orchestrated_audit
from areos.auditors.scoring import LAYER_DEDUCTIONS
from areos.db.migrate_audit_tables import migrate


class TestQ3AuditorCrashRecovery:
    """Test auditor error handling and AUDIT_PHASE_CRASHED findings (QA-H03)."""

    def test_auditor_crash_injects_finding(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_crash.db"
        monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
        monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
        migrate(test_db)

        with patch("areos.auditors.freshness_auditor.audit_freshness", side_effect=RuntimeError("Simulated Freshness Crash")):
            res = run_orchestrated_audit("example.com", sample_content="<html><body><p>Test content is here with enough words to analyze.</p></body></html>", db_path=test_db)
            crashed_findings = [f for f in res["raw_findings"] if f.get("code") == "AUDIT_PHASE_CRASHED"]
            assert len(crashed_findings) >= 1
            assert "Content freshness" in crashed_findings[0]["message"]
            assert crashed_findings[0]["severity"] == "error"

    def test_auditor_crash_doesnt_abort_remaining_phases(self, tmp_path, monkeypatch):
        test_db = tmp_path / "test_multi_phase.db"
        monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
        monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
        migrate(test_db)

        with patch("areos.auditors.media_blindness_auditor.audit_media_blindness", side_effect=RuntimeError("Media Crash")):
            res = run_orchestrated_audit("example.com", sample_content="<html><body><p>Substantive body text with enough words for extractability analysis.</p></body></html>", db_path=test_db)
            assert res["executive_scorecard"]["overall_score"] >= 5
            # Non-crashed phases should still produce findings or finish cleanly
            assert len(res["raw_findings"]) > 0


class TestQ3SafeGetSizeLimit:
    """Test safe_get response size limiting (QA-H04 / D-QA-009)."""

    def test_safe_get_enforces_5mb_limit(self):
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 200
            mock_resp.close = lambda: None
            mock_resp.iter_content = lambda chunk_size=8192: [b"x" * 1024 * 1024] * 6
            mock_get.return_value = mock_resp

            with pytest.raises(ValueError, match="exceeds 5242880 bytes limit"):
                safe_get("http://example.com/huge-file.html")

    def test_safe_get_normal_response_passes(self):
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 200
            mock_resp.encoding = "utf-8"
            mock_resp.iter_content = lambda chunk_size=8192: [b"<html><body><h1>Hello</h1></body></html>"]
            mock_get.return_value = mock_resp

            resp = safe_get("http://example.com/index.html")
            assert resp.text == "<html><body><h1>Hello</h1></body></html>"

    def test_safe_get_empty_response(self):
        with patch("requests.get") as mock_get:
            mock_resp = requests.Response()
            mock_resp.status_code = 200
            mock_resp.encoding = "utf-8"
            mock_resp.iter_content = lambda chunk_size=8192: []
            mock_get.return_value = mock_resp

            resp = safe_get("http://example.com/empty.html")
            assert resp.text == ""


class TestQ3AuthorityAuditorImports:
    """Test authority auditor imports and quotes (QA-H06)."""

    def test_authority_auditor_urllib_import_exists(self):
        from areos.auditors.authority_auditor import fetch_open_pagerank
        # Ensure fetch_open_pagerank doesn't fail with NameError on urllib.parse
        result = fetch_open_pagerank("example.com", "invalid_api_key_test")
        assert result is None  # Handled gracefully without NameError


class TestQ3SchemaValidatorEdgeCases:
    """Test Schema Validator @graph and mainEntity resilience (QA-H07, QA-H08)."""

    def test_schema_validator_graph_null(self):
        blocks = [{"@graph": None}]
        results = validate_page_schemas(blocks)
        assert len(results) >= 1
        assert results[0].passed is False

    def test_schema_validator_graph_single_dict(self):
        blocks = [{"@graph": {"@type": "Organization", "name": "Test Org"}}]
        results = validate_page_schemas(blocks)
        assert len(results) == 1
        assert results[0].schema_type == "Organization"

    def test_schema_validator_string_in_mainentity(self):
        faq_block = {
            "@type": "FAQPage",
            "mainEntity": [
                "https://schema.org/Question",  # String reference instead of dict
                {"@type": "Question", "name": "What is AREOS?", "acceptedAnswer": {"@type": "Answer", "text": "A platform."}}
            ]
        }
        result = validate_single(faq_block)
        # Must not raise AttributeError: 'str' object has no attribute 'get'
        assert result.schema_type == "FAQPage"


class TestQ3KnowledgeMapParity:
    """Test check_code_to_knowledge_map.json remapping (QA-H11)."""

    def test_check_codes_not_mapped_to_deprecated(self):
        map_path = Path(__file__).resolve().parents[1] / "areos" / "kb" / "check_code_to_knowledge_map.json"
        corpus_path = Path(__file__).resolve().parents[1] / "areos" / "kb" / "corpus" / "knowledge.jsonl"

        check_map = json.loads(map_path.read_text(encoding="utf-8"))
        knowledge_records = {}
        for line in corpus_path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if line and line.startswith("{"):
                rec = json.loads(line)
                knowledge_records[rec["kid"]] = rec

        # Verify no check code maps to deprecated KT-041 or any deprecated records in corpus
        for code, entry in check_map.items():
            assert entry.get("guidance_record") != "KT-041", f"Code {code} still maps to deprecated KT-041"
            assert "KT-041" not in entry.get("backing_records", []), f"Code {code} still has KT-041 in backing_records"

            guidance_kid = entry.get("guidance_record")
            if guidance_kid and guidance_kid in knowledge_records:
                # KT-130..KT-136, KT-155 were intentionally demoted in Phase F as empirically unbacked
                if guidance_kid not in ("KT-130", "KT-131", "KT-132", "KT-133", "KT-134", "KT-135", "KT-136", "KT-155"):
                    assert knowledge_records[guidance_kid]["status"] != "deprecated", f"Code {code} guidance {guidance_kid} is deprecated"
            for backing_kid in entry.get("backing_records", []):
                if backing_kid in knowledge_records:
                    assert knowledge_records[backing_kid]["status"] != "deprecated", f"Code {code} backing {backing_kid} is deprecated"
