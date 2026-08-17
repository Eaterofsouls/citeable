import logging
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
from areos.api.routers import claims, approvals, audit, verdicts, reports, outcomes, prompts, byok, synthesis

logger = logging.getLogger(__name__)
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all required tables exist on startup. Raises on failure (MF-9).
    migrate(get_db_path())
    logger.info("AREOS API started. DB migrations applied.")
    yield
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
@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 5_000_000:  # 5 MB
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large. Maximum request body is 5 MB."},
        )
    return await call_next(request)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    """MF-10: Live health check — verifies DB is reachable, not just process-alive."""
    try:
        from areos.db.connection import get_connection
        db_path = get_db_path()
        conn = get_connection(db_path)
        conn.execute("SELECT 1")
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
app.include_router(outcomes.router)
app.include_router(prompts.router)
app.include_router(byok.router)
app.include_router(synthesis.router)

_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
if _DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(_DOCS_DIR), html=True), name="docs")

_UI_DIR = Path(__file__).resolve().parents[1] / "ui"
if _UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
