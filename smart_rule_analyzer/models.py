from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True, order=True)
class DeviceState:
    device: str
    state: str

    @classmethod
    def from_dict(cls, value: Any) -> "DeviceState":
        if not isinstance(value, dict) or set(value) != {"device", "state"}:
            raise ValueError("each device state must contain only device and state")
        device, state = value["device"], value["state"]
        if (not isinstance(device, str) or not device
                or not isinstance(state, str) or not state):
            raise ValueError("device and state must be non-empty strings")
        return cls(device=device, state=state)


@dataclass(frozen=True)
class RuleSpec:
    id: str
    description: str
    triggers: Tuple[DeviceState, ...]
    conditions: Tuple[DeviceState, ...]
    actions: Tuple[DeviceState, ...]

    @classmethod
    def from_dict(cls, value: Any) -> "RuleSpec":
        required = {"id", "description", "triggers", "conditions", "actions"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("RuleSpec v0 requires exactly: " + ", ".join(sorted(required)))
        if not isinstance(value["id"], str) or not value["id"]:
            raise ValueError("rule id must be a non-empty string")
        if not isinstance(value["description"], str) or not value["description"]:
            raise ValueError("description must be a non-empty string")
        return cls(
            id=value["id"],
            description=value["description"],
            triggers=_states(value["triggers"], "triggers", required=True),
            conditions=_states(value["conditions"], "conditions"),
            actions=_states(value["actions"], "actions", required=True),
        )


def _states(values: Any, field: str,
            required: bool = False) -> Tuple[DeviceState, ...]:
    if not isinstance(values, list):
        raise ValueError(field + " must be an array")
    if required and not values:
        raise ValueError(field + " must not be empty")
    return tuple(DeviceState.from_dict(item) for item in values)
