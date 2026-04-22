from __future__ import annotations

import argparse

from .ui import run_local_minesweeper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minesweeper", description="Terminal minesweeper.")
    parser.add_argument(
        "--difficulty",
        choices=("beginner", "intermediate", "expert"),
        default="beginner",
        help="Preset board difficulty.",
    )
    parser.add_argument("--rows", type=int, help="Custom board height.")
    parser.add_argument("--cols", type=int, help="Custom board width.")
    parser.add_argument("--mines", type=int, help="Custom mine count.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_local_minesweeper(
        args.difficulty,
        rows=args.rows,
        cols=args.cols,
        mines=args.mines,
    )
