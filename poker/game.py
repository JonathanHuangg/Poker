"""Heads-up No-Limit Texas Hold'em engine.

Two players, you versus the computer. No I/O lives here: the CLI and the
AI drive the game through `legal_actions` and `apply_action`, so the rules
can be tested without a terminal.

Rules implemented:
  * Button posts the small blind and acts first pre-flop, last after it.
  * Blinds are 5/10 by default, stacks 1000 by default.
  * A bet or raise must be at least the big blind, and a re-raise at least
    the size of the previous raise. An all-in for less than a full raise
    does not reopen betting for the player who already acted.
  * The flop, turn and river are each preceded by a burn card.
  * If both players are all-in, the remaining streets are dealt out with
    no further betting.
  * At showdown the best five-card hand from seven wins; an exact tie
    splits the pot, with an odd chip going to the button.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .cards import Deck, format_cards
from .hands import HandResult, evaluate

STREETS = ("preflop", "flop", "turn", "river", "showdown")


@dataclass
class Player:
    """One side of a heads-up hand."""

    name: str
    stack: int
    hole: list = field(default_factory=list)
    bet: int = 0  # chips committed on the current street
    committed: int = 0  # chips committed over the whole hand
    folded: bool = False

    @property
    def all_in(self) -> bool:
        return self.stack == 0

    @property
    def is_active(self) -> bool:
        return not self.folded and not self.all_in


class Game:
    """One hand of heads-up No-Limit Hold'em."""

    def __init__(
        self,
        small_blind: int = 5,
        big_blind: int = 10,
        starting_stack: int = 1000,
        hero_name: str = "You",
        villain_name: str = "CPU",
        rng: random.Random | None = None,
    ) -> None:
        if small_blind <= 0 or big_blind <= small_blind:
            raise ValueError("blinds must satisfy 0 < small blind < big blind")
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.starting_stack = starting_stack
        self.rng = rng or random.Random()
        self.players = [
            Player(hero_name, starting_stack),
            Player(villain_name, starting_stack),
        ]
        self.button = 0  # hero has the button on the first hand
        self.hand_number = 0
        self.deck = Deck(self.rng)
        self.community: list = []
        self.pot = 0
        self.street = "preflop"
        self.current = 0  # index of the player to act, or -1 when no action
        self.current_bet = 0
        self.min_raise = big_blind
        self.winners: list[int] = []
        self.showdown_hands: dict[int, HandResult] = {}
        self.hand_over = False
        self.result_text = ""
        self._acted: set[int] = set()
        self._raise_allowed = [True, True]
        self._started = False

    # -- hand setup -----------------------------------------------------

    def _post(self, player: Player, amount: int) -> int:
        posted = min(amount, player.stack)
        player.stack -= posted
        player.bet += posted
        player.committed += posted
        return posted

    def start_hand(self) -> None:
        """Shuffle, deal, post blinds and set the first player to act."""
        if self._started and not self.hand_over:
            raise RuntimeError("current hand is still in progress")
        for player in self.players:
            player.hole = []
            player.bet = 0
            player.committed = 0
            player.folded = False
        self.deck = Deck(self.rng)
        self.community = []
        self.pot = 0
        self.winners = []
        self.showdown_hands = {}
        self.hand_over = False
        self.result_text = ""
        self.street = "preflop"
        self.hand_number += 1
        if self.hand_number > 1:
            self.button = 1 - self.button

        button = self.players[self.button]
        big_blind_player = self.players[1 - self.button]
        self._post(button, self.small_blind)
        self._post(big_blind_player, self.big_blind)
        self.current_bet = self.big_blind
        self.min_raise = self.big_blind
        self._acted = set()
        self._raise_allowed = [True, True]

        for _ in range(2):  # deal one card to each player, button first
            for player in (button, big_blind_player):
                player.hole.append(self.deck.deal())

        self.current = self.button
        self._started = True
        if button.all_in or big_blind_player.all_in:
            self._deal_out_remaining()

    # -- actions ----------------------------------------------------------

    def amount_to_call(self, idx: int) -> int:
        return max(0, self.current_bet - self.players[idx].bet)

    def legal_actions(self, idx: int) -> list[tuple]:
        """Legal actions for a player as (action, ...) tuples.

        Returns ("fold",), ("check",), ("call", amount),
        ("raise", min_total, max_total) or ("all-in", total).
        "raise" means raise *to* the given total bet for the street.
        """
        if self.hand_over or idx != self.current:
            return []
        player = self.players[idx]
        to_call = self.amount_to_call(idx)
        actions: list[tuple] = [("fold",)]
        if to_call == 0:
            actions.append(("check",))
        else:
            actions.append(("call", min(to_call, player.stack)))
        if self._raise_allowed[idx] and player.stack > to_call:
            min_total = self.current_bet + self.min_raise
            max_total = player.bet + player.stack
            if max_total >= min_total:
                actions.append(("raise", min_total, max_total))
            elif max_total > self.current_bet:
                # Can only shove for less than a full raise.
                actions.append(("all-in", max_total))
        return actions

    def apply_action(self, idx: int, action: str, amount: int | None = None) -> None:
        """Apply a legal action for the player to act."""
        if self.hand_over:
            raise RuntimeError("hand is over")
        if idx != self.current:
            raise ValueError("it is not this player's turn")
        legal = {a[0] for a in self.legal_actions(idx)}
        if action not in legal:
            raise ValueError(f"illegal action {action!r} for {self.players[idx].name}")
        player = self.players[idx]
        other = self.players[1 - idx]

        if action == "fold":
            player.folded = True
            self._award_pot([1 - idx], showdown=False)
            return
        if action == "check":
            self._acted.add(idx)
        elif action == "call":
            call = min(self.amount_to_call(idx), player.stack)
            player.stack -= call
            player.bet += call
            player.committed += call
            self._acted.add(idx)
        elif action in ("raise", "all-in"):
            if action == "all-in":
                target = player.bet + player.stack
            elif amount is None:
                raise ValueError("raise needs a total amount")
            else:
                target = amount
            min_total, max_total = self.current_bet + self.min_raise, player.bet + player.stack
            if target < self.current_bet + self.min_raise and target != max_total:
                raise ValueError("raise is below the minimum")
            if target > max_total or target <= self.current_bet:
                raise ValueError("raise amount out of range")
            raise_size = target - self.current_bet
            added = target - player.bet
            player.stack -= added
            player.bet = target
            player.committed += added
            if raise_size >= self.min_raise:
                self.min_raise = raise_size
                self.current_bet = target
                self._acted = {idx}
                self._raise_allowed = [True, True]
            else:
                # Short all-in: does not reopen betting for the other player.
                self.current_bet = target
                self._acted.add(idx)
                self._raise_allowed[1 - idx] = False
        else:  # pragma: no cover - legal_actions only yields the above
            raise ValueError(f"unknown action {action!r}")

        self._advance()

    # -- street flow ------------------------------------------------------

    def _needs_to_act(self, idx: int) -> bool:
        player = self.players[idx]
        return (
            not player.folded
            and not player.all_in
            and (idx not in self._acted or player.bet < self.current_bet)
        )

    def _advance(self) -> None:
        """Move to the next player, or to the next street when betting ends."""
        for idx in (1 - self.current, self.current):
            if self._needs_to_act(idx):
                self.current = idx
                return
        self._end_street()

    def _collect_bets(self) -> None:
        for player in self.players:
            self.pot += player.bet
            player.bet = 0
        self.current_bet = 0
        self.min_raise = self.big_blind
        self._acted = set()
        self._raise_allowed = [True, True]

    def _end_street(self) -> None:
        self._collect_bets()
        if any(p.all_in for p in self.players):
            # Someone is all-in: deal the rest out with no more betting.
            self._deal_out_remaining()
            return
        next_street = {
            "preflop": "flop",
            "flop": "turn",
            "turn": "river",
            "river": "showdown",
        }[self.street]
        self.street = next_street
        if next_street == "flop":
            self.deck.burn()
            self.community = [self.deck.deal() for _ in range(3)]
        elif next_street in ("turn", "river"):
            self.deck.burn()
            self.community.append(self.deck.deal())
        elif next_street == "showdown":
            self._showdown()
            return
        # First to act after the flop is the non-button player.
        self.current = 1 - self.button
        if not self._needs_to_act(self.current):
            self._advance()

    def _deal_out_remaining(self) -> None:
        """Deal every street that is left, then go to showdown."""
        while self.street != "river":
            self._collect_bets()
            if self.street == "preflop":
                self.deck.burn()
                self.community = [self.deck.deal() for _ in range(3)]
                self.street = "flop"
            elif self.street == "flop":
                self.deck.burn()
                self.community.append(self.deck.deal())
                self.street = "turn"
            elif self.street == "turn":
                self.deck.burn()
                self.community.append(self.deck.deal())
                self.street = "river"
        self._collect_bets()
        self.street = "showdown"
        self.current = -1
        self._showdown()

    def _showdown(self) -> None:
        self.street = "showdown"
        self.current = -1
        active = [i for i, p in enumerate(self.players) if not p.folded]
        self.showdown_hands = {
            i: evaluate(self.players[i].hole + self.community) for i in active
        }
        best = max(result for result in self.showdown_hands.values())
        self.winners = [
            i for i, result in self.showdown_hands.items() if result == best
        ]
        self._award_pot(self.winners, showdown=True)

    def _award_pot(self, winners: list[int], showdown: bool) -> None:
        self.hand_over = True
        self.current = -1
        self.winners = list(winners)
        self._collect_bets()
        # A player can only win what the opponent matched. Any unmatched
        # chips (e.g. a bigger bet against a short all-in) go back to the
        # player who put them in before the pot is awarded.
        committed = [p.committed for p in self.players]
        matched = min(committed)
        main_pot = 2 * matched
        for idx, player in enumerate(self.players):
            excess = committed[idx] - matched
            if excess:
                player.stack += excess
                self.pot -= excess
        assert self.pot == main_pot, "pot does not match committed chips"
        if len(winners) == 1:
            winner = self.players[winners[0]]
            winner.stack += self.pot
            if showdown:
                hand = self.showdown_hands[winners[0]]
                self.result_text = (
                    f"{winner.name} wins {self.pot} with {hand.describe()} "
                    f"({format_cards(hand.best_five)})"
                )
            else:
                self.result_text = (
                    f"{self.players[1 - winners[0]].name} folds. "
                    f"{winner.name} wins {self.pot}."
                )
        else:
            share, odd = divmod(self.pot, len(winners))
            for idx in winners:
                self.players[idx].stack += share
            # Odd chip goes to the button.
            self.players[self.button].stack += odd
            names = " and ".join(self.players[i].name for i in winners)
            hand = self.showdown_hands[winners[0]]
            self.result_text = (
                f"Split pot: {names} each win {share} with {hand.describe()}."
            )
        self.pot = 0

    # -- helpers ----------------------------------------------------------

    def stacks(self) -> tuple[int, int]:
        return (self.players[0].stack, self.players[1].stack)

    def match_over(self) -> int | None:
        """Index of the match winner, or None while both players have chips."""
        if self.players[0].stack == 0:
            return 1
        if self.players[1].stack == 0:
            return 0
        return None
