"""Native worker Windows: một process trong Job Object, không kế thừa credentials.

Worker tạo suspended, gán Job trước resume; Job cấm tạo child process.
Blender vẫn dùng nhiều threads. Importer cần process phụ phải báo lỗi.
Không dùng locator Store, taskkill, registry, hay quét PID toàn máy.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess
import time
import threading
import logging

_FAILURES={}
_FAILURE_LOCK=threading.Lock()


def supervisor_failure(thread_id):
    with _FAILURE_LOCK:return _FAILURES.get(thread_id)


def _hold(reason):
    with _FAILURE_LOCK:
        first=threading.get_ident() not in _FAILURES
        _FAILURES[threading.get_ident()]=reason
    if first:logging.getLogger(__name__).error('supervisor_failed: %s',reason)
    time.sleep(.02)


def child_env():
    allowed=('SYSTEMROOT','WINDIR','TEMP','TMP','PATH','APPDATA','LOCALAPPDATA')
    return {key:os.environ[key] for key in allowed if key in os.environ}


class _Job:
    def __enter__(self):
        if os.name!='nt':raise OSError('worker native cần Windows Job Object')
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.nt=ctypes.WinDLL('ntdll')
        self.kernel.CreateJobObjectW.argtypes=(ctypes.c_void_p,wintypes.LPCWSTR)
        self.kernel.CreateJobObjectW.restype=wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD)
        self.kernel.AssignProcessToJobObject.argtypes=(wintypes.HANDLE,wintypes.HANDLE)
        self.kernel.TerminateJobObject.argtypes=(wintypes.HANDLE,wintypes.UINT)
        self.kernel.QueryInformationJobObject.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p)
        self.kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        self.kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
        self.nt.NtResumeProcess.argtypes=(wintypes.HANDLE,)
        self.nt.NtResumeProcess.restype=ctypes.c_long
        class Basic(ctypes.Structure):
            _fields_=[('per_process',ctypes.c_longlong),('per_job',ctypes.c_longlong),('flags',wintypes.DWORD),
                      ('minimum',ctypes.c_size_t),('maximum',ctypes.c_size_t),('active',wintypes.DWORD),
                      ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_ulonglong) for name in ('reads','writes','others','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
                      ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.handle=self.kernel.CreateJobObjectW(None,None) # non-inheritable, unnamed
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        self.process_handle=None
        limit=Extended()
        # Documented limits: KILL_ON_JOB_CLOSE | ACTIVE_PROCESS. No breakaway.
        # Chặn child trước khi chạy: chỉ root đã giữ handle mới có thể chạy.
        limit.basic.flags=0x2000|0x8
        limit.basic.active=1
        if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limit),ctypes.sizeof(limit)):
            self.kernel.CloseHandle(self.handle);raise ctypes.WinError(ctypes.get_last_error())
        return self

    def assign_resume(self,proc):
        if not self.kernel.AssignProcessToJobObject(self.handle,int(proc._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.process_handle=int(proc._handle)
        # Popen closes the primary thread handle; resume only this owned suspended process.
        if self.nt.NtResumeProcess(int(proc._handle))!=0:raise OSError('không resume được worker riêng')

    def stop_wait(self):
        while not self.kernel.TerminateJobObject(self.handle,1):
            _hold('Không dừng được worker; đang giữ khóa renderer, cần kiểm supervisor')
        # Không enumerate PID/reopen handle: giữ handle root từ trước resume.
        # Limit active_process=1 loại race child spawn và membership query lỗi.
        if self.process_handle is not None:
            while self.kernel.WaitForSingleObject(self.process_handle,1000)!=0:
                _hold('Đang đợi handle worker kết thúc; giữ khóa renderer')
        class Accounting(ctypes.Structure):
            _fields_=[(name,ctypes.c_longlong) for name in ('user','kernel','period_user','period_kernel')]+[
                (name,wintypes.DWORD) for name in ('faults','total','active','terminated')]
        accounting=Accounting()
        # Accounting là kiểm bổ sung, không thay bằng chứng handle signaled.
        while True:
            queried=self.kernel.QueryInformationJobObject(self.handle,1,ctypes.byref(accounting),ctypes.sizeof(accounting),None)
            if queried and accounting.active==0:break
            if not queried:_hold('Không xác minh được worker đã dừng; đang giữ khóa renderer')
            time.sleep(.02)

    def __exit__(self,*args):
        self.kernel.CloseHandle(self.handle)


def run(cmd,**kwargs):
    with _FAILURE_LOCK:_FAILURES.pop(threading.get_ident(),None)
    timeout=kwargs.pop('timeout',None)
    capture=kwargs.pop('capture_output',False)
    if capture:kwargs.update(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    kwargs['env']=child_env()
    kwargs['close_fds']=True
    kwargs['creationflags']=0x00000004|0x08000000 # CREATE_SUSPENDED | CREATE_NO_WINDOW
    with _Job() as job:
        proc=subprocess.Popen(cmd,**kwargs)
        try:
            try:
                job.assign_resume(proc)
            except BaseException:
                proc.kill();proc.wait();job.stop_wait();raise
            try:
                stdout,stderr=proc.communicate(timeout=timeout)
            except BaseException:
                job.stop_wait()
                proc.communicate()
                raise
            job.stop_wait() # success/nonzero đều xác minh root trước khi nhả renderer lock
            return subprocess.CompletedProcess(cmd,proc.returncode,stdout,stderr)
        finally:
            handle=getattr(proc,'_handle',None)
            if handle is not None:handle.Close()
            with _FAILURE_LOCK:_FAILURES.pop(threading.get_ident(),None)
