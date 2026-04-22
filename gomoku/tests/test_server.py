from __future__ import annotations

import socket
import threading
import unittest

from gomoku.net.protocol import read_message, send_message
from gomoku.net.server import GomokuServer


class ServerIntegrationTests(unittest.TestCase):
    def test_multi_round_scoreboard_ready_flow_and_color_rotation(self) -> None:
        server, thread = self._start_server()
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        try:
            alice_welcome = self._join(alice, "Alice")
            self._recv_room_state(alice)
            bob_welcome = self._join(bob, "Bob")
            alice_room = self._recv_room_state(alice)
            bob_room = self._recv_room_state(bob)

            self.assertEqual(alice_room["phase"], "waiting_ready")
            self.assertEqual(bob_room["phase"], "waiting_ready")
            self.assertEqual(alice_welcome["player"], "black")
            self.assertEqual(bob_welcome["player"], "white")

            alice_round, bob_round = self._ready_both(alice, bob)

            self.assertEqual(alice_round["phase"], "in_game")
            self.assertEqual(alice_round["round_number"], 1)
            self.assertEqual(alice_round["you_color"], "black")
            self.assertEqual(bob_round["you_color"], "white")

            sequence = [
                (alice, bob, (7, 0)),
                (bob, alice, (8, 0)),
                (alice, bob, (7, 1)),
                (bob, alice, (8, 1)),
                (alice, bob, (7, 2)),
                (bob, alice, (8, 2)),
                (alice, bob, (7, 3)),
                (bob, alice, (8, 3)),
            ]
            for current_client, other_client, (row, col) in sequence:
                send_message(current_client["writer"], {"type": "move", "row": row, "col": col})
                self._recv_room_state(current_client)
                self._recv_room_state(other_client)

            send_message(alice["writer"], {"type": "move", "row": 7, "col": 4})
            alice_finished = self._recv_room_state(alice)
            bob_finished = self._recv_room_state(bob)
            alice_between = self._recv_room_state(alice)
            bob_between = self._recv_room_state(bob)

            self.assertTrue(alice_finished["board_state"]["finished"])
            self.assertEqual(bob_finished["board_state"]["winner"], "black")
            self.assertEqual(alice_between["phase"], "waiting_ready")
            self.assertEqual(alice_between["scoreboard"]["black_wins"], 1)
            self.assertEqual(alice_between["you_color"], "white")
            self.assertEqual(bob_between["you_color"], "black")

            alice_second_round, bob_second_round = self._ready_both(alice, bob)

            self.assertEqual(alice_second_round["round_number"], 2)
            self.assertEqual(alice_second_round["you_color"], "white")
            self.assertEqual(bob_second_round["you_color"], "black")

            send_message(bob["writer"], {"type": "resign"})
            alice_after_resign = self._recv_room_state(alice)
            bob_after_resign = self._recv_room_state(bob)

            self.assertEqual(alice_after_resign["phase"], "waiting_ready")
            self.assertEqual(alice_after_resign["scoreboard"]["white_wins"], 1)
            self.assertEqual(bob_after_resign["scoreboard"]["black_wins"], 1)

            send_message(alice["writer"], {"type": "leave"})
            disconnect_alice = self._recv(alice)
            disconnect_bob = self._recv(bob)
            self.assertEqual(disconnect_alice["type"], "disconnect")
            self.assertEqual(disconnect_bob["type"], "disconnect")
        finally:
            self._cleanup(server, thread, alice, bob)

    def test_disconnect_and_reconnect_restores_the_same_player_slot(self) -> None:
        server, thread = self._start_server()
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        restored_bob = None
        intruder = None
        try:
            self._join(alice, "Alice")
            self._recv_room_state(alice)
            bob_welcome = self._join(bob, "Bob")
            self._recv_room_state(alice)
            self._recv_room_state(bob)
            alice_round, _ = self._ready_both(alice, bob)

            send_message(alice["writer"], {"type": "move", "row": 7, "col": 7})
            alice_after_move = self._recv_room_state(alice)
            bob_after_move = self._recv_room_state(bob)
            self.assertEqual(alice_after_move["board_state"]["board"][7][7], "B")
            self.assertEqual(bob_after_move["board_state"]["current_player"], "white")
            self.assertEqual(alice_round["round_number"], 1)

            bob_token = bob_welcome["session_token"]
            self._close_client(bob)
            paused = self._recv_room_state(alice)
            self.assertEqual(paused["phase"], "paused_reconnect")
            self.assertFalse(self._seat_by_color(paused, "white")["connected"])

            intruder = self._connect(server.port)
            send_message(intruder["writer"], {"type": "join", "name": "Mallory", "session_token": "bad-token"})
            self.assertEqual(self._recv(intruder)["type"], "error")

            restored_bob = self._connect(server.port)
            send_message(restored_bob["writer"], {"type": "join", "name": "Bob", "session_token": bob_token})
            restored_welcome = self._recv(restored_bob)
            alice_resumed = self._recv_room_state(alice)
            bob_resumed = self._recv_room_state(restored_bob)

            self.assertEqual(restored_welcome["type"], "welcome")
            self.assertEqual(alice_resumed["phase"], "in_game")
            self.assertEqual(bob_resumed["you_color"], "white")
            self.assertEqual(bob_resumed["board_state"]["board"][7][7], "B")

            send_message(restored_bob["writer"], {"type": "move", "row": 8, "col": 7})
            alice_after_reconnect_move = self._recv_room_state(alice)
            bob_after_reconnect_move = self._recv_room_state(restored_bob)

            self.assertEqual(alice_after_reconnect_move["board_state"]["board"][8][7], "W")
            self.assertEqual(bob_after_reconnect_move["board_state"]["current_player"], "black")

            send_message(alice["writer"], {"type": "leave"})
            self.assertEqual(self._recv(alice)["type"], "disconnect")
            self.assertEqual(self._recv(restored_bob)["type"], "disconnect")
        finally:
            self._cleanup(server, thread, alice, bob, restored_bob, intruder)

    def test_online_player_can_close_room_while_waiting_for_reconnect(self) -> None:
        server, thread = self._start_server()
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        try:
            self._join(alice, "Alice")
            self._recv_room_state(alice)
            self._join(bob, "Bob")
            self._recv_room_state(alice)
            self._recv_room_state(bob)
            self._ready_both(alice, bob)

            self._close_client(bob)
            paused = self._recv_room_state(alice)
            self.assertEqual(paused["phase"], "paused_reconnect")

            send_message(alice["writer"], {"type": "close_room"})
            disconnect = self._recv(alice)
            self.assertEqual(disconnect["type"], "disconnect")
        finally:
            self._cleanup(server, thread, alice, bob)

    def _start_server(self) -> tuple[GomokuServer, threading.Thread]:
        server = GomokuServer("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_game, daemon=True)
        thread.start()
        ready = server.ready_event.wait(timeout=2)
        self.assertTrue(ready, "Server did not start listening in time.")
        return server, thread

    def _connect(self, port: int) -> dict[str, object]:
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        sock.settimeout(2)
        return {
            "socket": sock,
            "reader": sock.makefile("r", encoding="utf-8", newline="\n"),
            "writer": sock.makefile("w", encoding="utf-8", newline="\n"),
        }

    def _join(self, client: dict[str, object], name: str) -> dict[str, object]:
        send_message(client["writer"], {"type": "join", "name": name})
        payload = self._recv(client)
        self.assertEqual(payload["type"], "welcome")
        return payload

    def _ready_both(self, alice: dict[str, object], bob: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        send_message(alice["writer"], {"type": "ready"})
        self._recv_room_state(alice)
        self._recv_room_state(bob)
        send_message(bob["writer"], {"type": "ready"})
        return self._recv_room_state(alice), self._recv_room_state(bob)

    def _recv_room_state(self, client: dict[str, object]) -> dict[str, object]:
        payload = self._recv(client)
        self.assertEqual(payload["type"], "room_state")
        return payload["room"]

    def _recv(self, client: dict[str, object]) -> dict[str, object]:
        payload = read_message(client["reader"])
        self.assertIsNotNone(payload)
        return payload

    def _seat_by_color(self, room: dict[str, object], color: str) -> dict[str, object]:
        for seat in room["seats"]:
            if seat["player_color"] == color:
                return seat
        self.fail(f"Seat {color} not found.")

    def _close_client(self, client: dict[str, object] | None) -> None:
        if client is None:
            return
        for key in ("writer", "reader", "socket"):
            handle = client.get(key)
            if handle is None:
                continue
            try:
                handle.close()
            except OSError:
                pass
            client[key] = None

    def _cleanup(
        self,
        server: GomokuServer,
        thread: threading.Thread,
        *clients: dict[str, object] | None,
    ) -> None:
        for client in clients:
            self._close_client(client)
        server.shutdown()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "Server thread did not terminate.")


if __name__ == "__main__":
    unittest.main()
