from __future__ import annotations

import argparse
import sys

from reversi.net.server import ReversiServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reversi", description="Terminal reversi (黑白棋).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    local_parser = subparsers.add_parser("local", help="Run a local two-player game.")
    local_parser.add_argument("--theme", choices=("modern", "stealth"), default="modern", help="UI style preset.")

    server_parser = subparsers.add_parser("server", help="Run a TCP reversi server.")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind.")
    server_parser.add_argument("--port", type=int, default=9001, help="Port to bind.")

    client_parser = subparsers.add_parser("client", help="Connect to a TCP reversi server.")
    client_parser.add_argument("--host", required=True, help="Server host to connect to.")
    client_parser.add_argument("--port", type=int, required=True, help="Server port to connect to.")
    client_parser.add_argument("--name", required=True, help="Player name for room and scoreboard display.")
    client_parser.add_argument("--session-token", help="Reconnect using a previous session token.")
    client_parser.add_argument("--theme", choices=("modern", "stealth"), default="modern", help="UI style preset.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "local":
        from reversi.ui.curses_app import run_local_game

        try:
            return run_local_game(theme=args.theme)
        except KeyboardInterrupt:
            print("Reversi local game interrupted.", file=sys.stderr, flush=True)
            return 130

    if args.command == "server":
        server = ReversiServer(args.host, args.port)
        try:
            server.serve_game()
        except KeyboardInterrupt:
            server.shutdown()
            print("Reversi server interrupted.", file=sys.stderr, flush=True)
            return 130
        return 0

    if args.command == "client":
        from reversi.ui.curses_app import run_remote_client

        try:
            return run_remote_client(args.host, args.port, args.name, args.session_token, args.theme)
        except KeyboardInterrupt:
            print("Reversi client interrupted.", file=sys.stderr, flush=True)
            return 130

    parser.error(f"Unsupported command: {args.command}")
    return 2
