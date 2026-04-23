from __future__ import annotations

import unittest

from minesweeper.ui import GameConfig, LocalMinesweeperApp


class MinesweeperUiTests(unittest.TestCase):
    def test_render_phase_and_next_action_show_finished_countdown(self) -> None:
        app = LocalMinesweeperApp(GameConfig(rows=4, cols=4, mines=2))
        app.game.finished = True
        app.game.won = True
        app._restart_countdown = 4

        self.assertIn("CLEARED", app.render_phase())
        self.assertIn("4s", app.render_next_action())

    def test_render_board_marks_selected_blank_cell_with_frame(self) -> None:
        app = LocalMinesweeperApp(GameConfig(rows=4, cols=4, mines=2))
        cell = app.game.grid[app.cursor_row][app.cursor_col]
        cell.is_revealed = True
        cell.adjacent_mines = 0

        board = app.render_board().plain

        self.assertIn("[ ]", board)

    def test_render_board_keeps_unselected_blank_cell_plain(self) -> None:
        app = LocalMinesweeperApp(GameConfig(rows=4, cols=4, mines=2))
        target = app.game.grid[0][0]
        target.is_revealed = True
        target.adjacent_mines = 0
        app.cursor_row = 1
        app.cursor_col = 1

        board = app.render_board().plain.splitlines()

        self.assertIn("   ", board[1])

    def test_render_board_keeps_selected_number_unframed(self) -> None:
        app = LocalMinesweeperApp(GameConfig(rows=4, cols=4, mines=2))
        cell = app.game.grid[app.cursor_row][app.cursor_col]
        cell.is_revealed = True
        cell.adjacent_mines = 2

        board = app.render_board().plain

        self.assertIn(" 2 ", board)
        self.assertNotIn("[2]", board)


if __name__ == "__main__":
    unittest.main()
