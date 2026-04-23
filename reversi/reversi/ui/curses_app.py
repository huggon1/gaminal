from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from reversi.core import BOARD_SIZE, GameState, Player
from reversi.net.client import RemoteClientConnection
from ._textual_base import COMMON_CSS, ThemedApp


def format_position(row: int, col: int) -> str:
    return f"{chr(ord('A') + col)}{row + 1}"


def render_board_text(state: GameState, cursor_row: int, cursor_col: int) -> str:
    valid = set(state.valid_moves_for_current()) if not state.finished else set()
    header = "   " + "".join(f" {chr(ord('A') + i)} " for i in range(BOARD_SIZE))
    lines = [header]
    for row in range(BOARD_SIZE):
        cells: list[str] = []
        for col in range(BOARD_SIZE):
            cell = state.board.grid[row][col]
            if cell is not None:
                symbol = cell.stone
            elif (row, col) in valid:
                symbol = "·"
            else:
                symbol = "."
            if row == cursor_row and col == cursor_col:
                token = f"[{symbol}]"
            elif state.last_move and state.last_move.row == row and state.last_move.col == col:
                token = f"({symbol})"
            else:
                token = f" {symbol} "
            cells.append(token)
        lines.append(f"{row + 1:>2} " + "".join(cells))
    return "\n".join(lines)


class _BaseReversiApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view, #info-view {
            height: auto;
        }

        #action-row {
            height: auto;
            margin-top: 1;
        }

        #action-row Button {
            margin-right: 1;
            min-width: 10;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("left", "move_left", "Left", show=False),
        Binding("right", "move_right", "Right", show=False),
        Binding("enter", "confirm_action", "Confirm"),
        Binding("space", "confirm_action", "Confirm", show=False),
    ]

    def __init__(self, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.state = GameState()
        self.cursor_row = BOARD_SIZE // 2 - 1
        self.cursor_col = BOARD_SIZE // 2 - 1
        self.message = "Arrow keys move. Enter places a piece."

    def compose(self) -> ComposeResult:
        yield Static("Reversi", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="info-view")
                with Horizontal(id="action-row"):
                    yield from self.compose_actions()
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def compose_actions(self) -> ComposeResult:
        yield Button("Place", id="place")

    def on_mount(self) -> None:
        super().on_mount()
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(render_board_text(self.state, self.cursor_row, self.cursor_col))
        self.query_one("#info-view", Static).update(self.render_info())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.state.winner is not None:
            return f"[bold green]✦ {self.state.winner.label.upper()} WINS ✦[/bold green]"
        if self.state.draw:
            return "[bold yellow]★ DRAW ★[/bold yellow]"
        return f"[bold cyan]▶ {self.state.current_player.label.upper()} TO MOVE[/bold cyan]"

    def render_info(self) -> str:
        black, white = self.state.get_scores()
        return "\n".join(
            [
                "[bold]Board[/bold]",
                f"Status:   {self.state.status_text()}",
                f"Cursor:   {format_position(self.cursor_row, self.cursor_col)}",
                f"Last:     {self._last_move_text()}",
                f"Score:    B {black} / W {white}",
                "",
                self.render_next_action(),
            ]
        )

    def render_next_action(self) -> str:
        if self.state.finished:
            return "[bold yellow]Next:[/bold yellow] Review the final count."
        return "[bold green]Next:[/bold green] Use the dotted moves to choose the strongest flip."

    def _last_move_text(self) -> str:
        if self.state.last_move is None:
            return "none"
        return f"{self.state.last_move.player.label} @ {format_position(self.state.last_move.row, self.state.last_move.col)}"

    def move_cursor(self, delta_row: int, delta_col: int) -> None:
        self.cursor_row = max(0, min(BOARD_SIZE - 1, self.cursor_row + delta_row))
        self.cursor_col = max(0, min(BOARD_SIZE - 1, self.cursor_col + delta_col))
        self.refresh_view()

    def action_move_up(self) -> None:
        self.move_cursor(-1, 0)

    def action_move_down(self) -> None:
        self.move_cursor(1, 0)

    def action_move_left(self) -> None:
        self.move_cursor(0, -1)

    def action_move_right(self) -> None:
        self.move_cursor(0, 1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "place":
            self.action_confirm_action()


class LocalGameApp(_BaseReversiApp):
    help_text = "Arrows move  Enter/Space place piece  · marks valid moves  t theme  ? help  q quit"

    def action_confirm_action(self) -> None:
        try:
            self.state.play(self.cursor_row, self.cursor_col)
        except ValueError as exc:
            self.message = str(exc)
        else:
            if self.state.finished:
                self.message = self.state.status_text()
            else:
                skip = " Opponent skipped." if self.state.skipped_turn else ""
                self.message = f"Placed at {format_position(self.cursor_row, self.cursor_col)}.{skip}"
        self.refresh_view()


class RemoteGameApp(_BaseReversiApp):
    BINDINGS = _BaseReversiApp.BINDINGS + [
        Binding("r", "send_ready", "Ready"),
        Binding("s", "send_resign", "Resign"),
        Binding("x", "close_room", "Close", show=False),
    ]
    help_text = "Arrows move  Enter send move  r ready  s resign  x close paused room  t theme"

    def __init__(self, host: str, port: int, name: str, session_token: str | None = None, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.host = host
        self.port = port
        self.player_name = name
        self.session_token = session_token
        self.connection = RemoteClientConnection(host, port, name, session_token)
        self.local_player: Player | None = None
        self.room: dict[str, Any] | None = None
        self.disconnected = False
        self.room_closed = False
        self.message = f"Connecting to {host}:{port}..."

    def compose_actions(self) -> ComposeResult:
        yield Button("Move", id="place")
        yield Button("Ready", id="ready")
        yield Button("Resign", id="resign")
        yield Button("Close", id="close")

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
                self.message = f"Joined as {payload['name']}."
            elif payload_type == "room_state":
                self.room = dict(payload["room"])
                self.local_player = Player(str(self.room["you_color"])) if "you_color" in self.room else None
                board_state = self.room.get("board_state")
                self.state = GameState.from_snapshot(board_state) if isinstance(board_state, dict) else GameState()
                self.message = str(self.room.get("message", self.message))
            elif payload_type == "error":
                self.message = str(payload.get("message", "Server rejected the action."))
            elif payload_type == "disconnect":
                self.disconnected = True
                self.room_closed = True
                self.message = str(payload.get("message", "Connection closed."))
        self.refresh_view()
        if self.room_closed:
            self.exit(0)

    def render_phase(self) -> str:
        if self.room is None:
            return super().render_phase()
        phase = str(self.room.get("phase", "")).upper()
        return f"[bold cyan]▶ {phase}[/bold cyan]"

    def render_info(self) -> str:
        black, white = self.state.get_scores()
        if self.room is None:
            lines = [
                "[bold]Room[/bold]",
                f"Status:   {self.state.status_text()}",
                f"Cursor:   {format_position(self.cursor_row, self.cursor_col)}",
                f"Last:     {self._last_move_text()}",
                f"Score:    B {black} / W {white}",
            ]
            if self.session_token is not None:
                lines.append(f"Token:    {self.session_token}")
            lines.extend(["", self.render_next_action()])
            return "\n".join(lines)

        scoreboard = self.room["scoreboard"]
        seats = {seat["player_color"]: seat for seat in self.room["seats"]}
        lines = [
            "[bold]Room[/bold]",
            f"Phase:    {self.room['phase']}",
            f"Round:    {self.room['round_number']}",
            f"Score:    B/W/D {scoreboard['black_wins']}/{scoreboard['white_wins']}/{scoreboard['draws']}",
            self._seat_status(Player.BLACK, seats.get(Player.BLACK.value, {})),
            self._seat_status(Player.WHITE, seats.get(Player.WHITE.value, {})),
            f"Status:   {self.state.status_text()}",
            f"Cursor:   {format_position(self.cursor_row, self.cursor_col)}",
            f"Last:     {self._last_move_text()}",
            f"Board:    B {black} / W {white}",
        ]
        if self.local_player is not None:
            lines.append(f"You:      {self.local_player.label}")
        if self.session_token is not None:
            lines.append(f"Token:    {self.session_token}")
        lines.extend(["", self.render_next_action()])
        return "\n".join(lines)

    def render_next_action(self) -> str:
        phase = "waiting_for_players" if self.room is None else str(self.room.get("phase", "waiting_for_players"))
        if phase != "in_game":
            return "[bold yellow]Next:[/bold yellow] Wait for the room to enter in_game."
        if self.local_player is None:
            return "[bold yellow]Next:[/bold yellow] Waiting for player assignment."
        if self.state.current_player is self.local_player:
            return "[bold green]Next:[/bold green] Choose a dotted square that flips a valuable edge."
        return f"[bold yellow]Next:[/bold yellow] Waiting for {self.state.current_player.label}."

    def _seat_status(self, color: Player, seat: dict[str, Any]) -> str:
        name = seat.get("name") or "(empty)"
        online = "online" if seat.get("connected") else "offline"
        ready = "ready" if seat.get("ready") else "not ready"
        return f"{color.stone} {color.label}: {name} [{online}, {ready}]"

    def action_confirm_action(self) -> None:
        phase = "waiting_for_players" if self.room is None else str(self.room.get("phase", "waiting_for_players"))
        if phase != "in_game":
            self.message = "The round is not running."
        elif self.local_player is None:
            self.message = "Still waiting for player assignment."
        elif self.state.current_player is not self.local_player:
            self.message = "It is not your turn."
        else:
            try:
                self.connection.send_move(self.cursor_row, self.cursor_col)
            except OSError:
                self.disconnected = True
                self.message = "Failed to send move. Connection closed."
            else:
                self.message = f"Submitted move at {format_position(self.cursor_row, self.cursor_col)}."
        self.refresh_view()

    def action_send_ready(self) -> None:
        try:
            self.connection.send_ready()
        except OSError:
            self.disconnected = True
            self.message = "Failed to send ready. Connection closed."
        else:
            self.message = "Ready sent."
        self.refresh_view()

    def action_send_resign(self) -> None:
        try:
            self.connection.send_resign()
        except OSError:
            self.disconnected = True
            self.message = "Failed to send resign. Connection closed."
        else:
            self.message = "Resignation sent."
        self.refresh_view()

    def action_close_room(self) -> None:
        try:
            self.connection.send_close_room()
        except OSError:
            self.disconnected = True
            self.message = "Failed to close room. Connection closed."
        else:
            self.message = "Room close requested."
        self.refresh_view()

    def action_quit_app(self) -> None:
        try:
            self.connection.send_leave()
        except OSError:
            pass
        self.exit(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "place":
            self.action_confirm_action()
        elif event.button.id == "ready":
            self.action_send_ready()
        elif event.button.id == "resign":
            self.action_send_resign()
        elif event.button.id == "close":
            self.action_close_room()


def run_local_game(*, theme: str = "modern") -> int:
    return LocalGameApp(theme=theme).run() or 0


def run_remote_client(
    host: str,
    port: int,
    name: str,
    session_token: str | None = None,
    theme: str = "modern",
) -> int:
    return RemoteGameApp(host, port, name, session_token, theme=theme).run() or 0
