from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import RacingGame


class RacingApp(ThemedApp):
    CSS = COMMON_CSS
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

    def compose(self) -> ComposeResult:
        yield Static("Racing", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="board-view")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
                yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.set_interval(0.05, self.on_tick)
        self.refresh_view("Steer to stay in the gap!")

    def on_tick(self) -> None:
        if self.game.game_over:
            return
        self.game.step()
        self.refresh_view("Game over!" if self.game.game_over else "Dodge!")

    def refresh_view(self, message: str) -> None:
        self.query_one("#board-view", Static).update(self.render_road())
        g = self.game
        self.query_one("#stats-view", Static).update(
            f"Score:  {g.score}\n"
            f"Coins:  {g.coins_collected}\n"
            f"Speed:  {'▮' * g.speed_level}{'▯' * (4 - min(g.speed_level, 4))}\n"
            f"Gap:    {'█' * g.current_gap_width}{'░' * (g.GAP_START - g.current_gap_width)}\n"
            f"State:  {'GAME OVER' if g.game_over else 'Running'}"
        )
        self.update_status(message)

    def render_road(self) -> Text:
        g = self.game
        txt = Text()
        player_row = g.road_rows - 1
        txt.append("+" + "-" * g.road_cols + "+\n")
        for r in range(g.road_rows):
            txt.append("|")
            for c in range(g.road_cols):
                is_wall = g.is_wall(r, c)
                is_player = r == player_row and c == g.player_col
                is_coin = g.has_coin(r, c)
                if is_player:
                    style = "bold bright_red" if g.game_over else "bold green"
                    txt.append("X" if g.game_over else "^", style=style)
                elif is_wall:
                    txt.append("#", style="bold red")
                elif is_coin:
                    txt.append("*", style="bold yellow")
                else:
                    txt.append(" ")
            txt.append("|\n")
        txt.append("+" + "-" * g.road_cols + "+")
        return txt

    def action_move_left(self) -> None:
        self.game.move_left()
        self.refresh_view("Dodge!")

    def action_move_right(self) -> None:
        self.game.move_right()
        self.refresh_view("Dodge!")

    def action_restart(self) -> None:
        self.game.restart()
        self.refresh_view("Steer to stay in the gap!")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "restart":
            self.action_restart()


def run_racing_game(*, rows: int = 20, cols: int = 15, theme: str = "modern") -> int:
    return RacingApp(rows=rows, cols=cols, theme=theme).run() or 0
