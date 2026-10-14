"""Điều phối clay 5 dự án giả: không DB/provider/Blender thật."""
import threading
import time
from pathlib import Path
import pytest
from core import clay_scheduler as queue
from core import blockout_clay, features
from tests.test_blockout import plan, box


@pytest.fixture(autouse=True)
def memory_fixture(monkeypatch):
    from core import clay_preview_service
    monkeypatch.setattr(clay_preview_service,'_portable_default',lambda:None)
    monkeypatch.setattr(queue,'_memory_available',lambda:64*1024**3)
    monkeypatch.setattr(blockout_clay.plates3d,'find_blender',lambda:'fake-blender')


def wait(service, ticket, timeout=4):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        status=service.status(ticket['project_id'],ticket['job_id'])
        if status['state'] not in ('pending','running','waiting_resources'):
            return status
        threading.Event().wait(.01)
    pytest.fail('worker không hoàn tất trong hạn fixture')


def make(service,pid,scene=1,rev=1,priority='batch',payload=None):
    return service.submit(pid,scene,rev,payload or {'kind':'fixture','value':pid},priority=priority)


def test_five_project_round_robin_and_interactive_no_batch_starvation(tmp_path):
    order=[]
    def execute(payload,folder,budget):
        order.append(payload['value']); return {'value':payload['value']}
    with queue.RenderQueue(execute,root=tmp_path,start=False) as service:
        jobs=[]
        for pid in range(1,6):
            jobs += [make(service,pid,scene=n) for n in (1,2)]
        service.start()
        for j in jobs: assert wait(service,j)['state']=='done'
    assert order==[1,2,3,4,5,1,2,3,4,5]
    order=[]
    with queue.RenderQueue(execute,root=tmp_path,start=False,interactive_burst=2) as service:
        batch=make(service,9)
        fast=[make(service,i,priority='interactive') for i in range(1,6)]
        service.start()
        assert wait(service,batch)['state']=='done'
        for j in fast: wait(service,j)
    assert order[:3]==[1,2,9]


def test_pending_coalesces_capacity_clear_and_latest_revision(tmp_path):
    with queue.RenderQueue(lambda *a:{'ok':True},root=tmp_path,start=False,max_pending=2) as service:
        old=make(service,1)
        latest=make(service,1,rev=2,priority='interactive')
        assert service.status(old['project_id'],old['job_id'])['state']=='superseded'
        other=make(service,2)
        rejected=make(service,3)
        assert rejected['state']=='rejected' and 'đầy' in rejected['reason']
        assert service.snapshot()['pending']==2
        stale=make(service,1,rev=1)
        assert stale['state']=='rejected' and 'revision' in stale['reason']
        service.start(); assert wait(service,latest)['state']=='done'; wait(service,other)


def test_running_old_revision_never_publishes_latest(tmp_path):
    entered=threading.Event(); release=threading.Event()
    def execute(payload,folder,budget):
        if payload['value']==1:
            entered.set(); release.wait(3)
        return {'value':payload['value']}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        old=make(service,1); assert entered.wait(2)
        latest=make(service,1,rev=2,payload={'kind':'fixture','value':2})
        release.set(); assert wait(service,old)['state']=='superseded'
        got=wait(service,latest)
        assert got['result']['value']==2 and service.latest(1,1)['job_id']==latest['job_id']


def test_cache_isolation_source_content_revision_config_and_bounds(tmp_path):
    calls=[]; source=tmp_path/'input.bin'; source.write_bytes(b'first')
    def execute(payload,folder,budget):
        calls.append(payload['value']); (folder/'result.png').write_bytes(b'bytes')
        return {'nested':{'v':[payload['value']]},'out_dir':str(folder)}
    with queue.RenderQueue(execute,root=tmp_path,max_cache_entries=1) as service:
        payload={'kind':'fixture','value':1,'source_files':[str(source)]}
        first=make(service,1,payload=payload); got=wait(service,first)
        got['result']['nested']['v'][0]=999
        assert service.status(first['project_id'],first['job_id'])['result']['nested']['v']==[1]
        again=make(service,1,payload=payload); assert wait(service,again)['cache_hit']
        assert calls==[1]
        source.write_bytes(b'other')
        changed=make(service,1,payload=payload); assert not wait(service,changed)['cache_hit']
        newer=make(service,1,rev=2,payload=payload); assert not wait(service,newer)['cache_hit']
        assert service.snapshot()['cache_entries']<=1
        assert service.status(first['project_id'],first['job_id'])['state']=='expired'
        isolated=make(service,2,payload=payload); assert not wait(service,isolated)['cache_hit']


def test_nonblocking_submit_one_worker_resources_and_config(tmp_path):
    running=0; peak=0; entered=threading.Event(); release=threading.Event(); available=[1]
    def execute(payload,folder,budget):
        nonlocal running,peak
        running+=1; peak=max(peak,running); entered.set(); release.wait(3); running-=1
        assert budget.cpu_threads==6
        return {'ok':True}
    budget=queue.RenderBudget(cpu_threads=6,reserve_ram_gib=16,render_ram_gib=8)
    with queue.RenderQueue(execute,root=tmp_path,budget=budget,memory_available=lambda:available[0]) as service:
        before=time.monotonic(); a=make(service,1); b=make(service,2)
        assert time.monotonic()-before<.5 and not entered.is_set()
        assert service.status(a['project_id'],a['job_id'])['state'] in ('pending','waiting_resources')
        available[0]=64*1024**3; service.wake(); assert entered.wait(2)
        release.set(); wait(service,a); wait(service,b)
    assert peak==1


def test_async_clay_off_no_render_and_on_snapshot(tmp_path,monkeypatch):
    monkeypatch.setattr(features,'on',lambda n:False)
    monkeypatch.setattr(blockout_clay,'render_sheet',lambda *a,**k:pytest.fail('submit chạy render đồng bộ'))
    with queue.RenderQueue(lambda p,*a:{'plan':p['plan']},root=tmp_path,start=False) as service:
        p=plan(box())
        assert blockout_clay.submit_preview(service,1,1,1,p,[])['state']=='disabled'
        assert service.snapshot()['pending']==0
        monkeypatch.setattr(features,'on',lambda n:True)
        ticket=blockout_clay.submit_preview(service,1,1,1,p,[])
        p['khoi'][0]['tam'][0]=99
        service.start(); assert wait(service,ticket)['result']['plan']['khoi'][0]['tam'][0]==3


def test_renderer_thread_cpu_cap_and_uses_existing_global_turn(tmp_path,monkeypatch):
    from core import plates3d
    from contextlib import contextmanager
    import json,subprocess
    calls=[]; seen=[]
    @contextmanager
    def turn(**kwargs):
        seen.append(kwargs); yield
    monkeypatch.setattr(plates3d,'blender_turn',turn)
    def native(cmd,**kwargs):
        calls.append(cmd)
        cfg=json.loads(Path(cmd[-1]).read_text())
        (Path(cfg['out_dir'])/'manifest.json').write_text(json.dumps({'plates':[]}))
        return subprocess.CompletedProcess(cmd,0,stdout='',stderr='')
    plates3d.render({'out_dir':str(tmp_path/'out'),'cpu_threads':6,'owner':'fixture'},blender='fake-blender',run=native)
    assert len(seen)==1 and calls[0][calls[0].index('--threads')+1]=='6'



def test_noisy_project_leaves_admission_for_four_others(tmp_path):
    with queue.RenderQueue(lambda *a:{},root=tmp_path,start=False) as service:
        noisy=[make(service,1,scene=i) for i in range(1,10)]
        assert sum(j['state']=='pending' for j in noisy)==4
        other=[make(service,pid) for pid in range(2,6)]
        assert all(j['state']=='pending' for j in other)
        latest=make(service,1,scene=1,rev=2)
        assert latest['state']=='pending' and service.snapshot()['pending']==8


def test_scope_denied_and_source_change_during_render_not_published(tmp_path):
    from core import clay_preview_service
    src=tmp_path/'in.bin';src.write_bytes(b'before')
    def execute(payload,folder,budget):
        src.write_bytes(b'after'); return {'private':'project-only'}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        j=make(service,1,payload={'kind':'fixture','source_files':[str(src)]})
        assert wait(service,j)['state']=='failed'
        assert clay_preview_service.status(service,2,j)['state']=='unknown'
        assert 'result' not in clay_preview_service.status(service,2,j)


def test_legacy_store_adapter_keeps_existing_bootstrap(tmp_path,monkeypatch):
    from core import plates3d
    from contextlib import contextmanager
    from types import SimpleNamespace
    calls=[]
    @contextmanager
    def turn(**kwargs):yield
    monkeypatch.setattr(plates3d,'blender_turn',turn)
    def store(blender,args,work,timeout,run=None):
        calls.append((args,timeout,run))
        (Path(work)/'manifest.json').write_text('{"plates":[]}')
        return SimpleNamespace(returncode=0,stdout='',stderr='')
    monkeypatch.setattr(plates3d,'_run_in_store',store)
    runner=lambda *a,**k:None
    cfg={'out_dir':str(tmp_path/'store'),'cpu_threads':6}
    plates3d.render(cfg,blender=plates3d.STORE+'fake_family|C:/fake/blender.exe',run=runner)
    assert len(calls)==1 and calls[0][2] is None and '--threads' in calls[0][0]



def test_gltf_dependency_cache_invalidated_and_private_cache_file_verified(tmp_path):
    import json
    model=tmp_path/'m.gltf';texture=tmp_path/'t.png';texture.write_bytes(b'first')
    model.write_text(json.dumps({'images':[{'uri':'t.png'}]}))
    calls=[]
    def execute(payload,folder,budget):
        calls.append(1);(folder/'image.png').write_bytes(b'complete')
        return {'out_dir':str(folder)}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        payload={'kind':'fixture','cfg':{'model':str(model)},'source_files':[str(model)]}
        first=make(service,1,payload=payload);got=wait(service,first)
        texture.write_bytes(b'other')
        changed=make(service,1,payload=payload);got=wait(service,changed)
        assert not got['cache_hit']
        (Path(got['result']['out_dir'])/'image.png').write_bytes(b'corrupted')
        repaired=make(service,1,payload=payload)
        assert not wait(service,repaired)['cache_hit'] and len(calls)==3


def test_cache_byte_limit_rejects_oversize_and_close_cancels_pending(tmp_path):
    def execute(payload,folder,budget):
        (folder/'image.png').write_bytes(b'large'*100);return {}
    service=queue.RenderQueue(execute,root=tmp_path,start=False,max_cache_bytes=100)
    job=make(service,1);service.start()
    assert wait(service,job)['state']=='failed' and service.snapshot()['cache_bytes']==0
    service.close()
    with queue.RenderQueue(execute,root=tmp_path,start=False) as service:
        job=make(service,1);service.close()
        assert service.status(1,job['job_id'])['state']=='cancelled'



def test_submit_poll_do_not_wait_for_background_source_hash(tmp_path,monkeypatch):
    entered=threading.Event();release=threading.Event()
    original=queue._source_hash
    def slow(payload,limit):
        entered.set();release.wait(2);return original(payload,limit)
    monkeypatch.setattr(queue,'_source_hash',slow)
    with queue.RenderQueue(lambda *a:{},root=tmp_path) as service:
        first=make(service,1);assert entered.wait(1)
        before=time.monotonic();second=make(service,2);service.status(1,first['job_id'])
        assert time.monotonic()-before<.3
        release.set();wait(service,first);wait(service,second)


def test_clay_projection_fallback_does_not_poison_success_cache(tmp_path):
    calls=[]
    def execute(payload,folder,budget):
        calls.append(1);return {'enabled':True,'clay':False}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        payload={'kind':'clay','clay_enabled':True}
        first=make(service,1,payload=payload);wait(service,first)
        second=make(service,1,payload=payload)
        assert not wait(service,second)['cache_hit'] and len(calls)==2


@pytest.mark.parametrize('field', ['max_source_bytes','interactive_timeout_sec','batch_timeout_sec'])
@pytest.mark.parametrize('value', [float('nan'),float('inf'),True,1.5,0])
def test_budget_rejects_non_integer_resource_limits(field,value):
    with pytest.raises(ValueError):queue.RenderBudget(**{field:value})


@pytest.mark.parametrize('field', ['max_pending','max_scopes','max_records','max_cache_entries',
                                  'max_cache_bytes','interactive_burst','max_pending_per_project','max_scopes_per_project'])
@pytest.mark.parametrize('value', [float('nan'),float('inf'),True,1.5])
def test_queue_rejects_bad_limits_before_temp_creation(tmp_path,monkeypatch,field,value):
    monkeypatch.setattr(queue.tempfile,'mkdtemp',lambda **kw:pytest.fail('bad limit created directory'))
    with pytest.raises(ValueError):queue.RenderQueue(lambda *a:{},root=tmp_path,**{field:value})


def test_export_refuses_tampered_cache(tmp_path):
    def execute(payload,folder,budget):
        (folder/'image.png').write_bytes(b'correct');return {'out_dir':str(folder)}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        ticket=make(service,1);status=wait(service,ticket)
        (Path(status['result']['out_dir'])/'image.png').write_bytes(b'corrupt')
        with pytest.raises(ValueError):service.export(1,ticket['job_id'],tmp_path/'export')
        assert not (tmp_path/'export').exists()


def test_export_failure_can_retry_and_preserves_existing_target(tmp_path,monkeypatch):
    def execute(payload,folder,budget):
        (folder/'image.png').write_bytes(b'correct');return {'out_dir':str(folder)}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        ticket=make(service,1);wait(service,ticket)
        target=tmp_path/'export';original=queue.shutil.copytree
        def partial(src,dst):Path(dst).mkdir();raise OSError('fixture copy failure')
        monkeypatch.setattr(queue.shutil,'copytree',partial)
        with pytest.raises(OSError):service.export(1,ticket['job_id'],target)
        monkeypatch.setattr(queue.shutil,'copytree',original)
        exported=service.export(1,ticket['job_id'],target)
        assert (Path(exported['out_dir'])/'image.png').read_bytes()==b'correct'
        with pytest.raises(FileExistsError):service.export(1,ticket['job_id'],target)
        assert (target/'image.png').read_bytes()==b'correct'


def test_gltf_budget_checked_before_json_allocation(tmp_path,monkeypatch):
    model=tmp_path/'large.gltf';model.write_bytes(b' '*100)
    monkeypatch.setattr(Path,'read_text',lambda *a,**kw:pytest.fail('read oversized GLTF'))
    with pytest.raises(ValueError):queue._source_hash({'cfg':{'model':str(model)},'source_files':[str(model)]},10)


def test_background_store_rejected_without_bootstrap(tmp_path,monkeypatch):
    from core import clay_preview_service,plates3d
    monkeypatch.setattr(features,'on',lambda n:True)
    monkeypatch.setattr(plates3d,'find_blender',lambda:plates3d.STORE+'fake_family|C:/fake/blender.exe')
    monkeypatch.setattr(plates3d,'render',lambda *a,**kw:pytest.fail('Store started'))
    with queue.RenderQueue(lambda *a:{},root=tmp_path,start=False) as service:
        ticket=clay_preview_service.submit_plates(service,'fixture',1,1,{})
        assert ticket['state']=='rejected' and 'Microsoft Store' in ticket['reason']
        assert service.snapshot()['pending']==0


def test_sanitized_store_guard_before_process_activation(tmp_path,monkeypatch):
    from core import plates3d
    monkeypatch.setattr(plates3d,'_run_in_store',lambda *a,**kw:pytest.fail('Store bootstrap invoked'))
    with pytest.raises(plates3d.Plates3DError,match='Microsoft Store'):
        plates3d._render({'out_dir':str(tmp_path/'out'),'sanitized_child':True},
                        plates3d.STORE+'fake_family|C:/fake/blender.exe',lambda *a,**kw:None,1)


def test_clay_store_rejected_before_queue_admission(tmp_path,monkeypatch):
    monkeypatch.setattr(features,'on',lambda n:True)
    monkeypatch.setattr(blockout_clay.plates3d,'find_blender',lambda:blockout_clay.plates3d.STORE+'fake|C:/fake/blender.exe')
    with queue.RenderQueue(lambda *a:{},root=tmp_path,start=False) as service:
        ticket=blockout_clay.submit_preview(service,1,1,1,plan(box()),[])
        assert ticket['state']=='rejected' and 'Microsoft Store' in ticket['reason']
        assert service.snapshot()['pending']==0


def test_export_detects_tamper_during_copy_and_cleans_only_staging(tmp_path,monkeypatch):
    def execute(payload,folder,budget):
        (folder/'image.png').write_bytes(b'correct');return {'out_dir':str(folder)}
    with queue.RenderQueue(execute,root=tmp_path) as service:
        ticket=make(service,1);wait(service,ticket)
        original=queue.shutil.copytree
        def copy_then_tamper(src,dst):
            original(src,dst);(Path(dst)/'image.png').write_bytes(b'corrupt')
        monkeypatch.setattr(queue.shutil,'copytree',copy_then_tamper)
        marker=tmp_path/'user-owned.txt';marker.write_text('preserve')
        with pytest.raises(ValueError):service.export(1,ticket['job_id'],tmp_path/'export')
        assert marker.read_text()=='preserve' and not (tmp_path/'export').exists()
        assert not list(tmp_path.glob('clay_export_*'))
        assert service.status(1,ticket['job_id'])['state']=='expired'


def test_legacy_store_looks_up_subprocess_runner_at_call_time(tmp_path,monkeypatch):
    from core import plates3d
    calls=[]
    def fake_activation(cmd,**kwargs):
        calls.append(cmd)
        scripts=list(tmp_path.glob('store_*.cmd'))
        assert len(scripts)==1
        scripts[0].with_suffix('.rc').write_text('0',encoding='ascii')
        scripts[0].with_suffix('.log').write_text('fixture-only',encoding='utf-8')
    monkeypatch.setattr(plates3d.subprocess,'run',fake_activation)
    monkeypatch.setattr(plates3d.time,'sleep',lambda _:None)
    # Nếu default cũ bind từ import, đây là bẫy fake; tuyệt đối không native activation.
    original=plates3d._run_in_store
    if original.__defaults__[-1] is not None:
        monkeypatch.setattr(plates3d,'_run_in_store',type(original)(original.__code__,original.__globals__,
                            original.__name__,(lambda *a,**kw:pytest.fail('bound runner bypassed call-time mock'),),original.__closure__))
    result=plates3d._run_in_store(plates3d.STORE+'fake_family|C:/fake/blender.exe',[],str(tmp_path),1)
    assert result.returncode==0 and len(calls)==1
