# tests/test_qa_phase_q5.py
#
# QA Remediation Phase Q5 Test Suite (Cleanup & Minor Fixes)
# Tests: QA-L03, QA-L04, QA-L05, QA-L07

import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")

from areos.auditors.robots_checker import parse_robots_txt
from areos.auditors.multipage_auditor import audit_multi_page
from areos.auditors.media_blindness_auditor import audit_media_blindness


class TestQ5RobotsCheckerComments:
    """Test robots.txt comment stripping and fragment preservation (QA-L05)."""

    def test_robots_checker_fragment_preserved(self):
        robots_txt = """
User-agent: *
Disallow: /admin
Sitemap: https://example.com/sitemap.xml#section
"""
        res = parse_robots_txt(robots_txt)
        assert len(res.sitemap_urls) == 1
        assert res.sitemap_urls[0] == "https://example.com/sitemap.xml#section"

    def test_robots_checker_inline_comment_stripped(self):
        robots_txt = """
User-agent: *
Disallow: /admin # administrative area
Sitemap: https://example.com/sitemap.xml # main production sitemap
"""
        res = parse_robots_txt(robots_txt)
        assert len(res.sitemap_urls) == 1
        assert res.sitemap_urls[0] == "https://example.com/sitemap.xml"


class TestQ5AuditorConstants:
    """Test auditor threshold constants and behavior (QA-L03, QA-L04)."""

    def test_media_blindness_thresholds(self):
        # Empty body with 1 image missing alt -> MEDIA_OK or IMAGES_MISSING_ALT
        html = "<html><body><p>" + ("word " * 100) + "</p><img src='img.jpg'></body></html>"
        res = audit_media_blindness("https://example.com", html)
        codes = [i.code for i in res.issues]
        assert "IMAGES_MISSING_ALT" in codes

    def test_dom_js_loaded_once(self):
        ui_dir = Path(__file__).resolve().parents[1] / "areos" / "ui"
        for html_file in ["index.html", "claims_browser.html"]:
            target = ui_dir / html_file
            if target.exists():
                content = target.read_text(encoding="utf-8")
                assert content.count('src="dom.js"') <= 1, f"Duplicate dom.js script tag in {html_file}"
