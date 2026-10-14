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
_WORKER_BLENDER=None
DEFAULT_WORKER_BLENDER=Path(r'D:/AI-Video-Pipeline/.codex-runtime/blender-worker-5.0.1-x64/unpacked/blender-5.0.1-windows-x64/blender.exe')


def _portable_default():
    # Profile máy chính đã duyệt; chỉ worker ON dùng, không đổi find_blender legacy.
    return str(DEFAULT_WORKER_BLENDER) if DEFAULT_WORKER_BLENDER.is_file() else None


def configure_worker_runtime(path):
    """Cấu hình process-local riêng worker; không sửa UserEnv/legacy locator."""
    global _WORKER_BLENDER
    value=str(path)
    if value.startswith(plates3d.STORE) or not Path(value).is_absolute() or not Path(value).is_file():
        raise ValueError('Blender worker phải là tệp native có đường dẫn tuyệt đối tồn tại')
    if Path(value).name.lower()!='blender.exe':raise ValueError('worker cần blender.exe portable')
    with _SERVICE_LOCK:
        if _SERVICE is not None and getattr(_SERVICE,'worker_blender',None)!=value:
            raise ValueError('cấu hình runtime trước khi dịch vụ khởi tạo')
        _WORKER_BLENDER=value
    return value


def worker_blender(service,explicit=None):
    return explicit or getattr(service,'worker_blender',None) or _WORKER_BLENDER or _portable_default() or plates3d.find_blender()


def worker_sources(blender):
    from . import clay_native_worker
    files=[str(Path(__file__).resolve()),str(Path(clay_native_worker.__file__).resolve())]
    if blender and not blender.startswith(plates3d.STORE) and Path(blender).is_file():
        files.append(str(Path(blender).resolve()))
    return files


def _native_run(cmd,**kwargs):
    from . import clay_native_worker
    return clay_native_worker.run(cmd,**kwargs)


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


def get_service(*,budget=None,worker_blender=None):
    global _SERVICE
    if worker_blender is not None:configure_worker_runtime(worker_blender)
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE=clay_scheduler.RenderQueue(_execute,budget=budget)
            _SERVICE.worker_blender=_WORKER_BLENDER or _portable_default()
            atexit.register(_SERVICE.close)
        elif budget is not None and budget!=_SERVICE.budget:
            raise ValueError("dịch vụ đã khởi tạo ngân sách khác; cấu hình trước khi submit lượt đầu")
        return _SERVICE


def submit_plates(service,project_scope,scene_id,revision,cfg,*,priority='batch',blender=None):
    if not features.on('clay_background_queue'):
        return {'state':'disabled','reason':'cờ clay_background_queue đang tắt'}
    blender=worker_blender(service,blender)
    if blender and blender.startswith(plates3d.STORE):
        return {'state':'rejected','reason':'Render nền Microsoft Store chưa được hỗ trợ: chưa xác minh dừng đúng process/tree và môi trường package; tắt clay_background_queue để dùng render đồng bộ'}
    cfg=deepcopy(cfg);cfg.pop('out_dir',None);cfg.pop('owner',None)
    model=cfg.get('model');files=[str(Path(plates3d.SCRIPT).resolve())]+worker_sources(blender)
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
    info=service.status(project_scope,ticket['job_id'])
    from . import clay_native_worker
    worker=getattr(service,'_worker',None)
    failure=clay_native_worker.supervisor_failure(getattr(worker,'ident',None))
    if failure and info.get('state')=='running':
        info=dict(info,supervisor_state='supervisor_failed',reason=failure)
    return info
