from __future__ import annotations

import json
from typing import Any, TextIO


def send_message(writer: TextIO, message: dict[str, Any]) -> None:
    writer.write(json.dumps(message, separators=(",", ":")))
    writer.write("\n")
    writer.flush()


def read_message(reader: TextIO) -> dict[str, Any] | None:
    line = reader.readline()
    if not line:
        return None
    return json.loads(line)
