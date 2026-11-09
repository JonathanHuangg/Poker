"""Cards and deck for Texas Hold'em.

A card is a (rank, suit) pair. Ranks run 2-14, where 11 is Jack, 12 is
Queen, 13 is King and 14 is Ace. Suits are the four standard suits.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

RANK_LABELS = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
    10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
}
SUITS = ("spades", "hearts", "diamonds", "clubs")
SUIT_SYMBOLS = {
    "spades": "\u2660",
    "hearts": "\u2665",
    "diamonds": "\u2666",
    "clubs": "\u2663",
}
NUM_CARDS = 52


@dataclass(frozen=True, order=True)
class Card:
    """A single playing card."""

    rank: int  # 2-14, 14 is Ace
    suit: str  # one of SUITS

    def __post_init__(self) -> None:
        if self.rank not in RANK_LABELS:
            raise ValueError(f"invalid rank: {self.rank}")
        if self.suit not in SUITS:
            raise ValueError(f"invalid suit: {self.suit}")

    def __str__(self) -> str:
        return f"{RANK_LABELS[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def __repr__(self) -> str:
        return f"Card({self.rank}, {self.suit!r})"


def parse_card(text: str) -> Card:
    """Parse a card from text like "As", "10h", "Kd" or "A of spades".

    Accepts rank labels 2-10, J, Q, K, A and suit letters s/h/d/c.
    """
    text = text.strip().lower()
    if " of " in text:
        rank_text, suit_text = text.split(" of ", 1)
        suit = suit_text.strip()
    else:
        rank_text, suit_text = text[:-1], text[-1]
        suit = {"s": "spades", "h": "hearts", "d": "diamonds", "c": "clubs"}.get(
            suit_text
        )
        if suit is None:
            raise ValueError(f"unknown suit in {text!r}")
    rank_text = rank_text.strip().upper()
    rank = {"J": 11, "Q": 12, "K": 13, "A": 14}.get(rank_text)
    if rank is None:
        rank = int(rank_text)
    return Card(rank, suit)


class Deck:
    """A standard 52-card deck, shuffled on creation."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANK_LABELS]
        self._rng.shuffle(self.cards)

    def deal(self) -> Card:
        """Deal the top card. Raises IndexError on an empty deck."""
        return self.cards.pop()

    def burn(self) -> Card:
        """Discard the top card, as done before the flop, turn and river."""
        return self.deal()

    def __len__(self) -> int:
        return len(self.cards)


def format_cards(cards) -> str:
    """Render cards as a space separated string, e.g. "A\u2660 K\u2665 10\u2666"."""
    return " ".join(str(card) for card in cards)
