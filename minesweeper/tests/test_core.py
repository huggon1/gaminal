from __future__ import annotations

import unittest

from minesweeper.core import MinesweeperGame, PRESET_DIFFICULTIES
from minesweeper.ui import resolve_config


class MinesweeperCoreTests(unittest.TestCase):
    def test_invalid_dimensions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            MinesweeperGame(0, 9, 10)
        with self.assertRaisesRegex(ValueError, "smaller than the board area"):
            MinesweeperGame(2, 2, 4)

    def test_first_reveal_places_mines_and_keeps_start_safe(self) -> None:
        game = MinesweeperGame(5, 5, 5, seed=7)
        self.assertFalse(game.initialized)

        game.reveal(2, 2)

        self.assertTrue(game.initialized)
        self.assertFalse(game.grid[2][2].has_mine)
        self.assertEqual(sum(cell.has_mine for row in game.grid for cell in row), 5)

    def test_adjacent_mine_counts_are_computed(self) -> None:
        game = MinesweeperGame(3, 3, 2, mine_positions={(0, 0), (2, 2)})
        self.assertEqual(game.grid[0][1].adjacent_mines, 1)
        self.assertEqual(game.grid[1][1].adjacent_mines, 2)
        self.assertEqual(game.grid[1][2].adjacent_mines, 1)

    def test_zero_region_reveal_expands_until_number_boundary(self) -> None:
        game = MinesweeperGame(4, 4, 2, mine_positions={(0, 0), (0, 1)})

        revealed = game.reveal(3, 3)

        self.assertEqual(len(revealed), 14)
        self.assertTrue(game.finished)
        self.assertTrue(game.won)
        self.assertTrue(game.grid[1][0].is_revealed)
        self.assertEqual(game.grid[1][0].adjacent_mines, 2)

    def test_flagging_rules_are_enforced(self) -> None:
        game = MinesweeperGame(3, 3, 2, mine_positions={(0, 0), (2, 2)})

        self.assertTrue(game.toggle_flag(0, 0))
        self.assertEqual(game.remaining_mine_estimate(), 1)
        with self.assertRaisesRegex(ValueError, "Flagged cells"):
            game.reveal(0, 0)
        self.assertFalse(game.toggle_flag(0, 0))
        game.reveal(0, 1)
        with self.assertRaisesRegex(ValueError, "cannot be flagged"):
            game.toggle_flag(0, 1)

    def test_losing_reveals_all_mines(self) -> None:
        game = MinesweeperGame(3, 3, 2, mine_positions={(0, 0), (2, 2)})

        game.reveal(0, 0)

        self.assertTrue(game.finished)
        self.assertTrue(game.lost)
        self.assertFalse(game.won)
        self.assertTrue(game.grid[2][2].is_revealed)

    def test_winning_reveals_completion_state(self) -> None:
        game = MinesweeperGame(2, 2, 1, mine_positions={(0, 0)})

        game.reveal(0, 1)
        game.reveal(1, 0)
        game.reveal(1, 1)

        self.assertTrue(game.finished)
        self.assertTrue(game.won)
        self.assertFalse(game.lost)
        self.assertEqual(game.flags_placed, 1)
        self.assertTrue(game.grid[0][0].is_flagged)

    def test_restart_clears_progress(self) -> None:
        game = MinesweeperGame(3, 3, 1, mine_positions={(0, 0)})
        game.toggle_flag(0, 0)
        game.reveal(2, 2)

        game.restart()

        self.assertTrue(game.initialized)
        self.assertFalse(game.finished)
        self.assertEqual(game.flags_placed, 0)
        self.assertFalse(game.grid[2][2].is_revealed)

    def test_preset_difficulties_and_custom_configs_are_resolved(self) -> None:
        beginner = resolve_config()
        custom = resolve_config("expert", rows=10, cols=12, mines=20)

        self.assertEqual(beginner.rows, PRESET_DIFFICULTIES["beginner"].rows)
        self.assertEqual(beginner.difficulty_name, "beginner")
        self.assertEqual((custom.rows, custom.cols, custom.mines), (10, 12, 20))
        self.assertIsNone(custom.difficulty_name)

    def test_custom_config_requires_all_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "together"):
            resolve_config(rows=10, cols=10)


if __name__ == "__main__":
    unittest.main()
