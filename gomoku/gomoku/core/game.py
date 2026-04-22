from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

BOARD_SIZE = 15
EMPTY_TOKEN = "."


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
        return "X" if self is Player.BLACK else "O"

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

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def get(self, row: int, col: int) -> Player | None:
        if not self.in_bounds(row, col):
            raise ValueError("Position is out of bounds.")
        return self.grid[row][col]

    def place(self, player: Player, row: int, col: int) -> None:
        if not self.in_bounds(row, col):
            raise ValueError("Move is out of bounds.")
        if self.grid[row][col] is not None:
            raise ValueError("That position is already occupied.")
        self.grid[row][col] = player

    def is_full(self) -> bool:
        return all(cell is not None for row in self.grid for cell in row)

    def has_five_in_a_row(self, row: int, col: int, player: Player) -> bool:
        for delta_row, delta_col in ((1, 0), (0, 1), (1, 1), (1, -1)):
            if self._count_line(row, col, delta_row, delta_col, player) >= 5:
                return True
        return False

    def _count_line(self, row: int, col: int, delta_row: int, delta_col: int, player: Player) -> int:
        count = 1
        count += self._count_direction(row, col, delta_row, delta_col, player)
        count += self._count_direction(row, col, -delta_row, -delta_col, player)
        return count

    def _count_direction(self, row: int, col: int, delta_row: int, delta_col: int, player: Player) -> int:
        count = 0
        current_row = row + delta_row
        current_col = col + delta_col
        while self.in_bounds(current_row, current_col) and self.grid[current_row][current_col] is player:
            count += 1
            current_row += delta_row
            current_col += delta_col
        return count

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

    def play(self, row: int, col: int) -> Move:
        if self.finished:
            raise ValueError("Game is already finished.")

        player = self.current_player
        self.board.place(player, row, col)
        move = Move(row=row, col=col, player=player)
        self.last_move = move

        if self.board.has_five_in_a_row(row, col, player):
            self.winner = player
            self.finished = True
            return move

        if self.board.is_full():
            self.draw = True
            self.finished = True
            return move

        self.current_player = self.current_player.other()
        return move

    def status_text(self) -> str:
        if self.winner is not None:
            return f"{self.winner.label} wins."
        if self.draw:
            return "Draw game."
        return f"{self.current_player.label} to move."

    def to_snapshot(self) -> dict[str, object]:
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
        )
