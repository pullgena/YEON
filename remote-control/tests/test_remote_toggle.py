"""Verify the OFF control is enforced by the host even for logged-in admins."""
import http.client
import json
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from remote_server import RemoteHTTPServer

class Controller:
    def __init__(self): self.actions=[]; self.releases=0
    def screen_size(self): return (1920,1080)
    def screenshot_jpeg(self): return b'\xff\xd8\xff\xd9'
    def perform(self, action): self.actions.append(action)
    def release_all(self): self.releases+=1

class ControlToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control=Controller()
        cls.server=RemoteHTTPServer(('127.0.0.1',0),cls.control,Path(__file__).resolve().parents[1]/'web/index.html')
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls): cls.server.stop()
    def call(self,method,path,payload=None,cookie=None):
        port=self.server.server_address[1]
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        headers={'Host':f'127.0.0.1:{port}','Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json'}
        if cookie: headers['Cookie']=cookie
        data=json.dumps(payload).encode() if payload is not None else None
        conn.request(method,path,body=data,headers=headers)
        r=conn.getresponse(); status=r.status; raw=r.read(); cookie_header=r.getheader('Set-Cookie');conn.close()
        return status,raw,cookie_header
    def login(self):
        status,_,cookie=self.call('POST','/api/login',{'pin':self.server.state.pin})
        self.assertEqual(status,200);return cookie.split(';')[0]
    def test_default_off_still_allows_screen(self):
        self.server.state.set_remote_control(False)
        c=self.login()
        self.assertEqual(self.call('GET','/api/frame',cookie=c)[0],200)
        status,data,_=self.call('GET','/api/status',cookie=c)
        self.assertEqual(status,200)
        self.assertIs(json.loads(data)['remoteControlEnabled'],False)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],403)
    def test_on_allows_input_off_immediately_blocks_existing_session(self):
        c=self.login()
        self.server.state.set_remote_control(True)
        self.assertIs(json.loads(self.call('GET','/api/status',cookie=c)[1])['remoteControlEnabled'],True)
        initial=len(self.control.actions)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],200)
        self.assertEqual(len(self.control.actions),initial+1)
        before=self.control.releases
        self.server.state.set_remote_control(False)
        self.assertGreater(self.control.releases,before)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],403)
        self.assertEqual(len(self.control.actions),initial+1)
    def test_remote_cannot_set_permission(self):
        c=self.login()
        for path in ['/api/control/on','/api/control/toggle','/api/set_control']:
            self.assertEqual(self.call('POST',path,{'enabled':True},c)[0],404)
        self.assertFalse(self.server.state.can_remote_control())

if __name__ == '__main__':unittest.main()
