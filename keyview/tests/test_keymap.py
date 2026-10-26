import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from keymap import ALL_KEYS, MAIN_ROWS, resolve_key


class KeyMapTests(unittest.TestCase):
    def test_unique_visible_key_ids(self):
        ids = [key.id for key in ALL_KEYS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_letter_by_scan_code(self):
        self.assertEqual(resolve_key("ㅁ", 30), "a")
        self.assertEqual(resolve_key("q", 16), "q")

    def test_modifiers_and_arrows(self):
        self.assertEqual(resolve_key("right shift", 54), "rshift")
        self.assertEqual(resolve_key("shift", 54), "rshift")
        self.assertEqual(resolve_key("up", 72, False), "up")
        self.assertEqual(resolve_key("한/영", None), "ralt")
        self.assertEqual(resolve_key("한자", None), "rctrl")

    def test_numpad_and_main_numbers(self):
        self.assertEqual(resolve_key("7", 8, False), "7")
        self.assertEqual(resolve_key("home", 71, True), "num7")
        self.assertEqual(resolve_key("home", 71, False), "home")
        self.assertEqual(resolve_key("enter", 28, True), "numenter")

    def test_unrecognized(self):
        self.assertIsNone(resolve_key("unknown weird key", None))
        self.assertGreaterEqual(len(MAIN_ROWS), 6)


if __name__ == "__main__":
    unittest.main()
