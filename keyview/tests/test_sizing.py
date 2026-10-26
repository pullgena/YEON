import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from sizing import (clamp_zoom, fit_scale, load_zoom, save_zoom, PRESETS, MIN_ZOOM, MAX_ZOOM)
from modes import MODE_NAMES, get_mode_geometry
from mouse_panel import PANEL_HEIGHT


class ZoomTests(unittest.TestCase):
    def test_zoom_limits_and_steps(self):
        self.assertEqual(clamp_zoom(5), MIN_ZOOM)
        self.assertEqual(clamp_zoom(999), MAX_ZOOM)
        self.assertEqual(clamp_zoom(73), 75)
        self.assertEqual(clamp_zoom(97), 95)
        self.assertEqual(clamp_zoom(None), 100)
        self.assertEqual(clamp_zoom(float("inf")), 100)
        self.assertEqual(PRESETS, (50, 75, 100, 125, 150))

    def test_all_three_modes_fit_screen_without_clipping(self):
        for mode in MODE_NAMES:
            w, h, footer, _ = get_mode_geometry(mode)
            h += PANEL_HEIGHT
            for screen_w, screen_h in ((1920, 1080), (1366, 768), (1024, 640)):
                for zoom in PRESETS:
                    scale = fit_scale(w, h, screen_w, screen_h, zoom)
                    self.assertGreater(scale, 0)
                    self.assertLessEqual(scale, zoom / 100)
                    self.assertLessEqual(round(w * scale), screen_w - 32 + 1)
                    self.assertLessEqual(round(h * scale), screen_h - 84 + 1)

    def test_persists_size_in_own_file_without_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "KeyView" / "zoom.json"
            self.assertEqual(load_zoom(path), 100)
            self.assertTrue(save_zoom(75, path))
            self.assertEqual(load_zoom(path), 75)
            self.assertEqual(json.loads(path.read_text("utf-8")), {"zoom": 75})
            self.assertTrue(save_zoom(125, path))
            self.assertEqual(load_zoom(path), 125)

    def test_invalid_settings_recover(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "zoom.json"
            for raw in ("{", '{"zoom": 999}', '{"zoom": "bad"}', '{"zoom": true}'):
                path.write_text(raw, encoding="utf-8")
                self.assertEqual(load_zoom(path), 100)
            with self.assertRaises(ValueError):
                fit_scale(0, 386, 1280, 720, 100)


if __name__ == "__main__":
    unittest.main()
