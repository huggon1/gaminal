from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

BOARD_SIZE = 8
EMPTY_TOKEN = "."

_DIRECTIONS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


class Player(str, Enum):
    BLACK = "black"
    WHITE = "white"

    def other(self) -> "Player":
        return Player.WHITE if self is Player.BLACK else Player.BLACK

    @property
    def label(self) -> str:
        return "Black" if self is Player.BLACK else "White"

    @property
    def token(self) -> str:
        return "B" if self is Player.BLACK else "W"

    @property
    def stone(self) -> str:
        return "●" if self is Player.BLACK else "○"

    @classmethod
    def from_token(cls, token: str) -> "Player | None":
        if token == "B":
            return cls.BLACK
        if token == "W":
            return cls.WHITE
        return None


@dataclass(frozen=True)
class Move:
    row: int
    col: int
    player: Player


@dataclass
class Board:
    size: int = BOARD_SIZE
    grid: list[list[Player | None]] = field(
        default_factory=lambda: [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    )

    def __post_init__(self) -> None:
        if len(self.grid) != self.size or any(len(row) != self.size for row in self.grid):
            raise ValueError("Board grid must match board size.")
        mid = self.size // 2
        # Only seed the opening position for a completely fresh board.
        if all(cell is None for row in self.grid for cell in row):
            self.grid[mid - 1][mid - 1] = Player.WHITE
            self.grid[mid - 1][mid] = Player.BLACK
            self.grid[mid][mid - 1] = Player.BLACK
            self.grid[mid][mid] = Player.WHITE

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def get(self, row: int, col: int) -> Player | None:
        if not self.in_bounds(row, col):
            raise ValueError("Position is out of bounds.")
        return self.grid[row][col]

    def _flips(self, player: Player, row: int, col: int) -> list[tuple[int, int]]:
        if not self.in_bounds(row, col) or self.grid[row][col] is not None:
            return []
        opponent = player.other()
        flipped: list[tuple[int, int]] = []
        for dr, dc in _DIRECTIONS:
            line: list[tuple[int, int]] = []
            r, c = row + dr, col + dc
            while self.in_bounds(r, c) and self.grid[r][c] is opponent:
                line.append((r, c))
                r += dr
                c += dc
            if line and self.in_bounds(r, c) and self.grid[r][c] is player:
                flipped.extend(line)
        return flipped

    def place(self, player: Player, row: int, col: int) -> list[tuple[int, int]]:
        if not self.in_bounds(row, col):
            raise ValueError("Position is out of bounds.")
        if self.grid[row][col] is not None:
            raise ValueError("Position is already occupied.")
        flips = self._flips(player, row, col)
        if not flips:
            raise ValueError("Invalid move: no pieces would be flipped.")
        self.grid[row][col] = player
        for r, c in flips:
            self.grid[r][c] = player
        return flips

    def valid_moves(self, player: Player) -> list[tuple[int, int]]:
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.grid[r][c] is None and self._flips(player, r, c)
        ]

    def count(self, player: Player) -> int:
        return sum(1 for row in self.grid for cell in row if cell is player)

    def is_full(self) -> bool:
        return all(cell is not None for row in self.grid for cell in row)

    def to_tokens(self) -> list[str]:
        rows: list[str] = []
        for row in self.grid:
            rows.append("".join(cell.token if cell is not None else EMPTY_TOKEN for cell in row))
        return rows

    @classmethod
    def from_tokens(cls, rows: list[str]) -> "Board":
        size = len(rows)
        grid: list[list[Player | None]] = []
        for row in rows:
            if len(row) != size:
                raise ValueError("Serialized board rows must form a square.")
            grid_row: list[Player | None] = []
            for token in row:
                if token == EMPTY_TOKEN:
                    grid_row.append(None)
                else:
                    player = Player.from_token(token)
                    if player is None:
                        raise ValueError(f"Unknown board token: {token}")
                    grid_row.append(player)
            grid.append(grid_row)
        return cls(size=size, grid=grid)


@dataclass
class GameState:
    board: Board = field(default_factory=Board)
    current_player: Player = Player.BLACK
    winner: Player | None = None
    last_move: Move | None = None
    draw: bool = False
    finished: bool = False
    skipped_turn: bool = False  # True when last turn was auto-skipped

    def valid_moves_for_current(self) -> list[tuple[int, int]]:
        return self.board.valid_moves(self.current_player)

    def get_scores(self) -> tuple[int, int]:
        return self.board.count(Player.BLACK), self.board.count(Player.WHITE)

    def play(self, row: int, col: int) -> Move:
        if self.finished:
            raise ValueError("Game is already finished.")

        player = self.current_player
        self.board.place(player, row, col)  # raises ValueError if invalid
        move = Move(row=row, col=col, player=player)
        self.last_move = move

        if self.board.is_full():
            self._resolve_winner()
            return move

        opponent = player.other()
        if self.board.valid_moves(opponent):
            self.current_player = opponent
            self.skipped_turn = False
        elif self.board.valid_moves(player):
            # Opponent has no moves — current player plays again
            self.skipped_turn = True
        else:
            # Neither player has moves
            self._resolve_winner()

        return move

    def _resolve_winner(self) -> None:
        self.finished = True
        black, white = self.get_scores()
        if black > white:
            self.winner = Player.BLACK
        elif white > black:
            self.winner = Player.WHITE
        else:
            self.draw = True

    def status_text(self) -> str:
        black, white = self.get_scores()
        if self.winner is not None:
            return f"● {black}  ○ {white} — {self.winner.label} wins!"
        if self.draw:
            return f"● {black}  ○ {white} — Draw."
        skip_note = " (opponent skipped)" if self.skipped_turn else ""
        return f"● {black}  ○ {white} — {self.current_player.label} to move.{skip_note}"

    def to_snapshot(self) -> dict[str, object]:
        black, white = self.get_scores()
        return {
            "board_size": self.board.size,
            "board": self.board.to_tokens(),
            "current_player": self.current_player.value,
            "winner": self.winner.value if self.winner is not None else None,
            "last_move": None
            if self.last_move is None
            else {
                "row": self.last_move.row,
                "col": self.last_move.col,
                "player": self.last_move.player.value,
            },
            "draw": self.draw,
            "finished": self.finished,
            "skipped_turn": self.skipped_turn,
            "scores": [black, white],
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, object]) -> "GameState":
        board = Board.from_tokens(list(snapshot["board"]))
        current_player = Player(str(snapshot["current_player"]))
        winner_raw = snapshot.get("winner")
        winner = Player(str(winner_raw)) if winner_raw is not None else None
        last_move_raw = snapshot.get("last_move")
        last_move = None
        if isinstance(last_move_raw, dict):
            last_move = Move(
                row=int(last_move_raw["row"]),
                col=int(last_move_raw["col"]),
                player=Player(str(last_move_raw["player"])),
            )
        return cls(
            board=board,
            current_player=current_player,
            winner=winner,
            last_move=last_move,
            draw=bool(snapshot["draw"]),
            finished=bool(snapshot["finished"]),
            skipped_turn=bool(snapshot.get("skipped_turn", False)),
        )
