"""End-to-end tests: the real CLI, driven through stdin and --auto."""

import subprocess
import sys
import unittest

ROOT = __file__.rsplit("/", 2)[0]


def run_cli(args, stdin_text=""):
    return subprocess.run(
        [sys.executable, "main.py", *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )


class TestAutoPlay(unittest.TestCase):
    def test_auto_100_hands_completes(self):
        result = run_cli(["--auto", "100", "--seed", "42"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Played 100 hands", result.stdout)
        self.assertIn("Final stacks", result.stdout)

    def test_auto_is_deterministic_with_seed(self):
        first = run_cli(["--auto", "50", "--seed", "7"])
        second = run_cli(["--auto", "50", "--seed", "7"])
        self.assertEqual(first.stdout, second.stdout)

    def test_auto_with_tiny_stacks(self):
        result = run_cli(["--auto", "20", "--seed", "3", "--stack", "30"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Played 20 hands", result.stdout)


class TestInteractivePlay(unittest.TestCase):
    def test_scripted_session_plays_hands_and_quits(self):
        # Check/call through every decision, decline the next hand.
        moves = ("c\n" * 60) + "n\n"
        result = run_cli(["--seed", "11"], stdin_text=moves)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hand #1", result.stdout)
        self.assertIn("Board:", result.stdout)
        self.assertIn("Quitting", result.stdout)

    def test_invalid_input_is_rejected_not_fatal(self):
        moves = "banana\nr 99999\nr 40\n" + ("c\n" * 200) + "n\n"
        result = run_cli(["--seed", "11"], stdin_text=moves)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not a legal move", result.stdout)

    def test_quit_immediately(self):
        result = run_cli(["--seed", "11"], stdin_text="q\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Quitting", result.stdout)

    def test_opponent_cards_hidden_before_showdown(self):
        # The board line and the CPU line before showdown never show the
        # CPU's hole cards: the CPU line reads "?? ??" until the hand ends.
        moves = ("c\n" * 60) + "n\n"
        result = run_cli(["--seed", "11"], stdin_text=moves)
        lines = result.stdout.splitlines()
        cpu_lines = [line for line in lines if line.startswith("CPU")]
        hidden = [line for line in cpu_lines if "?? ??" in line]
        self.assertTrue(hidden, "CPU cards were never hidden")
        self.assertTrue(
            any("?? ??" not in line for line in cpu_lines),
            "CPU cards were never revealed at showdown",
        )


if __name__ == "__main__":
    unittest.main()
