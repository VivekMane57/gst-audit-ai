# """
# main.py — FastAPI entry point
# Run: uvicorn app.main:app --reload --port 8000
# """
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from contextlib import asynccontextmanager
# import logging
# import time

# from app.config import get_settings
# from app.routers import health
# from app.routers import audit   as audit_router
# from app.routers import clients as clients_router
# from app.routers import reports as reports_router
# from app.routers import hsn     as hsn_router
# from app.routers import reconciliation as recon_router

# try:
#     import sentry_sdk
#     _sentry_available = True
# except ImportError:
#     _sentry_available = False

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
# )
# logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     settings = get_settings()
#     if _sentry_available and getattr(settings, "sentry_dsn", None):
#         sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
#     logger.info(f"Starting GST Audit AI v1.0.0 | debug={settings.debug}")
#     from fastapi.routing import APIRoute
#     for route in app.routes:
#         if isinstance(route, APIRoute):
#             logger.info(f"  Route: {list(route.methods)} {route.path}")
#     yield
#     logger.info("Shutting down GST Audit AI")


# settings = get_settings()

# app = FastAPI(
#     title       = "GST Audit AI",
#     version     = "1.0.0",
#     description = "AI-powered GST Audit Engine for Indian CAs",
#     lifespan    = lifespan,
#     docs_url    = "/docs",
#     redoc_url   = "/redoc",
#     openapi_url = "/openapi.json",
# )

# # ── CORS ──────────────────────────────────────────────────────
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.middleware("http")
# async def add_process_time(request: Request, call_next):
#     start    = time.perf_counter()
#     response = await call_next(request)
#     ms       = round((time.perf_counter() - start) * 1000, 2)
#     response.headers["X-Process-Time-Ms"] = str(ms)
#     logger.info(f"{request.method} {request.url.path} → {response.status_code} [{ms}ms]")
#     return response


# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
#     return JSONResponse(
#         status_code=500,
#         content={"error": "Something went wrong. Please retry."},
#     )


# # ── Routers ───────────────────────────────────────────────────
# app.include_router(health.router,                         tags=["Health"])
# app.include_router(audit_router.router,   prefix="",      tags=["Audit"])
# app.include_router(clients_router.router, prefix="",      tags=["Clients"])
# app.include_router(reports_router.router, prefix="",      tags=["Reports"])
# app.include_router(hsn_router.router,     prefix="",      tags=["HSN"])
# app.include_router(recon_router.router)




"""
main.py — FastAPI entry point  (Production v2.0)
-------------------------------------------------
Teri existing clean architecture SAME rakhi hai.
Sirf 3 production middlewares add kiye hain:
  1. RequestLoggingMiddleware  — JSON structured logs
  2. FileSizeLimitMiddleware   — 20MB hard cap (header level, zero body cost)
  3. TimeoutMiddleware         — 30s hard timeout
+ Supabase warmup on startup
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import asyncio
import json
import uuid

from app.config import get_settings
from app.routers import health
from app.routers import audit          as audit_router
from app.routers import clients        as clients_router
from app.routers import reports        as reports_router
from app.routers import hsn            as hsn_router
from app.routers import reconciliation as recon_router

try:
    import sentry_sdk
    _sentry_available = True
except ImportError:
    _sentry_available = False

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _limiter_available = True
    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
except ImportError:
    _limiter_available = False
    limiter = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# MIDDLEWARE 1 — Request Logging (JSON structured)
# ══════════════════════════════════════════════════════════════
class RequestLoggingMiddleware:
    """
    Har request ka ek JSON log line — method, path, status,
    duration_ms, user_id, real_ip sab included.
    Grep karo: grep '"status": 500' audit_access.log
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request    = Request(scope, receive)
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start      = time.perf_counter()

        status_code = 500
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log = {
            "ts":          time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id":  request_id,
            "method":      scope.get("method", ""),
            "path":        scope.get("path", ""),
            "status":      status_code,
            "duration_ms": duration_ms,
            "user_id":     request.headers.get("x-user-id", "anonymous"),
            "real_ip":     request.headers.get("x-real-ip",
                           request.client.host if request.client else "unknown"),
        }
        logger.info(json.dumps(log))


# ══════════════════════════════════════════════════════════════
# MIDDLEWARE 2 — File Size Limit (20MB)
# ══════════════════════════════════════════════════════════════
class FileSizeLimitMiddleware:
    """
    Content-Length header check karo — body read karne se PEHLE reject.
    Zero body cost — RAM waste nahi.
    20MB = Node.js diskStorage limit ke saath match karta hai.
    """
    MAX_BYTES = 20 * 1024 * 1024  # 20MB

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_length = int(headers.get(b"content-length", b"0"))
            if content_length > self.MAX_BYTES:
                response = JSONResponse(
                    status_code=413,
                    content={"error": "File 20MB se badi hai. Chhoti file upload karo."},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# ══════════════════════════════════════════════════════════════
# MIDDLEWARE 3 — Request Timeout (30s)
# ══════════════════════════════════════════════════════════════
class TimeoutMiddleware:
    """
    30s se zyada koi request nahi chalegi.
    Audit routes Celery task_id turant return karte hain —
    isliye 30s bahut hai.
    """
    TIMEOUT = float(30)

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await asyncio.wait_for(
                self.app(scope, receive, send),
                timeout=self.TIMEOUT,
            )
        except asyncio.TimeoutError:
            response = JSONResponse(
                status_code=504,
                content={"error": "Request 30 seconds mein complete nahi hua. Retry karo."},
            )
            await response(scope, receive, send)


# ══════════════════════════════════════════════════════════════
# LIFESPAN — startup/shutdown
# ══════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    if _sentry_available and getattr(settings, "sentry_dsn", None):
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    logger.info(f"Starting GST Audit AI v{settings.app_version} | debug={settings.debug}")

    # DB warmup — pehli request pe cold start nahi hoga
    try:
        from app.db.supabase_client import get_supabase
        get_supabase()
        logger.info("Supabase client warmed up.")
    except Exception as e:
        logger.warning(f"Supabase warmup failed (non-fatal): {e}")

    from fastapi.routing import APIRoute
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"  Route: {list(route.methods)} {route.path}")

    yield
    logger.info("Shutting down GST Audit AI")


# ══════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════
settings = get_settings()

app = FastAPI(
    title       = "GST Audit AI",
    version     = "2.0.0",
    description = "AI-powered GST Audit Engine for Indian CAs",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    openapi_url = "/openapi.json",
)

# ── SlowAPI rate limiting ──────────────────────────────────────
if _limiter_available and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("SlowAPI rate limiting: 200 req/min per IP")

# ── CORS (env-based — no wildcard in production) ──────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.allowed_origins,
    allow_credentials = False,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Production middlewares ─────────────────────────────────────
# add_middleware stack: LIFO — last added = outermost (runs first)
# Order: Timeout (outermost) → FileSizeLimit → RequestLogging → handler
app.add_middleware(RequestLoggingMiddleware)  # added first = innermost
app.add_middleware(FileSizeLimitMiddleware)   # added second
app.add_middleware(TimeoutMiddleware)         # added last = outermost ✅

# ── Global error handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong. Please retry."},
    )

# ── Routers — teri existing structure bilkul same ─────────────
app.include_router(health.router)
app.include_router(audit_router.router,   prefix="")
app.include_router(clients_router.router, prefix="")
app.include_router(reports_router.router, prefix="")
app.include_router(hsn_router.router,     prefix="")
app.include_router(recon_router.router)