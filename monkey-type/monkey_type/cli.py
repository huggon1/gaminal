from __future__ import annotations

import argparse

from monkey_type.ui import run_monkey_type


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="monkey_type", description="Terminal typing speed test.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--time",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Timed mode duration in seconds (default: 30).",
    )
    group.add_argument(
        "--words",
        type=int,
        metavar="COUNT",
        help="Word count mode: type exactly N words.",
    )
    parser.add_argument("--theme", choices=("modern", "stealth"), default="modern")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.words:
        return run_monkey_type(duration=0, word_count=args.words, theme=args.theme)
    return run_monkey_type(duration=args.time, word_count=0, theme=args.theme)
