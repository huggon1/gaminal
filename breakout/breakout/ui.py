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
    1: ("■", "bold white"),
    2: ("▪", "bold yellow"),
    3: ("▣", "bold red"),
    -1: ("▒", "dim"),
}


class BreakoutApp(ThemedApp):
    CSS = COMMON_CSS
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

    def compose(self) -> ComposeResult:
        yield Static("Breakout", id="app-title")
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
        self.set_interval(0.08, self.on_tick)
        self.refresh_view("Running")

    def on_tick(self) -> None:
        if self.paused or self.game.game_over or self.game.won:
            return
        self.game.step()
        if self.game.won:
            self.refresh_view("You win!")
        elif self.game.game_over:
            self.refresh_view("Game over")
        else:
            self.refresh_view("Running")

    def refresh_view(self, message: str) -> None:
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#stats-view", Static).update(self._render_stats())
        self.update_status(message)

    def _render_stats(self) -> str:
        g = self.game
        state = "Won!" if g.won else ("Game Over" if g.game_over else ("Paused" if self.paused else "Running"))
        mult = g._combo_multiplier()
        combo_str = f"{g.combo}x (×{mult})" if g.combo > 0 else "—"

        effects = []
        for k, ticks in g.active_effects.items():
            secs = round(ticks * 0.08)
            effects.append(f"{k}({secs}s)")
        effect_str = ", ".join(effects) if effects else "—"

        return (
            f"Score:  {g.score}\n"
            f"Lives:  {'♥ ' * g.lives}\n"
            f"Level:  {g.level}\n"
            f"Bricks: {g.brick_count}\n"
            f"Combo:  {combo_str}\n"
            f"Effect: {effect_str}\n"
            f"State:  {state}"
        )

    def render_board(self) -> Text:
        txt = Text()
        g = self.game

        ball_cells: set[tuple[int, int]] = set()
        for ball in g.balls:
            ball_cells.add((int(ball.row), int(ball.col)))

        powerup_cells: dict[tuple[int, int], tuple[str, str]] = {}
        for pu in g.powerups:
            pr, pc = int(pu.row), int(pu.col)
            ch, style = POWERUP_DISPLAY.get(pu.kind, ("?", "bold"))
            powerup_cells[(pr, pc)] = (ch, style)

        paddle_row = g.rows - 1

        txt.append("+" + "-" * g.cols + "+\n")
        for r in range(g.rows):
            txt.append("|")
            for c in range(g.cols):
                if (r, c) in ball_cells:
                    txt.append("o", style="bold yellow")
                elif (r, c) in powerup_cells:
                    ch, style = powerup_cells[(r, c)]
                    txt.append(ch, style=style)
                elif r == paddle_row and c in g.paddle_cells:
                    txt.append("=", style="bold cyan")
                elif g.board[r][c] != 0:
                    hp = g.board[r][c]
                    ch, style = BRICK_DISPLAY.get(hp, ("■", "bold white"))
                    txt.append(ch, style=style)
                else:
                    txt.append(" ")
            txt.append("|\n")
        txt.append("+" + "-" * g.cols + "+")
        return txt

    def action_move_left(self) -> None:
        self.game.move_paddle_left()
        self.refresh_view("Running")

    def action_move_right(self) -> None:
        self.game.move_paddle_right()
        self.refresh_view("Running")

    def action_toggle_pause(self) -> None:
        if self.game.game_over or self.game.won:
            return
        self.paused = not self.paused
        self.refresh_view("Paused" if self.paused else "Running")

    def action_restart(self) -> None:
        self.game.restart()
        self.paused = False
        self.refresh_view("Running")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()


def run_breakout_game(*, rows: int = 32, cols: int = 24, theme: str = "modern") -> int:
    return BreakoutApp(rows=rows, cols=cols, theme=theme).run() or 0
