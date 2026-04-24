from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from ._textual_base import COMMON_CSS, ThemedApp
from .core import MAP_PRESETS, SPEED_PRESETS, SnakeGame

MAP_ORDER = ["classic_walls", "open_wrap", "center_blocks", "cross_portal", "islands", "gate_maze"]
SPEED_ORDER = ["slow", "normal", "fast", "insane"]


class SnakeApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #phase-view {
            height: auto;
            padding-bottom: 1;
        }

        #summary-view, #next-view {
            height: auto;
        }

        #control-row {
            height: auto;
            margin-top: 1;
        }

        #control-row Button {
            margin-right: 1;
            min-width: 11;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "up", show=False),
        Binding("down", "down", show=False),
        Binding("left", "left", show=False),
        Binding("right", "right", show=False),
        Binding("w", "up", show=False),
        Binding("s", "down", show=False),
        Binding("a", "left", show=False),
        Binding("d", "right", show=False),
        Binding("space", "toggle_pause", "Pause"),
        Binding("m", "cycle_map", "Map"),
        Binding("v", "cycle_speed", "Speed"),
        Binding("enter", "start_round", "Start"),
        Binding("r", "restart", "Restart"),
    ]
    help_text = "Arrows/WASD direction  Space pause  m map  v speed  Enter start  r restart  t theme  ? help  q quit"

    def __init__(
        self,
        rows: int = 30,
        cols: int = 30,
        *,
        theme: str = "modern",
        map_id: str = "classic_walls",
        speed_id: str = "normal",
    ) -> None:
        super().__init__(theme=theme)
        if map_id not in MAP_PRESETS:
            raise ValueError(f"Unknown snake map: {map_id}")
        if speed_id not in SPEED_PRESETS:
            raise ValueError(f"Unknown snake speed: {speed_id}")
        self.rows = rows
        self.cols = cols
        self.selected_map_id = map_id
        self.selected_speed_id = speed_id
        self.game = SnakeGame(rows=rows, cols=cols, map_id=map_id, speed_id=speed_id)
        self.configuring = True
        self.paused = False
        self.message = "Choose a map and speed, then start the round."
        self.session_best = 0
        self.rounds_started = 0
        self._tick_timer = None

    def compose(self) -> ComposeResult:
        yield Static("Snake", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="phase-view")
                yield Static("", id="board-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="summary-view")
                yield Static("", id="next-view")
                with Horizontal(id="control-row"):
                    yield Button("Map", id="map")
                    yield Button("Speed", id="speed")
                    yield Button("Start", id="start")
                    yield Button("Pause", id="pause")
                    yield Button("Restart", id="restart")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        self.refresh_view()

    def on_tick(self) -> None:
        if self.configuring or self.paused or self.game.game_over:
            return
        previous_score = self.game.score
        self.game.step()
        if self.game.game_over:
            self.session_best = max(self.session_best, self.game.score)
            self.message = "Snake crashed. Choose settings for the next round."
            self.configuring = True
            self._stop_tick_timer()
        elif self.game.score > previous_score:
            self.session_best = max(self.session_best, self.game.score)
            self.message = f"Fruit eaten. Score {self.game.score}."
        self.refresh_view()

    def refresh_view(self) -> None:
        self.query_one("#phase-view", Static).update(self.render_phase())
        self.query_one("#board-view", Static).update(self.render_board())
        self.query_one("#summary-view", Static).update(self.render_summary())
        self.query_one("#next-view", Static).update(self.render_next_action())
        self._refresh_buttons()
        self.update_status(self.message)

    def render_phase(self) -> str:
        if self.configuring:
            return "[bold cyan]▶ SETUP[/bold cyan]"
        if self.game.game_over:
            return "[bold red]★ CRASH ★[/bold red]"
        if self.paused:
            return "[bold yellow]⏸ PAUSED[/bold yellow]"
        return "[bold cyan]▶ HUNTING[/bold cyan]"

    def render_summary(self) -> str:
        selected_map = MAP_PRESETS[self.selected_map_id]
        selected_speed = SPEED_PRESETS[self.selected_speed_id]
        if self.configuring:
            last_score = self.game.score if self.game.game_over else 0
            return "\n".join(
                [
                    "[bold]Next Round[/bold]",
                    f"Map:      {selected_map.name}",
                    f"Speed:    {selected_speed.name}",
                    f"Fruit:    +{selected_speed.fruit_score}",
                    f"Tick:     {selected_speed.tick_seconds:.2f}s",
                    f"Last:     {last_score}",
                    f"Best:     {max(self.session_best, self.game.score)}",
                    f"Rounds:   {self.rounds_started}",
                ]
            )
        state = "Paused" if self.paused else ("Over" if self.game.game_over else "Running")
        progress = self._bar(self.game.score, goal=max(6, self.session_best or 3), width=12)
        return "\n".join(
            [
                "[bold]Session[/bold]",
                f"Map:      {self.game.map.name}",
                f"Speed:    {self.game.speed.name}",
                f"Fruit:    +{self.game.speed.fruit_score}",
                f"Score:    {self.game.score}",
                f"Best:     {max(self.session_best, self.game.score)}",
                f"Length:   {len(self.game.snake)}",
                f"Rounds:   {self.rounds_started}",
                f"Growth:   {progress}",
                f"State:    {state}",
            ]
        )

    def render_next_action(self) -> str:
        if self.configuring:
            return "[bold green]Next:[/bold green] Press Enter or Start to launch this setup."
        if self.game.game_over:
            return "[bold yellow]Next:[/bold yellow] Waiting to restart."
        if self.paused:
            return "[bold yellow]Next:[/bold yellow] Press Space to resume the run."
        return "[bold green]Next:[/bold green] Guide the head to fruit and avoid walls."

    def render_board(self) -> Text:
        if self.configuring:
            return self.render_setup()

        return self._render_game_board(self.game)

    def render_setup(self) -> Text:
        selected_map = MAP_PRESETS[self.selected_map_id]
        selected_speed = SPEED_PRESETS[self.selected_speed_id]
        preview = SnakeGame(rows=self.rows, cols=self.cols, map_id=self.selected_map_id, speed_id=self.selected_speed_id)
        txt = Text()
        txt.append("Choose your next run\n\n", style="bold")
        txt.append(f"Map:   {selected_map.name}\n", style="bold cyan")
        txt.append(f"       {selected_map.description}\n\n", style="dim")
        txt.append(f"Speed: {selected_speed.name}  ", style="bold yellow")
        txt.append(f"{selected_speed.tick_seconds:.2f}s per tick, +{selected_speed.fruit_score} per fruit\n\n", style="yellow")
        txt.append("Preview\n", style="bold")
        txt.append_text(self._render_game_board(preview))
        txt.append("\n\nm cycles map, v cycles speed, Enter starts.", style="dim")
        return txt

    def _render_game_board(self, game: SnakeGame) -> Text:
        snake_body = set(game.snake[1:-1])
        txt = Text()
        wrap = game.map.wrap_rows or game.map.wrap_cols
        border_style = "cyan" if wrap else "#5b7cbe"
        h_fill = "≈" * game.cols if wrap else "═" * game.cols
        txt.append("╔" + h_fill + "╗\n", style=border_style)
        for r in range(0, game.rows, 2):
            txt.append("║", style=border_style)
            for c in range(game.cols):
                top = self._cell_kind(game, (r, c), snake_body)
                bottom = self._cell_kind(game, (r + 1, c), snake_body) if r + 1 < game.rows else None
                self._append_half_cell(txt, top, bottom)
            txt.append("║\n", style=border_style)
        txt.append("╚" + h_fill + "╝", style=border_style)
        return txt

    def _cell_kind(self, game: SnakeGame, pos: tuple[int, int], snake_body: set) -> str | None:
        if pos == game.snake[-1]:
            return "head-crashed" if game.game_over else "head"
        if pos == game.snake[0]:
            return "tail"
        if pos in snake_body:
            return "body"
        if pos == game.food:
            return "food"
        if pos in game.obstacles:
            return "obstacle"
        return None

    @staticmethod
    def _append_half_cell(txt: Text, top: str | None, bottom: str | None) -> None:
        ts = SnakeApp._kind_style(top)
        bs = SnakeApp._kind_style(bottom)
        if ts is None and bs is None:
            txt.append(" ")
            return
        if ts == bs:
            txt.append("█", style=ts)
            return
        if ts and bs:
            txt.append("▀", style=f"{ts} on {bs}")
        elif ts:
            txt.append("▀", style=ts)
        else:
            txt.append("▄", style=bs)

    @staticmethod
    def _kind_style(kind: str | None) -> str | None:
        if kind == "head":
            return "bright_white"
        if kind == "head-crashed":
            return "bright_red"
        if kind == "body":
            return "green"
        if kind == "tail":
            return "dark_green"
        if kind == "food":
            return "bright_yellow"
        if kind == "obstacle":
            return "red"
        return None

    def action_up(self) -> None:
        if self.configuring:
            return
        self.game.change_direction("up")
        self.update_status("Heading up.")

    def action_down(self) -> None:
        if self.configuring:
            return
        self.game.change_direction("down")
        self.update_status("Heading down.")

    def action_left(self) -> None:
        if self.configuring:
            return
        self.game.change_direction("left")
        self.update_status("Heading left.")

    def action_right(self) -> None:
        if self.configuring:
            return
        self.game.change_direction("right")
        self.update_status("Heading right.")

    def action_toggle_pause(self) -> None:
        if self.configuring or self.game.game_over:
            return
        self.paused = not self.paused
        self.message = "Paused." if self.paused else "Run resumed."
        self.refresh_view()

    def action_cycle_map(self) -> None:
        index = MAP_ORDER.index(self.selected_map_id)
        self.selected_map_id = MAP_ORDER[(index + 1) % len(MAP_ORDER)]
        self.message = f"Map selected: {MAP_PRESETS[self.selected_map_id].name}."
        self.refresh_view()

    def action_cycle_speed(self) -> None:
        index = SPEED_ORDER.index(self.selected_speed_id)
        self.selected_speed_id = SPEED_ORDER[(index + 1) % len(SPEED_ORDER)]
        speed = SPEED_PRESETS[self.selected_speed_id]
        self.message = f"Speed selected: {speed.name}, +{speed.fruit_score} per fruit."
        self.refresh_view()

    def action_start_round(self) -> None:
        if not self.configuring:
            return
        self._start_round()

    def action_restart(self) -> None:
        self._return_to_setup(manual=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "map":
            self.action_cycle_map()
        elif event.button.id == "speed":
            self.action_cycle_speed()
        elif event.button.id == "start":
            self.action_start_round()
        elif event.button.id == "pause":
            self.action_toggle_pause()
        elif event.button.id == "restart":
            self.action_restart()

    def _start_round(self) -> None:
        self.game = SnakeGame(rows=self.rows, cols=self.cols, map_id=self.selected_map_id, speed_id=self.selected_speed_id)
        self.configuring = False
        self.paused = False
        self.rounds_started += 1
        self.message = f"Round started: {self.game.map.name}, {self.game.speed.name}."
        self._start_tick_timer()
        self.refresh_view()

    def _return_to_setup(self, *, manual: bool) -> None:
        self.session_best = max(self.session_best, self.game.score)
        self.configuring = True
        self.paused = False
        self._stop_tick_timer()
        self.message = "Choose settings for a new round." if manual else "Choose settings for the next round."
        self.refresh_view()

    def _start_tick_timer(self) -> None:
        self._stop_tick_timer()
        self._tick_timer = self.set_interval(self.game.speed.tick_seconds, self.on_tick)

    def _stop_tick_timer(self) -> None:
        if self._tick_timer is None:
            return
        try:
            self._tick_timer.stop()
        except Exception:
            pass
        self._tick_timer = None

    def _refresh_buttons(self) -> None:
        try:
            self.query_one("#map", Button).label = f"Map: {MAP_PRESETS[self.selected_map_id].name}"
            speed = SPEED_PRESETS[self.selected_speed_id]
            self.query_one("#speed", Button).label = f"Speed: {speed.name}"
            self.query_one("#start", Button).display = self.configuring
            self.query_one("#map", Button).display = self.configuring
            self.query_one("#speed", Button).display = self.configuring
            self.query_one("#pause", Button).display = not self.configuring
            self.query_one("#restart", Button).label = "New Setup" if not self.configuring else "Reset"
        except Exception:
            return

    @staticmethod
    def _bar(value: int, *, goal: int, width: int) -> str:
        goal = max(goal, 1)
        filled = min(width, max(0, round((value / goal) * width)))
        return f"{'█' * filled}{'░' * (width - filled)}"


def run_snake_game(
    *,
    rows: int = 30,
    cols: int = 30,
    theme: str = "modern",
    map_id: str = "classic_walls",
    speed_id: str = "normal",
) -> int:
    return SnakeApp(rows=rows, cols=cols, theme=theme, map_id=map_id, speed_id=speed_id).run() or 0
