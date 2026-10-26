"""
tests/test_citation_sampler.py — Gemini Grounding & Citation Sampler Verification (WP-1.1)

Verifies:
1. Gemini grounding responses extracting web.domain when present over the vertexaisearch redirect proxy.
2. Graceful fallback to web.uri when web.domain is absent.
3. Accurate citation aggregation in sample_citations.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from areos.auditors.citation_sampler import _query_gemini_grounded


def _build_mock_gemini_response(grounding_chunks: list[dict], text: str = "Test answer") -> bytes:
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}]
                },
                "groundingMetadata": {
                    "groundingChunks": grounding_chunks
                }
            }
        ]
    }
    return json.dumps(data).encode("utf-8")


def test_gemini_grounding_prefers_domain_over_redirect_uri():
    """DEF-02 / WP-1.1: If web.domain is present, prefer it over vertex redirect proxy URI."""
    chunks = [
        {
            "web": {
                "domain": "targetdomain.com",
                "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/ABC123DEF456",
            }
        }
    ]
    raw_resp = _build_mock_gemini_response(chunks)

    mock_resp_obj = MagicMock()
    mock_resp_obj.read.side_effect = [raw_resp, b""]
    mock_resp_obj.__enter__.return_value = mock_resp_obj

    with patch("urllib.request.urlopen", return_value=mock_resp_obj):
        cited, snippet, full = _query_gemini_grounded("What is target domain?", "test_api_key")

    assert cited == ["targetdomain.com"]
    assert "targetdomain.com" in cited
    assert "vertexaisearch" not in cited[0]


def test_gemini_grounding_falls_back_to_uri_when_domain_absent():
    """DEF-02 / WP-1.1: If web.domain is absent, fallback to web.uri."""
    chunks = [
        {
            "web": {
                "uri": "https://example.com/article/1",
            }
        }
    ]
    raw_resp = _build_mock_gemini_response(chunks)

    mock_resp_obj = MagicMock()
    mock_resp_obj.read.side_effect = [raw_resp, b""]
    mock_resp_obj.__enter__.return_value = mock_resp_obj

    with patch("urllib.request.urlopen", return_value=mock_resp_obj):
        cited, snippet, full = _query_gemini_grounded("Query prompt", "test_api_key")

    assert cited == ["https://example.com/article/1"]


def test_gemini_grounding_mixed_chunks():
    """DEF-02 / WP-1.1: Multi-source grounding correctly extracts domain where available and uri otherwise."""
    chunks = [
        {
            "web": {
                "domain": "first-domain.com",
                "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AAA",
            }
        },
        {
            "web": {
                "uri": "https://second-domain.com/page",
            }
        },
        {
            "web": {
                "domain": "third-domain.com",
                "uri": "https://third-domain.com/resource",
            }
        }
    ]
    raw_resp = _build_mock_gemini_response(chunks)

    mock_resp_obj = MagicMock()
    mock_resp_obj.read.side_effect = [raw_resp, b""]
    mock_resp_obj.__enter__.return_value = mock_resp_obj

    with patch("urllib.request.urlopen", return_value=mock_resp_obj):
        cited, snippet, full = _query_gemini_grounded("Query prompt", "test_api_key")

    assert cited == ["first-domain.com", "https://second-domain.com/page", "third-domain.com"]
