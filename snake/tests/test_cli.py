from __future__ import annotations

import unittest

from snake.cli import build_parser


class SnakeCliTests(unittest.TestCase):
    def test_default_theme(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.theme, "modern")

    def test_stealth_theme(self) -> None:
        args = build_parser().parse_args(["--theme", "stealth"])
        self.assertEqual(args.theme, "stealth")


if __name__ == "__main__":
    unittest.main()
