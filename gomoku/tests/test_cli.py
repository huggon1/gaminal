from __future__ import annotations

import unittest

from gomoku.cli import build_parser


class GomokuCliTests(unittest.TestCase):
    def test_local_supports_theme(self) -> None:
        args = build_parser().parse_args(["local", "--theme", "stealth"])

        self.assertEqual(args.command, "local")
        self.assertEqual(args.theme, "stealth")

    def test_client_supports_theme(self) -> None:
        args = build_parser().parse_args(
            ["client", "--host", "127.0.0.1", "--port", "9000", "--name", "Alice", "--theme", "modern"]
        )

        self.assertEqual(args.command, "client")
        self.assertEqual(args.theme, "modern")


if __name__ == "__main__":
    unittest.main()
