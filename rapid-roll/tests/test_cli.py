from __future__ import annotations

import unittest

from rapid_roll.cli import build_parser


class RapidRollCliTests(unittest.TestCase):
    def test_parser_accepts_board_size_and_theme(self) -> None:
        args = build_parser().parse_args(["--rows", "28", "--cols", "26", "--theme", "stealth"])

        self.assertEqual(args.rows, 28)
        self.assertEqual(args.cols, 26)
        self.assertEqual(args.theme, "stealth")


if __name__ == "__main__":
    unittest.main()
