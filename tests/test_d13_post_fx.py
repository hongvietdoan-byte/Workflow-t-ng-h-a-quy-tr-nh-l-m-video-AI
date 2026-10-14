"""Đ13v1: dữ liệu giả, không client/API, shell proof thay environ trước import."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from core import post_fx, rough_cut, editor_review, features, knowledge
from tests.test_post_fx import SPEC, pipeline


def test_output_same_inputs_stable_and_source_changes(tmp_path, monkeypatch):
    src = tmp_path / 'source.mp4'; src.write_bytes(b'first')
    def render(cmd):
        from pathlib import Path
        Path(cmd[-1]).write_bytes(b'rendered')
    monkeypatch.setattr(features, 'on', lambda n: n == 'post_fx_render')
    monkeypatch.setattr(post_fx.f, 'find_ffmpeg', lambda: 'fake-ffmpeg')
    monkeypatch.setattr(post_fx.f, 'run', render)
    p = pipeline(SPEC)
    def apply(seconds=2):
        paths = [str(src)]
        result = post_fx.apply(p, [{'scene_id':1, 'idx':1, 'path':str(src)}], paths, [seconds], str(tmp_path/'fx'))
        assert result[0]['muc'] == 'xanh'
        return paths[0]
    a = apply(); assert a == apply()
    alias=tmp_path/'same-bytes.mp4'; alias.write_bytes(src.read_bytes())
    assert post_fx._output_path(str(tmp_path/'fx'),1,str(alias),SPEC,2)==a
    assert len(list((tmp_path/'fx').glob('*.mp4'))) == 1
    src.write_bytes(b'other')
    assert apply() != a
    assert apply(1.5) != apply()
    previous = apply()
    p.conn.execute('UPDATE scenes SET data=?', (json.dumps({'post_fx':{**SPEC, 'cuong_do':.3}}),))
    assert apply() != previous
    assert src.read_bytes() == b'other'
    p.conn.close()


def test_repeat_failure_keeps_previous_atomic_output(tmp_path, monkeypatch):
    from pathlib import Path
    src=tmp_path/'src.mp4'; src.write_bytes(b'original')
    p=pipeline(SPEC); paths=[str(src)]; rows=[{'scene_id':1,'path':str(src)}]
    monkeypatch.setattr(features,'on',lambda n:True)
    monkeypatch.setattr(post_fx.f,'find_ffmpeg',lambda:'fake')
    monkeypatch.setattr(post_fx.f,'run',lambda cmd:Path(cmd[-1]).write_bytes(b'complete'))
    post_fx.apply(p,rows,paths,[2],str(tmp_path/'fx')); dst=paths[0]
    def fail(cmd):
        Path(cmd[-1]).write_bytes(b'partial')
        raise post_fx.f.FFmpegError('fake failure')
    monkeypatch.setattr(post_fx.f,'run',fail)
    paths=[str(src)]; got=post_fx.apply(p,rows,paths,[2],str(tmp_path/'fx'))
    assert got[0]['muc']=='vang' and paths==[str(src)]
    assert Path(dst).read_bytes()==b'complete' and not list((tmp_path/'fx').glob('*.part-*.mp4'))
    p.conn.close()


def test_editor_post_fx_flag_context_and_cache(monkeypatch):
    res={'fingerprint':'same','source':'director_intent_raw','shots':[],'scenes':[], 'sheets':[],
         'post_fx':[{'scene_id':1,'muc':'xanh','spec':{**SPEC,'loai':'glitch'}}, {'scene_id':2,'muc':'vang','reasons':['fake failure']}]}
    monkeypatch.setattr(knowledge,'kelly_blocks',lambda *a:[])
    monkeypatch.setattr(features,'on',lambda n:False)
    off=editor_review.editor_prompt(res)
    clean=deepcopy(res); clean.pop('post_fx')
    assert editor_review.editor_prompt(clean)==off
    off_fp=editor_review.fingerprint(res)
    monkeypatch.setattr(features,'on',lambda n:n=='post_fx_render')
    on=editor_review.editor_prompt(res)
    assert on[0]!=off[0] and 'post_fx' in on[0] and 'glitch' in on[0] and 'VÀNG' in on[0]
    assert editor_review.fingerprint(res)!=off_fp
    changed=deepcopy(res); changed['post_fx'][0]['spec']['cuong_do']=.1
    assert editor_review.fingerprint(changed)!=editor_review.fingerprint(res)


def test_rough_cut_manifest_context_and_fingerprint(tmp_path, monkeypatch):
    src=tmp_path/'final.mp4'; src.write_bytes(b'fake')
    effects=[{'scene_id':1,'muc':'xanh','spec':SPEC}]
    row={'id':1,'path':str(src),'manifest':json.dumps({'timeline':[], 'post_fx':effects})}
    intent={'fingerprint':'intent','source':'none','stale':False,'scenes':{}}
    monkeypatch.setattr(rough_cut.lineage,'latest_output',lambda *a:row)
    monkeypatch.setattr(rough_cut.director_two_pass,'intent_all',lambda *a:intent)
    monkeypatch.setattr(rough_cut,'shot_clock',lambda *a:[])
    monkeypatch.setattr(rough_cut,'glitch_hints',lambda *a:0)
    monkeypatch.setattr(rough_cut.music_timing,'loudness',lambda *a:[])
    from core import final_qc
    monkeypatch.setattr(final_qc,'silent_spans',lambda *a:[])
    monkeypatch.setattr(rough_cut,'sheets',lambda *a:{'paths':[],'seen':0,'total':0,'dropped':[]})
    p=SimpleNamespace(conn=None)
    monkeypatch.setattr(features,'on',lambda n:False)
    off=rough_cut.build(p,1,str(tmp_path/'data'),force=True)
    assert 'post_fx' not in off
    monkeypatch.setattr(features,'on',lambda n:n=='post_fx_render')
    on=rough_cut.build(p,1,str(tmp_path/'data'))
    assert on['post_fx']==effects and on['fingerprint']!=off['fingerprint']
    row['manifest']=json.dumps({'timeline':[], 'post_fx':[]})
    assert rough_cut.fingerprint(row,intent)!=on['fingerprint']


def test_director_schema_only_when_p24_enabled(monkeypatch):
    monkeypatch.setattr(features,'on',lambda n:False)
    assert knowledge.p24_blocks()==[]
    monkeypatch.setattr(features,'on',lambda n:n=='p24_lessons')
    text=knowledge.p24_blocks()[0]
    assert all(word in text for word in ('post_fx','loai','vi_tri','thoi_luong_s','cuong_do','ca_shot'))


def test_missing_rgbashift_only_skips_glitch(monkeypatch):
    from tests import test_post_fx as tests
    monkeypatch.setattr(tests.subprocess,'check_output',lambda *a,**k:' T.. noise video noise\n T.. eq video equalizer')
    with pytest.raises(pytest.skip.Exception,match='rgbashift'):
        tests.require_filter('fake','rgbashift')
    tests.require_filter('fake','noise')

@pytest.mark.parametrize('mode', [None, 'per_shot'])
def test_director_storage_reaches_post_fx_renderer(tmp_path, monkeypatch, mode):
    from core import llm_io, shots
    from core.db import connect
    from core.pipeline import Pipeline
    p=Pipeline(connect()); pid=p.create_project('fixture')
    p.create_scene(pid,1,'fixture')
    p.conn.execute('UPDATE projects SET shot_mode=? WHERE id=?',(mode,pid));p.conn.commit()
    scene={'idx':1,'location':'fixture','time':'day','mood':'fixture','lighting':'fixture','shot':'MS','image_prompt':'fixture','characters':[], 'duration_s':2,'post_fx':deepcopy(SPEC)}
    if mode:
        scene['shots']=[{'size':'MS','role':'action','action':'fixture','image_prompt':'fixture','duration_s':2,'characters':[],'post_fx':deepcopy(SPEC)}]
    obj={'characters':[],'scenes':[scene]}
    monkeypatch.setattr(features,'on',lambda n:n in ('p24_lessons','post_fx_render'))
    monkeypatch.setattr(llm_io,'_normalized',lambda p,pid,o:o)
    from core import prompt_formula
    monkeypatch.setattr(prompt_formula,'snapshot',lambda *a:None)
    monkeypatch.setattr(prompt_formula,'after_director',lambda *a:None)
    llm_io.store_scene_analysis(p,pid,obj)
    row=p.conn.execute('SELECT id,data FROM scenes WHERE project_id=?',(pid,)).fetchone()
    assert json.loads(row['data'])['post_fx']==SPEC
    src=tmp_path/'src.mp4';src.write_bytes(b'fixture')
    monkeypatch.setattr(post_fx.f,'find_ffmpeg',lambda:'fake')
    monkeypatch.setattr(post_fx.f,'run',lambda cmd:__import__('pathlib').Path(cmd[-1]).write_bytes(b'complete'))
    paths=[str(src)]
    result=post_fx.apply(p,[{'scene_id':row['id'],'path':str(src)}],paths,[2],str(tmp_path/'fx'))
    assert result[0]['muc']=='xanh' and result[0]['spec']==SPEC
    p.conn.close()


def test_second_reviewer_has_same_post_fx_context_and_off_bytes(monkeypatch):
    from core import director_two_pass
    res={'shots':[],'sound':{},'post_fx':[{'scene_id':1,'muc':'xanh','spec':SPEC},{'scene_id':2,'muc':'vang','reasons':['fixture']}]}
    monkeypatch.setattr(director_two_pass,'intent_all',lambda *a:{'scenes':{}})
    monkeypatch.setattr(features,'on',lambda n:False)
    off=editor_review.director_prompt(None,1,res,[])
    empty=deepcopy(res);empty.pop('post_fx')
    assert editor_review.director_prompt(None,1,empty,[])==off
    monkeypatch.setattr(features,'on',lambda n:n=='post_fx_render')
    on=editor_review.director_prompt(None,1,res,[])
    assert 'manifest.post_fx' in on and 'cuoi' in on and 'VÀNG' in on and on!=off

@pytest.mark.parametrize('enabled', [False, True])
def test_shot_post_fx_storage_gate_and_invalid_kept_for_yellow(tmp_path, monkeypatch, enabled):
    from core import shots
    monkeypatch.setattr(features,'on',lambda n:enabled and n=='p24_lessons')
    sc={'idx':1,'characters':[]}
    sh={'size':'MS','role':'action','action':'fixture','image_prompt':'fixture','duration_s':2,'post_fx':{'loai':'invalid'}}
    base=deepcopy(sh);base.pop('post_fx')
    data=shots.shot_data(sc,sh,1)
    if not enabled:
        assert data==shots.shot_data(sc,base,1)
    else:
        assert data['post_fx']==sh['post_fx']
        assert post_fx.validate(data['post_fx'],2)['muc']=='vang'
        sh['post_fx']['loai']='changed'
        assert data['post_fx']['loai']=='invalid'
