"""Worker portable: môi trường giả đặt trước import, không gọi provider."""
import os
from pathlib import Path
from unittest.mock import patch


def test_private_locator_both_callers(tmp_path):
    with patch.object(os, 'environ', {'TEMP':str(tmp_path), 'TMP':str(tmp_path)}):
        from core import clay_preview_service as service, blockout_clay, features, plates3d
        exe=tmp_path/'blender.exe';exe.write_bytes(b'fixture')
        class Queue:
            worker_blender=str(exe)
            def submit(self,*args,**kwargs):return args[3]
        with patch.object(features,'on',return_value=True), patch.object(plates3d,'find_blender',side_effect=AssertionError('legacy locator')):
            assert service.submit_plates(Queue(),'p','s',1,{})['blender']==str(exe)
            assert blockout_clay.submit_preview(Queue(),'p','s',1,{},[])['blender']==str(exe)


def test_locator_rejects_relative_missing_and_store(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path), 'TMP':str(tmp_path)}):
        from core import clay_preview_service as service
        import pytest
        for value in ('blender.exe', str(tmp_path/'absent.exe'), 'STORE:fake'):
            with pytest.raises(ValueError):service.configure_worker_runtime(value)


def test_off_does_not_resolve_runtime(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path), 'TMP':str(tmp_path)}):
        from core import clay_preview_service as service, blockout_clay, features
        with patch.object(features,'on',return_value=False):
            assert service.submit_plates(None,'p','s',1,{})['state']=='disabled'
            assert blockout_clay.submit_preview(None,'p','s',1,{},[])['state']=='disabled'


def test_timeout_closes_owned_job_before_return(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path), 'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        import subprocess
        events=[]
        class Job:
            def __enter__(self):events.append('job');return self
            def assign_resume(self,proc):events.append('assign_resume')
            def stop_wait(self):events.append('tree_finished')
            def __exit__(self,*args):events.append('close')
        class Process:
            returncode=0
            def communicate(self,timeout=None):
                if timeout is not None:raise subprocess.TimeoutExpired('fixture',timeout)
                events.append('drained');return ('','')
            def kill(self):events.append('kill')
            def wait(self):events.append('wait')
        import pytest
        with patch.object(native,'_Job',Job),patch.object(native.subprocess,'Popen',return_value=Process()):
            with pytest.raises(subprocess.TimeoutExpired):native.run(['fixture'],timeout=1,capture_output=True,text=True)
        assert events==['job','assign_resume','tree_finished','drained','close']


def test_native_timeout_terminates_single_owned_worker(tmp_path):
    import ctypes
    from ctypes import wintypes
    import subprocess
    import sys
    marker=tmp_path/'root.pid'
    script=tmp_path/'owned.py'
    script.write_text("import os,time,sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(60)\n")
    with patch.object(os,'environ',{'SYSTEMROOT':r'C:\Windows','WINDIR':r'C:\Windows','TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        import pytest
        with pytest.raises(subprocess.TimeoutExpired):
            native.run([sys.executable,str(script),str(marker)],timeout=2,capture_output=True,text=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    handle=kernel.OpenProcess(0x00100000,False,int(marker.read_text()))
    if handle:
        try:assert kernel.WaitForSingleObject(handle,0)==0
        finally:kernel.CloseHandle(handle)


def test_default_profile_used_by_admin_service(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_preview_service as service, clay_scheduler
        exe=tmp_path/'blender.exe';exe.write_bytes(b'fixture')
        with patch.object(service,'DEFAULT_WORKER_BLENDER',exe),patch.object(service,'_SERVICE',None),patch.object(service,'_WORKER_BLENDER',None),patch.object(clay_scheduler,'RenderQueue') as queue:
            selected=service.get_service()
            assert selected.worker_blender==str(exe)
            assert service.worker_blender(selected)==str(exe)


def test_success_confirms_single_root_handle_before_return(tmp_path):
    import sys
    with patch.object(os,'environ',{'SYSTEMROOT':r'C:\Windows','WINDIR':r'C:\Windows','TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        events=[];stop=native._Job.stop_wait
        def observed(job):
            assert job.process_handle is not None
            stop(job)
            assert job.kernel.WaitForSingleObject(job.process_handle,0)==0
            events.append('root_signaled')
        with patch.object(native._Job,'stop_wait',observed):
            result=native.run([sys.executable,'-c','print("success fixture")'],timeout=10,capture_output=True,text=True)
        assert events==['root_signaled'] and result.returncode==0


def test_native_nonzero_confirms_single_worker(tmp_path):
    import sys
    with patch.object(os,'environ',{'SYSTEMROOT':r'C:\Windows','WINDIR':r'C:\Windows','TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        result=native.run([sys.executable,'-c','import sys;print("fixture output");sys.exit(7)'],
                          timeout=10,capture_output=True,text=True)
    assert result.returncode==7
    assert result.stdout.strip()=='fixture output'


def test_assign_failure_kills_and_waits_suspended_process(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        import pytest
        events=[]
        class Job:
            def __enter__(self):return self
            def assign_resume(self,proc):raise OSError('fixture assign failure')
            def stop_wait(self):events.append('tree_finished')
            def __exit__(self,*args):events.append('job_closed')
        class Handle:
            def Close(self):events.append('process_handle_closed')
        class Process:
            _handle=Handle()
            def kill(self):events.append('kill')
            def wait(self):events.append('wait')
        with patch.object(native,'_Job',Job),patch.object(native.subprocess,'Popen',return_value=Process()):
            with pytest.raises(OSError):native.run(['fixture'],timeout=1,capture_output=True,text=True)
        assert events==['kill','wait','tree_finished','process_handle_closed','job_closed']


def test_supervisor_failure_keeps_waiting_and_reports(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native, clay_preview_service as service
        from types import SimpleNamespace
        holds=[]
        class Kernel:
            attempts=0
            def QueryInformationJobObject(self,handle,kind,pointer,*args):
                if kind==3:return True
                pointer._obj.active=0
                return True
            def TerminateJobObject(self,*args):
                self.attempts+=1
                return self.attempts>1
        job=native._Job();job.kernel=Kernel();job.handle=1;job.process_handle=None
        with patch.object(native,'_hold',side_effect=lambda reason:holds.append('held')):
            job.stop_wait()
        assert holds==['held'] and job.kernel.attempts==2
        queue=SimpleNamespace(_worker=SimpleNamespace(ident=42),status=lambda *args:{'state':'running'})
        with patch.object(native,'supervisor_failure',return_value='fixture supervisor failure'):
            info=service.status(queue,'p',{'job_id':'j'})
        assert info['supervisor_state']=='supervisor_failed' and info['state']=='running'


def test_native_worker_refuses_child_process_before_it_runs(tmp_path):
    import sys
    marker=tmp_path/'unexpected_child.txt'
    script=tmp_path/'single_worker.py'
    script.write_text("import subprocess,sys\ntry:\n p=subprocess.Popen([sys.executable,'-c',\"import sys;from pathlib import Path;Path(sys.argv[1]).write_text('ran')\",sys.argv[1]])\n p.wait()\n print('child_returned',p.returncode)\nexcept OSError:\n print('child_refused')\n")
    with patch.object(os,'environ',{'SYSTEMROOT':r'C:\Windows','WINDIR':r'C:\Windows','TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        result=native.run([sys.executable,str(script),str(marker)],timeout=10,capture_output=True,text=True)
    assert result.returncode==0
    assert not marker.exists()
    line=result.stdout.strip()
    assert line=='child_refused' or (line.startswith('child_returned ') and int(line.split()[1])!=0)


def test_root_signal_is_required_before_release_even_with_zero_active(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        events=[]
        class Kernel:
            waited=0
            def QueryInformationJobObject(self,handle,kind,pointer,*args):
                events.append('accounting');pointer._obj.active=0;return True
            def TerminateJobObject(self,*args):events.append('terminate');return True
            def WaitForSingleObject(self,*args):
                self.waited+=1;events.append('root_wait')
                return 258 if self.waited==1 else 0
            def CloseHandle(self,*args):pass
        job=native._Job();job.kernel=Kernel();job.handle=1;job.process_handle=2
        with patch.object(native,'_hold',side_effect=lambda reason:events.append('held')):
            job.stop_wait()
        assert events==['terminate','root_wait','held','root_wait','accounting']


def test_single_worker_accounting_failure_stays_failclosed(tmp_path):
    with patch.object(os,'environ',{'TEMP':str(tmp_path),'TMP':str(tmp_path)}):
        from core import clay_native_worker as native
        events=[]
        class Kernel:
            attempts=0
            def TerminateJobObject(self,*args):return True
            def WaitForSingleObject(self,*args):events.append('root_signaled');return 0
            def QueryInformationJobObject(self,handle,kind,pointer,*args):
                self.attempts+=1;events.append('query')
                pointer._obj.active=0
                return self.attempts>1
        job=native._Job();job.kernel=Kernel();job.handle=1;job.process_handle=2
        with patch.object(native,'_hold',side_effect=lambda reason:events.append('held')):
            job.stop_wait()
        assert events==['root_signaled','query','held','query']
