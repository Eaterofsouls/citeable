"""Phase R4 Regression Suite: Auditor Resilience, Bounds & Parsing (TR-401 to TR-405)."""
import logging
import pytest
from unittest.mock import patch, MagicMock

from areos.auditors.multipage_auditor import audit_multi_page, _extract_page_text
from areos.auditors.competitor_analyzer import analyze_competitors
from areos.auditors.audit_orchestrator import _fetch_robots_txt
from areos.llm.synthesis_pipeline import _parse_flags


class TestR4MultiPageAuditor:
    """Tests for multi-page crawler resilience and unescaping."""

    def test_multipage_auditor_handles_network_exception(self, caplog):
        """Verify audit_multi_page handles network exceptions gracefully with warning."""
        with patch("areos.auditors.multipage_auditor.safe_get", side_effect=Exception("Connection refused")):
            with caplog.at_level(logging.WARNING):
                res = audit_multi_page(["https://example.com/p1", "https://example.com/p2"], "example.com")
            assert res.page_count == 0
            assert any(i.code == "SITEMAP_PAGES_UNREACHABLE" for i in res.issues)
            assert any("Failed to fetch multi-page URL" in msg for msg in caplog.messages)

    def test_multipage_extract_page_text_unescapes_entities(self):
        """Verify _extract_page_text cleans HTML tags and unescapes &amp; &lt; etc."""
        raw_html = "<html><body><h1>Title &amp; Subtitle</h1><p>Text &gt; 50 &copy; 2026</p></body></html>"
        extracted = _extract_page_text(raw_html)
        assert extracted == "Title & Subtitle Text > 50 © 2026"

    def test_multipage_near_duplicate_detection(self):
        """Verify audit_multi_page detects near duplicate pages (>85% text similarity)."""
        content1 = "<html><body>" + ("Repeated sentence for duplicate test content. " * 30) + "</body></html>"
        content2 = "<html><body>" + ("Repeated sentence for duplicate test content. " * 30) + " Minor diff.</body></html>"
        mock_resp1 = MagicMock(status_code=200, text=content1)
        mock_resp2 = MagicMock(status_code=200, text=content2)

        def mock_get(url, **kwargs):
            if "p1" in url:
                return mock_resp1
            return mock_resp2

        with patch("areos.auditors.multipage_auditor.safe_get", side_effect=mock_get):
            res = audit_multi_page(["https://example.com/p1", "https://example.com/p2"], "example.com")
            assert len(res.duplicate_pairs) > 0
            assert any(i.code == "NEAR_DUPLICATE_PAGES" for i in res.issues)


class TestR4CompetitorAnalyzer:
    """Tests for competitor analysis error handling and schema comparison."""

    def test_competitor_analyzer_handles_timeout_gracefully(self, caplog):
        """Verify analyze_competitors logs warning on competitor fetch timeout."""
        with patch("areos.auditors.competitor_analyzer.safe_get", side_effect=Exception("Timeout")):
            with caplog.at_level(logging.WARNING):
                res = analyze_competitors(["competitor.com"], "target.com")
            assert len(res.competitors_analyzed) == 0
            assert any("Failed to fetch competitor URL" in msg for msg in caplog.messages)

    def test_competitor_analyzer_identifies_schema_advantage(self):
        """Verify analyze_competitors emits COMPETITOR_SCHEMA_ADVANTAGE when competitor has schema types."""
        comp_html = '<html><head><script type="application/ld+json">{"@type": "Product", "name": "Item"}</script></head></html>'
        mock_resp = MagicMock(status_code=200, text=comp_html)
        with patch("areos.auditors.competitor_analyzer.safe_get", return_value=mock_resp):
            res = analyze_competitors(["rival.com"], "target.com", target_schema_types=["Organization"])
            assert "rival.com" in res.competitors_analyzed
            assert any(i.code == "COMPETITOR_SCHEMA_ADVANTAGE" for i in res.issues)


class TestR4RobotsAndLLMResilience:
    """Tests for robots.txt fetch logging and synthesis pipeline flag parsing."""

    def test_fetch_robots_txt_logs_warning_on_network_error(self, caplog):
        """Verify _fetch_robots_txt logs warning on network error."""
        with patch("areos.auditors.audit_orchestrator.safe_get", side_effect=Exception("DNS failure")):
            with caplog.at_level(logging.WARNING):
                res = _fetch_robots_txt("unresolvable-domain-12345.com")
            assert res is None
            assert any("Failed to fetch robots.txt" in msg for msg in caplog.messages)

    def test_parse_flags_handles_dict_wrapped_flags(self):
        """Verify _parse_flags parses dictionary with 'flags' key."""
        raw_json = '```json\n{"flags": [{"flag": "HALLUCINATED_CLAIM", "claim_id": "C010", "reason": "Not in source"}]}\n```'
        flags = _parse_flags(raw_json)
        assert len(flags) == 1
        assert flags[0]["flag"] == "HALLUCINATED_CLAIM"

    def test_parse_flags_handles_single_dict_flag(self):
        """Verify _parse_flags parses a single dict object with 'flag' key."""
        raw_json = '{"flag": "UNSUPPORTED_LEAP", "reason": "No evidence"}'
        flags = _parse_flags(raw_json)
        assert len(flags) == 1
        assert flags[0]["flag"] == "UNSUPPORTED_LEAP"

