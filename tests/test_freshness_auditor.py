from datetime import date
from areos.auditors.freshness_auditor import (
    FreshnessAuditResult,
    FreshnessIssue,
    audit_freshness,
    extract_dates_from_html,
    extract_dates_from_json_ld,
    parse_date_string,
)


def test_date_missing():
    result = audit_freshness("https://example.com", "", [])
    assert len(result.issues) == 1
    assert result.issues[0].code == "DATE_MISSING"
    assert result.issues[0].severity == "warning"
    assert result.dates_found == []
    assert result.most_recent_date is None
    assert result.age_days is None


def test_freshness_ok_json_ld():
    ref_date = date(2026, 9, 1)
    json_ld = [{"@type": "Article", "dateModified": "2026-08-15T12:00:00Z"}]
    result = audit_freshness("https://example.com/article", "", json_ld, reference_date=ref_date)
    assert len(result.issues) == 1
    assert result.issues[0].code == "FRESHNESS_OK"
    assert result.issues[0].severity == "info"
    assert result.age_days == 17
    assert result.passed is True


def test_content_aging():
    ref_date = date(2026, 9, 1)
    json_ld = [{"@type": "Article", "datePublished": "2026-02-01"}]
    result = audit_freshness("https://example.com/post", "", json_ld, reference_date=ref_date)
    assert len(result.issues) == 1
    assert result.issues[0].code == "CONTENT_AGING"
    assert result.issues[0].severity == "warning"
    assert result.age_days == 212
    assert result.passed is True


def test_content_stale():
    ref_date = date(2026, 9, 1)
    json_ld = [{"@type": "Article", "datePublished": "2024-01-01"}]
    result = audit_freshness("https://example.com/old", "", json_ld, reference_date=ref_date)
    assert len(result.issues) == 1
    assert result.issues[0].code == "CONTENT_STALE"
    assert result.issues[0].severity == "error"
    assert result.passed is False
    assert result.error_count == 1


def test_html_meta_and_time_tags():
    ref_date = date(2026, 9, 1)
    html = """
    <html>
      <head>
        <meta property="article:modified_time" content="2026-07-01T10:00:00Z">
        <meta name="date" content="2025-01-01">
      </head>
      <body>
        <time datetime="2026-08-20">August 20, 2026</time>
      </body>
    </html>
    """
    result = audit_freshness("https://example.com/page", html, [], reference_date=ref_date)
    assert len(result.dates_found) == 3
    assert result.most_recent_date == "2026-08-20"
    assert result.age_days == 12
    assert result.issues[0].code == "FRESHNESS_OK"


def test_as_finding_dicts():
    result = audit_freshness("https://example.com", "", [])
    findings = result.as_finding_dicts()
    assert len(findings) == 1
    assert findings[0]["code"] == "DATE_MISSING"
    assert findings[0]["check_type"] == "freshness"
    assert findings[0]["url"] == "https://example.com"
