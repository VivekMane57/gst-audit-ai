"""
models/client.py
----------------
Client ka Pydantic model.
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class Client(BaseModel):
    """Single client record."""
    id:              Optional[str] = None
    ca_id:           str
    business_name:   str
    gstin_masked:    Optional[str] = None
    gstin_encrypted: Optional[str] = None
    sector:          Optional[str] = None
    contact_person:  Optional[str] = None
    phone:           Optional[str] = None
    email:           Optional[str] = None
    address:         Optional[str] = None
    created_at:      Optional[datetime] = None

    @field_validator("business_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class AddClientRequest(BaseModel):
    """POST /clients request body."""
    business_name:  str
    gstin:          str
    sector:         Optional[str] = None
    contact_person: Optional[str] = None
    phone:          Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None


class UpdateClientRequest(BaseModel):
    """PUT /clients/{id} request body."""
    business_name:  Optional[str] = None
    gstin:          Optional[str] = None
    sector:         Optional[str] = None
    contact_person: Optional[str] = None
    phone:          Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None


class ClientResponse(BaseModel):
    """Client data returned to frontend."""
    id:             str
    business_name:  str
    gstin_masked:   Optional[str] = None
    sector:         Optional[str] = None
    contact_person: Optional[str] = None
    phone:          Optional[str] = None
    email:          Optional[str] = None
    address:        Optional[str] = None
    created_at:     Optional[datetime] = None
    last_score:     Optional[int] = None
    last_audit_at:  Optional[datetime] = None