from __future__ import annotations

import unittest

from snake.ui import SnakeApp


class SnakeUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_shortcuts_pause_and_toggle_theme(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test() as pilot:
            self.assertTrue(app.configuring)
            app.action_start_round()
            self.assertFalse(app.configuring)

            await pilot.press("space")
            self.assertTrue(app.paused)
            self.assertIn("Paused", app.message)

            await pilot.press("t")
            self.assertEqual(app.theme_mode, "stealth")

    async def test_setup_cycles_map_and_speed(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test() as pilot:
            await pilot.press("m")
            await pilot.press("v")

            self.assertEqual(app.selected_map_id, "open_wrap")
            self.assertEqual(app.selected_speed_id, "fast")
            self.assertIn("Open Wrap", app.render_summary())
            self.assertIn("+3", app.render_summary())

    async def test_restart_returns_to_setup(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test() as pilot:
            app.action_start_round()
            self.assertFalse(app.configuring)

            await pilot.press("r")

            self.assertTrue(app.configuring)
            self.assertIn("Start", app.render_next_action())

    async def test_crash_returns_to_setup(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test() as pilot:
            app.action_start_round()
            app.game.snake = [(0, 2), (0, 1), (0, 0)]
            app.game.direction = "left"
            app.game.next_direction = "left"
            app.on_tick()

            self.assertTrue(app.configuring)
            self.assertTrue(app.game.game_over)

    async def test_board_uses_half_height_cells(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test():
            app.action_start_round()
            board = app.render_board().plain

            # 8 game rows packed into 4 half-block rows + 2 border rows = 6 lines
            lines = board.splitlines()
            self.assertEqual(len(lines), 6)
            # 8 cols + 2 border chars = 10 chars per line
            self.assertEqual(len(lines[0]), 10)
            self.assertEqual(len(lines[1]), 10)
            self.assertNotIn("@@", board)

    async def test_board_marks_head_and_food(self) -> None:
        app = SnakeApp(rows=8, cols=8)

        async with app.run_test():
            app.action_start_round()
            board = app.render_board().plain

            # head and body are rendered as block chars
            self.assertTrue(any(ch in board for ch in "█▀▄"))
            # empty cells are single spaces (no dot noise)
            self.assertNotIn("·", board)


if __name__ == "__main__":
    unittest.main()
