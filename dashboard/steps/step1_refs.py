"""📎 Đầu vào & tham chiếu (đợt 3, 01/10; sắp lại S14.28, 05/10): the ways to start a project, and attaching pictures the script should
use (a new character, a place, an outfit) without leaving the screen. Everything attached goes through core/assets.py, the same Kho the
Director / image prompts / QC already read — nothing new for the pipeline to learn.

S14.28 (người dùng duyệt 05/10): in the script mode (default) the script box comes FIRST; the references block sits AFTER the scene
analysis, folded, and attaches per recognised character / place (the Kho still matches by name on its own). Before a script there is
only a one-line hint, no form. The "sắp có" ways in are one line.
GHI CHÚ cho S11 (chế độ 🎬 Làm theo video ref / 💃 Cover nhảy): ở hai chế độ đó ô gắn VIDEO ref phải đứng TRƯỚC kịch bản (đầu thẻ ①),
ngược với chế độ kịch bản ở đây — giữ chỗ thứ tự này khi làm S11.

Video-ref cover, dance cover and trend are plan S11 (docs/KE_HOACH_TINH_NANG_DIRECTOR_2026-10-01.md): shown as "sắp có", not clickable."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)
from core import assets

COMING = (("🎬 Làm theo video ref", "giữ cấu trúc + nhịp của video mẫu, viết lại lời, nhân vật FF — kế hoạch S11 (R-A)"),
          ("💃 Cover nhảy", "nhân vật FF nhảy theo động tác của video ref (chuyển sang dạng không mặt) — S11 (R-B)"),
          ("📈 Theo trend", "gợi ý từ thẻ trend đã duyệt (tùy chọn) — S11 (T)"))
PICK_KINDS = ("character", "location", "outfit", "prop", "weapon", "pet")
HINT = "🖼 Gắn ảnh tham chiếu sau khi phân tích cảnh — Kho tự ghép nhân vật / nơi theo tên trong kịch bản"
NO_CHARACTER = "(chỉ lưu vào Kho — chọn nhân vật sau)"


def _summary(p: Pipeline, pid: int) -> str:
    chosen = assets.project_assets(p.conn, pid)
    by: dict = {}
    for a in chosen:
        by[a["kind_label"]] = by.get(a["kind_label"], 0) + 1
    return "đầu vào: kịch bản / ý tưởng · tham chiếu: " + (", ".join(f"{n} {k.lower()}" for k, n in by.items()) if by else "chưa gắn")


def modes_line(pid: int) -> None:
    """S14.28: the ways in on ONE line — the script (in use) + the three "sắp có" buttons (disabled, same keys coming_…)."""
    cols = st.columns([5, 1.6], vertical_alignment="center")
    cols[0].caption("📝 **Kịch bản / ý tưởng** — đang dùng (dán, gõ hoặc 📎 file ở khung chat bên dưới)")
    with cols[1].popover("⋯ Cách khác", width="stretch", help="Sắp có: " + " · ".join(t for t, _ in COMING)):     # S14.36: three buttons → one small menu
        for title, why in COMING:
            st.button(title, key=f"coming_{title[:2]}_{pid}", disabled=True, width="stretch", help="Sắp có — " + why)


def recognised(p: Pipeline, pid: int) -> list:
    """[(name, kind)] the scene analysis / Director recognised: Character Bible names, the characters and places named in the scenes."""
    out: dict = {}

    def put(name, kind):
        name = " ".join(str(name or "").split())
        if name and assets.fold(name) not in {assets.fold(n) for n in out}:
            out[name] = kind
    for r in p.conn.execute("SELECT name FROM characters WHERE project_id=? ORDER BY id", (pid,)):
        put(r["name"], "character")
    for r in p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)):
        try:
            d = json.loads(r["data"] or "{}")
        except (TypeError, ValueError):
            continue
        for n in d.get("characters") or []:
            if isinstance(n, str):
                put(n, "character")
        if isinstance(d.get("location"), str):
            put(d["location"], "location")
    return list(out.items())


def _has_picture(chosen, name: str, kind: str):
    """The attached asset that carries this recognised name (character: assets.match_character; place: same name / alias)."""
    if kind == "character":
        return assets.match_character(chosen, name)
    key = assets.fold(name)
    return next((a for a in chosen if a["kind"] == "location" and a["images"] and key in {assets.fold(n) for n in assets.names_of(a)}), None)


def inputs_and_refs(p: Pipeline, pid: int, has_script: bool) -> None:
    """Old screen: drawn AFTER the 1a script fold (S14.28). No script yet → one hint line; else a fold, closed by default."""
    if not has_script:
        st.caption(HINT)
        return
    with ui.fold("🖼 Tham chiếu & gắn ảnh nhân vật / nơi", _summary(p, pid), f"refs_{pid}", default_open=False,
                 sub="gắn theo từng nhân vật / nơi đã nhận ra · Kho tự ghép theo tên") as opened:
        if not opened:
            return
        attach_form(p, pid)


def attach_form(p: Pipeline, pid: int) -> None:
    """The attached references + the form that adds one (keys ref_up_/ref_kind_/ref_name_/ref_shared_/ref_go_/ref_kho_;
    S14.28: ref_for_ = which recognised character / place, ref_outfit_for_ = the character an outfit is for)."""
    chosen = assets.project_assets(p.conn, pid)
    names = recognised(p, pid)
    if names:                                                   # S14.28: per recognised character / place, has it a picture?
        parts = []
        for n, k in names:
            a = _has_picture(chosen, n, k)
            parts.append(f"{n} ✔ {a['name']}" if a else f"{n} — chưa có ảnh")
        cap("Đã nhận ra: " + " · ".join(parts), f"script-refs-recognised-{pid}", summary=f"Đã nhận ra {len(names)} nhân vật / nơi · "
            f"{sum(1 for n, k in names if _has_picture(chosen, n, k))} đã có ảnh")
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
    picked = ""
    if names:
        labels = {n: f"{n} ({'nhân vật' if k == 'character' else 'nơi'})" for n, k in names}
        picked = st.selectbox("Gắn cho (đã nhận ra)", [""] + [n for n, _ in names], key=f"ref_for_{pid}",
                              format_func=lambda n: labels.get(n, "— tên khác: gõ ở ô Tên —"))
    f1, f2, f3 = st.columns([2.4, 1.6, 2], vertical_alignment="bottom")
    files = f1.file_uploader("Ảnh (JPG / PNG / WebP)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                             key=f"ref_up_{pid}")
    kind = f2.selectbox("Là", PICK_KINDS, format_func=lambda k: assets.KINDS[k], key=f"ref_kind_{pid}")
    typed = f3.text_input("Tên bộ trang phục (vd: Kelly đồ bơi)" if kind == "outfit" else "Tên (vd: Orion, Sân thượng)", key=f"ref_name_{pid}")
    name = typed.strip() or ("" if kind == "outfit" else picked)
    who = None
    if kind == "outfit":                                        # S14.28: an outfit is FOR a character of this project (set_outfit)
        bible = [r["name"] for r in p.conn.execute("SELECT name FROM characters WHERE project_id=? ORDER BY id", (pid,))]
        default = [NO_CHARACTER] + bible
        who = st.selectbox("cho nhân vật …", default, index=default.index(picked) if picked in bible else 0, key=f"ref_outfit_for_{pid}")
        if not bible:
            cap("Chưa có nhân vật trong Character Bible (chạy Director trước) — ảnh trang phục vẫn lưu vào Kho, chọn sau ở 👗 Trang phục.")
        who = None if who == NO_CHARACTER else who
        if not typed.strip() and who:
            name = f"{who} — trang phục"
    shared = st.checkbox("Lưu vào Kho chung (dùng lại ở mọi dự án — ảnh chờ duyệt trước khi pipeline dùng)", False, key=f"ref_shared_{pid}",
                         help="Bỏ chọn: chỉ dùng trong dự án này, dùng ngay.")
    if st.button("➕ Gắn vào dự án", key=f"ref_go_{pid}", disabled=not (files and name.strip()), type="primary"):
        def go():
            game = p.project(pid)["game"] or "FF"
            data = [(f.name, f.getvalue()) for f in files]
            if kind == "outfit":
                rep = assets.add_outfit_images(p.conn, pid, game, name, data, shared, character=who, created_by=p.actor)
            else:
                rep = assets.add_reference_images(p.conn, pid, game, kind, name, data, shared, created_by=p.actor)
            msg = f"Đã gắn {rep['added']} ảnh cho “{name.strip()}”" + (" (chờ duyệt ở Kho)" if shared and rep["added"] else "")
            if rep.get("note"):
                msg += " · " + rep["note"]
            if rep["skipped"]:
                msg += " · bỏ qua: " + "; ".join(f"{n}: {w}" for n, w in rep["skipped"][:3])
            st.toast(msg)
        if act(go):
            st.rerun()
    b1, b2 = st.columns(2)
    if b1.button("📁 Mở Kho tài nguyên (duyệt ảnh chờ, nhân vật 3D, âm thanh)", key=f"ref_kho_{pid}", width="stretch"):
        open_dialog("dlg_assets")
    with b2:
        cap("🎥 Video ref chuyển động gắn cho từng cảnh ở **Storyboard → 🎞 Motion**; ảnh khung nào muốn tự đưa vào: **Storyboard → 🖼 Ảnh → Nhập ảnh thủ công** (ghim ref cho từng khung: chưa có).",
            f"script-refs-video-{pid}", summary="🎥 Video ref gắn từng cảnh ở Storyboard → Motion")
    cap("Ảnh quá lệch tỉ lệ hoặc quá nhỏ bị báo trước khi gửi video (luật model). Mỗi tài nguyên tối đa "
               f"{assets.MAX_IMAGES_PER_ASSET} ảnh.")


def inputs_and_refs_v2(p: Pipeline, pid: int, has_script: bool) -> None:
    """UI v2: the references card, drawn AFTER card ① (script + scene analysis) — S14.28. No script yet → one hint line only; with
    scenes → the form in an expander, folded by default. Same widgets and keys as the old screen. The ways in: modes_line() in card ①."""
    from dashboard.design import components as D
    with D.card(f"script-refs-{pid}"):
        if not has_script:
            D.line(f'<span class="script-sum">{escape(HINT)}</span>')
            return
        with st.expander("🖼 Tham chiếu & gắn ảnh nhân vật / nơi — " + _summary(p, pid).split("tham chiếu: ", 1)[-1], expanded=False):
            attach_form(p, pid)
