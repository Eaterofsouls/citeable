#!/usr/bin/env python3
"""
scripts/generate_scoring_docs.py

Regenerates the scoring deduction table and access-gate table in docs/external.md
directly from the live definitions in areos.auditors.scoring.
Guarantees documentation parity with code.
"""

import sys
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from areos.auditors.scoring import LAYER_DEDUCTIONS, ACCESS_GATE, LAYERS

LAYER_DISPLAY = {
    "access": "Access",
    "schema": "Schema",
    "content": "Content",
    "citation": "Citation",
    "authority": "Authority",
}

LAYER_ORDER = {
    "access": 1,
    "schema": 2,
    "content": 3,
    "citation": 4,
    "authority": 5,
}

ACCESS_GATE_DESCRIPTIONS = {
    "CRAWLER_FULLY_BLOCKED": "a major AI crawler is fully disallowed",
    "CRAWLER_PARTIAL": "some AI crawlers are restricted",
    "CLOAKING_DETECTED": "cloaked content detected between bots and users",
    "META_NOINDEX": "page carries noindex directive blocking indexing",
}


def generate_deductions_table() -> str:
    """Generate Markdown deduction table from LAYER_DEDUCTIONS."""
    # Deterministic sorting: layer order, descending deduction points, then check code name
    sorted_items = sorted(
        LAYER_DEDUCTIONS.items(),
        key=lambda item: (LAYER_ORDER.get(item[1][0], 99), -item[1][1], item[0])
    )

    lines = [
        "| Check code | Layer | Deduction |",
        "|---|---|---|",
    ]
    for code, (layer, points) in sorted_items:
        layer_label = LAYER_DISPLAY.get(layer, layer.title())
        # Use Unicode minus \u2212 to match existing document style
        lines.append(f"| `{code}` | {layer_label} | \u2212{points} |")
    return "\n".join(lines)


def generate_access_gate_table() -> str:
    """Generate Markdown access gate table from ACCESS_GATE."""
    lines = [
        "| Trigger | Overall score capped at |",
        "|---|---|",
    ]
    for trigger, cap in ACCESS_GATE.items():
        desc = ACCESS_GATE_DESCRIPTIONS.get(trigger, "")
        label = f"`{trigger}` ({desc})" if desc else f"`{trigger}`"
        lines.append(f"| {label} | {cap} |")
    return "\n".join(lines)


def update_external_md(doc_path: Path | str | None = None) -> bool:
    """
    Update docs/external.md with generated scoring tables.
    Returns True if file was updated, False if already up-to-date.
    """
    if doc_path is None:
        doc_path = _ROOT / "docs" / "external.md"
    else:
        doc_path = Path(doc_path)

    content = doc_path.read_text(encoding="utf-8")

    deductions_table = generate_deductions_table()
    access_gate_table = generate_access_gate_table()

    # Exact delimiters for §5.3 deduction table
    t1_start_marker = "| Check code | Layer | Deduction |"
    t1_end_marker = "`CITATION_OBSERVED`"

    t1_start = content.find(t1_start_marker)
    if t1_start == -1:
        raise RuntimeError(f"Could not locate start of §5.3 deduction table ({t1_start_marker})")
    
    t1_end = content.find(t1_end_marker, t1_start)
    if t1_end == -1:
        raise RuntimeError(f"Could not locate end of §5.3 deduction table ({t1_end_marker})")

    # Replace table 1 (keeping the double newline before t1_end_marker)
    content = content[:t1_start] + deductions_table + "\n\n" + content[t1_end:]

    # Exact delimiters for §5.4 access gate table
    t2_start_marker = "| Trigger | Overall score capped at |"
    t2_end_marker = "The gate is a **ceiling**"

    t2_start = content.find(t2_start_marker)
    if t2_start == -1:
        raise RuntimeError(f"Could not locate start of §5.4 access gate table ({t2_start_marker})")
    
    t2_end = content.find(t2_end_marker, t2_start)
    if t2_end == -1:
        raise RuntimeError(f"Could not locate end of §5.4 access gate table ({t2_end_marker})")

    # Replace table 2 (keeping double newline before t2_end_marker)
    content = content[:t2_start] + access_gate_table + "\n\n" + content[t2_end:]

    # Also update "two specific findings" to "four specific findings" in §5.4 text for accuracy
    content = content.replace(
        "To encode this, two specific findings\napply a hard ceiling",
        "To encode this, four specific findings\napply a hard ceiling"
    )

    old_content = doc_path.read_text(encoding="utf-8")
    if content == old_content:
        return False

    doc_path.write_text(content, encoding="utf-8")
    return True


if __name__ == "__main__":
    doc = _ROOT / "docs" / "external.md"
    changed = update_external_md(doc)
    if changed:
        print("Updated docs/external.md with live scoring definitions.")
    else:
        print("docs/external.md is already up to date.")
