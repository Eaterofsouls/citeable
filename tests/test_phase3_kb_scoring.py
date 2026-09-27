# tests/test_phase3_kb_scoring.py
#
# Phase 3 Gate: KB Wiring & Scoring (T-301→T-305).
# Run: python -m pytest tests/test_phase3_kb_scoring.py -v

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_ADMIN_TOKEN", "test_phase3_token")


# ── T-301: LAYER_DEDUCTIONS ──────────────────────────────────────────────────

class TestT301LayerDeductions:
    def test_phase2_codes_in_deductions(self):
        """All Phase 2 check codes must be in LAYER_DEDUCTIONS."""
        from areos.auditors.scoring import LAYER_DEDUCTIONS
        phase2_codes = [
            "CONTENT_STALE", "CONTENT_AGING", "DATE_MISSING",
            "REDIRECT_CHAIN_LONG", "REDIRECT_CHAIN_EXCESSIVE", "META_NOINDEX",
            "REDIRECT_DOMAIN_CHANGE", "CANONICAL_MISMATCH",
            "CLOAKING_DETECTED", "CLOAKING_SUSPECTED", "AI_BOT_BLOCKED_HTTP",
            "ENTITY_NAME_MISSING", "SAMEAS_MISSING", "SAMEAS_INCOMPLETE", "WIKIDATA_MISSING",
            "IFRAME_HEAVY", "IMAGES_MISSING_ALT", "ALL_CONTENT_IN_MEDIA", "VIDEO_NO_TRANSCRIPT",
            "SITEMAP_MISSING", "SITEMAP_EMPTY", "SITEMAP_NOT_IN_ROBOTS",
            "SITEMAP_PAGES_UNREACHABLE", "SITEMAP_NO_LASTMOD",
            "CITATION_RATE_LOW", "SHARE_OF_VOICE_LOW",
        ]
        for code in phase2_codes:
            assert code in LAYER_DEDUCTIONS, f"{code} not in LAYER_DEDUCTIONS"

    def test_deductions_have_valid_layers(self):
        """All deductions must reference valid layer IDs."""
        from areos.auditors.scoring import LAYER_DEDUCTIONS, LAYERS
        valid_layers = set(LAYERS.keys())
        for code, (layer, points) in LAYER_DEDUCTIONS.items():
            assert layer in valid_layers, f"{code} references invalid layer '{layer}'"
            assert isinstance(points, int) and points > 0, f"{code} has invalid points: {points}"

    def test_score_floor_enforcement(self):
        """Score must never go below SCORE_FLOOR even with maximum deductions."""
        from areos.auditors.scoring import compute_layered_score, SCORE_FLOOR
        # Create extreme findings for every possible deduction
        findings = [{"code": "CRAWLER_FULLY_BLOCKED", "severity": "error", "message": "x"}]
        findings += [{"code": "CITATION_NOT_OBSERVED", "severity": "error", "message": "x"}]
        findings += [{"code": "EXTRACTABILITY_NONE", "severity": "error", "message": "x"}]
        findings += [{"code": "MISSING_TYPE", "severity": "error", "message": "x"}]
        findings += [{"code": "AUTHORITY_DR_LOW", "severity": "error", "message": "x"}]
        result = compute_layered_score(findings)
        assert result.overall_score >= SCORE_FLOOR

    def test_score_ceiling_enforcement(self):
        """Score must never exceed SCORE_CEILING (98) even with zero deductions."""
        from areos.auditors.scoring import compute_layered_score, SCORE_CEILING
        result = compute_layered_score([])  # no findings at all
        assert result.overall_score == 98
        assert result.overall_score <= SCORE_CEILING


# ── T-302: ACCESS_GATE ───────────────────────────────────────────────────────

class TestT302AccessGate:
    def test_cloaking_detected_in_gate(self):
        """CLOAKING_DETECTED must be in ACCESS_GATE with cap 35."""
        from areos.auditors.scoring import ACCESS_GATE
        assert "CLOAKING_DETECTED" in ACCESS_GATE
        assert ACCESS_GATE["CLOAKING_DETECTED"] == 35

    def test_meta_noindex_in_gate(self):
        """META_NOINDEX must be in ACCESS_GATE with cap 15."""
        from areos.auditors.scoring import ACCESS_GATE
        assert "META_NOINDEX" in ACCESS_GATE
        assert ACCESS_GATE["META_NOINDEX"] == 15

    def test_gate_caps_score(self):
        """Access gate should cap overall score when triggered."""
        from areos.auditors.scoring import compute_layered_score
        findings = [{"code": "META_NOINDEX", "severity": "error", "message": "noindex found"}]
        result = compute_layered_score(findings)
        assert result.overall_score <= 15
        assert result.access_gate_applied is True


# ── T-303 + T-305: Knowledge Map ─────────────────────────────────────────────

class TestT303KnowledgeMap:
    def test_knowledge_map_valid_json(self):
        """check_code_to_knowledge_map.json must be valid JSON."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "kb", "check_code_to_knowledge_map.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_all_deductions_mapped(self):
        """Every code in LAYER_DEDUCTIONS should have a knowledge map entry."""
        from areos.auditors.scoring import LAYER_DEDUCTIONS
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "kb", "check_code_to_knowledge_map.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            km = json.load(f)
        # Check that Phase 2 deduction codes exist in the map
        phase2_codes = [c for c in LAYER_DEDUCTIONS.keys()
                       if c.startswith(("CONTENT_STALE", "CONTENT_AGING", "DATE_MISSING",
                                       "REDIRECT_", "META_NOINDEX", "CANONICAL_",
                                       "CLOAKING_", "AI_BOT_", "ENTITY_NAME_",
                                       "SAMEAS_", "WIKIDATA_", "IFRAME_", "IMAGES_",
                                       "ALL_CONTENT_", "VIDEO_", "SITEMAP_",
                                       "CITATION_RATE", "SHARE_OF_VOICE"))]
        missing = [c for c in phase2_codes if c not in km]
        assert not missing, f"Missing from knowledge map: {missing}"

    def test_unverifiable_codes_mapped(self):
        """T-305: Unverifiable codes must be in knowledge map."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "kb", "check_code_to_knowledge_map.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            km = json.load(f)
        for code in ["SCHEMA_MISSING", "SCHEMA_UNVERIFIABLE", "ROBOTS_UNVERIFIABLE", "LLMS_UNVERIFIABLE"]:
            assert code in km, f"{code} not in knowledge map"
            assert "guidance_record" in km[code], f"{code} missing guidance_record"

    def test_page_fetch_failed_mapped(self):
        """PAGE_FETCH_FAILED should be in knowledge map."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "areos", "kb", "check_code_to_knowledge_map.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            km = json.load(f)
        assert "PAGE_FETCH_FAILED" in km


# ── T-304: ACTION_SNIPPETS ───────────────────────────────────────────────────

class TestT304ActionSnippets:
    def test_every_deduction_has_snippet(self):
        """Every code in LAYER_DEDUCTIONS should have an ACTION_SNIPPET."""
        from areos.auditors.scoring import LAYER_DEDUCTIONS
        from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
        phase2_codes = [c for c in LAYER_DEDUCTIONS.keys()
                       if c.startswith(("CONTENT_STALE", "CONTENT_AGING", "DATE_MISSING",
                                       "REDIRECT_", "META_NOINDEX", "CANONICAL_",
                                       "CLOAKING_", "AI_BOT_", "ENTITY_NAME_",
                                       "SAMEAS_", "WIKIDATA_", "IFRAME_", "IMAGES_",
                                       "ALL_CONTENT_", "VIDEO_", "SITEMAP_",
                                       "CITATION_RATE", "SHARE_OF_VOICE"))]
        missing = [c for c in phase2_codes if c not in ACTION_SNIPPETS]
        assert not missing, f"Missing from ACTION_SNIPPETS: {missing}"

    def test_unverifiable_snippets(self):
        """Unverifiable codes should have ACTION_SNIPPETS."""
        from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
        for code in ["SCHEMA_MISSING", "SCHEMA_UNVERIFIABLE", "ROBOTS_UNVERIFIABLE", "LLMS_UNVERIFIABLE"]:
            assert code in ACTION_SNIPPETS, f"{code} not in ACTION_SNIPPETS"

    def test_snippets_are_nonempty_strings(self):
        """All ACTION_SNIPPETS values must be non-empty strings."""
        from areos.auditors.audit_orchestrator import ACTION_SNIPPETS
        for code, snippet in ACTION_SNIPPETS.items():
            assert isinstance(snippet, str), f"{code} snippet is not a string"
            assert len(snippet) > 0, f"{code} snippet is empty"
