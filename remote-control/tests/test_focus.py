import http.client
import threading
import time
import json
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focus_mode import FocusSession
from remote_server import RemoteHTTPServer

class FocusStateTests(unittest.TestCase):
    def test_requires_local_acceptance_and_single_owner(self):
        focus = FocusSession()
        self.assertTrue(focus.request('a'))
        self.assertFalse(focus.request('b'))
        self.assertFalse(focus.push('a', b'\xff\xd8hello\xff\xd9'))
        self.assertTrue(focus.accept())
        self.assertFalse(focus.push('b', b'\xff\xd8hello\xff\xd9'))
        self.assertTrue(focus.push('a', b'\xff\xd8hello\xff\xd9'))
        self.assertEqual(focus.status('a'), 'active')
        self.assertEqual(focus.status('b'), 'idle')
        self.assertFalse(focus.stop('b'))
        self.assertTrue(focus.stop('a'))
        self.assertEqual(focus.latest()[0], 'idle')

    def test_inactive_or_expired_session_stops(self):
        f = FocusSession()
        self.assertTrue(f.request('a'))
        f.requested_at -= 45
        self.assertFalse(f.pending())
        self.assertEqual(f.status('a'), 'denied')
        self.assertTrue(f.request('b'))
        self.assertTrue(f.accept())
        f.last_frame -= 10
        self.assertEqual(f.latest()[0], 'idle')

    def test_corrupt_jpeg_rejected(self):
        f = FocusSession(); f.request('a'); f.accept()
        self.assertFalse(f.push('a', b'bad'))
        self.assertTrue(f.push('a', b'\xff\xd8hello\xff\xd9'))

class DummyController:
    def screen_size(self): return (1920,1080)
    def screenshot_jpeg(self): return b'\xff\xd8\xff\xd9'
    def perform(self, data): return None

class FocusApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv=RemoteHTTPServer(('127.0.0.1',0),DummyController(),Path(__file__).resolve().parents[1]/'web/index.html')
        cls.worker=threading.Thread(target=cls.srv.serve_forever,daemon=True); cls.worker.start()
    @classmethod
    def tearDownClass(cls): cls.srv.stop()
    def call(self,path,method='POST',cookie=None,frame=False):
        port=self.srv.server_address[1]; conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        headers={'Host':f'127.0.0.1:{port}','Origin':f'http://127.0.0.1:{port}', 'Content-Type':'image/jpeg' if frame else 'application/json'}
        if cookie: headers['Cookie']=cookie
        body=b'\xff\xd8hello\xff\xd9' if frame else b'{}'
        conn.request(method,path,headers=headers,body=None if method=='GET' else body)
        response=conn.getresponse(); code=response.status; raw=response.read(); session=response.getheader('Set-Cookie');conn.close()
        return code,raw,session
    def login(self):
        port=self.srv.server_address[1]; conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        raw=json.dumps({'pin':self.srv.state.pin}).encode()
        conn.request('POST','/api/login',body=raw,headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{port}','Host':f'127.0.0.1:{port}'})
        r=conn.getresponse(); self.assertEqual(r.status,200); cookie=r.getheader('Set-Cookie').split(';')[0];r.read();conn.close();return cookie
    def test_focus_needs_login_and_local_consent(self):
        self.srv.state.focus.stop()
        self.assertEqual(self.call('/api/focus/request')[0],401)
        cookie=self.login()
        self.assertEqual(self.call('/api/focus/request',cookie=cookie)[0],200)
        self.assertEqual(self.call('/api/focus/frame',cookie=cookie,frame=True)[0],409)
        self.assertEqual(json.loads(self.call('/api/focus/status','GET',cookie)[1])['mode'],'pending')
        self.assertTrue(self.srv.state.focus.accept())
        self.assertEqual(self.call('/api/focus/frame',cookie=cookie,frame=True)[0],200)
        self.assertEqual(self.call('/api/focus/stop',cookie=cookie)[0],200)
    def test_logout_stops_focus(self):
        self.srv.state.focus.stop();cookie=self.login()
        self.assertEqual(self.call('/api/focus/request',cookie=cookie)[0],200)
        self.assertEqual(self.call('/api/logout',cookie=cookie)[0],200)
        self.assertEqual(self.srv.state.focus.latest()[0],'idle')
    def test_no_other_session_can_take_over_focus(self):
        self.srv.state.focus.stop(); first=self.login();second=self.login()
        self.assertEqual(self.call('/api/focus/request',cookie=first)[0],200)
        self.srv.state.focus.accept()
        self.assertEqual(self.call('/api/focus/stop',cookie=second)[0],403)
        self.assertEqual(self.call('/api/focus/frame',cookie=second,frame=True)[0],409)
        self.srv.state.focus.stop()

if __name__=='__main__': unittest.main()
