from __future__ import annotations

import time
from dataclasses import dataclass

from point24.core import validate_submission
from point24.storage import Point24Puzzle, Point24Repository, Point24Stats


def _load_curses():
    try:
        import curses
    except ImportError as exc:
        raise RuntimeError("curses is required for the terminal UI and is typically available on Linux.") from exc
    return curses


@dataclass
class _SessionState:
    puzzle: Point24Puzzle
    started_at: float


class Point24App:
    def __init__(self, repository: Point24Repository | None = None) -> None:
        self.repository = repository or Point24Repository()

    def run(self) -> int:
        catalog = self.repository.ensure_catalog()
        stats = self.repository.load_stats()
        first_puzzle = self.repository.choose_next_puzzle(catalog, stats.solved_puzzle_keys)
        stats.mark_started()
        self.repository.save_stats(stats)

        session = _SessionState(puzzle=first_puzzle, started_at=time.monotonic())
        curses = _load_curses()
        return curses.wrapper(self._main, catalog, stats, session)

    def _main(self, stdscr, catalog: list[Point24Puzzle], stats: Point24Stats, session: _SessionState) -> int:
        curses = _load_curses()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(100)

        prompt = ""
        message = "Enter an expression that evaluates to 24 using each number exactly once."

        while True:
            elapsed = time.monotonic() - session.started_at
            self._render(stdscr, stats, session, prompt, message, elapsed, len(catalog))
            key = stdscr.getch()
            if key == -1:
                continue

            if key in (ord("q"), ord("Q")):
                self.repository.save_stats(stats)
                return 0

            if key in (ord("n"), ord("N")):
                message = f"Skipped. One solution: {session.puzzle.solution}"
                session = self._advance_puzzle(catalog, stats)
                prompt = ""
                continue

            if key in (10, 13):
                submitted = prompt.strip()
                prompt = ""
                if not submitted:
                    continue
                try:
                    validate_submission(session.puzzle.numbers, submitted)
                except ValueError as exc:
                    message = str(exc)
                    continue

                elapsed = time.monotonic() - session.started_at
                stats.mark_solved(session.puzzle.key, elapsed)
                self.repository.save_stats(stats)
                message = f"Correct in {elapsed:.1f}s."
                session = self._advance_puzzle(catalog, stats)
                continue

            if key in (curses.KEY_BACKSPACE, 127, 8):
                prompt = prompt[:-1]
                continue

            if 32 <= key <= 126:
                prompt += chr(key)

    def _advance_puzzle(self, catalog: list[Point24Puzzle], stats: Point24Stats) -> _SessionState:
        next_puzzle = self.repository.choose_next_puzzle(catalog, stats.solved_puzzle_keys)
        stats.mark_started()
        self.repository.save_stats(stats)
        return _SessionState(puzzle=next_puzzle, started_at=time.monotonic())

    def _render(
        self,
        stdscr,
        stats: Point24Stats,
        session: _SessionState,
        prompt: str,
        message: str,
        elapsed: float,
        total_puzzles: int,
    ) -> None:
        curses = _load_curses()
        stdscr.erase()
        numbers = "  ".join(str(number) for number in session.puzzle.numbers)
        lines = [
            "24 Point",
            "",
            f"Numbers: {numbers}",
            f"Timer: {elapsed:.1f}s",
            f"Started: {stats.puzzles_started}  Solved: {stats.puzzles_solved}  Success: {stats.success_rate * 100:.1f}%",
            f"Average solve time: {stats.average_solve_seconds:.1f}s",
            f"Unique solved puzzles: {len(stats.solved_puzzle_keys)}/{total_puzzles}",
            "",
            "Rules: use the four numbers exactly once; operators allowed: + - * / and parentheses.",
            "Commands: Enter submit, n skip, q quit",
            "",
            f"Status: {message}",
            f"> {prompt}",
        ]

        height, width = stdscr.getmaxyx()
        for row, line in enumerate(lines[: max(0, height - 1)]):
            try:
                stdscr.addstr(row, 0, line[: max(0, width - 1)])
            except curses.error:
                pass
        stdscr.refresh()


def run_point24_game() -> int:
    return Point24App().run()
