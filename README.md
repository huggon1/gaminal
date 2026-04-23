# Gaminal — Terminal Games Workspace

A collection of terminal games built with Python and [Textual](https://github.com/Textualize/textual). Each game lives in its own directory with an independent `uv` environment.

## Games

| Game | Type | Description |
|------|------|-------------|
| [gomoku](./gomoku/README.md) | Multiplayer | Classic five-in-a-row, local or networked |
| [dou-dizhu](./dou-dizhu/README.md) | Multiplayer | Chinese landlord card game, 3-player networked |
| [bluff-cards](./bluff-cards/README.md) | Multiplayer | Bluffing card game for 2–6 players, networked |
| [minesweeper](./minesweeper/README.md) | Single-player | Classic minesweeper with customizable grid and difficulty |
| [point24](./point24/README.md) | Single-player | 24-point arithmetic puzzle with precomputed puzzle set |
| [game-2048](./game-2048/README.md) | Single-player | Slide-and-merge tile puzzle |
| [snake](./snake/README.md) | Single-player | Classic snake, endless survival |
| [tetris](./tetris/README.md) | Single-player | Standard Tetris with SRS rotation and NES scoring |
| [racing](./racing/README.md) | Single-player | Corridor racer: stay in the drifting gap, collect coins, gap narrows |
| [breakout](./breakout/README.md) | Single-player | Ball-and-paddle brick breaker, 3 lives |
| [fishing](./fishing/README.md) | Single-player | Stardew Valley-style fishing minigame |

## Requirements

- [`uv`](https://github.com/astral-sh/uv)
- Python 3.12+
- A terminal with Textual support (most modern terminals)

## Getting Started

Each game is self-contained. Enter its directory, install dependencies, and run:

```bash
cd <game>
uv sync
uv run python -m <module> --theme modern
```

See each game's README for the exact command, available options, and controls.

## Themes

All games support two visual themes selectable at launch or toggled in-game with `t`:

- `modern` — blue-toned dark UI
- `stealth` — monochrome black and white
