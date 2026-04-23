# Reversi

A terminal Reversi (黑白棋) implementation for Linux with local and TCP multiplayer modes.

## Requirements

- `uv`
- Python 3.12+
- A terminal with Textual support

## Setup

```bash
uv sync
```

## Run

```bash
uv run python -m reversi local --theme modern
uv run python -m reversi server --host 0.0.0.0 --port 9001
uv run python -m reversi client --host 127.0.0.1 --port 9001 --name Alice --theme stealth
```

All Textual clients support `--theme modern|stealth`, and you can press `t` in-app to switch styles.

## Remote Play

- Start the server once, then have two players connect with different `--name` values.
- After both players connect, both must press `r` to mark ready and start the round.
- After each round, the scoreboard is preserved and colors rotate before the next ready check.
- If a player disconnects, the room pauses and the remaining player can wait or press `x` to close the room.
- Reconnect with:

```bash
uv run python -m reversi client --host 127.0.0.1 --port 9001 --name Alice --session-token <token>
```

## Controls

- Arrow keys: move cursor
- `Enter` or `Space`: place a stone or send a move
- `·`: valid move indicator on empty cells
- `r`: ready for the next round
- `s`: resign the current round
- `x`: close the room while waiting for an opponent to reconnect
- `q`: quit current session

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
