import copy, importlib, os, sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import pytest
with patch.object(os, 'environ', {}):
    from tests.test_stage_registry_schema import bundle

@pytest.fixture(autouse=True)
def safe_env():
    with patch.object(os, 'environ', {}):
        mod=importlib.import_module('core.stage_registry_store')
        with patch.object(mod.features,'on',lambda name: name=='stage_registry_a'): yield

@pytest.fixture
def setup(tmp_path):
    conn=sqlite3.connect(tmp_path/'fake.sqlite'); conn.row_factory=sqlite3.Row
    for sql in ['CREATE TABLE projects(id INTEGER PRIMARY KEY,name TEXT,created_by TEXT)', 'CREATE TABLE project_watchers(project_id INTEGER,email TEXT,level TEXT)', 'CREATE TABLE scenes(id INTEGER PRIMARY KEY,project_id INTEGER)', 'CREATE TABLE assets(id INTEGER PRIMARY KEY,project_id INTEGER)', 'CREATE TABLE project_assets(project_id INTEGER,asset_id INTEGER)']:
        conn.execute(sql)
    conn.executemany('INSERT INTO projects VALUES(?,?,?)', [(123,'fake','creator'),(124,'fake2','other')])
    conn.execute('INSERT INTO scenes VALUES(456,123)')
    conn.executemany('INSERT INTO assets VALUES(?,NULL)',[(1234,),(1235,)])
    conn.executemany('INSERT INTO project_assets VALUES(123,?)',[(1234,),(1235,)])
    conn.executemany('INSERT INTO project_watchers VALUES(123,?,?)',[('viewer','view'),('editor','edit')]); conn.commit()
    mod=importlib.import_module('core.stage_registry_store')
    p=SimpleNamespace(conn=conn,user={'email':'creator','role':'member'})
    store=mod.StageRegistryStore(p,opt_in=True); store.bootstrap(123)
    yield mod,store,p
    conn.close()

def rows(b=None):
    b=b or bundle(); return [(kind,r) for kind in ('stages','segments','states','cameras','shots') for r in b[kind]]
def create(s):
    rs=rows(); return s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='initial',reason='fake')

def test_off_no_ddl(tmp_path):
    mod=importlib.import_module('core.stage_registry_store'); c=sqlite3.connect(tmp_path/'off.sqlite')
    s=mod.StageRegistryStore(SimpleNamespace(conn=c,user=None))
    with pytest.raises(mod.RegistryNotReady): s.bootstrap(123)
    assert not c.execute("SELECT name FROM sqlite_master").fetchall()

def test_create_snapshot_retry(setup):
    m,s,p=setup; result=create(s); assert create(s)==result
    assert s.snapshot(123,'shot',1)['end']['objects']['actor']['pose']=='lying'
    assert len(s.history(123,'states','end'))==1
    assert len(s.outbox(123))==1

def test_cas_history_and_old_pin(setup):
    m,s,p=setup; create(s); r=s.head(123,'states','end'); r['patches'][0]['pose']='crouching'
    s.apply(123,[('states',r)],{('states','end'):1},request_id='edit',reason='fake')
    assert s.head(123,'states','end')['revision']==2
    assert s.snapshot(123,'shot',1)['end']['objects']['actor']['pose']=='lying'
    with pytest.raises(m.RegistryConflict): s.apply(123,[('states',r)],{('states','end'):1},request_id='stale',reason='fake')

@pytest.mark.parametrize('identity,read,write',[('viewer',True,False),('editor',True,True),('other',False,False),('creator',True,True)])
def test_real_acl(setup,identity,read,write):
    m,s,p=setup; create(s); p.user={'email':identity,'role':'member'}
    if read: assert s.history(123,'states','end')
    else:
        with pytest.raises(PermissionError): s.history(123,'states','end')
    r=bundle()['states'][1]
    if write: s.apply(123,[('states',r)],{('states','end'):1},request_id='acl',reason='fake')
    else:
        with pytest.raises(PermissionError): s.apply(123,[('states',r)],{('states','end'):1},request_id='acl',reason='fake')

@pytest.mark.parametrize('step',['revision','head','audit','outbox','request'])
def test_fault_atomic(setup,step):
    m,s,p=setup; create(s); r=s.head(123,'states','end')
    s._point=lambda point: (_ for _ in ()).throw(RuntimeError('fake')) if point==step else None
    with pytest.raises(RuntimeError): s.apply(123,[('states',r)],{('states','end'):1},request_id='fault',reason='fake')
    assert s.head(123,'states','end')['revision']==1
    assert len(s.history(123,'states','end'))==1
    assert s.request(123,'apply','fault') is None

def test_nested_reject_preserves_pending(setup):
    m,s,p=setup; p.conn.execute('UPDATE projects SET name=? WHERE id=123',('pending',))
    with pytest.raises(m.RegistryTransactionError): create(s)
    assert p.conn.in_transaction
    p.conn.rollback(); assert p.conn.execute('SELECT name FROM projects WHERE id=123').fetchone()[0]=='fake'

def test_semantic_and_fk_rollback(setup):
    m,s,p=setup; b=bundle(); b['states'][0]['patches'][0]['op']='update'
    with pytest.raises(m.RegistryStoreError): s.apply(123,rows(b),{(k,r['id']):None for k,r in rows(b)},request_id='bad',reason='fake')
    assert s.head(123,'stages','stage') is None
    p.conn.execute('DELETE FROM project_assets'); p.conn.commit()
    with pytest.raises(m.RegistryStoreError): create(s)

def test_locks_unlock_undo(setup):
    m,s,p=setup; b=bundle(); b['states'][1]['_user_locked']={'patches[0].pose':{'author_id':'fake','created_at_utc':'2026-10-14T00:00:00Z','reason':'fake'}}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='locks',reason='fake')
    r=s.head(123,'states','end'); r['_user_locked']={}; r['patches'][0]['pose']='standing'
    with pytest.raises(m.RegistryLocked): s.apply(123,[('states',r)],{('states','end'):1},request_id='bypass',reason='fake')
    s.unlock(123,'states','end',['patches[0].pose'],1,request_id='unlock',reason='manual')
    s.undo(123,'states','end',1,2,request_id='undo',reason='manual')
    assert s.head(123,'states','end')['revision']==3
    assert s.head(123,'states','end')['_user_locked']=={}

def test_request_actor_collision_revocation(setup):
    m,s,p=setup; create(s); p.user={'email':'editor','role':'member'}
    with pytest.raises(m.RegistryConflict): create(s)
    p.user={'email':'other','role':'member'}
    with pytest.raises(PermissionError): create(s)

def test_append_only_and_outbox(setup):
    m,s,p=setup; create(s)
    for table in ['stage_registry_revisions','stage_registry_audit']:
        with pytest.raises(sqlite3.IntegrityError): p.conn.execute('DELETE FROM '+table)
        p.conn.rollback()
    oid=s.outbox(123)[0]['id']; s.ack(123,oid); s.ack(123,oid)
    assert s.outbox(123)==[]

def test_two_connections_one_cas_winner(setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    m,s,p=setup; create(s)
    path=p.conn.execute('PRAGMA database_list').fetchone()[2]; barrier=Barrier(2)
    def writer(n):
        with patch.object(os,'environ',{}):
            c=sqlite3.connect(path,timeout=5); c.row_factory=sqlite3.Row
            try:
                other=m.StageRegistryStore(SimpleNamespace(conn=c,user={'email':'creator','role':'member'}),opt_in=True)
                r=other.head(123,'states','end'); r['patches'][0]['pose']='fake'+str(n); barrier.wait()
                try: other.apply(123,[('states',r)],{('states','end'):1},request_id='race'+str(n),reason='fake'); return 'ok'
                except m.RegistryConflict: return 'conflict'
            finally: c.close()
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(writer,[1,2]))
    assert sorted(results)==['conflict','ok']
    assert len(s.history(123,'states','end'))==2

def test_multi_head_cas_failure_no_partial(setup):
    m,s,p=setup; create(s); a=s.head(123,'states','end'); c=s.head(123,'cameras','camera')
    with pytest.raises(m.RegistryConflict): s.apply(123,[('states',a),('cameras',c)],{('states','end'):1,('cameras','camera'):9},request_id='multi',reason='fake')
    assert s.head(123,'states','end')['revision']==1
    assert len(s.outbox(123))==1

def test_owner_system_and_cross_scope(setup):
    m,s,p=setup; create(s); p.user={'email':'owner','role':'owner'}
    assert s.history(123,'states','end')
    assert s.history(124,'states','end')==[]
    assert s.request(124,'apply','initial') is None
    event=s.outbox(123)[0]['id']
    with pytest.raises(m.RegistryStoreError): s.ack(124,event)
    with pytest.raises(m.RegistryStoreError): s.snapshot(124,'shot',1)
    p.user=None; assert s.head(123,'states','end')

def test_missing_schema_and_corrupt_payload(setup):
    m,s,p=setup; create(s)
    p.conn.execute('DROP TRIGGER stage_registry_revisions_update')
    p.conn.execute("UPDATE stage_registry_revisions SET payload='invalid'"); p.conn.commit()
    with pytest.raises(m.RegistryStoreError): s.head(123,'states','end')
    p.conn.execute('UPDATE stage_registry_schema SET version=99'); p.conn.commit()
    with pytest.raises(m.RegistryNotReady): s.outbox(123)

def test_missing_tables_no_auto_ddl(setup):
    m,s,p=setup; p.conn.execute('DROP TABLE stage_registry_outbox'); p.conn.commit()
    with pytest.raises(m.RegistryNotReady): s.history(123,'states','end')
    assert p.conn.execute("SELECT name FROM sqlite_master WHERE name='stage_registry_outbox'").fetchone() is None

def test_unlock_retry_and_undo_retry(setup):
    m,s,p=setup; b=bundle(); b['states'][1]['_user_locked']={'patches':{'author_id':'fake','created_at_utc':'2026-10-14T00:00:00Z','reason':'fake'}}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='locks',reason='fake')
    result=s.unlock(123,'states','end',['patches'],1,request_id='unlock',reason='manual')
    assert s.unlock(123,'states','end',['patches'],1,request_id='unlock',reason='manual')==result
    result=s.undo(123,'states','end',1,2,request_id='undo',reason='manual')
    assert s.undo(123,'states','end',1,2,request_id='undo',reason='manual')==result

@pytest.mark.parametrize('bad',[0,-1,True,2**63])
def test_invalid_project_id(setup,bad):
    m,s,p=setup
    with pytest.raises(m.RegistryStoreError): s.history(bad,'states','end')


def test_disable_between_constructor_and_call(setup):
    m,s,p=setup
    with patch.object(m.features,'on',lambda name:False):
        with pytest.raises(m.RegistryNotReady): create(s)
    assert s.head(123,'stages','stage') is None

def test_indexed_lock_schema_regression():
    with patch.object(os,'environ',{}):
        from core.stage_registry_schema import validate_bundle
        b=bundle(); b['states'][1]['_user_locked']={'patches[0].pose':{'author_id':'fake','created_at_utc':'2026-10-14T00:00:00Z','reason':'fake'}}
        assert not validate_bundle(b)['errors']


@pytest.mark.parametrize('bad',[1,'true','false',[],{}])
def test_review_optin_exact_true(setup,bad):
    m,s,p=setup; other=m.StageRegistryStore(p,opt_in=bad)
    with pytest.raises(m.RegistryNotReady): other.history(123,'states','end')


def test_review_lock_author_is_server_and_path_exists(setup):
    m,s,p=setup; b=bundle()
    b['states'][1]['_user_locked']={'patches[0].pose':dict(author_id='fake',created_at_utc='2026-10-14T00:00:00Z',reason='manual')}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='lock-author',reason='fake')
    assert s.head(123,'states','end')['_user_locked']['patches[0].pose']['author_id']=='creator'


def test_review_invalid_lock_target_rejected(setup):
    m,s,p=setup; b=bundle()
    b['states'][1]['_user_locked']={'patches[999].pose':dict(author_id='fake',created_at_utc='2026-10-14T00:00:00Z',reason='manual')}
    with pytest.raises(m.RegistryStoreError): s.apply(123,rows(b),{(k,r['id']):None for k,r in rows(b)},request_id='bad-lock',reason='fake')


def test_review_append_outside_indexed_lock(setup):
    m,s,p=setup; b=bundle()
    b['states'][1]['_user_locked']={'patches[0].pose':dict(author_id='fake',created_at_utc='2026-10-14T00:00:00Z',reason='manual')}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='lock-index',reason='fake')
    r=s.head(123,'states','end'); r['patches'].append(dict(object_id='well',op='update',pose='fake'))
    s.apply(123,[('states',r)],{('states','end'):1},request_id='append',reason='fake')
    assert s.head(123,'states','end')['revision']==2


def test_review_unlock_retry_after_later_edit(setup):
    m,s,p=setup; b=bundle(); b['states'][1]['_user_locked']={'patches':dict(author_id='fake',created_at_utc='2026-10-14T00:00:00Z',reason='manual')}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='lock-retry',reason='fake')
    saved=s.unlock(123,'states','end',['patches'],1,request_id='unlock-retry',reason='manual')
    r=s.head(123,'states','end'); r['patches'][0]['pose']='other'
    s.apply(123,[('states',r)],{('states','end'):2},request_id='later-edit',reason='fake')
    assert s.unlock(123,'states','end',['patches'],1,request_id='unlock-retry',reason='manual')==saved


def test_review_provenance_not_silently_dropped(setup):
    m,s,p=setup; create(s); r=s.head(123,'states','end'); r['provenance']={'raw':{'note':'fake'}}
    with pytest.raises(m.RegistryStoreError): s.apply(123,[('states',r)],{('states','end'):1},request_id='provenance',reason='fake')


@pytest.mark.parametrize('case',['trigger_missing','trigger_replaced','head_missing','head_old'])
def test_review_schema_and_head_corruption(setup,case):
    m,s,p=setup; create(s)
    if case=='trigger_missing': p.conn.execute('DROP TRIGGER stage_registry_audit_delete')
    if case=='trigger_replaced':
        p.conn.execute('DROP TRIGGER stage_registry_audit_delete'); p.conn.execute('CREATE TRIGGER stage_registry_audit_delete BEFORE DELETE ON stage_registry_audit BEGIN SELECT 1; END')
    if case=='head_missing': p.conn.execute("DELETE FROM stage_registry_heads WHERE kind='states' AND id='end'")
    if case=='head_old':
        r=s.head(123,'states','end'); s.apply(123,[('states',r)],{('states','end'):1},request_id='new-head',reason='fake')
        p.conn.execute("UPDATE stage_registry_heads SET revision=1 WHERE kind='states' AND id='end'")
    p.conn.commit()
    with pytest.raises(m.RegistryStoreError): s.history(123,'states','end')


@pytest.mark.parametrize('table,read',[('stage_registry_requests',lambda s:s.request(123,'apply','initial')),('stage_registry_audit',lambda s:s.audit(123)),('stage_registry_outbox',lambda s:s.outbox(123))])
def test_review_corrupt_metadata_reads(setup,table,read):
    m,s,p=setup; create(s)
    if table!='stage_registry_outbox': p.conn.execute('DROP TRIGGER '+table+'_update')
    field='payload' if table=='stage_registry_outbox' else 'result'
    p.conn.execute('UPDATE '+table+' SET '+field+'=?', ('{}',))
    if table!='stage_registry_outbox': p.conn.execute(m._trigger_sql(table,'UPDATE'))
    p.conn.commit()
    with pytest.raises(m.RegistryStoreError): read(s)


def test_review_history_bound_before_load(setup):
    m,s,p=setup; create(s)
    with patch.object(m,'MAX_HISTORY_ROWS',1,create=True), patch.object(m,'_load') as loaded:
        with pytest.raises(m.RegistryStoreError): s.history(123,'states','end')
        loaded.assert_not_called()


def test_review_old_snapshot_survives_asset_detach(setup):
    m,s,p=setup; create(s); p.conn.execute('DELETE FROM project_assets'); p.conn.commit()
    assert s.snapshot(123,'shot',1)['end']['objects']['actor']['pose']=='lying'


def test_review_duplicate_unlock_sanitized(setup):
    m,s,p=setup; b=bundle(); b['states'][1]['_user_locked']={'patches':dict(author_id='fake',created_at_utc='2026-10-14T00:00:00Z',reason='manual')}
    rs=rows(b); s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='dup-lock',reason='fake')
    with pytest.raises(m.RegistryStoreError): s.unlock(123,'states','end',['patches','patches'],1,request_id='dup-unlock',reason='fake')


@pytest.mark.parametrize('raw',['{"a":1,"a":2}','{"a":NaN}'])
def test_review_stored_json_strict(setup,raw):
    m,s,p=setup
    with pytest.raises(m.RegistryStoreError): m._load(raw)



def test_review_inactive_source_does_not_block_new_stage(setup):
    m,s,p=setup; create(s)
    p.conn.execute('INSERT INTO assets VALUES(1236,NULL)'); p.conn.execute('INSERT INTO project_assets VALUES(123,1236)'); p.conn.commit()
    r=s.head(123,'stages','stage'); r['source_asset_id']=1236
    s.apply(123,[('stages',r)],{('stages','stage'):1},request_id='new-source',reason='fake')
    p.conn.execute('DELETE FROM project_assets WHERE asset_id=1234'); p.conn.commit()
    r=s.head(123,'stages','stage'); r['geometry']['source']='fake-new'
    s.apply(123,[('stages',r)],{('stages','stage'):2},request_id='new-source-again',reason='fake')
    assert s.head(123,'stages','stage')['revision']==3
    assert s.snapshot(123,'shot',1)['end']['objects']['actor']['pose']=='lying'


def test_review_new_live_source_must_be_attached(setup):
    m,s,p=setup; create(s); p.conn.execute('DELETE FROM project_assets WHERE asset_id=1234'); p.conn.commit()
    r=s.head(123,'states','end'); r['beat']='fake-new'
    with pytest.raises(m.RegistryStoreError): s.apply(123,[('states',r)],{('states','end'):1},request_id='live-unbound',reason='fake')
    assert s.head(123,'states','end')['revision']==1


def test_review_borrowed_read_preserves_pending(setup):
    m,s,p=setup; create(s); p.conn.execute("UPDATE projects SET name='pending' WHERE id=123")
    assert s.head(123,'states','end')
    assert p.conn.in_transaction
    p.conn.rollback(); assert p.conn.execute('SELECT name FROM projects WHERE id=123').fetchone()[0]=='fake'


def test_review_proposed_history_limit_no_unreadable_commit(setup):
    m,s,p=setup; create(s); r=s.head(123,'states','end')
    count=p.conn.execute('SELECT COUNT(*) FROM stage_registry_revisions').fetchone()[0]
    with patch.object(m,'MAX_HISTORY_ROWS',count):
        with pytest.raises(m.RegistryStoreError): s.apply(123,[('states',r)],{('states','end'):1},request_id='over-limit',reason='fake')
    assert s.head(123,'states','end')['revision']==1


def test_review_cycle_alias_and_unicode_rejected(setup):
    m,s,p=setup
    for mode in ('cycle','alias','unicode'):
        b=bundle()
        if mode=='cycle': b['stages'][0]['source']['cycle']=b['stages'][0]['source']
        if mode=='alias': b['stages'][0]['source']=b['stages'][0]['provenance']
        if mode=='unicode': b['stages'][0]['source']['text']=chr(0xd800)
        rs=rows(b)
        with pytest.raises(m.RegistryStoreError): s.apply(123,rs,{(k,r['id']):None for k,r in rs},request_id='invalid-'+mode,reason='fake')
    assert s.head(123,'stages','stage') is None


def test_review_experimental_does_not_enable_registry(setup):
    m,s,p=setup
    with patch.object(os,'environ',{}), patch.object(m.features,'settings',return_value={'preset':'experimental','flags':{},'modes':{}}):
        assert m.features.state('stage_registry_a')=='off'



def test_review_unknown_trigger_rejected_before_write(setup):
    m,s,p=setup
    p.conn.execute("CREATE TRIGGER unexpected AFTER INSERT ON stage_registry_outbox BEGIN UPDATE projects SET name='bad' WHERE id=123; END"); p.conn.commit()
    with pytest.raises(m.RegistryNotReady): create(s)
    assert p.conn.execute('SELECT name FROM projects WHERE id=123').fetchone()[0]=='fake'


def test_review_future_callback_attribute_has_no_production_effect(setup):
    m,s,p=setup; s.fault=lambda name: (_ for _ in ()).throw(RuntimeError('unused callback'))
    create(s)
    assert s.head(123,'states','end')['revision']==1



def test_review_pending_look_mapping_fails_closed(setup):
    m,s,p=setup; b=bundle(); b['stages'][0]['objects'][0].update(look_id=1234,look_revision=1)
    with pytest.raises(m.RegistryStoreError): s.apply(123,rows(b),{(k,r['id']):None for k,r in rows(b)},request_id='pending-look',reason='fake')
    assert s.head(123,'stages','stage') is None


@pytest.mark.parametrize('table,column',[('stage_registry_requests','result'),('stage_registry_audit','result'),('stage_registry_outbox','payload')])
def test_review_projected_metadata_bytes_before_commit(setup,table,column):
    m,s,p=setup; create(s)
    limit=40000
    existing=p.conn.execute('SELECT SUM(length(CAST('+column+' AS BLOB))) FROM '+table+' WHERE project_id=123').fetchone()[0]
    raw=m._dump(s.request(123,'apply','initial'))
    padded=raw+' '*(limit-1-existing-len(raw.encode('utf-8')))
    if table=='stage_registry_requests':
        p.conn.execute('INSERT INTO stage_registry_requests VALUES(?,?,?,?,?,?)',(123,'apply','padding','creator','0'*64,padded))
    elif table=='stage_registry_audit':
        p.conn.execute('INSERT INTO stage_registry_audit(project_id,operation,actor,created_at_utc,reason,result) VALUES(?,?,?,?,?,?)',(123,'apply','creator','2026-10-14T00:00:00Z','fake',padded))
    else:
        p.conn.execute('INSERT INTO stage_registry_outbox(project_id,event,payload) VALUES(?,?,?)',(123,'registry_invalidated',padded))
    p.conn.commit(); r=s.head(123,'states','end')
    with patch.object(m,'MAX_HISTORY_BYTES',limit):
        with pytest.raises(m.RegistryStoreError): s.apply(123,[('states',r)],{('states','end'):1},request_id='over-meta',reason='fake')
    assert s.head(123,'states','end')['revision']==1
    assert s.request(123,'apply','over-meta') is None
