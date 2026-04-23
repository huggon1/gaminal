from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import ClassVar

# SRS standard rotation offsets: each piece has 4 rotations, each rotation is a list of (dr, dc) offsets from pivot
TETROMINOES: dict[str, list[list[tuple[int, int]]]] = {
    "I": [
        [(0, -1), (0, 0), (0, 1), (0, 2)],
        [(-1, 1), (0, 1), (1, 1), (2, 1)],
        [(1, -1), (1, 0), (1, 1), (1, 2)],
        [(-1, 0), (0, 0), (1, 0), (2, 0)],
    ],
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    "T": [
        [(-1, 0), (0, -1), (0, 0), (0, 1)],
        [(-1, 0), (0, 0), (0, 1), (1, 0)],
        [(0, -1), (0, 0), (0, 1), (1, 0)],
        [(-1, 0), (0, -1), (0, 0), (1, 0)],
    ],
    "S": [
        [(0, 0), (0, 1), (-1, -1), (-1, 0)],
        [(-1, 0), (0, 0), (0, 1), (1, 1)],
        [(0, 0), (0, 1), (1, -1), (1, 0)],
        [(-1, -1), (0, -1), (0, 0), (1, 0)],
    ],
    "Z": [
        [(-1, 0), (-1, 1), (0, -1), (0, 0)],
        [(-1, 1), (0, 0), (0, 1), (1, 0)],
        [(0, 0), (0, 1), (1, -1), (1, 0)],
        [(-1, 0), (0, -1), (0, 0), (1, -1)],
    ],
    "J": [
        [(-1, -1), (0, -1), (0, 0), (0, 1)],
        [(-1, 0), (-1, 1), (0, 0), (1, 0)],
        [(0, -1), (0, 0), (0, 1), (1, 1)],
        [(-1, 0), (0, 0), (1, -1), (1, 0)],
    ],
    "L": [
        [(-1, 1), (0, -1), (0, 0), (0, 1)],
        [(-1, 0), (0, 0), (1, 0), (1, 1)],
        [(0, -1), (0, 0), (0, 1), (1, -1)],
        [(-1, -1), (-1, 0), (0, 0), (1, 0)],
    ],
}

PIECES = list(TETROMINOES.keys())

# Wall kick offsets to try when rotation fails: (dr, dc)
WALL_KICKS = [(0, 0), (0, -1), (0, 1), (-1, 0), (0, -2), (0, 2)]


@dataclass
class TetrisPiece:
    kind: str
    row: int
    col: int
    rotation: int = 0

    def cells(self) -> list[tuple[int, int]]:
        offsets = TETROMINOES[self.kind][self.rotation]
        return [(self.row + dr, self.col + dc) for dr, dc in offsets]

    def rotated(self, delta: int = 1) -> "TetrisPiece":
        return TetrisPiece(self.kind, self.row, self.col, (self.rotation + delta) % 4)

    def moved(self, dr: int, dc: int) -> "TetrisPiece":
        return TetrisPiece(self.kind, self.row + dr, self.col + dc, self.rotation)


@dataclass
class TetrisGame:
    seed: int | None = None

    board: list[list[str | None]] = field(init=False)
    current: TetrisPiece = field(init=False)
    next_kind: str = field(init=False)
    score: int = field(init=False, default=0)
    lines: int = field(init=False, default=0)
    level: int = field(init=False, default=1)
    game_over: bool = field(init=False, default=False)

    ROWS: ClassVar[int] = 20
    COLS: ClassVar[int] = 10
    LEVEL_SPEEDS: ClassVar[list[float]] = [0.8, 0.65, 0.53, 0.43, 0.35, 0.27, 0.20, 0.15, 0.10, 0.07]
    SCORE_TABLE: ClassVar[list[int]] = [0, 40, 100, 300, 1200]

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        self.board = [[None] * self.COLS for _ in range(self.ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.next_kind = self._rng.choice(PIECES)
        self._spawn()

    def _spawn(self) -> None:
        kind = self.next_kind
        self.next_kind = self._rng.choice(PIECES)
        piece = TetrisPiece(kind, 0, self.COLS // 2)
        self.current = piece
        if not self._fits(piece):
            self.game_over = True

    def _fits(self, piece: TetrisPiece) -> bool:
        for r, c in piece.cells():
            if r >= self.ROWS or c < 0 or c >= self.COLS:
                return False
            if r >= 0 and self.board[r][c] is not None:
                return False
        return True

    def move_left(self) -> bool:
        if self.game_over:
            return False
        candidate = self.current.moved(0, -1)
        if self._fits(candidate):
            self.current = candidate
            return True
        return False

    def move_right(self) -> bool:
        if self.game_over:
            return False
        candidate = self.current.moved(0, 1)
        if self._fits(candidate):
            self.current = candidate
            return True
        return False

    def soft_drop(self) -> bool:
        if self.game_over:
            return False
        candidate = self.current.moved(1, 0)
        if self._fits(candidate):
            self.current = candidate
            return True
        self._lock()
        return False

    def hard_drop(self) -> None:
        if self.game_over:
            return
        while True:
            candidate = self.current.moved(1, 0)
            if self._fits(candidate):
                self.current = candidate
            else:
                break
        self._lock()

    def rotate(self) -> bool:
        if self.game_over:
            return False
        rotated = self.current.rotated(1)
        for dr, dc in WALL_KICKS:
            candidate = TetrisPiece(rotated.kind, rotated.row + dr, rotated.col + dc, rotated.rotation)
            if self._fits(candidate):
                self.current = candidate
                return True
        return False

    def gravity_step(self) -> None:
        self.soft_drop()

    def _lock(self) -> None:
        for r, c in self.current.cells():
            if 0 <= r < self.ROWS:
                self.board[r][c] = self.current.kind
        cleared = self._clear_lines()
        self._update_score(cleared)
        if not self.game_over:
            self._spawn()

    def _clear_lines(self) -> int:
        full_rows = [row for row in self.board if all(c is not None for c in row)]
        cleared = len(full_rows)
        if cleared:
            self.board = [row for row in self.board if not all(c is not None for c in row)]
            for _ in range(cleared):
                self.board.insert(0, [None] * self.COLS)
        self.lines += cleared
        return cleared

    def _update_score(self, cleared: int) -> None:
        self.score += self.SCORE_TABLE[min(cleared, 4)] * self.level
        self.level = min(self.lines // 10 + 1, len(self.LEVEL_SPEEDS))

    def ghost_piece(self) -> TetrisPiece:
        piece = self.current
        while True:
            candidate = piece.moved(1, 0)
            if self._fits(candidate):
                piece = candidate
            else:
                return piece

    @property
    def tick_interval(self) -> float:
        return self.LEVEL_SPEEDS[self.level - 1]
