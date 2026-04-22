from __future__ import annotations

from dataclasses import dataclass

from .core import MinesweeperGame, PRESET_DIFFICULTIES


def _load_curses():
    try:
        import curses
    except ImportError as exc:
        raise RuntimeError("curses is required for the terminal UI and is typically available on Linux.") from exc
    return curses


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


class _BoardRenderer:
    CELL_WIDTH = 4
    ROW_LABEL_WIDTH = 4

    def __init__(self, curses_mod) -> None:
        self.curses = curses_mod

    def render(
        self,
        stdscr,
        game: MinesweeperGame,
        cursor_row: int,
        cursor_col: int,
        status_lines: list[str],
        footer_lines: list[str],
    ) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        required_height = game.rows + len(status_lines) + len(footer_lines) + 5
        required_width = self.ROW_LABEL_WIDTH + (game.cols * self.CELL_WIDTH)
        if height < required_height or width < required_width:
            self._safe_addstr(stdscr, 0, 0, f"Terminal too small. Need at least {required_width}x{required_height}.")
            self._safe_addstr(stdscr, 1, 0, f"Current size: {width}x{height}")
            stdscr.refresh()
            return

        start_y = 1
        start_x = self.ROW_LABEL_WIDTH
        for col in range(game.cols):
            label = column_label(col)
            self._safe_addstr(stdscr, 0, start_x + (col * self.CELL_WIDTH), label.center(self.CELL_WIDTH))

        for row in range(game.rows):
            self._safe_addstr(stdscr, start_y + row, 0, f"{row + 1:>3} ")
            for col in range(game.cols):
                attr = self.curses.A_NORMAL
                if row == cursor_row and col == cursor_col:
                    attr |= self.curses.A_REVERSE
                if game.exploded_cell == (row, col):
                    attr |= self.curses.A_BOLD
                symbol = self._cell_symbol(game, row, col)
                self._safe_addstr(
                    stdscr,
                    start_y + row,
                    start_x + (col * self.CELL_WIDTH),
                    symbol.center(self.CELL_WIDTH),
                    attr,
                )

        info_y = start_y + game.rows + 1
        for offset, line in enumerate(status_lines):
            self._safe_addstr(stdscr, info_y + offset, 0, line[: max(0, width - 1)])

        footer_y = info_y + len(status_lines) + 1
        for offset, line in enumerate(footer_lines):
            self._safe_addstr(stdscr, footer_y + offset, 0, line[: max(0, width - 1)])

        stdscr.refresh()

    def _cell_symbol(self, game: MinesweeperGame, row: int, col: int) -> str:
        cell = game.grid[row][col]
        if cell.is_flagged:
            return "F"
        if not cell.is_revealed:
            return "#"
        if cell.has_mine:
            return "*"
        if cell.adjacent_mines == 0:
            return "."
        return str(cell.adjacent_mines)

    def _safe_addstr(self, stdscr, row: int, col: int, text: str, attr: int = 0) -> None:
        try:
            stdscr.addstr(row, col, text, attr)
        except self.curses.error:
            pass


class LocalMinesweeperApp:
    def __init__(self, config: GameConfig) -> None:
        self.config = config

    def run(self) -> int:
        curses = _load_curses()
        return curses.wrapper(self._main)

    def _main(self, stdscr) -> int:
        curses = _load_curses()
        renderer = _BoardRenderer(curses)
        game = MinesweeperGame(
            self.config.rows,
            self.config.cols,
            self.config.mines,
            difficulty_name=self.config.difficulty_name,
        )
        cursor_row = min(game.rows // 2, game.rows - 1)
        cursor_col = min(game.cols // 2, game.cols - 1)
        message = "Arrow keys move. Enter/Space reveals. f toggles a flag."

        self._configure_screen(stdscr, curses)

        while True:
            status = [
                f"Minesweeper {self.config.title} | Board {game.rows}x{game.cols} | Mines {game.mines} | Remaining {game.remaining_mine_estimate()}",
                f"Cursor: {format_position(cursor_row, cursor_col)}",
                game.status_text(),
                message,
            ]
            footer = self._footer_lines(game)
            renderer.render(stdscr, game, cursor_row, cursor_col, status, footer)

            key = stdscr.getch()
            if key == -1:
                continue

            if key in (ord("q"), ord("Q")):
                if self._confirm_quit(stdscr, curses, game.rows):
                    return 0
                message = "Quit cancelled."
                continue

            moved = move_cursor_from_key(curses, key, cursor_row, cursor_col, game.rows, game.cols)
            if moved is not None:
                cursor_row, cursor_col = moved
                continue

            if key in (ord("r"), ord("R")):
                game.restart()
                message = "Started a new board."
                continue

            if key in (ord("f"), ord("F")):
                try:
                    flagged = game.toggle_flag(cursor_row, cursor_col)
                except ValueError as exc:
                    message = str(exc)
                else:
                    message = "Flag placed." if flagged else "Flag removed."
                continue

            if key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                try:
                    revealed = game.reveal(cursor_row, cursor_col)
                except ValueError as exc:
                    message = str(exc)
                else:
                    if game.lost or game.won:
                        message = game.status_text()
                    elif len(revealed) > 1:
                        message = f"Revealed {len(revealed)} cells."
                    else:
                        message = f"Revealed {format_position(cursor_row, cursor_col)}."

    def _configure_screen(self, stdscr, curses) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(-1)

    def _footer_lines(self, game: MinesweeperGame) -> list[str]:
        if game.finished:
            return ["Controls: r restart, q quit"]
        return ["Controls: arrows move, Enter/Space reveal, f flag, r restart, q quit"]

    def _confirm_quit(self, stdscr, curses, board_rows: int) -> bool:
        height, _width = stdscr.getmaxyx()
        prompt_row = min(height - 1, board_rows + 7)
        stdscr.move(prompt_row, 0)
        stdscr.clrtoeol()
        stdscr.addstr(prompt_row, 0, "Quit current game? (y/N) ")
        stdscr.refresh()
        key = stdscr.getch()
        return key in (ord("y"), ord("Y"))


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


def move_cursor_from_key(
    curses_mod,
    key: int,
    row: int,
    col: int,
    rows: int,
    cols: int,
) -> tuple[int, int] | None:
    if key == curses_mod.KEY_UP:
        return max(0, row - 1), col
    if key == curses_mod.KEY_DOWN:
        return min(rows - 1, row + 1), col
    if key == curses_mod.KEY_LEFT:
        return row, max(0, col - 1)
    if key == curses_mod.KEY_RIGHT:
        return row, min(cols - 1, col + 1)
    return None


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
) -> int:
    config = resolve_config(difficulty_name, rows=rows, cols=cols, mines=mines)
    return LocalMinesweeperApp(config).run()
