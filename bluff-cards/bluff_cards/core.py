from __future__ import annotations

import random
from dataclasses import dataclass, field

TABLE_RANKS = ("A", "K", "Q")
DEFAULT_LIVES = 3
MAX_PLAY_COUNT = 3
RANK_ORDER = {"Q": 12, "K": 13, "A": 14, "JOKER": 15}


def create_shuffled_deck(seed: int | None = None) -> list[str]:
    deck = [f"{rank}{index}" for rank in TABLE_RANKS for index in range(1, 7)]
    deck.extend(["JOKER1", "JOKER2"])
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck


def card_rank(card: str) -> str:
    if card.startswith("JOKER"):
        return "JOKER"
    return card[0]


def card_label(card: str) -> str:
    rank = card_rank(card)
    return "Joker" if rank == "JOKER" else rank


def sort_cards(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda card: (RANK_ORDER[card_rank(card)], card))


def is_truthful_claim(cards: list[str], table_rank: str) -> bool:
    return all(card_rank(card) in {table_rank, "JOKER"} for card in cards)


def choose_basic_claim(hand: list[str], table_rank: str) -> list[str]:
    if not hand:
        raise ValueError("Cannot choose a claim from an empty hand.")

    truthful_cards = [card for card in sort_cards(hand) if card_rank(card) in {table_rank, "JOKER"}]
    if truthful_cards:
        return truthful_cards[: min(MAX_PLAY_COUNT, len(truthful_cards))]

    bluff_cards = sort_cards(hand)[: min(MAX_PLAY_COUNT, len(hand))]
    return bluff_cards[:1] if len(bluff_cards) > 1 else bluff_cards


def should_basic_challenge(hand: list[str], table_rank: str, claimed_count: int, claimer_hand_count: int) -> bool:
    matching_cards = sum(1 for card in hand if card_rank(card) in {table_rank, "JOKER"})
    if claimer_hand_count == 0:
        return True
    if matching_cards == 0 and claimed_count >= 2:
        return True
    if matching_cards <= 1 and claimed_count == 3:
        return True
    return False


@dataclass(frozen=True)
class BluffClaim:
    seat: int
    table_rank: str
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
    next_table_rank: str | None


@dataclass
class BluffRoundState:
    hands: dict[int, list[str]]
    lives: dict[int, int]
    table_rank: str
    current_turn: int = 1
    phase: str = "in_round"
    last_claim: BluffClaim | None = None
    winner_seat: int | None = None
    discard_pile: list[str] = field(default_factory=list)

    @classmethod
    def from_deck(cls, deck: list[str], player_count: int, lives: int = DEFAULT_LIVES, table_rank: str | None = None) -> "BluffRoundState":
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
            table_rank=table_rank or random.choice(TABLE_RANKS),
            current_turn=1,
            phase="in_round",
            discard_pile=discard,
        )

    def active_seats(self) -> list[int]:
        return [seat for seat in sorted(self.hands) if self.lives[seat] > 0]

    def play_claim(self, seat: int, actual_cards: list[str]) -> BluffClaim:
        if self.phase != "in_round":
            raise ValueError("Round is not active.")
        if seat != self.current_turn:
            raise ValueError("It is not your turn.")
        if self.last_claim is not None and not self.hands[self.last_claim.seat]:
            raise ValueError("The previous final claim must be challenged.")
        if len(actual_cards) < 1 or len(actual_cards) > MAX_PLAY_COUNT:
            raise ValueError("You must play between 1 and 3 cards.")

        hand = list(self.hands[seat])
        for card in actual_cards:
            if card not in hand:
                raise ValueError("Played cards must come from your hand.")
            hand.remove(card)
        self.hands[seat] = sort_cards(hand)
        claim = BluffClaim(
            seat=seat,
            table_rank=self.table_rank,
            claimed_count=len(actual_cards),
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

        claim = self.last_claim
        truthful = is_truthful_claim(claim.actual_cards, claim.table_rank)
        loser_seat = challenger_seat if truthful else claim.seat
        winner_seat = claim.seat if truthful else challenger_seat
        self.lives[loser_seat] = max(0, self.lives[loser_seat] - 1)
        loser_eliminated = self.lives[loser_seat] == 0

        if truthful and not self.hands[claim.seat]:
            self.phase = "finished"
            self.winner_seat = claim.seat
            next_table_rank = None
        elif len(self.active_seats()) == 1:
            self.phase = "finished"
            self.winner_seat = self.active_seats()[0]
            next_table_rank = None
        else:
            self._redeal_for_next_round(starting_seat=winner_seat)
            next_table_rank = self.table_rank

        result = BluffRevealResult(
            challenged_seat=claim.seat,
            challenger_seat=challenger_seat,
            actual_cards=list(claim.actual_cards),
            truthful=truthful,
            loser_seat=loser_seat,
            winner_seat=winner_seat,
            loser_lives=self.lives[loser_seat],
            loser_eliminated=loser_eliminated,
            next_table_rank=next_table_rank,
        )
        if self.phase == "finished":
            self.last_claim = None
        return result

    def seat_snapshot(self, seat: int) -> dict[str, object]:
        return {
            "current_turn": self.current_turn,
            "table_rank": self.table_rank,
            "last_claim": None
            if self.last_claim is None
            else {
                "seat": self.last_claim.seat,
                "table_rank": self.last_claim.table_rank,
                "claimed_count": self.last_claim.claimed_count,
            },
            "winner_seat": self.winner_seat,
            "your_hand": list(self.hands[seat]),
            "lives": dict(self.lives),
            "discard_count": len(self.discard_pile),
        }

    def _redeal_for_next_round(self, starting_seat: int) -> None:
        active = self.active_seats()
        deck = create_shuffled_deck()
        cards_per_player = len(deck) // len(active)
        next_hands = {seat: [] for seat in self.hands}
        index = 0
        for seat in active:
            next_hands[seat] = sort_cards(deck[index : index + cards_per_player])
            index += cards_per_player
        self.hands = next_hands
        self.discard_pile = sort_cards(deck[index:])
        self.table_rank = random.choice(TABLE_RANKS)
        self.last_claim = None
        self.current_turn = starting_seat if self.lives[starting_seat] > 0 else self._next_active_seat(starting_seat)
        self.phase = "in_round"

    def _next_active_seat(self, seat: int) -> int:
        active = self.active_seats()
        if not active:
            raise ValueError("No active seats remaining.")
        ordered = [active_seat for active_seat in active if active_seat > seat]
        if ordered:
            return ordered[0]
        return active[0]
