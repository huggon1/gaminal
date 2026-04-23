from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from gomoku.cli import build_parser, main


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

    def test_server_returns_130_on_keyboard_interrupt(self) -> None:
        server = MagicMock()
        server.serve_game.side_effect = KeyboardInterrupt
        with patch("gomoku.cli.GomokuServer", return_value=server):
            result = main(["server"])

        self.assertEqual(result, 130)
        server.shutdown.assert_called_once()

    def test_client_returns_130_on_keyboard_interrupt(self) -> None:
        with patch("gomoku.ui.curses_app.run_remote_client", side_effect=KeyboardInterrupt):
            result = main(["client", "--host", "127.0.0.1", "--port", "9000", "--name", "Alice"])

        self.assertEqual(result, 130)


if __name__ == "__main__":
    unittest.main()
