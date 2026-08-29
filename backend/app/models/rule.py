"""
models/rule.py
--------------
Pydantic schemas for compliance_rules table.

Design notes:
  - RuleConditionConfig is a recursive tree — engine walks it, not DB.
  - ComplianceRuleDB  = what comes OUT of Supabase (has id, timestamps)
  - ComplianceRuleCreate = what goes IN (admin API payload)
  - ComplianceRuleUpdate = partial update (all optional)
  - ActiveRuleView = lightweight read model for engine consumption
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Literal, Union
from datetime import date, datetime
from enum import Enum
import uuid


# ── Enums (validated at app layer — DB stores raw TEXT) ──────

class RuleCategory(str, Enum):
    ITC             = "itc"
    INVOICING       = "invoicing"
    GSTIN           = "gstin"
    RECONCILIATION  = "reconciliation"
    HSN             = "hsn"
    FILING          = "filing"
    FRAUD           = "fraud"
    CLASSIFICATION  = "classification"
    TAX_COMPUTATION = "tax_computation"
    SECTOR          = "sector"


class RuleSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class ConditionOperator(str, Enum):
    EQUALS      = "equals"
    NOT_EQUALS  = "not_equals"
    GT          = "gt"
    GTE         = "gte"
    LT          = "lt"
    LTE         = "lte"
    IN          = "in"
    NOT_IN      = "not_in"
    EXISTS      = "exists"
    NOT_EXISTS  = "not_exists"
    REGEX       = "regex"
    LENGTH_EQ   = "length_eq"
    LENGTH_NE   = "length_ne"
    CONTAINS    = "contains"


class PenaltyFormulaType(str, Enum):
    FIXED_AMOUNT             = "fixed_amount"
    PERCENTAGE_OF_AMOUNT     = "percentage_of_amount"
    TAX_PLUS_INTEREST        = "tax_plus_interest_percent"
    LATE_FEE_PER_DAY         = "late_fee_per_day"
    NO_PENALTY               = "no_penalty"
    CUSTOM_EXPOSURE_NOTE     = "custom_exposure_note"


# ── Condition Tree ────────────────────────────────────────────

class LeafCondition(BaseModel):
    """Single field comparison condition."""
    field:    str
    operator: ConditionOperator
    value:    Optional[Any] = None
    # value not required for EXISTS / NOT_EXISTS operators


class CompositeCondition(BaseModel):
    """
    Composite condition: all / any / not.
    Recursive — conditions can nest arbitrarily.
    Engine walks this tree depth-first.
    """
    type:       Literal["all", "any", "not"]
    conditions: List["ConditionNode"] = Field(default_factory=list)


class AlwaysFlagCondition(BaseModel):
    """No evaluation — always flags. Used for external detectors."""
    type: Literal["always_flag"] = "always_flag"


# Union type — discriminated by 'type' field where possible
ConditionNode = Union[CompositeCondition, AlwaysFlagCondition, LeafCondition]

# Pydantic v2 forward ref resolution
CompositeCondition.model_rebuild()


# ── Penalty Formula Configs ───────────────────────────────────

class FixedAmountConfig(BaseModel):
    amount:   float
    currency: str = "INR"


class PercentageConfig(BaseModel):
    rate: float               # 0.18 = 18%
    cap:  Optional[float] = None   # Max penalty in INR
    min_amount: Optional[float] = None


class TaxPlusInterestConfig(BaseModel):
    tax_rate:              float   # 0.18
    interest_rate:         float   # 0.18
    interest_period_days:  int     = 365


class LateFeeConfig(BaseModel):
    amount_per_day: float
    max_days:       int = 180


class CustomNoteConfig(BaseModel):
    note: str


# ── Core Rule Schemas ─────────────────────────────────────────

class ComplianceRuleBase(BaseModel):
    """Shared fields between Create and DB model."""
    rule_code:              str
    title:                  str
    description:            str
    category:               RuleCategory
    severity:               RuleSeverity               = RuleSeverity.MEDIUM
    condition_type:         str                        = "all"
    condition_config:       dict                       = Field(default_factory=dict)
    law_code:               Optional[str]              = None
    plain_explanation:      Optional[str]              = None
    penalty_formula_type:   PenaltyFormulaType         = PenaltyFormulaType.NO_PENALTY
    penalty_formula_config: dict                       = Field(default_factory=dict)
    notice_risk_weight:     float                      = Field(default=0.0, ge=0.0, le=35.0)
    notice_risk_max:        float                      = Field(default=10.0, ge=0.0, le=35.0)
    is_active:              bool                       = True
    version:                int                        = 1
    effective_from:         Optional[date]             = None
    effective_to:           Optional[date]             = None

    @field_validator("rule_code")
    @classmethod
    def rule_code_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("rule_code cannot be empty")
        return v

    @field_validator("notice_risk_max")
    @classmethod
    def max_gte_weight(cls, v: float, info: Any) -> float:
        weight = info.data.get("notice_risk_weight", 0.0)
        if v < weight:
            raise ValueError("notice_risk_max must be >= notice_risk_weight")
        return v


class ComplianceRuleCreate(ComplianceRuleBase):
    """Payload for POST /admin/rules."""
    created_by: Optional[str] = None   # clerk_id of creator


class ComplianceRuleUpdate(BaseModel):
    """
    Partial update payload for PATCH /admin/rules/{id}.
    All fields optional — only provided fields are updated.
    """
    title:                  Optional[str]              = None
    description:            Optional[str]              = None
    severity:               Optional[RuleSeverity]     = None
    condition_type:         Optional[str]              = None
    condition_config:       Optional[dict]             = None
    law_code:               Optional[str]              = None
    plain_explanation:      Optional[str]              = None
    penalty_formula_type:   Optional[PenaltyFormulaType] = None
    penalty_formula_config: Optional[dict]             = None
    notice_risk_weight:     Optional[float]            = Field(default=None, ge=0.0, le=35.0)
    notice_risk_max:        Optional[float]            = Field(default=None, ge=0.0, le=35.0)
    is_active:              Optional[bool]             = None
    effective_from:         Optional[date]             = None
    effective_to:           Optional[date]             = None


class ComplianceRuleDB(ComplianceRuleBase):
    """
    Full DB row — what repositories return.
    Includes DB-generated fields.
    """
    id:         uuid.UUID
    created_by: Optional[str]     = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActiveRuleView(BaseModel):
    """
    Lightweight rule for engine consumption.
    Only fields the evaluator and risk scorer need.
    Avoids passing full DB rows into hot-path evaluation loops.
    """
    rule_code:              str
    category:               str
    severity:               str
    condition_type:         str
    condition_config:       dict
    penalty_formula_type:   str
    penalty_formula_config: dict
    notice_risk_weight:     float
    notice_risk_max:        float
    law_code:               Optional[str] = None
    plain_explanation:      Optional[str] = None

    @classmethod
    def from_db(cls, row: ComplianceRuleDB) -> "ActiveRuleView":
        return cls(
            rule_code              = row.rule_code,
            category               = row.category.value if hasattr(row.category, "value") else row.category,
            severity               = row.severity.value if hasattr(row.severity, "value") else row.severity,
            condition_type         = row.condition_type,
            condition_config       = row.condition_config,
            penalty_formula_type   = row.penalty_formula_type.value if hasattr(row.penalty_formula_type, "value") else row.penalty_formula_type,
            penalty_formula_config = row.penalty_formula_config,
            notice_risk_weight     = row.notice_risk_weight,
            notice_risk_max        = row.notice_risk_max,
            law_code               = row.law_code,
            plain_explanation      = row.plain_explanation,
        )