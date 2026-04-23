from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="breakout", description="Terminal breakout game.")
    parser.add_argument("--cols", type=int, default=24, help="Board width.")
    parser.add_argument("--rows", type=int, default=32, help="Board height (default 32, min 18).")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_breakout_game

    return run_breakout_game(rows=args.rows, cols=args.cols, theme=args.theme)
