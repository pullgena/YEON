"""YEON 관리 대상: explicitly approved local network screen sharing with a visible system tray."""
from __future__ import annotations

import ipaddress
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from remote_server import RemoteHTTPServer
from tray_visual import VERSION, make_tray_icon, status_title
from focus_mode import FocusOverlay

PORT = 8765


def resource_path(relative: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / relative


def local_address() -> str:
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


class ManagedDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"YEON 관리 대상 v{VERSION}")
        self.root.geometry("590x620")
        self.root.minsize(520, 580)
        self.root.configure(bg="#111827")
        self.server: RemoteHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.address = ""
        self.closing = False
        self.stopping = False
        self.tray = None
        self.tray_ready = False
        self.hide_notice_sent = False
        self.focus_overlay = None
        self.focus_prompt_open = False
        try:
            self.root.iconbitmap(str(resource_path("assets/yeon-managed.ico")))
        except (tk.TclError, OSError):
            pass

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Primary.TButton", font=("Malgun Gothic", 11, "bold"), padding=11,
                        foreground="white", background="#4F46E5", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#6366F1")])
        style.configure("Neutral.TButton", font=("Malgun Gothic", 10), padding=9,
                        foreground="#E5E7EB", background="#374151", borderwidth=0)
        style.map("Neutral.TButton", background=[("active", "#4B5563")])

        box = tk.Frame(root, bg="#111827", padx=30, pady=24)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="YEON  ·  REMOTE MANAGED PC", bg="#111827", fg="#A5B4FC",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(box, text="YEON 관리 대상", bg="#111827", fg="white",
                 font=("Malgun Gothic", 23, "bold")).pack(anchor="w", pady=(12, 6))
        tk.Label(box, text="관리자가 접속할 컴퓨터에서 실행하는 프로그램입니다.",
                 bg="#111827", fg="#9CA3AF", font=("Malgun Gothic", 10)).pack(anchor="w")

        panel = tk.Frame(box, bg="#1F2937", padx=18, pady=16)
        panel.pack(fill="x", pady=(22, 13))
        tk.Label(panel, text="관리자에게 알려줄 접속 주소", fg="#9CA3AF", bg="#1F2937",
                 font=("Malgun Gothic", 10)).pack(anchor="w")
        self.url_label = tk.Label(panel, text="공유를 시작하면 표시됩니다", fg="white",
                                  bg="#1F2937", font=("Segoe UI", 12, "bold"))
        self.url_label.pack(anchor="w", pady=(4, 12))
        tk.Label(panel, text="일회용 접속 코드", fg="#9CA3AF", bg="#1F2937",
                 font=("Malgun Gothic", 10)).pack(anchor="w")
        self.pin_label = tk.Label(panel, text="— — — — — — — —", fg="#818CF8",
                                  bg="#1F2937", font=("Consolas", 22, "bold"))
        self.pin_label.pack(anchor="w", pady=(3, 3))

        row = tk.Frame(box, bg="#111827")
        row.pack(fill="x", pady=(2, 8))
        self.start_btn = ttk.Button(row, text="공유 시작", style="Primary.TButton", command=self.start)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ttk.Button(row, text="공유 즉시 중지", style="Neutral.TButton", command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=(9, 0))
        self.control_btn = ttk.Button(box, text="원격 제어 OFF · ON으로 변경", style="Primary.TButton",
                                      command=self.toggle_remote_control, state="disabled")
        self.control_btn.pack(fill="x", pady=(5, 9))
        self.control_status = tk.StringVar(value="원격 제어: OFF (화면 공유만 허용)")
        tk.Label(box, textvariable=self.control_status, fg="#FBBF24", bg="#111827",
                 font=("Malgun Gothic", 10, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Button(box, text="접속 주소 복사", style="Neutral.TButton", command=self.copy_url).pack(fill="x")
        ttk.Button(box, text="백그라운드로 보내기 (트레이 아이콘)",
                   style="Neutral.TButton", command=self.hide_window).pack(fill="x", pady=(9, 0))

        self.status = tk.StringVar(value="● 공유 중지됨")
        tk.Label(box, textvariable=self.status, fg="#A5B4FC", bg="#111827",
                 font=("Malgun Gothic", 10)).pack(anchor="w", pady=(13, 5))
        tk.Label(box,
                 text="X 버튼을 누르면 창만 숨겨지고 알림 영역에 아이콘이 남습니다.\n"
                      "공유 중일 때는 백그라운드에서도 계속 공유됩니다.\n"
                      "트레이 아이콘 우클릭 → 원격 제어 ON/OFF · 공유 중지 · 완전 종료.",
                 fg="#A6B0C5", bg="#111827", justify="left",
                 font=("Malgun Gothic", 9)).pack(anchor="w")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.after(900, self.refresh_status)
        self.tray_thread = threading.Thread(target=self._tray_worker, daemon=True, name="YEON-tray")
        self.tray_thread.start()

    def _run_on_ui(self, callback):
        if self.closing:
            return
        try:
            self.root.after(0, callback)
        except (RuntimeError, tk.TclError):
            pass

    def _tray_worker(self):
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("관리 대상 창 열기", lambda icon, item: self._run_on_ui(self.show_window), default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda item: status_title(self.server is not None), None, enabled=False),
                pystray.MenuItem("화면 공유 시작", lambda icon, item: self._run_on_ui(self.start),
                                 enabled=lambda item: self.server is None and not self.stopping),
                pystray.MenuItem(lambda item: '원격 제어 OFF로 변경' if self._control_allowed() else '원격 제어 ON으로 변경',
                                 lambda icon, item: self._run_on_ui(self.toggle_remote_control),
                                 enabled=lambda item: self.server is not None),
                pystray.MenuItem("공유 즉시 중지", lambda icon, item: self._run_on_ui(self.stop),
                                 enabled=lambda item: self.server is not None),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("프로그램 완전 종료", lambda icon, item: self._run_on_ui(self.quit_app))
            )
            icon = pystray.Icon("yeon_managed", make_tray_icon(False), status_title(False), menu)
            self.tray = icon
            def ready(icon_obj):
                icon_obj.visible = True  # Explicit setup callbacks must make the tray icon visible.
                self.tray_ready = True
                self._run_on_ui(self._refresh_tray)
            icon.run(setup=ready)
        except Exception as exc:
            # Never claim to be running in the background if the tray fails.
            self._run_on_ui(lambda: messagebox.showwarning(
                "알림 영역 오류", f"시스템 트레이 아이콘을 사용할 수 없습니다.\n\n{exc}\n\n창을 닫으면 공유가 중지됩니다."))
        finally:
            self.tray_ready = False

    def _control_allowed(self):
        return bool(self.server and self.server.state.can_remote_control())

    def _update_control_ui(self):
        allowed = self._control_allowed()
        if hasattr(self, 'control_btn'):
            self.control_btn.config(text='원격 제어 ON · OFF로 변경' if allowed else '원격 제어 OFF · ON으로 변경',
                                    state='normal' if self.server else 'disabled')
        if hasattr(self, 'control_status'):
            self.control_status.set('원격 제어: ON (관리자 마우스·키보드 허용)' if allowed
                                    else '원격 제어: OFF (화면 공유만 허용)')
        self._refresh_tray()

    def toggle_remote_control(self):
        if not self.server or self.closing or self.stopping:
            return
        self.server.state.set_remote_control(not self.server.state.can_remote_control())
        self._update_control_ui()

    def _refresh_tray(self):
        tray = self.tray
        if not (self.tray_ready and tray):
            return
        sharing = self.server is not None
        try:
            tray.icon = make_tray_icon(sharing)
            tray.title = status_title(sharing) + (' · 원격 제어 ON' if self._control_allowed() else ' · 원격 제어 OFF')
            tray.update_menu()
        except Exception:
            pass

    def start(self):
        if self.server is not None or self.stopping or self.closing:
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
        self.status.set("● 공유 중 · 알림 영역에서 언제든 중지 가능")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.thread = threading.Thread(target=srv.serve_forever, daemon=True, name="YEON-http")
        self.thread.start()
        self._update_control_ui()

    def stop(self):
        srv = self.server
        if not srv:
            return
        if getattr(self, 'focus_overlay', None):
            self.focus_overlay.stop()
        self.server = None
        self.stopping = True
        srv.state.end()  # Revoke existing sessions immediately, including hidden-window sharing.
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.pin_label.config(text="— — — — — — — —")
        self.url_label.config(text="공유가 중지되었습니다")
        self.address = ""
        self.status.set("● 공유 중지 중 · 연결 해제됨")
        self._update_control_ui()
        def shutdown():
            try:
                srv.shutdown()
                srv.server_close()
            finally:
                self._run_on_ui(self._after_stop)
        threading.Thread(target=shutdown, daemon=True, name="YEON-stop").start()

    def _after_stop(self):
        self.stopping = False
        self.start_btn.config(state="normal")
        self.status.set("● 공유 중지됨")
        self._refresh_tray()

    def copy_url(self):
        if self.address:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.address)
            self.status.set("✓ 접속 주소가 복사되었습니다.")

    def refresh_status(self):
        if self.closing:
            return
        if self.server:
            self.status.set(f"● 공유 중 · 원격 제어 {'ON' if self._control_allowed() else 'OFF'} · 연결된 기기 {self.server.state.connections()}개")
            focus = self.server.state.focus
            if focus.pending() and not self.focus_prompt_open:
                self.focus_prompt_open = True
                self.root.after(0, self.ask_focus_permission)
            if self.focus_overlay and focus.latest()[0] != 'active':
                self.focus_overlay.close()
                self.focus_overlay = None
        self._refresh_tray()
        self.root.after(650, self.refresh_status)

    def ask_focus_permission(self):
        try:
            if not self.server or not self.server.state.focus.pending():
                return
            # This prompt is shown on the managed PC even when its main window was hidden.
            self.show_window()
            approved = messagebox.askyesno(
                'YEON 집중 화면 전송 승인',
                '관리자가 자신의 화면을 이 PC에 전체 화면으로 전송하려고 합니다.\n\n'
                '승인하면 일반 데스크톱 조작이 전체 화면 안내로 가려집니다.\n'
                'ESC 또는 화면 아래의 빨간 종료 버튼으로 언제든 중지할 수 있습니다.\n\n'
                '집중 화면 전송을 허용하시겠습니까?', parent=self.root)
            if self.server and self.server.state.focus.pending():
                if approved and self.server.state.focus.accept():
                    self.focus_overlay = FocusOverlay(self.root, self.server.state.focus, self.focus_exited)
                else:
                    self.server.state.focus.deny()
        finally:
            self.focus_prompt_open = False

    def focus_exited(self):
        self.focus_overlay = None
        self.status.set('● 집중 화면이 관리 대상 PC에서 종료되었습니다.')

    def hide_window(self):
        if self.closing:
            return
        if not self.tray_ready:
            if messagebox.askyesno("알림 영역 사용 불가", "트레이 아이콘이 준비되지 않았습니다. 공유를 종료하고 앱을 닫으시겠습니까?"):
                self.quit_app()
            return
        self.root.withdraw()
        if not self.hide_notice_sent:
            self.hide_notice_sent = True
            try:
                self.tray.notify("YEON 관리 대상은 알림 영역에서 실행됩니다. 오른쪽 클릭으로 공유 중지/종료할 수 있습니다.", "YEON 관리 대상")
            except Exception:
                pass

    def show_window(self):
        if self.closing:
            return
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_app(self):
        if self.closing:
            return
        self.closing = True
        srv = self.server
        self.server = None
        if getattr(self, 'focus_overlay', None):
            self.focus_overlay.stop()
        if srv:
            srv.state.end()
            # Background thread only tears down the listener; sessions are already revoked.
            threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    ManagedDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
