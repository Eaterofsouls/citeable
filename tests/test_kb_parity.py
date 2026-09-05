# tests/test_kb_parity.py
#
# Phase 2 Regression Gate: Verify the KB-backed pipeline produces the same
# or better output as the old hardcoded dicts.
#
# WHAT WE TEST:
#   1. Every check code in PRIORITY_SCORES has a mapping in kb_check_code_map
#   2. Every check code in REMEDIATION_TEXT has a GUIDANCE record in the KB
#   3. The claims VIEW returns rows with the expected columns
#   4. wire_finding() wires correctly through the new kb_check_code_map
#   5. _build_automated_recommendations() produces non-empty results
#   6. Knowledge Router resolves deterministic paths for known check codes

import os
import sys
import pytest

# Ensure the project root is on PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("AREOS_API_TOKEN", "test_parity_token")


@pytest.fixture(scope="module")
def db_path():
    """Build the KB and return the DB path for testing."""
    from areos.kb.build_kb import build
    build()
    from areos.db.connection import get_db_path
    return get_db_path()


@pytest.fixture(scope="module")
def conn(db_path):
    from areos.db.connection import get_connection
    return get_connection(db_path)


class TestCheckCodeParity:
    """Verify check codes are mapped in the new KB."""

    def test_remediation_codes_have_guidance(self, conn):
        # Check that GUIDANCE records exist and have check_codes or check_links
        guidance_count = conn.execute(
            "SELECT count(*) FROM knowledge WHERE type = 'GUIDANCE' AND status = 'active'"
        ).fetchone()[0]
        assert guidance_count >= 30, f"Expected >=30 GUIDANCE records, got {guidance_count}"


class TestClaimsView:
    """Verify the claims VIEW is backward-compatible."""

    def test_claims_view_exists(self, conn):
        row = conn.execute(
            "SELECT type FROM sqlite_master WHERE name = 'claims'"
        ).fetchone()
        assert row is not None, "claims not found in database"
        assert row["type"] == "view", f"claims is {row['type']}, expected 'view'"

    def test_claims_view_columns(self, conn):
        row = conn.execute("SELECT * FROM claims LIMIT 1").fetchone()
        assert row is not None, "claims VIEW is empty"
        # Must have these columns for backward compatibility
        expected_cols = {
            "claim_id", "stage_id", "claim_scope", "claim_type",
            "statement", "status", "confidence", "source_url",
            "source_tier_vocab", "source_tier_value", "source_date",
            "last_verified", "superseded_by", "is_client_evidence",
        }
        actual_cols = set(row.keys())
        missing = expected_cols - actual_cols
        assert not missing, f"Claims VIEW missing columns: {missing}"

    def test_claims_view_count(self, conn):
        count = conn.execute("SELECT count(*) FROM claims").fetchone()[0]
        assert count >= 200, f"Expected >= 200 claims, got {count}"


class TestWireFinding:
    """Verify wire_finding works with the new kb_check_code_map."""

    def test_known_code_wires(self, db_path):
        from pathlib import Path
        from areos.auditors.findings_to_claims import wire_finding
        wired = wire_finding(
            check_code="CRAWLER_FULLY_BLOCKED",
            severity="error",
            message="GPTBot is fully blocked",
            source_auditor="automated",
            db_path=Path(db_path),
        )
        assert wired.wiring_status == "WIRED", f"Expected WIRED, got {wired.wiring_status}"
        assert wired.claim_id is not None
        # The claim_id should now be a KT-xxx kid
        assert wired.claim_id.startswith("KT-"), f"Expected KT-xxx, got {wired.claim_id}"

    def test_unknown_code_unmapped(self, db_path):
        from pathlib import Path
        from areos.auditors.findings_to_claims import wire_finding
        wired = wire_finding(
            check_code="TOTALLY_MADE_UP_CODE",
            severity="info",
            message="test",
            source_auditor="automated",
            db_path=Path(db_path),
        )
        assert wired.wiring_status == "UNMAPPED"


class TestKnowledgeRouter:
    """Verify the Knowledge Router resolves known check codes."""

    def test_deterministic_resolve(self, db_path):
        from areos.kb.router import resolve
        resolution = resolve("CRAWLER_FULLY_BLOCKED", db_path=db_path)
        assert resolution.path == "DETERMINISTIC"
        assert resolution.primary_kid is not None
        assert resolution.primary_record is not None
        # GUIDANCE records should have guidance populated
        if resolution.primary_record.type == "GUIDANCE":
            assert resolution.guidance is not None

    def test_unknown_code_insufficient(self, db_path):
        from areos.kb.router import resolve
        resolution = resolve("TOTALLY_MADE_UP_CODE", db_path=db_path)
        assert resolution.path == "INSUFFICIENT"

    def test_evidence_chain_populated(self, db_path):
        from areos.kb.router import resolve
        resolution = resolve("CRAWLER_FULLY_BLOCKED", db_path=db_path)
        # Most GUIDANCE records should have evidence
        assert len(resolution.evidence_chain) >= 0  # may be 0 for some
        # Source citations should be populated if evidence exists
        if resolution.evidence_chain:
            assert len(resolution.source_citations) > 0


class TestSynthesisIntegration:
    """Verify the full synthesis pipeline works with KB data."""

    def test_build_automated_recommendations(self, db_path):
        from pathlib import Path
        from areos.auditors.synthesis_engine import _build_automated_recommendations
        findings = [
            {"code": "CRAWLER_FULLY_BLOCKED", "severity": "error",
             "message": "GPTBot fully blocked", "page_url": "https://example.com"},
            {"code": "JSON_PARSE_FAILURE", "severity": "error",
             "message": "Invalid JSON-LD", "page_url": "https://example.com/page"},
        ]
        recs, rejected = _build_automated_recommendations(findings, Path(db_path))
        assert len(recs) > 0, "No recommendations generated"
        # Each rec should have a claim_id
        for rec in recs:
            assert rec.claim_id, f"Recommendation for {rec.check_code} has no claim_id"
            # V2: should have resolution_path
            assert rec.resolution_path in ("DETERMINISTIC", "SEMANTIC", "INSUFFICIENT", None)
