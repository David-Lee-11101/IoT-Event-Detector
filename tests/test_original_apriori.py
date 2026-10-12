import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (Path(__file__).resolve().parents[1] / "experiments" / "historical-detector"
               / "source" / "Apriori" / "Apriori.py")
SPEC = importlib.util.spec_from_file_location("historical_apriori", MODULE_PATH)
historical_apriori = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(historical_apriori)
generate_L = historical_apriori.generate_L
generate_big_rules = historical_apriori.generate_big_rules


class OriginalAprioriTest(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            ["motion", "light"],
            ["motion", "light"],
            ["motion", "notification"],
            ["light", "notification"],
        ]

    def test_known_support_and_pruning(self):
        levels, support = generate_L(self.transactions, k=2, min_support=0.5)
        motion_light = frozenset({"motion", "light"})
        motion_notification = frozenset({"motion", "notification"})

        self.assertIn(motion_light, levels[1])
        self.assertEqual(0.5, support[motion_light])
        self.assertNotIn(motion_notification, levels[1])

    def test_known_confidence(self):
        levels, support = generate_L(self.transactions, k=2, min_support=0.5)
        rules = generate_big_rules(levels, support, min_conf=0.6)
        confidence = {
            (tuple(sorted(left)), tuple(sorted(right))): value
            for left, right, value in rules
        }
        self.assertAlmostEqual(2 / 3, confidence[(("motion",), ("light",))])
        self.assertAlmostEqual(2 / 3, confidence[(("light",), ("motion",))])


if __name__ == "__main__":
    unittest.main()
