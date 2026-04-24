from __future__ import annotations

import unittest

from rapid_roll.core import BonusItem, Platform, RapidRollGame, SLOW_DURATION


class RapidRollCoreTests(unittest.TestCase):
    def test_initial_state_has_safe_ball_and_platforms(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)

        self.assertGreaterEqual(game.lives, 1)
        self.assertGreater(len(game.platforms), 1)
        self.assertFalse(game.game_over)
        self.assertTrue(0 <= game.ball_col < game.cols)
        self.assertTrue(any(platform.row > game.ball_row for platform in game.platforms))

    def test_movement_stays_inside_board(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)

        for _ in range(50):
            game.move_left()
        self.assertEqual(game.ball_col, 0.0)

        for _ in range(50):
            game.move_right()
        self.assertEqual(game.ball_col, float(game.cols - 1))

    def test_landing_scores_and_resets_fall_speed(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)
        game.platforms = [Platform(row=10.0, col=4, width=8)]
        game.ball_row = 8.8
        game.ball_col = 7.0
        game.ball_vy = 0.3
        score = game.score

        game.step()

        self.assertEqual(game.landings, 1)
        self.assertGreater(game.score, score)
        self.assertEqual(game.ball_vy, 0.0)
        self.assertAlmostEqual(game.ball_row, game.platforms[0].row - 1.0)

    def test_platform_carries_supported_ball_upward(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)
        platform = Platform(row=10.0, col=4, width=8)
        game.platforms = [platform]
        game.ball_row = platform.row - 1.0
        game.ball_col = 7.0
        game.ball_vy = 0.0
        game._grounded_platform = platform

        game.step()

        self.assertEqual(game.ball_vy, 0.0)
        self.assertAlmostEqual(game.ball_row, platform.row - 1.0)

    def test_hazard_costs_life_and_game_over_at_zero(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)
        game.lives = 1
        game.ball_row = float(game.rows - 1)

        game.step()

        self.assertTrue(game.game_over)
        self.assertEqual(game.lives, 0)

    def test_items_apply_effects(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)

        game._activate_item("coin")
        self.assertEqual(game.score, 50)

        game.lives = 3
        game._activate_item("heart")
        self.assertEqual(game.lives, 4)

        game._activate_item("slow")
        self.assertEqual(game.active_effects["slow"], SLOW_DURATION)

    def test_collect_item_removes_it(self) -> None:
        game = RapidRollGame(rows=18, cols=16, seed=1)
        game.ball_row = 7.0
        game.ball_col = 5.0
        game.items = [BonusItem(kind="coin", row=7.0, col=5)]

        game._collect_items()

        self.assertEqual(game.items, [])
        self.assertEqual(game.score, 50)

    def test_seeded_generation_is_deterministic(self) -> None:
        left = RapidRollGame(rows=18, cols=16, seed=7)
        right = RapidRollGame(rows=18, cols=16, seed=7)

        for _ in range(90):
            left.step()
            right.step()

        self.assertEqual([(p.row, p.col, p.width) for p in left.platforms], [(p.row, p.col, p.width) for p in right.platforms])
        self.assertEqual([(i.kind, i.row, i.col) for i in left.items], [(i.kind, i.row, i.col) for i in right.items])


if __name__ == "__main__":
    unittest.main()
