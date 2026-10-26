"""
tests/test_sameas_dead_link.py

Unit tests for WP-2.2:
- Wire SAMEAS_DEAD_LINK in entity_verifier.py
- Mocked liveness checking (404 dead link vs 200 healthy link)
- SSRF-safety check (SSRF ValueError safely marks link as dead)
- Verify Schema layer deduction (-3 pts)
"""

from unittest.mock import patch, MagicMock
from areos.auditors.entity_verifier import audit_entities, _check_sameas_liveness
from areos.auditors.scoring import compute_layered_score


def test_sameas_dead_link_fires_with_dead_and_alive_urls():
    """
    WP-2.2 Checkpoint 2:
    Mocked sameAs list with one 404 URL and one 200 URL:
    Assert SAMEAS_DEAD_LINK fires exactly once, mentioning the dead URL.
    """
    def mock_fetch(url, **kwargs):
        resp = MagicMock()
        if "dead-link" in url:
            resp.status_code = 404
        else:
            resp.status_code = 200
        return resp

    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": [
            "https://example.com/healthy-link",
            "https://example.com/dead-link",
            "https://www.wikidata.org/wiki/Q12345",
        ],
    }]

    with patch("areos.auditors.entity_verifier.safe_get", side_effect=mock_fetch):
        res = audit_entities("https://example.com", "", json_ld)

    dead_issues = [i for i in res.issues if i.code == "SAMEAS_DEAD_LINK"]
    assert len(dead_issues) == 1, f"Expected exactly 1 SAMEAS_DEAD_LINK, got {len(dead_issues)}"

    msg = dead_issues[0].message
    assert "https://example.com/dead-link" in msg
    assert "https://example.com/healthy-link" not in msg

    # Scoring check: SAMEAS_DEAD_LINK (-1 in Schema per Model A rebalance)
    findings = res.as_finding_dicts()
    scorecard = compute_layered_score(findings)
    schema_subscore = scorecard.sub_scores["schema"]
    dead_deduction = next(d for d in schema_subscore.deductions if d["code"] == "SAMEAS_DEAD_LINK")
    assert dead_deduction["points"] == -1


def test_sameas_all_healthy_urls_no_dead_link_finding():
    """When all sameAs URLs return 200, SAMEAS_DEAD_LINK must not fire."""
    mock_resp = MagicMock(status_code=200)
    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": [
            "https://example.com/healthy1",
            "https://example.com/healthy2",
            "https://www.wikidata.org/wiki/Q12345",
        ],
    }]

    with patch("areos.auditors.entity_verifier.safe_get", return_value=mock_resp):
        res = audit_entities("https://example.com", "", json_ld)

    assert not any(i.code == "SAMEAS_DEAD_LINK" for i in res.issues)
    assert any(i.code == "ENTITY_OK" for i in res.issues)


def test_sameas_ssrf_attempt_marked_dead():
    """An internal/metadata URL blocked by SSRF filter is safely flagged as dead."""
    def mock_fetch(url, **kwargs):
        if "169.254" in url:
            raise ValueError("Domain resolves to a restricted address")
        return MagicMock(status_code=200)

    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": [
            "http://169.254.169.254/latest/meta-data/",
            "https://www.wikidata.org/wiki/Q12345",
        ],
    }]

    with patch("areos.auditors.entity_verifier.safe_get", side_effect=mock_fetch):
        res = audit_entities("https://example.com", "", json_ld)

    dead_issues = [i for i in res.issues if i.code == "SAMEAS_DEAD_LINK"]
    assert len(dead_issues) == 1
    assert "169.254.169.254" in dead_issues[0].message
