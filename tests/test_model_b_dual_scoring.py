"""
tests/test_model_b_dual_scoring.py

Unit tests for WP-5.2 Model B dual readiness and visibility scoring:
- Scenario (a): High technical readiness (100) with zero citations surfaces distinct readiness and visibility scores
- Scenario (b): Unconfigured authority calculates visibility from citation alone without penalty
- Scenario (c): Citation sample counts properly tier confidence to low (<5), medium (5-9), and high (>=10)
- Backward compatibility: overall_score remains intact and identical
"""

import pytest
from areos.auditors.scoring import compute_layered_score, SCORE_CEILING


def test_scenario_a_perfect_readiness_distinct_from_low_visibility():
    """
    WP-5.2 Checkpoint 2(a):
    A site with perfect technical foundations (no access, schema, or content issues)
    but completely absent from citations and authority should surface distinct readiness
    and visibility scores (readiness 100, visibility low), rather than a single collapsing score.
    """
    findings = [
        {"code": "CITATION_NOT_OBSERVED", "severity": "error"},
        {"code": "REFERRING_DOMAINS_CRITICAL", "severity": "warning"},
        {"code": "WIKIPEDIA_ENTITY_MISSING", "severity": "warning"},
        {"code": "BRAND_MENTIONS_STAGNANT", "severity": "warning"},
    ]
    card = compute_layered_score(findings, citation_samples_count=2)

    # Technical readiness: Access (20) + Schema (15) + Content (20) = 55/55 -> 100
    assert card.readiness_score == 100
    # Visibility: Citation (0) + Authority (2) = 2/45 -> 4
    assert card.visibility_score == 4
    # Both are distinctly available in as_dict()
    as_dict = card.as_dict()
    assert as_dict["readiness_score"] == 100
    assert as_dict["visibility_score"] == 4
    assert as_dict["visibility_confidence"] == "low"
    assert "overall_score" in as_dict


def test_scenario_b_unconfigured_authority_computes_visibility_from_citation_alone():
    """
    WP-5.2 Checkpoint 2(b):
    When authority is unconfigured, visibility_score is computed solely from Citation
    (out of 30) without penalizing the site for absent third-party API credentials.
    """
    # 1. Full citation points with authority unconfigured -> 100% visibility
    findings_full_citation = [
        {"code": "AUTHORITY_UNCONFIGURED", "severity": "info"}
    ]
    card_full = compute_layered_score(findings_full_citation, authority_unconfigured=True)
    assert card_full.authority_excluded is True
    assert card_full.visibility_score == 100  # 30 / 30

    # 2. Partial citation points (CITATION_RATE_LOW: -15 pts) -> 15/30 = 50% visibility
    findings_half_citation = [
        {"code": "CITATION_RATE_LOW", "severity": "warning"},
        {"code": "AUTHORITY_UNCONFIGURED", "severity": "info"},
    ]
    card_half = compute_layered_score(findings_half_citation, authority_unconfigured=True)
    assert card_half.authority_excluded is True
    assert card_half.visibility_score == 50  # 15 / 30 = 50%


def test_scenario_c_visibility_confidence_tiers():
    """
    WP-5.2 Checkpoint 2(c):
    Visibility confidence reflects sampling depth:
    <5 -> low, 5-9 -> medium, >=10 -> high.
    """
    card_low = compute_layered_score([], citation_samples_count=3)
    assert card_low.visibility_confidence == "low"
    assert card_low.citation_samples_count == 3

    card_med = compute_layered_score([], citation_samples_count=6)
    assert card_med.visibility_confidence == "medium"
    assert card_med.citation_samples_count == 6

    card_high = compute_layered_score([], citation_samples_count=12)
    assert card_high.visibility_confidence == "high"
    assert card_high.citation_samples_count == 12


def test_backward_compatibility_overall_score_unchanged():
    """
    WP-5.2 Checkpoint 3:
    overall_score behavior must be byte-for-byte unchanged from WP-5.1.
    """
    clean_card = compute_layered_score([])
    assert clean_card.overall_score == 98
    assert clean_card.readiness_score == 100
    assert clean_card.visibility_score == 100

    deductions_card = compute_layered_score([
        {"code": "NOSNIPPET_BLOCKING_AI"},      # -3 in access
        {"code": "JSON_PARSE_FAILURE"},          # -3 in schema
        {"code": "EXTRACTABILITY_MEDIUM"},       # -3 in content
    ])
    # 100 - 9 = 91
    assert deductions_card.overall_score == 91
    # Readiness: (17 + 12 + 17) / 55 = 46 / 55 = 83.6% -> 84
    assert deductions_card.readiness_score == 84
