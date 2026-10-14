import http.client
import io
import json
import threading
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from remote_server import RemoteHTTPServer


class FakeController:
    def __init__(self):
        self.actions = []
    def screen_size(self):
        return 1920, 1080
    def screenshot_jpeg(self):
        return b'\xff\xd8\xff\xd9'
    def perform(self, data):
        if data.get('type') != 'move':
            raise ValueError('unsupported')
        self.actions.append(data)


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = FakeController()
        cls.srv = RemoteHTTPServer(('127.0.0.1', 0), cls.control, Path(__file__).resolve().parents[1] / 'web' / 'index.html')
        cls.port = cls.srv.server_address[1]
        cls.worker = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.stop()

    def connect(self, method, path, data=None, cookie=None, origin=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=4)
        headers = {'Content-Type': 'application/json', 'Host': f'127.0.0.1:{self.port}'}
        if origin: headers['Origin'] = f'http://127.0.0.1:{self.port}'
        if cookie: headers['Cookie'] = cookie
        conn.request(method, path, body=json.dumps(data).encode() if data is not None else None, headers=headers)
        response = conn.getresponse()
        code = response.status; raw = response.read(); cookie_hdr = response.getheader('Set-Cookie')
        conn.close()
        return code, raw, cookie_hdr

    def test_screen_denied_before_login(self):
        code, _, _ = self.connect('GET', '/api/frame')
        self.assertEqual(code, 401)

    def test_wrong_pin_rejected(self):
        wrong = '00000000' if self.srv.state.pin != '00000000' else '99999999'
        code, _, _ = self.connect('POST', '/api/login', {'pin': wrong})
        self.assertEqual(code, 401)

    def test_login_action_logout(self):
        code, raw, cookie = self.connect('POST', '/api/login', {'pin': self.srv.state.pin})
        self.assertEqual(code, 200)
        token = cookie.split(';')[0]
        self.assertIn('HttpOnly', cookie)
        code, body, _ = self.connect('GET', '/api/status', cookie=token)
        self.assertEqual(json.loads(body)['width'], 1920)
        code, body, _ = self.connect('POST', '/api/control', {'enabled': True}, cookie=token)
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)['remoteControlEnabled'])
        code, _, _ = self.connect('POST', '/api/action', {'type':'move','x':0.5,'y':0.3}, cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(len(self.control.actions), 1)
        code, _, _ = self.connect('POST', '/api/logout', {}, cookie=token)
        self.assertEqual(code, 200)
        code, _, _ = self.connect('GET', '/api/frame', cookie=token)
        self.assertEqual(code, 401)

    def test_computer_name_visible_only_after_login(self):
        import socket
        code, _, _ = self.connect('GET', '/api/status')
        self.assertEqual(code, 401)
        code, _, cookie = self.connect('POST', '/api/login', {'pin': self.srv.state.pin})
        self.assertEqual(code, 200)
        code, raw, _ = self.connect('GET', '/api/status', cookie=cookie.split(';')[0])
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)['computerName'], socket.gethostname()[:64])

    def test_origin_rejected(self):
        code, _, _ = self.connect('POST', '/api/login', {'pin': self.srv.state.pin}, origin=False)
        self.assertEqual(code, 403)

    def test_html_served(self):
        code, page, _ = self.connect('GET', '/')
        self.assertEqual(code, 200)
        self.assertIn('YEON 원격 조정'.encode('utf-8'), page)


if __name__ == '__main__':
    unittest.main()
