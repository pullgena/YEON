"""YEON KeyView - 104-key purple overlay, Shift glyphs and background tray mode."""
import queue
import sys
import threading
import time
import tkinter as tk

import keyboard
import pystray
from PIL import Image, ImageDraw

from keymap import resolve_key
from layout import WIDTH, HEIGHT, FOOTER_Y, keyboard_rectangles
from stats import KeyCounter

VERSION = "1.2.0"
BG = "#080511"
CELL_BG = "#221633"
CELL_STROKE = "#9A56EE"
CELL_GLOW = "#4C2584"
HELD_BG = "#6636AA"
HELD_BORDER = "#E7BCFF"
TEXT = "#FBF5FF"
COUNT_TEXT = "#DECEFA"


def rounded_box(canvas, x, y, w, h, radius, **kw):
    r = min(radius, w / 2, h / 2)
    points = [
        x + r, y, x + w - r, y, x + w, y,
        x + w, y + r, x + w, y + h - r, x + w, y + h,
        x + w - r, y + h, x + r, y + h, x, y + h,
        x, y + h - r, x, y + r, x, y,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=9, **kw)


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
        self.root.title(f"YEON KeyView {VERSION}")
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)
        self.root.resizable(False, False)

        # 104 keys are all visible, also on smaller laptop displays.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.scale = min(1.0, max(0.45, (screen_w - 48) / WIDTH),
                         max(0.45, (screen_h - 90) / HEIGHT))
        self.display_w = round(WIDTH * self.scale)
        self.display_h = round(HEIGHT * self.scale)
        x = max(0, screen_w - self.display_w - 24)
        y = max(0, min(180, screen_h - self.display_h - 64))
        self.root.geometry(f"{self.display_w}x{self.display_h}+{x}+{y}")
        self.root.attributes("-topmost", True)

        self.pinned = True
        self.events = queue.SimpleQueue()
        self.commands = queue.SimpleQueue()
        self.counter = KeyCounter()
        self.key_rects = keyboard_rectangles()
        self.running = True
        self.capture_enabled = False
        self.hook = None
        self.tray = None
        self.tray_started = False
        self.visible = True
        self.drag_origin = None
        self.capture_error = ""

        self.canvas = tk.Canvas(self.root, width=self.display_w,
                                height=self.display_h, bg=BG,
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
        self.root.after(50, self.tick)

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
                self.capture_error = ""
            except Exception as error:
                self.capture_error = type(error).__name__

    def toggle_capture(self):
        self.set_capture(not self.capture_enabled)

    def on_keyboard_event(self, event):
        # The keyboard library invokes this callback off the Tkinter UI thread.
        key_id = resolve_key(getattr(event, "name", None),
                             getattr(event, "scan_code", None),
                             getattr(event, "is_keypad", False))
        if key_id:
            self.events.put((key_id, event.event_type == "down", time.monotonic()))

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

        for _ in range(700):
            try:
                key_id, pressed, event_time = self.events.get_nowait()
            except queue.Empty:
                break
            if self.capture_enabled:
                self.counter.add_event(key_id, pressed, event_time)

        now = time.monotonic()
        self.counter.kps(now)
        if self.visible:
            self.redraw(now)
        self.root.after(50, self.tick)

    def redraw(self, now):
        canvas = self.canvas
        canvas.delete("all")

        def font(size, bold=True):
            return ("Segoe UI", max(7, round(size * self.scale)),
                    "bold" if bold else "normal")

        for key_id, (x, y, width, height) in self.key_rects.items():
            hot = self.counter.highlighted(key_id, now)
            rounded_box(canvas, x, y, width, height, 5,
                        fill=HELD_BG if hot else CELL_BG,
                        outline=HELD_BORDER if hot else CELL_GLOW,
                        width=2.7)
            rounded_box(canvas, x + 1, y + 1, width - 2, height - 2, 4,
                        fill=HELD_BG if hot else CELL_BG,
                        outline=HELD_BORDER if hot else CELL_STROKE,
                        width=1.2)
            label = self.counter.label(key_id, now)
            label_size = 16 if len(label) <= 2 else (12 if len(label) <= 5 else 10)
            label_y = y + (17 if height < 60 else height / 2 - 10)
            count_y = y + (38 if height < 60 else height / 2 + 15)
            canvas.create_text(x + width / 2, label_y, text=label,
                               fill=TEXT, font=font(label_size))
            canvas.create_text(x + width / 2, count_y,
                               text=str(self.counter.counts.get(key_id, 0)),
                               fill=COUNT_TEXT, font=font(10))

        footer_x = 12
        footer_width = (WIDTH - 2 * footer_x - 8) / 2
        for left in (footer_x, footer_x + footer_width + 8):
            rounded_box(canvas, left, FOOTER_Y, footer_width, 29, 4,
                        fill="#20152F", outline=CELL_STROKE, width=1.8)

        canvas.create_text(footer_x + 10, FOOTER_Y + 15, anchor="w",
                           text="KPS", fill=TEXT, font=font(16))
        canvas.create_text(footer_x + footer_width - 14, FOOTER_Y + 15, anchor="e",
                           text=str(self.counter.kps(now)), fill=TEXT, font=font(16))
        canvas.create_text(footer_x + footer_width + 18, FOOTER_Y + 15,
                           anchor="w", text="Total", fill=TEXT, font=font(16))
        canvas.create_text(WIDTH - footer_x - 14, FOOTER_Y + 15,
                           anchor="e", text=str(self.counter.total),
                           fill=TEXT, font=font(16))
        if self.capture_error:
            canvas.create_text(WIDTH / 2, HEIGHT - 7, anchor="s",
                               text="키 입력 감지를 시작할 수 없습니다: " + self.capture_error,
                               fill="#FF8DA0", font=font(9))
        # Canvas item coordinates must be scaled to the actual window dimensions.
        if self.scale != 1.0:
            canvas.scale("all", 0, 0, self.scale, self.scale)

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
