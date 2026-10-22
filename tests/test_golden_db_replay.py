"""DB/files tổng hợp, worker native; không dữ liệu hay provider thật."""
from contextlib import closing
import importlib
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# C-GOLDEN2 (g): worker dựng gói (tools/golden_capture.replay_builder, tools/golden_db_replay.build_from_database) chỉ chạy native Python 3.14
needs_native_314 = pytest.mark.skipif(not (sys.version_info[:2] == (3, 14) and sys.prefix == sys.base_prefix),
                                      reason="cần worker native Python 3.14 (golden_capture / golden_db_replay) — máy này khác (cloud 3.13); "
                                             "chạy ở máy chính")


@pytest.fixture
def database(tmp_path):
    with patch.object(os, "environ", {}):
        db_module = importlib.import_module("core.db")
        module = importlib.import_module("tools.golden_db_replay")
        flags_module = importlib.import_module("tools.golden_capture")
        path = tmp_path / "source.sqlite"
        conn = db_module.connect(str(path))
        conn.execute("INSERT INTO projects(id,name,game,video_model,created_at) VALUES(24,'synthetic','OTHER','kling','2026-10-21')")
        data = {"image_prompt": "A red cube on a white table.", "characters": [], "location": "", "duration_s": 5}
        conn.execute("INSERT INTO scenes(id,project_id,idx,data) VALUES(7,24,1,?)", (json.dumps(data),))
        conn.execute("INSERT INTO motion_prompts(scene_id,motion_prompt,duration_sec,state) VALUES(7,'The cube rotates.',5,'approved')")
        for job_id, kind, state in ((1,'image_gen','approved'),(2,'video_gen','succeeded')):
            conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,created_at,updated_at) VALUES(?,24,7,?,?,?,?)", (job_id,kind,state,'2026-10-21','2026-10-21'))
        conn.commit()
        conn.execute("UPDATE jobs SET sent_package='DO_NOT_USE_STORED_PACKAGE'")
        conn.commit()
        conn.close()
        from PIL import Image
        picture = tmp_path / "data/projects/24/images/job_1.png"
        picture.parent.mkdir(parents=True)
        Image.new('RGB',(16,16),'red').save(picture)
        flags = {k:False for k in flags_module.feature_catalog()}
        yield module, path, tmp_path, flags


def build(database, job_id, manifest=None):
    module, db, root, flags = database
    with patch.object(os, "environ", {}), patch.object(importlib.import_module("tools.golden_capture"), "head_sha", return_value="a"*40):
        return module.build_from_database(db=db, ref_root=root, job_id=job_id, flags=flags,
            envelope={"provider":"fake","at":"2026-10-21T00:00:00","external_id":"synthetic"}, manifest=manifest)


@pytest.mark.parametrize('job_id',[1,2])
@needs_native_314
def test_actual_prepare_build_native(database, job_id):
    result = build(database,job_id)
    assert result['status'] == 'BUILT', result
    raw = json.loads(result['raw'])
    assert ('red cube' if job_id==1 else 'cube rotates') in raw['prompt']
    assert result['manifest']['provenance'] == 'snapshot_at_capture_not_at_send'
    expected = json.loads((Path(__file__).parent/'golden/db_package_expected.json').read_text(encoding='utf-8'))
    assert result['raw'].encode('utf-8') == expected[str(job_id)].encode('utf-8')
    assert build(database,job_id,result['manifest'])['raw'] == result['raw']


def test_manifest_missing_is_insufficient(database):
    assert build(database,1,{})['status'] == 'INSUFFICIENT_INPUT'


@needs_native_314
def test_db_drift_is_data_changed(database):
    result = build(database,2)
    assert result['status'] == 'BUILT', result
    with closing(sqlite3.connect(database[1])) as conn, conn:
        conn.execute("UPDATE motion_prompts SET motion_prompt='Changed synthetic input'")
    assert build(database,2,result['manifest'])['status'] == 'DATA_CHANGED'


@needs_native_314
def test_file_drift_is_data_changed(database):
    result = build(database,2)
    assert result['status'] == 'BUILT', result
    (database[2]/'data/projects/24/images/job_1.png').write_bytes(b'changed synthetic')
    assert build(database,2,result['manifest'])['status'] == 'DATA_CHANGED'


@needs_native_314
def test_capture_and_replay_without_sidecar(database):
    module,db,root,flags = database
    expected = json.loads((Path(__file__).parent/'golden/db_package_expected.json').read_text(encoding='utf-8'))
    with closing(sqlite3.connect(db)) as conn, conn:
        for job_id,raw in expected.items():
            conn.execute('UPDATE jobs SET sent_package=? WHERE id=?',(raw,int(job_id)))
    flags_file=root/'flags.json'
    flags_file.write_text(json.dumps(flags),encoding='utf-8')
    with patch.object(os,'environ',{}), patch.object(importlib.import_module('tools.golden_capture'),'head_sha',return_value='a'*40):
        capture=importlib.import_module('tools.golden_capture').capture(db=db,project=24,shot=7,flags_file=flags_file,ref_root=root,purpose='compat',database_replay=True)
        assert all(j['database_replay']['matched_at_capture'] for j in capture['jobs'])
        before_db = hashlib.sha256(db.read_bytes()).hexdigest()
        before_data = {str(p.relative_to(root)): p.stat().st_mtime_ns for p in (root/'data').rglob('*')}
        assert all(j['status']=='COMPAT' for j in module.replay_fixture(capture,db=db,ref_root=root)['jobs'])
        assert hashlib.sha256(db.read_bytes()).hexdigest() == before_db
        assert {str(p.relative_to(root)): p.stat().st_mtime_ns for p in (root/'data').rglob('*')} == before_data
        saved=root/'capture.json';saved.write_text(json.dumps(capture),encoding='utf-8')
        output=root/'replay.json'
        assert module.main(['--fixture',str(saved),'--db',str(db),'--ref-root',str(root),'--output',str(output)])==0
        report=json.loads(output.read_text(encoding='utf-8'))
        assert report['projects']['24']['distinct_compat_image_shots']==1
        assert report['projects']['24']['distinct_compat_video_shots']==1
        capture['jobs'][0].pop('database_replay')
        assert module.replay_fixture(capture,db=db,ref_root=root)['jobs'][0]['status']=='INSUFFICIENT_INPUT'


def test_virtual_environment_is_fail_closed(database):
    with patch.object(sys, 'prefix', 'synthetic-venv'), patch.object(sys, 'base_prefix', 'synthetic-native'), \
         patch.object(subprocess, 'run', side_effect=AssertionError('venv must not spawn')):
        with pytest.raises(ValueError, match='native Python3.14'):
            build(database, 1)


@needs_native_314
def test_missing_dependency_appearing_is_data_changed(database):
    result=build(database,1)
    assert result['status']=='BUILT',result
    missing=next(name for name,value in result['manifest']['files'].items() if value is None)
    path=database[2]/missing
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('{}',encoding='utf-8')
    assert build(database,1,result['manifest'])['status']=='DATA_CHANGED'


def test_insufficient_history_is_not_code_mismatch(database):
    module=database[0]
    job={'sent_package_raw':'historical-synthetic','database_replay':{'matched_at_capture':False}}
    assert module.compare_database_job(job,{'status':'BUILT','raw':'different'})['status']=='INSUFFICIENT_INPUT'
    job['database_replay']['matched_at_capture']=True
    assert module.compare_database_job(job,{'status':'BUILT','raw':'different'})['status']=='CODE_MISMATCH'
    assert module.compare_database_job(job,{'status':'DATA_CHANGED','reason':'synthetic'})['status']=='DATA_CHANGED'


@pytest.mark.parametrize('name',['../outside','C:/outside','data/projects/24/../../outside'])
@needs_native_314
def test_unsafe_manifest_path_rejected(database,name):
    result=build(database,1)
    result['manifest']['files']={name:None}
    with pytest.raises(ValueError,match='INSUFFICIENT_INPUT'):
        build(database,1,result['manifest'])


@needs_native_314
def test_api_leaves_global_cwd_and_environment(database):
    fake={}
    with patch.object(os,'environ',fake),patch.object(os,'chdir',side_effect=AssertionError('global cwd')):
        assert build(database,1)['status']=='BUILT'
        assert os.environ is fake
        assert fake=={}


@pytest.mark.parametrize('operation',['write','os_open','utime','network','subprocess','os_system','read_outside','read_asset_text'])
def test_worker_blocks_source_writes_network_and_unknown_reads(database,operation):
    module,db,root,flags=database
    marker=root/'synthetic-outside.txt'
    marker.write_text('synthetic sentinel',encoding='utf-8')
    if operation == 'read_asset_text':
        with closing(sqlite3.connect(db)) as conn,conn:
            conn.execute("INSERT INTO assets(id,game,kind,name) VALUES(900,'OTHER','object','red cube')")
            conn.execute("INSERT INTO asset_images(asset_id,path) VALUES(900,'synthetic-outside.txt')")
    with tempfile.TemporaryDirectory(prefix='golden-probe-') as temp,patch.object(os,'environ',{}):
        box=Path(temp);(box/'data').mkdir()
        module._db_snapshot(db,box/'data/manifest.sqlite')
        request={'root':str(root),'job_id':1,'flags':flags,'envelope':{'provider':'fake','at':'2026-10-21','external_id':'fixture'},'public_config':{},'expected_files':None}
        path=box/'probe.json';path.write_text(json.dumps(request),encoding='utf-8')
        code="""import os,sys,json,socket,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 def probe(self,job):
  path=Path(request['root'])/'synthetic-outside.txt'
  operation=sys.argv[3]
  if operation=='write':path.write_text('forbidden',encoding='utf-8')
  elif operation=='os_open':os.open(path,os.O_WRONLY)
  elif operation=='utime':os.utime(path,(1,1))
  elif operation=='network':socket.socket()
  elif operation=='subprocess':subprocess.Popen(['forbidden'])
  elif operation=='os_system':os.system('exit 0')
  elif operation in ('read_outside','read_asset_text'):path.read_text(encoding='utf-8')
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  try:_worker(request)
  except ValueError:Path('blocked').write_text('yes')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(path),operation],cwd=box,
            env={'SYSTEMROOT':'C:/Windows','HOME':temp,'USERPROFILE':temp,'TEMP':temp,'TMP':temp},capture_output=True,timeout=60)
        assert result.returncode==0
        assert (box/'blocked').read_text()=='yes'
    assert marker.read_text(encoding='utf-8')=='synthetic sentinel'


def test_summary_counts_distinct_shots_and_keeps_insufficient_separate():
    with patch.object(os,'environ',{}):
        module=importlib.import_module('tools.golden_db_replay')
        rows=[{'project_id':24,'scene_id':7,'type':'image_gen','job_id':i,'status':'COMPAT'} for i in (1,2,3)]
        rows += [{'project_id':24,'scene_id':8,'type':'video_gen','job_id':4,'status':'INSUFFICIENT_INPUT'},
                 {'project_id':24,'scene_id':9,'type':'video_gen','job_id':5,'status':'DATA_CHANGED'}]
        result=module.summarize(rows+rows)['projects']['24']
        assert result['selected_cases']==5
        assert result['distinct_compat_image_shots']==1
        assert result['distinct_compat_video_shots']==0
        assert result['INSUFFICIENT_INPUT']==1
        assert result['compat_percent_complete_input']==100
        assert result['data_changed_fraction']==1/5


@pytest.mark.parametrize('cached',[True,False,'ambiguous'])
@needs_native_314
def test_verified_hosted_refs_use_only_active_cached_registry(database,cached):
    module,db,root,flags=database
    flags['seedance_subjects']=True
    from contextlib import closing
    with closing(sqlite3.connect(db)) as conn:
        conn.execute('CREATE TABLE seedance_subject_pictures(sha TEXT PRIMARY KEY,name TEXT NOT NULL,asset_id TEXT,asset_uri TEXT,status TEXT NOT NULL,message TEXT,path TEXT,created_at TEXT,updated_at TEXT)')
        if cached:
            digest=hashlib.sha256((root/'data/projects/24/images/job_1.png').read_bytes()).hexdigest()
            conn.execute("INSERT INTO seedance_subject_pictures(sha,name,asset_id,asset_uri,status) VALUES(?,'synthetic','fixture-public','asset://fixture-public','active')",(digest,))
            if cached == 'ambiguous':
                conn.execute("INSERT INTO seedance_subject_pictures(sha,name,asset_id,asset_uri,status) VALUES(?,'other','fixture-public','asset://other','active')",('b'*64,))
        conn.commit()
    with tempfile.TemporaryDirectory(prefix='golden-cache-') as temp,patch.object(os,'environ',{}):
        box=Path(temp);(box/'data').mkdir()
        module._db_snapshot(db,box/'data/manifest.sqlite')
        request={'root':str(root),'job_id':2,'flags':flags,'envelope':{'provider':'clipai','at':'2026-10-21','external_id':'fixture'},'public_config':{},'expected_files':None}
        path=box/'probe.json';path.write_text(json.dumps(request),encoding='utf-8')
        code="""import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 original=runner.VideoRunner._submit_args
 def hosted(self,job):
  refs=self._hosted_pictures(job,[('synthetic','data/projects/24/images/job_1.png')],clean=False)
  Path('hosted.json').write_text(json.dumps(refs),encoding='utf-8')
  return original(self,job)
 with patch.object(runner.VideoRunner,'_submit_args',hosted):
  try:answer=_worker(request)
  except ValueError:answer={'status':'INSUFFICIENT_INPUT'}
  Path('answer.json').write_text(json.dumps(answer),encoding='utf-8')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(path)],cwd=box,
            env={'SYSTEMROOT':'C:/Windows','HOME':temp,'USERPROFILE':temp,'TEMP':temp,'TMP':temp},capture_output=True,timeout=60)
        assert result.returncode==0
        answer=json.loads((box/'answer.json').read_text(encoding='utf-8'))
        if cached is True:
            assert answer['status']=='BUILT',answer
            assert json.loads((box/'hosted.json').read_text())==[{'uri':'asset://fixture-public'}]
            assert answer['registry'][0]['status']=='active'
        else:
            assert answer['status']=='INSUFFICIENT_INPUT'


def test_legacy_flags_must_be_explicit(database):
    flags_module = importlib.import_module('tools.golden_capture')
    legacy = next(k for k,v in flags_module.feature_catalog().items() if v.get('verified') is not False)
    database[3].pop(legacy)
    with pytest.raises(ValueError, match='INSUFFICIENT_INPUT'):
        build(database,1)


@needs_native_314
def test_low_level_read_is_fingerprinted(database):
    module,db,root,flags=database
    target=root/'data/pricing.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text('{}',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='golden-probe-') as temp,patch.object(os,'environ',{}):
        box=Path(temp);(box/'data').mkdir()
        module._db_snapshot(db,box/'data/manifest.sqlite')
        request={'root':str(root),'job_id':1,'flags':flags,'envelope':{'provider':'fake','at':'2026-10-21','external_id':'fixture'},'public_config':{},'expected_files':None}
        path=box/'probe.json';path.write_text(json.dumps(request),encoding='utf-8')
        code="""import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 original=runner.ImageRunner._submit_args
 def probe(self,job):
  fd=os.open(Path(request['root'])/'data/pricing.json',os.O_RDONLY)
  try:os.read(fd,2)
  finally:os.close(fd)
  return original(self,job)
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  answer=_worker(request)
  Path('answer.json').write_text(json.dumps(answer),encoding='utf-8')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(path)],cwd=box,
            env={'SYSTEMROOT':'C:/Windows','HOME':temp,'USERPROFILE':temp,'TEMP':temp,'TMP':temp},capture_output=True,timeout=60)
        assert result.returncode==0
        answer=json.loads((box/'answer.json').read_text(encoding='utf-8'))
        assert answer['status']=='BUILT'
        assert answer['files']['data/pricing.json']==hashlib.sha256(b'{}').hexdigest()


@needs_native_314
def test_capture_cli_preserves_explicit_public_config(database):
    module,db,root,flags=database
    expected=json.loads((Path(__file__).parent/'golden/db_package_expected.json').read_text(encoding='utf-8'))
    with closing(sqlite3.connect(db)) as conn,conn:
        for job_id,raw in expected.items():
            conn.execute('UPDATE jobs SET sent_package=? WHERE id=?',(raw,int(job_id)))
    flags_file=root/'flags.json';flags_file.write_text(json.dumps(flags),encoding='utf-8')
    public_file=root/'public.json';public_file.write_text(json.dumps({'LLM_PROVIDER':'synthetic'}),encoding='utf-8')
    output=root/'fixture.json'
    with patch.object(os,'environ',{}),patch.object(importlib.import_module('tools.golden_capture'),'head_sha',return_value='a'*40):
        capture=importlib.import_module('tools.golden_capture')
        assert capture.main(['--db',str(db),'--project','24','--shot','7','--flags-file',str(flags_file),
            '--ref-root',str(root),'--output',str(output),'--purpose','compat','--database-replay',
            '--public-config-file',str(public_file)])==0
    fixture=json.loads(output.read_text(encoding='utf-8'))
    assert all(j['database_replay']['manifest']['public_config']=={'LLM_PROVIDER':'synthetic'} for j in fixture['jobs'])


@pytest.mark.parametrize("name", ["data/_plates3d/cache/plate.png", "data/assets/900/ref.png"])
def test_job_ref_permission_is_exact_file_readonly(database, name):
    module, _, root, _ = database
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b"synthetic image")
    with patch.object(os,"environ",{}):
        granted=module._job_ref_paths({"refs":[{"path":name}]},root)
        assert granted=={name}
        assert (Path(name).parent/'other.png').as_posix() not in granted
        assert module._job_ref_paths({"refs":[{"path":"data/assets/900/config.json"}]},root)==set()
        with pytest.raises(ValueError):
            module._job_ref_paths({"refs":[{"path":"data/assets/900/../../../escape.png"}]},root)
        exc=module.SandboxDenied("read", name)
        assert exc.diagnostic=={"kind":"read","path":name}


@pytest.mark.parametrize("name", ["data/_plates3d/cache/plate.png", "data/assets/900/ref.png"])
@needs_native_314   # gọi thẳng _worker: trên 3.13 audit hook đệ quy trong pathlib.relative_to (đỏ cả trên main ở cloud)
def test_worker_reads_only_job_ref_and_reports_blocked_sibling(database,name):
    module,db,root,flags=database
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b"synthetic referenced image")
    sibling=target.with_name('other.png');sibling.write_bytes(b"unreferenced")
    with closing(sqlite3.connect(db)) as conn,conn:
        conn.execute('UPDATE jobs SET sent_package=? WHERE id=1',(json.dumps({'refs':[{'path':name}]}),))
    with tempfile.TemporaryDirectory(prefix='golden-probe-') as temp,patch.object(os,'environ',{}):
        box=Path(temp);(box/'data').mkdir();module._db_snapshot(db,box/'data/manifest.sqlite')
        request={'root':str(root),'job_id':1,'flags':flags,'envelope':{'provider':'fake','at':'2026-10-21','external_id':'fixture'},'public_config':{},'expected_files':None}
        path=box/'probe.json';path.write_text(json.dumps(request),encoding='utf-8')
        code="""import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker,SandboxDenied
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 def probe(self,job):
  path=Path(request['root'])/sys.argv[3]
  assert path.read_bytes()==b'synthetic referenced image'
  try:path.with_name('other.png').read_bytes()
  except SandboxDenied as exc:Path('denied.json').write_text(json.dumps(exc.diagnostic))
  return None
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  result=_worker(request)
 Path('answer.json').write_text(json.dumps(result))
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]),str(path),name],cwd=box,
            env={'SYSTEMROOT':'C:/Windows','HOME':temp,'USERPROFILE':temp,'TEMP':temp,'TMP':temp},capture_output=True,timeout=60)
        assert result.returncode==0
        assert json.loads((box/'denied.json').read_text())=={'kind':'data','path':str(Path(name).with_name('other.png')).replace('\\','/')}
