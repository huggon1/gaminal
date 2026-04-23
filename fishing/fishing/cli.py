from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fishing", description="Terminal fishing minigame.")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    parser.add_argument(
        "--lanes",
        type=int,
        choices=(1, 2, 3, 4),
        default=1,
        metavar="N",
        help="Number of fishing lanes (1-4). Keys: h=lane1 j=lane2 k=lane3 l=lane4.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_fishing_game

    return run_fishing_game(theme=args.theme, lanes=args.lanes)
