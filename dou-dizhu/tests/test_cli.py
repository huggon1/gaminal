from __future__ import annotations

import unittest

from dou_dizhu.cli import build_parser


class DdzCliTests(unittest.TestCase):
    def test_client_supports_theme(self) -> None:
        args = build_parser().parse_args(
            ["client", "--host", "127.0.0.1", "--port", "9010", "--name", "Alice", "--theme", "stealth"]
        )

        self.assertEqual(args.command, "client")
        self.assertEqual(args.theme, "stealth")


if __name__ == "__main__":
    unittest.main()
