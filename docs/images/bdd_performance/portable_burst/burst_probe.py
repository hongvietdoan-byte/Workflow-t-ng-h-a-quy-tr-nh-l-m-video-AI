import os,sys,time,json,math,threading,ctypes,shutil,types
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
OUT=ROOT/'docs/images/bdd_performance/portable_burst';TEMP=OUT/'portable_temp';TEMP.mkdir(exist_ok=True)
FAKE={'SYSTEMROOT':r'C:\Windows','WINDIR':r'C:\Windows','TEMP':str(TEMP),'TMP':str(TEMP),'PATH':r'C:\Windows\System32','APPDATA':str(TEMP/'appdata'),'LOCALAPPDATA':str(TEMP/'local')}
for d in ('appdata','local'):(TEMP/d).mkdir(exist_ok=True)
patch.object(os,'environ',FAKE).start()
sys.modules['core.assets']=types.SimpleNamespace(fold=lambda x:x)
sys.modules['core.features']=types.SimpleNamespace(on=lambda name:True)
from core import clay_preview_service as svc,clay_scheduler as sched,blockout_clay as clay,clay_native_worker as native,plates3d
from ctypes import wintypes as W
K=ctypes.WinDLL('kernel32',use_last_error=True);P=ctypes.WinDLL('psapi')
K.GetCurrentProcess.restype=W.HANDLE
K.GetProcessTimes.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
P.GetProcessMemoryInfo.argtypes=[W.HANDLE,ctypes.c_void_p,W.DWORD]
class Mem(ctypes.Structure):
 _fields_=[('cb',W.DWORD),('faults',W.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak','rss','pp','p','npp','np','page','peakpage')]
def sample(h):
 m=Mem();m.cb=ctypes.sizeof(m);P.GetProcessMemoryInfo(h,ctypes.byref(m),m.cb)
 a,b,c,d=[ctypes.c_ulonglong() for _ in range(4)];K.GetProcessTimes(h,ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d))
 return m.rss,(c.value+d.value)/1e7
LOCK=threading.Lock();owned={};proof=[];metrics=[];current=None;stop=False
origassign=native._Job.assign_resume;origstop=native._Job.stop_wait;origclose=native._Job.__exit__
def assign(job,proc):
 origassign(job,proc)
 with LOCK:owned[int(proc._handle)]=proc.pid
 proof.append({'pid':proc.pid,'assigned':True})
def stopwait(job):
 origstop(job)
 with LOCK:
  pid=owned.pop(job.process_handle,None)
 proof.append({'pid':pid,'root_signaled':job.kernel.WaitForSingleObject(job.process_handle,0)==0,'job_active_zero_verified':True})
def close(job,*a):
 origclose(job,*a);proof.append({'job_closed':True})
def monitor():
 previous={};prevtime=time.perf_counter()
 while not stop:
  now=time.perf_counter();dt=now-prevtime;prevtime=now
  with LOCK:
   handles=[K.GetCurrentProcess()]+list(owned)
   values=[sample(h) for h in handles]
   active=len(owned)
  if current is not None:
   current['ram_free_min_gib']=min(current['ram_free_min_gib'],sched._memory_available()/2**30)
   current['python_rss_peak_mib']=max(current['python_rss_peak_mib'],values[0][0]/2**20)
   current['blender_rss_peak_mib']=max(current['blender_rss_peak_mib'],sum(x[0] for x in values[1:])/2**20)
   cpu=sum(max(0,v[1]-previous.get(h,v[1])) for h,v in zip(handles,values))/dt*100
   current['cpu_peak_one_core_percent']=max(current['cpu_peak_one_core_percent'],cpu)
   current['owned_active_peak']=max(current['owned_active_peak'],active)
  previous={h:v[1] for h,v in zip(handles,values)};time.sleep(.05)
def p95(a):return round(sorted(a)[max(0,math.ceil(len(a)*.95)-1)],3) if a else None
PLAN={'san':{'kich_thuoc':[20,20],'z':0},'khoi':[{'id':f'b{i}','loai':'hop','tam':[-7+(i%6)*2.6,-5+(i//6)*3],'kich_thuoc':[[1,1],[1,1],[2,2]],'nguon':'anh','huong':0,'mo_ta_ngan':f'Khoi {i}'} for i in range(24)],'loi_mo':[],'huong_sang':90}
budget=sched.RenderBudget(engine_mode='cpu',interactive_timeout_sec=110,batch_timeout_sec=110)
results={'profile':'CPU Cycles 6 threads; 640x360; samples8; four cameras; 24 boxes','cpu_definition':'100%=one core; Python+owned Blender only, 50ms samples; divide16 for full logical machine','vram_baseline_mib':2975,'vram_baseline_source':'parent prebenchmark NVIDIA baseline; not measured native GPU load','scenarios':metrics,'native_proof':proof}
started=time.perf_counter()
with patch.object(native._Job,'assign_resume',assign),patch.object(native._Job,'stop_wait',stopwait),patch.object(native._Job,'__exit__',close),patch.object(plates3d,'find_blender',side_effect=RuntimeError('legacy forbidden')),patch.object(plates3d,'models',side_effect=RuntimeError('model lookup forbidden')):
 version=native.run([str(svc.DEFAULT_WORKER_BLENDER),'--version'],capture_output=True,text=True,timeout=20);results['version']=version.stdout.splitlines()[0];results['version_returncode']=version.returncode
 th=threading.Thread(target=monitor,daemon=True);th.start()
 for count in (20,30):
  if time.perf_counter()-started>245:results['stopped_reason']='global budget remaining insufficient';break
  if count==30 and (metrics[-1]['wall_sec']>140 or metrics[-1]['ram_free_min_gib']<24):results['stopped_reason']='20-project bound/health prevents30';break
  current={'projects':count,'jobs_per_project':1,'ram_free_min_gib':1000,'python_rss_peak_mib':0,'blender_rss_peak_mib':0,'cpu_peak_one_core_percent':0,'owned_active_peak':0}
  t0=time.perf_counter();begins={};renders=[];submitted={};tickets=[];lat=[];slat=[];wait=[];barrier=threading.Barrier(count)
  def execute(payload,folder,b):
   start=time.perf_counter();wait.append((start-submitted[payload['project_scope']])*1000)
   r=svc._execute(payload,folder,b);renders.append(time.perf_counter()-start)
   if not r['clay'] or len(r['views'])!=4 or r['camera_kind']!='clay':raise RuntimeError('native clay absent')
   return r
  queue=sched.RenderQueue(execute,root=TEMP,budget=budget);queue.worker_blender=str(svc.DEFAULT_WORKER_BLENDER)
  def producer(i):
   barrier.wait();scope=f'portable{count}_{i}';submitted[scope]=time.perf_counter();t=time.perf_counter()
   ticket=clay.submit_preview(queue,scope,'scene',1,PLAN,[],resolution=(640,360),timeout=110)
   lat.append((time.perf_counter()-t)*1000);tickets.append((scope,ticket))
  producers=[threading.Thread(target=producer,args=(i,)) for i in range(count)]
  for t in producers:t.start()
  for t in producers:t.join()
  rejected=[{'project':scope,'state':ticket['state'],'reason':ticket.get('reason')} for scope,ticket in tickets if 'job_id' not in ticket]
  pending=[(scope,ticket) for scope,ticket in tickets if 'job_id' in ticket];terminal=[]
  while pending and time.perf_counter()-started<355:
   for scope,ticket in pending[:]:
    t=time.perf_counter();s=svc.status(queue,scope,ticket);slat.append((time.perf_counter()-t)*1000)
    if s['state'] in ('done','failed','cancelled','superseded','rejected','expired'):
     terminal.append({'project':scope,'state':s['state'],'clay':s.get('result',{}).get('clay'),'views':s.get('result',{}).get('views')});pending.remove((scope,ticket))
     if s['state']=='done' and len(terminal)==1:
      exported=queue.export(scope,ticket['job_id'],OUT/f'portable_{count}_project')
   time.sleep(.05)
  queue.close()
  if queue._worker.is_alive():
   queue._worker.join(timeout=110)
  current.update(wall_sec=round(time.perf_counter()-t0,3),accepted=len(tickets)-len(rejected),rejected=rejected,terminal=terminal,submit_p95_ms=p95(lat),status_p95_ms=p95(slat),queuewait_p95_ms=p95(wait),render_p95_sec=p95(renders),queue_closed=queue._closed,worker_stopped=not queue._worker.is_alive(),owned_remaining=len(owned));metrics.append(current);current=None
  print(json.dumps({k:v for k,v in metrics[-1].items() if k!='terminal'}),flush=True)
  (OUT/'burst_metrics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
  if pending or any(x['state']!='done' or not x['clay'] for x in terminal):results['stopped_reason']='native failure; capacity not passed';break
 stop=True;th.join(2)
results['total_sec']=round(time.perf_counter()-started,3);results['owned_remaining']=len(owned)
(OUT/'burst_metrics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('BENCH_COMPLETE',results['total_sec'],flush=True)

if not owned and all(m['worker_stopped'] and m['queue_closed'] for m in metrics):
 target=TEMP.resolve(); workspace=ROOT.resolve()
 if target.is_relative_to(workspace) and target==OUT.resolve()/'portable_temp':shutil.rmtree(target)
