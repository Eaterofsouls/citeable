# areos/db/kb_version.py
#
# Knowledge base version management.
# Spec: AREOS_ONTOLOGY_EVOLUTION_SPEC.md §3.6

import datetime
import sqlite3


def increment_kb_version(conn: sqlite3.Connection, actor: str) -> str:
    """
    Increment the kb_version in kb_meta and update total_claims.
    Must be called inside an active write_as context.
    Returns the new version string.
    """
    today = datetime.date.today().strftime("%Y.%m.%d")

    meta = conn.execute("SELECT kb_version FROM kb_meta WHERE id = 1").fetchone()
    current = meta["kb_version"] if meta else f"{today}.0"

    parts = current.rsplit(".", 1)
    if parts[0] == today:
        n = int(parts[1]) + 1
    else:
        n = 1
    new_version = f"{today}.{n}"

    total_claims = conn.execute("SELECT COUNT(*) AS c FROM claims").fetchone()["c"]

    conn.execute(
        "UPDATE kb_meta SET kb_version = ?, last_updated = datetime('now'), "
        "total_claims = ?, updated_by = ? WHERE id = 1",
        (new_version, total_claims, actor)
    )
    return new_version


def get_kb_version(conn: sqlite3.Connection) -> dict | None:
    """Return the current kb_meta row or None if the table doesn't exist."""
    try:
        row = conn.execute(
            "SELECT kb_version, last_updated, total_claims, updated_by FROM kb_meta WHERE id = 1"
        ).fetchone()
        if row:
            return {
                "kb_version": row["kb_version"],
                "last_updated": row["last_updated"],
                "total_claims": row["total_claims"],
                "updated_by": row["updated_by"],
            }
        return None
    except Exception:
        return None
