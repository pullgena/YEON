import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stats import KeyCounter, label_for


class KeyCounterTests(unittest.TestCase):
    def test_count_and_repeat_suppression(self):
        counts = KeyCounter()
        self.assertTrue(counts.add_event("a", True, 20))
        self.assertFalse(counts.add_event("a", True, 20.1))
        self.assertEqual(counts.total, 1)
        self.assertEqual(counts.counts["a"], 1)
        self.assertTrue(counts.add_event("a", False, 20.2))
        self.assertTrue(counts.add_event("a", True, 20.3))
        self.assertEqual(counts.total, 2)

    def test_kps_window(self):
        counts = KeyCounter()
        counts.add_event("q", True, 3.0)
        counts.add_event("w", True, 3.4)
        self.assertEqual(counts.kps(3.5), 2)
        self.assertEqual(counts.kps(4.01), 1)
        self.assertEqual(counts.kps(4.5), 0)

    def test_release_and_reset(self):
        counts = KeyCounter()
        counts.add_event("b", True, 1)
        counts.release_all()
        self.assertEqual(len(counts.held), 0)
        self.assertEqual(counts.total, 1)
        counts.reset()
        self.assertEqual(counts.total, 0)

    def test_labels(self):
        self.assertEqual(label_for("backspace"), "Back")
        self.assertEqual(label_for("rctrl"), "RCtrl")
        self.assertEqual(label_for("num8", {"lshift"}), "N8")


if __name__ == "__main__":
    unittest.main()
