from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class FishState(Enum):
    FISHING = "fishing"
    CAUGHT = "caught"
    ESCAPED = "escaped"
    WAITING = "waiting"


@dataclass
class FishType:
    name: str
    agility: float
    jitter: float
    score: int
    symbol: str


FISH_TYPES: list[FishType] = [
    FishType("Carp",    0.08, 0.02, 10,  "~o~"),
    FishType("Bass",    0.15, 0.10, 25,  "><>"),
    FishType("Catfish", 0.22, 0.18, 50,  "==>"),
    FishType("Squid",   0.30, 0.28, 100, "~~~"),
]

# Weights indexed by fish_caught milestones (0, 10, 20, 30+)
DIFFICULTY_TABLE: list[tuple[int, list[float]]] = [
    (0,  [0.70, 0.25, 0.05, 0.00]),
    (10, [0.20, 0.40, 0.30, 0.10]),
    (20, [0.00, 0.20, 0.40, 0.40]),
    (30, [0.00, 0.00, 0.30, 0.70]),
]


def _get_weights(fish_caught: int) -> list[float]:
    weights = DIFFICULTY_TABLE[0][1]
    for threshold, w in DIFFICULTY_TABLE:
        if fish_caught >= threshold:
            weights = w
    return weights


@dataclass
class FishingGame:
    seed: int | None = None
    zone_height: int = 20
    indicator_height: int = 5

    ind_pos: float = field(init=False)
    ind_vel: float = field(init=False)
    fish_pos: float = field(init=False)
    fish_vel: float = field(init=False)
    fish_target: float = field(init=False)
    catch_progress: float = field(init=False)
    current_fish: FishType = field(init=False)
    score: int = field(init=False, default=0)
    fish_caught: int = field(init=False, default=0)
    streak: int = field(init=False, default=0)
    escaped: bool = field(init=False, default=False)
    state: FishState = field(init=False, default=FishState.FISHING)
    last_score: int = field(init=False, default=0)
    last_bonus: int = field(init=False, default=1)
    last_fish_name: str = field(init=False, default="")
    _frame: int = field(init=False, default=0)
    _target_timer: int = field(init=False, default=0)
    _result_timer: int = field(init=False, default=0)
    boost_requested: bool = field(init=False, default=False)

    GRAVITY: ClassVar[float] = 0.15
    BOOST: ClassVar[float] = 0.85
    CATCH_RATE: ClassVar[float] = 0.035
    ESCAPE_RATE: ClassVar[float] = 0.018
    FISH_DAMPING: ClassVar[float] = 0.85
    TARGET_INTERVAL_MIN: ClassVar[int] = 20
    TARGET_INTERVAL_MAX: ClassVar[int] = 45
    RESULT_FRAMES: ClassVar[int] = 30   # ~1.5s result display
    WAIT_FRAMES: ClassVar[int] = 20     # ~1s before next fish

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        self.score = 0
        self.fish_caught = 0
        self.streak = 0
        self.escaped = False
        self.state = FishState.FISHING
        self.last_score = 0
        self.last_bonus = 1
        self.last_fish_name = ""
        self._frame = 0
        self._result_timer = 0
        self.boost_requested = False
        self._spawn_fish()

    def _spawn_fish(self) -> None:
        self.escaped = False
        weights = _get_weights(self.fish_caught)
        self.current_fish = self._rng.choices(FISH_TYPES, weights=weights, k=1)[0]
        self.ind_pos = float((self.zone_height - self.indicator_height) // 2)
        self.ind_vel = 0.0
        self.fish_pos = float(self._rng.randint(0, self.zone_height - 1))
        self.fish_vel = 0.0
        self.fish_target = float(self._rng.randint(0, self.zone_height - 1))
        self.catch_progress = 0.5
        self._target_timer = self._rng.randint(self.TARGET_INTERVAL_MIN, self.TARGET_INTERVAL_MAX)

    def request_boost(self) -> None:
        if self.state == FishState.FISHING:
            self.boost_requested = True

    def step(self) -> None:
        self._frame += 1
        if self.state == FishState.FISHING:
            self._update_indicator()
            self._update_fish()
            self._update_catch()
        elif self.state in (FishState.CAUGHT, FishState.ESCAPED):
            self._result_timer -= 1
            if self._result_timer <= 0:
                self.state = FishState.WAITING
                self._result_timer = self.WAIT_FRAMES
        elif self.state == FishState.WAITING:
            self._result_timer -= 1
            if self._result_timer <= 0:
                self._spawn_fish()
                self.state = FishState.FISHING

    def _update_indicator(self) -> None:
        if self.boost_requested:
            self.ind_vel = self.BOOST
            self.boost_requested = False
        self.ind_vel -= self.GRAVITY
        self.ind_pos += self.ind_vel
        max_pos = float(self.zone_height - self.indicator_height)
        if self.ind_pos < 0.0:
            self.ind_pos = 0.0
            self.ind_vel = 0.0
        elif self.ind_pos > max_pos:
            self.ind_pos = max_pos
            self.ind_vel = 0.0

    def _update_fish(self) -> None:
        self._target_timer -= 1
        if self._target_timer <= 0:
            self.fish_target = float(self._rng.randint(0, self.zone_height - 1))
            # Squid: 20% chance to reverse direction after reaching target
            if self.current_fish.name == "Squid" and self._rng.random() < 0.20:
                delta = self.fish_target - self.fish_pos
                self.fish_target = max(0.0, min(float(self.zone_height - 1), self.fish_pos - delta))
            self._target_timer = self._rng.randint(self.TARGET_INTERVAL_MIN, self.TARGET_INTERVAL_MAX)

        fish = self.current_fish
        agility = fish.agility
        jitter = fish.jitter

        # Panic mode: fish struggles harder when nearly caught
        if self.catch_progress > 0.75:
            agility *= 1.5
            jitter *= 3.0

        self.fish_vel += agility * (self.fish_target - self.fish_pos)
        self.fish_vel += self._rng.uniform(-jitter, jitter)
        self.fish_vel *= self.FISH_DAMPING

        # Random sprint: 5% chance per frame
        if self._rng.random() < 0.05:
            direction = 1.0 if self._rng.random() < 0.5 else -1.0
            self.fish_vel += direction * self._rng.uniform(0.3, 0.6)

        self.fish_pos += self.fish_vel
        if self.fish_pos < 0.0:
            self.fish_pos = 0.0
            self.fish_vel = abs(self.fish_vel)
        elif self.fish_pos > self.zone_height - 1:
            self.fish_pos = float(self.zone_height - 1)
            self.fish_vel = -abs(self.fish_vel)

    def _update_catch(self) -> None:
        if self.fish_in_indicator:
            self.catch_progress = min(1.0, self.catch_progress + self.CATCH_RATE)
        else:
            self.catch_progress = max(0.0, self.catch_progress - self.ESCAPE_RATE)

        if self.catch_progress >= 1.0:
            self._on_caught()
        elif self.catch_progress <= 0.0:
            self._on_escaped()

    def _on_caught(self) -> None:
        bonus = 1 + self.streak // 3
        gained = self.current_fish.score * bonus
        self.score += gained
        self.fish_caught += 1
        self.streak += 1
        self.last_score = gained
        self.last_bonus = bonus
        self.last_fish_name = self.current_fish.name
        self.state = FishState.CAUGHT
        self._result_timer = self.RESULT_FRAMES

    def _on_escaped(self) -> None:
        self.last_fish_name = self.current_fish.name
        self.streak = 0
        self.escaped = True
        self.state = FishState.ESCAPED
        self._result_timer = self.RESULT_FRAMES

    @property
    def fish_in_indicator(self) -> bool:
        return self.ind_pos <= self.fish_pos <= self.ind_pos + self.indicator_height - 1
