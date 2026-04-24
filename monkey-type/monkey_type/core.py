from __future__ import annotations
import random, time
from dataclasses import dataclass, field


@dataclass
class WordResult:
    word: str
    typed: str

    @property
    def correct(self) -> bool:
        return self.word == self.typed

    @property
    def correct_chars(self) -> int:
        return sum(1 for a, b in zip(self.typed, self.word) if a == b)


@dataclass
class TypingSession:
    words: list[str]
    duration: int          # seconds; 0 = word-count mode
    target_count: int = 0  # for word-count mode

    completed: list[WordResult] = field(default_factory=list)
    current_input: str = ""
    start_time: float | None = None
    end_time: float | None = None
    wpm_history: list[float] = field(default_factory=list)
    _last_sample: float = 0.0

    @property
    def started(self) -> bool:
        return self.start_time is not None

    @property
    def finished(self) -> bool:
        if self.end_time is not None:
            return True
        if not self.started:
            return False
        if self.duration > 0:
            return time.monotonic() - self.start_time >= self.duration
        return self.target_count > 0 and len(self.completed) >= self.target_count

    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        if self.end_time is not None:
            return self.end_time - self.start_time
        if self.duration > 0:
            return min(float(self.duration), time.monotonic() - self.start_time)
        return time.monotonic() - self.start_time

    @property
    def remaining(self) -> float:
        if self.duration == 0:
            return 0.0
        return max(0.0, self.duration - self.elapsed)

    @property
    def current_word(self) -> str:
        idx = len(self.completed)
        return self.words[idx] if idx < len(self.words) else ""

    @property
    def current_word_idx(self) -> int:
        return len(self.completed)

    def _correct_chars(self) -> int:
        return sum(r.correct_chars for r in self.completed)

    def wpm(self) -> float:
        mins = max(0.001, self.elapsed / 60)
        return self._correct_chars() / 5 / mins

    def raw_wpm(self) -> float:
        total = sum(len(r.typed) + 1 for r in self.completed)
        mins = max(0.001, self.elapsed / 60)
        return total / 5 / mins

    def accuracy(self) -> float:
        total = sum(len(r.typed) for r in self.completed)
        if total == 0:
            return 100.0
        return min(100.0, self._correct_chars() / total * 100)

    def error_count(self) -> int:
        return sum(1 for r in self.completed if not r.correct)

    def consistency(self) -> float:
        h = self.wpm_history
        if len(h) < 2:
            return 100.0
        mean = sum(h) / len(h)
        if mean == 0:
            return 100.0
        variance = sum((x - mean) ** 2 for x in h) / len(h)
        cv = variance ** 0.5 / mean
        return max(0.0, min(100.0, (1 - cv) * 100))

    def type_char(self, char: str) -> None:
        if self.finished:
            return
        if self.start_time is None:
            now = time.monotonic()
            self.start_time = now
            self._last_sample = now
        if len(self.current_input) < len(self.current_word):
            self.current_input += char

    def backspace(self) -> None:
        if self.finished or not self.current_input:
            return
        self.current_input = self.current_input[:-1]

    def submit_word(self) -> bool:
        if self.finished or not self.current_input or self.start_time is None:
            return False
        result = WordResult(word=self.current_word, typed=self.current_input)
        self.completed.append(result)
        self.current_input = ""
        self._sample_wpm(force=True)
        if self.finished:
            self.end_time = time.monotonic()
        return True

    def tick(self) -> None:
        if not self.started or self.finished:
            return
        self._sample_wpm()
        if self.duration > 0 and time.monotonic() - self.start_time >= self.duration:
            self.end_time = time.monotonic()
            self._sample_wpm(force=True)

    def _sample_wpm(self, force: bool = False) -> None:
        if self.start_time is None:
            return
        now = time.monotonic()
        if force or (now - self._last_sample >= 1.0):
            self.wpm_history.append(round(self.wpm(), 1))
            self._last_sample = now


def make_session(
    words: list[str],
    duration: int = 30,
    target_count: int = 0,
    seed: int | None = None,
) -> TypingSession:
    rng = random.Random(seed)
    needed = max(300, target_count + 100)
    pool: list[str] = []
    while len(pool) < needed:
        chunk = words[:]
        rng.shuffle(chunk)
        pool.extend(chunk)
    return TypingSession(words=pool[:needed], duration=duration, target_count=target_count)
