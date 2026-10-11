import unittest

from Detector.Apriori.Apriori import generate_L, generate_big_rules


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
