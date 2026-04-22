from __future__ import annotations

from typing import Any

from bluff_cards.client import BluffClientConnection


def _load_curses():
    try:
        import curses
    except ImportError as exc:
        raise RuntimeError("curses is required for the terminal UI and is typically available on Linux.") from exc
    return curses


class BluffRemoteApp:
    def __init__(self, host: str, port: int, name: str, session_token: str | None = None) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.session_token = session_token

    def run(self) -> int:
        connection = BluffClientConnection(self.host, self.port, self.name, self.session_token)
        connection.connect()
        curses = _load_curses()
        try:
            return curses.wrapper(self._main, connection)
        finally:
            connection.close()

    def _main(self, stdscr, connection: BluffClientConnection) -> int:
        curses = _load_curses()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(100)

        room: dict[str, Any] | None = None
        session_token = self.session_token
        message = f"Connected to {self.host}:{self.port}. Joining room..."
        reveal: dict[str, Any] | None = None
        disconnected = False
        prompt = ""

        while True:
            for payload in connection.poll_messages():
                payload_type = payload.get("type")
                if payload_type == "welcome":
                    session_token = str(payload["session_token"])
                    message = f"Joined seat {payload['seat']} as {payload['name']}."
                elif payload_type == "room_state":
                    room = dict(payload["room"])
                    message = str(room.get("message", message))
                elif payload_type == "reveal_result":
                    reveal = dict(payload["result"])
                    message = self._reveal_message(reveal)
                elif payload_type == "error":
                    message = str(payload.get("message", "Action rejected."))
                elif payload_type == "disconnect":
                    disconnected = True
                    message = str(payload.get("message", "Connection closed."))

            self._render(stdscr, room, message, reveal, session_token, prompt, disconnected)
            key = stdscr.getch()
            if key == -1:
                continue
            if disconnected:
                return 0
            if key in (10, 13):
                submitted = prompt.strip()
                prompt = ""
                if not submitted:
                    continue
                if submitted.lower() in {"q", "quit", "exit"}:
                    try:
                        connection.send_leave()
                    except OSError:
                        pass
                    return 0
                try:
                    self._dispatch_command(connection, room, submitted)
                except ValueError as exc:
                    message = str(exc)
                except OSError:
                    disconnected = True
                    message = "Connection closed while sending the command."
                continue
            if key in (curses.KEY_BACKSPACE, 127, 8):
                prompt = prompt[:-1]
                continue
            if 32 <= key <= 126:
                prompt += chr(key)

    def _render(
        self,
        stdscr,
        room: dict[str, Any] | None,
        message: str,
        reveal: dict[str, Any] | None,
        session_token: str | None,
        prompt: str,
        disconnected: bool,
    ) -> None:
        curses = _load_curses()
        stdscr.erase()
        lines: list[str] = []
        if room is None:
            lines.append("Waiting for room state...")
        else:
            lines.append(
                f"Phase: {room['phase']} | Players: {room['players']} | You: seat {room['you_seat']} {room['your_name']}"
            )
            lines.append("Seats: " + " | ".join(self._seat_line(seat) for seat in room["seats"]))
            target = room.get("target_rank")
            if target is not None:
                lines.append(f"Target: {target} | Turn: seat {room.get('current_turn')} | Discarded: {room.get('discard_count')}")
            claim = room.get("last_claim")
            if isinstance(claim, dict):
                lines.append(
                    f"Last claim: seat {claim['seat']} says {claim['claimed_count']} x {claim['target_rank']}"
                )
            hand = room.get("your_hand", [])
            if hand:
                indexed = "  ".join(f"{index + 1}:{card}" for index, card in enumerate(hand))
                lines.append("Your hand:")
                lines.append(indexed)
            if room.get("winner_seat") is not None:
                lines.append(f"Winner: seat {room['winner_seat']}")
        if reveal is not None:
            cards = " ".join(reveal["actual_cards"])
            lines.append(f"Reveal: seat {reveal['challenged_seat']} actually played {cards}")

        lines.append("")
        lines.append("Commands:")
        lines.append("  play #1 #2 claim 2")
        lines.append("  play AS BJ claim 2")
        lines.append("  challenge")
        lines.append("  accept")
        lines.append("  quit")
        lines.append("")
        lines.append(f"Status: {message}")
        if session_token is not None:
            lines.append(f"Reconnect token: {session_token}")
        if disconnected:
            lines.append("Session ended. Press any key to exit.")
        lines.append(f"> {prompt}")

        height, width = stdscr.getmaxyx()
        for row, line in enumerate(lines[: max(0, height - 1)]):
            try:
                stdscr.addstr(row, 0, line[: max(0, width - 1)])
            except curses.error:
                pass
        stdscr.refresh()

    def _seat_line(self, seat: dict[str, Any]) -> str:
        name = seat.get("name") or "(empty)"
        status = "online" if seat.get("connected") else "offline"
        hand_count = "-" if seat.get("hand_count") is None else str(seat.get("hand_count"))
        lives = "-" if seat.get("lives") is None else str(seat.get("lives"))
        eliminated = "out" if seat.get("eliminated") else "in"
        return f"S{seat['seat']} {name} [{status},hand={hand_count},hp={lives},{eliminated}]"

    def _dispatch_command(self, connection: BluffClientConnection, room: dict[str, Any] | None, command: str) -> None:
        parts = command.split()
        if not parts:
            return
        action = parts[0].lower()
        if action == "challenge":
            connection.send_challenge()
            return
        if action == "accept":
            connection.send_accept()
            return
        if action == "play":
            if room is None:
                raise ValueError("Room state is not available yet.")
            if "claim" not in [token.lower() for token in parts]:
                raise ValueError("Usage: play <card/card-index...> claim <count>")
            claim_index = next(index for index, token in enumerate(parts) if token.lower() == "claim")
            if claim_index == 1 or claim_index == len(parts) - 1:
                raise ValueError("Usage: play <card/card-index...> claim <count>")
            actual_cards = self._resolve_cards(room.get("your_hand", []), parts[1:claim_index])
            claimed_count = int(parts[claim_index + 1])
            connection.send_play_claim(actual_cards, claimed_count)
            return
        raise ValueError("Unknown command.")

    def _resolve_cards(self, hand: list[str], tokens: list[str]) -> list[str]:
        cards: list[str] = []
        used_indexes: set[int] = set()
        for token in tokens:
            if token.startswith("#"):
                index = int(token[1:]) - 1
                if index < 0 or index >= len(hand):
                    raise ValueError(f"Hand index out of range: {token}")
                if index in used_indexes:
                    raise ValueError(f"Hand index used twice: {token}")
                used_indexes.add(index)
                cards.append(hand[index])
            else:
                cards.append(token)
        return cards

    def _reveal_message(self, reveal: dict[str, Any]) -> str:
        truth = "truthful" if reveal.get("truthful") else "bluffing"
        return f"Reveal: seat {reveal['challenged_seat']} was {truth}. Seat {reveal['loser_seat']} lost 1 life."


def run_bluff_remote_client(host: str, port: int, name: str, session_token: str | None = None) -> int:
    return BluffRemoteApp(host, port, name, session_token).run()
