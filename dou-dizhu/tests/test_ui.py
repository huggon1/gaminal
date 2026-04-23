from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from dou_dizhu.client import DdzClientConnection
from dou_dizhu.ui import DdzRemoteApp


class DdzUiTests(unittest.TestCase):
    def test_remote_app_keeps_player_name_without_touching_textual_app_name(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")

        self.assertEqual(app.player_name, "Alice")

    def test_on_mount_keeps_app_open_with_message_when_connect_fails(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.connection = Mock()
        app.connection.connect.side_effect = OSError("boom")
        app.refresh_view = Mock()
        app.set_interval = Mock()

        with patch("dou_dizhu.ui.ThemedApp.on_mount", autospec=True):
            app.on_mount()

        self.assertTrue(app.disconnected)
        self.assertIn("Failed to connect", app.message)
        app.refresh_view.assert_called_once()

    def test_poll_messages_marks_disconnect_without_exiting(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.connection = Mock()
        app.connection.poll_messages.return_value = [{"type": "disconnect", "message": "Connection closed."}]
        app.refresh_view = Mock()
        app.exit = Mock()

        app.poll_messages()

        self.assertTrue(app.disconnected)
        self.assertEqual(app.message, "Connection closed.")
        app.exit.assert_not_called()

    def test_render_instruction_describes_bidding_turn(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {"phase": "bidding", "you_seat": 1, "current_turn": 1, "highest_bid": 2}

        instruction = app.render_instruction()

        self.assertIn("your bid", instruction)
        self.assertIn("0/1/2/3", instruction)

    def test_render_instruction_describes_play_response(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {"phase": "playing", "you_seat": 2, "current_turn": 2, "table_seat": 1}

        instruction = app.render_instruction()

        self.assertIn("respond to the table", instruction)
        self.assertIn("Press a to pass", instruction)

    def test_render_table_shows_recent_actions(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {
            "phase": "playing",
            "you_seat": 1,
            "your_name": "Alice",
            "current_turn": 2,
            "highest_bid": 1,
            "highest_bidder": 1,
            "landlord_seat": 1,
            "bottom_cards": ["9H", "10H", "10S"],
            "table_seat": 2,
            "table_cards": ["3S"],
            "hand_counts": {1: 19, 2: 16, 3: 17},
            "seats": [
                {"seat": 1, "name": "Alice", "connected": True, "hand_count": 19, "is_landlord": True},
                {"seat": 2, "name": "Bot 2", "connected": True, "hand_count": 16, "is_landlord": False},
                {"seat": 3, "name": "Bot 3", "connected": True, "hand_count": 17, "is_landlord": False},
            ],
            "action_log": ["Seat 1 bid 1.", "Seat 1 became landlord.", "Seat 2 played 3S."],
        }

        table = app.render_table()

        self.assertIn("Recent actions:", table)
        self.assertIn("- Seat 2 played 3S.", table)

    def test_render_phase_shows_finished_round(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {"phase": "finished"}

        self.assertIn("ROUND FINISHED", app.render_phase())

    def test_render_session_shows_multi_round_scores(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {
            "you_seat": 1,
            "session": {
                "round_number": 3,
                "points": {"1": 6, "2": -3, "3": -3},
                "wins": {"1": 2, "2": 0, "3": 0},
            },
        }

        session = app.render_session()

        self.assertIn("Round:      3", session)
        self.assertIn("Your score: +6", session)
        self.assertIn("Seat pts:   S1=+6  S2=-3  S3=-3", session)

    def test_bid_actions_only_show_during_bidding(self) -> None:
        app = DdzRemoteApp("127.0.0.1", 9010, "Alice", theme="modern")
        app.room = {"phase": "bidding"}
        self.assertTrue(app.should_show_bid_actions())
        self.assertFalse(app.should_show_play_actions())

        app.room = {"phase": "playing"}
        self.assertFalse(app.should_show_bid_actions())
        self.assertTrue(app.should_show_play_actions())

    def test_client_connection_returns_socket_to_blocking_mode_after_connect(self) -> None:
        fake_socket = Mock()
        fake_socket.makefile.side_effect = [Mock(), Mock()]

        fake_thread = Mock()

        with patch("dou_dizhu.client.socket.create_connection", return_value=fake_socket), patch(
            "dou_dizhu.client.threading.Thread", return_value=fake_thread
        ):
            connection = DdzClientConnection("127.0.0.1", 9010, "Alice")
            connection.send = Mock()

            connection.connect()

        fake_socket.settimeout.assert_called_with(None)
        fake_thread.start.assert_called_once()

    def test_compose_uses_two_action_rows(self) -> None:
        self.assertIn("#action-grid", DdzRemoteApp.CSS)
        self.assertIn("layout: vertical;", DdzRemoteApp.CSS)
        self.assertIn(".action-row", DdzRemoteApp.CSS)


if __name__ == "__main__":
    unittest.main()
