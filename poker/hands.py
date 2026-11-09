"""Seven-card Texas Hold'em hand evaluation.

`evaluate` takes the seven cards available to a player (two hole cards
plus five community cards) and returns the best five-card hand, ranked so
that results compare directly: a higher result always beats a lower one,
and equal results mean a split pot.

Hand categories, strongest first:
    8  straight flush
    7  four of a kind
    6  full house
    5  flush
    4  straight
    3  three of a kind
    2  two pair
    1  one pair
    0  high card
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .cards import Card

CATEGORY_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}

STRAIGHT_FLUSH = 8
FOUR_OF_A_KIND = 7
FULL_HOUSE = 6
FLUSH = 5
STRAIGHT = 4
THREE_OF_A_KIND = 3
TWO_PAIR = 2
ONE_PAIR = 1
HIGH_CARD = 0


@dataclass(frozen=True)
class HandResult:
    """The best five-card hand found in a set of cards."""

    category: int
    tiebreak: tuple[int, ...]
    best_five: tuple[Card, ...]

    @property
    def name(self) -> str:
        return CATEGORY_NAMES[self.category]

    def rank_key(self) -> tuple[int, tuple[int, ...]]:
        """Sort key: higher wins, equal means a tie."""
        return (self.category, self.tiebreak)

    def __lt__(self, other: "HandResult") -> bool:
        return self.rank_key() < other.rank_key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandResult):
            return NotImplemented
        return self.rank_key() == other.rank_key()

    def describe(self) -> str:
        """Plain-language description, e.g. "Pair of Kings" or "Ace-high Flush"."""
        from .cards import RANK_LABELS

        label = RANK_LABELS
        plural = {
            2: "Twos", 3: "Threes", 4: "Fours", 5: "Fives", 6: "Sixes",
            7: "Sevens", 8: "Eights", 9: "Nines", 10: "Tens",
            11: "Jacks", 12: "Queens", 13: "Kings", 14: "Aces",
        }
        cat = self.category
        t = self.tiebreak
        if cat == STRAIGHT_FLUSH:
            high = "Ace" if t[0] == 14 else label[t[0]]
            return f"Straight Flush, {high}-high"
        if cat == FOUR_OF_A_KIND:
            return f"Four of a Kind, {plural[t[0]]}"
        if cat == FULL_HOUSE:
            return f"Full House, {plural[t[0]]} full of {plural[t[1]]}"
        if cat == FLUSH:
            return f"Flush, {label[t[0]]}-high"
        if cat == STRAIGHT:
            high = "Ace" if t[0] == 14 else label[t[0]]
            return f"Straight, {high}-high"
        if cat == THREE_OF_A_KIND:
            return f"Three of a Kind, {plural[t[0]]}"
        if cat == TWO_PAIR:
            return f"Two Pair, {plural[t[0]]} and {plural[t[1]]}"
        if cat == ONE_PAIR:
            return f"Pair of {plural[t[0]]}"
        return f"{label[t[0]]}-high"


def _straight_high(ranks: list[int]) -> int | None:
    """Highest card of a straight in these ranks, or None.

    The wheel (A-2-3-4-5) counts as a 5-high straight.
    """
    unique = sorted(set(ranks), reverse=True)
    if 14 in unique:
        unique.append(1)  # Ace can play low for the wheel.
    for i in range(len(unique) - 4):
        window = unique[i : i + 5]
        if window[0] - window[4] == 4:
            return window[0]
    return None


def _evaluate_five(cards: tuple[Card, ...]) -> HandResult:
    ranks = sorted((c.rank for c in cards), reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)

    counts: dict[int, int] = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1
    # Groups sorted by count desc, then rank desc: quads, trips, pairs first.
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)

    if is_flush and straight_high is not None:
        return HandResult(STRAIGHT_FLUSH, (straight_high,), cards)
    if groups[0][1] == 4:
        kicker = max(rank for rank, count in counts.items() if count != 4)
        return HandResult(FOUR_OF_A_KIND, (groups[0][0], kicker), cards)
    if groups[0][1] == 3 and groups[1][1] == 2:
        return HandResult(FULL_HOUSE, (groups[0][0], groups[1][0]), cards)
    if is_flush:
        return HandResult(FLUSH, tuple(ranks), cards)
    if straight_high is not None:
        return HandResult(STRAIGHT, (straight_high,), cards)
    if groups[0][1] == 3:
        kickers = tuple(
            rank for rank, count in sorted(counts.items(), reverse=True)
            if count == 1
        )
        return HandResult(THREE_OF_A_KIND, (groups[0][0],) + kickers, cards)
    if groups[0][1] == 2 and groups[1][1] == 2:
        pairs = sorted((groups[0][0], groups[1][0]), reverse=True)
        kicker = max(rank for rank, count in counts.items() if count == 1)
        return HandResult(TWO_PAIR, (pairs[0], pairs[1], kicker), cards)
    if groups[0][1] == 2:
        kickers = tuple(
            rank for rank, count in sorted(counts.items(), reverse=True)
            if count == 1
        )
        return HandResult(ONE_PAIR, (groups[0][0],) + kickers, cards)
    return HandResult(HIGH_CARD, tuple(ranks), cards)


def evaluate(cards) -> HandResult:
    """Best five-card hand out of five to seven cards."""
    cards = tuple(cards)
    if len(cards) < 5 or len(cards) > 7:
        raise ValueError("evaluation needs 5 to 7 cards")
    if len(set(cards)) != len(cards):
        raise ValueError("duplicate cards in hand")
    return max(_evaluate_five(five) for five in combinations(cards, 5))
