from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Platform:
    row: float
    col: int
    width: int


@dataclass
class BonusItem:
    kind: str
    row: float
    col: int


BONUS_KINDS = ("coin", "heart", "slow")
BONUS_SCORE = 50
SLOW_DURATION = 180


@dataclass
class RapidRollGame:
    rows: int = 24
    cols: int = 22
    seed: int | None = None

    platforms: list[Platform] = field(init=False)
    items: list[BonusItem] = field(init=False)
    active_effects: dict[str, int] = field(init=False)
    _grounded_platform: Platform | None = field(init=False, default=None)
    ball_row: float = field(init=False)
    ball_col: float = field(init=False)
    ball_vy: float = field(init=False)
    score: int = field(init=False, default=0)
    lives: int = field(init=False, default=3)
    frame: int = field(init=False, default=0)
    landings: int = field(init=False, default=0)
    game_over: bool = field(init=False, default=False)
    last_event: str = field(init=False, default="ready")

    START_LIVES: ClassVar[int] = 3
    MAX_LIVES: ClassVar[int] = 5
    BALL_RADIUS: ClassVar[float] = 0.0
    GRAVITY: ClassVar[float] = 0.055
    MAX_FALL_SPEED: ClassVar[float] = 0.9
    SUPPORT_TOLERANCE: ClassVar[float] = 0.35
    BASE_SCROLL_SPEED: ClassVar[float] = 0.070
    MAX_SCROLL_SPEED: ClassVar[float] = 0.155
    BONUS_CHANCE: ClassVar[float] = 0.28
    LANDING_SCORE: ClassVar[int] = 10

    def __post_init__(self) -> None:
        if self.rows < 14 or self.cols < 12:
            raise ValueError("Board too small. Need rows >= 14 and cols >= 12.")
        self._rng = random.Random(self.seed)
        self.restart()

    @property
    def scroll_speed(self) -> float:
        speed = min(self.MAX_SCROLL_SPEED, self.BASE_SCROLL_SPEED + self.score / 9000)
        if "slow" in self.active_effects:
            speed *= 0.58
        return speed

    @property
    def speed_level(self) -> int:
        raw = 1 + int((self.BASE_SCROLL_SPEED + self.score / 9000 - self.BASE_SCROLL_SPEED) / 0.02)
        return max(1, min(5, raw))

    @property
    def platform_width(self) -> int:
        width = 8 - self.score // 700
        return max(4, min(8, width))

    @property
    def platform_gap(self) -> int:
        gap = 5 + self.score // 1200
        return max(5, min(7, gap))

    def restart(self) -> None:
        self.score = 0
        self.lives = self.START_LIVES
        self.frame = 0
        self.landings = 0
        self.game_over = False
        self.active_effects = {}
        self.items = []
        self.platforms = []
        self._grounded_platform = None
        self._build_starting_platforms()
        start = self.platforms[-2]
        self.ball_row = start.row - 1.0
        self.ball_col = start.col + start.width // 2
        self.ball_vy = 0.0
        self._grounded_platform = start
        self.last_event = "ready"

    def _build_starting_platforms(self) -> None:
        width = self.platform_width
        row = float(self.rows - 3)
        while row > 2:
            col = (self.cols - width) // 2 if not self.platforms else self._random_platform_col(width)
            self.platforms.append(Platform(row=row, col=col, width=width))
            row -= self.platform_gap
        self.platforms.sort(key=lambda p: p.row)

    def move_left(self) -> None:
        if not self.game_over:
            self.ball_col = max(0.0, self.ball_col - 1.0)

    def move_right(self) -> None:
        if not self.game_over:
            self.ball_col = min(float(self.cols - 1), self.ball_col + 1.0)

    def step(self) -> None:
        if self.game_over:
            return

        self.frame += 1
        self.score += 1
        self.last_event = "running"
        self._tick_effects()
        self._scroll_world()
        self._apply_ball_physics()
        self._collect_items()
        self._check_hazards()

    def _tick_effects(self) -> None:
        expired = [kind for kind, ticks in self.active_effects.items() if ticks <= 1]
        for kind in expired:
            del self.active_effects[kind]
        for kind in list(self.active_effects):
            self.active_effects[kind] -= 1

    def _scroll_world(self) -> None:
        speed = self.scroll_speed
        for platform in self.platforms:
            platform.row -= speed
        for item in self.items:
            item.row -= speed

        self.platforms = [p for p in self.platforms if p.row >= 1.0]
        if self._grounded_platform not in self.platforms:
            self._grounded_platform = None
        self.items = [i for i in self.items if 1.0 <= i.row < self.rows - 1]

        while not self.platforms or self.platforms[-1].row < self.rows - self.platform_gap:
            self._spawn_platform()

    def _spawn_platform(self) -> None:
        width = self.platform_width
        row = float(self.rows - 2)
        col = self._random_platform_col(width)
        platform = Platform(row=row, col=col, width=width)
        self.platforms.append(platform)
        if self._rng.random() < self.BONUS_CHANCE:
            kind = self._rng.choices(BONUS_KINDS, weights=(0.62, 0.18, 0.20), k=1)[0]
            self.items.append(BonusItem(kind=kind, row=row - 1.0, col=self._rng.randint(col, col + width - 1)))

    def _random_platform_col(self, width: int) -> int:
        return self._rng.randint(0, max(0, self.cols - width))

    def _apply_ball_physics(self) -> None:
        if self._grounded_platform is not None:
            platform_top = self._grounded_platform.row - 1.0
            if self._is_over_platform(self._grounded_platform) and abs(self.ball_row - platform_top) <= 1.0:
                self.ball_row = self._grounded_platform.row - 1.0
                self.ball_vy = 0.0
                self.ball_col = max(0.0, min(float(self.cols - 1), self.ball_col))
                return
            self._grounded_platform = None

        previous_row = self.ball_row
        self.ball_vy = min(self.MAX_FALL_SPEED, self.ball_vy + self.GRAVITY)
        next_row = self.ball_row + self.ball_vy

        if self.ball_vy >= 0:
            hit = self._platform_landed_on(previous_row, next_row)
            if hit is not None:
                next_row = hit.row - 1.0
                self.ball_vy = 0.0
                self._grounded_platform = hit
                self.landings += 1
                streak_bonus = min(4, self.landings // 6)
                self.score += self.LANDING_SCORE + streak_bonus * 5
                self.last_event = f"landing:{self.landings}"

        self.ball_row = next_row
        self.ball_col = max(0.0, min(float(self.cols - 1), self.ball_col))

    def _platform_landed_on(self, previous_row: float, next_row: float) -> Platform | None:
        candidates = [
            platform
            for platform in self.platforms
            if self._is_over_platform(platform)
            and previous_row <= platform.row - 1.0 <= next_row + self.SUPPORT_TOLERANCE
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: abs(p.row - next_row))

    def _is_over_platform(self, platform: Platform) -> bool:
        col = int(round(self.ball_col))
        return platform.col <= col < platform.col + platform.width

    def _collect_items(self) -> None:
        ball_r = int(round(self.ball_row))
        ball_c = int(round(self.ball_col))
        collected: list[int] = []
        for index, item in enumerate(self.items):
            if int(round(item.row)) == ball_r and item.col == ball_c:
                self._activate_item(item.kind)
                collected.append(index)
        for index in reversed(collected):
            self.items.pop(index)

    def _activate_item(self, kind: str) -> None:
        if kind == "coin":
            self.score += BONUS_SCORE
            self.last_event = "coin"
        elif kind == "heart":
            self.lives = min(self.MAX_LIVES, self.lives + 1)
            self.last_event = "heart"
        elif kind == "slow":
            self.active_effects["slow"] = SLOW_DURATION
            self.last_event = "slow"

    def _check_hazards(self) -> None:
        if self.ball_row <= 0.0 or self.ball_row >= self.rows - 1:
            self._lose_life()

    def _lose_life(self) -> None:
        self.lives -= 1
        self.landings = 0
        self.active_effects.pop("slow", None)
        self.last_event = "life_lost"
        if self.lives <= 0:
            self.game_over = True
            return
        self._reset_ball_to_safe_platform()

    def _reset_ball_to_safe_platform(self) -> None:
        safe = max(self.platforms, key=lambda p: p.row)
        self.ball_row = max(1.0, safe.row - 1.0)
        self.ball_col = safe.col + safe.width // 2
        self.ball_vy = 0.0
        self._grounded_platform = safe

    def platform_cells(self) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for platform in self.platforms:
            row = int(round(platform.row))
            if 0 <= row < self.rows:
                for col in range(platform.col, platform.col + platform.width):
                    cells.add((row, col))
        return cells
