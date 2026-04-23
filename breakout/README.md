# Breakout

A terminal brick-breaker game. Bounce the ball to clear all bricks before losing your three lives.

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
uv run python -m breakout --theme modern
uv run python -m breakout --theme stealth
uv run python -m breakout --theme modern --cols 32
```

Press `t` while playing to switch theme.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--cols` | `24` | Board width |
| `--theme` | `modern` | Visual theme (`modern` or `stealth`) |

## Controls

- `left` / `a`: move paddle left
- `right` / `d`: move paddle right
- `Space`: pause / resume
- `r`: restart
- `q`: quit

## Mechanics

- 3 lives — lose one each time the ball drops below the paddle
- Ball angle changes based on where it hits the paddle (edge hits = sharper angle)
- Clear all bricks to win the round
- Each brick scores 10 points
