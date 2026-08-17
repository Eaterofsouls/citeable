import json
import sqlite3
from collections.abc import Callable

from fastapi import HTTPException

IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"

def with_idempotency(conn: sqlite3.Connection, key: str | None, endpoint: str, handler: Callable[[], tuple[int, dict]]) -> tuple[int, dict]:  # noqa: E501
    """
    Executes handler idempotently if key is provided.
    Returns (status_code, response_dict).
    """
    if not key:
        return handler()

    # Attempt to insert pending sentinel
    try:
        conn.execute(
            "INSERT INTO idempotency_keys (idempotency_key, endpoint, response_status, response_body) VALUES (?, ?, ?, ?)",  # noqa: E501
            (key, endpoint, 202, IDEMPOTENCY_IN_PROGRESS)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Key exists, check state
        row = conn.execute(
            "SELECT response_status, response_body FROM idempotency_keys WHERE idempotency_key = ?", (key,)  # noqa: E501
        ).fetchone()
        
        if not row:
            # Extremely rare race condition where it was deleted between insert and select
            return handler()
            
        status, body = row
        if body == IDEMPOTENCY_IN_PROGRESS:
            raise HTTPException(status_code=409, detail="Request already in progress") from None
        
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = body
            
        return status, parsed_body

    # Execute handler
    try:
        status, body = handler()
        
        # Update row with result
        conn.execute(
            "UPDATE idempotency_keys SET response_status = ?, response_body = ? WHERE idempotency_key = ?",  # noqa: E501
            (status, json.dumps(body), key)
        )
        conn.commit()
        return status, body
    except Exception as e:
        # If the handler fails, we should either leave it in progress or clear it.
        # Often it's safer to delete so they can retry, but if it failed halfway, it might need manual intervention.  # noqa: E501
        # We will delete the key on unhandled exceptions so the client can retry cleanly.
        conn.execute("DELETE FROM idempotency_keys WHERE idempotency_key = ?", (key,))
        conn.commit()
        raise e
