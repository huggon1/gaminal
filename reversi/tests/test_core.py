from __future__ import annotations

import unittest

from reversi.core import Board, GameState, Player


class ReversiCoreTests(unittest.TestCase):
    def test_initial_valid_moves_for_black(self) -> None:
        state = GameState()

        self.assertEqual(
            state.valid_moves_for_current(),
            [(2, 3), (3, 2), (4, 5), (5, 4)],
        )
        self.assertEqual(state.get_scores(), (2, 2))

    def test_play_flips_pieces_and_switches_turn(self) -> None:
        state = GameState()

        move = state.play(2, 3)

        self.assertEqual(move.player, Player.BLACK)
        self.assertEqual(state.board.grid[2][3], Player.BLACK)
        self.assertEqual(state.board.grid[3][3], Player.BLACK)
        self.assertEqual(state.current_player, Player.WHITE)
        self.assertEqual(state.get_scores(), (4, 1))

    def test_rejects_occupied_and_non_flipping_moves(self) -> None:
        state = GameState()

        with self.assertRaisesRegex(ValueError, "occupied"):
            state.play(3, 3)
        with self.assertRaisesRegex(ValueError, "no pieces would be flipped"):
            state.play(0, 0)

    def test_rejects_out_of_bounds_move(self) -> None:
        state = GameState()

        with self.assertRaisesRegex(ValueError, "out of bounds"):
            state.play(-1, 0)

    def test_skips_turn_when_opponent_has_no_moves(self) -> None:
        state = GameState(
            board=Board.from_tokens(
                [
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBW.W.",
                ]
            ),
            current_player=Player.BLACK,
        )

        state.play(7, 5)

        self.assertTrue(state.skipped_turn)
        self.assertFalse(state.finished)
        self.assertEqual(state.current_player, Player.BLACK)
        self.assertEqual(state.board.valid_moves(Player.WHITE), [])
        self.assertEqual(state.board.valid_moves(Player.BLACK), [(7, 7)])

    def test_full_board_resolves_winner_by_count(self) -> None:
        state = GameState(
            board=Board.from_tokens(
                [
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBBB",
                    "BBBBBBW.",
                ]
            ),
            current_player=Player.BLACK,
        )

        state.play(7, 7)

        self.assertTrue(state.finished)
        self.assertEqual(state.winner, Player.BLACK)
        self.assertFalse(state.draw)
        self.assertEqual(state.get_scores(), (64, 0))

    def test_resolve_winner_marks_draw_for_equal_counts(self) -> None:
        state = GameState(
            board=Board.from_tokens(
                [
                    "BWBWBWBW",
                    "WBWBWBWB",
                    "BWBWBWBW",
                    "WBWBWBWB",
                    "BWBWBWBW",
                    "WBWBWBWB",
                    "BWBWBWBW",
                    "WBWBWBWB",
                ]
            ),
            current_player=Player.BLACK,
        )

        state._resolve_winner()

        self.assertTrue(state.finished)
        self.assertTrue(state.draw)
        self.assertIsNone(state.winner)
        self.assertEqual(state.get_scores(), (32, 32))

    def test_snapshot_round_trip_preserves_state(self) -> None:
        state = GameState()
        for row, col in [(2, 3), (2, 2), (2, 1)]:
            state.play(row, col)

        restored = GameState.from_snapshot(state.to_snapshot())

        self.assertEqual(restored.board.to_tokens(), state.board.to_tokens())
        self.assertEqual(restored.current_player, state.current_player)
        self.assertEqual(restored.winner, state.winner)
        self.assertEqual(restored.draw, state.draw)
        self.assertEqual(restored.finished, state.finished)
        self.assertEqual(restored.skipped_turn, state.skipped_turn)
        self.assertIsNotNone(restored.last_move)
        self.assertEqual(restored.last_move.row, 2)
        self.assertEqual(restored.last_move.col, 1)
        self.assertEqual(restored.last_move.player, Player.BLACK)
        self.assertEqual(restored.get_scores(), state.get_scores())


if __name__ == "__main__":
    unittest.main()
