"""Đ18.4c dry-run offline trên nguồn chỉ định, không DB/provider/env thật."""
import importlib
import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch
import pytest

@pytest.fixture(autouse=True)
def isolated():
    with patch.object(os,'environ',{}): yield

def mod():return importlib.import_module('core.stage_registry_import')
def write(root,name,value):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False).encode('utf-8');p.write_bytes(raw);return raw

@pytest.fixture
def source(tmp_path):
    raw=write(tmp_path,'stage_v2_1/stage.json',{'id':'fake-stage','units':'m','round':'round1','objects':[{'id':'fake-actor','kind':'actor','actor_id':123,'pose':'lying','relation':{'in':'well'},'unknown':{'keep':42}}],'_user_locked':{'objects':'manual'},'unknown_root':[1,2,3]})
    write(tmp_path,'stage_v2_1/blocking.json',{'states':[{'id':'end','beat':'dinh','objects':[{'id':'fake-actor','pose':'lying','hidden':False,'in':'well'}]}]})
    write(tmp_path,'stage_v2_1/shot_specs.json',{'shots':[{'scene_id':456,'subject':{'id':'fake-actor'},'end_actor':{'pose':'lying'},'state':'end','move':{'end_location':[1,2,3]},'POV':'fake-actor','spec_override':{'unknown':'raw'}}]})
    write(tmp_path,'scene.json',{'scene_id':456,'approved':True,'approval_history':[{'status':'approved','take':7}],'data':{'stage_camera':{'move':'pull_out'},'_user_locked':{'blocking':True}}})
    write(tmp_path,'approvals.json',{'approved_round':'round1','history':[{'revision':1,'approved':True}]})
    m=mod();specs=[m.SourceSpec('stage','stage-source','stage_v2_1/stage.json','round1'),m.SourceSpec('blocking','blocking-source','stage_v2_1/blocking.json','round1'),m.SourceSpec('shot_specs','shot-source','stage_v2_1/shot_specs.json','round1'),m.SourceSpec('scene_data','scene-source','scene.json'),m.SourceSpec('approvals','approval-source','approvals.json')]
    return m,tmp_path,specs,raw

@pytest.mark.parametrize('pid',[24,27])
def test_fake_history_raw_immutable_idempotent(source,pid):
    m,root,specs,raw=source;a=m.dry_run(root,pid,specs);b=m.dry_run(root,pid,list(reversed(specs)))
    assert a==b;assert a.status=='PARTIAL';assert not a.ready_for_apply
    entry=next(x for x in a.sources if x.kind=='stage');assert entry.raw_bytes==raw
    assert json.loads(entry.raw_bytes)['objects'][0]['relation']=={'in':'well'}
    assert json.loads(entry.raw_bytes)['unknown_root']==[1,2,3]
    with pytest.raises(FrozenInstanceError):entry.raw_bytes=b'changed'
    shot=next(x for x in a.sources if x.kind=='shot_specs')
    assert json.loads(shot.raw_bytes)['shots'][0]['subject']['id']=='fake-actor'
    assert json.loads(shot.raw_bytes)['shots'][0]['end_actor']['pose']=='lying'
    assert any(x.code=='conversion_pending' for x in a.issues)
    assert all(x.source_hash and x.migration_version==1 and x.proposed_revision==1 for x in a.mappings)

def test_changed_source_changes_mapping_not_source(source):
    m,root,specs,raw=source;a=m.dry_run(root,24,specs)
    path=root/'stage_v2_1/stage.json';new=raw+b' ';path.write_bytes(new)
    b=m.dry_run(root,24,specs)
    assert a.inventory_hash!=b.inventory_hash
    am=next(x for x in a.mappings if x.kind=='stage');bm=next(x for x in b.mappings if x.kind=='stage')
    assert am.candidate_id!=bm.candidate_id
    assert path.read_bytes()==new

def test_restore_raw_bytes_proof_without_io(source):
    m,root,specs,raw=source;report=m.dry_run(root,27,specs)
    entries=m.restore_payloads(report)
    assert dict(entries)['stage_v2_1/stage.json']==raw
    assert all((root/path).read_bytes()==content for path,content in entries)

@pytest.mark.parametrize('bad',['../escape.json','/absolute.json','C:/fake.json','folder/../stage.json','folder\\stage.json'])
def test_escape_rejected(tmp_path,bad):
    m=mod()
    with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake',bad)])

def test_symlink_rejected(tmp_path):
    m=mod();target=tmp_path/'real.json';target.write_bytes(b'{}');link=tmp_path/'link.json'
    try:link.symlink_to(target)
    except OSError:pytest.skip('Symlink privilege unavailable')
    with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','link.json')])

def test_binary_bytes_preserved(tmp_path):
    m=mod();raw=b'\x00\xff\xfeRAW';(tmp_path/'reference.bin').write_bytes(raw)
    report=m.dry_run(tmp_path,27,[m.SourceSpec('binary','fake','reference.bin')])
    assert report.sources[0].raw_bytes==raw
    assert m.restore_payloads(report)==(('reference.bin',raw),)

@pytest.mark.parametrize('payload,code',[({'objects':[{'kind':'actor'}]},'missing_units'),({'units':'m','objects':[{'kind':'actor'}]},'missing_actor_id'),({'units':'m','objects':[{'kind':'actor','actor_id':123,'look_id':99}]},'look_domain_pending')])
def test_missing_domain_unresolved_no_guess(tmp_path,payload,code):
    m=mod();write(tmp_path,'stage.json',payload);r=m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])
    assert code in {x.code for x in r.issues};assert not r.ready_for_apply

def test_multiple_rounds_not_latest(tmp_path):
    m=mod();write(tmp_path,'one.json',{'id':'one','units':'m'});write(tmp_path,'two.json',{'id':'two','units':'m'})
    r=m.dry_run(tmp_path,24,[m.SourceSpec('stage','one','one.json','r1'),m.SourceSpec('stage','two','two.json','r2')])
    assert any(x.code=='approved_round_ambiguous' and x.severity=='conflict' for x in r.issues)

@pytest.mark.parametrize('limit,payload',[('max_file_bytes',{'id':'big','unknown':'x'*100}),('max_depth',{'a':{'b':{'c':1}}}),('max_nodes',{'a':[1,2,3,4,5]}),('max_total_bytes',{'id':'big','unknown':'x'*100})])
def test_budget_fail_closed(tmp_path,limit,payload):
    m=mod();write(tmp_path,'stage.json',payload)
    with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')],**{limit:2})

def test_text_blocking_unresolved(tmp_path):
    m=mod();write(tmp_path,'blocking.json',{'blocking':'fake legacy text','unknown':1})
    report=m.dry_run(tmp_path,27,[m.SourceSpec('blocking','fake','blocking.json')])
    assert 'textual_blocking' in {x.code for x in report.issues}

def test_import_no_store_dependency_or_db_io(tmp_path):
    m=mod();assert not hasattr(m,'StageRegistryStore');assert not hasattr(m,'apply')
    write(tmp_path,'stage.json',{'id':'fake','units':'m'})
    with patch('sqlite3.connect',side_effect=AssertionError('DB forbidden')):
        assert m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')]).status=='PARTIAL'

def test_restore_copy_byte_for_byte(source,tmp_path):
    m,root,specs,raw=source;report=m.dry_run(root,24,specs)
    copy_root=tmp_path/'restored-copy'
    for relative,data in m.restore_payloads(report):
        target=copy_root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        assert target.read_bytes()==(root/relative).read_bytes()

def test_duplicate_key_json_nan_and_corrupt_rejected(tmp_path):
    m=mod();path=tmp_path/'stage.json'
    for raw in [b'{"id":1,"id":2}',b'{"xyz":NaN}',b'\xffbroken',b'[] trailing']:
        path.write_bytes(raw)
        with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])

def test_hash_scope_project_version_binary(source):
    m,root,specs,raw=source
    a=m.dry_run(root,24,specs);b=m.dry_run(root,27,specs);c=m.dry_run(root,24,specs,migration_version=2)
    assert len({a.inventory_hash,b.inventory_hash,c.inventory_hash})==3
    assert a.mappings[0].candidate_id!=b.mappings[0].candidate_id
    assert a.mappings[0].candidate_id!=c.mappings[0].candidate_id

def test_duplicate_sources_missing_and_ads_fail_closed(tmp_path):
    m=mod();write(tmp_path,'stage.json',{'id':'fake','units':'m'});spec=m.SourceSpec('stage','fake','stage.json')
    for specs in [[spec,spec],[m.SourceSpec('stage','missing','missing.json')],[m.SourceSpec('binary','ads','stage.json:stream')]]:
        with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,specs)

def test_change_during_read_rejected(tmp_path):
    m=mod();path=tmp_path/'stage.json';path.write_bytes(b'{"id":"fake"}')
    original_open=Path.open
    class ChangingReader:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def fileno(self):return self.stream.fileno()
        def read(self,count):
            value=self.stream.read(count)
            with original_open(path,'wb') as writer:writer.write(b'{"id":"changed"}')
            return value
    def changed_open(obj,mode='r',*args,**kwargs):
        opened=original_open(obj,mode,*args,**kwargs)
        return ChangingReader(opened) if obj==path and mode=='rb' else opened
    with patch.object(Path,'open',changed_open):
        with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])

def test_restore_tamper_rejected(source):
    from dataclasses import replace
    m,root,specs,raw=source;r=m.dry_run(root,24,specs)
    altered=replace(r,sources=(replace(r.sources[0],raw_bytes=b'tampered'),))
    with pytest.raises(m.ImportInventoryError):m.restore_payloads(altered)

def test_approval_conflicts_never_reapprove(tmp_path):
    m=mod();write(tmp_path,'stage.json',{'id':'fake','units':'m'});write(tmp_path,'approved.json',{'approved_round':'other','history':[{'approved':True}]})
    r=m.dry_run(tmp_path,27,[m.SourceSpec('stage','fake','stage.json','r1'),m.SourceSpec('approvals','approval','approved.json')])
    assert 'approved_round_ambiguous' in {i.code for i in r.issues};assert not r.ready_for_apply

@pytest.mark.parametrize('kind',[[],{},None,True])
def test_malformed_kind_sanitized(tmp_path,kind):
    m=mod()
    with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec(kind,'fake','source.json')])

def test_root_ancestor_link_rejected_without_native_privilege(tmp_path):
    m=mod();root=tmp_path/'fake-parent'/'root';root.mkdir(parents=True);write(root,'stage.json',{'id':'fake','units':'m'})
    original=m._link
    with patch.object(m,'_link',lambda path:path==root.parent or original(path)):
        with pytest.raises(m.ImportInventoryError):m.dry_run(root,24,[m.SourceSpec('stage','fake','stage.json')])

def test_link_swap_after_open_rejected_without_native_privilege(tmp_path):
    m=mod();write(tmp_path,'stage.json',{'id':'fake','units':'m'});original=m._link;calls=0
    def swap(path):
        nonlocal calls
        if path==tmp_path/'stage.json':
            calls+=1
            if calls>1:return True
        return original(path)
    with patch.object(m,'_link',swap):
        with pytest.raises(m.ImportInventoryError):m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])


@pytest.mark.parametrize('root',['//qa-server/share',r'\\qa-server\share'])
def test_review_network_root_rejected_before_stat(root):
    m=mod()
    with patch.object(m,'_link',side_effect=AssertionError('IO forbidden')) as probed:
        with pytest.raises(m.ImportInventoryError): m.dry_run(root,24,[m.SourceSpec('binary','fake','file.bin')])
        probed.assert_not_called()


@pytest.mark.parametrize('path',['CON.json','folder/NUL.bin','AUX','PRN.txt','COM1.bin','LPT9.log','stage.json.','stage.json ','dir/file:stream'])
def test_review_windows_alias_rejected_before_stat(tmp_path,path):
    m=mod()
    with patch.object(m,'_link',side_effect=AssertionError('IO forbidden')) as probed:
        with pytest.raises(m.ImportInventoryError): m.dry_run(tmp_path,24,[m.SourceSpec('binary','fake',path)])
        probed.assert_not_called()


def test_review_case_alias_rejected_before_stat(tmp_path):
    m=mod(); specs=[m.SourceSpec('stage','first','stage.json'),m.SourceSpec('stage','second','STAGE.JSON')]
    with patch.object(m,'_link',side_effect=AssertionError('IO forbidden')) as probed:
        with pytest.raises(m.ImportInventoryError): m.dry_run(tmp_path,24,specs)
        probed.assert_not_called()


@pytest.mark.parametrize('field,value',[('project_id',99),('migration_version',2),('inventory_hash','0'*64),('ready_for_apply',True),('status','READY')])
def test_review_restore_report_integrity(source,field,value):
    from dataclasses import replace
    m,root,specs,raw=source; report=m.dry_run(root,24,specs)
    with pytest.raises(m.ImportInventoryError): m.restore_payloads(replace(report,**{field:value}))


@pytest.mark.parametrize('field,value',[('relative_path','relocated.json'),('legacy_key','different'),('round_id','other'),('kind','binary')])
def test_review_restore_source_metadata_integrity(source,field,value):
    from dataclasses import replace
    m,root,specs,raw=source; report=m.dry_run(root,24,specs)
    altered=replace(report.sources[0],**{field:value})
    with pytest.raises(m.ImportInventoryError): m.restore_payloads(replace(report,sources=(altered,*report.sources[1:])))


def test_review_restore_mapping_integrity(source):
    from dataclasses import replace
    m,root,specs,raw=source; report=m.dry_run(root,24,specs)
    changed=replace(report.mappings[0],candidate_id='wrong')
    with pytest.raises(m.ImportInventoryError): m.restore_payloads(replace(report,mappings=(changed,*report.mappings[1:])))


@pytest.mark.parametrize('sources',[[],(object(),)])
def test_review_restore_malformed_sanitized(source,sources):
    from dataclasses import replace
    m,root,specs,raw=source; report=m.dry_run(root,24,specs)
    with pytest.raises(m.ImportInventoryError): m.restore_payloads(replace(report,sources=sources))


def test_review_restore_count_budget_before_hash(source):
    from dataclasses import replace
    m,root,specs,raw=source; report=m.dry_run(root,24,specs)
    with patch.object(m,'MAX_FILES',1):
        with pytest.raises(m.ImportInventoryError): m.restore_payloads(report)


@pytest.mark.parametrize('scale',[False,0,-1,{}, {'value':None,'confidence':'unknown','source':''}])
def test_review_unknown_scale_diagnostic(tmp_path,scale):
    m=mod(); write(tmp_path,'stage.json',dict(id='stage',world_frame=dict(units='m',scale=scale)))
    report=m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])
    assert 'missing_scale' in {i.code for i in report.issues}


@pytest.mark.parametrize('ident',[True,['not-stable'],{'bad':'id'}])
def test_review_malformed_stage_id_unresolved(tmp_path,ident):
    m=mod(); write(tmp_path,'stage.json',dict(id=ident,units='m',scale=1))
    report=m.dry_run(tmp_path,24,[m.SourceSpec('stage','fake','stage.json')])
    assert 'missing_stable_id' in {i.code for i in report.issues}


def test_review_total_read_budget_preflight(tmp_path):
    m=mod(); (tmp_path/'a.bin').write_bytes(b'12'); (tmp_path/'b.bin').write_bytes(b'3456')
    seen=[]; original=Path.open
    def opened(path,*args,**kwargs):
        seen.append(path.name); return original(path,*args,**kwargs)
    with patch.object(Path,'open',opened):
        with pytest.raises(m.ImportInventoryError): m.dry_run(tmp_path,24,[m.SourceSpec('binary','first','a.bin'),m.SourceSpec('binary','second','b.bin')],max_total_bytes=3)
    assert seen==['a.bin']
