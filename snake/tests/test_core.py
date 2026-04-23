from __future__ import annotations

import unittest

from snake.core import SnakeGame


class SnakeCoreTests(unittest.TestCase):
    def test_step_moves_head(self) -> None:
        game = SnakeGame(rows=8, cols=8, seed=1)
        old_head = game.snake[-1]
        game.step()
        self.assertNotEqual(game.snake[-1], old_head)


if __name__ == "__main__":
    unittest.main()
