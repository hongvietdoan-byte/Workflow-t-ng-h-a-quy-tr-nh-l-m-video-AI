"""08/10 (#24 shot 7): nút "↩ Dùng bản này" ở bản CŨ của một shot (dải v1…vN của thẻ ảnh, bản khác của clip ở Bước 4).

Bấm → `Pipeline.use_older_take`: tệp bản cũ về chỗ cũ (lấy lại từ thùng rác nếu cần), các bản mới hơn bị loại/hủy (không gen lại),
bản cũ được duyệt. Không tốn tiền. Bản mới nhất đang ĐÃ DUYỆT → hỏi xác nhận trước (bỏ duyệt nó).
Tách riêng file này để storyboard_cards.py / step2.py / step4.py chỉ thêm một dòng gọi (dễ gộp với nhánh khác)."""
import streamlit as st

from dashboard import common as C

USABLE = ("rejected", "succeeded", "pending_review")


def _has_file(p, job) -> bool:
    if job["type"] == "image_gen":
        return bool(C.job_image(job["project_id"], job["id"]))
    from core import takes, trash
    return takes.has_own_file(p.conn, job) or bool(trash.find_for_job(C.DATA, job["project_id"], "videos", job["id"]))


def use_button(p, job, latest, version: int = None, label: str = "↩ Dùng bản này", key: str = None) -> None:
    """Nút dùng lại `job` thay cho `latest` (bản mới nhất / đang dùng của shot). Không hiện khi bản này không dùng lại được."""
    if job is None or job["state"] not in USABLE or (latest is not None and latest["id"] == job["id"]) or not _has_file(p, job):
        return
    jid = job["id"]
    key = key or f"uot_{jid}"
    version = version or p.take_version(jid)
    what = "ảnh" if job["type"] == "image_gen" else "clip"
    help_text = (f"Duyệt lại bản v{version} cho shot (lấy tệp từ thùng rác nếu cần); các bản mới hơn bị loại/hủy, không gen lại — "
                 "không tốn tiền.")

    def run():
        if C.act(lambda: p.use_older_take(jid, data_dir=C.DATA), f"Đã dùng lại {what} bản v{version}"):
            st.session_state.pop(f"{key}_ask", None)
            st.rerun()

    if st.button(label, key=key, width="stretch", help=help_text):
        if latest is not None and latest["state"] == "approved":
            st.session_state[f"{key}_ask"] = True
        else:
            run()
    if st.session_state.get(f"{key}_ask"):
        st.warning(f"Bản mới nhất (v{p.take_version(latest['id'])}) đang ĐÃ DUYỆT — dùng bản v{version} sẽ bỏ duyệt bản đó "
                   "(không gen lại). Tiếp tục?")
        a, b = st.columns(2, gap="small")
        if a.button("Có, dùng bản này", key=f"{key}_yes", type="primary", width="stretch"):
            run()
        if b.button("Không", key=f"{key}_no", width="stretch"):
            st.session_state.pop(f"{key}_ask", None)
            st.rerun()
