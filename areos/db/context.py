# areos/db/context.py
#
# write_as() — the ONE place "who did this and why" reaches the database engine.
#
# Pattern (ADR D3):
#   Triggers own the mechanical guarantee (they fire on EVERY write, regardless of
#   which code path performed it). Application code owns the semantic context
#   (actor, reason) via a one-row staging table (_txn_context) set immediately
#   before the write, inside the same transaction.
#
# EVERY write path in the system (CLI, API, worker) MUST go through this context
# manager. Calling conn.execute("UPDATE claims ...") outside of write_as() is
# forbidden — it will still be logged by the trigger (mechanical guarantee holds),
# but actor/reason will be NULL in the changelog (semantic context lost).

import contextlib
import logging
import sqlite3

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def write_as(conn: sqlite3.Connection, actor: str, reason: str):
    """
    Context manager that attaches actor/reason to the current transaction so
    that the auto-generated AFTER INSERT/UPDATE triggers can record them in the
    changelog without needing to know anything about the calling code.

    Usage:
        with write_as(conn, actor="operator:you", reason="approved CLM-042"):
            conn.execute("UPDATE claims SET status = 'active' WHERE claim_id = ?",
                         ("CLM-042",))
        # conn.commit() is called automatically on clean exit.

    Raises:
        Any exception from the body of the `with` block is re-raised after
        rolling back the transaction.
    """
    try:
        cur = conn.execute(
            "UPDATE _txn_context SET actor = ?, reason = ? WHERE id = 1",
            (actor, reason),
        )
        if cur.rowcount == 0:
            conn.execute("INSERT OR REPLACE INTO _txn_context (id, actor, reason) VALUES (1, ?, ?)", (actor, reason))
    except sqlite3.OperationalError:
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS _txn_context (id INTEGER PRIMARY KEY, actor TEXT, reason TEXT)")
        conn.execute("INSERT OR REPLACE INTO _txn_context (id, actor, reason) VALUES (1, ?, ?)", (actor, reason))
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        logger.error("write_as() rolling back: %s", exc, exc_info=True)
        try:
            conn.rollback()
        except Exception as rb_exc:
            logger.error("write_as() exception during rollback: %s", rb_exc)
        raise
