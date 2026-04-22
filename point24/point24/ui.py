from __future__ import annotations

import time
from dataclasses import dataclass
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static

from ._textual_base import COMMON_CSS, ThemedApp
from point24.core import validate_submission
from point24.storage import Point24Puzzle, Point24Repository, Point24Stats


@dataclass
class _SessionState:
    puzzle: Point24Puzzle
    started_at: float


class ExpressionInput(Input):
    def on_key(self, event: events.Key) -> None:
        shortcut_actions = {
            "t": "action_toggle_theme",
            "question_mark": "action_toggle_help",
            "q": "action_quit_app",
            "n": "action_skip_puzzle",
        }
        action_name = shortcut_actions.get(event.key)
        if action_name is None:
            return
        event.prevent_default()
        event.stop()
        action = getattr(self.app, action_name, None)
        if action is not None:
            action()


class Point24App(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #numbers-view {
            content-align: center middle;
            text-style: bold;
            height: 5;
        }

        #actions {
            height: auto;
        }

        #actions Button {
            margin-right: 1;
            min-width: 10;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("n", "skip_puzzle", "Skip", priority=True),
        Binding("ctrl+enter", "submit_expression", "Submit", show=False, priority=True),
    ]
    help_text = "Type an expression and press Enter or Submit. n skips. t switches theme."

    def __init__(self, repository: Point24Repository | None = None, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.repository = repository or Point24Repository()
        self.catalog = self.repository.ensure_catalog()
        self.stats = self.repository.load_stats()
        first_puzzle = self.repository.choose_next_puzzle(self.catalog, self.stats.solved_puzzle_keys)
        self.stats.mark_started()
        self.repository.save_stats(self.stats)
        self.session = _SessionState(puzzle=first_puzzle, started_at=time.monotonic())
        self.message = "Enter an expression that evaluates to 24 using each number exactly once."

    def compose(self) -> ComposeResult:
        yield Static("24 Point", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="numbers-view")
                yield ExpressionInput(placeholder="(8 / (3 - (8 / 3)))", id="expression")
                with Horizontal(id="actions"):
                    yield Button("Submit", id="submit")
                    yield Button("Skip", id="skip")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.set_interval(0.2, self.refresh_view)
        self.refresh_view()
        self.query_one("#expression", Input).focus()

    def refresh_view(self) -> None:
        elapsed = time.monotonic() - self.session.started_at
        numbers = "   ".join(str(number) for number in self.session.puzzle.numbers)
        self.query_one("#numbers-view", Static).update(
            "\n".join(
                [
                    f"Numbers: {numbers}",
                    f"Elapsed: {elapsed:.1f}s",
                    f"Puzzle key: {self.session.puzzle.key}",
                ]
            )
        )
        stats_lines = [
            f"Started: {self.stats.puzzles_started}",
            f"Solved: {self.stats.puzzles_solved}",
            f"Success rate: {self.stats.success_rate * 100:.1f}%",
            f"Average solve: {self.stats.average_solve_seconds:.1f}s",
            f"Unique solved: {len(self.stats.solved_puzzle_keys)}/{len(self.catalog)}",
            "",
            "Rules:",
            "Use all four numbers exactly once.",
            "Operators: + - * / and parentheses.",
        ]
        self.query_one("#stats-view", Static).update("\n".join(stats_lines))
        self.update_status(self.message)

    def submit_current_expression(self) -> None:
        expression = self.query_one("#expression", Input).value.strip()
        if not expression:
            self.message = "Expression cannot be empty."
            self.refresh_view()
            return
        try:
            validate_submission(self.session.puzzle.numbers, expression)
        except ValueError as exc:
            self.message = str(exc)
        else:
            elapsed = time.monotonic() - self.session.started_at
            self.stats.mark_solved(self.session.puzzle.key, elapsed)
            self.repository.save_stats(self.stats)
            self.message = f"Correct in {elapsed:.1f}s."
            self.advance_puzzle()
        self.query_one("#expression", Input).value = ""
        self.refresh_view()

    def advance_puzzle(self) -> None:
        next_puzzle = self.repository.choose_next_puzzle(self.catalog, self.stats.solved_puzzle_keys)
        self.stats.mark_started()
        self.repository.save_stats(self.stats)
        self.session = _SessionState(puzzle=next_puzzle, started_at=time.monotonic())

    def action_skip_puzzle(self) -> None:
        self.message = f"Skipped. One solution: {self.session.puzzle.solution}"
        self.advance_puzzle()
        self.query_one("#expression", Input).value = ""
        self.refresh_view()

    def action_submit_expression(self) -> None:
        self.submit_current_expression()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "expression":
            self.submit_current_expression()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.submit_current_expression()
        elif event.button.id == "skip":
            self.action_skip_puzzle()


def run_point24_game(*, theme: str = "modern") -> int:
    return Point24App(theme=theme).run() or 0
