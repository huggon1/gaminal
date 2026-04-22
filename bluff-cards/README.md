# Bluff Cards

A terminal bluff card game for Linux.

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
uv run python -m bluff_cards server --host 0.0.0.0 --port 9020 --players 4
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice --theme modern
```

The Textual client supports `--theme modern|stealth`, runtime switching with `t`, and selection-based play/claim controls.

## Controls

- Up/Down browse your hand
- Space toggles card selection
- `1`/`2`/`3` sets the claim count
- `p` submits the selected cards with the current claim count
- `c` challenges the previous claim
- `a` accepts an empty-hand claim
- Reconnect with:

```bash
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice --session-token <token>
```

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
