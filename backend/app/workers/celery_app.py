"""
workers/celery_app.py
---------------------
Celery + Redis — Production v2.1
Changes: Added Celery Beat schedule for monthly notice recheck
"""
from celery import Celery
from celery.schedules import crontab
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

    # ── Startup retry fix ─────────────────────────────────────
    broker_connection_retry_on_startup = True,

    # ── Beat Schedule — Monthly recheck ───────────────────────
    # Runs on 1st of every month at 6:00 AM IST (00:30 UTC)
    beat_schedule = {
        "monthly-notice-recheck": {
            "task":     "recheck.monthly_notice_risk",
            "schedule": crontab(
                hour         = 0,
                minute       = 30,
                day_of_month = "1",
            ),
            "options": {"expires": 3600},   # expire if not picked up in 1hr
        },
    },
)

# Auto-discover + explicit imports
celery_app.autodiscover_tasks(["app.workers"])

import app.workers.audit_tasks       # noqa: E402, F401
import app.workers.recheck_scheduler  # noqa: E402, F401  ← Added