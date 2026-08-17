# areos/cli/research.py
#
# CLI entry point: `python -m areos.cli.research --stage AP-03`
# or via the top-level `areos` script if setup.py/pyproject.toml is configured.
#
# CONTRACT:
#   - This is a thin adapter. All logic lives in areos.services.research_service.
#   - Output is JSON to stdout (machine-readable) + human summary to stderr.
#   - NEVER writes to the live DB. Candidate output only.
#   - Saves output to candidates/<run_id>.json for Task 2c (diff step).

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root so this works whether run as a module or script
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
_CANDIDATES_DIR = _ROOT / "candidates"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="areos research",
        description=(
            "AREOS Research Command — fetch and LLM-extract candidate claims "
            "for a given audit pipeline stage. NEVER writes to the live DB."
        ),
    )
    parser.add_argument(
        "--stage",
        required=True,
        metavar="STAGE_ID",
        help="Audit phase ID to research (e.g. AP-03, AP-01). "
             "Must match a key in sources.yaml.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write JSON output to FILE instead of auto-naming in candidates/.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and sources for the stage, but do not "
             "make any HTTP or LLM calls.",
    )
    parser.add_argument(
        "--sources-yaml",
        metavar="PATH",
        default=None,
        help="Override path to sources.yaml (default: project root).",
    )

    args = parser.parse_args(argv)
    stage_id: str = args.stage.strip().upper()

    # --- Import here so the CLI can report import errors cleanly ---
    try:
        from areos.services.research_service import run_research, _load_sources_yaml, SOURCES_YAML_PATH
    except ImportError as e:
        _err(f"Import error: {e}")
        return 1

    sources_yaml_path = Path(args.sources_yaml) if args.sources_yaml else None

    # --- Dry-run mode ---
    if args.dry_run:
        return _dry_run(stage_id, sources_yaml_path or SOURCES_YAML_PATH)

    # --- Real run ---
    _info(f"[areos research] Stage: {stage_id} | Started: {datetime.now().isoformat()}")
    _info("CONTRACT: No DB writes will occur. Output is candidates only.")
    _info("-" * 60)

    try:
        bundle = run_research(stage_id, sources_yaml_path=sources_yaml_path)
    except ValueError as e:
        _err(str(e))
        return 1
    except EnvironmentError as e:
        _err(str(e))
        return 1

    # --- Write output ---
    _CANDIDATES_DIR.mkdir(exist_ok=True)
    out_path = (
        Path(args.output)
        if args.output
        else _CANDIDATES_DIR / f"{bundle['run_id']}.json"
    )
    
    import tempfile, os
    fd, tmp_path = tempfile.mkstemp(dir=out_path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(bundle, indent=2, ensure_ascii=False))
        os.replace(tmp_path, out_path)
    except Exception:
        os.unlink(tmp_path)
        raise

    # --- Human summary to stderr ---
    n_candidates = len(bundle["candidates"])
    n_sources    = len(bundle["sources_hit"])
    n_errors     = len(bundle["errors"])

    _info("")
    _info("=" * 60)
    _info(f"RESEARCH COMPLETE — {bundle['stage_name']} ({stage_id})")
    _info("=" * 60)
    _info(f"  Run ID:          {bundle['run_id']}")
    _info(f"  Sources fetched: {n_sources}")
    _info(f"  Candidates:      {n_candidates}")
    _info(f"  Errors:          {n_errors}")
    _info(f"  Output file:     {out_path}")
    _info("")

    if bundle["errors"]:
        _info("ERRORS (non-fatal):")
        for err in bundle["errors"]:
            _info(f"  {err}")
        _info("")

    if bundle["sources_hit"]:
        _info("SOURCES HIT:")
        for s in bundle["sources_hit"]:
            _info(f"  [{s['tier_label']:6s}] {s['name']} — {s['candidates_extracted']} candidates")
        _info("")

    if n_candidates > 0:
        _info("CANDIDATE CLAIMS (first 3 shown):")
        for c in bundle["candidates"][:3]:
            _info(f"  [{c['claim_scope']}] [{c['confidence']}] {c['statement'][:120]}...")
        if n_candidates > 3:
            _info(f"  ... and {n_candidates - 3} more. See {out_path}")
    else:
        _info("No candidates extracted. Check errors above or inspect fetched content.")

    # --- Machine-readable output to stdout ---
    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    return 0


def _dry_run(stage_id: str, yaml_path: Path) -> int:
    _info(f"[DRY RUN] Validating stage '{stage_id}' in {yaml_path}")
    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        _err(f"sources.yaml not found at {yaml_path}")
        return 1

    if stage_id not in data:
        valid = sorted(k for k in data if k.startswith("AP-"))
        _err(f"Stage '{stage_id}' not found. Valid: {valid}")
        return 1

    stage = data[stage_id]
    _info(f"  Stage name: {stage.get('name', '?')}")
    for tier in ("tier-1", "tier-2"):
        entries = stage.get(tier, [])
        _info(f"  {tier}: {len(entries)} source(s)")
        for e in entries:
            _info(f"    - {e.get('name', '?')} → {e.get('url', 'NO URL')}")
    _info("[DRY RUN] Configuration OK. No HTTP or LLM calls made.")
    return 0


def _info(msg: str) -> None:
    print(msg, file=sys.stderr)


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
