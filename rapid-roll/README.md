# Rapid Roll

A terminal version of the classic Nokia Rapid Roll survival game. Roll the ball left and right, keep falling onto new platforms, collect bonuses, and avoid the danger edges.

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
uv run python -m rapid_roll --theme modern
uv run python -m rapid_roll --theme stealth
uv run python -m rapid_roll --theme modern --rows 28 --cols 26
```

Press `t` while playing to switch theme.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--rows` | `24` | Height of the board |
| `--cols` | `22` | Width of the board (min 12) |
| `--theme` | `modern` | Visual theme (`modern` or `stealth`) |

## Controls

- `left` / `a`: roll left
- `right` / `d`: roll right
- `space` / `p`: pause or resume
- `r`: restart
- `?`: toggle help
- `q`: quit

## Mechanics

- Platforms scroll upward while the ball falls under gravity
- Land on platforms to survive and earn points
- Hitting the top or bottom danger edge costs one life
- Losing all lives ends the round; a new round starts automatically after 5 seconds
- Surviving earns steady points, and clean platform landings add bonus points
- Pickups:
  - `◆` coin: +50 score
  - `♥` heart: +1 life, up to 5
  - `S` slow: temporarily lowers platform scroll speed
