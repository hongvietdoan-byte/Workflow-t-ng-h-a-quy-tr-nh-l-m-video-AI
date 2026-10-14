"""Hàng đợi render cục bộ, RAM; một worker dùng plates3d.render/global file lock.

Không SQLite/Streamlit/client. Khởi động lại mất ticket; caller phải submit lại.
Chỉ snapshot JSON tại submit, băm file lớn và render ở worker.
"""
from collections import OrderedDict, deque
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
import uuid


@dataclass(frozen=True)
class RenderBudget:
    cpu_threads: int = 6
    reserve_ram_gib: float = 16
    render_ram_gib: float = 8
    max_source_bytes: int = 2 * 1024**3
    engine_mode: str = 'auto'
    interactive_timeout_sec: int = 110
    batch_timeout_sec: int = 3600

    def __post_init__(self):
        if (type(self.cpu_threads) is not int or not 1 <= self.cpu_threads <= 6
                or not isinstance(self.reserve_ram_gib,(int,float)) or isinstance(self.reserve_ram_gib,bool)
                or not math.isfinite(self.reserve_ram_gib) or self.reserve_ram_gib < 8
                or not isinstance(self.render_ram_gib,(int,float)) or isinstance(self.render_ram_gib,bool)
                or not math.isfinite(self.render_ram_gib) or self.render_ram_gib <= 0
                or any(type(value) is not int or value<=0 for value in
                       (self.max_source_bytes,self.interactive_timeout_sec,self.batch_timeout_sec))
                or self.engine_mode not in ('auto','cpu')):
            raise ValueError('ngân sách render không hợp lệ: tối đa 6 luồng, chừa ít nhất 8 GiB RAM')


def _memory_available():
    if os.name == 'nt':
        import ctypes
        class Memory(ctypes.Structure):
            _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                        ('total',ctypes.c_ulonglong),('available',ctypes.c_ulonglong),
                        ('page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),
                        ('virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),
                        ('extended',ctypes.c_ulonglong)]
        value=Memory(); value.length=ctypes.sizeof(value)
        return value.available if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)) else None
    try:
        return os.sysconf('SC_AVPHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
    except (ValueError, OSError, AttributeError):
        return None


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False)


def _local(path):
    if str(path).startswith(('\\\\','//')) or '://' in str(path):
        raise ValueError('render nền chỉ nhận tệp cục bộ')
    return Path(path).resolve()


def _source_hash(payload, limit):
    from urllib.parse import unquote
    files=set(str(_local(p)) for p in payload.get('source_files',[]))
    model=(payload.get('cfg') or {}).get('model')
    if model and Path(model).suffix.lower() in ('.glb','.gltf'):
        model_path=_local(model)
        if model_path.suffix.lower()=='.gltf':
            metadata_limit=min(limit,8*1024**2)
            if model_path.stat().st_size>metadata_limit:
                raise ValueError('GLTF JSON vượt ngân sách/trần metadata 8 MiB')
            with model_path.open('rb') as stream:metadata=stream.read(metadata_limit+1)
            if len(metadata)>metadata_limit:raise ValueError('GLTF JSON tăng quá ngân sách trong khi đọc')
            model_json=json.loads(metadata.decode('utf-8'))
        else:
            if model_path.stat().st_size>limit:raise ValueError('GLB vượt ngân sách nguồn')
            import struct
            with model_path.open('rb') as stream:
                header=stream.read(20)
                if len(header)!=20 or header[:4]!=b'glTF':raise ValueError('GLB không có header hợp lệ')
                length,kind=struct.unpack('<II',header[12:20])
                if kind!=0x4E4F534A or length>min(limit,8*1024**2):raise ValueError('GLB JSON chunk không hợp lệ/quá lớn')
                model_json=json.loads(stream.read(length))
        for entry in model_json.get('buffers',[])+model_json.get('images',[]):
            uri=entry.get('uri')
            if not uri or uri.startswith('data:'):continue
            candidate=_local(model_path.parent/unquote(uri))
            if candidate.suffix.lower() not in ('.bin','.png','.jpg','.jpeg','.webp','.dds','.ktx','.ktx2'):
                raise ValueError('dependency GLTF phải là texture/buffer cục bộ')
            if '://' in uri or uri.startswith(('\\','//')):raise ValueError('không đọc dependency qua mạng')
            files.add(str(candidate))
    files=sorted(files)
    result=[]; size=0
    for name in files:
        path=Path(name); size+=path.stat().st_size
        if size>limit:
            raise ValueError('nguồn vượt ngân sách đọc file; giảm gói tài nguyên hoặc tăng cấu hình ngân sách')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                digest.update(chunk)
        result.append((name,digest.hexdigest()))
    return result


class RenderQueue:
    def __init__(self,execute,*,root=None,start=True,max_pending=24,max_scopes=64,max_records=160,
                 max_cache_entries=16,max_cache_bytes=256*1024**2,interactive_burst=3,max_pending_per_project=4,max_scopes_per_project=12,
                 budget=None,memory_available=None):
        if (any(type(value) is not int or value<1 for value in
                (max_pending,max_scopes,max_records,max_cache_entries,max_cache_bytes,
                 interactive_burst,max_pending_per_project,max_scopes_per_project))
                or max_records<max_scopes+max_pending+1):
            raise ValueError('giới hạn hàng đợi/cache không hợp lệ')
        self.root=Path(tempfile.mkdtemp(prefix='clay_queue_',dir=root)).resolve()
        self.execute=execute; self.budget=budget or RenderBudget()
        self.memory_available=memory_available or _memory_available
        self.max_pending=max_pending; self.max_pending_per_project=min(max_pending_per_project,max_pending)
        self.max_scopes_per_project=min(max_scopes_per_project,max_scopes); self.max_scopes=max_scopes; self.max_records=max_records
        self.max_cache_entries=max_cache_entries; self.max_cache_bytes=max_cache_bytes
        self.interactive_burst=interactive_burst; self._burst=0
        self._condition=threading.Condition(); self._jobs=OrderedDict(); self._latest={}
        self._lanes={'interactive':OrderedDict(),'batch':OrderedDict()}
        self._cache=OrderedDict(); self._cache_bytes=0
        self._worker=None; self._closed=False
        if start:self.start()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    def start(self):
        with self._condition:
            if self._closed:raise ValueError('hàng đợi đã đóng')
            if self._worker is None:
                self._worker=threading.Thread(target=self._work,name='clay-preview-worker',daemon=True)
                self._worker.start()

    def wake(self):
        with self._condition:self._condition.notify_all()

    def _pending(self):
        return sum(len(jobs) for lane in self._lanes.values() for jobs in lane.values())

    def _remove_pending(self,job):
        lane=self._lanes[job['priority']]; pid=job['project_id']
        jobs=lane.get(pid)
        if jobs is not None:
            try:jobs.remove(job['job_id'])
            except ValueError:pass
            if not jobs:lane.pop(pid,None)

    def _trim_records(self):
        pinned={j['job_id'] for j in self._latest.values()}
        for jid,job in list(self._jobs.items()):
            if len(self._jobs)<self.max_records:break
            if jid not in pinned and job['state'] not in ('pending','running','waiting_resources'):
                self._jobs.pop(jid)

    def submit(self,project_id,scene_id,revision,payload,*,priority='interactive'):
        if (not isinstance(project_id,(int,str)) or isinstance(project_id,bool) or not str(project_id).strip()
                or not isinstance(scene_id,(int,str)) or isinstance(scene_id,bool) or not str(scene_id).strip()
                or type(revision) is not int or revision<0 or priority not in self._lanes):
            raise ValueError('cần project/scene/revision hợp lệ và ưu tiên interactive hoặc batch')
        snapshot=json.loads(_json(payload))
        if not isinstance(snapshot,dict):raise ValueError('đầu vào render phải là object JSON, không chứa kết nối CSDL')
        if len(_json(snapshot).encode())>1024*1024:raise ValueError('snapshot vượt 1 MiB, không submit gói lớn trên giao diện')
        request=hashlib.sha256(_json(snapshot).encode()).hexdigest(); scope=(project_id,scene_id)
        with self._condition:
            previous=self._latest.get(scope)
            rejected=lambda why:{'state':'rejected','reason':why,'project_id':project_id,'scene_id':scene_id,'revision':revision}
            if self._closed:return rejected('hàng đợi đã đóng; khởi tạo dịch vụ mới rồi gửi lại')
            if previous and revision<previous['revision']:return rejected('revision đã cũ; tải revision mới nhất')
            if previous and revision==previous['revision']:
                if request!=previous['request']:return rejected('revision cùng số nhưng đầu vào khác; tăng revision trước khi gửi')
                if previous['state'] in ('pending','running','waiting_resources'):return self._view(previous)
            if scope not in self._latest and sum(s[0]==project_id for s in self._latest)>=self.max_scopes_per_project:
                return rejected('dự án đã đủ cảnh theo dõi; giải phóng cảnh đã đóng để chừa chỗ dự án khác')
            if scope not in self._latest and len(self._latest)>=self.max_scopes:
                return rejected('đã đủ số cảnh theo dõi; giải phóng cảnh đã đóng rồi gửi lại')
            replacing=bool(previous and previous['state']=='pending')
            project_pending=sum(len(lane.get(project_id,[])) for lane in self._lanes.values())
            if project_pending>=self.max_pending_per_project and not replacing:
                return rejected('dự án đã đầy lượt chờ; chừa chỗ cho dự án khác, thử lại sau')
            if self._pending()>=self.max_pending and not replacing:return rejected('hàng đợi đầy; thử lại khi một lượt hoàn tất')
            if replacing:self._remove_pending(previous); previous['state']='superseded'
            self._trim_records()
            if len(self._jobs)>=self.max_records:return rejected('đã đầy lịch sử theo dõi; đóng cảnh cũ rồi gửi lại')
            jid=uuid.uuid4().hex
            job={'job_id':jid,'project_id':project_id,'scene_id':scene_id,'revision':revision,
                 'priority':priority,'request':request,'state':'pending','reason':'đang chờ lượt render',
                 'cache_hit':False,'payload':snapshot}
            self._jobs[jid]=job; self._latest[scope]=job
            self._lanes[priority].setdefault(project_id,deque()).append(jid)
            self._condition.notify_all()
            return self._view(job)

    def _view(self,job):
        keys=('job_id','project_id','scene_id','revision','priority','state','reason','cache_hit')
        result={k:deepcopy(job[k]) for k in keys}
        key=job.get('cache_key')
        if job['state']=='done':
            cached=self._cache.get(key) if not self._closed else None
            if cached and not cached.get('invalid'):result['result']=json.loads(cached['json'])
            else:result.update(state='expired',reason='ảnh trong cache đã hết hạn; gửi lại để dựng hoặc đọc nguồn mới')
        return result

    def status(self,project_id,job_id):
        with self._condition:
            job=self._jobs.get(job_id)
            if not job or job['project_id']!=project_id:
                return {'state':'unknown','reason':'ticket không còn trong phiên dịch vụ hoặc không thuộc dự án; gửi lại'}
            return self._view(job)

    def latest(self,project_id,scene_id):
        with self._condition:
            job=self._latest.get((project_id,scene_id))
            return self._view(job) if job else {'state':'unknown','reason':'chưa có ticket của cảnh'}

    def forget(self,project_id,scene_id):
        with self._condition:
            job=self._latest.get((project_id,scene_id))
            if not job:return
            if any(j['project_id']==project_id and j['scene_id']==scene_id and j['state'] in ('pending','running','waiting_resources') for j in self._jobs.values()):
                raise ValueError('cảnh còn lượt chờ/đang chạy, chưa thể giải phóng')
            self._latest.pop((project_id,scene_id))
            for jid,j in list(self._jobs.items()):
                if j['project_id']==project_id and j['scene_id']==scene_id:self._jobs.pop(jid)

    def snapshot(self):
        with self._condition:
            return {'pending':self._pending(),'running':sum(j['state'] in ('running','waiting_resources') for j in self._jobs.values()),
                    'cache_entries':len(self._cache),'cache_bytes':self._cache_bytes,'records':len(self._jobs),'scopes':len(self._latest)}

    def _take(self):
        name='interactive' if self._lanes['interactive'] and (self._burst<self.interactive_burst or not self._lanes['batch']) else 'batch'
        lane=self._lanes[name]
        if not lane:return None
        pid,jobs=lane.popitem(last=False); jid=jobs.popleft()
        if jobs:lane[pid]=jobs
        self._burst=self._burst+1 if name=='interactive' else 0
        return self._jobs[jid]

    def _current(self,job):
        return self._latest.get((job['project_id'],job['scene_id'])) is job

    def _delete(self,folder):
        path=Path(folder).resolve()
        if path.parent!=self.root:raise ValueError('cache folder nằm ngoài thư mục riêng của dịch vụ')
        shutil.rmtree(path,ignore_errors=True)


    def _prepare_cache(self,folder,result):
        encoded=_json(result)
        if len(encoded.encode())>64*1024:raise ValueError('metadata render vượt 64 KiB')
        files=[p for p in folder.rglob('*') if p.is_file()]
        if len(files)>64:raise ValueError('kết quả vượt 64 tệp cache')
        size=len(encoded.encode())+sum(p.stat().st_size for p in files)
        if size>self.max_cache_bytes:raise ValueError('kết quả vượt dung lượng cache; giảm độ phân giải/số góc')
        return {'json':encoded,'folder':folder,'size':size,'files':self._artifact_hash(folder),'pins':0}


    def _cache_add(self,key,prepared):
        size=prepared['size'];count=len(self._cache);total=self._cache_bytes;removing=[]
        for old_key,old in self._cache.items():
            if count<self.max_cache_entries and total+size<=self.max_cache_bytes:break
            if not old['pins']:
                removing.append(old_key);count-=1;total-=old['size']
        if count>=self.max_cache_entries or total+size>self.max_cache_bytes:
            raise ValueError('cache đang được sao chép; gửi lại khi lượt xuất ảnh xong')
        trash=[]
        for old_key in removing:
            old=self._cache.pop(old_key);self._cache_bytes-=old['size'];trash.append(old['folder'])
        self._cache[key]=prepared;self._cache_bytes+=size
        return trash

    def _artifact_hash(self,folder):
        result=[]
        for path in sorted(folder.rglob('*')):
            if path.is_symlink() or folder.resolve() not in path.resolve().parents:
                raise ValueError('artifact không thuộc thư mục cache riêng')
            if path.is_file():
                digest=hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
                result.append((str(path.relative_to(folder)),digest.hexdigest()))
        return result


    def _work(self):
        while True:
            with self._condition:
                while not self._closed and not self._pending():self._condition.wait()
                if self._closed:return
                job=self._take(); job['state']='waiting_resources'; job['reason']='chờ đủ RAM dự phòng'
                while not self._closed:
                    if not self._current(job):job['state']='superseded';break
                    try:available=self.memory_available()
                    except Exception:available=None
                    job['reason']='không đo được RAM khả dụng; chưa khởi chạy' if available is None else 'chờ đủ RAM dự phòng'
                    if available is not None and available>=(self.budget.reserve_ram_gib+self.budget.render_ram_gib)*1024**3:break
                    self._condition.wait(.5)
                if self._closed:return
                if job['state']=='superseded':continue
                job['state']='running';job['reason']='đang băm nguồn/render; Blender dùng khóa chung'
            folder=self.root/job['job_id']; folder.mkdir();trash=[]
            try:
                sources=_source_hash(job['payload'],self.budget.max_source_bytes)
                key=hashlib.sha256(_json({'project':job['project_id'],'scene':job['scene_id'],'revision':job['revision'],
                                        'payload':job['payload'],'sources':sources,'budget':self.budget.__dict__,'version':1,
                                        'noncache':job['job_id'] if job['payload'].get('cacheable') is False else None}).encode()).hexdigest()
                with self._condition:cached=self._cache.get(key)
                if cached:
                    intact=self._artifact_hash(cached['folder'])==cached['files']
                    with self._condition:
                        if not intact:
                            if cached['pins']:raise ValueError('cache đang được sao chép, chưa thể dựng lại')
                            self._cache.pop(key);self._cache_bytes-=cached['size'];trash.append(cached['folder']);cached=None
                        else:self._cache.move_to_end(key)
                if cached:
                    with self._condition:
                        job.update(state='done' if self._current(job) else 'superseded',cache_key=key,cache_hit=True,reason='ảnh từ cache đúng nguồn/revision')
                    self._delete(folder);continue
                result=self.execute(deepcopy(job['payload']),folder,self.budget)
                if _source_hash(job['payload'],self.budget.max_source_bytes)!=sources:
                    raise ValueError('nguồn thay đổi trong lúc render; gửi lại revision mới')
                if job['payload'].get('kind')=='clay' and job['payload'].get('clay_enabled') and not result.get('clay'):
                    # Projection sau lỗi Blender không được tái dùng như một render clay thành công.
                    key=hashlib.sha256((key+job['job_id']).encode()).hexdigest()
                prepared=self._prepare_cache(folder,result)
                with self._condition:
                    if self._current(job) and not self._closed:
                        trash.extend(self._cache_add(key,prepared))
                        job.update(state='done',cache_key=key,reason='đã hoàn tất bản xem trước')
                    else:job.update(state='superseded',reason='revision mới/dịch vụ đóng đã thay lượt này')
                if job['state']=='superseded':self._delete(folder)
            except Exception as error:
                with self._condition:
                    job.update(state='failed' if self._current(job) else 'superseded',reason=f'render không hoàn tất ({type(error).__name__}); kiểm nguồn/ngân sách rồi gửi lại')
                self._delete(folder)
            finally:
                for old_folder in trash:self._delete(old_folder)
                with self._condition:job.pop('payload',None);self._condition.notify_all()


    def export(self,project_id,job_id,out_dir):
        """Copy artifact cho caller; pin cache trong lúc copy, không giữ mutex/SQLite/render."""
        target=_local(out_dir)
        if target==self.root or self.root in target.parents:raise ValueError('không export vào cache riêng')
        with self._condition:
            job=self._jobs.get(job_id)
            if not job or job['project_id']!=project_id:raise ValueError('ticket không thuộc dự án')
            status=self._view(job)
            if status['state']!='done':raise ValueError('ticket chưa có artifact còn hiệu lực')
            cached=self._cache[job['cache_key']];cached['pins']+=1
        old=cached['folder'];stage=None;trash=None
        try:
            if self._artifact_hash(old)!=cached['files']:
                with self._condition:cached['invalid']=True
                raise ValueError('artifact cache đã thay đổi; gửi lại để dựng mới')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise FileExistsError('thư mục xuất đã tồn tại; giữ nguyên dữ liệu hiện có')
            stage=Path(tempfile.mkdtemp(prefix='clay_export_',dir=target.parent)).resolve()
            copied=stage/'artifacts'
            shutil.copytree(old,copied)
            if self._artifact_hash(old)!=cached['files'] or self._artifact_hash(copied)!=cached['files']:
                with self._condition:cached['invalid']=True
                raise ValueError('artifact đổi trong khi sao chép; gửi lại để dựng mới')
            if target.exists():raise FileExistsError('thư mục xuất đã tồn tại; giữ nguyên dữ liệu hiện có')
            copied.rename(target)
            def relocate(value):
                if isinstance(value,str):return value.replace(str(old),str(target))
                if isinstance(value,list):return [relocate(v) for v in value]
                if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
                return value
            return relocate(status['result'])
        finally:
            if stage is not None:
                resolved=stage.resolve()
                if resolved.parent==target.parent.resolve() and resolved.name.startswith('clay_export_'):
                    shutil.rmtree(resolved,ignore_errors=True)
            with self._condition:
                cached['pins']-=1
                if cached.get('invalid') and not cached['pins']:
                    key=job['cache_key']
                    if self._cache.get(key) is cached:
                        self._cache.pop(key);self._cache_bytes-=cached['size'];trash=old
                self._condition.notify_all()
            if trash is not None:self._delete(trash)

    def close(self):
        with self._condition:
            self._closed=True
            for job in self._jobs.values():
                if job['state'] in ('pending','waiting_resources'):job.update(state='cancelled',reason='dịch vụ đã đóng; gửi lại sau khi khởi tạo')
            self._condition.notify_all()
        if self._worker:self._worker.join(timeout=5)
        if not self._worker or not self._worker.is_alive():
            if self.root.name.startswith('clay_queue_') and not any(c['pins'] for c in self._cache.values()):
                shutil.rmtree(self.root,ignore_errors=True)
                self._cache.clear();self._cache_bytes=0
