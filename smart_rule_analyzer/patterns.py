"""Finite execution-pattern classification over sanitized rule journal records."""

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class ExecutionRecord:
    rule_id: str
    trigger_rule_id: str
    status: str
    actions: Tuple[Tuple[str, str], ...]
    conditions: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self):
        if self.status not in {"run", "skipped"}:
            raise ValueError("status must be run or skipped")
        if not self.rule_id:
            raise ValueError("rule_id is required")


@dataclass(frozen=True, order=True)
class PatternFinding:
    kind: str
    left_rule_id: str
    right_rule_id: str
    resource: str


def classify_execution_patterns(records: Iterable[ExecutionRecord]) -> List[PatternFinding]:
    ordered = list(records)
    findings = set()
    for left, right in combinations(ordered, 2):
        left_actions = dict(left.actions)
        right_actions = dict(right.actions)
        for resource in sorted(left_actions.keys() & right_actions.keys()):
            same_state = left_actions[resource] == right_actions[resource]
            same_chain = left.trigger_rule_id == right.trigger_rule_id
            if same_state:
                findings.add(PatternFinding("action-repetition", left.rule_id, right.rule_id, resource))
                if right.trigger_rule_id == left.rule_id:
                    findings.add(PatternFinding("action-loop", left.rule_id, right.rule_id, resource))
            elif same_chain:
                findings.add(PatternFinding("action-conflict", left.rule_id, right.rule_id, resource))
                findings.add(PatternFinding("action-revert", left.rule_id, right.rule_id, resource))
            else:
                findings.add(PatternFinding("unexpected-conflict", left.rule_id, right.rule_id, resource))

        left_conditions = dict(left.conditions)
        right_conditions = dict(right.conditions)
        for resource in sorted(left_conditions.keys() & right_conditions.keys()):
            if left_conditions[resource] != right_conditions[resource]:
                findings.add(PatternFinding("condition-contradictory", left.rule_id, right.rule_id, resource))

        if right.status == "skipped":
            for resource in sorted(set(left_actions) & set(dict(right.conditions))):
                findings.add(PatternFinding("condition-block", left.rule_id, right.rule_id, resource))
            for resource in sorted(left_actions.keys() & right_actions.keys()):
                if left_actions[resource] == right_actions[resource]:
                    findings.add(PatternFinding("condition-bypass", left.rule_id, right.rule_id, resource))
        elif right.status == "run":
            right_conditions = dict(right.conditions)
            for resource in sorted(set(left_actions) & set(right_conditions)):
                if left_actions[resource] == right_conditions[resource]:
                    findings.add(PatternFinding("condition-pass", left.rule_id, right.rule_id, resource))
    return sorted(findings)
