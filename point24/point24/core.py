from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations_with_replacement

TARGET_VALUE = Fraction(24, 1)
CATALOG_VERSION = 1
ALLOWED_NUMBERS = tuple(range(1, 14))


@dataclass(frozen=True)
class ValidationResult:
    expression: str
    value: Fraction


@dataclass(frozen=True)
class _ExpressionState:
    value: Fraction
    expression: str


def puzzle_key(numbers: list[int] | tuple[int, int, int, int]) -> str:
    values = _normalize_numbers(numbers)
    return ",".join(str(value) for value in sorted(values))


def parse_puzzle_key(key: str) -> tuple[int, int, int, int]:
    parts = key.split(",")
    if len(parts) != 4:
        raise ValueError("Puzzle key must contain exactly four numbers.")
    return tuple(_normalize_numbers(int(part) for part in parts))


def iter_all_puzzle_keys() -> list[str]:
    return [",".join(str(value) for value in values) for values in combinations_with_replacement(ALLOWED_NUMBERS, 4)]


def is_solvable(numbers: list[int] | tuple[int, int, int, int]) -> bool:
    return find_solution(numbers) is not None


def find_solution(numbers: list[int] | tuple[int, int, int, int]) -> str | None:
    states = [_ExpressionState(Fraction(value, 1), str(value)) for value in _normalize_numbers(numbers)]
    return _search_solution(states)


def validate_submission(numbers: list[int] | tuple[int, int, int, int], expression: str) -> ValidationResult:
    cleaned = expression.strip()
    if not cleaned:
        raise ValueError("Expression cannot be empty.")

    try:
        parsed = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Expression syntax is invalid.") from exc

    required_numbers = sorted(_normalize_numbers(numbers))
    used_numbers: list[int] = []
    value = _evaluate_ast(parsed.body, used_numbers)
    if sorted(used_numbers) != required_numbers:
        raise ValueError("Expression must use each puzzle number exactly once.")
    if value != TARGET_VALUE:
        raise ValueError("Expression does not evaluate to 24.")
    return ValidationResult(expression=cleaned, value=value)


def _search_solution(states: list[_ExpressionState]) -> str | None:
    if len(states) == 1:
        return states[0].expression if states[0].value == TARGET_VALUE else None

    seen: set[tuple[tuple[int, int], ...]] = set()
    for left_index in range(len(states)):
        for right_index in range(left_index + 1, len(states)):
            left = states[left_index]
            right = states[right_index]
            remaining = [states[index] for index in range(len(states)) if index not in (left_index, right_index)]
            for candidate in _combine_states(left, right):
                signature_values = [state.value for state in remaining]
                signature_values.append(candidate.value)
                signature = tuple(sorted((value.numerator, value.denominator) for value in signature_values))
                if signature in seen:
                    continue
                seen.add(signature)
                solution = _search_solution([*remaining, candidate])
                if solution is not None:
                    return solution
    return None


def _combine_states(left: _ExpressionState, right: _ExpressionState) -> list[_ExpressionState]:
    candidates = [
        _ExpressionState(left.value + right.value, f"({left.expression} + {right.expression})"),
        _ExpressionState(left.value - right.value, f"({left.expression} - {right.expression})"),
        _ExpressionState(right.value - left.value, f"({right.expression} - {left.expression})"),
        _ExpressionState(left.value * right.value, f"({left.expression} * {right.expression})"),
    ]
    if right.value != 0:
        candidates.append(_ExpressionState(left.value / right.value, f"({left.expression} / {right.expression})"))
    if left.value != 0:
        candidates.append(_ExpressionState(right.value / left.value, f"({right.expression} / {left.expression})"))
    return candidates


def _evaluate_ast(node: ast.AST, used_numbers: list[int]) -> Fraction:
    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left, used_numbers)
        right = _evaluate_ast(node.right, used_numbers)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("Division by zero is not allowed.")
            return left / right
        raise ValueError("Only +, -, *, / are allowed.")

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate_ast(node.operand, used_numbers)

    if isinstance(node, ast.Constant) and type(node.value) is int:
        number = int(node.value)
        if number not in ALLOWED_NUMBERS:
            raise ValueError("Only numbers from 1 to 13 are allowed.")
        used_numbers.append(number)
        return Fraction(number, 1)

    raise ValueError("Expression may only contain numbers, operators, and parentheses.")


def _normalize_numbers(values) -> tuple[int, int, int, int]:
    normalized = tuple(int(value) for value in values)
    if len(normalized) != 4:
        raise ValueError("Puzzle must contain exactly four numbers.")
    for value in normalized:
        if value not in ALLOWED_NUMBERS:
            raise ValueError("Puzzle numbers must be between 1 and 13.")
    return normalized
