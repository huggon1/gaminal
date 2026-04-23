from __future__ import annotations

import unittest

from reversi.core import GameState, Player
from reversi.ui.curses_app import LocalGameApp, RemoteGameApp


class ReversiUiTests(unittest.TestCase):
    def test_local_phase_reports_current_player(self) -> None:
        app = LocalGameApp(theme="modern")

        self.assertIn("BLACK TO MOVE", app.render_phase())
        self.assertIn("dotted moves", app.render_next_action())

    def test_remote_next_action_reports_turn_owner(self) -> None:
        app = RemoteGameApp("127.0.0.1", 9001, "Alice", theme="modern")
        app.room = {"phase": "in_game", "round_number": 1, "scoreboard": {"black_wins": 0, "white_wins": 0, "draws": 0}, "seats": []}
        app.local_player = Player.BLACK
        app.state = GameState(current_player=Player.WHITE)

        self.assertIn("Waiting for White", app.render_next_action())
