from __future__ import annotations

import json
import queue
import secrets
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, TextIO

from bluff_cards.core import DEFAULT_LIVES, BluffRevealResult, BluffRoundState, create_shuffled_deck
from bluff_cards.protocol import send_message


@dataclass
class _ConnectedClient:
    client_id: str
    socket: socket.socket
    reader: TextIO
    writer: TextIO
    address: tuple[str, int]
    participant_token: str | None = None
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, message: dict[str, Any]) -> None:
        with self.send_lock:
            send_message(self.writer, message)

    def close(self) -> None:
        try:
            self.writer.close()
        except OSError:
            pass
        try:
            self.reader.close()
        except OSError:
            pass
        try:
            self.socket.close()
        except OSError:
            pass


@dataclass
class _Participant:
    seat: int
    name: str
    session_token: str
    connected_client_id: str | None = None

    @property
    def connected(self) -> bool:
        return self.connected_client_id is not None


class BluffServer:
    def __init__(
        self,
        host: str,
        port: int,
        players: int = 4,
        lives: int = DEFAULT_LIVES,
        deck_factory: Callable[[], list[str]] | None = None,
    ) -> None:
        if players < 2 or players > 4:
            raise ValueError("Player count must be between 2 and 4.")
        self.host = host
        self.port = port
        self.player_capacity = players
        self.lives = lives
        self.ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._listener: socket.socket | None = None
        self._events: queue.Queue[tuple[str, str | None, Any]] | None = None
        self._connections: dict[str, _ConnectedClient] = {}
        self._participants: dict[str, _Participant] = {}
        self._round: BluffRoundState | None = None
        self._phase = "waiting_for_players"
        self._message = f"Waiting for {self.player_capacity} players."
        self._resume_phase: str | None = None
        self._last_reveal: BluffRevealResult | None = None
        self._deck_factory = deck_factory or create_shuffled_deck

    def shutdown(self) -> None:
        self._shutdown_event.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
        if self._events is not None:
            self._events.put(("shutdown", None, None))

    def serve_game(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        events: queue.Queue[tuple[str, str | None, Any]] = queue.Queue()
        self._listener = listener
        self._events = events
        try:
            listener.bind((self.host, self.port))
            self.port = listener.getsockname()[1]
            listener.listen()
            self.ready_event.set()
            threading.Thread(target=self._accept_loop, args=(listener, events), daemon=True).start()

            while not self._shutdown_event.is_set():
                event_type, client_id, payload = events.get()

                if event_type == "shutdown":
                    self._close_room("Server shutting down.")
                    break
                if event_type == "incoming":
                    self._register_connection(payload)
                    continue
                if client_id is None:
                    continue
                if event_type == "disconnect":
                    self._handle_disconnect(client_id)
                    if self._phase == "closed":
                        break
                    continue
                if event_type == "invalid_json":
                    client = self._connections.get(client_id)
                    if client is not None:
                        self._send_error(client, "Invalid JSON message.")
                    continue
                if event_type == "message":
                    should_stop = self._handle_message(client_id, payload)
                    if should_stop:
                        break
        finally:
            self._shutdown_event.set()
            for client in list(self._connections.values()):
                client.close()
            try:
                listener.close()
            except OSError:
                pass

    def _accept_loop(self, listener: socket.socket, events: queue.Queue[tuple[str, str | None, Any]]) -> None:
        while not self._shutdown_event.is_set():
            try:
                client_socket, address = listener.accept()
            except OSError:
                return
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            events.put(("incoming", None, (client_socket, address)))

    def _register_connection(self, payload: Any) -> None:
        client_socket, address = payload
        client_id = secrets.token_hex(8)
        client = _ConnectedClient(
            client_id=client_id,
            socket=client_socket,
            reader=client_socket.makefile("r", encoding="utf-8", newline="\n"),
            writer=client_socket.makefile("w", encoding="utf-8", newline="\n"),
            address=address,
        )
        self._connections[client_id] = client
        threading.Thread(target=self._reader_loop, args=(client,), daemon=True).start()

    def _reader_loop(self, client: _ConnectedClient) -> None:
        assert self._events is not None
        while not self._shutdown_event.is_set():
            try:
                line = client.reader.readline()
            except OSError:
                self._events.put(("disconnect", client.client_id, None))
                return
            if not line:
                self._events.put(("disconnect", client.client_id, None))
                return
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._events.put(("invalid_json", client.client_id, None))
                continue
            self._events.put(("message", client.client_id, payload))

    def _handle_message(self, client_id: str, payload: Any) -> bool:
        client = self._connections.get(client_id)
        if client is None:
            return False
        if not isinstance(payload, dict):
            self._send_error(client, "Message payload must be an object.")
            return False
        if client.participant_token is None:
            return self._handle_join(client, payload)

        message_type = payload.get("type")
        if self._phase == "paused_reconnect" and message_type != "leave":
            self._send_error(client, "Room is waiting for a reconnect.")
            return False

        if message_type == "play_claim":
            return self._handle_play_claim(client, payload)
        if message_type == "challenge":
            return self._handle_challenge(client)
        if message_type == "accept":
            return self._handle_accept(client)
        if message_type == "leave":
            return self._handle_leave(client)

        self._send_error(client, "Unsupported message type.")
        return False

    def _handle_join(self, client: _ConnectedClient, payload: dict[str, Any]) -> bool:
        if payload.get("type") != "join":
            self._send_error(client, "First message must be a join request.")
            return False
        name = payload.get("name")
        session_token = payload.get("session_token")
        if not isinstance(name, str) or not name.strip():
            self._send_error(client, "Join request must include a non-empty name.")
            return False

        if session_token is None:
            if len(self._participants) >= self.player_capacity:
                self._send_error(client, "Room is full.")
                return False
            participant = _Participant(
                seat=len(self._participants) + 1,
                name=name.strip(),
                session_token=secrets.token_urlsafe(16),
                connected_client_id=client.client_id,
            )
            self._participants[participant.session_token] = participant
            client.participant_token = participant.session_token
            self._message = f"{participant.name} joined seat {participant.seat}."
        else:
            if not isinstance(session_token, str):
                self._send_error(client, "Session token must be a string.")
                return False
            participant = self._participants.get(session_token)
            if participant is None:
                self._send_error(client, "Unknown session token.")
                return False
            if participant.connected:
                self._send_error(client, "That player is already connected.")
                return False
            participant.connected_client_id = client.client_id
            client.participant_token = session_token
            self._message = f"{participant.name} reconnected."
            if self._phase == "paused_reconnect" and self._all_connected():
                self._phase = self._resume_phase or self._phase_before_round()
                self._message = f"{participant.name} reconnected. Round resumed."

        self._send_welcome(client)
        self._send_room_state(participant)
        self._broadcast_room_state(exclude_token=participant.session_token)

        if len(self._participants) == self.player_capacity and self._round is None and self._all_connected():
            self._start_round()
        return False

    def _start_round(self) -> None:
        self._round = BluffRoundState.from_deck(self._deck_factory(), self.player_capacity, self.lives)
        self._phase = "in_round"
        self._message = f"All players connected. Target is {self._round.target_rank}. Seat 1 starts."
        self._broadcast_room_state()

    def _handle_play_claim(self, client: _ConnectedClient, payload: dict[str, Any]) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        actual_cards = payload.get("actual_cards")
        claimed_count = payload.get("claimed_count")
        if not isinstance(actual_cards, list) or not all(isinstance(card, str) for card in actual_cards):
            self._send_error(client, "Play must include a list of actual cards.")
            return False
        if not isinstance(claimed_count, int):
            self._send_error(client, "Claimed count must be an integer.")
            return False
        try:
            claim = self._round.play_claim(participant.seat, list(actual_cards), claimed_count)
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False

        self._phase = self._round.phase
        self._last_reveal = None
        self._message = f"Seat {participant.seat} claims {claim.claimed_count} x {claim.target_rank}."
        self._broadcast_room_state()
        return False

    def _handle_challenge(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        try:
            result = self._round.challenge(participant.seat)
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False

        self._last_reveal = result
        self._phase = self._round.phase
        self._message = self._challenge_message(result)
        self._broadcast_reveal_result(result)
        self._broadcast_room_state()
        return False

    def _handle_accept(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        try:
            winner = self._round.accept(participant.seat)
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False

        self._phase = self._round.phase
        self._last_reveal = None
        self._message = f"Seat {participant.seat} accepted the empty-hand claim. Seat {winner} wins."
        self._broadcast_room_state()
        return False

    def _handle_leave(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        self._close_room(f"{participant.name} left the room.")
        return True

    def _handle_disconnect(self, client_id: str) -> None:
        client = self._connections.pop(client_id, None)
        if client is None:
            return
        participant = self._participant_for_client(client)
        if participant is not None:
            participant.connected_client_id = None
            client.participant_token = None
            if self._phase != "closed":
                self._resume_phase = self._phase_before_round()
                self._phase = "paused_reconnect"
                self._message = f"{participant.name} disconnected. Waiting for reconnect."
                self._broadcast_room_state()
        client.close()

    def _phase_before_round(self) -> str:
        if self._round is None:
            return "waiting_for_players"
        return self._round.phase

    def _all_connected(self) -> bool:
        return len(self._participants) == self.player_capacity and all(participant.connected for participant in self._participants.values())

    def _participant_for_client(self, client: _ConnectedClient) -> _Participant | None:
        if client.participant_token is None:
            return None
        return self._participants.get(client.participant_token)

    def _require_participant(self, client: _ConnectedClient) -> _Participant | None:
        participant = self._participant_for_client(client)
        if participant is None:
            self._send_error(client, "Client is not joined to the room.")
        return participant

    def _participant_by_seat(self, seat: int) -> _Participant | None:
        for participant in self._participants.values():
            if participant.seat == seat:
                return participant
        return None

    def _send_welcome(self, client: _ConnectedClient) -> None:
        participant = self._participant_for_client(client)
        if participant is None:
            return
        try:
            client.send(
                {
                    "type": "welcome",
                    "seat": participant.seat,
                    "name": participant.name,
                    "session_token": participant.session_token,
                    "players": self.player_capacity,
                }
            )
        except OSError:
            pass

    def _broadcast_room_state(self, exclude_token: str | None = None) -> None:
        for participant in self._participants.values():
            if exclude_token is not None and participant.session_token == exclude_token:
                continue
            self._send_room_state(participant)

    def _send_room_state(self, participant: _Participant) -> None:
        if participant.connected_client_id is None:
            return
        client = self._connections.get(participant.connected_client_id)
        if client is None:
            return
        try:
            client.send({"type": "room_state", "room": self._room_snapshot(participant)})
        except OSError:
            pass

    def _room_snapshot(self, participant: _Participant) -> dict[str, Any]:
        seats = []
        for seat_number in range(1, self.player_capacity + 1):
            occupant = self._participant_by_seat(seat_number)
            lives = None if self._round is None else self._round.lives.get(seat_number)
            hand_count = None if self._round is None else len(self._round.hands.get(seat_number, []))
            seats.append(
                {
                    "seat": seat_number,
                    "name": occupant.name if occupant is not None else None,
                    "connected": occupant.connected if occupant is not None else False,
                    "lives": lives,
                    "hand_count": hand_count,
                    "eliminated": bool(lives == 0) if lives is not None else False,
                }
            )
        round_snapshot = {} if self._round is None else self._round.seat_snapshot(participant.seat)
        return {
            "phase": self._phase,
            "message": self._message,
            "players": self.player_capacity,
            "you_seat": participant.seat,
            "your_name": participant.name,
            "seats": seats,
            **round_snapshot,
        }

    def _broadcast_reveal_result(self, result: BluffRevealResult) -> None:
        payload = {
            "type": "reveal_result",
            "result": {
                "challenged_seat": result.challenged_seat,
                "challenger_seat": result.challenger_seat,
                "actual_cards": list(result.actual_cards),
                "truthful": result.truthful,
                "loser_seat": result.loser_seat,
                "winner_seat": result.winner_seat,
                "loser_lives": result.loser_lives,
                "loser_eliminated": result.loser_eliminated,
            },
        }
        for participant in self._participants.values():
            if participant.connected_client_id is None:
                continue
            client = self._connections.get(participant.connected_client_id)
            if client is None:
                continue
            try:
                client.send(payload)
            except OSError:
                continue

    def _challenge_message(self, result: BluffRevealResult) -> str:
        truth_text = "truthful" if result.truthful else "bluffing"
        return (
            f"Seat {result.challenged_seat} revealed {' '.join(result.actual_cards)} and was {truth_text}. "
            f"Seat {result.loser_seat} loses 1 life."
        )

    def _send_error(self, client: _ConnectedClient, message: str) -> None:
        try:
            client.send({"type": "error", "message": message})
        except OSError:
            pass

    def _close_room(self, message: str) -> None:
        self._phase = "closed"
        self._message = message
        for client in list(self._connections.values()):
            try:
                client.send({"type": "disconnect", "message": message})
            except OSError:
                pass
        self.shutdown()
