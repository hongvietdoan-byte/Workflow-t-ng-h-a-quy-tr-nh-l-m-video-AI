"""Bản đồ shot × khâu ngay dưới thanh bước (Đợt 3 tab kiểu chat; cờ chat_first — core/stage_map.py). Gập: một dòng "khâu đang làm" +
số xong mỗi khâu (đủ, không thừa); mở: lưới shot × Ảnh · Motion · Video, mỗi ô một nhãn màu (xong · chờ duyệt · đang gen · cũ · lỗi · chưa làm)."""
from html import escape

import streamlit as st

from core import stage_map as M
from dashboard.design import components as D

KIND = {"done": "ok", "review": "info", "running": "info", "stale": "warn", "failed": "bad", "none": "mute"}


def render(conn, pid: int) -> None:
    from core import chat_intake
    if not chat_intake.enabled():
        return
    rows = M.build(conn, pid)
    if not rows:
        return
    s = M.summary(rows)
    names = dict(M.STAGES)
    counts = " · ".join(f"{names[k]} {d}/{t}" for k, (d, t) in s["counts"].items())
    head = f"🗺 Tiến độ {len(rows)} shot: {counts}" + (f" — đang ở khâu **{names[s['current']]}**" if s["current"] else " — xong cả 3 khâu")
    with st.expander(head, expanded=False):
        cols = "".join(f"<th>{'▶ ' if k == s['current'] else ''}{escape(n)}</th>" for k, n in M.STAGES)
        body = "".join(
            f"<tr><td><b>Shot {r['idx']}</b></td>" + "".join(
                f"<td>{D.pill(M.STATE_LABEL[r[k]], KIND[r[k]], running=r[k] == 'running')}</td>" for k, _ in M.STAGES) + "</tr>"
            for r in rows)
        legend = " ".join(D.pill(M.STATE_LABEL[k], KIND[k]) for k in ("done", "review", "running", "stale", "failed", "none"))
        st.html(f'<div class="stage-map"><table style="width:100%;border-collapse:separate;border-spacing:0 6px">'
                f'<tr style="text-align:left"><th>Shot</th>{cols}</tr>{body}</table>'
                f'<div style="margin-top:8px;opacity:.85">{legend}</div></div>')
