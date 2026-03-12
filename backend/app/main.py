"""
main.py
-------
FastAPI application entry point.
Yahan sirf app setup hota hai — logic routers mein hoti hai.

Run karo:
  uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sentry_sdk
import logging
import time

from app.config import get_settings
from app.routers import health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────
    settings = get_settings()

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment="production" if not settings.debug else "development",
        )
        logger.info("Sentry initialized")

    logger.info(
        f"Starting {settings.app_name} v{settings.app_version} "
        f"| debug={settings.debug}"
    )
    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("Application shutting down")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered GST Audit Engine for Indian CAs",
    lifespan=lifespan,
    # Docs sirf debug mode mein
    docs_url="/docs"   if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration)
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} [{duration}ms]"
    )
    return response


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Kuch problem aa gayi. Please 2 minute baad try karo.",
            "support": "support@gstauditai.com",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])

# Day 2 mein add honge:
# app.include_router(audit.router,   prefix="/audit",   tags=["Audit"])
# app.include_router(clients.router, prefix="/clients", tags=["Clients"])
# app.include_router(reports.router, prefix="/reports", tags=["Reports"])