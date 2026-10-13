"""Input and capture adapter for the *foreground, locally approved* host PC."""
from __future__ import annotations

import io
import threading


class PCController:
    def __init__(self):
        self._input_lock = threading.RLock()
        self._screen_lock = threading.Lock()
        import pyautogui
        import mss
        from PIL import Image
        self.pg = pyautogui
        self.mss = mss
        self.Image = Image
        self.pg.FAILSAFE = True  # Move host mouse to top-left to trigger input failsafe.
        self.pg.PAUSE = 0.01

    def _monitor(self):
        with self.mss.mss() as sct:
            return dict(sct.monitors[1])

    def screen_size(self) -> tuple[int, int]:
        mon = self._monitor()
        return mon["width"], mon["height"]

    def screenshot_jpeg(self) -> bytes:
        with self._screen_lock, self.mss.mss() as sct:
            mon = sct.monitors[1]  # Primary monitor only (no accidental multi-monitor leak).
            shot = sct.grab(mon)
            image = self.Image.frombytes("RGB", shot.size, shot.rgb)
            image.thumbnail((1400, 900), self.Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            image.save(buf, "JPEG", quality=66, optimize=False)
            return buf.getvalue()

    def _coords(self, data):
        x, y = data.get("x"), data.get("y")
        if not isinstance(x, (float, int)) or isinstance(x, bool):
            raise ValueError("X 좌표가 올바르지 않습니다.")
        if not isinstance(y, (float, int)) or isinstance(y, bool):
            raise ValueError("Y 좌표가 올바르지 않습니다.")
        w, h = self.screen_size()
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("좌표 범위 초과")
        return min(w - 1, int(x * w)), min(h - 1, int(y * h))

    def perform(self, data: dict) -> None:
        op = data.get("type")
        # Client can only simulate GUI input. No arbitrary command execution API.
        with self._input_lock:
            if op in ("move", "down", "up"):
                x, y = self._coords(data)
                self.pg.moveTo(x, y, duration=0)
                if op != "move":
                    button = data.get("button", "left")
                    if button not in ("left", "right", "middle"):
                        raise ValueError("잘못된 마우스 버튼")
                    (self.pg.mouseDown if op == "down" else self.pg.mouseUp)(button=button)
            elif op == "scroll":
                amount = data.get("amount")
                if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not -10 <= amount <= 10:
                    raise ValueError("스크롤 범위 초과")
                self.pg.scroll(int(amount))
            elif op in ("keyDown", "keyUp"):
                key = data.get("key")
                if not isinstance(key, str) or len(key) > 32 or key not in self.pg.KEYBOARD_KEYS:
                    raise ValueError("지원하지 않는 키입니다.")
                (self.pg.keyDown if op == "keyDown" else self.pg.keyUp)(key)
            elif op == "text":
                text = data.get("text")
                if not isinstance(text, str) or not 0 < len(text) <= 1000:
                    raise ValueError("한 번에 1~1000자까지 입력할 수 있습니다.")
                # Clipboard paste supports Hangul/unicode; this replaces clipboard content.
                import pyperclip
                pyperclip.copy(text)
                self.pg.hotkey("ctrl", "v")
            elif op == "hotkey":
                key = data.get("name")
                # Deliberately exclude secure-attention keys such as Ctrl+Alt+Delete.
                shortcuts = {
                    "desktop": ("win", "d"),
                    "switch": ("alt", "tab"),
                    "copy": ("ctrl", "c"),
                    "paste": ("ctrl", "v"),
                    "enter": ("enter",),
                    "escape": ("esc",),
                    "backspace": ("backspace",),
                }
                if key not in shortcuts:
                    raise ValueError("지원하지 않는 단축키")
                self.pg.hotkey(*shortcuts[key])
            else:
                raise ValueError("허용되지 않은 조작입니다.")
