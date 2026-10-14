import json, os, types
from unittest import mock
import pytest
from core import scene_storyboard as sb, pilot, features
from core.db import connect
from core.pipeline import Pipeline

@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_STORYBOARD_API','1')
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','1')
    p=Pipeline(connect(':memory:')); pid=p.create_project('spots'); ids=[]
    for i,(spot,size) in enumerate([('a','CU'),('b','WS'),('a','WS'),('b','CU')],1):
        sid=p.create_scene(pid,i,'shot'); ids.append(sid)
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps({'story_scene':1,'shot_no':i,'size':size,'plate_spot':spot,'image_prompt':'x'}),sid))
    p.conn.commit()
    return p,pid,ids,tmp_path

def picture(p,pid,sid,path,state='approved'):
    jid=p.create_job(sid,'image_gen'); p.conn.execute('UPDATE jobs SET state=? WHERE id=?',(state,jid)); p.conn.commit()
    target=path/str(pid)/'images'/f'job_{jid}.png'; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b'png')
    return str(target)

def test_groups_first_anchor_and_no_cross_spot(setup):
    p,pid,ids,path=setup
    for sid,expected in [(ids[2],ids[0]),(ids[3],ids[1])]:
        g=sb.group_of(p.conn,pid,sid)
        assert g['anchor']['id']==expected
        assert len(g['shots'])==2 and g['index']==1
        assert sb.uses_anchor(g,sid)
    assert pilot.anchors_needed(p,pid,[ids[2],ids[3]])==ids[:2]

def test_warning_preserves_available_pending_anchor(setup):
    p,pid,ids,path=setup
    first=picture(p,pid,ids[0],path,'pending_review')
    picture(p,pid,ids[2],path)
    assert not sb.waits(p.conn,str(path),pid,ids[2])
    assert sb.anchor_warning(p.conn,str(path),pid,ids[2])
    fields=sb.job_fields(p.conn,str(path),pid,ids[2],[])
    assert fields['refs'][0]['path']==first
    p.conn.execute("UPDATE jobs SET state='approved' WHERE scene_id=?",(ids[0],)); p.conn.commit()
    assert sb.anchor_warning(p.conn,str(path),pid,ids[2]) is None

def test_off_strict_and_toggle_session(setup,monkeypatch):
    p,pid,ids,path=setup
    on=sb.group_of(p.conn,pid,ids[2])
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','0')
    old=sb.group_of(p.conn,pid,ids[2]); assert old['anchor']['id']==ids[1] and len(old['shots'])==4
    assert sb.storyboard_id(pid,old,7)=='sb_'+__import__('hashlib').sha1(f'{pid}:1:7'.encode()).hexdigest()[:12]
    assert sb.storyboard_id(pid,on,7)!=sb.storyboard_id(pid,old,7)
    assert 'anchor_by_spot' in features.OPT_IN_ONLY


def test_runner_payload_warning_and_solo(setup):
    from core.runner import ImageRunner
    p,pid,ids,path=setup
    first=picture(p,pid,ids[0],path,'pending_review')
    second=picture(p,pid,ids[1],path)
    captured=[]; notes=[]
    provider=types.SimpleNamespace(supports_storyboard=True,
        submit=lambda prompt,references,**kw: captured.append((prompt,references,kw)))
    runner=ImageRunner(p,provider,str(path))
    runner._diag=lambda job,sev,code,msg: notes.append((sev,code,msg))
    for sid,anchor,other in [(ids[2],first,second),(ids[3],second,first)]:
        job=dict(p.job(p.create_job(sid,'image_gen')))
        prompt,refs=runner._finish_args(job,'frame',[])
        provider.submit(prompt,refs,**runner._submit_kwargs(job))
        assert anchor in captured[-1][1] and other not in captured[-1][1]
        board=captured[-1][2]['storyboard']
        assert (board['frame_index'],board['group_size'])==(1,2)
        assert 'Image 1' in board['image_mapping']
    assert captured[0][2]['storyboard']['storyboard_id']!=captured[1][2]['storyboard']['storyboard_id']
    assert any(sev=='warn' and code=='storyboard_anchor_unapproved' for sev,code,msg in notes)
    d={'story_scene':1,'shot_no':5,'plate_spot':'solo','image_prompt':'x'}
    sid=p.create_scene(pid,5,'solo');p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps(d),sid));p.conn.commit()
    assert sb.group_of(p.conn,pid,sid) is None
    assert sb.anchor_warning(p.conn,str(path),pid,sid) is None      # shot một mình ở chỗ: không có ảnh neo nào để chờ duyệt
    job=dict(p.job(p.create_job(sid,'image_gen')))
    runner._storyboard[job["id"]]={"storyboard_id":"stale"}
    assert runner._finish_args(job,'solo',[])==('solo',)
    assert 'storyboard' not in runner._submit_kwargs(job)

def test_no_spot_old_group_and_malformed_warning(setup):
    p,pid,ids,path=setup
    def update(value):
        d=json.loads(p.conn.execute('SELECT data FROM scenes WHERE id=?',(ids[2],)).fetchone()['data']);d['plate_spot']=value
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps(d),ids[2]));p.conn.commit()
    update(None)
    assert sb.group_of(p.conn,pid,ids[2])['anchor']['id']==ids[1]
    assert sb.anchor_warning(p.conn,str(path),pid,ids[2]) is None
    update(['a'])
    assert 'không hợp lệ' in sb.anchor_warning(p.conn,str(path),pid,ids[2])

def test_default_off_even_global_toggle(monkeypatch):
    monkeypatch.delenv('FEATURE_ANCHOR_BY_SPOT',raising=False)
    with mock.patch.object(features, 'settings', return_value={'flags': {}, 'preset': 'experimental'}):
        assert not features.on('anchor_by_spot')


def test_before_run_uses_both_group_anchors(setup):
    from core.before_run import _storyboard_items
    p,pid,ids,path=setup
    scenes=[dict(r) for r in p.conn.execute('SELECT id,idx,data FROM scenes WHERE project_id=?',(pid,))]
    for row in scenes:
        row['data']=json.loads(row['data'])
    items=_storyboard_items(p.conn,str(path),pid,scenes)
    text=str(items)
    assert 'neo shot 1' in text and 'neo shot 2' in text

def test_before_run_mixed_spots_counts_each_dependency_once(setup):
    from core.before_run import _storyboard_items
    p,pid,ids,path=setup
    for i,spot in [(5,None),(6,'solo')]:
        sid=p.create_scene(pid,i,'mixed')
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?',
                       (json.dumps({'story_scene':1,'shot_no':i,'plate_spot':spot,'size':'CU'}),sid))
    p.conn.commit()
    scenes=[dict(r) for r in p.conn.execute('SELECT id,idx,data FROM scenes WHERE project_id=?',(pid,))]
    for row in scenes:
        row['data']=json.loads(row['data'])
    scenes.append(scenes[2])  # danh sách lặp không tạo thêm phụ thuộc
    items=_storyboard_items(p.conn,str(path),pid,scenes)
    assert len(items)==1
    assert '1 shot chờ ảnh neo shot 1' in items[0]['text']
    assert '2 shot chờ ảnh neo shot 2' in items[0]['text']
    assert items[0]['text'].count('shot chờ ảnh neo')==2
    for sid in ids[:2]:
        p.create_job(sid,'image_gen')
    assert _storyboard_items(p.conn,str(path),pid,scenes)[0]['text']==(
        'Chế độ storyboard: 3 shot chờ ảnh neo đang làm — gửi sau khi có ảnh neo')

def test_warning_tracks_selected_anchor_job_missing_latest_file(setup):
    p,pid,ids,path=setup
    picture(p,pid,ids[0],path)
    latest=picture(p,pid,ids[0],path)
    os.remove(latest)
    assert sb.anchor_picture(p.conn,str(path),pid,ids[0]) is None
    assert sb.anchor_warning(p.conn,str(path),pid,ids[2])
    assert sb.waits(p.conn,str(path),pid,ids[2])

def test_runner_off_preserves_legacy_cache_but_clears_after_on(setup,monkeypatch):
    from core.runner import ImageRunner
    p,pid,ids,path=setup
    sid=p.create_scene(pid,5,'solo')
    p.conn.execute('UPDATE scenes SET data=? WHERE id=?',
                   (json.dumps({'story_scene':2,'shot_no':1,'plate_spot':'solo'}),sid))
    p.conn.commit()
    runner=ImageRunner(p,types.SimpleNamespace(supports_storyboard=True),str(path))
    job=dict(p.job(p.create_job(sid,'image_gen')))
    cached={'storyboard_id':'legacy'}
    runner._storyboard={job['id']:cached}
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','0')
    runner._finish_args(job,'solo',[])
    assert runner._submit_kwargs(job)['storyboard']==cached
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','1')
    runner._finish_args(job,'solo',[])
    assert 'storyboard' not in runner._submit_kwargs(job)
    runner._storyboard[job['id']]={'storyboard_id':'on-stale'}
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','0')
    runner._finish_args(job,'solo',[])
    assert 'storyboard' not in runner._submit_kwargs(job)
    runner._storyboard[job['id']]=cached
    runner._finish_args(job,'solo',[])
    assert runner._submit_kwargs(job)['storyboard']==cached


def test_no_warning_while_drawing_the_anchor_itself(setup):
    p,pid,ids,path=setup
    assert sb.anchor_warning(p.conn,str(path),pid,ids[0]) is None   # shot neo chưa có ảnh: không tự cảnh báo chính nó
    assert sb.anchor_warning(p.conn,str(path),pid,ids[2])            # shot dùng neo chưa duyệt: vẫn VÀNG


def test_change_review_reaches_no_spot_shot_anchored_on_the_changed_shot(tmp_path, monkeypatch):
    from core import change_review
    monkeypatch.setenv('FEATURE_STORYBOARD_API','1')
    monkeypatch.setenv('FEATURE_ANCHOR_BY_SPOT','1')
    p=Pipeline(connect(':memory:')); pid=p.create_project('spots'); ids=[]
    for i,(spot,size) in enumerate([('a','WS'),('a','CU'),(None,'MS'),(None,'CU')],1):
        sid=p.create_scene(pid,i*10,'shot'); ids.append(sid)
        d={'story_scene':1,'shot_no':i,'size':size,'image_prompt':'x'}
        if spot: d['plate_spot']=spot
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps(d),sid))
    p.conn.commit()
    assert sb.group_of(p.conn,pid,ids[3])['anchor']['id']==ids[0]
    kind=next(iter(change_review.SHOT_KINDS))
    got=change_review.affected_scenes(p.conn,{'kind':kind,'scene_id':ids[0],'asset_id':None})
    assert ids[3] in got and ids[2] in got
