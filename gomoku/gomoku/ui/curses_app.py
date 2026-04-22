from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gomoku.core import BOARD_SIZE, GameState, Player
from gomoku.net.client import RemoteClientConnection


def _load_curses():
    try:
        import curses
    except ImportError as exc:
        raise RuntimeError("curses is required for the terminal UI and is typically available on Linux.") from exc
    return curses


@dataclass
class _RenderContext:
    state: GameState
    cursor_row: int
    cursor_col: int
    status_lines: list[str]
    footer_lines: list[str]


class _BoardRenderer:
    def __init__(self, curses_mod) -> None:
        self.curses = curses_mod

    def render(self, stdscr, context: _RenderContext) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        required_height = BOARD_SIZE + 7
        required_width = 4 + (BOARD_SIZE * 3)
        if height < required_height or width < required_width:
            self._safe_addstr(stdscr, 0, 0, f"Terminal too small. Need at least {required_width}x{required_height}.")
            self._safe_addstr(stdscr, 1, 0, f"Current size: {width}x{height}")
            stdscr.refresh()
            return

        start_y = 1
        start_x = 4

        self._safe_addstr(stdscr, 0, start_x, self._column_header())
        for row in range(BOARD_SIZE):
            self._safe_addstr(stdscr, start_y + row, 0, f"{row + 1:>2} ")
            for col in range(BOARD_SIZE):
                attr = self.curses.A_NORMAL
                if context.state.last_move and context.state.last_move.row == row and context.state.last_move.col == col:
                    attr |= self.curses.A_BOLD
                if context.cursor_row == row and context.cursor_col == col:
                    attr |= self.curses.A_REVERSE
                symbol = self._cell_symbol(context.state, row, col)
                self._safe_addstr(stdscr, start_y + row, start_x + (col * 3), f" {symbol} ", attr)

        info_y = start_y + BOARD_SIZE + 1
        for offset, line in enumerate(context.status_lines):
            self._safe_addstr(stdscr, info_y + offset, 0, line[: max(0, width - 1)])

        footer_y = info_y + len(context.status_lines) + 1
        for offset, line in enumerate(context.footer_lines):
            self._safe_addstr(stdscr, footer_y + offset, 0, line[: max(0, width - 1)])

        stdscr.refresh()

    def _column_header(self) -> str:
        labels = [chr(ord("A") + index) for index in range(BOARD_SIZE)]
        return "".join(f" {label} " for label in labels)

    def _cell_symbol(self, state: GameState, row: int, col: int) -> str:
        cell = state.board.grid[row][col]
        if cell is None:
            return "."
        return cell.stone

    def _safe_addstr(self, stdscr, row: int, col: int, text: str, attr: int = 0) -> None:
        try:
            stdscr.addstr(row, col, text, attr)
        except self.curses.error:
            pass


class LocalGameApp:
    def run(self) -> int:
        curses = _load_curses()
        return curses.wrapper(self._main)

    def _main(self, stdscr) -> int:
        curses = _load_curses()
        renderer = _BoardRenderer(curses)
        state = GameState()
        cursor_row = BOARD_SIZE // 2
        cursor_col = BOARD_SIZE // 2
        message = "Arrow keys move. Enter/Space places a stone."

        self._configure_screen(stdscr, curses, blocking=True)

        while True:
            footer = ["Controls: arrows move, Enter/Space place, q quit"]
            if state.finished:
                footer = ["Game over. Press any key to exit."]

            renderer.render(
                stdscr,
                _RenderContext(
                    state=state,
                    cursor_row=cursor_row,
                    cursor_col=cursor_col,
                    status_lines=[state.status_text(), message],
                    footer_lines=footer,
                ),
            )

            key = stdscr.getch()

            if state.finished:
                return 0

            if key in (ord("q"), ord("Q")):
                if self._confirm_quit(stdscr, curses):
                    return 0
                message = "Quit cancelled."
                continue

            moved = _move_cursor_from_key(key, cursor_row, cursor_col)
            if moved is not None:
                cursor_row, cursor_col = moved
                continue

            if key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                try:
                    state.play(cursor_row, cursor_col)
                except ValueError as exc:
                    message = str(exc)
                else:
                    if state.finished:
                        message = state.status_text()
                    else:
                        message = f"Placed {state.last_move.player.label} at {format_position(cursor_row, cursor_col)}."

    def _configure_screen(self, stdscr, curses, blocking: bool) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(-1 if blocking else 100)

    def _confirm_quit(self, stdscr, curses) -> bool:
        height, _width = stdscr.getmaxyx()
        prompt_row = min(height - 1, BOARD_SIZE + 6)
        stdscr.move(prompt_row, 0)
        stdscr.clrtoeol()
        stdscr.addstr(prompt_row, 0, "Quit current game? (y/N) ")
        stdscr.refresh()
        key = stdscr.getch()
        return key in (ord("y"), ord("Y"))


class RemoteGameApp:
    def __init__(self, host: str, port: int, name: str, session_token: str | None = None) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.session_token = session_token

    def run(self) -> int:
        connection = RemoteClientConnection(self.host, self.port, self.name, self.session_token)
        connection.connect()
        curses = _load_curses()
        try:
            return curses.wrapper(self._main, connection)
        finally:
            connection.close()

    def _main(self, stdscr, connection: RemoteClientConnection) -> int:
        curses = _load_curses()
        renderer = _BoardRenderer(curses)
        state = GameState()
        cursor_row = BOARD_SIZE // 2
        cursor_col = BOARD_SIZE // 2
        local_player: Player | None = None
        room: dict[str, Any] | None = None
        message = f"Connected to {self.host}:{self.port}. Joining room..."
        disconnected = False
        room_closed = False
        session_token = self.session_token

        self._configure_screen(stdscr, curses)

        while True:
            for payload in connection.poll_messages():
                payload_type = payload.get("type")
                if payload_type == "welcome":
                    session_token = str(payload["session_token"])
                    message = f"Joined as {payload['name']}. Session token saved for reconnect."
                elif payload_type == "room_state":
                    room = dict(payload["room"])
                    local_player = Player(str(room["you_color"]))
                    board_state = room.get("board_state")
                    state = GameState.from_snapshot(board_state) if isinstance(board_state, dict) else GameState()
                    message = str(room.get("message", ""))
                elif payload_type == "error":
                    message = str(payload.get("message", "Server rejected the action."))
                elif payload_type == "disconnect":
                    disconnected = True
                    room_closed = True
                    message = str(payload.get("message", "Connection closed."))

            phase = "waiting_for_players" if room is None else str(room.get("phase", "waiting_for_players"))
            footer = self._footer_lines(phase, local_player, state, disconnected)
            status = self._status_lines(room, local_player, state, cursor_row, cursor_col, message, session_token)

            renderer.render(
                stdscr,
                _RenderContext(
                    state=state,
                    cursor_row=cursor_row,
                    cursor_col=cursor_col,
                    status_lines=status,
                    footer_lines=footer,
                ),
            )

            key = stdscr.getch()

            if key == -1:
                continue

            if disconnected:
                return 0

            if key in (ord("q"), ord("Q")):
                try:
                    connection.send_leave()
                except OSError:
                    pass
                return 0

            moved = _move_cursor_from_key(key, cursor_row, cursor_col)
            if moved is not None:
                cursor_row, cursor_col = moved
                continue

            if key in (ord("r"), ord("R")):
                try:
                    connection.send_ready()
                except OSError:
                    disconnected = True
                    message = "Failed to send ready. Connection closed."
                else:
                    message = "Ready sent."
                continue

            if key in (ord("s"), ord("S")):
                try:
                    connection.send_resign()
                except OSError:
                    disconnected = True
                    message = "Failed to send resign. Connection closed."
                else:
                    message = "Resignation sent."
                continue

            if key in (ord("x"), ord("X")):
                try:
                    connection.send_close_room()
                except OSError:
                    disconnected = True
                    message = "Failed to close room. Connection closed."
                else:
                    message = "Room close requested."
                continue

            if key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                if phase != "in_game":
                    message = "The round is not running."
                elif local_player is None:
                    message = "Still waiting for player assignment."
                elif state.current_player is not local_player:
                    message = "It is not your turn."
                else:
                    try:
                        connection.send_move(cursor_row, cursor_col)
                    except OSError:
                        disconnected = True
                        message = "Failed to send move. Connection closed."
                    else:
                        message = f"Submitted move at {format_position(cursor_row, cursor_col)}."

            if room_closed:
                return 0

    def _configure_screen(self, stdscr, curses) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(100)

    def _footer_lines(self, phase: str, local_player: Player | None, state: GameState, disconnected: bool) -> list[str]:
        if disconnected or phase == "closed":
            return ["Session ended. Press any key to exit."]
        if phase == "waiting_for_players":
            return ["Waiting for another player.", "Press q to leave."]
        if phase == "waiting_ready":
            return ["Between rounds: press r when ready, q to leave."]
        if phase == "paused_reconnect":
            return ["Opponent disconnected: press x to close room, q to leave."]
        if local_player is not None and state.current_player is local_player:
            return ["Your turn: arrows move, Enter/Space send move, s resign, q leave"]
        return ["Opponent's turn: arrows move, s resign, q leave"]

    def _status_lines(
        self,
        room: dict[str, Any] | None,
        local_player: Player | None,
        state: GameState,
        cursor_row: int,
        cursor_col: int,
        message: str,
        session_token: str | None,
    ) -> list[str]:
        if room is None:
            lines = [state.status_text(), message]
            if session_token is not None:
                lines.append(f"Reconnect token: {session_token}")
            return lines

        scoreboard = room["scoreboard"]
        seats = {seat["player_color"]: seat for seat in room["seats"]}
        black = seats.get(Player.BLACK.value, {})
        white = seats.get(Player.WHITE.value, {})
        phase = str(room["phase"])
        lines = [
            f"Phase: {phase} | Round: {room['round_number']} | Score B/W/D: {scoreboard['black_wins']}/{scoreboard['white_wins']}/{scoreboard['draws']}",
            self._seat_status(Player.BLACK, black),
            self._seat_status(Player.WHITE, white),
        ]

        if phase == "in_game":
            lines.append(state.status_text())
        if local_player is not None:
            lines.append(f"You are {local_player.label}. Cursor at {format_position(cursor_row, cursor_col)}.")
        lines.append(message)
        if session_token is not None:
            lines.append(f"Reconnect token: {session_token}")
        return lines

    def _seat_status(self, color: Player, seat: dict[str, Any]) -> str:
        name = seat.get("name") or "(empty)"
        online = "online" if seat.get("connected") else "offline"
        ready = "ready" if seat.get("ready") else "not ready"
        return f"{color.label}: {name} [{online}, {ready}]"


def _move_cursor_from_key(key: int, row: int, col: int) -> tuple[int, int] | None:
    if key == _load_curses().KEY_UP:
        return max(0, row - 1), col
    if key == _load_curses().KEY_DOWN:
        return min(BOARD_SIZE - 1, row + 1), col
    if key == _load_curses().KEY_LEFT:
        return row, max(0, col - 1)
    if key == _load_curses().KEY_RIGHT:
        return row, min(BOARD_SIZE - 1, col + 1)
    return None


def format_position(row: int, col: int) -> str:
    return f"{chr(ord('A') + col)}{row + 1}"


def run_local_game() -> int:
    return LocalGameApp().run()


def run_remote_client(host: str, port: int, name: str, session_token: str | None = None) -> int:
    return RemoteGameApp(host, port, name, session_token).run()
