from __future__ import annotations

import unittest

from bluff_cards.cli import build_parser


class BluffCliTests(unittest.TestCase):
    def test_server_supports_bots(self) -> None:
        args = build_parser().parse_args(["server", "--players", "4", "--bots", "2"])

        self.assertEqual(args.command, "server")
        self.assertEqual(args.bots, 2)

    def test_client_supports_theme(self) -> None:
        args = build_parser().parse_args(
            ["client", "--host", "127.0.0.1", "--port", "9020", "--name", "Alice", "--theme", "stealth"]
        )

        self.assertEqual(args.command, "client")
        self.assertEqual(args.theme, "stealth")
        self.assertFalse(hasattr(args, "session_token"))


if __name__ == "__main__":
    unittest.main()
