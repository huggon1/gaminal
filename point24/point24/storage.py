from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

from point24.core import CATALOG_VERSION, find_solution, iter_all_puzzle_keys, parse_puzzle_key


@dataclass
class Point24Stats:
    schema_version: int = 1
    puzzles_started: int = 0
    puzzles_solved: int = 0
    total_solve_seconds: float = 0.0
    solved_puzzle_keys: set[str] = field(default_factory=set)

    @property
    def success_rate(self) -> float:
        if self.puzzles_started == 0:
            return 0.0
        return self.puzzles_solved / self.puzzles_started

    @property
    def average_solve_seconds(self) -> float:
        if self.puzzles_solved == 0:
            return 0.0
        return self.total_solve_seconds / self.puzzles_solved

    def mark_started(self) -> None:
        self.puzzles_started += 1

    def mark_solved(self, key: str, elapsed_seconds: float) -> None:
        self.puzzles_solved += 1
        self.total_solve_seconds += max(0.0, elapsed_seconds)
        self.solved_puzzle_keys.add(key)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "puzzles_started": self.puzzles_started,
            "puzzles_solved": self.puzzles_solved,
            "total_solve_seconds": self.total_solve_seconds,
            "solved_puzzle_keys": sorted(self.solved_puzzle_keys),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Point24Stats":
        version = int(payload.get("schema_version", 1))
        if version != 1:
            raise ValueError("Unsupported stats schema version.")
        solved = payload.get("solved_puzzle_keys", [])
        if not isinstance(solved, list):
            raise ValueError("Solved puzzle keys must be a list.")
        return cls(
            schema_version=version,
            puzzles_started=int(payload.get("puzzles_started", 0)),
            puzzles_solved=int(payload.get("puzzles_solved", 0)),
            total_solve_seconds=float(payload.get("total_solve_seconds", 0.0)),
            solved_puzzle_keys={str(item) for item in solved},
        )


@dataclass(frozen=True)
class Point24Puzzle:
    key: str
    numbers: tuple[int, int, int, int]
    solution: str


def default_state_dir() -> Path:
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    base_dir = Path(xdg_state_home) if xdg_state_home else Path.home() / ".local" / "state"
    return base_dir / "terminal-games" / "point24"


class Point24Repository:
    def __init__(self, state_dir: Path | None = None) -> None:
        self.state_dir = state_dir or default_state_dir()
        self.catalog_path = self.state_dir / "catalog.json"
        self.stats_path = self.state_dir / "stats.json"

    def ensure_catalog(self) -> list[Point24Puzzle]:
        cached = self._load_catalog()
        if cached is not None:
            return cached

        puzzles: list[Point24Puzzle] = []
        for key in iter_all_puzzle_keys():
            numbers = parse_puzzle_key(key)
            solution = find_solution(numbers)
            if solution is not None:
                puzzles.append(Point24Puzzle(key=key, numbers=numbers, solution=solution))
        self._write_json(
            self.catalog_path,
            {
                "version": CATALOG_VERSION,
                "puzzles": [{"key": puzzle.key, "solution": puzzle.solution} for puzzle in puzzles],
            },
        )
        return puzzles

    def load_stats(self) -> Point24Stats:
        if not self.stats_path.exists():
            return Point24Stats()
        try:
            payload = json.loads(self.stats_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return Point24Stats()
        if not isinstance(payload, dict):
            return Point24Stats()
        try:
            return Point24Stats.from_dict(payload)
        except (TypeError, ValueError):
            return Point24Stats()

    def save_stats(self, stats: Point24Stats) -> None:
        self._write_json(self.stats_path, stats.to_dict())

    def choose_next_puzzle(
        self,
        puzzles: list[Point24Puzzle],
        solved_puzzle_keys: set[str],
        rng: Random | None = None,
    ) -> Point24Puzzle:
        chooser = rng or Random()
        unsolved = [puzzle for puzzle in puzzles if puzzle.key not in solved_puzzle_keys]
        return chooser.choice(unsolved or puzzles)

    def _load_catalog(self) -> list[Point24Puzzle] | None:
        if not self.catalog_path.exists():
            return None
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
        if not isinstance(payload, dict) or int(payload.get("version", -1)) != CATALOG_VERSION:
            return None
        raw_puzzles = payload.get("puzzles")
        if not isinstance(raw_puzzles, list):
            return None

        puzzles: list[Point24Puzzle] = []
        for item in raw_puzzles:
            if not isinstance(item, dict):
                return None
            key = str(item.get("key", ""))
            solution = str(item.get("solution", ""))
            if not key or not solution:
                return None
            puzzles.append(Point24Puzzle(key=key, numbers=parse_puzzle_key(key), solution=solution))
        return puzzles

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(serialized)
            handle.write("\n")
            temp_name = handle.name
        Path(temp_name).replace(path)
