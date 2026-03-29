"""
core/dependencies.py
---------------------
Dependency Injection container.
FastAPI ke Depends() ke saath use karo.

Pattern:
    @router.post("")
    async def run_audit(deps: AuditDeps = Depends(get_audit_deps)):
        deps.audit_repo.insert(...)
        deps.client_repo.get_name(...)

Iska faida:
- Thread-safe: har request ka apna object
- Testable: mock karke unit test karo
- Supabase singleton nahi — connection fresh per-request
"""
from __future__ import annotations
from dataclasses import dataclass
from fastapi import Header, HTTPException
from typing import Optional

from app.db.supabase_client import get_supabase
from app.utils.auth import get_user_uuid
from app.repositories.audit_repo import AuditRepository
from app.repositories.client_repo import ClientRepository


@dataclass
class AuditDeps:
    """All dependencies for audit operations."""
    audit_repo:  AuditRepository
    client_repo: ClientRepository
    user_uuid:   str
    ca_id:       str
    ca_email:    Optional[str]
    ca_name:     str


@dataclass
class ClientDeps:
    """All dependencies for client operations."""
    client_repo: ClientRepository
    ca_id:       str


@dataclass
class ReportDeps:
    """All dependencies for report operations."""
    audit_repo:  AuditRepository
    ca_id:       str


# ── Dependency providers ──────────────────────────────────────

def get_audit_deps(
    x_user_id:    Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None),
    x_user_name:  Optional[str] = Header(default=None),
) -> AuditDeps:
    """
    FastAPI Depends provider for audit routes.
    Per-request — thread safe.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db          = get_supabase()
    user_uuid   = get_user_uuid(db, x_user_id, email=x_user_email, full_name=x_user_name)
    audit_repo  = AuditRepository(db)
    client_repo = ClientRepository(db)

    # Email validation — placeholder nahi
    ca_email = _clean_email(x_user_email)
    if not ca_email:
        # DB fallback
        try:
            res = db.table("users").select("email, full_name").eq("clerk_id", x_user_id).limit(1).execute()
            if res.data:
                ca_email = _clean_email(res.data[0].get("email"))
                x_user_name = x_user_name or res.data[0].get("full_name") or "CA"
        except Exception:
            pass

    return AuditDeps(
        audit_repo  = audit_repo,
        client_repo = client_repo,
        user_uuid   = user_uuid,
        ca_id       = x_user_id,
        ca_email    = ca_email,
        ca_name     = x_user_name or "CA",
    )


def get_client_deps(
    x_user_id:    Optional[str] = Header(default=None),
    x_user_email: Optional[str] = Header(default=None),
    x_user_name:  Optional[str] = Header(default=None),
) -> ClientDeps:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = get_supabase()
    get_user_uuid(db, x_user_id, email=x_user_email, full_name=x_user_name)
    return ClientDeps(
        client_repo = ClientRepository(db),
        ca_id       = x_user_id,
    )


def get_report_deps(
    x_user_id: Optional[str] = Header(default=None),
) -> ReportDeps:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = get_supabase()
    get_user_uuid(db, x_user_id)
    return ReportDeps(
        audit_repo = AuditRepository(db),
        ca_id      = x_user_id,
    )


# ── Helper ───────────────────────────────────────────────────
def _clean_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip()
    if "@placeholder" in email or "auditai.app" in email or "@" not in email:
        return None
    return email