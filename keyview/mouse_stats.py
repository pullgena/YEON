"""Mouse button, scroll and motion indications kept in memory only."""
from collections import Counter

BUTTONS = ("left", "middle", "right")
WHEEL = ("scroll_up", "scroll_down")
MOUSE_LABELS = {
    "left": "LMB", "middle": "MMB", "right": "RMB",
    "scroll_up": "▲", "scroll_down": "▼", "move": "MOVE",
}


class MouseCounter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.counts = Counter()
        self.total = 0
        self.held = set()
        self.flashes = {}
        self.motion_until = -1

    def release_all(self):
        self.held.clear()
        self.flashes.clear()
        self.motion_until = -1

    def add_button(self, name, pressed, now):
        if name not in BUTTONS:
            return False
        if not pressed:
            seen = name in self.held
            self.held.discard(name)
            return seen
        if name in self.held:
            return False
        self.held.add(name)
        self.counts[name] += 1
        self.total += 1
        self.flashes[name] = now + .15
        return True

    def add_scroll(self, direction, now):
        if direction not in WHEEL:
            return False
        self.counts[direction] += 1
        self.total += 1
        self.flashes[direction] = now + .22
        return True

    def add_motion(self, now):
        # Only a short visible pulse, never x/y, distance or pointer path.
        self.motion_until = now + .28

    def highlighted(self, name, now):
        if name == "move":
            return now < self.motion_until
        return name in self.held or self.flashes.get(name, -1) > now
