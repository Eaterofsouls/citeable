# areos/cli/critique_changelog.py
#
# Entry point for Task 2g.
# Reads a proposed changelog, finds any 'contradicting' entries,
# runs them through the adversarial check (hostilereviewer), and
# attaches the critique directly into the changelog JSON.

import argparse
import json
import logging
import sys
from pathlib import Path

from areos.services.adversarial_service import generate_critique

logger = logging.getLogger(__name__)

def main() -> int:
    parser = argparse.ArgumentParser(description="Run adversarial check on contradicting changelog entries")
    parser.add_argument("--run-id", required=True, help="Run ID of the changelog to process")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    root_dir = Path(__file__).resolve().parents[2]
    changelog_path = root_dir / "changelogs" / f"{args.run_id}.json"
    
    if not changelog_path.exists():
        logger.error(f"[ERROR] Changelog not found: {changelog_path}")
        return 1

    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            changelog = json.load(f)
    except Exception as e:
        logger.error(f"[ERROR] Could not read changelog: {e}")
        return 1

    changes = changelog.get("proposed_changes", [])
    contradictions = [c for c in changes if c.get("classification") == "contradicting"]
    
    logger.info(f"Loaded changelog for run {args.run_id}.")
    logger.info(f"Found {len(contradictions)} contradicting entries out of {len(changes)} total.")

    modified = False
    for c in contradictions:
        if "adversarial_critique" in c:
            continue
            
        logger.info(f"Running adversarial critique on candidate {c['candidate_id']}...")
        
        # Build an artifact string for the adversarial service
        artifact_text = (
            f"CANDIDATE STATEMENT:\n{c.get('candidate_statement', 'UNKNOWN')}\n\n"
            f"TARGET CLAIM ID (Existing): {c.get('target_claim_id')}\n"
            f"RATIONALE FOR CONTRADICTION: {c.get('rationale')}"
        )
        
        critique = generate_critique(artifact_text, persona="hostilereviewer")
        c["adversarial_critique"] = critique
        modified = True

    if modified:
        try:
            with open(changelog_path, "w", encoding="utf-8") as f:
                json.dump(changelog, f, indent=2)
            logger.info("=" * 60)
            logger.info("CRITIQUES ATTACHED AND CHANGELOG SAVED")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"[ERROR] Failed to save updated changelog: {e}")
            return 1
    else:
        logger.info("No new critiques to attach.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
