"""Windowed vs focused screen broadcast requires consent and correct session ownership."""
import unittest
import http.client
import json
from pathlib import Path
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from focus_mode import FocusSession
from remote_server import RemoteHTTPServer

class Controller:
    def screen_size(self): return (1920,1080)
    def screenshot_jpeg(self): return b'\xff\xd8\xff\xd9'

class BroadcastTests(unittest.TestCase):
    def test_window_and_focus_modes_preserve_local_approval(self):
        for mode in ('window','focus'):
            s=FocusSession()
            self.assertTrue(s.request('admin',mode))
            self.assertEqual(s.display(),mode)
            self.assertFalse(s.push('admin',b'\xff\xd8frame\xff\xd9'))
            self.assertTrue(s.accept())
            self.assertTrue(s.push('admin',b'\xff\xd8frame\xff\xd9'))
            self.assertFalse(s.push('other',b'\xff\xd8frame\xff\xd9'))
            self.assertTrue(s.stop('admin'))
    def test_rejects_unsupported_display_mode(self):
        s=FocusSession()
        self.assertFalse(s.request('admin','locked'))
        self.assertEqual(s.status('admin'),'idle')
    def test_http_window_request_only_with_authenticated_cookie(self):
        path=Path(__file__).resolve().parents[1]/'web/index.html'
        server=RemoteHTTPServer(('127.0.0.1',0),Controller(),path)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            host=f'127.0.0.1:{server.server_address[1]}'
            def post(uri, data, cookie=None):
                c=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=3)
                headers={'Origin':'http://'+host,'Host':host,'Content-Type':'application/json'}
                if cookie: headers['Cookie']=cookie
                c.request('POST',uri,json.dumps(data).encode(),headers)
                response=c.getresponse()
                status=response.status; token=response.getheader('Set-Cookie')
                response.read();c.close()
                return status,token
            self.assertEqual(post('/api/focus/request',{'displayMode':'window'})[0],401)
            code,session=post('/api/login',{'pin':server.state.pin})
            self.assertEqual(code,200)
            cookie=session.split(';')[0]
            self.assertEqual(post('/api/focus/request',{'displayMode':'invalid'},cookie)[0],400)
            self.assertEqual(post('/api/focus/request',{'displayMode':'window'},cookie)[0],200)
            self.assertEqual(server.state.focus.display(),'window')
            self.assertEqual(server.state.focus.status(cookie),'idle')  # token is the cookie *value*, not entire header
            self.assertTrue(server.state.focus.accept())
            self.assertEqual(server.state.focus.latest()[0],'active')
            self.assertEqual(post('/api/focus/stop',{},cookie)[0],200)
            self.assertEqual(server.state.focus.latest()[0],'idle')
        finally:
            server.stop()

if __name__=='__main__': unittest.main()
