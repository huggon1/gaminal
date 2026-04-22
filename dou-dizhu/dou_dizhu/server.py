from __future__ import annotations

import json
import queue
import secrets
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, TextIO

from dou_dizhu.core import DdzRoundState, create_shuffled_deck, sort_cards
from dou_dizhu.protocol import send_message


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


class DdzServer:
    def __init__(self, host: str, port: int, deck_factory: Callable[[], list[str]] | None = None) -> None:
        self.host = host
        self.port = port
        self.ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._listener: socket.socket | None = None
        self._events: queue.Queue[tuple[str, str | None, Any]] | None = None
        self._connections: dict[str, _ConnectedClient] = {}
        self._participants: dict[str, _Participant] = {}
        self._round: DdzRoundState | None = None
        self._phase = "waiting_for_players"
        self._message = "Waiting for three players."
        self._resume_phase: str | None = None
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

        if message_type == "bid":
            return self._handle_bid(client, payload)
        if message_type == "play":
            return self._handle_play(client, payload)
        if message_type == "pass":
            return self._handle_pass(client)
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
            if len(self._participants) >= 3:
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

        if len(self._participants) == 3 and self._round is None and self._all_connected():
            self._start_round()
        return False

    def _start_round(self) -> None:
        self._round = DdzRoundState.from_deck(self._deck_factory())
        self._phase = "bidding"
        self._message = "Three players connected. Bidding starts at seat 1."
        self._broadcast_room_state()

    def _handle_bid(self, client: _ConnectedClient, payload: dict[str, Any]) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        amount = payload.get("amount")
        if not isinstance(amount, int):
            self._send_error(client, "Bid must include an integer amount.")
            return False
        try:
            self._round.bid(participant.seat, amount)
        except ValueError as exc:
            if str(exc) == "No one bid for landlord.":
                self._message = "Nobody bid. Redealing."
                self._round = DdzRoundState.from_deck(self._deck_factory())
                self._phase = "bidding"
                self._broadcast_room_state()
                return False
            self._send_error(client, str(exc))
            return False

        self._phase = self._round.phase
        if self._round.phase == "bidding":
            self._message = f"Seat {participant.seat} bid {amount}."
        else:
            self._message = f"Seat {self._round.landlord_seat} became landlord."
        self._broadcast_room_state()
        return False

    def _handle_play(self, client: _ConnectedClient, payload: dict[str, Any]) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        cards = payload.get("cards")
        if not isinstance(cards, list) or not all(isinstance(card, str) for card in cards):
            self._send_error(client, "Play must include a list of cards.")
            return False
        try:
            self._round.play_cards(participant.seat, sort_cards(list(cards)))
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False
        self._phase = self._round.phase
        self._message = f"Seat {participant.seat} played {' '.join(sort_cards(list(cards)))}."
        if self._round.phase == "finished":
            self._message = f"Seat {participant.seat} won for the {self._round.winner_side} side."
        self._broadcast_room_state()
        return False

    def _handle_pass(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._round is None:
            self._send_error(client, "Round has not started.")
            return False
        try:
            self._round.pass_turn(participant.seat)
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False
        self._message = f"Seat {participant.seat} passed."
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
        room = self._room_snapshot(participant)
        try:
            client.send({"type": "room_state", "room": room})
        except OSError:
            return

    def _room_snapshot(self, participant: _Participant) -> dict[str, Any]:
        seats = []
        for seat_number in (1, 2, 3):
            occupant = self._participant_by_seat(seat_number)
            seats.append(
                {
                    "seat": seat_number,
                    "name": occupant.name if occupant is not None else None,
                    "connected": occupant.connected if occupant is not None else False,
                    "hand_count": len(self._round.hands[seat_number]) if self._round is not None else None,
                    "is_landlord": self._round is not None and self._round.landlord_seat == seat_number,
                }
            )
        round_snapshot = {} if self._round is None else self._round.seat_snapshot(participant.seat)
        return {
            "phase": self._phase,
            "message": self._message,
            "you_seat": participant.seat,
            "your_name": participant.name,
            "seats": seats,
            **round_snapshot,
        }

    def _participant_by_seat(self, seat: int) -> _Participant | None:
        for participant in self._participants.values():
            if participant.seat == seat:
                return participant
        return None

    def _participant_for_client(self, client: _ConnectedClient) -> _Participant | None:
        if client.participant_token is None:
            return None
        return self._participants.get(client.participant_token)

    def _require_participant(self, client: _ConnectedClient) -> _Participant | None:
        participant = self._participant_for_client(client)
        if participant is None:
            self._send_error(client, "Client is not joined to the room.")
        return participant

    def _all_connected(self) -> bool:
        return len(self._participants) == 3 and all(participant.connected for participant in self._participants.values())

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
                }
            )
        except OSError:
            pass

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
