"""Consented, short-lived full-screen classroom focus view.

Never runs without local approval. ESC and the local emergency-stop button
always exit; stale streams automatically unlock the managed desktop.
"""
from __future__ import annotations

import io
import os
import ctypes
import threading
import time
import tkinter as tk
from PIL import Image, ImageTk


class FocusSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.mode = 'idle'  # idle, pending, active, denied
        self.owner = None
        self.requested_at = 0.0
        self.frame = None
        self.frame_seq = 0
        self.last_frame = 0.0

    def request(self, token):
        with self.lock:
            if self.mode in ('pending', 'active'):
                return False
            self.mode = 'pending'
            self.owner = token
            self.requested_at = time.monotonic()
            self.frame = None
            self.frame_seq = 0
            return True

    def pending(self):
        with self.lock:
            if self.mode == 'pending' and time.monotonic() - self.requested_at > 40:
                self.mode = 'denied'
            return self.mode == 'pending'

    def accept(self):
        with self.lock:
            if not self.pending():
                return False
            self.mode = 'active'
            self.last_frame = time.monotonic()
            return True

    def deny(self):
        with self.lock:
            if self.mode == 'pending':
                self.mode = 'denied'

    def status(self, token):
        with self.lock:
            if token != self.owner:
                return 'idle'
            self.pending()
            return self.mode

    def push(self, token, jpeg):
        with self.lock:
            if token != self.owner or self.mode != 'active':
                return False
            if len(jpeg) < 4 or not jpeg.startswith(b'\xff\xd8') or not jpeg.endswith(b'\xff\xd9'):
                return False
            self.frame = jpeg
            self.frame_seq += 1
            self.last_frame = time.monotonic()
            return True

    def latest(self):
        with self.lock:
            if self.mode == 'active' and time.monotonic() - self.last_frame > 8:
                self.stop()
            return self.mode, self.frame_seq, self.frame

    def stop(self, token=None):
        with self.lock:
            if token is not None and token != self.owner:
                return False
            self.mode = 'idle'
            self.owner = None
            self.frame = None
            self.frame_seq += 1
            return True


class CursorGuard:
    """Clip the Windows pointer to the emergency-stop button, never the whole OS.

    A separate watchdog removes the restriction if the UI stops responding.
    On non-Windows systems, the fullscreen overlay still prevents desktop clicks.
    """
    def __init__(self):
        self.enabled = False
        self.heartbeat = 0.0
        self._stop = threading.Event()

    def lock_to_button(self, button):
        if os.name != 'nt':
            return
        try:
            class RECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                            ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
            r = RECT(button.winfo_rootx(), button.winfo_rooty(),
                     button.winfo_rootx() + button.winfo_width(),
                     button.winfo_rooty() + button.winfo_height())
            if ctypes.windll.user32.ClipCursor(ctypes.byref(r)):
                self.enabled = True
                self.tick()
                threading.Thread(target=self._watchdog, daemon=True, name='YEON-cursor-unlock').start()
        except (AttributeError, OSError, ValueError):
            return

    def tick(self):
        self.heartbeat = time.monotonic()

    def _watchdog(self):
        while not self._stop.wait(0.5):
            if time.monotonic() - self.heartbeat > 2.5:
                self.release()
                break

    def release(self):
        self._stop.set()
        if self.enabled and os.name == 'nt':
            self.enabled = False
            ctypes.windll.user32.ClipCursor(None)


class FocusOverlay:
    """Full-screen topmost picture with a locally accessible emergency escape.

    The overlay intercepts clicks so the underlying desktop cannot be operated.
    The cursor is *not* trapped by OS hooks: a local ESC escape must remain safe.
    """
    def __init__(self, root, session: FocusSession, on_stop):
        self.root = root
        self.session = session
        self.on_stop = on_stop
        self.window = tk.Toplevel(root)
        self.window.title('YEON 집중 화면 전송 · ESC 종료')
        self.window.configure(bg='#070b1b')
        self.window.attributes('-fullscreen', True)
        self.window.attributes('-topmost', True)
        self.window.protocol('WM_DELETE_WINDOW', self.stop)
        self.window.bind('<Escape>', self.stop)
        self.window.bind('<Control-Shift-q>', self.stop)
        self.closed = False
        self.last_seq = -1
        self.image = None
        self.cursor_guard = CursorGuard()
        self.content = tk.Label(self.window, text='관리자 화면을 연결하는 중…',
                                font=('Malgun Gothic', 22), fg='white', bg='#070b1b')
        self.content.pack(fill='both', expand=True)
        toolbar = tk.Frame(self.window, bg='#182039')
        toolbar.pack(fill='x', side='bottom')
        tk.Label(toolbar, text='YEON 집중 화면 전송 · 화면을 보는 동안 다른 작업이 제한됩니다',
                 fg='white', bg='#182039', padx=15, pady=12).pack(side='left')
        stop_button = tk.Button(toolbar, text='집중 화면 종료 (ESC)', command=self.stop,
                  bg='#b91c1c', fg='white', relief='flat', padx=18, pady=10)
        stop_button.pack(side='right', padx=12)
        self.window.focus_force()
        self.window.update_idletasks()
        self.cursor_guard.lock_to_button(stop_button)
        self.poll()

    def poll(self):
        if self.closed:
            return
        self.cursor_guard.tick()
        mode, seq, frame = self.session.latest()
        if mode != 'active':
            self.close()
            return
        if frame is not None and seq != self.last_seq:
            try:
                image = Image.open(io.BytesIO(frame))
                image.load()
                width = max(1, self.window.winfo_screenwidth())
                height = max(1, self.window.winfo_screenheight() - 48)
                image.thumbnail((width, height), Image.Resampling.LANCZOS)
                self.image = ImageTk.PhotoImage(image)
                self.content.configure(image=self.image, text='')
                self.last_seq = seq
            except (OSError, ValueError):
                pass
        self.window.after(90, self.poll)

    def stop(self, _event=None):
        self.session.stop()
        self.close()
        self.on_stop()

    def close(self):
        if not self.closed:
            self.closed = True
            self.cursor_guard.release()
            try:
                self.window.destroy()
            except tk.TclError:
                pass
