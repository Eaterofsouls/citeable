# tests/test_rendering_auditor.py
#
# Phase 5 Comprehensive Suite: JS-Rendering Diff Auditor (T-501, T-502).
# Run: python -m pytest tests/test_rendering_auditor.py -v

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase5_token")


class TestT501RenderingAuditor:
    def test_module_importable(self):
        from areos.auditors.rendering_auditor import audit_js_rendering, PLAYWRIGHT_AVAILABLE, RenderingAuditResult
        assert audit_js_rendering is not None
        assert isinstance(PLAYWRIGHT_AVAILABLE, bool)

    def test_graceful_skip_when_playwright_unavailable_or_disabled(self):
        from areos.auditors.rendering_auditor import audit_js_rendering
        with patch.dict(os.environ, {"AREOS_ENABLE_PLAYWRIGHT": "0"}):
            res = audit_js_rendering("https://example.com", "<html><body>Hello</body></html>")
            assert res.skipped is True
            assert "disabled" in res.reason or "installed" in res.reason

    def test_rendering_audit_result_structure(self):
        from areos.auditors.rendering_auditor import RenderingAuditResult, RenderingIssue
        issue = RenderingIssue(severity="warning", code="JS_CONTENT_DEPENDENCY", message="Diff test")
        res = RenderingAuditResult(url="https://example.com", passed=True, issues=[issue], diff_ratio=0.75)
        findings = res.as_finding_dicts()
        assert len(findings) == 1
        assert findings[0]["code"] == "JS_CONTENT_DEPENDENCY"
        assert findings[0]["check_type"] == "rendering"

    def test_requirements_and_render_yaml_have_playwright_references(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        req_path = os.path.join(root, "requirements.txt")
        with open(req_path, "r", encoding="utf-8") as f:
            req_text = f.read()
        assert "playwright" in req_text.lower()

        render_path = os.path.join(root, "render.yaml")
        with open(render_path, "r", encoding="utf-8") as f:
            render_text = f.read()
        assert "AREOS_ENABLE_PLAYWRIGHT" in render_text

    @patch("areos.auditors.rendering_auditor.PLAYWRIGHT_AVAILABLE", True)
    @patch("areos.auditors.rendering_auditor.sync_playwright")
    def test_js_critical_content_gated_detected(self, mock_playwright):
        from areos.auditors.rendering_auditor import audit_js_rendering
        # Raw HTML has almost no text; rendered DOM has full rich content (< 0.5 ratio)
        raw_html = "<html><body><div id='app'>Loading...</div></body></html>"
        rendered_text = "Citeable provides comprehensive AI search engineering, tracking, schema generation, and ranking analytics."

        mock_page = MagicMock()
        mock_page.evaluate.side_effect = lambda script: rendered_text if "innerText" in script else 0
        mock_ctx = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_ctx
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        with patch.dict(os.environ, {"AREOS_ENABLE_PLAYWRIGHT": "1"}):
            res = audit_js_rendering("https://example.com", raw_html)
            codes = [i.code for i in res.issues]
            assert "JS_CRITICAL_CONTENT_GATED" in codes
            assert res.passed is False

    @patch("areos.auditors.rendering_auditor.PLAYWRIGHT_AVAILABLE", True)
    @patch("areos.auditors.rendering_auditor.sync_playwright")
    def test_lazy_and_hidden_elements_detected(self, mock_playwright):
        from areos.auditors.rendering_auditor import audit_js_rendering
        raw_html = "<p>Standard matching page text paragraph.</p>"
        rendered_text = "Standard matching page text paragraph."

        mock_page = MagicMock()
        def eval_side_effect(script):
            if "innerText" in script:
                return rendered_text
            if "data-src" in script:
                return 12  # >5 lazy elements
            if "aria-expanded" in script:
                return 8   # >5 hidden elements
            return 0

        mock_page.evaluate.side_effect = eval_side_effect
        mock_ctx = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_ctx
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        with patch.dict(os.environ, {"AREOS_ENABLE_PLAYWRIGHT": "1"}):
            res = audit_js_rendering("https://example.com", raw_html)
            codes = [i.code for i in res.issues]
            assert "LAZY_LOAD_HIDDEN" in codes
            assert "HIDDEN_CONTENT_DEFAULT" in codes

    @patch("areos.auditors.rendering_auditor.PLAYWRIGHT_AVAILABLE", True)
    @patch("areos.auditors.rendering_auditor.sync_playwright")
    def test_rendering_ok_when_aligned(self, mock_playwright):
        from areos.auditors.rendering_auditor import audit_js_rendering
        raw_html = "<p>Completely matching clean static paragraph without hidden content.</p>"
        rendered_text = "Completely matching clean static paragraph without hidden content."

        mock_page = MagicMock()
        mock_page.evaluate.side_effect = lambda script: rendered_text if "innerText" in script else 0
        mock_ctx = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_ctx
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        with patch.dict(os.environ, {"AREOS_ENABLE_PLAYWRIGHT": "1"}):
            res = audit_js_rendering("https://example.com", raw_html)
            codes = [i.code for i in res.issues]
            assert "RENDERING_OK" in codes
            assert res.passed is True
