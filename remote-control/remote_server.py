"""Local-only-by-design web remote control HTTP server.

This server does not offer internet relay, unattended startup, or a shell API.
Always keep the host desktop app in control of when sharing starts and stops.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import secrets
import socket
import threading
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from focus_mode import FocusSession
from file_exchange import FileExchange, MAX_FILE

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
        self.files = FileExchange()
        # Each authenticated administrator session starts in screen-only mode.
        self.remote_permissions: dict[str, bool] = {}

    def can_remote_control(self, token: str | None) -> bool:
        with self.lock:
            return self.active and bool(token) and self.authenticated(token) and self.remote_permissions.get(token, False)

    def set_remote_control(self, token: str | None, enabled: bool) -> bool:
        """Switch only this signed-in controller's input capability (not screen sharing)."""
        with self.lock:
            if not self.authenticated(token):
                return False
            self.remote_permissions[token] = enabled
            if not enabled:
                release = getattr(self.controller, 'release_all', None)
                if callable(release):
                    release()
            return enabled

    def perform_if_allowed(self, token: str | None, data: dict) -> bool:
        # The action and OFF toggle are serialized on the same lock.
        with self.lock:
            if not self.can_remote_control(token):
                return False
            self.controller.perform(data)
            return True

    def enabled_sessions(self) -> int:
        with self.lock:
            return sum(1 for token, enabled in list(self.remote_permissions.items())
                       if enabled and self.authenticated(token))

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
            self.remote_permissions[token] = False
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
                if self.remote_permissions.pop(token, False):
                    release = getattr(self.controller, 'release_all', None)
                    if callable(release): release()
                return False
            return True

    def revoke(self, token: str | None) -> None:
        if token:
            with self.lock:
                self.sessions.pop(token, None)
                enabled = self.remote_permissions.pop(token, False)
                if enabled:
                    release = getattr(self.controller, 'release_all', None)
                    if callable(release): release()
            if self.focus.owner == token:
                self.focus.stop()
            self.files.revoke(token)

    def end(self) -> None:
        with self.lock:
            self.active = False
            self.remote_permissions.clear()
            self.sessions.clear()
            release = getattr(self.controller, 'release_all', None)
            if callable(release):
                release()
            self.focus.stop()
            self.files.close()

    def connections(self) -> int:
        now = time.monotonic()
        with self.lock:
            for token, expiry in list(self.sessions.items()):
                if expiry < now:
                    self.sessions.pop(token, None)
                    if self.remote_permissions.pop(token, False):
                        release = getattr(self.controller, 'release_all', None)
                        if callable(release): release()
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
    server_version = "YEONManaged/1.3.7"
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
        if path == "/api/discover":
            # Advertise the service type only. Never disclose the PIN, sessions,
            # screenshots, computer identity or other private metadata.
            self._json(HTTPStatus.OK, {"service": "YEON_REMOTE_MANAGED", "protocol": 1})
        elif path == "/":
            self._write(HTTPStatus.OK, self.server.page, "text/html; charset=utf-8")
        elif path == "/api/status":
            if not self.server.state.authenticated(self._token()):
                self._json(HTTPStatus.UNAUTHORIZED, {"authorized": False})
                return
            try:
                w, h = self.server.state.controller.screen_size()
                self._json(HTTPStatus.OK, {"authorized": True, "width": w, "height": h, "remoteControlEnabled": self.server.state.can_remote_control(self._token()), "computerName": socket.gethostname()[:64]})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "화면 크기를 읽을 수 없습니다."})
        elif path == "/api/focus/status":
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "인증 필요"})
                return
            self._json(HTTPStatus.OK, {"mode": self.server.state.focus.status(token),
                                       "displayMode": self.server.state.focus.display()})
        elif path == "/api/files/status":
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
                return
            key = __import__('urllib.parse', fromlist=['parse_qs']).parse_qs(urlsplit(self.path).query).get('id', [''])[0]
            info = self.server.state.files.status(key, token)
            self._json(HTTPStatus.OK, info) if info else self._json(HTTPStatus.NOT_FOUND, {"error": "파일 요청을 찾을 수 없습니다."})
        elif path == "/api/files/download":
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
                return
            key = __import__('urllib.parse', fromlist=['parse_qs']).parse_qs(urlsplit(self.path).query).get('id', [''])[0]
            result = self.server.state.files.download(key, token)
            if result is None:
                self._json(HTTPStatus.CONFLICT, {"error": "관리 대상이 파일을 선택하지 않았습니다."})
                return
            filename, data = result
            self._write(HTTPStatus.OK, data, "application/octet-stream")
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
                self._json(HTTPStatus.CONFLICT, {"error": "화면 전송 허용 필요"})
                return
            self._json(HTTPStatus.OK, {"ok": True})
            return
        if path == '/api/files/upload':
            token = self._token()
            if not self.server.state.authenticated(token):
                self._json(HTTPStatus.UNAUTHORIZED, {'error': '로그인이 필요합니다.'})
                return
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/octet-stream':
                self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {'error': '바이너리 전송만 허용합니다.'})
                return
            try: length = int(self.headers.get('Content-Length', '0'))
            except ValueError: length = 0
            if not 1 <= length <= MAX_FILE:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {'error': '8MB 초과 파일은 전송할 수 없습니다.'})
                return
            from urllib.parse import parse_qs
            key = parse_qs(urlsplit(self.path).query).get('id', [''])[0]
            # Only read after local approval and before applying the finite byte cap.
            info = self.server.state.files.status(key, token)
            if not info or info['state'] != 'approved' or info['size'] != length:
                self._json(HTTPStatus.CONFLICT, {'error': '관리 대상 PC에서 파일 저장을 먼저 허용해야 합니다.'})
                return
            if not self.server.state.files.accept_bytes(key, token, self.rfile.read(length)):
                self._json(HTTPStatus.CONFLICT, {'error': '파일 저장에 실패했거나 요청이 취소되었습니다.'})
                return
            self._json(HTTPStatus.OK, {'ok': True})
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
        if path == "/api/files/offer":
            try:
                key = self.server.state.files.offer(token, data.get('filename'), data.get('size'))
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {'error': str(exc)})
                return
            self._json(HTTPStatus.OK, {'id': key})
        elif path == "/api/files/request":
            key = self.server.state.files.request(token)
            self._json(HTTPStatus.OK, {'id': key})
        elif path == "/api/focus/request":
            display_mode = data.get('displayMode', 'focus')
            if display_mode not in ('focus', 'window'):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "지원하지 않는 화면 전송 모드입니다."})
                return
            if not self.server.state.focus.request(token, display_mode):
                self._json(HTTPStatus.CONFLICT, {"error": "이미 화면 전송 요청/전송이 진행 중입니다."})
                return
            self._json(HTTPStatus.OK, {"mode": "pending"})
        elif path == "/api/focus/stop":
            if not self.server.state.focus.stop(token):
                self._json(HTTPStatus.FORBIDDEN, {"error": "전송 중인 관리자만 종료할 수 있습니다."})
                return
            self._json(HTTPStatus.OK, {"ok": True})
        elif path == "/api/control":
            if type(data.get("enabled")) is not bool:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "enabled는 true 또는 false여야 합니다."})
                return
            enabled = self.server.state.set_remote_control(token, data["enabled"])
            self._json(HTTPStatus.OK, {"remoteControlEnabled": enabled})
        elif path == "/api/logout":
            self.server.state.revoke(token)
            self._json(HTTPStatus.OK, {"ok": True}, {"Set-Cookie": "yeon_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
        elif path == "/api/action":
            if self.server.state.focus.latest()[0] == 'active':
                self._json(HTTPStatus.CONFLICT, {"error": "집중 화면 전송을 종료한 후 원격 제어를 사용하세요."})
                return
            try:
                if not self.server.state.perform_if_allowed(token, data):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "관리자 앱에서 원격 제어가 OFF 상태입니다."})
                    return
            except (ValueError, TypeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception as exc:
                # Fail-safe corner is deliberately *not* disabled. Report an actionable
                # reason without exposing IPs, cookies, passwords or raw error internals.
                if type(exc).__name__ == 'FailSafeException':
                    detail = '관리 대상 PC의 마우스가 화면 모서리의 안전 정지 지점에 있습니다. 대상 PC에서 마우스를 중앙으로 이동한 뒤 다시 시도하세요.'
                elif type(exc).__name__ in ('PermissionError', 'OSError'):
                    detail = 'Windows에서 입력을 차단했습니다. 잠금·UAC 보안 화면을 닫고 일반 데스크톱에서 다시 시도하세요.'
                else:
                    detail = '마우스·키보드 입력에 실패했습니다. 관리 대상 PC의 화면 잠금, 권한 및 프로그램 상태를 확인하세요.'
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": detail})
                return
            self._json(HTTPStatus.OK, {"ok": True})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "알 수 없는 요청입니다."})
