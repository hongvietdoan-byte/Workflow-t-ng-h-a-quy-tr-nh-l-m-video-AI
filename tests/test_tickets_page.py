import sqlite3
from datetime import timedelta
import pytest
from streamlit.testing.v1 import AppTest
from core import db, tickets
from core.auth import Identity

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr('core.features.on', lambda n: True)
    c=db.connect(); yield c; c.close()

def make(c, root='a', kind='code', **kw):
    return tickets.open_or_merge(c,title=root,kind=kind,source_actor='tieu_nhi',root_cause=root,**kw)

def test_from_fix_merge(store):
    a=tickets.from_fix(store,1,2,3,'thiếu mẫu','thêm ảnh kho',{'sent_job_ids':[3]})
    b=tickets.from_fix(store,1,2,4,'thiếu mẫu','thêm ảnh kho',{'sent_job_ids':[4]})
    assert a['id']==b['id'] and b['kind']=='code'
    assert b['workaround']['text']=='đã gỡ tạm bằng: thêm ảnh kho'
    assert b['evidence_refs']['sent_job_ids']==[3,4]
    assert b['state']=='new'

def test_human_details_money_vietnam_time_and_link(store):
    from devsys import tickets_page as ui
    t=make(store,impact={'blocked_shots':[10],'money_usd':0.12},
           cause={'confidence':'guess','summary':'thiếu mẫu','evidence_refs':{'job_ids':[651]}},
           now='2026-10-08T08:23:13+00:00')
    assert ui.impact_text(t)=='chặn shot 10; tiền 0.12 USD'
    assert 'đoán — thiếu mẫu; bằng chứng: job: 651'==ui.cause_text(t)
    assert ui.due_text(t,'2026-10-11T09:23:13+00:00')=='11/10 15:23 (giờ VN) · quá 1.0 h'
    query={'ticket':t['id']}; session={}
    assert not ui.consume_ticket_link(query,session,False) and query
    assert ui.consume_ticket_link(query,session,True) and not query
    assert session['ticket_focus']==t['id']
    assert not ui.consume_ticket_link(query,session,True)

def test_human_details_render_evidence_as_literal_text(store,tmp_path,monkeypatch):
    from devsys import tickets_page as ui
    refs={'artifacts':['![bằng chứng](relative/image.png)','test_case_*_01']}
    t=make(store,impact={'blocked_shots':['shot_*_10'],'money_usd':0.12},
           cause={'confidence':'guess','summary':'**thiếu mẫu**','evidence_refs':refs},
           evidence_refs=refs)
    path=tmp_path/'literal.sqlite'
    with sqlite3.connect(path) as saved: store.backup(saved)
    monkeypatch.setenv('PIPELINE_DB',str(path))
    at=AppTest.from_string('from devsys.tickets_page import render\nrender()').run()
    assert not at.exception
    expected=['Ảnh hưởng: '+ui.impact_text(t),'Nguyên nhân: '+ui.cause_text(t),
              'Bằng chứng: '+ui.evidence_text(refs)]
    assert all(line in [element.value for element in at.text] for line in expected)
    assert not any('![bằng chứng]' in element.value for element in at.markdown)

def test_queue_merge_and_readonly(store,tmp_path,monkeypatch):
    from devsys import tickets_page as ui
    now=tickets._time()
    other=make(store,'other')
    near=make(store,'near',now=now-timedelta(hours=60))
    over=make(store,'over',now=now-timedelta(hours=80))
    blocked=make(store,'blocked',impact={'blocked_shots':[2]})
    make(store,'other')
    q=ui.queue(store,now=now)
    assert [t['title'] for t in q]==['blocked','over','near','other']
    assert q[-1]['occurrences']==2
    path=tmp_path/'db.sqlite'; disk=sqlite3.connect(path); store.backup(disk);disk.close()
    monkeypatch.setenv('PIPELINE_DB',str(path))
    at=AppTest.from_string('from devsys.tickets_page import render\nrender()').run()
    assert not at.exception
    assert all(b.disabled for b in at.button if b.label in ui.DECISIONS)
    assert 'CHỈ ĐỌC' in at.warning[0].value
    at.selectbox(key='ticket_kind').select('budget').run()
    at.query_params['ticket']=blocked['id']; at.run()
    assert any('blocked' in e.label for e in at.expander)
    with ui.read_connection() as ro:
        with pytest.raises(sqlite3.OperationalError): ro.execute('delete from support_tickets')

def test_adapter_next_bulk_guard(store):
    from devsys import tickets_page as ui
    owner=Identity('owner@example.com','owner','owner')
    a=make(store,'a'); b=make(store,'b')
    assert ui.decide(store,a['id'],'Duyệt',owner,'đã kiểm',a['revision'])['state']=='triaged'
    assert ui.next_ticket(ui.queue(store),a['id'])==b['id']
    paid=make(store,'paid',kind='budget')
    with pytest.raises(tickets.TicketError): ui.bulk_preview(store,[a['id'],paid['id']])
    money=make(store,'money',impact={'money_usd':1})
    with pytest.raises(tickets.TicketError): ui.bulk_preview(store,[money['id']])
    with pytest.raises(tickets.TicketError): ui.decide(store,b['id'],'Duyệt','owner','x',b['revision'])

def test_from_fix_updates_workaround_atomically(store):
    a=make(store,'missing',project_id=1)
    store.execute('BEGIN')
    b=tickets.from_fix(store,1,None,3,'missing','cách một',{'sent_job_ids':[3]})
    c=tickets.from_fix(store,1,None,4,'missing','cách hai',{'sent_job_ids':[4]})
    assert c['workaround']['text']=='đã gỡ tạm bằng: cách hai'
    assert [w['text'] for w in c['workaround']['history']]==['đã gỡ tạm bằng: cách một','đã gỡ tạm bằng: cách hai']
    assert c['state']==a['state'] and c['due_at']==a['due_at'] and c['original_due_at']==a['original_due_at']
    assert c['evidence_refs']['sent_job_ids']==[3,4]
    assert store.in_transaction
    store.rollback()
    assert tickets.get(store,a['id'])['workaround']=={}
    assert store.execute('SELECT count(*) FROM ticket_events WHERE ticket_id=?',(a['id'],)).fetchone()[0]==1
    # Audit failure must roll back workaround + refs + event together.
    store.execute("CREATE TEMP TRIGGER fail_merge_audit BEFORE INSERT ON audit_log BEGIN SELECT RAISE(ABORT,'audit failed'); END")
    with pytest.raises(sqlite3.IntegrityError):
        tickets.from_fix(store,1,None,5,'missing','cách ba',{'sent_job_ids':[5]})
    assert tickets.get(store,a['id'])==a
    assert store.execute('SELECT count(*) FROM ticket_events WHERE ticket_id=?',(a['id'],)).fetchone()[0]==1

def test_closed_blocked_queue_is_history(store):
    from devsys import tickets_page as ui
    closed=make(store,'closed',impact={'blocked_shots':[2]})
    store.execute("UPDATE support_tickets SET state='closed' WHERE id=?",(closed['id'],))
    active=make(store,'active',now=tickets._time()-timedelta(hours=80))
    assert [t['id'] for t in ui.queue(store)]==[active['id'],closed['id']]

def test_rejected_approve_closes_with_cas(store):
    from devsys import tickets_page as ui
    owner=Identity('owner@example.com','owner','owner')
    a=make(store,'rejected',kind='budget')
    for state in ('triaged','waiting_admin','rejected'):
        a=tickets.transition(store,a['id'],state,owner,'đã kiểm',a['state'],expected_revision=a['revision'])
    b=ui.decide(store,a['id'],'Duyệt',owner,'đóng sau từ chối',a['revision'])
    assert b['state']=='closed' and b['closed_by']==owner.email
    assert b['due_at']==a['due_at'] and b['original_due_at']==a['original_due_at']
    with pytest.raises(tickets.TicketError): ui.decide(store,a['id'],'Gia hạn',owner,'cũ',a['revision'],new_due=tickets._time()+timedelta(days=8))

def test_read_connection_paths_ignore_cwd(tmp_path,monkeypatch):
    from devsys import tickets_page as ui
    captured=[]
    class Connection:
        def execute(self,*args): pass
        def close(self): pass
    monkeypatch.setattr(ui.sqlite3,'connect',lambda database,**kw: captured.append(database) or Connection())
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('PIPELINE_DB',raising=False)
    from pathlib import Path
    root=Path(ui.__file__).resolve().parents[1]
    with ui.read_connection(): pass
    assert captured[-1]==(root/'data'/'manifest.sqlite').as_uri()+'?mode=ro'
    monkeypatch.setenv('PIPELINE_DB','relative/test.sqlite')
    with ui.read_connection(): pass
    assert captured[-1]==(root/'relative'/'test.sqlite').as_uri()+'?mode=ro'
    monkeypatch.setenv('PIPELINE_DB',str(tmp_path/'absolute.sqlite'))
    with ui.read_connection(): pass
    assert captured[-1]==(tmp_path/'absolute.sqlite').as_uri()+'?mode=ro'

@pytest.mark.parametrize('support,admin',[(False,False),(False,True),(True,False),(True,True)])
def test_navigation_flags_preserve_old_options(monkeypatch,support,admin):
    import ast
    from pathlib import Path
    from devsys import tickets_page as ui
    source=(Path(ui.__file__).parent/'app.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    sidebar=next(n for n in tree.body if isinstance(n,ast.With) and ast.unparse(n.items[0].context_expr)=='st.sidebar')
    start=next(i for i,n in enumerate(sidebar.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ticket_ui_enabled','page') for t in n.targets))
    end=next(i for i in range(start,len(sidebar.body)) if isinstance(sidebar.body[i],ast.Expr) and ast.unparse(sidebar.body[i])=='st.divider()')
    snippet='\n'.join(ast.unparse(n) for n in sidebar.body[start:end])
    monkeypatch.setattr('core.features.on',lambda name: support if name=='support_tickets' else admin)
    at=AppTest.from_string('import streamlit as st\nfrom core import features\n'+snippet+'\nst.text(page)').run()
    at.query_params['ticket']='linked'; at.run()
    original=['📋 Kế hoạch đang chạy','🗺 Sơ đồ tiến độ','Tổng quan','Bản đồ hệ thống','Dòng thời gian','Sức khỏe (đo bằng code)','Chấm điểm AI','Hiệu quả vận hành','Hiệu quả quy trình','Ai quyết','Làm ↔ Kiểm','Bộ kỹ năng 3 vai','Đang chạy']
    assert at.radio[0].options==original+(['Phiếu'] if support and admin else [])
    assert at.text[0].value==('Phiếu' if support and admin else original[0])
