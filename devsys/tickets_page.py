"""Trang phiếu admin trên 8502.

Chưa đăng nhập (hoặc không phải Owner): CHỈ ĐỌC. Owner đăng nhập qua devsys/admin_auth (phiên trong CSDL, kiểm phía server mỗi lần
chạy trang): các quyết định gọi service ở đây với danh tính đọc từ CSDL — không bao giờ nhận actor/role từ trình duyệt/session_state.
"""
import sqlite3
from datetime import timedelta
import streamlit as st
from core import features, tickets

DECISIONS=('Duyệt','Từ chối','Cần thêm thông tin','Gia hạn')
REASONS=('Đã kiểm bằng chứng','Cần bổ sung ca thật','Chưa đúng phạm vi','Cần thêm thời gian')

from devsys.admin_auth import read_connection  # noqa: E402 — một nguồn đường dẫn CSDL

def queue(conn, *, now=None, kind=None, project=None):
    out=tickets.list_tickets(conn)
    for t in out:
        t['occurrences']=conn.execute("SELECT count(*) FROM ticket_events WHERE ticket_id=? AND (transition IN ('open','merge') OR transition IN ('closed->reopened','resolved->reopened'))",(t['id'],)).fetchone()[0]
    def priority(t):
        if t['state'] in tickets.DONE_STATES: return (4,t['due_at'],t['id'])
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
        target=next(iter(choices)) if t['state'] in ('blocked','waiting_info') else 'closed' if t['state']=='rejected' else path[path.index(t['state'])+1] if t['state'] in path[:-1] else 'triaged'
    else: raise tickets.TicketError('Quyết định không hợp lệ')
    if target not in choices: raise tickets.TicketError('Quyết định không hợp lệ ở trạng thái này')
    return tickets.transition(conn,ident,target,actor,reason,t['state'],expected_revision=revision)

def action(t):
    if t['kind']=='budget': return 'duyệt nâng trần'
    if t['kind']=='shared_asset': return 'duyệt sửa Kho'
    return 'duyệt gộp' if t['state']=='waiting_merge' else 'giao bảo trì'

def consume_ticket_link(query, session, enabled):
    """Chỉ dùng link khi mở trang; xóa tham số để lần đổi sidebar kế tiếp có hiệu lực."""
    if enabled and query.get('ticket'):
        session['ticket_focus'] = query.get('ticket')
        del query['ticket']
        return True
    return False

def due_text(t, now=None):
    at = tickets._time(now)
    due = tickets._time(t['due_at'])
    hours = (due-at).total_seconds()/3600
    detail = 'đã xong' if t['state'] in tickets.DONE_STATES else f"{'quá' if hours<=0 else 'còn'} {abs(hours):.1f} h"
    return due.astimezone(tickets.VN_TIME).strftime('%d/%m %H:%M')+' (giờ VN) · '+detail

def evidence_text(refs):
    names={'job_ids':'job','sent_job_ids':'job đã gửi','diag_ids':'chẩn đoán','test_ids':'test','artifacts':'tệp bằng chứng','hashes':'mã hash'}
    return '; '.join(names.get(k,str(k))+': '+', '.join(map(str,v if isinstance(v,list) else [v])) for k,v in refs.items()) or 'chưa có'

def impact_text(t):
    impact=t['impact']
    parts=[]
    for field,label in [('blocked_projects','chặn dự án'),('blocked_shots','chặn shot')]:
        if impact.get(field): parts.append(label+' '+', '.join(map(str,impact[field])))
    return ('; '.join(parts) or 'chưa ghi nhận chặn sản xuất')+'; tiền '+tickets.money_text(t)

def cause_text(t):
    cause=t['cause']
    return ('đã xác nhận' if cause.get('confidence')=='confirmed' else 'đoán')+' — '+str(cause.get('summary') or 'chưa rõ')+'; bằng chứng: '+evidence_text(cause.get('evidence_refs') or t['evidence_refs'])

def _apply(t, label, admin, reason, items):
    """Một quyết định của Owner: ghi qua service (CAS theo revision của LẦN VẼ có nút được bấm — khóa nút mang revision), rồi chuyển
    sang phiếu kế (nhớ trong session, không ghi lên địa chỉ để thanh bên vẫn đổi trang được)."""
    from devsys import admin_auth
    try:
        with admin_auth.write_connection() as conn:
            new_due = None
            if label == 'Gia hạn':        # phiếu đã quá hạn lâu: tính từ bây giờ, không từ hạn cũ (hạn mới phải muộn hơn hiện tại)
                new_due = (max(tickets._time(t['due_at']), tickets._time()) + timedelta(hours=24)).isoformat()
            decide(conn, t['id'], label, admin, reason, t['revision'], new_due=new_due)
    except (tickets.TicketError, sqlite3.Error, OSError) as e:
        st.session_state['ticket_flash'] = ('error', f'{t["title"]}: {e}')
        st.rerun()
    st.session_state['ticket_flash'] = ('success', f'{label}: {t["title"]}')
    nxt = next_ticket(items, t['id'])
    if nxt and nxt != t['id']:
        st.session_state['ticket_focus'] = nxt
    st.rerun()

def render():
    from devsys import admin_auth
    st.title('Phiếu')
    if not features.on('support_tickets') or not features.on('tickets_admin_ui'):
        st.info('Trang phiếu đang tắt; chưa bật sản xuất.'); return
    who = admin_auth.current()
    admin = who if admin_auth.is_owner(who) else None
    if admin:
        c1, c2 = st.columns([4, 1])
        c1.success(f'Đã đăng nhập Owner: {admin.email} — quyết định ghi thật (có lý do, ghi vết, không tự chi tiền).')
        if c2.button('Đăng xuất', key='ticket_logout'):
            admin_auth.sign_out(); st.rerun()
    else:
        st.warning('CHỈ ĐỌC: ' + ('tài khoản này không phải Owner — chỉ Owner duyệt phiếu.' if who else
                                  'đăng nhập Owner (cùng tài khoản Dashboard) để duyệt.'))
        if not who:
            admin_auth.login_box('ticket_login')
    if st.session_state.pop('ticket_bulk_clear', False):
        st.session_state.pop('ticket_bulk', None)
    flash = st.session_state.pop('ticket_flash', None)
    if flash:
        (st.success if flash[0] == 'success' else st.error)(flash[1])
    try:
        with read_connection() as conn: rows=queue(conn)
    except (sqlite3.Error,OSError,ValueError):
        st.error('Không đọc được kho phiếu; không khởi tạo hoặc sửa CSDL.'); return
    c1,c2=st.columns(2)
    kind=c1.selectbox('Loại',['Tất cả',*sorted(tickets.KINDS)],key='ticket_kind')
    project=c2.selectbox('Dự án',['Tất cả',*sorted({t['project_id'] for t in rows if t['project_id'] is not None})],key='ticket_project')
    consume_ticket_link(st.query_params, st.session_state, True)
    linked=st.session_state.get('ticket_focus')
    focus=st.session_state.get('ticket_focus') or linked
    shown=[t for t in rows if (kind=='Tất cả' or t['kind']==kind) and (project=='Tất cả' or t['project_id']==project)]
    target=next((t for t in rows if t['id']==linked),None)
    if linked and target is None: st.info('Phiếu liên kết không tồn tại trong kho đang đọc.')
    if target:
        shown=[target]+[t for t in shown if t['id']!=linked]
        st.caption('Đang mở phiếu từ liên kết; phiếu này được giữ dù bộ lọc khác.')
    st.caption(f'{len(shown)} phiếu · một hàng cho mỗi fingerprint · không tự gửi tiền')
    open_items=[t for t in shown if t['state'] not in tickets.DONE_STATES]
    for t in shown:
        due=tickets.due_status(t)
        money=tickets.money_text(t)
        summary=f"{t['title']} · dự án {t['project_id']} / shot {t['impact'].get('blocked_shots') or t['scene_id'] or '—'} · tiền {money} · {due_text(t)} · {action(t)} · {t['occurrences']} lần"
        (st.error if due=='red' else st.warning if due=='yellow' else st.info)(summary)
        allowed=set(tickets.allowed_transitions(t)) if admin else set()
        usable={'Duyệt': bool(admin) and t['state']!='closed', 'Từ chối': 'rejected' in allowed,
                'Cần thêm thông tin': 'waiting_info' in allowed, 'Gia hạn': bool(admin) and t['state']!='closed'}
        reason_key=f'ticket_reason_{t["id"]}'; note_key=f'ticket_note_{t["id"]}'
        cols=st.columns(4)
        for col,label in zip(cols,DECISIONS):
            # khóa nút mang revision: phiếu đổi (người khác duyệt / bấm đúp) thì cú bấm cũ không còn nút nào nhận
            if col.button(label,key=f'ticket_{t["id"]}_{t["revision"]}_{label}',disabled=not usable[label]):
                picked_reason=st.session_state.get(reason_key,REASONS[0])
                if label=='Gia hạn' and picked_reason==REASONS[0]: picked_reason='Cần thêm thời gian'
                reason=picked_reason+(' — '+st.session_state[note_key] if st.session_state.get(note_key) else '')
                _apply(t,label,admin,reason,open_items)
        with st.expander('Chi tiết: '+t['title'],expanded=t['id']==focus):
            st.write('Trạng thái: '+t['state']+' · người làm: '+str(t['assigned_to'] or 'chưa giao'))
            st.write('Hạn: '+due_text(t)+' · hạn gốc: '+tickets._time(t['original_due_at']).astimezone(tickets.VN_TIME).strftime('%d/%m %H:%M')+' (giờ VN)')
            st.write('Cần: '+str(t['requested_action'] or action(t)))
            st.text('Ảnh hưởng: '+impact_text(t))
            st.text('Nguyên nhân: '+cause_text(t))
            st.text('Bằng chứng: '+evidence_text(t['evidence_refs']))
            for name,field in [('Gỡ tạm','workaround'),('Kỹ thuật (file / test / nhánh / diff)','technical')]:
                st.write(name); st.json(t[field])
            if t['kind']=='budget':
                st.write('Nâng trần: trước / sau / trần dự án (USD)')
                st.json({k:t['impact'].get(k,'chưa rõ') for k in ('budget_before_usd','budget_after_usd','project_cap_usd')})
                st.caption('Duyệt phiếu chưa tự đổi trần hoặc chi tiền; cần adapter trần có xác thực.')
            st.selectbox('Lý do mẫu',REASONS,key=reason_key,disabled=not admin)
            st.text_input('Ghi thêm',key=note_key,disabled=not admin)
    picked=st.multiselect('Xem trước hàng loạt',[t['id'] for t in shown],format_func=lambda i:next(t['title'] for t in shown if t['id']==i),key='ticket_bulk',disabled=not admin)
    if admin and picked:
        try:
            with read_connection() as conn: preview=bulk_preview(conn,picked)
        except tickets.TicketError as e:
            st.warning(str(e))
        else:
            st.table([{'Phiếu':r['title'],'Trạng thái':r['state']} for r in preview])
            stamp='_'.join(f"{r['id']}-{r['revision']}" for r in preview)          # đúng danh sách + revision đã xem
            if st.button(f'Duyệt {len(preview)} phiếu đã xem', key=f'ticket_bulk_apply_{stamp}'):
                done,errors=0,[]
                try:
                    with admin_auth.write_connection() as conn:
                        for r in preview:
                            try:
                                decide(conn,r['id'],'Duyệt',admin,'Duyệt hàng loạt — '+REASONS[0],r['revision']); done+=1
                            except tickets.TicketError as e: errors.append(f"{r['title']}: {e}")
                except (sqlite3.Error,OSError) as e:
                    errors.append(f'CSDL: {e}')
                msg=f'Đã ghi {done}/{len(preview)} phiếu' + (' — lỗi: '+'; '.join(errors) if errors else '')
                st.session_state['ticket_flash']=('error' if errors else 'success',msg)
                st.session_state['ticket_bulk_clear']=True
                st.rerun()
    st.caption('Hàng loạt chỉ cùng loại không tốn tiền và phải xem danh sách trước.' + ('' if admin else ' Hiện khóa — cần Owner đăng nhập.'))
