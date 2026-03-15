"""
main.py — FastAPI entry point
Run: uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.config import get_settings
from app.routers import health
from app.routers import audit   as audit_router
from app.routers import clients as clients_router
from app.routers import reports as reports_router

try:
    import sentry_sdk
    _sentry_available = True
except ImportError:
    _sentry_available = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if _sentry_available and getattr(settings, "sentry_dsn", None):
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    logger.info(f"Starting GST Audit AI v1.0.0 | debug={settings.debug}")
    from fastapi.routing import APIRoute
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"  Route: {list(route.methods)} {route.path}")
    yield
    logger.info("Shutting down GST Audit AI")


settings = get_settings()

app = FastAPI(
    title       = "GST Audit AI",
    version     = "1.0.0",
    description = "AI-powered GST Audit Engine for Indian CAs",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    openapi_url = "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.allowed_origins,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "PUT", "DELETE"],
    allow_headers     = ["Authorization", "Content-Type", "X-Clerk-Id", "x-clerk-id"],
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    ms       = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(ms)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} [{ms}ms]")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong. Please retry."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
# Your routers already have full paths inside them:
#   audit.py   → @router.post("/audit"),    @router.get("/audit/{id}")
#   clients.py → @router.get("/clients"),   @router.post("/clients") etc.
#   reports.py → @router.get("/reports"),   @router.get("/reports/{id}/pdf")
#
# So prefix="" here — routers own their full paths.
app.include_router(health.router,                         tags=["Health"])
app.include_router(audit_router.router,   prefix="",      tags=["Audit"])
app.include_router(clients_router.router, prefix="",      tags=["Clients"])
app.include_router(reports_router.router, prefix="",      tags=["Reports"])