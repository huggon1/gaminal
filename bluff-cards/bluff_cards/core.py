from __future__ import annotations

import random
from dataclasses import dataclass, field

RANK_ORDER = {
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
    "2": 15,
    "BJ": 16,
    "RJ": 17,
}

SUITS = ("S", "H", "C", "D")
TARGET_SEQUENCE = ("A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2")
DEFAULT_LIVES = 3


def create_shuffled_deck(seed: int | None = None) -> list[str]:
    deck = [f"{rank}{suit}" for rank in ("3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2") for suit in SUITS]
    deck.extend(["BJ", "RJ"])
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck


def sort_cards(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda card: (RANK_ORDER[card_rank(card)], card))


def card_rank(card: str) -> str:
    if card in ("BJ", "RJ"):
        return card
    return card[:-1]


def is_truthful_claim(cards: list[str], target_rank: str) -> bool:
    return all(card_rank(card) in {target_rank, "BJ", "RJ"} for card in cards)


@dataclass(frozen=True)
class BluffClaim:
    seat: int
    target_rank: str
    claimed_count: int
    actual_cards: list[str]


@dataclass(frozen=True)
class BluffRevealResult:
    challenged_seat: int
    challenger_seat: int
    actual_cards: list[str]
    truthful: bool
    loser_seat: int
    winner_seat: int
    loser_lives: int
    loser_eliminated: bool


@dataclass
class BluffRoundState:
    hands: dict[int, list[str]]
    lives: dict[int, int]
    target_index: int = 0
    current_turn: int = 1
    phase: str = "in_round"
    last_claim: BluffClaim | None = None
    winner_seat: int | None = None
    discard_pile: list[str] = field(default_factory=list)

    @classmethod
    def from_deck(cls, deck: list[str], player_count: int, lives: int = DEFAULT_LIVES) -> "BluffRoundState":
        if player_count < 2 or player_count > 4:
            raise ValueError("Player count must be between 2 and 4.")
        cards_per_player = len(deck) // player_count
        hands: dict[int, list[str]] = {}
        index = 0
        for seat in range(1, player_count + 1):
            hands[seat] = sort_cards(deck[index : index + cards_per_player])
            index += cards_per_player
        discard = sort_cards(deck[index:])
        return cls(
            hands=hands,
            lives={seat: lives for seat in hands},
            target_index=0,
            current_turn=1,
            phase="in_round",
            discard_pile=discard,
        )

    @property
    def target_rank(self) -> str:
        return TARGET_SEQUENCE[self.target_index]

    def active_seats(self) -> list[int]:
        return [seat for seat in sorted(self.hands) if self.lives[seat] > 0]

    def play_claim(self, seat: int, actual_cards: list[str], claimed_count: int) -> BluffClaim:
        if self.phase != "in_round":
            raise ValueError("Round is not active.")
        if seat != self.current_turn:
            raise ValueError("It is not your turn.")
        if claimed_count < 1 or claimed_count > 3:
            raise ValueError("Claimed count must be between 1 and 3.")
        if len(actual_cards) < 1 or len(actual_cards) > 3:
            raise ValueError("You must play between 1 and 3 cards.")
        if len(actual_cards) != claimed_count:
            raise ValueError("Actual cards must match the claimed count in the first version.")
        if self.last_claim is not None and not self.hands[self.last_claim.seat]:
            raise ValueError("The previous empty-hand claim must be challenged or accepted.")

        hand = list(self.hands[seat])
        for card in actual_cards:
            if card not in hand:
                raise ValueError("Played cards must come from your hand.")
            hand.remove(card)
        self.hands[seat] = sort_cards(hand)
        claim = BluffClaim(
            seat=seat,
            target_rank=self.target_rank,
            claimed_count=claimed_count,
            actual_cards=sort_cards(list(actual_cards)),
        )
        self.last_claim = claim
        self.current_turn = self._next_active_seat(seat)
        return claim

    def challenge(self, challenger_seat: int) -> BluffRevealResult:
        if self.phase != "in_round":
            raise ValueError("Round is not active.")
        if self.last_claim is None:
            raise ValueError("There is no claim to challenge.")
        if challenger_seat != self.current_turn:
            raise ValueError("Only the next active player may challenge.")
        if challenger_seat == self.last_claim.seat:
            raise ValueError("You cannot challenge your own claim.")

        truthful = is_truthful_claim(self.last_claim.actual_cards, self.last_claim.target_rank)
        loser_seat = challenger_seat if truthful else self.last_claim.seat
        winner_seat = self.last_claim.seat if truthful else challenger_seat
        self.lives[loser_seat] = max(0, self.lives[loser_seat] - 1)
        loser_eliminated = self.lives[loser_seat] == 0

        result = BluffRevealResult(
            challenged_seat=self.last_claim.seat,
            challenger_seat=challenger_seat,
            actual_cards=list(self.last_claim.actual_cards),
            truthful=truthful,
            loser_seat=loser_seat,
            winner_seat=winner_seat,
            loser_lives=self.lives[loser_seat],
            loser_eliminated=loser_eliminated,
        )

        if truthful and not self.hands[self.last_claim.seat]:
            self.phase = "finished"
            self.winner_seat = self.last_claim.seat
            self.last_claim = None
            return result

        if len(self.active_seats()) == 1:
            self.phase = "finished"
            self.winner_seat = self.active_seats()[0]
            self.last_claim = None
            return result

        self.last_claim = None
        self._advance_target()
        self.current_turn = winner_seat if self.lives[winner_seat] > 0 else self._next_active_seat(winner_seat)
        return result

    def accept(self, seat: int) -> int:
        if self.phase != "in_round":
            raise ValueError("Round is not active.")
        if self.last_claim is None:
            raise ValueError("There is no claim to accept.")
        if seat != self.current_turn:
            raise ValueError("Only the next active player may accept.")
        if self.hands[self.last_claim.seat]:
            raise ValueError("Accept is only available when the claimer has emptied their hand.")

        self.phase = "finished"
        self.winner_seat = self.last_claim.seat
        self.last_claim = None
        return self.winner_seat

    def seat_snapshot(self, seat: int) -> dict[str, object]:
        return {
            "current_turn": self.current_turn,
            "target_rank": self.target_rank,
            "last_claim": None
            if self.last_claim is None
            else {
                "seat": self.last_claim.seat,
                "target_rank": self.last_claim.target_rank,
                "claimed_count": self.last_claim.claimed_count,
            },
            "winner_seat": self.winner_seat,
            "your_hand": list(self.hands[seat]),
            "lives": dict(self.lives),
            "discard_count": len(self.discard_pile),
        }

    def _advance_target(self) -> None:
        self.target_index = (self.target_index + 1) % len(TARGET_SEQUENCE)

    def _next_active_seat(self, seat: int) -> int:
        active = self.active_seats()
        if not active:
            raise ValueError("No active seats remaining.")
        ordered = [active_seat for active_seat in active if active_seat > seat]
        if ordered:
            return ordered[0]
        return active[0]
