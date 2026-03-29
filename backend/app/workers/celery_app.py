"""
workers/celery_app.py
---------------------
Celery + Redis — Production v2.0
"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

REDIS_URL = getattr(settings, "redis_url", "redis://localhost:6379/0")

celery_app = Celery(
    "auditai",
    broker  = REDIS_URL,
    backend = REDIS_URL,
)

celery_app.conf.update(
    # ── Serialization ─────────────────────────────────────────
    task_serializer   = "json",
    result_serializer = "json",
    accept_content    = ["json"],

    # ── Timezone ──────────────────────────────────────────────
    timezone          = "Asia/Kolkata",
    enable_utc        = True,

    # ── Task limits ───────────────────────────────────────────
    task_soft_time_limit = 120,
    task_time_limit      = 180,

    # ── Reliability ───────────────────────────────────────────
    task_acks_late             = True,
    worker_prefetch_multiplier = 1,

    # ── Memory management ─────────────────────────────────────
    result_expires             = 3600,
    worker_max_tasks_per_child = 100,

    # ── Retry defaults ────────────────────────────────────────
    task_max_retries         = 2,
    task_default_retry_delay = 30,

    # ── Startup retry fix (Celery 6.0 warning band) ───────────
    broker_connection_retry_on_startup = True,
)

# Auto-discover + explicit import — task registration ensure karta hai
celery_app.autodiscover_tasks(["app.workers"])

# Explicit import — "-I flag" ki zaroorat nahi hogi ab
import app.workers.audit_tasks  # noqa: E402, F401