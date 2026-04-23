from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Ball:
    row: float
    col: float
    dr: float
    dc: float


@dataclass
class PowerUp:
    kind: str  # 'expand', 'extra_life', 'slow', 'multi_ball', 'shrink'
    row: float
    col: float


POWERUP_KINDS = ["expand", "extra_life", "slow", "multi_ball", "shrink"]
EFFECT_DURATIONS = {"expand": 200, "slow": 150, "multi_ball": 300, "shrink": 150}
POWERUP_DROP_CHANCE = 0.30


@dataclass
class BreakoutGame:
    rows: int = 32
    cols: int = 24

    board: list[list[int]] = field(init=False)
    balls: list[Ball] = field(init=False)
    powerups: list[PowerUp] = field(init=False)
    active_effects: dict[str, int] = field(init=False)
    paddle_col: int = field(init=False)
    paddle_width: int = field(init=False)
    lives: int = field(init=False)
    score: int = field(init=False)
    level: int = field(init=False)
    combo: int = field(init=False)
    _combo_timer: int = field(init=False)
    ball_speed: float = field(init=False)
    won: bool = field(init=False)
    game_over: bool = field(init=False)

    BASE_PADDLE_WIDTH: ClassVar[int] = 5

    def __post_init__(self) -> None:
        if self.rows < 18 or self.cols < 8:
            raise ValueError("Board too small.")
        self.restart()

    def restart(self) -> None:
        self.level = 1
        self.score = 0
        self.lives = 3
        self.combo = 0
        self._combo_timer = 0
        self.ball_speed = 1.0
        self.paddle_width = self.BASE_PADDLE_WIDTH
        self.paddle_col = (self.cols - self.paddle_width) // 2
        self.powerups = []
        self.active_effects = {}
        self.won = False
        self.game_over = False
        self.board = self._make_bricks(self.level)
        self.balls = [self._spawn_ball()]

    def _spawn_ball(self) -> Ball:
        return Ball(
            row=float(self.rows // 2),
            col=float(self.cols // 2),
            dr=-1.0,
            dc=1.0,
        )

    def _make_bricks(self, level: int) -> list[list[int]]:
        board: list[list[int]] = [[0] * self.cols for _ in range(self.rows)]

        if level == 1:
            brick_rows = 4
            pattern = [1, 1, 1, 1]
        elif level == 2:
            brick_rows = 5
            pattern = [2, 2, 1, 1, 1]
        elif level == 3:
            brick_rows = 6
            pattern = [3, 2, 2, 1, 1, 1]
        else:
            brick_rows = min(6 + (level - 3), 10)
            pattern = [3] * 2 + [2] * 2 + [1] * (brick_rows - 4)

        for r, hp in enumerate(pattern[:brick_rows]):
            for c in range(self.cols):
                if level >= 3 and r == 0 and c % 5 == 0:
                    board[r][c] = -1  # unbreakable
                else:
                    board[r][c] = hp

        return board

    def _next_level(self) -> None:
        self.level += 1
        self.ball_speed = min(1.0 + 0.15 * (self.level - 1), 2.0)
        self.paddle_width = self.BASE_PADDLE_WIDTH
        self.paddle_col = (self.cols - self.paddle_width) // 2
        self.powerups = []
        self.active_effects = {}
        self.board = self._make_bricks(self.level)
        self.balls = [self._spawn_ball()]

    def move_paddle_left(self) -> None:
        if not self.game_over and not self.won and self.paddle_col > 0:
            self.paddle_col -= 1

    def move_paddle_right(self) -> None:
        if not self.game_over and not self.won and self.paddle_col + self.paddle_width < self.cols:
            self.paddle_col += 1

    def _combo_multiplier(self) -> int:
        if self.combo >= 10:
            return 5
        if self.combo >= 6:
            return 3
        if self.combo >= 3:
            return 2
        return 1

    def step(self) -> None:
        if self.game_over or self.won:
            return

        # Tick effects
        self._combo_timer += 1
        if self._combo_timer > 60:
            self.combo = 0

        expired = [k for k, v in self.active_effects.items() if v <= 1]
        for k in expired:
            del self.active_effects[k]
            if k == "expand":
                self.paddle_width = self.BASE_PADDLE_WIDTH
                self.paddle_col = min(self.paddle_col, self.cols - self.paddle_width)
            elif k == "shrink":
                self.paddle_width = self.BASE_PADDLE_WIDTH
                self.paddle_col = min(self.paddle_col, self.cols - self.paddle_width)
        for k in self.active_effects:
            self.active_effects[k] -= 1

        # Move all balls
        lost_balls: list[int] = []
        for i, ball in enumerate(self.balls):
            fell = self._move_ball_single(ball)
            if fell:
                lost_balls.append(i)

        for i in reversed(lost_balls):
            self.balls.pop(i)

        if not self.balls:
            self.combo = 0
            self._combo_timer = 0
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                self.balls = [self._spawn_ball()]

        # Move powerups
        paddle_row = self.rows - 1
        caught: list[int] = []
        for i, pu in enumerate(self.powerups):
            pu.row += 0.3
            if pu.row >= paddle_row:
                pc = int(pu.col)
                if self.paddle_col <= pc < self.paddle_col + self.paddle_width:
                    self._activate_powerup(pu.kind)
                caught.append(i)
            elif pu.row > self.rows:
                caught.append(i)
        for i in reversed(sorted(set(caught))):
            self.powerups.pop(i)

        # Check win
        if self._no_breakable_bricks():
            self._next_level()

    def _no_breakable_bricks(self) -> bool:
        return not any(
            self.board[r][c] > 0
            for r in range(self.rows)
            for c in range(self.cols)
        )

    def _activate_powerup(self, kind: str) -> None:
        if kind == "extra_life":
            self.lives = min(self.lives + 1, 5)
        elif kind == "expand":
            self.active_effects.pop("shrink", None)
            self.active_effects["expand"] = EFFECT_DURATIONS["expand"]
            self.paddle_width = min(self.BASE_PADDLE_WIDTH + 3, self.cols // 2)
        elif kind == "shrink":
            self.active_effects.pop("expand", None)
            self.active_effects["shrink"] = EFFECT_DURATIONS["shrink"]
            self.paddle_width = max(self.BASE_PADDLE_WIDTH - 2, 2)
            self.paddle_col = min(self.paddle_col, self.cols - self.paddle_width)
        elif kind == "slow":
            self.active_effects["slow"] = EFFECT_DURATIONS["slow"]
        elif kind == "multi_ball":
            self.active_effects["multi_ball"] = EFFECT_DURATIONS["multi_ball"]
            for ball in list(self.balls):
                self.balls.append(Ball(ball.row, ball.col, -ball.dr, -ball.dc))

    def _move_ball_single(self, ball: Ball) -> bool:
        speed = self.ball_speed
        if "slow" in self.active_effects:
            speed *= 0.6

        dr = ball.dr * speed
        dc = ball.dc * speed

        new_row = ball.row + dr
        new_col = ball.col + dc

        # Left/right wall bounce
        if new_col < 0:
            new_col = -new_col
            ball.dc = -ball.dc
        elif new_col >= self.cols:
            new_col = 2.0 * (self.cols - 1) - new_col
            ball.dc = -ball.dc

        # Top wall bounce
        if new_row < 0:
            new_row = -new_row
            ball.dr = -ball.dr

        # Bottom: ball fell
        if new_row >= self.rows:
            return True

        # Brick collision
        br, bc = int(new_row), int(new_col)
        if 0 <= br < self.rows and 0 <= bc < self.cols and self.board[br][bc] > 0:
            hp = self.board[br][bc]
            self.board[br][bc] = hp - 1
            mult = self._combo_multiplier()
            self.score += 10 * mult
            self.combo += 1
            self._combo_timer = 0
            ball.dr = -ball.dr
            new_row = ball.row + ball.dr * speed

            # Maybe drop powerup
            if self.board[br][bc] == 0 and random.random() < POWERUP_DROP_CHANCE:
                kind = random.choice(POWERUP_KINDS)
                self.powerups.append(PowerUp(kind=kind, row=float(br), col=float(bc)))

        # Paddle collision
        paddle_row = self.rows - 1
        if int(new_row) == paddle_row and self.paddle_col <= int(new_col) < self.paddle_col + self.paddle_width:
            center = self.paddle_width // 2
            hit = int(new_col) - self.paddle_col
            offset = hit - center
            ball.dc = float(offset) if offset != 0 else (1.0 if ball.dc >= 0 else -1.0)
            ball.dr = -abs(ball.dr)

        ball.row = max(0.0, min(float(self.rows - 1), new_row))
        ball.col = max(0.0, min(float(self.cols - 1), new_col))
        return False

    @property
    def paddle_cells(self) -> range:
        return range(self.paddle_col, self.paddle_col + self.paddle_width)

    @property
    def brick_count(self) -> int:
        return sum(1 for r in range(self.rows) for c in range(self.cols) if self.board[r][c] > 0)
