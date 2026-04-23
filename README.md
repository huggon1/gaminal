# Games Workspace

This repository now holds independent game projects at the root.

## Projects

- [gomoku](./gomoku/README.md)
- [dou-dizhu](./dou-dizhu/README.md)
- [bluff-cards](./bluff-cards/README.md)
- [minesweeper](./minesweeper/README.md)
- [point24](./point24/README.md)
- [game-2048](./game-2048/README.md)
- [snake](./snake/README.md)

## Usage

Enter the game directory you want, then use its own `uv` environment and README.

```bash
cd gomoku
uv sync
uv run python -m gomoku local --theme modern
```

```bash
cd dou-dizhu
uv sync
uv run python -m dou_dizhu server --host 0.0.0.0 --port 9010
uv run python -m dou_dizhu client --host 127.0.0.1 --port 9010 --name Alice --theme stealth
```

```bash
cd bluff-cards
uv sync
uv run python -m bluff_cards server --host 0.0.0.0 --port 9020 --players 4
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice --theme modern
```

```bash
cd minesweeper
uv sync
uv run python -m minesweeper --difficulty expert --theme stealth
```

```bash
cd point24
uv sync
uv run python -m point24 --theme modern
```


```bash
cd game-2048
uv sync
uv run python -m game_2048 --theme modern
```

```bash
cd snake
uv sync
uv run python -m snake --theme stealth
```
