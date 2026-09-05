# tests/test_competitor_analyzer.py
#
# Phase 7 Comprehensive Suite: Competitor Extraction & Analysis (T-701).
# Run: python -m pytest tests/test_competitor_analyzer.py -v

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase7_token")


class TestT701CompetitorAnalyzer:
    def test_module_importable(self):
        from areos.auditors.competitor_analyzer import analyze_competitors, CompetitorAnalysisResult
        assert analyze_competitors is not None

    def test_empty_competitors_returns_empty_result(self):
        from areos.auditors.competitor_analyzer import analyze_competitors
        res = analyze_competitors([], "example.com")
        assert res.competitors_analyzed == []
        assert res.issues == []

    def test_self_domain_is_filtered_out(self):
        from areos.auditors.competitor_analyzer import analyze_competitors
        # If the target domain or subdomains are in competitor_domains, filter them out
        res = analyze_competitors(["example.com", "sub.example.com"], "example.com")
        assert res.competitors_analyzed == []
        assert res.issues == []

    @patch("areos.auditors.competitor_analyzer.safe_get")
    def test_competitor_schema_advantage_detected(self, mock_safe_get):
        from areos.auditors.competitor_analyzer import analyze_competitors

        comp_html = """
        <html>
        <head>
          <script type="application/ld+json">{"@type": "FAQPage"}</script>
          <script type="application/ld+json">{"@type": "Product"}</script>
        </head>
        <body><p>Competitor homepage text.</p></body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = comp_html
        mock_safe_get.return_value = mock_resp

        res = analyze_competitors(["competitor.com"], "example.com", target_schema_types=["Organization"])
        assert "competitor.com" in res.competitors_analyzed
        codes = [i.code for i in res.issues]
        assert "COMPETITOR_SCHEMA_ADVANTAGE" in codes

    @patch("areos.auditors.competitor_analyzer.safe_get")
    def test_competitor_content_advantage_detected(self, mock_safe_get):
        from areos.auditors.competitor_analyzer import analyze_competitors

        comp_html = """
        <html>
        <body>
          <ul><li>Item 1</li><li>Item 2</li></ul>
          <table><tr><td>Row</td></tr></table>
        </body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = comp_html
        mock_safe_get.return_value = mock_resp

        res = analyze_competitors(["structured-rival.com"], "example.com", target_schema_types=[])
        codes = [i.code for i in res.issues]
        assert "COMPETITOR_CONTENT_ADVANTAGE" in codes

    @patch("areos.auditors.competitor_analyzer.safe_get")
    def test_competitor_analysis_ok_when_target_is_ahead(self, mock_safe_get):
        from areos.auditors.competitor_analyzer import analyze_competitors

        comp_html = """
        <html>
        <head><script type="application/ld+json">{"@type": "Organization"}</script></head>
        <body><p>Plain unformatted text without tables.</p></body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = comp_html
        mock_safe_get.return_value = mock_resp

        res = analyze_competitors(["basic-rival.com"], "example.com", target_schema_types=["Organization", "FAQPage", "Product"])
        codes = [i.code for i in res.issues]
        assert "COMPETITOR_ANALYSIS_OK" in codes

    @patch("areos.auditors.competitor_analyzer.safe_get")
    def test_caps_at_max_competitors(self, mock_safe_get):
        from areos.auditors.competitor_analyzer import analyze_competitors
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Competitor content</p></body></html>"
        mock_safe_get.return_value = mock_resp

        domains = [f"rival{i}.com" for i in range(10)]
        res = analyze_competitors(domains, "example.com", max_competitors=3)
        assert len(res.competitors_analyzed) == 3

    @patch("areos.auditors.competitor_analyzer.safe_get")
    def test_malformed_jsonld_handled_gracefully(self, mock_safe_get):
        from areos.auditors.competitor_analyzer import analyze_competitors
        bad_html = """<html><head><script type="application/ld+json">{ broken json !!!</script></head></html>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = bad_html
        mock_safe_get.return_value = mock_resp

        res = analyze_competitors(["broken-rival.com"], "example.com", target_schema_types=["Organization"])
        assert "broken-rival.com" in res.competitors_analyzed
        assert res.competitor_stats["broken-rival.com"]["schema_types"] == []
