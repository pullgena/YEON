"""Mouse strip geometry, sized for all three keyboard layouts."""

PANEL_HEIGHT = 90
ITEM_KEYS = ("left", "middle", "right", "scroll_up", "scroll_down", "move")


def mouse_panel_geometry(keyboard_width, keyboard_height):
    """Return heading rectangle and 6 indicator rectangles below the keyboard."""
    area_width = min(keyboard_width - 6, 535)
    left = (keyboard_width - area_width) / 2
    top = keyboard_height + 7
    heading_width = 68
    gap = 4
    indicator_width = (area_width - heading_width - gap * 6) / len(ITEM_KEYS)
    heading = (left, top, heading_width, 72)
    boxes = {
        name: (
            left + heading_width + gap + i * (indicator_width + gap),
            top + 1, indicator_width, 70,
        )
        for i, name in enumerate(ITEM_KEYS)
    }
    return heading, boxes
