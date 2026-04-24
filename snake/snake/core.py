from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


ObstacleBuilder = Callable[[int, int], set[tuple[int, int]]]


@dataclass(frozen=True)
class SnakeMap:
    id: str
    name: str
    description: str
    wrap_rows: bool = False
    wrap_cols: bool = False
    obstacle_builder: ObstacleBuilder | None = None

    def obstacles(self, rows: int, cols: int) -> set[tuple[int, int]]:
        if self.obstacle_builder is None:
            return set()
        return self.obstacle_builder(rows, cols)


@dataclass(frozen=True)
class SpeedPreset:
    id: str
    name: str
    tick_seconds: float
    fruit_score: int


def _safe_cells(rows: int, cols: int) -> set[tuple[int, int]]:
    r, c = rows // 2, cols // 2
    return {
        (r, c - 2),
        (r, c - 1),
        (r, c),
        (r, c + 1),
        (r, c + 2),
        (r - 1, c),
        (r + 1, c),
    }


def _bounded(cells: set[tuple[int, int]], rows: int, cols: int) -> set[tuple[int, int]]:
    safe = _safe_cells(rows, cols)
    return {(r, c) for r, c in cells if 0 <= r < rows and 0 <= c < cols and (r, c) not in safe}


def _center_blocks(rows: int, cols: int) -> set[tuple[int, int]]:
    if rows < 8 or cols < 10:
        return set()
    cr, cc = rows // 2, cols // 2
    cells = {
        (cr - 2, cc - 2),
        (cr - 2, cc + 2),
        (cr + 2, cc - 2),
        (cr + 2, cc + 2),
        (cr - 1, cc),
        (cr + 1, cc),
    }
    return _bounded(cells, rows, cols)


def _cross_portal(rows: int, cols: int) -> set[tuple[int, int]]:
    if rows < 6 or cols < 6:
        return set()
    cr, cc = rows // 2, cols // 2
    return {(cr, c) for c in range(cols)} | {(r, cc) for r in range(rows)}


def _islands(rows: int, cols: int) -> set[tuple[int, int]]:
    if rows < 10 or cols < 12:
        return set()
    anchors = [
        (rows // 4, cols // 4),
        (rows // 4, cols - cols // 4 - 1),
        (rows - rows // 4 - 1, cols // 4),
        (rows - rows // 4 - 1, cols - cols // 4 - 1),
    ]
    cells: set[tuple[int, int]] = set()
    for r, c in anchors:
        cells.update({(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)})
    return _bounded(cells, rows, cols)


def _gate_maze(rows: int, cols: int) -> set[tuple[int, int]]:
    if rows < 10 or cols < 12:
        return set()
    upper = rows // 3
    lower = rows - rows // 3 - 1
    left_gap = cols // 4
    right_gap = cols - cols // 4 - 1
    cells = {(upper, c) for c in range(1, cols - 1) if c != right_gap}
    cells.update({(lower, c) for c in range(1, cols - 1) if c != left_gap})
    return _bounded(cells, rows, cols)


MAP_PRESETS: dict[str, SnakeMap] = {
    "classic_walls": SnakeMap(
        id="classic_walls",
        name="Classic Walls",
        description="Four lethal borders. No internal obstacles.",
    ),
    "open_wrap": SnakeMap(
        id="open_wrap",
        name="Open Wrap",
        description="Edges connect to the opposite side. No obstacles.",
        wrap_rows=True,
        wrap_cols=True,
    ),
    "center_blocks": SnakeMap(
        id="center_blocks",
        name="Center Blocks",
        description="Classic borders with a compact obstacle cluster.",
        obstacle_builder=_center_blocks,
    ),
    "cross_portal": SnakeMap(
        id="cross_portal",
        name="Cross Portal",
        description="A full cross wall splits the board. Use edge wrapping to cross regions.",
        wrap_rows=True,
        wrap_cols=True,
        obstacle_builder=_cross_portal,
    ),
    "islands": SnakeMap(
        id="islands",
        name="Islands",
        description="Classic borders with four small obstacle islands.",
        obstacle_builder=_islands,
    ),
    "gate_maze": SnakeMap(
        id="gate_maze",
        name="Gate Maze",
        description="Classic borders with two barrier lines and offset gates.",
        obstacle_builder=_gate_maze,
    ),
}

SPEED_PRESETS: dict[str, SpeedPreset] = {
    "slow": SpeedPreset(id="slow", name="Slow", tick_seconds=0.24, fruit_score=1),
    "normal": SpeedPreset(id="normal", name="Normal", tick_seconds=0.18, fruit_score=2),
    "fast": SpeedPreset(id="fast", name="Fast", tick_seconds=0.12, fruit_score=3),
    "insane": SpeedPreset(id="insane", name="Insane", tick_seconds=0.08, fruit_score=5),
}


@dataclass
class SnakeGame:
    rows: int = 24
    cols: int = 24
    seed: int | None = None
    map_id: str = "classic_walls"
    speed_id: str = "normal"
    snake: list[tuple[int, int]] = field(init=False)
    direction: str = field(init=False, default="right")
    next_direction: str = field(init=False, default="right")
    food: tuple[int, int] = field(init=False)
    score: int = field(init=False, default=0)
    game_over: bool = field(init=False, default=False)
    map: SnakeMap = field(init=False)
    speed: SpeedPreset = field(init=False)
    obstacles: set[tuple[int, int]] = field(init=False)

    def __post_init__(self) -> None:
        if self.rows < 4 or self.cols < 4:
            raise ValueError("Board is too small.")
        if self.map_id not in MAP_PRESETS:
            raise ValueError(f"Unknown snake map: {self.map_id}")
        if self.speed_id not in SPEED_PRESETS:
            raise ValueError(f"Unknown snake speed: {self.speed_id}")
        self.map = MAP_PRESETS[self.map_id]
        self.speed = SPEED_PRESETS[self.speed_id]
        self.obstacles = self.map.obstacles(self.rows, self.cols)
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        self.map = MAP_PRESETS[self.map_id]
        self.speed = SPEED_PRESETS[self.speed_id]
        self.obstacles = self.map.obstacles(self.rows, self.cols)
        self.snake = self._initial_snake()
        self.direction = "right"
        self.next_direction = "right"
        self.score = 0
        self.game_over = False
        self._spawn_food()

    def change_direction(self, direction: str) -> None:
        if direction in DIRECTIONS and direction != OPPOSITE[self.direction]:
            self.next_direction = direction

    def step(self) -> None:
        if self.game_over:
            return
        self.direction = self.next_direction
        dr, dc = DIRECTIONS[self.direction]
        head_r, head_c = self.snake[-1]
        nr, nc = head_r + dr, head_c + dc

        if self.map.wrap_rows:
            nr %= self.rows
        if self.map.wrap_cols:
            nc %= self.cols

        if nr < 0 or nr >= self.rows or nc < 0 or nc >= self.cols:
            self.game_over = True
            return

        new_head = (nr, nc)
        if new_head in self.obstacles:
            self.game_over = True
            return

        tail = self.snake[0]
        body = set(self.snake[1:])
        if new_head in body or (new_head == tail and new_head != self.food):
            self.game_over = True
            return

        self.snake.append(new_head)
        if new_head == self.food:
            self.score += self.speed.fruit_score
            self._spawn_food()
        else:
            self.snake.pop(0)

    def _spawn_food(self) -> None:
        blocked = set(self.snake) | self.obstacles
        spaces = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in blocked]
        if not spaces:
            self.game_over = True
            self.food = self.snake[-1]
            return
        self.food = self._rng.choice(spaces)

    def _initial_snake(self) -> list[tuple[int, int]]:
        preferred = (self.rows // 2, self.cols // 2)
        candidates = [preferred]
        candidates.extend((r, c) for r in range(self.rows) for c in range(1, self.cols - 1) if (r, c) != preferred)
        for r, c in candidates:
            snake = [(r, c - 1), (r, c), (r, c + 1)]
            if all(cell not in self.obstacles for cell in snake):
                return snake
        raise ValueError("Map leaves no safe snake start.")
