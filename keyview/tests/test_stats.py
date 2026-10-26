import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stats import DEFAULT_SLOTS, KeyCounter, label_for


class KeyCounterTests(unittest.TestCase):
    def test_default_layout(self):
        self.assertEqual(len(DEFAULT_SLOTS), 16)
        self.assertEqual(len(set(DEFAULT_SLOTS)), 16)
        self.assertEqual(label_for("backspace"), "Back")
        self.assertEqual(label_for("rctrl"), "RCtrl")

    def test_keydown_count_and_repeat_suppression(self):
        counts = KeyCounter()
        self.assertTrue(counts.add_event("a", True, 20.0))
        self.assertFalse(counts.add_event("a", True, 20.1))
        self.assertEqual(counts.total, 1)
        self.assertEqual(counts.counts["a"], 1)
        self.assertTrue(counts.add_event("a", False, 20.2))
        self.assertTrue(counts.add_event("a", True, 20.3))
        self.assertEqual(counts.total, 2)
        self.assertEqual(counts.counts["a"], 2)

    def test_dynamic_slot_for_any_supported_key(self):
        counts = KeyCounter()
        counts.add_event("f7", True, 11.0)
        self.assertIn("f7", counts.slots)
        self.assertEqual(len(counts.slots), 16)
        self.assertEqual(counts.counts["f7"], 1)
        counts.add_event("f7", False, 11.01)
        self.assertTrue(counts.highlighted("f7", 11.1))
        self.assertFalse(counts.highlighted("f7", 11.2))

    def test_kps_window_and_release_all(self):
        counts = KeyCounter()
        counts.add_event("q", True, 3.0)
        counts.add_event("w", True, 3.4)
        self.assertEqual(counts.kps(3.5), 2)
        self.assertEqual(counts.kps(4.01), 1)
        self.assertEqual(counts.kps(4.5), 0)
        counts.release_all()
        self.assertEqual(len(counts.held), 0)
        self.assertEqual(counts.total, 2)

    def test_reset(self):
        counts = KeyCounter()
        counts.add_event("b", True, 1.0)
        counts.reset()
        self.assertEqual(counts.total, 0)
        self.assertEqual(counts.counts["b"], 0)
        self.assertEqual(counts.slots, DEFAULT_SLOTS)


if __name__ == "__main__":
    unittest.main()
