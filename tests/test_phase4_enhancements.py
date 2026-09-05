# tests/test_phase4_enhancements.py
#
# Phase 4 Comprehensive Suite: Content format (T-401) & robots sitemap extraction (T-402).
# Run: python -m pytest tests/test_phase4_enhancements.py -v

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase4_token")


# ── T-401: Content Format Auditor 30% Position & Edge Cases ───────────────────

class TestT401ContentFormatAuditor:
    def test_answer_in_first_30_percent_passes(self):
        from areos.auditors.content_format_auditor import audit_page_format
        # 10 blocks: first block is substantive (>30 words)
        blocks = [
            "<p>Citeable is an advanced search engineering and AI optimization platform that automates citation tracking, knowledge base verification, technical crawling audits, and structured data validation for modern enterprise brands and digital growth teams globally.</p>"
        ] + [f"<p>Short paragraph {i} with basic details.</p>" for i in range(9)]
        html = "".join(blocks)
        res = audit_page_format("https://example.com", html=html)
        codes = [iss.code for iss in res.issues]
        assert "ANSWER_NOT_NEAR_TOP" not in codes

    def test_answer_past_30_percent_fails(self):
        from areos.auditors.content_format_auditor import audit_page_format
        # 10 blocks: first 5 blocks are short (< 30 words), substantive block is at block 6 (60%)
        blocks = [f"<p>Short introductory snippet {i}.</p>" for i in range(5)]
        blocks.append(
            "<p>Citeable is an advanced search engineering and AI optimization platform that automates citation tracking, knowledge base verification, and structured data validation for modern enterprise brands.</p>"
        )
        blocks.extend([f"<p>Trailing paragraph {i}.</p>" for i in range(4)])
        html = "".join(blocks)
        res = audit_page_format("https://example.com", html=html)
        codes = [iss.code for iss in res.issues]
        assert "ANSWER_NOT_NEAR_TOP" in codes

    def test_single_block_boundary(self):
        """Single block page should not trigger ANSWER_NOT_NEAR_TOP if len(text_blocks) < 2."""
        from areos.auditors.content_format_auditor import audit_page_format
        html = "<p>A single short sentence on a page.</p>"
        res = audit_page_format("https://example.com", html=html)
        codes = [iss.code for iss in res.issues]
        assert "ANSWER_NOT_NEAR_TOP" not in codes

    def test_empty_html_content_format(self):
        from areos.auditors.content_format_auditor import audit_page_format
        res = audit_page_format("https://example.com", html="")
        assert res.passed is True
        assert res.signals_analyzed["text_blocks_count"] == 0

    def test_exact_30_percent_boundary_calculation(self):
        """Verify dynamic 30% calculation on a 20-block page (top 6 blocks evaluated)."""
        from areos.auditors.content_format_auditor import audit_page_format
        # Blocks 0-4 short, Block 5 (>30 words, index 5 which is within top 6 blocks = 30%)
        substantive = "<p>Citeable is an advanced search engineering and AI optimization platform that automates citation tracking, knowledge base verification, technical crawling audits, and structured data validation for modern enterprise brands and digital growth teams globally.</p>"
        blocks = [f"<p>Short paragraph {i}.</p>" for i in range(5)] + [substantive] + [f"<p>Later paragraph {i}.</p>" for i in range(14)]
        html = "".join(blocks)
        res = audit_page_format("https://example.com", html=html)
        codes = [iss.code for iss in res.issues]
        assert "ANSWER_NOT_NEAR_TOP" not in codes


# ── T-402: Robots.txt Sitemap Extraction & Formatting Edge Cases ──────────────

class TestT402RobotsSitemapExtraction:
    def test_sitemap_urls_extracted(self):
        from areos.auditors.robots_checker import parse_robots_txt
        robots_txt = """
User-agent: *
Disallow: /admin/
Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap_news.xml
"""
        result = parse_robots_txt(robots_txt)
        assert hasattr(result, "sitemap_urls")
        assert len(result.sitemap_urls) == 2
        assert "https://example.com/sitemap.xml" in result.sitemap_urls
        assert "https://example.com/sitemap_news.xml" in result.sitemap_urls

    def test_no_sitemap_returns_empty_list(self):
        from areos.auditors.robots_checker import parse_robots_txt
        robots_txt = """
User-agent: *
Disallow: /private/
"""
        result = parse_robots_txt(robots_txt)
        assert hasattr(result, "sitemap_urls")
        assert result.sitemap_urls == []

    def test_sitemap_with_inline_comments(self):
        from areos.auditors.robots_checker import parse_robots_txt
        robots_txt = """
User-agent: GPTBot
Disallow:
Sitemap: https://example.com/sitemap.xml # Primary production sitemap
"""
        result = parse_robots_txt(robots_txt)
        assert len(result.sitemap_urls) == 1
        assert result.sitemap_urls[0] == "https://example.com/sitemap.xml"

    def test_case_insensitive_sitemap_directive(self):
        from areos.auditors.robots_checker import parse_robots_txt
        robots_txt = """
SITEMAP: https://example.com/sitemap_upper.xml
sitemap: https://example.com/sitemap_lower.xml
"""
        result = parse_robots_txt(robots_txt)
        assert len(result.sitemap_urls) == 2
        assert "https://example.com/sitemap_upper.xml" in result.sitemap_urls
        assert "https://example.com/sitemap_lower.xml" in result.sitemap_urls
