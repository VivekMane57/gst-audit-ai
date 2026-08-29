"""
models/threshold.py
--------------------
Pydantic schemas for risk_thresholds table.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class RiskThresholdBase(BaseModel):
    profile_name: str
    low_max:      float = 30.0
    medium_max:   float = 60.0
    high_max:     float = 85.0
    critical_min: float = 85.0
    is_default:   bool  = False

    def validate_bands(self) -> None:
        if not (self.low_max < self.medium_max < self.high_max):
            raise ValueError(
                f"Band thresholds must be ascending: "
                f"low_max({self.low_max}) < medium_max({self.medium_max}) < high_max({self.high_max})"
            )
        if self.critical_min != self.high_max:
            raise ValueError(
                f"critical_min({self.critical_min}) must equal high_max({self.high_max})"
            )


class RiskThresholdCreate(RiskThresholdBase):
    pass


class RiskThresholdUpdate(BaseModel):
    profile_name: Optional[str]   = None
    low_max:      Optional[float] = None
    medium_max:   Optional[float] = None
    high_max:     Optional[float] = None
    critical_min: Optional[float] = None
    is_default:   Optional[bool]  = None


class RiskThresholdDB(RiskThresholdBase):
    id:         str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Hardcoded fallback — used by ThresholdRepository.get_default()
# when DB is unavailable. Matches migration seed values.
DEFAULT_THRESHOLD_FALLBACK = RiskThresholdCreate(
    profile_name = "default",
    low_max      = 30.0,
    medium_max   = 60.0,
    high_max     = 85.0,
    critical_min = 85.0,
    is_default   = True,
)