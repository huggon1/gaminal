from __future__ import annotations

import unittest

from game_2048.cli import build_parser


class Game2048CliTests(unittest.TestCase):
    def test_default_theme(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.theme, "modern")

    def test_stealth_theme(self) -> None:
        args = build_parser().parse_args(["--theme", "stealth"])
        self.assertEqual(args.theme, "stealth")


if __name__ == "__main__":
    unittest.main()
