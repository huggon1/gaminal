from __future__ import annotations

import queue
import socket
import threading
import unittest

from bluff_cards.core import BluffRoundState
from bluff_cards.protocol import read_message, send_message
from bluff_cards.server import BluffServer, _Participant


def _four_player_deck() -> list[str]:
    return [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "A6",
        "K6",
        "Q6",
        "JOKER1",
        "JOKER2",
    ]


def _two_player_deck() -> list[str]:
    return ["A1", "K1", "Q1", "JOKER1", "A2", "K2", "Q2", "JOKER2", "A3", "K3", "Q3", "A4", "K4", "Q4", "A5", "K5", "Q5", "A6", "K6", "Q6"]


class BluffServerIntegrationTests(unittest.TestCase):
    def test_human_can_start_room_with_bots(self) -> None:
        server, thread = self._start_server(players=3, bot_count=2, deck_factory=_four_player_deck)
        alice = self._connect(server.port)
        try:
            welcome = self._join(alice, "Alice")
            state = self._recv_until_phase(alice, "in_round")

            self.assertEqual(welcome["seat"], 1)
            self.assertEqual(state["players"], 3)
            self.assertEqual([seat["name"] for seat in state["seats"]], ["Alice", "Bot 2", "Bot 3"])
            self.assertEqual(state["current_turn"], 1)
            self.assertIn(state["table_rank"], {"A", "K", "Q"})
        finally:
            self._cleanup(server, thread, alice)

    def test_bot_challenges_impossible_claim(self) -> None:
        server = BluffServer("127.0.0.1", 0, players=3, bot_count=2, bot_delay=0.05)
        server._events = queue.Queue()
        server._participants["human-token"] = _Participant(
            seat=1,
            name="Alice",
            session_token="human-token",
            connected_client_id="human-client",
        )
        server._ensure_bot_participants()
        server._round = BluffRoundState(
            hands={
                1: ["Q1", "K1"],
                2: ["A1", "A2", "A3", "A4", "JOKER1"],
                3: ["Q2"],
            },
            lives={1: 3, 2: 3, 3: 3},
            table_rank="A",
            current_turn=1,
        )
        server._phase = "in_round"
        server._round.play_claim(1, ["Q1", "K1"])

        server._handle_bot_turn("bot-seat-2")

        self.assertEqual(server._round.lives[1], 2)
        self.assertEqual(server._round.current_turn, 2)
        self.assertIn(server._round.table_rank, {"A", "K", "Q"})
        self.assertIn("bluffing", server._message)

    def test_truthful_claim_can_be_challenged_and_revealed(self) -> None:
        server, thread = self._start_server(players=4, deck_factory=_four_player_deck)
        clients = [self._connect(server.port) for _ in range(4)]
        try:
            for client, name in zip(clients, ("Alice", "Bob", "Cara", "Drew")):
                self._join(client, name)
            for client in clients:
                state = self._recv_until_phase(client, "in_round")
                self.assertIn(state["table_rank"], {"A", "K", "Q"})

            send_message(clients[0]["writer"], {"type": "play_claim", "actual_cards": ["A1", "JOKER1"]})
            for client in clients:
                claim_state = self._recv_until_message_contains(client, "claims 2 x")
                self.assertEqual(claim_state["last_claim"]["seat"], 1)
                self.assertEqual(claim_state["current_turn"], 2)

            send_message(clients[1]["writer"], {"type": "challenge"})
            reveal = self._recv_until_type(clients[0], "reveal_result")["result"]
            self.assertTrue(reveal["truthful"])
            self.assertEqual(reveal["actual_cards"], ["A1", "JOKER1"])
            for client in clients[1:]:
                self._recv_until_type(client, "reveal_result")

            final_states = [self._recv_until_message_contains(client, "loses 1 life") for client in clients]
            self.assertIn(final_states[0]["table_rank"], {"A", "K", "Q"})
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

            send_message(alice["writer"], {"type": "play_claim", "actual_cards": ["Q1"]})
            for client in (alice, bob, cara, drew):
                self._recv_until_message_contains(client, "claims 1 x A")

            self._close_client(bob)
            paused = self._recv_until_phase(alice, "paused_reconnect")
            self.assertEqual(paused["current_turn"], 2)
            self.assertEqual(paused["last_claim"]["seat"], 1)

            bob_reconnected = self._connect(server.port)
            send_message(bob_reconnected["writer"], {"type": "join", "name": "Bob"})
            welcome = self._recv(bob_reconnected)
            resumed_alice = self._recv_until_message_contains(alice, "reconnected")
            resumed_bob = self._recv_until_message_contains(bob_reconnected, "reconnected")

            self.assertEqual(welcome["type"], "welcome")
            self.assertEqual(welcome["seat"], bob_welcome["seat"])
            self.assertEqual(resumed_alice["phase"], "in_round")
            self.assertEqual(resumed_bob["you_seat"], 2)
            self.assertEqual(resumed_bob["current_turn"], 2)
            self.assertEqual(resumed_bob["last_claim"]["claimed_count"], 1)
            self.assertEqual(len(resumed_bob["your_hand"]), 13)
        finally:
            self._cleanup(server, thread, alice, bob, cara, drew, bob_reconnected)

    def test_duplicate_online_name_replaces_old_connection(self) -> None:
        server, thread = self._start_server(players=3, deck_factory=_four_player_deck, bot_count=2)
        alice = self._connect(server.port)
        replacement = self._connect(server.port)
        try:
            first_welcome = self._join(alice, "Alice")

            send_message(replacement["writer"], {"type": "join", "name": "Alice"})
            replacement_notice = self._recv(alice)
            replacement_welcome = self._recv(replacement)

            self.assertEqual(replacement_notice["type"], "disconnect")
            self.assertIn("replaced by a new connection", replacement_notice["message"])
            self.assertEqual(replacement_welcome["type"], "welcome")
            self.assertEqual(replacement_welcome["seat"], first_welcome["seat"])
        finally:
            self._cleanup(server, thread, alice, replacement)

    def test_room_snapshot_includes_recent_action_log(self) -> None:
        server = BluffServer("127.0.0.1", 0, players=3, bot_count=2, bot_delay=0.05)
        participant = _Participant(
            seat=1,
            name="Alice",
            session_token="human-token",
            connected_client_id="human-client",
        )
        server._participants["human-token"] = participant
        server._ensure_bot_participants()
        server._start_round()
        server._append_action_log("Seat 1 claims 1 x A.")

        snapshot = server._room_snapshot(participant)

        self.assertIn("action_log", snapshot)
        self.assertIn("Seat 1 claims 1 x A.", snapshot["action_log"])

    def test_final_truthful_claim_must_be_challenged_and_can_win(self) -> None:
        server, thread = self._start_server(players=2, deck_factory=_two_player_deck)
        alice = self._connect(server.port)
        bob = self._connect(server.port)
        try:
            self._join(alice, "Alice")
            self._join(bob, "Bob")
            for client in (alice, bob):
                self._recv_until_phase(client, "in_round")

            send_message(alice["writer"], {"type": "play_claim", "actual_cards": ["AS"]})
            for client in (alice, bob):
                self._recv_until_message_contains(client, "claims 1 x")

            send_message(bob["writer"], {"type": "challenge"})
            finished_alice = self._recv_until_phase(alice, "finished")
            finished_bob = self._recv_until_phase(bob, "finished")

            self.assertEqual(finished_alice["winner_seat"], 1)
            self.assertEqual(finished_bob["winner_seat"], 1)
        finally:
            self._cleanup(server, thread, alice, bob)

    def _start_server(self, players: int, deck_factory, bot_count: int = 0) -> tuple[BluffServer, threading.Thread]:
        server = BluffServer("127.0.0.1", 0, players=players, deck_factory=deck_factory, bot_count=bot_count, bot_delay=0.05)
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
