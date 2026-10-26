"""
tests/test_canonical_auditor.py

Unit tests for WP-2.1:
- Wire CANONICAL_MISSING in redirect_auditor.py
- Verify canonical absent -> CANONICAL_MISSING fires
- Verify matching canonical -> neither CANONICAL_MISSING nor CANONICAL_MISMATCH fires
- Verify mismatched canonical -> CANONICAL_MISMATCH fires, not CANONICAL_MISSING
"""

from areos.auditors.redirect_auditor import audit_redirects_and_access
from areos.auditors.scoring import compute_layered_score


def test_canonical_missing_fires_when_no_canonical_tag():
    """WP-2.1 Checkpoint 2(a): Page with no canonical tag emits CANONICAL_MISSING."""
    html = "<html><head><title>No Canonical</title></head><body><p>Hello</p></body></html>"
    result = audit_redirects_and_access(
        page_url="https://example.com",
        html=html,
        hop_count=0,
        final_url="https://example.com",
    )
    codes = [i.code for i in result.issues]
    assert "CANONICAL_MISSING" in codes, f"Expected CANONICAL_MISSING in {codes}"
    assert "CANONICAL_MISMATCH" not in codes
    assert "ACCESS_OK" not in codes

    # Scoring verification: CANONICAL_MISSING carries a 1 pt deduction in Schema per Model A rebalance
    findings = [{"code": i.code, "severity": i.severity, "message": i.message} for i in result.issues]
    scorecard = compute_layered_score(findings)
    schema_subscore = scorecard.sub_scores["schema"]
    deduction_entry = next(d for d in schema_subscore.deductions if d["code"] == "CANONICAL_MISSING")
    assert deduction_entry["points"] == -1


def test_canonical_matching_fires_neither_missing_nor_mismatch():
    """WP-2.1 Checkpoint 2(b): Page with matching canonical tag emits neither missing nor mismatch."""
    html = '<html><head><link rel="canonical" href="https://example.com/canonical-page"></head><body><p>Hello</p></body></html>'
    result = audit_redirects_and_access(
        page_url="https://example.com/canonical-page",
        html=html,
        hop_count=0,
        final_url="https://example.com/canonical-page",
    )
    codes = [i.code for i in result.issues]
    assert "CANONICAL_MISSING" not in codes
    assert "CANONICAL_MISMATCH" not in codes
    assert "ACCESS_OK" in codes


def test_canonical_mismatched_fires_mismatch_not_missing():
    """Page with different canonical URL emits CANONICAL_MISMATCH, not CANONICAL_MISSING."""
    html = '<html><head><link rel="canonical" href="https://example.com/other-page"></head><body><p>Hello</p></body></html>'
    result = audit_redirects_and_access(
        page_url="https://example.com/canonical-page",
        html=html,
        hop_count=0,
        final_url="https://example.com/canonical-page",
    )
    codes = [i.code for i in result.issues]
    assert "CANONICAL_MISMATCH" in codes
    assert "CANONICAL_MISSING" not in codes
