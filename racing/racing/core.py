from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class RacingGame:
    road_rows: int = 20
    road_cols: int = 15
    seed: int | None = None

    # Per-row (gap_left, gap_width) as generated — index 0 = top, road_rows-1 = player row
    gap_segs: list[tuple[int, int]] = field(init=False)
    # coin column per row (None = no coin)
    coin_cols: list[int | None] = field(init=False)
    player_col: int = field(init=False)
    score: int = field(init=False, default=0)
    coins_collected: int = field(init=False, default=0)
    frame: int = field(init=False, default=0)
    game_over: bool = field(init=False, default=False)
    _drift: int = field(init=False, default=0)

    GAP_START: ClassVar[int] = 7
    GAP_MIN: ClassVar[int] = 3
    COIN_CHANCE: ClassVar[float] = 0.25
    COIN_SCORE: ClassVar[int] = 25
    BASE_INTERVAL: ClassVar[int] = 5   # frames per scroll step
    MIN_INTERVAL: ClassVar[int] = 2
    SPEED_UP_EVERY: ClassVar[int] = 100
    NARROW_EVERY: ClassVar[int] = 250  # frames per -1 gap width

    def __post_init__(self) -> None:
        if self.road_rows < 6 or self.road_cols < self.GAP_START + 4:
            raise ValueError(f"Road too small. Need cols >= {self.GAP_START + 4}.")
        self._rng = random.Random(self.seed)
        self.restart()

    # ── derived state ──────────────────────────────────────────────────────────

    @property
    def current_gap_width(self) -> int:
        return max(self.GAP_MIN, self.GAP_START - self.frame // self.NARROW_EVERY)

    @property
    def scroll_interval(self) -> int:
        return max(self.MIN_INTERVAL, self.BASE_INTERVAL - self.frame // self.SPEED_UP_EVERY)

    @property
    def speed_level(self) -> int:
        return self.BASE_INTERVAL - self.scroll_interval + 1

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def restart(self) -> None:
        self.score = 0
        self.coins_collected = 0
        self.frame = 0
        self.game_over = False
        self._drift = 0
        gw = self.GAP_START
        gl = (self.road_cols - gw) // 2
        self.gap_segs = [(gl, gw)] * self.road_rows
        self.coin_cols = [None] * self.road_rows
        for i in range(self.road_rows - 2):
            self._maybe_place_coin(i)
        self.player_col = gl + gw // 2

    # ── controls ───────────────────────────────────────────────────────────────

    def move_left(self) -> None:
        if not self.game_over and self.player_col > 0:
            self.player_col -= 1

    def move_right(self) -> None:
        if not self.game_over and self.player_col < self.road_cols - 1:
            self.player_col += 1

    # ── game loop ──────────────────────────────────────────────────────────────

    def step(self) -> None:
        if self.game_over:
            return
        self.frame += 1
        self.score += 1

        # collect coin at player position before scrolling
        player_row = self.road_rows - 1
        if self.coin_cols[player_row] == self.player_col:
            self.coins_collected += 1
            self.score += self.COIN_SCORE
            self.coin_cols[player_row] = None

        if self.frame % self.scroll_interval == 0:
            self._scroll()

    def _scroll(self) -> None:
        gw = self.current_gap_width

        # momentum drift: 15% chance to change direction
        if self._rng.random() < 0.15:
            self._drift = self._rng.choice([-1, 0, 1])

        prev_gl = self.gap_segs[0][0]
        new_gl = max(0, min(self.road_cols - gw, prev_gl + self._drift))

        # shift all rows down, insert new row at top
        self.gap_segs = [(new_gl, gw)] + self.gap_segs[:-1]
        self.coin_cols = [None] + self.coin_cols[:-1]
        self._maybe_place_coin(0)

        # collision: is player inside the gap at the bottom row?
        gl, gw_row = self.gap_segs[self.road_rows - 1]
        if not (gl <= self.player_col < gl + gw_row):
            self.game_over = True

    def _maybe_place_coin(self, row: int) -> None:
        if self._rng.random() < self.COIN_CHANCE:
            gl, gw = self.gap_segs[row]
            if gw > 0:
                self.coin_cols[row] = self._rng.randint(gl, gl + gw - 1)

    # ── query helpers ──────────────────────────────────────────────────────────

    def is_wall(self, row: int, col: int) -> bool:
        gl, gw = self.gap_segs[row]
        return col < gl or col >= gl + gw

    def has_coin(self, row: int, col: int) -> bool:
        return self.coin_cols[row] == col
