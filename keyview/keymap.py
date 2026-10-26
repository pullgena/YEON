"""Physical keyboard layout and event-to-key translation (Windows)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class KeySpec:
    id: str
    label: str
    units: float = 1.0
    scan: int | None = None


def K(key_id, label, units=1.0, scan=None):
    return KeySpec(key_id, label, units, scan)


def G(units=1.0):
    return K("_", "", units)


def letters(chars, scans):
    return [K(ch, ch.upper(), scan=sc) for ch, sc in zip(chars, scans)]


MAIN_ROWS = [
    [K("esc", "Esc", scan=1), G(.7)]
    + [K(f"f{i}", f"F{i}", scan=sc) for i, sc in zip(range(1, 5), range(59, 63))]
    + [G(.42)]
    + [K(f"f{i}", f"F{i}", scan=sc) for i, sc in zip(range(5, 9), range(63, 67))]
    + [G(.42)]
    + [K(f"f{i}", f"F{i}", scan=sc) for i, sc in zip(range(9, 13), (67, 68, 87, 88))],
    [K("grave", "~", scan=41)]
    + [K(str(i), str(i), scan=sc) for i, sc in zip((1, 2, 3, 4, 5, 6, 7, 8, 9, 0), range(2, 12))]
    + [K("minus", "-", scan=12), K("equal", "=", scan=13), K("backspace", "Backspace", 2.0, 14)],
    [K("tab", "Tab", 1.55, 15)]
    + letters("qwertyuiop", range(16, 26))
    + [K("lbracket", "[", scan=26), K("rbracket", "]", scan=27), K("backslash", "\\", 1.45, 43)],
    [K("capslock", "Caps Lock", 1.85, 58)]
    + letters("asdfghjkl", range(30, 39))
    + [K("semicolon", ";", scan=39), K("quote", "'", scan=40), K("enter", "Enter", 2.15, 28)],
    [K("lshift", "Shift", 2.35, 42)]
    + letters("zxcvbnm", range(44, 51))
    + [K("comma", ",", scan=51), K("period", ".", scan=52), K("slash", "/", scan=53), K("rshift", "Shift", 2.65, 54)],
    [K("lctrl", "Ctrl", 1.35, 29), K("lwin", "Win", 1.3), K("lalt", "Alt", 1.3, 56),
     K("space", "Space", 6.0, 57), K("ralt", "한/영", 1.3), K("fn", "Fn", 1.1),
     K("menu", "Menu", 1.25), K("rctrl", "한자", 1.4)],
]

NAV_ROWS = [
    [K("printscreen", "PrtSc"), K("scrolllock", "ScrLk", scan=70), K("pause", "Pause")],
    [K("insert", "Ins"), K("home", "Home"), K("pageup", "PgUp")],
    [K("delete", "Del"), K("end", "End"), K("pagedown", "PgDn")],
    [G(), G(), G()],
    [G(), K("up", "↑"), G()],
    [K("left", "←"), K("down", "↓"), K("right", "→")],
]

PAD_ROWS = [
    [K("numlock", "Num", scan=69), K("numslash", "/", scan=53),
     K("nummultiply", "*", scan=55), K("numminus", "-", scan=74)],
    [K("num7", "7", scan=71), K("num8", "8", scan=72),
     K("num9", "9", scan=73), K("numplus", "+", scan=78)],
    [K("num4", "4", scan=75), K("num5", "5", scan=76),
     K("num6", "6", scan=77), G()],
    [K("num1", "1", scan=79), K("num2", "2", scan=80),
     K("num3", "3", scan=81), K("numenter", "Enter")],
    [K("num0", "0", 2.0, 82), K("numdecimal", ".", scan=83), G()],
]

ALL_KEYS = [k for row in MAIN_ROWS + NAV_ROWS + PAD_ROWS for k in row if k.id != "_"]
MAIN_SCANS = {k.scan: k.id for row in MAIN_ROWS for k in row if k.scan is not None}
PAD_SCANS = {k.scan: k.id for row in PAD_ROWS for k in row if k.scan is not None}
NAME_TO_ID = {k.id: k.id for k in ALL_KEYS}
NAME_TO_ID.update({
    "escape": "esc", "esc": "esc", "`": "grave", "backtick": "grave",
    "-": "minus", "=": "equal", "backspace": "backspace",
    "caps lock": "capslock", "capslock": "capslock",
    "left shift": "lshift", "right shift": "rshift", "shift": "lshift",
    "left ctrl": "lctrl", "right ctrl": "rctrl", "ctrl": "lctrl",
    "left control": "lctrl", "right control": "rctrl", "control": "lctrl",
    "left alt": "lalt", "right alt": "ralt", "alt": "lalt", "alt gr": "ralt",
    "left windows": "lwin", "right windows": "lwin", "windows": "lwin",
    "win": "lwin", "space": "space", "spacebar": "space",
    "menu": "menu", "application": "menu", "apps": "menu",
    "hangul": "ralt", "hangeul": "ralt", "한/영": "ralt",
    "hanja": "rctrl", "한자": "rctrl",
    "enter": "enter", "return": "enter", "tab": "tab",
    "[": "lbracket", "]": "rbracket", "\\": "backslash",
    ";": "semicolon", "'": "quote", ",": "comma",
    ".": "period", "/": "slash",
    "print screen": "printscreen", "printscreen": "printscreen", "prtsc": "printscreen",
    "scroll lock": "scrolllock", "pause": "pause", "break": "pause",
    "insert": "insert", "ins": "insert",
    "delete": "delete", "del": "delete",
    "page up": "pageup", "pageup": "pageup", "prior": "pageup",
    "page down": "pagedown", "pagedown": "pagedown", "next": "pagedown",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "num lock": "numlock", "numlock": "numlock",
    "multiply": "nummultiply", "add": "numplus",
    "subtract": "numminus", "divide": "numslash", "decimal": "numdecimal",
    "num enter": "numenter", "numpad enter": "numenter",
})


def resolve_key(name: str | None, scan_code: int | None, is_keypad: bool = False) -> str | None:
    """Return the rendered physical key ID, never a typed text string."""
    normalized = (name or "").strip().lower()
    if normalized in ("right shift", "right ctrl", "right control", "right alt",
                      "alt gr", "hanja", "한자", "hangul", "hangeul", "한/영"):
        return NAME_TO_ID[normalized]
    if normalized == "shift" and scan_code == 54:
        return "rshift"
    if normalized in ("ctrl", "control") and scan_code in (285, 3613):
        return "rctrl"
    if normalized == "alt" and scan_code in (312, 3640):
        return "ralt"
    if is_keypad:
        if normalized in ("enter", "return"):
            return "numenter"
        if scan_code in PAD_SCANS:
            return PAD_SCANS[scan_code]
        if normalized.startswith("num "):
            number = normalized[4:]
            if number.isdigit() and len(number) == 1:
                return "num" + number
    if scan_code in MAIN_SCANS:
        return MAIN_SCANS[scan_code]
    return NAME_TO_ID.get(normalized)
