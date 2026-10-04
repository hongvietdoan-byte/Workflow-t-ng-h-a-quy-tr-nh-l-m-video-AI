"""S14.17 — mục gập "✏ Prompt đã sửa (vN)" trên thẻ ảnh Storyboard và thẻ clip Video (UI v2): so sánh prompt cũ/mới (bôi phần đổi), danh sách
thay đổi của Đạo diễn, lý do, nút "↩ Dùng lại prompt cũ" (không tốn tiền). Chỉ hiện khi shot có phiên bản do Đạo diễn viết lại
(core/prompt_rewrite.py) và prompt hiện tại vẫn là bản đã lưu cuối. Khóa widget mới: pvrevert_<kind>_<scene_id>."""
import contextlib
from html import escape

import streamlit as st

from core import prompt_rewrite

_STYLE = {"del": "background:rgba(220,60,60,.18);text-decoration:line-through;", "ins": "background:rgba(40,170,90,.22);"}


WAIT_TEXT = "Đạo diễn đang viết lại prompt… (tối đa khoảng 3 phút; lỗi / quá giờ thì gen lại theo cách cũ, ghi chú của bạn giữ nguyên)"


REVERT_WARNING = ("⚠ Đổi prompt về bản cũ: lần gen sau dùng bản này. Nếu shot đã có ảnh / clip ĐÃ DUYỆT làm từ prompt hiện tại, bản đó sẽ bị coi là "
                  "cũ và chạy tự động / nút “Gen” sẽ làm lại nó — TỐN TIỀN (trừ khi đã có lần gen đang chờ cho shot).")


def busy():
    """A spinner while a reject / redo may wait for the Director (flag director_rewrite on); otherwise nothing."""
    from core import features
    return st.spinner(WAIT_TEXT) if features.on("director_rewrite") else contextlib.nullcontext()


def spin(fn):
    """Wrap a button action (passed to act()) so it runs under busy()."""
    def run():
        with busy():
            return fn()
    return run


def diff_html(old: str, new: str) -> str:
    """Old → new prompt, word by word: removed words struck through red, added words green (escaped HTML)."""
    out = []
    for op, text in prompt_rewrite.word_diff(old, new):
        t = escape(text)
        out.append(f'<span style="{_STYLE[op]}">{t}</span>' if op in _STYLE else t)
    return '<div style="font-size:.85rem;line-height:1.45;white-space:pre-wrap">' + "".join(out) + "</div>"


def panel(p, scene_id: int, kind: str, act=None) -> bool:
    """Draw the panel for one shot (kind 'image' | 'video'). Returns True when something was shown."""
    vers = prompt_rewrite.live_versions(p.conn, scene_id, kind)
    if not any(v["source"] == "director_rewrite" for v in vers):
        return False
    last = vers[-1]
    if last["source"] != "director_rewrite":                       # reverted: say which prompt is in use, nothing to compare
        st.caption(f"↩ Đang dùng prompt cũ (v{last['version']}) — Đạo diễn từng sửa prompt shot này")
        return True
    prev = vers[-2] if len(vers) > 1 else {"prompt": "", "version": 0}
    with st.expander(f"✏ Prompt đã sửa (v{last['version']})", expanded=False):
        st.caption(f"Đạo diễn viết lại prompt {'ảnh' if kind == 'image' else 'motion'} trước lần gen lại — v{prev['version']} → "
                   f"v{last['version']} (đỏ gạch = bỏ, xanh = thêm)")
        st.markdown(diff_html(prev["prompt"], last["prompt"]), unsafe_allow_html=True)
        if last.get("changed"):
            st.markdown("\n".join(f"- {c}" for c in last["changed"]))
        if last.get("why"):
            st.caption("Lý do: " + str(last["why"]))
        if last.get("note"):
            st.caption("Theo: " + str(last["note"])[:300])
        st.caption(REVERT_WARNING)
        ok = st.checkbox("Tôi hiểu, vẫn dùng lại prompt cũ", key=f"pvrevack_{kind}_{scene_id}")
        if st.button("↩ Dùng lại prompt cũ", key=f"pvrevert_{kind}_{scene_id}", disabled=not ok,
                     help="Bản thân nút này không gọi Claude, không tạo job — nhưng đọc cảnh báo bên trên."):
            run = act or (lambda fn, msg="": (fn(), True)[1])
            if run(lambda: prompt_rewrite.revert(p, scene_id, kind), "Đã dùng lại prompt cũ — gen lại khi bạn muốn"):
                st.rerun()
    return True
