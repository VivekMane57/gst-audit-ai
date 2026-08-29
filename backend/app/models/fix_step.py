"""
models/fix_step.py
-------------------
Pydantic schemas for rule_fix_steps table.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class RuleFixStepBase(BaseModel):
    rule_code:    str
    step_order:   int
    step_text_en: str
    step_text_hi: Optional[str] = None
    step_text_mr: Optional[str] = None


class RuleFixStepCreate(RuleFixStepBase):
    pass


class RuleFixStepUpdate(BaseModel):
    step_order:   Optional[int] = None
    step_text_en: Optional[str] = None
    step_text_hi: Optional[str] = None
    step_text_mr: Optional[str] = None


class RuleFixStepDB(RuleFixStepBase):
    id:         str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RuleFixStepsBundle(BaseModel):
    """
    Engine-ready bundle — all languages for a rule's fix steps.
    hi/mr fall back to en if not translated.
    """
    rule_code: str
    en:        list[str] = []
    hi:        list[str] = []
    mr:        list[str] = []

    def for_lang(self, lang: str) -> list[str]:
        """Return steps for given language, fallback to English."""
        return getattr(self, lang, self.en) or self.en