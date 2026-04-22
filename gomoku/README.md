# Gomoku

A standard-library-only terminal gomoku implementation for Linux.

## Requirements

- `uv`
- Python 3.12+
- A Linux terminal with `curses`

## Setup

```bash
uv sync
```

## Run

```bash
uv run python -m gomoku local
uv run python -m gomoku server --host 0.0.0.0 --port 9000
uv run python -m gomoku client --host 127.0.0.1 --port 9000 --name Alice
```

## Remote Play

- Start the server once, then have two players connect with different `--name` values.
- After both players connect, both must press `r` to mark ready and start the round.
- After each round, the scoreboard is preserved and colors rotate before the next ready check.
- If a player disconnects, the room pauses and the remaining player can wait or press `x` to close the room.
- Reconnect with:

```bash
uv run python -m gomoku client --host 127.0.0.1 --port 9000 --name Alice --session-token <token>
```

## Controls

- Arrow keys: move cursor
- `Enter` or `Space`: place stone
- `r`: ready for the next round
- `s`: resign the current round
- `x`: close the room while waiting for an opponent to reconnect
- `q`: quit current session

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
