import os
import sqlite3
from unittest.mock import patch
import pytest

@pytest.fixture
def db():
    with patch.object(os, 'environ', {}):
        c = sqlite3.connect(':memory:')
        c.row_factory = sqlite3.Row
        c.executescript('CREATE TABLE assets(id INTEGER PRIMARY KEY, name TEXT, profile TEXT); CREATE TABLE asset_images(id INTEGER PRIMARY KEY, asset_id INTEGER, path TEXT, status TEXT); CREATE TABLE audit_log(id INTEGER PRIMARY KEY, at TEXT, email TEXT, action TEXT, detail TEXT);')
        c.execute("INSERT INTO assets VALUES(1,'Kelly','{}')")
        yield c

def test_missing_fields_are_not_invented(db):
    from core import kho_profile as k
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        p = k.read(db, 1)
        assert p['hair'] is None and p['face'] is None
        assert p['gaps']

def test_ai_cannot_overwrite_and_revision_cas(db):
    from core import kho_profile as k
    human = {'kind':'human', 'who':'fixture'}
    ai = {'kind':'ai', 'who':'fixture-model', 'model':'fixture', 'from_text':'fixture'}
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        k.save(db, 1, {'hair':{'text_en':'black bob'}}, human, 0)
        p = k.save(db, 1, {'hair':{'text_en':'blonde'}}, ai, 1)
        assert p['hair']['text_en'] == 'black bob'
        assert p['proposals']['hair']['text_en'] == 'blonde'
        with pytest.raises(k.ProfileError):
            k.save(db, 1, {}, human, 0)

def test_approved_image_beats_ai_text(db):
    from core import kho_profile as k
    p = {'schema_version':2, 'hair':{'text_en':'blonde', 'ref_image_ids':[7], '_p':{'source':'ai','model':'fixture','from_text':'fixture','state':'REVIEW_REQUIRED'}}}
    db.execute("INSERT INTO asset_images VALUES(7,1,'fixture.png','approved')")
    import json
    db.execute('UPDATE assets SET profile=?', (json.dumps(p),))
    with patch.object(os, 'environ', {'FEATURE_KHO_FORMS_V2':'1'}):
        read = k.read(db, 1)
        assert 'blonde' not in k.lock_text_en(read)
        assert read['hair']['_p']['state'] == 'REVIEW_REQUIRED'

def test_nested_human_form_cannot_be_replaced_by_ai(db):
    from core import kho_profile as k
    form={'ma':'ghost_form','ten_en':'ghost form','image_ids':[]}
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        first=k.save(db,1,{'forms':[form]}, {'kind':'human','who':'fixture'},0)
        second=k.save(db,1,{'forms':[]},{'kind':'ai','who':'fixture','model':'fixture','from_text':'fixture'},1)
        assert second['forms']==first['forms'] and second['approved'] is True
        assert second['proposals']['forms']==[]

def test_malformed_v2_is_reported_and_not_approved(db):
    from core import kho_profile as k
    db.execute('UPDATE assets SET profile=?', ('{"schema_version":2,"approved":true,"outfit":{"sets":["bad"]}}',))
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        p=k.read(db,1)
        assert p['approved'] is False and p['gaps'] and p['forms']==[]

def test_capture_records_revision_read_not_later_revision(db):
    from core import kho_profile as k
    import json
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
        class Builder:
            @k.capture_inputs
            def _submit_args(self, job):
                return k.read(db,1)['hair']['text_en']
        runner=Builder();job={'id':7}
        assert runner._submit_args(job)=='black bob'
        k.save(db,1,{'hair':{'text_en':'short black bob'}},{'kind':'human','who':'fixture'},1)
        assert k.package_inputs(runner,job)==[{'kho_id':1,'revision':1}]

def test_off_preserves_v2_and_legacy_v1_writer(db):
    from core import assets, kho_profile as k
    with patch.object(os,'environ',{}):
        db.execute('ALTER TABLE assets ADD COLUMN kind TEXT')
        p=assets.set_profile(db,1,{'identity':'fixture'},False)
        assert 'schema_version' not in p and p['identity']=='fixture'
        first=k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
        raw=db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]
        with pytest.raises(assets.AssetError):
            assets.set_profile(db,1,{'identity':'replacement'},False)
        assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]==raw
        saved=assets.set_profile(db,1,{'identity':'updated'},False,actor={'kind':'human','who':'fixture'},expected_revision=1)
        assert saved['hair']==first['hair'] and saved['schema_version']==2 and saved['revision']==2
        with pytest.raises(k.ProfileError):
            assets.set_profile(db,1,{},False,actor={'kind':'human','who':'fixture'},expected_revision=1)


def test_ai_locked_noop_preserves_provenance_and_approval(db):
    from core import kho_profile as k
    human={'kind':'human','who':'fixture'}
    ai={'kind':'ai','who':'fixture-ai','model':'fixture','from_text':'fixture'}
    first=k.save(db,1,{'hair':{'text_en':'black bob'},'identity':'Kelly'},human,0)
    second=k.save(db,1,{'hair':first['hair'],'identity':'Kelly'},ai,1)
    assert second['hair']==first['hair'] and second['_p']==first['_p']
    assert second['approved'] is True
    third=k.save(db,1,{'hair':{'text_en':'blonde'}},ai,2)
    assert third['hair']==first['hair'] and third['proposals']['hair']['text_en']=='blonde'


def test_save_outfit_preserves_untouched_ai_set_provenance(db):
    from core import assets, kho_profile as k
    ai={'kind':'ai','who':'fixture-ai','model':'fixture','from_text':'fixture'}
    first=k.save(db,1,{'outfit':{'sets':[{'id':'draft','items':[],'image_ids':[]}]}},ai,0)
    db.execute("INSERT INTO asset_images VALUES(7,1,'fixture.png','approved')")
    with patch.object(assets,'link_characters',return_value={'Kelly':{'id':1}}), patch.object(assets,'outfit_images',return_value=[{'id':7}]), patch.object(assets,'outfit_label',return_value='fixture'):
        assert k.save_outfit_to_kho(db,9,'Kelly',{'kind':'human','who':'fixture'})=='project_9'
    saved=assets.get_profile(db,1)
    assert saved['outfit']['sets'][0]==first['outfit']['sets'][0]
    assert saved['outfit']['sets'][1]['_p']['state']=='USER_LOCKED'
    assert saved['approved'] is False


def test_save_keeps_outer_transaction_rollback_atomic(db):
    from core import kho_profile as k
    db.commit()
    db.execute('BEGIN')
    k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
    db.rollback()
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]=='{}'
    assert db.execute('SELECT count(*) FROM audit_log').fetchone()[0]==0


@pytest.mark.parametrize('actor,revision', [(None,0), ({'kind':'human','who':'fixture'},True)])
def test_invalid_writer_inputs_raise_profile_error_without_write(db, actor, revision):
    from core import kho_profile as k
    with pytest.raises(k.ProfileError):
        k.save(db,1,{},actor,revision)
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]=='{}'


def test_audit_failure_rolls_back_profile_and_preserves_outer_work(db):
    from core import kho_profile as k
    db.commit()
    db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON audit_log BEGIN SELECT RAISE(ABORT,'fixture audit failure'); END")
    db.execute("UPDATE assets SET name='Outer change' WHERE id=1")
    with pytest.raises(k.ProfileError,match='audit'):
        k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
    row=db.execute('SELECT name,profile FROM assets WHERE id=1').fetchone()
    assert tuple(row)==('Outer change','{}')
    assert db.execute('SELECT count(*) FROM audit_log').fetchone()[0]==0


def test_audit_contains_only_metadata_and_hashes(db):
    from core import kho_profile as k
    import json
    k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
    row=db.execute('SELECT email,action,detail FROM audit_log').fetchone()
    assert tuple(row[:2])==('fixture','kho_profile')
    detail=json.loads(row['detail'])
    assert set(detail)=={'kho_id','actor_kind','before_revision','revision','changed_keys','before_hash','after_hash'}
    assert detail['changed_keys']==['hair'] and detail['before_revision']==0 and detail['revision']==1
    assert len(detail['before_hash'])==len(detail['after_hash'])==64


@pytest.mark.parametrize('enabled,identity,dbrole,active,clicked,expected', [
    (False,{'email':'owner.fixture','role':'owner'},'owner',1,True,False),
    (True,{},'owner',1,True,False),
    (True,{'email':'owner.fixture','role':'member'},'owner',1,True,False),
    (True,{'email':'owner.fixture','role':'owner'},'owner',0,True,False),
    (True,{'email':'owner.fixture','role':'owner'},'member',1,True,False),
    (True,{'email':'owner.fixture','role':'owner'},None,1,True,False),
    (True,{'email':'owner.fixture','role':'owner'},'owner',1,False,False),
    (True,{'email':'owner.fixture','role':'owner'},'owner',1,True,True),
])
def test_outfit_ui_owner_guard_fake_ui(db,enabled,identity,dbrole,active,clicked,expected):
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    from unittest.mock import Mock
    from core import kho_profile as k
    db.execute('CREATE TABLE users(email TEXT,role TEXT,active INTEGER)')
    if dbrole is not None:
        db.execute('INSERT INTO users VALUES(?,?,?)',('owner.fixture',dbrole,active))
    # Thực thi đúng helper UI đã lưu, không import Dashboard/common hay mở phiên thật.
    tree=ast.parse(Path('dashboard/steps/step1_characters.py').read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_outfit_to_kho_button')
    scope={'C':SimpleNamespace(me=lambda:identity),'kho_profile':k}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixture-ui>','exec'),scope)
    box=Mock();box.button.return_value=clicked
    with patch.object(k,'enabled',return_value=enabled),patch.object(k,'save_outfit_to_kho') as save:
        scope['_outfit_to_kho_button'](SimpleNamespace(conn=db),9,'Kelly',box)
        assert save.called is expected
        if expected:
            assert save.call_args.args[1:]==(9,'Kelly',{'kind':'human','who':'owner.fixture'})
    if not enabled or not identity or identity.get('role') != 'owner':
        box.button.assert_not_called()


def test_outfit_from_other_asset_rejected_without_write(db):
    from core import assets, kho_profile as k
    db.execute("INSERT INTO asset_images VALUES(7,2,'fixture.png','approved')")
    with patch.object(assets,'link_characters',return_value={'Kelly':{'id':1}}),patch.object(assets,'outfit_images',return_value=[{'id':7}]):
        with pytest.raises(k.ProfileError,match='thuộc mục Kho khác'):
            k.save_outfit_to_kho(db,9,'Kelly',{'kind':'human','who':'fixture'})
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]=='{}'


@pytest.mark.parametrize('srcversion,dstversion,srcapproved,dstapproved',[(2,2,True,True),(2,2,False,True),(2,2,True,False),(2,1,False,True),(1,2,False,True)])
def test_merge_refuses_different_v2_fields_before_filesystem(db,srcversion,dstversion,srcapproved,dstapproved):
    from core import assets
    import json
    db.execute('ALTER TABLE asset_images ADD COLUMN sort INTEGER')
    db.execute("INSERT INTO assets VALUES(2,'Kelly alt','{}')")
    for aid,text,version,approved in [(1,'black bob',dstversion,dstapproved),(2,'blonde',srcversion,srcapproved)]:
        db.execute('UPDATE assets SET profile=? WHERE id=?',(json.dumps({'schema_version':version,'revision':1,'approved':approved,'hair':{'text_en':text}}),aid))
    snapshots=[tuple(r) for r in db.execute('SELECT id,profile FROM assets ORDER BY id')]
    with patch.object(assets,'get',side_effect=lambda c,i:{'id':i,'name':'fixture','aliases':''}),patch.object(assets,'_count',return_value=0),patch.object(assets,'root',side_effect=AssertionError('Không được chạm filesystem')):
        with pytest.raises(assets.AssetError,match='khác nhau'):
            assets.merge(db,2,1)
    assert [tuple(r) for r in db.execute('SELECT id,profile FROM assets ORDER BY id')]==snapshots


def test_diagnostic_and_review_prompt_use_structured_lock(db):
    from core import kho_profile as k, before_run, change_review
    import json
    db.executescript("ALTER TABLE assets ADD COLUMN kind TEXT DEFAULT 'character'; ALTER TABLE assets ADD COLUMN aliases TEXT DEFAULT ''; ALTER TABLE assets ADD COLUMN description TEXT DEFAULT ''; CREATE TABLE project_assets(project_id INTEGER,asset_id INTEGER); INSERT INTO project_assets VALUES(9,1); CREATE TABLE scenes(id INTEGER,idx INTEGER,data TEXT);")
    data={'characters':['Kelly']}
    db.execute('INSERT INTO scenes VALUES(1,1,?)',(json.dumps(data),))
    k.save(db,1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        items=before_run._input_items(db,9,[{'id':1,'idx':1,'data':data}])
        assert not any('must_keep' in item['text'] for item in items)
        text=change_review.build_prompt(db,{'before':'{}','after':'{}','id':1,'kind':'scene','scene_id':1},[],[1],[])
        assert 'must_keep = black bob' in text


def test_digest_off_does_not_write_existing_v2_without_revision(db):
    from core import kho_profile as k, profile_digest
    k.save(db,1,{'identity':'fixture'},{'kind':'human','who':'fixture'},0)
    raw=db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]
    profile_digest.refresh(db,1)
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]==raw


def test_review_v2_unapproved_lock_never_falls_back_to_description(db):
    from core import kho_profile as k, change_review
    import json
    db.executescript("ALTER TABLE assets ADD COLUMN description TEXT DEFAULT 'blonde outfit'; CREATE TABLE scenes(id INTEGER,idx INTEGER,data TEXT);")
    db.execute('INSERT INTO scenes VALUES(1,1,?)',(json.dumps({'characters':['Kelly']}),))
    k.save(db,1,{'hair':{'text_en':'blonde'}},{'kind':'ai','who':'fixture-ai','model':'fixture','from_text':'fixture'},0)
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        text=change_review.build_prompt(db,{'before':'{}','after':'{}','id':1,'kind':'scene','scene_id':1},[],[1],[])
        assert 'blonde outfit' not in text
        assert 'hồ sơ v2 chưa có khóa đã duyệt' in text


@pytest.mark.parametrize('profile',[
    {'schema_version':2.0},
    {'schema_version':2,'_p':[]},
    {'schema_version':2,'_p':{'identity':{'source':'ai','state':'REVIEW_REQUIRED'}}},
    {'schema_version':2,'outfit':{'sets':[{'id':'one','items':'invalid','_p':{'source':'human','state':'USER_LOCKED'}}]}},
])
def test_nested_schema_and_scalar_provenance_rejected(db,profile):
    from core import kho_profile as k
    with pytest.raises(k.ProfileError):
        k.validate(profile,db,1)


@pytest.mark.parametrize('raw',['[]','{bad'])
def test_writer_malformed_source_reports_profile_error_without_write(db,raw):
    from core import kho_profile as k
    db.execute('UPDATE assets SET profile=? WHERE id=1',(raw,))
    with pytest.raises(k.ProfileError):
        k.save(db,1,{}, {'kind':'human','who':'fixture'},0)
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]==raw


def test_failed_compare_and_swap_never_creates_audit(db):
    from core import kho_profile as k
    from types import SimpleNamespace
    class Conflict:
        def execute(self,sql,args=()):
            if sql.startswith('UPDATE assets SET profile='):
                return SimpleNamespace(rowcount=0)
            return db.execute(sql,args)
    with pytest.raises(k.ProfileError,match='revision'):
        k.save(Conflict(),1,{'hair':{'text_en':'black bob'}},{'kind':'human','who':'fixture'},0)
    assert db.execute('SELECT profile FROM assets WHERE id=1').fetchone()[0]=='{}'
    assert db.execute('SELECT count(*) FROM audit_log').fetchone()[0]==0


def test_revision_change_between_prepare_phases_is_blocked(db):
    from core import kho_profile as k
    human={'kind':'human','who':'fixture'}
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        k.save(db,1,{'hair':{'text_en':'black bob'}},human,0)
        class Builder:
            @k.capture_inputs
            def _submit_args(self,job):
                return k.read(db,1)
            @k.capture_inputs
            def _prepare_kwargs(self,job):
                return k.read(db,1)
        runner=Builder();job={'id':8}
        runner._submit_args(job)
        k.save(db,1,{'hair':{'text_en':'long black hair'}},human,1)
        with pytest.raises(k.ProfileError,match='đổi trong khi dựng gói'):
            runner._prepare_kwargs(job)


def test_ai_scalar_profile_stays_unapproved(db):
    from core import kho_profile as k
    saved=k.save(db,1,{'identity':'fixture','must_keep':'fixture'},{'kind':'ai','who':'fixture-ai','model':'fixture','from_text':'fixture'},0)
    assert saved['approved'] is False
    assert all(meta['state']=='REVIEW_REQUIRED' for meta in saved['_p'].values())


def test_unreviewed_forms_and_outfit_are_not_selected_as_standard(db):
    from core import kho_profile as k, assets
    import json
    db.execute("INSERT INTO asset_images VALUES(7,1,'fixture.png','approved')")
    saved=k.save(db,1,{'forms':[{'ma':'ghost','ten_en':'ghost','applies_to':['Kelly'],'image_ids':[7]}],
                       'outfit':{'default':'draft','sets':[{'id':'draft','image_ids':[7],'items':[]}]}},
                 {'kind':'ai','who':'fixture-ai','model':'fixture','from_text':'fixture'},0)
    asset={'id':1,'name':'Kelly','profile':json.dumps(saved),'images':[{'id':7,'status':'approved','path':'fixture.png'}]}
    scene={'characters':['Kelly'],'text':'ghost'}
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}),patch.object(k.character_forms,'for_shot',return_value={}),patch.object(assets,'link_characters',return_value={'Kelly':asset}),patch.object(assets,'outfit_images',return_value=[]):
        assert k.forms_for_shot(db,9,scene,[asset])=={}
        assert k.outfit_for(db,9,'Kelly') is None
        assert k.selected_images(asset,scene) is None
