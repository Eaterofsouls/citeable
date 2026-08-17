# areos/cli/diff.py
#
# Entry point for `areos diff --run-id N`.
# Part of Task 2c: Building the diff step.
#
# Generates a proposed changelog for a given research run without modifying the DB.

import argparse
import json
import logging
import sys
from pathlib import Path

from areos.services.diff_service import generate_changelog

logger = logging.getLogger(__name__)

def main() -> int:
    parser = argparse.ArgumentParser(description="Diff candidate claims against live DB")
    parser.add_argument("--run-id", required=True, help="Run ID of the candidates to process")
    parser.add_argument("--db-path", default="areos.db", help="Path to SQLite database")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    root_dir = Path(__file__).resolve().parents[2]
    db_path = root_dir / args.db_path
    
    candidates_dir = root_dir / "candidates"
    candidate_file = candidates_dir / f"{args.run_id}.json"
    
    if not candidate_file.exists():
        logger.error(f"[ERROR] Candidate file not found: {candidate_file}")
        return 1

    try:
        with open(candidate_file, "r", encoding="utf-8") as f:
            candidate_bundle = json.load(f)
    except Exception as e:
        logger.error(f"[ERROR] Failed to read candidate file: {e}")
        return 1
        
    logger.info(f"Loaded {len(candidate_bundle.get('candidates', []))} candidates for run {args.run_id}")
    logger.info(f"Stage: {candidate_bundle.get('stage_id')}")
    
    try:
        changelog = generate_changelog(str(db_path), candidate_bundle)
    except Exception as e:
        logger.error(f"[ERROR] Failed to generate changelog: {e}")
        return 1
        
    changelogs_dir = root_dir / "changelogs"
    changelogs_dir.mkdir(exist_ok=True)
    changelog_file = changelogs_dir / f"{args.run_id}.json"
    
    try:
        import tempfile, os
        fd, tmp_path = tempfile.mkstemp(dir=changelog_file.parent, prefix=".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(changelog, f, indent=2)
            os.replace(tmp_path, changelog_file)
        except Exception:
            os.unlink(tmp_path)
            raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to write changelog file: {e}")
        return 1
        
    logger.info("=" * 60)
    logger.info("DIFF COMPLETE (Propose, Never Apply)")
    logger.info("=" * 60)
    logger.info(f"  Run ID:      {args.run_id}")
    logger.info(f"  Stage ID:    {candidate_bundle.get('stage_id')}")
    logger.info(f"  Candidates:  {len(candidate_bundle.get('candidates', []))}")
    logger.info(f"  Changes:     {len(changelog.get('proposed_changes', []))}")
    logger.info(f"  Output file: {changelog_file}")
    
    stats = {"novel": 0, "corroborating": 0, "contradicting": 0}
    for c in changelog.get('proposed_changes', []):
        cls = c.get("classification")
        if cls in stats:
            stats[cls] += 1
            
    logger.info("CLASSIFICATIONS:")
    logger.info(f"  Novel:         {stats['novel']}")
    logger.info(f"  Corroborating: {stats['corroborating']}")
    logger.info(f"  Contradicting: {stats['contradicting']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
