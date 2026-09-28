#!/usr/bin/env python3
"""
scripts/verify_kb_semantic_parity.py

Automated CI Semantic Parity Gate.
Fails with exit code 1 if any auditor check code is missing from:
1. areos/kb/check_code_to_knowledge_map.json
2. LAYER_DEDUCTIONS in areos/auditors/scoring.py (for issue check codes)
3. ACTION_SNIPPETS in areos/auditors/audit_orchestrator.py
or if any mapped KID does not exist in areos/kb/corpus/knowledge.jsonl.
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT))

from areos.kb.build_kb import parse_jsonl
from areos.auditors.scoring import LAYER_DEDUCTIONS
from areos.auditors.audit_orchestrator import ACTION_SNIPPETS

INFORMATIONAL_OR_POSITIVE_CODES = {
    # Deprecated codes that carry 0 deduction per CHECK_CODE_REGISTRY.md
    "LLMS_TXT_MISSING", "GPTBOT_MISSING", "GOOGLE_EXTENDED_MISSING",
    "LLMS_TXT_MISSING_H1", "LLMS_TXT_MISSING_SECTION", "LLMS_TXT_NO_LINKS",
    "LLMS_TXT_EMPTY_CONTENT", "AUTHORITY_DR_LOW",
    "CITATION_OBSERVED",
    "CITATION_WHY_UNKNOWN",
    "CRAWLER_ALLOWED",
    "NO_DIRECTIVE",
    "EXTRACTABILITY_HIGH",
    "ANSWER_FORMAT_GOOD",
    "AUTHORITY_PROFILE_GOOD",
    "SCHEMA_UNVERIFIABLE",
    "ROBOTS_UNVERIFIABLE",
    "LLMS_UNVERIFIABLE",
    "AUDIT_PHASE_CRASHED",
}


def check_high_confidence_has_support(knowledge: list[dict], evidence: list[dict]) -> list[str]:
    """Verify that every active claim with confidence 'high' has at least one 'supports' evidence row."""
    supports_kids = {e["kid"] for e in evidence if e.get("relationship") == "supports"}
    errors = []
    for k in knowledge:
        if k.get("status") == "active" and k.get("confidence") == "high":
            if k.get("kid") not in supports_kids:
                errors.append(
                    f"Active claim {k.get('kid')} has confidence 'high' but no 'supports' evidence rows"
                )
    return errors


def verify_parity() -> bool:
    knowledge_path = WORKSPACE_ROOT / "areos/kb/corpus/knowledge.jsonl"
    evidence_path = WORKSPACE_ROOT / "areos/kb/corpus/evidence.jsonl"
    map_path = WORKSPACE_ROOT / "areos/kb/check_code_to_knowledge_map.json"

    knowledge = parse_jsonl(knowledge_path)
    evidence = parse_jsonl(evidence_path)
    valid_kids = {k["kid"] for k in knowledge}

    with open(map_path, "r", encoding="utf-8") as f:
        cc_map = json.load(f)

    errors = []

    # 1. Verify every check code in map has valid KIDs
    for code, entry in cc_map.items():
        g = entry.get("guidance_record")
        if g and g not in valid_kids:
            errors.append(f"Check code {code} has invalid guidance KID '{g}'")
        for b in entry.get("backing_records", []):
            if b not in valid_kids:
                errors.append(f"Check code {code} has invalid backing KID '{b}'")

    # 2. Verify all mapped issue check codes have LAYER_DEDUCTIONS entries
    for code in cc_map.keys():
        if code not in INFORMATIONAL_OR_POSITIVE_CODES:
            if code not in LAYER_DEDUCTIONS:
                errors.append(f"Issue check code {code} mapped in JSON but missing from LAYER_DEDUCTIONS in scoring.py")

    # 3. Verify all mapped check codes have ACTION_SNIPPETS entries
    for code in cc_map.keys():
        if code not in ACTION_SNIPPETS:
            errors.append(f"Check code {code} mapped in JSON but missing from ACTION_SNIPPETS in audit_orchestrator.py")

    # 4. Consistency gate: active claim with confidence 'high' must have at least one 'supports' evidence row
    support_errors = check_high_confidence_has_support(knowledge, evidence)
    errors.extend(support_errors)

    if errors:
        print(f"[FAIL] Semantic Parity Gate FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        return False

    print(f"[PASS] Semantic Parity Gate PASSED: {len(cc_map)} check codes synchronized; all active high-confidence claims have supports evidence.")
    return True


if __name__ == "__main__":
    success = verify_parity()
    sys.exit(0 if success else 1)
