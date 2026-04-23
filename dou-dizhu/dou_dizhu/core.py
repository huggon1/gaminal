from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

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


@dataclass(frozen=True)
class PlayContext:
    seat: int
    landlord_seat: int | None
    last_play_seat: int | None
    hand_counts: dict[int, int]


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


def _cards_by_rank(hand: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for card in sort_cards(list(hand)):
        grouped.setdefault(card_rank(card), []).append(card)
    return grouped


def _candidate_priority(cards: list[str], previous: CardPattern | None) -> tuple[int, int, int, int]:
    pattern = analyze_play(cards)
    bomb_penalty = 1 if pattern.kind in {"bomb", "rocket"} else 0
    if previous is None:
        lead_kind_rank = {
            "airplane_pair": 0,
            "airplane_single": 1,
            "airplane": 2,
            "pair_straight": 3,
            "straight": 4,
            "triple_pair": 5,
            "triple_single": 6,
            "triple": 7,
            "pair": 8,
            "single": 9,
            "four_two_pair": 10,
            "four_two_single": 11,
            "bomb": 12,
            "rocket": 13,
        }
        return (
            bomb_penalty,
            lead_kind_rank.get(pattern.kind, 99),
            -pattern.length,
            pattern.primary_value,
        )
    return (bomb_penalty, pattern.primary_value, pattern.length, pattern.chain_length)


def generate_legal_plays(hand: list[str], previous: CardPattern | None = None) -> list[list[str]]:
    if not hand:
        return []

    by_rank = _cards_by_rank(hand)
    ranks = _sorted_ranks(Counter(card_rank(card) for card in hand))
    candidates: dict[tuple[str, ...], list[str]] = {}

    def add(cards: list[str]) -> None:
        normalized = sort_cards(list(cards))
        try:
            pattern = analyze_play(normalized)
        except ValueError:
            return
        if compare_patterns(pattern, previous):
            candidates[tuple(normalized)] = normalized

    for rank in ranks:
        cards = by_rank[rank]
        add(cards[:1])
        if len(cards) >= 2:
            add(cards[:2])
        if len(cards) >= 3:
            add(cards[:3])
        if len(cards) == 4:
            add(cards[:4])

    if "BJ" in by_rank and "RJ" in by_rank:
        add(["BJ", "RJ"])

    playable_sequence_ranks = [rank for rank in ranks if RANK_ORDER[rank] <= SEQUENCE_MAX_VALUE]
    for start in range(len(playable_sequence_ranks)):
        for end in range(start + 5, len(playable_sequence_ranks) + 1):
            chain = playable_sequence_ranks[start:end]
            values = [RANK_ORDER[rank] for rank in chain]
            if not _is_consecutive(values):
                break
            add([by_rank[rank][0] for rank in chain])

    pair_ranks = [rank for rank in playable_sequence_ranks if len(by_rank[rank]) >= 2]
    for start in range(len(pair_ranks)):
        for end in range(start + 3, len(pair_ranks) + 1):
            chain = pair_ranks[start:end]
            values = [RANK_ORDER[rank] for rank in chain]
            if not _is_consecutive(values):
                break
            cards: list[str] = []
            for rank in chain:
                cards.extend(by_rank[rank][:2])
            add(cards)

    triple_ranks = [rank for rank in playable_sequence_ranks if len(by_rank[rank]) >= 3]
    for rank in triple_ranks:
        base = by_rank[rank][:3]
        add(base)
        for single_rank in ranks:
            if single_rank == rank:
                continue
            add(base + by_rank[single_rank][:1])
        for pair_rank in ranks:
            if pair_rank == rank or len(by_rank[pair_rank]) < 2:
                continue
            add(base + by_rank[pair_rank][:2])

    for start in range(len(triple_ranks)):
        for end in range(start + 2, len(triple_ranks) + 1):
            chain = triple_ranks[start:end]
            values = [RANK_ORDER[rank] for rank in chain]
            if not _is_consecutive(values):
                break
            chain_cards: list[str] = []
            for rank in chain:
                chain_cards.extend(by_rank[rank][:3])
            add(chain_cards)

            chain_set = set(chain)
            attachment_ranks = [rank for rank in ranks if rank not in chain_set]
            for single_combo in combinations(attachment_ranks, len(chain)):
                cards = list(chain_cards)
                for rank in single_combo:
                    cards.extend(by_rank[rank][:1])
                add(cards)
            pair_attachment_ranks = [rank for rank in attachment_ranks if len(by_rank[rank]) >= 2]
            for pair_combo in combinations(pair_attachment_ranks, len(chain)):
                cards = list(chain_cards)
                for rank in pair_combo:
                    cards.extend(by_rank[rank][:2])
                add(cards)

    for rank in ranks:
        if len(by_rank[rank]) != 4:
            continue
        quad = by_rank[rank][:4]
        remaining_ranks = [other for other in ranks if other != rank]
        for single_combo in combinations(remaining_ranks, 2):
            cards = list(quad)
            for single_rank in single_combo:
                cards.extend(by_rank[single_rank][:1])
            add(cards)
        pair_ranks_for_quad = [other for other in remaining_ranks if len(by_rank[other]) >= 2]
        for pair_combo in combinations(pair_ranks_for_quad, 2):
            cards = list(quad)
            for pair_rank in pair_combo:
                cards.extend(by_rank[pair_rank][:2])
            add(cards)

    return sorted(candidates.values(), key=lambda cards: _candidate_priority(cards, previous))


def _hand_group_count(hand: list[str]) -> int:
    return len(generate_legal_plays(hand, None)[:1]) if not hand else len(_cards_by_rank(hand))


def _is_teammate(context: PlayContext, other_seat: int | None) -> bool:
    if other_seat is None or context.landlord_seat is None:
        return False
    return (context.seat == context.landlord_seat) == (other_seat == context.landlord_seat)


def _remaining_hand_score(hand: list[str]) -> tuple[int, int, int]:
    counts = Counter(card_rank(card) for card in hand)
    group_count = len(counts)
    singles = sum(1 for count in counts.values() if count == 1)
    high_cards = sum(1 for rank in counts if RANK_ORDER[rank] >= RANK_ORDER["A"])
    return (group_count, singles, high_cards)


def _follow_play_score(cards: list[str], hand: list[str], context: PlayContext) -> tuple[int, int, int, int, int]:
    pattern = analyze_play(cards)
    remaining = list(hand)
    for card in cards:
        remaining.remove(card)
    groups, singles, high_cards = _remaining_hand_score(remaining)
    bombs_used = 1 if pattern.kind in {"bomb", "rocket"} else 0
    threat_seat = context.last_play_seat
    threat_cards = context.hand_counts.get(threat_seat, 99) if threat_seat is not None else 99
    aggressive = threat_seat is not None and not _is_teammate(context, threat_seat) and threat_cards <= 2
    finish_bonus = -20 if not remaining else 0
    if aggressive:
        return (bombs_used, finish_bonus, groups, singles, -pattern.primary_value)
    return (bombs_used, finish_bonus, groups, singles, high_cards + pattern.primary_value)


def _lead_play_score(cards: list[str], hand: list[str], context: PlayContext | None) -> tuple[int, int, int, int, int]:
    pattern = analyze_play(cards)
    remaining = list(hand)
    for card in cards:
        remaining.remove(card)
    groups, singles, high_cards = _remaining_hand_score(remaining)
    bomb_penalty = 3 if pattern.kind in {"bomb", "rocket"} and remaining else 0
    pattern_rank = {
        "airplane_pair": 0,
        "airplane_single": 1,
        "airplane": 2,
        "pair_straight": 3,
        "straight": 4,
        "triple_pair": 5,
        "triple_single": 6,
        "triple": 7,
        "pair": 8,
        "single": 9,
        "four_two_pair": 10,
        "four_two_single": 11,
        "bomb": 12,
        "rocket": 13,
    }.get(pattern.kind, 99)
    pressure_bonus = 0
    if context is not None:
        next_seat = 1 if context.seat == 3 else context.seat + 1
        if not _is_teammate(context, next_seat) and context.hand_counts.get(next_seat, 99) <= 2:
            pressure_bonus = -2 if pattern.kind not in {"single", "pair"} else 0
    return (bomb_penalty, groups, singles, pattern_rank + pressure_bonus, high_cards + pattern.primary_value)


def choose_basic_bid(hand: list[str], current_highest: int = 0) -> int:
    counts = Counter(card_rank(card) for card in hand)
    score = 0
    for rank, count in counts.items():
        value = RANK_ORDER[rank]
        if value >= RANK_ORDER["2"]:
            score += 2 + count
        elif value >= RANK_ORDER["A"]:
            score += 2
        elif value >= RANK_ORDER["K"]:
            score += 1
        if count == 4:
            score += 4
        elif count == 3:
            score += 2
    if {"BJ", "RJ"} <= set(counts):
        score += 4
    longest_pair_chain = max((count for count in counts.values() if count >= 2), default=0)
    triple_count = sum(1 for count in counts.values() if count >= 3)
    score += triple_count
    if longest_pair_chain >= 2:
        score += 1

    target_bid = 0
    if score >= 15:
        target_bid = 3
    elif score >= 11:
        target_bid = 2
    elif score >= 7:
        target_bid = 1

    if target_bid <= current_highest:
        return 0
    if current_highest == 2 and target_bid == 3:
        return 3
    if current_highest == 1 and target_bid >= 2:
        return 2 if target_bid == 2 else 3
    if current_highest == 0:
        return target_bid
    return 0


def choose_basic_play(
    hand: list[str],
    previous: CardPattern | None = None,
    *,
    context: PlayContext | None = None,
) -> list[str] | None:
    legal_plays = generate_legal_plays(hand, previous)
    if not legal_plays:
        return None
    if len(legal_plays) == 1:
        return legal_plays[0]

    winning = [cards for cards in legal_plays if len(cards) == len(hand)]
    if winning:
        return min(winning, key=lambda cards: _candidate_priority(cards, previous))

    if previous is not None and context is not None and _is_teammate(context, context.last_play_seat):
        teammate_cards_left = context.hand_counts.get(context.last_play_seat or -1, 99)
        if teammate_cards_left > 2:
            return None
        urgent_plays = [cards for cards in legal_plays if len(hand) - len(cards) <= 2]
        if urgent_plays:
            return min(urgent_plays, key=lambda cards: _follow_play_score(cards, hand, context))
        return None

    if previous is None:
        return min(legal_plays, key=lambda cards: _lead_play_score(cards, hand, context))

    non_bombs = [cards for cards in legal_plays if analyze_play(cards).kind not in {"bomb", "rocket"}]
    if context is not None and context.last_play_seat is not None:
        threat_cards = context.hand_counts.get(context.last_play_seat, 99)
        last_is_enemy = not _is_teammate(context, context.last_play_seat)
        if last_is_enemy and threat_cards > 2 and non_bombs:
            legal_plays = non_bombs
        elif not last_is_enemy and non_bombs:
            legal_plays = non_bombs
    elif non_bombs:
        legal_plays = non_bombs

    if context is None:
        return min(legal_plays, key=lambda cards: _candidate_priority(cards, previous))
    return min(legal_plays, key=lambda cards: _follow_play_score(cards, hand, context))


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
