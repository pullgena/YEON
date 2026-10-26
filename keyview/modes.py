"""Three visual-only key layouts and keyboard mode shortcuts."""
from layout import WIDTH as FULL_WIDTH, HEIGHT as FULL_HEIGHT, FOOTER_Y as FULL_FOOTER, keyboard_rectangles

PHOTO_KEYS = (
    "grave", "1", "2", "e", "p", "equal", "backspace", "backslash",
    "up", "lshift", "c", "minus", "ralt", "period", "enter", "rctrl",
)
WASD_KEYS = ("w", "a", "s", "d", "space")
MODE_NAMES = {"full": "104키", "photo": "사진 16키", "wasd": "WASD + Space"}
MODE_SHORTCUTS = {"1": "photo", "2": "wasd", "3": "full"}

PHOTO_LABELS = {
    "grave": "~", "backspace": "Back", "backslash": "\\",
    "up": "⇧", "lshift": "L⇧", "minus": "~",
    "ralt": "RAlt", "period": ".", "enter": "↵", "rctrl": "RCtrl",
}


def mode_for_chord(key_id, down, is_new_press, held_before):
    """Resolve Shift + digit on physical-key down only; returns None otherwise."""
    if not down or not is_new_press:
        return None
    if not ({"lshift", "rshift"} & set(held_before)):
        return None
    return MODE_SHORTCUTS.get(key_id)


def get_mode_geometry(mode):
    """Return (width, height, footer_y, key rectangles). Coordinates are logical pixels."""
    if mode == "full":
        return FULL_WIDTH, FULL_HEIGHT, FULL_FOOTER, keyboard_rectangles()
    if mode == "photo":
        width, height = 386, 127
        cell = (width - 6 - 7 * 4) / 8
        boxes = {
            key: (3 + (i % 8) * (cell + 4), 3 + (i // 8) * 48, cell, 44)
            for i, key in enumerate(PHOTO_KEYS)
        }
        return width, height, 100, boxes
    if mode == "wasd":
        width, height = 386, 215
        boxes = {
            "w": (166, 8, 54, 50),
            "a": (109, 63, 54, 50),
            "s": (166, 63, 54, 50),
            "d": (223, 63, 54, 50),
            "space": (109, 119, 168, 48),
        }
        return width, height, 176, boxes
    raise ValueError(f"Unknown keyboard mode: {mode}")


def label_in_mode(mode, key_id, key_counter, now):
    if mode == "photo":
        return PHOTO_LABELS.get(key_id, key_counter.label(key_id, now) if key_id not in ("1", "2") else key_id)
    if mode == "wasd" and key_id == "space":
        return "SPACE"
    return key_counter.label(key_id, now)
