from __future__ import annotations

import unittest

from gomoku.core import Board, GameState, Player


class BoardTests(unittest.TestCase):
    def test_first_move_succeeds(self) -> None:
        state = GameState()
        move = state.play(7, 7)
        self.assertEqual(move.player, Player.BLACK)
        self.assertEqual(state.board.grid[7][7], Player.BLACK)

    def test_occupied_position_is_rejected(self) -> None:
        state = GameState()
        state.play(7, 7)
        with self.assertRaisesRegex(ValueError, "occupied"):
            state.play(7, 7)

    def test_out_of_bounds_move_is_rejected(self) -> None:
        state = GameState()
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            state.play(-1, 0)

    def test_horizontal_win_is_detected(self) -> None:
        state = GameState()
        self._play_moves(state, [(7, 0), (8, 0), (7, 1), (8, 1), (7, 2), (8, 2), (7, 3), (8, 3), (7, 4)])
        self.assertTrue(state.finished)
        self.assertEqual(state.winner, Player.BLACK)

    def test_vertical_win_is_detected(self) -> None:
        state = GameState()
        self._play_moves(state, [(0, 7), (0, 8), (1, 7), (1, 8), (2, 7), (2, 8), (3, 7), (3, 8), (4, 7)])
        self.assertTrue(state.finished)
        self.assertEqual(state.winner, Player.BLACK)

    def test_diagonal_wins_are_detected(self) -> None:
        descending = GameState()
        self._play_moves(
            descending,
            [(0, 0), (0, 5), (1, 1), (1, 5), (2, 2), (2, 5), (3, 3), (3, 5), (4, 4)],
        )
        self.assertEqual(descending.winner, Player.BLACK)

        ascending = GameState()
        self._play_moves(
            ascending,
            [(4, 0), (0, 5), (3, 1), (1, 5), (2, 2), (2, 5), (1, 3), (3, 5), (0, 4)],
        )
        self.assertEqual(ascending.winner, Player.BLACK)

    def test_longer_than_five_counts_as_win(self) -> None:
        board = Board()
        for col in range(6):
            board.place(Player.BLACK, 7, col)
        self.assertTrue(board.has_five_in_a_row(7, 5, Player.BLACK))

    def test_draw_is_detected_on_full_board_without_winner(self) -> None:
        size = 15
        board_tokens = []
        for row in range(size):
            first = "B" if row % 4 in (0, 1) else "W"
            second = "W" if first == "B" else "B"
            board_tokens.append("".join(first if col % 2 == 0 else second for col in range(size)))

        board_tokens[-1] = board_tokens[-1][:-1] + "."

        state = GameState(board=Board.from_tokens(board_tokens), current_player=Player.BLACK)
        state.play(14, 14)
        self.assertTrue(state.draw)
        self.assertTrue(state.finished)
        self.assertIsNone(state.winner)

    def test_no_moves_after_finish(self) -> None:
        state = GameState()
        self._play_moves(state, [(7, 0), (8, 0), (7, 1), (8, 1), (7, 2), (8, 2), (7, 3), (8, 3), (7, 4)])
        with self.assertRaisesRegex(ValueError, "finished"):
            state.play(0, 0)

    def _play_moves(self, state: GameState, moves: list[tuple[int, int]]) -> None:
        for row, col in moves:
            state.play(row, col)


if __name__ == "__main__":
    unittest.main()
