from __future__ import annotations

import argparse

from bluff_cards.server import BluffServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bluff_cards", description="Terminal bluff cards.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    server_parser = subparsers.add_parser("server", help="Run a TCP bluff card server.")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind.")
    server_parser.add_argument("--port", type=int, default=9020, help="Port to bind.")
    server_parser.add_argument("--players", type=int, default=4, help="Number of seats, from 2 to 4.")

    client_parser = subparsers.add_parser("client", help="Connect to a TCP bluff card server.")
    client_parser.add_argument("--host", required=True, help="Server host to connect to.")
    client_parser.add_argument("--port", type=int, required=True, help="Server port to connect to.")
    client_parser.add_argument("--name", required=True, help="Player name for room display.")
    client_parser.add_argument("--session-token", help="Reconnect using a previous session token.")
    client_parser.add_argument("--theme", choices=("modern", "stealth"), default="modern", help="UI style preset.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "server":
        server = BluffServer(args.host, args.port, players=args.players)
        server.serve_game()
        return 0

    if args.command == "client":
        from bluff_cards.ui import run_bluff_remote_client

        return run_bluff_remote_client(args.host, args.port, args.name, args.session_token, args.theme)

    parser.error(f"Unsupported command: {args.command}")
    return 2
