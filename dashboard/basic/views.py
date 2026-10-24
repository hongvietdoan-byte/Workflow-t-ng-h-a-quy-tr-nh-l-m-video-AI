"""Năm màn Cơ bản độc lập; chưa gắn vào entrypoint production (pha B)."""
import streamlit as st

from core import cost, simple_budget
from dashboard import paid_confirm
from . import actions, model

STYLE = """<style>
[data-testid=stMainBlockContainer]{max-width:1160px;}
[data-testid=stMarkdownContainer] p,[data-testid=stMarkdownContainer] h3{overflow-wrap:anywhere;}
[data-testid=stButton] button{white-space:normal;max-width:100%;}
@media(max-width:600px){[data-testid=stMainBlockContainer]{padding:1rem;}}
</style>"""


def _act(fn, done):
    try:
        fn()
    except (PermissionError, ValueError):
        st.warning("Đang giữ — quyền, đầu vào hoặc báo giá đã đổi. Xem lại trước khi xác nhận.")
        return False
    except Exception:
        st.error("Chưa hoàn tất thao tác. Máy đã dừng; bạn có thể giữ bản hiện tại và báo kỹ thuật.")
        return False
    st.success(done)
    return True


def money_top(status):
    if status["approved"]:
        label = f"Hạn mức tự động: {status['recorded']:.2f} / {status['limit']:.2f} USD"
    else:
        label = "Hạn mức tự động: chưa có hạn mức"
    with st.expander(label):
        st.caption("Hạn mức chi của luồng tự động · thao tác tay vượt chỉ cảnh báo")
        st.write(f"Đã ghi nhận {status['recorded']:.2f} USD · Đang giữ chỗ {status['held']:.2f} USD")
        for stage, usd in status["stages"].items():
            if usd:
                st.caption(f"{stage}: {usd:.2f} USD")
        st.caption("Ngân sách tự sửa và bộ đếm dùng chính sách hiện hành. Chưa có luồng tự động trả phí từ chế độ Cơ bản.")
    if status["ratio"] is not None:
        st.progress(min(1.0, status["ratio"]))
    if status["warning"]:
        st.warning("Đã dùng/giữ chỗ từ 80% hạn mức tự động. EP kiểm tra trước khi cho máy làm thêm.")


def idea_screen(p, pid, state):
    st.subheader("Bắt đầu từ một ý tưởng")
    st.caption("Ai, ở đâu, chuyện gì? Máy giữ ý tưởng để bạn hoàn thiện kịch bản.")
    idea = st.text_area("Ý tưởng của bạn", key=f"basic_idea_{pid}", height=110)
    if st.button("Gửi ý tưởng", key=f"basic_idea_save_{pid}", disabled=not state["can_edit"]):
        _act(lambda: actions.save_idea(p, pid, idea), "Đã lưu ý tưởng — chưa gọi dịch vụ trả phí")
    if not state["budget"]["approved"]:
        try:
            quote = simple_budget.proposal(p, pid)
        except Exception:
            quote = None
        if not quote or quote.get("incomplete") or not quote.get("total") or quote.get("qd3_complete") is not True:
            st.info("Đang giữ — dự toán chưa đủ mức xấu nhất và ngân sách tự sửa 40%; chưa cho duyệt hạn mức tự động.")
        else:
            st.caption(f"Hạn mức đề xuất (ước tính): {quote['total']:.2f} USD. Chỉ EP được duyệt.")
            confirmed = st.checkbox("Tôi xác nhận hạn mức chi của luồng tự động", key=f"basic_limit_confirm_{pid}")
            if st.button("Duyệt hạn mức tự động", key=f"basic_limit_approve_{pid}", disabled=not confirmed):
                _act(lambda: simple_budget.approve(p, pid, expected_total=quote["total"], confirmed=confirmed), "Đã duyệt hạn mức tự động")


def script_screen(p, pid, state):
    st.subheader("Đọc và góp ý kịch bản")
    idea = state["idea"]
    if idea.get("directions"):
        chosen = idea.get("chosen")
        for i, direction in enumerate(idea["directions"]):
            st.markdown(f"**{'Đang chọn · ' if chosen == i else ''}{direction.get('title', 'Hướng kịch bản')}**")
            st.write(direction.get("logline", ""))
        st.caption("Phương án khác: giữ các hướng đã có; hướng được EP khóa không tự đổi.")
    text = st.text_area("Kịch bản theo cảnh", value=state["project"].get("script_text") or idea.get("script") or "",
                        key=f"basic_script_{pid}", height=280)
    st.caption("“Được, làm tiếp” chỉ dùng kịch bản; không duyệt hồ sơ, sân khấu, chỉ dẫn chuyển động hay gửi API thay EP.")
    if st.button("Được, làm tiếp", key=f"basic_script_use_{pid}", disabled=not text or not state["can_edit"]):
        _act(lambda: actions.use_script(p, pid, text), "Đã dùng kịch bản; các cổng duyệt sau vẫn giữ nguyên")


def media_screen(p, pid, state, kind):
    noun, job_kind, counter, limit = ("Ảnh", "image_gen", "image_used", 3) if kind == "images" else ("Video", "video_gen", "video_used", 2)
    st.subheader(f"{noun} theo cảnh")
    for scene in state["scenes"]:
        with st.container(border=True):
            st.markdown(f"**Cảnh {scene['idx']} · {scene.get('title') or 'Chưa đặt tên'}**")
            used = scene[counter]
            st.caption(f"Lượt {'ảnh' if kind == 'images' else 'video'} {used}/{limit} · tính cả lượt đầu")
            if used >= limit:
                st.warning("Cảnh này đã dùng hết lượt — giữ bản tốt nhất hoặc xin EP xem thêm lượt")
            job = model.latest_job(state, scene["id"], job_kind)
            path = model.media_path(state["data_dir"], pid, job.get("result_path")) if job else None
            if path:
                (st.image if kind == "images" else st.video)(str(path))
            else:
                st.caption("Chưa có bản để xem; mục cần EP hoặc chưa đạt vẫn giữ chờ.")
            st.caption("Được · Sửa bằng lời · Đổi ảnh tham chiếu · Khác — các thao tác làm lại nối ở pha B.")
    if not state["scenes"]:
        st.info("Đang giữ — cần kịch bản và các cổng duyệt trước khi tạo ảnh/video.")
    if kind == "videos":
        st.info("Bản 1080p tự động: đang chờ xác minh. Chấp nhận chỉ dẫn chuyển động không đồng nghĩa gửi video.")
    st.caption("Trước cổng M8.4: chỉ người bấm gửi có báo giá và xác nhận; không máy tự gửi.")
    # Cổng giá/quyền của luồng hiện hành, không tạo đường gửi provider mới.
    try:
        quoted = actions.quote(p, pid, state["data_dir"], kind)
        amount = quoted["usd"]
    except Exception:
        quoted, amount = None, None
    tag = cost.price_tag(amount)
    blocked = not state["can_edit"] or bool(state["project"].get("paused")) or amount is None or not state["scenes"] or not paid_confirm.enabled()
    send_key = f"basic_send_{kind}_{pid}"
    if st.session_state.get(send_key + "_quote") != quoted:
        st.session_state.pop(paid_confirm.ASK_PREFIX + send_key, None)
        st.session_state[send_key + "_quote"] = quoted
    if paid_confirm.paid_button(f"Gửi làm {'ảnh' if kind == 'images' else 'video'}", key=send_key,
                                tag=tag, disabled=blocked):
        _act(lambda: actions.send(p, pid, state["data_dir"], kind, confirmed=True, expected_quote=quoted), "Đã xử lý lượt gửi bạn xác nhận")
    if not paid_confirm.enabled():
        st.info("Đang giữ — lớp xác nhận giá chưa bật; chưa có nút gửi hoạt động.")
    if not actions.selected_send_ready():
        st.info("Đang giữ cả lô — chờ bảo đảm đúng tập job gửi (CX24-M82B). Chưa gửi ảnh/video từ giai đoạn này.")
    if state["can_edit"] and paid_confirm.enabled():
        from dashboard import approve_preview
        ids = approve_preview.pending_ids(p.conn, pid, "images" if kind == "images" else "clips")
        approve_preview.approve_all_box(p, pid, "images" if kind == "images" else "clips", f"basic_approve_{kind}_{pid}",
                                        ids, "Duyệt hết — xem trước từng mục")


def download_screen(p, pid, state):
    st.subheader("Tải bản giao")
    st.checkbox("Có phụ đề", key=f"basic_subtitles_{pid}", disabled=True,
                help="Nối lựa chọn bản giao/phụ đề theo luồng hiện hành ở pha B")
    st.info("Xem bản ghép đã duyệt; chưa tự dựng hoặc tự dịch/gọi dịch vụ trả phí.")
    rows = p.conn.execute("SELECT * FROM deliveries WHERE project_id=? ORDER BY id DESC", (pid,)).fetchall()
    for row in rows:
        item = dict(row)
        path = model.media_path(state["data_dir"], pid, item.get("final_path") or item.get("path"))
        if path:
            st.video(str(path))
            st.download_button("Tải bản giao", path.read_bytes(), file_name=path.name, key=f"basic_download_{pid}_{item['id']}")
            return
    st.info("Đang giữ — chưa có bản giao hợp lệ trong thư mục dự án.")


def render_workspace(p, pid, data_dir):
    st.markdown(STYLE, unsafe_allow_html=True)
    try:
        state = model.load(p, pid, data_dir)
    except Exception:
        st.error("Không mở được dự án. Kiểm tra quyền truy cập và dữ liệu trước khi tiếp tục.")
        return
    st.title("Chế độ Cơ bản")
    st.caption(state["project"]["name"])
    money_top(state["budget"])
    paused = bool(state["project"].get("paused"))
    if st.button("Tiếp tục" if paused else "Tạm dừng", key=f"basic_pause_{pid}", disabled=not state["can_edit"]):
        if _act(lambda: actions.pause(p, pid, not paused), "Đã cập nhật trạng thái"):
            st.rerun()
    if paused:
        st.warning("Đã tạm dừng — không gửi job mới; job đang chạy chạy nốt, không bị hủy")
    selected = st.selectbox("Bước làm phim", model.SCREENS, key=f"basic_screen_{pid}")
    for card in model.issue_cards(state):
        with st.expander(card["what"]):
            st.write("Máy đã thử gì — " + card["tried"])
            st.write("Bạn chọn — " + card["choice"])
    if selected == model.SCREENS[0]:
        idea_screen(p, pid, state)
    elif selected == model.SCREENS[1]:
        script_screen(p, pid, state)
    elif selected in model.SCREENS[2:4]:
        media_screen(p, pid, state, "images" if selected == model.SCREENS[2] else "videos")
    else:
        download_screen(p, pid, state)
