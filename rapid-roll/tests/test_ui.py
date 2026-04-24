from __future__ import annotations

import unittest

from rapid_roll.core import BonusItem, Platform
from rapid_roll.ui import RapidRollApp


class RapidRollUiTests(unittest.TestCase):
    def test_css_gives_board_view_flexible_height(self) -> None:
        self.assertIn("#board-view", RapidRollApp.CSS)
        self.assertIn("height: 1fr;", RapidRollApp.CSS)

    def test_render_summary_reports_session_stats(self) -> None:
        app = RapidRollApp(rows=18, cols=16)
        app.session_best = 200
        app.rounds_started = 3
        app.game.score = 75
        app.game.active_effects = {"slow": 10}

        summary = app.render_summary()

        self.assertIn("Best:     200", summary)
        self.assertIn("Rounds:   3", summary)
        self.assertIn("Lives:", summary)
        self.assertIn("slow", summary)

    def test_render_next_action_shows_restart_countdown(self) -> None:
        app = RapidRollApp(rows=18, cols=16)
        app.game.game_over = True
        app._restart_countdown = 4

        self.assertIn("4s", app.render_next_action())

    def test_render_board_contains_core_symbols(self) -> None:
        app = RapidRollApp(rows=18, cols=16)
        app.game.platforms = [Platform(row=8.0, col=3, width=5)]
        app.game.items = [BonusItem(kind="coin", row=7.0, col=5)]
        app.game.ball_row = 6.0
        app.game.ball_col = 6.0

        board = app.render_board().plain

        self.assertIn("●", board)
        self.assertIn("═", board)
        self.assertIn("◆", board)
        self.assertIn("^", board)
        self.assertIn("v", board)


if __name__ == "__main__":
    unittest.main()
