"""
tests/test_robots.py

Unit tests for robots.txt parser and crawler access auditing:
- WP-1.5 / VAL-01: CRAWLER_PARTIAL path-sensitivity and single emission
- Access gate capping behavior (65 soft cap on partial block, 25 hard cap on full block)
"""

import pytest
from areos.auditors.robots_checker import (
    parse_robots_txt,
    _NON_SIGNIFICANT_DISALLOW_PATHS,
    AI_CRAWLERS,
)
from areos.auditors.scoring import compute_layered_score


def test_robots_disallow_admin_no_crawler_partial_and_no_access_gate_cap():
    """
    VAL-01 / WP-1.5 Checkpoint 2(a):
    A robots.txt with only Disallow: /admin for all crawlers must yield 0 CRAWLER_PARTIAL
    findings and must NOT trigger the 65 access gate cap.
    """
    robots_txt = """
User-agent: *
Disallow: /admin
Disallow: /wp-admin/
Disallow: /login/
Disallow: /checkout
Disallow: /cart/
"""
    result = parse_robots_txt(robots_txt)
    partial_issues = [i for i in result.issues if i.code == "CRAWLER_PARTIAL"]
    assert len(partial_issues) == 0, f"Expected 0 CRAWLER_PARTIAL issues, got: {partial_issues}"

    # Score with compute_layered_score
    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)

    assert scorecard.access_gate_applied is False
    assert scorecard.access_gate_cap is None
    assert scorecard.overall_score > 65


def test_robots_disallow_blog_single_crawler_partial_and_access_gate_caps_at_65():
    """
    VAL-01 / WP-1.5 Checkpoint 2(b):
    A robots.txt with Disallow: /blog for one crawler yields exactly one CRAWLER_PARTIAL
    finding total (not multiple), and the 65-cap still applies in scoring.
    """
    robots_txt = """
User-agent: GPTBot
Disallow: /blog
"""
    result = parse_robots_txt(robots_txt)
    partial_issues = [i for i in result.issues if i.code == "CRAWLER_PARTIAL"]
    assert len(partial_issues) == 1, f"Expected exactly 1 CRAWLER_PARTIAL issue, got: {partial_issues}"
    assert "GPTBot" in partial_issues[0].message
    assert "/blog" in partial_issues[0].message

    # Score with compute_layered_score
    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)

    assert scorecard.access_gate_applied is True
    assert scorecard.access_gate_cap == 65
    assert scorecard.overall_score <= 65


def test_robots_multiple_crawlers_with_disallows_emits_crawler_partial_at_most_once():
    """
    VAL-01 / WP-1.5 Part B:
    Disallows across multiple AI crawlers must aggregate and emit CRAWLER_PARTIAL
    at most ONCE per audit run.
    """
    robots_txt = """
User-agent: GPTBot
Disallow: /articles/

User-agent: ClaudeBot
Disallow: /news/

User-agent: PerplexityBot
Disallow: /research/

User-agent: CCBot
Disallow: /content/
"""
    result = parse_robots_txt(robots_txt)
    partial_issues = [i for i in result.issues if i.code == "CRAWLER_PARTIAL"]
    assert len(partial_issues) == 1, f"Expected exactly 1 CRAWLER_PARTIAL issue, got {len(partial_issues)}"

    msg = partial_issues[0].message
    assert "GPTBot" in msg and "/articles/" in msg
    assert "ClaudeBot" in msg and "/news/" in msg
    assert "PerplexityBot" in msg and "/research/" in msg
    assert "CCBot" in msg and "/content/" in msg


def test_robots_multiple_crawlers_fully_blocked_emits_crawler_fully_blocked_at_most_once():
    """
    VAL-01 / WP-1.5 Part B:
    CRAWLER_FULLY_BLOCKED must also emit at most once across all blocked crawlers,
    capping score at 25.
    """
    robots_txt = """
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: PerplexityBot
Disallow: /
"""
    result = parse_robots_txt(robots_txt)
    blocked_issues = [i for i in result.issues if i.code == "CRAWLER_FULLY_BLOCKED"]
    assert len(blocked_issues) == 1, f"Expected exactly 1 CRAWLER_FULLY_BLOCKED issue, got {len(blocked_issues)}"

    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)

    assert scorecard.access_gate_applied is True
    assert scorecard.access_gate_cap == 25
    assert scorecard.overall_score <= 25


def test_all_non_significant_paths_individually_ignored():
    """
    Verify every path in _NON_SIGNIFICANT_DISALLOW_PATHS is ignored and does not trigger CRAWLER_PARTIAL.
    """
    for path in _NON_SIGNIFICANT_DISALLOW_PATHS:
        robots_txt = f"User-agent: GPTBot\nDisallow: {path}\n"
        result = parse_robots_txt(robots_txt)
        partial_issues = [i for i in result.issues if i.code == "CRAWLER_PARTIAL"]
        assert len(partial_issues) == 0, f"Path '{path}' incorrectly triggered CRAWLER_PARTIAL"


def test_search_crawler_blocked_distinction():
    """
    WP-4.1: AI Crawler role differentiation.
    Blocking a search-indexing bot (OAI-SearchBot) while allowing training (GPTBot)
    must emit SEARCH_CRAWLER_BLOCKED (severity="error") and CRAWLER_FULLY_BLOCKED
    mentioning OAI-SearchBot, but NOT GPTBot.
    Scoring must apply a 10-point deduction in the Access layer for SEARCH_CRAWLER_BLOCKED.
    """
    robots_txt = """
User-agent: OAI-SearchBot
Disallow: /

User-agent: GPTBot
Allow: /
"""
    result = parse_robots_txt(robots_txt)
    search_blocked_issues = [i for i in result.issues if i.code == "SEARCH_CRAWLER_BLOCKED"]
    assert len(search_blocked_issues) == 1, f"Expected 1 SEARCH_CRAWLER_BLOCKED, got {search_blocked_issues}"
    assert search_blocked_issues[0].severity == "error"
    assert "OAI-SearchBot" in search_blocked_issues[0].message

    fully_blocked_issues = [i for i in result.issues if i.code == "CRAWLER_FULLY_BLOCKED"]
    assert len(fully_blocked_issues) == 1
    assert "OAI-SearchBot" in fully_blocked_issues[0].message
    assert "GPTBot" not in fully_blocked_issues[0].message

    allowed_issues = [i for i in result.issues if i.code == "CRAWLER_ALLOWED"]
    assert any("GPTBot" in i.message for i in allowed_issues)

    # Test direct score deduction for SEARCH_CRAWLER_BLOCKED alone
    scorecard_isolated = compute_layered_score([{"code": "SEARCH_CRAWLER_BLOCKED"}])
    access_deductions = [
        d for d in scorecard_isolated.sub_scores["access"].deductions
        if d["code"] == "SEARCH_CRAWLER_BLOCKED"
    ]
    assert len(access_deductions) == 1
    assert access_deductions[0]["points"] == -10
    assert scorecard_isolated.sub_scores["access"].score == 10  # 20 - 10

    # Test combined score with parsed issues
    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)
    assert any(
        d["code"] == "SEARCH_CRAWLER_BLOCKED" and d["points"] == -10
        for d in scorecard.sub_scores["access"].deductions
    )

