"""Tests for the heads-up game engine: blinds, betting, showdown, pots."""

import random
import unittest

from poker.cards import parse_card
from poker.game import Game


def make_game(seed=1, stack=1000):
    return Game(starting_stack=stack, rng=random.Random(seed))


def set_hole(game, hero, villain):
    game.players[0].hole = [parse_card(c) for c in hero]
    game.players[1].hole = [parse_card(c) for c in villain]


def set_board(game, board):
    game.community = [parse_card(c) for c in board]


class TestBlindsAndDealing(unittest.TestCase):
    def test_blinds_posted_and_button_acts_first(self):
        game = make_game()
        game.start_hand()
        self.assertEqual(game.players[0].bet, 5)  # hero is button, small blind
        self.assertEqual(game.players[1].bet, 10)
        self.assertEqual(game.players[0].stack, 995)
        self.assertEqual(game.players[1].stack, 990)
        self.assertEqual(game.current, 0)
        self.assertEqual(len(game.players[0].hole), 2)
        self.assertEqual(len(game.players[1].hole), 2)
        all_cards = game.players[0].hole + game.players[1].hole
        self.assertEqual(len(set(all_cards)), 4)

    def test_button_alternates_each_hand(self):
        game = make_game()
        game.start_hand()
        self.assertEqual(game.button, 0)
        game.apply_action(0, "fold")
        game.start_hand()
        self.assertEqual(game.button, 1)
        self.assertEqual(game.players[1].bet, 5)

    def test_fold_awards_pot_to_other_player(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "fold")
        self.assertTrue(game.hand_over)
        self.assertEqual(game.players[1].stack, 1000 + 5)
        self.assertEqual(game.players[0].stack, 995)
        self.assertIn("folds", game.result_text)

    def test_illegal_actions_rejected(self):
        game = make_game()
        game.start_hand()
        with self.assertRaises(ValueError):
            game.apply_action(1, "check")  # not villain's turn
        with self.assertRaises(ValueError):
            game.apply_action(0, "check")  # bet to face preflop
        with self.assertRaises(ValueError):
            game.apply_action(0, "raise", 12)  # below min raise to 20

    def test_no_duplicate_cards_across_hand(self):
        game = make_game(seed=7)
        game.start_hand()
        seen = list(game.players[0].hole + game.players[1].hole)
        seen_community = 0
        while not game.hand_over:
            idx = game.current
            legal = {a[0]: a for a in game.legal_actions(idx)}
            if "check" in legal:
                game.apply_action(idx, "check")
            else:
                game.apply_action(idx, "call")
            seen += game.community[seen_community:]
            seen_community = len(game.community)
        self.assertEqual(len(set(seen)), len(seen))


class TestBettingRounds(unittest.TestCase):
    def test_call_and_check_ends_preflop(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "call")  # button calls 5
        self.assertEqual(game.current, 1)  # big blind still has the option
        game.apply_action(1, "check")
        self.assertEqual(game.street, "flop")
        self.assertEqual(len(game.community), 3)
        self.assertEqual(game.pot, 20)

    def test_raise_and_call(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "raise", 40)
        self.assertEqual(game.current_bet, 40)
        game.apply_action(1, "call")
        self.assertEqual(game.street, "flop")
        self.assertEqual(game.pot, 80)

    def test_min_raise_grows_with_each_raise(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "raise", 30)  # raise by 20
        legal = {a[0]: a for a in game.legal_actions(1)}
        self.assertEqual(legal["raise"][1], 50)  # must raise by at least 20

    def test_big_blind_can_raise_after_button_calls(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "call")
        legal = {a[0]: a for a in game.legal_actions(1)}
        self.assertIn("raise", legal)
        game.apply_action(1, "raise", 40)
        self.assertEqual(game.current, 0)

    def test_postflop_non_button_acts_first(self):
        game = make_game()
        game.start_hand()
        game.apply_action(0, "call")
        game.apply_action(1, "check")
        self.assertEqual(game.street, "flop")
        self.assertEqual(game.current, 1)

    def test_all_in_short_raise_does_not_reopen(self):
        # Hero's whole stack only reaches 18, less than the minimum raise
        # to 20, so the all-in is a short raise and cannot be re-raised.
        game = Game(starting_stack=18, rng=random.Random(3))
        game.start_hand()
        game.apply_action(0, "all-in")
        legal = {a[0]: a for a in game.legal_actions(1)}
        self.assertNotIn("raise", legal)
        self.assertIn("call", legal)
        game.apply_action(1, "call")
        self.assertTrue(game.hand_over)
        self.assertEqual(game.street, "showdown")

    def test_both_all_in_deals_out_board(self):
        game = Game(starting_stack=100, rng=random.Random(5))
        game.start_hand()
        game.apply_action(0, "raise", 100)
        game.apply_action(1, "call")
        self.assertTrue(game.hand_over)
        self.assertEqual(game.street, "showdown")
        self.assertEqual(len(game.community), 5)
        self.assertEqual(sum(game.stacks()), 200)

    def test_chips_conserved_across_betting_hand(self):
        game = make_game(seed=11)
        game.start_hand()
        total_before = (
            sum(game.stacks()) + game.pot + sum(p.bet for p in game.players)
        )
        while not game.hand_over:
            idx = game.current
            legal = {a[0]: a for a in game.legal_actions(idx)}
            if "raise" in legal:
                game.apply_action(idx, "raise", legal["raise"][1])
            elif "call" in legal:
                game.apply_action(idx, "call")
            else:
                game.apply_action(idx, "check")
        total_after = (
            sum(game.stacks()) + game.pot + sum(p.bet for p in game.players)
        )
        self.assertEqual(total_before, total_after)


class TestShowdown(unittest.TestCase):
    def test_fixed_board_showdown(self):
        game = make_game(seed=2)
        game.start_hand()
        # Rig the deck order by replacing the community after each deal.
        set_hole(game, ["As", "Ad"], ["Ks", "Kd"])
        board = [parse_card(c) for c in ["Qs", "Jd", "9h", "2c", "3d"]]
        while not game.hand_over:
            idx = game.current
            legal = {a[0]: a for a in game.legal_actions(idx)}
            if "check" in legal:
                game.apply_action(idx, "check")
            elif "call" in legal:
                game.apply_action(idx, "call")
            else:
                game.apply_action(idx, "fold")
            if game.street == "flop":
                game.community = board[:3]
            elif game.street == "turn":
                game.community = board[:4]
            elif game.street == "river":
                game.community = board[:5]
        self.assertEqual(game.winners, [0])
        self.assertIn("Pair of Aces", game.result_text)
        self.assertEqual(game.players[0].stack, 1010)
        self.assertEqual(game.players[1].stack, 990)

    def test_split_pot_on_identical_board_hand(self):
        game = make_game(seed=4)
        game.start_hand()
        set_hole(game, ["2s", "3d"], ["2h", "3c"])
        board = [parse_card(c) for c in ["As", "Kd", "Qh", "Jc", "10s"]]
        while not game.hand_over:
            idx = game.current
            legal = {a[0]: a for a in game.legal_actions(idx)}
            if "check" in legal:
                game.apply_action(idx, "check")
            elif "call" in legal:
                game.apply_action(idx, "call")
            else:
                game.apply_action(idx, "fold")
            if game.street == "flop":
                game.community = board[:3]
            elif game.street == "turn":
                game.community = board[:4]
            elif game.street == "river":
                game.community = board[:5]
        self.assertEqual(sorted(game.winners), [0, 1])
        self.assertEqual(game.players[0].stack, 1000)
        self.assertEqual(game.players[1].stack, 1000)
        self.assertIn("Split pot", game.result_text)

    def test_short_all_in_refunds_unmatched_chips(self):
        # Hero has 15 chips, villain 1000. Hero can only win what villain
        # matched, so villain's extra chips come back.
        game = Game(starting_stack=1000, rng=random.Random(9))
        game.players[0].stack = 15
        game.start_hand()
        # Hero (button, SB 5) has 10 left; shove all-in for 15 total.
        game.apply_action(0, "all-in")
        game.apply_action(1, "call")
        self.assertTrue(game.hand_over)
        # Pot was 30; winner takes 30, nobody loses chips they did not match.
        self.assertEqual(sum(game.stacks()), 1015)

    def test_match_ends_when_a_player_is_broke(self):
        game = Game(starting_stack=20, rng=random.Random(6))
        game.start_hand()
        game.apply_action(0, "raise", 20)
        game.apply_action(1, "call")
        self.assertIsNotNone(game.match_over())


if __name__ == "__main__":
    unittest.main()
