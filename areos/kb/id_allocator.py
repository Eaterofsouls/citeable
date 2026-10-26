# areos/kb/id_allocator.py
"""
Monotonically increasing ID allocator for AREOS Knowledge Base.
Inspects production corpus files to compute next available IDs for
knowledge claims (KT-xxx), sources (SRC-xxx), and evidence links (EV-xxx).
"""

from __future__ import annotations
import json
import re
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"


def get_next_id(filename: str, key: str, prefix: str, min_digits: int = 3) -> str:
    path = CORPUS_DIR / filename
    if not path.exists():
        return f"{prefix}{1:0{min_digits}d}"
    max_num = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rec = json.loads(line)
                val = rec.get(key, "")
                m = re.match(rf"^{prefix}(\d+)$", val)
                if m:
                    max_num = max(max_num, int(m.group(1)))
            except Exception:
                continue
    return f"{prefix}{max_num + 1:0{min_digits}d}"


def get_next_available_ids() -> dict[str, str]:
    return {
        "kid": get_next_id("knowledge.jsonl", "kid", "KT-", 3),
        "sid": get_next_id("sources.jsonl", "sid", "SRC-", 3),
        "eid": get_next_id("evidence.jsonl", "eid", "EV-", 3),
    }


if __name__ == "__main__":
    ids = get_next_available_ids()
    print("Next Available IDs:")
    print(f"  Claim ID (kid):    {ids['kid']}")
    print(f"  Source ID (sid):   {ids['sid']}")
    print(f"  Evidence ID (eid): {ids['eid']}")
