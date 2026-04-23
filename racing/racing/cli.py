from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="racing", description="Terminal endless racing game.")
    parser.add_argument("--rows", type=int, default=20, help="Road height.")
    parser.add_argument("--cols", type=int, default=15, help="Road width (min 11).")
    parser.add_argument(
        "--theme",
        choices=("modern", "stealth"),
        default="modern",
        help="UI style preset.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from .ui import run_racing_game

    return run_racing_game(rows=args.rows, cols=args.cols, theme=args.theme)
