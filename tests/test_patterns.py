import unittest

from smart_rule_analyzer.patterns import ExecutionRecord, classify_execution_patterns


class ExecutionPatternTest(unittest.TestCase):
    def test_classifies_nine_bounded_historical_pattern_families(self):
        records = [
            ExecutionRecord("rule-a", "root-one", "run", (("lamp", "on"), ("door", "open"))),
            ExecutionRecord("rule-b", "root-one", "run", (("lamp", "off"),), (("door", "open"),)),
            ExecutionRecord("rule-c", "rule-a", "run", (("door", "open"),), (("lamp", "on"),)),
            ExecutionRecord("rule-d", "root-two", "skipped", (("door", "open"),), (("lamp", "off"),)),
            ExecutionRecord("rule-e", "root-three", "run", (("lamp", "off"),), (("door", "closed"),)),
        ]
        kinds = {finding.kind for finding in classify_execution_patterns(records)}
        self.assertEqual({
            "action-conflict", "unexpected-conflict", "action-repetition", "action-revert",
            "action-loop", "condition-bypass", "condition-block", "condition-pass",
            "condition-contradictory",
        }, kinds)

    def test_output_is_sorted_and_repeatable(self):
        records = [
            ExecutionRecord("rule-a", "root-one", "run", (("lamp", "on"),)),
            ExecutionRecord("rule-b", "root-two", "run", (("lamp", "off"),)),
        ]
        first = classify_execution_patterns(records)
        second = classify_execution_patterns(list(records))
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), first)


if __name__ == "__main__":
    unittest.main()
