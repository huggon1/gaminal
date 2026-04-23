from __future__ import annotations

import unittest

from bluff_cards.core import BluffRoundState, choose_basic_claim, create_shuffled_deck, is_truthful_claim, should_basic_challenge


class BluffCoreTests(unittest.TestCase):
    def test_liars_deck_uses_small_card_pool(self) -> None:
        deck = create_shuffled_deck(seed=1)

        self.assertEqual(len(deck), 20)
        self.assertEqual(sum(1 for card in deck if card.startswith("A")), 6)
        self.assertEqual(sum(1 for card in deck if card.startswith("K")), 6)
        self.assertEqual(sum(1 for card in deck if card.startswith("Q")), 6)
        self.assertEqual(sum(1 for card in deck if card.startswith("JOKER")), 2)

    def test_basic_claim_prefers_truthful_table_cards(self) -> None:
        actual_cards = choose_basic_claim(["Q1", "A1", "JOKER1"], "A")

        self.assertEqual(actual_cards, ["A1", "JOKER1"])

    def test_basic_challenge_is_aggressive_against_final_claim(self) -> None:
        self.assertTrue(should_basic_challenge(["Q1"], "A", 1, 0))
        self.assertFalse(should_basic_challenge(["A1", "JOKER1"], "A", 1, 2))

    def test_truthful_claim_accepts_jokers_as_wildcards(self) -> None:
        self.assertTrue(is_truthful_claim(["A1", "JOKER1"], "A"))
        self.assertFalse(is_truthful_claim(["A1", "K1"], "A"))

    def test_challenge_redeals_and_changes_table_rank_when_round_continues(self) -> None:
        state = BluffRoundState(
            hands={1: ["Q1", "A1"], 2: ["K1"], 3: ["Q2"]},
            lives={1: 3, 2: 3, 3: 3},
            table_rank="A",
            current_turn=1,
        )

        state.play_claim(1, ["Q1"])
        result = state.challenge(2)

        self.assertFalse(result.truthful)
        self.assertEqual(result.loser_seat, 1)
        self.assertEqual(state.lives[1], 2)
        self.assertEqual(state.phase, "in_round")
        self.assertIsNone(state.last_claim)
        self.assertIn(state.table_rank, {"A", "K", "Q"})
        self.assertEqual(state.current_turn, 2)

    def test_truthful_final_claim_wins_immediately(self) -> None:
        state = BluffRoundState(
            hands={1: ["A1"], 2: ["K1"]},
            lives={1: 3, 2: 3},
            table_rank="A",
            current_turn=1,
        )

        state.play_claim(1, ["A1"])
        result = state.challenge(2)

        self.assertTrue(result.truthful)
        self.assertEqual(state.phase, "finished")
        self.assertEqual(state.winner_seat, 1)


if __name__ == "__main__":
    unittest.main()
