from itertools import combinations
from typing import Dict, Iterable, List, Set

from .models import RuleSpec


def analyze_rules(rules: Iterable[RuleSpec]) -> Dict[str, object]:
    """Analyze write conflicts and ordered dependency edges.

    A conflict is a pair of rules that writes different states to the same
    device. A dependency follows the historical analyzer semantics: an earlier
    rule shares an action device with a later rule's action or trigger device.
    Input order is therefore meaningful and is retained in the DAG direction.
    """
    ordered = list(rules)
    if len({rule.id for rule in ordered}) != len(ordered):
        raise ValueError("rule ids must be unique")

    conflicts: List[Dict[str, object]] = []
    for left, right in combinations(ordered, 2):
        left_states = _action_states(left)
        right_states = _action_states(right)
        devices = sorted(device for device in left_states.keys() & right_states.keys()
                         if left_states[device] != right_states[device])
        if devices:
            conflicts.append({"devices": devices, "left": left.id, "right": right.id})

    dependencies: List[Dict[str, object]] = []
    for index, source in enumerate(ordered):
        source_actions = {action.device for action in source.actions}
        for target in ordered[index + 1:]:
            target_inputs = {item.device for item in target.triggers}
            target_inputs.update(action.device for action in target.actions)
            devices = sorted(source_actions & target_inputs)
            if devices:
                dependencies.append({"devices": devices, "source": source.id, "target": target.id})

    return {"conflicts": conflicts, "dependencies": dependencies, "rule_count": len(ordered)}


def _action_states(rule: RuleSpec) -> Dict[str, Set[str]]:
    result: Dict[str, Set[str]] = {}
    for action in rule.actions:
        result.setdefault(action.device, set()).add(action.state)
    return result
