from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import SnakeGame


class SnakeApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view {
            height: auto;
            padding-bottom: 1;
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
            min-width: 11;
        }
        """
    )
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
        self.message = "Collect fruit and keep the head inside the arena."
        self.session_best = 0
        self.rounds_started = 1
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Snake", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="summary-view")
                yield Static("", id="next-view")
                with Horizontal(id="control-row"):
                    yield Button("Pause", id="pause")
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.set_interval(0.18, self.on_tick)
        self.refresh_view()

    def on_tick(self) -> None:
        if self.paused or self._restart_countdown is not None or self.game.game_over:
            return
        previous_score = self.game.score
        self.game.step()
        if self.game.game_over:
            self.session_best = max(self.session_best, self.game.score)
            self.message = "Snake crashed. New round queued."
            self._schedule_auto_restart()
        elif self.game.score > previous_score:
            self.session_best = max(self.session_best, self.game.score)
            self.message = f"Fruit eaten. Score {self.game.score}."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.game_over:
            return "[bold red]★ CRASH ★[/bold red]"
        if self.paused:
            return "[bold yellow]⏸ PAUSED[/bold yellow]"
        return "[bold cyan]▶ HUNTING[/bold cyan]"

    def render_summary(self) -> str:
        state = "Paused" if self.paused else ("Over" if self.game.game_over else "Running")
        progress = self._bar(self.game.score, goal=max(6, self.session_best or 3), width=12)
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {self.game.score}",
                f"Best:     {max(self.session_best, self.game.score)}",
                f"Length:   {len(self.game.snake)}",
                f"Rounds:   {self.rounds_started}",
                f"Growth:   {progress}",
                f"State:    {state}",
            ]
        )

    def render_next_action(self) -> str:
        if self.game.game_over and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] New round in {self._restart_countdown}s."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        if self.paused:
            return "[bold yellow]Next:[/bold yellow] Press Space to resume the run."
        return "[bold green]Next:[/bold green] Guide the head to fruit and avoid walls."

    def render_board(self) -> Text:
        snake_set = set(self.game.snake)
        head = self.game.snake[-1]
        txt = Text()
        txt.append("+" + "-" * self.game.cols + "+\n", style="dim")
        for r in range(self.game.rows):
            txt.append("|", style="dim")
            for c in range(self.game.cols):
                pos = (r, c)
                if pos == head:
                    style = "bold bright_red" if self.game.game_over else "bold bright_green"
                    txt.append("@", style=style)
                elif pos in snake_set:
                    txt.append("o", style="green")
                elif pos == self.game.food:
                    txt.append("✦", style="bold yellow")
                else:
                    txt.append("·", style="dim #31425f")
            txt.append("|\n", style="dim")
        txt.append("+" + "-" * self.game.cols + "+", style="dim")
        return txt

    def action_up(self) -> None:
        self.game.change_direction("up")
        self.message = "Heading up."
        self.refresh_view()

    def action_down(self) -> None:
        self.game.change_direction("down")
        self.message = "Heading down."
        self.refresh_view()

    def action_left(self) -> None:
        self.game.change_direction("left")
        self.message = "Heading left."
        self.refresh_view()

    def action_right(self) -> None:
        self.game.change_direction("right")
        self.message = "Heading right."
        self.refresh_view()

    def action_toggle_pause(self) -> None:
        if self.game.game_over:
            return
        self.paused = not self.paused
        self.message = "Paused." if self.paused else "Run resumed."
        self.refresh_view()

    def action_restart(self) -> None:
        self._restart_round(manual=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()

    def _schedule_auto_restart(self) -> None:
        self._restart_token += 1
        token = self._restart_token
        self._restart_countdown = 5
        for index, seconds_left in enumerate(range(5, 0, -1)):
            self.set_timer(float(index), lambda remaining=seconds_left, countdown_token=token: self._set_restart_countdown(countdown_token, remaining))
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
        self.paused = False
        self.rounds_started += 1
        self.message = "Round restarted." if manual else "Fresh round started."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_snake_game(*, rows: int = 16, cols: int = 24, theme: str = "modern") -> int:
    return SnakeApp(rows=rows, cols=cols, theme=theme).run() or 0
