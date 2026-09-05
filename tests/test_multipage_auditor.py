# tests/test_multipage_auditor.py
#
# Phase 6 Comprehensive Suite: Limited Multi-Page Crawl (T-601).
# Run: python -m pytest tests/test_multipage_auditor.py -v

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase6_token")


class TestT601MultiPageAuditor:
    def test_module_importable(self):
        from areos.auditors.multipage_auditor import audit_multi_page, MultiPageAuditResult
        assert audit_multi_page is not None

    def test_empty_urls_returns_empty_result(self):
        from areos.auditors.multipage_auditor import audit_multi_page
        res = audit_multi_page([], "example.com")
        assert res.page_count == 0
        assert res.issues == []

    @patch("areos.auditors.multipage_auditor.safe_get")
    def test_multipage_detects_schema_gaps_and_duplicates(self, mock_safe_get):
        from areos.auditors.multipage_auditor import audit_multi_page

        html_with_schema = """<html><head><script type="application/ld+json">{"@type":"Article"}</script></head><body><p>Unique content paragraph for page one with many words describing the platform and services offered in depth.</p></body></html>"""
        html_no_schema = """<html><head></head><body><p>Unique content paragraph for page one with many words describing the platform and services offered in depth.</p></body></html>"""

        def side_effect(url, timeout=4):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "page1" in url:
                mock_resp.text = html_with_schema
            else:
                mock_resp.text = html_no_schema
            return mock_resp

        mock_safe_get.side_effect = side_effect

        urls = ["https://example.com/page1", "https://example.com/page2"]
        res = audit_multi_page(urls, "example.com")
        assert res.page_count == 2
        codes = [i.code for i in res.issues]
        assert "MULTI_PAGE_SCHEMA_GAPS" in codes
        assert "NEAR_DUPLICATE_PAGES" in codes

    @patch("areos.auditors.multipage_auditor.safe_get")
    def test_multipage_detects_thin_content(self, mock_safe_get):
        from areos.auditors.multipage_auditor import audit_multi_page
        thin_html = "<html><body><p>Too short.</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = thin_html
        mock_safe_get.return_value = mock_resp

        res = audit_multi_page(["https://example.com/thin1", "https://example.com/thin2"], "example.com")
        codes = [i.code for i in res.issues]
        assert "MULTI_PAGE_THIN_CONTENT" in codes

    @patch("areos.auditors.multipage_auditor.safe_get")
    def test_multipage_detects_unreachable_urls(self, mock_safe_get):
        from areos.auditors.multipage_auditor import audit_multi_page
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_safe_get.return_value = mock_resp

        res = audit_multi_page(["https://example.com/dead1", "https://example.com/dead2"], "example.com")
        codes = [i.code for i in res.issues]
        assert "SITEMAP_PAGES_UNREACHABLE" in codes

    @patch("areos.auditors.multipage_auditor.safe_get")
    def test_multipage_ok_when_healthy(self, mock_safe_get):
        from areos.auditors.multipage_auditor import audit_multi_page
        p1 = """<html><head><script type="application/ld+json">{"@type":"Product"}</script></head><body><p>Alpha platform provides comprehensive real-time database management, automated clustering, automated failover triggers, high-availability data replication, and distributed consensus verification for modern cloud-native systems operating across multiregional clusters with zero downtime requirements and strict consistency guarantees.</p></body></html>"""
        p2 = """<html><head><script type="application/ld+json">{"@type":"Service"}</script></head><body><p>Beta consulting services offer specialized advisory solutions for enterprise organizations migrating legacy monolithic applications into decoupled microservices architectures, container orchestration pipelines, automated continuous delivery systems, and observability dashboards with round-the-clock incident response coverage.</p></body></html>"""

        def side_effect(url, timeout=4):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = p1 if "alpha" in url else p2
            return mock_resp

        mock_safe_get.side_effect = side_effect
        res = audit_multi_page(["https://example.com/alpha", "https://example.com/beta"], "example.com")
        codes = [i.code for i in res.issues]
        assert "MULTI_PAGE_OK" in codes
        assert "NEAR_DUPLICATE_PAGES" not in codes

    @patch("areos.auditors.multipage_auditor.safe_get")
    def test_multipage_caps_at_max_pages(self, mock_safe_get):
        from areos.auditors.multipage_auditor import audit_multi_page
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><p>Valid content with sufficient word count to exceed thresholds comfortably.</p></body></html>"
        mock_safe_get.return_value = mock_resp

        urls = [f"https://example.com/page_{i}" for i in range(25)]
        res = audit_multi_page(urls, "example.com", max_pages=10)
        assert len(res.urls_crawled) == 10
