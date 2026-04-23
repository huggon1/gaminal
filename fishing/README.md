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
uv run python -m fishing --theme modern --lanes 2
```

Press `t` while playing to switch theme.

`--lanes` supports `1` or `2`. In two-lane mode, each lane tracks its own score, catches, and streak, and the side panel also shows total score and total catches.

## Controls

- `Space` / `up` / `w`: boost lane 1
- `f`: boost lane 1
- `j`: boost lane 2 in two-lane mode
- `p`: pause / resume
- `r`: restart
- `q`: quit

## Mechanics

- A vertical fishing zone shows your **catch indicator** (cyan `===`) and the **fish** (yellow symbol)
- Press the lane key rhythmically to push the indicator up while gravity pulls it back down
- Optional two-lane mode runs two fishing zones side by side, each controlled independently
- When the indicator overlaps the fish, the **catch progress bar** fills; when it drifts away, the bar drains
- Fill the bar to 100% to catch the fish; drain to 0% and the fish escapes
- Consecutive catches on the same lane build that lane's streak bonus (`+1 bonus per 3 caught in a row`)

## Fish Types

| Fish | Difficulty | Score | Behavior |
|------|------------|-------|----------|
| Carp `~o~` | 1/4 | 10 | Slow, predictable |
| Bass `><>` | 2/4 | 25 | Moderate speed |
| Catfish `==>` | 3/4 | 50 | Occasional sharp darts |
| Squid `~~~` | 4/4 | 100 | Fast and erratic |

Harder fish appear more often as your catch count grows.
