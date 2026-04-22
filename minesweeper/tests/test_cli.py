from __future__ import annotations

import unittest

from minesweeper.cli import build_parser


class CliTests(unittest.TestCase):
    def test_minesweeper_defaults_to_beginner(self) -> None:
        args = build_parser().parse_args([])

        self.assertEqual(args.difficulty, "beginner")
        self.assertIsNone(args.rows)
        self.assertIsNone(args.cols)
        self.assertIsNone(args.mines)

    def test_minesweeper_accepts_custom_dimensions(self) -> None:
        args = build_parser().parse_args(
            ["--difficulty", "expert", "--rows", "10", "--cols", "12", "--mines", "20"]
        )

        self.assertEqual(args.difficulty, "expert")
        self.assertEqual((args.rows, args.cols, args.mines), (10, 12, 20))


if __name__ == "__main__":
    unittest.main()
