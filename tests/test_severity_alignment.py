"""
tests/test_severity_alignment.py

Unit tests for VAL-03 / WP-1.7:
Confirm that check codes carrying point deductions emit severity="warning", not "info":
- UNKNOWN_SCHEMA_TYPE
- VIDEO_NO_TRANSCRIPT
- COMPETITOR_SCHEMA_ADVANTAGE
- COMPETITOR_CONTENT_ADVANTAGE
"""

from unittest.mock import patch, MagicMock
from areos.auditors.schema_validator import validate_single
from areos.auditors.media_blindness_auditor import audit_media_blindness
from areos.auditors.competitor_analyzer import analyze_competitors


def test_unknown_schema_type_severity_warning():
    """VAL-03: UNKNOWN_SCHEMA_TYPE (-2 in scoring) must have severity='warning'."""
    res = validate_single({"@type": "CustomUnrecognizedEntityXYZ"}, index=0)
    issue = next(i for i in res.issues if i.code == "UNKNOWN_SCHEMA_TYPE")
    assert issue.severity == "warning", f"Expected warning, got {issue.severity}"


def test_video_no_transcript_severity_warning():
    """VAL-03: VIDEO_NO_TRANSCRIPT (-3 in scoring) must have severity='warning'."""
    html = "<html><body><p>" + ("word " * 100) + "</p><video src='vid.mp4'></video></body></html>"
    res = audit_media_blindness("https://example.com", html)
    issue = next(i for i in res.issues if i.code == "VIDEO_NO_TRANSCRIPT")
    assert issue.severity == "warning", f"Expected warning, got {issue.severity}"


@patch("areos.auditors.competitor_analyzer.safe_get")
def test_competitor_advantages_severity_warning(mock_safe_get):
    """VAL-03: COMPETITOR_SCHEMA_ADVANTAGE (-3) and COMPETITOR_CONTENT_ADVANTAGE (-2) must have severity='warning'."""
    def comp_fetch(url, timeout=4):
        resp = MagicMock()
        resp.status_code = 200
        # Competitor has Product schema, table, and list
        resp.text = """<html><head><script type="application/ld+json">{"@type":"Product"}</script></head>
        <body><table><tr><td>Feature</td></tr></table><ul><li>Item 1</li></ul></body></html>"""
        return resp

    mock_safe_get.side_effect = comp_fetch

    # Target has NO schema, so competitor will have both schema and content advantage
    res = analyze_competitors(
        competitor_domains=["competitor.com"],
        target_domain="target.com",
        target_schema_types=[],
    )

    schema_adv = next(i for i in res.issues if i.code == "COMPETITOR_SCHEMA_ADVANTAGE")
    assert schema_adv.severity == "warning", f"Expected warning, got {schema_adv.severity}"

    content_adv = next(i for i in res.issues if i.code == "COMPETITOR_CONTENT_ADVANTAGE")
    assert content_adv.severity == "warning", f"Expected warning, got {content_adv.severity}"
