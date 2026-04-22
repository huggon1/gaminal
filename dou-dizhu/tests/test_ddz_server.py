from __future__ import annotations

import socket
import threading
import unittest

from dou_dizhu.protocol import read_message, send_message
from dou_dizhu.server import DdzServer


def _fixed_deck() -> list[str]:
    return [
        "3S",
        "3H",
        "3C",
        "4S",
        "4H",
        "4C",
        "5S",
        "5H",
        "5C",
        "6S",
        "6H",
        "6C",
        "7S",
        "7H",
        "8S",
        "8H",
        "9S",
        "3D",
        "4D",
        "5D",
        "6D",
        "7C",
        "7D",
        "8C",
        "8D",
        "9C",
        "9D",
        "10C",
        "10D",
        "JS",
        "JH",
        "JC",
        "JD",
        "QS",
        "QH",
        "QC",
        "QD",
        "KS",
        "KH",
        "KC",
        "KD",
        "AS",
        "AH",
        "AC",
        "AD",
        "2S",
        "2H",
        "2C",
        "2D",
        "BJ",
        "RJ",
        "9H",
        "10S",
        "10H",
    ]


class DdzServerIntegrationTests(unittest.TestCase):
    def test_full_round_can_finish_after_bidding(self) -> None:
        server, thread = self._start_server()
        clients = [self._connect(server.port) for _ in range(3)]
        try:
            welcomes = [self._join(client, name) for client, name in zip(clients, ("Alice", "Bob", "Cara"))]
            for client in clients:
                bidding_state = self._recv_until_phase(client, "bidding")
                self.assertEqual(bidding_state["phase"], "bidding")

            self.assertEqual(welcomes[0]["seat"], 1)
            send_message(clients[0]["writer"], {"type": "bid", "amount": 3})

            playing_states = [self._recv_until_phase(client, "playing") for client in clients]
            self.assertEqual(playing_states[0]["landlord_seat"], 1)
            self.assertEqual(len(playing_states[0]["your_hand"]), 20)
            self.assertEqual(playing_states[0]["bottom_cards"], ["9H", "10H", "10S"])

            winning_cards = list(playing_states[0]["your_hand"])
            send_message(clients[0]["writer"], {"type": "play", "cards": winning_cards})

            finished_states = [self._recv_until_phase(client, "finished") for client in clients]
            for state in finished_states:
                self.assertEqual(state["winner_seat"], 1)
                self.assertEqual(state["winner_side"], "landlord")
        finally:
            self._cleanup(server, thread, *clients)

    def test_reconnect_restores_private_hand_and_turn_state(self) -> None:
        server, thread = self._start_server()
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        cara = self._connect(server.port)
        bob_reconnected = None
        try:
            self._join(alice, "Alice")
            bob_welcome = self._join(bob, "Bob")
            self._join(cara, "Cara")
            for client in (alice, bob, cara):
                self._recv_until_phase(client, "bidding")

            send_message(alice["writer"], {"type": "bid", "amount": 1})
            for client in (alice, bob, cara):
                self._recv_until_message_contains(client, "bid 1")

            self._close_client(bob)
            paused = self._recv_until_phase(alice, "paused_reconnect")
            self.assertEqual(paused["phase"], "paused_reconnect")

            bob_reconnected = self._connect(server.port)
            send_message(
                bob_reconnected["writer"],
                {"type": "join", "name": "Bob", "session_token": bob_welcome["session_token"]},
            )
            welcome = self._recv(bob_reconnected)
            resumed_alice = self._recv_until_message_contains(alice, "reconnected")
            resumed_bob = self._recv_until_message_contains(bob_reconnected, "reconnected")

            self.assertEqual(welcome["type"], "welcome")
            self.assertEqual(resumed_alice["phase"], "bidding")
            self.assertEqual(resumed_bob["you_seat"], 2)
            self.assertEqual(len(resumed_bob["your_hand"]), 17)
            self.assertEqual(resumed_bob["current_turn"], 2)
        finally:
            self._cleanup(server, thread, alice, bob, cara, bob_reconnected)

    def _start_server(self) -> tuple[DdzServer, threading.Thread]:
        server = DdzServer("127.0.0.1", 0, deck_factory=_fixed_deck)
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
        welcome = self._recv(client)
        self.assertEqual(welcome["type"], "welcome")
        return welcome

    def _recv(self, client: dict[str, object]) -> dict[str, object]:
        payload = read_message(client["reader"])
        self.assertIsNotNone(payload)
        return payload

    def _recv_until_phase(self, client: dict[str, object], phase: str) -> dict[str, object]:
        while True:
            payload = self._recv(client)
            if payload["type"] == "room_state" and payload["room"]["phase"] == phase:
                return payload["room"]

    def _recv_until_message_contains(self, client: dict[str, object], text: str) -> dict[str, object]:
        while True:
            payload = self._recv(client)
            if payload["type"] == "room_state" and text in str(payload["room"].get("message", "")):
                return payload["room"]

    def _close_client(self, client: dict[str, object] | None) -> None:
        if client is None:
            return
        for key in ("writer", "reader", "socket"):
            handle = client.get(key)
            if handle is None:
                continue
            try:
                if key == "socket":
                    handle.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                handle.close()
            except OSError:
                pass
            client[key] = None

    def _cleanup(self, server: DdzServer, thread: threading.Thread, *clients: dict[str, object] | None) -> None:
        for client in clients:
            self._close_client(client)
        server.shutdown()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "Server thread did not terminate.")


if __name__ == "__main__":
    unittest.main()
