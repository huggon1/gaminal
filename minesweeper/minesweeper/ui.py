from __future__ import annotations

from dataclasses import dataclass
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import MinesweeperGame, PRESET_DIFFICULTIES


@dataclass(frozen=True)
class GameConfig:
    rows: int
    cols: int
    mines: int
    difficulty_name: str | None = None

    @property
    def title(self) -> str:
        if self.difficulty_name is not None:
            return self.difficulty_name
        return f"{self.rows}x{self.cols}/{self.mines}"


class LocalMinesweeperApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #board-panel {
            width: 2fr;
        }

        #stats-panel {
            width: 1fr;
        }

        #board-view {
            text-style: bold;
        }

        #control-row {
            height: auto;
        }

        #control-row Button {
            margin-right: 1;
            min-width: 8;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("left", "move_left", "Left", show=False),
        Binding("right", "move_right", "Right", show=False),
        Binding("enter", "reveal_cell", "Reveal"),
        Binding("space", "reveal_cell", "Reveal", show=False),
        Binding("f", "toggle_flag", "Flag"),
        Binding("r", "restart_board", "Restart"),
    ]
    help_text = "Arrows move  Enter/Space reveal  f flag  r restart  t theme  ? help  q quit"

    def __init__(self, config: GameConfig, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.config = config
        self.game = MinesweeperGame(
            config.rows,
            config.cols,
            config.mines,
            difficulty_name=config.difficulty_name,
        )
        self.cursor_row = min(self.game.rows // 2, self.game.rows - 1)
        self.cursor_col = min(self.game.cols // 2, self.game.cols - 1)
        self.message = "Arrow keys move. Enter reveals. f toggles a flag."

    def compose(self) -> ComposeResult:
        yield Static(f"Minesweeper [{self.config.title}]", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel", id="board-panel"):
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel", id="stats-panel"):
                yield Static("", id="stats-view")
                with Horizontal(id="control-row"):
                    yield Button("Reveal", id="reveal")
                    yield Button("Flag", id="flag")
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#board-view", Static).update(self.render_board())
        stats = [
            f"Board: {self.game.rows}x{self.game.cols}",
            f"Mines: {self.game.mines}",
            f"Remaining estimate: {self.game.remaining_mine_estimate()}",
            f"Cursor: {format_position(self.cursor_row, self.cursor_col)}",
            f"State: {self.game.status_text()}",
            "",
            "Controls:",
            "  Arrows move",
            "  Enter/Space reveal",
            "  f toggles flag",
            "  r restarts board",
        ]
        self.query_one("#stats-view", Static).update("\n".join(stats))
        self.update_status(self.message)

    def render_board(self) -> Text:
        board = Text()
        board.append("    " + " ".join(column_label(col).rjust(3) for col in range(self.game.cols)))
        board.append("\n")
        for row in range(self.game.rows):
            board.append(f"{row + 1:>3} ")
            for col in range(self.game.cols):
                symbol = self.cell_symbol(row, col)
                token = f" {symbol} "
                if row == self.cursor_row and col == self.cursor_col:
                    board.append(token, style="reverse")
                else:
                    board.append(token)
            if row < self.game.rows - 1:
                board.append("\n")
        return board

    def cell_symbol(self, row: int, col: int) -> str:
        cell = self.game.grid[row][col]
        if self.game.finished and cell.is_flagged and not cell.has_mine:
            return "x"
        if cell.is_revealed and self.game.exploded_cell == (row, col):
            return "!"
        if cell.is_revealed and cell.has_mine:
            return "*"
        if cell.is_flagged:
            return "F"
        if not cell.is_revealed:
            return "#"
        if cell.adjacent_mines == 0:
            return " "
        return str(cell.adjacent_mines)

    def move_cursor(self, delta_row: int, delta_col: int) -> None:
        self.cursor_row = (self.cursor_row + delta_row) % self.game.rows
        self.cursor_col = (self.cursor_col + delta_col) % self.game.cols
        self.refresh_view()

    def action_move_up(self) -> None:
        self.move_cursor(-1, 0)

    def action_move_down(self) -> None:
        self.move_cursor(1, 0)

    def action_move_left(self) -> None:
        self.move_cursor(0, -1)

    def action_move_right(self) -> None:
        self.move_cursor(0, 1)

    def action_reveal_cell(self) -> None:
        was_revealed = self.game.grid[self.cursor_row][self.cursor_col].is_revealed
        try:
            revealed = self.game.reveal(self.cursor_row, self.cursor_col)
        except ValueError as exc:
            self.message = str(exc)
        else:
            if self.game.finished:
                self.message = self.game.status_text()
            elif was_revealed and revealed:
                self.message = f"Opened {len(revealed)} adjacent cells."
            elif was_revealed:
                self.message = "Adjacent flags do not match the number."
            elif len(revealed) > 1:
                self.message = f"Revealed {len(revealed)} cells."
            else:
                self.message = f"Revealed {format_position(self.cursor_row, self.cursor_col)}."
        self.refresh_view()

    def action_toggle_flag(self) -> None:
        try:
            flagged = self.game.toggle_flag(self.cursor_row, self.cursor_col)
        except ValueError as exc:
            self.message = str(exc)
        else:
            self.message = "Flag placed." if flagged else "Flag removed."
        self.refresh_view()

    def action_restart_board(self) -> None:
        self.game.restart()
        self.cursor_row = min(self.game.rows // 2, self.game.rows - 1)
        self.cursor_col = min(self.game.cols // 2, self.game.cols - 1)
        self.message = "Started a new board."
        self.refresh_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reveal":
            self.action_reveal_cell()
        elif event.button.id == "flag":
            self.action_toggle_flag()
        elif event.button.id == "restart":
            self.action_restart_board()


def column_label(col: int) -> str:
    index = col
    result = ""
    while True:
        index, remainder = divmod(index, 26)
        result = chr(ord("A") + remainder) + result
        if index == 0:
            return result
        index -= 1


def format_position(row: int, col: int) -> str:
    return f"{column_label(col)}{row + 1}"


def resolve_config(
    difficulty_name: str = "beginner",
    *,
    rows: int | None = None,
    cols: int | None = None,
    mines: int | None = None,
) -> GameConfig:
    if difficulty_name not in PRESET_DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {difficulty_name}")

    if rows is None and cols is None and mines is None:
        preset = PRESET_DIFFICULTIES[difficulty_name]
        return GameConfig(rows=preset.rows, cols=preset.cols, mines=preset.mines, difficulty_name=preset.name)

    if rows is None or cols is None or mines is None:
        raise ValueError("Custom boards require --rows, --cols, and --mines together.")
    validate_config(rows, cols, mines)
    return GameConfig(rows=rows, cols=cols, mines=mines, difficulty_name=None)


def validate_config(rows: int, cols: int, mines: int) -> None:
    if rows <= 0 or cols <= 0:
        raise ValueError("Rows and columns must be positive.")
    if mines <= 0:
        raise ValueError("Mine count must be positive.")
    if mines >= rows * cols:
        raise ValueError("Mine count must be smaller than the board area.")


def run_local_minesweeper(
    difficulty_name: str = "beginner",
    *,
    rows: int | None = None,
    cols: int | None = None,
    mines: int | None = None,
    theme: str = "modern",
) -> int:
    config = resolve_config(difficulty_name, rows=rows, cols=cols, mines=mines)
    return LocalMinesweeperApp(config, theme=theme).run() or 0
