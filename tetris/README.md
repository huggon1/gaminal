# Tetris

A terminal Tetris game with SRS rotation, ghost piece, and NES-style scoring.

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
uv run python -m tetris --theme modern
uv run python -m tetris --theme stealth
```

Press `t` while playing to switch theme.

## Controls

- Arrow keys / `WASD`: move and rotate (`up`/`w` rotates)
- `down` / `s`: soft drop
- `Space`: hard drop
- `p`: pause / resume
- `r`: restart
- `q`: quit

## Mechanics

- 7 standard tetrominoes with SRS (Super Rotation System) wall kicks
- Ghost piece shows where the current piece will land
- Speed increases every 10 lines cleared
- Scoring follows the NES formula: 40 / 100 / 300 / 1200 × level for 1–4 line clears
