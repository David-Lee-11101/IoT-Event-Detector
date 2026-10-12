"""Deterministic profiling for payload-free, instrumented RPC frame traces."""

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

MAX_OBSERVATIONS = 4096
MAX_TOTAL_ENCODED_BYTES = 16 * 1024 * 1024
MAX_PROFILES = 256
ALLOWED_SOURCES = {"instrumented-rpc", "synthetic-fixture"}
ALLOWED_DIRECTIONS = {"client-to-server", "server-to-client"}

Feature = Tuple[str, int]
FeatureSequence = Tuple[Feature, ...]


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            .encode("utf-8"))


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) < 3 or len(value) > 128:
        raise ValueError(field + " must be a bounded identifier")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9._:-]{2,127}", value) is None:
        raise ValueError(field + " contains unsupported characters")
    return value


def normalize_trace(trace: Mapping[str, Any]) -> FeatureSequence:
    """Validate a TrafficTrace v1 and return ordered direction/length features."""
    required = {"schemaVersion", "traceId", "modelInputVersion", "sourceKind", "observations"}
    if not isinstance(trace, Mapping) or set(trace) != required:
        raise ValueError("TrafficTrace has unsupported or missing fields")
    if not isinstance(trace["schemaVersion"], str) or re.fullmatch(r"1\.[0-9]+\.[0-9]+", trace["schemaVersion"]) is None:
        raise ValueError("unsupported TrafficTrace major version")
    _identifier(trace["traceId"], "traceId")
    _identifier(trace["modelInputVersion"], "modelInputVersion")
    if trace["sourceKind"] not in ALLOWED_SOURCES:
        raise ValueError("sourceKind must explicitly identify instrumented-rpc or synthetic-fixture")
    observations = trace["observations"]
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a non-empty array")
    if len(observations) > MAX_OBSERVATIONS:
        raise ValueError("trace observation limit exceeded")

    result: List[Feature] = []
    previous_offset = -1
    bound_session = None
    bound_request = None
    total_length = 0
    for observation in observations:
        expected = {"schemaVersion", "traceId", "sessionId", "requestId", "direction",
                    "encodedFrameLength", "monotonicOffsetNanos", "transport", "protocolVersion"}
        if not isinstance(observation, Mapping) or set(observation) != expected:
            raise ValueError("observation shape is invalid or contains payload/private metadata")
        if observation["schemaVersion"] != trace["schemaVersion"]:
            raise ValueError("observation schema version does not match trace")
        if observation["traceId"] != trace["traceId"]:
            raise ValueError("observation traceId does not match trace")
        session_id = _identifier(observation["sessionId"], "sessionId")
        request_id = _identifier(observation["requestId"], "requestId")
        if bound_session is None:
            bound_session, bound_request = session_id, request_id
        elif session_id != bound_session or request_id != bound_request:
            raise ValueError("observations must bind one sessionId and requestId")
        if observation["direction"] not in ALLOWED_DIRECTIONS:
            raise ValueError("unsupported frame direction")
        length = observation["encodedFrameLength"]
        if type(length) is not int or length < 1 or length > 1024 * 1024:
            raise ValueError("encodedFrameLength must be between 1 and 1048576")
        offset = observation["monotonicOffsetNanos"]
        if type(offset) is not int or offset < 0 or offset < previous_offset:
            raise ValueError("monotonic offsets must be non-negative and ordered")
        if observation["transport"] != "tiny-rpc-netty":
            raise ValueError("only tiny-rpc-netty instrumented frames are supported")
        if not isinstance(observation["protocolVersion"], str) or not 1 <= len(observation["protocolVersion"]) <= 32:
            raise ValueError("protocolVersion is required")
        previous_offset = offset
        total_length += length
        if total_length > MAX_TOTAL_ENCODED_BYTES:
            raise ValueError("trace encoded-length budget exceeded")
        result.append((observation["direction"], length))
    return tuple(result)


def edit_distance(left: Sequence[Feature], right: Sequence[Feature]) -> int:
    """Symmetric Levenshtein distance with a direction/length substitution cost."""
    if len(left) > MAX_OBSERVATIONS or len(right) > MAX_OBSERVATIONS:
        raise ValueError("feature sequence limit exceeded")
    previous = list(range(len(right) + 1))
    for index, left_feature in enumerate(left, 1):
        current = [index]
        for other_index, right_feature in enumerate(right, 1):
            substitution = 0 if left_feature == right_feature else 1
            current.append(min(current[-1] + 1,
                               previous[other_index] + 1,
                               previous[other_index - 1] + substitution))
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class ProfileModel:
    version: str
    threshold: int
    ambiguity_margin: int
    medoids: Tuple[Tuple[str, FeatureSequence], ...]
    fixture_hash: str
    profile_patterns: Tuple[Tuple[str, Tuple[Tuple[str, str, str], ...]], ...] = ()

    @property
    def model_hash(self) -> str:
        return _sha256(self.to_dict(include_hash=False))

    def to_dict(self, include_hash: bool = True) -> Dict[str, Any]:
        value: Dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "modelVersion": self.version,
            "threshold": self.threshold,
            "ambiguityMargin": self.ambiguity_margin,
            "fixtureHash": self.fixture_hash,
            "medoids": [{"label": label,
                         "features": [{"direction": direction, "encodedFrameLength": length}
                                      for direction, length in features]}
                        for label, features in self.medoids],
            "profilePatterns": [
                {"label": label,
                 "patterns": [{"kind": kind, "status": status, "details": details}
                              for kind, status, details in patterns]}
                for label, patterns in self.profile_patterns
            ],
        }
        if include_hash:
            value["modelHash"] = self.model_hash
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProfileModel":
        if not isinstance(value, Mapping):
            raise ValueError("model must be an object")
        allowed = {"schemaVersion", "modelVersion", "threshold", "ambiguityMargin",
                   "fixtureHash", "medoids", "profilePatterns", "modelHash"}
        if set(value) != allowed:
            raise ValueError("model has unsupported or missing fields")
        if not isinstance(value.get("schemaVersion"), str) or re.fullmatch(r"1\.[0-9]+\.[0-9]+", value["schemaVersion"]) is None:
            raise ValueError("unsupported model major version")
        version = _identifier(value.get("modelVersion"), "modelVersion")
        threshold = value.get("threshold")
        margin = value.get("ambiguityMargin")
        if type(threshold) is not int or threshold < 0 or type(margin) is not int or margin < 0:
            raise ValueError("threshold and ambiguityMargin must be non-negative integers")
        medoids = []
        raw_medoids = value.get("medoids")
        if not isinstance(raw_medoids, list) or not raw_medoids or len(raw_medoids) > MAX_PROFILES:
            raise ValueError("medoids must be a bounded non-empty array")
        for medoid in raw_medoids:
            if not isinstance(medoid, Mapping) or set(medoid) != {"label", "features"}:
                raise ValueError("invalid medoid shape")
            label = _identifier(medoid.get("label"), "label")
            features = medoid.get("features")
            if not isinstance(features, list) or not features or len(features) > MAX_OBSERVATIONS:
                raise ValueError("medoid features must be a bounded non-empty array")
            normalized: List[Feature] = []
            for feature in features:
                if not isinstance(feature, Mapping) or set(feature) != {"direction", "encodedFrameLength"}:
                    raise ValueError("invalid medoid feature shape")
                if feature["direction"] not in ALLOWED_DIRECTIONS:
                    raise ValueError("invalid medoid direction")
                length = feature["encodedFrameLength"]
                if type(length) is not int or not 1 <= length <= 1024 * 1024:
                    raise ValueError("invalid medoid frame length")
                normalized.append((feature["direction"], length))
            medoids.append((label, tuple(normalized)))
        if len({label for label, _ in medoids}) != len(medoids):
            raise ValueError("model labels must be unique")
        fixture_hash = value.get("fixtureHash")
        if not isinstance(fixture_hash, str) or re.fullmatch(r"[a-f0-9]{64}", fixture_hash) is None:
            raise ValueError("fixtureHash must be a SHA-256 digest")
        profile_patterns = []
        raw_profile_patterns = value.get("profilePatterns")
        if not isinstance(raw_profile_patterns, list) or len(raw_profile_patterns) > MAX_PROFILES:
            raise ValueError("profilePatterns must be a bounded array")
        allowed_kinds = {"ordering", "conflict", "dependency", "frequency"}
        allowed_statuses = {"matched", "violated", "unknown"}
        for entry in raw_profile_patterns:
            if not isinstance(entry, Mapping) or set(entry) != {"label", "patterns"}:
                raise ValueError("invalid profilePatterns entry")
            label = _identifier(entry["label"], "profile pattern label")
            if label not in {name for name, _ in medoids}:
                raise ValueError("profilePatterns label is not a model medoid")
            if not isinstance(entry["patterns"], list) or len(entry["patterns"]) > 64:
                raise ValueError("profile pattern count is invalid")
            patterns = []
            for pattern in entry["patterns"]:
                if not isinstance(pattern, Mapping) or set(pattern) != {"kind", "status", "details"}:
                    raise ValueError("invalid profile pattern shape")
                if pattern["kind"] not in allowed_kinds or pattern["status"] not in allowed_statuses:
                    raise ValueError("unsupported profile pattern")
                details = pattern["details"]
                if not isinstance(details, str) or len(details) > 256:
                    raise ValueError("profile pattern details are invalid")
                patterns.append((pattern["kind"], pattern["status"], details))
            profile_patterns.append((label, tuple(patterns)))
        model = cls(version, threshold, margin, tuple(sorted(medoids)), fixture_hash,
                    tuple(sorted(profile_patterns)))
        supplied_hash = value.get("modelHash")
        if supplied_hash != model.model_hash:
            raise ValueError("modelHash does not match model content")
        return model


def train_model(labelled_traces: Mapping[str, Iterable[Mapping[str, Any]]], *,
                version: str = "traffic-profile-v1", threshold: int = 1,
                ambiguity_margin: int = 0,
                label_patterns: Mapping[str, Iterable[Mapping[str, str]]] = None) -> ProfileModel:
    _identifier(version, "modelVersion")
    if not labelled_traces or len(labelled_traces) > MAX_PROFILES:
        raise ValueError("training set must contain a bounded number of labels")
    normalized: Dict[str, Tuple[FeatureSequence, ...]] = {}
    fixture_material: List[Dict[str, Any]] = []
    for label in sorted(labelled_traces):
        _identifier(label, "label")
        traces = list(labelled_traces[label])
        if not traces or len(traces) > MAX_PROFILES:
            raise ValueError("each label needs a bounded non-empty trace set")
        sequences = tuple(normalize_trace(trace) for trace in traces)
        normalized[label] = sequences
        fixture_material.extend(dict(trace) for trace in traces)

    medoids: List[Tuple[str, FeatureSequence]] = []
    for label, sequences in sorted(normalized.items()):
        medoid = min(sequences,
                     key=lambda candidate: (sum(edit_distance(candidate, other) for other in sequences),
                                            candidate))
        medoids.append((label, medoid))
    patterns = []
    for label, entries in sorted((label_patterns or {}).items()):
        if label not in normalized:
            raise ValueError("label_patterns contains an unknown label")
        converted = []
        for entry in entries:
            converted.append((entry["kind"], entry["status"], entry["details"]))
        patterns.append((label, tuple(converted)))
    model = ProfileModel(version, threshold, ambiguity_margin, tuple(medoids),
                         _sha256(fixture_material), tuple(patterns))
    # Reuse the serialized-model validator so direct API callers and the CLI
    # enforce identical bounds and pattern vocabularies.
    return ProfileModel.from_dict(model.to_dict())


def classify(trace: Mapping[str, Any], model: ProfileModel, *,
             produced_at: str = "1970-01-01T00:00:00Z") -> Dict[str, Any]:
    features = normalize_trace(trace)
    distances = sorted((edit_distance(features, medoid), label)
                       for label, medoid in model.medoids)
    best_distance, best_label = distances[0]
    competitors = [label for distance, label in distances
                   if distance <= best_distance + model.ambiguity_margin]
    ambiguous = len(competitors) > 1
    anomalous = best_distance > model.threshold
    accepted = not ambiguous and not anomalous
    label = best_label if accepted else "unknown-profile"
    confidence = 0.0 if ambiguous else max(0.0, 1.0 - (best_distance / max(1, model.threshold + 1)))
    try:
        parsed = datetime.fromisoformat(produced_at.replace("Z", "+00:00"))
    except (ValueError, TypeError) as error:
        raise ValueError("produced_at must be RFC 3339") from error
    if not produced_at.endswith("Z") or parsed.tzinfo is None:
        raise ValueError("produced_at must be UTC RFC 3339 ending in Z")
    trace_id = trace["traceId"]
    profile_suffix = hashlib.sha256((trace_id + model.model_hash).encode("utf-8")).hexdigest()[:16]
    profile_patterns = dict(model.profile_patterns)
    return {
        "schemaVersion": "1.0.1",
        "profileId": "profile-" + profile_suffix,
        "traceId": trace_id,
        "modelVersion": model.version,
        "modelHash": model.model_hash,
        "fixtureHash": model.fixture_hash,
        "distance": best_distance,
        "label": label,
        "confidence": confidence,
        "anomaly": {"detected": anomalous,
                    "reason": "distance-above-threshold" if anomalous else ""},
        "ambiguity": {"detected": ambiguous,
                      "candidateLabels": sorted(competitors) if ambiguous else []},
        "patterns": [{"kind": kind, "status": status, "details": details}
                     for kind, status, details in profile_patterns.get(best_label, ())] if accepted else [],
        "producedAt": produced_at,
    }


def canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
