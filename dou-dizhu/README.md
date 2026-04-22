# Dou Dizhu

A terminal dou dizhu implementation for Linux.

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
uv run python -m dou_dizhu server --host 0.0.0.0 --port 9010
uv run python -m dou_dizhu client --host 127.0.0.1 --port 9010 --name Alice
```

## Commands

Enter commands directly in the curses client prompt and press `Enter`.

```text
bid 1
bid 3
play #1 #2 #3
play 3S 3H 3C
pass
quit
```

- `play #1 #2 #3` uses the indexes shown in your hand display.
- Reconnect with:

```bash
uv run python -m dou_dizhu client --host 127.0.0.1 --port 9010 --name Alice --session-token <token>
```

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
