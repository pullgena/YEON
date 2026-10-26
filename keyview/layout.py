"""Pixel positions for every key on an ANSI 104-key keyboard."""
from keymap import MAIN_ROWS, NAV_ROWS, PAD_ROWS, ALL_KEYS

WIDTH = 1280
HEIGHT = 386
PITCH = 55
KEY_HEIGHT = 48
GAP = 5
MAIN_X = 12
NAV_X = 863
PAD_X = 1050
TOP = 12
FOOTER_Y = 346
NAV_ROW_OFFSETS = (0, 2, 3, 0, 4, 5)


def keyboard_rectangles():
    """Return {physical_key_id: (x, y, width, height)} for all 104 keys."""
    rectangles = {}

    def put(rows, origin_x, row_offsets, pad=False):
        for row_index, row in enumerate(rows):
            x = origin_x
            y = TOP + row_offsets[row_index] * PITCH
            for spec in row:
                if spec.id != "_":
                    w = PITCH * spec.units - GAP
                    h = KEY_HEIGHT
                    # Conventional vertical two-row numpad + and Enter keys.
                    if pad and spec.id in ("numplus", "numenter"):
                        h = KEY_HEIGHT + PITCH
                    if spec.id in rectangles:
                        raise ValueError(f"Duplicate key: {spec.id}")
                    rectangles[spec.id] = (x, y, w, h)
                x += spec.units * PITCH

    put(MAIN_ROWS, MAIN_X, range(6))
    put(NAV_ROWS, NAV_X, NAV_ROW_OFFSETS)
    put(PAD_ROWS, PAD_X, range(1, 6), pad=True)

    expected = {key.id for key in ALL_KEYS}
    if len(rectangles) != 104 or set(rectangles) != expected:
        raise ValueError(f"Invalid ANSI keyboard: {len(rectangles)} keys")
    return rectangles
