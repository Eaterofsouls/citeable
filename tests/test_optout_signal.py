"""
tests/test_optout_signal.py

Unit tests for WP-4.3:
- Detection of <meta name="robots" content="noarchive">
- Detection of <meta name="bingbot" content="nocache">
- Severity is 'info' and score deduction is exactly 0
"""

import pytest
from areos.auditors.redirect_auditor import audit_redirects_and_access
from areos.auditors.scoring import compute_layered_score


def test_meta_robots_noarchive_fires_info_zero_deduction():
    """
    WP-4.3 Checkpoint 2:
    Page containing <meta name="robots" content="noarchive"> emits
    AI_OPTOUT_SIGNAL_PRESENT with severity 'info' and 0 point deduction.
    """
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="robots" content="noarchive">
        <link rel="canonical" href="https://example.com/">
      </head>
      <body>
        <p>Sample content</p>
      </body>
    </html>
    """
    result = audit_redirects_and_access("https://example.com", html=html)
    optout_issues = [i for i in result.issues if i.code == "AI_OPTOUT_SIGNAL_PRESENT"]
    assert len(optout_issues) == 1, f"Expected 1 AI_OPTOUT_SIGNAL_PRESENT, got {result.issues}"
    issue = optout_issues[0]
    assert issue.severity == "info"
    assert "Bing Chat/Copilot answers and training" in issue.message

    # Score verification: must contribute 0 deduction
    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)
    assert scorecard.sub_scores["access"].score == 20  # full 20 points intact
    # Flat breakdown should not deduct points
    optout_deductions = [d for d in scorecard.sub_scores["access"].deductions if d["code"] == "AI_OPTOUT_SIGNAL_PRESENT"]
    assert len(optout_deductions) == 0  # 0 pts deduction is skipped from active deductions ledger


def test_meta_bingbot_nocache_fires_info():
    """Verify <meta name="bingbot" content="nocache"> triggers the opt-out signal."""
    html = """
    <html>
      <head>
        <meta name="bingbot" content="nocache">
        <link rel="canonical" href="https://example.com/">
      </head>
      <body><p>Content</p></body>
    </html>
    """
    result = audit_redirects_and_access("https://example.com", html=html)
    optout_issues = [i for i in result.issues if i.code == "AI_OPTOUT_SIGNAL_PRESENT"]
    assert len(optout_issues) == 1
    assert optout_issues[0].severity == "info"


def test_meta_robots_comma_separated_directives():
    """Verify comma-separated directive list containing noarchive is properly recognized."""
    html = """
    <html>
      <head>
        <meta name="robots" content="index, follow, noarchive, max-snippet:-1">
        <link rel="canonical" href="https://example.com/">
      </head>
      <body><p>Content</p></body>
    </html>
    """
    result = audit_redirects_and_access("https://example.com", html=html)
    optout_issues = [i for i in result.issues if i.code == "AI_OPTOUT_SIGNAL_PRESENT"]
    assert len(optout_issues) == 1
    assert optout_issues[0].severity == "info"


def test_standard_robots_does_not_fire_optout():
    """Standard index/follow directives must not trigger the opt-out signal."""
    html = """
    <html>
      <head>
        <meta name="robots" content="index, follow">
        <link rel="canonical" href="https://example.com/">
      </head>
      <body><p>Content</p></body>
    </html>
    """
    result = audit_redirects_and_access("https://example.com", html=html)
    optout_issues = [i for i in result.issues if i.code == "AI_OPTOUT_SIGNAL_PRESENT"]
    assert len(optout_issues) == 0
