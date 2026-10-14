"""HTTP integration tests for actionable remote-control failures and fallback."""
import http.client
import json
import threading
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from remote_server import RemoteHTTPServer

class FailSafeException(Exception): pass

class FakeController:
    def __init__(self): self.problem=None; self.actions=[]
    def screen_size(self): return (1920,1080)
    def screenshot_jpeg(self): return b'\xff\xd8\xff\xd9'
    def perform(self,action):
        if self.problem: raise self.problem
        self.actions.append(action)
    def release_all(self): pass

class InputErrorTests(unittest.TestCase):
    def setUp(self):
        self.ctrl=FakeController()
        self.server=RemoteHTTPServer(('127.0.0.1',0),self.ctrl,Path(__file__).resolve().parents[1]/'web/index.html')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        code,body,headers=self.post('/api/login',{'pin':self.server.state.pin})
        self.assertEqual(code,200)
        self.cookie=headers.get('set-cookie').split(';')[0]
    def tearDown(self):self.server.stop()
    def post(self,path,data):
        host=f'127.0.0.1:{self.server.server_port}'
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        headers={'Origin':'http://'+host,'Content-Type':'application/json'}
        if hasattr(self,'cookie'):headers['Cookie']=self.cookie
        conn.request('POST',path,body=json.dumps(data).encode(),headers=headers)
        r=conn.getresponse();code=r.status;body=r.read();hdr={k.lower():v for k,v in r.getheaders()};conn.close()
        return code,json.loads(body),hdr
    def test_action_requires_explicit_on_and_failure_explains_windows_failsafe(self):
        act={'type':'move','x':0.3,'y':0.5}
        status,body,_=self.post('/api/action',act)
        self.assertEqual(status,403);self.assertIn('OFF',body['error'])
        self.assertEqual(self.post('/api/control',{'enabled':True})[0],200)
        self.ctrl.problem=FailSafeException('sensitive')
        status,body,_=self.post('/api/action',act)
        self.assertEqual(status,503);self.assertIn('안전 정지',body['error']);self.assertNotIn('sensitive',body['error'])
        self.ctrl.problem=PermissionError('sensitive')
        status,body,_=self.post('/api/action',act)
        self.assertEqual(status,503);self.assertIn('Windows',body['error']);self.assertNotIn('sensitive',body['error'])
        self.ctrl.problem=None
        self.assertEqual(self.post('/api/action',act)[0],200)
        self.assertEqual(len(self.ctrl.actions),1)
        self.assertEqual(self.post('/api/control',{'enabled':False})[0],200)
        self.assertEqual(self.post('/api/action',act)[0],403)
if __name__=='__main__':unittest.main()
