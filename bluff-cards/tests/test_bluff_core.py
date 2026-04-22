from __future__ import annotations

import unittest

from bluff_cards.core import BluffRoundState, is_truthful_claim


class BluffCoreTests(unittest.TestCase):
    def test_truthful_claim_accepts_jokers_as_wildcards(self) -> None:
        self.assertTrue(is_truthful_claim(["AS", "BJ"], "A"))
        self.assertFalse(is_truthful_claim(["AS", "KS"], "A"))

    def test_challenge_penalizes_bluffer_and_advances_target(self) -> None:
        state = BluffRoundState(
            hands={
                1: ["3S", "AS"],
                2: ["KH"],
                3: ["QH"],
            },
            lives={1: 3, 2: 3, 3: 3},
            current_turn=1,
        )

        state.play_claim(1, ["3S"], 1)
        result = state.challenge(2)

        self.assertFalse(result.truthful)
        self.assertEqual(result.loser_seat, 1)
        self.assertEqual(state.lives[1], 2)
        self.assertEqual(state.target_rank, "K")
        self.assertEqual(state.current_turn, 2)
        self.assertIsNone(state.last_claim)

    def test_accept_finishes_when_empty_hand_claim_is_not_challenged(self) -> None:
        state = BluffRoundState(
            hands={
                1: ["AS"],
                2: ["KH"],
            },
            lives={1: 3, 2: 3},
            current_turn=1,
        )

        state.play_claim(1, ["AS"], 1)
        winner = state.accept(2)

        self.assertEqual(winner, 1)
        self.assertEqual(state.phase, "finished")
        self.assertEqual(state.winner_seat, 1)


if __name__ == "__main__":
    unittest.main()
