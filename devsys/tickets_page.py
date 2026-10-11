"""Trang phiếu chỉ đọc: 8502 chưa có xác thực admin phía server.

Các adapter quyết định là service nội bộ cho server tích hợp về sau;
render không gọi chúng, không nhận actor/role từ trình duyệt/session_state.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
import streamlit as st
from core import features, tickets

DECISIONS=('Duyệt','Từ chối','Cần thêm thông tin','Gia hạn')
REASONS=('Đã kiểm bằng chứng','Cần bổ sung ca thật','Chưa đúng phạm vi','Cần thêm thời gian')

@contextmanager
def read_connection():
    path=Path(os.environ.get('PIPELINE_DB',os.path.join('data','manifest.sqlite')))
    if not path.is_absolute(): path=Path(__file__).resolve().parents[1]/path
    path=path.resolve()
    conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    try: yield conn
    finally: conn.close()

def queue(conn, *, now=None, kind=None, project=None):
    out=tickets.list_tickets(conn)
    for t in out:
        t['occurrences']=conn.execute("SELECT count(*) FROM ticket_events WHERE ticket_id=? AND transition IN ('open','merge')",(t['id'],)).fetchone()[0]
    def priority(t):
        if t['state']=='closed': return (4,t['due_at'],t['id'])
        blocked=bool(t['impact'].get('blocked_projects') or t['impact'].get('blocked_shots'))
        due=tickets.due_status(t,now)
        return (0 if blocked else 1 if due=='red' else 2 if due=='yellow' else 3,t['due_at'],t['id'])
    return sorted((t for t in out if (not kind or t['kind']==kind) and (project is None or t['project_id']==project)),key=priority)

def next_ticket(items,current):
    ids=[t['id'] for t in items]
    if not ids: return None
    if current not in ids: return ids[0]
    i=ids.index(current)
    return ids[i+1] if i+1<len(ids) else (ids[0] if len(ids)>1 else None)

def bulk_preview(conn,ids):
    if not ids or len(ids)!=len(set(ids)): raise tickets.TicketError('Chọn danh sách phiếu duy nhất')
    rows=[tickets.get(conn,i) for i in ids]
    if len({t['kind'] for t in rows})!=1 or any(t['kind']=='budget' or t['impact'].get('money_unknown',True) or t['impact'].get('money_usd') not in (0,0.0) for t in rows):
        raise tickets.TicketError('Hàng loạt chỉ cùng loại, đã xác minh không tốn tiền')
    return [{'id':t['id'],'title':t['title'],'revision':t['revision'],'state':t['state']} for t in rows]

def decide(conn,ident,decision,actor,reason,revision, *, new_due=None):
    """Server phải resolve actor từ session thật trước khi gọi service này."""
    t=tickets.get(conn,ident)
    if decision=='Gia hạn':
        if new_due is None: raise tickets.TicketError('Cần hạn mới')
        return tickets.extend_due(conn,ident,new_due,actor,reason,expected_revision=revision)
    choices=tickets.allowed_transitions(t)
    if decision=='Cần thêm thông tin': target='waiting_info'
    elif decision=='Từ chối': target='rejected'
    elif decision=='Duyệt':
        path=tickets.ACTION_PATH if t['kind'] in ('budget','shared_asset') else tickets.CODE_PATH
        target='closed' if t['state']=='rejected' else path[path.index(t['state'])+1] if t['state'] in path[:-1] else 'triaged'
    else: raise tickets.TicketError('Quyết định không hợp lệ')
    if target not in choices: raise tickets.TicketError('Quyết định không hợp lệ ở trạng thái này')
    return tickets.transition(conn,ident,target,actor,reason,t['state'],expected_revision=revision)

def action(t):
    if t['kind']=='budget': return 'duyệt nâng trần'
    if t['kind']=='shared_asset': return 'duyệt sửa Kho'
    return 'duyệt gộp' if t['state']=='waiting_merge' else 'giao bảo trì'

def render():
    st.title('Phiếu')
    if not features.on('support_tickets') or not features.on('tickets_admin_ui'):
        st.info('Trang phiếu đang tắt; chưa bật sản xuất.'); return
    st.warning('CHỈ ĐỌC: 8502 chưa có đăng nhập admin được xác thực phía server. Các quyết định bị khóa.')
    try:
        with read_connection() as conn: rows=queue(conn)
    except (sqlite3.Error,OSError,ValueError):
        st.error('Không đọc được kho phiếu; không khởi tạo hoặc sửa CSDL.'); return
    c1,c2=st.columns(2)
    kind=c1.selectbox('Loại',['Tất cả',*sorted(tickets.KINDS)],key='ticket_kind')
    project=c2.selectbox('Dự án',['Tất cả',*sorted({t['project_id'] for t in rows if t['project_id'] is not None})],key='ticket_project')
    linked=st.query_params.get('ticket')
    shown=[t for t in rows if (kind=='Tất cả' or t['kind']==kind) and (project=='Tất cả' or t['project_id']==project)]
    target=next((t for t in rows if t['id']==linked),None)
    if linked and target is None: st.info('Phiếu liên kết không tồn tại trong kho đang đọc.')
    if target:
        shown=[target]+[t for t in shown if t['id']!=linked]
        st.caption('Đang mở phiếu từ liên kết; phiếu này được giữ dù bộ lọc khác.')
    st.caption(f'{len(shown)} phiếu · một hàng cho mỗi fingerprint · không tự gửi tiền')
    for t in shown:
        due=tickets.due_status(t)
        remain=(tickets._time(t['due_at'])-tickets._time()).total_seconds()/3600
        money='chưa rõ' if t['impact'].get('money_unknown',True) else str(t['impact'].get('money_usd'))+' USD'
        summary=f"{t['title']} · dự án {t['project_id']} / shot {t['impact'].get('blocked_shots') or t['scene_id'] or '—'} · tiền {money} · {'quá hạn' if remain<=0 else 'còn'} {abs(remain):.0f} h · {action(t)} · {t['occurrences']} lần"
        (st.error if due=='red' else st.warning if due=='yellow' else st.info)(summary)
        cols=st.columns(4)
        for col,label in zip(cols,DECISIONS): col.button(label,key=f'ticket_{t["id"]}_{label}',disabled=True)
        with st.expander('Chi tiết: '+t['title'],expanded=t['id']==linked):
            st.write('Trạng thái: '+t['state']+' · người làm: '+str(t['assigned_to'] or 'chưa giao'))
            st.write('Hạn: '+t['due_at']+' · hạn gốc: '+t['original_due_at'])
            st.write('Cần: '+str(t['requested_action'] or action(t)))
            for name,field in [('Ảnh hưởng','impact'),('Nguyên nhân','cause'),('Gỡ tạm','workaround'),('Bằng chứng (job / mã test / hash)','evidence_refs'),('Kỹ thuật (file / test / nhánh / diff)','technical')]:
                st.write(name); st.json(t[field])
            if t['kind']=='budget':
                st.write('Nâng trần: trước / sau / trần dự án (USD)')
                st.json({k:t['impact'].get(k,'chưa rõ') for k in ('budget_before_usd','budget_after_usd','project_cap_usd')})
                st.caption('Duyệt phiếu chưa tự đổi trần hoặc chi tiền; cần adapter trần có xác thực.')
            st.selectbox('Lý do mẫu',REASONS,key=f'ticket_reason_{t["id"]}',disabled=True)
            st.text_input('Ghi thêm',key=f'ticket_note_{t["id"]}',disabled=True)
    st.multiselect('Xem trước hàng loạt',[t['id'] for t in shown],format_func=lambda i:next(t['title'] for t in shown if t['id']==i),key='ticket_bulk',disabled=True)
    st.caption('Hàng loạt chỉ cùng loại không tốn tiền và phải xem danh sách trước; hiện khóa vì thiếu xác thực server.')
