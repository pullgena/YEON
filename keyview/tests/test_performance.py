import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stats import KeyCounter
from mouse_stats import MouseCounter
from modes import mode_for_chord
from keymap import ALL_KEYS
from performance import mode_delay, active_keys_for_refresh, active_mouse_for_refresh


class MinecraftPerformanceTests(unittest.TestCase):
    def test_adaptive_refresh_intervals(self):
        self.assertEqual(mode_delay(True, True, True), 64)
        self.assertEqual(mode_delay(True, False, True), 140)
        self.assertEqual(mode_delay(False, False, True), 320)
        self.assertEqual(mode_delay(True, True, False), 35)
        self.assertEqual(mode_delay(False, False, False), 180)

    def test_dirty_keys_are_small_subset_of_104(self):
        counter = KeyCounter()
        counter.add_event("w", True, 1.0)
        active = active_keys_for_refresh(counter, 1.1, set(k.id for k in ALL_KEYS))
        self.assertEqual(active, {"w"})
        counter.add_event("w", False, 1.12)
        self.assertEqual(active_keys_for_refresh(counter, 1.4, set(k.id for k in ALL_KEYS)), set())

    def test_mouse_motion_uses_only_short_pulse(self):
        counter = MouseCounter()
        counter.add_motion(3.0)
        self.assertEqual(active_mouse_for_refresh(counter, 3.1, {"move", "left"}), {"move"})
        self.assertEqual(active_mouse_for_refresh(counter, 3.5, {"move", "left"}), set())
        self.assertEqual(counter.total, 0)

    def test_shortcuts_unchanged(self):
        self.assertEqual(mode_for_chord("1", True, True, {"lshift"}), "photo")
        self.assertEqual(mode_for_chord("2", True, True, {"rshift"}), "wasd")
        self.assertEqual(mode_for_chord("3", True, True, {"lshift"}), "full")


if __name__ == "__main__":
    unittest.main()
