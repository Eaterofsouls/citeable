import hmac
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from areos.api.error_codes import ErrorCode
from areos.api.dependencies import get_db_path, get_db
from areos.db.connection import close_all_connections
from areos.db.migrate_audit_tables import migrate
from areos.util.logging_config import _error_id_ctx, setup_logging

# Import routers
from areos.api.routers import claims, approvals, audit, verdicts, reports, prompts, byok, synthesis, knowledge

logger = logging.getLogger(__name__)
setup_logging()


async def _periodic_backup_loop():
    """Background task to periodically back up SQLite database to persistent disk."""
    import asyncio
    try:
        from scripts.backup_db import backup_database
        # Wait 300s after startup so initialization and healthchecks are complete
        await asyncio.sleep(300)
        while True:
            try:
                backup_database()
            except Exception as e:
                logger.warning("Periodic DB backup failed: %s", e)
            # Run every 12 hours
            await asyncio.sleep(43200)
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = get_db_path()
    # Ensure all required tables exist on startup. Raises on failure (MF-9).
    migrate(db_path)
    logger.info("AREOS API started. DB migrations applied.")

    # Cloud/Fresh-disk auto-seeding: build Knowledge Base if missing or empty
    try:
        from areos.db.connection import get_connection
        conn = get_connection(db_path)
        kb_row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge'"
        ).fetchone()
        kb_empty = not kb_row or (conn.execute("SELECT count(*) FROM knowledge").fetchone()[0] == 0)
        if kb_empty:
            logger.info("Knowledge base empty or missing. Auto-building from corpus...")
            from areos.kb.build_kb import build
            build(db_path)
            logger.info("Knowledge base build complete.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to auto-seed Knowledge Base: %s", exc, exc_info=True)

    import asyncio
    backup_task = asyncio.create_task(_periodic_backup_loop())

    yield
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
    # MF-11: Close all pooled connections before the process exits.
    close_all_connections()
    logger.info("AREOS API shutdown. Pooled DB connections closed.")




app = FastAPI(
    title="AREOS API",
    description="API for AREOS Local UI",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

@app.middleware("http")
async def _correlation_id_middleware(request: Request, call_next):
    token = _error_id_ctx.set(uuid.uuid4().hex)
    try:
        response = await call_next(request)
        return response
    finally:
        _error_id_ctx.reset(token)

# ── Internal Docs Auth Guard ─────────────────────────────────────────────
# Server-side protection for /docs/internal/ paths. Without this, the
# StaticFiles mount would serve internal engineering documentation to
# anyone who knows the URL — the client-side sessionStorage check in
# docs.js is cosmetic only and trivially bypassed.
_INTERNAL_DOCS_TOKEN = os.environ.get("AREOS_API_TOKEN", "")

_PROTECTED_DOC_PREFIXES = (
    "/docs/internal",
    "/docs/external_legacy",
    "/docs/session_artifacts",
)

def _normalize_doc_path(raw_path: str) -> str:
    """Collapse duplicate slashes, resolve dot segments and lowercase, so variants
    like /docs//internal/x.md cannot dodge the prefix check."""
    import posixpath
    from urllib.parse import unquote
    decoded = unquote(unquote(raw_path)).replace("\\", "/")
    collapsed = re.sub(r"/+", "/", decoded)
    return posixpath.normpath(collapsed).lower()

@app.middleware("http")
async def _guard_internal_docs(request: Request, call_next):
    path = _normalize_doc_path(request.url.path)
    if path.startswith(_PROTECTED_DOC_PREFIXES):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Authorization required for internal documentation"}, status_code=401)
        supplied_token = auth_header.split(" ", 1)[1]
        if not _INTERNAL_DOCS_TOKEN or not hmac.compare_digest(supplied_token, _INTERNAL_DOCS_TOKEN):
            return JSONResponse({"detail": "Invalid or missing API token"}, status_code=401)
    return await call_next(request)

@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4().hex
    logger.error(
        "Unhandled exception", extra={"error_id": error_id, "path": request.url.path}, exc_info=exc
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": ErrorCode.INTERNAL_ERROR,
            "error_id": error_id,
            "detail": "An internal error occurred. Reference error_id when reporting this.",
        },
    )

# ── CORS ─────────────────────────────────────────────────────────────────────
# FIX (Readiness Audit, Minor #2): the previous comment claimed this was
# "restricted to local origins only" as if it were a meaningful production
# security control. It isn't one here: the shipped UI is served same-origin
# (mounted at /ui on this same app), so the browser never needs a CORS grant
# to call this API from it, and this allowlist has no effect on that path.
# Its only real job is letting `python -m http.server`-style local dev UIs
# talk to a locally-running API during development. If a genuinely separate,
# cross-origin frontend is ever stood up against this API, add its real
# origin here (or via an env var) rather than relying on this list.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Outermost user middleware: enforce body size limits before Starlette task groups (DEC-05)


class _PayloadTooLarge(BaseException):
    """Internal sentinel exception to cleanly abort downstream ASGI execution when body exceeds size limit."""
    pass


class BodySizeLimitMiddleware:
    def __init__(self, app, max_size: int = 5_000_000):
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for header, value in scope.get("headers", []):
            if header.lower() == b"content-length":
                try:
                    if int(value) > self.max_size:
                        response = JSONResponse(
                            status_code=413,
                            content={"detail": "Payload too large. Maximum request body is 5 MB."},
                        )
                        await response(scope, receive, send)
                        return
                except ValueError:
                    pass

        total_bytes = 0

        async def custom_receive():
            nonlocal total_bytes
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                total_bytes += len(body)
                if total_bytes > self.max_size:
                    raise _PayloadTooLarge()
            return message

        try:
            await self.app(scope, custom_receive, send)
        except _PayloadTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Payload too large. Maximum request body is 5 MB."},
            )
            await response(scope, receive, send)
            return

# Outermost user middleware: enforce body size limits before Starlette task groups (DEC-05)
app.add_middleware(BodySizeLimitMiddleware)

# ── Security headers ────────────────────────────────────────────────────────
# FIX (Readiness Audit, Blocker 5 / Minor #4): the app previously shipped
# with zero security headers, which meant a stored-XSS injection (see the
# approvals.js fix) had no defense-in-depth backstop at all — no CSP, no
# clickjacking protection, no MIME-sniffing protection. This is a second
# layer on top of the actual XSS fix (escaping the LLM-derived content in
# approvals.js), not a replacement for it.
#
# Known limitation: several UI pages use inline <script> bootstrap blocks
# (no external CDN scripts, but genuinely inline), so script-src still needs
# 'unsafe-inline' for the app to function. That means this CSP does not by
# itself block a future inline-script injection — moving those bootstrap
# blocks into external .js files (with a nonce or hash-based CSP) is a
# recommended follow-up to close that gap fully.
@app.middleware("http")
async def _security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-src *; "  # audited-page preview iframes use sandbox="" (no script/same-origin/forms)
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response

# ── Request body size cap ─────────────────────────────────────────────────────
# FIX (QA-GAP-2): no body limit meant a malicious client could POST a multi-MB
# payload and exhaust server memory before Pydantic saw it. Pydantic's
# max_length on individual fields is application-level only — the ASGI server
# buffers the full body first. 5 MB is generous for any legitimate AREOS
# request (the largest expected payload is sample_content at ~50 000 chars ≈ 200 KB).



# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """MF-10: Live health check — verifies DB is reachable, not just process-alive."""
    try:
        import anyio
        def _check_db():
            from areos.db.connection import get_connection
            db_path = get_db_path()
            conn = get_connection(db_path)
            conn.execute("SELECT 1")
        await anyio.to_thread.run_sync(_check_db)
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="Database unreachable") from e

# ─────────────────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(claims.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(verdicts.router)
app.include_router(reports.router)
# outcomes.router removed — Outcome Logger deprecated (v4.0)
app.include_router(prompts.router)
app.include_router(byok.router)
app.include_router(synthesis.router)
app.include_router(knowledge.router)

_DOCS_DIR = Path(__file__).resolve().parents[1] / "ui" / "docs"
if _DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(_DOCS_DIR), html=True), name="docs")

_UI_DIR = Path(__file__).resolve().parents[1] / "ui"
if _UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
