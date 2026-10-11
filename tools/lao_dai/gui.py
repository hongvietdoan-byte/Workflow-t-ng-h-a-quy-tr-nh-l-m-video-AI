"""Pet Tk Windows chỉ đọc. Chạy `py -m tools.lao_dai.gui`; không token CLI/env."""
import argparse
import ctypes
import queue
import re
import threading
import webbrowser

from tools.lao_dai.channel import CredentialStore, PetClient
from tools.lao_dai.logic import PetLogic, allowed_url
from tools.lao_dai.native import InstanceGuard, NativeWindow, WindowsToast, WindowsTray

def ticket_url(ident):
    url='http://127.0.0.1:8502/?ticket='+str(ident)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',str(ident)) or not allowed_url(url):raise ValueError('Mã phiếu không hợp lệ')
    return url

class PetController:
    def __init__(self,client,draw,toast,opener=webbrowser.open):
        self.client=client;self.draw=draw;self.toast=toast;self.opener=opener
        self.logic=PetLogic();self.selected=None

    def poll(self):
        try:
            snapshot=self.client.snapshot();view=self.logic.update(snapshot)
            if view.state in ('idle','tickets'):
                rows=[r for r in snapshot['ticket_summaries'] if r['state'] in ('waiting_admin','waiting_merge')]
                rows.sort(key=lambda r:({'red':0,'yellow':1}.get(r['due_status'],2),r['id']))
                self.selected=rows[0]['id'] if rows else None
            else:self.selected=None
        except Exception as error:
            self.selected=None
            reason=str(error) if isinstance(error,(PermissionError,ConnectionError)) else 'Broker không sẵn sàng'
            view=self.logic.failure(reason)
        self.draw(view)
        for event in view.toasts:self.toast(event)
        return self.logic.poll_seconds

    def open_ticket(self):
        if self.selected:self.opener(ticket_url(self.selected))

class PetApp:
    def __init__(self,client,*,qa_name=None):
        import tkinter as tk
        self.commands=queue.Queue();self.stopping=threading.Event();self.notice=''
        self.scale=1.0
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            self.scale=ctypes.windll.user32.GetDpiForSystem()/96
        except (AttributeError,OSError):pass
        self.root=tk.Tk();self.root.withdraw();self.root.title('Lão Đại · chỉ đọc')
        self.root.overrideredirect(True);self.root.attributes('-topmost',True)
        self.root.configure(bg='#ff00ff');self.root.attributes('-transparentcolor','#ff00ff')
        self.width=int(330*self.scale);self.height=int(300*self.scale)
        self.root.geometry(f'{self.width}x{self.height}+{self.root.winfo_screenwidth()-self.width-24}+{self.root.winfo_screenheight()-self.height-75}')
        self.canvas=tk.Canvas(self.root,width=self.width,height=self.height,bg='#ff00ff',highlightthickness=0,takefocus=0)
        self.canvas.pack();self.root.update_idletasks()
        self.native=NativeWindow(self.root,lambda dpi,rect:self.commands.put(('layout',(dpi,rect))))
        self._layout(self.native.dpi(),None)
        self.drag=None;self.moved=False
        self.canvas.bind('<ButtonPress-1>',self._down);self.canvas.bind('<B1-Motion>',self._drag);self.canvas.bind('<ButtonRelease-1>',self._up)
        self.canvas.bind('<Button-3>',lambda event:self.native.hide())
        self.tray=WindowsTray(self.commands,qa_name or 'production')
        app_id='AI.VideoPipeline.LaoDai.'+('QA.'+qa_name if qa_name else 'v1')
        try:self.toast=WindowsToast(app_id)
        except Exception:self.toast=None;self.notice='Toast chưa sẵn sàng'
        self.qa_name=qa_name
        self.controller=PetController(client,lambda view:self.commands.put(('view',view)),self._toast)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.deiconify();self.native.show()
        threading.Thread(target=self._poll,daemon=True,name='lao-dai-poller').start()
        self.root.after(80,self._drain)

    def _toast(self,event):
        if self.toast is None:return
        try:self.toast.show(event)
        except Exception as error:self.commands.put(('notice',str(error) if isinstance(error,RuntimeError) else 'Toast WinRT không sẵn sàng'))

    def _poll(self):
        while not self.stopping.is_set():
            seconds=self.controller.poll()
            if self.stopping.wait(seconds):return

    def _down(self,event):
        self.drag=(event.x_root,event.y_root,self.root.winfo_x(),self.root.winfo_y());self.moved=False

    def _drag(self,event):
        if self.drag:
            x,y,origin_x,origin_y=self.drag
            dx,dy=event.x_root-x,event.y_root-y
            if abs(dx)+abs(dy)>4:self.moved=True
            self.native.move(origin_x+dx,origin_y+dy)

    def _up(self,event):
        if not self.moved:self.controller.open_ticket()
        self.drag=None

    def _layout(self,dpi,rect):
        self.scale=(dpi or self.native.dpi())/96
        self.width=int(330*self.scale);self.height=int(300*self.scale)
        self.canvas.configure(width=self.width,height=self.height)
        # Chỉ resize qua Tk; tọa độ Win32 tuyệt đối hỗ trợ màn có x/y âm.
        self.root.geometry(f'{self.width}x{self.height}')
        self.root.update_idletasks()
        if rect:self.native.move(rect[0],rect[1])
        else:self.native.reposition()
        if hasattr(self,'view'):self.draw(self.view)

    def _drain(self):
        if self.stopping.is_set():return
        while True:
            try:command,value=self.commands.get_nowait()
            except queue.Empty:break
            if command=='view':self.view=value;self.draw(value)
            elif command=='notice':
                self.notice=value
                if hasattr(self,'view'):self.draw(self.view)
            elif command=='layout':self._layout(*value)
            elif command=='show':self._layout(None,None);self.native.show()
            elif command=='hide':self.native.hide()
            elif command=='exit':self.close();return
        self.root.after(80,self._drain)

    def draw(self,view):
        c=self.canvas;s=self.scale;c.delete('all')
        def oval(box,**kwargs):return c.create_oval(*(int(v*s) for v in box),**kwargs)
        def rect(box,**kwargs):return c.create_rectangle(*(int(v*s) for v in box),**kwargs)
        def text(x,y,value,size=11,**kwargs):return c.create_text(x*s,y*s,text=value,font=('Segoe UI',int(size*s)),**kwargs)
        color='#4f46e5' if view.state=='tickets' else '#667085' if view.state=='disconnected' else '#332f64'
        if view.bubble:
            rect((10,8,320,73),fill=color,outline='')
            # Vẽ Unicode màu hạn riêng: không phụ thuộc emoji font Windows.
            message=view.bubble.split(' · ')[0]
            text(165,28,message,11,fill='white')
            if view.state=='tickets':
                parts=view.bubble.split(' · ')
                text(92,52,parts[1].replace('🔴 ','') if len(parts)>1 else '',9,fill='#ffb7b7')
                text(240,52,parts[2].replace('🟡 ','') if len(parts)>2 else '',9,fill='#ffe39d')
            else:text(165,53,view.reason or 'Cấp quyền trên Phiếu · 8502',9,fill='white',width=290*s)
        # Cú Lão Đại: vector Tk native từ hình 🦉 mockup, không tải tài nguyên/mạng.
        oval((93,102,237,232),fill='#40376d',outline='#282148',width=2)
        c.create_polygon(*(v*s for v in [98,140,103,86,142,119]),fill='#40376d',outline='#282148')
        c.create_polygon(*(v*s for v in [188,119,228,86,231,140]),fill='#40376d',outline='#282148')
        oval((108,120,167,181),fill='#f4e8d7',outline='');oval((165,120,224,181),fill='#f4e8d7',outline='')
        oval((131,137,148,160),fill='#19182b',outline='');oval((182,137,199,160),fill='#19182b',outline='')
        oval((135,140,140,145),fill='white',outline='');oval((186,140,191,145),fill='white',outline='')
        c.create_polygon(*(v*s for v in [156,168,175,168,165,182]),fill='#eba652',outline='')
        oval((90,168,126,220),fill='#5b4c88',outline='');oval((208,168,244,220),fill='#5b4c88',outline='')
        if view.state=='tickets':
            rect((133,193,204,229),fill='#fff4df',outline='#d1a86c')
            c.create_line(*(v*s for v in [133,193,168,214,204,193]),fill='#d1a86c',width=2)
        elif view.state=='disconnected':text(165,207,'?',22,fill='#f4e8d7')
        text(165,248,'Lão Đại',13,fill='#332f64')
        footer='Bấm mở đúng phiếu · kéo để di chuyển' if self.controller.selected else 'Chỉ đọc · khay: hiện / ẩn / thoát'
        text(165,270,footer,9,fill='#667085')
        if self.notice:text(165,288,self.notice,8,fill='#aa5500',width=310*s)

    def close(self):
        if self.stopping.is_set():return
        self.stopping.set();self.tray.close();self.native.close();self.root.destroy()
        if self.qa_name and self.toast:
            self.toast.shortcut.unlink(missing_ok=True)

    def run(self):self.root.mainloop()

def main():
    parser=argparse.ArgumentParser(description='Pet chỉ đọc, cấp quyền trên 8502')
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--qa-name',default='manual')
    parser.add_argument('--demo-state',choices=['idle','tickets','disconnected'],default='idle')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',args.qa_name):parser.error('Tên QA không hợp lệ')
    try:guard=InstanceGuard('QA.'+args.qa_name if args.demo else 'production')
    except RuntimeError:
        ctypes.windll.user32.MessageBoxW(0,'Lão Đại đã chạy. Dùng icon khay để hiện.','Lão Đại',0)
        return
    service=None
    try:
        store=CredentialStore('AI.VideoPipeline.LaoDai.QA.'+args.qa_name if args.demo else 'AI.VideoPipeline.LaoDai.ReadOnly.v1')
        if args.demo:
            from tools.lao_dai.demo import DemoBroker
            from tools.lao_dai.channel import ChannelService
            service=ChannelService(DemoBroker(args.demo_state),store)
            if args.demo_state!='disconnected':service.authorize('synthetic-owner',local=True,owner=True)
            else:store.delete()
        PetApp(PetClient(store),qa_name=args.qa_name if args.demo else None).run()
    except Exception:
        ctypes.windll.user32.MessageBoxW(0,'Không mở được pet. Kiểm Python, pywin32 và kho credential Windows.','Lão Đại',0)
    finally:
        if service:service.stop()
        guard.close()

if __name__=='__main__':main()
