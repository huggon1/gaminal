from __future__ import annotations

import argparse

from gomoku.net.server import GomokuServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gomoku", description="Terminal gomoku.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("local", help="Run a local two-player game.")

    server_parser = subparsers.add_parser("server", help="Run a TCP gomoku server.")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind.")
    server_parser.add_argument("--port", type=int, default=9000, help="Port to bind.")

    client_parser = subparsers.add_parser("client", help="Connect to a TCP gomoku server.")
    client_parser.add_argument("--host", required=True, help="Server host to connect to.")
    client_parser.add_argument("--port", type=int, required=True, help="Server port to connect to.")
    client_parser.add_argument("--name", required=True, help="Player name for room and scoreboard display.")
    client_parser.add_argument("--session-token", help="Reconnect using a previous session token.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "local":
        from gomoku.ui.curses_app import run_local_game

        return run_local_game()

    if args.command == "server":
        server = GomokuServer(args.host, args.port)
        server.serve_game()
        return 0

    if args.command == "client":
        from gomoku.ui.curses_app import run_remote_client

        return run_remote_client(args.host, args.port, args.name, args.session_token)

    parser.error(f"Unsupported command: {args.command}")
    return 2
