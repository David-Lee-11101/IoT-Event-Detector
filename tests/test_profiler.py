import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from smart_rule_analyzer.profiler import (
    MAX_OBSERVATIONS, ProfileModel, canonical_json, classify, edit_distance,
    normalize_trace, train_model,
)


def trace(trace_id, lengths, source="synthetic-fixture"):
    observations = []
    for index, length in enumerate(lengths):
        observations.append({
            "schemaVersion": "1.0.0",
            "traceId": trace_id,
            "sessionId": "session-demo",
            "requestId": "request-demo",
            "direction": "client-to-server" if index % 2 == 0 else "server-to-client",
            "encodedFrameLength": length,
            "monotonicOffsetNanos": index * 100,
            "transport": "tiny-rpc-netty",
            "protocolVersion": "1",
        })
    return {"schemaVersion": "1.0.0", "traceId": trace_id,
            "sourceKind": source, "observations": observations}


class TrafficProfilerTest(unittest.TestCase):
    def setUp(self):
        self.training = {
            "sensor-read": [trace("trace-train-a", [96, 64]), trace("trace-train-b", [96, 65])],
            "device-write": [trace("trace-train-c", [128, 48, 48]), trace("trace-train-d", [127, 48, 48])],
        }
        self.patterns = {
            "sensor-read": [{"kind": "ordering", "status": "matched",
                             "details": "request frame precedes response frame"}],
            "device-write": [{"kind": "conflict", "status": "violated",
                              "details": "write-shaped profile requires conservative ordering"}],
        }
        self.model = train_model(self.training, threshold=1, ambiguity_margin=0,
                                 label_patterns=self.patterns)

    def test_distance_identity_symmetry_and_empty(self):
        left = (("client-to-server", 10), ("server-to-client", 20))
        right = (("client-to-server", 10),)
        self.assertEqual(0, edit_distance(left, left))
        self.assertEqual(edit_distance(left, right), edit_distance(right, left))
        self.assertEqual(2, edit_distance(left, ()))

    def test_model_and_evidence_are_byte_stable(self):
        other = train_model(copy.deepcopy(self.training), threshold=1, ambiguity_margin=0,
                            label_patterns=copy.deepcopy(self.patterns))
        self.assertEqual(canonical_json(self.model.to_dict()), canonical_json(other.to_dict()))
        sample = trace("trace-eval-exact", [96, 64], source="instrumented-rpc")
        first = classify(sample, self.model)
        second = classify(copy.deepcopy(sample), other)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual("sensor-read", first["label"])
        self.assertFalse(first["anomaly"]["detected"])
        self.assertEqual([{"kind": "ordering", "status": "matched",
                           "details": "request frame precedes response frame"}], first["patterns"])

    def test_near_match_anomaly_and_unknown(self):
        near = classify(trace("trace-eval-near", [96, 66]), self.model)
        self.assertEqual("sensor-read", near["label"])
        far = classify(trace("trace-eval-far", [7, 8, 9, 10, 11]), self.model)
        self.assertEqual("unknown-profile", far["label"])
        self.assertTrue(far["anomaly"]["detected"])

    def test_ambiguous_match_abstains(self):
        model = train_model({
            "alpha-profile": [trace("trace-alpha", [10])],
            "beta-profile": [trace("trace-beta", [20])],
        }, threshold=1, ambiguity_margin=0)
        evidence = classify(trace("trace-ambiguous", [30]), model)
        self.assertEqual("unknown-profile", evidence["label"])
        self.assertTrue(evidence["ambiguity"]["detected"])
        self.assertEqual(["alpha-profile", "beta-profile"],
                         evidence["ambiguity"]["candidateLabels"])

    def test_rejects_payload_private_metadata_bad_source_and_limits(self):
        sample = trace("trace-invalid", [20])
        sample["observations"][0]["payload"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "payload/private"):
            normalize_trace(sample)
        with self.assertRaisesRegex(ValueError, "sourceKind"):
            normalize_trace(trace("trace-source", [20], source="packet-capture"))
        oversized = trace("trace-limit", [1] * (MAX_OBSERVATIONS + 1))
        with self.assertRaisesRegex(ValueError, "observation limit"):
            normalize_trace(oversized)

    def test_training_and_evaluation_fixtures_are_distinct(self):
        evaluation = trace("trace-evaluation-only", [96, 64])
        evidence = classify(evaluation, self.model)
        self.assertNotEqual(evidence["traceId"], "trace-train-a")
        self.assertNotEqual(evidence["traceId"], "trace-train-b")

    def test_training_rejects_unsupported_profile_patterns(self):
        invalid = {"sensor-read": [{"kind": "marketing-claim", "status": "matched",
                                     "details": "unsupported"}]}
        with self.assertRaisesRegex(ValueError, "unsupported profile pattern"):
            train_model(self.training, label_patterns=invalid)

    def test_cli_accepts_instrumented_trace_and_writes_canonical_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_path = root / "model.json"
            trace_path = root / "trace.json"
            output_path = root / "evidence.json"
            model_path.write_text(canonical_json(self.model.to_dict()), encoding="utf-8")
            trace_path.write_text(canonical_json(trace("trace-loopback", [96, 64],
                                                       source="instrumented-rpc")), encoding="utf-8")
            completed = subprocess.run([
                sys.executable, "-m", "smart_rule_analyzer.profile_cli",
                "--trace", str(trace_path), "--model", str(model_path),
                "--output", str(output_path), "--produced-at", "2026-01-01T00:00:00Z",
            ], check=False, capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            value = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("trace-loopback", value["traceId"])
            self.assertEqual("sensor-read", value["label"])


if __name__ == "__main__":
    unittest.main()
