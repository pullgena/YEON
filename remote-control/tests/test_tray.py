"""Tray icon checks do not require a Windows display server."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tray_visual import make_tray_icon, status_title


class TrayAppearanceTests(unittest.TestCase):
    def test_idle_icon(self):
        image = make_tray_icon(False)
        self.assertEqual(image.size, (64,64))
        self.assertEqual(image.mode,"RGBA")

    def test_sharing_icon_is_distinct(self):
        idle = make_tray_icon(False)
        sharing = make_tray_icon(True)
        self.assertNotEqual(idle.tobytes(),sharing.tobytes())

    def test_tray_icon_is_scalable(self):
        self.assertEqual(make_tray_icon(True,256).size,(256,256))

    def test_too_small_image_disallowed(self):
        with self.assertRaises(ValueError):
            make_tray_icon(False,16)

    def test_status_text(self):
        self.assertIn("공유 중",status_title(True))
        self.assertIn("공유 중지",status_title(False))


if __name__ == "__main__":
    unittest.main()
