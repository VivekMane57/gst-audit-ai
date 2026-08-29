"""
models/law.py
-------------
LawCatalog Pydantic schemas.
"""
from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime
import uuid


class LawCatalogBase(BaseModel):
    law_code:            str
    act_name:            str
    section:             str
    short_text:          str
    official_source_url: Optional[str] = None
    reviewed_on:         Optional[date] = None
    is_active:           bool           = True

    @field_validator("law_code")
    @classmethod
    def normalize_law_code(cls, v: str) -> str:
        return v.strip().upper()


class LawCatalogCreate(LawCatalogBase):
    pass


class LawCatalogUpdate(BaseModel):
    act_name:            Optional[str]  = None
    section:             Optional[str]  = None
    short_text:          Optional[str]  = None
    official_source_url: Optional[str]  = None
    reviewed_on:         Optional[date] = None
    is_active:           Optional[bool] = None


class LawCatalogDB(LawCatalogBase):
    id:         uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


"""
models/fix_step.py
------------------
RuleFixStep Pydantic schemas.
"""

class RuleFixStepBase(BaseModel):
    rule_code:    str
    step_order:   int
    step_text_en: str
    step_text_hi: str = ""
    step_text_mr: str = ""


class RuleFixStepCreate(RuleFixStepBase):
    pass


class RuleFixStepUpdate(BaseModel):
    step_order:   Optional[int]  = None
    step_text_en: Optional[str]  = None
    step_text_hi: Optional[str]  = None
    step_text_mr: Optional[str]  = None


class RuleFixStepDB(RuleFixStepBase):
    id:         uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RuleFixStepsBundle(BaseModel):
    """All fix steps for a rule, language-keyed."""
    rule_code: str
    en: list[str] = []
    hi: list[str] = []
    mr: list[str] = []

    def get(self, lang: str) -> list[str]:
        if lang == "hi": return self.hi or self.en
        if lang == "mr": return self.mr or self.en
        return self.en


"""
models/threshold.py
-------------------
RiskThreshold Pydantic schemas.
"""

class RiskThresholdBase(BaseModel):
    profile_name: str
    low_max:      int = 24
    medium_max:   int = 44
    high_max:     int = 69
    critical_min: int = 70
    is_default:   bool = False

    def validate_bands(self) -> None:
        """Call after init to assert band ordering invariant."""
        if not (0 <= self.low_max < self.medium_max < self.high_max < self.critical_min <= 100):
            raise ValueError(
                f"Threshold bands must satisfy: 0 <= low_max < medium_max < high_max < critical_min <= 100. "
                f"Got: {self.low_max}/{self.medium_max}/{self.high_max}/{self.critical_min}"
            )

    def classify(self, probability: int) -> str:
        """Map probability integer to risk label."""
        if probability <= self.low_max:    return "LOW"
        if probability <= self.medium_max: return "MEDIUM"
        if probability <= self.high_max:   return "HIGH"
        return "VERY_HIGH"


class RiskThresholdCreate(RiskThresholdBase):
    pass


class RiskThresholdUpdate(BaseModel):
    low_max:      Optional[int]  = None
    medium_max:   Optional[int]  = None
    high_max:     Optional[int]  = None
    critical_min: Optional[int]  = None
    is_default:   Optional[bool] = None


class RiskThresholdDB(RiskThresholdBase):
    id:         uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Hardcoded fallback — used when DB is unavailable or not yet seeded
DEFAULT_THRESHOLD_FALLBACK = RiskThresholdBase(
    profile_name = "hardcoded_fallback",
    low_max      = 24,
    medium_max   = 44,
    high_max     = 69,
    critical_min = 70,
    is_default   = True,
)