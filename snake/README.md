# Snake

A terminal snake game.

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
uv run python -m snake --theme modern
uv run python -m snake --theme stealth
uv run python -m snake --map open_wrap --speed fast
```

Press `t` while playing to switch theme.

## Controls

- Arrow keys / `WASD`: move snake
- `Space`: pause/resume
- `m`: cycle map on the setup screen
- `v`: cycle speed on the setup screen
- `Enter`: start the selected setup
- `r`: restart
- `q`: quit

## Maps

- `classic_walls`: four lethal borders, no internal obstacles
- `open_wrap`: no lethal borders; edges wrap to the opposite side
- `center_blocks`: classic borders with a compact center obstacle cluster
- `cross_portal`: full cross wall; use edge wrapping to move between regions
- `islands`: classic borders with four small obstacle islands
- `gate_maze`: classic borders with two gated barrier lines

## Speeds

- `slow`: 0.24s per tick, +1 per fruit
- `normal`: 0.18s per tick, +2 per fruit
- `fast`: 0.12s per tick, +3 per fruit
- `insane`: 0.08s per tick, +5 per fruit
