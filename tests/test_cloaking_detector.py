# tests/test_cloaking_detector.py
#
# Unit tests for areos.auditors.cloaking_detector (Task T-203)

import pytest
from areos.auditors.cloaking_detector import audit_cloaking, CloakingResult, CloakingIssue


def test_cloaking_detected(monkeypatch):
    """Word count diff > 50% must trigger CLOAKING_DETECTED with error severity."""
    monkeypatch.setattr(
        "areos.auditors.cloaking_detector.safe_get",
        lambda *a, **kw: type("obj", (object,), {"status_code": 200, "text": "<p>Short bot text</p>"})(),
    )
    long_browser_html = "<div>" + " ".join(["word"] * 50) + "</div>"
    res = audit_cloaking("test.com", "http://test.com", long_browser_html)
    assert any(i.code == "CLOAKING_DETECTED" for i in res.issues)
    assert not res.passed
    assert res.browser_word_count == 50
    assert res.bot_word_count == 3


def test_cloaking_suspected(monkeypatch):
    """Word count diff > 20% and <= 50% must trigger CLOAKING_SUSPECTED with warning severity."""
    monkeypatch.setattr(
        "areos.auditors.cloaking_detector.safe_get",
        lambda *a, **kw: type("obj", (object,), {"status_code": 200, "text": "<div>" + " ".join(["word"] * 75) + "</div>"})(),
    )
    browser_html = "<div>" + " ".join(["word"] * 100) + "</div>"
    res = audit_cloaking("test.com", "http://test.com", browser_html)
    assert any(i.code == "CLOAKING_SUSPECTED" for i in res.issues)
    assert res.passed
    assert res.browser_word_count == 100
    assert res.bot_word_count == 75


def test_bot_blocked_http(monkeypatch):
    """HTTP 403 response to AI bot must trigger AI_BOT_BLOCKED_HTTP error."""
    monkeypatch.setattr(
        "areos.auditors.cloaking_detector.safe_get",
        lambda *a, **kw: type("obj", (object,), {"status_code": 403, "text": ""})(),
    )
    res = audit_cloaking("test.com", "http://test.com", "<p>Normal browser text</p>")
    assert any(i.code == "AI_BOT_BLOCKED_HTTP" for i in res.issues)
    assert not res.passed


def test_cloaking_pass(monkeypatch):
    """Identical or near-identical text should pass with CLOAKING_OK."""
    monkeypatch.setattr(
        "areos.auditors.cloaking_detector.safe_get",
        lambda *a, **kw: type("obj", (object,), {"status_code": 200, "text": "<h1>Title</h1><p>Normal text content here.</p>"})(),
    )
    res = audit_cloaking("test.com", "http://test.com", "<h1>Title</h1><p>Normal text content here.</p>")
    assert res.passed
    assert any(i.code == "CLOAKING_OK" for i in res.issues)


def test_cloaking_fetch_failed(monkeypatch):
    """Network failure or exception during fetch should emit CLOAKING_FETCH_FAILED."""
    def raise_err(*a, **kw):
        raise ConnectionError("DNS failure")

    monkeypatch.setattr("areos.auditors.cloaking_detector.safe_get", raise_err)
    res = audit_cloaking("test.com", "http://test.com", "<p>Normal text</p>")
    assert any(i.code == "CLOAKING_FETCH_FAILED" for i in res.issues)
    assert res.passed  # fetch failure is info severity, not hard error


def test_missing_elements_detection(monkeypatch):
    """Missing headings in bot view should be listed in missing_elements."""
    bot_html = "<div>Just some paragraph text without the heading</div>"
    monkeypatch.setattr(
        "areos.auditors.cloaking_detector.safe_get",
        lambda *a, **kw: type("obj", (object,), {"status_code": 200, "text": bot_html})(),
    )
    browser_html = "<h1>Secret Heading For Humans</h1><div>" + " ".join(["word"] * 50) + "</div>"
    res = audit_cloaking("test.com", "http://test.com", browser_html)
    assert len(res.missing_elements) > 0
    assert any("Secret Heading For Humans" in el for el in res.missing_elements)
