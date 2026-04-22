from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from bluff_cards.client import BluffClientConnection


class BluffRemoteApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #action-row {
            height: auto;
        }

        #action-row Button {
            margin-right: 1;
            margin-bottom: 1;
            min-width: 10;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_hand_up", "Prev", show=False),
        Binding("down", "move_hand_down", "Next", show=False),
        Binding("space", "toggle_card", "Select"),
        Binding("p", "play_claim", "Play"),
        Binding("c", "challenge_claim", "Challenge"),
        Binding("a", "accept_claim", "Accept"),
        Binding("1", "set_claim_one", "Claim1", show=False),
        Binding("2", "set_claim_two", "Claim2", show=False),
        Binding("3", "set_claim_three", "Claim3", show=False),
        Binding("escape", "clear_selection", "Clear", show=False),
    ]
    help_text = "Up/Down browse hand  Space select  1-3 claim count  p play  c challenge  a accept"

    def __init__(self, host: str, port: int, name: str, session_token: str | None = None, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.host = host
        self.port = port
        self.name = name
        self.session_token = session_token
        self.connection = BluffClientConnection(host, port, name, session_token)
        self.room: dict[str, Any] | None = None
        self.reveal: dict[str, Any] | None = None
        self.disconnected = False
        self.cursor_index = 0
        self.selected_indexes: set[int] = set()
        self.claim_count = 1
        self.message = f"Connecting to {host}:{port}..."

    def compose(self) -> ComposeResult:
        yield Static("Bluff Cards", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="table-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="hand-view")
                with Horizontal(id="action-row"):
                    yield Button("Play", id="play")
                    yield Button("Challenge", id="challenge")
                    yield Button("Accept", id="accept")
                    yield Button("Clear", id="clear")
                    yield Button("Claim 1", id="claim-1")
                    yield Button("Claim 2", id="claim-2")
                    yield Button("Claim 3", id="claim-3")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.connection.connect()
        self.set_interval(0.1, self.poll_messages)
        self.message = f"Connected to {self.host}:{self.port}. Joining room..."
        self.refresh_view()

    def on_unmount(self) -> None:
        self.connection.close()

    def poll_messages(self) -> None:
        for payload in self.connection.poll_messages():
            payload_type = payload.get("type")
            if payload_type == "welcome":
                self.session_token = str(payload["session_token"])
                self.message = f"Joined seat {payload['seat']} as {payload['name']}."
            elif payload_type == "room_state":
                self.room = dict(payload["room"])
                self.message = str(self.room.get("message", self.message))
                self.trim_selection()
            elif payload_type == "reveal_result":
                self.reveal = dict(payload["result"])
                self.message = self.reveal_message(self.reveal)
            elif payload_type == "error":
                self.message = str(payload.get("message", "Action rejected."))
            elif payload_type == "disconnect":
                self.disconnected = True
                self.message = str(payload.get("message", "Connection closed."))
        self.refresh_view()
        if self.disconnected:
            self.exit(0)

    def current_hand(self) -> list[str]:
        if self.room is None:
            return []
        return list(self.room.get("your_hand", []))

    def trim_selection(self) -> None:
        hand = self.current_hand()
        if not hand:
            self.cursor_index = 0
            self.selected_indexes.clear()
            return
        self.cursor_index = max(0, min(len(hand) - 1, self.cursor_index))
        self.selected_indexes = {index for index in self.selected_indexes if index < len(hand)}

    def render_table(self) -> str:
        if self.room is None:
            return "Waiting for room state..."
        seats = []
        for seat in self.room["seats"]:
            status = "online" if seat.get("connected") else "offline"
            seats.append(
                f"S{seat['seat']} {seat.get('name') or '(empty)'} [{status}, hand={seat.get('hand_count')}, hp={seat.get('lives')}, out={seat.get('eliminated')}]"
            )
        lines = [
            f"Phase: {self.room['phase']}",
            f"You: seat {self.room['you_seat']} {self.room['your_name']}",
            f"Players: {self.room['players']}",
            "Seats:",
            *seats,
            "",
            f"Target rank: {self.room.get('target_rank')}",
            f"Current turn: seat {self.room.get('current_turn')}",
            f"Discard count: {self.room.get('discard_count')}",
            f"Claim count selector: {self.claim_count}",
        ]
        claim = self.room.get("last_claim")
        if isinstance(claim, dict):
            lines.append(f"Last claim: seat {claim['seat']} says {claim['claimed_count']} x {claim['target_rank']}")
        if self.reveal is not None:
            lines.append(self.reveal_message(self.reveal))
        if self.room.get("winner_seat") is not None:
            lines.append(f"Winner: seat {self.room['winner_seat']}")
        if self.session_token is not None:
            lines.append(f"Reconnect token: {self.session_token}")
        return "\n".join(lines)

    def render_hand(self) -> str:
        hand = self.current_hand()
        if not hand:
            return "Your hand:\n  (empty)"
        lines = ["Your hand:"]
        for index, card in enumerate(hand):
            pointer = ">" if index == self.cursor_index else " "
            chosen = "*" if index in self.selected_indexes else " "
            lines.append(f"{pointer}{chosen} {index + 1:>2}. {card}")
        return "\n".join(lines)

    def refresh_view(self) -> None:
        self.query_one("#table-view", Static).update(self.render_table())
        self.query_one("#hand-view", Static).update(self.render_hand())
        self.update_status(self.message)

    def move_cursor(self, delta: int) -> None:
        hand = self.current_hand()
        if not hand:
            return
        self.cursor_index = max(0, min(len(hand) - 1, self.cursor_index + delta))
        self.refresh_view()

    def action_move_hand_up(self) -> None:
        self.move_cursor(-1)

    def action_move_hand_down(self) -> None:
        self.move_cursor(1)

    def action_toggle_card(self) -> None:
        hand = self.current_hand()
        if not hand:
            self.message = "No cards available."
            self.refresh_view()
            return
        if self.cursor_index in self.selected_indexes:
            self.selected_indexes.remove(self.cursor_index)
        else:
            self.selected_indexes.add(self.cursor_index)
        self.message = f"Selected {len(self.selected_indexes)} card(s)."
        self.refresh_view()

    def action_clear_selection(self) -> None:
        self.selected_indexes.clear()
        self.message = "Selection cleared."
        self.refresh_view()

    def set_claim_count(self, count: int) -> None:
        self.claim_count = count
        self.message = f"Claim count set to {count}."
        self.refresh_view()

    def action_set_claim_one(self) -> None:
        self.set_claim_count(1)

    def action_set_claim_two(self) -> None:
        self.set_claim_count(2)

    def action_set_claim_three(self) -> None:
        self.set_claim_count(3)

    def action_play_claim(self) -> None:
        hand = self.current_hand()
        if not self.selected_indexes:
            self.message = "Select at least one card first."
            self.refresh_view()
            return
        cards = [hand[index] for index in sorted(self.selected_indexes)]
        try:
            self.connection.send_play_claim(cards, self.claim_count)
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending play."
        else:
            self.message = f"Claimed {self.claim_count} card(s)."
            self.selected_indexes.clear()
        self.refresh_view()

    def action_challenge_claim(self) -> None:
        try:
            self.connection.send_challenge()
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending challenge."
        else:
            self.message = "Challenge sent."
        self.refresh_view()

    def action_accept_claim(self) -> None:
        try:
            self.connection.send_accept()
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending accept."
        else:
            self.message = "Accept sent."
        self.refresh_view()

    def reveal_message(self, reveal: dict[str, Any]) -> str:
        truth = "truthful" if reveal.get("truthful") else "bluffing"
        cards = " ".join(reveal.get("actual_cards", []))
        return f"Reveal: seat {reveal['challenged_seat']} showed {cards} and was {truth}. Seat {reveal['loser_seat']} lost 1 life."

    def action_quit_app(self) -> None:
        try:
            self.connection.send_leave()
        except OSError:
            pass
        self.exit(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "play":
            self.action_play_claim()
        elif button_id == "challenge":
            self.action_challenge_claim()
        elif button_id == "accept":
            self.action_accept_claim()
        elif button_id == "clear":
            self.action_clear_selection()
        elif button_id and button_id.startswith("claim-"):
            self.set_claim_count(int(button_id.rsplit("-", 1)[1]))


def run_bluff_remote_client(
    host: str,
    port: int,
    name: str,
    session_token: str | None = None,
    theme: str = "modern",
) -> int:
    return BluffRemoteApp(host, port, name, session_token, theme=theme).run() or 0
