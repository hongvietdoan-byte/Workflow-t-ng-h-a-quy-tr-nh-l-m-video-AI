"""Hồi quy giao diện/credential; không dùng credential hay CSDL sản xuất."""
import contextlib
import json
import time
import threading
import http.client
import pytest

from tools.lao_dai.channel import Grant, CredentialStore, PetClient, ChannelService
from tools.lao_dai.gui import PetController, ticket_url
from tools.lao_dai.native import toast_xml

class MemoryStore:
    def __init__(self): self.value = None
    def write(self, grant): self.value = grant
    def read(self): return self.value
    def delete(self): self.value = None
    def delete_if(self, grant):
        if self.value == grant: self.value = None

class Broker:
    def __init__(self): self.enabled=True; self.valid=True; self.tokens={}; self.reads=0; self.issued=0
    def _enabled(self):
        if not self.enabled: raise PermissionError()
    def issue(self, session, ttl=300):
        self._enabled()
        if session!='owner' or not self.valid: raise PermissionError()
        self.issued+=1; token='synthetic-token-for-test-'+str(self.issued); self.tokens[token]=True; return token
    def validate(self, token):
        self._enabled()
        if not self.valid or token not in self.tokens: raise PermissionError()
    def revoke(self, token):
        self.tokens.pop(token,None)
    def snapshot(self, token):
        self._enabled()
        if not self.valid or token not in self.tokens: raise PermissionError()
        self.reads+=1
        return {'schema_version':1,'enabled':True,'available':True,'ticket_counts':{'waiting_admin':1},'ticket_summaries':[{'id':'TN-001','state':'waiting_admin','due_status':'red','title':'NEVER SHOW TITLE'}]}

def test_service_explicit_owner_and_revoke():
    b=Broker(); store=MemoryStore(); service=ChannelService(b,store)
    try:
        for session,local,owner in [('owner',False,True),('owner',True,False),('',True,True)]:
            with pytest.raises(PermissionError):service.authorize(session,local=local,owner=owner)
        service.authorize('owner',local=True,owner=True)
        grant=store.read()
        assert 0<grant.expires_at-time.time()<=300
        assert PetClient(store).snapshot()['available']
        b.valid=False
        with pytest.raises(PermissionError):PetClient(store).snapshot()
        assert store.read() is None
        assert not service.active
    finally:service.stop()

def test_off_stops_cached_service_and_deletes_grant():
    b=Broker(); store=MemoryStore(); service=ChannelService(b,store)
    service.authorize('owner',local=True,owner=True)
    b.enabled=False
    service.check()
    assert not service.active and store.read() is None

def test_expiry_deletes_without_network():
    store=MemoryStore();store.write(Grant('x',12345,time.time()-1))
    with pytest.raises(PermissionError):PetClient(store).snapshot()
    assert store.read() is None

def test_untrusted_port_never_receives_bearer():
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            seen.append(dict(self.headers)); body=b'{"proof":"wrong"}'
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    store=MemoryStore();store.write(Grant('secret',server.server_port,time.time()+10))
    try:
        with pytest.raises(PermissionError):PetClient(store).snapshot()
        assert seen and all('Authorization' not in h for h in seen)
        assert store.read() is None
    finally:server.shutdown();server.server_close()

def test_native_store_fake_safe_target():
    class Native:
        CRED_TYPE_GENERIC=1;CRED_PERSIST_SESSION=1;CRED_PERSIST_LOCAL_MACHINE=2
        def __init__(self):self.rows={}
        def CredWrite(self,row,flags):
            assert isinstance(row['CredentialBlob'],str)
            assert row['Persist']==self.CRED_PERSIST_SESSION   # rà gộp 12/10: gone at sign-out, never outlives the session
            self.rows[row['TargetName']]=dict(row,CredentialBlob=row['CredentialBlob'].encode('utf-16-le'))
        def CredRead(self,target,kind,flags):return self.rows[target]
        def CredDelete(self,target,kind,flags):self.rows.pop(target,None)
    native=Native();store=CredentialStore('AI.VideoPipeline.LaoDai.QA.unittest',native=native,lock_factory=contextlib.nullcontext)   # Linux CI: no pywin32 mutex
    grant=Grant('test-only',32001,time.time()+100)
    store.write(grant)
    assert store.read()==grant
    row=next(iter(native.rows.values()))
    assert row['Type']==1 and 'test-only' in row['CredentialBlob'].decode('utf-16-le')
    store.delete();assert not native.rows

def test_controller_no_title_and_links_allowlist():
    store=MemoryStore();service=ChannelService(Broker(),store)
    draws=[];opened=[];toasts=[]
    controller=PetController(PetClient(store),draws.append,toasts.append,opened.append)
    try:
        service.authorize('owner',local=True,owner=True)
        controller.poll()
        assert draws[-1].state=='tickets' and '1 phiếu' in draws[-1].bubble
        assert toasts==['TN-001 · waiting_admin · red']
        controller.open_ticket();assert opened==['http://127.0.0.1:8502/?ticket=TN-001']
        controller.poll();assert len(toasts)==1
        service.stop();controller.poll();assert draws[-1].state=='disconnected'
        controller.open_ticket();assert len(opened)==1
        with pytest.raises(ValueError):ticket_url('bad&session=secret')
    finally:service.stop()

def test_toast_only_id_state_due_and_protocol_url():
    xml=toast_xml('TN-001 · waiting_admin · yellow')
    assert 'activationType="protocol"' in xml and '?ticket=TN-001' in xml
    assert 'waiting_admin' in xml and 'yellow' in xml
    with pytest.raises(ValueError):toast_xml('TN-001 · waiting_admin · yellow · SECRET')
    with pytest.raises(ValueError):toast_xml('bad&x=secret · waiting_admin · yellow')

@pytest.mark.parametrize('port,ttl',[(8502,10),(True,10),(12345,301)])
def test_grant_reject_reserved_ports_and_excess_ttl(port,ttl):
    with pytest.raises(ValueError):Grant('x',port,time.time()+ttl).validate()

def test_eof_proof_no_reconnect_or_redirect(monkeypatch):
    from tools.lao_dai.channel import proof
    class Socket:pass
    instances=[]
    class Connection:
        def __init__(self,host,port,timeout):self.sock=Socket();self.auto_open=1;self.calls=[];instances.append(self)
        def connect(self):pass
        def request(self,method,path,headers=None):
            if len(self.calls):
                assert self.auto_open==0
                raise http.client.NotConnected()
            self.calls.append((method,path,headers))
        def getresponse(self):
            nonce=self.calls[0][1].split('=')[1]
            class Response:
                status=200;will_close=False
                def read(self,n):return json.dumps({'proof':proof('test-token',nonce)}).encode()
            return Response()
        def close(self):pass
    monkeypatch.setattr(http.client,'HTTPConnection',Connection)
    store=MemoryStore();store.write(Grant('test-token',32100,time.time()+100))
    with pytest.raises(ConnectionError):PetClient(store).snapshot()
    assert len(instances)==1 and len(instances[0].calls)==1

def test_read_channel_rejects_origin_query_and_writes():
    store=MemoryStore();service=ChannelService(Broker(),store)
    try:
        service.authorize('owner',local=True,owner=True);port=store.read().port
        for method,path,headers,status in [('GET','/snapshot',{},401),('POST','/snapshot',{},405),
            ('GET','/snapshot?token=wrong',{},404),('GET','/snapshot',{'Origin':'https://evil.test'},403)]:
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            conn.request(method,path,headers=headers);response=conn.getresponse()
            assert response.status==status;response.read();conn.close()
        assert store.read() is not None # sai client không tự thu hồi Owner khác
        assert PetClient(store).snapshot()['available']
    finally:service.stop()

def test_ui_off_and_remote_owner_cannot_create_service(monkeypatch):
    from devsys import lao_dai_channel as module
    class UI:
        session_state={}
        def __init__(self):self.sidebar=self
        def caption(self,text):pass
    class Auth:
        TOKEN_KEY='private-session'
        def current(self):return 'owner'
        def is_owner(self,who):return True
        def request_source(self):return ('remote',False)
    monkeypatch.setattr(module,'_service',None)
    monkeypatch.setattr(module.features,'on',lambda key:False)
    module.render(UI(),Auth());assert module._service is None
    monkeypatch.setattr(module.features,'on',lambda key:True)
    module.render(UI(),Auth());assert module._service is None

def test_real_temp_database_through_credential_channel(tmp_path,monkeypatch):
    from core import auth,db,tickets
    from tools.lao_dai.broker import SnapshotBroker
    monkeypatch.setattr('core.features.on',lambda name:True)
    path=tmp_path/'qa.sqlite';conn=db.connect(str(path))
    conn.execute("INSERT INTO users(email,name,role,perms,active) VALUES ('owner@test.invalid','QA','owner','[]',1)")
    conn.execute('INSERT INTO sessions(token_hash,email,expires_at,created_at) VALUES (?,?,?,0)',
                 (auth._hash('qa-session'),'owner@test.invalid',time.time()+300))
    conn.commit()
    before=path.read_bytes()
    store=MemoryStore();service=ChannelService(SnapshotBroker(path,data_dir=tmp_path),store)
    try:
        service.authorize('qa-session',local=True,owner=True)
        snapshot=PetClient(store).snapshot()
        assert snapshot['schema_version']==1 and snapshot['available']
        assert path.read_bytes()==before
        conn.execute("UPDATE users SET role='member' WHERE email='owner@test.invalid'");conn.commit()
        with pytest.raises(PermissionError):PetClient(store).snapshot()
        assert store.read() is None
    finally:service.stop();conn.close()


@pytest.mark.parametrize('old_kind',['valid','expired','malformed'])
def test_credential_conditional_delete_serializes_regrant(old_kind):
    from contextlib import contextmanager
    from tools.lao_dai.channel import delete_grant
    lock=threading.RLock();observed=threading.Event();attempted=threading.Event()
    old=Grant('old',32101,time.time()+100);new=Grant('new',32102,time.time()+100)
    class Native:
        CRED_TYPE_GENERIC=1;CRED_PERSIST_SESSION=1;CRED_PERSIST_LOCAL_MACHINE=2
        row=None;pause=False
        def CredWrite(self,row,flags):self.row=dict(row,CredentialBlob=row['CredentialBlob'].encode('utf-16-le'))
        def CredRead(self,*args):
            result=self.row.copy()
            if self.pause:
                self.pause=False;observed.set();assert attempted.wait(2)
            return result
        def CredDelete(self,*args):self.row=None
    @contextmanager
    def transaction():
        with lock:yield
    native=Native();a=CredentialStore('AI.VideoPipeline.LaoDai.QA.atomic',native=native,lock_factory=transaction)
    b=CredentialStore('AI.VideoPipeline.LaoDai.QA.atomic',native=native,lock_factory=transaction)
    a.write(old)
    if old_kind=='expired':
        native.row['CredentialBlob']=json.dumps({'token':old.token,'port':old.port,'expires_at':time.time()-1}).encode('utf-16-le')
    elif old_kind=='malformed':native.row['CredentialBlob']=b'x'
    native.pause=True
    def writer():
        assert observed.wait(2);attempted.set();b.write(new)
    thread=threading.Thread(target=writer);thread.start()
    if old_kind=='valid':delete_grant(a,old)
    else:assert a.read() is None
    thread.join(2)
    assert not thread.is_alive() and b.read()==new
    delete_grant(a,old);assert b.read()==new


def test_monitor_bounds_dpi_and_removed_monitor():
    from tools.lao_dai.native import clamp_position,NativeWindow
    assert clamp_position(-2200,-20,330,300,(-1920,0,0,1040))==(-1920,0)
    assert clamp_position(1900,1000,495,450,(0,0,1920,1040))==(1425,590)
    class Gui:
        rect=(-1500,20,-1170,320)
        def GetWindowRect(self,hwnd):return self.rect
        def MonitorFromRect(self,rect,flags):return 'remaining-monitor'
        def GetMonitorInfo(self,monitor):return {'Work':(0,0,1920,1040)}
        def SetWindowPos(self,*args):self.position=args
        def ShowWindow(self,*args):self.shown=args
        def CallWindowProc(self,*args):return 0
    class Con:
        WM_MOUSEACTIVATE=33;MA_NOACTIVATE=3;HWND_TOPMOST=-1
        SWP_NOSIZE=1;SWP_NOACTIVATE=16;SW_SHOWNOACTIVATE=4;SW_HIDE=0
    window=NativeWindow.__new__(NativeWindow);window.gui=Gui();window.con=Con();window.hwnd=1;window.old=0
    events=[];window.layout_callback=lambda *args:events.append(args)
    window.show();assert window.gui.position[2:4]==(0,20)
    assert window.gui.position[-1]&16 and window.gui.shown[-1]==4
    import ctypes
    rect=(ctypes.c_long*4)(100,200,595,650)
    window._proc(1,0x02E0,144|(144<<16),ctypes.addressof(rect))
    assert events==[(144,(100,200,595,650))]
    window._proc(1,0x007E,0,0);assert events[-1]==(None,None)


def test_tk_layout_rescales_without_activation():
    from tools.lao_dai.gui import PetApp
    class Canvas:
        def configure(self,**kw):self.options=kw
    class Root:
        def geometry(self,value):self.value=value
        def update_idletasks(self):pass
    class Native:
        def move(self,x,y):self.position=(x,y)
        def dpi(self):return 96
        def reposition(self):self.clamped=True
    app=PetApp.__new__(PetApp);app.canvas=Canvas();app.root=Root();app.native=Native();app.scale=1
    app._layout(144,(100,200,595,650))
    assert app.scale==1.5 and app.canvas.options=={'width':495,'height':450}
    assert app.native.position==(100,200)
    app._layout(None,None);assert app.scale==1 and app.native.clamped


def test_stale_watchdog_keeps_new_credential():
    store=MemoryStore();broker=Broker();service=ChannelService(broker,store)
    try:
        service.authorize('owner',local=True,owner=True)
        new=Grant('new-epoch',32102,time.time()+100);store.write(new)
        broker.valid=False;service.check()
        assert service.server is None and store.read()==new
    finally:service.stop()


@pytest.mark.parametrize('reason',['Quyền pet hết hạn; cấp lại trên 8502','Quyền Owner/pet bị thu hồi hoặc broker đang tắt'])
def test_disconnected_draw_shows_reason(reason):
    from tools.lao_dai.gui import PetApp
    from tools.lao_dai.logic import PetView
    class Canvas:
        def __init__(self):self.texts=[]
        def delete(self,*args):pass
        def create_text(self,*args,**kwargs):self.texts.append(kwargs)
        def __getattr__(self,name):return lambda *args,**kwargs:None
    app=PetApp.__new__(PetApp);app.canvas=Canvas();app.scale=1.5;app.notice=''
    app.controller=type('Controller',(),{'selected':None})()
    app.draw(PetView('disconnected','Mất kết nối',reason))
    assert any(row['text']==reason and row.get('width')==290*app.scale for row in app.canvas.texts)


def test_watchdog_checks_auth_without_reading_ticket_snapshot():
    broker=Broker();store=MemoryStore();service=ChannelService(broker,store)
    try:
        service.authorize('owner',local=True,owner=True)
        service.check()
        assert broker.reads==0
        first=service.grant.token
        service.authorize('owner',local=True,owner=True)
        assert first not in broker.tokens
        second=service.grant.token
        service.stop()
        assert second not in broker.tokens
    finally:service.stop()


def test_three_reauthorizations_and_failed_store_leave_no_token():
    broker=Broker();store=MemoryStore();service=ChannelService(broker,store)
    try:
        previous=[]
        for _ in range(3):
            service.authorize('owner',local=True,owner=True)
            token=service.grant.token
            assert token not in previous and set(broker.tokens)=={token}
            previous.append(token)
        service.stop()
        def fail(grant):raise OSError('fake credential failure')
        store.write=fail
        with pytest.raises(OSError):service.authorize('owner',local=True,owner=True)
        assert not broker.tokens and not service.active
    finally:service.stop()


def test_bind_failure_revokes_new_token(monkeypatch):
    import tools.lao_dai.channel as channel
    broker=Broker();store=MemoryStore();service=ChannelService(broker,store)
    def fail(*a,**k):raise OSError('fake bind failure')
    monkeypatch.setattr(channel,'ThreadingHTTPServer',fail)
    with pytest.raises(OSError):service.authorize('owner',local=True,owner=True)
    assert not broker.tokens and not service.active and store.value is None


def test_partial_credential_write_cleans_grant_and_token():
    broker=Broker();store=MemoryStore();service=ChannelService(broker,store)
    def fail(grant):
        store.value=grant
        raise OSError('fake partial write')
    store.write=fail
    with pytest.raises(OSError):service.authorize('owner',local=True,owner=True)
    assert not broker.tokens and not service.active and store.value is None


@pytest.fixture
def real_owner_broker(tmp_path, monkeypatch):
    import sqlite3
    from core import auth, tickets
    from tools.lao_dai.broker import SnapshotBroker
    path=tmp_path/'owner-fixture.sqlite'
    conn=sqlite3.connect(path)
    conn.executescript("CREATE TABLE users(email TEXT,name TEXT,role TEXT,perms TEXT,active INTEGER); "
                      "CREATE TABLE sessions(token_hash TEXT,email TEXT,expires_at REAL); "
                      "INSERT INTO users VALUES ('fixture@example.test','Fixture','owner','[]',1)")
    session='synthetic-session'
    conn.execute('INSERT INTO sessions VALUES (?,?,?)',
                 (auth._hash(session),'fixture@example.test',time.time()+300))
    conn.commit()
    flags={'enabled':True}
    monkeypatch.setattr('core.features.on',lambda name:flags['enabled'])
    def no_snapshot(*args,**kwargs):raise AssertionError('validate không được quét phiếu/sổ chi')
    monkeypatch.setattr(tickets,'admin_snapshot',no_snapshot)
    try:yield SnapshotBroker(path),conn,session,flags,path
    finally:conn.close()


def test_reauthorize_delete_failure_revokes_new_token_real_broker(real_owner_broker):
    broker,conn,session,flags,path=real_owner_broker
    store=MemoryStore();service=ChannelService(broker,store)
    token=broker.issue(session)
    service.grant=Grant(token,12345,time.time()+299)
    store.value=service.grant
    before=path.read_bytes()
    def fail(grant):raise PermissionError('synthetic credential deletion error')
    store.delete_if=fail
    with pytest.raises(PermissionError,match='synthetic credential deletion'):
        service.authorize(session,local=True,owner=True)
    assert not broker._tokens and not service.active and service.server is None
    assert path.read_bytes()==before


@pytest.mark.parametrize('reason',['owner_disabled','session_revoked','flag_off','expired'])
def test_real_broker_watchdog_rechecks_auth_without_snapshot(real_owner_broker,reason):
    broker,conn,session,flags,path=real_owner_broker
    store=MemoryStore();service=ChannelService(broker,store)
    token=broker.issue(session)
    service.grant=Grant(token,12345,time.time()+299);store.value=service.grant
    before=path.read_bytes();service.check()
    assert service.active and path.read_bytes()==before
    if reason=='owner_disabled':conn.execute('UPDATE users SET active=0')
    elif reason=='session_revoked':conn.execute('DELETE FROM sessions')
    elif reason=='flag_off':flags['enabled']=False
    else:broker.clock=lambda:float('inf')
    conn.commit();before=path.read_bytes()
    service.check()
    assert not broker._tokens and not service.active and store.value is None
    assert path.read_bytes()==before
