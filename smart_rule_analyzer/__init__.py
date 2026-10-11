"""Deterministic rule-conflict and dependency analysis."""

from .analyzer import analyze_rules
from .models import RuleSpec

__all__ = ["RuleSpec", "analyze_rules"]
