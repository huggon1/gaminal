from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import RacingGame


class RacingApp(ThemedApp):
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
        Binding("left", "move_left", show=False),
        Binding("right", "move_right", show=False),
        Binding("a", "move_left", show=False),
        Binding("d", "move_right", show=False),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/AD steer  r restart  t theme  ? help  q quit"

    def __init__(self, rows: int = 20, cols: int = 15, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = RacingGame(road_rows=rows, road_cols=cols)
        self.message = "Stay inside the gap and collect coins."
        self.session_best = 0
        self.rounds_started = 1
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Racing", id="app-title")
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
        self.set_interval(0.05, self.on_tick)
        self.refresh_view()

    def on_tick(self) -> None:
        if self._restart_countdown is not None or self.game.game_over:
            return
        previous_score = self.game.score
        previous_coins = self.game.coins_collected
        previous_speed = self.game.speed_level
        previous_gap = self.game.current_gap_width
        self.game.step()
        self.session_best = max(self.session_best, self.game.score)
        if self.game.game_over:
            self.message = "You clipped the wall. Resetting the road."
            self._schedule_auto_restart()
        elif self.game.coins_collected > previous_coins:
            self.message = f"Coin collected. Total coins {self.game.coins_collected}."
        elif self.game.speed_level != previous_speed:
            self.message = f"Speed up. Level {self.game.speed_level} drift."
        elif self.game.current_gap_width < previous_gap:
            self.message = "The road narrowed."
        elif self.game.score > previous_score and self.game.score % 50 == 0:
            self.message = f"Distance {self.game.score}."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_road())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.game_over:
            return "[bold red]★ CRASH ★[/bold red]"
        return f"[bold cyan]▶ SPEED {self.game.speed_level}[/bold cyan]"

    def render_summary(self) -> str:
        g = self.game
        speed = "★" * min(g.speed_level, 4) + "☆" * max(0, 4 - min(g.speed_level, 4))
        gap_bar = self._bar(g.current_gap_width, goal=g.GAP_START, width=g.GAP_START)
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {g.score}",
                f"Best:     {max(self.session_best, g.score)}",
                f"Rounds:   {self.rounds_started}",
                f"Coins:    {g.coins_collected}",
                f"Speed:    {speed}",
                f"Gap:      {gap_bar}",
                f"Drift:    {g.frame}f",
                f"State:    {'Over' if g.game_over else 'Running'}",
            ]
        )

    def render_next_action(self) -> str:
        if self.game.game_over and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] New road in {self._restart_countdown}s."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        return "[bold green]Next:[/bold green] Read the next gap early and steer one lane at a time."

    def render_road(self) -> Text:
        g = self.game
        txt = Text()
        player_row = g.road_rows - 1
        txt.append("+" + "-" * g.road_cols + "+\n", style="dim")
        for row in range(g.road_rows):
            txt.append("|", style="dim")
            for col in range(g.road_cols):
                is_wall = g.is_wall(row, col)
                is_player = row == player_row and col == g.player_col
                is_coin = g.has_coin(row, col)
                if is_player:
                    style = "bold bright_red" if g.game_over else "bold bright_cyan"
                    txt.append("▲" if not g.game_over else "✕", style=style)
                elif is_wall:
                    txt.append("█", style="bold red")
                elif is_coin:
                    txt.append("◆", style="bold yellow")
                else:
                    txt.append("·", style="dim #31425f")
            txt.append("|\n", style="dim")
        txt.append("+" + "-" * g.road_cols + "+", style="dim")
        return txt

    def action_move_left(self) -> None:
        self.game.move_left()
        self.message = "Steered left."
        self.refresh_view()

    def action_move_right(self) -> None:
        self.game.move_right()
        self.message = "Steered right."
        self.refresh_view()

    def action_restart(self) -> None:
        self._restart_round(manual=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.action_restart()

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
        self.message = "Road reset." if manual else "Fresh road loaded."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_racing_game(*, rows: int = 20, cols: int = 15, theme: str = "modern") -> int:
    return RacingApp(rows=rows, cols=cols, theme=theme).run() or 0
