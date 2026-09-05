import sqlite3
from collections.abc import Generator
from fastapi import Header, HTTPException, Request

from areos.db.connection import get_connection, get_db_path
# We need to import _API_TOKEN from wherever it lives, or read it here.
# For now we'll recreate the logic from main.py
import os

_API_TOKEN = os.environ.get("AREOS_API_TOKEN")
if not _API_TOKEN:
    raise RuntimeError(
        "AREOS_API_TOKEN environment variable is not set. "
        "AREOS will not start without an explicit admin token."
    )

# get_db_path() now lives in areos.db.connection (Readiness Audit, Blocker 3)
# so non-FastAPI callers like areos/db/ingest_claims.py can share the exact
# same Render-aware path resolution without importing this module (which
# requires AREOS_API_TOKEN to already be set just to import it).

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """MF-3: Yield a pooled DB connection without closing it (MF-13)."""
    conn = get_connection(get_db_path())
    try:
        yield conn
    finally:
        if getattr(conn, "in_transaction", False):
            try:
                conn.rollback()
            except Exception:
                pass

def verify_admin(authorization: str | None = Header(None)) -> None:
    """Verify API token using constant-time comparison."""
    import hmac
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    if not hmac.compare_digest(parts[1], _API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid API token")

def get_client_keys(request: Request) -> dict[str, str]:
    """Extract BYOK API keys from request headers."""
    keys = {}
    for header, value in request.headers.items():
        header_lower = header.lower()
        if header_lower.startswith("x-api-key-"):
            provider = header_lower.replace("x-api-key-", "").lower()
            keys[provider] = value.strip()
        elif header_lower.startswith("x-api-base-"):
            provider_base = header_lower.replace("-", "_")  # e.g., x-api-base-azure -> x_api_base_azure
            keys[provider_base] = value.strip()
    return keys
