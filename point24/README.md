# 24 Point

A terminal 24-point puzzle game.

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
uv run python -m point24 --theme modern
uv run python -m point24 --theme stealth
```

The Textual UI supports `t` for runtime theme switching and `?` for help.

## Controls

- Type an expression and press `Enter` to submit
- `n`: skip the current puzzle and show one solution
- `q`: save and quit

## Notes

- First launch precomputes all solvable `1-13` four-number puzzles and caches them in the user state directory.
- Progress is stored in `$XDG_STATE_HOME/terminal-games/point24/` or `~/.local/state/terminal-games/point24/`.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
