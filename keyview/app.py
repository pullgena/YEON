"""YEON KeyView v1.6: Minecraft-friendly low-CPU input overlay."""
import ctypes
import queue
import sys
import threading
import time
import tkinter as tk

import keyboard
import pystray
from pynput import mouse as mouse_hook
from PIL import Image, ImageDraw

from keymap import resolve_key
from modes import MODE_NAMES, get_mode_geometry, label_in_mode, mode_for_chord
from mouse_panel import PANEL_HEIGHT, mouse_panel_geometry
from mouse_stats import MouseCounter, MOUSE_LABELS
from stats import KeyCounter, SHIFTED_LABELS
from performance import mode_delay, active_keys_for_refresh, active_mouse_for_refresh
from themes import THEMES, load_theme, save_theme

VERSION = "1.6.0"
BG = "#080511"
KEY_BG = "#221633"
KEY_EDGE = "#9657E8"
ACTIVE_BG = "#6737AB"
ACTIVE_EDGE = "#E7BCFF"
TEXT = "#FBF5FF"
COUNT_TEXT = "#DECEFA"
FOOT_BG = "#20152F"


def rounded_box(canvas, x, y, w, h, radius, **kw):
    """Rounded polygon drawn once, not recreated each animation frame."""
    r = min(radius, w / 2, h / 2)
    points = [
        x + r, y, x + w - r, y, x + w, y,
        x + w, y + r, x + w, y + h - r, x + w, y + h,
        x + w - r, y + h, x + r, y + h, x, y + h,
        x, y + h - r, x, y + r, x, y,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=8, **kw)


def tray_image(palette):
    image = Image.new("RGBA", (64, 64), palette["background"])
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 5, 59, 59), radius=0 if palette["pixel"] else 12,
                           fill=palette["key"], outline=palette["edge"], width=5)
    draw.line([(21, 17), (21, 47)], fill=palette["text"], width=6)
    draw.line([(44, 16), (24, 32), (44, 48)], fill=palette["text"], width=6)
    return image


class KeyView:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("YEON KeyView supports Windows only.")

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("YEON KeyView")
        self.root.overrideredirect(True)
        self.theme = load_theme()
        self.palette = THEMES[self.theme]
        self.theme_choice = tk.StringVar(master=self.root, value=self.theme)
        self.root.configure(bg=self.palette["background"])

        self.events = queue.SimpleQueue()
        self.commands = queue.SimpleQueue()
        self.counter = KeyCounter()
        self.mouse_counter = MouseCounter()
        self.last_pointer_position = None
        self.next_mouse_poll = 0.0
        self.mouse_listener = None
        self.game_optimized = True
        self.mouse_passthrough = False
        self.previous_hot_keys = set()
        self.previous_hot_mouse = set()
        self.mode = "full"
        self.running = True
        self.visible = True
        self.pinned = True
        self.capture_enabled = False
        self.capture_error = ""
        self.hook = None
        self.tray = None
        self.tray_available = False
        self.drag_origin = None
        self.key_items = {}
        self.cached = {}
        self.mouse_items = {}
        self.cached_mouse = {}
        self.mouse_total_item = None
        self.last_mouse_total = None
        self.kps_item = None
        self.total_item = None
        self.last_footer = None
        self.last_painted_at = time.monotonic()
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.window_position = None

        self.canvas = tk.Canvas(self.root, bg=self.palette["background"], highlightthickness=0, bd=0)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Button-3>", self.context_menu)

        self.menu = tk.Menu(self.root, tearoff=False, bg=self.palette["menu"],
                            fg=self.palette["text"],
                            activebackground=self.palette["hover"],
                            activeforeground=self.palette["text"])
        for m, title in (("full", "104키 표시 (Shift+3)"),
                         ("photo", "사진 16키 표시 (Shift+1)"),
                         ("wasd", "WASD + Space 표시 (Shift+2)")):
            self.menu.add_command(label=title, command=lambda value=m: self.set_mode(value))
        self.menu.add_separator()
        self.theme_menu = tk.Menu(self.menu, tearoff=False, bg=self.palette["menu"],
                                  fg=self.palette["text"],
                                  activebackground=self.palette["hover"],
                                  activeforeground=self.palette["text"])
        for theme_id, theme_data in THEMES.items():
            self.theme_menu.add_radiobutton(
                label=theme_data["name"], variable=self.theme_choice,
                value=theme_id, command=lambda value=theme_id: self.set_theme(value))
        self.menu.add_cascade(label="테마 변경", menu=self.theme_menu)
        self.menu.add_separator()
        self.menu.add_command(label="백그라운드로 숨기기", command=self.hide)
        self.menu.add_command(label="입력 감지 중지 / 시작", command=self.toggle_capture)
        self.menu.add_command(label="항상 위 켜기 / 끄기", command=self.toggle_pin)
        self.menu.add_command(label="마인크래프트 최적화 모드 켜기 / 끄기", command=self.toggle_game_mode)
        self.menu.add_command(label="마우스 클릭 통과 켜기 / 끄기 (트레이에서 해제)", command=self.toggle_passthrough)
        self.menu.add_command(label="키보드·마우스 카운터 초기화", command=self.reset_counts)
        self.menu.add_separator()
        self.menu.add_command(label="완전히 종료", command=self.exit)

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.set_mode("full", preserve_position=False)
        self.install_tray()
        self.set_capture(True)
        self.root.deiconify()
        self.root.after(35, self.tick)

    def install_tray(self):
        def enqueue(command):
            return lambda icon=None, item=None: self.commands.put(command)

        menu = pystray.Menu(
            pystray.MenuItem("가상 키보드 보이기", enqueue("show"), default=True),
            pystray.MenuItem("104키 (Shift+3)", enqueue("full")),
            pystray.MenuItem("사진 16키 (Shift+1)", enqueue("photo")),
            pystray.MenuItem("WASD + Space (Shift+2)", enqueue("wasd")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("테마 변경", pystray.Menu(
                *[pystray.MenuItem(data["name"], enqueue("theme:" + key),
                                  checked=lambda item, expected=key: self.theme == expected,
                                  radio=True)
                  for key, data in THEMES.items()]
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("백그라운드로 숨기기", enqueue("hide")),
            pystray.MenuItem("입력 감지 중지 / 시작", enqueue("capture")),
            pystray.MenuItem("항상 위 켜기 / 끄기", enqueue("pin")),
            pystray.MenuItem("마인크래프트 최적화 모드", enqueue("gaming"),
                             checked=lambda item: self.game_optimized),
            pystray.MenuItem("마우스 클릭 통과 (트레이에서 해제)", enqueue("passthrough"),
                             checked=lambda item: self.mouse_passthrough),
            pystray.MenuItem("키보드·마우스 카운터 초기화", enqueue("reset")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("완전히 종료", enqueue("exit")),
        )
        self.tray = pystray.Icon("yeon-keyview", tray_image(self.palette),
                                 "YEON KeyView - 실행 중", menu)

        def worker():
            try:
                self.tray.run()
            except Exception:
                self.commands.put("tray_error")

        threading.Thread(target=worker, daemon=True,
                         name="KeyViewTray").start()
        self.tray_available = True

    def set_capture(self, enabled):
        if self.hook is not None:
            try:
                keyboard.unhook(self.hook)
            except Exception:
                pass
            self.hook = None
        if self.mouse_listener is not None:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
            self.mouse_listener = None
        self.capture_enabled = False
        self.last_pointer_position = None
        self.counter.release_all()
        self.mouse_counter.release_all()
        self.drain_events()
        if enabled:
            errors = []
            try:
                self.hook = keyboard.hook(self.on_key, suppress=False)
            except Exception as error:
                errors.append("Keyboard: " + type(error).__name__)
            try:
                listener = mouse_hook.Listener(
                    on_click=self.on_mouse_click,
                    on_scroll=self.on_mouse_scroll,
                    # No high-frequency on_move callback; poll cursor occasionally.
                    # Minecraft 26.3 uses relative mouse movement in-game.
                )
                listener.start()
                self.mouse_listener = listener
            except Exception as error:
                errors.append("Mouse: " + type(error).__name__)
            self.capture_enabled = self.hook is not None or self.mouse_listener is not None
            self.capture_error = ", ".join(errors)

    def toggle_capture(self):
        self.set_capture(not self.capture_enabled)
        if self.visible:
            self.refresh_items(time.monotonic(), force=True)

    def on_key(self, event):
        # The Windows hook callback must not touch Tk controls.
        key_id = resolve_key(getattr(event, "name", None),
                             getattr(event, "scan_code", None),
                             getattr(event, "is_keypad", False))
        if key_id:
            self.events.put(("key", key_id, event.event_type == "down", time.monotonic()))

    def on_mouse_click(self, x, y, button, pressed):
        # Screen coordinates are intentionally ignored: never record the pointer path.
        if not self.capture_enabled:
            return
        name = getattr(button, "name", "")
        if name in ("left", "middle", "right"):
            self.events.put(("mouse_button", name, pressed, time.monotonic()))

    def on_mouse_scroll(self, x, y, dx, dy):
        if self.capture_enabled and dy:
            self.events.put(("mouse_scroll",
                             "scroll_up" if dy > 0 else "scroll_down",
                             True, time.monotonic()))

    def sample_pointer(self, now):
        """Low-frequency cursor sampling avoids costly hook callbacks during gaming."""
        if now < self.next_mouse_poll:
            return False
        self.next_mouse_poll = now + (0.24 if self.game_optimized else 0.14)
        try:
            current = self.root.winfo_pointerxy()
        except tk.TclError:
            return False
        if self.last_pointer_position is None:
            self.last_pointer_position = current
            return False
        moved = current != self.last_pointer_position
        self.last_pointer_position = current
        if moved:
            self.mouse_counter.add_motion(now)
        return moved

    def drain_events(self):
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def tick(self):
        if not self.running:
            return
        actions = {
            "show": self.show, "hide": self.hide, "capture": self.toggle_capture,
            "pin": self.toggle_pin, "reset": self.reset_counts, "exit": self.exit,
            "gaming": self.toggle_game_mode, "passthrough": self.toggle_passthrough,
            "tray_error": self.on_tray_error,
        }
        while True:
            try:
                action = self.commands.get_nowait()
            except queue.Empty:
                break
            if action in MODE_NAMES:
                self.set_mode(action)
            elif action.startswith("theme:"):
                self.set_theme(action.split(":", 1)[1])
            else:
                actions[action]()
            if not self.running:
                return

        target_mode = None
        dirty_keys = set()
        dirty_mouse = set()
        for _ in range(500):
            try:
                kind, key_id, down, timestamp = self.events.get_nowait()
            except queue.Empty:
                break
            if not self.capture_enabled:
                continue
            if kind == "mouse_button":
                if self.mouse_counter.add_button(key_id, down, timestamp):
                    dirty_mouse.add(key_id)
            elif kind == "mouse_scroll":
                if self.mouse_counter.add_scroll(key_id, timestamp):
                    dirty_mouse.add(key_id)
            elif kind == "key":
                held_before = self.counter.held if down and key_id in ("1", "2", "3") else ()
                changed = self.counter.add_event(key_id, down, timestamp)
                if changed:
                    dirty_keys.add(key_id)
                    if key_id in ("lshift", "rshift"):
                        dirty_keys.update(SHIFTED_LABELS)
                requested = mode_for_chord(key_id, down, changed, held_before)
                if requested is not None:
                    target_mode = requested
        if target_mode is not None and self.mode != target_mode:
            self.set_mode(target_mode)

        now = time.monotonic()
        self.counter.kps(now)
        if self.visible:
            if self.capture_enabled and self.sample_pointer(now):
                dirty_mouse.add("move")
            # Only pressed or fading keys need repeated checks. In particular,
            # idle 104-key views no longer walk all 104 Tk items every frame.
            hot_keys = active_keys_for_refresh(self.counter, now, self.key_items)
            dirty_keys.update(hot_keys)
            dirty_keys.update(self.previous_hot_keys)
            self.previous_hot_keys = hot_keys

            hot_mouse = active_mouse_for_refresh(self.mouse_counter, now, self.mouse_items)
            dirty_mouse.update(hot_mouse)
            dirty_mouse.update(self.previous_hot_mouse)
            self.previous_hot_mouse = hot_mouse

            self.refresh_items(now, key_ids=dirty_keys, mouse_ids=dirty_mouse)
        # 16 FPS during visual activity; idle frames are slower, hidden 3-4Hz.
        delay = mode_delay(self.visible, bool(dirty_keys or dirty_mouse), self.game_optimized)
        self.root.after(delay, self.tick)

    def set_mode(self, mode, preserve_position=True):
        if mode not in MODE_NAMES:
            return
        if preserve_position and self.window_position is None:
            self.window_position = (self.root.winfo_x(), self.root.winfo_y())
        self.mode = mode
        width, keyboard_height, footer_y, positions = get_mode_geometry(mode)
        height = keyboard_height + PANEL_HEIGHT
        self.logical_w = width
        self.logical_h = height
        self.scale = min(1.0, (self.screen_w - 30) / width,
                         (self.screen_h - 90) / height)
        self.scale = max(0.35, self.scale)
        pixel_w = round(width * self.scale)
        pixel_h = round(height * self.scale)

        if preserve_position and self.window_position is not None:
            x, y = self.window_position
            x = max(0, min(x, self.screen_w - pixel_w))
            y = max(0, min(y, self.screen_h - pixel_h))
        else:
            x = max(0, self.screen_w - pixel_w - 25)
            y = max(0, min(180, self.screen_h - pixel_h - 65))
        self.window_position = (x, y)
        self.root.geometry(f"{pixel_w}x{pixel_h}+{x}+{y}")
        self.canvas.configure(width=pixel_w, height=pixel_h)
        self.canvas.delete("all")
        self.key_items.clear()
        self.cached.clear()
        self.previous_hot_keys.clear()
        self.previous_hot_mouse.clear()
        self.mouse_items.clear()
        self.cached_mouse.clear()
        self.last_mouse_total = None
        self.last_footer = None

        def font(size):
            family = "Consolas" if self.palette["pixel"] else "Segoe UI"
            return (family, max(7, round(size * self.scale)), "bold")

        for key_id, (kx, ky, kw, kh) in positions.items():
            held = self.counter.highlighted(key_id, time.monotonic())
            label = label_in_mode(self.mode, key_id, self.counter, time.monotonic())
            outer = rounded_box(self.canvas, kx, ky, kw, kh,
                                0 if self.palette["pixel"] else 5,
                                fill=self.palette["active"] if held else self.palette["key"],
                                outline=self.palette["active_edge"] if held else self.palette["edge"],
                                width=2.2)
            label_size = 16 if len(label) <= 2 else (12 if len(label) <= 5 else 10)
            if mode == "full":
                label_y = ky + (17 if kh < 60 else kh / 2 - 10)
                count_y = ky + (38 if kh < 60 else kh / 2 + 15)
            else:
                label_y = ky + kh * 0.36
                count_y = ky + kh * 0.79
            text_item = self.canvas.create_text(kx + kw / 2, label_y,
                                                text=label, fill=self.palette["text"],
                                                font=font(label_size))
            count_value = str(self.counter.counts.get(key_id, 0))
            count_item = self.canvas.create_text(kx + kw / 2, count_y,
                                                 text=count_value, fill=self.palette["count"],
                                                 font=font(11))
            self.key_items[key_id] = (outer, text_item, count_item)

        side_pad = 3 if mode == "photo" else 12
        footer_w = (width - side_pad * 2 - 5) / 2
        for left in (side_pad, side_pad + footer_w + 5):
            rounded_box(self.canvas, left, footer_y, footer_w,
                        24 if mode == "photo" else 29, 4,
                        fill=self.palette["footer"], outline=self.palette["edge"],
                        width=1.8)
        fy = footer_y + (12 if mode == "photo" else 15)
        self.canvas.create_text(side_pad + 8, fy, anchor="w", text="KPS",
                                fill=self.palette["text"], font=font(15))
        self.kps_item = self.canvas.create_text(side_pad + footer_w - 11, fy,
                                                anchor="e", text="0",
                                                fill=self.palette["text"], font=font(15))
        self.canvas.create_text(side_pad + footer_w + 13, fy, anchor="w",
                                text="Total", fill=self.palette["text"], font=font(15))
        self.total_item = self.canvas.create_text(width - side_pad - 10, fy,
                                                  anchor="e", text="0",
                                                  fill=self.palette["text"], font=font(15))

        # Separate purple mouse panel, kept in all three keyboard modes.
        # Theme accent drawn only when the mode/theme changes, never per tick.
        self.canvas.create_rectangle(0, keyboard_height + 1, width, keyboard_height + 4,
                                     fill=self.palette["accent"], outline="")
        heading, mouse_boxes = mouse_panel_geometry(width, keyboard_height)
        hx, hy, hw, hh = heading
        rounded_box(self.canvas, hx, hy, hw, hh, 5,
                    fill=self.palette["footer"], outline=self.palette["edge"],
                    width=1.7)
        self.canvas.create_text(hx + hw / 2, hy + 22, text="MOUSE",
                                fill=self.palette["text"], font=font(12))
        self.mouse_total_item = self.canvas.create_text(
            hx + hw / 2, hy + 50, text="0", fill=self.palette["count"], font=font(15))
        for mouse_key, (mx, my, mw, mh) in mouse_boxes.items():
            shape = rounded_box(self.canvas, mx, my, mw, mh,
                                0 if self.palette["pixel"] else 5,
                                fill=self.palette["mouse"],
                                outline=self.palette["edge"], width=1.8)
            text_label = self.canvas.create_text(
                mx + mw / 2, my + 22, text=MOUSE_LABELS[mouse_key],
                fill=self.palette["text"],
                font=font(11 if mouse_key != "move" else 9))
            text_count = self.canvas.create_text(
                mx + mw / 2, my + mh - 13,
                text="·" if mouse_key == "move" else "0",
                fill=self.palette["count"], font=font(12))
            self.mouse_items[mouse_key] = (shape, text_label, text_count)
        if self.scale != 1.0:
            self.canvas.scale("all", 0, 0, self.scale, self.scale)
        self.root.title(f"YEON KeyView - {MODE_NAMES[mode]}")
        self.refresh_items(time.monotonic(), force=True)

    def refresh_items(self, now, force=False, key_ids=None, mouse_ids=None):
        # Update only keys touched by events or fading highlights; never redraw
        # the entire canvas unless switching modes or themes.
        if force or key_ids is None:
            key_ids = self.key_items.keys()
        if force or mouse_ids is None:
            mouse_ids = self.mouse_items.keys()
        for key_id in key_ids:
            items = self.key_items.get(key_id)
            if items is None:
                continue
            outer, text_item, count_item = items
            active = self.counter.highlighted(key_id, now)
            label = label_in_mode(self.mode, key_id, self.counter, now)
            count = self.counter.counts.get(key_id, 0)
            state = (active, label, count)
            old = self.cached.get(key_id)
            if not force and old == state:
                continue
            if force or old is None or old[0] != active:
                self.canvas.itemconfigure(outer,
                                          fill=self.palette["active"] if active else self.palette["key"],
                                          outline=self.palette["active_edge"] if active else self.palette["edge"])
            if force or old is None or old[1] != label:
                self.canvas.itemconfigure(text_item, text=label)
            if force or old is None or old[2] != count:
                self.canvas.itemconfigure(count_item, text=str(count))
            self.cached[key_id] = state
        footer = (self.counter.kps(now), self.counter.total)
        if force or footer != self.last_footer:
            self.canvas.itemconfigure(self.kps_item, text=str(footer[0]))
            self.canvas.itemconfigure(self.total_item, text=str(footer[1]))
            self.last_footer = footer

        for mouse_key in mouse_ids:
            items = self.mouse_items.get(mouse_key)
            if items is None:
                continue
            shape, label_item, count_item = items
            active = self.mouse_counter.highlighted(mouse_key, now)
            value = ("●" if active else "·") if mouse_key == "move" else self.mouse_counter.counts[mouse_key]
            state = (active, value)
            old = self.cached_mouse.get(mouse_key)
            if force or old != state:
                if force or old is None or old[0] != active:
                    self.canvas.itemconfigure(
                        shape,
                        fill=self.palette["active"] if active else self.palette["mouse"],
                        outline=self.palette["active_edge"] if active else self.palette["edge"])
                if force or old is None or old[1] != value:
                    self.canvas.itemconfigure(count_item, text=str(value))
                self.cached_mouse[mouse_key] = state
        if force or self.last_mouse_total != self.mouse_counter.total:
            self.canvas.itemconfigure(self.mouse_total_item, text=str(self.mouse_counter.total))
            self.last_mouse_total = self.mouse_counter.total

    def toggle_game_mode(self):
        self.game_optimized = not self.game_optimized
        if self.tray is not None:
            try:
                self.tray.update_menu()
            except Exception:
                pass

    def toggle_passthrough(self):
        """Allow Minecraft to receive clicks through the optional overlay."""
        desired = not self.mouse_passthrough
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetAncestor(int(self.root.winfo_id()), 2)  # GA_ROOT
            if not hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x20
            WS_EX_LAYERED = 0x80000
            current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if desired:
                updated = current | WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                updated = current & ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, updated)
            # Preserve size/position and activate newly applied nonclient style.
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
            self.mouse_passthrough = desired
            if self.tray is not None:
                self.tray.update_menu()
        except (OSError, ValueError, AttributeError):
            self.mouse_passthrough = False

    def set_theme(self, theme_id):
        """Apply the selected palette and save only its ID locally."""
        if theme_id not in THEMES:
            return
        self.theme = theme_id
        self.palette = THEMES[theme_id]
        self.theme_choice.set(theme_id)
        self.root.configure(bg=self.palette["background"])
        self.canvas.configure(bg=self.palette["background"])
        for menu in (self.menu, self.theme_menu):
            menu.configure(bg=self.palette["menu"], fg=self.palette["text"],
                           activebackground=self.palette["hover"],
                           activeforeground=self.palette["text"])
        if self.tray is not None:
            try:
                self.tray.icon = tray_image(self.palette)
                self.tray.update_menu()
            except Exception:
                pass
        save_theme(theme_id)
        self.set_mode(self.mode)

    def start_drag(self, event):
        self.drag_origin = (event.x_root - self.root.winfo_x(),
                            event.y_root - self.root.winfo_y())

    def drag(self, event):
        if self.drag_origin is not None:
            x = event.x_root - self.drag_origin[0]
            y = event.y_root - self.drag_origin[1]
            self.window_position = (x, y)
            self.root.geometry(f"+{x}+{y}")

    def context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)

    def reset_counts(self):
        self.counter.reset()
        self.mouse_counter.reset()
        self.last_pointer_position = None
        self.previous_hot_keys.clear()
        self.previous_hot_mouse.clear()
        self.drain_events()
        if self.visible:
            self.refresh_items(time.monotonic(), force=True)

    def show(self):
        self.visible = True
        self.last_pointer_position = None
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.pinned)
        self.refresh_items(time.monotonic(), force=True)

    def hide(self):
        if not self.tray_available:
            return
        self.visible = False
        self.last_pointer_position = None
        self.root.withdraw()

    def on_tray_error(self):
        self.tray_available = False
        if not self.visible:
            self.show()

    def exit(self):
        if not self.running:
            return
        self.running = False
        self.set_capture(False)
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    KeyView().run()
