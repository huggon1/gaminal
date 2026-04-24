from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import RapidRollGame

ITEM_DISPLAY = {
    "coin": ("◆", "bold yellow"),
    "heart": ("♥", "bold bright_red"),
    "slow": ("S", "bold cyan"),
}


class RapidRollApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view {
            height: auto;
            padding-bottom: 1;
        }

        #board-view {
            height: 1fr;
            width: auto;
            content-align: left top;
        }

        #summary-view, #next-view, #legend-view {
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
        Binding("space", "toggle_pause", "Pause"),
        Binding("p", "toggle_pause", show=False),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/AD roll  Space/p pause  r restart  t theme  ? help  q quit"

    def __init__(self, rows: int = 24, cols: int = 22, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = RapidRollGame(rows=rows, cols=cols)
        self.paused = False
        self.message = "Roll sideways and keep dropping to the next platform."
        self.session_best = 0
        self.rounds_started = 1
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Rapid Roll", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="summary-view")
                yield Static("", id="legend-view")
                yield Static("", id="next-view")
                with Horizontal(id="control-row"):
                    yield Button("Pause", id="pause")
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.set_interval(0.05, self.on_tick)
        self.refresh_view()

    def on_tick(self) -> None:
        if self.paused or self._restart_countdown is not None or self.game.game_over:
            return
        previous_score = self.game.score
        previous_lives = self.game.lives
        previous_landings = self.game.landings
        previous_effects = set(self.game.active_effects)
        self.game.step()
        self.session_best = max(self.session_best, self.game.score)
        if self.game.game_over:
            self.message = "No lives left. New drop incoming."
            self._schedule_auto_restart()
        elif self.game.lives < previous_lives:
            self.message = f"Hit the danger edge. {self.game.lives} life left."
        elif self.game.lives > previous_lives:
            self.message = "Extra life collected."
        elif self.game.last_event == "coin":
            self.message = "Coin collected."
        elif self.game.last_event == "slow":
            self.message = "Slow field active."
        elif self.game.landings > previous_landings:
            self.message = f"Platform caught. Drop streak {self.game.landings}."
        elif set(self.game.active_effects) != previous_effects:
            self.message = "Slow field faded."
        elif self.game.score > previous_score and self.game.score % 100 == 0:
            self.message = f"Score {self.game.score}. The platforms are climbing faster."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#legend-view", Static).update(self.render_legend())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.game_over:
            return "[bold red]★ GAME OVER ★[/bold red]"
        if self.paused:
            return "[bold yellow]⏸ PAUSED[/bold yellow]"
        return f"[bold cyan]▶ SPEED {self.game.speed_level}[/bold cyan]"

    def render_summary(self) -> str:
        g = self.game
        hearts = "♥" * g.lives + "♡" * max(0, g.MAX_LIVES - g.lives)
        speed = "★" * g.speed_level + "☆" * max(0, 5 - g.speed_level)
        drop_bar = self._bar(min(g.landings, 12), goal=12, width=12)
        effects = []
        for kind, ticks in sorted(g.active_effects.items()):
            secs = max(1, round(ticks * 0.05))
            effects.append(f"{kind} {secs}s")
        effect_str = ", ".join(effects) if effects else "none"
        state = "Over" if g.game_over else ("Paused" if self.paused else "Running")
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {g.score}",
                f"Best:     {max(self.session_best, g.score)}",
                f"Rounds:   {self.rounds_started}",
                f"Lives:    {hearts}",
                f"Speed:    {speed}",
                f"Drops:    {g.landings}  {drop_bar}",
                f"Effects:  {effect_str}",
                f"State:    {state}",
            ]
        )

    def render_legend(self) -> str:
        return "\n".join(
            [
                "[bold]Pickups[/bold]",
                "[yellow]◆[/yellow] coin +50",
                "[bright_red]♥[/bright_red] life",
                "[cyan]S[/cyan] slow",
            ]
        )

    def render_next_action(self) -> str:
        if self.game.game_over and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] New drop in {self._restart_countdown}s."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        if self.paused:
            return "[bold yellow]Next:[/bold yellow] Press Space to resume the fall."
        return "[bold green]Next:[/bold green] Roll toward the next lower platform before the edge catches you."

    def render_board(self) -> Text:
        g = self.game
        txt = Text()
        platform_cells = g.platform_cells()
        item_cells: dict[tuple[int, int], tuple[str, str]] = {}
        for item in g.items:
            row = int(round(item.row))
            if 0 <= row < g.rows:
                item_cells[(row, item.col)] = ITEM_DISPLAY.get(item.kind, ("?", "bold"))

        ball_cell = (int(round(g.ball_row)), int(round(g.ball_col)))
        txt.append("+" + "^" * g.cols + "+\n", style="bold red")
        for row in range(g.rows):
            txt.append("|", style="dim")
            for col in range(g.cols):
                pos = (row, col)
                if pos == ball_cell:
                    style = "bold bright_red" if g.game_over else "bold bright_cyan"
                    txt.append("●", style=style)
                elif pos in item_cells:
                    ch, style = item_cells[pos]
                    txt.append(ch, style=style)
                elif pos in platform_cells:
                    txt.append("═", style="bold green")
                else:
                    txt.append("·", style="dim #31425f")
            txt.append("|\n", style="dim")
        txt.append("+" + "v" * g.cols + "+", style="bold red")
        return txt

    def action_move_left(self) -> None:
        self.game.move_left()
        self.message = "Rolled left."
        self.refresh_view()

    def action_move_right(self) -> None:
        self.game.move_right()
        self.message = "Rolled right."
        self.refresh_view()

    def action_toggle_pause(self) -> None:
        if self.game.game_over:
            return
        self.paused = not self.paused
        self.message = "Paused." if self.paused else "Drop resumed."
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
        self.paused = False
        self.rounds_started += 1
        self.message = "Drop reset." if manual else "Fresh drop loaded."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_rapid_roll_game(*, rows: int = 24, cols: int = 22, theme: str = "modern") -> int:
    return RapidRollApp(rows=rows, cols=cols, theme=theme).run() or 0
