# Dou Dizhu

A terminal dou dizhu implementation for Linux.

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
uv run python -m dou_dizhu server --host 0.0.0.0 --port 9010
uv run python -m dou_dizhu client --host 127.0.0.1 --port 9010 --name Alice --theme modern
```

The Textual client supports `--theme modern|stealth`, runtime switching with `t`, and selection-based hand interaction.

## Controls

- Up/Down browse your hand
- Space toggles card selection
- `p` plays selected cards
- `a` passes
- `0`/`1`/`2`/`3` sends bids
- `t` switches theme
- Reconnect with:

```bash
uv run python -m dou_dizhu client --host 127.0.0.1 --port 9010 --name Alice --session-token <token>
```

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
