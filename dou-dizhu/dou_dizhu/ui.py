from __future__ import annotations

from typing import Any

from dou_dizhu.client import DdzClientConnection


def _load_curses():
    try:
        import curses
    except ImportError as exc:
        raise RuntimeError("curses is required for the terminal UI and is typically available on Linux.") from exc
    return curses


class DdzRemoteApp:
    def __init__(self, host: str, port: int, name: str, session_token: str | None = None) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.session_token = session_token

    def run(self) -> int:
        connection = DdzClientConnection(self.host, self.port, self.name, self.session_token)
        connection.connect()
        curses = _load_curses()
        try:
            return curses.wrapper(self._main, connection)
        finally:
            connection.close()

    def _main(self, stdscr, connection: DdzClientConnection) -> int:
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
                elif payload_type == "error":
                    message = str(payload.get("message", "Action rejected."))
                elif payload_type == "disconnect":
                    disconnected = True
                    message = str(payload.get("message", "Connection closed."))

            self._render(stdscr, room, message, session_token, prompt, disconnected)
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
        session_token: str | None,
        prompt: str,
        disconnected: bool,
    ) -> None:
        stdscr.erase()
        lines: list[str] = []
        if room is None:
            lines.append("Waiting for room state...")
        else:
            lines.append(f"Phase: {room['phase']} | You: seat {room['you_seat']} {room['your_name']}")
            lines.append("Seats: " + " | ".join(self._seat_line(seat) for seat in room["seats"]))
            if room.get("phase") == "bidding":
                lines.append(
                    f"Bidding: current seat {room.get('current_turn')} | highest bid {room.get('highest_bid')} by {room.get('highest_bidder')}"
                )
            if room.get("landlord_seat") is not None:
                bottom = " ".join(room.get("bottom_cards", [])) or "(hidden)"
                lines.append(f"Landlord: seat {room.get('landlord_seat')} | Bottom: {bottom}")
            if room.get("phase") in {"playing", "finished", "paused_reconnect"}:
                table_cards = " ".join(room.get("table_cards", [])) or "(none)"
                lines.append(f"Turn: seat {room.get('current_turn')} | Table: seat {room.get('table_seat')} -> {table_cards}")
            hand = room.get("your_hand", [])
            if hand:
                indexed = "  ".join(f"{index + 1}:{card}" for index, card in enumerate(hand))
                lines.append("Your hand:")
                lines.append(indexed)
            if room.get("winner_seat") is not None:
                lines.append(f"Winner: seat {room['winner_seat']} ({room['winner_side']})")

        lines.append("")
        lines.append("Commands:")
        lines.append("  bid <0-3>")
        lines.append("  play <card> <card> ...")
        lines.append("  play #1 #2 #3   (use your hand indexes)")
        lines.append("  pass")
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
        role = "landlord" if seat.get("is_landlord") else "farmer"
        count = seat.get("hand_count")
        count_text = "-" if count is None else str(count)
        return f"S{seat['seat']} {name} [{status},{role},{count_text}]"

    def _dispatch_command(self, connection: DdzClientConnection, room: dict[str, Any] | None, command: str) -> None:
        parts = command.split()
        if not parts:
            return
        action = parts[0].lower()
        if action == "bid":
            if len(parts) != 2:
                raise ValueError("Usage: bid <0-3>")
            connection.send_bid(int(parts[1]))
            return
        if action == "pass":
            connection.send_pass()
            return
        if action == "play":
            if len(parts) < 2:
                raise ValueError("Usage: play <card> <card> ...")
            if room is None:
                raise ValueError("Room state is not available yet.")
            cards = self._resolve_cards(room.get("your_hand", []), parts[1:])
            connection.send_play(cards)
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


def run_ddz_remote_client(host: str, port: int, name: str, session_token: str | None = None) -> int:
    return DdzRemoteApp(host, port, name, session_token).run()
