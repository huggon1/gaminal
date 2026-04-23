from __future__ import annotations

import unittest

from game_2048.core import Game2048


class Game2048CoreTests(unittest.TestCase):
    def test_move_merges_once(self) -> None:
        game = Game2048(seed=1)
        game.board = [
            [2, 2, 2, 2],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        game.move("left")
        self.assertEqual(game.board[0][:2], [4, 4])


if __name__ == "__main__":
    unittest.main()
