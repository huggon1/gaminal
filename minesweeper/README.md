# Minesweeper

A terminal minesweeper implementation for Linux.

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
uv run python -m minesweeper --theme modern
uv run python -m minesweeper --difficulty expert --theme stealth
uv run python -m minesweeper --rows 10 --cols 12 --mines 20 --theme modern
```

The Textual UI supports `--theme modern|stealth`, and you can press `t` while playing to switch themes.

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
