from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import TETROMINOES, TetrisGame

PIECE_COLORS: dict[str, str] = {
    "I": "cyan",
    "O": "yellow",
    "T": "magenta",
    "S": "green",
    "Z": "red",
    "J": "blue",
    "L": "bright_red",
}

ACTIVE_CELL = "[]"
LOCKED_CELL = "[]"
GHOST_CELL = ".."
EMPTY_CELL = "  "


class TetrisApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view {
            height: auto;
            padding-bottom: 1;
        }

        #summary-view, #next-piece-view, #next-view {
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
        self.message = "Stack cleanly and keep the well open."
        self.session_best = 0
        self.rounds_started = 1
        self._restart_token = 0
        self._restart_countdown: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("Tetris", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="summary-view")
                yield Static("", id="next-piece-view")
                yield Static("", id="next-view")
                with Horizontal(id="control-row"):
                    yield Button("Pause", id="pause")
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self._reset_timer()
        self.refresh_view()

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(self.game.tick_interval, self.on_tick)

    def on_tick(self) -> None:
        if self.paused or self._restart_countdown is not None or self.game.game_over:
            return
        previous_score = self.game.score
        previous_lines = self.game.lines
        previous_level = self.game.level
        self.game.gravity_step()
        self.session_best = max(self.session_best, self.game.score)
        if self.game.level != previous_level:
            self._reset_timer()
        if self.game.game_over:
            self.message = "Stack topped out. Fresh well incoming."
            self._schedule_auto_restart()
        elif self.game.lines > previous_lines:
            cleared = self.game.lines - previous_lines
            self.message = f"Cleared {cleared} line(s)."
        elif self.game.score > previous_score:
            self.message = "Piece locked."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-piece-view", Static).update(self.render_next_piece())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.game.game_over:
            return "[bold red]* TOP OUT *[/bold red]"
        if self.paused:
            return "[bold yellow]|| PAUSED[/bold yellow]"
        return f"[bold cyan]> LEVEL {self.game.level}[/bold cyan]"

    def render_summary(self) -> str:
        g = self.game
        line_bar = self._bar(g.lines % 10, goal=10, width=10)
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Score:    {g.score}",
                f"Best:     {max(self.session_best, g.score)}",
                f"Rounds:   {self.rounds_started}",
                f"Lines:    {g.lines}",
                f"Level:    {g.level}",
                f"To next:  {line_bar}",
                f"State:    {'Paused' if self.paused else ('Over' if g.game_over else 'Running')}",
            ]
        )

    def render_next_action(self) -> str:
        if self.game.game_over and self._restart_countdown is not None:
            return f"[bold yellow]Next:[/bold yellow] New stack in {self._restart_countdown}s."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        if self.paused:
            return "[bold yellow]Next:[/bold yellow] Press p to resume gravity."
        return "[bold green]Next:[/bold green] Keep the center open and watch the next piece."

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

        inner_width = self.game.COLS * len(EMPTY_CELL)
        txt.append("+" + "-" * inner_width + "+\n", style="dim")
        for row in range(self.game.ROWS):
            txt.append("|", style="dim")
            for col in range(self.game.COLS):
                if (row, col) in current_cells:
                    color = PIECE_COLORS.get(current_kind, "white")
                    txt.append(ACTIVE_CELL, style=f"bold {color}")
                elif (row, col) in ghost_cells:
                    txt.append(GHOST_CELL, style="dim white")
                elif self.game.board[row][col] is not None:
                    kind = self.game.board[row][col]
                    color = PIECE_COLORS.get(kind, "white")
                    txt.append(LOCKED_CELL, style=color)
                else:
                    txt.append(EMPTY_CELL, style="dim #31425f")
            txt.append("|\n", style="dim")
        txt.append("+" + "-" * inner_width + "+", style="dim")
        return txt

    def render_next_piece(self) -> Text:
        txt = Text("Next piece:\n", style="bold")
        kind = self.game.next_kind
        offsets = TETROMINOES[kind][0]
        cells = {(dr, dc) for dr, dc in offsets}
        min_row = min(dr for dr, _ in offsets)
        min_col = min(dc for _, dc in offsets)
        max_row = max(dr for dr, _ in offsets)
        max_col = max(dc for _, dc in offsets)
        color = PIECE_COLORS.get(kind, "white")
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                if (row, col) in cells:
                    txt.append(ACTIVE_CELL, style=f"bold {color}")
                else:
                    txt.append(EMPTY_CELL)
            txt.append("\n")
        return txt

    def action_move_left(self) -> None:
        moved = self.game.move_left()
        self.message = "Moved left." if moved else "Left wall blocked the piece."
        self.refresh_view()

    def action_move_right(self) -> None:
        moved = self.game.move_right()
        self.message = "Moved right." if moved else "Right wall blocked the piece."
        self.refresh_view()

    def action_soft_drop(self) -> None:
        moved = self.game.soft_drop()
        self.message = "Soft drop." if moved else "Piece locked."
        self.refresh_view()

    def action_rotate(self) -> None:
        rotated = self.game.rotate()
        self.message = "Rotated." if rotated else "Rotation blocked."
        self.refresh_view()

    def action_hard_drop(self) -> None:
        if self.game.game_over:
            return
        self.game.hard_drop()
        self.message = "Hard drop."
        self.refresh_view()

    def action_toggle_pause(self) -> None:
        if self.game.game_over:
            return
        self.paused = not self.paused
        self.message = "Paused." if self.paused else "Gravity resumed."
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
        self._reset_timer()
        self.message = "Well reset." if manual else "Fresh stack started."
        self.refresh_view()

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'#' * filled}{'-' * (width - filled)}"


def run_tetris_game(*, theme: str = "modern") -> int:
    return TetrisApp(theme=theme).run() or 0
