import json
from pathlib import Path
from unittest import mock
import pytest
from core.db import connect
from core.pipeline import Pipeline
from core import access, features
from dashboard import continuity_ui as ui

@pytest.fixture
def project():
    p = Pipeline(connect(':memory:'))
    pid = p.create_project('Giả')
    for idx, place in [(1,'khác'), (2,'sân'), (3,'sân'), (4,'sân')]:
        sid = p.create_scene(pid,idx,f'Shot {idx}')
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps({'location':place,'shot_no':idx,'continuity_from':4 if idx==3 else None}),sid))
    p.conn.commit()
    return p,pid

def test_same_place_previous_first_future_current_preserved(project):
    p,pid=project
    assert [r['idx'] for r in ui.options(p,pid,3)] == [2,1,4]
    assert [r['idx'] for r in ui.options(p,pid,2)] == [1]

def test_save_through_backend_keeps_lock_and_rejects_cycle(project):
    p,pid=project
    ui.save(p,pid,3,2)
    d=json.loads(p.conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=3',(pid,)).fetchone()[0])
    assert d['continuity_from']==2 and 'continuity_from' in d['_user_locked']
    with pytest.raises(Exception,match='vòng'):
        ui.save(p,pid,2,3)
    ui.save(p,pid,3,None)
    assert json.loads(p.conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=3',(pid,)).fetchone()[0])['continuity_from'] is None

def test_server_edit_rights(project):
    p,pid=project
    p.user={'email':'stranger@example.test','role':'member'}
    with pytest.raises(access.AccessDenied): ui.save(p,pid,3,1)

def test_preview_uses_selected_job_and_local_file(project,tmp_path):
    p,pid=project
    sid=p.conn.execute('SELECT id FROM scenes WHERE project_id=? AND idx=2',(pid,)).fetchone()[0]
    jid=p.create_job(sid,'image_gen')
    p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?",(jid,)); p.conn.commit()
    assert ui.preview(p,pid,2,tmp_path)==(None,'chưa có ảnh',True)
    dest=tmp_path/str(pid)/'images'/f'job_{jid}.png'; dest.parent.mkdir(parents=True); dest.write_bytes(b'png')
    assert ui.preview(p,pid,2,tmp_path)==(str(dest),'đã duyệt',False)
    p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?",(jid,)); p.conn.commit()
    assert ui.preview(p,pid,2,tmp_path)[1:]==('chờ duyệt',True)
    assert ui.preview(p,pid+999,2,tmp_path)==(None,'chưa có ảnh',True)

def test_off_does_not_render_or_read(project):
    p,pid=project
    with mock.patch.object(features,'on',return_value=False), mock.patch.object(ui,'options',side_effect=AssertionError):
        ui.render(p,pid,3,'step1')

def test_flag_is_opt_in():
    assert 'continuity_from_ui' in features.OPT_IN_ONLY
    assert features.FEATURES['continuity_from_ui']['verified'] is False

def test_component_select_save_remove_and_future(project,tmp_path):
    from streamlit.testing.v1 import AppTest
    p,pid=project
    db=tmp_path/'demo.sqlite'
    target=connect(str(db));p.conn.backup(target);target.close()
    script='''
import streamlit as st
from unittest import mock
from dashboard import continuity_ui as ui, common as C
from core import features
from core.db import connect
from core.pipeline import Pipeline
p=Pipeline(connect(st.session_state['db']))
with mock.patch.object(features,'on',side_effect=lambda name: name=='continuity_from_ui'), mock.patch.object(C,'read_only',return_value=False), mock.patch.object(C,'DATA',st.session_state['data_dir']):
    ui.render(p,st.session_state['pid'],3,'test')
p.conn.close()
'''
    at=AppTest.from_string(script)
    at.session_state['db']=str(db);at.session_state['pid']=pid;at.session_state['data_dir']=str(tmp_path)
    at.run()
    assert not at.exception
    assert at.selectbox[0].value==4
    assert len(at.warning)==1
    at.selectbox[0].select(2).run()
    at.button[-1].click().run()
    assert not at.exception
    conn=connect(str(db))
    assert json.loads(conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=3',(pid,)).fetchone()[0])['continuity_from']==2
    at.button[0].click().run()
    assert not at.exception
    assert at.selectbox[0].value is None
    assert json.loads(conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=3',(pid,)).fetchone()[0])['continuity_from'] is None
    conn.close()

@pytest.mark.parametrize('older,enabled', [(False,True),(True,True),(False,False)])
def test_v2_card_reaches_real_component(project,tmp_path,older,enabled):
    from streamlit.testing.v1 import AppTest
    p,pid=project
    sid=p.conn.execute('SELECT id FROM scenes WHERE project_id=? AND idx=3',(pid,)).fetchone()[0]
    for _ in range(2):
        jid=p.create_job(sid,'image_gen')
        p.conn.execute("UPDATE jobs SET state='cancelled' WHERE id=?",(jid,))
    p.conn.commit()
    db=tmp_path/'v2.sqlite'
    target=connect(str(db));p.conn.backup(target);target.close()
    script='''
import streamlit as st
from contextlib import nullcontext
from unittest import mock
from core.db import connect
from core.pipeline import Pipeline
from core import features
from dashboard import continuity_ui as ui,common as C
from dashboard.design.screens import storyboard_cards as SB,prompt_versions_ui,older_take_ui
p=Pipeline(connect(st.session_state['db']))
pid=st.session_state['pid']
history=[dict(r) for r in p.conn.execute("SELECT j.*,s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE s.project_id=? ORDER BY j.id",(pid,))]
st.session_state[f'hist_{pid}_{history[0]["scene_id"]}']=0 if st.session_state['older'] else 1
with mock.patch.object(features,'on',side_effect=lambda name: st.session_state['enabled'] and name=='continuity_from_ui'), mock.patch.object(C,'read_only',return_value=False), mock.patch.object(C,'DATA',st.session_state['data_dir']), mock.patch.object(C,'job_image',return_value=None), mock.patch.object(SB.cost,'image_button_tag',return_value=''), mock.patch.object(SB.D,'info',side_effect=lambda *a,**k:nullcontext()), mock.patch.object(SB,'card_details'), mock.patch.object(SB,'_qc_chips',return_value=''), mock.patch.object(prompt_versions_ui,'panel'), mock.patch.object(older_take_ui,'use_button'), mock.patch.object(ui,'render',wraps=ui.render) as reached:
    SB.image_group_v2(p,pid,history,p.project(pid))
    st.session_state['reached']=[(call.args[1:3],call.kwargs) for call in reached.call_args_list]
p.conn.close()
'''
    at=AppTest.from_string(script)
    for key,value in dict(db=str(db),pid=pid,data_dir=str(tmp_path),older=older,enabled=enabled).items():
        at.session_state[key]=value
    at.run()
    assert not at.exception
    assert at.session_state['reached']==[((pid,3),{'read_only':older})]
    assert len(at.selectbox)==int(enabled)
    if enabled:
        assert at.selectbox[0].value==4
        assert at.selectbox[0].disabled==older
        assert len(at.warning)==1
