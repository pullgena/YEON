"""Persistent user zoom and safe per-mode resizing without dependencies."""
import json
import os
from pathlib import Path

MIN_ZOOM = 50
MAX_ZOOM = 150
STEP = 5
DEFAULT_ZOOM = 100
PRESETS = (50, 75, 100, 125, 150)


def clamp_zoom(value):
    """Normalize requested percentage to a stable 5% increment."""
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_ZOOM
    if not -1e9 < numeric < 1e9:
        return DEFAULT_ZOOM
    numeric = max(MIN_ZOOM, min(MAX_ZOOM, numeric))
    return int(max(MIN_ZOOM, min(MAX_ZOOM,
                               STEP * int(numeric / STEP + 0.5))))


def fit_scale(width, height, screen_width, screen_height, zoom):
    """Scale content uniformly; prefer specified zoom but never clip the window."""
    if width <= 0 or height <= 0:
        raise ValueError("Invalid overlay size")
    available_w = max(1, screen_width - 32)
    available_h = max(1, screen_height - 84)
    return min(clamp_zoom(zoom) / 100.0,
               available_w / width, available_h / height)


def zoom_settings_path():
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) / "YEON" / "KeyView" if appdata else Path.home() / ".yeon" / "keyview"
    return base / "zoom.json"


def load_zoom(path=None):
    path = Path(path) if path is not None else zoom_settings_path()
    try:
        contents = json.loads(path.read_text(encoding="utf-8"))
        zoom = contents.get("zoom")
        if type(zoom) is int and MIN_ZOOM <= zoom <= MAX_ZOOM and zoom % STEP == 0:
            return zoom
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return DEFAULT_ZOOM


def save_zoom(zoom, path=None):
    zoom = clamp_zoom(zoom)
    path = Path(path) if path is not None else zoom_settings_path()
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"zoom": zoom}), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
