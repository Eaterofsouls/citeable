# tests/test_extractability.py
"""
Unit tests for content extractability judge and orchestrator integration.
Covers WP-2.3:
  - Fast-path heuristics in extractability_judge (none, high)
  - Missing-key graceful degradation (medium)
  - LLM judge calls and failure recovery
  - Orchestrator findings mapping for all four labels (none, low, medium, high)
"""

from unittest.mock import patch, MagicMock
import pytest
from areos.auditors.extractability_judge import (
    judge_page,
    build_signals,
    extract_rag_signals_from_html,
    ExtractabilityResult,
)
from areos.auditors.audit_orchestrator import run_orchestrated_audit
from areos.db.migrate_audit_tables import migrate


class TestExtractabilityJudgeDirect:
    """Test extractability_judge.py functions directly."""

    def test_heuristic_thin_content_returns_none(self):
        """Page with minimal text returns 'none' via fast-path heuristic without LLM call."""
        page_data = {
            "url": "https://example.com/empty",
            "status_code": 200,
            "html": "<html><body><p>Thin content</p></body></html>",
        }
        res = judge_page(page_data)
        assert res.label == "none"
        assert res.confidence == "high"
        assert "heuristic" in res.rationale.lower()

    def test_heuristic_non_200_returns_none(self):
        """Non-200 status code triggers 'none' heuristic."""
        page_data = {
            "url": "https://example.com/404",
            "status_code": 404,
            "rag_chunkability": {
                "total_substantive_paragraphs": 10,
                "list_item_count": 5,
            },
        }
        res = judge_page(page_data)
        assert res.label == "none"

    def test_heuristic_faq_returns_high(self):
        """Page with FAQ schema and FAQ indicators returns 'high' via heuristic."""
        page_data = {
            "url": "https://example.com/faq",
            "status_code": 200,
            "rag_chunkability": {
                "total_substantive_paragraphs": 5,
                "list_item_count": 5,
                "faq_indicators": 3,
            },
            "json_lds": [{"@type": "FAQPage"}],
        }
        res = judge_page(page_data)
        assert res.label == "high"
        assert res.confidence == "high"
        assert "heuristic" in res.rationale.lower()

    def test_no_api_key_degrades_to_medium(self):
        """Ambiguous page with no API keys configured degrades gracefully to 'medium'."""
        page_data = {
            "url": "https://example.com/article",
            "status_code": 200,
            "rag_chunkability": {
                "total_substantive_paragraphs": 4,
                "avg_paragraph_word_count": 50.0,
                "heading_count": 3,
                "list_item_count": 0,
                "faq_indicators": 0,
            },
            "json_lds": [],
        }
        res = judge_page(page_data, client_keys={})
        assert res.label == "medium"
        assert res.confidence == "low"
        assert "no api key" in res.rationale.lower()

    def test_llm_judge_returns_mocked_label(self):
        """When API key is present, LLM judge completes and returns label."""
        page_data = {
            "url": "https://example.com/guide",
            "status_code": 200,
            "rag_chunkability": {
                "total_substantive_paragraphs": 6,
                "avg_paragraph_word_count": 45.0,
                "heading_count": 4,
                "list_item_count": 4,
                "faq_indicators": 0,
            },
        }
        mock_response = '{"label": "low", "confidence": "high", "rationale": "Buried in dense CSS and script."}'
        with patch("areos.llm.providers.complete", return_value=mock_response):
            res = judge_page(page_data, client_keys={"openai": "sk-mock-key"})
            assert res.label == "low"
            assert res.confidence == "high"
            assert "Buried in dense CSS" in res.rationale

    def test_llm_judge_exception_degrades_to_medium(self):
        """If LLM call throws an exception, judge degrades to 'medium' without crashing."""
        page_data = {
            "url": "https://example.com/guide",
            "status_code": 200,
            "rag_chunkability": {
                "total_substantive_paragraphs": 6,
                "list_item_count": 4,
            },
        }
        with patch("areos.llm.providers.complete", side_effect=RuntimeError("API timeout")):
            res = judge_page(page_data, client_keys={"openai": "sk-mock-key"})
            assert res.label == "medium"
            assert res.confidence == "low"
            assert "defaulted to medium" in res.rationale

    def test_extract_rag_signals_from_html(self):
        """HTML parser correctly identifies paragraphs, headings, list items, and scripts."""
        sample_html = """
        <html>
          <head>
            <script>var x = 12345;</script>
            <script type="application/ld+json">{"@context": "https://schema.org", "@type": "FAQPage"}</script>
          </head>
          <body>
            <h1>Main Title</h1>
            <h2>What is AREOS?</h2>
            <p>AREOS is an automated answer engine optimization diagnostic tool that analyzes technical search factors.</p>
            <p>It evaluates 131 scientific claims across multiple layers to assess content extractability for AI search engines.</p>
            <ul>
              <li>Feature one</li>
              <li>Feature two</li>
              <li>Feature three</li>
            </ul>
          </body>
        </html>
        """
        signals = extract_rag_signals_from_html(sample_html)
        assert signals["heading_count"] == 2
        assert signals["list_item_count"] == 3
        assert signals["total_substantive_paragraphs"] >= 2
        assert signals["has_faq_schema"] is True
        assert signals["faq_indicators"] >= 1


class TestOrchestratorExtractabilityWiring:
    """Test that audit_orchestrator routes judge_page output to findings for all 4 labels."""

    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path, monkeypatch):
        self.test_db = tmp_path / "test_extractability_orch.db"
        monkeypatch.setenv("AREOS_TEST_DB", str(self.test_db))
        monkeypatch.setenv("AREOS_DB_PATH", str(self.test_db))
        migrate(self.test_db)

    def _run_with_mock_judge(self, label: str):
        mock_result = ExtractabilityResult(
            page_id="test_page",
            url="https://example.com",
            label=label,
            confidence="high",
            rationale=f"Test rationale for {label}",
            signals_summary={},
        )
        sample_html = "<html><body><h1>Title</h1><p>Sample body paragraph with content.</p></body></html>"
        with patch("areos.auditors.audit_orchestrator.judge_page", return_value=mock_result):
            res = run_orchestrated_audit(
                "example.com",
                sample_content=sample_html,
                db_path=str(self.test_db),
            )
        return [f for f in res["raw_findings"] if f["code"].startswith("EXTRACTABILITY_")]

    def test_orchestrator_emits_extractability_none(self):
        findings = self._run_with_mock_judge("none")
        codes = [f["code"] for f in findings]
        assert "EXTRACTABILITY_NONE" in codes
        finding = next(f for f in findings if f["code"] == "EXTRACTABILITY_NONE")
        assert finding["severity"] == "error"

    def test_orchestrator_emits_extractability_low(self):
        findings = self._run_with_mock_judge("low")
        codes = [f["code"] for f in findings]
        assert "EXTRACTABILITY_LOW" in codes
        finding = next(f for f in findings if f["code"] == "EXTRACTABILITY_LOW")
        assert finding["severity"] == "warning"

    def test_orchestrator_emits_extractability_medium(self):
        findings = self._run_with_mock_judge("medium")
        codes = [f["code"] for f in findings]
        assert "EXTRACTABILITY_MEDIUM" in codes
        finding = next(f for f in findings if f["code"] == "EXTRACTABILITY_MEDIUM")
        assert finding["severity"] == "warning"

    def test_orchestrator_emits_extractability_high(self):
        findings = self._run_with_mock_judge("high")
        codes = [f["code"] for f in findings]
        assert "EXTRACTABILITY_HIGH" in codes
        finding = next(f for f in findings if f["code"] == "EXTRACTABILITY_HIGH")
        assert finding["severity"] == "info"

    def test_orchestrator_handles_judge_exception_gracefully(self):
        """If judge_page raises an exception inside orchestrator, it degrades to EXTRACTABILITY_MEDIUM."""
        sample_html = "<html><body><h1>Title</h1><p>Sample body paragraph with content.</p></body></html>"
        with patch("areos.auditors.audit_orchestrator.judge_page", side_effect=Exception("Judge crash")):
            res = run_orchestrated_audit(
                "example.com",
                sample_content=sample_html,
                db_path=str(self.test_db),
            )
        extract_findings = [f for f in res["raw_findings"] if f["code"].startswith("EXTRACTABILITY_")]
        assert len(extract_findings) == 1
        assert extract_findings[0]["code"] == "EXTRACTABILITY_MEDIUM"
        assert extract_findings[0]["severity"] == "warning"
