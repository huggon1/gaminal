from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import BreakoutGame

POWERUP_DISPLAY = {
    "expand": ("E", "bold green"),
    "extra_life": ("+", "bold bright_red"),
    "slow": ("S", "bold cyan"),
    "multi_ball": ("M", "bold magenta"),
    "shrink": ("s", "bold dark_red"),
}

BRICK_DISPLAY = {
    1: ("░", "bold white"),
    2: ("▒", "bold yellow"),
    3: ("▓", "bold red"),
    -1: ("■", "dim"),
}


class BreakoutApp(ThemedApp):
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
        Binding("space", "toggle_pause", "Pause"),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/AD paddle  Space pause  r restart  t theme  ? help  q quit"

    def __init__(self, rows: int = 32, cols: int = 24, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.game = BreakoutGame(rows=rows, cols=cols)
        self.paused = False
        self.message = "Break the wall and keep the ball alive."
        self.session_best = 0
        self.rounds_started = 1
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Breakout", id="app-title")
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
        self.set_interval(0.08, self.on_tick)
        self.refresh_view()

    def on_tick(self) -> None:
        if self.paused or self._restart_countdown is not None or self.game.game_over or self.game.won:
            return
        previous_score = self.game.score
        previous_level = self.game.level
        previous_lives = self.game.lives
        previous_effects = set(self.game.active_effects)
        self.game.step()
        self.session_best = max(self.session_best, self.game.score)
        if self.game.game_over:
            self.message = "Last life lost. New wall incoming."
            self._schedule_auto_restart()
        elif self.game.level != previous_level:
            self.message = f"Level up. Welcome to wall {self.game.level}."
        elif self.game.lives < previous_lives:
            self.message = f"Ball lost. {self.game.lives} life left."
        elif set(self.game.active_effects) != previous_effects:
            active = ", ".join(sorted(self.game.active_effects)) or "none"
            self.message = f"Power-up state changed: {active}."
        elif self.game.score > previous_score:
            self.message = f"Brick hit. Combo x{self.game._combo_multiplier()}."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.game_over:
            return "[bold red]★ GAME OVER ★[/bold red]"
        if self.paused:
            return "[bold yellow]⏸ PAUSED[/bold yellow]"
        return f"[bold cyan]▶ LEVEL {self.game.level}[/bold cyan]"

    def render_summary(self) -> str:
        g = self.game
        state = "Won!" if g.won else ("Game Over" if g.game_over else ("Paused" if self.paused else "Running"))
        combo_bar = self._bar(min(g.combo, 10), goal=10, width=10)
        effects = []
        for kind, ticks in sorted(g.active_effects.items()):
            secs = max(1, round(ticks * 0.08))
            effects.append(f"{kind} {secs}s")
        effect_str = ", ".join(effects) if effects else "none"
        hearts = "♥" * g.lives + "♡" * max(0, 5 - g.lives)
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {g.score}",
                f"Best:     {max(self.session_best, g.score)}",
                f"Rounds:   {self.rounds_started}",
                f"Lives:    {hearts}",
                f"Bricks:   {g.brick_count}",
                f"Combo:    x{g._combo_multiplier()}  {combo_bar}",
                f"Effects:  {effect_str}",
                f"State:    {state}",
            ]
        )

    def render_next_action(self) -> str:
        if self.game.game_over and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] Fresh wall in {self._restart_countdown}s."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        if self.paused:
            return "[bold yellow]Next:[/bold yellow] Press Space to resume the volley."
        return "[bold green]Next:[/bold green] Keep the paddle centered under the hottest ball."

    def render_board(self) -> Text:
        txt = Text()
        g = self.game

        ball_cells: set[tuple[int, int]] = set()
        for ball in g.balls:
            ball_cells.add((int(ball.row), int(ball.col)))

        powerup_cells: dict[tuple[int, int], tuple[str, str]] = {}
        for powerup in g.powerups:
            row, col = int(powerup.row), int(powerup.col)
            ch, style = POWERUP_DISPLAY.get(powerup.kind, ("?", "bold"))
            powerup_cells[(row, col)] = (ch, style)

        paddle_row = g.rows - 1
        txt.append("+" + "-" * g.cols + "+\n", style="dim")
        for row in range(g.rows):
            txt.append("|", style="dim")
            for col in range(g.cols):
                if (row, col) in ball_cells:
                    txt.append("●", style="bold yellow")
                elif (row, col) in powerup_cells:
                    ch, style = powerup_cells[(row, col)]
                    txt.append(ch, style=style)
                elif row == paddle_row and col in g.paddle_cells:
                    txt.append("═", style="bold cyan")
                elif g.board[row][col] != 0:
                    hp = g.board[row][col]
                    ch, style = BRICK_DISPLAY.get(hp, ("■", "bold white"))
                    txt.append(ch, style=style)
                else:
                    txt.append("·", style="dim #31425f")
            txt.append("|\n", style="dim")
        txt.append("+" + "-" * g.cols + "+", style="dim")
        return txt

    def action_move_left(self) -> None:
        self.game.move_paddle_left()
        self.message = "Paddle left."
        self.refresh_view()

    def action_move_right(self) -> None:
        self.game.move_paddle_right()
        self.message = "Paddle right."
        self.refresh_view()

    def action_toggle_pause(self) -> None:
        if self.game.game_over or self.game.won:
            return
        self.paused = not self.paused
        self.message = "Paused." if self.paused else "Volley resumed."
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
        self.message = "Wall reset." if manual else "Fresh wall loaded."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_breakout_game(*, rows: int = 32, cols: int = 24, theme: str = "modern") -> int:
    return BreakoutApp(rows=rows, cols=cols, theme=theme).run() or 0
