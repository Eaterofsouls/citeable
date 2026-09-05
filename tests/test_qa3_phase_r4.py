import pytest
import yaml
from unittest.mock import patch, MagicMock

from areos.auditors.citation_sampler import sample_citations, CitationSampleResult, CitationObservation
from areos.auditors.schema_validator import validate_page_schemas
from areos.auditors.authority_auditor import fetch_open_pagerank


def test_circuit_breaker_triggers_on_http_500():
    """Verify circuit breaker increments failure count on HTTP 500 errors."""
    cb = {}

    with patch("areos.auditors.citation_sampler._query_perplexity", side_effect=Exception("HTTP 500 Internal Server Error")):
        with patch("areos.auditors.citation_sampler.time.sleep"):
            res = sample_citations(
                target_domain="example.com",
                prompt_set=["What is citeable?"],
                n_runs=1,
                engine="perplexity",
                api_key="test-key",
                circuit_breaker=cb,
                delay_seconds=0
            )
            assert cb.get("perplexity") == 1
            assert len(res.observations) == 1
            assert "HTTP 500" in res.observations[0].error


def test_circuit_breaker_resets_on_success():
    """Verify successful response resets circuit breaker failure count to 0."""
    cb = {"perplexity": 2}

    with patch("areos.auditors.citation_sampler._query_perplexity", return_value=(["https://example.com"], "snippet", "full text")):
        sample_citations(
            target_domain="example.com",
            prompt_set=["What is citeable?"],
            n_runs=1,
            engine="perplexity",
            api_key="test-key",
            circuit_breaker=cb,
            delay_seconds=0
        )
        assert cb.get("perplexity") == 0


def test_circuit_breaker_open_skips_call():
    """Verify open circuit breaker (>=3) skips network request immediately."""
    cb = {"perplexity": 3}

    with patch("areos.auditors.citation_sampler._query_perplexity") as mock_query:
        res = sample_citations(
            target_domain="example.com",
            prompt_set=["What is citeable?"],
            n_runs=1,
            engine="perplexity",
            api_key="test-key",
            circuit_breaker=cb,
            delay_seconds=0
        )
        mock_query.assert_not_called()
        assert "Circuit breaker open" in res.observations[0].error


def test_schema_validator_caps_json_ld_blocks_at_100():
    """Verify page with 250 JSON-LD blocks only parses the first 100 blocks."""
    blocks = [{"@type": "Organization", "name": f"Org {i}"} for i in range(250)]
    results = validate_page_schemas(blocks)
    assert len(results) == 100


def test_render_yaml_has_disk_block():
    """Verify render.yaml contains a persistent disk mount."""
    with open("render.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    service = data["services"][0]
    assert "disk" in service
    assert service["disk"]["mountPath"] == "/data"
    assert service["disk"]["sizeGB"] >= 1


def test_dockerfile_uvicorn_concurrency_limits():
    """Verify Dockerfile CMD specifies --limit-concurrency and --timeout-keep-alive."""
    with open("Dockerfile", "r", encoding="utf-8") as f:
        content = f.read()
    assert "--limit-concurrency 100" in content
    assert "--timeout-keep-alive 5" in content


def test_requirements_no_httpx_package():
    """Verify unused httpx package is removed from requirements.txt."""
    with open("requirements.txt", "r", encoding="utf-8") as f:
        content = f.read()
    assert "httpx==" not in content


def test_authority_auditor_bounded_read():
    """Verify fetch_open_pagerank passes a 5MB maximum byte limit to resp.read()."""
    with open("areos/auditors/authority_auditor.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "resp.read(5 * 1024 * 1024)" in content
