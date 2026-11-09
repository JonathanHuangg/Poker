"""Computer opponent for heads-up No-Limit Hold'em.

The strategy is deliberately simple and readable: estimate hand strength,
compare the price of calling with the pot odds, and bet strong hands,
check or call medium ones, and fold weak ones. A small random bluff keeps
it from being fully predictable. The random source is injected so games
are reproducible with a seed.
"""

from __future__ import annotations

import random

from .cards import Card
from .game import Game
from .hands import evaluate


def _preflop_strength(hole: list[Card]) -> float:
    """Rough 0-1 strength of two hole cards before the flop."""
    a, b = sorted((c.rank for c in hole), reverse=True)
    suited = hole[0].suit == hole[1].suit
    if a == b:  # pocket pair
        return 0.45 + a / 40.0
    strength = (a + b) / 28.0
    if suited:
        strength += 0.05
    if a - b == 1:
        strength += 0.04
    if a == 14:
        strength += 0.08
    return min(strength, 0.95)


def _draws(hole: list[Card], community: list[Card]) -> int:
    """Count outs-ish: flush draws and open-ended straight draws."""
    cards = hole + community
    draws = 0
    for suit in ("spades", "hearts", "diamonds", "clubs"):
        if sum(1 for c in cards if c.suit == suit) == 4:
            draws += 9
    ranks = {c.rank for c in cards}
    if 14 in ranks:
        ranks.add(1)
    for low in range(1, 11):
        window = {low, low + 1, low + 2, low + 3, low + 4}
        if len(window & ranks) == 4:
            draws += 8
    return draws


def hand_strength(game: Game, idx: int) -> float:
    """Rough 0-1 strength of a player's current hand."""
    player = game.players[idx]
    if game.street == "preflop":
        return _preflop_strength(player.hole)
    hand = evaluate(player.hole + game.community)
    # Category dominates; kickers nudge within a category.
    strength = hand.category / 8.0
    strength += (hand.tiebreak[0] / 14.0) * 0.08
    draws = _draws(player.hole, game.community)
    strength += min(draws, 12) / 12.0 * 0.12
    return min(strength, 0.99)


def choose_action(game: Game, idx: int, rng: random.Random) -> tuple:
    """Pick a legal action for the player at `idx`.

    Returns an (action, amount) pair matching `Game.apply_action`.
    """
    legal = {a[0]: a for a in game.legal_actions(idx)}
    if not legal:
        raise RuntimeError("no legal actions for AI player")
    can_raise = "raise" in legal or "all-in" in legal
    player = game.players[idx]
    to_call = game.amount_to_call(idx)
    pot = game.pot + player.bet + game.players[1 - idx].bet
    strength = hand_strength(game, idx)

    # Price of calling as a fraction of what we would win.
    pot_odds = to_call / (pot + to_call) if to_call else 0.0

    if "raise" in legal or "all-in" in legal:
        min_raise = legal["raise"][1] if "raise" in legal else None
        max_raise = legal["raise"][2] if "raise" in legal else None
    else:
        min_raise = max_raise = None

    def raise_to(amount: int) -> tuple:
        if min_raise is not None:
            return ("raise", max(min_raise, min(amount, max_raise)))
        return ("all-in", None)

    if to_call == 0:
        # No bet to face: bet strong hands and draws, check the rest.
        if strength > 0.75 or rng.random() < 0.06:
            if can_raise:
                size = max(game.big_blind, int(pot * 0.6))
                return raise_to(player.bet + size)
        if strength > 0.55 and rng.random() < 0.5:
            if can_raise:
                size = max(game.big_blind, int(pot * 0.4))
                return raise_to(player.bet + size)
        return ("check", None)

    if strength > 0.8:
        # Strong: raise for value, sometimes just call to trap.
        if can_raise and rng.random() < 0.7:
            size = max(game.big_blind, int(pot * 0.75))
            return raise_to(player.bet + to_call + size)
        return ("call", None)
    if strength > pot_odds + 0.15:
        # Good enough price to continue.
        if can_raise and strength > 0.65 and rng.random() < 0.3:
            size = max(game.big_blind, int(pot * 0.5))
            return raise_to(player.bet + to_call + size)
        return ("call", None)
    if can_raise and rng.random() < 0.05:
        # Occasional bluff raise.
        size = max(game.big_blind, int(pot * 0.5))
        return raise_to(player.bet + to_call + size)
    return ("fold", None)
