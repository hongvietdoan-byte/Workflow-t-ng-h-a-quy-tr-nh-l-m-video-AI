"""📎 Đầu vào & tham chiếu (đợt 3, 01/10), at the top of the Kịch bản screen: the ways to start a project, and attaching pictures the
script should use (a new character, a place) without leaving the screen. Everything attached goes through core/assets.py, the same
Kho the Director / image prompts / QC already read — nothing new for the pipeline to learn.

Video-ref cover, dance cover and trend are plan S11 (docs/KE_HOACH_TINH_NANG_DIRECTOR_2026-10-01.md): shown as "sắp có", not clickable."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap  # noqa: F401  (v2: long captions become a one-line summary + ⓘ)
from core import assets

COMING = (("🎬 Làm theo video ref", "giữ cấu trúc + nhịp của video mẫu, viết lại lời, nhân vật FF — kế hoạch S11 (R-A)"),
          ("💃 Cover nhảy", "nhân vật FF nhảy theo động tác của video ref (chuyển sang dạng không mặt) — S11 (R-B)"),
          ("📈 Theo trend", "gợi ý từ thẻ trend đã duyệt (tùy chọn) — S11 (T)"))
PICK_KINDS = ("character", "location", "prop", "weapon", "pet")


def _summary(p: Pipeline, pid: int) -> str:
    chosen = assets.project_assets(p.conn, pid)
    by: dict = {}
    for a in chosen:
        by[a["kind_label"]] = by.get(a["kind_label"], 0) + 1
    return "đầu vào: kịch bản / ý tưởng · tham chiếu: " + (", ".join(f"{n} {k.lower()}" for k, n in by.items()) if by else "chưa gắn")


def inputs_and_refs(p: Pipeline, pid: int, has_script: bool) -> None:
    with ui.fold("📎 Đầu vào & tham chiếu", _summary(p, pid), f"refs_{pid}", default_open=not has_script,
                 sub="chọn cách bắt đầu · gắn ảnh nhân vật / nơi cho kịch bản") as opened:
        if not opened:
            return
        cols = st.columns(4)
        with cols[0].container(border=True):
            st.markdown("**📝 Kịch bản / ý tưởng**")
            cap("✔ đang dùng — dán, kéo file hoặc gõ ý thô ở 1a bên dưới (tự nhận dạng)")
        for col, (title, why) in zip(cols[1:], COMING):
            with col.container(border=True):
                st.markdown(f"**{title}**")
                cap(why)
                st.button("Sắp có", key=f"coming_{title[:2]}_{pid}", disabled=True, width="stretch")
        attach_form(p, pid)


def attach_form(p: Pipeline, pid: int) -> None:
    """The attached references + the form that adds one (keys ref_up_/ref_kind_/ref_name_/ref_shared_/ref_go_/ref_kho_)."""
    chosen = assets.project_assets(p.conn, pid)
    st.markdown("**🖼 Tham chiếu đang gắn cho dự án**")
    if chosen and ui.v2_on() and len(chosen) > 3:          # v2 (P3): one summary line + the whole list inside ⓘ
        from dashboard.design import components as D
        rows = [f"- **{a['kind_label']}** {a['name']} — {len(a['images'])} ảnh ("
                + ("chỉ dự án này" if a.get("project_id") else "Kho chung") + ")"
                + (f" · {len(a['pending'])} ảnh chờ duyệt" if a.get("pending") else "") for a in chosen]
        D.line(f'<span class="script-sum">{len(chosen)} tham chiếu đang gắn · '
               f'{sum(len(a["images"]) for a in chosen)} ảnh</span>', "\n".join(rows), f"script-refs-list-{pid}")
    elif chosen:
        for a in chosen[:12]:
            wait = f" · {len(a['pending'])} ảnh chờ duyệt" if a.get("pending") else ""
            scope = "chỉ dự án này" if a.get("project_id") else "Kho chung"
            cap(f"• **{a['kind_label']}** {a['name']} — {len(a['images'])} ảnh ({scope}){wait}")
        if len(chosen) > 12:
            cap(f"… và {len(chosen) - 12} mục nữa")
    else:
        cap("Chưa gắn gì — Director sẽ tự ghép nhân vật / nơi từ Kho theo tên trong kịch bản.")
    st.markdown("**➕ Gắn ảnh tham chiếu mới**")
    f1, f2, f3 = st.columns([2.4, 1.6, 2], vertical_alignment="bottom")
    files = f1.file_uploader("Ảnh (JPG / PNG / WebP)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                             key=f"ref_up_{pid}")
    kind = f2.selectbox("Là", PICK_KINDS, format_func=lambda k: assets.KINDS[k], key=f"ref_kind_{pid}")
    name = f3.text_input("Tên (vd: Orion, Sân thượng)", key=f"ref_name_{pid}")
    shared = st.checkbox("Lưu vào Kho chung (dùng lại ở mọi dự án — ảnh chờ duyệt trước khi pipeline dùng)", False, key=f"ref_shared_{pid}",
                         help="Bỏ chọn: chỉ dùng trong dự án này, dùng ngay.")
    if st.button("➕ Gắn vào dự án", key=f"ref_go_{pid}", disabled=not (files and name.strip()), type="primary"):
        def go():
            rep = assets.add_reference_images(p.conn, pid, p.project(pid)["game"] or "FF", kind, name, [(f.name, f.getvalue()) for f in files],
                                              shared, created_by=p.actor)
            msg = f"Đã gắn {rep['added']} ảnh cho “{name.strip()}”" + (" (chờ duyệt ở Kho)" if shared and rep["added"] else "")
            if rep["skipped"]:
                msg += " · bỏ qua: " + "; ".join(f"{n}: {w}" for n, w in rep["skipped"][:3])
            st.toast(msg)
        if act(go):
            st.rerun()
    b1, b2 = st.columns(2)
    if b1.button("📁 Mở Kho tài nguyên (duyệt ảnh chờ, nhân vật 3D, âm thanh)", key=f"ref_kho_{pid}", width="stretch"):
        open_dialog("dlg_assets")
    b2.caption("🎥 Video ref chuyển động gắn cho từng cảnh ở **Storyboard → 🎞 Motion**; ảnh khung nào muốn tự đưa vào: **Storyboard → 🖼 Ảnh → Nhập ảnh thủ công** (ghim ref cho từng khung: chưa có).")
    cap("Ảnh quá lệch tỉ lệ hoặc quá nhỏ bị báo trước khi gửi video (luật model). Mỗi tài nguyên tối đa "
               f"{assets.MAX_IMAGES_PER_ASSET} ảnh.")


def inputs_and_refs_v2(p: Pipeline, pid: int, has_script: bool) -> None:
    """UI v2 (S13 lane E): the first card of the screen — the four ways in as small cards, then the references (form in an expander
    that is open while there is no script yet). Same widgets and keys as the folded version."""
    from dashboard.design import components as D
    with D.card(f"script-refs-{pid}"):
        st.html('<div class="script-h">📎 Đầu vào &amp; tham chiếu</div>')
        cols = st.columns(4)
        with cols[0]:
            st.html(D.pill("Đang dùng", "ok") + '<div class="script-mode"><b>📝 Kịch bản / ý tưởng</b>'
                    "<span>Dán, kéo file hoặc gõ ý thô ở thẻ ① bên dưới (tự nhận dạng)</span></div>")
        for col, (title, why) in zip(cols[1:], COMING):
            with col:
                st.html(D.pill("Sắp có", "mute") + f'<div class="script-mode"><b>{escape(title)}</b><span>{escape(why)}</span></div>')
                st.button("Sắp có", key=f"coming_{title[:2]}_{pid}", disabled=True, width="stretch")
        with st.expander("🖼 Tham chiếu & gắn ảnh nhân vật / nơi — " + _summary(p, pid).split("tham chiếu: ", 1)[-1], expanded=not has_script):
            attach_form(p, pid)
