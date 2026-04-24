from __future__ import annotations

import unittest

from snake.core import MAP_PRESETS, SPEED_PRESETS, SnakeGame


class SnakeCoreTests(unittest.TestCase):
    def test_step_moves_head(self) -> None:
        game = SnakeGame(rows=8, cols=8, seed=1)
        old_head = game.snake[-1]
        game.step()
        self.assertNotEqual(game.snake[-1], old_head)

    def test_classic_map_hits_outer_wall(self) -> None:
        game = SnakeGame(rows=6, cols=6, map_id="classic_walls")
        game.snake = [(0, 2), (0, 1), (0, 0)]
        game.direction = "left"
        game.next_direction = "left"

        game.step()

        self.assertTrue(game.game_over)

    def test_wrap_map_crosses_outer_edge(self) -> None:
        game = SnakeGame(rows=6, cols=6, map_id="open_wrap")
        game.snake = [(2, 2), (2, 1), (2, 0)]
        game.direction = "left"
        game.next_direction = "left"
        game.food = (4, 4)

        game.step()

        self.assertFalse(game.game_over)
        self.assertEqual(game.snake[-1], (2, 5))

    def test_obstacle_collision_ends_game(self) -> None:
        game = SnakeGame(rows=12, cols=12, map_id="center_blocks")
        target = next(cell for cell in game.obstacles if cell[0] > 0 and cell[1] >= 2)
        r, c = target
        game.snake = [(r - 1, c - 2), (r - 1, c - 1), (r - 1, c)]
        game.direction = "down"
        game.next_direction = "down"
        game.food = (0, 0)

        game.step()

        self.assertTrue(game.game_over)

    def test_speed_controls_fruit_score(self) -> None:
        game = SnakeGame(rows=8, cols=8, speed_id="fast")
        head_r, head_c = game.snake[-1]
        game.food = (head_r, head_c + 1)

        game.step()

        self.assertEqual(game.score, SPEED_PRESETS["fast"].fruit_score)

    def test_food_never_spawns_on_obstacles(self) -> None:
        game = SnakeGame(rows=12, cols=12, map_id="gate_maze", seed=3)

        self.assertNotIn(game.food, game.obstacles)
        self.assertNotIn(game.food, game.snake)

    def test_all_maps_create_safe_start_on_default_board(self) -> None:
        for map_id in MAP_PRESETS:
            with self.subTest(map_id=map_id):
                game = SnakeGame(rows=16, cols=24, map_id=map_id)
                self.assertFalse(set(game.snake) & game.obstacles)
                self.assertNotIn(game.food, game.obstacles)


if __name__ == "__main__":
    unittest.main()
