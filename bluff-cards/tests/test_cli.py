from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from bluff_cards.cli import build_parser, main


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

    def test_server_returns_130_on_keyboard_interrupt(self) -> None:
        server = MagicMock()
        server.serve_game.side_effect = KeyboardInterrupt
        with patch("bluff_cards.cli.BluffServer", return_value=server):
            result = main(["server"])

        self.assertEqual(result, 130)
        server.shutdown.assert_called_once()

    def test_client_returns_130_on_keyboard_interrupt(self) -> None:
        with patch("bluff_cards.ui.run_bluff_remote_client", side_effect=KeyboardInterrupt):
            result = main(["client", "--host", "127.0.0.1", "--port", "9020", "--name", "Alice"])

        self.assertEqual(result, 130)


if __name__ == "__main__":
    unittest.main()
