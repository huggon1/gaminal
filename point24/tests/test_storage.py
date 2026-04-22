from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from random import Random

from point24.storage import Point24Puzzle, Point24Repository, Point24Stats


class Point24StorageTests(unittest.TestCase):
    def test_stats_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = Point24Repository(Path(temp_dir))
            stats = Point24Stats()
            stats.mark_started()
            stats.mark_solved("1,2,3,4", 5.5)

            repository.save_stats(stats)
            loaded = repository.load_stats()

            self.assertEqual(loaded.puzzles_started, 1)
            self.assertEqual(loaded.puzzles_solved, 1)
            self.assertEqual(loaded.total_solve_seconds, 5.5)
            self.assertEqual(loaded.solved_puzzle_keys, {"1,2,3,4"})

    def test_choose_next_puzzle_prefers_unsolved(self) -> None:
        repository = Point24Repository(Path("/tmp/unused-point24-tests"))
        puzzles = [
            Point24Puzzle(key="1,1,4,6", numbers=(1, 1, 4, 6), solution="solution-a"),
            Point24Puzzle(key="3,3,8,8", numbers=(3, 3, 8, 8), solution="solution-b"),
        ]

        chosen = repository.choose_next_puzzle(puzzles, {"1,1,4,6"}, rng=Random(0))
        self.assertEqual(chosen.key, "3,3,8,8")

    def test_catalog_is_rebuilt_when_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = Point24Repository(Path(temp_dir))
            repository.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            repository.catalog_path.write_text("{bad json", encoding="utf-8")

            catalog = repository.ensure_catalog()
            payload = json.loads(repository.catalog_path.read_text(encoding="utf-8"))

            self.assertTrue(catalog)
            self.assertIn("puzzles", payload)


if __name__ == "__main__":
    unittest.main()
