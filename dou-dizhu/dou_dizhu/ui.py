from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from dou_dizhu.client import DdzClientConnection


class DdzRemoteApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #hand-panel {
            width: 1fr;
        }

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
        Binding("p", "play_selected", "Play"),
        Binding("a", "pass_turn", "Pass"),
        Binding("escape", "clear_selection", "Clear", show=False),
        Binding("0", "bid_zero", "Bid0", show=False),
        Binding("1", "bid_one", "Bid1", show=False),
        Binding("2", "bid_two", "Bid2", show=False),
        Binding("3", "bid_three", "Bid3", show=False),
    ]
    help_text = "Up/Down move  Space select card  p play  a pass  0-3 bid  Esc clear  q quit"

    def __init__(self, host: str, port: int, name: str, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.host = host
        self.port = port
        self.player_name = name
        self.connection = DdzClientConnection(host, port, name)
        self.room: dict[str, Any] | None = None
        self.disconnected = False
        self.cursor_index = 0
        self.selected_indexes: set[int] = set()
        self.message = f"Connecting to {host}:{port}..."

    def compose(self) -> ComposeResult:
        yield Static("Dou Dizhu", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="table-view", classes="board-text")
            with Vertical(classes="panel side-panel", id="hand-panel"):
                yield Static("", id="hand-view")
                with Vertical(id="action-grid"):
                    with Horizontal(classes="action-row"):
                        yield Button("Play", id="play")
                        yield Button("Pass", id="pass")
                        yield Button("Clear", id="clear")
                    with Horizontal(classes="action-row"):
                        yield Button("Bid 0", id="bid-0")
                        yield Button("Bid 1", id="bid-1")
                        yield Button("Bid 2", id="bid-2")
                        yield Button("Bid 3", id="bid-3")
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
            elif payload_type == "error":
                self.message = str(payload.get("message", "Action rejected."))
            elif payload_type == "disconnect":
                self.disconnected = True
                self.message = str(payload.get("message", "Connection closed."))
        self.refresh_view()

    def trim_selection(self) -> None:
        hand = self.current_hand()
        if not hand:
            self.cursor_index = 0
            self.selected_indexes.clear()
            return
        self.cursor_index = max(0, min(len(hand) - 1, self.cursor_index))
        self.selected_indexes = {index for index in self.selected_indexes if index < len(hand)}

    def current_hand(self) -> list[str]:
        if self.room is None:
            return []
        return list(self.room.get("your_hand", []))

    def render_table(self) -> str:
        if self.room is None:
            return "\n".join(
                [
                    "Waiting for room state...",
                    "",
                    "How to play:",
                    "1. Wait for three seats to fill.",
                    "2. During bidding, press 0/1/2/3.",
                    "3. During play, select cards with Space, then press p.",
                    "4. If you cannot beat the table, press a to pass.",
                ]
            )
        seats = []
        for seat in self.room["seats"]:
            role = "landlord" if seat.get("is_landlord") else "farmer"
            status = "online" if seat.get("connected") else "offline"
            seats.append(f"S{seat['seat']} {seat.get('name') or '(empty)'} [{role}, {status}, cards={seat.get('hand_count', '-')}]")
        table_cards = " ".join(self.room.get("table_cards", [])) or "(none)"
        bottom = " ".join(self.room.get("bottom_cards", [])) or "(hidden)"
        hand_counts = self.room.get("hand_counts", {})
        action_log = self.room.get("action_log", [])
        lines = [
            f"Phase: {self.room['phase']}",
            f"You: seat {self.room['you_seat']} {self.room['your_name']}",
            self.render_instruction(),
            "Seats:",
            *seats,
            "",
            f"Current turn: seat {self.room.get('current_turn')}",
            f"Highest bid: {self.room.get('highest_bid')} by {self.room.get('highest_bidder')}",
            f"Landlord: {self.room.get('landlord_seat')}",
            f"Bottom cards: {bottom}",
            f"Table: seat {self.room.get('table_seat')} -> {table_cards}",
            f"Hand counts: S1={hand_counts.get(1, '-')}  S2={hand_counts.get(2, '-')}  S3={hand_counts.get(3, '-')}",
            "",
            "Recent actions:",
            *(f"- {entry}" for entry in action_log[-8:]),
        ]
        if self.room.get("winner_seat") is not None:
            lines.append(f"Winner: seat {self.room['winner_seat']} ({self.room['winner_side']})")
        return "\n".join(lines)

    def render_hand(self) -> str:
        hand = self.current_hand()
        if not hand:
            return "Your hand:\n  (empty)"
        lines = [
            "Your hand:",
            "  > cursor   * selected",
            "  Select cards with Space. Press p to play the selected set.",
        ]
        for index, card in enumerate(hand):
            pointer = ">" if index == self.cursor_index else " "
            chosen = "*" if index in self.selected_indexes else " "
            lines.append(f"{pointer}{chosen} {index + 1:>2}. {card}")
        return "\n".join(lines)

    def render_instruction(self) -> str:
        if self.room is None:
            return "Next: wait for the server to send the room state."

        phase = str(self.room.get("phase"))
        you_seat = self.room.get("you_seat")
        current_turn = self.room.get("current_turn")
        if self.disconnected:
            return "Next: disconnected. Restart the client with the same name to rejoin."
        if phase == "waiting_for_players":
            return "Next: wait for all three seats to be filled."
        if phase == "paused_reconnect":
            return "Next: a player disconnected. Wait for them to rejoin with the same name."
        if phase == "bidding":
            if current_turn == you_seat:
                highest_bid = self.room.get("highest_bid", 0)
                return f"Next: your bid. Press 0/1/2/3. Current highest bid is {highest_bid}."
            return f"Next: wait for seat {current_turn} to bid."
        if phase == "playing":
            if self.room.get("winner_seat") is not None:
                return "Next: round finished. Press q to quit, or restart the room from the server."
            if current_turn == you_seat:
                table_seat = self.room.get("table_seat")
                if table_seat is None:
                    return "Next: lead this trick. Select a valid set of cards with Space, then press p."
                return "Next: respond to the table. Select a stronger valid set, then press p. Press a to pass."
            return f"Next: wait for seat {current_turn} to act."
        if phase == "finished":
            return "Next: round finished. Press q to quit."
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

    def play_selected_cards(self) -> None:
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
            self.connection.send_play(cards)
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending play."
        else:
            self.message = f"Played {' '.join(cards)}."
            self.selected_indexes.clear()
        self.refresh_view()

    def action_play_selected(self) -> None:
        self.play_selected_cards()

    def action_pass_turn(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        try:
            self.connection.send_pass()
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending pass."
        else:
            self.message = "Pass sent."
            self.selected_indexes.clear()
        self.refresh_view()

    def send_bid(self, amount: int) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        try:
            self.connection.send_bid(amount)
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending bid."
        else:
            self.message = f"Bid {amount} sent."
        self.refresh_view()

    def action_bid_zero(self) -> None:
        self.send_bid(0)

    def action_bid_one(self) -> None:
        self.send_bid(1)

    def action_bid_two(self) -> None:
        self.send_bid(2)

    def action_bid_three(self) -> None:
        self.send_bid(3)

    def action_quit_app(self) -> None:
        try:
            self.connection.send_leave()
        except OSError:
            pass
        self.exit(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "play":
            self.play_selected_cards()
        elif button_id == "pass":
            self.action_pass_turn()
        elif button_id == "clear":
            self.action_clear_selection()
        elif button_id and button_id.startswith("bid-"):
            self.send_bid(int(button_id.rsplit("-", 1)[1]))


def run_ddz_remote_client(
    host: str,
    port: int,
    name: str,
    theme: str = "modern",
) -> int:
    return DdzRemoteApp(host, port, name, theme=theme).run() or 0
