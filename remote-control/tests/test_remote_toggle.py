"""Admin ON/OFF switches the authenticated session, not the managed PC GUI."""
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
    def call(self,method,path,payload=None,cookie=None,origin=True):
        port=self.server.server_address[1]
        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        headers={'Host':f'127.0.0.1:{port}','Content-Type':'application/json'}
        if origin: headers['Origin']=f'http://127.0.0.1:{port}'
        if cookie: headers['Cookie']=cookie
        data=json.dumps(payload).encode() if payload is not None else None
        conn.request(method,path,body=data,headers=headers)
        r=conn.getresponse(); status=r.status; raw=r.read(); cookie_header=r.getheader('Set-Cookie');conn.close()
        return status,raw,cookie_header
    def login(self):
        status,_,cookie=self.call('POST','/api/login',{'pin':self.server.state.pin})
        self.assertEqual(status,200);return cookie.split(';')[0]
    def status(self,c):
        code,raw,_=self.call('GET','/api/status',cookie=c)
        self.assertEqual(code,200)
        return json.loads(raw)['remoteControlEnabled']
    def test_admin_on_off_works_and_does_not_disable_screen(self):
        c=self.login()
        self.assertFalse(self.status(c))
        self.assertEqual(self.call('GET','/api/frame',cookie=c)[0],200)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],403)
        self.assertEqual(self.call('POST','/api/control',{'enabled':True},c)[0],200)
        self.assertTrue(self.status(c))
        before=len(self.control.actions)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],200)
        self.assertEqual(len(self.control.actions),before+1)
        releases=self.control.releases
        self.assertEqual(self.call('POST','/api/control',{'enabled':False},c)[0],200)
        self.assertGreater(self.control.releases,releases)
        self.assertFalse(self.status(c))
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],403)
        self.assertEqual(self.call('GET','/api/frame',cookie=c)[0],200)
    def test_each_login_has_separate_authority(self):
        first=self.login();second=self.login()
        self.assertEqual(self.call('POST','/api/control',{'enabled':True},first)[0],200)
        self.assertTrue(self.status(first));self.assertFalse(self.status(second))
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.3,'y':0.3},second)[0],403)
        self.assertEqual(self.call('POST','/api/logout',{},first)[0],200)
        self.assertFalse(self.status(second))
    def test_missing_or_invalid_auth_cannot_toggle(self):
        self.assertEqual(self.call('POST','/api/control',{'enabled':True})[0],401)
        c=self.login()
        self.assertEqual(self.call('POST','/api/control',{'enabled':True},c,origin=False)[0],403)
        self.assertFalse(self.status(c))
    def test_boolean_parameter_is_required(self):
        c=self.login()
        for value in [0,1,'true','false',None,{},[]]:
            self.assertEqual(self.call('POST','/api/control',{'enabled':value},c)[0],400)
        self.assertFalse(self.status(c))
    def test_logout_revokes_control(self):
        c=self.login()
        self.assertEqual(self.call('POST','/api/control',{'enabled':True},c)[0],200)
        self.assertEqual(self.call('POST','/api/logout',{},c)[0],200)
        self.assertEqual(self.call('POST','/api/action',{'type':'move','x':0.1,'y':0.5},c)[0],401)

if __name__ == '__main__': unittest.main()
