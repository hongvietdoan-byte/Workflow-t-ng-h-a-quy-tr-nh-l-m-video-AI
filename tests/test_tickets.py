import sqlite3
from datetime import datetime, timezone, timedelta
import pytest
from core import db
from core.auth import Identity

NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
OWNER = Identity('owner@example.com', 'owner', 'owner')

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr('core.features.on', lambda name: name == 'support_tickets')
    c = db.connect()
    yield c
    c.close()

def ticket(c, **kw):
    from core import tickets
    return tickets.open_or_merge(c, title='LỖI ảnh', kind='code', source_actor='tieu_nhi', root_cause='missing_ref', now=NOW, **kw)

def test_create_merge_due_audit(store):
    from core import tickets
    a = ticket(store, evidence_refs={'diag_ids':[1]})
    b = ticket(store, evidence_refs={'diag_ids':[2]})
    assert a['id'] == b['id']
    assert b['evidence_refs']['diag_ids'] == [1,2]
    assert b['title'] == 'lỗi ảnh'
    assert b['due_at'] == (NOW + timedelta(hours=72)).isoformat()
    assert store.execute('select count(*) from ticket_events').fetchone()[0] == 2
    assert store.execute('select count(*) from audit_log').fetchone()[0] == 2

@pytest.mark.parametrize('state', ['resolved', 'closed'])
def test_merge_reopens_finished_ticket(store, state):
    from core import tickets
    a = ticket(store, project_id=1, impact={'blocked_shots':[10]})
    store.execute('UPDATE support_tickets SET state=?,closed_by=?,closed_at=? WHERE id=?',
                  (state, OWNER.email, NOW.isoformat(), a['id']))
    before = tickets.get(store, a['id'])
    assert tickets.user_projection(before, project_id=1) is None
    assert tickets.due_status(before, NOW + timedelta(days=5)) == 'closed'
    b = ticket(store, project_id=1, evidence_refs={'job_ids':[651]})
    assert b['state'] == 'reopened' and b['revision'] == before['revision'] + 1
    assert b['closed_at'] is None and b['closed_by'] is None
    assert store.execute('SELECT transition FROM ticket_events ORDER BY rowid DESC LIMIT 1').fetchone()[0] == state+'->reopened'

def test_nonblocking_projection_and_absolute_path(store):
    from core import tickets
    assert tickets.user_projection(ticket(store, project_id=1), project_id=1) is None
    with pytest.raises(tickets.TicketError): tickets._safe('/tmp/evidence.png')

def test_paused_ticket_returns_to_previous_state(store):
    from core import tickets
    t = ticket(store)
    for state in ['triaged', 'waiting_admin', 'assigned', 'blocked', 'assigned', 'waiting_info', 'assigned']:
        t = tickets.transition(store,t['id'],state,OWNER,'kiểm',t['state'],expected_revision=t['revision'])
    assert t['state'] == 'assigned'

def test_snapshot_vietnam_day_mixed_utc_formats(store):
    from core import tickets
    at = datetime(2026,10,11,18,tzinfo=timezone.utc)  # 01:00 ngày 12 ở VN
    for stamp in ['2026-10-11 16:59:59','2026-10-11T16:59:59+00:00',
                  '2026-10-11 17:00:00','2026-10-11T17:00:00+00:00']:
        store.execute("INSERT INTO usage_events(kind,provider,model,tier,quantity,unit,at) VALUES('llm','claude','m','x',1,'usd',?)",(stamp,))
    before = store.total_changes
    snap = tickets.admin_snapshot(store,now=at,pricing={'per_million_tokens':{'m':{'x':1000000}}})
    assert snap['available'] and snap['spend_today']['usd'] == 2
    assert store.total_changes == before

def test_standalone_wait_reason_readonly(store, monkeypatch):
    from core import tickets
    import sys
    monkeypatch.delitem(sys.modules, 'core.runner', raising=False)
    store.execute("INSERT INTO projects(id,name,created_at) VALUES(1,'p',?)", (NOW.isoformat(),))
    store.execute('INSERT INTO scenes(id,project_id,idx) VALUES(1,1,1)')
    stamp=(NOW-timedelta(hours=2)).isoformat()
    store.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,created_at,updated_at) VALUES(1,1,1,'video_gen','queued',?,?)",(stamp,stamp))
    store.execute("INSERT INTO motion_prompts(scene_id,motion_prompt,state) VALUES(1,'move','pending')")
    store.commit(); store.execute('PRAGMA query_only=ON')
    before=store.total_changes
    snapshot=tickets.admin_snapshot(store,now=NOW)
    assert snapshot['available']
    assert snapshot['stuck_jobs'][0]['reason']=='Motion prompt chưa được duyệt'
    assert 'core.runner' not in sys.modules and store.total_changes==before

def test_code_lifecycle_and_cas(store):
    from core import tickets
    t = ticket(store)
    with pytest.raises(tickets.TicketError):
        tickets.transition(store,t['id'],'closed',OWNER,'x','new')
    for to in ['triaged','waiting_admin','assigned','investigating','fixing','verifying','waiting_merge']:
        t = tickets.transition(store,t['id'],to,OWNER,'kiểm',t['state'])
    with pytest.raises(tickets.TicketError):
        tickets.transition(store,t['id'],'deployed',OWNER,'kiểm','new')
    with pytest.raises(tickets.TicketError):
        tickets.transition(store,t['id'],'deployed',OWNER,'kiểm',t['state'])
    t = tickets.transition(store,t['id'],'deployed',OWNER,'triển khai',t['state'],technical={'deploy_commit':'abc'},verification={'health':True,'real_case':'case24'})
    for to in ['resolved','closed']:
        t=tickets.transition(store,t['id'],to,OWNER,'x',t['state'])
    assert t['closed_by'] == OWNER.email

@pytest.mark.parametrize('kind',['budget','shared_asset'])
def test_action_branch(store,kind):
    from core import tickets
    t=tickets.open_or_merge(store,title='trần',kind=kind,source_actor='assistant',root_cause='cap',now=NOW)
    for to in ['triaged','waiting_admin','approved','applied','verified','closed']:
        t=tickets.transition(store,t['id'],to,OWNER,'x',t['state'])
    assert t['state']=='closed'

def test_owner_and_reason_required(store):
    from core import tickets
    t=ticket(store)
    for actor,reason in [('admin','x'),(Identity('m','m','member'),'x'),(OWNER,'')]:
        with pytest.raises(tickets.TicketError): tickets.transition(store,t['id'],'triaged',actor,reason,'new')

def test_extend_and_clock(store):
    from core import tickets
    t=ticket(store)
    assert tickets.due_status(t,NOW+timedelta(hours=48)) == 'yellow'
    assert tickets.due_status(t,NOW+timedelta(hours=72)) == 'red'
    old=t['due_at']
    t=tickets.extend_due(store,t['id'],NOW+timedelta(hours=96),OWNER,'chờ bằng chứng',expected_revision=t['revision'],now=NOW)
    assert t['original_due_at']==old
    assert t['due_at'] != old
    assert tickets.due_status(t,NOW+timedelta(hours=73)) == 'yellow'

def test_append_only(store):
    ticket(store)
    for sql in ['delete from ticket_events','update ticket_events set reason="x"']:
        with pytest.raises(sqlite3.IntegrityError): store.execute(sql)

def test_off_no_mutation(store,monkeypatch):
    from core import tickets
    monkeypatch.setattr('core.features.on',lambda name:False)
    before=store.total_changes
    assert ticket(store) is None
    assert tickets.admin_snapshot(store)['enabled'] is False
    assert store.total_changes==before

def test_old_database(tmp_path):
    p=tmp_path/'old.sqlite'
    c=sqlite3.connect(p); c.execute('create table legacy (id integer)');c.commit();c.close()
    c=db.connect(str(p))
    assert c.execute('select count(*) from support_tickets').fetchone()[0]==0
    assert c.execute('select count(*) from legacy').fetchone()[0]==0
    c.close()

def test_user_projection_scope(store):
    from core import tickets
    t=ticket(store,project_id=1,impact={'blocked_projects':[1,2],'blocked_shots':[3]},technical={'branch':'secret'})
    assert tickets.user_projection(t,project_id=2) is None
    u=tickets.user_projection(t,project_id=1)
    assert set(u)=={'error','message'}
    assert 'đã báo admin' in u['message']
    assert 'secret' not in str(u)

def test_snapshot_read_only_and_no_false_done(store):
    from core import tickets
    ticket(store)
    store.execute("insert into projects(id,name,created_at,autopilot_state) values(1,'p',?,'done')",(NOW.isoformat(),)); store.commit()
    before=store.total_changes
    s=tickets.admin_snapshot(store,now=NOW)
    assert s['ticket_counts']=={'new':1}
    assert s['gen_done_projects']==[]
    assert 'pending' in s['spend_today'] and 'unknown' in s['spend_today']
    assert store.total_changes==before

def test_rejected_reopened_and_revision_guard(store):
    from core import tickets
    t=tickets.open_or_merge(store,title='trần',kind='budget',source_actor='assistant',root_cause='cap')
    for to in ['triaged','waiting_admin','rejected','closed','reopened','triaged','waiting_info','triaged']:
        t=tickets.transition(store,t['id'],to,OWNER,'lý do',t['state'])
    with pytest.raises(tickets.TicketError):
        tickets.transition(store,t['id'],'waiting_admin',OWNER,'x',t['state'],expected_revision=1)

@pytest.mark.parametrize('payload',[{'api_key':'private'},{'file':'C:\\private\\secret'}, {'raw':'data:image/png;base64,abc'}])
def test_reject_unfiltered_evidence(store,payload):
    from core import tickets
    with pytest.raises(tickets.TicketError): ticket(store,technical=payload)
    assert store.execute('select count(*) from support_tickets').fetchone()[0]==0

def test_snapshot_gen_target_stale_and_pending_readonly(store,tmp_path,monkeypatch):
    from core import tickets
    store.execute("insert into projects(id,name,created_at) values(1,'p',?)",(NOW.isoformat(),))
    store.execute("insert into scenes(id,project_id,idx) values(1,1,1)")
    stamp=NOW.isoformat()
    store.execute("insert into jobs(id,project_id,scene_id,type,state,result_path,created_at,updated_at) values(1,1,1,'image_gen','approved','image.png',?,?)",(stamp,stamp))
    import json
    (tmp_path/'image.png').write_bytes(b'fixture image')
    from core.sent_package import sha256_of
    package=json.dumps({'prompt':'move','refs':[{'param':'image_path','path':'image.png','sha256':sha256_of(str(tmp_path/'image.png'))}]})
    store.execute("insert into jobs(id,project_id,scene_id,type,state,result_path,sent_package,created_at,updated_at) values(2,1,1,'video_gen','pending_review','video.mp4',?,?,?)",(package,stamp,stamp))
    store.execute("insert into motion_prompts(scene_id,motion_prompt,image_job_id) values(1,'changed',1)")
    store.execute('create table llm_holds(id integer primary key,at text,project_id integer,stage text,usd real)')
    store.execute("insert into llm_holds values(1,?,1,'test',0.15)",(stamp,));store.commit()
    assert tickets.admin_snapshot(store,now=NOW)['gen_done_projects']==[]
    store.execute("update motion_prompts set motion_prompt='move'");store.commit()
    store.execute('pragma query_only=on')
    snap=tickets.admin_snapshot(store,now=NOW,data_dir=str(tmp_path))
    assert snap['available'] is True
    assert snap['gen_done_projects']==[1]
    assert snap['spend_today']['pending']==0.15
    assert store.execute('select count(*) from usage_events').fetchone()[0]==0

    disk=tmp_path/'manifest.sqlite'
    with sqlite3.connect(disk) as saved:
        store.backup(saved)
    from tools.lao_dai.broker import SnapshotBroker
    monkeypatch.setattr('core.features.on',lambda name:True)
    monkeypatch.setattr('core.auth.identity',lambda c,s:OWNER)
    broker=SnapshotBroker(disk,data_dir=tmp_path)
    assert broker.snapshot(broker.issue('test-owner'))['gen_done_projects']==[1]

    (tmp_path/'image.png').write_bytes(b'changed image')
    assert tickets.admin_snapshot(store,now=NOW,data_dir=str(tmp_path))['gen_done_projects']==[]

@pytest.mark.parametrize('operation', ['open', 'transition', 'extend'])
def test_caller_transaction_not_committed(store, operation):
    from core import tickets
    t=ticket(store)
    store.execute('create table caller_marker (id integer)');store.commit()
    store.execute('insert into caller_marker values (1)')
    if operation == 'open':
        ticket(store, evidence_refs={'diag_ids':[99]})
    elif operation == 'transition':
        tickets.transition(store,t['id'],'triaged',OWNER,'x','new')
    else:
        tickets.extend_due(store,t['id'],NOW+timedelta(hours=96),OWNER,'x',expected_revision=1,now=NOW)
    assert store.in_transaction
    store.rollback()
    assert store.execute('select count(*) from caller_marker').fetchone()[0]==0
    assert tickets.get(store,t['id'])['revision']==1

def test_audit_failure_rolls_back_only_ticket_savepoint(store):
    from core import tickets
    store.execute('create table caller_marker (id integer)')
    store.execute("create trigger fail_audit before insert on audit_log begin select raise(abort,'fixture'); end")
    store.commit()
    store.execute('insert into caller_marker values (1)')
    with pytest.raises(sqlite3.IntegrityError): ticket(store)
    assert store.in_transaction
    assert store.execute('select count(*) from caller_marker').fetchone()[0]==1
    assert store.execute('select count(*) from support_tickets').fetchone()[0]==0
    assert store.execute('select count(*) from ticket_events').fetchone()[0]==0
    store.rollback()

@pytest.mark.parametrize('path',['C:/private/file.png','//server/share/file.png'])
def test_reject_slash_machine_paths(store,path):
    from core import tickets
    with pytest.raises(tickets.TicketError): ticket(store,evidence_refs={'artifacts':[path]})
    assert ticket(store,evidence_refs={'artifacts':['relative/image.png','a'*64]})

@pytest.mark.parametrize('problem',['missing','permission','package_list','refs_null','refs_object'])
def test_snapshot_bad_evidence_warns_readonly(store,tmp_path,monkeypatch,problem):
    from core import tickets
    import json
    store.execute("insert into projects(id,name,created_at) values(1,'p',?)",(NOW.isoformat(),))
    store.execute('insert into scenes(id,project_id,idx) values(1,1,1)')
    store.execute("insert into jobs(id,project_id,scene_id,type,state,result_path,created_at,updated_at) values(1,1,1,'image_gen','approved','image.png',?,?)",(NOW.isoformat(),NOW.isoformat()))
    package={'prompt':'move','refs':[{'param':'image_path','sha256':'a'*64}]}
    if problem=='package_list': package=[]
    if problem=='refs_null': package['refs']=[None]
    if problem=='refs_object': package['refs']={'param':'image_path'}
    store.execute("insert into jobs(id,project_id,scene_id,type,state,result_path,sent_package,created_at,updated_at) values(2,1,1,'video_gen','succeeded','video.mp4',?,?,?)",(json.dumps(package),NOW.isoformat(),NOW.isoformat()))
    store.execute("insert into motion_prompts(scene_id,motion_prompt,image_job_id) values(1,'move',1)")
    if problem!='missing': (tmp_path/'image.png').write_bytes(b'fixture')
    if problem=='permission':
        def denied(path): raise PermissionError('fixture')
        monkeypatch.setattr('core.sent_package.sha256_of',denied)
    store.commit();store.execute('pragma query_only=on')
    before=store.total_changes
    snap=tickets.admin_snapshot(store,now=NOW,data_dir=str(tmp_path))
    assert snap['available'] is True
    assert snap['gen_done_projects']==[]
    assert any('Dự án 1' in warning for warning in snap['warnings'])
    assert store.total_changes==before
