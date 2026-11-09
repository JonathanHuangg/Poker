"""Tests for the seven-card hand evaluator."""

import unittest

from poker.cards import parse_card
from poker.hands import (
    FLUSH,
    FOUR_OF_A_KIND,
    FULL_HOUSE,
    HIGH_CARD,
    ONE_PAIR,
    STRAIGHT,
    STRAIGHT_FLUSH,
    THREE_OF_A_KIND,
    TWO_PAIR,
    evaluate,
)


def cards(*texts):
    return [parse_card(t) for t in texts]


class TestHandCategories(unittest.TestCase):
    def test_straight_flush_beats_four_of_a_kind(self):
        sf = evaluate(cards("9s", "8s", "7s", "6s", "5s", "2d", "3c"))
        quads = evaluate(cards("As", "Ad", "Ah", "Ac", "Ks", "2d", "3c"))
        self.assertEqual(sf.category, STRAIGHT_FLUSH)
        self.assertEqual(quads.category, FOUR_OF_A_KIND)
        self.assertGreater(sf, quads)

    def test_royal_flush_is_top_straight_flush(self):
        royal = evaluate(cards("As", "Ks", "Qs", "Js", "10s", "2d", "3c"))
        self.assertEqual(royal.category, STRAIGHT_FLUSH)
        self.assertEqual(royal.tiebreak, (14,))

    def test_four_of_a_kind_kicker(self):
        aces = evaluate(cards("As", "Ad", "Ah", "Ac", "Ks", "2d", "3c"))
        kings = evaluate(cards("Ks", "Kd", "Kh", "Kc", "As", "2d", "3c"))
        self.assertGreater(aces, kings)

    def test_full_house_uses_best_trips_then_pair(self):
        # Aces full of kings beats kings full of aces.
        a = evaluate(cards("As", "Ad", "Ah", "Ks", "Kd", "2c", "3d"))
        b = evaluate(cards("Ks", "Kd", "Kh", "As", "Ad", "2c", "3d"))
        self.assertEqual(a.category, FULL_HOUSE)
        self.assertGreater(a, b)

    def test_full_house_picks_best_five_of_seven(self):
        # Three pair plus trips available: best is aces full of kings.
        hand = evaluate(cards("As", "Ad", "Ah", "Ks", "Kd", "Qs", "Qd"))
        self.assertEqual(hand.category, FULL_HOUSE)
        self.assertEqual(hand.tiebreak, (14, 13))

    def test_flush_beats_straight(self):
        flush = evaluate(cards("As", "9s", "7s", "5s", "3s", "2d", "4c"))
        straight = evaluate(cards("9d", "8c", "7h", "6s", "5d", "2s", "3c"))
        self.assertEqual(flush.category, FLUSH)
        self.assertEqual(straight.category, STRAIGHT)
        self.assertGreater(flush, straight)

    def test_wheel_straight_counts_as_five_high(self):
        wheel = evaluate(cards("As", "2d", "3h", "4c", "5s", "Kd", "Qc"))
        self.assertEqual(wheel.category, STRAIGHT)
        self.assertEqual(wheel.tiebreak, (5,))
        six_high = evaluate(cards("6d", "5c", "4h", "3s", "2d", "Kd", "Qc"))
        self.assertGreater(six_high, wheel)

    def test_wheel_straight_flush(self):
        wheel_sf = evaluate(cards("As", "2s", "3s", "4s", "5s", "Kd", "Qc"))
        self.assertEqual(wheel_sf.category, STRAIGHT_FLUSH)
        self.assertEqual(wheel_sf.tiebreak, (5,))

    def test_three_of_a_kind(self):
        hand = evaluate(cards("9s", "9d", "9h", "Ks", "Qd", "2c", "3d"))
        self.assertEqual(hand.category, THREE_OF_A_KIND)
        self.assertEqual(hand.tiebreak, (9, 13, 12))

    def test_two_pair_kicker_decides(self):
        a = evaluate(cards("As", "Ad", "Ks", "Kd", "Qs", "2c", "3d"))
        b = evaluate(cards("As", "Ad", "Ks", "Kd", "Js", "2c", "3d"))
        self.assertEqual(a.category, TWO_PAIR)
        self.assertGreater(a, b)

    def test_one_pair_kickers_in_order(self):
        a = evaluate(cards("As", "Ad", "Ks", "Qd", "Js", "2c", "3d"))
        b = evaluate(cards("As", "Ad", "Ks", "Qd", "10s", "2c", "3d"))
        self.assertEqual(a.category, ONE_PAIR)
        self.assertGreater(a, b)

    def test_high_card(self):
        hand = evaluate(cards("As", "Kd", "9h", "7c", "5s", "2d", "3c"))
        self.assertEqual(hand.category, HIGH_CARD)
        self.assertEqual(hand.tiebreak, (14, 13, 9, 7, 5))

    def test_exact_tie(self):
        # Same best five from the board: both players play the board.
        a = evaluate(cards("2s", "3d", "As", "Kd", "Qh", "Jc", "10s"))
        b = evaluate(cards("2h", "3c", "As", "Kd", "Qh", "Jc", "10s"))
        self.assertEqual(a, b)

    def test_best_five_ignores_extra_cards(self):
        hand = evaluate(cards("As", "Ad", "Ks", "Kd", "Qs", "2c", "3d"))
        self.assertEqual(len(hand.best_five), 5)
        self.assertEqual(hand.category, TWO_PAIR)

    def test_duplicate_cards_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(cards("As", "As", "Ks", "Kd", "Qs", "2c", "3d"))

    def test_descriptions(self):
        self.assertEqual(
            evaluate(cards("As", "Ad", "Ks", "Kd", "Qs", "2c", "3d")).describe(),
            "Two Pair, Aces and Kings",
        )
        self.assertEqual(
            evaluate(cards("9s", "8s", "7s", "6s", "5s", "2d", "3c")).describe(),
            "Straight Flush, 9-high",
        )


if __name__ == "__main__":
    unittest.main()
