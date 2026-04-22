# Games Workspace

This repository now holds independent game projects at the root.

## Projects

- [gomoku](./gomoku/README.md)
- [dou-dizhu](./dou-dizhu/README.md)
- [bluff-cards](./bluff-cards/README.md)
- [minesweeper](./minesweeper/README.md)
- [point24](./point24/README.md)

## Usage

Enter the game directory you want, then use its own `uv` environment and README.

```bash
cd gomoku
uv sync
uv run python -m gomoku local
```

```bash
cd dou-dizhu
uv sync
uv run python -m dou_dizhu server --host 0.0.0.0 --port 9010
```

```bash
cd bluff-cards
uv sync
uv run python -m bluff_cards server --host 0.0.0.0 --port 9020 --players 4
```

```bash
cd minesweeper
uv sync
uv run python -m minesweeper --difficulty expert
```

```bash
cd point24
uv sync
uv run python -m point24
```
