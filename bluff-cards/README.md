# Bluff Cards

A terminal bluff card game for Linux.

## Requirements

- `uv`
- Python 3.12+
- A Linux terminal with `curses`

## Setup

```bash
uv sync
```

## Run

```bash
uv run python -m bluff_cards server --host 0.0.0.0 --port 9020 --players 4
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice
```

## Commands

Enter commands directly in the curses client prompt and press `Enter`.

```text
play #1 claim 1
play #1 #2 claim 2
play AS BJ claim 2
challenge
accept
quit
```

- `play ... claim N` sends the real cards from your hand and publicly claims they are `N` copies of the current target rank.
- `challenge` reveals the previous claim and applies the life penalty immediately.
- `accept` is only valid when the previous claimer has emptied their hand and you choose not to challenge.
- Reconnect with:

```bash
uv run python -m bluff_cards client --host 127.0.0.1 --port 9020 --name Alice --session-token <token>
```

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
