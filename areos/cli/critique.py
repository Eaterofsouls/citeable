# areos/cli/critique.py
#
# Entry point for `areos critique --artifact PATH --persona NAME`.
# Part of Task 2f: Adversarial Check Script.

import argparse
import sys
from pathlib import Path
import logging

from areos.services.adversarial_service import generate_critique, PERSONAS

logger = logging.getLogger(__name__)

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an adversarial critique for an artifact")
    parser.add_argument("--artifact", required=True, help="Path to the artifact file (markdown, text, json)")
    parser.add_argument("--persona", required=True, choices=list(PERSONAS.keys()), help="Which adversarial persona to use")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    root_dir = Path(__file__).resolve().parents[2]
    artifact_path = root_dir / args.artifact
    
    if not artifact_path.exists():
        logger.error(f"[ERROR] Artifact not found: {artifact_path}")
        return 1

    try:
        artifact_text = artifact_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"[ERROR] Could not read artifact: {e}")
        return 1

    logger.info(f"Running adversarial critique on {artifact_path.name} using {args.persona} persona...")
    
    critique = generate_critique(artifact_text, args.persona)
    
    # Save critique alongside the artifact, or print it if it's a test
    out_path = artifact_path.parent / f"{artifact_path.stem}_critique_{args.persona}.md"
    
    try:
        out_path.write_text(critique, encoding="utf-8")
        logger.info("=" * 60)
        logger.info(f"CRITIQUE GENERATED: {out_path}")
        logger.info("=" * 60)
        print(critique)
    except Exception as e:
        logger.error(f"[ERROR] Failed to save critique: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
