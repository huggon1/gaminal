from __future__ import annotations

import unittest

from point24.core import find_solution, is_solvable, puzzle_key, validate_submission


class Point24CoreTests(unittest.TestCase):
    def test_known_solvable_puzzle_returns_solution(self) -> None:
        solution = find_solution((3, 3, 8, 8))
        self.assertIsNotNone(solution)
        validate_submission((3, 3, 8, 8), str(solution))

    def test_known_unsolvable_puzzle_is_rejected(self) -> None:
        self.assertFalse(is_solvable((1, 1, 1, 1)))

    def test_submission_must_use_each_number_once(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_submission((1, 2, 3, 4), "12 + 3 + 9")

    def test_submission_rejects_wrong_total(self) -> None:
        with self.assertRaisesRegex(ValueError, "24"):
            validate_submission((1, 2, 3, 4), "1 + 2 + 3 + 4")

    def test_submission_accepts_fractional_intermediate_values(self) -> None:
        result = validate_submission((3, 3, 8, 8), "8 / (3 - (8 / 3))")
        self.assertEqual(int(result.value), 24)

    def test_puzzle_key_sorts_numbers(self) -> None:
        self.assertEqual(puzzle_key((8, 3, 8, 3)), "3,3,8,8")


if __name__ == "__main__":
    unittest.main()
