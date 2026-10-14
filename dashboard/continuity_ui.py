"""Đ18 việc 3: ô giữ bố cục, dùng chung Bước 1/2; không tự gen ảnh."""
import json
from pathlib import Path
import streamlit as st
from core import access, features, llm_io
from core.runner import layout_frame_job


def options(p, pid, idx):
    access.need_view(p, pid, 'xem bố cục')
    rows = [dict(r) for r in p.conn.execute('SELECT idx,data FROM scenes WHERE project_id=? ORDER BY idx',(pid,))]
    current = next((json.loads(r['data'] or '{}') for r in rows if r['idx']==idx), {})
    place = current.get('location_asset') or current.get('location')
    previous = [r for r in rows if r['idx'] < idx]
    previous.sort(key=lambda r: (not bool(place and (json.loads(r['data'] or '{}').get('location_asset') or json.loads(r['data'] or '{}').get('location'))==place),r['idx']))
    # llm_io.update_scene nhận cả shot ĐỨNG SAU (#27: shot 15/17 giữ bố cục theo shot 18) → các shot sau xếp cuối danh sách.
    return previous + [r for r in rows if r['idx'] > idx]


def preview(p, pid, idx, data_dir):
    access.need_view(p,pid,'xem ảnh bố cục')
    row=layout_frame_job(p.conn,pid,{'continuity_from':idx})
    path=Path(data_dir)/str(pid)/'images'/f"job_{row['id']}.png" if row else None
    if not path or not path.is_file(): return None,'chưa có ảnh',True
    return str(path), ('đã duyệt' if row['state']=='approved' else 'chờ duyệt'), row['state']!='approved'


def save(p,pid,idx,source):
    return llm_io.update_scene(p,pid,idx,{'continuity_from':source})


def render(p,pid,idx,scope,read_only=False):
    if not features.on('continuity_from_ui'): return
    from dashboard import common as C
    access.need_view(p,pid,'xem bố cục')
    row=p.conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=?',(pid,idx)).fetchone()
    if row is None: return
    current=json.loads(row['data'] or '{}').get('continuity_from')
    if not (current is None or (isinstance(current,int) and not isinstance(current,bool))):
        try: current=int(current)   # dữ liệu viết tay/Đạo diễn lỡ để chuỗi: so số không vỡ thẻ
        except (TypeError,ValueError): current=None
    rows=options(p,pid,idx)
    choices=[None]+[r['idx'] for r in rows]
    if current is not None and current not in choices:
        choices.append(current)  # nguồn đã mất: hiện rõ + cho bỏ, không âm thầm đổi dữ liệu
    disabled=read_only or C.read_only(p,pid)
    key=f'continuity_{scope}_{pid}_{idx}'
    a,b=st.columns([5,1],vertical_alignment='bottom')
    picked=a.selectbox('Giữ bố cục theo shot …',choices,index=choices.index(current),
        format_func=lambda v: 'Không giữ theo shot khác' if v is None else f'Shot {v}'+(' · ở phía sau' if v>idx else ''),
        key=key,disabled=disabled,help='Shot trước cùng địa điểm lên đầu, shot đứng sau ở cuối. Đổi lựa chọn rồi bấm Lưu bố cục; không tự gen ảnh.')
    if b.button('Bỏ',key=key+'_remove',disabled=disabled or current is None):
        if C.act(lambda: save(p,pid,idx,None),'Đã bỏ giữ bố cục'):
            del st.session_state[key]
            st.rerun()
    if picked!=current and st.button('Lưu bố cục',key=key+'_save',disabled=disabled):
        if C.act(lambda: save(p,pid,idx,picked),'Đã lưu giữ bố cục'): st.rerun()
    if picked is not None:
        path,label,yellow=preview(p,pid,picked,C.DATA)
        if path: st.image(path,width=144)
        message=f'Shot {picked} · {label}'
        if yellow:
            from core import layout_follow
            waiting=layout_follow.wait_reason(p.conn,pid,{'continuity_from':picked}) if features.on('layout_from_follow') else None
            st.warning(message+' — '+(waiting or 'cảnh báo VÀNG; thiếu ảnh thì chưa gửi được bố cục.'))
        else: st.caption(message)
