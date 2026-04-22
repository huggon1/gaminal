from __future__ import annotations

import random
from collections import Counter
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
SEQUENCE_MAX_VALUE = RANK_ORDER["A"]


def create_shuffled_deck(seed: int | None = None) -> list[str]:
    deck = [f"{rank}{suit}" for rank in ("3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2") for suit in SUITS]
    deck.extend(["BJ", "RJ"])
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck


def card_rank(card: str) -> str:
    if card in ("BJ", "RJ"):
        return card
    return card[:-1]


def sort_cards(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda card: (RANK_ORDER[card_rank(card)], card))


def _is_consecutive(values: list[int]) -> bool:
    return all(current + 1 == following for current, following in zip(values, values[1:]))


def _sequence_values(ranks: list[str]) -> list[int]:
    values = [RANK_ORDER[rank] for rank in ranks]
    if not values or max(values) > SEQUENCE_MAX_VALUE:
        return []
    return values


def _sorted_ranks(counter: Counter[str]) -> list[str]:
    return sorted(counter, key=lambda rank: RANK_ORDER[rank])


@dataclass(frozen=True)
class CardPattern:
    kind: str
    primary_value: int
    length: int
    chain_length: int = 1


def analyze_play(cards: list[str]) -> CardPattern:
    if not cards:
        raise ValueError("At least one card is required.")

    ranks = [card_rank(card) for card in cards]
    counts = Counter(ranks)
    ordered_ranks = _sorted_ranks(counts)
    values = [RANK_ORDER[rank] for rank in ordered_ranks]
    length = len(cards)

    if length == 1:
        return CardPattern("single", values[0], length)

    if length == 2:
        if set(ranks) == {"BJ", "RJ"}:
            return CardPattern("rocket", RANK_ORDER["RJ"], length)
        if len(counts) == 1:
            return CardPattern("pair", values[0], length)
        raise ValueError("Invalid pair play.")

    if length == 3 and len(counts) == 1:
        return CardPattern("triple", values[0], length)

    if len(counts) == 1 and length == 4:
        return CardPattern("bomb", values[0], length)

    if sorted(counts.values()) == [1, 3]:
        triple_rank = next(rank for rank, count in counts.items() if count == 3)
        return CardPattern("triple_single", RANK_ORDER[triple_rank], length)

    if sorted(counts.values()) == [2, 3]:
        triple_rank = next(rank for rank, count in counts.items() if count == 3)
        return CardPattern("triple_pair", RANK_ORDER[triple_rank], length)

    if all(count == 1 for count in counts.values()) and length >= 5:
        straight_values = _sequence_values(ordered_ranks)
        if straight_values and _is_consecutive(straight_values):
            return CardPattern("straight", straight_values[0], length, chain_length=length)

    if all(count == 2 for count in counts.values()) and length >= 6:
        pair_values = _sequence_values(ordered_ranks)
        if pair_values and _is_consecutive(pair_values):
            return CardPattern("pair_straight", pair_values[0], length, chain_length=len(ordered_ranks))

    triple_ranks = [rank for rank, count in counts.items() if count == 3]
    triple_values = _sequence_values(sorted(triple_ranks, key=lambda rank: RANK_ORDER[rank]))
    if triple_values and len(triple_ranks) >= 2 and _is_consecutive(triple_values):
        chain_length = len(triple_ranks)
        triple_set = set(triple_ranks)
        remaining = Counter({rank: count for rank, count in counts.items() if rank not in triple_set})
        if not remaining and length == chain_length * 3:
            return CardPattern("airplane", triple_values[0], length, chain_length=chain_length)
        if sum(remaining.values()) == chain_length and length == chain_length * 4:
            return CardPattern("airplane_single", triple_values[0], length, chain_length=chain_length)
        if all(count == 2 for count in remaining.values()) and len(remaining) == chain_length and length == chain_length * 5:
            return CardPattern("airplane_pair", triple_values[0], length, chain_length=chain_length)

    if 4 in counts.values():
        quad_rank = next(rank for rank, count in counts.items() if count == 4)
        remaining_counts = sorted(count for rank, count in counts.items() if rank != quad_rank)
        if length == 6 and remaining_counts == [1, 1]:
            return CardPattern("four_two_single", RANK_ORDER[quad_rank], length)
        if length == 8 and remaining_counts == [2, 2]:
            return CardPattern("four_two_pair", RANK_ORDER[quad_rank], length)

    raise ValueError("Unsupported card combination.")


def compare_patterns(current: CardPattern, previous: CardPattern | None) -> bool:
    if previous is None:
        return True
    if current.kind == "rocket":
        return True
    if previous.kind == "rocket":
        return False
    if current.kind == "bomb" and previous.kind != "bomb":
        return True
    if current.kind != previous.kind:
        return False
    if current.length != previous.length:
        return False
    if current.chain_length != previous.chain_length:
        return False
    return current.primary_value > previous.primary_value


@dataclass
class DdzRoundState:
    hands: dict[int, list[str]]
    bottom_cards: list[str]
    phase: str = "bidding"
    current_turn: int = 1
    highest_bid: int = 0
    highest_bidder: int | None = None
    bids_made: int = 0
    landlord_seat: int | None = None
    last_play_cards: list[str] = field(default_factory=list)
    last_play_pattern: CardPattern | None = None
    last_play_seat: int | None = None
    winner_seat: int | None = None
    winner_side: str | None = None
    reveal_bottom: bool = False

    @classmethod
    def from_deck(cls, deck: list[str]) -> "DdzRoundState":
        if len(deck) != 54:
            raise ValueError("Dou dizhu deck must contain 54 cards.")
        hands = {
            1: sort_cards(deck[0:17]),
            2: sort_cards(deck[17:34]),
            3: sort_cards(deck[34:51]),
        }
        bottom = sort_cards(deck[51:54])
        return cls(hands=hands, bottom_cards=bottom)

    def bid(self, seat: int, amount: int) -> None:
        if self.phase != "bidding":
            raise ValueError("Bidding is not active.")
        if seat != self.current_turn:
            raise ValueError("It is not your turn to bid.")
        if amount not in (0, 1, 2, 3):
            raise ValueError("Bid must be 0, 1, 2, or 3.")
        if amount != 0 and amount <= self.highest_bid:
            raise ValueError("Bid must be higher than the current highest bid.")

        self.bids_made += 1
        if amount > self.highest_bid:
            self.highest_bid = amount
            self.highest_bidder = seat

        if amount == 3:
            self._assign_landlord(seat)
            return

        if self.bids_made >= 3:
            if self.highest_bidder is None:
                raise ValueError("No one bid for landlord.")
            self._assign_landlord(self.highest_bidder)
            return

        self.current_turn = self._next_seat(seat)

    def _assign_landlord(self, seat: int) -> None:
        self.landlord_seat = seat
        self.phase = "playing"
        self.reveal_bottom = True
        self.hands[seat] = sort_cards(self.hands[seat] + self.bottom_cards)
        self.current_turn = seat

    def play_cards(self, seat: int, cards: list[str]) -> CardPattern:
        if self.phase != "playing":
            raise ValueError("Cards can only be played during the round.")
        if seat != self.current_turn:
            raise ValueError("It is not your turn.")
        hand = list(self.hands[seat])
        for card in cards:
            if card not in hand:
                raise ValueError("Played cards must come from your hand.")
            hand.remove(card)

        pattern = analyze_play(cards)
        if not compare_patterns(pattern, self.last_play_pattern):
            raise ValueError("Played cards do not beat the current table.")

        self.hands[seat] = sort_cards(hand)
        self.last_play_cards = sort_cards(list(cards))
        self.last_play_pattern = pattern
        self.last_play_seat = seat

        if not self.hands[seat]:
            self.phase = "finished"
            self.winner_seat = seat
            self.winner_side = "landlord" if seat == self.landlord_seat else "farmers"
            self.current_turn = seat
            return pattern

        self.current_turn = self._next_seat(seat)
        return pattern

    def pass_turn(self, seat: int) -> None:
        if self.phase != "playing":
            raise ValueError("Pass is only available during the round.")
        if seat != self.current_turn:
            raise ValueError("It is not your turn.")
        if self.last_play_pattern is None or self.last_play_seat is None:
            raise ValueError("You cannot pass when leading the trick.")
        if seat == self.last_play_seat:
            raise ValueError("The trick leader must play.")

        next_turn = self._next_seat(seat)
        if next_turn == self.last_play_seat:
            self.last_play_cards = []
            self.last_play_pattern = None
            self.current_turn = next_turn
            return
        self.current_turn = next_turn

    def seat_snapshot(self, seat: int) -> dict[str, object]:
        return {
            "current_turn": self.current_turn,
            "highest_bid": self.highest_bid,
            "highest_bidder": self.highest_bidder,
            "landlord_seat": self.landlord_seat,
            "bottom_cards": list(self.bottom_cards) if self.reveal_bottom else [],
            "table_cards": list(self.last_play_cards),
            "table_seat": self.last_play_seat,
            "winner_seat": self.winner_seat,
            "winner_side": self.winner_side,
            "your_hand": list(self.hands[seat]),
            "hand_counts": {key: len(value) for key, value in self.hands.items()},
        }

    @staticmethod
    def _next_seat(seat: int) -> int:
        return 1 if seat == 3 else seat + 1
