import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, cast

from smart_rule_analyzer.analyzer import analyze_rules
from smart_rule_analyzer.cli import main
from smart_rule_analyzer.models import RuleSpec


FIXTURE = Path(__file__).parents[1] / "examples" / "rulespec-v0.json"


class AnalyzerTest(unittest.TestCase):
    def test_rulespec_is_immutable(self):
        rule = RuleSpec.from_dict(json.loads(FIXTURE.read_text())[0])
        with self.assertRaises(Exception):
            rule.description = "changed"  # pyright: ignore[reportAttributeAccessIssue]

    def test_detects_conflicting_writes_but_not_identical_writes(self):
        rules = [RuleSpec.from_dict(item) for item in json.loads(FIXTURE.read_text())]
        result = analyze_rules(rules)
        conflicts = cast(List[Dict[str, object]], result["conflicts"])
        pairs = {(item["left"], item["right"]) for item in conflicts}
        self.assertIn(("close-curtain", "open-curtain"), pairs)
        self.assertNotIn(("close-curtain", "close-curtain-backup"), pairs)

    def test_builds_action_to_trigger_dependency_and_omits_independent_rules(self):
        rules = [RuleSpec.from_dict(item) for item in json.loads(FIXTURE.read_text())]
        result = analyze_rules(rules)
        dependencies = cast(List[Dict[str, object]], result["dependencies"])
        edges = {(item["source"], item["target"]) for item in dependencies}
        self.assertIn(("close-curtain", "notify-curtain-closed"), edges)
        self.assertNotIn(("independent-light", "notify-curtain-closed"), edges)

    def test_fixture_output_is_reproducible(self):
        rules = [RuleSpec.from_dict(item) for item in json.loads(FIXTURE.read_text())]
        actual = analyze_rules(rules)
        expected = json.loads((FIXTURE.parent / "expected-analysis.json").read_text())
        self.assertEqual(expected, actual)

    def test_rulespec_rejects_shared_contract_violations(self):
        valid = {
            "id": "r1",
            "description": "demo",
            "triggers": [{"device": "sensor", "state": "on"}],
            "conditions": [],
            "actions": [{"device": "lamp", "state": "on"}],
        }
        invalid_documents = [
            dict(valid, description=""),
            dict(valid, triggers=[]),
            dict(valid, actions=[]),
            dict(valid, actions=[{"device": "lamp", "state": ""}]),
            dict(valid, actions=["not-an-object"]),
            dict(valid, extra="unsupported"),
        ]
        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    RuleSpec.from_dict(document)

    def test_cli_rejects_empty_fixture_array(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "empty.json"
            fixture.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "2"):
                main([str(fixture)])


if __name__ == "__main__":
    unittest.main()
