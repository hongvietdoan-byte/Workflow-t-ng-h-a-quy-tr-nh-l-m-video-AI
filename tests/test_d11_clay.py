from copy import deepcopy
import time
from PIL import Image
import pytest
from core import features, blockout_sheet, blockout_clay, director_blockout
from tests.test_blockout import box, plan

@pytest.fixture(autouse=True)
def isolated_flags(monkeypatch):
    monkeypatch.setattr(features, 'on', lambda name: True)

def test_round_columns(tmp_path):
    r = blockout_sheet.render_top_view(plan(box(loai='cot')), [], tmp_path/'top.png')
    assert r['blocks'][0]['shape'] == 'ellipse'

def test_fake_render_contract_and_sheet(tmp_path):
    calls = []
    def render(cfg, **kw):
        calls.append(cfg)
        plates = []
        for cam in cfg['cameras']:
            from pathlib import Path
            f = Path(cfg['out_dir']) / ('plate_'+cam['name']+'.png')
            Image.new('RGB', (320, 180), 'gray').save(f)
            plates.append({'name':cam['name'], 'file':f.name})
        return {'plates':plates}
    r = blockout_clay.render_sheet(plan(box()), [[0,0]], tmp_path/'sheet.png', renderer=render)
    assert r['clay'] and len(r['views']) == 4
    assert calls[0]['blockout_clay'] and calls[0]['model'] is None
    assert all(c['props'][0]['stand_in'] for c in calls[0]['cameras'])
    assert Image.open(tmp_path/'sheet.png').width > 1200

def test_failure_projects_camera_and_explains(tmp_path):
    def fail(*a, **k): raise RuntimeError('fake renderer')
    r = blockout_clay.render_sheet(plan(box()), [], tmp_path/'sheet.png', renderer=fail)
    assert not r['clay'] and r['reason'] and r['projection']['blocks']

def test_three_environments_and_geometry(tmp_path):
    from core import blockout
    for i, kind in enumerate(('tuong','cay_khoi','bac')):
        start=time.monotonic()
        p=plan(box(loai=kind))
        assert not any(x['muc']=='do' for x in blockout.check_geometry(p))
        blockout_clay.render_sheet(p, [], tmp_path/f'{i}.png', renderer=lambda *a, **k: {'plates':[]})
        assert time.monotonic()-start < 120
    assert any(x['code']=='overlap' for x in blockout.check_geometry(plan(box('a'),box('b'))))
    assert blockout.check_geometry(plan(), vat_kich_ban=['giếng'])

def test_director_retry_changes_input_estimates_and_locks():
    source = plan(box('wall'))
    inp={'previous_end':source, 'same_space':True, 'locked_blocks':{'wall':{'tam':[3,3]}}}
    seen=[]; estimates=[]
    def call(prompt):
        seen.append(prompt)
        answer=deepcopy(source)
        if len(seen)==1: answer['khoi'].append(box('b'))
        return {'blockout':answer}
    r=director_blockout.generate(inp, call=call, estimate=lambda: estimates.append(1) or .01)
    assert r['ok'] and len(seen)==2 and seen[0]!=seen[1] and len(estimates)==2
    assert source['khoi'][0]['tam']==[3,3]

def test_director_off_no_call(monkeypatch):
    monkeypatch.setattr(features,'on',lambda name:False)
    assert director_blockout.append_prompt('exact\r\n',{})=='exact\r\n'
    assert director_blockout.generate({},call=lambda p: pytest.fail('OFF called'),estimate=lambda:0)['enabled'] is False

def test_director_locked_change_and_exhaustion():
    source=plan(box('wall'))
    changed=deepcopy(source); changed['khoi'][0]['tam']=[4,3]
    r=director_blockout.generate({'locked_blocks':{'wall':{'tam':[3,3]}}},call=lambda _: {'blockout':changed},estimate=lambda:.01)
    assert not r['ok'] and r['calls']==2 and r['issues'] and 'hai lần' in r['warning']

def test_actors_use_whitebox_and_local_paths(tmp_path):
    cfg=blockout_clay.render_config(plan(box()),tmp_path,people=[{'key':'Kelly','at':[1,2,.5],'H':1.7,'facing':90}])
    assert cfg['actors'][0]['keys'][0]['location']==[1,2,.5]
    for path in ('https://fake/a.png',r'\\fake\a.png'):
        with pytest.raises(ValueError,match='cục bộ'):
            blockout_clay.render_sheet(plan(box()),[],tmp_path/'x.png',reference=path)

def test_paid_adapter_estimates_each_call_and_tags_ledger(monkeypatch):
    from core import llm_runner,cost
    from contextlib import contextmanager
    from types import SimpleNamespace
    events=[]
    @contextmanager
    def tagged(stage,pid):
        events.append('tag'); yield
    monkeypatch.setattr(llm_runner,'tagged',tagged)
    monkeypatch.setattr(cost,'llm_estimate',lambda *a:events.append('estimate') or .01)
    class Fake:
        ledger='fake-ledger'
        def complete(self,text):
            events.append('call')
            return SimpleNamespace(text=__import__('json').dumps({'blockout':plan(box())}),input_tokens=3,output_tokens=4)
    result=director_blockout.run_stage(None,Fake(),{'same_space':False},'prompt',lambda a:None)
    assert result['ok'] and result['tokens']==[3,4] and events==['estimate','tag','call']

def test_unknown_or_missing_continuity_is_visible():
    answer={'blockout':plan(box())}
    assert any(i['muc']=='do' for i in director_blockout.issues_for(answer,{'same_space':True}))
    assert any(i['muc']=='vang' for i in director_blockout.issues_for(answer,{}))

def test_off_prompt_matches_base_bytes(monkeypatch):
    import hashlib
    from core import stage_director
    from tests.test_stage_director import inputs
    monkeypatch.setattr(features,'on',lambda name:False)
    assert hashlib.sha256(stage_director.build_prompt(inputs()).encode()).hexdigest() == '15c686d81f2c44adaa06ae1a696584d7b1a1c6540e9ad70b704c1db830522d65'   # 16/10: prompt 29 nói rõ thứ tự vùng ngang-dọc + vật cố định code tự thêm

@pytest.mark.parametrize('enabled',[False,True])
def test_v3_caller_fake_saves_blockout_and_people(tmp_path,monkeypatch,enabled):
    import json
    from types import SimpleNamespace
    from tools import stage_grid as cli
    from core import cost,llm_runner,script_cap,change_review,stage_grid
    from tests.test_stage_director import inputs,hand_answer,MARKS
    monkeypatch.setattr(features,'on',lambda name:enabled if name=='director_blockout' else False)
    inp=inputs(); inp['same_space']=False
    answer=hand_answer()
    if enabled:
        inp.update(fixed=[],people=[{'key':'kelly','H':1.7}],shots=[{'shot':1,'action':'Kelly đứng'}],cho_dung=[[0,0]],vat_kich_ban=['a'])
        answer={'blockout':plan(box()),'blocking':{'objects':[{'key':'kelly','kind':'nguoi','at':[0,0],'H':1.7,'facing':0}]},
                'shot_specs':[{'shot':1,'co':'WS','do_cao':'ngang','goc':'ngang','muc_dich':'nhìn Kelly',
                               'thanh_phan':[{'vat':'kelly','vai':'chinh','vung':'giua','thay':'mat'}]}]}
    source=tmp_path/'source'; source.mkdir()
    (source/'stage.json').write_text(json.dumps(dict(stage_grid.make_stage([0,0,0]),marks=MARKS)),encoding='utf-8')
    (source/'grid.json').write_text('{"cells":[]}',encoding='utf-8')
    path=tmp_path/'inputs.json'; path.write_text(json.dumps(inp),encoding='utf-8')
    calls=[]; previews=[]
    class Fake:
        ledger='fake-ledger'; retries=2
        def complete(self,prompt):
            calls.append('complete')
            assert self.retries==0
            assert prompt.count('## Sơ đồ khối bắt buộc')==1
            return SimpleNamespace(text=json.dumps(answer),input_tokens=2,output_tokens=3)
    def ask(*args,**kwargs):
        calls.append('ask_json'); return answer,2,3
    monkeypatch.setattr(llm_runner,'client_from_env',lambda **kwargs:Fake())
    monkeypatch.setattr(llm_runner,'ask_json',ask)
    monkeypatch.setattr(cost,'llm_estimate',lambda *args:.01)
    monkeypatch.setattr(cost,'llm_model',lambda:'fake')
    monkeypatch.setattr(change_review,'enabled',lambda:False)
    monkeypatch.setattr(script_cap,'from_args',lambda *args:SimpleNamespace(start=lambda:None))
    monkeypatch.setattr(cli,'_scene_shots',lambda *args:[])
    monkeypatch.setattr(cli,'_floor_notes',lambda *args:[])
    monkeypatch.setattr(cli,'review_stage_round',lambda *args,**kwargs:None)
    monkeypatch.setattr(blockout_clay,'render_sheet',lambda *args,**kwargs:previews.append(kwargs) or {'clay':False})
    def v2(args):
        if enabled: pytest.fail('nhánh C chỉ ảnh không được gọi v2 renderer đòi model3d')
        out=__import__('pathlib').Path(args[args.index('--out')+1])
        (out/'setups.json').write_text('{"shots":[]}',encoding='utf-8')
        (out/'v2.json').write_text('{"shots":[]}',encoding='utf-8')
    monkeypatch.setattr(cli,'v2_main',v2)
    out=tmp_path/'out'
    import sqlite3
    with sqlite3.connect(tmp_path/'db.sqlite') as db:
        db.execute('CREATE TABLE assets(id INTEGER PRIMARY KEY, profile TEXT)')
        db.execute('INSERT INTO assets VALUES(?,?)',(inp['place'],'{}'))
    cli.v3_main(['--db',str(tmp_path/'db.sqlite'),'--inputs',str(path),'--out',str(out),'--stage-from',str(source),'--yes','--max-usd','1'])
    assert calls==(['complete'] if enabled else ['ask_json'])
    assert (out/'r1'/'blockout.json').exists() is enabled
    if enabled:
        assert previews[0]['people'][0]['H']==1.7
        assert previews[0]['camera']['location'] != [0,0,0]
        assert json.loads((out/'r1'/'blocking.json').read_text(encoding='utf-8'))['objects'][1]['key']=='a'
        assert json.loads((out/'r1'/'v2.json').read_text(encoding='utf-8'))['measurement']=='numeric_only'

def test_corrupt_locked_blocks_and_missing_geometry_inputs_visible():
    for locks in ([],['wall'],{'wall':[]}):
        issues=director_blockout.issues_for({'blockout':plan(box())},{'locked_blocks':locks})
        assert any(i['muc']=='do' and i['path']=='locked_blocks' for i in issues)
    issues=director_blockout.issues_for({'blockout':plan(box())},{'same_space':False})
    assert {i['path'] for i in issues if i['muc']=='vang'} >= {'cho_dung','vat_kich_ban'}

def test_real_model_never_uses_branch_c_or_appends_prompt():
    import sqlite3,json
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE assets(id INTEGER PRIMARY KEY,profile TEXT)')
        db.execute('INSERT INTO assets VALUES(1,?)',(json.dumps({'model3d':{'path':'local-fake.glb'}}),))
        assert not director_blockout.scene_uses_blockout(db,{'place':1})
        assert director_blockout.append_prompt('exact',{'_blockout_enabled':False})=='exact'
        with pytest.raises(ValueError,match='chưa có hồ sơ'):
            director_blockout.scene_uses_blockout(db,{'place':2})

def test_numeric_camera_failure_retries_with_changed_input():
    from core import llm_io
    seen=[]
    def call(text): seen.append(text); return {'blockout':plan(box())}
    def validate(obj):
        if len(seen)==1: raise llm_io.SchemaError('shot 1: máy ngoài khung; cần dời máy')
    result=director_blockout.generate({'same_space':False,'cho_dung':[],'vat_kich_ban':[]},
                    call=call,estimate=lambda:.01,validate=validate)
    assert result['ok'] and result['calls']==2
    assert 'máy ngoài khung' in seen[1] and seen[0]!=seen[1]
