#!/usr/bin/env python3
"""
scripts/backup_db.py — Online SQLite Backup Utility (TASK-10 / DEC-10)

Performs live, non-blocking online backups of the SQLite database using
the SQLite Online Backup API (conn.backup), safe for WAL mode under concurrent writes.
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from areos.db.connection import get_connection, get_db_path


def backup_database(source_db_path: str | None = None, dest_dir: str | Path | None = None, max_retained: int = 10) -> Path:
    """
    Perform an online backup of the SQLite database.
    
    Args:
        source_db_path: Path to source SQLite database (defaults to resolved get_db_path()).
        dest_dir: Directory where the timestamped backup file should be saved.
        max_retained: Number of most recent backups to retain (older ones pruned).
        
    Returns:
        Path to the newly created backup database file.
    """
    if source_db_path is None:
        source_db_path = get_db_path()
        
    if dest_dir is None:
        if os.environ.get("RENDER") or Path("/data").exists():
            dest_dir = Path("/data/backups")
        else:
            dest_dir = _ROOT / "backups"
    else:
        dest_dir = Path(dest_dir)
        
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = dest_dir / f"areos_backup_{timestamp}.db"
    
    src_conn = get_connection(source_db_path)
    dst_conn = sqlite3.connect(str(backup_file))
    
    try:
        # Perform online backup (pages copied in non-blocking slices)
        src_conn.backup(dst_conn, pages=100)
        
        # Verify integrity of backup
        cursor = dst_conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        status = cursor.fetchone()[0]
        if status != "ok":
            raise RuntimeError(f"Backup integrity check failed: {status}")
            
        print(f"[SUCCESS] SQLite online backup completed: {backup_file} (Integrity: {status})")

        # Prune old backups if count exceeds max_retained
        try:
            existing = sorted(dest_dir.glob("areos_backup_*.db"), key=lambda f: f.stat().st_mtime)
            if len(existing) > max_retained:
                for old_backup in existing[:-max_retained]:
                    try:
                        old_backup.unlink()
                        print(f"[PRUNE] Removed old backup: {old_backup.name}")
                    except OSError:
                        pass
        except Exception:
            pass

        return backup_file
    finally:
        dst_conn.close()



if __name__ == "__main__":
    from areos.db.connection import close_all_connections
    parser = argparse.ArgumentParser(description="Citeable SQLite Online Backup Tool")
    parser.add_argument("--source", default=None, help="Source database path")
    parser.add_argument("--dest", default=None, help="Destination directory for backup file")
    args = parser.parse_args()
    
    try:
        backup_database(args.source, args.dest)
    finally:
        close_all_connections()

