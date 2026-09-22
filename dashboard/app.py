"""Unified control dashboard (V1): one tool, stepper by step order, per-step control buttons.

Run:  py -m streamlit run dashboard/app.py
Layout and colors follow mockup/dashboard.html (see dashboard/ui.py).
Claude steps (Director / QC / motion prompt) use copy-paste JSON until the API runner is wired in.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from html import escape

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import asset_vision, autoqc, ff_site, sfx_plan, sound_lib, assets, audio_lib, subtitles, script_reader, auth, autopilot, dialogue, diag, knowledge, lessons, perf, regen, research, style, subjects, trash, waveform, cost, ffmpeg_studio, final_cut, llm_io, llm_runner, music, preflight, prompts, script_parser, video_analysis  # noqa: E402
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
         "5 · Nhạc nền & Ghép video", "📊 Theo dõi hiệu suất"]
STEP_PERMISSION = {"📊 Theo dõi hiệu suất": "monitor"}
# Lịch sử / Bài học / Phân quyền moved off the step bar into the settings gear (see settings_menu()) --
# each opens as its own closable st.dialog panel instead of living inline in the stepper.
DIALOG_FLAGS = ("dlg_assets", "dlg_pricing", "dlg_knowledge", "dlg_history", "dlg_lessons", "dlg_users")


def open_dialog(flag: str) -> None:
    """Only one st.dialog may be open per script run: opening one always closes any other."""
    for f in DIALOG_FLAGS:
        st.session_state[f] = (f == flag)


def close_dialog(flag: str) -> None:
    st.session_state[flag] = False
ERRORS = (sqlite3.IntegrityError, zipfile.BadZipFile, llm_runner.LlmError, InvalidTransition, llm_io.SchemaError, PipelinePaused, ffmpeg_studio.FFmpegNotFound,
          ffmpeg_studio.FFmpegError, ValueError, KeyError)
CRITERIA_LABEL = {"character": "Đúng nhân vật", "hands_face": "Không lỗi tay/mặt", "composition": "Đúng bố cục",
                  "mood_lighting": "Đúng mood / ánh sáng", "consistency": "Không chi tiết thừa/sai"}
FILTERS = {"all": "Tất cả", "review": "Chờ duyệt", "pass": "Đã duyệt", "fail": "FAIL", "run": "Chờ / đang gen"}
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


def confirm_all(key: str, ids, label: str, question: str, container=st, yes_label: str = "Có, duyệt hết") -> bool:
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
    if yes.button(yes_label, key=f"{key}_yes", type="primary"):
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


def show_video(path: str, size: str = "Vừa") -> None:
    """Inline player at a comfortable width; the player's own ⛶ button goes full screen."""
    try:
        st.columns([1, 1])[0].video(path)
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
            bool(scenes) and videos >= scenes,
            os.path.exists(os.path.join(DATA, str(pid), "output", "FINAL_VIDEO.mp4")), False, False, False, False]


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


def distill_panel(group: str, ov: dict) -> None:
    """Read all documents ONCE, keep a short playbook split by topic; the step then reads the playbook only."""
    st.markdown("**🧪 Chắt lọc thành cẩm nang ngắn**")
    st.caption("Claude đọc và phân tích toàn bộ tài liệu một lần, tổng kết thành cẩm nang ngắn chia rõ theo từng mảng nội dung "
               "(" + " · ".join(knowledge.DISTILL_SECTIONS[group][:5]) + " …). Sau đó bước này chỉ đọc cẩm nang, "
               "không đọc lại từng tài liệu.")
    d = ov["distilled"]
    include = st.checkbox("Gồm cả tài liệu kiến thức có sẵn (giảm thêm token mỗi lần chạy)",
                          bool(d.get("include_builtin")) if d["exists"] else False, key=f"kb_inc_{group}")
    inputs = knowledge.distill_inputs(group, include)
    src = sum(len(t) for _, t in inputs)
    st.caption(f"Nguồn để chắt lọc: {len(inputs)} tài liệu · {src:,} ký tự (≈ {knowledge.approx_tokens(src):,} token, chỉ đọc "
               f"một lần khi chắt lọc). Cẩm nang mục tiêu ≈ {knowledge.TARGET_CHARS[group]:,} ký tự.")
    if not d["exists"]:
        st.info("Chưa có cẩm nang: mỗi lần chạy bước này vẫn gửi nguyên các tài liệu.")
    elif d["active"]:
        st.success(f"Đang dùng cẩm nang ({d['chars']:,} ký tự ≈ {d['tokens']:,} token, tạo {d['created_at']}) thay cho "
                   f"≈ {ov['raw_tokens']:,} token tài liệu gốc.")
    elif not d["fresh"]:
        st.warning("Tài liệu đã thay đổi sau lần chắt lọc → cẩm nang đã cũ, tạm thời bước này dùng lại tài liệu gốc. "
                   "Hãy chắt lọc lại.")
    else:
        st.info("Cẩm nang đang TẮT: bước này dùng tài liệu gốc.")
    client = llm_client()
    if client is not None and inputs:
        if st.button("🤖 Chắt lọc bằng Claude API", type="primary", key=f"kb_distill_{group}"):
            with st.spinner("Claude đang đọc và tổng kết tài liệu…"):
                ok = act(lambda: st.session_state.__setitem__("llm_res", llm_runner.run_distill(group, client, include)))
            if ok:
                r = st.session_state.pop("llm_res")
                st.toast(f"Cẩm nang {r['chars']:,} ký tự từ {r['source_chars']:,} ký tự ({tokens_text(r)})")
                st.rerun()
    with st.expander("✍ Chắt lọc tay: prompt gửi Claude + dán cẩm nang"):
        if inputs:
            st.code(knowledge.build_distill_bundle(group, include), language="markdown")
        else:
            st.caption("Chưa có tài liệu để chắt lọc.")
        raw = st.text_area("Dán cẩm nang Claude trả về (Markdown, các mục `## `)", key=f"kb_paste_{group}", height=140)
        if st.button("Lưu cẩm nang", disabled=not raw.strip(), key=f"kb_save_{group}"):
            if act(lambda: knowledge.store_distilled(group, raw, include), "Đã lưu cẩm nang"):
                st.rerun()
    if d["exists"]:
        with st.expander("📘 Xem / sửa cẩm nang"):
            use = st.checkbox("Dùng cẩm nang thay cho tài liệu gốc", d["use"], key=f"kb_use_{group}")
            if use != d["use"]:
                knowledge.set_use_distilled(group, use)
                st.rerun()
            st.caption("Nguồn: " + ", ".join(d["sources"]))
            edited = st.text_area("Nội dung (sửa được)", d["text"], key=f"kb_edit_{group}", height=260)
            if st.button("Lưu chỉnh sửa", key=f"kb_edit_save_{group}", disabled=edited == d["text"]):
                if act(lambda: knowledge.store_distilled(group, edited, d["include_builtin"], d["use"]), "Đã lưu"):
                    st.rerun()
            if confirm_all(f"kb_dclear_{group}", ["x"], "🗑 Xóa cẩm nang", "Xóa cẩm nang (tài liệu gốc vẫn còn)?", st,
                           "Có, xóa"):
                knowledge.clear_distilled(group)
                st.rerun()


def knowledge_panel() -> None:
    """Where the Claude steps get their skills from: what ships with the project, what the user added, and a way to
    add more (documents are appended to that step's prompt while switched on)."""
    keys = list(knowledge.GROUPS)
    group = st.selectbox("Bước dùng Claude", keys, format_func=lambda k: knowledge.GROUPS[k][0], key="kb_group")
    _, purpose, _ = knowledge.GROUPS[group]
    ov = knowledge.overview(group)
    st.caption(purpose)
    m1, m2, m3 = st.columns(3)
    m1.metric("Tài liệu đang bật", sum(1 for d in ov["docs"] if d["enabled"]))
    m2.metric("Ký tự gửi Claude mỗi lần chạy", f"{ov['chars']:,}")
    m3.metric("≈ token mỗi lần chạy", f"{ov['tokens']:,}")
    st.caption(f"📁 Có sẵn (cùng mã nguồn, có trong git): `{ov['builtin_dir']}` và thư mục `prompts/`  ·  "
               f"📁 Bạn thêm (ngoài git): `{ov['user_dir']}`")
    if ov["tokens"] > 25_000:
        st.warning("Lượng tài liệu khá lớn: mỗi lần chạy bước này sẽ gửi ≈ %s token. Tắt bớt tài liệu ít dùng để tiết kiệm." % f"{ov['tokens']:,}")
    st.dataframe([{"Tên": d["title"], "Nguồn": "có sẵn" if d["source"] == "builtin" else "bạn thêm",
                   "Ghi chú": d["note"], "Ký tự": d["chars"], "≈ token": knowledge.approx_tokens(d["chars"]),
                   "Bật": "✓" if d["enabled"] else "—",
                   "Cẩm nang thay thế": "✓" if d.get("replaced") else ""} for d in ov["docs"]],
                 width="stretch", hide_index=True, height=min(38 * (len(ov["docs"]) + 1) + 3, 260))
    distill_panel(group, ov)
    for d in ov["docs"]:
        tag = "" if d["source"] == "builtin" else " · bạn thêm"
        with st.expander(f"📄 {d['title']}{tag}"):
            text = knowledge.read_doc(group, d["source"], d["file"])
            ui.html('<div class="scriptfull">' + escape(text[:6000]) + ("\n…" if len(text) > 6000 else "") + "</div>")
            st.caption(f"{d['chars']:,} ký tự · {d['path']}")
            if d["source"] == "user":
                on = st.checkbox("Bật (gửi kèm mỗi lần chạy)", d["enabled"], key=f"kb_en_{group}_{d['file']}")
                if on != d["enabled"]:
                    knowledge.set_enabled(group, d["file"], on)
                    st.rerun()
                if confirm_all(f"kb_del_{group}_{d['file']}", [d["file"]], "🗑 Xóa tài liệu này",
                               f"Xóa “{d['title']}” khỏi kho?", st, "Có, xóa"):
                    if act(lambda: knowledge.remove_doc(group, d["file"]), "Đã xóa tài liệu"):
                        st.rerun()
            else:
                st.caption("Tài liệu có sẵn chỉ sửa được trong mã nguồn (thư mục knowledge/ và prompts/).")
    st.markdown("**➕ Thêm tài liệu để nâng cấp kho**")
    st.caption(f"File .md, .txt hoặc .docx; mỗi file tối đa {knowledge.MAX_DOC_CHARS:,} ký tự, tổng bổ sung tối đa "
               f"{knowledge.MAX_USER_CHARS:,} ký tự cho mỗi bước. Ví dụ: hướng dẫn phong cách của studio, kịch bản mẫu và "
               "kết quả bạn hài lòng, danh sách lỗi hay gặp.")
    up = st.file_uploader("Tài liệu", type=["md", "txt", "docx"], key=f"kb_up_{group}", label_visibility="collapsed")
    k1, k2 = st.columns(2)
    title = k1.text_input("Tên hiển thị (tùy chọn)", key=f"kb_title_{group}")
    note = k2.text_input("Ghi chú (tùy chọn)", key=f"kb_note_{group}")
    if st.button("⬆ Thêm vào kho", disabled=up is None, key=f"kb_add_{group}", type="primary"):
        if act(lambda: knowledge.add_doc(group, up.name, up.getvalue(), title, note), "Đã thêm tài liệu"):
            st.rerun()


def auth_on() -> bool:
    return os.environ.get("DASHBOARD_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")


def me() -> dict:
    """The signed-in person of THIS browser session ({'email','name','role','perms'})."""
    return st.session_state.get("identity") or {}


def allowed(permission: str) -> bool:
    return auth.can(me(), permission)


def request_source() -> tuple:
    """(where the request came from for the audit log, whether it is the dashboard machine itself)."""
    try:
        host = st.context.headers.get("Host", "") or ""
        ip = st.context.ip_address or ""
    except Exception:  # noqa: BLE001 - an older Streamlit or a test runner: unknown origin
        return "", True
    local = host.split(":")[0].strip("[]") in ("localhost", "127.0.0.1", "::1", "")
    return f"host={host} ip={ip}", local


def lan_address() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        ip = "localhost"
    return f"http://{ip}:{os.environ.get('DASHBOARD_PORT', '8501')}"


def sign_in(conn, email: str) -> bool:
    """Try to sign this browser session in. True on success (the address remembers the e-mail for reloads)."""
    source, local = request_source()
    try:
        st.session_state["auth_token"] = auth.login(conn, email, source, local)
    except auth.AuthError as e:
        st.session_state["login_error"] = str(e)
        return False
    st.session_state.pop("login_error", None)
    st.query_params["login"] = auth.normalize_email(email)
    return True


def login_screen(conn) -> None:
    """Sign-in screen: only an e-mail. Nothing else is shown until someone signs in."""
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        ui.html('<div class="brand" style="font-size:20px"><i></i>AI Video Pipeline</div>')
        email = st.text_input("E-mail của bạn", key="login_email", placeholder="ten@garena.vn")
        if st.button("Vào Dashboard", key="login_btn", type="primary") and sign_in(conn, email):
            st.rerun()
        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])
        st.caption("Chỉ cần nhập e-mail. E-mail công ty được vào với quyền làm video; quyền khác do Owner cấp.")


def require_login(conn) -> None:
    """Sets st.session_state['identity']; shows the sign-in screen and stops the page when nobody is signed in."""
    if not auth_on():
        st.session_state["identity"] = {"email": "local", "name": "Local (đăng nhập tắt)", "role": "owner", "perms": []}
        return
    auth.ensure_owner(conn)
    ident = auth.identity(conn, st.session_state.get("auth_token"))
    if ident is None:
        st.session_state.pop("identity", None)
        st.session_state.pop("auth_token", None)
        remembered = st.query_params.get("login")          # a reload or a bookmark: ?login=ten@garena.vn
        if remembered and not st.session_state.get("login_tried") and sign_in(conn, remembered):
            st.session_state["login_tried"] = True
            ident = auth.identity(conn, st.session_state.get("auth_token"))
        st.session_state["login_tried"] = True
        if ident is None:
            login_screen(conn)
            st.stop()
    st.session_state["identity"] = {"email": ident.email, "name": ident.name, "role": ident.role, "perms": ident.perms}


def current_pid(p: Pipeline):
    """The project selected in the header dropdown (global_bar), read from session_state so the header row
    (rendered above the dropdown) already knows it in the same script run -- selectbox key="global_pid"."""
    ids = [r["id"] for r in p.conn.execute("SELECT id FROM projects ORDER BY id").fetchall()]
    pid = st.session_state.get("global_pid")
    return pid if pid in ids else (ids[0] if ids else None)


def new_project_control(p: Pipeline) -> None:
    """The "+ new project" action, next to the user's name -- a lightweight popover, not a full dialog."""
    with st.popover("➕ Dự án mới", help="Tạo dự án mới"):
        name = st.text_input("Tên dự án", key="new_name")
        if st.button("Tạo dự án", key="new_project_go", type="primary", disabled=not name.strip()):
            pid = p.create_project(name.strip(), created_by=me()["email"])
            st.session_state["global_pid"] = pid
            st.rerun()


def settings_menu(p: Pipeline, pid) -> None:
    """Gear icon next to sign-out: every settings-like feature opens as its own closable panel (st.dialog,
    native X) instead of living inline in the page. Kho tài nguyên/Bảng giá/Kho kiến thức only need the DB;
    Lịch sử/Bài học/Phân quyền act on the project selected in the header. Old ?step=history/lessons/users
    deep links still work -- they open the matching dialog once per browser session."""
    deep = st.query_params.get("step")
    if deep in ("history", "lessons", "users") and "deep_dialog_done" not in st.session_state:
        st.session_state["deep_dialog_done"] = True
        if deep == "history":
            open_dialog("dlg_history")
        elif deep == "lessons" and allowed("lessons"):
            open_dialog("dlg_lessons")
        elif deep == "users" and allowed("users"):
            open_dialog("dlg_users")
    with st.popover("⚙", help="Cài đặt"):
        if allowed("assets") and st.button("📁 Kho tài nguyên", key="settings_assets", width="stretch"):
            open_dialog("dlg_assets")
        if allowed("settings") and st.button("💲 Bảng giá", key="settings_pricing", width="stretch"):
            open_dialog("dlg_pricing")
        if allowed("knowledge") and st.button("📚 Kho kiến thức", key="settings_knowledge", width="stretch"):
            open_dialog("dlg_knowledge")
        if pid is not None:
            st.divider()
            if st.button("🗒 Lịch sử", key="settings_history", width="stretch"):
                open_dialog("dlg_history")
            if allowed("lessons") and st.button("🎓 Bài học", key="settings_lessons", width="stretch"):
                open_dialog("dlg_lessons")
            if allowed("users") and st.button("👥 Phân quyền", key="settings_users", width="stretch"):
                open_dialog("dlg_users")
    if st.session_state.get("dlg_assets"):
        _dialog_assets(p)
    if st.session_state.get("dlg_pricing"):
        _dialog_pricing()
    if st.session_state.get("dlg_knowledge"):
        _dialog_knowledge()
    if pid is not None and st.session_state.get("dlg_history"):
        _dialog_history(p, pid)
    if pid is not None and st.session_state.get("dlg_lessons"):
        _dialog_lessons(p, pid)
    if pid is not None and st.session_state.get("dlg_users"):
        _dialog_users(p, pid)


@st.dialog("📁 Kho tài nguyên", width="large", on_dismiss=lambda: close_dialog("dlg_assets"))
def _dialog_assets(p: Pipeline) -> None:
    asset_library_panel(p)


@st.dialog("💲 Bảng giá", on_dismiss=lambda: close_dialog("dlg_pricing"))
def _dialog_pricing() -> None:
    price_editor()


@st.dialog("📚 Kho kiến thức (Director, QC, Motion)", width="large", on_dismiss=lambda: close_dialog("dlg_knowledge"))
def _dialog_knowledge() -> None:
    knowledge_panel()


@st.dialog("🗒 Lịch sử", width="large", on_dismiss=lambda: close_dialog("dlg_history"))
def _dialog_history(p: Pipeline, pid: int) -> None:
    history(p, pid)


@st.dialog("🎓 Bài học", width="large", on_dismiss=lambda: close_dialog("dlg_lessons"))
def _dialog_lessons(p: Pipeline, pid: int) -> None:
    lessons_tab(p, pid)


@st.dialog("👥 Phân quyền", width="large", on_dismiss=lambda: close_dialog("dlg_users"))
def _dialog_users(p: Pipeline, pid: int) -> None:
    users_tab(p, pid)


def account_bar(p: Pipeline) -> None:
    """Identity + quick actions (new project, settings gear) + sign-out, all in one top bar."""
    conn = p.conn
    who = me()
    c1, c2, c3, c4 = st.columns([5, 1.6, 0.6, 1.1], vertical_alignment="center")
    role = "Owner" if who["role"] == "owner" else "Thành viên"
    c1.markdown(f"👤 **{escape(who['name'])}** · {escape(who['email'])} · {role}")
    with c2:
        new_project_control(p)
    with c3:
        settings_menu(p, current_pid(p))
    if not auth_on():
        c1.caption("Đăng nhập đang tắt (DASHBOARD_AUTH=off): mọi người đều là Owner.")
        return
    if c4.button("Đăng xuất", key="logout_btn"):
        auth.logout(conn, st.session_state.get("auth_token"))
        for key in ("auth_token", "identity", "login_tried"):
            st.session_state.pop(key, None)
        st.query_params.pop("login", None)
        st.rerun()


def users_tab(p: Pipeline, pid: int) -> None:
    """Owner only: the permission table."""
    conn = p.conn
    actor = auth.Identity(me()["email"], me()["name"], me()["role"], me().get("perms", []))
    ui.html(ui.card_title("👥 Bảng phân quyền", "nhập e-mail và tick những gì người đó được dùng"))
    st.caption("Mọi người đều có các bước làm video (kể cả chế độ tự động). Ở đây bạn cấp thêm: cài đặt & bảng giá, kho kiến thức, theo dõi "
               "hiệu suất, bài học. Quản lý người dùng và tắt Dashboard chỉ dành cho Owner.")
    people = [u for u in auth.list_users(conn) if u["role"] != "owner"]
    st.markdown(f"**Owner:** {escape(auth.OWNER_EMAIL)} — toàn quyền, không ai đổi được.")
    perm_cols = list(auth.PERM_LABELS.items())
    if people:
        table = [{"E-mail": u["email"], "Được vào": u["active"],
                  **{label: key in u["perms"] for key, label in perm_cols},
                  "Đăng nhập gần nhất": u["last_login"] or "-"} for u in people]
        edited = st.data_editor(table, hide_index=True, width="stretch", key="perm_table",
                                disabled=["E-mail", "Đăng nhập gần nhất"])
        if st.button("💾 Lưu bảng phân quyền", key="perm_save", type="primary"):
            try:
                rows = [{"email": r["E-mail"], "active": bool(r["Được vào"]),
                         "perms": [key for key, label in perm_cols if r[label]]} for r in edited.to_dict("records")
                        ] if hasattr(edited, "to_dict") else [
                    {"email": r["E-mail"], "active": bool(r["Được vào"]), "perms": [k for k, l in perm_cols if r[l]]} for r in edited]
                changed = auth.apply_table(conn, actor, rows)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.success(f"Đã lưu ({changed} thay đổi). Có hiệu lực ngay, kể cả với người đang đăng nhập.")
    else:
        st.caption("Chưa có ai khác trong bảng. Người dùng e-mail công ty tự vào được ở quyền cơ bản (xem mục tên miền bên dưới).")
    with st.container(border=True):
        st.markdown("**Thêm e-mail**")
        c1, c2, c3 = st.columns([3, 3, 1.4], vertical_alignment="bottom")
        new_email = c1.text_input("E-mail", key="add_email", placeholder="ten@garena.vn")
        new_perms = c2.multiselect("Quyền thêm", list(auth.PERM_LABELS), format_func=lambda k: auth.PERM_LABELS[k], key="add_perms")
        if c3.button("Thêm", key="add_go", type="primary"):
            try:
                auth.add_user(conn, actor, new_email, new_perms)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.rerun()
    if people:
        with st.container(border=True):
            st.markdown("**Xóa khỏi bảng**")
            gone = st.selectbox("E-mail", [u["email"] for u in people], key="rm_email")
            if confirm_all("rm_user", [gone], "Xóa khỏi bảng", f"Xóa {gone}? (nếu là e-mail công ty, họ vẫn tự vào lại được ở quyền cơ bản)", st,
                           "Có, xóa"):
                try:
                    auth.remove_user(conn, actor, gone)
                except auth.AuthError as e:
                    st.error(str(e))
                else:
                    st.rerun()
    with st.container(border=True):
        st.markdown("**Ai tự vào được (quyền cơ bản)**")
        domains = st.text_input("Tên miền e-mail được tự vào làm Thành viên (cách nhau bằng dấu phẩy; để trống = chỉ e-mail trong bảng)",
                                ", ".join(auth.auto_domains(conn)), key="auto_domains")
        if st.button("Lưu tên miền", key="auto_domains_save"):
            try:
                auth.set_auto_domains(conn, actor, domains)
            except auth.AuthError as e:
                st.error(str(e))
            else:
                st.success("Đã lưu")
        st.caption(f"Địa chỉ đưa cho người khác: {lan_address()}")
    st.markdown(":orange[Không có mật khẩu: ai mở được Dashboard và gõ đúng e-mail của một người thì vào như người đó, kể cả Owner. "
                "Chỉ dùng trong mạng tin cậy. Muốn Owner chỉ đăng nhập từ máy chạy Dashboard, đặt DASHBOARD_OWNER_LOCAL_ONLY=1.]")
    with st.expander("Nhật ký (đăng nhập, thay đổi quyền)"):
        st.dataframe([{"Lúc": r["at"], "Ai": r["email"] or "", "Việc": r["action"], "Chi tiết": r["detail"] or ""}
                      for r in auth.recent_audit(conn)], hide_index=True, use_container_width=True)


def clean_name(raw: str) -> str:
    return " ".join((raw or "").split())[:40]


def user_bar() -> str:
    """Who is using the dashboard (honour system, no password). Kept in the address (?user=Ten) so a refresh or a
    bookmark remembers it; every job created from this browser is counted for this name."""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = clean_name(st.query_params.get("user", ""))
    c1, c2 = st.columns([2, 5], vertical_alignment="center")
    typed = clean_name(c1.text_input("👤 Tên của bạn", value=st.session_state["user_name"], placeholder="ví dụ: Viet",
                                     key="user_input", help="Để hệ thống ghi nhận ai đã gen video. Không cần mật khẩu."))
    if typed != st.session_state["user_name"]:
        st.session_state["user_name"] = typed
        st.query_params["user"] = typed
    if not typed:
        c2.markdown(":orange[Nhập tên trước khi gen ảnh/video để lượt gen được ghi cho bạn (nếu để trống sẽ tính là “chưa nhập tên”).]")
    return typed


def can_delete_project(proj) -> bool:
    """Only the person who created a project may delete it (an old project with no recorded creator: the Owner)."""
    if not auth_on():
        return True
    creator = proj["created_by"] if "created_by" in proj.keys() else None
    who = me()
    return who["email"] == creator if creator else who["role"] == "owner"


def project_settings_popover(p: Pipeline, pid: int, proj) -> None:
    """Gear next to the project picker: QC mode/threshold + delete -- moved off the control bar itself
    (2026-09-22 cleanup, same "gear -> popover" pattern as the header's settings_menu) so that row only
    keeps the picker, the risk note and the frequently-used Pause/Resume/Cancel buttons."""
    with st.popover("⚙", help="Cấu hình dự án: chế độ QC, threshold, xóa dự án"):
        mode = st.radio("Chế độ QC", ["auto", "human_qc"], index=0 if proj["operating_mode"] == "auto" else 1,
                        horizontal=True, key=f"mode_{pid}")
        if mode != proj["operating_mode"]:
            p.set_mode(pid, mode)
        th = st.slider("QC threshold", 0.5, 1.0, float(proj["qc_auto_pass_threshold"]), 0.01, key=f"th_{pid}")
        if abs(th - proj["qc_auto_pass_threshold"]) > 1e-9:
            p.set_threshold(pid, th)
        st.divider()
        st.caption("🗑 Xóa dự án cùng cảnh, ảnh, clip, nhạc và video đã tạo (tài nguyên trong kho chung không bị xóa; lịch sử chi tiêu được giữ). "
                   "Chỉ người tạo dự án mới xóa được (dự án cũ chưa ghi người tạo thì Owner xóa).")
        if not can_delete_project(proj):
            who = proj["created_by"]
            st.caption("Dự án này do " + (escape(who) if who else "người dùng cũ") + " tạo nên bạn không xóa được.")
        elif confirm_all(f"proj_del_{pid}", [pid], "🗑 Xóa dự án", f"Xóa hẳn dự án “{proj['name']}”? Không thể khôi phục.", st, "Có, xóa dự án"):
            autopilot.stop(p, pid, "Dự án bị xóa")
            p.cancel_all_active(pid)
            p.delete_project(pid, DATA)
            st.toast(f"Đã xóa dự án “{proj['name']}”")
            st.rerun()


def global_bar(p: Pipeline):
    """Project picker + per-project controls. Project creation and the Kho tài nguyên/Bảng giá/Kho kiến thức
    panels moved to the header (account_bar -> new_project_control / settings_menu); mode/threshold/delete
    moved into project_settings_popover so this row only keeps the picker, risk note and Pause/Resume/Cancel."""
    projects = p.conn.execute("SELECT id, name FROM projects ORDER BY id").fetchall()
    if not projects:
        st.info("Chưa có dự án. Bấm “➕ Dự án mới” ở đầu trang để bắt đầu.")
        return None
    with st.container(border=True):
        c0, c1, c2, c3, c4 = st.columns([1.4, 2.2, 1.3, 0.6, 3.0], vertical_alignment="center")
        c0.markdown('<div class="brand"><i></i>AI Video Pipeline</div>', unsafe_allow_html=True)
        ids = [r["id"] for r in projects]
        default_pid = current_pid(p)
        pid = c1.selectbox("Dự án", ids, index=ids.index(default_pid) if default_pid in ids else 0,
                           format_func=lambda i: next(r["name"] for r in projects if r["id"] == i), key="global_pid")
        proj = p.project(pid)
        with c2:
            risk_popover(p, pid)
        with c3:
            project_settings_popover(p, pid, proj)
        b1, b2, b3 = c4.columns(3)
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
    ap = autopilot.status(p, pid)
    if ap["state"] in ("running", "queued"):
        st.caption(f"🚀 Chế độ tự động: {ap['note']} (xem chi tiết ở Bước 1)")
    return pid


# ---- step 1 --------------------------------------------------------------------------
@st.cache_resource
def autopilot_manager(db: str, data: str):
    return autopilot.Manager(db, data, poll_sec=float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))


@st.fragment(run_every=5)
def autopilot_progress(pid: int) -> None:
    """Live progress (refreshes itself every 5 s while the page is open; the run itself lives in a background thread)."""
    p = Pipeline(connect(DB))
    info = autopilot.status(p, pid)
    state = info["state"]
    tag = {"queued": ("xếp hàng", "b-warn"), "running": ("đang chạy", "b-info"), "done": ("hoàn tất", "b-ok"), "needs_attention": ("cần bạn xử lý", "b-warn"),
           "stopped": ("đã dừng", "b-warn"), "error": ("lỗi", "b-bad")}.get(state, (state, ""))
    ui.html(ui.badge(*tag) + f' <span class="muted">{escape(info["note"])}</span>')
    for label, done, total in autopilot.progress(p, pid, DATA):
        st.progress(0 if not total else min(done / total, 1.0), text=f"{label}: {done}/{total}")
    if info["log"]:
        st.caption(" · ".join(f"{e['at']} {e['msg']}" for e in info["log"][-4:]))
    mgr = autopilot_manager(DB, DATA)
    stale = (autopilot.is_stale(p, pid, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
             or (state == "queued" and not mgr.queued(pid) and not mgr.alive(pid)))
    if stale:
        st.warning("Không thấy tiến trình chạy nền (có thể máy chủ vừa khởi động lại). Bấm “Tiếp tục”.")
    if state == "queued" and not stale:
        if st.button("■ Bỏ khỏi hàng đợi", key=f"ap_unqueue_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state == "running" and not stale:
        c1, c2 = st.columns(2)
        if c1.button("⏸ Tạm dừng", key=f"ap_pause_{pid}"):
            p.set_paused(pid, True)
        if c2.button("■ Dừng hẳn", key=f"ap_stop_{pid}"):
            autopilot.stop(p, pid)
            st.rerun()
    elif state in ("needs_attention", "stopped", "error") or stale:
        if st.button("▶ Tiếp tục", key=f"ap_resume_{pid}", type="primary"):
            autopilot.resume(p, pid, p.actor)
            autopilot_manager(DB, DATA).start(pid)
            st.rerun()
    if state == "done":
        out = os.path.join(DATA, str(pid), "output", "FINAL_VIDEO.mp4")
        if os.path.exists(out):
            show_video(out)


def autopilot_panel(p: Pipeline, pid: int) -> None:
    """Fully automatic mode for short clips: approve the scene breakdown once, the rest runs by itself."""
    if not allowed("autopilot"):
        return
    info = autopilot.status(p, pid)
    with st.container(border=True):
        ui.html(ui.card_title("🚀 Chế độ tự động hoàn toàn (clip ngắn)", "bạn chỉ duyệt phân cảnh, phần còn lại tự chạy"))
        if info["state"] in ("queued", "running", "done", "needs_attention", "stopped", "error"):
            autopilot_progress(pid)
            if info["state"] not in ("running", "queued"):
                with st.expander("Chạy lại từ đầu cho dự án này"):
                    st.caption("Đặt lại trạng thái tự động (ảnh/video đã làm được giữ nguyên).")
                    if st.button("↺ Đặt lại chế độ tự động", key=f"ap_reset_{pid}"):
                        p.conn.execute("UPDATE projects SET autopilot_state=NULL, autopilot_note=NULL WHERE id=?", (pid,))
                        p.conn.commit()
                        st.rerun()
            return
        st.caption("Sau khi bạn duyệt phân cảnh, hệ thống tự làm: Director (Character Bible + thông số cảnh) → gen ảnh → Claude chấm QC "
                   "(đạt ngưỡng thì tự duyệt) → Claude viết motion prompt (tự duyệt) → gen video → 1 bản nhạc nền → ghép video cuối. "
                   "Gặp việc cần người (cảnh hết số lần thử, bị chặn risk control, chạm trần số job) thì **dừng và báo**, "
                   "không tự đoán. Cần Claude API, Deepix và Clip AI đã cấu hình.")
        issues = autopilot.problems(p, pid)
        for msg in issues:
            st.markdown(f":red[✖ {msg}]")
        scenes = p.conn.execute("SELECT COUNT(*) c FROM scenes WHERE project_id=?", (pid,)).fetchone()["c"]
        per = p.project(pid)["max_retry_count"] + 2
        if not issues:
            st.success(f"Sẵn sàng: {scenes} cảnh. Trần an toàn: tối đa {scenes * per} job ảnh và {scenes * per} job video "
                       "(kể cả gen lại).")
        if confirm_all(f"ap_start_{pid}", ["go"], "✔ Duyệt phân cảnh & chạy tự động hoàn toàn",
                       "Bắt đầu chạy tự động? Sẽ gọi Deepix, Clip AI và Claude thật (tốn credit) cho toàn bộ dự án.", st,
                       "Có, chạy") and not issues:
            autopilot.start(p, pid, p.actor)
            autopilot_manager(DB, DATA).start(pid)
            st.rerun()
        if issues:
            st.caption("Hãy xử lý các mục đỏ ở trên trước khi bấm chạy.")


WB_LABELS = (("render_style", "Phong cách dựng hình", "vd: hoạt hình 3D mềm, không viền, chuyển sắc liên tục"),
             ("palette", "Bảng màu", "màu chủ đạo, màu điểm nhấn, phủ định (no bloom...)"),
             ("texture_finish", "Chất liệu / hoàn thiện", "hạt phim, tương phản, chất ống kính"),
             ("lighting_logic", "Logic ánh sáng (tùy chọn)", "ánh sáng đến từ nguồn nào"),
             ("era_lore", "Thời đại / thế giới (tùy chọn)", "ràng buộc để không lệch thời đại"),
             ("physics", "Vật lý / thời tiết (tùy chọn)", "mưa, trọng lực, chất liệu chuyển động thế nào"))


def world_bible_panel(p: Pipeline, pid: int) -> None:
    """Project style bible: written by hand or drafted by Claude from reference pictures, then inherited by every prompt."""
    saved = style.load(p, pid)
    with st.expander("⚙ Tùy chọn nâng cao · 🎨 Phong cách hình ảnh (World Bible)" + (" ✓" if any(saved.values()) else ""),
                     expanded=False):
        st.caption("Khóa một bộ tham số phong cách dùng chung: Director và Motion sẽ kế thừa cho **mọi** cảnh, tránh cảnh này một kiểu cảnh kia "
                   "một kiểu. Gõ tay, hoặc tải 2–6 ảnh tham khảo để Claude soạn bản nháp rồi bạn sửa. Bản nháp chỉ có tác dụng sau khi bạn bấm Lưu.")
        proj_wb = p.project(pid)
        sb_on = st.checkbox("📽 Chế độ Storyboard (mỗi cảnh dùng ảnh cảnh TRƯỚC làm thêm 1 ảnh tham chiếu)",
                            bool(proj_wb["storyboard_mode"]), key=f"sb_mode_{pid}",
                            help="Deepix không có Storyboard qua API (chỉ web) — đây là cách thay thế: khi gen ảnh cảnh N, "
                                 "ảnh cảnh N-1 đã duyệt được gửi kèm làm ảnh tham chiếu bổ sung (giữ phong cách/ánh sáng/bố cục "
                                 "liên tục như storyboard thật), cộng với ảnh nhân vật/bối cảnh như bình thường. Chỉ áp dụng khi "
                                 "cảnh trước ĐÃ có ảnh duyệt; cảnh đầu tiên không có gì để nối nên vẽ như cũ. Tắt mặc định vì không "
                                 "phải dự án nào cũng có các cảnh nối tiếp nhau về không gian/thời gian.")
        if sb_on != bool(proj_wb["storyboard_mode"]):
            p.set_storyboard_mode(pid, sb_on)
        uploads = st.file_uploader("Ảnh tham khảo phong cách", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   key=f"wb_up_{pid}")
        llm = llm_runner.client_from_env()
        if st.button("🤖 Phân tích ảnh phong cách bằng Claude", key=f"wb_run_{pid}", disabled=not uploads or llm is None,
                     help="Cần ANTHROPIC_API_KEY và ít nhất 1 ảnh"):
            folder = project_dir(pid, "style_refs")
            paths = []
            for i, f in enumerate(uploads[:style.MAX_REFS], 1):
                path = os.path.join(folder, f"ref_{i}{os.path.splitext(f.name)[1].lower() or '.png'}")
                with open(path, "wb") as fh:
                    fh.write(f.getvalue())
                paths.append(path)
            try:
                draft = style.analyse(llm, paths, note=lambda m: diag.record(p.conn, "director", "warn", m, "bad_json_retry", pid))
            except ERRORS as e:
                st.error(str(e))
            else:
                for key, _, _ in WB_LABELS:
                    st.session_state[f"wb_{key}_{pid}"] = draft.get(key) or ""
                st.session_state[f"wb_draft_{pid}"] = draft
        draft = st.session_state.get(f"wb_draft_{pid}")
        if draft:
            st.info(draft.get("plain_note") or "Đã soạn bản nháp: xem và sửa các ô bên dưới rồi Lưu.")
            for flag in draft.get("check_flags") or []:
                st.markdown(f":orange[⚠ {escape(str(flag))}]")
            if draft.get("candidate_elements"):
                with st.expander("Yếu tố bầu không khí nhận ra (gợi ý, tùy chọn)"):
                    for el in draft["candidate_elements"]:
                        st.markdown(f"- **{escape(str(el.get('label', '')))}**: `{escape(str(el.get('prose', '')))}` "
                                    f"— {escape(str(el.get('evidence', '')))}")
        values = {}
        for key, label, hint in WB_LABELS:
            values[key] = st.text_area(label, value=saved.get(key, ""), key=f"wb_{key}_{pid}", placeholder=hint, height=68)
        c1, c2 = st.columns(2)
        if c1.button("💾 Lưu World Bible", key=f"wb_save_{pid}", type="primary"):
            style.save(p, pid, values)
            st.success("Đã lưu. Chạy lại Director/Motion để áp dụng cho các cảnh chưa làm.")
        if c2.button("Xóa World Bible", key=f"wb_clear_{pid}"):
            style.save(p, pid, {})
            for key, _, _ in WB_LABELS:
                st.session_state.pop(f"wb_{key}_{pid}", None)
            st.rerun()


RESIZE_PRESETS = {"Dọc 1080×1920 (TikTok/Reels/Shorts)": (1080, 1920), "Ngang 1920×1080": (1920, 1080),
                  "Ngang 1558×720": (1558, 720), "Vuông 1080×1080": (1080, 1080), "Tự nhập": None}


def resize_panel(pid: int, src: str) -> None:
    """Export a copy at a given size and file-size limit (2-pass encoding), e.g. for upload limits."""
    with st.expander("📐 Xuất bản theo kích thước / dung lượng"):
        st.caption("Tạo thêm một bản của video cuối theo kích thước và dung lượng tối đa bạn cần (tự tính bitrate, mã hóa 2 lượt, "
                   "tự nén lại nếu vượt). Bản gốc không bị đổi.")
        preset = st.selectbox("Kích thước", list(RESIZE_PRESETS), key=f"rs_preset_{pid}")
        size = RESIZE_PRESETS[preset]
        c1, c2, c3 = st.columns(3)
        width = c1.number_input("Rộng", 64, 7680, size[0] if size else 1080, 2, key=f"rs_w_{pid}", disabled=size is not None)
        height = c2.number_input("Cao", 64, 7680, size[1] if size else 1920, 2, key=f"rs_h_{pid}", disabled=size is not None)
        limit = c3.number_input("Dung lượng tối đa (MB, 0 = không giới hạn)", 0.0, 2000.0, 15.0, 1.0, key=f"rs_mb_{pid}")
        if st.button("Xuất bản", key=f"rs_go_{pid}"):
            w, h = size if size else (int(width), int(height))
            dst = os.path.join(project_dir(pid, "output"), f"FINAL_VIDEO_{w}x{h}.mp4")
            try:
                with st.spinner("Đang mã hóa…"):
                    res = ffmpeg_studio.resize_to_size(src, dst, w, h, limit or None)
            except ERRORS as e:
                st.error(str(e))
            else:
                (st.success if res["fits"] else st.warning)(
                    f"Xong: {res['size_mb']:.1f} MB" + ("" if res["fits"] else f" — vẫn vượt {limit:g} MB sau {res['attempts']} lần, thử kích thước nhỏ hơn"))
                with open(dst, "rb") as f:
                    st.download_button(f"⬇ Tải {os.path.basename(dst)}", f, file_name=os.path.basename(dst), mime="video/mp4",
                                       key=f"rs_dl_{pid}")


def asset_thumbs(items, width: int = 80) -> None:
    """A row of the first picture of each asset."""
    with_pics = [a for a in items if a["images"]]
    if with_pics:
        cols = st.columns(min(len(with_pics), 8))
        for col, a in zip(cols, with_pics[:8]):
            col.image(a["images"][0]["path"], caption=a["name"], width=width)


def assets_panel(p: Pipeline, pid: int) -> None:
    """Step 1, after the script is split: pick the resources (characters, weapons, pets, places...) that go with this script."""
    proj = p.project(pid)
    game = proj["game"]
    text = proj["script_text"] or "\n".join(json.loads(s["data"] or "{}").get("text", "") for s in
                                            p.conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,)))
    chosen = assets.project_assets(p.conn, pid)
    chosen_ids = {a["id"] for a in chosen}
    suggested = [a for a in assets.find_in_text(p.conn, text, game, pid) if a["id"] not in chosen_ids]
    label = f"🧰 Tài nguyên đi kèm kịch bản — {len(chosen)} đã chọn" + (f" · {len(suggested)} gợi ý mới" if suggested else "")
    with st.expander(label, expanded=bool(suggested) or bool(chosen)):
        st.caption("Chọn nhân vật, vũ khí, thú cưng, bản đồ… có sẵn trong kho (hoặc tải ảnh riêng) để dùng cùng kịch bản. Director sẽ dùng đúng "
                   "tên và thiết kế này thay vì tự nghĩ ra, và ảnh của chúng là ảnh tham khảo khi gen.")
        if suggested:
            st.markdown("**Tìm thấy trong kịch bản** (gợi ý):")
            for a in suggested:
                c1, c2, c3 = st.columns([1, 6, 1.6], vertical_alignment="center")
                if a["images"]:
                    c1.image(assets.thumbnail(a["images"][0]["path"], 112), width=56)
                c2.markdown(f"**{escape(a['name'])}** · {a['kind_label']} · xuất hiện {a['mentions']} lần"
                            + (f" — {escape(a['description'][:90])}" if a["description"] else ""))
                if c3.button("➕ Dùng", key=f"as_use_{pid}_{a['id']}"):
                    assets.attach(p.conn, pid, a["id"])
                    st.rerun()
            if st.button("➕ Dùng tất cả gợi ý", key=f"as_use_all_{pid}"):
                for a in suggested:
                    assets.attach(p.conn, pid, a["id"])
                st.rerun()
        if chosen:
            st.markdown("**Đang dùng cho dự án này:**")
            for a in chosen:
                c1, c2, c3 = st.columns([1, 6, 1.4], vertical_alignment="center")
                if a["images"]:
                    c1.image(assets.thumbnail(a["images"][0]["path"], 112), width=56)
                scope = "riêng dự án" if a["project_id"] else "kho chung"
                c2.markdown(f"**{escape(a['name'])}** · {a['kind_label']} · {scope} · {len(a['images'])} ảnh")
                if c3.button("✖ Bỏ", key=f"as_drop_{pid}_{a['id']}"):
                    assets.detach(p.conn, pid, a["id"])
                    st.rerun()
        library = [a for a in assets.list_assets(p.conn, game, None, pid) if a["id"] not in chosen_ids]
        if library:
            labels = {a["id"]: f"{a['kind_label']}: {a['name']}" for a in library}
            pick = st.selectbox("Thêm từ kho", [None] + list(labels), key=f"as_pick_{pid}",
                                format_func=lambda i: "— chọn —" if i is None else labels[i])
            if pick is not None and st.button("➕ Thêm vào dự án", key=f"as_add_{pid}"):
                assets.attach(p.conn, pid, pick)
                st.rerun()
        elif not chosen:
            st.caption(f"Kho tài nguyên của game này đang trống. Người quản lý có thể thêm ở nút “⚙” (Cài đặt) → Kho tài nguyên; "
                       "hoặc bạn tải ảnh riêng ở dưới.")
        with st.container(border=True):
            st.markdown("**⬆ Tải ảnh riêng cho dự án này** (nhân vật gốc, đạo cụ…)")
            n1, n2 = st.columns([3, 2])
            name = n1.text_input("Tên", key=f"as_new_name_{pid}", placeholder="vd Lyra")
            kind = n2.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key=f"as_new_kind_{pid}")
            desc = st.text_input("Mô tả ngắn (tùy chọn)", key=f"as_new_desc_{pid}", placeholder="tóc bạc dài, giáp xanh…")
            files = st.file_uploader("Ảnh (JPG/PNG/WebP, tối đa 10 MB mỗi ảnh)", type=["png", "jpg", "jpeg", "webp"],
                                     accept_multiple_files=True, key=f"as_new_files_{pid}")
            share = allowed("assets") and st.checkbox("Lưu cả vào kho dùng chung", key=f"as_new_share_{pid}")
            if st.button("Lưu vào dự án", key=f"as_new_go_{pid}", disabled=not (name.strip() and files)):
                try:
                    aid = assets.create(p.conn, game, kind, name, desc, "", None if share else pid, me().get("email"))
                    for f in files[: assets.MAX_IMAGES_PER_ASSET]:
                        assets.add_image(p.conn, aid, f.name, f.getvalue())
                    assets.attach(p.conn, pid, aid)
                except assets.AssetError as e:
                    st.error(str(e))
                else:
                    st.rerun()


def asset_library_panel(p: Pipeline) -> None:
    """Settings: the shared resource library (people with the Kho tài nguyên right)."""
    catalog = subjects.games()
    keys = list(catalog)
    game = st.selectbox("Game / loại nội dung", keys, format_func=lambda k: catalog[k][0], key="lib_game")
    items = assets.list_assets(p.conn, game, None, None, shared_only=True)
    st.caption(f"{len(items)} mục trong kho **{catalog[game][0]}**. Mọi dự án của game này đều chọn dùng được.")
    with st.expander("🔄 Nguồn đồng bộ: thư mục tài nguyên (cập nhật kho bằng 1 cú bấm hoặc tự động)", expanded=not assets.list_sources(p.conn, game)):
        st.caption("Chọn một thư mục trên máy chạy Dashboard chứa ảnh (ví dụ thư mục đang đồng bộ với Google Drive). Kho sẽ giống thư mục đó: "
                   "ảnh mới được thêm, ảnh sửa được cập nhật, ảnh trùng không bị thêm hai lần; tên, mô tả bạn đã sửa trong Dashboard **không bị ghi đè**. "
                   "Bật “Tự động” thì mỗi lần mở Dashboard hệ thống tự kiểm tra thư mục có gì mới.")
        st.caption("Cấu trúc nhận được: `Lyra_front.png`, `Lyra_back.png` (cùng tên = một mục), hoặc thư mục `Lyra/1.png…`, hoặc chia theo thư mục con "
                   "`Nhân vật`, `Vũ khí`, `Thú cưng`, `Bản đồ`, `Đạo cụ`. Chỉ nhận JPG/PNG/WebP ≤ 10 MB, tối đa 6 ảnh mỗi mục.")
        for src in assets.list_sources(p.conn, game):
            with st.container(border=True):
                st.markdown(f"**{escape(src['path'])}**")
                st.caption(f"Lần đồng bộ gần nhất: {src['last_sync'] or 'chưa'}" + (f" — {escape(src['last_summary'])}" if src["last_summary"] else ""))
                c1, c2, c3 = st.columns([2, 3, 1.4], vertical_alignment="bottom")
                k = c1.selectbox("Loại mặc định", list(assets.KINDS), index=list(assets.KINDS).index(src["kind"]) if src["kind"] in assets.KINDS else 0,
                                 format_func=lambda x: assets.KINDS[x], key=f"src_kind_{src['id']}")
                ig = c2.text_input("Bỏ qua file/thư mục có từ (cách nhau bằng dấu phẩy)", src["ignore"] or "", key=f"src_ign_{src['id']}")
                auto = c3.checkbox("Tự động", bool(src["auto"]), key=f"src_auto_{src['id']}")
                if (k, ig.strip(), bool(auto)) != (src["kind"], (src["ignore"] or "").strip(), bool(src["auto"])):
                    assets.set_source(p.conn, src["id"], k, ig, auto)
                b1, b2, b3 = st.columns([1.6, 1.6, 1.6])
                rm = b3.checkbox("Xóa ảnh không còn trong thư mục", key=f"src_rm_{src['id']}")
                if b1.button("🔄 Đồng bộ ngay", key=f"src_run_{src['id']}", type="primary"):
                    try:
                        st.session_state[f"src_rep_{src['id']}"] = assets.run_source(p.conn, src["id"], me().get("email"), rm)
                    except (assets.AssetError, OSError) as e:
                        st.error(str(e))
                    else:
                        st.rerun()
                if confirm_all(f"src_del_{src['id']}", [src["id"]], "🗑 Bỏ nguồn này", "Bỏ thư mục này khỏi danh sách (ảnh đã nhập vẫn giữ)?", b2, "Có, bỏ"):
                    assets.remove_source(p.conn, src["id"])
                    st.rerun()
                rep = st.session_state.get(f"src_rep_{src['id']}")
                if rep:
                    st.success(assets.summary(rep) or "Không có gì thay đổi")
                    for title, key in (("Mục mới", "created"), ("Không còn trong thư mục", "missing"), ("Lỗi / không nhận", "skipped")):
                        if rep[key]:
                            with st.expander(f"{title} ({len(rep[key])})"):
                                for item in rep[key][:80]:
                                    st.caption(f"• {item if isinstance(item, str) else item[0] + ' — ' + item[1]}")
        with st.container(border=True):
            st.markdown("**➕ Thêm thư mục nguồn**")
            path = st.text_input("Đường dẫn thư mục", key="lib_import_path",
                                 placeholder=r"G:\My Drive\Free Fire Save resources\ingame Free Fire\FF_Character_Reference")
            d1, d2 = st.columns([2, 3])
            default_kind = d1.selectbox("Loại mặc định (khi thư mục không nói rõ)", list(assets.KINDS), format_func=lambda k: assets.KINDS[k],
                                        key="lib_import_kind")
            ignore = d2.text_input("Bỏ qua file/thư mục có từ", assets.DEFAULT_IGNORE, key="lib_import_ignore")
            if st.button("Thêm và đồng bộ ngay", key="lib_import_go", disabled=not path.strip(), type="primary"):
                try:
                    sid = assets.add_source(p.conn, game, path, default_kind, ignore, True)
                    st.session_state[f"src_rep_{sid}"] = assets.run_source(p.conn, sid, me().get("email"))
                except (assets.AssetError, OSError) as e:
                    st.error(str(e))
                else:
                    st.rerun()
        st.caption("💡 Cách dễ nhất để luôn cập nhật: cài **Google Drive cho máy tính** (Drive for desktop), để thư mục tài nguyên ở chế độ "
                   "“Ngoại tuyến/Mirror”, rồi thêm chính thư mục đó làm nguồn với “Tự động” bật. Ai thêm ảnh lên Drive, lần mở Dashboard sau ảnh tự vào kho.")
    with st.expander("🌐 Cập nhật từ website Free Fire (ff.garena.com)"):
        st.caption("Đọc trang web chính thức: 6 bản đồ và mọi khu vực (tên, mô tả, ảnh), cùng 12 nhân vật / thú cưng / vũ khí mới nhất (tiểu sử, kỹ năng, chỉ số). "
                   "Mục đã có trong kho chỉ được **bổ sung** mô tả (đặt trong khối `[ff.garena.com]`, chạy lại thì thay khối đó) và ảnh chính thức, "
                   "không ghi đè phần bạn đã viết. Website không cho lấy toàn bộ danh sách nên đây chỉ là các mục mới nhất; phần còn lại vẫn lấy từ thư mục Drive. "
                   "Tự động chạy lại mỗi 30 ngày. Cần Node.js trên máy.")
        info = ff_site.status(p.conn)
        if info["last"] or info["text"]:
            st.caption(f"Lần gần nhất: {info['last'] or '—'} — {escape(info['text'])}")
        if st.button("🌐 Cập nhật ngay", key="ff_site_go", disabled=info["running"], type="primary"):
            if ff_site.start_background(DB, game, me().get("email")):
                st.toast("Đang đọc website ở nền, vài phút; bấm tải lại trang để xem kết quả")
            st.rerun()
    with st.expander("🤖 Đọc mô tả ngoại hình bằng Claude (nhân vật / thú cưng)"):
        st.caption("Ảnh đầu của mỗi nhân vật thường là một bảng thiết kế nhiều góc/tư thế (turn-around, bảng màu, phụ kiện) — rất nhiều chi tiết hữu ích, "
                   "nhưng gửi thẳng tấm đó cho AI vẽ ảnh lại làm nó chép lẫn lộn giữa các nhân vật trong cùng một cảnh, nên Bước 2 không dùng tấm này làm ảnh "
                   "tham chiếu (xem “🖼 Ảnh tham chiếu” ở Bước 1). Chữ thì không bị chép lẫn như vậy: nút này cho Claude **nhìn ảnh và viết lại** màu/kiểu tóc, "
                   "trang phục, phụ kiện thành một đoạn mô tả, lưu vào mô tả của mục (không đè phần bạn đã viết) — Director sẽ đọc được đoạn này khi phân tích kịch bản.")
        n_pending = asset_vision.pending(p.conn, game)
        st.caption(f"{n_pending} mục nhân vật/thú cưng chưa được đọc" if n_pending else "Mọi mục nhân vật/thú cưng đã được đọc.")
        prog = asset_vision.progress(game)
        if asset_vision.active(game) and prog["total"]:
            st.progress(prog["done"] / prog["total"], text=f"Đang đọc {prog['done']}/{prog['total']} mục…")
        problem = asset_vision.last_error(game)
        if problem:
            st.warning(f"⚠ Đã dừng: {problem}")
            if st.button("↻ Thử lại", key="asset_vision_retry"):
                asset_vision.clear_error(game)
                st.rerun()
        if st.button("🤖 Đọc mô tả ngoại hình", key="asset_vision_go", disabled=not n_pending or asset_vision.active(game), type="primary"):
            if asset_vision.start(DB, game):
                st.toast("Đang đọc ở nền; bấm tải lại trang để xem tiến độ")
            st.rerun()
    with st.expander("📹 Phân tích video kỹ năng bằng Claude (nhân vật quay trong gameplay)"):
        st.caption("Tải video gameplay quay skill của một nhân vật — Claude nhìn các khung hình lấy mẫu đều theo thời gian và viết lại "
                   "nhận dạng nhân vật + kỹ năng/VFX thành chữ, MỖI câu gắn nhãn [OBSERVED] (thấy trực tiếp) / [EXPLICIT] (chữ overlay nói rõ) / "
                   "[INFERRED] (suy luận có lý do) / [UNKNOWN] (không xác nhận được) — video là bằng chứng gốc, không tự bịa sát thương/thời gian hồi/"
                   "tầm bắn nếu video không xác nhận. Bạn xem, sửa và tự chọn ảnh muốn giữ trước khi lưu — không tự động ghi gì cả.")
        characters = [a for a in items if a["kind"] in ("character", "pet")]
        if not characters:
            st.caption("Kho chưa có nhân vật/thú cưng nào.")
        else:
            by_id = {a["id"]: a["name"] for a in characters}
            va_asset_id = st.selectbox("Nhân vật / thú cưng", list(by_id), format_func=lambda i: by_id[i], key="va_asset")
            va_video = st.file_uploader("Video gameplay (mp4/mov/webm/mkv, tối đa 200 MB)", type=["mp4", "mov", "webm", "mkv"], key="va_video")
            va_note = st.text_input("Ghi chú thêm cho Claude (tuỳ chọn)", key="va_note",
                                    placeholder="vd: chỉ nhìn skill chủ động, bỏ qua trang phục")
            va_count = st.slider("Số khung hình lấy mẫu", 4, video_analysis.MAX_FRAMES, 8, key="va_count")
            if st.button("🎬 Phân tích video", key="va_go", disabled=not va_video, type="primary"):
                client = llm_client()
                if client is not None:
                    try:
                        with st.spinner("Đang trích khung hình + hỏi Claude…"):
                            tmp_dir = tempfile.mkdtemp(prefix="va_")
                            video_path = os.path.join(tmp_dir, va_video.name)
                            with open(video_path, "wb") as f:
                                f.write(va_video.getvalue())
                            meta = video_analysis.probe(video_path)
                            frames = video_analysis.extract_frames(video_path, os.path.join(tmp_dir, "frames"), va_count)
                            text = video_analysis.analyze(client, by_id[va_asset_id], frames, meta, va_note)
                    except (video_analysis.VideoAnalysisError, llm_runner.LlmError) as e:
                        st.error(str(e))
                    else:
                        st.session_state[f"va_draft_{va_asset_id}"] = {"text": text, "frames": frames, "source": va_video.name}
                        st.rerun()
            draft = st.session_state.get(f"va_draft_{va_asset_id}")
            if draft:
                st.markdown(f"**Bản nháp phân tích — {by_id[va_asset_id]}** (từ `{draft['source']}`)")
                cols = st.columns(min(len(draft["frames"]), 5) or 1)
                keep = []
                for i, fp in enumerate(draft["frames"]):
                    with cols[i % len(cols)]:
                        st.image(fp, use_container_width=True)
                        if st.checkbox("Thêm làm ảnh tham chiếu", key=f"va_kf_{va_asset_id}_{i}"):
                            keep.append(fp)
                edited = st.text_area("Nội dung (sửa được trước khi lưu)", draft["text"], height=220, key=f"va_text_{va_asset_id}")
                b1, b2 = st.columns(2)
                if b1.button("💾 Lưu vào mô tả", key=f"va_save_{va_asset_id}", type="primary"):
                    asset = assets.get(p.conn, va_asset_id)
                    new_desc = video_analysis.with_block(asset["description"], edited, draft["source"])
                    assets.update(p.conn, va_asset_id, asset["name"], asset["aliases"], new_desc)
                    st.session_state.pop(f"va_draft_{va_asset_id}", None)
                    st.success("Đã lưu vào mô tả.")
                    st.rerun()
                if b2.button(f"🖼 Thêm {len(keep)} ảnh đã tick vào tài nguyên", key=f"va_addimg_{va_asset_id}", disabled=not keep):
                    added = 0
                    for fp in keep:
                        with open(fp, "rb") as f:
                            try:
                                assets.add_image(p.conn, va_asset_id, os.path.basename(fp), f.read())
                                added += 1
                            except assets.AssetError as e:
                                st.warning(str(e))
                    st.success(f"Đã thêm {added} ảnh.")
                    st.rerun()
    with st.expander("⬆ Tải nhiều ảnh cùng lúc (tên file = tên tài nguyên)"):
        st.caption("Chọn nhiều ảnh một lượt: `Lyra_front.png` + `Lyra_back.png` thành một mục Lyra; mục đã có thì được thêm ảnh; ảnh trùng bị bỏ qua.")
        bulk_kind = st.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key="lib_bulk_kind")
        bulk = st.file_uploader("Ảnh", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="lib_bulk_files")
        if st.button("Thêm vào kho", key="lib_bulk_go", disabled=not bulk):
            r = assets.add_files(p.conn, game, bulk_kind, [(f.name, f.getvalue()) for f in bulk], me().get("email"))
            st.success(f"Mục mới: {len(r['created'])}, ảnh thêm: {r['added']}, trùng bỏ qua: {r['unchanged']}" + (f", lỗi: {len(r['skipped'])}" if r["skipped"] else ""))
            for name, why in r["skipped"][:20]:
                st.caption(f"• {name} — {why}")
    with st.expander("🎼 Kho âm thanh (nhạc nền & hiệu ứng) — thư mục nguồn", expanded=not sound_lib.list_sources(p.conn)):
        st.caption("Thư mục chứa nhạc và hiệu ứng (mp3, wav, m4a, ogg, flac). Hệ thống chỉ liệt kê file (không mở từng file) nên thư mục vài GB vẫn xong ngay; "
                   "phân loại nhạc nền / hiệu ứng và tâm trạng (vui vẻ, sôi động, kịch tính, hài...) dựa theo tên thư mục. Ở Bước 5 mọi người tìm, nghe thử và dùng.")
        for src in sound_lib.list_sources(p.conn):
            with st.container(border=True):
                st.markdown(f"**{escape(src['path'])}** · {src['tracks']} bản")
                st.caption(f"Lần quét gần nhất: {src['last_sync'] or 'chưa'}" + (f" — {escape(src['last_summary'])}" if src["last_summary"] else ""))
                s1, s2, s3 = st.columns([3, 1.2, 1.4], vertical_alignment="bottom")
                ig = s1.text_input("Bỏ qua thư mục có từ", src["ignore"] or "", key=f"snd_ign_{src['id']}")
                auto = s2.checkbox("Tự động", bool(src["auto"]), key=f"snd_auto_{src['id']}")
                if (ig.strip(), bool(auto)) != ((src["ignore"] or "").strip(), bool(src["auto"])):
                    sound_lib.set_source(p.conn, src["id"], ig, auto)
                if s3.button("🔄 Quét ngay", key=f"snd_scan_{src['id']}", type="primary"):
                    try:
                        sound_lib.scan(p.conn, src["id"])
                    except (sound_lib.SoundError, OSError) as e:
                        st.error(str(e))
                    else:
                        st.rerun()
                if confirm_all(f"snd_del_{src['id']}", [src["id"]], "🗑 Bỏ nguồn này", "Bỏ thư mục khỏi kho âm thanh (file gốc không bị xóa)?", st, "Có, bỏ"):
                    sound_lib.remove_source(p.conn, src["id"])
                    st.rerun()
        a1, a2 = st.columns([4, 1.4], vertical_alignment="bottom")
        snd_path = a1.text_input("Thêm thư mục âm thanh", key="snd_new_path", placeholder=r"G:\My Drive\...\Free Fire Save resources\Sound Effect")
        if a2.button("Thêm và quét", key="snd_new_go", disabled=not snd_path.strip(), type="primary"):
            try:
                sid = sound_lib.add_source(p.conn, snd_path)
                sound_lib.scan(p.conn, sid)
            except (sound_lib.SoundError, OSError) as e:
                st.error(str(e))
            else:
                st.rerun()
    with st.expander("➕ Thêm một mục"):
        c1, c2 = st.columns([3, 2])
        name = c1.text_input("Tên", key="lib_new_name")
        kind = c2.selectbox("Loại", list(assets.KINDS), format_func=lambda k: assets.KINDS[k], key="lib_new_kind")
        aliases = st.text_input("Tên gọi khác trong kịch bản (cách nhau bằng dấu phẩy)", key="lib_new_aliases")
        desc = st.text_area("Mô tả (ngoại hình, đặc điểm để Director dùng)", key="lib_new_desc", height=70)
        files = st.file_uploader("Ảnh tham khảo", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="lib_new_files")
        if st.button("Thêm vào kho", key="lib_new_go", disabled=not name.strip()):
            try:
                aid = assets.create(p.conn, game, kind, name, desc, aliases, None, me().get("email"))
                for f in files[: assets.MAX_IMAGES_PER_ASSET]:
                    assets.add_image(p.conn, aid, f.name, f.getvalue())
            except assets.AssetError as e:
                st.error(str(e))
            else:
                st.rerun()
    kind_filter = st.radio("Xem", ["all"] + list(assets.KINDS), horizontal=True, key="lib_filter",
                           format_func=lambda k: "Tất cả" if k == "all" else assets.KINDS[k])
    query = st.text_input("Tìm theo tên", key="lib_query", placeholder="vd Lyra, Đền, Bermuda")
    shown = [a for a in items if (kind_filter == "all" or a["kind"] == kind_filter)
             and (not query.strip() or assets.fold(query) in assets.fold(a["name"] + " " + (a["aliases"] or "")))]
    per_page = 12                                     # every picture on the page is decoded on each rerun: never draw the whole library at once
    pages = max((len(shown) + per_page - 1) // per_page, 1)
    if pages > 1:
        page = int(st.number_input(f"Trang (có {len(shown)} mục, {pages} trang)", 1, pages, 1, key="lib_page"))
        shown = shown[(page - 1) * per_page: page * per_page]
    for a in shown:
        with st.expander(f"{a['kind_label']} · {a['name']} · {len(a['images'])} ảnh"):
            if a["images"]:
                cols = st.columns(min(len(a["images"]), 6))
                for col, img in zip(cols, a["images"]):
                    col.image(assets.thumbnail(img["path"]), width=110)
                    if col.button("Xóa ảnh", key=f"lib_img_rm_{img['id']}"):
                        assets.remove_image(p.conn, img["id"])
                        st.rerun()
            if a["description"]:
                st.caption(a["description"][:700])
            if st.checkbox("✏️ Sửa, gộp hoặc xóa mục này", key=f"lib_edit_{a['id']}"):     # the form only exists when asked for (keeps the page light)
                e_name = st.text_input("Tên", a["name"], key=f"lib_e_name_{a['id']}")
                e_alias = st.text_input("Tên gọi khác", a["aliases"], key=f"lib_e_alias_{a['id']}")
                e_desc = st.text_area("Mô tả", a["description"], key=f"lib_e_desc_{a['id']}", height=70)
                more = st.file_uploader("Thêm ảnh", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key=f"lib_e_up_{a['id']}")
                others = [x for x in items if x["id"] != a["id"]]
                if others:
                    g1, g2 = st.columns([3, 1.4], vertical_alignment="bottom")
                    names = {x["id"]: f"{x['kind_label']}: {x['name']}" for x in others}
                    target = g1.selectbox("Gộp mục này vào mục khác (ảnh chuyển sang, tên này thành tên gọi khác)", [None] + list(names),
                                          format_func=lambda i: "— không gộp —" if i is None else names[i], key=f"lib_merge_{a['id']}")
                    if target is not None and g2.button("Gộp", key=f"lib_merge_go_{a['id']}"):
                        try:
                            assets.merge(p.conn, a["id"], target)
                        except assets.AssetError as e:
                            st.error(str(e))
                        else:
                            st.rerun()
                b1, b2 = st.columns(2)
                if b1.button("💾 Lưu", key=f"lib_e_save_{a['id']}", type="primary"):
                    try:
                        assets.update(p.conn, a["id"], e_name, e_alias, e_desc)
                        for f in more:
                            assets.add_image(p.conn, a["id"], f.name, f.getvalue())
                    except assets.AssetError as e:
                        st.error(str(e))
                    else:
                        st.rerun()
                if confirm_all(f"lib_del_{a['id']}", [a["id"]], "🗑 Xóa mục này", f"Xóa “{a['name']}” khỏi kho (các dự án đang dùng cũng mất)?", b2, "Có, xóa"):
                    assets.delete(p.conn, a["id"])
                    st.rerun()


def script_html(text: str) -> str:
    """Whole script as a scrollable block; scene headings in bold so the scenes can be found at a glance."""
    lines = []
    for line in text.splitlines():
        safe = escape(line)
        lines.append(f"<b>{safe}</b>" if script_parser._HEADING.match(line) else safe)
    return '<div class="scriptfull">' + "\n".join(lines) + "</div>"


def step1(p: Pipeline, pid: int):
    proj = p.project(pid)
    scenes = p.conn.execute("SELECT idx, title, state, data FROM scenes WHERE project_id=? ORDER BY idx",
                            (pid,)).fetchall()
    chars = p.conn.execute("SELECT name, description, wardrobe, locked FROM characters WHERE project_id=?",
                           (pid,)).fetchall()
    warnings = preflight.check_characters(p.conn, pid, preflight.load_blocklist()) if chars else []
    risky = {w["character"] for w in warnings}
    char_names = [c["name"] for c in chars]

    with st.container(border=True):
        head, info = st.columns([3, 2], vertical_alignment="center")
        head.markdown(ui.card_title("① Kịch bản", "toàn văn (trái) · chia theo cảnh (phải)"), unsafe_allow_html=True)
        if scenes:
            info.caption(f"✓ {len(scenes)} cảnh · {len(chars)} nhân vật")
        if st.session_state.get("parse_warn") and scenes:
            st.warning(st.session_state["parse_warn"])
        t_file, t_text = st.tabs(["📎 Tải file", "✍ Gõ / dán văn bản"])
        with t_file:
            up = st.file_uploader("Kịch bản", type=list(script_reader.SUPPORTED), key=f"up_{pid}", label_visibility="collapsed",
                                  help="Word (.docx, kể cả kịch bản viết trong bảng), Excel (.xlsx), CSV/TSV, .txt, .md")
            st.caption("Đọc được: Word (.docx, cả bảng), Excel (.xlsx), CSV/TSV, .txt, .md. Kịch bản dạng bảng cần dòng tiêu đề cột như "
                       "Cảnh, Mô tả, Nhân vật, Lời thoại, Bối cảnh, Thời gian, Góc máy.")
        with t_text:
            pasted = st.text_area("Gõ hoặc dán kịch bản", key=f"paste_{pid}", height=170, label_visibility="collapsed",
                                  placeholder="CẢNH 1 - ĐÊM, RỪNG ELDER\nSương mù phủ kín khu rừng…\nLYRA: Có thứ gì đó đang theo chúng ta.\n\n"
                                              "Dán cả bảng copy từ Excel / Google Sheets cũng được.")
        u2, u3, u4 = st.columns([2.4, 1.2, 4], vertical_alignment="center")
        has_input = up is not None or bool(pasted.strip())
        if u2.button("▶ Phân tích (tách cảnh)", disabled=not has_input, type="primary", key=f"btn_analyse_{pid}"):
            def analyse():
                res = script_reader.read_script(up.name, up.getvalue()) if up is not None else script_reader.from_text(pasted)
                parsed = script_parser.split_scenes(res.paragraphs)
                script_parser.import_scenes(p, pid, parsed, full_text="\n\n".join(res.paragraphs))
                st.session_state["parse_info"] = res.info
                if len(parsed) == 1 and parsed[0].heading == "Mở đầu":
                    st.session_state["parse_warn"] = ("Không thấy tiêu đề cảnh (vd “Cảnh 1”, “Scene 2”, “INT./EXT.”): "
                                                      "cả kịch bản thành 1 cảnh. Hãy thêm/sửa cảnh thủ công.")
                st.toast(f"Đã tách {len(parsed)} cảnh")
            if act(analyse):
                st.rerun()
        u4.caption("Nếu có cả file lẫn văn bản, hệ thống dùng file." if has_input else "Chọn file hoặc dán văn bản, rồi bấm Phân tích.")
        if st.session_state.get("parse_info") and scenes:
            with st.expander("Hệ thống đã đọc kịch bản thế nào (kiểm tra lại)"):
                for line in st.session_state["parse_info"]:
                    st.caption("• " + line)
        if u3.button("↺ Reset", help="Xóa cảnh chưa có ảnh + nhân vật chưa khóa", key="btn_bad_reset"):
            p.conn.execute("DELETE FROM characters WHERE project_id=? AND locked=0", (pid,))
            p.conn.execute("DELETE FROM scenes WHERE project_id=? AND id NOT IN (SELECT scene_id FROM jobs)", (pid,))
            p.conn.commit()
            if not p.conn.execute("SELECT 1 FROM scenes WHERE project_id=?", (pid,)).fetchone():
                p.set_script_text(pid, None)
            st.session_state.pop("parse_info", None)
            st.rerun()
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Kịch bản đầy đủ**")
            full = proj["script_text"] or "\n\n".join(
                (json.loads(s["data"] or "{}").get("text") or s["title"] or "") for s in scenes)
            if full.strip():
                ui.html(script_html(full))
            else:
                st.caption("Chưa có kịch bản: tải file hoặc gõ/dán văn bản rồi bấm Phân tích.")
        with right:
            st.markdown(f"**Chia theo cảnh** · bấm vào từng cảnh để xem và sửa")
            for s in scenes:
                d = json.loads(s["data"] or "{}")
                bits = [f"S{s['idx']:02d}", " · ".join(filter(None, [d.get("time"), d.get("location")])),
                        ", ".join(d.get("characters") or []), " · ".join(filter(None, [d.get("shot"), d.get("mood")]))]
                with st.expander("   |   ".join(x for x in bits if x) + f"   [{s['state']}]"):
                    scene_editor(p, pid, s, char_names)
            if st.button("➕ Thêm cảnh", key=f"scene_add_{pid}", help="Cho kịch bản mà công cụ không tự tách được"):
                act(lambda: p.add_scene_next(pid))
                st.rerun()

    if scenes:
        assets_panel(p, pid)
        ui.html(ui.card_title("④ Chọn cách chạy", "sau khi đã tách cảnh ở trên"))
        auto_col, manual_col = st.columns(2, gap="large")
        with auto_col:
            autopilot_panel(p, pid)
        with manual_col, st.container(border=True):
            ui.html(ui.card_title("🧭 Chạy lần lượt từng bước", "bạn kiểm soát và duyệt ở mỗi bước"))
            st.caption("Tự xem và duyệt từng khâu: chạy Director và khóa Character Bible ở bên dưới → Bước 2 gen ảnh + QC (bạn duyệt ảnh) "
                       "→ Bước 3 duyệt motion prompt → Bước 4 gen video → Bước 5 nhạc và ghép. Hợp với dự án dài hoặc cần chỉnh kỹ.")
            st.button("⏭ Sang Bước 2 (gen ảnh + QC)", key=f"go_step2_{pid}", disabled=not any(c["locked"] for c in chars),
                      help="Bật sau khi Character Bible đã khóa",
                      on_click=lambda: st.session_state.__setitem__("step", STEPS[1]))
            if not any(c["locked"] for c in chars):
                st.caption("Chạy Director và khóa Character Bible ở phần bên dưới trước.")
        st.markdown("##### Chạy lần lượt: ② Director và ③ Character Bible")

    dl, dr = st.columns([1, 1.7], gap="large")
    with dl:
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
    with dr:
        if chars:
            with st.container(border=True):
                head, status = st.columns([3, 2], vertical_alignment="center")
                head.markdown(ui.card_title("③ Character Bible", f"{len(chars)} mục"), unsafe_allow_html=True)
                if risky:
                    status.caption(f"⚠ {len(risky)} mục có thể vướng IP (xem “⚠ Rủi ro” ở góc trên)")
                linked = assets.link_characters(p.conn, pid, char_names)
                st.dataframe([{"Nhân vật / đối tượng": c["name"],
                               "Mô tả": c["description"] + (f" · {c['wardrobe']}" if c["wardrobe"] else ""),
                               "Ảnh tham chiếu": (f"✔ {linked[c['name']]['name']} · {len(linked[c['name']]['images'])} ảnh" if linked.get(c["name"])
                                                  else "— vẽ theo mô tả"),
                               "IP": "⚠ rủi ro" if c["name"] in risky else "an toàn",
                               "Khóa": "🔒" if c["locked"] else ""} for c in chars],
                             width="stretch", hide_index=True, height=min(38 * (len(chars) + 1) + 3, 220))
                character_reference_panel(p, pid, chars)
                subject_panel(p, pid, chars)
                with st.expander("✏ Sửa / thêm nhân vật, đối tượng · khóa"):
                    if any(c["locked"] for c in chars):
                        st.caption("Character Bible đang khóa. Muốn sửa phải mở khóa (ảnh đã gen vẫn theo mô tả cũ).")
                        if st.button("🔓 Mở khóa để sửa", key="btn_bad_unlock"):
                            act(lambda: llm_io.unlock_character_bible(p, pid), "Đã mở khóa Character Bible")
                            st.rerun()
                    else:
                        who = st.selectbox("Chọn mục cần sửa", char_names, key=f"csel_{pid}")
                        c = next(c for c in chars if c["name"] == who)
                        n_name = st.text_input("Tên", c["name"], key=f"cn_{pid}_{c['name']}")
                        n_desc = st.text_area("Mô tả", c["description"], key=f"cd_{pid}_{c['name']}", height=80)
                        n_ward = st.text_input("Trang phục / dấu hiệu", c["wardrobe"] or "", key=f"cw_{pid}_{c['name']}")
                        if st.button("Lưu", key=f"cs_{pid}_{c['name']}"):
                            if act(lambda: llm_io.update_character(p, pid, c["name"], n_desc, n_ward, n_name),
                                   f"Đã lưu {n_name}"):
                                st.rerun()
                    st.markdown("**➕ Thêm nhân vật / đối tượng**")
                    st.caption("Không chỉ người: cũng có thể là sinh vật, linh vật, đạo cụ… bất cứ thứ gì cần giống nhau ở mọi cảnh.")
                    a_name = st.text_input("Tên", key=f"cadd_name_{pid}")
                    a_desc = st.text_area("Mô tả ngoại hình", key=f"cadd_desc_{pid}", height=70)
                    a_ward = st.text_input("Trang phục / dấu hiệu (tùy chọn)", key=f"cadd_ward_{pid}")
                    if st.button("Thêm vào Character Bible", key=f"cadd_{pid}", disabled=not (a_name.strip() and a_desc.strip())):
                        if act(lambda: llm_io.add_character(p, pid, a_name, a_desc, a_ward), f"Đã thêm {a_name}"):
                            st.rerun()
            with st.container(border=True):
                a, b = st.columns([2, 1], vertical_alignment="center")
                a.caption("Cần Approve & Lock để mở Bước 2")
                if b.button("✔ Duyệt & khóa → Bước 2", type="primary"):
                    act(lambda: llm_io.lock_character_bible(p, pid), "Đã khóa Character Bible")
                    st.rerun()
    world_bible_panel(p, pid)


def character_reference_panel(p: Pipeline, pid: int, chars) -> None:
    """Character Bible: the reference picture(s) of each character, visible here and changeable (this is what image generation copies)."""
    linked = assets.link_characters(p.conn, pid, [c["name"] for c in chars])
    pool = [a for a in assets.project_assets(p.conn, pid) if a["kind"] in ("character", "pet") and a["images"]]
    saved = {r["name"]: r for r in p.conn.execute("SELECT name, ref_asset_id, ref_image_id, ref_image_ids FROM characters WHERE project_id=?", (pid,))}
    have = sum(1 for a in linked.values() if a)
    with st.expander(f"🖼 Ảnh tham chiếu của từng nhân vật — {have}/{len(chars)} đã có", expanded=have < len(chars) or not pool):
        st.caption("Đây là (những) ảnh mà bước gen ảnh sẽ **bám theo** (gương mặt, tóc, trang phục). Mặc định tự chọn theo tên, ưu tiên ảnh MỘT người rõ mặt "
                   "(không phải cả tấm bảng nhiều tư thế) và lấy thêm góc/chi tiết thứ hai nếu có, để nhân vật không bị lẫn với người khác trong cảnh. "
                   "Bạn đổi được sang tài nguyên khác, hoặc tự chọn 1-2 ảnh cụ thể. Muốn thêm tài nguyên, chọn ở mục “🧰 Tài nguyên đi kèm kịch bản” phía trên.")
        if not pool:
            st.warning("Dự án chưa chọn tài nguyên nhân vật nào, nên ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế). Chọn ở “🧰 Tài nguyên đi kèm kịch bản”.")
        options = ["auto", "none"] + [a["id"] for a in pool]
        labels = {"auto": "Tự động (theo tên)", "none": "Không dùng ảnh (vẽ theo mô tả)", **{a["id"]: f"{a['name']} ({len(a['images'])} ảnh)" for a in pool}}
        for c in chars:
            row = saved.get(c["name"])
            a = linked[c["name"]]
            with st.container(border=True):
                left, right = st.columns([1.1, 3], vertical_alignment="top")
                if a:
                    left.image([assets.thumbnail(img["path"], 220) for img in a["refs"]], width=105)
                else:
                    left.caption("— chưa có ảnh")
                right.markdown(f"**{escape(c['name'])}** — " + (f"dùng {len(a['refs'])} ảnh của **{escape(a['name'])}**" if a else "vẽ theo mô tả chữ"))
                mode = "auto" if row["ref_asset_id"] is None else ("none" if row["ref_asset_id"] == 0 else row["ref_asset_id"])
                if mode not in options:
                    mode = "auto"
                pick = right.selectbox("Ảnh tham chiếu lấy từ", options, options.index(mode), format_func=lambda o: labels[o], key=f"cref_{pid}_{c['name']}")
                new_asset = None if pick == "auto" else (0 if pick == "none" else pick)
                if pick != mode:                                     # another source picked: save it (automatic picture choice until chosen otherwise)
                    assets.set_character_link(p.conn, pid, c["name"], new_asset, None, None)
                    st.rerun()
                shown = a if pick == "auto" else next((x for x in pool if x["id"] == pick), None)
                if shown and len(shown["images"]) > 1:
                    numbers = list(range(1, len(shown["images"]) + 1))
                    current_ids = {img["id"] for img in a["refs"]} if a and a["id"] == shown["id"] else set()
                    default = [i for i, img in enumerate(shown["images"], 1) if img["id"] in current_ids] or [1]
                    chosen_nums = right.multiselect("Dùng ảnh số (chọn 1-2 ảnh rõ mặt, nhiều góc/chi tiết thì càng chuẩn)", numbers, default,
                                                    key=f"cimg_{pid}_{c['name']}")
                    right.image([assets.thumbnail(img["path"], 160) for img in shown["images"]], width=70, caption=[str(i) for i in numbers])
                    if chosen_nums and set(chosen_nums) != set(default):
                        ids = [shown["images"][i - 1]["id"] for i in sorted(chosen_nums)]
                        assets.set_character_link(p.conn, pid, c["name"], shown["id"], ids[0], ids)
                        st.rerun()


def subject_panel(p: Pipeline, pid: int, chars) -> None:
    """Seedance Subject Library: upload each character once, then attach it to Seedance videos."""
    proj = p.project(pid)
    rows = p.conn.execute("SELECT name, subject_asset_id, subject_status, subject_name FROM characters"
                          " WHERE project_id=?", (pid,)).fetchall()
    active = sum(1 for r in rows if r["subject_status"] == "active")
    with st.expander(f"🧩 Kho chủ thể Seedance — {active}/{len(rows)} nhân vật đã có"):
        catalog = subjects.games()
        keys = list(catalog)
        game = st.selectbox("Game / loại nội dung của dự án", keys,
                            index=keys.index(proj["game"]) if proj["game"] in keys else 0,
                            format_func=lambda k: catalog[k][0], key=f"game_{pid}")
        if game != proj["game"]:
            p.set_game(pid, game)
        if subjects.is_covered(game):
            st.success("Free Fire đã ký thỏa thuận bản quyền với Clip AI: chủ thể ở trạng thái active đã qua duyệt "
                       "người thật + bản quyền, dùng được trong Seedance.")
        else:
            st.warning("Game / nội dung này chưa có thỏa thuận bản quyền: chủ thể active chỉ qua duyệt người thật; "
                       "khi gen vẫn có thể bị chặn bản quyền.")
        with st.expander("➕ Thêm game / loại nội dung khác"):
            g_key = st.text_input("Mã ngắn (vd AOV, MV_CA_SI)", key=f"gnew_key_{pid}")
            g_label = st.text_input("Tên hiển thị", key=f"gnew_label_{pid}")
            g_cov = st.checkbox("Đã ký thỏa thuận bản quyền với Clip AI", False, key=f"gnew_cov_{pid}",
                                help="Chỉ tick khi thật sự có thỏa thuận; ảnh hưởng thông báo hiển thị.")
            if st.button("Thêm", key=f"gnew_{pid}", disabled=not (g_key.strip() and g_label.strip())):
                if act(lambda: subjects.add_game(g_key, g_label, g_cov), "Đã thêm"):
                    st.rerun()
        st.dataframe([{"Nhân vật": r["name"], "Trạng thái": subjects.STATUS_LABEL.get(r["subject_status"], r["subject_status"]),
                       "Tên trên kho": r["subject_name"] or ""} for r in rows], width="stretch", hide_index=True,
                     height=min(38 * (len(rows) + 1) + 3, 200))
        try:
            library = factory.subject_library()
        except ProviderError as e:
            st.error(f"Clip AI: {e}")
            return
        if library is None:
            st.caption("Cần CLIPAI_TOKEN và VIDEO_PROVIDER=clipai (hoặc SUBJECT_PROVIDER=mock để thử) để tải lên kho.")
            return
        who = st.selectbox("Nhân vật", [r["name"] for r in rows], key=f"subj_who_{pid}")
        up = st.file_uploader("Ảnh nhân vật (JPG / PNG / WebP)", type=["jpg", "jpeg", "png", "webp"],
                              key=f"subj_up_{pid}_{who}")
        default_name = f"{game}_{who}".replace(" ", "_")  # any name is fine; the prefix just keeps the library tidy
        name = st.text_input("Tên trên kho", default_name, key=f"subj_name_{pid}_{who}")
        b1, b2, b3 = st.columns(3)
        if b1.button("⬆ Tải lên kho chủ thể", disabled=up is None, key=f"subj_go_{pid}", type="primary"):
            suffix = os.path.splitext(up.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(up.getvalue())
            try:
                with st.spinner("Đang tải lên và chờ kho duyệt (có thể mất 1–3 phút)…"):
                    ok = act(lambda: subjects.link(p, pid, who, library.upload(f.name, name)), f"Đã có chủ thể cho {who}")
            finally:
                os.remove(f.name)
            if ok:
                st.rerun()
        if b2.button("⟳ Cập nhật trạng thái", key=f"subj_refresh_{pid}"):
            act(lambda: st.toast(f"{subjects.refresh(p, pid, library)} chủ thể vừa active"))
            st.rerun()
        if b3.button("Gỡ liên kết", key=f"subj_unlink_{pid}", help="Chỉ bỏ liên kết trong dự án; ảnh vẫn ở kho Clip AI"):
            subjects.unlink(p, pid, who)
            st.rerun()
        with st.expander("📥 Nhập chủ thể đã có trên kho"):
            try:
                assets = [a for a in library.list_assets("image") if a.get("asset_id")]
            except ProviderError as e:
                st.error(str(e))
                assets = []
            if not assets:
                st.caption("Kho chưa có ảnh nào (hoặc không đọc được).")
            else:
                pick = st.selectbox("Chủ thể trên kho", assets, key=f"subj_pick_{pid}",
                                    format_func=lambda a: f"{a.get('name')} · {a.get('provider_status')}")
                if st.button(f"Gắn cho {who}", key=f"subj_link_{pid}"):
                    act(lambda: subjects.link(p, pid, who, pick), f"Đã gắn cho {who}")
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
    if confirm_all(f"scene_del_{pid}_{idx}", [idx], "🗑 Xóa cảnh này", f"Xóa cảnh {idx}?", st, "Có, xóa cảnh"):
        if act(lambda: p.delete_scene(pid, idx), f"Đã xóa cảnh {idx}"):
            st.rerun()
    if st.button("💾 Lưu cảnh", key=f"sds_{pid}_{idx}"):
        fields = {"location": location, "time": time_, "shot": shot, "mood": mood, "lighting": lighting,
                  "image_prompt": image_prompt}
        if char_names:
            fields["characters"] = cast
        if act(lambda: llm_io.update_scene(p, pid, idx, fields, text=text), f"Đã lưu cảnh {idx}"):
            st.rerun()


# ---- step 2 --------------------------------------------------------------------------
POLL_SECONDS = {"image": 6, "video": 15}


def image_busy(conn, pid: int) -> bool:
    """Something the page should keep watching: a job at the provider, pictures being / waiting to be checked automatically, or an
    automatic fix (retry) that is queued."""
    one = lambda sql: conn.execute(sql, (pid,)).fetchone()[0]                     # noqa: E731
    if one("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='running'"):
        return True
    if autoqc.active(pid) or autoqc.can_run(conn, pid):
        return True
    return bool(conn.execute("SELECT qc_autofix FROM projects WHERE id=?", (pid,)).fetchone()[0]
                and one("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued' AND retry_count>0"))


def _poll_running(pid: int, kind: str) -> None:
    """Ask the provider about this project's submitted jobs (read-only, no credit), start the automatic picture check, send queued automatic
    fixes, and redraw the page when anything changed."""
    conn = connect(DB)
    job_type = "image_gen" if kind == "image" else "video_gen"
    busy = image_busy(conn, pid) if kind == "image" else bool(
        conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type=? AND state='running' LIMIT 1", (pid, job_type)).fetchone())
    if not busy:
        st.rerun()                                     # nothing left to watch (finished elsewhere): show the final state
    try:
        provider = factory.image_provider() if kind == "image" else factory.video_provider()
    except ProviderError:
        provider = None
    p = Pipeline(conn)
    counts = {"succeeded": 0, "failed": 0, "retried": 0, "running": 0}
    if provider is not None:
        runner = ImageRunner(p, provider, DATA) if kind == "image" else VideoRunner(p, provider, DATA)
        try:
            counts = runner.poll_once(pid)
            queued_fix = kind == "image" and p.project(pid)["qc_autofix"] and conn.execute(
                "SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen' AND state='queued' AND retry_count>0 LIMIT 1", (pid,)).fetchone()
            if counts["succeeded"] or counts["failed"] or counts["retried"] or queued_fix:
                runner.submit_pending(pid)             # a slot is free: send the next queued job (the person's, or an automatic fix)
        except InvalidTransition:
            st.rerun()                                 # another tab finished the same job first
        except ProviderError as e:
            st.caption(f"⚠ Chưa hỏi được trạng thái ({e}); sẽ thử lại.")
    if kind == "image" and p.project(pid)["operating_mode"] != "auto":  # "auto" mode already runs its own QC via autopilot; avoid doing it twice
        autoqc.start(DB, DATA, pid)                    # freshly generated pictures are checked by Claude in the background
        rows = conn.execute("SELECT id, state FROM jobs WHERE project_id=? AND type='image_gen' ORDER BY id", (pid,)).fetchall()
        signature = tuple((r["id"], r["state"]) for r in rows)
        key = f"imgsig_{pid}"
        previous = st.session_state.get(key)
        st.session_state[key] = signature
        if previous is not None and previous != signature:
            st.rerun()                                 # a job changed state (finished, checked, sent again): redraw with it
    if counts["succeeded"] or counts["failed"] or counts["retried"]:
        st.rerun()                                     # a result arrived: redraw the whole page with it
    checking = " · 🔍 đang tự kiểm tra ảnh" if kind == "image" and autoqc.active(pid) else ""
    st.caption(f"🔄 Tự cập nhật mỗi {POLL_SECONDS[kind]} giây · {counts['running']} còn đang chạy{checking} · kiểm tra lúc {time.strftime('%H:%M:%S')}")


@st.fragment(run_every=POLL_SECONDS["image"])
def auto_poll_images(pid: int) -> None:
    _poll_running(pid, "image")


@st.fragment(run_every=POLL_SECONDS["video"])
def auto_poll_videos(pid: int) -> None:
    _poll_running(pid, "video")


def image_progress(p: Pipeline, pid: int, runner) -> None:
    """One plain answer to "is it generating?": the progress, and when nothing moves, the reason and what to press."""
    proj = p.project(pid)
    counts = {r["state"]: r["n"] for r in p.conn.execute(
        "SELECT state, COUNT(*) n FROM jobs WHERE project_id=? AND type='image_gen' AND state NOT IN ('rejected','cancelled') GROUP BY state", (pid,))}
    total = sum(counts.values())
    if not total:
        return
    queued, running, failed = counts.get("queued", 0) + counts.get("retryable", 0), counts.get("running", 0), counts.get("failed", 0)
    done = counts.get("succeeded", 0) + counts.get("pending_review", 0) + counts.get("approved", 0)
    ap_running = autopilot.status(p, pid)["state"] in ("running", "queued")
    names = [r["name"] for r in p.conn.execute("SELECT name FROM characters WHERE project_id=?", (pid,))]
    linked = assets.link_characters(p.conn, pid, names) if names else {}
    with st.container(border=True):
        if linked:
            have = [n for n, a in linked.items() if a]
            lack = [n for n, a in linked.items() if not a]
            st.caption(("🖼 Ảnh tham chiếu gửi kèm mỗi cảnh (theo nhân vật trong cảnh): " + ", ".join(have) + "." if have else
                        "🖼 Chưa có nhân vật nào gắn tài nguyên: ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế).")
                       + (f" Chưa có ảnh tham chiếu cho: {', '.join(lack)} (vẽ theo mô tả)." if have and lack else ""))
        st.progress(done / total, text=f"{done}/{total} ảnh đã có · {queued} đang chờ · {running} đang gen · {failed} lỗi")
        rows = p.conn.execute(
            "SELECT j.state, j.retry_count, j.escalated, s.idx, (SELECT AVG(score) FROM qc_results WHERE job_id=j.id) AS qc "
            "FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND j.type='image_gen' AND j.state NOT IN ('rejected','cancelled') "
            "ORDER BY s.idx", (pid,)).fetchall()
        if rows:
            client_ready = llm_client() is not None
            wait_label = "Chờ Claude kiểm tra" if client_ready else "Chờ bạn duyệt (chưa có Claude)"
            state_label = {"queued": "Chờ gen", "retryable": "Chờ gửi lại", "running": "Đang gen", "succeeded": wait_label,
                          "pending_review": "Chờ bạn duyệt", "approved": "Đã duyệt", "failed": "Lỗi"}
            st.dataframe([{"Cảnh": r["idx"], "Trạng thái": state_label.get(r["state"], r["state"]) + (" ⚠ cần xem" if r["escalated"] else ""),
                          "Điểm QC": f"{r['qc']:.2f}" if r["qc"] is not None else "—", "Đã tự sửa": r["retry_count"]} for r in rows],
                         hide_index=True, width="stretch", height=min(38 * (len(rows) + 1) + 3, 230))
        fixed = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND retry_count>0 AND state NOT IN ('cancelled')", (pid,)).fetchone()[0]
        flagged = p.conn.execute("SELECT COUNT(*) FROM jobs WHERE project_id=? AND type='image_gen' AND escalated=1 AND state='pending_review'", (pid,)).fetchone()[0]
        if autoqc.active(pid):
            st.info("🔍 **Đang tự kiểm tra ảnh** bằng Claude (so từng người với ảnh tham chiếu). Ảnh lỗi sẽ được gen lại tự động; ảnh đạt mới đến chỗ bạn duyệt.")
        if fixed:
            st.caption(f"🛠 Đã tự gen lại {fixed} lần vì QC thấy lỗi" + (f" · {flagged} ảnh vẫn còn lỗi sau các lần sửa, đã đánh dấu để bạn xem." if flagged else "."))
        problem = autoqc.last_error(pid)
        if problem:
            st.warning(f"⚠ **Tự kiểm tra ảnh đã dừng**: {problem}")
            if st.button("↻ Thử kiểm tra lại", key=f"autoqc_retry_{pid}"):
                autoqc.clear_error(pid)
                st.rerun()
        if queued + running == 0:
            st.success("Không còn job nào chờ: " + (f"{counts.get('pending_review', 0)} ảnh đang chờ bạn duyệt." if counts.get("pending_review") else "xong."))
        elif proj["paused"]:
            st.warning(f"⏸ **Chưa tạo ảnh nào**: dự án đang **PAUSE** nên {queued + running} job xếp hàng nhưng không job nào được bắt đầu. Bấm **▶ Resume** ở thanh trên cùng.")
        elif running:
            st.info(f"🔄 **Đang tạo ảnh**: {running} ảnh đang được xử lý, {queued} đang chờ. Trang tự cập nhật, ảnh xong sẽ tự hiện; bạn không cần bấm gì.")
        elif ap_running:
            st.info("🚀 Chế độ tự động đang xử lý các ảnh này (xem tiến độ chi tiết ở Bước 1).")
        elif runner is None:
            st.warning(f"⚠ **Chưa tạo ảnh nào**: Deepix chưa được cấu hình (thiếu `DEEPIX_TOKEN`) nên hệ thống không tự gen. {queued} job đang chờ bạn "
                       "nhập ảnh thủ công ở từng cảnh, hoặc nhờ quản trị cấu hình Deepix.")
        else:
            st.warning(f"⚠ **Chưa tạo ảnh nào**: {queued} job đã xếp hàng nhưng chưa được gửi đi. Ở chế độ từng bước hãy bấm **⟳ Submit + Poll 1 lần** "
                       "hoặc **▶ Chạy heartbeat tới khi xong** bên dưới (hoặc dùng chế độ tự động).")


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
    image_progress(p, pid, runner)
    if image_busy(p.conn, pid):
        auto_poll_images(pid)                           # results, the automatic check and automatic fixes all show up by themselves
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
        autofix = st.checkbox(f"Tự kiểm tra bằng Claude và tự gen lại ảnh lỗi trước khi đến bạn duyệt (tối đa {proj['max_retry_count']} lần mỗi ảnh; mỗi lần gen tốn credit)",
                              bool(proj["qc_autofix"]), key=f"autofix_{pid}",
                              help="Ảnh vừa gen được so với ảnh tham chiếu của từng nhân vật. Ảnh đạt threshold mới đến bạn duyệt; ảnh lỗi được gen lại với lỗi ghi vào prompt. "
                                   "Tắt thì QC chỉ cho điểm gợi ý và mọi ảnh đều chờ bạn.")
        if autofix != bool(proj["qc_autofix"]):
            p.set_qc_autofix(pid, autofix)
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
    if client is None and to_check:
        st.warning(f"⚠ **Chưa có điểm QC**: {to_check} ảnh vừa gen chưa được chấm vì chưa có Claude (cần `ANTHROPIC_API_KEY`, hoặc `LLM_PROVIDER=claude_cli` "
                   "để dùng Claude Code trên máy). Trong lúc đó hãy tự xem từng ảnh (đúng nhân vật? đúng bối cảnh? lỗi tay/mặt?) rồi ✓ duyệt hoặc ✕ loại.")
    jobs = p.conn.execute(
        "SELECT j.*, s.idx, s.title FROM jobs j JOIN scenes s ON s.id=j.scene_id"
        " WHERE j.project_id=? AND j.type='image_gen' ORDER BY s.idx, j.id", (pid,)).fetchall()
    if not jobs:
        st.caption("Chưa có job gen ảnh. Duyệt Character Bible ở Bước 1 rồi bấm ‘Tạo job gen ảnh’.")
        return
    history = {}                                          # scene_id -> its jobs, oldest first (every retry / "gen lại" kept, not just the newest)
    for j in jobs:
        history.setdefault(j["scene_id"], []).append(j)
    latest = {sid: hist[-1] for sid, hist in history.items()}
    counts = {k: sum(1 for j in latest.values() if j["state"] in v) for k, v in FILTER_STATES.items()}
    counts["all"] = len(latest)
    flt = st.radio("Lọc", list(FILTERS), horizontal=True, key=f"filter_{pid}", label_visibility="collapsed",
                   format_func=lambda k: f"{FILTERS[k]} {counts[k]}")
    shown_sids = [sid for sid, j in latest.items() if flt == "all" or j["state"] in FILTER_STATES[flt]]
    sel_key = f"sel_{pid}"
    if st.session_state.get(sel_key) not in {j["id"] for j in jobs}:
        st.session_state[sel_key] = latest[shown_sids[0]]["id"] if shown_sids else jobs[0]["id"]
    grid, detail = st.columns([3, 1.15], gap="large")
    with grid:
        per_row = 3
        for start in range(0, len(shown_sids), per_row):
            cols = st.columns(per_row)
            for col, sid in zip(cols, shown_sids[start:start + per_row]):
                with col:
                    image_card_group(p, pid, history[sid], proj)
        if not shown_sids:
            st.caption("Không có ảnh nào trong bộ lọc này.")
    with detail:
        job = next(j for j in jobs if j["id"] == st.session_state[sel_key])
        image_detail(p, pid, job, proj)


def image_card_group(p: Pipeline, pid: int, history: list, proj) -> None:
    """One card per SCENE (not per job): every "gen lại" adds an attempt to this scene's history instead of a new card in the
    grid, which would make a scene with several retries hard to tell apart from others once there are many scenes. ‹ › pages
    through the attempts; only the newest attempt is live (can be approved/rejected/retried), older ones are for comparison."""
    sid = history[0]["scene_id"]
    n = len(history)
    key = f"hist_{pid}_{sid}"
    pointer = min(st.session_state.get(key, n - 1), n - 1)
    j = history[pointer]
    is_latest = pointer == n - 1
    with st.container(border=True):
        if n > 1:
            nav = st.columns([1, 3, 1], vertical_alignment="center")
            if nav[0].button("‹", key=f"{key}_prev", disabled=pointer == 0, help="Bản trước"):
                st.session_state[key] = pointer - 1
                st.rerun()
            nav[1].markdown(f"<div style='text-align:center' class='muted'>Bản {pointer + 1}/{n}"
                            + ("" if is_latest else " · bản cũ") + "</div>", unsafe_allow_html=True)
            if nav[2].button("›", key=f"{key}_next", disabled=is_latest, help="Bản sau (mới hơn)"):
                st.session_state[key] = pointer + 1
                st.rerun()
        image_card(p, pid, j, proj, read_only=not is_latest)


def image_card(p: Pipeline, pid: int, j, proj, read_only: bool = False):
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
        if read_only:                                     # an older attempt: for comparison only, no approve/reject/retry here
            if j["retry_reason"]:
                st.caption(f"Lý do gen lại lúc đó: {j['retry_reason'][:160]}")
            if st.button("🔍 Chi tiết", key=f"sel_btn_{jid}", width="stretch"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        elif state in ("succeeded", "pending_review"):
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
        elif state == "failed" and not j["escalated"]:
            a, b = st.columns(2)
            if a.button("↻", key=f"retry_{jid}", help="Retry"):
                act(lambda: p.retry(jid, "retry"))
                st.rerun()
            if b.button("🔍", key=f"sel_btn_{jid}", help="Chi tiết"):
                st.session_state[f"sel_{pid}"] = jid
                st.rerun()
        else:
            if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"rs_{jid}",
                                            help="Đã hết số lần thử: bắt đầu lại cảnh này với một job mới"):
                if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                    st.rerun()
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
            if client is not None:
                st.caption("🔍 Claude tự kiểm tra ảnh này ở nền (không cần bấm); xem tiến độ ở đầu Bước 2.")
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
        if state == "failed" and not j["escalated"] and st.button("↻ Retry", key=f"dretry_{jid}"):
            act(lambda: p.retry(jid, "retry"))
            st.rerun()
        if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"drs_{jid}", type="primary"):
            if act(lambda: p.restart_job(jid), "Đã xếp hàng job mới cho cảnh"):
                st.rerun()
        if state == "approved":
            r_note = st.text_input("Lý do bỏ duyệt (đưa vào prompt gen lại)", key=f"rn_{jid}")
            st.caption("Video đã làm từ ảnh này không tự đổi; gen lại video ở Bước 4 nếu cần.")
            if st.button("↩ Bỏ duyệt & gen lại ảnh", key=f"reopen_{jid}"):
                if act(lambda: p.reopen_approved(jid, r_note or None), "Đã bỏ duyệt, xếp hàng gen lại"):
                    st.rerun()


# ---- step 3 --------------------------------------------------------------------------
def dialogue_panel(p: Pipeline, pid: int, key: str) -> None:
    """Warn when a scene's dialogue is longer than its clip (cut-off / rushed lines, wasted credit)."""
    entries = dialogue.check(p, pid)
    if not entries:
        return
    bad = dialogue.problems(entries)
    proj = p.project(pid)
    label = f"🗣 Thoại so với độ dài clip — {len(bad)} cảnh cần chú ý" if bad else f"🗣 Thoại so với độ dài clip — {len(entries)} cảnh có thoại, đều vừa"
    with st.expander(label, expanded=bool(bad)):
        if not proj["video_audio"]:
            st.caption("Đang tắt “Model tự tạo âm thanh/lời thoại”: thoại sẽ được lồng tiếng riêng (Bước 5a), độ dài clip chỉ cần đủ cho hình.")
        for e in entries:
            icon = {"ok": "✔", "tight": "◐", "extend": "⚠", "split": "✖"}[e["status"]]
            color = {"ok": "green", "tight": "orange", "extend": "orange", "split": "red"}[e["status"]]
            st.markdown(f":{color}[{icon} S{e['idx']:02d}] {escape(', '.join(e['speakers']))} · {e['syllables']} âm tiết ≈ {e['needed']:g}s "
                        f"/ clip {e['planned']:g}s" + (f" — {escape(e['advice'])}" if e["advice"] else ""))
        fixable = [e for e in bad if e["status"] == "extend"]
        if fixable and st.button(f"⏱ Tự tăng thời lượng {len(fixable)} clip cho vừa thoại", key=f"dlg_fix_{key}_{pid}"):
            dialogue.extend(p, entries)
            st.rerun()
        st.caption("Ước lượng theo tốc độ nói ~3,5 âm tiết/giây (DIALOGUE_SYLLABLES_PER_SEC) cộng 0,5s chừa hơi; chỉ là ước lượng.")


def step3(p: Pipeline, pid: int):
    approved = p.conn.execute(
        "SELECT s.idx FROM scenes s WHERE s.project_id=? AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id"
        " AND j.type='image_gen' AND j.state='approved') ORDER BY s.idx", (pid,)).fetchall()
    rows = p.conn.execute(
        "SELECT s.id sid, s.idx, m.* FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
        " WHERE s.project_id=? ORDER BY s.idx", (pid,)).fetchall()
    dialogue_panel(p, pid, "s3")
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
            with st.expander("🎥 Video tham chiếu chuyển động" + (" — đã gắn" if r["ref_video_path"] else ""),
                             expanded=False):
                st.caption("Video chỉ cho model **chuyển động/nhịp/lực** (vd clip gameplay thật của một skill); "
                          "**diện mạo nhân vật vẫn lấy từ ảnh khung đầu / Character Bible**, không lấy từ video này. "
                          "Kling: chọn 'feature' (mặc định, tạo clip mới theo chuyển động) hoặc 'base' (sửa trực tiếp "
                          "clip này). Seedance: luôn coi là ví dụ chuyển động, không phân biệt feature/base. "
                          "Không dùng cùng lúc với '🔊 Model tự tạo âm thanh' trên Kling (API sẽ từ chối).")
                if r["ref_video_path"]:
                    st.caption(f"Đang gắn: `{os.path.basename(r['ref_video_path'])}`")
                    if st.button("✖ Bỏ video tham chiếu", key=f"mprv_clear_{r['sid']}"):
                        act(lambda: p.set_motion_ref_video(r["sid"], None), "Đã bỏ")
                        st.rerun()
                up = st.file_uploader("Tải video tham chiếu (MP4)", type=["mp4", "mov", "webm"],
                                      key=f"mprv_up_{r['sid']}")
                refer_type = st.radio("Kiểu tham chiếu (chỉ Kling)", ["feature", "base"],
                                      horizontal=True, key=f"mprv_type_{r['sid']}")
                if st.button("⬆ Lưu video tham chiếu", key=f"mprv_save_{r['sid']}", disabled=up is None):
                    dest = os.path.join(project_dir(pid, "motion_ref"), f"scene_{r['idx']}_{up.name}")
                    with open(dest, "wb") as f:
                        f.write(up.getbuffer())
                    act(lambda: p.set_motion_ref_video(r["sid"], dest, refer_type), "Đã gắn video tham chiếu")
                    st.rerun()
            scene_expander(p, r["sid"])
            st.divider()


# ---- step 4 --------------------------------------------------------------------------
def step4(p: Pipeline, pid: int):
    ready = llm_io.ready_for_video(p, pid)
    dialogue_panel(p, pid, "s4")
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
        n_subj = p.conn.execute("SELECT COUNT(*) c FROM characters WHERE project_id=? AND subject_status='active'",
                                (pid,)).fetchone()["c"]
        use_subj = st.checkbox(f"🧩 Gắn ảnh chủ thể nhân vật vào video (Seedance) — {n_subj} nhân vật có chủ thể active",
                               bool(proj["use_subjects"]), key=f"vsubj_{pid}",
                               help="Chỉ Seedance. Mỗi cảnh gắn chủ thể của các nhân vật xuất hiện trong cảnh (kho chủ thể ở Bước 1). "
                                    "Chưa thử thật; ảnh chủ thể tính vào giới hạn số ảnh tham chiếu.")
        if use_subj != bool(proj["use_subjects"]):
            p.set_use_subjects(pid, use_subj)
        if runner is None:
            st.caption("ℹ Clip AI chưa cấu hình: chỉ theo dõi job thủ công.")
            with st.expander("Cách cấu hình"):
                st.write("Đặt VIDEO_PROVIDER=clipai và CLIPAI_TOKEN (biến môi trường), xem docs/RUNBOOK.md.")
        else:
            st.caption(f"Provider video: {runner.provider.name}" + (" (giả lập)" if runner.provider.name == "mock" else " (gọi API thật, tốn credit)"))
        allowed = show_estimate(video_estimate(p, pid), runner)
        if p.conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='video_gen' AND state='running' LIMIT 1", (pid,)).fetchone():
            st.info("🔄 Video đang được tạo: trang tự cập nhật, clip xong sẽ tự hiện; bạn không cần bấm gì.")
            auto_poll_videos(pid)
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
                if j["escalated"] and st.button("↺ Làm lại từ đầu", key=f"vrs_{j['id']}",
                                                help="Đã hết số lần thử: bắt đầu lại với một job video mới"):
                    if act(lambda: p.restart_job(j["id"]), "Đã xếp hàng job video mới"):
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
        ok = act(lambda: final_cut.preview_with_music(p, DATA, pid, music_path, out,
                                                      keep_audio=bool(p.project(pid)["video_audio"])),
                 "Đã tạo bản xem thử")
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
            show_video(shown[0], "Vừa")
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
def _has_audio(path: str, mtime: float) -> bool:
    return ffmpeg_studio.has_audio(path)


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
            vsize = "Vừa"
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
                show_video(out, "Vừa")
                with open(out, "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name="FINAL_VIDEO.mp4", mime="video/mp4")
                resize_panel(pid, out)
        subtitle_panel(p, pid, out)
        music_branch(p, pid)
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
        keep = st.checkbox("🔊 Giữ âm thanh gốc của clip (lời thoại do model tạo)", bool(p.project(pid)["video_audio"]),
                           key=f"keepaud_{pid}", help="Nhạc nền được trộn bên dưới lời thoại. Cần MỌI clip đã chọn có âm thanh.")
        if keep and chosen:
            silent_clips = [os.path.basename(c) for c in chosen if not _has_audio(c, os.path.getmtime(c))]
            if silent_clips:
                st.warning("Clip không có âm thanh: " + ", ".join(silent_clips) + " → âm thanh gốc sẽ bị bỏ cho cả bản ghép.")
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
                ok = act(lambda: ffmpeg_studio.render_final(chosen, out, durations, transition, fade, music_file, volume, extras, keep),
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


def monitor(p: Pipeline, pid: int) -> None:
    """Load and performance of the whole system (all projects), to spot overload before it costs credit."""
    mgr = autopilot_manager(DB, DATA)
    snap = perf.snapshot(p.conn, mgr.queue_length(), mgr.running_count(), mgr.max_parallel)
    ui.html(ui.card_title("📊 Theo dõi hiệu suất & tải hệ thống", "toàn bộ dự án, làm mới bằng nút bên phải"))
    if st.button("↻ Làm mới", key="perf_refresh"):
        st.rerun()
    for msg in snap["alerts"]:
        st.markdown(f":orange[⚠ {msg}]")
    if not snap["alerts"]:
        st.markdown(":green[✔ Chưa thấy dấu hiệu quá tải.]")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dự án chạy tự động", f"{mgr.running_count()}/{mgr.max_parallel}", help="AUTOPILOT_MAX_PARALLEL")
    c2.metric("Đang xếp hàng", mgr.queue_length())
    c3.metric("Job hôm nay", f"{snap['jobs_today']}/{snap['daily_limit'] or '∞'}", help="AUTOPILOT_DAILY_JOBS (giờ UTC)")
    c4.metric("Job đang chạy/chờ", sum(k["running"] + k["queued"] for k in snap["kinds"]))
    rows = []
    for k in snap["kinds"]:
        total = k["ok_24h"] + k["failed_24h"]
        rows.append({"Loại": dict(perf.KINDS)[k["kind"]], "Đang chạy": k["running"], "Chờ": k["queued"],
                     "Xong 1h": k["ok_1h"], "Lỗi 1h": k["failed_1h"], "Xong 24h": k["ok_24h"], "Lỗi 24h": k["failed_24h"],
                     "Tỉ lệ lỗi 24h": f"{k['failed_24h'] / total:.0%}" if total else "-",
                     "Thời gian TB": f"{k['avg_sec']:.0f}s" if k["avg_sec"] else "-",
                     "Gần đây / trước đó": (f"{k['recent_sec']:.0f}s / {k['earlier_sec']:.0f}s"
                                            if k["recent_sec"] and k["earlier_sec"] else "-")})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption("Mức song song tự học (tăng dần khi chạy êm, giảm một nửa khi nhà cung cấp báo quá tải 429): " + "; ".join(
        f"{dict(perf.KINDS)[k]}: {v['limit']} job cùng lúc, đã bị giới hạn {v['hits']} lần" for k, v in snap["learned"].items()))
    if snap["usage_today"]:
        st.caption("Dùng hôm nay: " + ", ".join(f"{q:g} {unit} ({kind})" for kind, unit, q in snap["usage_today"]))
    ui.html(ui.card_title("👥 Số video theo người dùng", "ai đã gen bao nhiêu (tính theo tên nhập ở góc trên)"))
    period = st.radio("Khoảng thời gian", ["Hôm nay", "7 ngày", "30 ngày", "Tất cả"], horizontal=True, key="by_user_period")
    days = {"Hôm nay": 1, "7 ngày": 7, "30 ngày": 30, "Tất cả": None}[period]
    people = perf.by_user(p.conn, days)
    if people:
        st.dataframe([{"Người dùng": r["who"], "Video đã gen": str(r["videos_ok"]), "Video đã gửi": str(r["videos"]),
                       "Lỗi": str(r["videos_failed"]), "Gen lại": str(r["videos_retry"]),
                       "Tổng giây video": f"{r['seconds']:g}", "Ảnh đã gen": str(r["images"]), "Dự án": str(r["projects"]),
                       "Lần gần nhất": (r["last_at"] or "")[:16].replace("T", " ")} for r in people],
                     hide_index=True, use_container_width=True)
        st.caption("“Video đã gen” = video thành công; “đã gửi” gồm cả lỗi và gen lại. Tên là tự khai, không phải tài khoản: "
                   "chỉ dùng để thống kê, không ngăn được người khác mạo danh.")
    else:
        st.caption("Chưa có lượt gen nào trong khoảng này.")
    ui.html(ui.card_title("📁 Tổng quan tất cả dự án", "mọi dự án — tự động hoàn toàn lẫn từng bước/bán tự động — cùng lúc"))
    portfolio = perf.portfolio_rows(p.conn, DATA)
    if not portfolio:
        st.caption("Chưa có dự án nào.")
    else:
        mode_label = {"auto": "Auto", "human_qc": "Human QC"}
        st.dataframe([{"Dự án": f"#{r['id']} {r['name']}",
                       "Chế độ QC": mode_label.get(r["operating_mode"], r["operating_mode"]),
                       "Đang chạy": ("⏸ Tạm dừng" if r["paused"] else "🚀 Tự động hoàn toàn" if r["running_auto"]
                                    else "🧭 Từng bước" if not r["done"] else "-"),
                       "Bước hiện tại": r["step_label"], "Ảnh duyệt": f"{r['images']}/{r['scenes']}",
                       "Prompt duyệt": f"{r['motion']}/{r['scenes']}", "Video xong": f"{r['videos']}/{r['scenes']}",
                       "Job hoạt động": r["active"], "Chờ duyệt": r["needs_review"],
                       "Người tạo": r["created_by"], "Ghi chú tự động": r["autopilot_note"]}
                      for r in portfolio], hide_index=True, use_container_width=True)
        finished = [r for r in portfolio if r["done"]]
        with st.expander(f"🎬 Sản phẩm đã hoàn tất ({len(finished)})", expanded=bool(finished)):
            if not finished:
                st.caption("Chưa có dự án nào ra FINAL_VIDEO.mp4.")
            for r in finished:
                st.markdown(f"**#{r['id']} {r['name']}**")
                show_video(r["final_video"], "Nhỏ")
                with open(r["final_video"], "rb") as f:
                    st.download_button("⬇ Tải FINAL_VIDEO.mp4", f, file_name=f"{r['name']}_FINAL_VIDEO.mp4",
                                       key=f"portfolio_dl_{r['id']}")
    st.caption("Ngưỡng cảnh báo chỉnh bằng biến môi trường: PERF_MAX_ACTIVE, PERF_FAIL_WARN, PERF_SLOW_WARN; "
               "song song: AUTOPILOT_MAX_PARALLEL; trần ngày: AUTOPILOT_DAILY_JOBS. "
               "Chưa đo thời gian gọi Claude (QC/motion).")


    st.markdown("---")
    ui.html(ui.card_title("🩺 Giám sát từng khâu", "lỗi, lỗi âm thầm và chỗ chưa trơn tru trong 24h qua"))
    stages = diag.stage_table(p.conn)
    st.dataframe([{"": diag.health(s), "Khâu": s["label"], "Job": "-" if s["jobs"] is None else str(s["jobs"]),
                   "Xong": "-" if s["ok"] is None else str(s["ok"]), "Lỗi": "-" if s["failed"] is None else str(s["failed"]),
                   "Gen lại": "-" if s["retried"] is None else str(s["retried"]), "Cảnh báo": s["warn"],
                   "Lỗi ghi nhận": s["error"]} for s in stages], hide_index=True, use_container_width=True)
    findings = diag.scan(p.conn, DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
    st.markdown(f"**Vấn đề phát hiện ({len(findings)})** — gồm cả lỗi không ai báo (job kẹt, file mất, tiến trình chết, gen lại nhiều...)")
    if not findings:
        st.markdown(":green[✔ Chưa thấy vấn đề âm thầm.]")
    for f in findings[:30]:
        color = "red" if f["severity"] == "error" else "orange"
        st.markdown(f":{color}[● {diag.STAGE_LABEL.get(f['stage'], f['stage'])}] {escape(diag.redact(f['title']))}"
                    + (f" — {escape(diag.redact(f['detail']))}" if f["detail"] else ""))
    events = diag.recent(p.conn, 24, 40)
    with st.expander(f"Sự kiện lỗi/cảnh báo gần đây ({len(events)})"):
        st.dataframe([{"Giờ": e["last_at"][11:19], "Mức": e["severity"], "Khâu": e["stage"], "Mã": e["code"] or "",
                       "Lần": e["count"], "Dự án": str(e["project_id"] or ""), "Nội dung": e["message"]} for e in events],
                     hide_index=True, use_container_width=True)
    text = diag.report(p.conn, DATA, {"Đang chạy/xếp hàng": f"{mgr.running_count()}/{mgr.queue_length()}",
                                      "Mức song song tự học": {k: v["limit"] for k, v in snap["learned"].items()}})
    st.markdown("**📋 Báo cáo chẩn đoán** — bấm nút copy ở góc khung dưới (hoặc tải file), dán vào chat để mình sửa. "
                "Đã che khóa/token và đường dẫn cá nhân.")
    st.download_button("⬇ Tải báo cáo (.md)", text, file_name="bao_cao_chan_doan.md", key="diag_dl")
    st.code(text, language="markdown")
    st.caption("Giám sát luôn chạy nền khi có thao tác gọi nhà cung cấp/Claude; ngưỡng: DIAG_STUCK_IMAGE_MIN, "
               "DIAG_STUCK_VIDEO_MIN, DIAG_QUEUED_MIN, DIAG_RETRY_WARN.")


def lessons_tab(p: Pipeline, pid: int) -> None:
    """Learning across projects: repeated mistakes and monthly research become lessons a person approves."""
    conn = p.conn
    ui.html(ui.card_title("🎓 Bài học rút ra từ các dự án", "hệ thống tự phát hiện lỗi lặp lại; bạn duyệt thì mới vào kiến thức"))
    st.caption("Lỗi lặp lại (cùng loại, nhiều lần, nhiều dự án) và tài liệu mới tìm được sẽ thành **đề xuất**. Chỉ khi bạn bấm "
               "Duyệt, đề xuất mới vào Kho kiến thức của Director/QC/Motion. Sau đó nhớ chắt lọc lại cẩm nang ở Cài đặt.")
    llm = llm_runner.client_from_env()
    c1, c2 = st.columns(2)
    if c1.button("🔎 Rút bài học từ các lỗi đã gặp", key="ls_mine", use_container_width=True):
        made = lessons.propose(conn, llm)
        st.success(f"Có {made} đề xuất mới." if made else "Chưa có loại lỗi nào lặp đủ nhiều để đề xuất.")
    if c2.button("🌐 Nghiên cứu tài liệu mới ngay", key="ls_research", use_container_width=True, disabled=llm is None,
                 help="Cần ANTHROPIC_API_KEY. Có tính phí tìm kiếm web (tối đa vài lượt tìm cho mỗi chủ đề)."):
        try:
            r = research.run(conn, llm)
            st.success(f"Nghiên cứu xong: {r['proposed']} đề xuất mới." + (f" Có lỗi: {r['errors'][0]}" if r["errors"] else ""))
        except ERRORS as e:
            st.error(str(e))
    monthly = st.checkbox("Tự nghiên cứu hàng tháng (khi mở Dashboard và đã đến hạn)", value=research.enabled(conn), key="ls_monthly",
                          help="Mặc định tắt vì tốn phí. Máy phải mở Dashboard ít nhất một lần trong tháng, hoặc dùng "
                               "tools/monthly_research.py với Task Scheduler.")
    if monthly != research.enabled(conn):
        lessons.set_meta(conn, "research_monthly", "1" if monthly else "0")
    last = lessons.meta(conn, "research_last_run")
    st.caption(f"Lần nghiên cứu gần nhất: {last or 'chưa có'}. Nội dung web coi là không đáng tin: chỉ thành đề xuất, không tự áp dụng.")
    proposed = lessons.list_lessons(conn, "proposed")
    st.markdown(f"**Đề xuất chờ duyệt ({len(proposed)})**")
    for row in proposed:
        with st.container(border=True):
            ev = json.loads(row["evidence"] or "{}")
            where = knowledge.GROUPS[row["group_name"]][0]
            origin = ("nghiên cứu web: " + ", ".join(ev.get("urls", []))) if row["source"] == "research" else (
                f"{ev.get('events')} lần ở {ev.get('projects')} dự án")
            st.markdown(f"**{escape(row['title'])}** · {escape(where)}")
            st.caption(f"Nguồn: {origin}")
            title = st.text_input("Tiêu đề", row["title"], key=f"ls_t_{row['id']}", label_visibility="collapsed")
            body = st.text_area("Nội dung quy tắc", row["body"], key=f"ls_b_{row['id']}", height=100)
            a, b, _ = st.columns([1, 1, 3])
            if a.button("👍 Duyệt", key=f"ls_ok_{row['id']}", type="primary"):
                lessons.edit(conn, row["id"], title, body)
                lessons.decide(conn, row["id"], True)
                st.rerun()
            if b.button("👎 Bỏ", key=f"ls_no_{row['id']}"):
                lessons.decide(conn, row["id"], False)
                st.rerun()
    approved = lessons.list_lessons(conn, "approved")
    with st.expander(f"Bài học đã duyệt ({len(approved)})"):
        for row in approved:
            st.markdown(f"- **{escape(row['title'])}** ({row['group_name']}): {escape(row['body'])}")
            if st.button("Gỡ bài học này", key=f"ls_rm_{row['id']}"):
                lessons.decide(conn, row["id"], False)
                st.rerun()
    lessons.harvest(conn)
    rows = lessons.clusters(conn)
    with st.expander(f"Các loại lỗi đã ghi nhận ({len(rows)})"):
        if rows:
            st.dataframe([{"Bước": r["group"], "Loại lỗi": r["label"], "Số lần": r["events"], "Số dự án": r["projects"],
                           "Đủ để đề xuất": "có" if r["ready"] else "chưa"} for r in rows], hide_index=True,
                         use_container_width=True)
        else:
            st.caption("Chưa có lỗi nào được ghi nhận (lấy từ ảnh/video bị loại kèm lý do và các lần bị risk control chặn).")
        st.caption(f"Ngưỡng đề xuất: ≥{lessons.MIN_EVENTS} lần và ≥{lessons.MIN_PROJECTS} dự án.")


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
    size = "Vừa"
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


def subtitle_panel(p: Pipeline, pid: int, out: str) -> None:
    """Step 5: automatic subtitles from the script's dialogue (language, font, size...), burned into a copy of the final video."""
    settings = subtitles.get_settings(p, pid)
    fonts = subtitles.discover()
    default = subtitles.default_font(fonts)
    with st.expander("🔤 Phụ đề tự động (từ lời thoại trong kịch bản)", expanded=os.path.exists(out)):
        st.caption("Lấy các dòng thoại `TÊN: lời` của từng cảnh, chia thời gian trong clip theo độ dài câu (ước lượng, **không phải nhận dạng "
                   "giọng nói**), có thể dịch sang ngôn ngữ khác bằng Claude, rồi in vào một bản sao của video cuối. Bạn sửa được chữ và "
                   "thời điểm trước khi in.")
        llm = llm_client()
        c1, c2, c3 = st.columns([2, 2, 1.4])
        langs = list(subtitles.LANGS)
        lang = c1.selectbox("Ngôn ngữ phụ đề", langs, index=langs.index(settings["lang"]) if settings["lang"] in langs else 0,
                            format_func=lambda k: subtitles.LANGS[k], key=f"sub_lang_{pid}")
        families = [f.family for f in fonts]
        current = settings["font"] if settings["font"] in families else (default.family if default else None)
        font_name = c2.selectbox("Font", families, index=families.index(current) if current in families else 0, key=f"sub_font_{pid}",
                                 help="Mặc định GFF Latin Bold (font Free Fire). Font không có đủ chữ của ngôn ngữ chọn sẽ được đổi tự động.") \
            if families else None
        size = c3.selectbox("Cỡ chữ", list(subtitles.SIZES), index=list(subtitles.SIZES).index(settings["size"]),
                            format_func=lambda k: subtitles.SIZES[k][0], key=f"sub_size_{pid}")
        d1, d2, d3 = st.columns([1.4, 1.4, 2.2], vertical_alignment="bottom")
        pos = d1.selectbox("Vị trí", list(subtitles.POSITIONS), index=list(subtitles.POSITIONS).index(settings["pos"]),
                           format_func=lambda k: subtitles.POSITIONS[k][0], key=f"sub_pos_{pid}")
        color = d2.selectbox("Màu chữ", list(subtitles.COLORS), index=list(subtitles.COLORS).index(settings["color"]),
                             format_func=lambda k: subtitles.COLORS[k][0], key=f"sub_color_{pid}")
        speaker = d3.checkbox("Ghi tên người nói trước câu", settings["speaker"], key=f"sub_speaker_{pid}")
        auto = st.checkbox("Tự thêm phụ đề khi chạy tự động hoàn toàn", settings["enabled"], key=f"sub_auto_{pid}")
        new = {"enabled": auto, "lang": lang, "font": font_name or "", "size": size, "pos": pos, "color": color, "speaker": speaker}
        if new != {k: settings[k] for k in new}:
            subtitles.save_settings(p, pid, new)
        up = st.file_uploader("Thêm font riêng (.ttf / .otf)", type=["ttf", "otf"], key=f"sub_fontup_{pid}")
        if up is not None and st.button("Thêm font này", key=f"sub_fontadd_{pid}"):
            try:
                subtitles.save_uploaded_font(up.name, up.getvalue())
            except subtitles.SubtitleError as e:
                st.error(str(e))
            else:
                st.rerun()
        if lang != "src" and llm is None:
            st.markdown(":orange[Dịch sang ngôn ngữ khác cần Claude API (ANTHROPIC_API_KEY). Chưa có thì chỉ dùng được “Giữ nguyên ngôn ngữ kịch bản”.]")
        key = f"sub_cues_{pid}"
        if st.button("📝 Tạo danh sách phụ đề", key=f"sub_make_{pid}", type="primary", disabled=lang != "src" and llm is None):
            try:
                cues = subtitles.build_cues(p, DATA, pid, st.session_state.get(f"tr_{pid}", "cut"), float(st.session_state.get(f"fade_{pid}", 1.0)))
                if not cues:
                    st.info("Chưa có dòng thoại nào (cần dòng `TÊN: lời` trong cảnh) hoặc chưa có clip ở Bước 4.")
                else:
                    with st.spinner("Đang dịch…" if lang != "src" else "Đang tạo…"):
                        cues = subtitles.translate(llm, cues, lang)
                    st.session_state[key] = [{"Cảnh": c.scene, "Người nói": c.speaker, "Bắt đầu (s)": c.start, "Kết thúc (s)": c.end,
                                              "Nội dung": c.text} for c in cues]
            except ERRORS + (subtitles.SubtitleError,) as e:
                st.error(str(e))
        rows = st.session_state.get(key)
        if rows:
            edited = st.data_editor(rows, hide_index=True, width="stretch", key=f"sub_table_{pid}",
                                    disabled=["Cảnh", "Người nói"], num_rows="fixed")
            table = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
            cues = [subtitles.Cue(float(r["Bắt đầu (s)"]), float(r["Kết thúc (s)"]), str(r["Nội dung"]).strip(), str(r["Người nói"] or ""),
                                  r["Cảnh"]) for r in table if str(r["Nội dung"]).strip()]
            font, note = subtitles.font_for_text(subtitles.font_by_family(fonts, font_name) if font_name else default, fonts,
                                                 " ".join(c.text for c in cues))
            if note:
                st.markdown(f":orange[{escape(note)}]")
            bad = [c for c in cues if c.end <= c.start]
            if bad:
                st.error("Có dòng kết thúc trước khi bắt đầu: sửa lại cột thời gian.")
            b1, b2 = st.columns(2)
            srt = subtitles.to_srt(cues, speaker)
            b1.download_button("⬇ Tải file .srt", srt.encode("utf-8"), file_name=f"phu_de_{lang}.srt", mime="application/x-subrip",
                               key=f"sub_srt_{pid}")
            if b2.button("🔥 In phụ đề vào video", key=f"sub_burn_{pid}", disabled=not os.path.exists(out) or bool(bad)):
                target = os.path.join(project_dir(pid, "output"), f"FINAL_VIDEO_sub_{lang}.mp4")
                try:
                    with st.spinner("Đang in phụ đề (mã hóa lại video)…"):
                        res = subtitles.burn(out, cues, target, font, size, pos, color, speaker)
                except ERRORS + (subtitles.SubtitleError,) as e:
                    st.error(str(e))
                else:
                    st.session_state[f"sub_done_{pid}"] = res
            if not os.path.exists(out):
                st.caption("Ghép video cuối trước, rồi mới in được phụ đề.")
        done = st.session_state.get(f"sub_done_{pid}")
        if done and os.path.exists(done["video"]):
            st.success(f"Đã in {done['cues']} dòng bằng font {done['font']}" + ("" if done["font_verified"] else " (không xác nhận được font, có thể bị thay)"))
            show_video(done["video"], "Vừa")
            with open(done["video"], "rb") as f:
                st.download_button(f"⬇ Tải {os.path.basename(done['video'])}", f, file_name=os.path.basename(done["video"]), mime="video/mp4",
                                   key=f"sub_dl_{pid}")


def sfx_assistant(p: Pipeline, pid: int) -> None:
    """One button: AI reads the scenes and the sound library and proposes effects; the person reviews, edits and adds them."""
    n = sound_lib.counts(p.conn)
    if not n:
        return
    key = f"sfxplan_{pid}"
    with st.container(border=True):
        ui.html(ui.card_title("🎧 Hiệu ứng âm thanh", "AI đọc kịch bản + kho của bạn, đề xuất chỗ cần điểm nhấn / chuyển cảnh"))
        if not n.get("sfx"):
            st.caption("Kho âm thanh chưa có hiệu ứng nào.")
        else:
            wish = st.text_input("Yêu cầu thêm (không bắt buộc)", key=f"sfx_wish_{pid}",
                                 placeholder="vd: ít thôi, chỉ ở chuyển cảnh · thêm tiếng va chạm ở cảnh 3")
            transition = st.session_state.get(f"tr_{pid}", "cut")
            fade = float(st.session_state.get(f"fade_{pid}", 1.0))
            if st.button("🤖 AI tự đề xuất hiệu ứng", key=f"sfx_ai_go_{pid}", type="primary"):
                client = llm_client()
                try:
                    with st.spinner("AI đang đọc các cảnh và chọn hiệu ứng…"):
                        st.session_state[key] = sfx_plan.propose(client, p, DATA, pid, transition, fade, wish)
                except (sfx_plan.SfxPlanError, llm_runner.LlmError) as e:
                    st.error(str(e))
            plan = st.session_state.get(key)
            if plan is not None:
                if plan["summary"]:
                    st.info(plan["summary"])
                if not plan["cues"]:
                    st.caption("AI không thấy chỗ nào cần thêm hiệu ứng.")
                else:
                    import pandas as pd
                    frame = pd.DataFrame([{"Dùng": True, "Giây": c["at"], "Cảnh": c["scene"], "Hiệu ứng": c["name"], "Thư mục": c["folder"],
                                           "Âm lượng": c["volume"], "Vì sao": c["reason"]} for c in plan["cues"]])
                    edited = st.data_editor(frame, key=f"sfx_table_{pid}", hide_index=True, width="stretch",
                                            disabled=["Cảnh", "Hiệu ứng", "Thư mục", "Vì sao"],
                                            column_config={"Giây": st.column_config.NumberColumn(min_value=0.0, step=0.1),
                                                           "Âm lượng": st.column_config.NumberColumn(min_value=0.0, max_value=1.5, step=0.05)})
                    b1, b2 = st.columns([2, 1])
                    if b1.button("✅ Thêm các hiệu ứng đã chọn vào video", key=f"sfx_apply_{pid}", type="primary"):
                        chosen = [{"id": plan["cues"][i]["id"], "at": float(row["Giây"]), "volume": float(row["Âm lượng"])}
                                  for i, row in edited.iterrows() if row["Dùng"]]
                        added = sfx_plan.apply(p, DATA, pid, chosen)
                        st.session_state.pop(key, None)
                        st.toast(f"Đã thêm {added} hiệu ứng (chỉnh tiếp ở mục Hiệu ứng âm thanh & giọng đọc bên trên)")
                        st.rerun()
                    if b2.button("Bỏ đề xuất", key=f"sfx_drop_{pid}"):
                        st.session_state.pop(key, None)
                        st.rerun()
        if n.get("music"):
            mode = p.project(pid)["music_mode"] == "library"
            auto = st.checkbox("Nhạc nền: ưu tiên lấy từ kho của tôi thay vì để AI tạo (tiết kiệm credit; AI tạo nhạc vẫn là mặc định)", mode,
                               key=f"music_mode_{pid}")
            if auto != mode:
                p.conn.execute("UPDATE projects SET music_mode=? WHERE id=?", ("library" if auto else None, pid))
                p.conn.commit()


def step5(p: Pipeline, pid: int):
    """Music and the final render are one step now."""
    ui.html(ui.card_title("🎞 Ghép & render", "cắt ghép clip; nhạc nền và phụ đề là các nhánh phụ"))
    step5b(p, pid)


def music_branch(p: Pipeline, pid: int) -> None:
    """Background music as a side branch of the render step (like the subtitles): AI-made music first, the own library as support."""
    _, selected_dir = music.project_dirs(DATA, pid)
    st.markdown("---")
    ui.html(ui.card_title("🎵 Nhạc nền (nhánh phụ)", "AI tạo nhạc theo mood các cảnh; kho nhạc của bạn chỉ hỗ trợ")
            + (ui.badge("đã chọn", "b-ok") if os.listdir(selected_dir) else ui.badge("chưa chọn")))
    step5a(p, pid)
    sfx_assistant(p, pid)


def run_startup_sync(fn, what: str, code: str) -> None:
    """Folder auto-sync (possibly over a slow Drive) runs in the background so the page opens at once; new items show on the next refresh."""
    def work():
        conn = connect(DB)
        try:
            fn(conn)
        except Exception as e:  # noqa: BLE001 - a library problem must never stop the dashboard from opening
            diag.record(conn, "system", "warn", f"{what} lỗi: {type(e).__name__}: {e}", code)
    if os.environ.get("DASHBOARD_SYNC_BACKGROUND", "1") == "0":
        work()
    else:
        threading.Thread(target=work, daemon=True).start()


def main():
    logo = os.path.join(os.path.dirname(__file__), "..", "assets", "logo_g_192.png")
    st.set_page_config(layout="wide", page_title="AI Video Pipeline", page_icon=logo if os.path.exists(logo) else None)
    ui.inject_css()
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    p = Pipeline(connect(DB))
    require_login(p.conn)
    account_bar(p)
    p.actor = me()["email"] if auth_on() else (user_bar() or None)
    pid = global_bar(p)
    if pid is None:
        return
    purge_trash(DATA)
    trash.sweep_rejected(p, DATA, pid)
    if "assets_synced" not in st.session_state:         # folders marked "auto": pick up new pictures, once per browser session
        st.session_state["assets_synced"] = True
        run_startup_sync(assets.auto_sync, "đồng bộ tài nguyên", "assets_sync")
    if "sounds_scanned" not in st.session_state:        # sound folders marked "auto": list new files, once per browser session
        st.session_state["sounds_scanned"] = True
        run_startup_sync(lambda conn: (sound_lib.auto_scan(conn), sound_lib.analyze(conn, limit=150), sound_lib.listen(conn, limit=150)), "quét và nghe kho âm thanh", "sounds_scan")
    if "ff_site_checked" not in st.session_state:       # official website refresh, at most monthly, in the background
        st.session_state["ff_site_checked"] = True
        try:
            ff_site.maybe_monthly(DB)
        except Exception as e:  # noqa: BLE001
            diag.record(p.conn, "system", "warn", f"kiểm tra cập nhật website lỗi: {type(e).__name__}: {e}", "ff_site")
    if "research_checked" not in st.session_state:      # monthly research, at most once per browser session
        st.session_state["research_checked"] = True
        research.maybe_run_in_background(DB)
    problems = [f for f in diag.scan(p.conn, DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15"))) if f["severity"] == "error"]
    if problems:
        st.markdown(f":red[🔴 Giám sát: {len(problems)} vấn đề nghiêm trọng, ví dụ: {escape(diag.redact(problems[0]['title']))}] "
                    "— mở tab “📊 Theo dõi hiệu suất” để xem và lấy báo cáo.")
    deep = st.query_params.get("step")  # ?step=2 opens a step directly (1..5, monitor); 5a/5b and the
    deep = {"5a": "5", "5b": "5"}.get(deep, deep)  # history/lessons/users dialog deep links still work (settings_menu)
    keys = ["1", "2", "3", "4", "5", "monitor"]
    visible = [s for s in STEPS if allowed(STEP_PERMISSION.get(s, "workflow"))]
    if deep in keys and "step" not in st.session_state and STEPS[keys.index(deep)] in visible:
        st.session_state["step"] = STEPS[keys.index(deep)]
    if st.session_state.get("step") not in visible:
        st.session_state.pop("step", None)
    step = st.radio("Bước", visible, horizontal=True, key="step", label_visibility="collapsed",
                    format_func=step_label(step_done(p, pid)))
    {STEPS[0]: step1, STEPS[1]: step2, STEPS[2]: step3, STEPS[3]: step4, STEPS[4]: step5,
     STEPS[5]: monitor}[step](p, pid)
    if allowed("shutdown"):
      with st.expander("⏻ Tắt Dashboard"):
        st.caption("Dừng máy chủ Dashboard trên máy này (các việc đang chạy nền cũng dừng; tiến độ đã lưu, bấm Tiếp tục khi mở lại).")
        if confirm_all("shutdown", ["go"], "⏻ Tắt Dashboard", "Tắt Dashboard ngay bây giờ?", st, "Có, tắt"):
            stop = os.path.join(os.path.dirname(__file__), "..", "tools", "stop_dashboard.ps1")
            subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", stop],
                             creationflags=0x00000008)
            st.info("Đang tắt… có thể đóng cửa sổ này.")


main()
