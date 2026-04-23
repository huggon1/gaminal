from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from bluff_cards.client import BluffClientConnection
from bluff_cards.ui import BluffRemoteApp


class BluffUiTests(unittest.TestCase):
    def test_remote_app_keeps_player_name_without_touching_textual_app_name(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")

        self.assertEqual(app.player_name, "Alice")

    def test_on_mount_keeps_app_open_with_message_when_connect_fails(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")
        app.connection = Mock()
        app.connection.connect.side_effect = OSError("boom")
        app.refresh_view = Mock()
        app.set_interval = Mock()

        with patch("bluff_cards.ui.ThemedApp.on_mount", autospec=True):
            app.on_mount()

        self.assertTrue(app.disconnected)
        self.assertIn("Failed to connect", app.message)
        app.refresh_view.assert_called_once()

    def test_poll_messages_marks_disconnect_without_exiting(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")
        app.connection = Mock()
        app.connection.poll_messages.return_value = [{"type": "disconnect", "message": "Connection closed."}]
        app.refresh_view = Mock()
        app.exit = Mock()

        app.poll_messages()

        self.assertTrue(app.disconnected)
        self.assertEqual(app.message, "Connection closed.")
        app.exit.assert_not_called()

    def test_render_instruction_describes_turn(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")
        app.room = {
            "phase": "in_round",
            "you_seat": 2,
            "current_turn": 2,
            "last_claim": {"seat": 1, "claimed_count": 2},
            "your_hand": [],
        }

        instruction = app.render_instruction()

        self.assertIn("Press c", instruction)
        self.assertIn("no cards left", instruction)

    def test_render_table_shows_recent_actions(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")
        app.room = {
            "phase": "in_round",
            "you_seat": 1,
            "your_name": "Alice",
            "players": 3,
            "seats": [
                {"seat": 1, "name": "Alice", "connected": True, "hand_count": 4, "lives": 3, "eliminated": False},
                {"seat": 2, "name": "Bot 2", "connected": True, "hand_count": 4, "lives": 3, "eliminated": False},
                {"seat": 3, "name": "Bot 3", "connected": True, "hand_count": 4, "lives": 3, "eliminated": False},
            ],
            "table_rank": "A",
            "current_turn": 2,
            "discard_count": 1,
            "last_claim": {"seat": 2, "claimed_count": 1, "table_rank": "A"},
            "action_log": ["Round started. Target rank is A. Seat 1 starts.", "Seat 2 claims 1 x A."],
        }

        table = app.render_table()

        self.assertIn("Recent actions:", table)
        self.assertIn("- Seat 2 claims 1 x A.", table)

    def test_reveal_animation_sets_first_stage_immediately(self) -> None:
        app = BluffRemoteApp("127.0.0.1", 9020, "Alice", theme="modern")
        app.set_timer = Mock()

        app.start_reveal_animation(
            {
                "challenger_seat": 2,
                "challenged_seat": 1,
                "actual_cards": ["A1", "JOKER1"],
                "truthful": False,
                "loser_seat": 1,
            }
        )

        self.assertIn("Challenge!", app.reveal_stage_text or "")
        self.assertEqual(app.set_timer.call_count, 3)

    def test_client_connection_returns_socket_to_blocking_mode_after_connect(self) -> None:
        fake_socket = Mock()
        fake_socket.makefile.side_effect = [Mock(), Mock()]
        fake_thread = Mock()

        with patch("bluff_cards.client.socket.create_connection", return_value=fake_socket), patch(
            "bluff_cards.client.threading.Thread", return_value=fake_thread
        ):
            connection = BluffClientConnection("127.0.0.1", 9020, "Alice")
            connection.send = Mock()

            connection.connect()

        fake_socket.settimeout.assert_called_with(None)
        fake_thread.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
