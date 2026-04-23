from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="game_2048", description="Terminal 2048 game.")
    parser.add_argument("--size", type=int, default=4, help="Board width/height.")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_2048_game

    return run_2048_game(size=args.size, theme=args.theme)
