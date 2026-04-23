from __future__ import annotations

import random
from dataclasses import dataclass, field

DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


@dataclass
class SnakeGame:
    rows: int = 16
    cols: int = 24
    seed: int | None = None
    snake: list[tuple[int, int]] = field(init=False)
    direction: str = field(init=False, default="right")
    next_direction: str = field(init=False, default="right")
    food: tuple[int, int] = field(init=False)
    score: int = field(init=False, default=0)
    game_over: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.rows < 4 or self.cols < 4:
            raise ValueError("Board is too small.")
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        r, c = self.rows // 2, self.cols // 2
        self.snake = [(r, c - 1), (r, c), (r, c + 1)]
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

        if nr < 0 or nr >= self.rows or nc < 0 or nc >= self.cols:
            self.game_over = True
            return

        new_head = (nr, nc)
        tail = self.snake[0]
        body = set(self.snake[1:])
        if new_head in body or (new_head == tail and new_head != self.food):
            self.game_over = True
            return

        self.snake.append(new_head)
        if new_head == self.food:
            self.score += 1
            self._spawn_food()
        else:
            self.snake.pop(0)

    def _spawn_food(self) -> None:
        spaces = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in set(self.snake)]
        if not spaces:
            self.game_over = True
            self.food = self.snake[-1]
            return
        self.food = self._rng.choice(spaces)
