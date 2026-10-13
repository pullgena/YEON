"""YEON 원격 조정 host: visible, manually enabled Windows desktop window."""
from __future__ import annotations

import ipaddress
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from remote_server import RemoteHTTPServer

PORT = 8765


def resource_path(relative: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative


def local_address() -> str:
    # UDP 'connect' selects a local interface but sends no actual packet.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
            if ipaddress.ip_address(candidate).is_private:
                return candidate
    except OSError:
        pass
    try:
        for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
            ip = ipaddress.ip_address(addr)
            if ip.is_private and not ip.is_loopback:
                return addr
    except OSError:
        pass
    return "127.0.0.1"


class DesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YEON 원격 조정 v1.0.1")
        self.root.geometry("560x515")
        self.root.minsize(490, 475)
        self.root.configure(bg="#111827")
        self.server = None
        self.thread = None
        self.address = ""
        self.closing = False

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Primary.TButton", font=("Malgun Gothic", 11, "bold"), padding=11,
                        foreground="white", background="#4F46E5", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#6366F1")])
        style.configure("Neutral.TButton", font=("Malgun Gothic", 10), padding=9,
                        foreground="#E5E7EB", background="#374151", borderwidth=0)
        style.map("Neutral.TButton", background=[("active", "#4B5563")])

        box = tk.Frame(root, bg="#111827", padx=30, pady=26)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="YEON  ·  원격 조정", bg="#111827", fg="#A5B4FC",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(box, text="YEON 원격 조정", bg="#111827", fg="white",
                 font=("Malgun Gothic", 23, "bold")).pack(anchor="w", pady=(12, 6))
        tk.Label(box, text="관리받는 PC에서 공유를 켜면, 다른 기기로 조종할 수 있습니다.",
                 bg="#111827", fg="#9CA3AF", font=("Malgun Gothic", 10)).pack(anchor="w")

        panel = tk.Frame(box, bg="#1F2937", padx=18, pady=17)
        panel.pack(fill="x", pady=(24, 15))
        tk.Label(panel, text="접속 주소", fg="#9CA3AF", bg="#1F2937",
                 font=("Malgun Gothic", 10)).pack(anchor="w")
        self.url_label = tk.Label(panel, text="공유를 시작하면 표시됩니다", fg="white",
                                  bg="#1F2937", font=("Segoe UI", 13, "bold"))
        self.url_label.pack(anchor="w", pady=(4, 14))
        tk.Label(panel, text="일회용 접속 코드", fg="#9CA3AF", bg="#1F2937",
                 font=("Malgun Gothic", 10)).pack(anchor="w")
        self.pin_label = tk.Label(panel, text="— — — — — — — —", fg="#818CF8",
                                  bg="#1F2937", font=("Consolas", 22, "bold"))
        self.pin_label.pack(anchor="w", pady=(3, 3))

        button_box = tk.Frame(box, bg="#111827")
        button_box.pack(fill="x", pady=(2, 8))
        self.start_btn = ttk.Button(button_box, text="공유 시작", style="Primary.TButton", command=self.start)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ttk.Button(button_box, text="즉시 중지", style="Neutral.TButton", command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=(9, 0))
        ttk.Button(box, text="접속 주소 복사", style="Neutral.TButton", command=self.copy_url).pack(fill="x")
        self.status = tk.StringVar(value="●  공유 중지됨")
        tk.Label(box, textvariable=self.status, fg="#A5B4FC", bg="#111827",
                 font=("Malgun Gothic", 10)).pack(anchor="w", pady=(18, 8))
        tk.Label(box, text="보안 안내: 집/학교 등 신뢰할 수 있는 Wi-Fi에서만 사용하세요.\n"
                           "공유 중에는 원격 기기에서 화면과 키보드를 조종할 수 있습니다.\n"
                           "창을 닫거나 '즉시 중지'를 누르면 접속이 끊깁니다.",
                 fg="#9CA3AF", bg="#111827", justify="left",
                 font=("Malgun Gothic", 9)).pack(anchor="w")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh_status()

    def start(self):
        if self.server:
            return
        try:
            from pc_control import PCController
            controller = PCController()
            srv = RemoteHTTPServer(("0.0.0.0", PORT), controller, resource_path("web/index.html"))
        except Exception as exc:
            messagebox.showerror("공유 시작 실패", f"공유를 시작하지 못했습니다.\n\n{exc}\n\n포트 {PORT} 사용 여부를 확인하세요.")
            return
        self.server = srv
        self.address = f"http://{local_address()}:{PORT}"
        self.url_label.config(text=self.address)
        self.pin_label.config(text=srv.state.pin)
        self.status.set("●  공유 중 · 접속 허용됨")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.thread = threading.Thread(target=srv.serve_forever, daemon=True, name="YEON-http")
        self.thread.start()

    def stop(self):
        srv = self.server
        if not srv:
            return
        self.server = None
        srv.state.end()  # Revoke sessions before shutdown thread completes.
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pin_label.config(text="— — — — — — — —")
        self.url_label.config(text="공유가 중지되었습니다")
        self.address = ""
        self.status.set("●  공유 중지됨")
        threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()

    def copy_url(self):
        if self.address:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.address)
            self.status.set("✓  접속 주소가 복사되었습니다.")

    def refresh_status(self):
        if self.server:
            self.status.set(f"●  공유 중 · 연결된 기기 {self.server.state.connections()}개")
        if not self.closing:
            self.root.after(2500, self.refresh_status)

    def close(self):
        self.closing = True
        self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
