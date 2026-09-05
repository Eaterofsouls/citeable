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
_ALIASES_MTIME: float | None = None


def _load_aliases(alias_file: Path) -> dict[str, str]:
    global _ALIASES, _ALIASES_MTIME
    current_mtime = alias_file.stat().st_mtime if alias_file.exists() else 0.0
    if _ALIASES is None or _ALIASES_MTIME != current_mtime:
        _ALIASES_MTIME = current_mtime
        default_aliases = {
            "stage-01": "STAGE-01", "stage-02": "STAGE-02", "stage-03": "STAGE-03",
            "stage-04": "STAGE-04", "stage-05": "STAGE-05",
            "ap-01": "STAGE-01", "ap-02": "STAGE-02", "ap-03": "STAGE-03",
            "ap-04": "STAGE-04", "ap-05": "STAGE-05",
        }
        if not alias_file.exists():
            _ALIASES = default_aliases
            return _ALIASES
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
        aliases_map = data.get("aliases", {}) if isinstance(data, dict) else {}
        _ALIASES = {k.lower().strip(): v for k, v in aliases_map.items()} if aliases_map else default_aliases
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
