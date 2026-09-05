import os
import math
import pytest
from unittest.mock import patch, MagicMock
import requests

from areos.util.ssrf import safe_get
from areos.kb.embeddings import cosine_similarity, _google_embed
from areos.llm.providers import _gemini_call


def test_ssrf_history_chain_populated():
    """Verify safe_get records all intermediate redirect hops in resp.history."""
    r1 = requests.Response()
    r1.status_code = 302
    r1.headers["Location"] = "https://example.com/step2"

    r2 = requests.Response()
    r2.status_code = 200
    r2.raw = MagicMock()
    r2.iter_content = MagicMock(return_value=[b"final content"])

    with patch("areos.util.ssrf.resolve_and_validate", return_value="93.184.216.34"):
        with patch("requests.Session.get", side_effect=[r1, r2]):
            resp = safe_get("https://example.com/step1", max_redirects=3)
            assert resp.status_code == 200
            assert len(resp.history) == 1
            assert resp.history[0].status_code == 302


def test_ssrf_history_empty_on_direct_fetch():
    """Verify safe_get returns an empty history when no redirects occur."""
    r = requests.Response()
    r.status_code = 200
    r.raw = MagicMock()
    r.iter_content = MagicMock(return_value=[b"direct page"])

    with patch("areos.util.ssrf.resolve_and_validate", return_value="93.184.216.34"):
        with patch("requests.Session.get", return_value=r):
            resp = safe_get("https://example.com/page")
            assert resp.status_code == 200
            assert resp.history == []


def test_dom_escape_html_quotes():
    """Verify HTML escaping logic covers double and single quotes."""
    with open("areos/ui/dom.js", "r", encoding="utf-8") as f:
        content = f.read()
    assert "&quot;" in content
    assert "&#039;" in content


def test_dom_safe_url_quote_injection():
    """Verify safeUrl runs returned URLs through escapeHtml."""
    with open("areos/ui/dom.js", "r", encoding="utf-8") as f:
        content = f.read()
    assert "return escapeHtml(url);" in content


def test_nav_cmdk_single_quote_kid_xss():
    """Verify nav.js encodes single quotes in kid URL parameters."""
    with open("areos/ui/nav.js", "r", encoding="utf-8") as f:
        content = f.read()
    assert "encodeURIComponent(c.kid).replace(/'/g, '%27')" in content


def test_studio_claim_href_sanitized():
    """Verify studio.js safely encodes and escapes governing_claim_id."""
    with open("areos/ui/studio.js", "r", encoding="utf-8") as f:
        content = f.read()
    assert "encodeURIComponent(rec.governing_claim_id || '').replace(/'/g, '%27')" in content


def test_embeddings_gemini_header_auth():
    """Verify _google_embed passes api_key via header rather than URL query."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": {"values": [0.1, 0.2, 0.3]}}

    with patch("areos.kb.embeddings._retry_post", return_value=mock_resp) as mock_post:
        res = _google_embed("secret_gemini_key", "test statement")
        assert res == [0.1, 0.2, 0.3]
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "?key=" not in args[0]
        assert kwargs["headers"].get("x-goog-api-key") == "secret_gemini_key"


def test_embeddings_cosine_similarity_nan_rejection():
    """Verify cosine_similarity safely returns 0.0 when given NaN values."""
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, float("nan"), 3.0]
    sim = cosine_similarity(v1, v2)
    assert sim == 0.0
    assert not math.isnan(sim)
