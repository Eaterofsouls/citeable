# tests/test_kb_parity_gate.py
#
# Automated CI test guaranteeing 100% check code mapping parity between
# scoring engine LAYER_DEDUCTIONS and check_code_to_knowledge_map.json.

import json
from pathlib import Path
import pytest

from areos.auditors.scoring import LAYER_DEDUCTIONS
from areos.kb.build_kb import build as build_kb
from areos.kb.router import resolve


def test_all_layer_deductions_have_kb_mappings():
    """Verify every check code with a deduction has an entry in check_code_to_knowledge_map.json."""
    kb_map_path = Path(__file__).resolve().parents[1] / "areos" / "kb" / "check_code_to_knowledge_map.json"
    assert kb_map_path.exists(), "check_code_to_knowledge_map.json not found"

    with open(kb_map_path, "r", encoding="utf-8") as f:
        kb_map = json.load(f)

    missing_mappings = []
    for check_code in LAYER_DEDUCTIONS:
        if check_code not in kb_map:
            missing_mappings.append(check_code)

    assert not missing_mappings, f"Check codes in LAYER_DEDUCTIONS missing from KB map: {missing_mappings}"


def test_audit_phase_crashed_parity(tmp_path):
    """Verify AUDIT_PHASE_CRASHED maps correctly in scoring and KB router."""
    assert "AUDIT_PHASE_CRASHED" in LAYER_DEDUCTIONS
    layer, pts = LAYER_DEDUCTIONS["AUDIT_PHASE_CRASHED"]
    assert layer == "access"
    assert pts == 5

    db_path = tmp_path / "parity_test.db"
    build_kb(db_path=str(db_path))

    resolution = resolve("AUDIT_PHASE_CRASHED", db_path=str(db_path))
    assert resolution.path == "DETERMINISTIC"
    assert resolution.primary_kid == "KT-124"
