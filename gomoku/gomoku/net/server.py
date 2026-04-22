from __future__ import annotations

import json
import queue
import secrets
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, TextIO

from gomoku.core import GameState, Player
from gomoku.net.protocol import send_message


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
    name: str
    session_token: str
    color: Player
    connected_client_id: str | None = None
    ready: bool = False

    @property
    def connected(self) -> bool:
        return self.connected_client_id is not None


class GomokuServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._listener: socket.socket | None = None
        self._events: queue.Queue[tuple[str, str | None, Any]] | None = None

        self._connections: dict[str, _ConnectedClient] = {}
        self._participants: dict[str, _Participant] = {}
        self._round_number = 0
        self._phase = "waiting_for_players"
        self._state: GameState | None = None
        self._last_message = "Waiting for players."
        self._scoreboard = {"black_wins": 0, "white_wins": 0, "draws": 0}

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

            accept_thread = threading.Thread(target=self._accept_loop, args=(listener, events), daemon=True)
            accept_thread.start()

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
        thread = threading.Thread(target=self._reader_loop, args=(client,), daemon=True)
        thread.start()

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
        if message_type == "move":
            return self._handle_move(client, payload)
        if message_type == "ready":
            return self._handle_ready(client)
        if message_type == "resign":
            return self._handle_resign(client)
        if message_type == "leave":
            return self._handle_leave(client)
        if message_type == "close_room":
            return self._handle_close_room(client)

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
            if len(self._participants) >= 2:
                self._send_error(client, "Room is full.")
                return False
            participant = _Participant(
                name=name.strip(),
                session_token=secrets.token_urlsafe(16),
                color=Player.BLACK if not self._participants else Player.WHITE,
                connected_client_id=client.client_id,
            )
            self._participants[participant.session_token] = participant
            client.participant_token = participant.session_token

            if len(self._participants) == 1:
                self._phase = "waiting_for_players"
                self._last_message = f"{participant.name} joined. Waiting for an opponent."
            else:
                self._phase = "waiting_ready"
                self._last_message = "Both players connected. Press r when ready."
                self._reset_ready_flags()
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

            if self._phase == "paused_reconnect":
                if self._state is not None and not self._state.finished and self._both_participants_connected():
                    self._phase = "in_game"
                    self._last_message = f"{participant.name} reconnected. Game resumed."
                elif self._both_participants_connected():
                    self._phase = "waiting_ready"
                    self._last_message = f"{participant.name} reconnected. Press r when ready."
            else:
                self._last_message = f"{participant.name} reconnected."

        self._send_welcome(client)
        self._send_room_state(participant)
        self._broadcast_room_state(exclude_token=participant.session_token)
        return False

    def _handle_move(self, client: _ConnectedClient, payload: dict[str, Any]) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._phase != "in_game" or self._state is None:
            self._send_error(client, "No active round is running.")
            return False

        if participant.color is not self._state.current_player:
            self._send_error(client, "It is not your turn.")
            return False

        row = payload.get("row")
        col = payload.get("col")
        if not isinstance(row, int) or not isinstance(col, int):
            self._send_error(client, "Move must include integer row and col.")
            return False

        try:
            self._state.play(row, col)
        except ValueError as exc:
            self._send_error(client, str(exc))
            return False

        self._last_message = f"{participant.name} played at {self._format_position(row, col)}."
        self._broadcast_room_state()

        if self._state.finished:
            winner = self._state.winner
            if winner is None:
                self._scoreboard["draws"] += 1
                finished_message = f"Round {self._round_number} ended in a draw."
            else:
                key = "black_wins" if winner is Player.BLACK else "white_wins"
                self._scoreboard[key] += 1
                finished_message = f"Round {self._round_number} won by {winner.label}."
            self._prepare_next_round(finished_message)
            self._broadcast_room_state()
        return False

    def _handle_ready(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._phase != "waiting_ready":
            self._send_error(client, "Players can only ready up between rounds.")
            return False
        if not self._both_participants_connected():
            self._send_error(client, "Both players must be connected to start a round.")
            return False

        participant.ready = True
        self._last_message = f"{participant.name} is ready."

        if self._all_ready():
            self._state = GameState()
            self._round_number += 1
            self._phase = "in_game"
            self._last_message = f"Round {self._round_number} started. {self._player_name(Player.BLACK)} to move."
        self._broadcast_room_state()
        return False

    def _handle_resign(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._phase != "in_game" or self._state is None:
            self._send_error(client, "No active round is running.")
            return False

        winner = participant.color.other()
        key = "black_wins" if winner is Player.BLACK else "white_wins"
        self._scoreboard[key] += 1
        self._prepare_next_round(f"{participant.name} resigned. {winner.label} wins the round.")
        self._broadcast_room_state()
        return False

    def _handle_leave(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        self._close_room(f"{participant.name} left the room.")
        return True

    def _handle_close_room(self, client: _ConnectedClient) -> bool:
        participant = self._require_participant(client)
        if participant is None:
            return False
        if self._phase != "paused_reconnect":
            self._send_error(client, "Room can only be closed while waiting for a reconnect.")
            return False
        self._close_room(f"{participant.name} closed the room while waiting for reconnect.")
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
                self._phase = "paused_reconnect"
                self._last_message = f"{participant.name} disconnected. Waiting for reconnect."
                self._broadcast_room_state()
        client.close()

    def _drop_connection(self, client_id: str) -> None:
        client = self._connections.pop(client_id, None)
        if client is None:
            return
        client.close()

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
            client.send(
                {
                    "type": "room_state",
                    "room": self._room_snapshot(participant),
                }
            )
        except OSError:
            return

    def _room_snapshot(self, participant: _Participant) -> dict[str, Any]:
        seats = []
        for color in (Player.BLACK, Player.WHITE):
            owner = self._participant_by_color(color)
            seats.append(
                {
                    "player_color": color.value,
                    "name": owner.name if owner is not None else None,
                    "connected": owner.connected if owner is not None else False,
                    "ready": owner.ready if owner is not None else False,
                }
            )
        return {
            "phase": self._phase,
            "round_number": self._round_number,
            "board_state": None if self._state is None else self._state.to_snapshot(),
            "scoreboard": dict(self._scoreboard),
            "seats": seats,
            "you_color": participant.color.value,
            "message": self._last_message,
        }

    def _prepare_next_round(self, message: str) -> None:
        self._swap_colors()
        self._state = None
        self._phase = "waiting_ready"
        self._last_message = f"{message} Press r when ready for the next round."
        self._reset_ready_flags()

    def _swap_colors(self) -> None:
        black = self._participant_by_color(Player.BLACK)
        white = self._participant_by_color(Player.WHITE)
        if black is None or white is None:
            return
        black.color, white.color = white.color, black.color

    def _reset_ready_flags(self) -> None:
        for participant in self._participants.values():
            participant.ready = False

    def _all_ready(self) -> bool:
        return len(self._participants) == 2 and all(participant.ready for participant in self._participants.values())

    def _both_participants_connected(self) -> bool:
        return len(self._participants) == 2 and all(participant.connected for participant in self._participants.values())

    def _participant_for_client(self, client: _ConnectedClient) -> _Participant | None:
        if client.participant_token is None:
            return None
        return self._participants.get(client.participant_token)

    def _require_participant(self, client: _ConnectedClient) -> _Participant | None:
        participant = self._participant_for_client(client)
        if participant is None:
            self._send_error(client, "Client is not joined to the room.")
        return participant

    def _participant_by_color(self, color: Player) -> _Participant | None:
        for participant in self._participants.values():
            if participant.color is color:
                return participant
        return None

    def _player_name(self, color: Player) -> str:
        participant = self._participant_by_color(color)
        if participant is None:
            return color.label
        return participant.name

    def _send_welcome(self, client: _ConnectedClient) -> None:
        participant = self._participant_for_client(client)
        if participant is None:
            return
        try:
            client.send(
                {
                    "type": "welcome",
                    "player": participant.color.value,
                    "name": participant.name,
                    "session_token": participant.session_token,
                    "board_size": GameState().board.size,
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
        self._last_message = message
        for client in list(self._connections.values()):
            try:
                client.send({"type": "disconnect", "message": message})
            except OSError:
                pass
        self.shutdown()

    def _format_position(self, row: int, col: int) -> str:
        return f"{chr(ord('A') + col)}{row + 1}"
