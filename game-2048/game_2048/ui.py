from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import Game2048

TILE_STYLES = {
    0: "dim #31425f",
    2: "bold white",
    4: "bold cyan",
    8: "bold bright_cyan",
    16: "bold green",
    32: "bold bright_green",
    64: "bold yellow",
    128: "bold bright_yellow",
    256: "bold magenta",
    512: "bold bright_magenta",
    1024: "bold red",
    2048: "bold bright_red",
}


class Game2048App(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view {
            height: auto;
            padding-bottom: 1;
        }

        #board-view {
            text-style: bold;
        }

        #summary-view, #next-view {
            height: auto;
        }

        #control-row {
            height: auto;
            margin-top: 1;
        }

        #control-row Button {
            margin-right: 1;
            min-width: 10;
        }
        """
    )
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
        self.session_best = 0
        self.rounds_started = 1
        self.session_wins = 0
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("2048", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="summary-view")
                yield Static("", id="next-view")
                with Horizontal(id="control-row"):
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.lost:
            return "[bold red]★ NO MOVES ★[/bold red]"
        if self.game.won:
            return "[bold green]✦ 2048 REACHED ✦[/bold green]"
        return "[bold cyan]▶ BUILDING[/bold cyan]"

    def render_summary(self) -> str:
        max_tile = max(max(row) for row in self.game.board)
        target_bar = self._bar(max_tile, goal=2048, width=12)
        state = "Won" if self.game.won else "Lost" if self.game.lost else "Running"
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {self.game.score}",
                f"Best:     {max(self.session_best, self.game.score)}",
                f"Rounds:   {self.rounds_started}",
                f"Wins:     {self.session_wins}",
                f"Max tile: {max_tile}",
                f"Target:   {target_bar}",
                f"State:    {state}",
            ]
        )

    def render_next_action(self) -> str:
        if (self.game.won or self.game.lost) and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] Fresh board in {self._restart_countdown}s."
        if self.game.won:
            return "[bold yellow]Next:[/bold yellow] Celebration running."
        if self.game.lost:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        return "[bold green]Next:[/bold green] Push toward corners and keep one merge lane open."

    def render_board(self) -> Text:
        text = Text()
        max_value = max(max(row) for row in self.game.board)
        width = max(4, len(str(max_value)))
        border = "+" + "+".join(["-" * (width + 2)] * self.game.size) + "+\n"
        text.append(border, style="dim")
        for row in self.game.board:
            text.append("|", style="dim")
            for value in row:
                cell = "" if value == 0 else str(value)
                style = TILE_STYLES.get(value, "bold bright_white")
                text.append(f" {cell:>{width}} ", style=style)
                text.append("|", style="dim")
            text.append("\n")
            text.append(border, style="dim")
        return text

    def _do_move(self, direction: str) -> None:
        if self._restart_countdown is not None:
            return
        changed = self.game.move(direction)
        self.session_best = max(self.session_best, self.game.score)
        if self.game.won:
            self.session_wins += 1
            self.message = "2048 reached. New board queued."
            self._schedule_auto_restart()
        elif self.game.lost:
            self.message = "No moves left. New board queued."
            self._schedule_auto_restart()
        elif changed:
            self.message = f"Moved {direction}."
        else:
            self.message = "Move blocked."
        self.refresh_view()

    def action_move_up(self) -> None:
        self._do_move("up")

    def action_move_down(self) -> None:
        self._do_move("down")

    def action_move_left(self) -> None:
        self._do_move("left")

    def action_move_right(self) -> None:
        self._do_move("right")

    def action_restart_game(self) -> None:
        self._restart_round(manual=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.action_restart_game()

    def _schedule_auto_restart(self) -> None:
        self._restart_token += 1
        token = self._restart_token
        self._restart_countdown = 5
        for index, seconds_left in enumerate(range(5, 0, -1)):
            self.set_timer(
                float(index),
                lambda remaining=seconds_left, countdown_token=token: self._set_restart_countdown(countdown_token, remaining),
            )
        self.set_timer(5.0, lambda countdown_token=token: self._auto_restart(countdown_token))
        self.refresh_view()

    def _set_restart_countdown(self, token: int, seconds_left: int) -> None:
        if token != self._restart_token:
            return
        self._restart_countdown = seconds_left
        self.refresh_view()

    def _auto_restart(self, token: int) -> None:
        if token != self._restart_token:
            return
        self._restart_round(manual=False)

    def _restart_round(self, *, manual: bool) -> None:
        self._restart_token += 1
        self._restart_countdown = None
        self.session_best = max(self.session_best, self.game.score)
        self.game.restart()
        self.rounds_started += 1
        self.message = "Started a new board." if manual else "Fresh board started."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_2048_game(*, size: int = 4, theme: str = "modern") -> int:
    return Game2048App(size=size, theme=theme).run() or 0
