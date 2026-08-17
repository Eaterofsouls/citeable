# areos/db/stage_normalization.py
#
# Stage ID alias normalization.
# Spec: AREOS_KNOWLEDGE_INGESTION_SPEC.md §2.7
#
# Loads stage_id_aliases.yaml once (cached) and maps any raw stage string
# to a canonical STAGE-XX identifier.

from __future__ import annotations
from pathlib import Path
from typing import Optional

_ALIASES: dict[str, str] | None = None


def _load_aliases(alias_file: Path) -> dict[str, str]:
    global _ALIASES
    if _ALIASES is None:
        try:
            import yaml
            data = yaml.safe_load(alias_file.read_text(encoding="utf-8"))
        except ImportError:
            # Fallback: minimal YAML parser for simple key: value lines
            data = {"aliases": {}}
            for line in alias_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or ":" not in line or line.startswith("aliases"):
                    continue
                k, _, v = line.partition(":")
                data["aliases"][k.strip().strip('"')] = v.strip().strip('"')
        _ALIASES = {k.lower().strip(): v for k, v in data.get("aliases", {}).items()}
    return _ALIASES


def normalize_stage_id(raw: str, alias_file: Path) -> tuple[Optional[str], Optional[str]]:
    """
    Normalize a raw stage ID string to a canonical STAGE-XX.
    Returns (normalized, error_message).
    If normalization succeeds: (canonical_stage_id, None).
    If not found in aliases: (None, "STAGE_ALIAS_NOT_FOUND: '{raw}'").
    """
    aliases = _load_aliases(alias_file)
    key = raw.lower().strip()
    if key in aliases:
        return aliases[key], None
    return None, f"STAGE_ALIAS_NOT_FOUND: '{raw}' — add to stage_id_aliases.yaml before re-running"


def reset_cache() -> None:
    """Reset the alias cache. Use in tests only."""
    global _ALIASES
    _ALIASES = None
