from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static
from textual.timer import Timer

from ._textual_base import COMMON_CSS, ThemedApp
from .core import FishingGame, FishState

_LANE_KEYS = ("h", "j", "k", "l")

_EXTRA_CSS = """
#lanes-container { width: 2fr; layout: horizontal; height: 100%; }
#lanes-container .primary-panel { width: 1fr; }
"""


class FishingApp(ThemedApp):
    CSS = COMMON_CSS + _EXTRA_CSS
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("space", "boost_0", "Lift"),
        Binding("up",    "boost_0", show=False),
        Binding("w",     "boost_0", show=False),
        Binding("h",     "boost_0", show=False),
        Binding("j",     "boost_1", show=False),
        Binding("k",     "boost_2", show=False),
        Binding("l",     "boost_3", show=False),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "restart", "Restart"),
    ]

    def __init__(self, *, theme: str = "modern", lanes: int = 1) -> None:
        super().__init__(theme=theme)
        self.num_lanes = max(1, min(4, lanes))
        self.games = [FishingGame() for _ in range(self.num_lanes)]
        self.paused = False
        self._timer: Timer | None = None
        keys_hint = "  ".join(
            f"{_LANE_KEYS[i]}=lane{i+1}" for i in range(self.num_lanes)
        )
        self.help_text = f"{keys_hint}  p pause  r restart  t theme  ? help  q quit"
        if self.num_lanes == 1:
            self.help_text = "h/Space/Up lift  p pause  r restart  t theme  ? help  q quit"

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

        total_score = sum(g.score for g in self.games)
        total_caught = sum(g.fish_caught for g in self.games)
        best_streak = max(g.streak for g in self.games)
        self.query_one("#stats-view", Static).update(
            f"Score:  {total_score}\n"
            f"Caught: {total_caught}\n"
            f"Streak: {best_streak}\n"
            f"State:  {'Paused' if self.paused else 'Fishing'}"
        )
        self.query_one("#fish-view", Static).update(self.render_fish_info())

        # Build status bar message
        msgs: list[str] = []
        for i, game in enumerate(self.games):
            prefix = f"[{_LANE_KEYS[i]}] " if self.num_lanes > 1 else ""
            if game.state == FishState.CAUGHT:
                bonus_txt = f" ×{game.last_bonus}" if game.last_bonus > 1 else ""
                msgs.append(f"{prefix}CAUGHT! +{game.last_score}{bonus_txt}")
            elif game.state == FishState.ESCAPED:
                msgs.append(f"{prefix}{game.last_fish_name} got away…")
            elif game.state == FishState.WAITING:
                msgs.append(f"{prefix}Next fish…")
        if self.paused:
            status = "Paused"
        elif msgs:
            status = "   ".join(msgs)
        else:
            status = "Fishing…"
        self.update_status(status)

    def render_zone(self, game: FishingGame) -> Text:
        txt = Text()

        if game.state == FishState.CAUGHT:
            bonus_txt = f"×{game.last_bonus}" if game.last_bonus > 1 else "  "
            pts = f"+{game.last_score}"[:3].center(3)
            mid = game.zone_height // 2
            txt.append("+---+\n")
            for r in range(game.zone_height):
                txt.append("|")
                if r == mid - 1:
                    txt.append("✦✦✦", style="bold bright_green")
                elif r == mid:
                    txt.append(pts, style="bold bright_green")
                elif r == mid + 1:
                    txt.append("✦✦✦", style="bold bright_green")
                else:
                    txt.append("   ", style="bright_green")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        if game.state == FishState.ESCAPED:
            mid = game.zone_height // 2
            txt.append("+---+\n")
            for r in range(game.zone_height):
                txt.append("|")
                if r == mid - 1:
                    txt.append("~~~", style="bold red")
                elif r == mid:
                    txt.append("RIP", style="bold red")
                elif r == mid + 1:
                    txt.append("~~~", style="bold red")
                else:
                    txt.append("   ", style="red")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        if game.state == FishState.WAITING:
            waves = ["~~~", "~ ~", " ~ ", "~ ~", "~~~"]
            txt.append("+---+\n")
            for r in range(game.zone_height):
                txt.append("|")
                txt.append(waves[r % len(waves)], style="dim cyan")
                txt.append("|\n")
            txt.append("+---+")
            return txt

        # Normal FISHING state
        ind_top = int(game.ind_pos)
        ind_bot = int(game.ind_pos + game.indicator_height - 1)
        fish_row = int(game.fish_pos)
        symbol = game.current_fish.symbol

        txt.append("+---+\n")
        for r in range(game.zone_height):
            in_ind = ind_top <= r <= ind_bot
            is_fish = r == fish_row
            txt.append("|")
            if is_fish and in_ind:
                txt.append(symbol, style="bold green")
            elif in_ind:
                txt.append("===", style="cyan")
            elif is_fish:
                txt.append(symbol, style="yellow")
            else:
                txt.append("   ")
            txt.append("|\n")
        txt.append("+---+")
        return txt

    def render_catch_bar(self, game: FishingGame) -> Text:
        p = game.catch_progress
        bar_width = 14 if self.num_lanes > 1 else 20
        filled = int(p * bar_width)
        if p > 0.8:
            color = "bright_green"
        elif p < 0.2:
            color = "red"
        else:
            color = "green"
        txt = Text()
        txt.append("[")
        txt.append("█" * filled, style=color)
        txt.append("░" * (bar_width - filled), style="dim")
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
                stars = "★" * stars_n + "☆" * (4 - stars_n)
                txt.append("Fish:\n", style="bold")
                txt.append(f"  {fish.symbol} {fish.name}\n", style="yellow")
                txt.append(f"  Diff: {stars}\n")
                txt.append(f"  Score: +{fish.score}")
        return txt

    def _boost(self, lane: int) -> None:
        if not self.paused and lane < self.num_lanes:
            self.games[lane].request_boost()

    def action_boost_0(self) -> None: self._boost(0)
    def action_boost_1(self) -> None: self._boost(1)
    def action_boost_2(self) -> None: self._boost(2)
    def action_boost_3(self) -> None: self._boost(3)

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
