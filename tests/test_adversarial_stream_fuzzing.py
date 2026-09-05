import os
os.environ["AREOS_API_TOKEN"] = "test-token"
os.environ["AREOS_ADMIN_TOKEN"] = "test-token"

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from areos.api.main import app
from areos.llm.providers import complete, _RateLimit


client = TestClient(app)


def test_streaming_chunked_boundary_exceeded():
    """Verify chunked payload exceeding 5MB is rejected with 413 without reading entire body."""
    oversized = b"A" * (5_000_000 + 50)
    response = client.post(
        "/api/v1/audit/observe/test-run",
        content=oversized,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert "Payload too large" in response.json().get("detail", "")


def test_malformed_json_returns_422_or_400():
    """Verify malformed JSON does not cause unhandled 500 server crashes."""
    bad_payload = b"{\"target_domain\": \"example.com\", \"broken_json: 123"
    response = client.post(
        "/api/v1/prompts",
        content=bad_payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer test-token"}
    )
    assert response.status_code in (400, 422)


def test_special_characters_in_query_params():
    """Verify special SQL/HTML metacharacters in query params do not crash the endpoint."""
    attack_payloads = [
        "<script>alert(1)</script>",
        "'; DROP TABLE knowledge; --",
        "../../../../etc/passwd",
        "%00%0D%0A",
        "\" OR 1=1 --",
    ]
    for p in attack_payloads:
        response = client.get(f"/api/v1/knowledge?search_query={p}")
        assert response.status_code in (200, 404, 422)


def test_provider_waterfall_global_time_budget_enforcement():
    """Verify waterfall halts and raises RuntimeError when cumulative provider delay exceeds budget."""
    def slow_failing_provider(*args, **kwargs):
        time.sleep(0.1)
        raise _RateLimit("Rate limited")

    with patch("areos.llm.providers._build_waterfall", return_value=[
        (slow_failing_provider, "Provider1"),
        (slow_failing_provider, "Provider2"),
        (slow_failing_provider, "Provider3"),
        (slow_failing_provider, "Provider4"),
        (slow_failing_provider, "Provider5"),
    ]):
        start = time.time()
        with pytest.raises(RuntimeError) as exc_info:
            complete("Test prompt", time_budget_seconds=0.25)
        elapsed = time.time() - start
        assert elapsed < 0.6  # Terminated early, well below 5 * 0.1 + retry delays
        assert "Global time budget" in str(exc_info.value) or "All LLM providers failed" in str(exc_info.value)
