"""YEON KeyView - compact violet keyboard overlay with visible tray controls."""
import queue
import sys
import threading
import time
import tkinter as tk

import keyboard
import pystray
from PIL import Image, ImageDraw

from keymap import resolve_key
from stats import KeyCounter, label_for

VERSION = "1.1.0"
WIDTH, HEIGHT = 386, 127
PADDING = 3
CELL_GAP = 4
CELL_WIDTH = (WIDTH - 2 * PADDING - 7 * CELL_GAP) / 8
CELL_HEIGHT = 44
BG = "#080511"
CELL_BG = "#231837"
CELL_STROKE = "#9657E8"
CELL_GLOW = "#4C2584"
HELD_BG = "#6737AB"
HELD_BORDER = "#E7BCFF"
TEXT = "#FBF5FF"
COUNT_TEXT = "#DECEFA"


def rounded_box(canvas, x, y, w, h, radius, **kw):
    """Smooth rounded rectangle drawn directly with Tk canvas primitives."""
    r = min(radius, w / 2, h / 2)
    points = [
        x + r, y, x + w - r, y, x + w, y,
        x + w, y + r, x + w, y + h - r, x + w, y + h,
        x + w - r, y + h, x + r, y + h, x, y + h,
        x, y + h - r, x, y + r, x, y,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=12, **kw)


def make_tray_image():
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
            raise RuntimeError("YEON KeyView requires Windows.")
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("YEON KeyView")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)
        self.root.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        x = max(0, screen_w - WIDTH - 34)
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+180")
        self.pinned = True
        self.root.attributes("-topmost", True)
        self.events = queue.SimpleQueue()
        self.commands = queue.SimpleQueue()
        self.counter = KeyCounter()
        self.running = True
        self.capture_enabled = False
        self.hook = None
        self.tray = None
        self.tray_started = False
        self.visible = True
        self.drag_origin = None

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg=BG,
                                highlightthickness=0, bd=0, relief="flat")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        self.menu = tk.Menu(self.root, tearoff=False, bg="#221832", fg=TEXT,
                            activebackground="#7949B8", activeforeground=TEXT)
        self.menu.add_command(label="백그라운드로 숨기기", command=self.hide)
        self.menu.add_command(label="입력 감지 중지 / 다시 시작", command=self.toggle_capture)
        self.menu.add_command(label="항상 위 켜기 / 끄기", command=self.toggle_pin)
        self.menu.add_command(label="카운터 초기화", command=self.clear)
        self.menu.add_separator()
        self.menu.add_command(label="완전히 종료", command=self.exit)

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.install_tray()
        self.set_capture(True)
        self.root.deiconify()
        self.redraw(time.monotonic())
        self.root.after(33, self.tick)

    def install_tray(self):
        def enqueue(action):
            return lambda icon=None, item=None: self.commands.put(action)

        menu = pystray.Menu(
            pystray.MenuItem("YEON KeyView 표시", enqueue("show"), default=True),
            pystray.MenuItem("백그라운드로 숨기기", enqueue("hide")),
            pystray.MenuItem("입력 감지 중지 / 다시 시작", enqueue("capture")),
            pystray.MenuItem("항상 위 켜기 / 끄기", enqueue("pin")),
            pystray.MenuItem("카운터 초기화", enqueue("clear")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("완전히 종료", enqueue("exit")),
        )
        self.tray = pystray.Icon("yeon-keyview", make_tray_image(),
                                 "YEON KeyView - 실행 중", menu)

        def run_tray():
            try:
                self.tray.run()
            except Exception:
                self.commands.put("tray_failed")

        threading.Thread(target=run_tray, name="KeyViewTray",
                         daemon=True).start()
        self.tray_started = True

    def set_capture(self, enabled):
        if self.hook is not None:
            try:
                keyboard.unhook(self.hook)
            except Exception:
                pass
            self.hook = None
        self.capture_enabled = False
        self.counter.release_all()
        self.drain_keyboard_events()
        if enabled:
            try:
                self.hook = keyboard.hook(self.on_keyboard_event, suppress=False)
                self.capture_enabled = True
            except Exception as error:
                print(f"KeyView keyboard hook error: {error}", file=sys.stderr)

    def toggle_capture(self):
        self.set_capture(not self.capture_enabled)

    def on_keyboard_event(self, event):
        # Hook callback is on a worker thread: never call Tkinter from here.
        key_id = resolve_key(getattr(event, "name", None),
                             getattr(event, "scan_code", None),
                             getattr(event, "is_keypad", False))
        if key_id:
            self.events.put((key_id, event.event_type == "down"))

    def drain_keyboard_events(self):
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def tick(self):
        if not self.running:
            return
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                break
            actions = {"show": self.show, "hide": self.hide,
                       "capture": self.toggle_capture, "pin": self.toggle_pin,
                       "clear": self.clear, "exit": self.exit,
                       "tray_failed": self.on_tray_failed}
            actions[command]()
            if not self.running:
                return

        now = time.monotonic()
        for _ in range(500):
            try:
                key_id, pressed = self.events.get_nowait()
            except queue.Empty:
                break
            if self.capture_enabled:
                self.counter.add_event(key_id, pressed, now)
        self.counter.kps(now)
        if self.visible:
            self.redraw(now)
        self.root.after(33, self.tick)

    def redraw(self, now):
        canvas = self.canvas
        canvas.delete("all")
        for i, key_id in enumerate(self.counter.slots):
            x = PADDING + (i % 8) * (CELL_WIDTH + CELL_GAP)
            y = PADDING + (i // 8) * (CELL_HEIGHT + 4)
            hot = self.counter.highlighted(key_id, now)
            rounded_box(canvas, x, y, CELL_WIDTH, CELL_HEIGHT, 5,
                        fill=HELD_BG if hot else CELL_BG,
                        outline=HELD_BORDER if hot else CELL_GLOW,
                        width=3)
            rounded_box(canvas, x + 1, y + 1, CELL_WIDTH - 2, CELL_HEIGHT - 2, 5,
                        fill=HELD_BG if hot else CELL_BG,
                        outline=HELD_BORDER if hot else CELL_STROKE,
                        width=1.6)
            label = label_for(key_id)
            font_size = 15 if len(label) <= 3 else (12 if len(label) <= 5 else 10)
            canvas.create_text(x + CELL_WIDTH / 2, y + 15, text=label,
                               fill=TEXT, font=("Segoe UI", font_size, "bold"))
            canvas.create_text(x + CELL_WIDTH / 2, y + 35,
                               text=str(self.counter.counts.get(key_id, 0)),
                               fill=COUNT_TEXT, font=("Segoe UI", 11, "bold"))
        foot_y = 100
        foot_width = (WIDTH - PADDING * 2 - 4) / 2
        for x in (PADDING, PADDING + foot_width + 4):
            rounded_box(canvas, x, foot_y, foot_width, 24, 4,
                        fill="#20152F", outline=CELL_STROKE, width=1.7)
        canvas.create_text(9, 111.5, anchor="w", text="KPS",
                           fill=TEXT, font=("Segoe UI", 13, "bold"))
        canvas.create_text(PADDING + foot_width - 7, 111.5, anchor="e",
                           text=str(self.counter.kps(now)),
                           fill=TEXT, font=("Segoe UI", 13, "bold"))
        canvas.create_text(PADDING + foot_width + 11, 111.5, anchor="w",
                           text="Total", fill=TEXT, font=("Segoe UI", 13, "bold"))
        canvas.create_text(WIDTH - 11, 111.5, anchor="e",
                           text=str(self.counter.total),
                           fill=TEXT, font=("Segoe UI", 13, "bold"))

    def start_drag(self, event):
        self.drag_origin = (event.x_root - self.root.winfo_x(),
                            event.y_root - self.root.winfo_y())

    def drag(self, event):
        if self.drag_origin is not None:
            x = event.x_root - self.drag_origin[0]
            y = event.y_root - self.drag_origin[1]
            self.root.geometry(f"+{x}+{y}")

    def show_context_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)

    def clear(self):
        self.counter.reset()
        self.drain_keyboard_events()
        if self.visible:
            self.redraw(time.monotonic())

    def show(self):
        self.visible = True
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", self.pinned)

    def hide(self):
        if not self.tray_started:
            return
        self.visible = False
        self.root.withdraw()

    def on_tray_failed(self):
        self.tray_started = False
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
