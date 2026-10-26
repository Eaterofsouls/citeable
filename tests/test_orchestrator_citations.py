"""
tests/test_orchestrator_citations.py — Orchestrator Citation Count Matching (DEF-01 / WP-1.2)

Verifies:
1. When citation sampling returns citations that do NOT include the target domain
   (e.g., only competitor.com or wikipedia.org), cited_runs evaluates to 0 and
   CITATION_NOT_OBSERVED fires.
2. CITATION_OBSERVED does not fire for competitor-only citations.
3. When citation sampling returns citations that DO include the target domain,
   CITATION_OBSERVED fires.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from areos.auditors.audit_orchestrator import run_orchestrated_audit
from areos.auditors.citation_sampler import CitationObservation, CitationSampleResult
from areos.db.migrate_audit_tables import migrate

os.environ.setdefault("AREOS_API_TOKEN", "test_qa_token")
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_admin_token")


def test_competitor_only_citations_trigger_citation_not_observed(tmp_path, monkeypatch):
    """DEF-01 / WP-1.2: A site not cited in AI answers must get CITATION_NOT_OBSERVED even if other sites were cited."""
    test_db = tmp_path / "test_citations.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    # Mock citation sampling returning citations for competitor and wikipedia, but NOT example.com
    mock_obs = [
        CitationObservation(
            run_index=1,
            prompt="best tools in ecosystem",
            engine="perplexity",
            cited_urls=["https://competitor.com/product", "https://en.wikipedia.org/wiki/Software"],
            raw_answer_snippet="competitor is great",
            full_answer_text="full text",
        ),
        CitationObservation(
            run_index=2,
            prompt="alternative tools",
            engine="gemini",
            cited_urls=["https://another-rival.com"],
            raw_answer_snippet="rival is great",
            full_answer_text="full text",
        ),
    ]
    mock_sample_res = CitationSampleResult(
        target_domain="example.com",
        prompt_set=["p1", "p2"],
        engine="multi",
        n_runs=2,
        observations=mock_obs,
    )

    with patch("areos.auditors.audit_orchestrator.run_citation_sampling_loop", return_value=mock_sample_res):
        res = run_orchestrated_audit(
            "example.com",
            sample_content="<html><body><p>Clean sample page with sufficient text for extractability.</p></body></html>",
            db_path=test_db,
        )

    finding_codes = [f["code"] for f in res["raw_findings"]]
    assert "CITATION_NOT_OBSERVED" in finding_codes
    assert "CITATION_OBSERVED" not in finding_codes


def test_target_domain_citation_triggers_citation_observed(tmp_path, monkeypatch):
    """DEF-01 / WP-1.2: Citations containing the audited domain string trigger CITATION_OBSERVED."""
    test_db = tmp_path / "test_citations_obs.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    mock_obs = [
        CitationObservation(
            run_index=1,
            prompt="best tools in ecosystem",
            engine="perplexity",
            cited_urls=["https://example.com/features", "https://en.wikipedia.org/wiki/Software"],
            raw_answer_snippet="example is great",
            full_answer_text="full text",
        )
    ]
    mock_sample_res = CitationSampleResult(
        target_domain="example.com",
        prompt_set=["p1"],
        engine="multi",
        n_runs=1,
        observations=mock_obs,
    )

    with patch("areos.auditors.audit_orchestrator.run_citation_sampling_loop", return_value=mock_sample_res):
        res = run_orchestrated_audit(
            "example.com",
            sample_content="<html><body><p>Clean sample page with sufficient text for extractability.</p></body></html>",
            db_path=test_db,
        )

    finding_codes = [f["code"] for f in res["raw_findings"]]
    assert "CITATION_OBSERVED" in finding_codes
    assert "CITATION_NOT_OBSERVED" not in finding_codes


def test_citation_penalty_tiers_are_mutually_exclusive(tmp_path, monkeypatch):
    """
    VAL-05 / WP-1.8 Checkpoint 2:
    Construct a scenario where cited_runs == 0 (which also implies citation_rate == 0
    and share_of_voice == 0) and assert the findings list contains EXACTLY ONE of the three
    citation codes (CITATION_NOT_OBSERVED), not all three.
    """
    test_db = tmp_path / "test_tiers.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    # 1. Zero citations: cited_runs == 0, citation_obs is non-empty
    mock_obs = [
        CitationObservation(
            run_index=1,
            prompt="prompt 1",
            engine="perplexity",
            cited_urls=["https://competitor.com/p1"],
        ),
        CitationObservation(
            run_index=2,
            prompt="prompt 2",
            engine="perplexity",
            cited_urls=["https://rival.com/p2"],
        ),
    ]
    mock_sample_res = CitationSampleResult(
        target_domain="example.com",
        prompt_set=["p1", "p2"],
        engine="perplexity",
        n_runs=2,
        observations=mock_obs,
    )

    with patch("areos.auditors.audit_orchestrator.run_citation_sampling_loop", return_value=mock_sample_res):
        res = run_orchestrated_audit(
            "example.com",
            sample_content="<html><body><p>Clean sample page with sufficient text for extractability.</p></body></html>",
            db_path=test_db,
        )

    finding_codes = [f["code"] for f in res["raw_findings"]]
    penalty_codes = [c for c in finding_codes if c in ("CITATION_NOT_OBSERVED", "CITATION_RATE_LOW", "SHARE_OF_VOICE_LOW")]

    # Must contain EXACTLY ONE penalty code: CITATION_NOT_OBSERVED
    assert penalty_codes == ["CITATION_NOT_OBSERVED"], f"Expected only CITATION_NOT_OBSERVED, got {penalty_codes}"
    assert "CITATION_RATE_LOW" not in finding_codes
    assert "SHARE_OF_VOICE_LOW" not in finding_codes


def test_citation_rate_low_tier_blocks_share_of_voice_low(tmp_path, monkeypatch):
    """
    VAL-05 / WP-1.8:
    When cited_runs > 0 but citation_rate < 0.2 and share_of_voice < 0.1,
    only CITATION_RATE_LOW fires, not SHARE_OF_VOICE_LOW.
    """
    test_db = tmp_path / "test_tiers2.db"
    monkeypatch.setenv("AREOS_TEST_DB", str(test_db))
    monkeypatch.setenv("AREOS_DB_PATH", str(test_db))
    migrate(test_db)

    # 1 out of 10 runs cites example.com (10% citation rate < 20%; share of voice < 10%)
    mock_obs = [
        CitationObservation(
            run_index=1,
            prompt="prompt 1",
            engine="perplexity",
            cited_urls=["https://example.com/p1", "https://comp1.com", "https://comp2.com"],
        )
    ] + [
        CitationObservation(
            run_index=i,
            prompt=f"prompt {i}",
            engine="perplexity",
            cited_urls=["https://comp1.com", "https://comp2.com"],
        )
        for i in range(2, 11)
    ]
    mock_sample_res = CitationSampleResult(
        target_domain="example.com",
        prompt_set=[f"p{i}" for i in range(1, 11)],
        engine="perplexity",
        n_runs=10,
        observations=mock_obs,
    )

    with patch("areos.auditors.audit_orchestrator.run_citation_sampling_loop", return_value=mock_sample_res):
        res = run_orchestrated_audit(
            "example.com",
            sample_content="<html><body><p>Clean sample page with sufficient text for extractability.</p></body></html>",
            db_path=test_db,
        )

    finding_codes = [f["code"] for f in res["raw_findings"]]
    penalty_codes = [c for c in finding_codes if c in ("CITATION_NOT_OBSERVED", "CITATION_RATE_LOW", "SHARE_OF_VOICE_LOW")]

    # Must contain CITATION_RATE_LOW, but NOT CITATION_NOT_OBSERVED or SHARE_OF_VOICE_LOW
    assert penalty_codes == ["CITATION_RATE_LOW"], f"Expected only CITATION_RATE_LOW, got {penalty_codes}"
    assert "CITATION_OBSERVED" in finding_codes

