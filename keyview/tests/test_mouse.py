import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modes import MODE_NAMES, get_mode_geometry
from mouse_panel import ITEM_KEYS, PANEL_HEIGHT, mouse_panel_geometry
from mouse_stats import MouseCounter


class MouseOverlayTests(unittest.TestCase):
    def test_key_and_mouse_layouts_fit_at_all_sizes(self):
        for mode in MODE_NAMES:
            width, height, _, keys = get_mode_geometry(mode)
            heading, indicators = mouse_panel_geometry(width, height)
            self.assertEqual(tuple(indicators), ITEM_KEYS)
            for x, y, w, h in [heading, *indicators.values()]:
                self.assertGreaterEqual(x, 0)
                self.assertGreater(w, 10)
                self.assertLessEqual(x + w, width)
                self.assertGreaterEqual(y, height)
                self.assertLessEqual(y + h, height + PANEL_HEIGHT)

    def test_buttons_only_count_new_downs(self):
        mouse = MouseCounter()
        self.assertTrue(mouse.add_button("left", True, 1.0))
        self.assertFalse(mouse.add_button("left", True, 1.01))
        self.assertTrue(mouse.highlighted("left", 1.2))
        self.assertEqual(mouse.counts["left"], 1)
        self.assertEqual(mouse.total, 1)
        self.assertTrue(mouse.add_button("left", False, 1.3))
        self.assertTrue(mouse.add_button("left", True, 1.4))
        self.assertEqual(mouse.total, 2)

    def test_scroll_directions_and_motion(self):
        mouse = MouseCounter()
        self.assertTrue(mouse.add_scroll("scroll_up", 5.0))
        self.assertTrue(mouse.add_scroll("scroll_down", 5.1))
        self.assertFalse(mouse.add_scroll("sideways", 5.2))
        self.assertEqual(mouse.total, 2)
        self.assertEqual(mouse.counts["scroll_up"], 1)
        self.assertEqual(mouse.counts["scroll_down"], 1)
        mouse.add_motion(6.0)
        self.assertTrue(mouse.highlighted("move", 6.1))
        self.assertFalse(mouse.highlighted("move", 6.3))
        self.assertFalse(hasattr(mouse, "coordinates"))

    def test_reset_releases_mouse(self):
        mouse = MouseCounter()
        mouse.add_button("right", True, 2)
        mouse.add_motion(2)
        mouse.release_all()
        self.assertEqual(mouse.total, 1)
        self.assertFalse(mouse.highlighted("right", 3))
        self.assertFalse(mouse.highlighted("move", 3))
        mouse.reset()
        self.assertEqual(mouse.total, 0)
        self.assertEqual(dict(mouse.counts), {})


if __name__ == "__main__":
    unittest.main()
