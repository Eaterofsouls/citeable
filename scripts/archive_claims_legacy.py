#!/usr/bin/env python3
"""
scripts/archive_claims_legacy.py

Task 8: Permanently archive the legacy claims_legacy table as claims_v1_archive.
Decision Date: 2026-09-27
Rationale: Task 7 removed the legacy claims table definition from schema.sql;
handle_claims_view() only creates the claims VIEW over knowledge. The existing
claims_legacy table is preserved as a permanent historical snapshot: claims_v1_archive.
"""

import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from areos.db.connection import get_db_path, get_connection


def archive_claims_legacy(db_path: Path | str | None = None) -> None:
    if db_path is None:
        db_path = get_db_path()
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    # Check if claims_legacy table exists
    row = cur.execute("SELECT type FROM sqlite_master WHERE name='claims_legacy'").fetchone()
    if row:
        print(f"Renaming claims_legacy -> claims_v1_archive in {db_path}...")
        cur.execute("DROP TABLE IF EXISTS claims_v1_archive")
        cur.execute("ALTER TABLE claims_legacy RENAME TO claims_v1_archive")
        conn.commit()
        print("Archive migration complete: claims_v1_archive created.")
    else:
        # Check if already archived
        arch_row = cur.execute("SELECT type FROM sqlite_master WHERE name='claims_v1_archive'").fetchone()
        if arch_row:
            print(f"claims_v1_archive already exists in {db_path}; no action needed.")
        else:
            print(f"Neither claims_legacy nor claims_v1_archive found in {db_path}.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    archive_claims_legacy(target)
