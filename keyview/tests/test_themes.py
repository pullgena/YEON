import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from themes import THEMES, load_theme, save_theme, seasonal_default, validate_palettes


class ThemeTests(unittest.TestCase):
    def test_palette_colors_and_variants(self):
        validate_palettes()
        self.assertTrue({"halloween", "minecraft", "classic", "cyber", "winter",
                         "cherry"} <= set(THEMES))
        self.assertTrue(THEMES["minecraft"]["pixel"])
        self.assertFalse(THEMES["halloween"]["pixel"])
        self.assertNotEqual(THEMES["minecraft"]["active"], THEMES["halloween"]["active"])

    def test_seasonal_default_only_before_november(self):
        self.assertEqual(seasonal_default(date(2026, 10, 26)), "halloween")
        self.assertEqual(seasonal_default(date(2026, 11, 1)), "classic")

    def test_user_choice_persists_across_sessions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "yeon" / "KeyView" / "settings.json"
            self.assertEqual(load_theme(path, date(2026, 10, 26)), "halloween")
            self.assertTrue(save_theme("minecraft", path))
            self.assertEqual(load_theme(path, date(2026, 12, 22)), "minecraft")
            self.assertEqual(path.read_text(encoding="utf-8"), '{"theme": "minecraft"}')
            self.assertTrue(save_theme("winter", path))
            self.assertEqual(load_theme(path, date(2026, 6, 1)), "winter")

    def test_invalid_input_falls_back_safely(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("{oops", encoding="utf-8")
            self.assertEqual(load_theme(path, date(2026, 11, 2)), "classic")
            path.write_text('{"theme":"bad_theme"}', encoding="utf-8")
            self.assertEqual(load_theme(path, date(2026, 10, 22)), "halloween")
            with self.assertRaises(ValueError):
                save_theme("invalid", path)
