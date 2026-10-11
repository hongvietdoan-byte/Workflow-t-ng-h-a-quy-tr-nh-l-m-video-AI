import sqlite3
import pytest
from core import auth
from tools.lao_dai.broker import SnapshotBroker, make_server
from tools.lao_dai.logic import PetLogic, allowed_url

@pytest.fixture
def broker(tmp_path, monkeypatch):
    p = tmp_path / 'manifest.sqlite'
    sqlite3.connect(p).close()
    monkeypatch.setattr('core.features.on', lambda n: True)
    monkeypatch.setattr(auth, 'identity', lambda c, s: auth.Identity('a@b.c','a','owner') if s == 'owner' else (auth.Identity('m@b.c','m','member') if s == 'member' else None))
    monkeypatch.setattr('core.tickets.admin_snapshot', lambda c: {'schema_version':1,'enabled':True,'available':True,'ticket_counts':{'new':1},'ticket_summaries':[{'id':'abc','state':'new','due_status':'green'}]})
    return SnapshotBroker(p, clock=lambda: 10)

def test_auth_expiry_revocation(broker, monkeypatch):
    for session in (None, 'bad', 'member'):
        with pytest.raises(PermissionError): broker.issue(session)
    token = broker.issue('owner', ttl=2)
    assert broker.snapshot(token)['ticket_counts']['new'] == 1
    with pytest.raises(PermissionError): broker.snapshot('bad')
    monkeypatch.setattr(auth,'identity', lambda c,s: None)
    with pytest.raises(PermissionError): broker.snapshot(token)
    broker.clock = lambda: 12
    with pytest.raises(PermissionError): broker.snapshot(token)

def test_readonly_and_off(broker, monkeypatch):
    before = broker.path.read_bytes()
    token = broker.issue('owner')
    def projection(c):
        with pytest.raises(sqlite3.OperationalError): c.execute('CREATE TABLE forbidden(x)')
        return {'available': True}
    monkeypatch.setattr('core.tickets.admin_snapshot', projection)
    broker.snapshot(token)
    assert broker.path.read_bytes() == before
    monkeypatch.setattr('core.features.on', lambda n: False)
    with pytest.raises(PermissionError): broker.issue('owner')
    with pytest.raises(PermissionError): broker.snapshot(token)
    with pytest.raises(PermissionError): make_server(broker)

def test_no_lan(broker):
    with pytest.raises(ValueError): make_server(broker, host='0.0.0.0')

@pytest.mark.parametrize('value', [None, [], {}, {'schema_version':1,'enabled':True,'available':True,'ticket_counts':{'new':-1},'ticket_summaries':[]}])
def test_bad_snapshot(value):
    assert PetLogic().update(value).state == 'disconnected'

def test_logic_dedupe_and_links():
    p = PetLogic()
    s = {'schema_version':1,'enabled':True,'available':True,'ticket_counts':{'new':2,'closed':3},'ticket_summaries':[{'id':'abc','state':'new','due_status':'yellow'}]}
    v=p.update(s)
    assert v.state == 'tickets' and '2' in v.bubble and v.toasts == ['abc · new · yellow']
    assert p.update(s).toasts == []
    assert p.failure('Lỗi broker').state == 'disconnected'
    assert allowed_url('http://127.0.0.1:8502/?ticket=abc')
    assert allowed_url('http://localhost:8501/?pid=1')
    for url in ['http://evil:8502/', 'http://localhost:8502/?token=secret','http://localhost:8502/?ticket=a&x=y', 'file:///x', 'http://user@localhost:8502/']:
        assert not allowed_url(url)

def test_http_get_only_and_query_denied(broker):
    import threading
    import http.client
    server = make_server(broker)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        token = broker.issue('owner')
        for method, path, headers, status in [
            ('GET','/snapshot',{},401),
            ('GET','/snapshot?token=bad',{},404),
            ('POST','/snapshot',{},405),
            ('DELETE','/snapshot',{},405),
            ('GET','/snapshot',{'Authorization':'Bearer '+token},200),
        ]:
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            c.request(method,path,headers=headers)
            r=c.getresponse()
            assert r.status == status
            r.read(); c.close()
    finally:
        server.shutdown(); server.server_close(); t.join(3)

def test_missing_db_not_created(tmp_path, monkeypatch):
    monkeypatch.setattr('core.features.on',lambda n:True)
    p=tmp_path/'missing.sqlite'
    with pytest.raises(sqlite3.OperationalError): SnapshotBroker(p).issue('owner')
    assert not p.exists()


def test_broker_rejects_cwd_dependent_database(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match='tuyệt đối'):
        SnapshotBroker('manifest.sqlite')


@pytest.mark.parametrize('url', [
    'http://localhost:8502/?ticket=abc&token=',
    'http://localhost:8502/?ticket=abc&ticket=',
    'http://localhost:8501/?pid=1&step=',
])
def test_url_blank_parameters_cannot_bypass_allowlist(url):
    assert not allowed_url(url)

def test_expired_owner_and_member_after_issue(broker, monkeypatch):
    token=broker.issue('owner',ttl=1)
    broker.clock=lambda:11
    with pytest.raises(PermissionError):broker.snapshot(token)
    broker.clock=lambda:10
    token=broker.issue('owner')
    monkeypatch.setattr(auth,'identity',lambda c,s:auth.Identity('a@b.c','a','member'))
    with pytest.raises(PermissionError):broker.snapshot(token)


def test_real_snapshot_auth_and_closed(tmp_path, monkeypatch):
    import time
    from core import db, tickets
    monkeypatch.setattr('core.features.on',lambda n:True)
    p=tmp_path/'real.sqlite'
    c=db.connect(str(p))
    c.execute("INSERT INTO users(email,name,role,perms,active) VALUES ('a@b.c','Admin','owner','[]',1)")
    c.execute("INSERT INTO sessions(token_hash,email,expires_at,created_at) VALUES (?,?,?,0)",(auth._hash('test-session'),'a@b.c',time.time()+300))
    c.commit()
    ticket=tickets.open_or_merge(c,title='test',kind='code',source_actor='tieu_nhi',root_cause='missing_ref')
    c.execute("UPDATE support_tickets SET state='closed' WHERE id=?",(ticket['id'],))
    c.commit()
    tickets.open_or_merge(c,title='open',kind='code',source_actor='tieu_nhi',root_cause='another')
    before=p.read_bytes()
    b=SnapshotBroker(p)
    token=b.issue('test-session')
    snapshot=b.snapshot(token)
    view=PetLogic().update(snapshot)
    assert view.state == 'tickets' and '1' in view.bubble
    assert p.read_bytes()==before
    auth.logout(c,'test-session')
    with pytest.raises(PermissionError):b.snapshot(token)
    c.close()


