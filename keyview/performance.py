"""UI scheduling and active-indicator selection, independent of Tkinter."""
def mode_delay(visible, active, optimized=True):
    """Milliseconds between UI wakeups. Minecraft preset is the default."""
    if not visible:
        return 320 if optimized else 180
    if optimized:
        return 64 if active else 140
    return 35 if active else 85


def active_keys_for_refresh(counter, now, visible_keys):
    candidates = counter.held.intersection(visible_keys)
    candidates.update(k for k, expiry in counter.flashes.items()
                      if expiry > now and k in visible_keys)
    candidates.update(k for k, expiry in counter.shifted_flashes.items()
                      if expiry > now and k in visible_keys)
    return candidates


def active_mouse_for_refresh(counter, now, visible_keys):
    candidates = counter.held.intersection(visible_keys)
    candidates.update(k for k, expiry in counter.flashes.items()
                      if expiry > now and k in visible_keys)
    if "move" in visible_keys and counter.highlighted("move", now):
        candidates.add("move")
    return candidates
