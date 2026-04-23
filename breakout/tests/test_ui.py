from __future__ import annotations

import unittest

from breakout.ui import BreakoutApp


class BreakoutUiTests(unittest.TestCase):
    def test_css_gives_board_view_flexible_height(self) -> None:
        self.assertIn("#board-view", BreakoutApp.CSS)
        self.assertIn("height: 1fr;", BreakoutApp.CSS)

    def test_render_summary_reports_session_stats(self) -> None:
        app = BreakoutApp(rows=20, cols=12)
        app.session_best = 120
        app.rounds_started = 3
        app.game.score = 75
        app.game.active_effects = {"slow": 10}

        summary = app.render_summary()

        self.assertIn("Best:     120", summary)
        self.assertIn("Rounds:   3", summary)
        self.assertIn("slow", summary)

    def test_render_next_action_shows_restart_countdown(self) -> None:
        app = BreakoutApp(rows=20, cols=12)
        app.game.game_over = True
        app._restart_countdown = 4

        self.assertIn("4s", app.render_next_action())


if __name__ == "__main__":
    unittest.main()
