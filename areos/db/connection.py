# areos/db/connection.py
#
# Single resolved connection factory.
# Every component that needs a database connection imports THIS function —
# never calls sqlite3.connect() directly. This ensures PRAGMAs are always set
# consistently and that WAL mode is never accidentally bypassed.
#
# ADR D1: SQLite + WAL + FK enforcement is ratified. Not open for re-litigation
# without the written-justification bar Bible §6.1 sets.
#
# MF-13: connections are cached per-thread AND per resolved db_path.
# The cache key is the resolved absolute path string, stored in _local.conns
# (a dict). This prevents the cross-test contamination bug described in the
# A5 corrected plan: two tests in the same thread with different temp-file
# paths will each get their own connection, not share the first thread's.
#
# MF-11: callers must NOT call conn.close() — the shutdown hook in main.py
# owns connection lifecycle via _close_pooled_connections().

import logging
import os
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# keyed by resolved absolute db_path string (MF-13).
_local = threading.local()

_all_conns: list[sqlite3.Connection] = []
_all_conns_lock = threading.Lock()


def get_db_path() -> str:
    """
    Single source of truth for resolving which DB file to use.

    FIX (Readiness Audit, Blocker 3): this used to live only in
    areos/api/dependencies.py. areos/db/ingest_claims.py — the documented
    KB-seeding entry point — never called it and instead hardcoded
    `<repo_root>/areos.db`, so on Render (where the running app reads
    /data/areos.db via the RENDER branch below) the documented seeding
    command silently wrote to the wrong, ephemeral file and the live app
    never saw the seeded claims. Moving this here (a module with no
    FastAPI/auth dependency) lets every caller — API, CLI seeding script,
    tests — share exactly one path-resolution rule instead of two that can
    drift apart.
    """
    import shutil

    test_db = os.environ.get("AREOS_TEST_DB")
    if test_db:
        return test_db
    if os.environ.get("RENDER"):
        data_db = Path("/data/areos.db")
        # Cloud auto-seeding safety mechanism: if the persistent disk is
        # newly mounted and empty, seed it from a pre-verified repository
        # database, if one happens to be present in the image.
        if not data_db.exists():
            root_db = Path(__file__).resolve().parents[2] / "areos.db"
            if root_db.exists():
                data_db.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root_db, data_db)
        return str(data_db)
    # Root of project (2 levels up from areos/db/connection.py)
    return str(Path(__file__).resolve().parents[2] / "areos.db")


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """
    Returns a per-thread, per-path cached SQLite connection (MF-13).

    PRAGMAs set on first open:
        foreign_keys = ON      — Bible Law 6.5, not optional.
        journal_mode = WAL     — readers (UI) don't block on a writer.
        synchronous  = NORMAL  — safe under WAL at this scale.
        busy_timeout = 30000   — wait 30 s rather than throwing on contention.

    row_factory is set to sqlite3.Row so callers can access columns by name.

    IMPORTANT: Do NOT call conn.close() on the returned connection.
    The shutdown hook (_close_pooled_connections in main.py) owns lifecycle.
    """
    db_str = str(Path(db_path).resolve())

    if not hasattr(_local, "conns"):
        _local.conns = {}

    if db_str not in _local.conns or _local.conns[db_str] is None:
        _local.conns[db_str] = _open_connection(db_str)
    else:
        # FIX (Readiness Audit, Part 2/UI-UX follow-up on connection pooling):
        # a cached connection can go stale if anything closes it out from under
        # the pool (a caller violating MF-11, a test fixture, an interrupted
        # process). Previously get_connection() would hand back that closed
        # connection object forever, and every subsequent call on this thread
        # for this db_path would raise sqlite3.ProgrammingError: Cannot operate
        # on a closed database, with no way to recover short of a process
        # restart. Detect it here and transparently reopen instead.
        try:
            _local.conns[db_str].execute("SELECT 1")
        except sqlite3.ProgrammingError:
            logger.warning(
                "Cached DB connection was closed externally, reopening: %s (thread=%s)",
                db_str,
                threading.current_thread().name,
            )
            _local.conns[db_str] = _open_connection(db_str)

    return _local.conns[db_str]


def _open_connection(db_str: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_str, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    logger.debug(
        "Opened new DB connection: %s (thread=%s)",
        db_str,
        threading.current_thread().name,
    )
    with _all_conns_lock:
        _all_conns.append(conn)
    return conn


def close_all_connections() -> None:
    """Close all open connections across all threads from the central registry."""
    with _all_conns_lock:
        for conn in _all_conns:
            try:
                conn.close()
                logger.debug("Closed pooled DB connection from central registry")
            except Exception as e:
                logger.warning("Error closing pooled connection: %s", e)
        _all_conns.clear()

    conns = getattr(_local, "conns", {})
    conns.clear()


def apply_schema(conn: sqlite3.Connection, schema_path: str | Path) -> None:
    """
    Applies schema.sql to the given connection.
    Used for first-time setup and in-memory test fixtures.
    """
    sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(sql)
