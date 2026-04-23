from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Game2048:
    size: int = 4
    seed: int | None = None
    board: list[list[int]] = field(init=False)
    score: int = field(init=False, default=0)
    won: bool = field(init=False, default=False)
    lost: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.size < 2:
            raise ValueError("Board size must be at least 2.")
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        self.board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.lost = False
        self._spawn_tile()
        self._spawn_tile()

    def move(self, direction: str) -> bool:
        if self.lost:
            return False
        original = [row[:] for row in self.board]
        if direction == "left":
            self._move_left()
        elif direction == "right":
            self._reverse_rows(); self._move_left(); self._reverse_rows()
        elif direction == "up":
            self._transpose(); self._move_left(); self._transpose()
        elif direction == "down":
            self._transpose(); self._reverse_rows(); self._move_left(); self._reverse_rows(); self._transpose()
        else:
            raise ValueError("Invalid direction.")

        changed = self.board != original
        if changed:
            self._spawn_tile()
            self.won = any(cell >= 2048 for row in self.board for cell in row)
            self.lost = not self._can_move()
        return changed

    def _move_left(self) -> None:
        for r, row in enumerate(self.board):
            tiles = [value for value in row if value != 0]
            merged: list[int] = []
            i = 0
            while i < len(tiles):
                if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
                    value = tiles[i] * 2
                    merged.append(value)
                    self.score += value
                    i += 2
                else:
                    merged.append(tiles[i])
                    i += 1
            merged.extend([0] * (self.size - len(merged)))
            self.board[r] = merged

    def _transpose(self) -> None:
        self.board = [list(row) for row in zip(*self.board)]

    def _reverse_rows(self) -> None:
        self.board = [list(reversed(row)) for row in self.board]

    def _empty_cells(self) -> list[tuple[int, int]]:
        return [(r, c) for r in range(self.size) for c in range(self.size) if self.board[r][c] == 0]

    def _spawn_tile(self) -> None:
        empty = self._empty_cells()
        if not empty:
            return
        r, c = self._rng.choice(empty)
        self.board[r][c] = 4 if self._rng.random() < 0.1 else 2

    def _can_move(self) -> bool:
        if self._empty_cells():
            return True
        for r in range(self.size):
            for c in range(self.size):
                v = self.board[r][c]
                if r + 1 < self.size and self.board[r + 1][c] == v:
                    return True
                if c + 1 < self.size and self.board[r][c + 1] == v:
                    return True
        return False
