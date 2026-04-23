from __future__ import annotations

import unittest

from dou_dizhu.cli import build_parser


class DdzCliTests(unittest.TestCase):
    def test_client_supports_theme(self) -> None:
        args = build_parser().parse_args(
            ["client", "--host", "127.0.0.1", "--port", "9010", "--name", "Alice", "--theme", "stealth"]
        )

        self.assertEqual(args.command, "client")
        self.assertEqual(args.theme, "stealth")
        self.assertFalse(hasattr(args, "session_token"))

    def test_server_supports_bot_count(self) -> None:
        args = build_parser().parse_args(["server", "--host", "127.0.0.1", "--port", "9010", "--bots", "2"])

        self.assertEqual(args.command, "server")
        self.assertEqual(args.bots, 2)


if __name__ == "__main__":
    unittest.main()
