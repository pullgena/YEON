"""Local-only-by-design web remote control HTTP server.

This server does not offer internet relay, unattended startup, or a shell API.
Always keep the host desktop app in control of when sharing starts and stops.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from focus_mode import FocusSession

PIN_TTL_SECONDS = 60 * 60
MAX_BODY = 8 * 1024
MAX_FOCUS_JPEG = 900_000
MAX_FAILURES = 5
FAIL_WINDOW = 60


class ShareState:
    def __init__(self, controller):
        self.controller = controller
        self.pin = f"{secrets.randbelow(100_000_000):08d}"
        self.created_at = time.monotonic()
        self.sessions: dict[str, float] = {}
        self.failures: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.RLock()
        self.active = True
        self.focus = FocusSession()
        self.remote_control_enabled = False  # local-only permission; reset on every share

    def can_remote_control(self) -> bool:
        with self.lock:
            return self.active and self.remote_control_enabled

    def set_remote_control(self, enabled: bool) -> bool:
        """Only the managed-PC GUI/tray calls this. Never expose a network toggle."""
        with self.lock:
            self.remote_control_enabled = bool(enabled) and self.active
            if not self.remote_control_enabled:
                release = getattr(self.controller, 'release_all', None)
                if callable(release):
                    release()
            return self.remote_control_enabled

    def perform_if_allowed(self, data: dict) -> bool:
        # Hold the same lock during input, so an OFF click cannot race an action.
        with self.lock:
            if not self.active or not self.remote_control_enabled:
                return False
            self.controller.perform(data)
            return True

    def authenticate(self, address: str, pin: str) -> str | None:
        now = time.monotonic()
        with self.lock:
            attempts = self.failures[address]
            while attempts and now - attempts[0] > FAIL_WINDOW:
                attempts.popleft()
            if not self.active or len(attempts) >= MAX_FAILURES:
                return None
            if now - self.created_at > PIN_TTL_SECONDS or not hmac.compare_digest(pin, self.pin):
                attempts.append(now)
                return None
            token = secrets.token_urlsafe(32)
            self.sessions[token] = now + PIN_TTL_SECONDS
            attempts.clear()
            return token

    def authenticated(self, token: str | None) -> bool:
        if not token:
            return False
        now = time.monotonic()
        with self.lock:
            if not self.active:
                return False
            expiry = self.sessions.get(token)
            if expiry is None or expiry < now:
                self.sessions.pop(token, None)
                return False
            return True

    def revoke(self, token: str | None) -> None:
        if token:
            with self.lock:
                self.sessions.pop(token, None)
            if self.focus.owner == token:
                self.focus.stop()

    def end(self) -> None:
        with self.lock:
            self.active = False
            self.remote_control_enabled = False
            self.sessions.clear()
            release = getattr(self.controller, 'release_all', None)
            if callable(release):
                release()
            self.focus.stop()

    def connections(self) -> int:
        now = time.monotonic()
        with self.lock:
            for token, expiry in list(self.sessions.items()):
                if expiry < now:
                    self.sessions.pop(token, None)
            return len(self.sessions)


class RemoteHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, controller, html_path: str | Path):
        super().__init__(address, RemoteHandler)
        self.state = ShareState(controller)
        self.page = Path(html_path).read_bytes()

    def stop(self) -> None:
        self.state.end()
        self.shutdown()
        self.server_close()


class RemoteHandler(BaseHTTPRequestHandler):
    server: RemoteHTTPServer
    server_version = "YEONManaged/1.3.1"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass  # Do not print session cookies or network addresses to a console.

    def _headers(self, status, content_type, length, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()

    def _write(self, status, raw, content_type="text/plain; charset=utf-8", extra=None):
        self._headers(status, content_type, len(raw), extra)
        try:
            self.wfile.write(raw)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def _json(self, status, data, extra=None):
        self._write(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", extra)

    def _token(self) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        item = cookie.get("yeon_session")
        return item.value if item else None

    def _check_client(self) -> bool:
        # Only LAN/loopback connections should be served; no public address relay.
        try:
            addr = ipaddress.ip_address(self.client_address[0])
            return addr.is_private or addr.is_loopback
        except ValueError:
            return False

    def _check_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return False
        try:
            url = urlsplit(origin)
            return url.scheme == "http" and url.netloc == self.headers.get("Host", "")
        except ValueError:
            return False

    def do_GET(self):
        if not self._check_client() or not self.server.state.active:
            self._json(HTTPStatus.FORBIDDEN, {"error": "공유가 중단되었거나 네트워크에서 접근할 수 없습니다."})
            return
        path = urlsplit(self.path).path
        if path == "/":
            self._write(HTTPStatus.OK, self.server.page, "text/html; charset=utf-8")
        elif path == "/api/status":
            if not self.server.state.authenticated(self._token()):
                self._json(HTTPStatus.UNAUTHORIZED, {"authorized": False})
                return
            try:
                w, h = self.server.state.controller.screen_size()
                self._json(HTTPStatus.OK, {"authorized": True, "width": w, "height": h, "remoteControlEnabled": self.server.state.can_remote_control()})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "화면 크기를 읽을 수 없습니다."})
        elif path == "/api/focus/status":
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "인증 필요"})
                return
            self._json(HTTPStatus.OK, {"mode": self.server.state.focus.status(token)})
        elif path == "/api/frame":
            if not self.server.state.authenticated(self._token()):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "인증 필요"})
                return
            try:
                frame = self.server.state.controller.screenshot_jpeg()
                self._write(HTTPStatus.OK, frame, "image/jpeg")
            except Exception:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "화면을 가져오지 못했습니다."})
        elif path == "/favicon.ico":
            self._write(HTTPStatus.NO_CONTENT, b"")
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "찾을 수 없습니다."})

    def do_POST(self):
        if not self._check_client() or not self.server.state.active:
            self._json(HTTPStatus.FORBIDDEN, {"error": "연결할 수 없습니다."})
            return
        if not self._check_origin():
            self._json(HTTPStatus.FORBIDDEN, {"error": "잘못된 요청 출처입니다."})
            return
        path = urlsplit(self.path).path
        if path == "/api/focus/frame":
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "인증 필요"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "image/jpeg":
                self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JPEG 형식만 허용"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 4 <= length <= MAX_FOCUS_JPEG:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "화면 크기 초과"})
                return
            if not self.server.state.focus.push(token, self.rfile.read(length)):
                self._json(HTTPStatus.CONFLICT, {"error": "집중 모드 허용 필요"})
                return
            self._json(HTTPStatus.OK, {"ok": True})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JSON 형식만 허용합니다."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "요청 크기 초과"})
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "잘못된 JSON"})
            return

        path = urlsplit(self.path).path
        if path == "/api/login":
            pin = data.get("pin")
            if not isinstance(pin, str) or not (len(pin) == 8 and pin.isascii() and pin.isdecimal()):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "8자리 접속 코드를 입력하세요."})
                return
            token = self.server.state.authenticate(self.client_address[0], pin)
            if token is None:
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "코드가 틀렸거나 시도 횟수를 초과했습니다. 잠시 후 재시도하세요."})
                return
            cookie = f"yeon_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={PIN_TTL_SECONDS}"
            self._json(HTTPStatus.OK, {"ok": True}, {"Set-Cookie": cookie})
            return
        token = self._token()
        if not self.server.state.authenticated(token):
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
            return
        if path == "/api/focus/request":
            if not self.server.state.focus.request(token):
                self._json(HTTPStatus.CONFLICT, {"error": "이미 집중 화면 요청/전송이 진행 중입니다."})
                return
            self._json(HTTPStatus.OK, {"mode": "pending"})
        elif path == "/api/focus/stop":
            if not self.server.state.focus.stop(token):
                self._json(HTTPStatus.FORBIDDEN, {"error": "전송 중인 관리자만 종료할 수 있습니다."})
                return
            self._json(HTTPStatus.OK, {"ok": True})
        elif path == "/api/logout":
            self.server.state.revoke(token)
            self._json(HTTPStatus.OK, {"ok": True}, {"Set-Cookie": "yeon_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
        elif path == "/api/action":
            if self.server.state.focus.latest()[0] == 'active':
                self._json(HTTPStatus.CONFLICT, {"error": "집중 화면 전송을 종료한 후 원격 제어를 사용하세요."})
                return
            try:
                if not self.server.state.perform_if_allowed(data):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "관리 대상 PC에서 원격 제어가 OFF 상태입니다."})
                    return
            except (ValueError, TypeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "입력 조작에 실패했습니다."})
                return
            self._json(HTTPStatus.OK, {"ok": True})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "알 수 없는 요청입니다."})
