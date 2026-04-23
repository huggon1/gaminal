#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"

mkdir -p "$UV_CACHE_DIR"

case "${1:-}" in
  sync)
    shift
    exec uv sync "$@"
    ;;
  server)
    shift
    exec uv run python -m dou_dizhu server "$@"
    ;;
  client)
    shift
    exec uv run python -m dou_dizhu client "$@"
    ;;
  test)
    shift
    exec uv run python -m unittest discover -s tests -v "$@"
    ;;
  *)
    cat <<'EOF'
Usage:
  ./run.sh sync
  ./run.sh server [--host HOST] [--port PORT] [--bots 0|1|2]
  ./run.sh client --host HOST --port PORT --name NAME [--theme modern|stealth]
  ./run.sh test

This wrapper keeps uv's cache inside the project so startup works even when ~/.cache is not writable.
EOF
    ;;
esac
