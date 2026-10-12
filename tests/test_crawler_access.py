import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")

from areos.api.main import app
from areos.auditors.robots_checker import parse_robots_txt, parse_llms_txt


@pytest.fixture
def client():
    return TestClient(app)


def test_robots_txt_allows_claude_crawlers(client):
    """Test that /robots.txt returns 200 and explicitly permits ClaudeBot, Claude-User, and anthropic-ai."""
    response = client.get("/robots.txt", headers={"User-Agent": "ClaudeBot/1.0; +claudebot@anthropic.com"})
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")

    content = response.text
    assert "User-agent: ClaudeBot" in content
    assert "User-agent: Claude-User" in content
    assert "User-agent: anthropic-ai" in content

    # Parse with Citeable's own robots auditor
    result = parse_robots_txt(content)
    assert not any(i.severity == "error" for i in result.issues), "robots.txt must not yield any errors"

    # Verify Anthropic crawlers are not blocked
    for crawler in ["ClaudeBot", "Claude-User", "anthropic-ai"]:
        directive = result.effective_policy(crawler)
        assert directive is not None, f"Directive missing for {crawler}"
        assert not directive.is_fully_blocked, f"{crawler} must not be blocked"
        assert directive.is_fully_allowed, f"{crawler} should be fully allowed"


def test_llms_txt_structure_and_links(client):
    """Test that /llms.txt returns 200 and passes llmstxt.org validation."""
    response = client.get("/llms.txt", headers={"User-Agent": "Claude-User"})
    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")

    content = response.text
    result = parse_llms_txt(content)

    assert result.present is True
    assert result.has_h1 is True
    assert len(result.sections) >= 4
    # Ensure zero error-level issues
    error_issues = [i for i in result.issues if i.severity == "error"]
    assert not error_issues, f"llms.txt has errors: {error_issues}"


def test_sitemap_xml_validity(client):
    """Test that /sitemap.xml returns 200 and valid XML referencing public pages."""
    response = client.get("/sitemap.xml", headers={"User-Agent": "ClaudeBot/1.0"})
    assert response.status_code == 200
    assert "xml" in response.headers.get("content-type", "")

    content = response.text
    assert "<urlset" in content
    assert "<loc>" in content
    assert "/docs/external.md" in content


def test_docs_external_publicly_crawlable(client):
    """Test that /docs/external.md returns 200 OK without requiring authentication."""
    response = client.get("/docs/external.md", headers={"User-Agent": "ClaudeBot/1.0"})
    assert response.status_code == 200
    assert len(response.text) > 1000
    assert "Citeable" in response.text


def test_cors_allows_claude_ai(client):
    """Test that CORS allows requests originating from claude.ai and anthropic.com."""
    # GET request with Origin
    res = client.get("/api/health", headers={"Origin": "https://claude.ai"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://claude.ai"

    # Preflight OPTIONS
    options_res = client.options(
        "/api/health",
        headers={
            "Origin": "https://claude.ai",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert options_res.status_code == 200
    assert options_res.headers.get("access-control-allow-origin") == "https://claude.ai"

    # Anthropic subdomain
    sub_res = client.get("/api/health", headers={"Origin": "https://research.anthropic.com"})
    assert sub_res.headers.get("access-control-allow-origin") == "https://research.anthropic.com"
