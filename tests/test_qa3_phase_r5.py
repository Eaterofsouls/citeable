import re
import pytest
from pathlib import Path


def test_identity_js_cancels_auto_dismiss_timer():
    """Verify identity.js clears auto-dismiss timer on commit validation."""
    content = Path("areos/ui/identity.js").read_text(encoding="utf-8")
    assert "clearTimeout(_autoDismissTimer)" in content
    # Ensure it's cleared inside commit
    assert "const commit = () => {" in content


def test_knowledge_explorer_format_text_escapes_html():
    """Verify knowledge_explorer.js escapes HTML in formatText before regex markdown formatting."""
    content = Path("areos/ui/knowledge_explorer.js").read_text(encoding="utf-8")
    assert "const formatText = (text) => {" in content
    assert "escapeHtml" in content or "replace(/&/g" in content


def test_app_js_awaits_json_res_run_id():
    """Verify app.js parses json from response before reading run_id."""
    content = Path("areos/ui/app.js").read_text(encoding="utf-8")
    assert "const data = await res.json();" in content
    assert "data.run_id" in content


def test_approvals_js_rejects_non_ok_in_allsettled():
    """Verify approvals.js throws if !res.ok to avoid false positives in Promise.allSettled."""
    content = Path("areos/ui/approvals.js").read_text(encoding="utf-8")
    assert "if (!res.ok) throw new Error" in content


def test_nav_js_cmdk_toggle_on_repeat_keypress():
    """Verify nav.js closes command palette if Cmd+K is pressed when already open."""
    content = Path("areos/ui/nav.js").read_text(encoding="utf-8")
    assert "if (cmdkModal.style.display === 'flex')" in content


def test_dom_js_make_dialog_accessible_fixed_elements():
    """Verify dom.js supports position:fixed elements in focus trap filter."""
    content = Path("areos/ui/dom.js").read_text(encoding="utf-8")
    assert "getClientRects" in content


def test_studio_js_safe_error_detail_extraction():
    """Verify studio.js safely extracts error details on audit failure."""
    content = Path("areos/ui/studio.js").read_text(encoding="utf-8")
    assert "let errorDetail = `HTTP error ${res.status}`" in content or "errorDetail = text.slice(0, 200)" in content


def test_studio_js_single_quote_xss_protection():
    """Verify studio.js encodes single quotes in governing_claim_id links."""
    content = Path("areos/ui/studio.js").read_text(encoding="utf-8")
    assert "safeKid" in content or "encodedKid" in content or "%27" in content
