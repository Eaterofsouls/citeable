"""
tests/test_host_block_prober.py

Unit and integration tests for WP-4.2:
- Host-block probing with AI crawler user-agents
- AI_CRAWLER_HOST_BLOCKED emission on 403, 429, 5xx
- Scoring deduction (-8 pts in Access layer)
- AUDIT_PHASE_CRASHED resilience when host block prober crashes
"""

from unittest.mock import MagicMock, patch
import pytest

from areos.auditors.host_block_prober import probe_host_blocks
from areos.auditors.scoring import compute_layered_score
from areos.auditors.audit_orchestrator import run_orchestrated_audit


def _make_mock_response(status_code: int):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "Mock Content"
    resp.url = "https://example.com"
    resp.history = []
    return resp


def test_host_block_prober_emits_ai_crawler_host_blocked_when_bot_gets_429():
    """
    WP-4.2 Checkpoint 2:
    When one bot UA (e.g. ClaudeBot) receives HTTP 429 while control is 200,
    emit AI_CRAWLER_HOST_BLOCKED with severity 'error' naming ClaudeBot.
    """
    def mock_safe_get(url, timeout=3.0, headers=None, **kwargs):
        ua = (headers or {}).get("User-Agent", "")
        if "ClaudeBot" in ua:
            return _make_mock_response(429)
        return _make_mock_response(200)

    with patch("areos.auditors.host_block_prober.safe_get", side_effect=mock_safe_get):
        result = probe_host_blocks("https://example.com", control_status=200)

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "AI_CRAWLER_HOST_BLOCKED"
    assert issue.severity == "error"
    assert "ClaudeBot (HTTP 429)" in issue.message
    assert result.blocked_bots == {"ClaudeBot": 429}


def test_host_block_prober_multiple_bots_blocked_with_different_codes():
    """
    Verify multiple blocked bots (e.g. 403 and 503) are aggregated into a single issue.
    """
    def mock_safe_get(url, timeout=3.0, headers=None, **kwargs):
        ua = (headers or {}).get("User-Agent", "")
        if "GPTBot" in ua:
            return _make_mock_response(403)
        if "OAI-SearchBot" in ua:
            return _make_mock_response(503)
        return _make_mock_response(200)

    with patch("areos.auditors.host_block_prober.safe_get", side_effect=mock_safe_get):
        result = probe_host_blocks("https://example.com", control_status=200)

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "AI_CRAWLER_HOST_BLOCKED"
    assert "GPTBot (HTTP 403)" in issue.message
    assert "OAI-SearchBot (HTTP 503)" in issue.message
    assert result.blocked_bots == {"GPTBot": 403, "OAI-SearchBot": 503}


def test_host_block_prober_all_200_emits_no_issues():
    """When all bots succeed with 200, no issues should be emitted."""
    with patch("areos.auditors.host_block_prober.safe_get", return_value=_make_mock_response(200)):
        result = probe_host_blocks("https://example.com", control_status=200)

    assert len(result.issues) == 0
    assert len(result.blocked_bots) == 0


def test_host_block_prober_ignored_when_control_status_not_2xx():
    """
    If control status is not 2xx (e.g. site down or global 503), do not emit host block findings.
    """
    with patch("areos.auditors.host_block_prober.safe_get", return_value=_make_mock_response(429)):
        result = probe_host_blocks("https://example.com", control_status=503)

    assert len(result.issues) == 0


def test_host_block_prober_scoring_deduction():
    """
    Verify AI_CRAWLER_HOST_BLOCKED deducts exactly 8 points in the Access layer.
    """
    scorecard = compute_layered_score([{"code": "AI_CRAWLER_HOST_BLOCKED"}])
    access = scorecard.sub_scores["access"]
    assert access.score == 12  # 20 - 8
    deductions = [d for d in access.deductions if d["code"] == "AI_CRAWLER_HOST_BLOCKED"]
    assert len(deductions) == 1
    assert deductions[0]["points"] == -8


def test_host_block_prober_network_timeouts_handled_gracefully():
    """
    If probe requests time out or raise connection exceptions, they should not trigger host blocks.
    """
    with patch("areos.auditors.host_block_prober.safe_get", side_effect=TimeoutError("Request timed out")):
        result = probe_host_blocks("https://example.com", control_status=200)

    assert len(result.issues) == 0
    assert len(result.blocked_bots) == 0


def test_orchestrator_host_block_prober_crash_caught_by_audit_phase_crashed(tmp_path, monkeypatch):
    """
    WP-4.2 Checkpoint 3:
    When probe_host_blocks crashes with an unhandled exception, the orchestrator
    catches it via try/except -> AUDIT_PHASE_CRASHED and completes the audit run.
    """
    from areos.db.migrate_audit_tables import migrate

    test_db = tmp_path / "test_areos.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    sample_html = "<html><body><h1>Sample Heading</h1><p>Sample body text with sufficient word count for extraction.</p></body></html>"

    with patch("areos.auditors.host_block_prober.probe_host_blocks", side_effect=RuntimeError("Simulated prober crash")):
        res = run_orchestrated_audit(
            "example.com",
            db_path=test_db,
            sample_content=sample_html,
        )

    assert "executive_scorecard" in res
    findings = res.get("raw_findings", [])
    crashed = [f for f in findings if f.get("code") == "AUDIT_PHASE_CRASHED" and "Host block prober phase failed" in f.get("message", "")]
    assert len(crashed) == 1, f"Expected AUDIT_PHASE_CRASHED for host block prober, got {findings}"
    assert crashed[0]["severity"] == "error"

