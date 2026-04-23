from __future__ import annotations

import unittest

from fishing.cli import build_parser


class FishingCliTests(unittest.TestCase):
    def test_default_theme_and_lanes(self) -> None:
        args = build_parser().parse_args([])

        self.assertEqual(args.theme, "modern")
        self.assertEqual(args.lanes, 1)

    def test_supports_two_lanes(self) -> None:
        args = build_parser().parse_args(["--lanes", "2"])

        self.assertEqual(args.lanes, 2)

    def test_rejects_more_than_two_lanes(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--lanes", "3"])


if __name__ == "__main__":
    unittest.main()
