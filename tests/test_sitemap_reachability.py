"""
tests/test_sitemap_reachability.py

Unit tests for DEF-05 / WP-1.6:
- SITEMAP_PAGES_UNREACHABLE is exclusively owned and emitted by sitemap_auditor.
- multipage_auditor does NOT double-emit SITEMAP_PAGES_UNREACHABLE.
- Access-layer deduction for unreachable sitemap URLs is -2, not -4.
"""

from unittest.mock import patch, MagicMock
from areos.auditors.sitemap_auditor import audit_sitemap
from areos.auditors.multipage_auditor import audit_multi_page
from areos.auditors.scoring import compute_layered_score


SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc><lastmod>2026-01-01</lastmod></url>
  <url><loc>https://example.com/page2</loc><lastmod>2026-01-01</lastmod></url>
  <url><loc>https://example.com/dead1</loc><lastmod>2026-01-01</lastmod></url>
  <url><loc>https://example.com/dead2</loc><lastmod>2026-01-01</lastmod></url>
  <url><loc>https://example.com/page3</loc><lastmod>2026-01-01</lastmod></url>
</urlset>
"""


@patch("areos.auditors.sitemap_auditor._check_url_reachable")
@patch("areos.auditors.sitemap_auditor.safe_get")
def test_sitemap_auditor_emits_unreachable(mock_safe_get, mock_reachable):
    """sitemap_auditor properly emits SITEMAP_PAGES_UNREACHABLE when sampled URLs fail."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_SITEMAP_XML
    mock_safe_get.return_value = mock_resp
    mock_reachable.side_effect = lambda url, timeout=2.0: "dead" not in url

    res = audit_sitemap("example.com", spot_check=True)
    unreachable_issues = [i for i in res.issues if i.code == "SITEMAP_PAGES_UNREACHABLE"]
    assert len(unreachable_issues) == 1
    assert "2 of 5 sampled sitemap URLs" in unreachable_issues[0].message


@patch("areos.auditors.sitemap_auditor._check_url_reachable")
@patch("areos.auditors.sitemap_auditor.safe_get")
@patch("areos.auditors.multipage_auditor.safe_get")
def test_sitemap_and_multipage_single_emit_and_deduction(mock_multi_get, mock_site_get, mock_reachable):
    """
    DEF-05 / WP-1.6 Checkpoint 2:
    For a target with unreachable sitemap URLs, the combined findings contain
    exactly ONE SITEMAP_PAGES_UNREACHABLE entry (not two), and the Access-layer
    deduction is -2, not -4.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_SITEMAP_XML
    mock_site_get.return_value = mock_resp
    mock_reachable.side_effect = lambda url, timeout=2.0: "dead" not in url

    # Mock safe_get for multipage auditor: 2 dead URLs return 404, 3 return 200
    def multipage_fetch(url, timeout=4):
        resp = MagicMock()
        if "dead" in url:
            resp.status_code = 404
            resp.text = "Not Found"
        else:
            resp.status_code = 200
            resp.text = '<html><head><script type="application/ld+json">{"@type":"Article"}</script></head><body>' + ("content " * 40) + '</body></html>'
        return resp

    mock_multi_get.side_effect = multipage_fetch

    # 1. Run sitemap auditor
    sitemap_res = audit_sitemap("example.com", spot_check=True)
    assert any(i.code == "SITEMAP_PAGES_UNREACHABLE" for i in sitemap_res.issues)

    # 2. Run multipage auditor
    multi_res = audit_multi_page(sitemap_res.urls[:5], "example.com")
    assert not any(i.code == "SITEMAP_PAGES_UNREACHABLE" for i in multi_res.issues), (
        "multipage_auditor must NOT emit SITEMAP_PAGES_UNREACHABLE"
    )

    # 3. Simulate orchestrator aggregation (audit_orchestrator.py lines 678-690)
    findings = []
    for iss in sitemap_res.issues:
        if iss.code != "SITEMAP_OK":
            findings.append({"code": iss.code, "severity": iss.severity, "message": iss.message})
    findings.extend(multi_res.as_finding_dicts())

    unreachable_findings = [f for f in findings if f.get("code") == "SITEMAP_PAGES_UNREACHABLE"]
    assert len(unreachable_findings) == 1, (
        f"Expected exactly 1 SITEMAP_PAGES_UNREACHABLE finding, got {len(unreachable_findings)}"
    )

    # 4. Score with compute_layered_score and verify Access layer deduction
    scorecard = compute_layered_score(findings)
    access_subscore = scorecard.sub_scores["access"]

    # Deductions: SITEMAP_PAGES_UNREACHABLE (-2), possibly SITEMAP_NOT_IN_ROBOTS (-1)
    # Crucially, SITEMAP_PAGES_UNREACHABLE deduction must be 2, NOT 4.
    unreachable_deductions = [d for d in access_subscore.deductions if d["code"] == "SITEMAP_PAGES_UNREACHABLE"]
    assert len(unreachable_deductions) == 1
    assert unreachable_deductions[0]["points"] == -1
    # Access max is 20: 20 - 1 (unreachable) = 19 (Model A rebalanced deduction)
    assert access_subscore.score == 19
