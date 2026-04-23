from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import Game2048


class Game2048App(ThemedApp):
    CSS = COMMON_CSS + """
    #board-view { text-style: bold; }
    #control-row { height: auto; }
    #control-row Button { margin-right: 1; min-width: 8; }
    """
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_up", "Up"),
        Binding("down", "move_down", "Down"),
        Binding("left", "move_left", "Left"),
        Binding("right", "move_right", "Right"),
        Binding("w", "move_up", show=False),
        Binding("a", "move_left", show=False),
        Binding("s", "move_down", show=False),
        Binding("d", "move_right", show=False),
        Binding("r", "restart_game", "Restart"),
    ]
    help_text = "Arrows/WASD move  r restart  t theme  ? help  q quit"

    def __init__(self, size: int = 4, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = Game2048(size=size)
        self.message = "Slide tiles to combine numbers."

    def compose(self) -> ComposeResult:
        yield Static("2048", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="board-view")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
                with Horizontal(id="control-row"):
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#board-view", Static).update(self.render_board())
        state = "Won" if self.game.won else "Lost" if self.game.lost else "Running"
        self.query_one("#stats-view", Static).update(f"Score: {self.game.score}\nState: {state}\nTarget: 2048")
        self.update_status(self.message)

    def render_board(self) -> Text:
        text = Text()
        width = max(4, len(str(max(max(r) for r in self.game.board))))
        border = "+" + "+".join(["-" * (width + 2)] * self.game.size) + "+\n"
        text.append(border)
        for row in self.game.board:
            text.append("|")
            for value in row:
                cell = "" if value == 0 else str(value)
                text.append(f" {cell:>{width}} |")
            text.append("\n" + border)
        return text

    def _do_move(self, direction: str) -> None:
        changed = self.game.move(direction)
        if self.game.won:
            self.message = "You reached 2048!"
        elif self.game.lost:
            self.message = "No moves left."
        elif changed:
            self.message = f"Moved {direction}."
        else:
            self.message = "Move blocked."
        self.refresh_view()

    def action_move_up(self) -> None: self._do_move("up")
    def action_move_down(self) -> None: self._do_move("down")
    def action_move_left(self) -> None: self._do_move("left")
    def action_move_right(self) -> None: self._do_move("right")

    def action_restart_game(self) -> None:
        self.game.restart()
        self.message = "Started a new game."
        self.refresh_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.action_restart_game()


def run_2048_game(*, size: int = 4, theme: str = "modern") -> int:
    return Game2048App(size=size, theme=theme).run() or 0
