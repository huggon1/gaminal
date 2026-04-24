from __future__ import annotations

import unittest

from snake.cli import build_parser


class SnakeCliTests(unittest.TestCase):
    def test_default_theme(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.theme, "modern")
        self.assertEqual(args.map, "classic_walls")
        self.assertEqual(args.speed, "normal")
        self.assertEqual(args.rows, 30)
        self.assertEqual(args.cols, 30)

    def test_stealth_theme(self) -> None:
        args = build_parser().parse_args(["--theme", "stealth"])
        self.assertEqual(args.theme, "stealth")

    def test_map_and_speed_options(self) -> None:
        args = build_parser().parse_args(["--map", "cross_portal", "--speed", "insane"])
        self.assertEqual(args.map, "cross_portal")
        self.assertEqual(args.speed, "insane")


if __name__ == "__main__":
    unittest.main()
