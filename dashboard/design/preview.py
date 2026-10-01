"""G1 — lát cắt dọc THẬT của giao diện v2 (đợt S13): dựng bằng chính Streamlit trên Dashboard thật, mở bằng ?step=design (cờ ui_v2 bật).
Có đủ mọi loại thành phần sẽ dùng ở các màn: hero + thống kê, lưới khung thẻ kính có nút, pill/nhãn duyệt, dải phiên bản, thanh tiến độ,
hộp thoại, bảng HTML, trạng thái rỗng / lỗi / đang chạy, thanh hành động dính. Dữ liệu là mẫu nhưng đủ lớn (12 khung, tên dài) để thấy giới hạn thật."""
import io
import random

import streamlit as st

from dashboard.design import components as D


def _frame_png(i: int, w: int = 360, h: int = 640) -> bytes:
    """A gradient 'frame' picture so the grid has real images (no files needed)."""
    from PIL import Image, ImageDraw
    rnd = random.Random(i)
    a = tuple(rnd.randint(30, 120) for _ in range(3))
    b = tuple(rnd.randint(90, 230) for _ in range(3))
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        row = tuple(int(a[k] * (1 - t) + b[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(img)
    d.ellipse((w * .3, h * .22, w * .7, h * .5), fill=(255, 255, 255))
    d.text((12, 10), f"Khung {i}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


SAMPLE_FRAMES = [
    (1, "approved", "Kelly vào sân thượng, nhìn xuống thành phố đêm", 0.94, 3), (2, "approved", "Kenta xuyên tường", 0.91, 2),
    (3, "review", "Maxim chặn lối ra — tay phải sai chiều?", 0.82, 2), (4, "working", "Orion tung kỹ năng Huyết Cầu Bảo Hộ", 0.0, 1),
    (5, "review", "Cận Kenta (mặt sáng, mũ đúng)", 0.88, 1), (6, "rejected", "Toàn cảnh tháp đồng hồ — thừa người", 0.51, 4),
    (7, "failed", "Shot 7 · lỗi nhà cung cấp 429", 0.0, 1), (8, "queued", "Shot 8 chờ gen", 0.0, 1),
    (9, "approved", "Cận Kelly cười", 0.93, 2), (10, "review", "Hai người đối mặt, ánh sáng đêm", 0.79, 3),
    (11, "working", "Chuyển cảnh lia nhòe", 0.0, 1), (12, "approved", "Kết: logo + CTA", 0.96, 1)]


def render() -> None:
    st.markdown("### 🧪 G1 — lát cắt dọc giao diện v2 (dữ liệu mẫu, widget thật)")
    st.caption("Trang này chỉ để duyệt giao diện. Bấm các nút để thử trạng thái thật của Streamlit (nút không làm gì ngoài thông báo).")

    with D.hero("demo"):
        st.markdown(D.hero_html("Thử 02/10 — kịch bản mới", "Kenta + Orion · 60 s · TikTok 9:16 · mức Duyệt cổng chính",
                                [("Chờ bạn", "warn"), ("12 khung", "info"), ("Ngân sách đã khóa", "ok")]), unsafe_allow_html=True)
        c = st.columns(4)
        c[0].markdown(D.stat("Đã duyệt", "4 / 12", "33 %"), unsafe_allow_html=True)
        c[1].markdown(D.stat("Chi / trần", "3,12 / 9,40 USD"), unsafe_allow_html=True)
        c[2].markdown(D.stat("Cần bạn", "3 việc"), unsafe_allow_html=True)
        c[3].markdown(D.stat("Còn khoảng", "12 phút"), unsafe_allow_html=True)
        st.markdown(D.meter(4 / 12, "Tiến độ storyboard"), unsafe_allow_html=True)
        st.markdown(D.meter(0.33, "Tiền đã chi (đảo màu: đầy = xấu)", invert=True), unsafe_allow_html=True)

    st.markdown("#### Lưới khung (thẻ kính, nút hiện sẵn, dải phiên bản)")
    cols = st.columns(4)
    for n, (i, state, title, qc, versions) in enumerate(SAMPLE_FRAMES):
        with cols[n % 4]:
            with D.card(f"frame-{i}"):
                if state in ("working", "queued"):
                    st.markdown(D.shimmer(260), unsafe_allow_html=True)
                else:
                    st.image(_frame_png(i), use_container_width=True)
                st.markdown(f"**{title}**")
                chips = D.frame_state_pill(state)
                if qc:
                    chips += " " + D.pill(f"QC {qc:.2f}", "ok" if qc >= 0.85 else "warn" if qc >= 0.7 else "bad")
                st.markdown(chips, unsafe_allow_html=True)
                st.markdown('<div class="v2-vers">' + "".join(f'<span class="v2-ver{" on" if v == versions else ""}">v{v}</span>'
                                                              for v in range(1, versions + 1)) + "</div>", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                if b1.button("✔ Duyệt", key=f"v2d_ok_{i}", type="primary", disabled=state in ("approved", "queued", "working")):
                    st.toast(f"Đã duyệt khung {i} (mẫu)")
                if b2.button("↻ Vẽ lại", key=f"v2d_redo_{i}", disabled=state in ("queued", "working")):
                    st.toast(f"Vẽ lại khung {i} (mẫu)")
                b3, b4 = st.columns(2)
                b3.button("✖ Loại", key=f"v2d_no_{i}", disabled=state in ("queued", "working"))
                b4.button("✎ Sửa", key=f"v2d_ed_{i}")

    st.markdown("#### Trạng thái: rỗng · lỗi · đang chạy · cảnh báo")
    s1, s2, s3 = st.columns(3)
    s1.markdown(D.empty_state("Chưa có clip nào", "Duyệt storyboard để gửi video — bấm “Duyệt storyboard” ở thanh dưới."), unsafe_allow_html=True)
    s2.error("ClipAI từ chối ảnh khung 7: tỉ lệ 3.74 ngoài 0.39–2.50. Chưa tốn tiền — đổi ảnh rồi gửi lại.")
    with s3:
        st.markdown(D.pill("Đang vẽ khung 4", "info", running=True) + " " + D.pill("đã chờ 02:14", "mute"), unsafe_allow_html=True)
        st.markdown(D.shimmer(70), unsafe_allow_html=True)
    st.warning("Ngân sách Claude chỉ còn 8 % — nạp thêm ở 💵 trước khi chạy tiếp.")

    st.markdown("#### Bảng (HTML, nền theo giao diện) và tab")
    t1, t2 = st.tabs(["Bảng chi tiêu", "Bảng gốc của Streamlit (để so sánh)"])
    rows = [("Ảnh", "3,10", "4,00", D.pill("ok", "ok")), ("Video", "5,10", "9,00", D.pill("chờ", "warn")), ("Claude", "2,60", "2,00", D.pill("vượt", "bad"))]
    with t1:
        st.markdown('<table class="v2-table"><tr><th>Khâu</th><th>Đã chi</th><th>Trần</th><th>Trạng thái</th></tr>'
                    + "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows) + "</table>", unsafe_allow_html=True)
    with t2:
        st.dataframe([{"Khâu": a, "Đã chi": b, "Trần": c} for a, b, c, _ in rows], hide_index=True)
        st.caption("Bảng gốc vẽ bằng canvas nên giữ nền sáng — vì vậy bảng quan trọng dùng bản HTML bên cạnh.")

    st.markdown("#### Hộp thoại, ô nhập, mục gập")
    with st.expander("Tinh chỉnh (mục gập)", expanded=False):
        st.text_input("Tên dự án", "Thử 02/10", key="v2d_name")
        st.selectbox("Mức tự động", ["Tôi duyệt hết", "Duyệt cổng chính", "Tự chạy trong trần"], index=1, key="v2d_level")
        st.checkbox("Dừng ở storyboard trước khi gen video", True, key="v2d_gate")
    if st.button("Mở hộp thoại mẫu", key="v2d_dlg_btn"):
        _dialog()

    with st.container(key="sticky-actions"):
        with D.card("actionbar"):
            a1, a2, a3 = st.columns([3, 1, 1])
            a1.markdown("**3 khung cần duyệt** · phím tắt chưa có (Streamlit không có sẵn) — nút luôn hiện nhãn chữ.")
            a2.button("✖ Loại hết", key="v2d_bulk_no")
            a3.button("✔ Duyệt cả loạt", key="v2d_bulk_ok", type="primary")


@st.dialog("Hộp thoại mẫu")
def _dialog() -> None:
    st.markdown(D.hero_html("Khóa ngân sách", "Sau khi khóa, mọi lời gọi trả tiền vượt trần sẽ dừng.", [("≈ 9,40 USD", "info")]), unsafe_allow_html=True)
    st.text_area("Lý do (bắt buộc)", key="v2d_reason")
    st.button("✔ Duyệt & khóa", key="v2d_lock", type="primary")
