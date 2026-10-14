import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_exchange import FileExchange, MAX_FILE, safe_name
from remote_server import RemoteHTTPServer

class DummyController:
    def screen_size(self): return (1280, 720)
    def screenshot_jpeg(self): return b'\xff\xd8\xff\xd9'
    def perform(self, data): pass

class FileStateTests(unittest.TestCase):
    def test_owner_and_host_consent(self):
        files=FileExchange()
        key=files.offer('first','../../hello.txt',4)
        self.assertEqual(files.status(key,'first')['filename'],'hello.txt')
        self.assertIsNone(files.status(key,'second'))
        self.assertFalse(files.accept_bytes(key,'first',b'data'))
        self.assertEqual(files.next_prompt()[0],key)
        self.assertIsNone(files.next_prompt())
        with tempfile.TemporaryDirectory() as td:
            destination=str(Path(td)/'saved.txt')
            self.assertTrue(files.decision(key,destination))
            self.assertFalse(files.accept_bytes(key,'second',b'data'))
            self.assertTrue(files.accept_bytes(key,'first',b'data'))
            self.assertEqual(Path(destination).read_bytes(),b'data')
            self.assertFalse(files.accept_bytes(key,'first',b'data'))

    def test_submission_requires_local_file_selection(self):
        files=FileExchange()
        key=files.request('admin')
        self.assertIsNone(files.download(key,'admin'))
        with tempfile.TemporaryDirectory() as td:
            selected=Path(td)/'report.txt';selected.write_bytes(b'report')
            self.assertTrue(files.decision(key,str(selected)))
            self.assertIsNone(files.download(key,'other'))
            self.assertEqual(files.download(key,'admin'),('report.txt',b'report'))
            self.assertIsNone(files.download(key,'admin'))

    def test_bad_file_name_size_cancel_revocation(self):
        files=FileExchange()
        with self.assertRaises(ValueError): files.offer('admin','a',MAX_FILE+1)
        with self.assertRaises(ValueError): safe_name('...')
        key=files.offer('admin','work.txt',4)
        files.decision(key,None)
        self.assertEqual(files.status(key,'admin')['state'],'denied')
        files.revoke('admin')
        self.assertIsNone(files.status(key,'admin'))

class FileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv=RemoteHTTPServer(('127.0.0.1',0),DummyController(),Path(__file__).resolve().parents[1]/'web/index.html')
        cls.thread=threading.Thread(target=cls.srv.serve_forever,daemon=True);cls.thread.start()
        cls.host=f'127.0.0.1:{cls.srv.server_address[1]}'
    @classmethod
    def tearDownClass(cls): cls.srv.stop()
    def call(self,method,path,body=None,cookie=None,content_type='application/json'):
        con=http.client.HTTPConnection('127.0.0.1',self.srv.server_address[1],timeout=4)
        headers={'Host':self.host,'Origin':f'http://{self.host}', 'Content-Type':content_type}
        if cookie:headers['Cookie']=cookie
        if isinstance(body,dict):body=json.dumps(body).encode()
        con.request(method,path,body=body,headers=headers)
        res=con.getresponse();data=res.read();session=res.getheader('Set-Cookie');code=res.status;con.close()
        try: data=json.loads(data)
        except (ValueError, UnicodeDecodeError):pass
        return code,data,session
    def login(self):
        code,data,s=self.call('POST','/api/login',{'pin':self.srv.state.pin})
        self.assertEqual(code,200)
        return s.split(';')[0]
    def test_file_offer_requires_login_and_consent(self):
        self.assertEqual(self.call('POST','/api/files/offer',{'filename':'report.txt','size':4})[0],401)
        cookie=self.login()
        code,result,_=self.call('POST','/api/files/offer',{'filename':'report.txt','size':4},cookie)
        self.assertEqual(code,200);key=result['id']
        self.assertEqual(self.call('POST',f'/api/files/upload?id={key}',b'data',cookie,'application/octet-stream')[0],409)
        with tempfile.TemporaryDirectory() as td:
            dest=str(Path(td)/'report.txt')
            self.srv.state.files.next_prompt();self.srv.state.files.decision(key,dest)
            code,data,_=self.call('POST',f'/api/files/upload?id={key}',b'data',cookie,'application/octet-stream')
            self.assertEqual(code,200);self.assertEqual(Path(dest).read_bytes(),b'data')
    def test_request_requires_managed_selection_and_same_cookie(self):
        cookie=self.login();other=self.login()
        code,result,_=self.call('POST','/api/files/request',{},cookie)
        self.assertEqual(code,200);key=result['id']
        self.assertEqual(self.call('GET',f'/api/files/download?id={key}',cookie=cookie)[0],409)
        self.assertEqual(self.call('GET',f'/api/files/status?id={key}',cookie=other)[0],404)
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'answer.txt';f.write_text('yes')
            self.srv.state.files.decision(key,str(f))
            self.assertEqual(self.call('GET',f'/api/files/download?id={key}',cookie=other)[0],409)
            code,data,_=self.call('GET',f'/api/files/download?id={key}',cookie=cookie)
            self.assertEqual(code,200);self.assertEqual(data,b'yes')

if __name__=='__main__':unittest.main()
