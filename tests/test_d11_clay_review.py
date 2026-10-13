"""Hồi quy rà Đ11v2: dữ liệu giả, không Blender/API/credentials."""
from copy import deepcopy
from pathlib import Path
import pytest
from PIL import Image
from core import blockout_clay, blockout_sheet, director_blockout, features, llm_io
from tests.test_blockout import box, plan

@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setattr(features, 'on', lambda name: True)

def answer():
    return {'blockout':plan(box()), 'blocking':{'objects':[
        {'key':'Kelly','kind':'nguoi','at':[0,0],'H':1.7,'facing':0}]}}

@pytest.mark.parametrize('position,reason',[([11,0],'outside_floor'),([3,3],'standing_blocked')])
@pytest.mark.parametrize('beat',[False,True])
def test_model_actor_geometry_all_beats(position,reason,beat):
    obj=answer()
    if beat: obj['blocking']['beats']={'later':{'Kelly':{'at':position}}}
    else: obj['blocking']['objects'][0]['at']=position
    with pytest.raises(llm_io.SchemaError,match=reason):
        director_blockout.blocking_from_plan(obj)

def test_model_prop_override_cannot_move_plan():
    obj=answer(); obj['blocking']['beats']={'later':{'a':{'at':[4,3]}}}
    with pytest.raises(llm_io.SchemaError,match='later.*a'):
        director_blockout.blocking_from_plan(obj)

def test_actor_elevated_floor_not_guessed():
    obj=answer(); obj['blocking']['objects'][0]['z']=1
    with pytest.raises(llm_io.SchemaError,match='sàn phẳng'):
        director_blockout.blocking_from_plan(obj)

def test_same_geometry_error_stops_at_two():
    obj=answer(); obj['blocking']['beats']={'later':{'Kelly':{'at':[11,0]}}}
    seen=[]
    result=director_blockout.generate({'same_space':False,'cho_dung':[],'vat_kich_ban':[]},
        call=lambda text:seen.append(text) or deepcopy(obj),estimate=lambda:.01,
        validate=director_blockout.blocking_from_plan)
    assert not result['ok'] and result['calls']==2 and len(seen)==2
    assert 'outside_floor' in seen[1] and seen[0]!=seen[1]

def test_changed_geometry_errors_still_cap_at_three():
    seen=[]
    def call(text):
        seen.append(text); obj=answer()
        if len(seen)==1: obj['blocking']['objects'][0]['at']=[11,0]
        elif len(seen)==2: obj['blocking']['objects'][0]['at']=[3,3]
        else: obj['blocking']['objects'][0]['z']=1
        return obj
    result=director_blockout.generate({'same_space':False,'cho_dung':[],'vat_kich_ban':[]},
        call=call,estimate=lambda:.01,validate=director_blockout.blocking_from_plan)
    assert not result['ok'] and result['calls']==3 and len(set(seen))==3
    assert 'outside_floor' in seen[1] and 'standing_blocked' in seen[2]

@pytest.mark.parametrize('success',[True,False])
def test_camera_png_survives_return_and_legend_has_all_ids(tmp_path,success):
    def renderer(cfg,**kwargs):
        if not success: raise RuntimeError('fake')
        for camera in cfg['cameras']:
            Image.new('RGB',(320,180),'gray').save(Path(cfg['out_dir'])/f"plate_{camera['name']}.png")
        return {}
    p=plan(box('WallW',xy=(-9,0)),box('StepA',xy=(3,3)),box('StepB',xy=(5,3)))
    result=blockout_clay.render_sheet(p,[],tmp_path/'sheet.png',renderer=renderer)
    with Image.open(result['camera_png']) as image: image.load(); assert image.width>0
    assert Path(result['camera_png']).parent==tmp_path
    assert result['camera_kind']==('clay' if success else 'projection_2d')
    assert result['label_mode']=='legend_only'
    assert [entry['id'] for entry in result['legend']]==['WallW','StepA','StepB']

def test_off_creates_no_camera_sidecar(tmp_path,monkeypatch):
    monkeypatch.setattr(features,'on',lambda name:False)
    result=blockout_clay.render_sheet(plan(box()),[],tmp_path/'sheet.png',renderer=lambda *a,**k:pytest.fail('OFF'))
    assert 'camera_png' not in result and list(tmp_path.glob('*_camera.png'))==[]

def test_topview_edge_label_is_inside_canvas(tmp_path):
    result=blockout_sheet.render_top_view(plan(box('WallW',xy=(-9.5,0),mo_ta_ngan='tường')),[],tmp_path/'top.png')
    x0,y0,x1,y1=result['blocks'][0]['label_box']
    assert 0<=x0<x1<=blockout_sheet.SIZE[0] and 0<=y0<y1<=blockout_sheet.SIZE[1]

@pytest.mark.parametrize('mode,expected_calls,ok',[('repair',2,True),('same',2,False),('changing',3,False)])
def test_v3_real_caller_geometry_retry_budget(tmp_path,monkeypatch,mode,expected_calls,ok):
    import json
    from contextlib import contextmanager
    from types import SimpleNamespace
    from tools import stage_grid as cli
    from core import cost,llm_runner,script_cap,change_review,stage_grid,diag
    inp={'pid':1,'place':1,'spot':'test','canh':'fake','same_space':False,'fixed':[],
         'people':[{'key':'Kelly','H':1.7}], 'shots':[{'shot':1,'action':'đứng'}],
         'cho_dung':[],'vat_kich_ban':['a']}
    source=tmp_path/'source'; source.mkdir()
    (source/'stage.json').write_text(json.dumps(stage_grid.make_stage([0,0,0])),encoding='utf-8')
    (source/'grid.json').write_text('{"cells":[]}',encoding='utf-8')
    path=tmp_path/'inputs.json'; path.write_text(json.dumps(inp),encoding='utf-8')
    seen=[]; events=[]
    class Fake:
        ledger='fake-ledger'; retries=2
        def complete(self,text):
            seen.append(text); events.append('call'); obj=answer()
            obj['shot_specs']=[{'shot':1,'co':'WS','do_cao':'ngang','goc':'ngang','muc_dich':'nhìn Kelly',
                               'thanh_phan':[{'vat':'Kelly','vai':'chinh','vung':'giua','thay':'mat'}]}]
            at=[11,0] if len(seen)==1 or mode=='same' else [3,3]
            if mode!='repair' or len(seen)==1:
                obj['blocking']['beats']={'later':{'Kelly':{'at':at}}}
            if mode=='changing' and len(seen)==3:
                obj['blocking']['beats']={'later':{'Kelly':{'z':1}}}
            return SimpleNamespace(text=json.dumps(obj),input_tokens=2,output_tokens=3)
    @contextmanager
    def tagged(*args):
        events.append('tag'); yield
    monkeypatch.setattr(director_blockout,'scene_uses_blockout',lambda *args:True)
    monkeypatch.setattr(llm_runner,'client_from_env',lambda **kwargs:Fake())
    monkeypatch.setattr(llm_runner,'tagged',tagged)
    monkeypatch.setattr(cost,'llm_estimate',lambda *args:events.append('estimate') or .01)
    monkeypatch.setattr(cost,'llm_model',lambda:'fake')
    monkeypatch.setattr(script_cap,'from_args',lambda *args:SimpleNamespace(start=lambda:None))
    monkeypatch.setattr(change_review,'enabled',lambda:False)
    monkeypatch.setattr(diag,'record',lambda *args:None)
    monkeypatch.setattr(cli,'_scene_shots',lambda *args:[])
    monkeypatch.setattr(cli,'_floor_notes',lambda *args:[])
    monkeypatch.setattr(cli,'review_stage_round',lambda *args,**kwargs:None)
    monkeypatch.setattr(cli,'v2_main',lambda *args:pytest.fail('nhánh C không gọi renderer model thật'))
    monkeypatch.setattr(blockout_clay,'render_sheet',lambda *args,**kwargs:{'clay':False})
    out=tmp_path/'out'
    cli.v3_main(['--db',str(tmp_path/'fake.sqlite'),'--inputs',str(path),'--out',str(out),
                 '--stage-from',str(source),'--yes','--max-usd','1'])
    result=json.loads((out/'blockout_review.json').read_text(encoding='utf-8'))
    assert result['ok'] is ok and result['calls']==expected_calls and len(seen)==expected_calls
    assert seen[0]!=seen[1] and 'outside_floor' in seen[1]
    if expected_calls==3: assert seen[1]!=seen[2] and 'standing_blocked' in seen[2]
    assert events[2:]==['estimate','tag','call']*expected_calls
    assert (out/'r1'/'blockout.json').exists() is ok
@pytest.mark.parametrize('heading',[0,90,180,270])
def test_clay_sun_matches_topview_compass_heading(tmp_path,heading):
    import math
    from core import blockout_clay
    from tests.test_blockout import plan,box
    source=plan(box()); source['huong_sang']=heading
    config=blockout_clay.render_config(source,tmp_path)
    azimuth=math.radians(config['sky']['sun_azimuth'])
    compass=math.radians(heading)
    # Topview: 0 Bắc, 90 Đông; Nishita: 0 Đông, 90 Bắc.
    actual=(math.cos(azimuth),math.sin(azimuth))
    expected=(math.sin(compass),math.cos(compass))
    assert actual==pytest.approx(expected)
