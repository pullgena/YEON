import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from keymap import ALL_KEYS, MAIN_ROWS, NAV_ROWS, PAD_ROWS, resolve_key
from layout import WIDTH, HEIGHT, keyboard_rectangles
from stats import KeyCounter, SHIFTED_LABELS, label_for


class FullKeyboardTests(unittest.TestCase):
    def test_physical_104_key_layout(self):
        ids = [key.id for key in ALL_KEYS]
        self.assertEqual(len(ids), 104)
        self.assertEqual(len(set(ids)), 104)
        self.assertEqual(len(MAIN_ROWS), 6)
        self.assertEqual(len(NAV_ROWS), 6)
        self.assertEqual(len(PAD_ROWS), 5)
        self.assertNotIn("fn", ids)
        self.assertIn("rwin", ids)
        self.assertIn("menu", ids)

    def test_all_visible_and_nonoverlapping(self):
        boxes = keyboard_rectangles()
        self.assertEqual(len(boxes), 104)
        for key_id, (x, y, w, h) in boxes.items():
            self.assertGreater(w, 15, key_id)
            self.assertGreater(h, 15, key_id)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, WIDTH, key_id)
            self.assertLessEqual(y + h, HEIGHT, key_id)
        self.assertGreater(boxes["numplus"][3], boxes["num7"][3])
        self.assertGreater(boxes["numenter"][3], boxes["num3"][3])

    def test_ansi_modifier_keys(self):
        self.assertEqual(resolve_key("right windows", None), "rwin")
        self.assertEqual(resolve_key("menu", None), "menu")
        self.assertEqual(resolve_key("right shift", 54), "rshift")
        self.assertEqual(resolve_key("1", 2), "1")
        self.assertEqual(resolve_key("!", 2), "1")
        self.assertEqual(resolve_key("한/영", None), "ralt")

    def test_shift_one_counts_physical_key_once(self):
        c = KeyCounter()
        self.assertTrue(c.add_event("lshift", True, 0.0))
        self.assertEqual(c.label("1", 0.01), "!")
        self.assertTrue(c.add_event("1", True, 0.02))
        self.assertFalse(c.add_event("1", True, 0.03))
        self.assertEqual(c.counts["1"], 1)
        self.assertEqual(c.total, 2)
        self.assertTrue(c.add_event("1", False, 0.04))
        self.assertTrue(c.add_event("lshift", False, 0.05))
        self.assertEqual(c.label("1", 0.10), "!")
        self.assertEqual(c.label("1", 0.25), "1")

    def test_all_shifted_punctuation(self):
        self.assertEqual(label_for("2", {"rshift"}), "@")
        self.assertEqual(label_for("slash", {"lshift"}), "?")
        self.assertEqual(label_for("equal", {"lshift"}), "+")
        self.assertEqual(label_for("quote", {"rshift"}), '"')
        self.assertEqual(label_for("1", set()), "1")
        self.assertEqual(label_for("num1", {"lshift"}), "N1")
        self.assertEqual(len(SHIFTED_LABELS), 21)


if __name__ == "__main__":
    unittest.main()
