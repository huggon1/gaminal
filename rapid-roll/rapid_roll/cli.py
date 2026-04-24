from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rapid_roll", description="Terminal Rapid Roll game.")
    parser.add_argument("--rows", type=int, default=24, help="Board height.")
    parser.add_argument("--cols", type=int, default=22, help="Board width (min 12).")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_rapid_roll_game

    return run_rapid_roll_game(rows=args.rows, cols=args.cols, theme=args.theme)
