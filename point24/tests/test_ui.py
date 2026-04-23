from __future__ import annotations

import unittest

from point24.storage import Point24Puzzle, Point24Stats
from point24.ui import Point24App


class _FakeRepository:
    def __init__(self) -> None:
        self.catalog = [
            Point24Puzzle(key="1,1,4,6", numbers=(1, 1, 4, 6), solution="(6 - 1) * (4 + 1)"),
            Point24Puzzle(key="3,3,8,8", numbers=(3, 3, 8, 8), solution="8 / (3 - (8 / 3))"),
        ]
        self.stats = Point24Stats()

    def ensure_catalog(self) -> list[Point24Puzzle]:
        return self.catalog

    def load_stats(self) -> Point24Stats:
        return self.stats

    def save_stats(self, stats: Point24Stats) -> None:
        self.stats = stats

    def choose_next_puzzle(
        self,
        catalog: list[Point24Puzzle],
        solved_puzzle_keys: set[str],
        rng: object | None = None,
    ) -> Point24Puzzle:
        for puzzle in catalog:
            if puzzle.key not in solved_puzzle_keys:
                return puzzle
        return catalog[0]


class Point24UiTests(unittest.IsolatedAsyncioTestCase):
    async def test_global_shortcuts_work_while_input_is_focused(self) -> None:
        app = Point24App(repository=_FakeRepository())

        async with app.run_test() as pilot:
            self.assertEqual(app.focused.id, "expression")

            await pilot.press("t")
            self.assertEqual(app.theme_mode, "stealth")

            await pilot.press("n")
            self.assertIn("Skipped. One solution:", app.message)

            await pilot.press("q")
            await pilot.pause()

            self.assertEqual(app.return_value, 0)
            self.assertFalse(app.is_running)

    def test_render_summary_includes_session_progress(self) -> None:
        app = Point24App(repository=_FakeRepository())
        app.session_streak = 2
        app.best_streak = 3
        app.session_skips = 1

        summary = app.render_summary()

        self.assertIn("Streak:    2", summary)
        self.assertIn("Best run:  3", summary)
        self.assertIn("Skips:     1", summary)


if __name__ == "__main__":
    unittest.main()
