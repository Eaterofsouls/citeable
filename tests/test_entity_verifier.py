# tests/test_entity_verifier.py

import pytest
from areos.auditors.entity_verifier import (
    EntityAuditResult,
    EntityIssue,
    audit_entities,
    format_entity_report,
)


def test_no_entities_found():
    """When no entity schemas are present, emit ENTITY_OK info."""
    json_ld = [{"@type": "WebPage", "name": "About Us"}]
    res = audit_entities("https://example.com/about", "", json_ld)
    assert res.passed is True
    assert len(res.entities_found) == 0
    assert any(i.code == "ENTITY_OK" for i in res.issues)


def test_entity_name_missing():
    """Organization without name field triggers ENTITY_NAME_MISSING error."""
    json_ld = [{"@type": "Organization", "sameAs": ["https://wikidata.org/wiki/Q12345"]}]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is False
    assert res.error_count == 1
    assert any(i.code == "ENTITY_NAME_MISSING" for i in res.issues)


def test_sameas_missing():
    """Organization without sameAs triggers SAMEAS_MISSING warning."""
    json_ld = [{"@type": "Organization", "name": "Acme Corp"}]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert res.warning_count == 1
    assert any(i.code == "SAMEAS_MISSING" for i in res.issues)
    assert len(res.entities_found) == 1
    assert res.entities_found[0]["name"] == "Acme Corp"
    assert res.entities_found[0]["sameAs_count"] == 0


def test_sameas_incomplete():
    """sameAs with fewer than 3 links triggers SAMEAS_INCOMPLETE info."""
    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": ["https://www.wikidata.org/wiki/Q12345", "https://twitter.com/acme"],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert any(i.code == "SAMEAS_INCOMPLETE" for i in res.issues)
    assert not any(i.code == "WIKIDATA_MISSING" for i in res.issues)
    assert res.entities_found[0]["sameAs_count"] == 2


def test_wikidata_missing():
    """sameAs without wikidata.org or wikipedia.org link triggers WIKIDATA_MISSING warning."""
    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": [
            "https://twitter.com/acme",
            "https://linkedin.com/company/acme",
            "https://facebook.com/acme",
        ],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert any(i.code == "WIKIDATA_MISSING" for i in res.issues)
    assert not any(i.code == "SAMEAS_INCOMPLETE" for i in res.issues)
    assert not any(i.code == "SAMEAS_MISSING" for i in res.issues)


def test_entity_ok():
    """Fully configured organization emits ENTITY_OK."""
    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": [
            "https://www.wikidata.org/wiki/Q12345",
            "https://en.wikipedia.org/wiki/Acme_Corp",
            "https://twitter.com/acme",
        ],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert res.error_count == 0
    assert res.warning_count == 0
    assert any(i.code == "ENTITY_OK" for i in res.issues)
    assert len(res.entities_found) == 1
    assert res.entities_found[0]["sameAs_count"] == 3


def test_nested_graph_entities():
    """Entities wrapped inside @graph structures are extracted and verified."""
    json_ld = [{
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": "Acme Site"},
            {
                "@type": "LocalBusiness",
                "name": "Acme Store #1",
                "sameAs": "https://en.wikipedia.org/wiki/Acme_Store",
            },
        ],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert len(res.entities_found) == 1
    assert res.entities_found[0]["type"] == "LocalBusiness"
    assert res.entities_found[0]["name"] == "Acme Store #1"
    assert res.entities_found[0]["sameAs_count"] == 1
    assert any(i.code == "SAMEAS_INCOMPLETE" for i in res.issues)
    assert not any(i.code == "WIKIDATA_MISSING" for i in res.issues)


def test_person_entity():
    """Person entities are detected and verified."""
    json_ld = [{
        "@type": "Person",
        "name": "Jane Doe",
        "sameAs": ["https://wikidata.org/wiki/Q999"],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    assert res.passed is True
    assert len(res.entities_found) == 1
    assert res.entities_found[0]["type"] == "Person"
    assert res.entities_found[0]["name"] == "Jane Doe"


def test_as_finding_dicts():
    """Findings dict format is compatible with the synthesis engine."""
    json_ld = [{"@type": "Organization", "name": "Acme Corp"}]
    res = audit_entities("https://example.com", "", json_ld)
    findings = res.as_finding_dicts()
    assert isinstance(findings, list)
    assert len(findings) == len(res.issues)
    assert all(f["check_type"] == "entity" for f in findings)
    assert all("code" in f and "severity" in f and "message" in f for f in findings)


def test_format_entity_report():
    """Human-readable text report generates cleanly."""
    json_ld = [{
        "@type": "Organization",
        "name": "Acme Corp",
        "sameAs": ["https://wikidata.org/wiki/Q1"],
    }]
    res = audit_entities("https://example.com", "", json_ld)
    report = format_entity_report(res)
    assert "Entity Verification Report for: https://example.com" in report
    assert "Acme Corp" in report
    assert "Entities Detected:" in report
