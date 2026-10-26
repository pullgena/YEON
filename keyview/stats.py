"""Session-only physical-key counts and Shift-transformed display labels."""
from collections import Counter, deque


SHIFTED_LABELS = {
    "grave": "~",
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
    "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
    "minus": "_", "equal": "+",
    "lbracket": "{", "rbracket": "}", "backslash": "|",
    "semicolon": ":", "quote": '"', "comma": "<",
    "period": ">", "slash": "?",
}

BASE_LABELS = {
    "grave": "`", "backspace": "Back", "backslash": "\\",
    "up": "↑", "lshift": "LShift", "rshift": "RShift",
    "ralt": "RAlt", "lalt": "LAlt", "lctrl": "LCtrl", "rctrl": "RCtrl",
    "lwin": "LWin", "rwin": "RWin", "menu": "Menu",
    "minus": "-", "equal": "=", "enter": "Enter", "space": "Space",
    "capslock": "Caps", "pageup": "PgUp", "pagedown": "PgDn",
    "printscreen": "PrtSc", "scrolllock": "ScrLk", "numlock": "Num",
    "delete": "Del", "nummultiply": "N*", "numslash": "N/",
    "numminus": "N-", "numplus": "N+", "numdecimal": "N.",
    "numenter": "NEnter", "semicolon": ";", "quote": "'",
    "comma": ",", "period": ".", "slash": "/", "lbracket": "[",
    "rbracket": "]", "left": "←", "right": "→", "down": "↓",
    "esc": "Esc", "tab": "Tab", "insert": "Ins",
}
for _letter in "abcdefghijklmnopqrstuvwxyz":
    BASE_LABELS[_letter] = _letter.upper()
for _digit in "0123456789":
    BASE_LABELS[_digit] = _digit
    BASE_LABELS["num" + _digit] = "N" + _digit


def label_for(key_id, held_keys=(), shifted_flash=False):
    """Only the visible glyph changes for Shift; physical key counts do not."""
    shift_on = "lshift" in held_keys or "rshift" in held_keys
    if (shift_on or shifted_flash) and key_id in SHIFTED_LABELS:
        return SHIFTED_LABELS[key_id]
    return BASE_LABELS.get(key_id, key_id.upper()[:7])


class KeyCounter:
    """Counts presses by physical key, not by the generated character."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.counts = Counter()
        self.total = 0
        self.held = set()
        self.recent_downs = deque()
        self.flashes = {}
        self.shifted_flashes = {}

    def release_all(self):
        self.held.clear()
        self.flashes.clear()
        self.shifted_flashes.clear()

    def add_event(self, key_id, is_down, now):
        if not key_id:
            return False
        if not is_down:
            had_key = key_id in self.held
            self.held.discard(key_id)
            return had_key
        if key_id in self.held:
            return False  # OS autorepeat does not create extra press counts.

        shift_was_held = "lshift" in self.held or "rshift" in self.held
        self.held.add(key_id)
        self.counts[key_id] += 1
        self.total += 1
        self.recent_downs.append(now)
        self.flashes[key_id] = now + .17
        if shift_was_held and key_id in SHIFTED_LABELS:
            self.shifted_flashes[key_id] = now + .17
        else:
            self.shifted_flashes.pop(key_id, None)
        return True

    def kps(self, now):
        while self.recent_downs and self.recent_downs[0] <= now - 1.0:
            self.recent_downs.popleft()
        return len(self.recent_downs)

    def highlighted(self, key_id, now):
        return key_id in self.held or self.flashes.get(key_id, -1) > now

    def label(self, key_id, now):
        return label_for(key_id, self.held, self.shifted_flashes.get(key_id, -1) > now)
