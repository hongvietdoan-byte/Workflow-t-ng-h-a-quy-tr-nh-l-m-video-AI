"""Adapter Windows: NOACTIVATE, icon khay, toast WinRT desktop thật."""
import base64
import ctypes
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from xml.etree import ElementTree as ET

from tools.lao_dai.logic import allowed_url

APP_ID='AI.VideoPipeline.LaoDai.v1'
_EVENT=re.compile(r'^([A-Za-z0-9_-]{1,128}) · (waiting_admin|waiting_merge) · (green|yellow|red|closed)$')

def toast_xml(event):
    match=_EVENT.fullmatch(event)
    if match is None:raise ValueError('Toast chỉ nhận mã/trạng thái/mốc hạn')
    ident,state,due=match.groups()
    url='http://127.0.0.1:8502/?ticket='+ident
    if not allowed_url(url):raise ValueError('Link toast không hợp lệ')
    root=ET.Element('toast',{'activationType':'protocol','launch':url})
    binding=ET.SubElement(ET.SubElement(root,'visual'),'binding',{'template':'ToastGeneric'})
    ET.SubElement(binding,'text').text='Lão Đại · '+ident
    ET.SubElement(binding,'text').text=state+' · '+due
    return ET.tostring(root,encoding='unicode')

def install_shortcut(app_id=APP_ID):
    """AUMID riêng của app; không sửa shortcut app khác hay quyền OS."""
    import pythoncom
    from win32com.shell import shell
    from win32com.propsys import propsys
    if not re.fullmatch(r'AI\.VideoPipeline\.LaoDai\.(v1|QA\.[A-Za-z0-9_-]{1,80})',app_id):raise ValueError('AUMID sai')
    folder=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(app_id+'.lnk')
    pythoncom.CoInitialize()
    try:
        link=pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        link.SetPath(str(pythonw))
        args='-m tools.lao_dai.gui'
        if app_id!=APP_ID:args+=' --demo --qa-name '+app_id.split('.QA.')[1]
        link.SetArguments(args)
        link.SetWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        link.SetDescription('Lão Đại · chỉ đọc phiếu, duyệt trên 8502')
        store=link.QueryInterface(propsys.IID_IPropertyStore)
        store.SetValue(propsys.PSGetPropertyKeyFromName('System.AppUserModel.ID'),propsys.PROPVARIANTType(app_id))
        store.Commit();link.QueryInterface(pythoncom.IID_IPersistFile).Save(str(path),True)
    finally:pythoncom.CoUninitialize()
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    return path

class WindowsToast:
    def __init__(self,app_id=APP_ID):
        self.app_id=app_id
        self.shortcut=install_shortcut(app_id)

    def show(self,event):
        xml=toast_xml(event)
        # Chỉ nội dung đã lọc qua stdin. Không token, session, title trong CLI/env/log.
        script=r'''$ErrorActionPreference='Stop'
[Console]::InputEncoding=[System.Text.Encoding]::UTF8
[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime] > $null
$xml=New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml([Console]::In.ReadToEnd())
$toast=[Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier=[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('__APP_ID__')
if ($notifier.Setting -ne 'Enabled') { exit 2 }
$notifier.Show($toast)
'''.replace('__APP_ID__',self.app_id)
        encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
            input=xml.encode('utf-8'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
        if result.returncode==2:raise RuntimeError('Thông báo Windows đang tắt cho Lão Đại')
        if result.returncode:raise RuntimeError('Không gửi được toast WinRT; kiểm Windows notifications')

def clamp_position(x,y,width,height,work):
    left,top,right,bottom=work
    return (max(left,min(int(x),max(left,right-width))),
            max(top,min(int(y),max(top,bottom-height))))

class NativeWindow:
    def __init__(self,root,layout_callback=None):
        import win32api,win32con,win32gui
        self.gui=win32gui;self.con=win32con;self.layout_callback=layout_callback
        self.hwnd=win32gui.GetAncestor(root.winfo_id(),win32con.GA_ROOT)
        style=win32gui.GetWindowLong(self.hwnd,win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(self.hwnd,win32con.GWL_EXSTYLE,style|win32con.WS_EX_NOACTIVATE|win32con.WS_EX_TOOLWINDOW)
        self.old=win32gui.SetWindowLong(self.hwnd,win32con.GWL_WNDPROC,self._proc)
        win32gui.SetWindowPos(self.hwnd,win32con.HWND_TOPMOST,0,0,0,0,win32con.SWP_NOMOVE|win32con.SWP_NOSIZE|win32con.SWP_NOACTIVATE)

    def _proc(self,hwnd,msg,wparam,lparam):
        if msg==self.con.WM_MOUSEACTIVATE:return self.con.MA_NOACTIVATE
        if msg==0x02E0 and self.layout_callback: # WM_DPICHANGED, RECT chỉ sống trong callback
            rect=ctypes.cast(lparam,ctypes.POINTER(ctypes.c_long*4)).contents
            self.layout_callback(wparam&0xffff,tuple(rect));return 0
        if msg==0x007E and self.layout_callback: # WM_DISPLAYCHANGE
            self.layout_callback(None,None)
        return self.gui.CallWindowProc(self.old,hwnd,msg,wparam,lparam)

    def dpi(self):
        try:
            api=ctypes.windll.user32.GetDpiForWindow
            api.argtypes=[ctypes.c_void_p];api.restype=ctypes.c_uint
            return api(self.hwnd) or 96
        except (AttributeError,OSError):return 96

    def reposition(self):
        rect=self.gui.GetWindowRect(self.hwnd)
        self.move(rect[0],rect[1])

    def show(self):
        self.reposition()
        self.gui.ShowWindow(self.hwnd,self.con.SW_SHOWNOACTIVATE)
    def hide(self):self.gui.ShowWindow(self.hwnd,self.con.SW_HIDE)
    def move(self,x,y):
        left,top,right,bottom=self.gui.GetWindowRect(self.hwnd)
        width,height=right-left,bottom-top
        monitor=self.gui.MonitorFromRect((int(x),int(y),int(x)+width,int(y)+height),2)
        x,y=clamp_position(x,y,width,height,self.gui.GetMonitorInfo(monitor)['Work'])
        self.gui.SetWindowPos(self.hwnd,self.con.HWND_TOPMOST,x,y,0,0,self.con.SWP_NOSIZE|self.con.SWP_NOACTIVATE)
    def close(self):
        if self.gui.IsWindow(self.hwnd):self.gui.SetWindowLong(self.hwnd,self.con.GWL_WNDPROC,self.old)

class WindowsTray:
    """Win32 Shell_NotifyIcon thật, không cần pystray, queue về thread Tk."""
    def __init__(self,commands,unique='production'):
        self.commands=commands;self.ready=threading.Event();self.error=None;self.hwnd=None
        self.thread=threading.Thread(target=self._run,args=(unique,),daemon=True,name='lao-dai-tray')
        self.thread.start();self.ready.wait(3)
        if self.error:raise RuntimeError('Không tạo được icon khay Windows') from None
        if not self.hwnd:raise RuntimeError('Khay Windows chưa sẵn sàng')

    def _run(self,unique):
        import win32api,win32con,win32gui
        self.gui=win32gui;self.con=win32con
        callback=win32con.WM_USER+20
        def proc(hwnd,msg,wparam,lparam):
            if msg==callback:
                if lparam==win32con.WM_LBUTTONUP:self.commands.put(('show',None))
                if lparam==win32con.WM_RBUTTONUP:
                    menu=win32gui.CreatePopupMenu()
                    for ident,label in [(1,'Hiện Lão Đại'),(2,'Ẩn Lão Đại'),(3,'Thoát')]:
                        win32gui.AppendMenu(menu,win32con.MF_STRING,ident,label)
                    # Foreground chỉ khi người chủ ý mở MENU khay, không lúc poll/show/drag.
                    win32gui.SetForegroundWindow(hwnd)
                    choice=win32gui.TrackPopupMenu(menu,win32con.TPM_RETURNCMD|win32con.TPM_NONOTIFY,*win32gui.GetCursorPos(),0,hwnd,None)
                    win32gui.DestroyMenu(menu)
                    if choice:self.commands.put(({1:'show',2:'hide',3:'exit'}[choice],None))
                return 0
            if msg==win32con.WM_CLOSE:win32gui.DestroyWindow(hwnd);return 0
            if msg==win32con.WM_DESTROY:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE,(hwnd,0));win32gui.PostQuitMessage(0);return 0
            return win32gui.DefWindowProc(hwnd,msg,wparam,lparam)
        try:
            wc=win32gui.WNDCLASS();wc.hInstance=win32api.GetModuleHandle(None);wc.lpszClassName='LaoDaiTray_'+unique;wc.lpfnWndProc=proc
            atom=win32gui.RegisterClass(wc)
            self.hwnd=win32gui.CreateWindow(atom,'Lão Đại',0,0,0,0,0,0,0,wc.hInstance,None)
            icon=win32gui.LoadIcon(0,win32con.IDI_APPLICATION)
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD,(self.hwnd,0,win32gui.NIF_ICON|win32gui.NIF_MESSAGE|win32gui.NIF_TIP,callback,icon,'Lão Đại · chỉ đọc'))
            self.ready.set();win32gui.PumpMessages()
            win32gui.UnregisterClass(atom,wc.hInstance)
        except Exception:self.error=True;self.ready.set()

    def close(self):
        if self.hwnd:self.gui.PostMessage(self.hwnd,self.con.WM_CLOSE,0,0)
        self.thread.join(3)

class InstanceGuard:
    def __init__(self,name='production'):
        import win32api,win32event
        self.handle=win32event.CreateMutex(None,False,'Local\\AI.VideoPipeline.LaoDai.'+name)
        if win32api.GetLastError()==183:
            win32api.CloseHandle(self.handle);self.handle=None
            raise RuntimeError('Lão Đại đã chạy; dùng icon khay để hiện')
    def close(self):
        if self.handle:
            import win32api
            win32api.CloseHandle(self.handle);self.handle=None
