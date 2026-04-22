from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    name: str
    rows: int
    cols: int
    mines: int


PRESET_DIFFICULTIES: dict[str, Difficulty] = {
    "beginner": Difficulty(name="beginner", rows=9, cols=9, mines=10),
    "intermediate": Difficulty(name="intermediate", rows=16, cols=16, mines=40),
    "expert": Difficulty(name="expert", rows=16, cols=30, mines=99),
}


@dataclass
class Cell:
    has_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    adjacent_mines: int = 0


class MinesweeperGame:
    def __init__(
        self,
        rows: int,
        cols: int,
        mines: int,
        *,
        seed: int | None = None,
        difficulty_name: str | None = None,
        mine_positions: set[tuple[int, int]] | None = None,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.seed = seed
        self.difficulty_name = difficulty_name
        self._mine_positions_override = set(mine_positions) if mine_positions is not None else None
        self._validate_dimensions()
        self._rng = random.Random(seed)
        self._reset_board()
        if self._mine_positions_override is not None:
            self._apply_mines(self._mine_positions_override)

    @classmethod
    def from_difficulty(cls, difficulty: Difficulty, *, seed: int | None = None) -> "MinesweeperGame":
        return cls(
            difficulty.rows,
            difficulty.cols,
            difficulty.mines,
            seed=seed,
            difficulty_name=difficulty.name,
        )

    def restart(self) -> None:
        self._rng = random.Random(self.seed)
        self._reset_board()
        if self._mine_positions_override is not None:
            self._apply_mines(self._mine_positions_override)

    def reveal(self, row: int, col: int) -> set[tuple[int, int]]:
        self._require_in_bounds(row, col)
        if self.finished:
            raise ValueError("Game is already finished.")
        cell = self.grid[row][col]
        if cell.is_flagged:
            raise ValueError("Flagged cells must be unflagged before revealing.")
        if cell.is_revealed:
            raise ValueError("That cell is already revealed.")
        if not self.initialized:
            self._place_random_mines(row, col)

        cell = self.grid[row][col]
        if cell.has_mine:
            cell.is_revealed = True
            self.finished = True
            self.won = False
            self.lost = True
            self.exploded_cell = (row, col)
            self._reveal_all_mines()
            return {(row, col)}

        revealed = self._reveal_region(row, col)
        if self.revealed_safe_cells == self.safe_cells:
            self.finished = True
            self.won = True
            self.lost = False
            self._flag_all_hidden_mines()
        return revealed

    def toggle_flag(self, row: int, col: int) -> bool:
        self._require_in_bounds(row, col)
        if self.finished:
            raise ValueError("Game is already finished.")
        cell = self.grid[row][col]
        if cell.is_revealed:
            raise ValueError("Revealed cells cannot be flagged.")
        cell.is_flagged = not cell.is_flagged
        self.flags_placed += 1 if cell.is_flagged else -1
        return cell.is_flagged

    def remaining_mine_estimate(self) -> int:
        return self.mines - self.flags_placed

    def status_text(self) -> str:
        if self.won:
            return "You cleared the board."
        if self.lost:
            return "Boom. You hit a mine."
        if not self.initialized:
            return "Ready. Reveal a cell to start."
        return "Board active."

    def _validate_dimensions(self) -> None:
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("Rows and columns must be positive.")
        if self.mines <= 0:
            raise ValueError("Mine count must be positive.")
        if self.mines >= self.rows * self.cols:
            raise ValueError("Mine count must be smaller than the board area.")
        if self._mine_positions_override is not None:
            if len(self._mine_positions_override) != self.mines:
                raise ValueError("Mine position count must match the configured mine count.")
            for row, col in self._mine_positions_override:
                if not self.in_bounds(row, col):
                    raise ValueError("Mine positions must stay within the board.")

    def _reset_board(self) -> None:
        self.grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]
        self.initialized = False
        self.finished = False
        self.won = False
        self.lost = False
        self.flags_placed = 0
        self.revealed_safe_cells = 0
        self.safe_cells = (self.rows * self.cols) - self.mines
        self.exploded_cell: tuple[int, int] | None = None

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _require_in_bounds(self, row: int, col: int) -> None:
        if not self.in_bounds(row, col):
            raise ValueError("Cell is out of bounds.")

    def _apply_mines(self, mine_positions: set[tuple[int, int]]) -> None:
        for row, col in mine_positions:
            self.grid[row][col].has_mine = True
        self._recompute_adjacent_counts()
        self.initialized = True

    def _place_random_mines(self, safe_row: int, safe_col: int) -> None:
        candidates = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if (row, col) != (safe_row, safe_col)
        ]
        mine_positions = set(self._rng.sample(candidates, self.mines))
        self._apply_mines(mine_positions)

    def _recompute_adjacent_counts(self) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self.grid[row][col]
                if cell.has_mine:
                    cell.adjacent_mines = 0
                    continue
                cell.adjacent_mines = sum(
                    1
                    for neighbor_row, neighbor_col in self._neighbors(row, col)
                    if self.grid[neighbor_row][neighbor_col].has_mine
                )

    def _neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        neighbors: list[tuple[int, int]] = []
        for delta_row in (-1, 0, 1):
            for delta_col in (-1, 0, 1):
                if delta_row == 0 and delta_col == 0:
                    continue
                next_row = row + delta_row
                next_col = col + delta_col
                if self.in_bounds(next_row, next_col):
                    neighbors.append((next_row, next_col))
        return neighbors

    def _reveal_region(self, start_row: int, start_col: int) -> set[tuple[int, int]]:
        revealed: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([(start_row, start_col)])
        while queue:
            row, col = queue.popleft()
            cell = self.grid[row][col]
            if cell.is_revealed or cell.is_flagged:
                continue
            cell.is_revealed = True
            self.revealed_safe_cells += 1
            revealed.add((row, col))
            if cell.adjacent_mines != 0:
                continue
            for neighbor_row, neighbor_col in self._neighbors(row, col):
                neighbor = self.grid[neighbor_row][neighbor_col]
                if neighbor.has_mine or neighbor.is_revealed or neighbor.is_flagged:
                    continue
                queue.append((neighbor_row, neighbor_col))
        return revealed

    def _reveal_all_mines(self) -> None:
        for row in self.grid:
            for cell in row:
                if cell.has_mine:
                    cell.is_revealed = True

    def _flag_all_hidden_mines(self) -> None:
        self.flags_placed = 0
        for row in self.grid:
            for cell in row:
                if cell.has_mine and not cell.is_flagged:
                    cell.is_flagged = True
                if cell.is_flagged:
                    self.flags_placed += 1
