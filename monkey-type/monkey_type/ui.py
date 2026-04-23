from __future__ import annotations

from math import ceil

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.timer import Timer
from textual.widgets import Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import TypingSession, WordResult, make_session
from .words import WORDS

_EXTRA_CSS = """
#words-panel {
    height: 7;
    border: round #3a5a9c;
    background: #0a1828;
    padding: 1 2;
    margin: 0 0 1 0;
}

#progress-panel {
    height: 2;
    margin: 0 0 1 0;
}

#main-stats-panel {
    height: 1fr;
    border: round #46659f;
    background: #0d1627;
    padding: 0 1;
}

#wpm-panel {
    height: 5;
    border: round #5b7cbe;
    content-align: center middle;
    margin: 0 0 1 0;
}

#sparkline-panel {
    height: 4;
    border: round #46659f;
    background: #0d1627;
    padding: 0 1;
    margin: 0 0 1 0;
}

#side-stats-panel {
    height: 1fr;
    border: round #46659f;
    background: #0d1627;
    padding: 0 1;
}
"""

_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"
_BAR_BLOCKS = " ▁▂▃▄▅▆▇█"


def _build_line_layout(words: list[str], target_width: int = 65) -> tuple[list[list[int]], dict[int, int]]:
    lines: list[list[int]] = []
    current: list[int] = []
    width = 0
    for idx, word in enumerate(words):
        extra = len(word) if not current else len(word) + 1
        if current and width + extra > target_width:
            lines.append(current)
            current = [idx]
            width = len(word)
            continue
        current.append(idx)
        width += extra
    if current:
        lines.append(current)

    word_to_line: dict[int, int] = {}
    for line_idx, line in enumerate(lines):
        for word_idx in line:
            word_to_line[word_idx] = line_idx
    return lines, word_to_line


def _resample(values: list[float], target_count: int) -> list[float]:
    if not values or target_count <= 0:
        return []
    if len(values) <= target_count:
        return values[:]

    compact: list[float] = []
    length = len(values)
    for column in range(target_count):
        start = round(column * length / target_count)
        end = round((column + 1) * length / target_count)
        segment = values[start:end] or [values[min(start, length - 1)]]
        compact.append(sum(segment) / len(segment))
    return compact


class MonkeyTypeApp(ThemedApp, inherit_bindings=False):
    CSS = COMMON_CSS + _EXTRA_CSS
    BINDINGS = [
        Binding("question_mark", "toggle_help", "Help"),
        Binding("q", "quit_app", "Quit"),
        Binding("tab", "restart", show=False, priority=True),
        Binding("escape", "restart", show=False, priority=True),
    ]

    def __init__(self, *, duration: int = 30, word_count: int = 0, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.duration = duration
        self.word_count = word_count
        self.session: TypingSession
        self._line_layout: list[list[int]]
        self._word_to_line: dict[int, int]
        self._timer: Timer | None = None
        self.help_text = (
            "Type to start  Space submit word  Backspace delete  "
            "Tab/Esc new test  ? help  q quit"
        )
        self._new_session()

    def compose(self) -> ComposeResult:
        yield Static("Monkey Type", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="words-panel")
                yield Static("", id="progress-panel")
                yield Static("", id="main-stats-panel", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="wpm-panel")
                yield Static("", id="sparkline-panel")
                yield Static("", id="side-stats-panel")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self._timer = self.set_interval(0.1, self.on_tick)
        self.refresh_view()

    def _new_session(self) -> None:
        self.session = make_session(WORDS, duration=self.duration, target_count=self.word_count)
        self._line_layout, self._word_to_line = _build_line_layout(self.session.words)

    def on_tick(self) -> None:
        self.session.tick()
        self.refresh_view()

    def on_key(self, event: Key) -> None:
        key = event.key
        if key in {"tab", "escape"}:
            self.action_restart()
            event.stop()
            return

        if key in {"backspace", "ctrl+h"}:
            self.session.backspace()
            self.refresh_view()
            event.stop()
            return

        if key == "space":
            self.session.submit_word()
            self.refresh_view()
            event.stop()
            return

        if key in {"q", "question_mark"}:
            return

        character = event.character
        if character and character.isprintable() and not character.isspace():
            self.session.type_char(character)
            self.refresh_view()
            event.stop()

    def action_restart(self) -> None:
        self._new_session()
        self.refresh_view()
        self.update_status(f"New {self._mode_label()} ready. Type to start.")

    def refresh_view(self) -> None:
        self.query_one("#words-panel", Static).update(self.render_words_panel())
        self.query_one("#progress-panel", Static).update(self.render_progress_panel())
        self.query_one("#main-stats-panel", Static).update(self.render_main_stats_panel())
        self.query_one("#wpm-panel", Static).update(self.render_wpm_panel())
        self.query_one("#sparkline-panel", Static).update(self.render_sparkline_panel())
        self.query_one("#side-stats-panel", Static).update(self.render_side_stats_panel())
        self.update_status(self.render_status_message())

    def render_status_message(self) -> str:
        if self.session.finished:
            return "Test finished. Press Tab or Esc for a new test, or q to quit."
        if not self.session.started:
            return f"Ready for a {self._mode_label()}. Type to start."
        if self.duration > 0:
            return f"Typing... {ceil(self.session.remaining)}s left. Press Space to confirm each word."
        return (
            f"Typing... {len(self.session.completed)}/{self.word_count} words complete. "
            "Press Space to confirm each word."
        )

    def render_words_panel(self) -> Text:
        if self.session.finished:
            return self._render_results_summary()

        current_line = self._word_to_line.get(self.session.current_word_idx, 0)
        start_line = max(0, min(current_line - 1, max(0, len(self._line_layout) - 3)))
        visible = self._line_layout[start_line : start_line + 3]

        text = Text()
        for row in range(3):
            if row < len(visible):
                text.append_text(self._render_line(visible[row]))
            if row < 2:
                text.append("\n")
        return text

    def render_progress_panel(self) -> Text:
        if self.session.finished:
            text = Text()
            text.append("Complete ", style="bold bright_green")
            text.append(f"{self._mode_label()}  ")
            text.append("[Tab] new test  [q] quit", style="dim")
            return text

        width = max(12, min(42, self._panel_inner_width("progress-panel", 40) - 12))
        if self.duration > 0:
            progress = min(1.0, self.session.elapsed / max(1, self.duration))
            filled = min(width, int(round(progress * width)))
            remaining_ratio = 1.0 - progress
            if remaining_ratio > 0.5:
                color = "bright_cyan"
            elif remaining_ratio > 0.2:
                color = "yellow"
            else:
                color = "red"
            label = f" {ceil(self.session.remaining)}s left"
        else:
            total = max(1, self.word_count)
            progress = len(self.session.completed) / total
            filled = min(width, int(round(progress * width)))
            color = "bright_cyan"
            label = f" {len(self.session.completed)}/{total} words"

        text = Text()
        text.append("█" * filled, style=color)
        text.append("░" * (width - filled), style="dim")
        text.append(label)
        return text

    def render_main_stats_panel(self) -> Text:
        if self.session.finished:
            return self._render_history_chart()

        text = Text()
        if not self.session.started:
            text.append("Type to start\n", style="bold")
            text.append(self._mode_label(), style="bright_cyan")
            text.append("  ")
            text.append("3 visible lines  Space confirms word", style="dim")
            return text

        text.append("wpm ", style="dim")
        text.append(f"{self.session.wpm():.1f}", style="bold bright_cyan")
        text.append("   raw ", style="dim")
        text.append(f"{self.session.raw_wpm():.1f}", style="white")
        text.append("   acc ", style="dim")
        acc_style = "green" if self.session.accuracy() >= 95 else "yellow"
        text.append(f"{self.session.accuracy():.1f}%", style=acc_style)
        text.append("   err ", style="dim")
        err = self.session.error_count()
        text.append(str(err), style="red" if err > 0 else "dim")
        text.append("\n")
        text.append("completed ", style="dim")
        text.append(str(len(self.session.completed)), style="bright_white")
        text.append(" words   peak ", style="dim")
        text.append(f"{self._peak_wpm():.1f}", style="bright_green")
        text.append("   avg ", style="dim")
        text.append(f"{self._avg_wpm():.1f}", style="cyan")
        return text

    def render_wpm_panel(self) -> Text:
        text = Text()
        text.append("WPM\n", style="dim")
        if not self.session.started:
            text.append("—", style="dim")
        else:
            text.append(f"{self.session.wpm():.1f}", style="bold bright_cyan")
        return text

    def render_sparkline_panel(self) -> Text:
        values = self._history_snapshot()
        width = 24
        spark = self._sparkline(values, width)
        text = Text()
        text.append("Trend\n", style="dim")
        text.append(spark, style="bright_cyan" if values else "dim")
        return text

    def render_side_stats_panel(self) -> Text:
        text = Text()
        text.append("raw ", style="dim")
        text.append(f"{self.session.raw_wpm():.1f}", style="white")
        text.append("\n")
        text.append("acc ", style="dim")
        acc_style = "green" if self.session.accuracy() >= 95 else "yellow"
        text.append(f"{self.session.accuracy():.1f}%", style=acc_style)
        text.append("\n")
        text.append("err ", style="dim")
        err = self.session.error_count()
        text.append(str(err), style="red" if err > 0 else "dim")
        text.append("\n")
        if not self.session.started:
            text.append("mode ", style="dim")
            text.append(self._mode_label(), style="bright_white")
            return text

        text.append("peak ", style="dim")
        text.append(f"{self._peak_wpm():.1f}", style="bright_green")
        text.append("\n")
        text.append("avg ", style="dim")
        text.append(f"{self._avg_wpm():.1f}", style="cyan")
        if self.session.finished:
            text.append("\n")
            text.append("consistency ", style="dim")
            text.append(f"{self.session.consistency():.1f}%", style="bright_white")
        return text

    def _render_line(self, word_indexes: list[int]) -> Text:
        text = Text()
        for offset, word_idx in enumerate(word_indexes):
            if offset:
                text.append(" ")
            if word_idx < len(self.session.completed):
                text.append_text(self._render_completed_word(self.session.completed[word_idx]))
            elif word_idx == self.session.current_word_idx:
                text.append_text(self._render_current_word(self.session.current_word, self.session.current_input))
            else:
                text.append(self.session.words[word_idx], style="dim")
        return text

    def _render_completed_word(self, result: WordResult) -> Text:
        text = Text()
        shared = min(len(result.word), len(result.typed))
        for idx in range(shared):
            style = "green" if result.typed[idx] == result.word[idx] else "red"
            text.append(result.typed[idx], style=style)
        if len(result.word) > shared:
            text.append(result.word[shared:], style="dim red")
        if len(result.typed) > shared:
            text.append(result.typed[shared:], style="bold red")
        return text

    def _render_current_word(self, word: str, typed: str) -> Text:
        text = Text()
        shared = min(len(word), len(typed))
        for idx in range(shared):
            style = "bright_white" if typed[idx] == word[idx] else "bold red on red"
            text.append(typed[idx], style=style)
        if len(typed) > shared:
            text.append(typed[shared:], style="bold red")
        if len(typed) < len(word):
            cursor = len(typed)
            text.append(word[cursor], style="underline white")
            if cursor + 1 < len(word):
                text.append(word[cursor + 1 :], style="dim white")
        else:
            text.append(" ", style="underline white")
        return text

    def _render_results_summary(self) -> Text:
        text = Text()
        text.append("wpm ", style="dim")
        text.append(f"{self.session.wpm():.1f}", style="bold bright_cyan")
        text.append("   raw ", style="dim")
        text.append(f"{self.session.raw_wpm():.1f}", style="white")
        text.append("   acc ", style="dim")
        acc_style = "green" if self.session.accuracy() >= 95 else "yellow"
        text.append(f"{self.session.accuracy():.1f}%", style=acc_style)
        text.append("\n")
        text.append("err ", style="dim")
        err = self.session.error_count()
        text.append(str(err), style="red" if err > 0 else "dim")
        text.append("   consistency ", style="dim")
        text.append(f"{self.session.consistency():.1f}%", style="bright_white")
        text.append("   words ", style="dim")
        text.append(str(len(self.session.completed)), style="bright_white")
        return text

    def _render_history_chart(self) -> Text:
        values = self._history_snapshot()
        chart_width = max(8, self._panel_inner_width("main-stats-panel", 52) - 7)
        samples = _resample(values, chart_width)
        if not samples:
            samples = [0.0]

        avg = sum(samples) / len(samples)
        peak = max(samples)
        max_value = max(10.0, peak)
        chart_height = 8

        text = Text()
        text.append("WPM history\n", style="bold")
        for row in range(chart_height, 0, -1):
            label = max_value * row / chart_height
            text.append(f"{label:>4.0f} │", style="dim")
            for value in samples:
                total_units = 0.0 if max_value == 0 else value / max_value * chart_height * 8
                row_units = total_units - (row - 1) * 8
                units = max(0, min(8, int(round(row_units))))
                if units == 0:
                    text.append(" ")
                else:
                    style = "bright_green" if value >= avg else "green"
                    text.append(_BAR_BLOCKS[units], style=style)
            text.append("│", style="dim")
            text.append("\n")

        text.append("   0 └", style="dim")
        text.append("─" * len(samples), style="dim")
        text.append("┘", style="dim")
        text.append("\n")
        text.append("avg ", style="dim")
        text.append(f"{self._avg_wpm():.1f}", style="cyan")
        text.append("  peak ", style="dim")
        text.append(f"{self._peak_wpm():.1f}", style="bright_green")
        text.append("  consistency ", style="dim")
        text.append(f"{self.session.consistency():.1f}%", style="bright_white")
        text.append("\n")
        text.append("[Tab] new test  [q] quit", style="dim")
        return text

    def _history_snapshot(self) -> list[float]:
        values = self.session.wpm_history[:]
        if self.session.started:
            current = round(self.session.wpm(), 1)
            if not values or values[-1] != current:
                values.append(current)
        return values

    def _sparkline(self, values: list[float], width: int) -> str:
        if not values:
            return "▁" * width
        compact = _resample(values, width)
        if len(compact) < width:
            compact = [0.0] * (width - len(compact)) + compact
        peak = max(compact) or 1.0
        chars: list[str] = []
        for value in compact:
            idx = min(len(_SPARK_BLOCKS) - 1, int(round(value / peak * (len(_SPARK_BLOCKS) - 1))))
            chars.append(_SPARK_BLOCKS[idx])
        return "".join(chars)

    def _avg_wpm(self) -> float:
        values = self._history_snapshot()
        return sum(values) / len(values) if values else 0.0

    def _peak_wpm(self) -> float:
        values = self._history_snapshot()
        return max(values) if values else 0.0

    def _panel_inner_width(self, widget_id: str, fallback: int) -> int:
        try:
            widget = self.query_one(f"#{widget_id}", Static)
        except Exception:
            return fallback
        return max(10, widget.size.width - 2)

    def _mode_label(self) -> str:
        if self.duration > 0:
            return f"{self.duration}s timed test"
        return f"{self.word_count} word test"


def run_monkey_type(*, duration: int = 30, word_count: int = 0, theme: str = "modern") -> int:
    return MonkeyTypeApp(duration=duration, word_count=word_count, theme=theme).run() or 0
