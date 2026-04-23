from __future__ import annotations

import unittest

from snake.ui import SnakeApp


class SnakeUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_shortcuts_pause_and_toggle_theme(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test() as pilot:
            await pilot.press("space")
            self.assertTrue(app.paused)
            self.assertIn("Paused", app.message)

            await pilot.press("t")
            self.assertEqual(app.theme_mode, "stealth")

    def test_render_next_action_shows_restart_countdown(self) -> None:
        app = SnakeApp(rows=8, cols=8)
        app.game.game_over = True
        app._restart_countdown = 3

        self.assertIn("3s", app.render_next_action())


if __name__ == "__main__":
    unittest.main()
