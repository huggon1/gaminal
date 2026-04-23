# Dou Dizhu

A terminal dou dizhu implementation for Linux.

## Requirements

- `uv`
- Python 3.12+
- A terminal with Textual support

## Setup

```bash
./run.sh sync
```

## Run

```bash
./run.sh server --host 0.0.0.0 --port 9010
./run.sh client --host 127.0.0.1 --port 9010 --name Alice --theme modern
```

To play with bots, start the server with `--bots 1` or `--bots 2`:

```bash
./run.sh server --host 0.0.0.0 --port 9010 --bots 2
./run.sh client --host 127.0.0.1 --port 9010 --name Alice --theme modern
```

The Textual client supports `--theme modern|stealth`, runtime switching with `t`, and selection-based hand interaction.

## Controls

- Up/Down: move the cursor in your hand
- Space: select or unselect the highlighted card
- `p`: play the currently selected cards
- `a`: pass when responding to another player's play
- `0`/`1`/`2`/`3`: bid during the bidding phase
- `Esc`: clear the current selection
- `t`: switch theme
- `q`: quit the client

## Rejoin

If the client disconnects but the server is still running, start the client again with the same player name. The server will automatically reconnect you to your previous seat:

```bash
./run.sh client --host 127.0.0.1 --port 9010 --name Alice
```

## Tests

```bash
./run.sh test
```
