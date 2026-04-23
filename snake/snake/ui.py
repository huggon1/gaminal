from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import SnakeGame


class SnakeApp(ThemedApp):
    CSS = COMMON_CSS
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "up", show=False),
        Binding("down", "down", show=False),
        Binding("left", "left", show=False),
        Binding("right", "right", show=False),
        Binding("w", "up", show=False),
        Binding("s", "down", show=False),
        Binding("a", "left", show=False),
        Binding("d", "right", show=False),
        Binding("space", "toggle_pause", "Pause"),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/WASD direction  Space pause  r restart  t theme  ? help  q quit"

    def __init__(self, rows: int = 16, cols: int = 24, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = SnakeGame(rows=rows, cols=cols)
        self.paused = False

    def compose(self) -> ComposeResult:
        yield Static("Snake", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="board-view")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
                yield Button("Pause/Resume", id="pause")
                yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.set_interval(0.18, self.on_tick)
        self.refresh_view("Running")

    def on_tick(self) -> None:
        if self.paused or self.game.game_over:
            return
        self.game.step()
        msg = "Game over" if self.game.game_over else "Running"
        self.refresh_view(msg)

    def refresh_view(self, message: str) -> None:
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#stats-view", Static).update(
            f"Score: {self.game.score}\nLength: {len(self.game.snake)}\nState: {'Paused' if self.paused else ('Over' if self.game.game_over else 'Running')}"
        )
        self.update_status(message)

    def render_board(self) -> Text:
        snake_set = set(self.game.snake)
        head = self.game.snake[-1]
        txt = Text()
        txt.append("+" + "-" * self.game.cols + "+\n")
        for r in range(self.game.rows):
            txt.append("|")
            for c in range(self.game.cols):
                pos = (r, c)
                if pos == head:
                    txt.append("@")
                elif pos in snake_set:
                    txt.append("o")
                elif pos == self.game.food:
                    txt.append("*")
                else:
                    txt.append(" ")
            txt.append("|\n")
        txt.append("+" + "-" * self.game.cols + "+")
        return txt

    def action_up(self) -> None: self.game.change_direction("up")
    def action_down(self) -> None: self.game.change_direction("down")
    def action_left(self) -> None: self.game.change_direction("left")
    def action_right(self) -> None: self.game.change_direction("right")

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self.refresh_view("Paused" if self.paused else "Resumed")

    def action_restart(self) -> None:
        self.game.restart()
        self.paused = False
        self.refresh_view("Restarted")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()


def run_snake_game(*, rows: int = 16, cols: int = 24, theme: str = "modern") -> int:
    return SnakeApp(rows=rows, cols=cols, theme=theme).run() or 0
