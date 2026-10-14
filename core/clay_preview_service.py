"""Dịch vụ xem trước chung của Dashboard và blockout; không DB/Streamlit trong worker."""
import atexit
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import threading
from . import clay_scheduler, features, plates3d

_SERVICE=None
_SERVICE_LOCK=threading.Lock()


def _native_run(cmd,**kwargs):
    # Chỉ whitelist hệ thống cần Blender; không kế thừa API credentials.
    allowed=('SYSTEMROOT','WINDIR','TEMP','TMP','PATH','APPDATA','LOCALAPPDATA')
    kwargs['env']={name:os.environ[name] for name in allowed if name in os.environ}
    return subprocess.run(cmd,**kwargs)


def _execute(payload,folder,budget):
    def render(cfg,**kwargs):
        cfg=deepcopy(cfg);cfg.update(cpu_threads=budget.cpu_threads,sanitized_child=True,
                                    owner=f"preview {payload['project_scope']}")
        if budget.engine_mode=='cpu':cfg.update(engine='cycles',cpu_only=True)
        blender=payload.get('blender')
        deadline=budget.interactive_timeout_sec if payload['priority']=='interactive' else budget.batch_timeout_sec
        kwargs['timeout']=min(kwargs.get('timeout',deadline),deadline)
        return plates3d.render(cfg,blender=blender,run=_native_run,**kwargs)
    if payload['kind']=='clay':
        from . import blockout_clay
        return blockout_clay.render_sheet(payload['plan'],payload['cho_dung'],folder/'sheet.png',
                    renderer=render,_clay_enabled=payload['clay_enabled'],**payload['options'])
    if payload['kind']=='plates':
        cfg=deepcopy(payload['cfg']);cfg['out_dir']=str(folder)
        return render(cfg)
    raise ValueError('loại xem trước chưa được hỗ trợ')


def get_service(*,budget=None):
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE=clay_scheduler.RenderQueue(_execute,budget=budget)
            atexit.register(_SERVICE.close)
        elif budget is not None and budget!=_SERVICE.budget:
            raise ValueError("dịch vụ đã khởi tạo ngân sách khác; cấu hình trước khi submit lượt đầu")
        return _SERVICE


def submit_plates(service,project_scope,scene_id,revision,cfg,*,priority='batch',blender=None):
    if not features.on('clay_background_queue'):
        return {'state':'disabled','reason':'cờ clay_background_queue đang tắt'}
    blender=blender or plates3d.find_blender()
    if blender and blender.startswith(plates3d.STORE):
        return {'state':'rejected','reason':'Render nền Microsoft Store chưa được hỗ trợ: chưa xác minh dừng đúng process/tree và môi trường package; tắt clay_background_queue để dùng render đồng bộ'}
    cfg=deepcopy(cfg);cfg.pop('out_dir',None);cfg.pop('owner',None)
    model=cfg.get('model');files=[str(Path(plates3d.SCRIPT).resolve())]
    if model:files.append(str(clay_scheduler._local(model)))
    hdri=(cfg.get('sky') or {}).get('hdri')
    if hdri:
        if Path(hdri).suffix.lower() not in ('.hdr','.exr'):raise ValueError('HDRI phải là tệp .hdr/.exr cục bộ')
        files.append(str(clay_scheduler._local(hdri)))
    # Các định dạng import có thể có texture ngoài gói; không tái dùng cache cho chúng.
    cacheable=not model or Path(model).suffix.lower() in ('.glb','.gltf')
    payload={'kind':'plates','project_scope':project_scope,'cfg':cfg,'source_files':files,
             'cacheable':cacheable,'blender':blender,'priority':priority}
    return service.submit(project_scope,scene_id,revision,payload,priority=priority)


def status(service,project_scope,ticket):
    return service.status(project_scope,ticket['job_id'])
