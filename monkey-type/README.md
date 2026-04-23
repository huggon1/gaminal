# Monkey Type

A terminal typing speed test.

## Requirements
- `uv`
- Python 3.12+

## Setup
```bash
uv sync
```

## Run
```bash
uv run python -m monkey_type               # 30-second timed test
uv run python -m monkey_type --time 60    # 60-second test
uv run python -m monkey_type --words 50   # 50-word test
uv run python -m monkey_type --theme stealth
```

## Controls
- **Type** to start the test
- **Space** — confirm word
- **Backspace** — delete last character
- **Tab / Esc** — restart test
- **Theme** — choose with `--theme` before launch
- **?** — toggle help
- **q** — quit
