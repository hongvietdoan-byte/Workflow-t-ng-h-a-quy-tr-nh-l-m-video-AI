"""Unified control dashboard (V1): one tool, stepper by step order, per-step control buttons.

Run:  py -m streamlit run dashboard/app.py
Layout and colors follow mockup/dashboard.html (see dashboard/ui.py).
Claude steps (Director / QC / motion prompt) use copy-paste JSON until the API runner is wired in.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
from html import escape

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import audio_lib, regen, trash, waveform, cost, ffmpeg_studio, final_cut, llm_io, llm_runner, music, preflight, prompts, script_parser  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline, PipelinePaused  # noqa: E402
from core.adapters import factory  # noqa: E402
from core.providers import ProviderError  # noqa: E402
from core.runner import ImageRunner, VideoRunner  # noqa: E402
from core.states import InvalidTransition, JobState  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import ui  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))
STEPS = ["1 · Kịch bản & phân tích", "2 · Gen ảnh + QC", "3 · Video Prompt", "4 · Gen video",
         "5a · Nhạc nền", "5b · Ghép & Render", "Lịch sử"]
ERRORS = (llm_runner.LlmError, InvalidTransition, llm_io.SchemaError, PipelinePaused, ffmpeg_studio.FFmpegNotFound,
          ffmpeg_studio.FFmpegError, ValueError, KeyError)
CRITERIA_LABEL = {"character": "Đúng nhân vật", "hands_face": "Không lỗi tay/mặt", "composition": "Đúng bố cục",
                  "mood_lighting": "Đúng mood / ánh sáng", "consistency": "Không chi tiết thừa/sai"}
FILTERS = {"all": "Tất cả", "review": "Chờ duyệt", "pass": "Đã duyệt", "fail": "FAIL", "run": "Đang chạy"}
FILTER_STATES = {"review": ("succeeded", "pending_review"), "pass": ("approved",), "fail": ("failed", "rejected"),
                 "run": ("queued", "running")}


# ---- providers / cost helpers ---------------------------------------------------------
def video_runner(p: Pipeline):
    """Provider chosen by VIDEO_PROVIDER (clipai | mock); None when not configured."""
    try:
        provider = factory.video_provider()
    except ProviderError as e:
        st.error(f"Clip AI: {e}")
        return None
    return VideoRunner(p, provider, DATA) if provider else None


def image_runner(p: Pipeline):
    """Provider chosen by IMAGE_PROVIDER (deepix | mock); None when not configured."""
    try:
        provider = factory.image_provider()
    except ProviderError as e:
        st.error(f"Deepix: {e}")
        return None
    return ImageRunner(p, provider, DATA) if provider else None


def llm_client():
    """Claude API client (ANTHROPIC_API_KEY / LLM_PROVIDER=mock); None when not configured -> paste JSON by hand."""
    try:
        return llm_runner.client_from_env()
    except llm_runner.LlmError as e:
        st.error(f"Claude API: {e}")
        return None


def tokens_text(r: dict) -> str:
    return f"{r.get('input_tokens', 0)} token vào / {r.get('output_tokens', 0)} token ra"


def image_estimate(p: Pipeline, pid: int):
    from core.adapters.deepix import DEFAULT_MODEL
    return cost.estimate_images(p, pid, cost.load_pricing(), os.environ.get("DEEPIX_MODEL", DEFAULT_MODEL))


def video_estimate(p: Pipeline, pid: int):
    from core.adapters.clipai import effective_duration, resolve_model
    try:
        canonical, family = resolve_model(p.project(pid)["video_model"])
    except ProviderError:
        return None
    tier = os.environ.get("CLIPAI_KLING_MODE", "pro") if family == "omni" else os.environ.get("CLIPAI_RESOLUTION", "720p")
    return cost.estimate_videos(p, pid, cost.load_pricing(), canonical, tier,
                                lambda seconds: effective_duration(canonical, family, seconds))


def show_estimate(est, runner) -> bool:
    """Show the estimate; for real providers require a confirmation tick on large batches. Returns 'allowed'."""
    if est is None:
        return True
    if est["items"] == 0:
        return True
    st.info("Ước tính chi phí: " + cost.format_estimate(est))
    if runner is None or runner.provider.name.startswith("mock"):
        return True
    if est["items"] >= cost.load_pricing()["confirm_batch_at"]:
        return st.checkbox(f"Tôi xác nhận batch {est['items']} mục này sẽ tốn credit", key=f"confirm_{est['kind']}")
    return True


def spend_line(p: Pipeline, pid: int) -> None:
    spend = cost.spend_summary(p.conn, pid, cost.load_pricing())
    if not (spend["images"] or spend["clips"] or spend["audios"]):
        return
    text = (f"Đã ghi nhận (gửi API thật): {spend['images']} ảnh · {spend['clips']} clip ({spend['seconds']:.0f} giây)"
            f" · {spend['audios']} âm thanh")
    if spend["unknown_prices"]:
        text += " — chưa có giá cho: " + ", ".join(spend["unknown_prices"]) + " (điền data/pricing.json)"
    else:
        text += f" → khoảng {spend['credits']:.1f} {spend['currency']} theo giá khai báo"
    st.caption(text)


def project_dir(pid: int, *parts: str) -> str:
    path = os.path.join(DATA, str(pid), *parts)
    os.makedirs(path, exist_ok=True)
    return path


def act(fn, success: str = ""):
    """Run an action, show errors instead of crashing, rerun on success."""
    try:
        fn()
    except ERRORS as e:
        st.error(f"{type(e).__name__}: {e}")
        return False
    if success:
        st.toast(success)
    return True


def confirm_all(key: str, ids, label: str, question: str, container=st) -> bool:
    """One 'approve all' button, then a yes/no question. True only when the user answers Yes.
    The question is tied to the exact set of items it was asked about: if the set changes, it is asked again."""
    ids = tuple(ids)
    pending_key = f"ask_{key}"
    if st.session_state.get(pending_key) not in (None, ids):
        st.session_state[pending_key] = None  # the list changed since the question: forget it
    if st.session_state.get(pending_key) != ids:
        if container.button(label, key=key, disabled=not ids):
            st.session_state[pending_key] = ids
            st.rerun()
        return False
    container.warning(question)
    yes, no = container.columns(2)
    if yes.button("Có, duyệt hết", key=f"{key}_yes", type="primary"):
        st.session_state[pending_key] = None
        return True
    if no.button("Không", key=f"{key}_no"):
        st.session_state[pending_key] = None
        st.rerun()
    return False


def job_image(pid: int, jid: int):
    """The job's image; a rejected/deleted one is looked up in the trash so versions can still be compared."""
    path = os.path.join(DATA, str(pid), "images", f"job_{jid}.png")
    return path if os.path.exists(path) else trash.find_for_job(DATA, pid, "images", jid)


@st.cache_data(ttl=3600, show_spinner=False)
def purge_trash(data_dir: str) -> int:
    """Delete trash entries older than the retention period (checked at most once an hour)."""
    return trash.purge_expired(data_dir)


def show_image(path, **kwargs):
    """st.image that survives a corrupt or half-downloaded file (shows a note instead of crashing the page)."""
    try:
        st.image(path, **kwargs)
    except Exception:  # noqa: BLE001 - PIL/streamlit raise many types for unreadable files
        st.caption(f"⚠ Không đọc được ảnh: {os.path.basename(str(path))}")


_GENERIC_TITLE = re.compile(r"(?i)^\s*(cảnh|canh|scene|sc|s)\s*\.?\s*\d+\s*$")


def scene_title(idx, title) -> str:
    """'Cảnh 3' or 'Cảnh 3 — Rừng Elder' (a bare 'CẢNH 3' heading is not repeated)."""
    t = (title or "").strip()
    return f"Cảnh {idx}" + ("" if not t or _GENERIC_TITLE.match(t) else f" — {t}")


def scene_expander(p: Pipeline, scene_id, expanded: bool = False, with_motion: bool = False) -> None:
    """Drop-down under an image/video: the script text of that scene plus its spec, so the result can be checked
    against what the script says."""
    row = p.conn.execute("SELECT idx, title, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return
    d = json.loads(row["data"] or "{}")
    with st.expander(f"📖 {scene_title(row['idx'], row['title'])} · nội dung kịch bản", expanded=expanded):
        if d.get("text"):
            ui.html(f'<div class="scenetext">{escape(d["text"])}</div>')
        else:
            st.caption("Chưa có nội dung kịch bản (chạy phân tích ở Bước 1).")
        lines = [("Bối cảnh", " · ".join(filter(None, [d.get("time"), d.get("location")]))),
                 ("Nhân vật", ", ".join(d.get("characters") or [])),
                 ("Mood / ánh sáng / cỡ cảnh", " · ".join(filter(None, [d.get("mood"), d.get("lighting"), d.get("shot")]))),
                 ("Prompt ảnh", d.get("image_prompt") or "")]
        if with_motion:
            m = p.conn.execute("SELECT motion_prompt FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
            lines.append(("Motion prompt", m["motion_prompt"] if m else ""))
        ui.html("".join(f'<div class="muted"><b>{escape(k)}:</b> {escape(v)}</div>' for k, v in lines if v))


VIDEO_SIZES = ["Nhỏ", "Vừa", "Lớn"]


def video_size_control(key: str) -> str:
    """One size switch for every video on a page (small / medium / full width). The player's own ⛶ button
    goes full screen."""
    return st.radio("Kích thước xem video", VIDEO_SIZES, index=1, horizontal=True, key=key)


def show_video(path: str, size: str = "Vừa") -> None:
    ratio = {"Nhỏ": [1, 3], "Vừa": [1, 1]}.get(size)
    try:
        if ratio:
            st.columns(ratio)[0].video(path)
        else:
            st.video(path)
    except Exception:  # noqa: BLE001 - unreadable file: say so instead of breaking the page
        st.caption(f"⚠ Không phát được video: {os.path.basename(path)}")


def qc_scores(p: Pipeline, jid: int):
    return p.conn.execute("SELECT criterion, score, threshold_at_time FROM qc_results WHERE job_id=? ORDER BY id",
                          (jid,)).fetchall()


# ---- step completion (stepper checkmarks) ----------------------------------------------
def step_done(p: Pipeline, pid: int) -> list:
    q = lambda sql, *a: p.conn.execute(sql, a).fetchone()[0]  # noqa: E731
    scenes = q("SELECT COUNT(*) FROM scenes WHERE project_id=?", pid)
    approved_imgs = q("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='image_gen'"
                      " AND state='approved'", pid)
    motion = q("SELECT COUNT(*) FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?"
               " AND m.state='approved'", pid)
    videos = q("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='video_gen'"
               " AND state='succeeded'", pid)
    drafts_dir, selected_dir = music.project_dirs(DATA, pid)
    return [bool(q("SELECT COUNT(*) FROM characters WHERE project_id=? AND locked=1", pid)),
            bool(scenes) and approved_imgs >= scenes, bool(scenes) and motion >= scenes,
            bool(scenes) and videos >= scenes, bool(os.listdir(selected_dir)),
            os.path.exists(os.path.join(DATA, str(pid), "output", "FINAL_VIDEO.mp4")), False]


def step_label(done: list):
    marks = {name: ("✓  " if done[i] else "") + name for i, name in enumerate(STEPS)}
    return lambda name: marks[name]


# ---- header --------------------------------------------------------------------------
def price_editor() -> None:
    """Edit data/pricing.json in the dashboard: copy the price the Clip AI web page shows before generating."""
    with st.container():
        st.caption("Web Clip AI hiện giá cho từng thiết lập trước khi bấm gen: chỉ cần chép lại. Ưu tiên tra: "
                   "`model:mức:Ns` (giá đúng thiết lập) → `model:mức` (giá mỗi clip) → giá mỗi giây. "
                   "Để trống = chưa biết giá (Dashboard vẫn đếm số lượng).")
        pricing = cost.load_pricing()
        c1, c2 = st.columns(2)
        currency = c1.text_input("Đơn vị tiền/credit", pricing["currency"], key="price_currency")
        confirm = c2.number_input("Xác nhận khi lô từ … mục trở lên", 1, 1000, int(pricing["confirm_batch_at"]),
                                  key="price_confirm")
        rows = st.data_editor(
            cost.pricing_to_rows(pricing), num_rows="dynamic", width="stretch", hide_index=True, key="price_rows",
            column_config={
                "kind": st.column_config.SelectboxColumn("Loại", options=list(cost.PRICE_KINDS), required=True,
                                                         width="large"),
                "key": st.column_config.TextColumn("Khóa", required=True, width="large"),
                "price": st.column_config.NumberColumn("Giá", min_value=0.0, format="%.4f"),
            })
        st.caption("Loại: " + " · ".join(f"`{k}` = {v}" for k, v in cost.PRICE_KINDS.items()))
        if st.button("💾 Lưu bảng giá", key="btn_save_prices"):
            try:
                base = dict(pricing, currency=currency.strip() or "credits", confirm_batch_at=int(confirm))
                cost.save_pricing(cost.rows_to_pricing(rows.to_dict("records") if hasattr(rows, "to_dict") else rows, base))
            except ValueError as e:
                st.error(str(e))
            else:
                st.toast("Đã lưu bảng giá")
                st.rerun()


def risk_popover(p: Pipeline, pid: int) -> None:
    """Small corner note: IP warnings and risk-control blocks seen so far in this project."""
    notes = preflight.risk_notes(p.conn, pid, preflight.load_blocklist())
    with st.popover(f"⚠ Rủi ro ({len(notes)})", help="Ghi chú rủi ro đã gặp: cảnh báo IP và các lần bị chặn risk control"):
        if not notes:
            st.caption("Chưa ghi nhận rủi ro nào.")
        for n in notes:
            tag = ui.badge("IP", "b-warn") if n["kind"] == "ip" else ui.badge("bị chặn", "b-bad")
            ui.html(f'{tag} <b>{escape(n["title"])}</b><br><span class="muted">{escape(n["detail"])}</span>')


def global_bar(p: Pipeline):
    projects = p.conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    with st.expander("⚙ Cài đặt & dự án", expanded=not projects):
        t_new, t_price = st.tabs(["Dự án mới", "Bảng giá"])
        with t_new:
            name = st.text_input("Tên dự án", key="new_name")
            if st.button("Tạo dự án") and name.strip():
                p.create_project(name.strip())
                st.rerun()
        with t_price:
            price_editor()
    if not projects:
        st.info("Chưa có dự án. Hãy tạo dự án để bắt đầu.")
        return None
    with st.container(border=True):
        c0, c1, c2, c3, c4, c5 = st.columns([1.4, 1.8, 2.0, 1.6, 1.3, 3.0], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
        ids = [r["id"] for r in projects]
        pid = c1.selectbox("Dự án", ids, format_func=lambda i: next(r["name"] for r in projects if r["id"] == i))
        proj = p.project(pid)
        mode = c2.radio("Chế độ QC", ["auto", "human_qc"], index=0 if proj["operating_mode"] == "auto" else 1,
                        horizontal=True, key=f"mode_{pid}")
        if mode != proj["operating_mode"]:
            p.set_mode(pid, mode)
        th = c3.slider("QC threshold", 0.5, 1.0, float(proj["qc_auto_pass_threshold"]), 0.01, key=f"th_{pid}")
        if abs(th - proj["qc_auto_pass_threshold"]) > 1e-9:
            p.set_threshold(pid, th)
        with c4:
            risk_popover(p, pid)
        b1, b2, b3 = c5.columns(3)
        if b1.button("⏸ Pause", disabled=bool(proj["paused"]), key="btn_pause"):
            p.set_paused(pid, True)
            st.rerun()
        if b2.button("▶ Resume", disabled=not proj["paused"], key="btn_resume"):
            p.set_paused(pid, False)
            st.rerun()
        if b3.button("■ Cancel", key="btn_cancel"):
            st.toast(f"Đã hủy {p.cancel_all_active(pid)} job")
            st.rerun()
    if proj["paused"]:
        st.warning("Pipeline đang PAUSE — không job nào được bắt đầu.")
    spend_line(p, pid)
    return pid


# ---- step 1 --------------------------------------------------------------------------
def step1(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx",
                            (pid,)).fetchall()
    chars = p.conn.execute("SELECT name, description, wardrobe, locked FROM characters WHERE project_id=?",
                           (pid,)).fetchall()
    warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist()) if chars else []
    risky = {w["character"] for w in warnings}
    left, right = st.columns([1, 1.7], gap="large")
    with left:
        with st.container(border=True):
            ui.html(ui.card_title("① Kịch bản"))
            up = st.file_uploader("script.docx", type=["docx"], key=f"up_{pid}", label_visibility="collapsed")
            c1, c2 = st.columns(2)
            if c1.button("▶ Phân tích (tách cảnh)", disabled=up is None, type="primary"):
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                    f.write(up.getvalue())
                try:
                    parsed = script_parser.parse_docx(f.name)
                finally:
                    os.remove(f.name)
                if act(lambda: script_parser.import_scenes(p, pid, parsed), f"Đã tách {len(parsed)} cảnh"):
                    st.rerun()
            if c2.button("↺ Reset", help="Xóa cảnh + nhân vật chưa khóa", key="btn_bad_reset"):
                p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
                p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
                p.conn.commit()
                st.rerun()
            if scenes:
                st.caption(f"✓ {len(scenes)} cảnh · {len(chars)} nhân vật")
        if scenes:
            with st.container(border=True):
                ui.html(ui.card_title("② Director", "Character Bible + thông số cảnh"))
                client = llm_client()
                if client is not None:
                    if st.button("🤖 Chạy Director bằng Claude API", type="primary", key=f"llm_dir_{pid}"):
                        with st.spinner("Claude đang phân tích kịch bản…"):
                            ok = act(lambda: st.session_state.__setitem__(
                                "llm_res", llm_runner.run_director(p, pid, client)))
                        if ok:
                            r = st.session_state.pop("llm_res")
                            st.toast(f"Đã lưu {r['characters']} nhân vật, {r['scenes']} cảnh ({tokens_text(r)})")
                            st.rerun()
                with st.expander("✍ Nhập tay: prompt gửi Claude + dán JSON kết quả", expanded=client is None and not chars):
                    st.code(prompts.build_director_bundle(p, pid), language="markdown")
                    raw = st.text_area("Dán JSON kết quả từ Claude", key=f"analysis_{pid}", height=120)
                    if st.button("Lưu phân tích", disabled=not raw.strip()):
                        if act(lambda: llm_io.store_scene_analysis(p, pid, raw), "Đã lưu Character Bible + thông số cảnh"):
                            st.rerun()
    with right:
        if chars:
            with st.container(border=True):
                head, status = st.columns([3, 2], vertical_alignment="center")
                head.markdown(ui.card_title("Character Bible", f"{len(chars)} nhân vật"), unsafe_allow_html=True)
                if risky:
                    status.caption(f"⚠ {len(risky)} nhân vật có thể vướng IP (xem “⚠ Rủi ro” ở góc trên)")
                st.dataframe([{"Nhân vật": c["name"], "Mô tả": c["description"] + (f" · {c['wardrobe']}" if c["wardrobe"] else ""),
                               "IP": "⚠ rủi ro" if c["name"] in risky else "an toàn",
                               "Khóa": "🔒" if c["locked"] else ""} for c in chars],
                             width="stretch", hide_index=True, height=min(38 * (len(chars) + 1) + 3, 220))
                with st.expander("✏ Sửa nhân vật / khóa"):
                    if any(c["locked"] for c in chars):
                        st.caption("Character Bible đang khóa. Muốn sửa phải mở khóa (ảnh đã gen vẫn theo mô tả cũ).")
                        if st.button("🔓 Mở khóa để sửa", key="btn_bad_unlock"):
                            act(lambda: llm_io.unlock_character_bible(p, pid), "Đã mở khóa Character Bible")
                            st.rerun()
                    else:
                        who = st.selectbox("Chọn nhân vật", [c["name"] for c in chars], key=f"csel_{pid}")
                        c = next(c for c in chars if c["name"] == who)
                        n_name = st.text_input("Tên", c["name"], key=f"cn_{pid}_{c['name']}")
                        n_desc = st.text_area("Mô tả", c["description"], key=f"cd_{pid}_{c['name']}", height=80)
                        n_ward = st.text_input("Trang phục / dấu hiệu", c["wardrobe"] or "", key=f"cw_{pid}_{c['name']}")
                        if st.button("Lưu nhân vật", key=f"cs_{pid}_{c['name']}"):
                            if act(lambda: llm_io.update_character(p, pid, c["name"], n_desc, n_ward, n_name),
                                   f"Đã lưu {n_name}"):
                                st.rerun()
        if scenes:
            with st.container(border=True):
                ui.html(ui.card_title("③ Phân cảnh", f"{len(scenes)} cảnh"))
                rows = []
                for s in scenes:
                    d = json.loads(s["data"] or "{}")
                    rows.append({"Cảnh": f"S{s['idx']:02d}",
                                 "Bối cảnh": " · ".join(filter(None, [d.get("time"), d.get("location")])),
                                 "Nhân vật": ", ".join(d.get("characters") or []),
                                 "Shot · mood": " · ".join(filter(None, [d.get("shot"), d.get("mood")])),
                                 "Trạng thái": s["state"]})
                st.dataframe(rows, width="stretch", hide_index=True, height=min(38 * (len(rows) + 1) + 3, 260))
                pick = st.selectbox("Xem / sửa chi tiết một cảnh", [s["idx"] for s in scenes], index=None,
                                    placeholder="Chọn cảnh…", key=f"scene_pick_{pid}",
                                    format_func=lambda i: scene_title(i, next(s["title"] for s in scenes if s["idx"] == i)))
                if pick is not None:
                    scene_editor(p, pid, next(s for s in scenes if s["idx"] == pick), [c["name"] for c in chars])
        if chars:
            with st.container(border=True):
                a, b = st.columns([2, 1], vertical_alignment="center")
                a.caption("Cần Approve & Lock để mở Bước 2")
                if b.button("✔ Duyệt & khóa → Bước 2", type="primary"):
                    act(lambda: llm_io.lock_character_bible(p, pid), "Đã khóa Character Bible")
                    st.rerun()


def scene_editor(p: Pipeline, pid: int, scene, char_names) -> None:
    """Detail of one scene: script text and spec, both editable (a scene's spec drives the image prompt)."""
    idx = scene["idx"]
    d = json.loads(scene["data"] or "{}")
    k = f"sd_{pid}_{idx}"
    text = st.text_area("Nội dung kịch bản của cảnh", d.get("text", ""), key=f"{k}_text", height=130)
    c1, c2, c3 = st.columns(3)
    location = c1.text_input("Địa điểm", d.get("location", ""), key=f"{k}_location")
    time_ = c2.text_input("Thời gian", d.get("time", ""), key=f"{k}_time")
    shot = c3.text_input("Cỡ cảnh / góc máy", d.get("shot", ""), key=f"{k}_shot")
    c4, c5 = st.columns(2)
    mood = c4.text_input("Mood", d.get("mood", ""), key=f"{k}_mood")
    lighting = c5.text_input("Ánh sáng", d.get("lighting", ""), key=f"{k}_lighting")
    cast = st.multiselect("Nhân vật trong cảnh", char_names, [c for c in d.get("characters") or [] if c in char_names],
                          key=f"{k}_cast")
    image_prompt = st.text_area("Prompt ảnh", d.get("image_prompt", ""), key=f"{k}_prompt", height=80)
    st.caption("Ảnh đã gen giữ nguyên; chỉ ảnh gen sau khi sửa mới theo nội dung mới.")
    if st.button("💾 Lưu cảnh", key=f"sds_{pid}_{idx}"):
        fields = {"location": location, "time": time_, "shot": shot, "mood": mood, "lighting": lighting,
                  "image_prompt": image_prompt}
        if char_names:
            fields["characters"] = cast
        if act(lambda: llm_io.update_scene(p, pid, idx, fields, text=text), f"Đã lưu cảnh {idx}"):
            st.rerun()


# ---- step 2 --------------------------------------------------------------------------
def step2(p: Pipeline, pid: int):
    proj = p.project(pid)
    runner = image_runner(p)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.2, 2, 2, 3], vertical_alignment="center")
        if c1.button("▶ Tạo job gen ảnh (cảnh READY)", type="primary"):
            rows = p.conn.execute(
                "SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN"
                " (SELECT scene_id FROM jobs WHERE type='image_gen' AND state NOT IN ('rejected','cancelled'))",
                (pid,)).fetchall()
            for r in rows:
                p.create_job(r["id"], "image_gen")
            st.toast(f"Đã tạo {len(rows)} job")
            st.rerun()
        pending = [j["id"] for j in p.conn.execute(
            "SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='pending_review' ORDER BY id",
            (pid,)).fetchall()]
        if confirm_all("approve_all", pending, f"✔ Duyệt tất cả ({len(pending)} ảnh)",
                       f"Duyệt tất cả {len(pending)} ảnh đang chờ duyệt?", c2):
            for jid in pending:
                p.approve(jid, "user")
            st.rerun()
        if c3.button("↻ Gen lại tất cả FAIL", key="reject_all"):
            for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='image_gen' AND state='failed'",
                                    (pid,)).fetchall():
                act(lambda: p.retry(j["id"], "retry all"))
            st.rerun()
        c4.markdown(ui.badge(f"Chế độ: {proj['operating_mode']} — "
                             + ("QC Agent tự duyệt theo threshold" if proj["operating_mode"] == "auto"
                                else "mọi ảnh chờ bạn duyệt"), "b-pri")
                    + f' <span class="muted">Retry tối đa {proj["max_retry_count"]}</span>', unsafe_allow_html=True)
    with st.expander("⚙ Thiết lập QC: tự loại ảnh điểm thấp · vùng chờ review"):
        f1, f2, f3 = st.columns([2, 3, 3], vertical_alignment="center")
        floor_on = f1.checkbox("Tự loại ảnh điểm thấp", proj["qc_reject_floor"] is not None, key=f"rej_on_{pid}",
                               help="Ảnh có điểm QC dưới mức này bị loại ngay (vào Thùng rác) và xếp hàng gen ảnh mới, "
                                    "ở cả hai chế độ. Ảnh điểm cao vẫn phải chờ bạn duyệt ở human_qc.")
        reject_floor = f2.slider("Dưới mức này tự loại + xếp hàng gen ảnh mới", 0.30, 0.80,
                                 float(proj["qc_reject_floor"] or 0.5), 0.05, key=f"rej_v_{pid}", disabled=not floor_on)
        f3.caption("Ảnh bị loại vào 🗑 Thùng rác (tab Lịch sử, giữ 30 ngày). Ảnh mới chỉ được gen khi bạn bấm chạy.")
        new_reject = round(reject_floor, 2) if floor_on else None
        if new_reject != proj["qc_reject_floor"] and (new_reject is None or proj["qc_reject_floor"] is None
                                                      or abs(new_reject - proj["qc_reject_floor"]) > 1e-9):
            p.set_reject_floor(pid, new_reject)
        if proj["operating_mode"] == "auto":
            z1, z2, _ = st.columns([2, 3, 3], vertical_alignment="center")
            zone_on = z1.checkbox("Vùng chờ review", proj["qc_review_floor"] is not None, key=f"zone_{pid}",
                                  help="Điểm nằm giữa mức sàn và threshold: QC Agent không tự loại mà chờ bạn duyệt.")
            floor = z2.slider("Mức sàn (dưới mức này tự loại)", 0.3, float(proj["qc_auto_pass_threshold"]),
                              min(float(proj["qc_review_floor"] or 0.6), float(proj["qc_auto_pass_threshold"])), 0.01,
                              key=f"floor_{pid}", disabled=not zone_on)
            new_floor = floor if zone_on else None
            if new_floor != proj["qc_review_floor"] and (new_floor is None or proj["qc_review_floor"] is None
                                                         or abs(new_floor - proj["qc_review_floor"]) > 1e-9):
                p.set_review_floor(pid, new_floor)
    if runner is None:
        st.caption("ℹ Deepix chưa cấu hình: nhập ảnh thủ công cho từng job (cách cấu hình: docs/RUNBOOK.md).")
    else:
        st.caption(f"Provider ảnh: {runner.provider.name}" + (" (giả lập — ảnh 1x1)" if runner.provider.name == "mock-image" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(image_estimate(p, pid), runner)
        r1, r2, _ = st.columns([2, 2, 4])
        if r1.button("⟳ Submit + Poll 1 lần (ảnh)", disabled=not allowed):
            submitted = runner.submit_pending(pid)
            st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
            st.rerun()
        if r2.button("▶ Chạy heartbeat tới khi xong (ảnh)", disabled=not allowed):
            with st.spinner("Đang gen ảnh…"):
                runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
            st.rerun()

    client = llm_client()
    to_check = p.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='image_gen' AND state='succeeded'",
                              (pid,)).fetchone()["c"]
    if client is not None and to_check:
        if st.button(f"🤖 QC {to_check} ảnh vừa gen bằng Claude", key=f"llm_qc_all_{pid}"):
            with st.spinner("Claude đang chấm ảnh…"):
                ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_qc_batch(p, pid, client, DATA)))
            if ok:
                r = st.session_state.pop("llm_res")
                st.toast(f"Đã chấm {r['checked']} ảnh {r['decisions']} ({tokens_text(r)})")
                for jid, msg in r["failed"]:
                    st.error(f"Job #{jid}: {msg}")
                if not r["failed"]:
                    st.rerun()
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    counts = {k: sum(1 for j in jobs if j["state"] in v) for k, v in FILTER_STATES.items()}
    counts["all"] = len(jobs)
    flt = st.radio("Lọc", list(FILTERS), horizontal=True, key=f"filter_{pid}", label_visibility="collapsed",
                   format_func=lambda k: f"{FILTERS[k]} {counts[k]}")
    shown = [j for j in jobs if flt == "all" or j["state"] in FILTER_STATES[flt]]
    if not jobs:
        st.caption("Chưa có job gen ảnh. Duyệt Character Bible ở Bước 1 rồi bấm ‘Tạo job gen ảnh’.")
        return
    sel_key = f"sel_{pid}"
    if st.session_state.get(sel_key) not in {j["id"] for j in jobs}:
        st.session_state[sel_key] = shown[0]["id"] if shown else jobs[0]["id"]
    grid, detail = st.columns([3, 1.15], gap="large")
    with grid:
        per_row = 3
        for start in range(0, len(shown), per_row):
            cols = st.columns(per_row)
            for col, j in zip(cols, shown[start:start + per_row]):
                with col:
                    image_card(p, pid, j, proj)
        if not shown:
            st.caption("Không có ảnh nào trong bộ lọc này.")
    with detail:
        job = next(j for j in jobs if j["id"] == st.session_state[sel_key])
        image_detail(p, pid, job, proj)


def image_card(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    scores = qc_scores(p, jid)
    with st.container(border=True):
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        else:
            ui.html('<div style="height:120px;border-radius:8px;background:var(--bg);display:grid;place-items:center;'
                    f'color:var(--muted)">{"⏳ đang gen…" if state == "running" else "chưa có ảnh"}</div>')
        flag = " " + ui.badge("⚠ escalated", "b-warn") if j["escalated"] else ""
        ui.html(f'<div class="cardhead"><b>Cảnh {j["idx"]}</b><span class="grow"></span>{ui.state_badge(state)}{flag}</div>')
        if scores:
            mean = sum(s["score"] for s in scores) / len(scores)
            ui.html(ui.qc_bar(mean, proj["qc_auto_pass_threshold"]))
        if state in ("succeeded", "pending_review"):
            a, b, c = st.columns(3)
            if a.button("✔", key=f"a_{jid}", help="Approve"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if b.button("✖", key=f"r_{jid}", help="Reject & gen lại (dùng ghi chú ở panel chi tiết)"):
                act(lambda: p.reject(jid, "user", st.session_state.get(f"note_{jid}") or None))
                st.rerun()
            if c.button("🔍", key=f"sel_btn_{jid}", help="Xem chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("queued", "running"):
            a, b = st.columns(2)
            if b.button("■", key=f"c_{jid}", help="Cancel"):
                act(lambda: p.cancel(jid))
                st.rerun()
            if a.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết / nhập ảnh thủ công"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state == "failed":
            a, b = st.columns(2)
            if a.button("↻", key=f"retry_{jid}", help="Retry"):
                act(lambda: p.retry(jid, "retry"))
                st.rerun()
            if b.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        scene_expander(p, j["scene_id"])


def image_detail(p: Pipeline, pid: int, j, proj):
    jid, state = j["id"], j["state"]
    with st.container(border=True):
        ui.html(ui.card_title(f"Chi tiết ảnh — Cảnh {j['idx']}", f"job #{jid} · retry {j['retry_count']}"))
        ui.html(ui.state_badge(state))
        if j["retry_reason"]:
            st.caption(f"Lý do retry: {j['retry_reason']}")
        img = job_image(pid, jid)
        if img:
            show_image(img, width="stretch")
        scene_expander(p, j["scene_id"], expanded=True)
        scores = qc_scores(p, jid)
        if scores:
            ui.html('<div class="muted" style="font-weight:600;margin-top:8px">QC checklist (Claude Vision)</div>')
            for s in scores:
                ui.html(f'<div class="crit"><span>{CRITERIA_LABEL.get(s["criterion"], s["criterion"])}</span>'
                        f'<b style="color:{ui.score_color(s["score"], proj["qc_auto_pass_threshold"])}">{s["score"]:.2f}</b></div>')
        if state in ("queued", "running"):
            up = st.file_uploader("Nhập ảnh thủ công", type=["png", "jpg", "jpeg"], key=f"img_{jid}")
            if up and st.button("Xác nhận ảnh đã có", key=f"ok_{jid}"):
                with open(os.path.join(project_dir(pid, "images"), f"job_{jid}.png"), "wb") as f:
                    f.write(up.getvalue())

                def done():
                    if p.state(jid) == JobState.QUEUED:
                        p.start(jid)
                    p.succeed(jid)
                if act(done):
                    st.rerun()
        elif state == "succeeded":
            client = llm_client()
            if client is not None and st.button("🤖 QC bằng Claude", key=f"llm_qc_{jid}", type="primary"):
                with st.spinner("Claude đang chấm ảnh…"):
                    ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_qc(p, jid, client, DATA)))
                if ok:
                    r = st.session_state.pop("llm_res")
                    st.toast(f"Quyết định: {r['decision']} ({tokens_text(r)})")
                    st.rerun()
            with st.expander("QC Agent — prompt & kết quả"):
                st.code(prompts.build_qc_bundle(p, j["scene_id"]), language="markdown")
                raw = st.text_area("JSON điểm QC từ Claude", key=f"qc_{jid}", height=100)
                if st.button("Chấm điểm", key=f"score_{jid}", disabled=not raw.strip()):
                    def score():
                        obj = llm_io.validate_qc_result(raw, prompts.qc_criteria())
                        st.toast(f"Quyết định: {p.apply_qc(jid, obj['criteria'])}")
                    if act(score):
                        st.rerun()
        if state in ("succeeded", "pending_review"):
            note = st.text_input("Ghi chú reject (đưa vào prompt gen lại)", key=f"note_{jid}")
            a, b = st.columns(2)
            if b.button("✖ Reject & Gen lại", key=f"dr_{jid}"):
                act(lambda: p.reject(jid, "user", note or None))
                st.rerun()
            if a.button("✔ Approve", key=f"da_{jid}", type="primary"):
                act(lambda: p.approve(jid, "user"))
                st.rerun()
            if st.button("🗑 Xóa (vào thùng rác, không gen lại)", key=f"dd_{jid}"):
                act(lambda: p.reject(jid, "user", note or "đã xóa", respawn=False))
                st.rerun()
        if state == "failed" and st.button("↻ Retry", key=f"dretry_{jid}"):
            act(lambda: p.retry(jid, "retry"))
            st.rerun()


# ---- step 3 --------------------------------------------------------------------------
def step3(p: Pipeline, pid: int):
    approved = p.conn.execute(
        "SELECT s.idx FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id"
        " AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (pid,)).fetchall()
    rows = p.conn.execute(
        "SELECT s.id sid, s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    with st.container(border=True):
        a, b = st.columns([3, 1], vertical_alignment="center")
        a.markdown(ui.badge(f"{len(approved)} cảnh đã có ảnh được duyệt", "b-info") +
                   ' <span class="muted">Knowledge Base · image-to-video</span>', unsafe_allow_html=True)
        waiting = [r["sid"] for r in rows if r["state"] != "approved"]
        if confirm_all("btn_ok_all", waiting, f"✔ Duyệt tất cả ({len(waiting)} prompt)",
                       f"Duyệt tất cả {len(waiting)} motion prompt đang chờ?", b):
            for sid in waiting:
                llm_io.approve_motion_prompt(p, sid)
            st.rerun()
        client = llm_client()
        if client is not None and st.button("🤖 Sinh motion prompt bằng Claude (cảnh chưa có)", type="primary",
                                            key=f"llm_mot_{pid}"):
            with st.spinner("Claude đang viết motion prompt…"):
                ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_motion(p, pid, client, DATA)))
            if ok:
                r = st.session_state.pop("llm_res")
                st.toast(f"Đã lưu {r['scenes']} motion prompt ({tokens_text(r)})")
                st.rerun()
        with st.expander("Prompt gửi Claude (copy) & dán kết quả"):
            st.code(prompts.build_motion_bundle(p, pid), language="markdown")
            raw = st.text_area("Dán JSON motion prompts từ Claude", key=f"motion_{pid}", height=140)
            if st.button("▶ Lưu motion prompts", disabled=not raw.strip()):
                if act(lambda: llm_io.store_motion_prompts(p, pid, raw), "Đã lưu"):
                    st.rerun()
    with st.container(border=True):
        ui.html(ui.card_title("Video Motion Prompt", f"{len(rows)} cảnh"))
        if not rows:
            st.caption("Chưa có motion prompt. Dán JSON từ Claude ở trên.")
        for r in rows:
            img_job = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'"
                                     " ORDER BY id DESC LIMIT 1", (r["sid"],)).fetchone()
            c0, c1, c2, c3 = st.columns([1.2, 5, 1.1, 1.6], vertical_alignment="center")
            with c0:
                ui.html(f'<b>Cảnh {r["idx"]}</b>')
                path = job_image(pid, img_job["id"]) if img_job else None
                if path:
                    show_image(path, width=96)
            new = c1.text_area("Motion prompt", r["motion_prompt"], key=f"mp_{r['sid']}", height=70,
                               label_visibility="collapsed")
            c2.markdown(ui.badge("đã duyệt", "b-ok") if r["state"] == "approved" else ui.badge("chờ duyệt", "b-warn"),
                        unsafe_allow_html=True)
            c2.caption(f"{r['duration_sec']}s")
            if c3.button("Lưu chỉnh sửa", key=f"mps_{r['sid']}"):
                act(lambda: llm_io.store_motion_prompts(
                    p, pid, {"scenes": [{"idx": r["idx"], "motion_prompt": new, "camera": r["camera"],
                                         "duration_sec": r["duration_sec"],
                                         "negative_prompt": r["negative_prompt"]}]}))
                st.rerun()
            if c3.button("✔ Duyệt", key=f"mpa_{r['sid']}", disabled=r["state"] == "approved", type="primary"):
                act(lambda: llm_io.approve_motion_prompt(p, r["sid"]))
                st.rerun()
            scene_expander(p, r["sid"])
            st.divider()


# ---- step 4 --------------------------------------------------------------------------
def step4(p: Pipeline, pid: int):
    ready = llm_io.ready_for_video(p, pid)
    runner = video_runner(p)
    models = ["(mặc định: kling-v3-omni)", "kling", "kling-o1", "seedance", "seedance-fast", "seedance-2.5"]
    proj = p.project(pid)
    current = proj["video_model"]
    with st.container(border=True):
        m1, m2, m3 = st.columns([2, 2.4, 2.6], vertical_alignment="center")
        m1.markdown(ui.badge(f"{len(ready)} cảnh sẵn sàng gen", "b-info") +
                    ' <span class="muted">ảnh + prompt đã duyệt</span>', unsafe_allow_html=True)
        choice = m2.selectbox("Model video", models, index=models.index(current) if current in models else 0,
                              key=f"vmodel_{pid}", help="Kling Omni / Seedance; bộ lọc kiểm duyệt khác nhau theo model")
        if (choice if choice in models[1:] else None) != current:
            p.set_video_model(pid, choice if choice in models[1:] else None)
        audio_on = m3.checkbox("🔊 Model tự tạo âm thanh / lời thoại", bool(proj["video_audio"]), key=f"vaudio_{pid}",
                               help="Bật: Kling `sound` / Seedance `generate_audio`. Nhân vật có thể nói (khớp môi do model tự "
                                    "xử lý) nếu lời thoại được ghi trong motion prompt. Có thể đổi giá; chưa thử thật.")
        if audio_on != bool(proj["video_audio"]):
            p.set_video_audio(pid, audio_on)
        if runner is None:
            st.caption("ℹ Clip AI chưa cấu hình: chỉ theo dõi job thủ công.")
            with st.expander("Cách cấu hình"):
                st.write("Đặt VIDEO_PROVIDER=clipai và CLIPAI_TOKEN (biến môi trường), xem docs/RUNBOOK.md.")
        else:
            st.caption(f"Provider video: {runner.provider.name}" + (" (giả lập)" if runner.provider.name == "mock" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(video_estimate(p, pid), runner)
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("▶ Tạo job gen video", disabled=not ready, type="primary"):
            for r in ready:
                exists = p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen'"
                                        " AND state NOT IN ('cancelled','rejected')", (r["scene_id"],)).fetchone()
                if not exists:
                    p.create_job(r["scene_id"], "video_gen")
            st.rerun()
        if c2.button("⟳ Submit + Poll 1 lần", disabled=runner is None or not allowed):
            submitted = runner.submit_pending(pid)
            st.toast(f"Đã gửi {submitted} · {runner.poll_once(pid)}")
            st.rerun()
        if c3.button("▶ Chạy heartbeat tới khi xong", disabled=runner is None or not allowed):
            with st.spinner("Đang chạy heartbeat…"):
                runner.run(pid, interval=float(os.environ.get("HEARTBEAT_SEC", "90")))
            st.rerun()
        if c4.button("↻ Retry tất cả job fail", key="btn_bad_retry"):
            for j in p.conn.execute("SELECT id FROM jobs WHERE project_id=? AND type='video_gen' AND state='failed'"
                                    " AND escalated=0", (pid,)).fetchall():
                act(lambda: p.retry(j["id"], "retry all"))
            st.rerun()
    jobs = p.conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id"
                          " WHERE j.project_id=? AND j.type='video_gen' AND j.state!='rejected' ORDER BY s.idx, j.id",
                          (pid,)).fetchall()
    done = sum(1 for j in jobs if j["state"] == "succeeded")
    running = sum(1 for j in jobs if j["state"] == "running")
    failed = sum(1 for j in jobs if j["state"] == "failed")
    blocked = p.conn.execute("SELECT COUNT(*) c FROM content_moderation_failures f JOIN jobs j ON j.id=f.job_id"
                             " WHERE j.project_id=?", (pid,)).fetchone()["c"]
    with st.container(border=True):
        extra = (ui.badge(f"{running} running", "b-info") if running else "") + " " + \
                (ui.badge(f"{failed} failed", "b-bad") if failed else "")
        ui.html(ui.card_title("Tiến độ batch") + ui.progress(done, len(jobs), extra))
        if blocked:
            st.caption(f"⚠ {blocked} lần bị chặn risk control — chi tiết ở “⚠ Rủi ro” góc trên.")
    size = "Vừa"
    if any(j["state"] == "succeeded" and j["result_path"] and os.path.exists(j["result_path"]) for j in jobs):
        size = video_size_control("vsize_4")
    for j in jobs:
        clip = j["result_path"] if j["state"] == "succeeded" and j["result_path"] and os.path.exists(j["result_path"]) else None
        with st.container(border=True):
            a, b, c, d = st.columns([1.2, 1.6, 1, 2.2], vertical_alignment="center")
            a.markdown(f"**Cảnh {j['idx']}**")
            b.markdown(ui.state_badge(j["state"]) + (" " + ui.badge("⚠ escalated", "b-warn") if j["escalated"] else ""),
                       unsafe_allow_html=True)
            c.caption(f"retry {j['retry_count']}")
            with d:
                if j["state"] in ("queued", "running") and st.button("■ Cancel", key=f"vc_{j['id']}"):
                    act(lambda: runner.cancel_job(j["id"]) if runner else p.cancel(j["id"]))
                    st.rerun()
                if j["state"] == "failed" and not j["escalated"] and st.button("↻ Retry", key=f"vr_{j['id']}"):
                    act(lambda: p.retry(j["id"], "retry"))
                    st.rerun()
                if clip and st.button("↻ Gen lại video", key=f"vregen_{j['id']}",
                                      help="Chưa ưng: clip này vào thùng rác (giữ 30 ngày) và xếp hàng một video mới. "
                                           "Muốn đổi cách quay thì sửa motion prompt ở Bước 3 trước."):
                    if act(lambda: regen.regenerate_video(p, DATA, j["id"]), "Đã xếp hàng gen lại video"):
                        st.rerun()
            if clip:
                show_video(clip, size)
            scene_expander(p, j["scene_id"], with_motion=True)


# ---- step 5a -------------------------------------------------------------------------
def preview_with_track(p: Pipeline, pid: int, music_path: str, tag: str) -> None:
    out = os.path.join(project_dir(pid, "output"), f"preview_music_{tag}.mp4")
    with st.spinner("Đang ghép bản xem thử (clip + nhạc)…"):
        ok = act(lambda: final_cut.preview_with_music(p, DATA, pid, music_path, out), "Đã tạo bản xem thử")
    if ok:
        st.session_state[f"prev5a_{pid}"] = (out, tag)
        st.rerun()


def step5a(p: Pipeline, pid: int):
    drafts_dir, selected_dir = music.project_dirs(DATA, pid)
    try:
        provider = music.audio_provider()
    except ProviderError as e:
        st.error(f"Clip AI audio: {e}")
        provider = None
    has_clips = any(c["path"] for c in final_cut.collect_clips(p, DATA, pid))

    files = os.listdir(selected_dir)
    with st.container(border=True):
        a, b = st.columns([3, 2], vertical_alignment="center")
        a.markdown(ui.card_title("Nhạc nền đang chọn") + (ui.badge(files[0], "b-ok") if files else ui.badge("chưa chọn / không dùng")),
                   unsafe_allow_html=True)
        if files:
            spath = os.path.join(selected_dir, files[0])
            ui.html(ui.waveform_svg(_peaks(spath, os.path.getmtime(spath))))
            st.audio(spath)
            if has_clips and b.button("🎬 Xem thử với video", key=f"prev_sel_{pid}"):
                preview_with_track(p, pid, spath, "selected")
        with st.expander("Upload nhạc có sẵn / bỏ nhạc"):
            up = st.file_uploader("Upload nhạc nền", type=["mp3", "wav", "m4a"], key=f"music_{pid}")
            if up and st.button("Dùng bản này"):
                music.clear_selected(selected_dir)
                with open(os.path.join(selected_dir, "selected" + os.path.splitext(up.name)[1]), "wb") as f:
                    f.write(up.getvalue())
                st.rerun()
            if st.button("Không dùng nhạc"):
                music.clear_selected(selected_dir)
                st.rerun()
    shown = st.session_state.get(f"prev5a_{pid}")
    if shown and os.path.exists(shown[0]):
        with st.container(border=True):
            ui.html(ui.card_title("Xem thử: clip + nhạc", shown[1]))
            show_video(shown[0], video_size_control("vsize_5a"))
    if not has_clips:
        st.caption("Chưa có clip nào (Bước 4) nên chưa thể xem thử nhạc cùng video.")

    with st.container(border=True):
        if provider is None:
            st.info("Chưa cấu hình tạo nhạc: đặt AUDIO_PROVIDER=clipai (hoặc VIDEO_PROVIDER=clipai) và CLIPAI_TOKEN, "
                    "hoặc upload nhạc có sẵn ở trên.")
        else:
            ui.html(ui.card_title("Music Brief", "gợi ý từ mood các cảnh — bạn sửa được") + ui.badge(
                provider.name + (" · giả lập" if provider.name == "mock-audio" else " · music_v2 · tốn credit"), "b-info"))
            brief = music.default_brief(p, pid)
            prompt = st.text_area("Prompt nhạc (≤ 2000 ký tự)", brief["prompt"], key=f"mprompt_{pid}", height=90)
            c1, c2, c3 = st.columns(3)
            seconds = c1.number_input("Độ dài (giây)", 3, 600, max(3, brief["length_ms"] // 1000), key=f"mlen_{pid}")
            instrumental = c2.checkbox("Không lời (instrumental)", brief["instrumental"], key=f"minst_{pid}")
            count = c3.number_input("Số bản nháp", 1, 5, 3, key=f"mcount_{pid}")
            b1, b2, b3 = st.columns([2, 2, 3])
            if b1.button(f"✨ Tạo {int(count)} bản nháp", type="primary", disabled=not prompt.strip()):
                n = music.submit_drafts(provider, drafts_dir, prompt, int(seconds) * 1000, instrumental, int(count),
                                        ledger=(p.conn, pid))
                st.toast(f"Đã gửi {n} bản")
                st.rerun()
            if b2.button("⟳ Kiểm tra + tải về"):
                counts = music.refresh_drafts(provider, drafts_dir)
                st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                st.rerun()
    drafts = music.load_drafts(drafts_dir)
    for start in range(0, len(drafts), 3):
        cols = st.columns(3)
        for col, (i, d) in zip(cols, list(enumerate(drafts))[start:start + 3]):
            with col, st.container(border=True):
                ui.html(f'<div class="cardhead"><b>Bản {chr(65 + i) if i < 26 else i + 1}</b><span class="grow"></span>'
                        f'{ui.state_badge(d["state"])}'
                        + (f' <span class="muted">{d["duration_ms"] / 1000:.0f}s</span>' if d.get("duration_ms") else "")
                        + '</div>')
                if d["state"] == "failed":
                    st.warning(f"Không tạo được: {d.get('message')} (không tự gửi lại để tránh tốn credit)")
                elif d.get("file"):
                    wpath = os.path.join(drafts_dir, d["file"])
                    ui.html(ui.waveform_svg(_peaks(wpath, os.path.getmtime(wpath))))
                    st.audio(wpath)
                    if has_clips and st.button("🎬 Xem thử với video", key=f"prevd_{pid}_{i}"):
                        preview_with_track(p, pid, wpath, f"draft_{i + 1}")
                    if st.button("Chọn bản này", key=f"pick_{pid}_{i}", type="primary"):
                        if act(lambda: music.select_draft(drafts_dir, selected_dir, i), "Đã chọn nhạc nền"):
                            st.rerun()
                else:
                    ui.html('<div class="wave"></div><span class="muted">đang tạo… bấm ‘Kiểm tra + tải về’</span>')
    if drafts and st.button("Xóa danh sách bản nháp"):
        shutil.rmtree(drafts_dir, ignore_errors=True)
        st.rerun()
    with st.expander("🎧 Hiệu ứng âm thanh & giọng đọc (tùy chọn)"):
        extras_section(p, pid, provider)


def extras_section(p: Pipeline, pid: int, provider):
    """Sound effects and voice-over: generate, preview, and choose what goes into the final mix."""
    directory = audio_lib.assets_dir(DATA, pid)
    with st.container(border=True):
        ui.html(ui.card_title("Hiệu ứng âm thanh & giọng đọc", "tùy chọn — trộn vào video ở Bước 5b"))
        if provider is None:
            st.caption("Cần cấu hình nhà cung cấp âm thanh (AUDIO_PROVIDER hoặc VIDEO_PROVIDER=clipai) để tạo mới.")
        else:
            t_sfx, t_tts = st.tabs(["SFX", "Giọng đọc (TTS)"])
            with t_sfx:
                s_prompt = st.text_input("Mô tả hiệu ứng (≤ 2000 ký tự)", key=f"sfx_p_{pid}",
                                         placeholder="A heavy stone door opens slowly")
                c1, c2, c3 = st.columns([2, 1, 2])
                s_sec = c1.number_input("Độ dài (giây, 0.5–30)", 0.5, 30.0, 3.0, 0.5, key=f"sfx_d_{pid}")
                s_loop = c2.checkbox("Loop", False, key=f"sfx_l_{pid}")
                if c3.button("✨ Tạo SFX", disabled=not s_prompt.strip(), key=f"sfx_go_{pid}"):
                    entry = audio_lib.submit_sfx(provider, directory, s_prompt, s_sec, s_loop, ledger=(p.conn, pid))
                    st.toast("Đã gửi SFX" if entry["asset_id"] else f"Lỗi: {entry['message']}")
                    st.rerun()
            with t_tts:
                voices = st.session_state.get(f"voices_{pid}")
                if voices is None:
                    try:
                        voices = provider.voice_actors(owner="official")
                    except ProviderError as e:
                        st.error(f"Không lấy được danh sách giọng: {e}")
                        voices = []
                    st.session_state[f"voices_{pid}"] = voices
                if not voices:
                    st.caption("Chưa có giọng nào để chọn.")
                else:
                    v = st.selectbox("Giọng", voices, format_func=lambda x: f"{x.get('name')} (#{x.get('id')})",
                                     key=f"tts_v_{pid}")
                    t_text = st.text_area("Nội dung (≤ 2000 ký tự)", key=f"tts_t_{pid}", height=80)
                    d1, d2 = st.columns(2)
                    t_model = d1.selectbox("Model", ["eleven_v3", "eleven_multilingual_v2", "eleven_turbo_v2_5"],
                                           key=f"tts_m_{pid}")
                    t_lang = d2.text_input("Mã ngôn ngữ (tùy chọn, vd vi, en)", key=f"tts_l_{pid}")
                    if st.button("✨ Tạo giọng đọc", disabled=not t_text.strip(), key=f"tts_go_{pid}"):
                        entry = audio_lib.submit_tts(provider, directory, t_text, int(v["id"]), str(v.get("name", "")),
                                                     t_model, t_lang.strip() or None, ledger=(p.conn, pid))
                        st.toast("Đã gửi giọng đọc" if entry["asset_id"] else f"Lỗi: {entry['message']}")
                        st.rerun()
            if st.button("⟳ Kiểm tra + tải về", key=f"ax_refresh_{pid}"):
                counts = audio_lib.refresh(provider, directory)
                st.toast(f"Đang chạy {counts['running']} · xong {counts['succeeded']} · lỗi {counts['failed']}")
                st.rerun()
        items = audio_lib.load(directory)
        for i, e in enumerate(items):
            with st.container(border=True):
                ui.html(f'<div class="cardhead"><b>{audio_lib.KINDS.get(e["kind"], e["kind"])}</b>'
                        f'<span class="muted">{e["label"][:90]}</span><span class="grow"></span>{ui.state_badge(e["state"])}</div>')
                if e["state"] == "failed":
                    st.warning(f"Không tạo được: {e.get('message')} (không tự gửi lại để tránh tốn credit)")
                elif e.get("file"):
                    st.audio(os.path.join(directory, e["file"]))
                a, b, c, d = st.columns([2, 1.3, 2, 1], vertical_alignment="center")
                use = a.checkbox("Đưa vào bản ghép", e["use"], key=f"ax_use_{pid}_{i}", disabled=e["state"] != "succeeded")
                start = b.number_input("Bắt đầu (giây)", 0.0, 600.0, float(e["start"]), 0.5, key=f"ax_st_{pid}_{i}")
                vol = c.slider("Âm lượng", 0.0, 2.0, float(e["volume"]), 0.05, key=f"ax_vol_{pid}_{i}")
                if d.button("Xóa", key=f"ax_rm_{pid}_{i}"):
                    audio_lib.remove(directory, i)
                    st.rerun()
                if e["state"] == "succeeded" and (use, start, vol) != (e["use"], e["start"], e["volume"]):
                    audio_lib.set_mix(directory, i, use, start, vol)


# ---- step 5b -------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _peaks(path: str, mtime: float):
    return waveform.peaks(path)


@st.cache_data(show_spinner=False)
def _probe(path: str, mtime: float, requested):
    return final_cut.clip_seconds(path, requested)


def step5b(p: Pipeline, pid: int):
    vdir = project_dir(pid, "videos")
    clips = final_cut.collect_clips(p, DATA, pid)
    present = [c for c in clips if c["path"]]
    missing = [c for c in clips if not c["path"]]
    left, right = st.columns([1.7, 1], gap="large")
    chosen, durations = [], []
    out = os.path.join(project_dir(pid, "output"), "FINAL_VIDEO.mp4")
    with left:
        with st.container(border=True):
            ui.html(ui.card_title("Clip theo thứ tự cảnh", f"{len(present)} có sẵn / {len(clips)} mục · lấy tự động từ Bước 4"))
            vsize = video_size_control("vsize_5b") if present else "Vừa"
            if not present:
                st.info("Chưa có clip nào. Chạy Bước 4 (gen video) hoặc nhập clip thủ công bên dưới.")
            names = ", ".join(f"cảnh {c['idx']}" + (f" ({c['state']})" if c["state"] else "") for c in missing if c["idx"])
            if names:
                st.warning(f"Thiếu clip: {names} — bản ghép sẽ bỏ qua các cảnh này.")
            for c in present:
                label = f"Cảnh {c['idx']} — {c['title']}" if c["idx"] else c["title"]
                base = os.path.basename(c["path"])
                real = _probe(c["path"], os.path.getmtime(c["path"]), c["requested_sec"])
                a, b, d = st.columns([3, 1, 1], vertical_alignment="center")
                use = a.checkbox(label, True, key=f"use_{pid}_{base}")
                sec = d.number_input("Giây", 0.5, 60.0, float(round(real, 2)), 0.1, key=f"sec_{pid}_{base}",
                                     label_visibility="collapsed")
                if b.checkbox("Xem", False, key=f"see_{pid}_{base}"):
                    show_video(c["path"], vsize)
                if use:
                    chosen.append(c["path"])
                    durations.append(sec)
                if c.get("scene_id"):
                    scene_expander(p, c["scene_id"], with_motion=True)
            with st.expander("Nhập clip thủ công (tên file theo thứ tự, vd 01.mp4)"):
                up = st.file_uploader("Clip .mp4", type=["mp4"], accept_multiple_files=True, key=f"vid_{pid}")
                if up and st.button("Lưu clip"):
                    for f in up:
                        with open(os.path.join(vdir, f.name), "wb") as fh:
                            fh.write(f.getvalue())
                    st.rerun()
        if os.path.exists(out):
            with st.container(border=True):
                ui.html(ui.card_title("Preview", "FINAL_VIDEO.mp4") + ui.badge("succeeded", "b-ok")
                        + f' <span class="muted">{os.path.getsize(out) / 1e6:.1f} MB</span>')
                show_video(out, video_size_control("vsize_final"))
                with open(out, "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name="FINAL_VIDEO.mp4", mime="video/mp4")
    with right, st.container(border=True):
        ui.html(ui.card_title("Tùy chọn render"))
        transition = st.radio("Transition", ["cut", "crossfade", "dip_to_black"], horizontal=True, key=f"tr_{pid}",
                              format_func=lambda t: {"cut": "Cut", "crossfade": "Cross-fade", "dip_to_black": "Dip to black"}[t])
        fade = st.slider("Thời gian chuyển cảnh (giây)", 0.3, 2.0, 1.0, 0.1, key=f"fade_{pid}",
                         disabled=transition == "cut")
        music_dir = project_dir(pid, "music")
        tracks = os.listdir(music_dir)
        volume = st.slider("Âm lượng nhạc nền", 0.0, 1.0, 0.6, 0.05, key=f"vol_{pid}", disabled=not tracks)
        st.caption(f"Nhạc nền: {tracks[0]} (chọn ở Bước 5a)" if tracks else "Không có nhạc nền (chọn ở Bước 5a nếu cần).")
        extras = audio_lib.mix_list(audio_lib.assets_dir(DATA, pid))
        st.caption(f"Hiệu ứng / giọng đọc đưa vào bản ghép: {len(extras)} (chọn ở Bước 5a)")
        problems = final_cut.render_problems(durations, transition, fade)
        for msg in problems:
            st.warning(msg)
        if durations and not problems:
            st.info(f"Tổng thời lượng dự kiến: {final_cut.total_seconds(durations, transition, fade):.1f} giây · {len(chosen)} clip")
        if st.button("▶ Render Final", disabled=bool(problems), type="primary", width="stretch"):
            music_file = os.path.join(music_dir, tracks[0]) if tracks else None
            with st.spinner("Đang render…"):
                ok = act(lambda: ffmpeg_studio.render_final(chosen, out, durations, transition, fade, music_file, volume, extras),
                         "Render xong")
            if ok:
                st.rerun()


# ---- history -------------------------------------------------------------------------
def trash_section(pid: int) -> None:
    """Deleted/rejected images and clips, kept for the retention period; restorable."""
    with st.container(border=True):
        ui.html(ui.card_title("🗑 Thùng rác", f"ảnh và video bị xóa/loại · tự xóa vĩnh viễn sau {trash.retention_days()} ngày"))
        t_img, t_vid = st.tabs(["Ảnh", "Video"])
        for tab, kind in ((t_img, "images"), (t_vid, "videos")):
            with tab:
                entries = trash.items(DATA, pid, kind)
                if not entries:
                    st.caption("Trống.")
                for e in entries:
                    a, b = st.columns([3, 1], vertical_alignment="center")
                    with a:
                        if kind == "images":
                            show_image(e["path"], width=220)
                        else:
                            with st.expander("▶ Xem video"):
                                st.video(e["path"])
                        scene = f"Cảnh {e['scene_idx']} · " if e.get("scene_idx") else ""
                        st.caption(f"{scene}{e['reason']} · xóa {time.strftime('%d/%m/%Y %H:%M', time.localtime(e['deleted_at']))}"
                                   f" · còn {e['days_left']} ngày · {e['original']}")
                    if b.button("↩ Khôi phục", key=f"tr_{kind}_{e['file']}"):
                        if act(lambda: trash.restore(DATA, pid, kind, e["file"]), "Đã khôi phục"):
                            st.rerun()


def history(p: Pipeline, pid: int):
    scenes = p.conn.execute("SELECT id, idx, title FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    if not scenes:
        st.caption("Chưa có cảnh.")
        trash_section(pid)
        return
    sid = st.selectbox("Cảnh", [s["id"] for s in scenes],
                       format_func=lambda i: next(f"{s['idx']} · {s['title']}" for s in scenes if s["id"] == i))
    jobs = p.conn.execute("SELECT * FROM jobs WHERE scene_id=? ORDER BY id", (sid,)).fetchall()
    scene_expander(p, sid, expanded=False, with_motion=True)
    size = video_size_control("vsize_hist") if any(j["result_path"] and os.path.exists(j["result_path"]) for j in jobs) else "Vừa"
    with st.container(border=True):
        ui.html(ui.card_title("Lịch sử phiên bản", "so sánh các lần gen"))
        for start in range(0, len(jobs), 3):
            cols = st.columns(3)
            for col, (n, j) in zip(cols, list(enumerate(jobs, 1))[start:start + 3]):
                with col, st.container(border=True):
                    img = job_image(j["project_id"], j["id"])
                    if img:
                        show_image(img, width="stretch")
                    elif j["type"] == "video_gen" and j["result_path"] and os.path.exists(j["result_path"]):
                        show_video(j["result_path"], size)
                    scores = qc_scores(p, j["id"])
                    qc = f" · QC {sum(s['score'] for s in scores) / len(scores):.2f}" if scores else ""
                    ui.html(f'<div class="cardhead"><b>v{n}</b><span class="grow"></span>{ui.state_badge(j["state"])}</div>'
                            f'<div class="muted">{j["type"]}{qc}' + (f' · “{j["retry_reason"]}”' if j["retry_reason"] else "") + "</div>")
    with st.expander("Nhật ký chi tiết các job"):
        for j in jobs:
            st.markdown(f"**job #{j['id']} {j['type']}** — {j['state']} (retry {j['retry_count']})")
            st.dataframe([dict(h) for h in p.history(j["id"])], width="stretch")
    trash_section(pid)


def main():
    st.set_page_config(layout="wide", page_title="AI Video Pipeline")
    ui.inject_css()
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    p = Pipeline(connect(DB))
    pid = global_bar(p)
    if pid is None:
        return
    purge_trash(DATA)
    trash.sweep_rejected(p, DATA, pid)
    deep = st.query_params.get("step")  # ?step=2 opens a step directly (1, 2, 3, 4, 5a, 5b, history)
    keys = ["1", "2", "3", "4", "5a", "5b", "history"]
    if deep in keys and "step" not in st.session_state:
        st.session_state["step"] = STEPS[keys.index(deep)]
    step = st.radio("Bước", STEPS, horizontal=True, key="step", label_visibility="collapsed",
                    format_func=step_label(step_done(p, pid)))
    {STEPS[0]: step1, STEPS[1]: step2, STEPS[2]: step3, STEPS[3]: step4, STEPS[4]: step5a,
     STEPS[5]: step5b, STEPS[6]: history}[step](p, pid)


main()
