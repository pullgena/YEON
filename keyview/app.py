"""YEON KeyView v1.3: event-driven canvas, three keyboard modes, background tray."""
import queue
import sys
import threading
import time
import tkinter as tk

import keyboard
import pystray
from PIL import Image, ImageDraw

from keymap import resolve_key
from modes import MODE_NAMES, get_mode_geometry, label_in_mode, mode_for_chord
from stats import KeyCounter

VERSION = "1.3.0"
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


def tray_image():
    image = Image.new("RGBA", (64, 64), "#0B0714")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 5, 59, 59), radius=12,
                           fill="#2B1A46", outline="#A86BFF", width=5)
    draw.line([(21, 17), (21, 47)], fill="#FFFFFF", width=6)
    draw.line([(44, 16), (24, 32), (44, 48)], fill="#FFFFFF", width=6)
    return image


class KeyView:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("YEON KeyView supports Windows only.")

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("YEON KeyView")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)

        self.events = queue.SimpleQueue()
        self.commands = queue.SimpleQueue()
        self.counter = KeyCounter()
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
        self.kps_item = None
        self.total_item = None
        self.last_footer = None
        self.last_painted_at = time.monotonic()
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.window_position = None

        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Button-3>", self.context_menu)

        self.menu = tk.Menu(self.root, tearoff=False, bg="#221832", fg=TEXT,
                            activebackground="#7949B8", activeforeground=TEXT)
        for m, title in (("full", "104키 표시 (Shift+3)"),
                         ("photo", "사진 16키 표시 (Shift+1)"),
                         ("wasd", "WASD + Space 표시 (Shift+2)")):
            self.menu.add_command(label=title, command=lambda value=m: self.set_mode(value))
        self.menu.add_separator()
        self.menu.add_command(label="백그라운드로 숨기기", command=self.hide)
        self.menu.add_command(label="입력 감지 중지 / 시작", command=self.toggle_capture)
        self.menu.add_command(label="항상 위 켜기 / 끄기", command=self.toggle_pin)
        self.menu.add_command(label="카운터 초기화", command=self.reset_counts)
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
            pystray.MenuItem("백그라운드로 숨기기", enqueue("hide")),
            pystray.MenuItem("입력 감지 중지 / 시작", enqueue("capture")),
            pystray.MenuItem("항상 위 켜기 / 끄기", enqueue("pin")),
            pystray.MenuItem("카운터 초기화", enqueue("reset")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("완전히 종료", enqueue("exit")),
        )
        self.tray = pystray.Icon("yeon-keyview", tray_image(),
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
        self.capture_enabled = False
        self.counter.release_all()
        self.drain_events()
        if enabled:
            try:
                self.hook = keyboard.hook(self.on_key, suppress=False)
                self.capture_enabled = True
                self.capture_error = ""
            except Exception as error:
                self.capture_error = type(error).__name__

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
            self.events.put((key_id, event.event_type == "down", time.monotonic()))

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
            "tray_error": self.on_tray_error,
        }
        while True:
            try:
                action = self.commands.get_nowait()
            except queue.Empty:
                break
            if action in MODE_NAMES:
                self.set_mode(action)
            else:
                actions[action]()
            if not self.running:
                return

        target_mode = None
        for _ in range(600):
            try:
                key_id, down, timestamp = self.events.get_nowait()
            except queue.Empty:
                break
            if not self.capture_enabled:
                continue
            held_before = self.counter.held.copy() if down and key_id in ("1", "2", "3") else ()
            is_new = self.counter.add_event(key_id, down, timestamp)
            requested = mode_for_chord(key_id, down, is_new, held_before)
            if requested is not None:
                target_mode = requested
        if target_mode is not None and self.mode != target_mode:
            self.set_mode(target_mode)

        # No full canvas redraw on key events. Only changed Tk item properties
        # are updated; hidden mode does not paint at all.
        if self.visible:
            self.refresh_items(time.monotonic())
        self.root.after(45 if self.visible else 110, self.tick)

    def set_mode(self, mode, preserve_position=True):
        if mode not in MODE_NAMES:
            return
        if preserve_position and self.window_position is None:
            self.window_position = (self.root.winfo_x(), self.root.winfo_y())
        self.mode = mode
        width, height, footer_y, positions = get_mode_geometry(mode)
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
        self.last_footer = None

        def font(size):
            return ("Segoe UI", max(7, round(size * self.scale)), "bold")

        for key_id, (kx, ky, kw, kh) in positions.items():
            held = self.counter.highlighted(key_id, time.monotonic())
            label = label_in_mode(self.mode, key_id, self.counter, time.monotonic())
            outer = rounded_box(self.canvas, kx, ky, kw, kh, 5,
                                fill=ACTIVE_BG if held else KEY_BG,
                                outline=ACTIVE_EDGE if held else KEY_EDGE, width=2.2)
            label_size = 16 if len(label) <= 2 else (12 if len(label) <= 5 else 10)
            if mode == "full":
                label_y = ky + (17 if kh < 60 else kh / 2 - 10)
                count_y = ky + (38 if kh < 60 else kh / 2 + 15)
            else:
                label_y = ky + kh * 0.36
                count_y = ky + kh * 0.79
            text_item = self.canvas.create_text(kx + kw / 2, label_y,
                                                text=label, fill=TEXT,
                                                font=font(label_size))
            count_value = str(self.counter.counts.get(key_id, 0))
            count_item = self.canvas.create_text(kx + kw / 2, count_y,
                                                 text=count_value, fill=COUNT_TEXT,
                                                 font=font(11))
            self.key_items[key_id] = (outer, text_item, count_item)

        side_pad = 3 if mode == "photo" else 12
        footer_w = (width - side_pad * 2 - 5) / 2
        for left in (side_pad, side_pad + footer_w + 5):
            rounded_box(self.canvas, left, footer_y, footer_w,
                        24 if mode == "photo" else 29, 4,
                        fill=FOOT_BG, outline=KEY_EDGE, width=1.8)
        fy = footer_y + (12 if mode == "photo" else 15)
        self.canvas.create_text(side_pad + 8, fy, anchor="w", text="KPS",
                                fill=TEXT, font=font(15))
        self.kps_item = self.canvas.create_text(side_pad + footer_w - 11, fy,
                                                anchor="e", text="0",
                                                fill=TEXT, font=font(15))
        self.canvas.create_text(side_pad + footer_w + 13, fy, anchor="w",
                                text="Total", fill=TEXT, font=font(15))
        self.total_item = self.canvas.create_text(width - side_pad - 10, fy,
                                                  anchor="e", text="0",
                                                  fill=TEXT, font=font(15))
        if self.scale != 1.0:
            self.canvas.scale("all", 0, 0, self.scale, self.scale)
        self.root.title(f"YEON KeyView - {MODE_NAMES[mode]}")
        self.refresh_items(time.monotonic(), force=True)

    def refresh_items(self, now, force=False):
        # Important: no canvas.delete(all), polygon construction or new fonts in loop.
        for key_id, (outer, text_item, count_item) in self.key_items.items():
            active = self.counter.highlighted(key_id, now)
            label = label_in_mode(self.mode, key_id, self.counter, now)
            count = self.counter.counts.get(key_id, 0)
            state = (active, label, count)
            old = self.cached.get(key_id)
            if not force and old == state:
                continue
            if force or old is None or old[0] != active:
                self.canvas.itemconfigure(outer, fill=ACTIVE_BG if active else KEY_BG,
                                          outline=ACTIVE_EDGE if active else KEY_EDGE)
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
        self.drain_events()
        if self.visible:
            self.refresh_items(time.monotonic(), force=True)

    def show(self):
        self.visible = True
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.pinned)
        self.refresh_items(time.monotonic(), force=True)

    def hide(self):
        if not self.tray_available:
            return
        self.visible = False
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
