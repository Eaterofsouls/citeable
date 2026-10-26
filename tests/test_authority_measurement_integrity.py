"""
Unit and regression tests for WP-1.1 / WP-1.4: Authority Measurement Integrity.

Verifies:
1. When provider is unconfigured, metrics are explicit None and provider_used is 'not_configured'.
   No fabricated 35/100 or 120 referring domains are generated, and no false deductions fire.
2. When provider key exists but request fails or quota exhausted, metrics are explicit None
   and provider_used is 'provider_unavailable'. No false deductions fire.
3. When provider returns valid measurements, real metrics are preserved and evaluated.
4. Measured zero (score=0, ref_domains=0) is strictly distinguished from unavailable (None).
5. Provider status and explicit None metrics survive orchestration and serialization.
6. studio.js UI rendering and Markdown export contracts enforce N/A states and prohibit 35/100.
7. WP-1.4: Unconfigured authority does not score 15/15 and real low authority does not score lower than unconfigured.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from areos.auditors.authority_auditor import (
    audit_domain_authority,
    get_fallback_metrics,
)
from areos.auditors.audit_orchestrator import run_orchestrated_audit
from areos.auditors.scoring import compute_layered_score
from areos.db.migrate_audit_tables import migrate


ROOT = Path(__file__).resolve().parents[1]


# ── 1. Provider Unconfigured Tests ──────────────────────────────────────────

def test_unconfigured_provider_returns_explicit_none(monkeypatch):
    """When no API key is provided, returns explicit None and provider='not_configured'."""
    monkeypatch.delenv("OPEN_PAGERANK_API_KEY", raising=False)
    
    # Check fallback metrics generator directly
    fallback = get_fallback_metrics("example.com")
    assert fallback["authority_score"] is None
    assert fallback["referring_domains"] is None
    assert fallback["wikipedia_presence"] is None
    assert fallback["brand_mention_growth"] is None
    assert fallback["provider"] == "not_configured"

    # Check auditor output
    res = audit_domain_authority("example.com", client_keys=None)
    assert res.provider_used == "not_configured"
    assert res.metrics["authority_score"] is None
    assert res.metrics["referring_domains"] is None
    assert res.metrics["wikipedia_presence"] is None
    assert res.metrics["brand_mention_growth"] is None
    
    # Crucially: no false deductions (AUTHORITY_DR_LOW, REFERRING_DOMAINS_CRITICAL, WIKIPEDIA_ENTITY_MISSING)
    issue_codes = [iss.code for iss in res.issues]
    assert "AUTHORITY_DR_LOW" not in issue_codes
    assert "REFERRING_DOMAINS_CRITICAL" not in issue_codes
    assert "WIKIPEDIA_ENTITY_MISSING" not in issue_codes
    assert "AUTHORITY_UNCONFIGURED" in issue_codes


def test_unconfigured_provider_does_not_score_15_out_of_15(monkeypatch):
    """WP-1.4: Unconfigured authority must not score 15/15 full marks (closes scoring inversion)."""
    monkeypatch.delenv("OPEN_PAGERANK_API_KEY", raising=False)
    res = audit_domain_authority("unknown-startup.org")
    
    scorecard = compute_layered_score([
        {"code": iss.code, "severity": iss.severity, "message": iss.message}
        for iss in res.issues
    ])
    
    # Authority layer should have 0 deductions and NOT score 15/15
    auth_subscore = scorecard.sub_scores["authority"]
    assert len(auth_subscore.deductions) == 0
    assert auth_subscore.score != 15
    assert auth_subscore.unconfigured is True
    assert scorecard.authority_excluded is True


# ── 2. Provider Quota Exhausted / Request Failed Tests ────────────────────────

def test_provider_failure_returns_provider_unavailable(monkeypatch):
    """When API key is present but OpenPageRank fetch fails (quota/network), returns 'provider_unavailable'."""
    monkeypatch.setenv("OPEN_PAGERANK_API_KEY", "exhausted_or_invalid_key")
    
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=None):
        res = audit_domain_authority("example.com")
        
        assert res.provider_used == "provider_unavailable"
        assert res.metrics["authority_score"] is None
        assert res.metrics["referring_domains"] is None
        assert res.metrics["provider"] == "provider_unavailable"
        assert any(iss.code == "AUTHORITY_PROVIDER_UNAVAILABLE" for iss in res.issues)


def test_byok_client_keys_failure_returns_provider_unavailable():
    """When client_keys provides key but API returns None, returns 'provider_unavailable'."""
    client_keys = {"open_pagerank": "user_submitted_key"}
    
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=None):
        res = audit_domain_authority("example.com", client_keys=client_keys)
        
        assert res.provider_used == "provider_unavailable"
        assert res.metrics["authority_score"] is None
        assert any(iss.code == "AUTHORITY_PROVIDER_UNAVAILABLE" for iss in res.issues)


# ── 3. Provider Valid Data Tests ─────────────────────────────────────────────

def test_valid_provider_low_authority_triggers_expected_deductions():
    """When provider returns genuine low measurements, deductions trigger as expected."""
    mock_metrics = {
        "authority_score": 10,
        "referring_domains": 12,
        "wikipedia_presence": False,
        "brand_mention_growth": -2.5,
        "provider": "open_pagerank"
    }
    
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=mock_metrics):
        res = audit_domain_authority("low-authority-domain.com", client_keys={"open_pagerank": "key"})
        
        assert res.provider_used == "open_pagerank"
        assert res.metrics["authority_score"] == 10
        assert res.metrics["referring_domains"] == 12
        
        codes = [iss.code for iss in res.issues]
        assert "AUTHORITY_DR_LOW" in codes
        assert "REFERRING_DOMAINS_CRITICAL" in codes
        assert "WIKIPEDIA_ENTITY_MISSING" in codes
        assert "BRAND_MENTIONS_STAGNANT" in codes


def test_valid_provider_healthy_authority_triggers_profile_good():
    """When provider returns genuine healthy measurements, AUTHORITY_PROFILE_GOOD is emitted."""
    mock_metrics = {
        "authority_score": 75,
        "referring_domains": 1500,
        "wikipedia_presence": True,
        "brand_mention_growth": 8.0,
        "provider": "open_pagerank"
    }
    
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=mock_metrics):
        res = audit_domain_authority("high-authority-domain.com", client_keys={"open_pagerank": "key"})
        
        assert res.provider_used == "open_pagerank"
        assert len(res.issues) == 1
        assert res.issues[0].code == "AUTHORITY_PROFILE_GOOD"


# ── 4. Measured Zero vs Unavailable Distinction ─────────────────────────────

def test_measured_zero_is_distinguishable_from_unavailable():
    """A measured zero (score=0, ref=0) is evaluated as poor authority, unlike None which is not penalized."""
    mock_zero = {
        "authority_score": 0,
        "referring_domains": 0,
        "wikipedia_presence": False,
        "brand_mention_growth": 0.0,
        "provider": "open_pagerank"
    }
    
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=mock_zero):
        res = audit_domain_authority("zero-authority.com", client_keys={"open_pagerank": "key"})
        
        assert res.provider_used == "open_pagerank"
        assert res.metrics["authority_score"] == 0
        assert res.metrics["referring_domains"] == 0
        
        codes = [iss.code for iss in res.issues]
        assert "AUTHORITY_DR_LOW" in codes
        assert "REFERRING_DOMAINS_CRITICAL" in codes


# ── 5. Manual Override Support ──────────────────────────────────────────────

def test_manual_overrides_respected():
    """Explicit overrides (for testing or manual audits) remain supported."""
    overrides = {
        "authority_score": 52,
        "referring_domains": 450,
        "wikipedia_presence": True,
        "brand_mention_growth": 3.2,
        "provider": "custom_eval"
    }
    res = audit_domain_authority("test.com", metrics_override=overrides)
    assert res.provider_used == "custom_eval"
    assert res.metrics["authority_score"] == 52
    assert res.metrics["referring_domains"] == 450
    assert len(res.issues) == 1
    assert res.issues[0].code == "AUTHORITY_PROFILE_GOOD"


# ── 6. Orchestration and Serialization Tests ────────────────────────────────

def test_orchestration_unconfigured_preserves_null_and_provider_used(tmp_path, monkeypatch):
    """Orchestrated audit must retain null authority metrics and 'not_configured' status."""
    monkeypatch.delenv("OPEN_PAGERANK_API_KEY", raising=False)
    test_db = tmp_path / "test_orch_auth.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    sample_html = "<html><body><h1>Test Page</h1><p>Substantive body text with enough content for extractability.</p></body></html>"
    res = run_orchestrated_audit("unconfigured-domain.com", sample_content=sample_html, db_path=test_db)
    
    scorecard = res["executive_scorecard"]
    assert scorecard["provider_used"] == "not_configured"
    auth_metrics = scorecard["authority_metrics"]
    assert auth_metrics["provider_used"] == "not_configured"
    assert auth_metrics["authority_score"] is None
    assert auth_metrics["referring_domains"] is None

    # Check score_detail_json stored in audit_runs
    import sqlite3
    conn = sqlite3.connect(test_db)
    row = conn.execute("SELECT score_detail_json FROM audit_runs WHERE run_id = ?", (res["run_id"],)).fetchone()
    conn.close()
    
    assert row is not None
    detail = json.loads(row[0])
    stored_auth = detail["authority_metrics"]
    assert stored_auth["provider_used"] == "not_configured"
    assert stored_auth["authority_score"] is None
    assert stored_auth["referring_domains"] is None


def test_orchestration_measured_metrics_preserved(tmp_path, monkeypatch):
    """Orchestrated audit must retain real numbers when provider returns valid data."""
    test_db = tmp_path / "test_orch_auth_live.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    mock_metrics = {
        "authority_score": 68,
        "referring_domains": 850,
        "wikipedia_presence": True,
        "brand_mention_growth": 4.5,
        "provider": "open_pagerank"
    }

    sample_html = "<html><body><h1>Live Auth Test</h1><p>Substantive content text for extractability.</p></body></html>"
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=mock_metrics):
        res = run_orchestrated_audit(
            "live-auth-domain.com",
            sample_content=sample_html,
            client_keys={"open_pagerank": "valid_key"},
            db_path=test_db
        )

    scorecard = res["executive_scorecard"]
    assert scorecard["provider_used"] == "open_pagerank"
    auth_metrics = scorecard["authority_metrics"]
    assert auth_metrics["provider_used"] == "open_pagerank"
    assert auth_metrics["authority_score"] == 68
    assert auth_metrics["referring_domains"] == 850


# ── 7. UI Rendering & Markdown Export Contract Tests ────────────────────────

def test_studio_js_contains_null_safe_authority_checks():
    """Verify studio.js implements proper unavailable state checks and does not assume 35/100."""
    studio_js_path = ROOT / "areos" / "ui" / "studio.js"
    assert studio_js_path.exists(), "studio.js must exist"
    code = studio_js_path.read_text(encoding="utf-8")

    # 1. UI tile display check
    assert "provider === 'not_configured' || provider === 'provider_unavailable'" in code
    assert "N/A \\u2014 no authority data available" in code or "N/A — no authority data available" in code
    
    # 2. Historical reload check must not default missing authority metrics to 0
    assert "authority_score: null, referring_domains: null, provider_used: \"not_configured\"" in code

    # 3. Executive markdown export must check unavailable state and emit N/A
    assert "isAuthUnavailable" in code
    assert "| **Entity Authority Score** | **N/A** | N/A" in code


# ── 8. WP-1.4 Scoring Inversion Closed Test ──────────────────────────────────

def test_inversion_closed_low_authority_does_not_score_lower_than_unconfigured(monkeypatch):
    """WP-1.4 Checkpoint: A domain with real low authority does NOT score lower overall than an identical domain audited without an API key."""
    monkeypatch.delenv("OPEN_PAGERANK_API_KEY", raising=False)

    base_findings = [
        {"code": "CONTENT_STALE", "severity": "warning", "message": "Stale content"},
    ]

    # 1. Unconfigured authority run
    unconfigured_res = audit_domain_authority("unconfigured.com")
    unconfigured_findings = base_findings + [
        {"code": iss.code, "severity": iss.severity, "message": iss.message}
        for iss in unconfigured_res.issues
    ]
    unconfigured_card = compute_layered_score(unconfigured_findings)

    # 2. Configured run with low authority (e.g. score=10, ref_domains=12 -> deductions)
    low_metrics = {
        "authority_score": 10,
        "referring_domains": 12,
        "wikipedia_presence": False,
        "brand_mention_growth": -2.0,
        "provider": "open_pagerank"
    }
    with patch("areos.auditors.authority_auditor.fetch_open_pagerank", return_value=low_metrics):
        configured_res = audit_domain_authority("configured-low.com", client_keys={"open_pagerank": "k"})

    configured_findings = base_findings + [
        {"code": iss.code, "severity": iss.severity, "message": iss.message}
        for iss in configured_res.issues
    ]
    configured_card = compute_layered_score(configured_findings)

    # Assertions per WP-1.4 checkpoint
    assert unconfigured_card.sub_scores["authority"].score != 15
    assert unconfigured_card.sub_scores["authority"].unconfigured is True
    assert unconfigured_card.authority_excluded is True

    # The inversion is closed: low authority domain does NOT score lower than unconfigured domain
    assert configured_card.overall_score >= unconfigured_card.overall_score
