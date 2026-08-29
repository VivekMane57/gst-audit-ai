"""
services/rule_engine_service.py
--------------------------------
Generic condition tree evaluator.

WHAT IS HARDCODED HERE (intentional):
  - operator handler functions
  - tree walking logic (all/any/not)
  - field resolution from invoice record

WHAT COMES FROM DB (via ActiveRuleView):
  - which fields to check
  - which operators to apply
  - what values to compare against
  - which categories/severities rules belong to

Usage:
    engine = RuleEngineService(rule_repo, fix_step_repo)
    matched = engine.evaluate_invoice(invoice_dict)
    # Returns list of MatchedRule — one per matched rule
"""
from __future__ import annotations
import logging
import re
from typing import Any, Optional

from app.repositories.rule_repository import RuleRepository
from app.repositories.fix_step_repository import FixStepRepository
from app.models.rule import ActiveRuleView

logger = logging.getLogger(__name__)


# ── Operator handlers (hardcoded — engine code, not rule content) ──

def _op_equals(field_val: Any, compare_val: Any) -> bool:
    if isinstance(field_val, str) and isinstance(compare_val, str):
        return field_val.strip().lower() == compare_val.strip().lower()
    return field_val == compare_val

def _op_not_equals(field_val: Any, compare_val: Any) -> bool:
    return not _op_equals(field_val, compare_val)

def _op_gt(field_val: Any, compare_val: Any) -> bool:
    try: return float(field_val) > float(compare_val)
    except (TypeError, ValueError): return False

def _op_gte(field_val: Any, compare_val: Any) -> bool:
    try: return float(field_val) >= float(compare_val)
    except (TypeError, ValueError): return False

def _op_lt(field_val: Any, compare_val: Any) -> bool:
    try: return float(field_val) < float(compare_val)
    except (TypeError, ValueError): return False

def _op_lte(field_val: Any, compare_val: Any) -> bool:
    try: return float(field_val) <= float(compare_val)
    except (TypeError, ValueError): return False

def _op_in(field_val: Any, compare_val: Any) -> bool:
    if not isinstance(compare_val, list): return False
    return field_val in compare_val

def _op_not_in(field_val: Any, compare_val: Any) -> bool:
    return not _op_in(field_val, compare_val)

def _op_exists(field_val: Any, _: Any) -> bool:
    return field_val is not None and field_val != "" and field_val is not False

def _op_not_exists(field_val: Any, _: Any) -> bool:
    return not _op_exists(field_val, _)

def _op_regex(field_val: Any, pattern: Any) -> bool:
    if not isinstance(field_val, str) or not isinstance(pattern, str): return False
    try: return bool(re.match(pattern, field_val))
    except re.error: return False

def _op_length_eq(field_val: Any, compare_val: Any) -> bool:
    try: return len(str(field_val)) == int(compare_val)
    except (TypeError, ValueError): return False

def _op_length_ne(field_val: Any, compare_val: Any) -> bool:
    return not _op_length_eq(field_val, compare_val)

def _op_contains(field_val: Any, compare_val: Any) -> bool:
    if isinstance(field_val, str) and isinstance(compare_val, str):
        return compare_val.lower() in field_val.lower()
    if isinstance(field_val, list):
        return compare_val in field_val
    return False


OPERATOR_MAP = {
    "equals":       _op_equals,
    "not_equals":   _op_not_equals,
    "gt":           _op_gt,
    "gte":          _op_gte,
    "lt":           _op_lt,
    "lte":          _op_lte,
    "in":           _op_in,
    "not_in":       _op_not_in,
    "exists":       _op_exists,
    "not_exists":   _op_not_exists,
    "regex":        _op_regex,
    "length_eq":    _op_length_eq,
    "length_ne":    _op_length_ne,
    "contains":     _op_contains,
}


# ── Result type ───────────────────────────────────────────────

class MatchedRule:
    """A rule that matched against an invoice/audit record."""
    __slots__ = ("rule", "record_snapshot")

    def __init__(self, rule: ActiveRuleView, record_snapshot: dict):
        self.rule            = rule
        self.record_snapshot = record_snapshot  # for audit trail

    def to_dict(self) -> dict:
        return {
            "rule_code":    self.rule.rule_code,
            "category":     self.rule.category,
            "severity":     self.rule.severity,
            "law_code":     self.rule.law_code,
            "risk_weight":  self.rule.notice_risk_weight,
            "risk_max":     self.rule.notice_risk_max,
        }


# ── Core evaluator ────────────────────────────────────────────

class RuleEngineService:
    """
    Stateless (after init) rule evaluator.
    Rules loaded once per audit run — not per invoice.
    Condition tree walker is recursive but bounded by tree depth.
    """

    def __init__(
        self,
        rule_repo:      RuleRepository,
        fix_step_repo:  Optional[FixStepRepository] = None,
    ):
        self._rule_repo     = rule_repo
        self._fix_step_repo = fix_step_repo

    def evaluate_batch(
        self,
        records:    list[dict],
        category:   Optional[str] = None,
    ) -> list[MatchedRule]:
        """
        Evaluate a batch of invoice/audit records against all active rules.
        Returns flat list of all matches across all records.

        Rules are loaded ONCE for the batch — not per record.
        """
        active_rules = self._rule_repo.get_active_rules(category=category)
        if not active_rules:
            logger.debug("No active DB rules found — engine returns empty")
            return []

        matched: list[MatchedRule] = []
        for record in records:
            for rule in active_rules:
                try:
                    if self._matches(rule, record):
                        matched.append(MatchedRule(rule, record))
                except Exception as e:
                    logger.warning(
                        f"Rule eval error rule_code={rule.rule_code} "
                        f"invoice={record.get('invoice_number', '?')}: {e}"
                    )
        return matched

    def evaluate_single(
        self,
        record:   dict,
        category: Optional[str] = None,
    ) -> list[MatchedRule]:
        """Evaluate a single record. Loads rules from DB."""
        return self.evaluate_batch([record], category=category)

    # ── Internal: condition tree walker ──────────────────────

    def _matches(self, rule: ActiveRuleView, record: dict) -> bool:
        """Entry point for rule condition evaluation."""
        condition_type   = rule.condition_type
        condition_config = rule.condition_config

        if condition_type == "always_flag":
            return True

        if condition_type in ("all", "any", "not"):
            return self._eval_node(
                {"type": condition_type, "conditions": condition_config.get("conditions", [])},
                record
            )

        # Treat root config as a leaf if it has 'field' key
        if "field" in condition_config:
            return self._eval_leaf(condition_config, record)

        logger.warning(f"Unknown condition_type={condition_type!r} for rule={rule.rule_code}")
        return False

    def _eval_node(self, node: dict, record: dict) -> bool:
        """
        Recursively evaluate a condition node.
        node types: all | any | not | leaf (has 'field' key)
        """
        node_type = node.get("type")

        if node_type == "all":
            conditions = node.get("conditions", [])
            if not conditions:
                return False   # Empty 'all' = no match (conservative)
            return all(self._eval_node(c, record) for c in conditions)

        if node_type == "any":
            conditions = node.get("conditions", [])
            if not conditions:
                return False
            return any(self._eval_node(c, record) for c in conditions)

        if node_type == "not":
            conditions = node.get("conditions", [])
            if not conditions:
                return False
            return not self._eval_node(conditions[0], record)

        if node_type == "always_flag":
            return True

        # Leaf node — has 'field' + 'operator'
        if "field" in node:
            return self._eval_leaf(node, record)

        logger.warning(f"Unrecognized condition node: {node}")
        return False

    def _eval_leaf(self, node: dict, record: dict) -> bool:
        """Evaluate a single field condition."""
        field    = node.get("field")
        operator = node.get("operator")
        value    = node.get("value")

        if not field or not operator:
            logger.warning(f"Leaf condition missing field/operator: {node}")
            return False

        field_val = self._resolve_field(field, record)
        handler   = OPERATOR_MAP.get(operator)

        if handler is None:
            logger.warning(f"Unknown operator: {operator!r}")
            return False

        return handler(field_val, value)

    def _resolve_field(self, field: str, record: dict) -> Any:
        """
        Resolve dot-notation field path from record dict.
        e.g. "supplier.gstin" → record["supplier"]["gstin"]
        Returns None if path not found — operators handle None gracefully.
        """
        parts = field.split(".")
        val   = record
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return None
        return val