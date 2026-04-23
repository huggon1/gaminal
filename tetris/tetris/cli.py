from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tetris", description="Terminal tetris game.")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_tetris_game

    return run_tetris_game(theme=args.theme)
