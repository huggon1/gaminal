from __future__ import annotations

import socket
import threading
import unittest

from bluff_cards.protocol import read_message, send_message
from bluff_cards.server import BluffServer


def _four_player_deck() -> list[str]:
    return [
        "AS",
        "BJ",
        "3S",
        "4S",
        "5S",
        "6S",
        "7S",
        "8S",
        "9S",
        "10S",
        "JS",
        "QS",
        "KS",
        "AH",
        "2S",
        "2H",
        "2C",
        "2D",
        "3H",
        "4H",
        "5H",
        "6H",
        "7H",
        "8H",
        "9H",
        "10H",
        "AD",
        "3C",
        "4C",
        "5C",
        "6C",
        "7C",
        "8C",
        "9C",
        "10C",
        "JC",
        "QC",
        "KC",
        "AC",
        "3D",
        "4D",
        "5D",
        "6D",
        "7D",
        "8D",
        "9D",
        "10D",
        "JD",
        "QD",
        "KD",
        "KH",
        "QH",
        "JH",
        "RJ",
    ]


def _two_player_deck() -> list[str]:
    return ["AS", "KH"]


class BluffServerIntegrationTests(unittest.TestCase):
    def test_truthful_claim_can_be_challenged_and_revealed(self) -> None:
        server, thread = self._start_server(players=4, deck_factory=_four_player_deck)
        clients = [self._connect(server.port) for _ in range(4)]
        try:
            for client, name in zip(clients, ("Alice", "Bob", "Cara", "Drew")):
                self._join(client, name)
            for client in clients:
                state = self._recv_until_phase(client, "in_round")
                self.assertEqual(state["target_rank"], "A")

            send_message(clients[0]["writer"], {"type": "play_claim", "actual_cards": ["AS", "BJ"], "claimed_count": 2})
            for client in clients:
                claim_state = self._recv_until_message_contains(client, "claims 2 x A")
                self.assertEqual(claim_state["last_claim"]["seat"], 1)
                self.assertEqual(claim_state["current_turn"], 2)

            send_message(clients[1]["writer"], {"type": "challenge"})
            reveal = self._recv_until_type(clients[0], "reveal_result")["result"]
            self.assertTrue(reveal["truthful"])
            self.assertEqual(reveal["actual_cards"], ["AS", "BJ"])
            for client in clients[1:]:
                self._recv_until_type(client, "reveal_result")

            final_states = [self._recv_until_message_contains(client, "loses 1 life") for client in clients]
            self.assertEqual(final_states[0]["target_rank"], "K")
            self.assertEqual(final_states[1]["lives"]["2"], 2)
            self.assertEqual(final_states[0]["current_turn"], 1)
        finally:
            self._cleanup(server, thread, *clients)

    def test_disconnect_and_reconnect_restore_pending_claim_state(self) -> None:
        server, thread = self._start_server(players=4, deck_factory=_four_player_deck)
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        cara = self._connect(server.port)
        drew = self._connect(server.port)
        bob_reconnected = None
        try:
            self._join(alice, "Alice")
            bob_welcome = self._join(bob, "Bob")
            self._join(cara, "Cara")
            self._join(drew, "Drew")
            for client in (alice, bob, cara, drew):
                self._recv_until_phase(client, "in_round")

            send_message(alice["writer"], {"type": "play_claim", "actual_cards": ["3S"], "claimed_count": 1})
            for client in (alice, bob, cara, drew):
                self._recv_until_message_contains(client, "claims 1 x A")

            self._close_client(bob)
            paused = self._recv_until_phase(alice, "paused_reconnect")
            self.assertEqual(paused["current_turn"], 2)
            self.assertEqual(paused["last_claim"]["seat"], 1)

            bob_reconnected = self._connect(server.port)
            send_message(
                bob_reconnected["writer"],
                {"type": "join", "name": "Bob", "session_token": bob_welcome["session_token"]},
            )
            welcome = self._recv(bob_reconnected)
            resumed_alice = self._recv_until_message_contains(alice, "reconnected")
            resumed_bob = self._recv_until_message_contains(bob_reconnected, "reconnected")

            self.assertEqual(welcome["type"], "welcome")
            self.assertEqual(resumed_alice["phase"], "in_round")
            self.assertEqual(resumed_bob["you_seat"], 2)
            self.assertEqual(resumed_bob["current_turn"], 2)
            self.assertEqual(resumed_bob["last_claim"]["claimed_count"], 1)
            self.assertEqual(len(resumed_bob["your_hand"]), 13)
        finally:
            self._cleanup(server, thread, alice, bob, cara, drew, bob_reconnected)

    def test_accept_wins_when_empty_hand_claim_is_not_challenged(self) -> None:
        server, thread = self._start_server(players=2, deck_factory=_two_player_deck)
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        try:
            self._join(alice, "Alice")
            self._join(bob, "Bob")
            for client in (alice, bob):
                self._recv_until_phase(client, "in_round")

            send_message(alice["writer"], {"type": "play_claim", "actual_cards": ["AS"], "claimed_count": 1})
            for client in (alice, bob):
                self._recv_until_message_contains(client, "claims 1 x A")

            send_message(bob["writer"], {"type": "accept"})
            finished_alice = self._recv_until_phase(alice, "finished")
            finished_bob = self._recv_until_phase(bob, "finished")

            self.assertEqual(finished_alice["winner_seat"], 1)
            self.assertEqual(finished_bob["winner_seat"], 1)
        finally:
            self._cleanup(server, thread, alice, bob)

    def _start_server(self, players: int, deck_factory) -> tuple[BluffServer, threading.Thread]:
        server = BluffServer("127.0.0.1", 0, players=players, deck_factory=deck_factory)
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

    def _recv_until_type(self, client: dict[str, object], payload_type: str) -> dict[str, object]:
        while True:
            payload = self._recv(client)
            if payload["type"] == payload_type:
                return payload

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

    def _cleanup(self, server: BluffServer, thread: threading.Thread, *clients: dict[str, object] | None) -> None:
        for client in clients:
            self._close_client(client)
        server.shutdown()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "Server thread did not terminate.")


if __name__ == "__main__":
    unittest.main()
