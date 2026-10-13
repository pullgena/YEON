"""Tests of background/tray safety invariants without a Windows display."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import ManagedDesktopApp


class FakeRoot:
    def __init__(self):
        self.hidden = False
        self.destroyed = False
    def withdraw(self):
        self.hidden = True
    def destroy(self):
        self.destroyed = True


class FakeTray:
    def __init__(self):
        self.messages = []
        self.icon = None
        self.title = None
        self.stopped = False
        self.menu_updates = 0
    def notify(self, message, title):
        self.messages.append(message)
    def update_menu(self):
        self.menu_updates += 1
    def stop(self):
        self.stopped = True


class FakeState:
    def __init__(self):
        self.ended = False
        self.remote = False
    def can_remote_control(self):
        return self.remote
    def set_remote_control(self, enabled):
        self.remote = bool(enabled)
    def end(self):
        self.ended = True


class FakeServer:
    def __init__(self):
        self.state = FakeState()
    def shutdown(self):
        pass
    def server_close(self):
        pass


class FakeControlButton:
    def __init__(self): self.settings = {}
    def config(self, **kwargs): self.settings.update(kwargs)

class FakeStringVar:
    def __init__(self): self.value = ''
    def set(self, value): self.value = value

class BackgroundBehaviorTests(unittest.TestCase):
    def prepare(self, active=True):
        app = ManagedDesktopApp.__new__(ManagedDesktopApp)
        app.root = FakeRoot()
        app.tray = FakeTray()
        app.tray_ready = True
        app.hide_notice_sent = False
        app.closing = False
        app.stopping = False
        app.control_btn = FakeControlButton()
        app.control_status = FakeStringVar()
        app.server = FakeServer() if active else None
        return app

    def test_close_window_keeps_share_live_in_tray(self):
        app = self.prepare()
        app.hide_window()
        self.assertTrue(app.root.hidden)
        self.assertTrue(app.server is not None)
        self.assertFalse(app.server.state.ended)
        self.assertEqual(len(app.tray.messages),1)
        app.hide_window()
        self.assertEqual(len(app.tray.messages),1)

    def test_tray_icon_reflects_sharing(self):
        app = self.prepare()
        app._refresh_tray()
        self.assertIn('공유 중',app.tray.title)
        active_icon = app.tray.icon.tobytes()
        app.server = None
        app._refresh_tray()
        self.assertIn('공유 중지',app.tray.title)
        self.assertNotEqual(active_icon,app.tray.icon.tobytes())

    def test_local_toggle_controls_remote_authority_and_tray(self):
        app=self.prepare()
        self.assertFalse(app.server.state.can_remote_control())
        app.toggle_remote_control()
        self.assertTrue(app.server.state.can_remote_control())
        self.assertIn('ON', app.tray.title)
        self.assertIn('OFF로 변경', app.control_btn.settings['text'])
        app.toggle_remote_control()
        self.assertFalse(app.server.state.can_remote_control())
        self.assertIn('OFF', app.tray.title)

    def test_full_quit_revokes_sessions(self):
        app = self.prepare()
        server = app.server
        app.quit_app()
        self.assertTrue(server.state.ended)
        self.assertTrue(app.tray.stopped)
        self.assertTrue(app.root.destroyed)


if __name__ == '__main__':
    unittest.main()
