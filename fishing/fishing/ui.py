from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import FishingGame, FishState

_LANE_KEYS = ("f", "j")

_EXTRA_CSS = """
#lanes-container { width: 2fr; layout: horizontal; height: 100%; }
#lanes-container .primary-panel { width: 1fr; }
"""


class FishingApp(ThemedApp):
    CSS = COMMON_CSS + _EXTRA_CSS
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("space", "boost_0", "Lift"),
        Binding("up", "boost_0", show=False),
        Binding("w", "boost_0", show=False),
        Binding("f", "boost_0", show=False),
        Binding("j", "boost_1", show=False),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "restart", "Restart"),
    ]

    def __init__(self, *, theme: str = "modern", lanes: int = 1) -> None:
        super().__init__(theme=theme)
        self.num_lanes = 1 if lanes <= 1 else 2
        self.games = [FishingGame() for _ in range(self.num_lanes)]
        self.paused = False
        self._timer: Timer | None = None
        keys_hint = "  ".join(f"{_LANE_KEYS[i]}=lane{i + 1}" for i in range(self.num_lanes))
        self.help_text = f"{keys_hint}  p pause  r restart  t theme  ? help  q quit"
        if self.num_lanes == 1:
            self.help_text = "f/Space/Up lift  p pause  r restart  t theme  ? help  q quit"

    def compose(self) -> ComposeResult:
        yield Static("Fishing", id="app-title")
        with Horizontal(id="app-body"):
            with Horizontal(id="lanes-container"):
                for i in range(self.num_lanes):
                    with Vertical(classes="panel primary-panel"):
                        label = f" [{_LANE_KEYS[i]}]" if self.num_lanes > 1 else ""
                        yield Static(label, id=f"lane-label-{i}")
                        yield Static("", id=f"zone-view-{i}")
                        yield Static("", id=f"catch-bar-{i}")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="stats-view")
                yield Static("", id="fish-view")
                yield Button("Pause/Resume", id="pause")
                yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self._timer = self.set_interval(0.05, self.on_tick)
        self.refresh_view()

    def on_tick(self) -> None:
        if self.paused:
            return
        for game in self.games:
            game.step()
        self.refresh_view()

    def refresh_view(self) -> None:
        for i, game in enumerate(self.games):
            self.query_one(f"#zone-view-{i}", Static).update(self.render_zone(game))
            self.query_one(f"#catch-bar-{i}", Static).update(self.render_catch_bar(game))

        self.query_one("#stats-view", Static).update(self.render_stats())
        self.query_one("#fish-view", Static).update(self.render_fish_info())

        messages: list[str] = []
        for i, game in enumerate(self.games):
            prefix = f"[{_LANE_KEYS[i]}] " if self.num_lanes > 1 else ""
            if game.state == FishState.CAUGHT:
                bonus_text = f" x{game.last_bonus}" if game.last_bonus > 1 else ""
                messages.append(f"{prefix}CAUGHT! +{game.last_score}{bonus_text}")
            elif game.state == FishState.ESCAPED:
                messages.append(f"{prefix}{game.last_fish_name} got away...")
            elif game.state == FishState.WAITING:
                messages.append(f"{prefix}Next fish...")
        if self.paused:
            status = "Paused"
        elif messages:
            status = "   ".join(messages)
        else:
            status = "Fishing..."
        self.update_status(status)

    def render_stats(self) -> str:
        total_score = sum(game.score for game in self.games)
        total_caught = sum(game.fish_caught for game in self.games)
        state = "Paused" if self.paused else "Fishing"

        if self.num_lanes == 1:
            game = self.games[0]
            return (
                f"Score:  {game.score}\n"
                f"Caught: {game.fish_caught}\n"
                f"Streak: {game.streak}\n"
                f"State:  {state}"
            )

        lines: list[str] = []
        for i, game in enumerate(self.games):
            lines.extend(
                [
                    f"[{_LANE_KEYS[i]}] Score:  {game.score}",
                    f"    Caught: {game.fish_caught}",
                    f"    Streak: {game.streak}",
                ]
            )
        lines.extend(
            [
                f"Total Score:  {total_score}",
                f"Total Caught: {total_caught}",
                f"State:        {state}",
            ]
        )
        return "\n".join(lines)

    def render_zone(self, game: FishingGame) -> Text:
        txt = Text()

        if game.state == FishState.CAUGHT:
            points = f"+{game.last_score}"[:3].center(3)
            mid = game.zone_height // 2
            txt.append("+---+\n")
            for row in range(game.zone_height):
                txt.append("|")
                if row == mid - 1:
                    txt.append("***", style="bold bright_green")
                elif row == mid:
                    txt.append(points, style="bold bright_green")
                elif row == mid + 1:
                    txt.append("***", style="bold bright_green")
                else:
                    txt.append("   ", style="bright_green")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        if game.state == FishState.ESCAPED:
            mid = game.zone_height // 2
            txt.append("+---+\n")
            for row in range(game.zone_height):
                txt.append("|")
                if row == mid - 1:
                    txt.append("~~~", style="bold red")
                elif row == mid:
                    txt.append("RIP", style="bold red")
                elif row == mid + 1:
                    txt.append("~~~", style="bold red")
                else:
                    txt.append("   ", style="red")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        if game.state == FishState.WAITING:
            waves = ["~~~", "~ ~", " ~ ", "~ ~", "~~~"]
            txt.append("+---+\n")
            for row in range(game.zone_height):
                txt.append("|")
                txt.append(waves[row % len(waves)], style="dim cyan")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        ind_top = int(game.ind_pos)
        ind_bot = int(game.ind_pos + game.indicator_height - 1)
        fish_row = int(game.fish_pos)
        symbol = game.current_fish.symbol

        txt.append("+---+\n")
        for row in range(game.zone_height):
            in_indicator = ind_top <= row <= ind_bot
            is_fish = row == fish_row
            txt.append("|")
            if is_fish and in_indicator:
                txt.append(symbol, style="bold green")
            elif in_indicator:
                txt.append("===", style="cyan")
            elif is_fish:
                txt.append(symbol, style="yellow")
            else:
                txt.append("   ")
            txt.append("|\n")
        txt.append("+---+")
        return txt

    def render_catch_bar(self, game: FishingGame) -> Text:
        progress = game.catch_progress
        bar_width = 14 if self.num_lanes > 1 else 20
        filled = int(progress * bar_width)
        if progress > 0.8:
            color = "bright_green"
        elif progress < 0.2:
            color = "red"
        else:
            color = "green"
        txt = Text()
        txt.append("[")
        txt.append("#" * filled, style=color)
        txt.append("-" * (bar_width - filled), style="dim")
        txt.append("]")
        return txt

    def render_fish_info(self) -> Text:
        txt = Text()
        for i, game in enumerate(self.games):
            fish = game.current_fish
            if self.num_lanes > 1:
                txt.append(f"[{_LANE_KEYS[i]}]", style="bold")
                txt.append(f" {fish.symbol} {fish.name}  +{fish.score}\n", style="yellow")
            else:
                stars_n = min(4, round(fish.agility / 0.08))
                stars = "*" * stars_n + "." * (4 - stars_n)
                txt.append("Fish:\n", style="bold")
                txt.append(f"  {fish.symbol} {fish.name}\n", style="yellow")
                txt.append(f"  Diff: {stars}\n")
                txt.append(f"  Score: +{fish.score}")
        return txt

    def _boost(self, lane: int) -> None:
        if not self.paused and lane < self.num_lanes:
            self.games[lane].request_boost()

    def action_boost_0(self) -> None:
        self._boost(0)

    def action_boost_1(self) -> None:
        self._boost(1)

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self.refresh_view()

    def action_restart(self) -> None:
        for game in self.games:
            game.restart()
        self.paused = False
        self.refresh_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()


def run_fishing_game(*, theme: str = "modern", lanes: int = 1) -> int:
    return FishingApp(theme=theme, lanes=lanes).run() or 0
