# Bluff Cards

A terminal bluff card game.

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
uv run python -m bluff_cards server --host 0.0.0.0 --port 9020 --players 4 --bots 0
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice --theme modern
```

The server supports `--bots N` to fill empty seats with basic AI bots, as long as at least one human seat remains. The Textual client supports `--theme modern|stealth`, runtime switching with `t`, and selection-based play/claim controls.

## Controls

- Up/Down: move the cursor in your hand
- Space: select or unselect the highlighted card
- `p`: submit 1-3 selected cards as a face-down claim matching the current table rank
- `c`: challenge the previous claim
- `Esc`: clear the current selection
- `q`: quit the client

## Rejoin

If the client disconnects but the server is still running, start the client again with the same player name. The server will automatically reconnect you to your previous seat:

```bash
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice
```

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
