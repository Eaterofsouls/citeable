"""
tests/test_rate_limiter_spoofing.py — Rate-Limiter Trusted Proxy & Spoofing Defense (WP-0.2)

Verifies that:
1. Attackers cannot bypass rate limits by rotating arbitrary X-Forwarded-For headers.
2. Requests from the same peer IP with different X-Forwarded-For headers share a single rate-limit bucket.
3. Authenticated requests (Bearer / BYOK) are properly keyed to caller credentials.
"""

import os
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException, Request
from areos.api.routers.audit import _rate_limit, _get_client_identity as _audit_client_id, _ip_buckets
from areos.api.routers.byok import check_byok_rate_limit, _get_client_identity as _byok_client_id, _byok_ip_buckets


class DummyClient:
    def __init__(self, host: str):
        self.host = host


class DummyRequest:
    def __init__(self, host: str = "198.51.100.5", headers: dict | None = None):
        self.client = DummyClient(host)
        self.headers = headers or {}


def test_rate_limiter_shares_bucket_across_spoofed_forwarded_headers():
    """Verify that requests from the same peer with different X-Forwarded-For share one bucket."""
    _ip_buckets.clear()

    req1 = DummyRequest(host="203.0.113.10", headers={"x-forwarded-for": "1.1.1.1"})
    req2 = DummyRequest(host="203.0.113.10", headers={"x-forwarded-for": "2.2.2.2"})
    req3 = DummyRequest(host="203.0.113.10", headers={"x-forwarded-for": "3.3.3.3"})
    req4 = DummyRequest(host="203.0.113.10", headers={"x-forwarded-for": "4.4.4.4"})

    # Bucket limit of 3
    _rate_limit(req1, bucket_prefix="orchestrate_spoof_test", limit=3, window_seconds=60)
    _rate_limit(req2, bucket_prefix="orchestrate_spoof_test", limit=3, window_seconds=60)
    _rate_limit(req3, bucket_prefix="orchestrate_spoof_test", limit=3, window_seconds=60)

    # All 3 calls should have accumulated in the same bucket keyed by the peer host
    key = "orchestrate_spoof_test:ip:203.0.113.10"
    assert key in _ip_buckets
    assert len(_ip_buckets[key]) == 3

    # 4th request must be rejected with 429 even though it provides a brand new X-Forwarded-For
    with pytest.raises(HTTPException) as exc_info:
        _rate_limit(req4, bucket_prefix="orchestrate_spoof_test", limit=3, window_seconds=60)
    assert exc_info.value.status_code == 429


def test_byok_rate_limiter_shares_bucket_across_spoofed_forwarded_headers():
    """Verify check_byok_rate_limit also cannot be bypassed via X-Forwarded-For rotation."""
    _byok_ip_buckets.clear()

    peer_host = "192.0.2.77"
    for i in range(15):
        req = DummyRequest(host=peer_host, headers={"x-forwarded-for": f"10.99.{i}.1"})
        check_byok_rate_limit(req)

    # 16th request must trigger 429
    req_blocked = DummyRequest(host=peer_host, headers={"x-forwarded-for": "10.99.100.1"})
    with pytest.raises(HTTPException) as exc_info:
        check_byok_rate_limit(req_blocked)
    assert exc_info.value.status_code == 429


def test_client_identity_bearer_token_isolation():
    """Verify that clients sending valid Authorization tokens are keyed by their token hash."""
    req_token_a = DummyRequest(host="10.0.0.1", headers={"authorization": "Bearer token-aaa"})
    req_token_b = DummyRequest(host="10.0.0.2", headers={"authorization": "Bearer token-bbb"})
    req_token_a_diff_ip = DummyRequest(host="10.0.0.99", headers={"authorization": "Bearer token-aaa"})

    id_a = _audit_client_id(req_token_a)
    id_b = _audit_client_id(req_token_b)
    id_a2 = _audit_client_id(req_token_a_diff_ip)

    assert id_a.startswith("auth:")
    assert id_b.startswith("auth:")
    assert id_a != id_b
    # Same token from different IP shares the auth identity
    assert id_a == id_a2
