import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from keymap import ALL_KEYS
from modes import (PHOTO_KEYS, WASD_KEYS, MODE_NAMES, get_mode_geometry,
                   label_in_mode, mode_for_chord)
from stats import KeyCounter


class KeyViewModesTests(unittest.TestCase):
    def test_mode_shortcuts_with_both_shifts(self):
        self.assertEqual(mode_for_chord("1", True, True, {"lshift"}), "photo")
        self.assertEqual(mode_for_chord("2", True, True, {"rshift"}), "wasd")
        self.assertEqual(mode_for_chord("3", True, True, {"lshift"}), "full")
        self.assertIsNone(mode_for_chord("1", True, True, set()))
        self.assertIsNone(mode_for_chord("2", False, True, {"lshift"}))
        self.assertIsNone(mode_for_chord("2", True, False, {"lshift"}))
        self.assertIsNone(mode_for_chord("4", True, True, {"lshift"}))

    def test_mode_geometry_and_visible_keys(self):
        full = get_mode_geometry("full")[3]
        photo = get_mode_geometry("photo")[3]
        wasd = get_mode_geometry("wasd")[3]
        self.assertEqual(len(full), 104)
        self.assertEqual(len(photo), 16)
        self.assertEqual(list(photo), list(PHOTO_KEYS))
        self.assertEqual(set(wasd), set(WASD_KEYS))
        self.assertEqual(set(full), {spec.id for spec in ALL_KEYS})
        for mode in MODE_NAMES:
            w, h, footer_y, rects = get_mode_geometry(mode)
            self.assertLess(footer_y, h)
            for k, (x, y, kw, kh) in rects.items():
                self.assertLessEqual(x + kw, w, k)
                self.assertLessEqual(y + kh, footer_y, k)
        with self.assertRaises(ValueError):
            get_mode_geometry("not-a-mode")

    def test_image_mode_fixed_labels(self):
        counts = KeyCounter()
        counts.add_event("lshift", True, 5.0)
        self.assertEqual(label_in_mode("photo", "1", counts, 5.1), "1")
        self.assertEqual(label_in_mode("full", "1", counts, 5.1), "!")
        self.assertEqual(label_in_mode("photo", "backspace", counts, 5.1), "Back")
        self.assertEqual(label_in_mode("wasd", "space", counts, 5.1), "SPACE")

    def test_hotkeys_keep_normal_keystroke_counts(self):
        c = KeyCounter()
        c.add_event("lshift", True, 1.0)
        before = c.held.copy()
        changed = c.add_event("1", True, 1.1)
        self.assertEqual(mode_for_chord("1", True, changed, before), "photo")
        self.assertEqual(c.counts["1"], 1)
        self.assertEqual(c.counts["lshift"], 1)
        self.assertEqual(c.total, 2)


if __name__ == "__main__":
    unittest.main()
