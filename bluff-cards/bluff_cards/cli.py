from __future__ import annotations

import argparse
import sys

from bluff_cards.server import BluffServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bluff_cards", description="Terminal bluff cards.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server_parser = subparsers.add_parser("server", help="Run a TCP bluff card server.")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind.")
    server_parser.add_argument("--port", type=int, default=9020, help="Port to bind.")
    server_parser.add_argument("--players", type=int, default=4, help="Number of seats, from 2 to 4.")
    server_parser.add_argument("--bots", type=int, default=0, help="Fill empty seats with basic AI bots.")

    client_parser = subparsers.add_parser("client", help="Connect to a TCP bluff card server.")
    client_parser.add_argument("--host", required=True, help="Server host to connect to.")
    client_parser.add_argument("--port", type=int, required=True, help="Server port to connect to.")
    client_parser.add_argument("--name", required=True, help="Player name for room display.")
    client_parser.add_argument("--theme", choices=("modern", "stealth"), default="modern", help="UI style preset.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "server":
        server = BluffServer(args.host, args.port, players=args.players, bot_count=args.bots)
        try:
            server.serve_game()
        except KeyboardInterrupt:
            server.shutdown()
            print("Bluff Cards server interrupted.", file=sys.stderr, flush=True)
            return 130
        return 0

    if args.command == "client":
        from bluff_cards.ui import run_bluff_remote_client

        try:
            return run_bluff_remote_client(args.host, args.port, args.name, args.theme)
        except KeyboardInterrupt:
            print("Bluff Cards client interrupted.", file=sys.stderr, flush=True)
            return 130

    parser.error(f"Unsupported command: {args.command}")
    return 2
