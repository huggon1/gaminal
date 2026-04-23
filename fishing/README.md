# Fishing

A terminal fishing minigame inspired by Stardew Valley. Keep your catch indicator on the fish to fill the progress bar and reel it in.

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
uv run python -m fishing --theme modern
uv run python -m fishing --theme stealth
```

Press `t` while playing to switch theme.

## Controls

- `Space` / `up` / `w`: boost the catch indicator upward
- `p`: pause / resume
- `r`: restart
- `q`: quit

## Mechanics

- A vertical fishing zone shows your **catch indicator** (cyan `===`) and the **fish** (yellow symbol)
- Press `Space` to push the indicator up; gravity pulls it back down — tap rhythmically to track the fish
- When the indicator overlaps the fish, the **catch progress bar** fills; when it drifts away, the bar drains
- Fill the bar to 100% to catch the fish; drain to 0% and the fish escapes (resets your streak)
- **Streak bonus**: consecutive catches multiply your score (`+1 bonus per 3 caught in a row`)

## Fish Types

| Fish | Difficulty | Score | Behavior |
|------|-----------|-------|----------|
| Carp `~o~` | ★☆☆ | 10 | Slow, predictable |
| Bass `><>` | ★★☆ | 25 | Moderate speed |
| Catfish `==>` | ★★★ | 50 | Occasional sharp darts |
| Squid `~~~` | ★★★★ | 100 | Fast and erratic |

Harder fish appear more often as your catch count grows.
