from __future__ import annotations

import unittest

from racing.ui import RacingApp


class RacingUiTests(unittest.TestCase):
    def test_render_summary_shows_gap_and_best_score(self) -> None:
        app = RacingApp(rows=10, cols=12)
        app.session_best = 140
        app.game.score = 90

        summary = app.render_summary()

        self.assertIn("Best:     140", summary)
        self.assertIn("Gap:", summary)
        self.assertIn("Speed:", summary)

    def test_render_next_action_shows_restart_countdown(self) -> None:
        app = RacingApp(rows=10, cols=12)
        app.game.game_over = True
        app._restart_countdown = 2

        self.assertIn("2s", app.render_next_action())


if __name__ == "__main__":
    unittest.main()
