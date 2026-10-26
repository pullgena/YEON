"""Color palettes, seasonal default and persistent theme-only preference."""
from datetime import date
import json
import os
from pathlib import Path


THEMES = {
    "halloween": {
        "name": "🎃 할로윈 · 호박과 밤",
        "background": "#160D1A", "key": "#281529", "edge": "#F38D36",
        "active": "#E87924", "active_edge": "#FFD08A", "text": "#FFF0DA",
        "count": "#FFC375", "footer": "#302037", "mouse": "#352039",
        "accent": "#A65BDD", "menu": "#291A30", "hover": "#6F327D",
        "pixel": False,
    },
    "minecraft": {
        "name": "⛏ 마인크래프트 · 잔디 블록",
        "background": "#172017", "key": "#343C32", "edge": "#77B84B",
        "active": "#5F9C3B", "active_edge": "#C4EE85", "text": "#FCF9E3",
        "count": "#E0F2B8", "footer": "#483A29", "mouse": "#4E402E",
        "accent": "#91C954", "menu": "#27362A", "hover": "#46633B",
        "pixel": True,
    },
    "classic": {
        "name": "💜 기본 · 퍼플",
        "background": "#080511", "key": "#221633", "edge": "#9657E8",
        "active": "#6737AB", "active_edge": "#E7BCFF", "text": "#FBF5FF",
        "count": "#DECEFA", "footer": "#20152F", "mouse": "#221633",
        "accent": "#B080FF", "menu": "#221832", "hover": "#7949B8",
        "pixel": False,
    },
    "cyber": {
        "name": "⚡ 사이버 · 네온",
        "background": "#06161D", "key": "#10313C", "edge": "#23E6EE",
        "active": "#008D98", "active_edge": "#CCFFFF", "text": "#E6FFFF",
        "count": "#7BFFEE", "footer": "#0C2632", "mouse": "#14323A",
        "accent": "#FF65CD", "menu": "#0E2933", "hover": "#14738B",
        "pixel": False,
    },
    "winter": {
        "name": "❄ 겨울 · 눈꽃",
        "background": "#0B1B2B", "key": "#243F58", "edge": "#75C7FB",
        "active": "#6EBCDE", "active_edge": "#F7FFFF", "text": "#F1FAFF",
        "count": "#C9EBFC", "footer": "#17344C", "mouse": "#274759",
        "accent": "#AFDFF5", "menu": "#1C3851", "hover": "#3E80A8",
        "pixel": False,
    },
    "cherry": {
        "name": "🌸 벚꽃 · 핑크",
        "background": "#21141F", "key": "#382437", "edge": "#F6A3C6",
        "active": "#BA648B", "active_edge": "#FFE5EF", "text": "#FFF2F8",
        "count": "#FFCEE0", "footer": "#382433", "mouse": "#483043",
        "accent": "#FFC6E0", "menu": "#382A39", "hover": "#9B5476",
        "pixel": False,
    },
}

REQUIRED_COLORS = {
    "background", "key", "edge", "active", "active_edge", "text",
    "count", "footer", "mouse", "accent", "menu", "hover",
}


def seasonal_default(today=None):
    """In October, show Halloween until changed; otherwise use purple."""
    today = today or date.today()
    return "halloween" if today.month == 10 else "classic"


def settings_location():
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "YEON" / "KeyView" / "settings.json"
    return Path.home() / ".yeon" / "keyview" / "settings.json"


def load_theme(path=None, today=None):
    """Read only a string theme ID. Invalid/corrupt files fall back safely."""
    path = Path(path) if path is not None else settings_location()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data.get("theme") if isinstance(data, dict) else None
        if isinstance(name, str) and name in THEMES:
            return name
    except (OSError, ValueError, TypeError):
        pass
    return seasonal_default(today)


def save_theme(name, path=None):
    """Only the chosen theme is persisted; no key or mouse input data."""
    if name not in THEMES:
        raise ValueError("Unknown theme")
    path = Path(path) if path is not None else settings_location()
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"theme": name}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def validate_palettes():
    for name, palette in THEMES.items():
        assert REQUIRED_COLORS <= set(palette), name
        for color in REQUIRED_COLORS:
            value = palette[color]
            assert len(value) == 7 and value.startswith("#") and all(
                c in "0123456789abcdefABCDEF" for c in value[1:]
            ), (name, color)
