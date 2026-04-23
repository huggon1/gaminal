from __future__ import annotations

import unittest

from game_2048.ui import Game2048App


class Game2048UiTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_theme_toggle_and_restart(self) -> None:
        app = Game2048App(size=4)

        async with app.run_test() as pilot:
            await pilot.press("t")
            self.assertEqual(app.theme_mode, "stealth")

            await pilot.press("r")
            self.assertIn("Started a new board.", app.message)

    def test_render_phase_and_countdown_for_finished_round(self) -> None:
        app = Game2048App(size=4)
        app.game.won = True
        app._restart_countdown = 4

        self.assertIn("2048", app.render_phase())
        self.assertIn("4s", app.render_next_action())


if __name__ == "__main__":
    unittest.main()
