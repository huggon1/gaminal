from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from bluff_cards.client import BluffClientConnection
from bluff_cards.core import card_label
from ._textual_base import COMMON_CSS, ThemedApp


class BluffRemoteApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #action-grid {
            height: auto;
            layout: vertical;
        }

        .action-row {
            height: auto;
        }

        .action-row Button {
            margin-right: 1;
            margin-bottom: 1;
            min-width: 8;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_hand_up", "Prev", show=False),
        Binding("down", "move_hand_down", "Next", show=False),
        Binding("space", "toggle_card", "Select"),
        Binding("p", "play_claim", "Play"),
        Binding("c", "challenge_claim", "Challenge"),
        Binding("escape", "clear_selection", "Clear", show=False),
    ]
    help_text = "Up/Down move  Space select  p play cards  c challenge  Esc clear  q quit"

    def __init__(self, host: str, port: int, name: str, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.host = host
        self.port = port
        self.player_name = name
        self.connection = BluffClientConnection(host, port, name)
        self.room: dict[str, Any] | None = None
        self.reveal: dict[str, Any] | None = None
        self.reveal_stage_text: str | None = None
        self.disconnected = False
        self.cursor_index = 0
        self.selected_indexes: set[int] = set()
        self.message = f"Connecting to {host}:{port}..."

    def compose(self) -> ComposeResult:
        yield Static("Bluff Cards", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="table-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="hand-view")
                with Vertical(id="action-grid"):
                    with Horizontal(classes="action-row"):
                        yield Button("Play", id="play")
                        yield Button("Challenge", id="challenge")
                        yield Button("Clear", id="clear")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        try:
            self.connection.connect()
        except OSError as exc:
            self.disconnected = True
            self.message = f"Failed to connect to {self.host}:{self.port}: {exc}"
        else:
            self.message = f"Connected to {self.host}:{self.port}. Joining room..."
        self.set_interval(0.1, self.poll_messages)
        self.refresh_view()

    def on_unmount(self) -> None:
        self.connection.close()

    def poll_messages(self) -> None:
        for payload in self.connection.poll_messages():
            payload_type = payload.get("type")
            if payload_type == "welcome":
                self.message = f"Joined seat {payload['seat']} as {payload['name']}."
            elif payload_type == "room_state":
                self.room = dict(payload["room"])
                self.message = str(self.room.get("message", self.message))
                self.trim_selection()
            elif payload_type == "reveal_result":
                self.reveal = dict(payload["result"])
                self.start_reveal_animation(self.reveal)
            elif payload_type == "error":
                self.message = str(payload.get("message", "Action rejected."))
            elif payload_type == "disconnect":
                self.disconnected = True
                self.message = str(payload.get("message", "Connection closed."))
        self.refresh_view()

    def start_reveal_animation(self, reveal: dict[str, Any]) -> None:
        card_text = " ".join(card_label(card) for card in reveal.get("actual_cards", []))
        truth = "TRUTH" if reveal.get("truthful") else "BLUFF"
        stages = [
            f"Challenge! Seat {reveal['challenger_seat']} calls seat {reveal['challenged_seat']}.",
            "Flipping the cards...",
            f"Revealed cards: {card_text}",
            f"Result: {truth}. Seat {reveal['loser_seat']} loses 1 life.",
        ]
        self.reveal_stage_text = stages[0]
        for index, stage in enumerate(stages[1:], start=1):
            self.set_timer(0.45 * index, lambda text=stage: self._set_reveal_stage(text))

    def _set_reveal_stage(self, text: str) -> None:
        self.reveal_stage_text = text
        self.refresh_view()

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
            return "\n".join(
                [
                    "Waiting for room state...",
                    "",
                    "How to play:",
                    "1. This table only uses A, K, Q and Jokers.",
                    "2. Select 1-3 cards with Space and press p to claim they all match the table rank.",
                    "3. The next player may either play their own cards or press c to challenge.",
                    "4. After a challenge, the cards are revealed and a new round is dealt.",
                ]
            )
        seats = []
        for seat in self.room["seats"]:
            status = "online" if seat.get("connected") else "offline"
            seats.append(
                f"S{seat['seat']} {seat.get('name') or '(empty)'} [{status}, hand={seat.get('hand_count')}, hp={seat.get('lives')}, out={seat.get('eliminated')}]"
            )
        action_log = self.room.get("action_log", [])
        lines = [
            f"Phase: {self.room['phase']}",
            f"You: seat {self.room['you_seat']} {self.room['your_name']}",
            self.render_instruction(),
            f"Players: {self.room['players']}",
            "Seats:",
            *seats,
            "",
            f"Table rank: {self.room.get('table_rank')}",
            f"Current turn: seat {self.room.get('current_turn')}",
            f"Discard count: {self.room.get('discard_count')}",
            "",
            "Recent actions:",
            *(f"- {entry}" for entry in action_log[-8:]),
        ]
        claim = self.room.get("last_claim")
        if isinstance(claim, dict):
            lines.append(f"Last claim: seat {claim['seat']} says {claim['claimed_count']} x {claim['table_rank']}")
        if self.reveal_stage_text is not None:
            lines.extend(["", self.reveal_stage_text])
        if self.room.get("winner_seat") is not None:
            lines.append(f"Winner: seat {self.room['winner_seat']}")
        return "\n".join(lines)

    def render_hand(self) -> str:
        hand = self.current_hand()
        if not hand:
            return "Your hand:\n  (empty)"
        lines = [
            "Your hand:",
            "  > cursor   * selected",
            "  Select 1-3 cards. Press p to claim they all match the table rank.",
        ]
        for index, card in enumerate(hand):
            pointer = ">" if index == self.cursor_index else " "
            chosen = "*" if index in self.selected_indexes else " "
            lines.append(f"{pointer}{chosen} {index + 1:>2}. {card_label(card)}")
        return "\n".join(lines)

    def render_instruction(self) -> str:
        if self.room is None:
            return "Next: wait for the server to send the room state."
        if self.disconnected:
            return "Next: disconnected. Restart the client with the same name to rejoin."

        phase = str(self.room.get("phase"))
        you_seat = self.room.get("you_seat")
        current_turn = self.room.get("current_turn")
        last_claim = self.room.get("last_claim")
        if phase == "waiting_for_players":
            return "Next: wait for all seats to be filled."
        if phase == "paused_reconnect":
            return "Next: a player disconnected. Wait for them to rejoin with the same name."
        if phase == "in_round":
            if current_turn == you_seat:
                if isinstance(last_claim, dict) and last_claim.get("seat") != you_seat:
                    if self.current_hand():
                        return "Next: choose one action. Press c to challenge, or select 1-3 cards and press p to continue the bluff."
                    return "Next: you have no cards left. Press c to challenge the previous claim."
                return "Next: your turn. Select 1-3 cards and press p."
            return f"Next: wait for seat {current_turn} to act."
        if phase == "finished":
            return "Next: game over. Press q to quit."
        if phase == "closed":
            return "Next: room closed. Press q to quit."
        return "Next: follow the status message below."

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
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
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
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        self.selected_indexes.clear()
        self.message = "Selection cleared."
        self.refresh_view()

    def action_play_claim(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        hand = self.current_hand()
        if not self.selected_indexes:
            self.message = "Select at least one card first."
            self.refresh_view()
            return
        cards = [hand[index] for index in sorted(self.selected_indexes)]
        try:
            self.connection.send_play_claim(cards)
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending play."
        else:
            self.message = f"Played {len(cards)} face-down card(s)."
            self.selected_indexes.clear()
        self.refresh_view()

    def action_challenge_claim(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        try:
            self.connection.send_challenge()
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending challenge."
        else:
            self.message = "Challenge sent."
        self.refresh_view()

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
        elif button_id == "clear":
            self.action_clear_selection()


def run_bluff_remote_client(
    host: str,
    port: int,
    name: str,
    theme: str = "modern",
) -> int:
    return BluffRemoteApp(host, port, name, theme=theme).run() or 0
