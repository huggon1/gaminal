from __future__ import annotations

import unittest

from reversi.cli import build_parser


class ReversiCliTests(unittest.TestCase):
    def test_local_supports_theme(self) -> None:
        args = build_parser().parse_args(["local", "--theme", "stealth"])

        self.assertEqual(args.command, "local")
        self.assertEqual(args.theme, "stealth")

    def test_client_supports_session_token_and_theme(self) -> None:
        args = build_parser().parse_args(
            [
                "client",
                "--host",
                "127.0.0.1",
                "--port",
                "9001",
                "--name",
                "Alice",
                "--session-token",
                "token-123",
                "--theme",
                "modern",
            ]
        )

        self.assertEqual(args.command, "client")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9001)
        self.assertEqual(args.name, "Alice")
        self.assertEqual(args.session_token, "token-123")
        self.assertEqual(args.theme, "modern")

    def test_server_defaults_to_reversi_port(self) -> None:
        args = build_parser().parse_args(["server"])

        self.assertEqual(args.command, "server")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9001)


if __name__ == "__main__":
    unittest.main()
