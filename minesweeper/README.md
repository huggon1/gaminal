# Minesweeper

A terminal minesweeper implementation for Linux.

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
uv run python -m minesweeper
uv run python -m minesweeper --difficulty expert
uv run python -m minesweeper --rows 10 --cols 12 --mines 20
```

## Controls

- Arrow keys: move cursor
- `Enter` or `Space`: reveal
- `f`: toggle flag
- `r`: restart
- `q`: quit

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
