# Racing

A terminal endless corridor racer. The road narrows and drifts — stay inside the gap and collect coins to score.

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
uv run python -m racing --theme modern
uv run python -m racing --theme stealth
uv run python -m racing --theme modern --rows 30 --cols 19
```

Press `t` while playing to switch theme.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--rows` | `20` | Height of the road |
| `--cols` | `15` | Width of the road (min 11) |
| `--theme` | `modern` | Visual theme (`modern` or `stealth`) |

## Controls

- `left` / `a`: steer left
- `right` / `d`: steer right
- `r`: restart
- `q`: quit

## Mechanics

- The road has a **corridor** (open gap) surrounded by walls (`#`) — the gap always exists, but it drifts left and right over time
- Stay inside the gap; hitting a wall ends the game
- Collect coins (`*`) inside the gap for +25 points each
- The gap **narrows** over time (from 7 down to 3 columns) and the road **scrolls faster** — both ramp independently
- Surviving earns 1 point per frame; coin bonuses reward precise positioning
