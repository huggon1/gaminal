from __future__ import annotations

import unittest

from dou_dizhu.core import CardPattern, analyze_play, compare_patterns


class DdzRuleTests(unittest.TestCase):
    def test_identifies_basic_patterns(self) -> None:
        self.assertEqual(analyze_play(["3S"]).kind, "single")
        self.assertEqual(analyze_play(["3S", "3H"]).kind, "pair")
        self.assertEqual(analyze_play(["BJ", "RJ"]).kind, "rocket")
        self.assertEqual(analyze_play(["4S", "4H", "4C", "4D"]).kind, "bomb")

    def test_identifies_straights_and_airplanes(self) -> None:
        straight = analyze_play(["3S", "4S", "5S", "6S", "7S"])
        pair_straight = analyze_play(["3S", "3H", "4S", "4H", "5S", "5H"])
        airplane_pair = analyze_play(
            [
                "3S",
                "3H",
                "3C",
                "4S",
                "4H",
                "4C",
                "5S",
                "5H",
                "5C",
                "6S",
                "6H",
                "6C",
                "7S",
                "7H",
                "8S",
                "8H",
                "9S",
                "9H",
                "10S",
                "10H",
            ]
        )

        self.assertEqual(straight, CardPattern("straight", 3, 5, chain_length=5))
        self.assertEqual(pair_straight.kind, "pair_straight")
        self.assertEqual(airplane_pair.kind, "airplane_pair")
        self.assertEqual(airplane_pair.chain_length, 4)

    def test_rejects_invalid_sequence_with_two_or_jokers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            analyze_play(["10S", "JS", "QS", "KS", "AS", "2S"])

    def test_compare_patterns_respects_bombs_and_matching_shapes(self) -> None:
        pair_low = analyze_play(["5S", "5H"])
        pair_high = analyze_play(["7S", "7H"])
        bomb = analyze_play(["4S", "4H", "4C", "4D"])
        rocket = analyze_play(["BJ", "RJ"])

        self.assertTrue(compare_patterns(pair_high, pair_low))
        self.assertFalse(compare_patterns(pair_low, pair_high))
        self.assertTrue(compare_patterns(bomb, pair_high))
        self.assertTrue(compare_patterns(rocket, bomb))


if __name__ == "__main__":
    unittest.main()
