from __future__ import annotations

import json
import queue
import socket
import threading
from typing import Any

from dou_dizhu.protocol import send_message


class DdzClientConnection:
    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host
        self.port = port
        self.name = name
        self._socket: socket.socket | None = None
        self._reader = None
        self._writer = None
        self._closed = threading.Event()
        self._send_lock = threading.Lock()
        self._messages: queue.Queue[dict[str, Any]] = queue.Queue()

    def connect(self) -> None:
        self._socket = socket.create_connection((self.host, self.port), timeout=5)
        self._socket.settimeout(None)
        self._socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._reader = self._socket.makefile("r", encoding="utf-8", newline="\n")
        self._writer = self._socket.makefile("w", encoding="utf-8", newline="\n")
        threading.Thread(target=self._reader_loop, daemon=True).start()
        self.send({"type": "join", "name": self.name})

    def _reader_loop(self) -> None:
        assert self._reader is not None
        while not self._closed.is_set():
            try:
                line = self._reader.readline()
            except OSError:
                break
            if not line:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._messages.put({"type": "disconnect", "message": "Server sent invalid JSON."})
                break
            self._messages.put(payload)
        if not self._closed.is_set():
            self._messages.put({"type": "disconnect", "message": "Connection closed."})

    def poll_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        while True:
            try:
                messages.append(self._messages.get_nowait())
            except queue.Empty:
                return messages

    def send_bid(self, amount: int) -> None:
        self.send({"type": "bid", "amount": amount})

    def send_play(self, cards: list[str]) -> None:
        self.send({"type": "play", "cards": list(cards)})

    def send_pass(self) -> None:
        self.send({"type": "pass"})

    def send_leave(self) -> None:
        self.send({"type": "leave"})

    def send(self, message: dict[str, Any]) -> None:
        if self._closed.is_set():
            raise ConnectionError("Connection is closed.")
        if self._writer is None:
            raise ConnectionError("Connection is not open.")
        with self._send_lock:
            send_message(self._writer, message)

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        if self._writer is not None:
            try:
                self._writer.close()
            except OSError:
                pass
        if self._reader is not None:
            try:
                self._reader.close()
            except OSError:
                pass
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
