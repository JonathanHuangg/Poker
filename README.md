# Poker

Heads-up No-Limit Texas Hold'em against the computer, played in the
terminal. You start with 1000 chips, blinds are 5/10, and hands keep
coming until one side runs out of chips.

## How to play

Requires Python 3.10 or newer. No third party packages are needed.

```sh
python main.py
```

You will see your two hole cards, the board, the pot, and both chip
stacks. The computer's cards stay hidden until showdown. On your turn,
type one of:

| Input       | Meaning                                  |
| ----------- | ---------------------------------------- |
| `f`         | Fold                                     |
| `c`         | Check, or call the current bet           |
| `r <amount>`| Raise to `<amount>` total, e.g. `r 40`   |
| `a`         | Go all-in                                |
| `q`         | Quit                                     |

Illegal moves are rejected with an explanation and you get to try
again. After each hand you can choose to keep playing or stop.

Options:

```sh
python main.py --seed 42            # reproducible deals and opponent play
python main.py --stack 500          # shorter match, 500 chips each
python main.py --auto 100           # watch the computer play 100 hands
python main.py --auto 100 --seed 7  # same 100 hands every time
```

## Rules implemented

* Standard heads-up structure: the button posts the small blind, acts
  first before the flop, and acts last after it. The button alternates
  every hand.
* Full betting rounds on the flop, turn, and river, with check, call,
  fold, bet, raise, and all-in.
* Minimum raise rules: a raise must be at least the big blind, and a
  re-raise at least the size of the previous raise. An all-in for less
  than a full raise does not reopen betting for the player who already
  acted.
* A burn card before the flop, turn, and river, as in a live game.
* If both players are all-in, the remaining streets are dealt out with
  no further betting.
* Showdown picks the best five-card hand out of seven, across all nine
  hand categories from high card to straight flush, including the wheel
  straight (A-2-3-4-5). An exact tie splits the pot, with an odd chip
  going to the button. A player can only win what the opponent matched,
  so unmatched chips from a short all-in are returned.
* Chip counts are conserved: every chip in play is always in a stack,
  in a bet, or in the pot.

## How it is built

The code is split by responsibility so the rules can be tested without
a terminal:

* `poker/cards.py` - cards, deck, shuffling, and burn cards.
* `poker/hands.py` - seven-card hand evaluation and comparison.
* `poker/game.py` - the game engine: blinds, betting rounds, streets,
  showdown, and pot awards. No input or output lives here.
* `poker/ai.py` - the computer opponent. It estimates hand strength
  from made hands and draws, weighs the price of calling against the
  pot odds, and bluffs occasionally.
* `poker/cli.py` - the terminal interface and the `--auto` self-play
  mode used for verification.
* `tests/` - unit and end-to-end tests.

Run the tests with:

```sh
python -m unittest discover -s tests -t .
```

## What is not done

* There is no multiplayer or networking. The opponent is a local
  computer player, and there is no way to play against another person.
* There is no real-money play and no account or persistence. Chips are
  play money, and stacks reset when you quit.
* There is no graphical interface, only the terminal.
* The computer opponent is a simple heuristic, not a strong player. It
  plays sensibly but it does not adapt to how you play, and it can be
  beaten.
* Hand history, statistics across sessions, and configurable opponent
  difficulty are not implemented.

## History

The first version of this repo dealt two hands and printed the
opponent's cards face up, with betting and winner determination left
as comments. This version keeps the same idea, heads-up Hold'em in a
single Python project, and finishes it: real betting, a real opponent,
real showdowns, and tests that play the game.
