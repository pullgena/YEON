"""YEON KeyView — real-time, read-only virtual keyboard visualizer for Windows."""
import queue
import sys
import tkinter as tk

import keyboard

from keymap import MAIN_ROWS, NAV_ROWS, PAD_ROWS, ALL_KEYS, resolve_key

VERSION = "1.0.0"
BG = "#0B1020"
PANEL = "#101B30"
KEY_BG = "#202D45"
KEY_OUTLINE = "#344564"
KEY_TEXT = "#E2EAF8"
ACTIVE_BG = "#53D9FF"
ACTIVE_TEXT = "#071522"
SUBTLE = "#9FAFCB"
ACCENT = "#74E0FC"
DANGER = "#FF828F"
PITCH = 51
HEIGHT = 45
BASE_WIDTH = 1192
BASE_HEIGHT = 338


class KeyView:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("YEON KeyView currently supports Windows only.")

        self.root = tk.Tk()
        self.root.title(f"YEON KeyView  v{VERSION}")
        self.root.geometry("1280x470")
        self.root.minsize(930, 380)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)

        self.events = queue.SimpleQueue()
        self.held = set()
        self.rectangles = {}
        self.labels = {}
        self.key_labels = {k.id: k.label for k in ALL_KEYS}
        self.hook = None
        self.enabled = False
        self.pinned = True
        self.draw_task = None

        top = tk.Frame(self.root, bg=BG, padx=24, pady=18)
        top.pack(fill="x")
        title_box = tk.Frame(top, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text="YEON  /  KEYVIEW", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(title_box, text="실제 키보드 입력을 가상 키보드에서 실시간으로 표시합니다.",
                 bg=BG, fg=SUBTLE, font=("Malgun Gothic", 10)).pack(anchor="w", pady=(3, 0))

        tools = tk.Frame(top, bg=BG)
        tools.pack(side="right")
        self.pin_button = self.make_button(tools, "항상 위: 켜짐", self.toggle_pin)
        self.pin_button.pack(side="left", padx=5)
        self.reset_button = self.make_button(tools, "키 초기화", self.reset_keys)
        self.reset_button.pack(side="left", padx=5)
        self.capture_button = self.make_button(tools, "입력 감지 중지", self.toggle_capture, primary=True)
        self.capture_button.pack(side="left", padx=5)

        board_frame = tk.Frame(self.root, bg=PANEL, highlightbackground="#23334F",
                               highlightthickness=1, padx=5, pady=6)
        board_frame.pack(fill="both", expand=True, padx=20, pady=(0, 9))
        self.canvas = tk.Canvas(board_frame, bg=PANEL, highlightthickness=0,
                                borderwidth=0, relief="flat")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.schedule_draw)

        bottom = tk.Frame(self.root, bg=BG, padx=24, pady=9)
        bottom.pack(fill="x")
        self.status = tk.Label(bottom, text="● 준비 중", bg=BG, fg=ACCENT,
                               font=("Malgun Gothic", 10))
        self.status.pack(side="left")
        self.recent = tk.Label(bottom, text="마지막 키: —", bg=BG, fg=SUBTLE,
                               font=("Malgun Gothic", 10))
        self.recent.pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.set_capture(True)
        self.root.after(16, self.pump)

    @staticmethod
    def make_button(parent, label, command, primary=False):
        return tk.Button(parent, text=label, command=command, cursor="hand2",
                         relief="flat", bd=0, padx=13, pady=9,
                         bg=ACTIVE_BG if primary else KEY_BG,
                         fg=ACTIVE_TEXT if primary else KEY_TEXT,
                         activebackground="#A7EBFF" if primary else "#3A4E70",
                         activeforeground=ACTIVE_TEXT if primary else KEY_TEXT,
                         font=("Malgun Gothic", 9, "bold"))

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned)
        self.pin_button.configure(text=f"항상 위: {'켜짐' if self.pinned else '꺼짐'}")

    def toggle_capture(self):
        self.set_capture(not self.enabled)

    def set_capture(self, value):
        if value:
            try:
                self.hook = keyboard.hook(self.on_keyboard_event, suppress=False)
                self.enabled = True
                self.capture_button.configure(text="입력 감지 중지")
                self.status.configure(text="● 모든 창의 키 입력 감지 중", fg=ACCENT)
            except Exception as error:
                self.hook = None
                self.enabled = False
                self.status.configure(text=f"● 키보드 감지 실패: {type(error).__name__}", fg=DANGER)
                self.capture_button.configure(text="감지 다시 시작")
        else:
            if self.hook is not None:
                try:
                    keyboard.unhook(self.hook)
                except Exception:
                    pass
                self.hook = None
            self.enabled = False
            self.reset_keys()
            self.capture_button.configure(text="입력 감지 시작")
            self.status.configure(text="● 감지 일시 중지", fg=SUBTLE)

    def on_keyboard_event(self, event):
        # The hook runs in a worker thread. Never call Tk from this thread.
        key_id = resolve_key(getattr(event, "name", None),
                             getattr(event, "scan_code", None),
                             getattr(event, "is_keypad", False))
        if key_id:
            self.events.put((key_id, event.event_type == "down"))

    def pump(self):
        updated = set()
        for _ in range(500):
            try:
                key_id, down = self.events.get_nowait()
            except queue.Empty:
                break
            if not self.enabled:
                continue
            if down:
                self.held.add(key_id)
                self.recent.configure(text=f"마지막 키: {self.key_labels.get(key_id, key_id)}")
            else:
                self.held.discard(key_id)
            updated.add(key_id)
        for key_id in updated:
            self.paint(key_id)
        self.root.after(16, self.pump)

    def reset_keys(self):
        previous = self.held.copy()
        self.held.clear()
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                break
        for key_id in previous:
            self.paint(key_id)

    def schedule_draw(self, _event=None):
        if self.draw_task is not None:
            self.root.after_cancel(self.draw_task)
        self.draw_task = self.root.after(45, self.draw)

    def draw(self):
        self.draw_task = None
        self.canvas.delete("all")
        self.rectangles.clear()
        self.labels.clear()

        width = max(10, self.canvas.winfo_width())
        height = max(10, self.canvas.winfo_height())
        scale = min(1.14, (width - 24) / BASE_WIDTH, (height - 15) / BASE_HEIGHT)
        offset_x = (width - BASE_WIDTH * scale) / 2
        offset_y = (height - BASE_HEIGHT * scale) / 2

        def draw_section(rows, x_units, y_start):
            for row_index, row in enumerate(rows):
                x = x_units
                y = 12 + (y_start + row_index) * PITCH
                for spec in row:
                    units = spec.units
                    if spec.id != "_":
                        px = offset_x + x * scale
                        py = offset_y + y * scale
                        pw = (PITCH * units - 5) * scale
                        ph = HEIGHT * scale
                        rectangle = self.canvas.create_rectangle(
                            px, py, px + pw, py + ph,
                            fill=KEY_BG, outline=KEY_OUTLINE,
                            width=max(1, round(scale)))
                        font_size = max(7, round((9 if len(spec.label) > 5 else 10) * scale))
                        text = self.canvas.create_text(px + pw / 2, py + ph / 2,
                                                       text=spec.label, fill=KEY_TEXT,
                                                       font=("Malgun Gothic", font_size, "bold"))
                        self.rectangles[spec.id] = rectangle
                        self.labels[spec.id] = text
                    x += PITCH * units

        draw_section(MAIN_ROWS, 10, 0)
        draw_section(NAV_ROWS, 796, 0)
        draw_section(PAD_ROWS, 969, 1)

        for key_id in self.held:
            self.paint(key_id)

    def paint(self, key_id):
        rectangle = self.rectangles.get(key_id)
        label = self.labels.get(key_id)
        if rectangle is None or label is None:
            return
        down = key_id in self.held
        self.canvas.itemconfig(rectangle,
                               fill=ACTIVE_BG if down else KEY_BG,
                               outline=ACTIVE_BG if down else KEY_OUTLINE)
        self.canvas.itemconfig(label, fill=ACTIVE_TEXT if down else KEY_TEXT)

    def close(self):
        if self.hook is not None:
            try:
                keyboard.unhook(self.hook)
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    KeyView().run()
