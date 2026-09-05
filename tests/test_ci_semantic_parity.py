import pytest
from scripts.verify_kb_semantic_parity import verify_parity


def test_ci_semantic_parity_gate_passes():
    """Verify that 100% of check codes are synchronized across KB, scoring, and remediation snippets."""
    assert verify_parity() is True
