"""Session-only key counts, rolling KPS and compact overlay slots."""
from collections import Counter, deque


DEFAULT_SLOTS = [
    "grave", "1", "2", "e", "p", "equal", "backspace", "backslash",
    "up", "lshift", "c", "minus", "ralt", "period", "enter", "rctrl",
]

KEY_LABELS = {
    "grave": "~", "backspace": "Back", "backslash": "\\",
    "up": "↑", "lshift": "L⇧", "rshift": "R⇧",
    "ralt": "RAlt", "lalt": "LAlt", "lctrl": "LCtrl", "rctrl": "RCtrl",
    "minus": "-", "equal": "=", "enter": "↵", "space": "Space",
    "capslock": "Caps", "pageup": "PgUp", "pagedown": "PgDn",
    "printscreen": "PrtSc", "numlock": "Num", "delete": "Del",
    "numslash": "N/", "nummultiply": "N*", "numminus": "N-",
    "numplus": "N+", "numdecimal": "N.", "numenter": "N↵",
    "semicolon": ";", "quote": "'", "comma": ",", "period": ".",
    "slash": "/", "lbracket": "[", "rbracket": "]",
    "left": "←", "right": "→", "down": "↓",
    "lwin": "Win", "rwin": "Win", "esc": "Esc", "tab": "Tab",
}
for _letter in "abcdefghijklmnopqrstuvwxyz":
    KEY_LABELS[_letter] = _letter.upper()
for _digit in "0123456789":
    KEY_LABELS[_digit] = _digit
    KEY_LABELS["num" + _digit] = "N" + _digit


def label_for(key_id):
    return KEY_LABELS.get(key_id, key_id[:6].upper())


class KeyCounter:
    """Key identities and numeric counts only; never stores typed text."""

    def __init__(self, initial_slots=None):
        self.initial_slots = list(initial_slots or DEFAULT_SLOTS)
        if len(self.initial_slots) != 16 or len(set(self.initial_slots)) != 16:
            raise ValueError("Exactly 16 distinct display slots are required.")
        self.reset()

    def reset(self):
        self.slots = self.initial_slots.copy()
        self.counts = Counter()
        self.total = 0
        self.held = set()
        self.recent_downs = deque()
        self.last_seen = {key: -1 for key in self.slots}
        self.flashes = {}

    def release_all(self):
        self.held.clear()
        self.flashes.clear()

    def add_event(self, key_id, is_down, now):
        """Process a physical keyboard event, ignoring OS autorepeat presses."""
        if not key_id:
            return False
        if not is_down:
            had_key = key_id in self.held
            self.held.discard(key_id)
            return had_key
        if key_id in self.held:
            return False

        self.held.add(key_id)
        self.counts[key_id] += 1
        self.total += 1
        self.recent_downs.append(now)
        self.flashes[key_id] = now + 0.12

        if key_id not in self.slots:
            candidates = (k for k in self.slots if k not in self.held)
            oldest = min(candidates, key=lambda k: self.last_seen.get(k, -1), default=None)
            if oldest is None:
                oldest = min(self.slots, key=lambda k: self.last_seen.get(k, -1))
            self.slots[self.slots.index(oldest)] = key_id
            self.last_seen.pop(oldest, None)
        self.last_seen[key_id] = now
        return True

    def kps(self, now):
        """Number of *new* key downs in the trailing one-second window."""
        while self.recent_downs and self.recent_downs[0] <= now - 1.0:
            self.recent_downs.popleft()
        return len(self.recent_downs)

    def highlighted(self, key_id, now):
        return key_id in self.held or self.flashes.get(key_id, -1) > now
