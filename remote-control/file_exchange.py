"""Consent-gated local file exchange for authenticated LAN sessions.

No filesystem enumeration or arbitrary path API is exposed. The managed PC
chooses where to save received files and chooses exactly which file to submit.
"""
from __future__ import annotations

import os
import secrets
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

MAX_FILE = 8 * 1024 * 1024
EXPIRES = 300


def safe_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError('파일 이름이 잘못되었습니다.')
    name = name.replace('\\', '/').split('/')[-1]
    name = ''.join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*')
    name = name.strip(' .')[:110]
    if not name or name in ('.', '..'):
        raise ValueError('파일 이름이 잘못되었습니다.')
    return name


@dataclass
class Transfer:
    owner: str
    kind: str  # receive (administrator -> managed) or submit (managed -> administrator)
    filename: str
    size: int
    status: str = 'pending'
    path: str = ''
    data: bytes = b''
    prompted: bool = False
    created: float = 0.0


class FileExchange:
    def __init__(self):
        self.lock = threading.RLock()
        self.transfers: dict[str, Transfer] = {}

    def _expire(self):
        now = time.monotonic()
        for key, item in list(self.transfers.items()):
            if now - item.created >= EXPIRES:
                del self.transfers[key]

    def _new(self, owner: str, kind: str, filename='', size=0) -> str:
        with self.lock:
            self._expire()
            if len(self.transfers) >= 12:
                raise ValueError('진행 중인 파일 작업이 많습니다. 잠시 후 다시 시도하세요.')
            key = secrets.token_urlsafe(18)
            self.transfers[key] = Transfer(owner, kind, filename, size, created=time.monotonic())
            return key

    def offer(self, owner: str, filename: str, size: int) -> str:
        if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_FILE:
            raise ValueError('파일 크기는 1바이트~8MB만 허용됩니다.')
        return self._new(owner, 'receive', safe_name(filename), size)

    def request(self, owner: str) -> str:
        return self._new(owner, 'submit')

    def next_prompt(self):
        with self.lock:
            self._expire()
            for key, t in self.transfers.items():
                if t.status == 'pending' and not t.prompted:
                    t.prompted = True
                    return key, t.kind, t.filename, t.size
        return None

    def decision(self, key: str, path: str | None):
        with self.lock:
            t = self.transfers.get(key)
            if not t or t.status != 'pending':
                return False
            if not path:
                t.status = 'denied'
                return True
            if t.kind == 'receive':
                t.path = str(path)
                t.status = 'approved'
                return True
            file = Path(path)
            try:
                size = file.stat().st_size
                if not 1 <= size <= MAX_FILE:
                    t.status = 'denied'
                    return False
                with file.open('rb') as f:
                    data = f.read(MAX_FILE + 1)
                if len(data) != size:
                    t.status = 'denied'
                    return False
            except (OSError, ValueError):
                t.status = 'denied'
                return False
            t.filename = safe_name(file.name)
            t.size = size
            t.data = data
            t.status = 'ready'
            return True

    def status(self, key: str, owner: str) -> dict | None:
        with self.lock:
            self._expire()
            t = self.transfers.get(key)
            if not t or t.owner != owner:
                return None
            return {'state': t.status, 'filename': t.filename, 'size': t.size}

    def accept_bytes(self, key: str, owner: str, content: bytes) -> bool:
        with self.lock:
            t = self.transfers.get(key)
            if not t or t.owner != owner or t.kind != 'receive' or t.status != 'approved':
                return False
            if len(content) != t.size or not 1 <= len(content) <= MAX_FILE:
                return False
            # The managed user selected the destination in a local save dialog.
            target = Path(t.path)
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.yeon-transfer-',
                                                 delete=False) as stream:
                    tmp_path = stream.name
                    stream.write(content)
                os.replace(tmp_path, target)
                t.status = 'done'
                return True
            except OSError:
                t.status = 'error'
                return False
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except OSError: pass

    def download(self, key: str, owner: str):
        with self.lock:
            t = self.transfers.get(key)
            if not t or t.owner != owner or t.kind != 'submit' or t.status != 'ready':
                return None
            data = t.data
            t.data = b''
            t.status = 'done'
            return t.filename, data

    def revoke(self, owner: str):
        with self.lock:
            for key, item in list(self.transfers.items()):
                if item.owner == owner:
                    del self.transfers[key]

    def close(self):
        with self.lock:
            self.transfers.clear()
