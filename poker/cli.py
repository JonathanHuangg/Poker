"""Terminal interface for heads-up No-Limit Hold'em.

Interactive mode: you play against the computer, hand after hand, until
one side runs out of chips. Auto mode (`--auto N`) plays N hands with the
computer strategy on both sides, which is how the game is verified
without a human at the keyboard.
"""

from __future__ import annotations

import argparse
import random
import sys

from .ai import choose_action
from .cards import format_cards
from .game import Game

ACTIONS_HELP = (
    "Actions: [f]old  [c]heck/call  [r]aise to <amount>  [a]ll-in  [q]uit"
)


def _clear() -> None:
    print("\033[2J\033[H", end="")


def _show_table(game: Game, reveal_villain: bool = False) -> None:
    hero, villain = game.players
    villain_cards = (
        format_cards(villain.hole) if reveal_villain else "?? ??"
    )
    print(f"Hand #{game.hand_number}  |  Blinds {game.small_blind}/{game.big_blind}")
    print(f"Pot: {game.pot + hero.bet + villain.bet}")
    print(f"CPU: {villain.stack} chips  |  cards: {villain_cards}"
          + (f"  |  bet: {villain.bet}" if villain.bet else ""))
    print(f"Board: {format_cards(game.community) if game.community else '(none yet)'}")
    print(f"You: {hero.stack} chips  |  cards: {format_cards(hero.hole)}"
          + (f"  |  bet: {hero.bet}" if hero.bet else ""))
    print()


def _describe_action(game: Game, idx: int, action: tuple) -> str:
    name = game.players[idx].name
    kind, amount = action[0], action[1] if len(action) > 1 else None
    to_call = game.amount_to_call(idx)
    if kind == "fold":
        return f"{name} folds."
    if kind == "check":
        return f"{name} checks."
    if kind == "call":
        return f"{name} calls {min(to_call, game.players[idx].stack)}."
    if kind == "raise":
        return f"{name} raises to {amount}."
    return f"{name} goes all-in ({game.players[idx].stack} more)."


def _read_action(game: Game) -> tuple | None:
    """Prompt until the player enters a legal action. None means quit."""
    legal = {a[0]: a for a in game.legal_actions(0)}
    to_call = game.amount_to_call(0)
    while True:
        print(ACTIONS_HELP)
        if to_call:
            print(f"To call: {to_call}. Your stack: {game.players[0].stack}.")
        try:
            raw = input("Your move: ").strip().lower()
        except EOFError:
            return None  # piped input ran out: quit cleanly
        if raw in ("q", "quit", "exit"):
            return None
        if raw in ("f", "fold") and "fold" in legal:
            return ("fold", None)
        if raw in ("c", "check", "call"):
            if "check" in legal:
                return ("check", None)
            if "call" in legal:
                return ("call", None)
        if raw in ("a", "all-in", "allin") and (
            "raise" in legal or "all-in" in legal
        ):
            return ("all-in", None)
        parts = raw.replace("=", " ").split()
        if parts and parts[0] in ("r", "raise", "bet", "b"):
            if len(parts) == 2 and parts[1].isdigit():
                amount = int(parts[1])
                if "raise" in legal:
                    lo, hi = legal["raise"][1], legal["raise"][2]
                    if lo <= amount <= hi:
                        return ("raise", amount)
                    print(f"Raise must be to between {lo} and {hi}.")
                    continue
                if "all-in" in legal and amount >= legal["all-in"][1]:
                    return ("all-in", None)
            print("Usage: r <amount>, e.g. r 40 to raise to 40 total.")
            continue
        print("That is not a legal move right now. Try again.")


def _play_hand_interactive(game: Game, rng: random.Random) -> bool:
    """Play one hand with a human hero. Returns False if the user quits."""
    game.start_hand()
    _clear()
    print("New hand. You have the button." if game.button == 0
          else "New hand. CPU has the button.")
    while not game.hand_over:
        _show_table(game)
        if game.current == 0:
            action = _read_action(game)
            if action is None:
                print("Quitting. Thanks for playing.")
                return False
            print(_describe_action(game, 0, action))
            game.apply_action(0, action[0], action[1])
        else:
            action = choose_action(game, 1, rng)
            print(_describe_action(game, 1, action))
            game.apply_action(1, action[0], action[1])
        print()
    _show_table(game, reveal_villain=True)
    print(game.result_text)
    print(f"Stacks: You {game.players[0].stack}, CPU {game.players[1].stack}")
    print()
    return True


def play_interactive(game: Game, rng: random.Random) -> None:
    """Play hands until someone is broke or the user quits."""
    print("Welcome to Poker: heads-up No-Limit Texas Hold'em.")
    print(f"You start with {game.starting_stack} chips. "
          f"Blinds are {game.small_blind}/{game.big_blind}.")
    print()
    while game.match_over() is None:
        if not _play_hand_interactive(game, rng):
            return
        winner = game.match_over()
        if winner is not None:
            break
        try:
            answer = input("Play another hand? [Y/n] ").strip().lower()
        except EOFError:
            print("Quitting. Thanks for playing.")
            return
        if answer in ("n", "no", "q", "quit"):
            print("Quitting. Thanks for playing.")
            return
    winner = game.match_over()
    if winner is not None:
        print(f"{game.players[winner].name} wins the match.")
    print(f"Final stacks: You {game.players[0].stack}, "
          f"CPU {game.players[1].stack}.")


def play_auto(game: Game, hands: int, rng: random.Random) -> dict:
    """Play `hands` hands with the AI on both sides. Returns a summary."""
    stats = {
        "hands": 0,
        "hero_wins": 0,
        "villain_wins": 0,
        "splits": 0,
        "folds": 0,
        "showdowns": 0,
    }

    def total_chips(game: Game) -> int:
        return sum(game.stacks()) + game.pot + sum(p.bet for p in game.players)

    for _ in range(hands):
        if game.match_over() is not None:
            # Rebuy both players so the run can continue.
            game.players[0].stack = game.starting_stack
            game.players[1].stack = game.starting_stack
        game.start_hand()
        total_before = total_chips(game)  # blinds are posted in start_hand
        while not game.hand_over:
            idx = game.current
            action = choose_action(game, idx, rng)
            game.apply_action(idx, action[0], action[1])
        total_after = total_chips(game)
        assert total_after == total_before, (
            f"chips leaked in hand {game.hand_number}: "
            f"{total_before} -> {total_after}"
        )
        stats["hands"] += 1
        if game.showdown_hands:
            stats["showdowns"] += 1
        else:
            stats["folds"] += 1
        if len(game.winners) > 1:
            stats["splits"] += 1
        elif game.winners[0] == 0:
            stats["hero_wins"] += 1
        else:
            stats["villain_wins"] += 1
    stats["final_stacks"] = game.stacks()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Heads-up No-Limit Texas Hold'em against the computer."
    )
    parser.add_argument("--auto", type=int, metavar="N",
                        help="play N hands automatically (AI on both sides)")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed for reproducible games")
    parser.add_argument("--stack", type=int, default=1000,
                        help="starting stack per player (default 1000)")
    parser.add_argument("--small-blind", type=int, default=5)
    parser.add_argument("--big-blind", type=int, default=10)
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    game = Game(
        small_blind=args.small_blind,
        big_blind=args.big_blind,
        starting_stack=args.stack,
        rng=rng,
    )
    if args.auto:
        stats = play_auto(game, args.auto, rng)
        print(f"Played {stats['hands']} hands: "
              f"hero {stats['hero_wins']} wins, "
              f"villain {stats['villain_wins']} wins, "
              f"{stats['splits']} splits, "
              f"{stats['showdowns']} showdowns, {stats['folds']} folds.")
        print(f"Final stacks: {stats['final_stacks']}.")
        return 0
    play_interactive(game, rng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
