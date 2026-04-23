from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from bluff_cards.client import BluffClientConnection
from bluff_cards.core import CARDS_PER_RANK, JOKER_COUNT, card_label, card_rank
from ._textual_base import COMMON_CSS, ThemedApp


class BluffRemoteApp(ThemedApp):
    CSS = (
        COMMON_CSS
        + """
        #scores-view {
            height: auto;
            padding: 0 0 1 0;
            border-bottom: solid #2a3a5c;
            margin-bottom: 1;
        }

        #action-grid {
            height: auto;
            layout: vertical;
        }

        .action-row {
            height: auto;
        }

        .action-row Button {
            margin-right: 1;
            margin-bottom: 1;
            min-width: 8;
        }
        """
    )
    BINDINGS = ThemedApp.BINDINGS + [
        Binding("up", "move_hand_up", "Prev", show=False),
        Binding("down", "move_hand_down", "Next", show=False),
        Binding("space", "toggle_card", "Select"),
        Binding("p", "play_claim", "Play"),
        Binding("c", "challenge_claim", "Challenge"),
        Binding("escape", "clear_selection", "Clear", show=False),
    ]
    help_text = "Up/Down move  Space select  p play cards  c challenge  Esc clear  q quit"

    def __init__(self, host: str, port: int, name: str, *, theme: str = "modern") -> None:
        super().__init__(theme=theme)
        self.host = host
        self.port = port
        self.player_name = name
        self.connection = BluffClientConnection(host, port, name)
        self.room: dict[str, Any] | None = None
        self.reveal: dict[str, Any] | None = None
        self.reveal_stage_text: str | None = None
        self.disconnected = False
        self.cursor_index = 0
        self.selected_indexes: set[int] = set()
        self.message = f"Connecting to {host}:{port}..."

    def compose(self) -> ComposeResult:
        yield Static("Bluff Cards", id="app-title")
        with Horizontal(id="app-body"):
            with Vertical(classes="panel primary-panel"):
                yield Static("", id="table-view", classes="board-text")
            with Vertical(classes="panel side-panel"):
                yield Static("", id="scores-view")
                yield Static("", id="hand-view")
                with Vertical(id="action-grid"):
                    with Horizontal(classes="action-row"):
                        yield Button("Play", id="play")
                        yield Button("Challenge", id="challenge")
                        yield Button("Clear", id="clear")
        yield Static("", id="help-panel")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        super().on_mount()
        try:
            self.connection.connect()
        except OSError as exc:
            self.disconnected = True
            self.message = f"Failed to connect to {self.host}:{self.port}: {exc}"
        else:
            self.message = f"Connected to {self.host}:{self.port}. Joining room..."
        self.set_interval(0.1, self.poll_messages)
        self.refresh_view()

    def on_unmount(self) -> None:
        self.connection.close()

    def poll_messages(self) -> None:
        for payload in self.connection.poll_messages():
            payload_type = payload.get("type")
            if payload_type == "welcome":
                self.message = f"Joined seat {payload['seat']} as {payload['name']}."
            elif payload_type == "room_state":
                self.room = dict(payload["room"])
                self.message = str(self.room.get("message", self.message))
                self.trim_selection()
            elif payload_type == "reveal_result":
                self.reveal = dict(payload["result"])
                self.start_reveal_animation(self.reveal)
            elif payload_type == "error":
                self.message = str(payload.get("message", "Action rejected."))
            elif payload_type == "disconnect":
                self.disconnected = True
                self.message = str(payload.get("message", "Connection closed."))
        self.refresh_view()

    def start_reveal_animation(self, reveal: dict[str, Any]) -> None:
        card_text = " ".join(card_label(card) for card in reveal.get("actual_cards", []))
        truthful = reveal.get("truthful")
        loser_seat = reveal["loser_seat"]
        challenger = reveal["challenger_seat"]
        challenged = reveal["challenged_seat"]
        loser_elim = reveal.get("loser_eliminated", False)

        if truthful:
            verdict = "[bold green]✓  TRUTH![/bold green]"
            damage = f"[red]Seat {loser_seat} (challenger) loses 1 ♥[/red]"
        else:
            verdict = "[bold red]✗  BLUFF![/bold red]"
            damage = f"[red]Seat {loser_seat} (claimer) loses 1 ♥[/red]"
        if loser_elim:
            damage += "  [bold red]— ELIMINATED![/bold red]"

        stages = [
            f"[bold yellow]⚡ CHALLENGE! ⚡[/bold yellow]\n[dim]Seat {challenger} calls out Seat {challenged}![/dim]",
            "[yellow]Flipping cards...[/yellow]",
            f"Revealed: [bold]{card_text}[/bold]",
            f"{verdict}\n{damage}",
        ]
        self.reveal_stage_text = stages[0]
        for index, stage in enumerate(stages[1:], start=1):
            self.set_timer(0.55 * index, lambda text=stage: self._set_reveal_stage(text))
        self.set_timer(0.55 * len(stages) + 1.5, lambda: self._clear_reveal_stage())

    def _set_reveal_stage(self, text: str) -> None:
        self.reveal_stage_text = text
        self.refresh_view()

    def _clear_reveal_stage(self) -> None:
        self.reveal_stage_text = None
        self.refresh_view()

    def current_hand(self) -> list[str]:
        if self.room is None:
            return []
        return list(self.room.get("your_hand", []))

    def trim_selection(self) -> None:
        hand = self.current_hand()
        if not hand:
            self.cursor_index = 0
            self.selected_indexes.clear()
            return
        self.cursor_index = max(0, min(len(hand) - 1, self.cursor_index))
        self.selected_indexes = {index for index in self.selected_indexes if index < len(hand)}

    # ── Render helpers ───────────────────────────────────────────────────────

    def render_table(self) -> str:
        if self.room is None:
            return "\n".join(
                [
                    "Waiting for room state...",
                    "",
                    "How to play:",
                    "1. This table only uses A, K, Q and Jokers.",
                    "2. Select 1-3 cards with Space and press p to claim they all match the table rank.",
                    "3. The next player may either play their own cards or press c to challenge.",
                    "4. After a challenge, the cards are revealed and the loser loses 1 life.",
                ]
            )

        room = self.room
        phase = room.get("phase", "")
        you_seat = room.get("you_seat")
        current_turn = room.get("current_turn")
        table_rank = room.get("table_rank", "?")
        max_lives: int = room.get("max_lives", 3)
        winner_seat = room.get("winner_seat")
        next_game_in = room.get("next_game_in")

        lines: list[str] = []

        # ── Phase header ──────────────────────────────────────────────────
        if phase == "in_round":
            total_matching = CARDS_PER_RANK + JOKER_COUNT  # always 8
            lines.append(
                f"[bold cyan]  TABLE RANK: {table_rank}  [/bold cyan]"
                f"[dim]  [{CARDS_PER_RANK}×{table_rank} + {JOKER_COUNT} Jokers = {total_matching} total][/dim]"
            )
        elif phase == "finished":
            if next_game_in is not None:
                lines.append(
                    f"[bold yellow]★ GAME OVER ★[/bold yellow]  "
                    f"[dim]New game in {next_game_in}s...[/dim]"
                )
            else:
                lines.append("[bold yellow]★ GAME OVER ★[/bold yellow]")
        elif phase == "waiting_for_players":
            lines.append("[dim]Waiting for players to join...[/dim]")
        elif phase == "paused_reconnect":
            lines.append("[yellow]⏸  PAUSED — waiting for reconnect[/yellow]")
        else:
            lines.append(f"[dim]{phase}[/dim]")
        lines.append("")

        # ── Player HP bars ────────────────────────────────────────────────
        for seat in room.get("seats", []):
            sn: int = seat["seat"]
            name: str = seat.get("name") or "(empty)"
            lives: int = seat.get("lives") if seat.get("lives") is not None else 0
            hand_count: int = seat.get("hand_count") or 0
            eliminated: bool = seat.get("eliminated", False)
            connected: bool = seat.get("connected", False)

            is_you = sn == you_seat
            is_current = sn == current_turn and phase == "in_round"

            hearts = "[red]♥[/red]" * lives + "[dim]♡[/dim]" * max(0, max_lives - lives)
            turn_arrow = "[bold green]▶[/bold green] " if is_current else "  "
            you_tag = " [bold](YOU)[/bold]" if is_you else ""

            if eliminated:
                line = (
                    f"{turn_arrow}[strike dim]S{sn} {name}[/strike dim]"
                    f"{you_tag}  {hearts}  [dim]ELIMINATED[/dim]"
                )
            elif not connected:
                line = (
                    f"{turn_arrow}[dim]S{sn} {name}[/dim]"
                    f"{you_tag}  {hearts}  [dim]({hand_count}c)  [red]OFFLINE[/red][/dim]"
                )
            else:
                name_part = f"[bold]{name}[/bold]" if is_you else name
                line = (
                    f"{turn_arrow}S{sn} {name_part}{you_tag}"
                    f"  {hearts}  [dim]({hand_count}c)[/dim]"
                )
            lines.append(line)

        # ── Card pool reasoning hint ──────────────────────────────────────
        if phase == "in_round" and table_rank:
            total_matching = CARDS_PER_RANK + JOKER_COUNT
            your_hand = room.get("your_hand", [])
            my_matching = sum(1 for c in your_hand if card_rank(c) in {table_rank, "JOKER"})
            discard_matching: int = room.get("discard_matching", 0)
            in_play = total_matching - my_matching - discard_matching
            lines.append(
                f"[dim]Pool: {total_matching} matching  "
                f"You hold: {my_matching}  "
                f"Discard: {discard_matching}  "
                f"→ others can have at most [/dim][bold]{in_play}[/bold]"
            )
        lines.append("")

        # ── Reveal animation ──────────────────────────────────────────────
        if self.reveal_stage_text:
            lines.append(self.reveal_stage_text)
            lines.append("")

        # ── Last claim ────────────────────────────────────────────────────
        claim = room.get("last_claim")
        if isinstance(claim, dict):
            clm_seat = claim["seat"]
            cnt = claim["claimed_count"]
            rank = claim["table_rank"]
            clm_p = next((s for s in room.get("seats", []) if s["seat"] == clm_seat), None)
            cname = clm_p["name"] if clm_p else f"Seat {clm_seat}"
            if clm_seat == you_seat:
                lines.append(f"[yellow]Your claim:[/yellow] {cnt} × {rank}")
            else:
                lines.append(f"[yellow]Last claim:[/yellow] {cname} says {cnt} × {rank}")

        # ── Turn / game-over notice ───────────────────────────────────────
        if phase == "in_round" and current_turn is not None:
            if current_turn == you_seat:
                lines.append("[bold green]→ Your turn![/bold green]")
            else:
                turn_p = next((s for s in room.get("seats", []) if s["seat"] == current_turn), None)
                tname = turn_p["name"] if turn_p else f"Seat {current_turn}"
                lines.append(f"[dim]Waiting for {tname}...[/dim]")
        elif phase == "finished" and winner_seat is not None:
            winner_p = next((s for s in room.get("seats", []) if s["seat"] == winner_seat), None)
            wname = winner_p["name"] if winner_p else f"Seat {winner_seat}"
            if winner_seat == you_seat:
                lines.append("[bold green]★ You win this game! ★[/bold green]")
            else:
                lines.append(f"[bold yellow]★ {wname} wins! ★[/bold yellow]")

        lines.append("")

        # ── Action log ────────────────────────────────────────────────────
        action_log = room.get("action_log", [])
        if action_log:
            lines.append("[dim]━━ Recent actions ━━[/dim]")
            for entry in action_log[-6:]:
                lines.append(f"[dim]  {entry}[/dim]")

        return "\n".join(lines)

    def render_scores(self) -> str:
        if self.room is None:
            return ""
        game_scores: dict = self.room.get("game_scores", {})
        seats = self.room.get("seats", [])
        you_seat = self.room.get("you_seat")

        rows: list[tuple[int, int, str]] = []
        for seat in seats:
            sn: int = seat["seat"]
            name: str = seat.get("name") or f"Seat {sn}"
            wins = game_scores.get(sn, game_scores.get(str(sn), 0))
            rows.append((wins, sn, name))
        rows.sort(key=lambda r: (-r[0], r[1]))

        lines = ["[dim]━━ Win board ━━[/dim]"]
        for wins, sn, name in rows:
            stars = "★" * wins if wins > 0 else "—"
            is_you = sn == you_seat
            if is_you:
                lines.append(f"[bold]{name}: {stars} ({wins})[/bold]")
            else:
                lines.append(f"{name}: {stars} ({wins})")
        return "\n".join(lines)

    def render_hand(self) -> str:
        hand = self.current_hand()
        if not hand:
            return "Your hand:\n  (empty)"
        lines = [f"Your hand ({len(hand)} cards):"]
        for index, card in enumerate(hand):
            pointer = "[bold green]►[/bold green]" if index == self.cursor_index else " "
            chosen = "[yellow]✓[/yellow]" if index in self.selected_indexes else " "
            lines.append(f" {pointer}{chosen} {card_label(card)}")
        return "\n".join(lines)

    def render_instruction(self) -> str:
        if self.room is None:
            return "Next: wait for the server to send the room state."
        if self.disconnected:
            return "Next: disconnected. Restart the client with the same name to rejoin."

        phase = str(self.room.get("phase"))
        you_seat = self.room.get("you_seat")
        current_turn = self.room.get("current_turn")
        last_claim = self.room.get("last_claim")
        next_game_in = self.room.get("next_game_in")

        if phase == "waiting_for_players":
            return "Next: wait for all seats to be filled."
        if phase == "paused_reconnect":
            return "Next: a player disconnected. Wait for them to rejoin with the same name."
        if phase == "in_round":
            if current_turn == you_seat:
                if isinstance(last_claim, dict) and last_claim.get("seat") != you_seat:
                    if self.current_hand():
                        return "Next: press c to challenge, or select 1-3 cards and press p to bluff."
                    return "Next: you have no cards left. Press c to challenge."
                return "Next: your turn. Select 1-3 cards and press p."
            return f"Next: wait for seat {current_turn} to act."
        if phase == "finished":
            if next_game_in is not None:
                return f"Next: new game starts in {next_game_in}s. Hang tight!"
            return "Next: game over. Press q to quit."
        if phase == "closed":
            return "Next: room closed. Press q to quit."
        return "Next: follow the status message below."

    def refresh_view(self) -> None:
        self.query_one("#table-view", Static).update(self.render_table())
        self.query_one("#hand-view", Static).update(self.render_hand())
        self.query_one("#scores-view", Static).update(self.render_scores())
        self.update_status(self.message)

    # ── Input actions ────────────────────────────────────────────────────────

    def move_cursor(self, delta: int) -> None:
        hand = self.current_hand()
        if not hand:
            return
        self.cursor_index = max(0, min(len(hand) - 1, self.cursor_index + delta))
        self.refresh_view()

    def action_move_hand_up(self) -> None:
        self.move_cursor(-1)

    def action_move_hand_down(self) -> None:
        self.move_cursor(1)

    def action_toggle_card(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        hand = self.current_hand()
        if not hand:
            self.message = "No cards available."
            self.refresh_view()
            return
        if self.cursor_index in self.selected_indexes:
            self.selected_indexes.remove(self.cursor_index)
        else:
            self.selected_indexes.add(self.cursor_index)
        self.message = f"Selected {len(self.selected_indexes)} card(s)."
        self.refresh_view()

    def action_clear_selection(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        self.selected_indexes.clear()
        self.message = "Selection cleared."
        self.refresh_view()

    def action_play_claim(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        hand = self.current_hand()
        if not self.selected_indexes:
            self.message = "Select at least one card first."
            self.refresh_view()
            return
        cards = [hand[index] for index in sorted(self.selected_indexes)]
        try:
            self.connection.send_play_claim(cards)
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending play."
        else:
            self.message = f"Played {len(cards)} face-down card(s)."
            self.selected_indexes.clear()
        self.refresh_view()

    def action_challenge_claim(self) -> None:
        if self.disconnected:
            self.message = "Disconnected. Press q to quit."
            self.refresh_view()
            return
        try:
            self.connection.send_challenge()
        except OSError:
            self.disconnected = True
            self.message = "Connection closed while sending challenge."
        else:
            self.message = "Challenge sent."
        self.refresh_view()

    def action_quit_app(self) -> None:
        try:
            self.connection.send_leave()
        except OSError:
            pass
        self.exit(0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "play":
            self.action_play_claim()
        elif button_id == "challenge":
            self.action_challenge_claim()
        elif button_id == "clear":
            self.action_clear_selection()


def run_bluff_remote_client(
    host: str,
    port: int,
    name: str,
    theme: str = "modern",
) -> int:
    return BluffRemoteApp(host, port, name, theme=theme).run() or 0
