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
        # _txn_context is reset to NULL/NULL after the block, clean for the next caller.

    Raises:
        Any exception from the body of the `with` block is re-raised after
        rolling back the transaction and resetting _txn_context.
    """
    conn.execute(
        "UPDATE _txn_context SET actor = ?, reason = ? WHERE id = 1",
        (actor, reason),
    )
    rolled_back = False
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        logger.error("write_as() rolling back: %s", exc, exc_info=True)
        try:
            conn.rollback()
            rolled_back = True
        except Exception as rb_exc:
            logger.error("write_as() exception during rollback: %s", rb_exc)
        raise
    finally:
        # Only reset if we didn't roll back (since rollback already restores prior state).
        if not rolled_back:
            try:
                conn.execute(
                    "UPDATE _txn_context SET actor = NULL, reason = NULL WHERE id = 1"
                )
                conn.commit()
            except Exception as reset_exc:
                logger.warning("Failed to reset _txn_context: %s", reset_exc)
