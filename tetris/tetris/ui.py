from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static
from textual.timer import Timer

from ._textual_base import COMMON_CSS, ThemedApp
from .core import TetrisGame, TETROMINOES

PIECE_COLORS: dict[str, str] = {
    "I": "cyan",
    "O": "yellow",
    "T": "magenta",
    "S": "green",
    "Z": "red",
    "J": "blue",
    "L": "bright_red",
}


class TetrisApp(ThemedApp):
    CSS = COMMON_CSS
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("left", "move_left", show=False),
        Binding("right", "move_right", show=False),
        Binding("a", "move_left", show=False),
        Binding("d", "move_right", show=False),
        Binding("down", "soft_drop", show=False),
        Binding("s", "soft_drop", show=False),
        Binding("up", "rotate", show=False),
        Binding("w", "rotate", show=False),
        Binding("space", "hard_drop", "Hard drop"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/WASD move  Space hard drop  p pause  r restart  t theme  ? help  q quit"

    def __init__(self, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = TetrisGame()
        self.paused = False
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static("Tetris", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="board-view")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
                yield Static("", id="next-view")
                yield Button("Pause/Resume", id="pause")
                yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self._reset_timer()
        self.refresh_view("Running")

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(self.game.tick_interval, self.on_tick)

    def on_tick(self) -> None:
        if self.paused or self.game.game_over:
            return
        old_level = self.game.level
        self.game.gravity_step()
        if self.game.level != old_level:
            self._reset_timer()
        self.refresh_view("Game over" if self.game.game_over else "Running")

    def refresh_view(self, message: str) -> None:
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#stats-view", Static).update(
            f"Score: {self.game.score}\n"
            f"Lines: {self.game.lines}\n"
            f"Level: {self.game.level}\n"
            f"State: {'Paused' if self.paused else ('Over' if self.game.game_over else 'Running')}"
        )
        self.query_one("#next-view", Static).update(self.render_next())
        self.update_status(message)

    def render_board(self) -> Text:
        txt = Text()
        if not self.game.game_over:
            ghost_cells = set(self.game.ghost_piece().cells())
            current_cells = set(self.game.current.cells())
            current_kind = self.game.current.kind
        else:
            ghost_cells = set()
            current_cells = set()
            current_kind = "I"

        txt.append("+" + "-" * self.game.COLS + "+\n")
        for r in range(self.game.ROWS):
            txt.append("|")
            for c in range(self.game.COLS):
                if (r, c) in current_cells:
                    color = PIECE_COLORS.get(current_kind, "white")
                    txt.append(current_kind, style=f"bold {color}")
                elif (r, c) in ghost_cells:
                    txt.append(".", style="dim")
                elif self.game.board[r][c] is not None:
                    kind = self.game.board[r][c]
                    color = PIECE_COLORS.get(kind, "white")
                    txt.append(kind, style=color)
                else:
                    txt.append(" ")
            txt.append("|\n")
        txt.append("+" + "-" * self.game.COLS + "+")
        return txt

    def render_next(self) -> Text:
        txt = Text("Next:\n")
        kind = self.game.next_kind
        offsets = TETROMINOES[kind][0]
        cells = {(dr, dc) for dr, dc in offsets}
        min_r = min(dr for dr, _ in offsets)
        min_c = min(dc for _, dc in offsets)
        max_r = max(dr for dr, _ in offsets)
        max_c = max(dc for _, dc in offsets)
        color = PIECE_COLORS.get(kind, "white")
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                if (r, c) in cells:
                    txt.append(kind, style=f"bold {color}")
                else:
                    txt.append(" ")
            txt.append("\n")
        return txt

    def action_move_left(self) -> None:
        self.game.move_left()
        self.refresh_view("Running")

    def action_move_right(self) -> None:
        self.game.move_right()
        self.refresh_view("Running")

    def action_soft_drop(self) -> None:
        self.game.soft_drop()
        self.refresh_view("Running")

    def action_rotate(self) -> None:
        self.game.rotate()
        self.refresh_view("Running")

    def action_hard_drop(self) -> None:
        self.game.hard_drop()
        self.refresh_view("Running")

    def action_toggle_pause(self) -> None:
        if self.game.game_over:
            return
        self.paused = not self.paused
        self.refresh_view("Paused" if self.paused else "Running")

    def action_restart(self) -> None:
        self.game.restart()
        self.paused = False
        self._reset_timer()
        self.refresh_view("Running")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()


def run_tetris_game(*, theme: str = "modern") -> int:
    return TetrisApp(theme=theme).run() or 0
