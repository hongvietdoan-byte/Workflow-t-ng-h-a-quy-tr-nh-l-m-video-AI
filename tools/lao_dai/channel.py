"""Kênh cấp trên server; pet chỉ đọc credential OS và GET loopback.

Phiên Owner chỉ tồn tại trong SnapshotBroker RAM. Không renewal ngầm: hết 300s
phải bấm cấp lại trên 8502. HMAC challenge xác minh server TRƯỚC Bearer,
cùng socket keep-alive, không tự reconnect, redirect hay proxy.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
import threading
import time

TARGET = 'AI.VideoPipeline.LaoDai.ReadOnly.v1'
MAX_BODY = 1024 * 1024

@dataclass(frozen=True, repr=False)
class Grant:
    token: str
    port: int
    expires_at: float

    def validate(self):
        if (not isinstance(self.token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',self.token) or
            type(self.port) is not int or not 1024<=self.port<=65535 or self.port in (8501,8502) or
            type(self.expires_at) not in (int,float) or not 0<self.expires_at-time.time()<=300):
            raise ValueError('Quyền pet thiếu, hết hạn hoặc sai cấu hình')
        return self

@contextmanager
def credential_mutex(target):
    """Cùng user, mọi Windows session: kho credential không tách theo session."""
    import win32api,win32con,win32event,win32security
    process_token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32con.TOKEN_QUERY)
    try:
        sid=win32security.ConvertSidToStringSid(win32security.GetTokenInformation(process_token,win32security.TokenUser)[0])
    finally:process_token.Close()
    name='Global\\AI.VideoPipeline.LaoDai.Credential.'+sid+'.'+hashlib.sha256(target.encode()).hexdigest()
    handle=win32event.CreateMutex(None,False,name)
    acquired=False
    try:
        result=win32event.WaitForSingleObject(handle,5000)
        if result not in (win32event.WAIT_OBJECT_0,win32event.WAIT_ABANDONED):
            raise PermissionError('Kho credential đang bận; thử lại')
        acquired=True
        yield
    finally:
        if acquired:win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)

class CredentialStore:
    def __init__(self, target=TARGET, *, native=None, lock_factory=None):
        if target!=TARGET and not re.fullmatch(r'AI\.VideoPipeline\.LaoDai\.QA\.[A-Za-z0-9_-]{1,80}',target):
            raise ValueError('Tên credential không được phép')
        self.target=target
        if native is None:
            import win32cred
            native=win32cred
        self.native=native
        self._transaction=lock_factory or (lambda:credential_mutex(self.target))

    def write(self, grant):
        with self._transaction():self._write(grant)

    def _write(self,grant):
        grant.validate()
        # pywin32 CredWrite yêu cầu Unicode; CredRead trả blob UTF-16LE bytes.
        blob=json.dumps({'token':grant.token,'port':grant.port,'expires_at':grant.expires_at})
        self.native.CredWrite({'Type':self.native.CRED_TYPE_GENERIC,'TargetName':self.target,
            'UserName':'LaoDaiReadOnly','CredentialBlob':blob,'Persist':self.native.CRED_PERSIST_SESSION},0)

    def read(self):
        with self._transaction():return self._read()

    def _read(self):
        try:
            row=self.native.CredRead(self.target,self.native.CRED_TYPE_GENERIC,0)
        except Exception as error:
            if getattr(error,'winerror',None)==1168 or (error.args and error.args[0]==1168):return None
            raise PermissionError('Không đọc được kho credential Windows') from None
        try:
            value=json.loads(row['CredentialBlob'].decode('utf-16-le'))
            return Grant(value['token'],value['port'],value['expires_at']).validate()
        except (ValueError,KeyError,TypeError,AttributeError):
            self._delete();return None

    def delete_if(self,grant):
        with self._transaction():
            current=self._read()
            if current is not None and current.port==grant.port and hmac.compare_digest(current.token,grant.token):
                self._delete()

    def delete(self):
        with self._transaction():self._delete()

    def _delete(self):
        try:self.native.CredDelete(self.target,self.native.CRED_TYPE_GENERIC,0)
        except Exception as error:
            if not (getattr(error,'winerror',None)==1168 or (error.args and error.args[0]==1168)):
                raise PermissionError('Không xóa được quyền pet trong kho Windows') from None

def proof(token, nonce):
    return hmac.new(token.encode('utf-8'),('lao-dai-v1:'+nonce).encode('ascii'),hashlib.sha256).hexdigest()

def delete_grant(store,grant):
    """Một poll cũ không xóa quyền mới vừa được Owner cấp lại."""
    store.delete_if(grant)

class PetClient:
    def __init__(self, store):self.store=store

    def snapshot(self):
        grant=self.store.read()
        if grant is None:raise PermissionError('Chưa cấp quyền pet; mở Phiếu trên 8502')
        try:grant.validate()
        except ValueError:
            delete_grant(self.store,grant);raise PermissionError('Quyền pet hết hạn; cấp lại trên 8502') from None
        conn=http.client.HTTPConnection('127.0.0.1',grant.port,timeout=3)
        authenticated=False
        try:
            nonce=secrets.token_hex(32)
            conn.connect()
            sock=conn.sock
            conn.auto_open=0
            conn.request('GET','/hello?nonce='+nonce)
            response=conn.getresponse()
            if response.status!=200 or response.will_close:raise PermissionError('Broker chưa được xác minh')
            body=self._read(response)
            if conn.sock is not sock or not hmac.compare_digest(str(body.get('proof','')),proof(grant.token,nonce)):
                raise PermissionError('Broker chưa được xác minh')
            authenticated=True
            # auto_open=0: EOF/takeover KHÔNG mở socket mới mang Bearer.
            conn.request('GET','/snapshot',headers={'Authorization':'Bearer '+grant.token})
            response=conn.getresponse()
            if response.status==503:raise ConnectionError('Broker chưa đọc được snapshot')
            if response.status!=200:raise PermissionError('Quyền Owner/pet bị thu hồi hoặc broker đang tắt')
            return self._read(response)
        except PermissionError:
            delete_grant(self.store,grant);raise
        except (OSError,http.client.HTTPException,ValueError,TypeError):
            if not authenticated:delete_grant(self.store,grant)
            raise ConnectionError('Không đọc được broker loopback') from None
        finally:conn.close()

    @staticmethod
    def _read(response):
        data=response.read(MAX_BODY+1)
        if len(data)>MAX_BODY:raise ValueError('Snapshot quá lớn')
        body=json.loads(data)
        if not isinstance(body,dict):raise ValueError('Snapshot sai định dạng')
        return body

class ChannelService:
    """Chỉ do server8502 tạo. Không endpoint mạng nào cấp quyền."""
    def __init__(self, broker, store):
        self.broker=broker;self.store=store;self.grant=None;self.server=None
        self._lock=threading.RLock();self._done=threading.Event()
        self._lifecycle=threading.RLock()

    @property
    def active(self):return self.grant is not None

    def authorize(self,session,*,local,owner):
        if local is not True or owner is not True or not session:raise PermissionError('Chỉ Owner local được cấp quyền pet')
        with self._lifecycle:self._authorize(session)

    def _authorize(self,session):
        # Phiên sai không làm gián đoạn grant đang chạy của Owner khác.
        token=self.broker.issue(session,ttl=300)
        try:self.stop()
        except Exception:
            # stop có thể lỗi khi xóa credential cũ; token mới chưa thành grant.
            self.broker.revoke(token);raise
        with self._lock:
            service=self
            class Handler(BaseHTTPRequestHandler):
                protocol_version='HTTP/1.1'
                def setup(self):
                    super().setup();self.connection.settimeout(3)
                def log_message(self,*args):pass
                def reply(self,status,body):
                    payload=json.dumps(body,ensure_ascii=False).encode('utf-8')
                    self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
                    self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)))
                    self.end_headers();self.wfile.write(payload)
                def do_GET(self):
                    if self.headers.get('Origin') or self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':
                        self.reply(403,{'error':'Chỉ client loopback'});return
                    try:
                        with service._lock:
                            grant=service.grant
                            if grant is None:raise PermissionError()
                            grant.validate()
                            if re.fullmatch(r'/hello\?nonce=[a-f0-9]{64}',self.path):
                                service.broker.validate(grant.token) # kiểm Owner thật mỗi poll trước proof
                                self.reply(200,{'proof':proof(grant.token,self.path.split('=')[1])})
                            elif self.path=='/snapshot':
                                supplied=self.headers.get('Authorization','')
                                if not hmac.compare_digest(supplied,'Bearer '+grant.token):
                                    self.reply(401,{'error':'Cần token chỉ đọc'});return
                                self.reply(200,service.broker.snapshot(grant.token))
                            else:self.reply(404,{'error':'Đường đọc không hợp lệ'})
                    except (PermissionError,ValueError):
                        service.invalidate();self.reply(401,{'error':'Quyền pet hết hạn hoặc đã thu hồi'})
                    except Exception:self.reply(503,{'error':'Broker không sẵn sàng'})
                def reject(self):
                    self.close_connection=True;self.reply(405,{'error':'Chỉ GET'})
                do_POST=do_PUT=do_PATCH=do_DELETE=do_HEAD=do_OPTIONS=do_TRACE=do_CONNECT=reject
            try:self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            except Exception:
                self.broker.revoke(token);raise
            self.server.daemon_threads=True
            self.grant=Grant(token,self.server.server_port,time.time()+300)
            try:self.store.write(self.grant)
            except Exception:
                self.server.server_close();self.server=None
                self.invalidate();raise
            self._done=threading.Event()
            threading.Thread(target=self.server.serve_forever,daemon=True,name='lao-dai-broker').start()
            threading.Thread(target=self._watch,args=(self._done,),daemon=True,name='lao-dai-expiry').start()

    def invalidate(self):
        with self._lock:
            previous=self.grant
            self.grant=None
            if previous is not None:
                self.broker.revoke(previous.token)
                delete_grant(self.store,previous)

    def check(self):
        with self._lifecycle:self._check()

    def _check(self):
        with self._lock:
            try:
                if self.grant is None:raise PermissionError()
                self.grant.validate();self.broker.validate(self.grant.token)
            except (PermissionError,ValueError):
                self.invalidate();invalid=True
            else:invalid=False
        if invalid:self.stop()

    def _watch(self,done):
        while not done.wait(2):
            with self._lifecycle:
                if done is not self._done or done.is_set():return
                try:self._check()
                except Exception:
                    # Lỗi CSDL/credential không được làm watchdog chết và bỏ quyền tồn tại.
                    self._stop();return

    def stop(self):
        with self._lifecycle:self._stop()

    def _stop(self):
        with self._lock:
            self._done.set();server=self.server;self.server=None
            try:
                if self.grant is not None:self.invalidate()
            finally:
                if server is not None:server.shutdown();server.server_close()
