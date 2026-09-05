# tests/test_phase1_fetch.py
#
# Phase 1 Gate: Regression tests for Page Fetch Refactor (T-101 through T-104).
# Run: python -m pytest tests/test_phase1_fetch.py -v
#
# WHAT WE TEST:
#   T-101: _fetch_page exists and returns (str, int, str) on failure
#   T-102: _extract_schema_claims returns correct dict keys
#   T-103: _validate_schema_from_html handles empty HTML gracefully
#   T-103: Orchestrator uses single-fetch flow (no _fetch_and_validate_schema)
#   T-104: FormatAuditResult has extracted_lead_text field

import os
import sys
import pytest
from unittest.mock import patch
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase1_token")


class TestT101FetchPage:
    """T-101: _fetch_page function exists and returns correct tuple."""

    def test_fetch_page_exists(self):
        """_fetch_page must be importable from audit_orchestrator."""
        from areos.auditors.audit_orchestrator import _fetch_page
        assert callable(_fetch_page)

    def test_fetch_page_signature(self):
        """_fetch_page returns (str, int, str) on failure with bad domain."""
        from areos.auditors.audit_orchestrator import _fetch_page
        result = _fetch_page("nonexistent.invalid.domain.xyz", "https://nonexistent.invalid.domain.xyz")
        assert isinstance(result, tuple)
        assert len(result) == 3
        html, hop_count, final_url = result
        assert isinstance(html, str)
        assert isinstance(hop_count, int)
        assert isinstance(final_url, str)

    def test_fetch_page_failure_returns_empty(self):
        """On network failure, _fetch_page returns ('', 0, original_url)."""
        from areos.auditors.audit_orchestrator import _fetch_page
        with patch("areos.auditors.audit_orchestrator.safe_get", side_effect=requests.RequestException("DNS resolution failed")):
            html, hop_count, final_url = _fetch_page(
                "nonexistent.invalid.domain.xyz",
                "https://nonexistent.invalid.domain.xyz"
            )
            assert html == ""
            assert hop_count == 0
            assert final_url == "https://nonexistent.invalid.domain.xyz"


class TestT102ExtractSchemaClaims:
    """T-102: _extract_schema_claims returns correct dict list with expected keys."""

    def test_extract_schema_claims_basic(self):
        """_extract_schema_claims extracts fields from a simple JSON-LD block."""
        from areos.auditors.schema_validator import _extract_schema_claims
        blocks = [{
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "AREOS",
            "url": "https://areos.com",
            "description": "AEO/GEO optimization platform"
        }]
        claims = _extract_schema_claims(blocks)
        assert isinstance(claims, list)
        assert len(claims) > 0
        # Each claim must have schema_type, field, value keys
        for claim in claims:
            assert "schema_type" in claim
            assert "field" in claim
            assert "value" in claim
        # Should have extracted Organization fields
        schema_types = {c["schema_type"] for c in claims}
        assert "Organization" in schema_types
        fields = {c["field"] for c in claims}
        assert "name" in fields
        assert "url" in fields
        # @context should be skipped
        assert "@context" not in fields

    def test_extract_schema_claims_skips_strings(self):
        """_extract_schema_claims skips unparseable string blocks."""
        from areos.auditors.schema_validator import _extract_schema_claims
        blocks = ["this is not valid JSON-LD", {"@type": "Article", "headline": "Test"}]
        claims = _extract_schema_claims(blocks)
        # Should only get claims from the Article block
        schema_types = {c["schema_type"] for c in claims}
        assert "Article" in schema_types
        assert len(claims) >= 1

    def test_extract_schema_claims_empty(self):
        """_extract_schema_claims returns [] for empty input."""
        from areos.auditors.schema_validator import _extract_schema_claims
        assert _extract_schema_claims([]) == []

    def test_extract_schema_claims_nested_dict(self):
        """Nested dict values should be serialized (not crash)."""
        from areos.auditors.schema_validator import _extract_schema_claims
        blocks = [{"@type": "Organization", "contactPoint": {"@type": "ContactPoint", "telephone": "+1"}}]
        claims = _extract_schema_claims(blocks)
        contact_claims = [c for c in claims if c["field"] == "contactPoint"]
        assert len(contact_claims) == 1
        assert contact_claims[0]["value"] == "ContactPoint"


class TestT103SingleFetchFlow:
    """T-103: Orchestrator uses single-fetch flow."""

    def test_no_fetch_and_validate_schema(self):
        """_fetch_and_validate_schema should no longer exist (replaced by _validate_schema_from_html)."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "auditors", "audit_orchestrator.py"
        )
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "_fetch_and_validate_schema" not in content, \
            "audit_orchestrator.py still has old _fetch_and_validate_schema function"
        assert "_validate_schema_from_html" in content, \
            "audit_orchestrator.py missing new _validate_schema_from_html function"
        assert "_fetch_page" in content, \
            "audit_orchestrator.py missing _fetch_page function"

    def test_validate_schema_from_html_empty(self):
        """_validate_schema_from_html must handle empty HTML gracefully."""
        from areos.auditors.audit_orchestrator import _validate_schema_from_html
        findings, blocks, claims = _validate_schema_from_html("", "https://example.com")
        assert len(findings) == 1
        assert findings[0]["code"] == "SCHEMA_UNVERIFIABLE"
        assert blocks == []
        assert claims == []

    def test_validate_schema_from_html_no_jsonld(self):
        """_validate_schema_from_html must handle HTML with no JSON-LD."""
        from areos.auditors.audit_orchestrator import _validate_schema_from_html
        findings, blocks, claims = _validate_schema_from_html(
            "<html><body><p>No schema here</p></body></html>",
            "https://example.com"
        )
        assert len(findings) == 1
        assert findings[0]["code"] == "SCHEMA_MISSING"
        assert blocks == []

    def test_validate_schema_from_html_with_jsonld(self):
        """_validate_schema_from_html must parse and validate real JSON-LD."""
        from areos.auditors.audit_orchestrator import _validate_schema_from_html
        html = '''<html><body>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Organization", "name": "Test Corp", "url": "https://test.com"}
        </script>
        </body></html>'''
        findings, blocks, claims = _validate_schema_from_html(html, "https://test.com")
        assert isinstance(findings, list)
        assert len(blocks) == 1
        assert isinstance(claims, list)
        assert len(claims) > 0
        # Claims should have Organization schema type
        assert any(c["schema_type"] == "Organization" for c in claims)

    def test_single_fetch_in_orchestrator_flow(self):
        """Orchestrator must call _fetch_page, not make duplicate HTTP requests for schema."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "auditors", "audit_orchestrator.py"
        )
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Should have the single-fetch pattern
        assert "page_html, redirect_hop_count, final_url = _fetch_page(" in content, \
            "Orchestrator missing single-fetch _fetch_page call"


class TestT104FormatAuditResultField:
    """T-104: FormatAuditResult must have extracted_lead_text field."""

    def test_extracted_lead_text_exists(self):
        """FormatAuditResult must have extracted_lead_text field."""
        from areos.auditors.content_format_auditor import FormatAuditResult
        result = FormatAuditResult(url="https://example.com", passed=True)
        assert hasattr(result, "extracted_lead_text")
        assert result.extracted_lead_text == ""

    def test_extracted_lead_text_settable(self):
        """extracted_lead_text must be settable."""
        from areos.auditors.content_format_auditor import FormatAuditResult
        result = FormatAuditResult(
            url="https://example.com",
            passed=True,
            extracted_lead_text="AREOS is an AEO/GEO optimization platform."
        )
        assert result.extracted_lead_text == "AREOS is an AEO/GEO optimization platform."
