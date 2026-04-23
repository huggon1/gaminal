from __future__ import annotations

import unittest

from tetris.ui import ACTIVE_CELL, EMPTY_CELL, TetrisApp


class TetrisUiTests(unittest.TestCase):
    def test_render_summary_reports_progress(self) -> None:
        app = TetrisApp()
        app.session_best = 300
        app.game.score = 180
        app.game.lines = 7

        summary = app.render_summary()

        self.assertIn("Best:     300", summary)
        self.assertIn("Lines:    7", summary)
        self.assertIn("To next:", summary)

    def test_render_next_action_shows_restart_countdown(self) -> None:
        app = TetrisApp()
        app.game.game_over = True
        app._restart_countdown = 5

        self.assertIn("5s", app.render_next_action())

    def test_render_board_uses_double_width_cells(self) -> None:
        app = TetrisApp()

        board = app.render_board().plain.splitlines()

        self.assertEqual("+" + "-" * (app.game.COLS * len(EMPTY_CELL)) + "+", board[0])
        self.assertEqual(2 + app.game.COLS * len(EMPTY_CELL), len(board[1]))

    def test_render_next_piece_uses_double_width_cells(self) -> None:
        app = TetrisApp()
        app.game.next_kind = "O"

        preview = app.render_next_piece().plain

        self.assertIn(ACTIVE_CELL * 2, preview)


if __name__ == "__main__":
    unittest.main()
