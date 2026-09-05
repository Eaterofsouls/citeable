# tests/test_phase2_auditors.py
#
# Phase 2 Gate: Tests for 7 new auditor modules + citation enhancements (T-201→T-208).
# Run: python -m pytest tests/test_phase2_auditors.py -v

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase2_token")


# ── T-201: Freshness Auditor ─────────────────────────────────────────────────

class TestT201FreshnessAuditor:
    def test_module_importable(self):
        from areos.auditors.freshness_auditor import audit_freshness, FreshnessIssue, FreshnessAuditResult
        assert callable(audit_freshness)

    def test_stale_content(self):
        from areos.auditors.freshness_auditor import audit_freshness
        html = '<meta property="article:modified_time" content="2024-01-01T00:00:00Z">'
        result = audit_freshness("https://example.com", html=html, json_ld_blocks=[])
        codes = {i.code for i in result.issues}
        assert "CONTENT_STALE" in codes or "CONTENT_AGING" in codes

    def test_date_missing(self):
        from areos.auditors.freshness_auditor import audit_freshness
        result = audit_freshness("https://example.com", html="<html><body>No dates</body></html>", json_ld_blocks=[])
        codes = {i.code for i in result.issues}
        assert "DATE_MISSING" in codes

    def test_fresh_jsonld(self):
        from areos.auditors.freshness_auditor import audit_freshness
        from datetime import date
        today = date.today().isoformat()
        blocks = [{"@type": "Article", "dateModified": today}]
        result = audit_freshness("https://example.com", html="", json_ld_blocks=blocks)
        codes = {i.code for i in result.issues}
        assert "FRESHNESS_OK" in codes


# ── T-202: Redirect Auditor ──────────────────────────────────────────────────

class TestT202RedirectAuditor:
    def test_module_importable(self):
        from areos.auditors.redirect_auditor import audit_redirects_and_access, RedirectIssue, RedirectAuditResult
        assert callable(audit_redirects_and_access)

    def test_long_redirect_chain(self):
        from areos.auditors.redirect_auditor import audit_redirects_and_access
        result = audit_redirects_and_access("https://a.com", "<html></html>", hop_count=6, final_url="https://a.com")
        codes = {i.code for i in result.issues}
        assert "REDIRECT_CHAIN_EXCESSIVE" in codes or "REDIRECT_CHAIN_LONG" in codes

    def test_meta_noindex(self):
        from areos.auditors.redirect_auditor import audit_redirects_and_access
        html = '<html><head><meta name="robots" content="noindex"></head></html>'
        result = audit_redirects_and_access("https://a.com", html, hop_count=0, final_url="https://a.com")
        codes = {i.code for i in result.issues}
        assert "META_NOINDEX" in codes

    def test_no_issues(self):
        from areos.auditors.redirect_auditor import audit_redirects_and_access
        result = audit_redirects_and_access("https://a.com", "<html></html>", hop_count=0, final_url="https://a.com")
        codes = {i.code for i in result.issues}
        assert "ACCESS_OK" in codes


# ── T-203: Cloaking Detector ─────────────────────────────────────────────────

class TestT203CloakingDetector:
    def test_module_importable(self):
        from areos.auditors.cloaking_detector import audit_cloaking, CloakingIssue, CloakingResult
        assert callable(audit_cloaking)

    def test_result_has_required_fields(self):
        from areos.auditors.cloaking_detector import CloakingResult
        r = CloakingResult(url="https://example.com", passed=True)
        assert hasattr(r, "browser_word_count")
        assert hasattr(r, "bot_word_count")
        assert hasattr(r, "missing_elements")
        assert hasattr(r, "content_diff_summary")


# ── T-204: Entity Verifier ───────────────────────────────────────────────────

class TestT204EntityVerifier:
    def test_module_importable(self):
        from areos.auditors.entity_verifier import audit_entities, EntityIssue, EntityAuditResult
        assert callable(audit_entities)

    def test_sameas_missing(self):
        from areos.auditors.entity_verifier import audit_entities
        blocks = [{"@type": "Organization", "name": "Test Corp", "url": "https://test.com"}]
        result = audit_entities("https://test.com", html="", json_ld_blocks=blocks)
        codes = {i.code for i in result.issues}
        assert "SAMEAS_MISSING" in codes

    def test_wikidata_missing(self):
        from areos.auditors.entity_verifier import audit_entities
        blocks = [{"@type": "Organization", "name": "Test", "sameAs": ["https://twitter.com/test"]}]
        result = audit_entities("https://test.com", html="", json_ld_blocks=blocks)
        codes = {i.code for i in result.issues}
        assert "WIKIDATA_MISSING" in codes

    def test_entity_ok(self):
        from areos.auditors.entity_verifier import audit_entities
        blocks = [{"@type": "Organization", "name": "Test", "sameAs": [
            "https://twitter.com/test", "https://linkedin.com/test",
            "https://www.wikidata.org/wiki/Q12345"
        ]}]
        result = audit_entities("https://test.com", html="", json_ld_blocks=blocks)
        codes = {i.code for i in result.issues}
        assert "ENTITY_OK" in codes


# ── T-205: Media Blindness Auditor ───────────────────────────────────────────

class TestT205MediaBlindness:
    def test_module_importable(self):
        from areos.auditors.media_blindness_auditor import audit_media_blindness, MediaIssue, MediaAuditResult
        assert callable(audit_media_blindness)

    def test_iframe_heavy(self):
        from areos.auditors.media_blindness_auditor import audit_media_blindness
        html = "<html><body>" + "<iframe src='x'></iframe>" * 5 + "<p>Some text here.</p></body></html>"
        result = audit_media_blindness("https://example.com", html)
        codes = {i.code for i in result.issues}
        assert "IFRAME_HEAVY" in codes

    def test_missing_alt(self):
        from areos.auditors.media_blindness_auditor import audit_media_blindness
        html = "<html><body>" + "<img src='x'>" * 10 + "<p>Some text content here for word count.</p></body></html>"
        result = audit_media_blindness("https://example.com", html)
        codes = {i.code for i in result.issues}
        assert "IMAGES_MISSING_ALT" in codes

    def test_media_ok(self):
        from areos.auditors.media_blindness_auditor import audit_media_blindness
        html = '<html><body><img src="x" alt="photo"><p>' + "word " * 60 + '</p></body></html>'
        result = audit_media_blindness("https://example.com", html)
        codes = {i.code for i in result.issues}
        assert "MEDIA_OK" in codes


# ── T-206: Sitemap Auditor ───────────────────────────────────────────────────

class TestT206SitemapAuditor:
    def test_module_importable(self):
        from areos.auditors.sitemap_auditor import audit_sitemap, SitemapIssue, SitemapAuditResult
        assert callable(audit_sitemap)

    def test_result_has_urls_field(self):
        from areos.auditors.sitemap_auditor import SitemapAuditResult
        r = SitemapAuditResult(url="https://example.com", passed=True)
        assert hasattr(r, "urls")
        assert isinstance(r.urls, list)


# ── T-207: CitationObservation Enhancement ───────────────────────────────────

class TestT207FullAnswerText:
    def test_full_answer_text_field_exists(self):
        from areos.auditors.citation_sampler import CitationObservation
        obs = CitationObservation(run_index=0, prompt="test", engine="perplexity")
        assert hasattr(obs, "full_answer_text")
        assert obs.full_answer_text == ""

    def test_full_answer_text_settable(self):
        from areos.auditors.citation_sampler import CitationObservation
        obs = CitationObservation(
            run_index=0, prompt="test", engine="perplexity",
            raw_answer_snippet="short",
            full_answer_text="This is the full untruncated answer text that is very long " * 20
        )
        assert len(obs.full_answer_text) > 300
        assert obs.raw_answer_snippet == "short"

    def test_backward_compat_raw_snippet(self):
        """raw_answer_snippet must still exist for backward compatibility."""
        from areos.auditors.citation_sampler import CitationObservation
        obs = CitationObservation(run_index=0, prompt="q", engine="gemini", raw_answer_snippet="snippet")
        assert obs.raw_answer_snippet == "snippet"


# ── T-208: Citation Analytics ────────────────────────────────────────────────

class TestT208CitationAnalytics:
    def test_compute_citation_analytics_importable(self):
        from areos.auditors.citation_sampler import compute_citation_analytics
        assert callable(compute_citation_analytics)

    def test_share_of_voice_calculation(self):
        from areos.auditors.citation_sampler import (
            compute_citation_analytics, CitationSampleResult, CitationObservation
        )
        obs1 = CitationObservation(
            run_index=0, prompt="q1", engine="perplexity",
            cited_urls=["https://example.com/page1", "https://competitor.com/page1", "https://example.com/page2"]
        )
        obs2 = CitationObservation(
            run_index=1, prompt="q2", engine="perplexity",
            cited_urls=["https://competitor.com/page2", "https://other.com/page1"]
        )
        result = CitationSampleResult(
            target_domain="example.com", prompt_set=["q1", "q2"],
            engine="perplexity", n_runs=2, observations=[obs1, obs2]
        )
        analytics = compute_citation_analytics(result)
        assert analytics["target_domain"] == "example.com"
        assert analytics["total_runs"] == 2
        assert analytics["cited_runs"] == 1  # only obs1 has example.com
        assert analytics["share_of_voice"] == 0.4  # 2 out of 5 URLs
        assert analytics["total_unique_urls"] == 5
        assert len(analytics["competitor_domains"]) >= 1
        # competitor.com should appear
        comp_domains = {c["domain"] for c in analytics["competitor_domains"]}
        assert "competitor.com" in comp_domains

    def test_empty_observations(self):
        from areos.auditors.citation_sampler import compute_citation_analytics, CitationSampleResult
        result = CitationSampleResult(
            target_domain="example.com", prompt_set=[], engine="perplexity", n_runs=0
        )
        analytics = compute_citation_analytics(result)
        assert analytics["citation_rate"] == 0.0
        assert analytics["share_of_voice"] == 0.0
        assert analytics["competitor_domains"] == []
