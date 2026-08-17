# areos/cli/approve.py
#
# Entry point for Task 2d: The Approval Workflow.
# Interactive script that reads a changelog and prompts the user
# to approve or reject each proposed change.
#
# CONTRACT:
#   - Approving an entry executes the DB write and updates the changelog status.
#   - Rejecting an entry updates the changelog status but doesn't touch the DB.

import argparse
import json
import logging
import sys
from pathlib import Path

from areos.db.connection import get_connection
from areos.db.context import write_as
from areos.db.lint import lint_claim
from areos.util.clock import utc_today_iso
from areos.services.auto_apply import record_approval, record_rejection

logger = logging.getLogger(__name__)

def apply_insert(conn, change: dict):
    data = change["claim_data"]
    # Provide default for last_verified
    last_verified = data.get("last_verified", utc_today_iso())
    data["last_verified"] = last_verified
    data["status"] = "active"
    
    errors = lint_claim(data)
    if errors:
        raise ValueError(f"Lint errors: {'; '.join(errors)}")
        
    conn.execute("""
        INSERT INTO claims (claim_id, stage_id, claim_scope, claim_type, statement, status, source_tier_vocab, source_tier_value, source_url, source_date, last_verified)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
    """, (
        data["claim_id"],
        data.get("stage_id", ""),  # Fallback
        data["claim_scope"],
        data["claim_type"],
        data["statement"],
        data["source_tier_vocab"],
        data["source_tier_value"],
        data.get("source_url", ""),
        data.get("source_date", ""),
        last_verified
    ))

def apply_update(conn, change: dict):
    target_id = change["target_claim_id"]
    changes = change.get("changes", {})
    last_verified = changes.get("last_verified", utc_today_iso())
    
    conn.execute("""
        UPDATE claims SET last_verified = ? WHERE claim_id = ?
    """, (last_verified, target_id))

def apply_flag_for_review(conn, change: dict):
    # For a contradiction, we insert the candidate as a 'contested' claim
    # and mark it as superseding nothing for now, but linked by topic.
    # We don't have the full candidate dict in FLAG_FOR_REVIEW if we only saved candidate_statement,
    # wait, the changelog might only have candidate_statement.
    # Let's check diff_service.py: we didn't include the full claim_data for contradicting.
    # If claim_data isn't there, we just update the target claim's status to 'contested'.
    
    target_id = change["target_claim_id"]
    conn.execute("""
        UPDATE claims SET status = 'contested' WHERE claim_id = ?
    """, (target_id,))

def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive approval workflow for proposed changelogs")
    parser.add_argument("--run-id", required=True, help="Run ID of the changelog to approve")
    parser.add_argument("--db-path", default="areos.db", help="Path to SQLite database")
    # Add auto-approve flag for tests
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve all for testing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    root_dir = Path(__file__).resolve().parents[2]
    changelog_path = root_dir / "changelogs" / f"{args.run_id}.json"
    db_path = root_dir / args.db_path
    
    if not changelog_path.exists():
        logger.error(f"[ERROR] Changelog not found: {changelog_path}")
        return 1

    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            changelog = json.load(f)
    except Exception as e:
        logger.error(f"[ERROR] Could not read changelog: {e}")
        return 1

    conn = get_connection(db_path)
    changes = changelog.get("proposed_changes", [])
    
    pending_changes = [c for c in changes if c.get("approval_status") not in ("approved", "rejected")]
    
    if not pending_changes:
        logger.info("No pending changes to review in this changelog.")
        return 0

    logger.info(f"Starting review of {len(pending_changes)} pending changes from run {args.run_id}.")
    
    modified_changelog = False
    
    for idx, change in enumerate(pending_changes, 1):
        action = change.get("action")
        classification = change.get("classification")
        cand_id = change.get("candidate_id")
            
        print(f"\n--- Change {idx}/{len(pending_changes)} ---")
        print(f"Candidate ID:   {cand_id}")
        print(f"Classification: {classification.upper()}")
        print(f"Proposed Action: {action}")
            
        if classification == "novel":
            print(f"Statement: {change.get('claim_data', {}).get('statement')}")
        elif classification == "corroborating":
            print(f"Target ID: {change.get('target_claim_id')}")
            print(f"Changes:   {change.get('changes')}")
        elif classification == "contradicting":
            print(f"Target ID:           {change.get('target_claim_id')}")
            print(f"Candidate Statement: {change.get('candidate_statement')}")
            print(f"Rationale:           {change.get('rationale')}")
            if "adversarial_critique" in change:
                print(f"\n[ADVERSARIAL CRITIQUE]\n{change['adversarial_critique']}\n")

        if args.auto_approve:
            choice = 'y'
        else:
            choice = input("Approve this change? [y/N]: ").strip().lower()

        if choice == 'y':
            try:
                with write_as(conn, actor="cli:approval", reason=f"Approved {cand_id}"):
                    if action == "INSERT":
                        # inject stage_id if missing in claim_data
                        if "stage_id" not in change["claim_data"]:
                            change["claim_data"]["stage_id"] = changelog.get("stage_id", "UNKNOWN")
                        apply_insert(conn, change)
                    elif action == "UPDATE":
                        apply_update(conn, change)
                    elif action == "FLAG_FOR_REVIEW":
                        apply_flag_for_review(conn, change)
                            
                    change["approval_status"] = "approved"
                        
                    # record approval for the source
                    source_url = change.get("claim_data", {}).get("source_url") or change.get("source_data", {}).get("source_url")
                    record_approval(conn, source_url)
                logger.info(f"[*] Approved {cand_id}")
            except Exception as e:
                logger.error(f"[!] Failed to approve {cand_id}: {e}")
        else:
            change["approval_status"] = "rejected"
                
            # record rejection for the source
            source_url = change.get("claim_data", {}).get("source_url") or change.get("source_data", {}).get("source_url")
            record_rejection(conn, source_url)
            conn.commit()
                
            logger.info(f"[ ] Rejected {cand_id}")
                
        modified_changelog = True

    if modified_changelog:
        with open(changelog_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2)
        logger.info("\nChangelog updated with approval states.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
