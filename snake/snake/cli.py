from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="snake", description="Terminal snake game.")
    parser.add_argument("--rows", type=int, default=16, help="Board rows.")
    parser.add_argument("--cols", type=int, default=24, help="Board columns.")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_snake_game

    return run_snake_game(rows=args.rows, cols=args.cols, theme=args.theme)
