import copy
import json
import os
from unittest.mock import patch
import pytest

P={'source':'human','by':'fixture','state':'USER_LOCKED'}

def profile():
    return {'schema_version':2,'revision':9,'approved':True,'face':{'text_en':'oval face','_p':P},'hair':{'text_en':'black bob','_p':P},'forms':[{'ma':'ghost_form','ten_en':'ghost form','applies_to':['KELLY'],'keeps':['face','hair'],'outfit_override':True,'image_ids':[9],'words_en':'translucent silhouette','_p':P}],'outfit':{'default':'everyday','sets':[{'id':'everyday','label':'Đồ thường','image_ids':[8],'items':[],'_p':P}]}}

@pytest.fixture
def adapter():
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        from core import kho_profile as k
        a={'id':1,'name':'KELLY','kind':'character','profile':json.dumps(profile()),'images':[{'id':9,'path':'ghost.png','status':'approved','role':'character_form'},{'id':8,'path':'outfit.png','status':'approved','role':'outfit'}]}
        with patch.object(k.assets,'project_assets',return_value=[a]), patch.object(k.assets,'get_profile',return_value=profile()), patch.object(k.assets,'link_characters',return_value={'KELLY':a}), patch.object(k.assets,'outfit_images',return_value=[]), patch.object(k.assets,'outfit_label',return_value=None):
            yield k,a

def test_form_and_outfit_precedence(adapter):
    k,a=adapter
    scene={'characters':['KELLY'],'byd':{'thanh_phan':[{'vat':'KELLY','dang':'ghost_form'}]}}
    f=k.forms_for_shot(None,1,scene)['KELLY']
    assert f['ma']=='ghost_form' and f['revision']==9 and f['image']['id']==9
    assert k.outfit_for(None,1,'KELLY',scene)['id']=='ghost_form'
    with patch.object(k.assets,'outfit_images',return_value=[{'id':12,'path':'project.png'}]):
        assert k.outfit_for(None,1,'KELLY',scene)['id']=='project'
    assert k.outfit_for(None,1,'KELLY')['id']=='everyday'

def test_multi_shot_does_not_spread_form(adapter):
    k,_=adapter
    rows=[{'data':{'characters':['KELLY'],'text':'ghost form'}},{'data':{'characters':['KELLY'],'text':'ordinary'}}]
    f=k.forms_for_rows(None,1,rows)['KELLY']
    assert f['shots']==[1] and f['all'] is False

def test_object_form_order_over_image_sort(adapter):
    k,a=adapter
    p=profile();p['forms'][0]['applies_to']=[]
    p['forms'].append(dict(p['forms'][0],ma='curved_deployed',ten_en='deployed',image_ids=[8]))
    a['profile']=json.dumps(p)
    assert k.selected_images(a)[0]['id']==9
    assert k.selected_images(a,{'text':'deployed'})[0]['id']==8

def test_unknown_dang_is_warning(adapter):
    k,_=adapter
    assert k.validate_dang(None,1,'KELLY','absent')[0]['muc']=='vang'


@pytest.fixture
def byd_conn():
    import sqlite3
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE asset_images(id INTEGER, asset_id INTEGER, status TEXT)')
    conn.executemany('INSERT INTO asset_images VALUES (?,1,?)',[(8,'approved'),(9,'approved')])
    yield conn
    conn.close()


@pytest.mark.parametrize('dang',['ghost_form',['ghost_form'],{'bat_dau':'ghost_form','ket_thuc':['ghost_form']}])
def test_byd_checks_declared_forms_with_project_context(adapter,byd_conn,dang):
    from core import shot_intent as s
    byd=s.empty(1);byd.update(byd_v=2,thanh_phan=[{'vat':'KELLY','vai':'chinh','vung':'giua','dang':dang}])
    issues = [i for i in s.assess(byd,byd_conn,project_id=1) if '.dang' in i['truong']]
    assert [i.get('ma') for i in issues] == (['dang_chua_chon_duoc'] if isinstance(dang,dict) else [])


def test_byd_unknown_form_reviews_at_exact_beat(adapter,byd_conn):
    # Rà 23/10: dạng ngoài forms Kho giữ REVIEW (trước đây WARN — hạ mức là lỗi VỪA 4).
    from core import shot_intent as s
    byd=s.empty(1);byd.update(byd_v=2,thanh_phan=[{'vat':'KELLY','vai':'chinh','vung':'giua','dang':{'bat_dau':'ghost_form','ket_thuc':['absent']}}])
    issues=[i for i in s.assess(byd,byd_conn,project_id=1) if i.get('ma')=='dang_khong_trong_kho']
    assert [(i['truong'],i['muc'],i['level']) for i in issues]==[('thanh_phan[0].dang.ket_thuc[0]','vang','REVIEW')]


def test_byd_missing_project_context_does_not_guess(adapter):
    from core import shot_intent as s
    byd=s.empty(1);byd.update(byd_v=2,thanh_phan=[{'vat':'KELLY','vai':'chinh','vung':'giua','dang':'ghost_form'}])
    issues=s.validate(byd)
    assert any(i.get('ma')=='dang_khong_kiem_duoc' for i in issues)


def test_director_threads_project_to_form_validation(adapter):
    from core import director_byd as d
    byd={'thanh_phan':[]}
    with patch.object(d.shot_intent,'validate',return_value=[]) as validate:
        assert d.problems({'byd':byd},None,project_id=17)==([],[])
    assert validate.call_args.kwargs=={'project_id':17}


def test_router_first_frame_uses_the_same_v2_form(adapter):
    from core import model_router
    _,asset=adapter
    scene={'characters':['KELLY'],'byd':{'thanh_phan':[{'vat':'KELLY','dang':'ghost_form'}]}}
    assert 'KELLY' in model_router.needs_first_frame(None,1,scene,chosen=[asset])


def test_single_form_list_selects_same_reference_as_scalar(adapter):
    k, _ = adapter
    scene = {'characters':['KELLY'],'byd':{'thanh_phan':[{'vat':'KELLY','dang':'ghost_form'}]}}
    scalar = k.forms_for_shot(None, 1, scene)
    scene['byd']['thanh_phan'][0]['dang'] = ['ghost_form']
    assert k.forms_for_shot(None, 1, scene) == scalar
    assert k.outfit_for(None, 1, 'KELLY', scene)['id'] == 'ghost_form'


@pytest.mark.parametrize('dang', [['ghost_form','ghost_form'], {'bat_dau':'ghost_form','ket_thuc':'ghost_form'}])
def test_non_scalar_form_selection_remains_visible_review(adapter, byd_conn, dang):
    k, _ = adapter
    from core import shot_intent as s
    byd = s.empty(1)
    byd.update(byd_v=2, thanh_phan=[{'vat':'KELLY','vai':'chinh','vung':'giua','dang':dang}])
    issues = s.assess(byd, byd_conn, project_id=1)
    assert any(i.get('ma') == 'dang_chua_chon_duoc' and i['muc'] == 'vang' and i['level'] == 'REVIEW' for i in issues)
    assert not k.forms_for_shot(byd_conn, 1, {'characters':['KELLY'],'byd':byd,'text':'ghost form'})


def test_declared_kho_id_mismatch_does_not_validate_another_asset(adapter, byd_conn):
    k, _ = adapter
    from core import shot_intent as s
    byd_conn.execute('CREATE TABLE assets(id INTEGER)')
    byd_conn.executemany('INSERT INTO assets VALUES (?)', [(1,), (2,)])
    byd = s.empty(1)
    byd.update(byd_v=2, thanh_phan=[{'vat':'KELLY','kho_id':2,'vai':'chinh','vung':'giua','dang':'ghost_form'}])
    with patch.object(k, 'read', side_effect=AssertionError('must not read another asset')):
        issues = s.assess(byd, byd_conn, project_id=1)
    assert any(i.get('ma') == 'dang_kho_khong_khop' and i['muc'] == 'vang' for i in issues)


def test_form_selector_rejects_declared_kho_id_mismatch(adapter):
    k, _ = adapter
    scene = {'characters':['KELLY'],'byd':{'thanh_phan':[{'vat':'KELLY','kho_id':2,'dang':'ghost_form'}]}}
    assert not k.forms_for_shot(None, 1, scene)


@pytest.mark.parametrize('source',['human','ai'])
def test_profile_level_provenance_does_not_require_field_state(adapter,source):
    k,_=adapter
    p=profile();meta={'source':source,'by':'fixture','at':'fixture-time'}
    if source=='ai':
        meta.update(model='fixture',from_text='fixture')
    p['_p']={'profile':meta}
    assert k.validate(p)
    if source=='ai':
        del meta['model']
        with pytest.raises(k.ProfileError):
            k.validate(p)
    p['_p']={'identity':{'source':'human'}}
    with pytest.raises(k.ProfileError):
        k.validate(p)


def test_v2_form_names_match_whole_words_and_exact_byd(adapter):
    k,asset=adapter
    p=profile();p['forms'][0].update(ma='ice',ten_en='ice')
    asset['profile']=json.dumps(p)
    with patch.object(k.assets,'get_profile',return_value=p):
        scene={'characters':['KELLY'],'text':'Alice changes her hair'}
        assert k.forms_for_shot(None,1,scene)=={}
        assert k.selected_images(asset,scene) is None
        scene['byd']={'thanh_phan':[{'vat':'KELLY','dang':'ice'}]}
        assert k.forms_for_shot(None,1,scene)['KELLY']['ma']=='ice'
        scene={'characters':['KELLY'],'text':'Kelly becomes ice.'}
        assert k.forms_for_shot(None,1,scene)['KELLY']['ma']=='ice'
        assert k.selected_images(asset,scene)[0]['id']==9
        p['forms'][0].update(ma='ghost_form',ten_en='ghost form',ten_vi='bóng mờ')
        scene['text']='Kelly thành bóng mờ.'
        assert k.forms_for_shot(None,1,scene)['KELLY']['ma']=='ghost_form'

@pytest.mark.parametrize('change',[{'forms':[{'ma':'Bad key'}]}, {'hair':{'_p':{'source':'ai','state':'AUTO'}}}, {'forms':{}}, {'outfit':{'default':'absent','sets':[]}}])
def test_invalid_schema_rejected(adapter,change):
    k,_=adapter
    p=profile();p.update(change)
    with pytest.raises(k.ProfileError):k.validate(p)

@pytest.fixture
def live_flow(tmp_path):
    with patch.object(os,'environ',{'ASSET_DIR':str(tmp_path/'assets'), 'FEATURE_SETTINGS_FILE':str(tmp_path/'features.json'),'PIPELINE_DATA':str(tmp_path/'projects'),'FEATURE_KHO_FORMS_V2':'1'}):
        from core import assets
        from core.db import connect
        from core.pipeline import Pipeline
        from PIL import Image
        import io
        p=Pipeline(connect())
        pid=p.create_project('fixture',game='FF')
        aid=assets.create(p.conn,'FF','character','KELLY')
        buf=io.BytesIO();Image.new('RGB',(64,96),'purple').save(buf,'PNG')
        assets.add_image(p.conn,aid,'face.png',buf.getvalue(),role='close_up')
        assets.add_image(p.conn,aid,'ghost.png',buf.getvalue(),role='character_form')
        assets.approve_images(p.conn,[i['id'] for i in assets.pending_images(p.conn)])
        assets.attach(p.conn,pid,aid)
        ids=[r['id'] for r in p.conn.execute('SELECT id FROM asset_images WHERE asset_id=? ORDER BY id',(aid,))]
        raw=profile();raw['face']['ref_image_ids']=[ids[0]];raw['forms'][0]['image_ids']=[ids[1]];raw['outfit']['sets'][0]['image_ids']=[ids[0]]
        p.conn.execute('UPDATE assets SET profile=? WHERE id=?',(json.dumps(raw),aid))
        p.conn.execute('INSERT INTO characters(project_id,name,ref_asset_id,description) VALUES(?,?,?,?)',(pid,'KELLY',aid,'fixture'))
        scene={'characters':['KELLY'],'text':'KELLY ghost form runs.','image_prompt':'KELLY ghost form runs.'}
        p.conn.execute('INSERT INTO scenes(project_id,idx,data) VALUES(?,1,?)',(pid,json.dumps(scene)))
        sid=p.conn.execute('SELECT id FROM scenes WHERE project_id=?',(pid,)).fetchone()['id']
        p.conn.commit()
        yield p,pid,aid,sid,scene
        p.conn.close()

def test_real_director_image_video_qc_read_same_revision(live_flow):
    from core import prompts, seedance_refs, kho_profile as k, qc_spec, lineage
    from core.runner import lock_note
    p,pid,aid,sid,scene=live_flow
    reads={};token=k._READS.set(reads)
    try:
        director=prompts.standard_block(p,pid)
        image=lock_note(p.conn,pid,['KELLY'],scene)
        refs=seedance_refs.identity_pictures(p.conn,pid,[{'id':sid,'data':scene}],8)
        qc=qc_spec.compile_frame(p.conn,pid,1,scene)
    finally:k._READS.reset(token)
    assert 'ghost_form' in director and 'black bob' in director
    assert 'ghost form' in image and 'black bob' in image
    assert any(n.endswith(seedance_refs.FORM_TAG) for n,path in refs)
    assert 'translucent silhouette' in json.dumps(qc)
    assert reads=={aid:9}
    old_hash=lineage.current_image_hash(p.conn,pid,sid)
    raw=profile();raw['forms'][0]['image_ids']=[];raw['outfit']['sets'][0]['image_ids']=[];raw['revision']=10
    p.conn.execute('UPDATE assets SET profile=? WHERE id=?',(json.dumps(raw),aid))
    assert lineage.current_image_hash(p.conn,pid,sid)!=old_hash

def test_autopilot_recognizes_profile_and_clone_shares_library(live_flow):
    from core import autopilot, compare, kho_profile as k, prompts
    p,pid,aid,sid,scene=live_flow
    assert autopilot.bible_gaps(p,pid)=={'no_lock':[],'no_picture':[]}
    clone=compare.clone_project(p,pid,'fixture clone')
    assert k.for_character(p.conn,clone,'KELLY')['kho_id']==aid
    assert k.for_character(p.conn,clone,'KELLY')['revision']==9
    # Director chạy lại đọc cùng Kho; clone không tạo bản sao hồ sơ.
    assert prompts.standard_block(p,clone)==prompts.standard_block(p,pid)
    assert p.conn.execute('SELECT count(*) FROM assets').fetchone()[0]==1

def test_profile_digest_does_not_persist_adapter_view(live_flow):
    from core import profile_digest
    p,pid,aid,_,_=live_flow
    before=p.conn.execute('SELECT profile FROM assets WHERE id=?',(aid,)).fetchone()['profile']
    profile_digest.refresh(p.conn,aid)
    after=p.conn.execute('SELECT profile FROM assets WHERE id=?',(aid,)).fetchone()['profile']
    assert after==before

@pytest.mark.parametrize('mode',[None,'per_shot','multishot'])
def test_image_prepare_and_sent_package_capture_revision(live_flow,tmp_path,mode):
    from core import runner, kho_profile as k
    p,pid,aid,sid,scene=live_flow
    p.conn.execute('UPDATE projects SET shot_mode=? WHERE id=?',(mode,pid))
    class Provider:
        name='fixture';supports_aspect=True;supports_model=False
        def submit(self,prompt,references,**kwargs):
            raise AssertionError('Không được gọi provider trong test 0 USD')
    image=runner.ImageRunner(p,Provider(),str(tmp_path))
    job={'id':99,'project_id':pid,'scene_id':sid,'retry_reason':None}
    args=image._submit_args(job)
    assert args and 'ghost form' in args[0]
    kwargs=image._prepare_kwargs(job)
    package,warnings=image._build_package(job,args,kwargs,kwargs,'fixture')
    payload=json.loads(package)
    assert payload['kho_profiles']==[{'kho_id':aid,'revision':9}]
    assert not warnings

@pytest.mark.parametrize('multi',[False,True])
def test_video_prepare_and_sent_package_capture_revision(live_flow,tmp_path,multi):
    from core import runner, seedance_refs
    from PIL import Image
    p,pid,aid,sid,scene=live_flow
    p.conn.execute('UPDATE projects SET shot_mode=?,video_model=? WHERE id=?',('multishot' if multi else 'per_shot','seedance',pid))
    scene.update(shot_no=1,story_scene=1,duration_s=4)
    p.conn.execute('UPDATE scenes SET data=? WHERE id=?',(json.dumps(scene),sid))
    rows=[{'id':sid,'idx':1,'data':scene}]
    if multi:
        second=dict(scene,shot_no=2)
        p.conn.execute('INSERT INTO scenes(project_id,idx,data) VALUES(?,2,?)',(pid,json.dumps(second)))
        sid2=p.conn.execute('SELECT max(id) FROM scenes').fetchone()[0]
        rows.append({'id':sid2,'idx':2,'data':second})
    folder=tmp_path/str(pid)/'images';folder.mkdir(parents=True)
    for i,r in enumerate(rows,1):
        p.conn.execute("INSERT INTO motion_prompts(scene_id,motion_prompt,negative_prompt,duration_sec,state) VALUES(?,?,?,4,'approved')",(r['id'],'KELLY in ghost form runs.',''))
        p.conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,created_at,updated_at) VALUES(?,?,?,'image_gen','approved','fixture','fixture')",(i,pid,r['id']))
        Image.new('RGB',(640,960),'purple').save(folder/f'job_{i}.png')
    p.conn.commit()
    class Provider:
        name='fixture';supports_aspect=True;supports_subjects=False
        def submit(self,*args,**kwargs):raise AssertionError('Không gọi provider')
    video=runner.VideoRunner(p,Provider(),str(tmp_path))
    job={'id':99,'project_id':pid,'scene_id':sid,'retry_reason':None}
    with patch.object(video,'_choice',return_value={'model':'seedance'}), patch.object(video,'_refs',return_value=True), patch.object(video,'_sends_group',return_value=rows if multi else None), patch.object(seedance_refs,'PAD_DIR',str(tmp_path/'padding')), patch.object(seedance_refs,'mark',side_effect=lambda path,*a,**kw:path):
        args=video._submit_args(job)
        kwargs=video._prepare_kwargs(job)
        sent={key:value for key,value in kwargs.items() if not key.startswith('_')}
        package,warnings=video._build_package(job,args,kwargs,sent,'fixture')
    assert not warnings
    payload=json.loads(package)
    assert payload['kho_profiles']==[{'kho_id':aid,'revision':9}]
    assert 'ghost form' in payload['prompt']
    assert any(ref['param']=='reference_only' for ref in payload['refs'])

def test_v1_on_and_off_produce_identical_prompts_and_refs(live_flow):
    from core import prompts,seedance_refs
    from core.runner import lock_note
    p,pid,aid,sid,scene=live_flow
    raw={'approved':True,'identity':'oval face, black bob','must_keep':'oval face; black bob; yellow jacket','forbidden':'red hair','height_m':1.7}
    p.conn.execute('UPDATE assets SET profile=? WHERE id=?',(json.dumps(raw),aid))
    def outputs():
        return (prompts.standard_block(p,pid), prompts.lock_text(p.conn,pid,['KELLY'],shots=[scene]),lock_note(p.conn,pid,['KELLY'],scene),seedance_refs.identity_pictures(p.conn,pid,[{'id':sid,'data':scene}],8))
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'0','ASSET_DIR':os.environ.get('ASSET_DIR'),'PIPELINE_DATA':os.environ.get('PIPELINE_DATA')}):
        off=outputs()
    assert outputs()==off


def test_v1_package_does_not_add_empty_provenance(live_flow,tmp_path):
    from core import runner
    p,pid,aid,sid,scene=live_flow
    p.conn.execute('UPDATE assets SET profile=? WHERE id=?',(json.dumps({'approved':True,'must_keep':'black bob'}),aid))
    class Provider:
        name='fixture'
        def submit(self,prompt,references,**kwargs):raise AssertionError('Không gọi provider')
    image=runner.ImageRunner(p,Provider(),str(tmp_path))
    job={'id':99,'project_id':pid,'scene_id':sid,'retry_reason':None}
    args=image._submit_args(job)
    package,warnings=image._build_package(job,args,{}, {},'fixture')
    assert not warnings
    assert 'kho_profiles' not in json.loads(package)


# ---- CX21-M23 vòng sửa sau rà kỹ 23/10 ----

def test_m23fix1_broken_v2_profile_falls_back_to_old_selector(adapter, caplog):
    k, a = adapter
    from core import assets
    p = profile(); p['forms'][0]['ma'] = 'Bad!'
    a['profile'] = json.dumps(p)
    front = {'id': 7, 'path': 'front.png', 'status': 'approved', 'role': 'front_standard'}
    a['images'].append(front)
    with patch.object(assets, '_shape', return_value=None), caplog.at_level('WARNING'):
        assert k.selected_images(a) is None
        assert assets.best_references(a, 1, {'characters': ['KELLY']}, 'KELLY')[0]['id'] == 7
        assert assets.view_picture(a, 'front_standard')['id'] == 7
        assert assets.standard_set(a, False) == [(front, 'character')]
    assert 'hồ sơ v2 hỏng' in caplog.text


def test_m23fix2_view_picture_never_returns_other_role(adapter):
    k, a = adapter
    from core import assets
    p = profile(); p['face']['ref_image_ids'] = [9]
    a['profile'] = json.dumps(p)
    assert k.selected_images(a)[0]['id'] == 9
    assert assets.view_picture(a, 'back') is None
    assert assets.view_picture(a, 'character_form')['id'] == 9


def test_m23fix3_selected_images_follows_byd_like_forms_for_shot(adapter):
    k, a = adapter
    text = 'Kelly in normal suit then turns ghost form'
    multi = {'characters': ['KELLY'], 'text': text, 'byd': {'thanh_phan': [{'vat': 'KELLY', 'dang': ['normal_suit', 'ghost_form']}]}}
    assert not k.forms_for_shot(None, 1, multi)
    assert k.selected_images(a, multi, 'KELLY') is None
    normal = {'characters': ['KELLY'], 'text': text, 'byd': {'thanh_phan': [{'vat': 'KELLY', 'dang': 'normal_suit'}]}}
    assert not k.forms_for_shot(None, 1, normal)
    assert k.selected_images(a, normal, 'KELLY') is None
    # BYĐ chốt dạng mà chữ không nhắc: cả hai đường cùng lấy dạng đó.
    byd = {'characters': ['KELLY'], 'text': 'Kelly runs', 'byd': {'thanh_phan': [{'vat': 'KELLY', 'dang': 'ghost_form'}]}}
    assert k.forms_for_shot(None, 1, byd)['KELLY']['ma'] == 'ghost_form'
    assert [i['id'] for i in k.selected_images(a, byd, 'KELLY')] == [9]


def test_m23fix3_two_forms_named_in_text_are_not_auto_picked(adapter):
    k, a = adapter
    p = profile()
    p['forms'].append(dict(p['forms'][0], ma='normal_suit', ten_en='normal suit', image_ids=[8]))
    a['profile'] = json.dumps(p)
    scene = {'characters': ['KELLY'], 'text': 'Kelly in normal suit then turns ghost form'}
    with patch.object(k.assets, 'get_profile', return_value=p):
        assert not k.forms_for_shot(None, 1, scene)
    assert k.selected_images(a, scene, 'KELLY') is None


def test_m23fix4_unchecked_and_out_of_enum_forms_stay_review(adapter, byd_conn):
    from core import shot_intent as s
    byd = s.empty(1); byd.update(byd_v=2, thanh_phan=[{'vat': 'KELLY', 'vai': 'chinh', 'vung': 'giua', 'dang': 'ghost_form'}])
    unchecked = [i for i in s.assess(byd) if i.get('ma') == 'dang_khong_kiem_duoc']
    assert unchecked and all(i['level'] == 'REVIEW' for i in unchecked)
    byd['thanh_phan'][0]['dang'] = 'absent'
    outside = [i for i in s.assess(byd, byd_conn, project_id=1) if i.get('ma') == 'dang_khong_trong_kho']
    assert outside and all(i['level'] == 'REVIEW' for i in outside)


def test_m23fix4_flag_off_keeps_m21_review_without_kho_check():
    with patch.object(os, 'environ', {}):
        from core import shot_intent as s
        byd = s.empty(1); byd.update(byd_v=2, thanh_phan=[{'vat': 'KELLY', 'vai': 'chinh', 'vung': 'giua', 'dang': 'ghost_form'}])
        issues = [i for i in s.assess(byd) if '.dang' in i.get('truong', '')]
        assert [(i.get('ma'), i['level']) for i in issues] == [(None, 'REVIEW')]
