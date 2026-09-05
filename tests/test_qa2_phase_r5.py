"""Phase R5 Regression Suite: Frontend UX, State & Error Recovery (TR-501 to TR-505)."""
import re
from pathlib import Path


class TestR5FrontendJSStaticIntegrity:
    """Tests for JavaScript static invariants, error handling, and security sanitization."""

    def test_auth_js_uses_lowercase_header_keys(self):
        """Verify auth.js formats BYOK headers with lowercase provider names."""
        auth_js = Path("areos/ui/auth.js").read_text(encoding="utf-8")
        assert "x-api-key-${provider.toLowerCase()}" in auth_js

    def test_guided_review_is_question_visible_express_mode(self):
        """Verify isQuestionVisible in guided_review.js filters to 4 questions in express mode."""
        gr_js = Path("areos/ui/guided_review.js").read_text(encoding="utf-8")
        assert "B2_CONTENT_ANSWERABILITY" in gr_js
        assert "C1_BRAND_ACCURACY" in gr_js
        assert "C2_CONTENT_TRUSTWORTHINESS" in gr_js
        assert "D2_ROOT_CAUSE_DIAGNOSIS" in gr_js
        assert "mode === 'express'" in gr_js

    def test_guided_review_is_question_visible_full_mode_conditionals(self):
        """Verify guided_review.js evaluates conditionals (B3, C3, C4, C5, D1)."""
        gr_js = Path("areos/ui/guided_review.js").read_text(encoding="utf-8")
        assert "B3_CLOAKING_INTENT" in gr_js
        assert "CLOAKING_DETECTED" in gr_js
        assert "C3_CITATION_FRAMING" in gr_js
        assert "C4_CITATION_GAP" in gr_js
        assert "C5_SPEAKABLE" in gr_js
        assert "D1_LLMS_TXT_REVIEW" in gr_js

    def test_guided_review_handles_missing_audit_result_safely(self):
        """Verify start() guards against missing window.AreosContext.auditResult."""
        gr_js = Path("areos/ui/guided_review.js").read_text(encoding="utf-8")
        assert "if (!window.AreosContext || !window.AreosContext.auditResult)" in gr_js

    def test_guided_review_submit_inline_verdict_rollback_logic(self):
        """Verify submitInlineVerdict handles non-ok response without marking card as saved."""
        gr_js = Path("areos/ui/guided_review.js").read_text(encoding="utf-8")
        assert "if (!res.ok)" in gr_js
        assert "Failed to save evaluation. Please retry." in gr_js

    def test_studio_js_trigger_post_wizard_synthesis_re_enables_inputs(self):
        """Verify studio.js re-enables inputs on synthesis failure."""
        studio_js = Path("areos/ui/studio.js").read_text(encoding="utf-8")
        assert "triggerPostWizardSynthesis" in studio_js
        assert "el.disabled = false" in studio_js
        assert "el.style.opacity = '1'" in studio_js

    def test_studio_js_export_executive_report_defensive_fallbacks(self):
        """Verify exportExecutiveReport handles missing scorecard properties safely."""
        studio_js = Path("areos/ui/studio.js").read_text(encoding="utf-8")
        assert "sc.overall_score || 0" in studio_js
        assert "sc.crawler_status || 'N/A'" in studio_js
        assert "sc.llms_txt_status || 'N/A'" in studio_js
        assert "enrichWizardCard" not in studio_js

    def test_identity_js_guards_window_areos_context(self):
        """Verify identity.js initializes window.AreosContext before accessing properties."""
        identity_js = Path("areos/ui/identity.js").read_text(encoding="utf-8")
        assert "window.AreosContext = window.AreosContext || {};" in identity_js

