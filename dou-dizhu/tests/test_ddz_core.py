from __future__ import annotations

import unittest

from dou_dizhu.core import CardPattern, PlayContext, analyze_play, choose_basic_bid, choose_basic_play, compare_patterns, generate_legal_plays


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

    def test_generate_legal_plays_filters_to_winning_responses(self) -> None:
        previous = analyze_play(["6S", "6H"])
        hand = ["3S", "4S", "7S", "7H", "8S", "8H", "9S", "9H", "9C", "9D", "BJ", "RJ"]

        legal_plays = generate_legal_plays(hand, previous)

        self.assertIn(["7H", "7S"], legal_plays)
        self.assertIn(["8H", "8S"], legal_plays)
        self.assertIn(["9C", "9D", "9H", "9S"], legal_plays)
        self.assertIn(["BJ", "RJ"], legal_plays)
        self.assertNotIn(["3S"], legal_plays)
        self.assertNotIn(["4S"], legal_plays)

    def test_basic_ai_prefers_smallest_winning_play_and_scores_strong_hands(self) -> None:
        previous = analyze_play(["10S"])
        response = choose_basic_play(["JS", "QS", "KS", "2S", "2H", "BJ", "RJ"], previous)

        self.assertEqual(response, ["JS"])
        self.assertEqual(choose_basic_bid(["2S", "2H", "2C", "AS", "AH", "BJ", "RJ"]), 3)

    def test_basic_ai_passes_when_teammate_is_winning_trick(self) -> None:
        previous = analyze_play(["9S"])
        response = choose_basic_play(
            ["10S", "JS", "QS", "QH"],
            previous,
            context=PlayContext(
                seat=2,
                landlord_seat=1,
                last_play_seat=3,
                hand_counts={1: 8, 2: 4, 3: 6},
            ),
        )

        self.assertIsNone(response)

    def test_basic_ai_avoids_bomb_when_normal_response_is_available(self) -> None:
        previous = analyze_play(["8S", "8H"])
        response = choose_basic_play(
            ["9S", "9H", "JS", "JH", "JC", "JD"],
            previous,
            context=PlayContext(
                seat=2,
                landlord_seat=2,
                last_play_seat=1,
                hand_counts={1: 7, 2: 6, 3: 7},
            ),
        )

        self.assertEqual(response, ["9H", "9S"])

    def test_basic_ai_uses_stronger_stop_card_against_enemy_on_last_card(self) -> None:
        previous = analyze_play(["10S"])
        response = choose_basic_play(
            ["JS", "QS", "KS", "AS"],
            previous,
            context=PlayContext(
                seat=2,
                landlord_seat=2,
                last_play_seat=1,
                hand_counts={1: 1, 2: 4, 3: 5},
            ),
        )

        self.assertEqual(response, ["AS"])

    def test_basic_bid_respects_current_highest_bid(self) -> None:
        self.assertEqual(choose_basic_bid(["3S", "4S", "5S", "6S", "7S"], current_highest=1), 0)


if __name__ == "__main__":
    unittest.main()
