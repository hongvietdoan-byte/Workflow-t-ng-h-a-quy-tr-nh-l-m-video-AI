"""Shared helpers of the dashboard: providers, cost, small widgets, auth lookups, constants.

DB / DATA are set by configure() on every script run (tests switch PIPELINE_DB / PIPELINE_DATA between runs while this module stays
imported), so other modules must read them as common.DB / common.DATA at call time.
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


from core import effectiveness, costume, previz, asset_vision, autoqc, ff_site, sfx_plan, sound_lib, assets, audio_lib, subtitles, script_reader, auth, autopilot, dialogue, diag, knowledge, lessons, perf, regen, research, style, subjects, trash, waveform, cost, ffmpeg_studio, final_cut, llm_io, llm_runner, music, preflight, prompts, script_parser, video_analysis  # noqa: E402
from core import batch, budget, claude_tasks, delivery, formats, lineage, model_router, pilot, qc_policy, voice, voice_check  # noqa: E402
from core import access  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline, PipelinePaused  # noqa: E402
from core.adapters import factory  # noqa: E402
from core.providers import ProviderError  # noqa: E402
from core.runner import ImageRunner, VideoRunner  # noqa: E402
from core.states import InvalidTransition, JobState  # noqa: E402

from dashboard import ui  # noqa: E402

DB = os.path.join("data", "manifest.sqlite")
DATA = os.path.join("data", "projects")


def configure(db: str, data: str) -> None:
    global DB, DATA
    DB, DATA = db, data


# Đợt 3 (01/10): 5 bước → 4 màn + trang đầu + Nhóm. Mỗi màn dựng từ các hàm bước cũ, KHÔNG bỏ tính năng nào:
#   Kịch bản = step1 · Storyboard = step2 (Ảnh + QC) + step3 (Motion & giọng) trong 2 tab · Video = step4 · Bản giao = step5.
STEPS = ["⌂ Tất cả dự án", "Kịch bản", "Storyboard", "Video", "Bản giao", "👥 Nhóm", "📊 Theo dõi"]
SCREEN_INDEX = {"home": 0, "script": 1, "storyboard": 2, "video": 3, "deliver": 4, "team": 5, "monitor": 6}

STEP_PERMISSION = {"📊 Theo dõi": "monitor", "👥 Nhóm": "monitor"}


def screen_label(key: str) -> str:
    return STEPS[SCREEN_INDEX[key]]


SB_TABS = ("🖼 Ảnh + QC", "🎞 Motion, giọng & animatic")        # the two tabs of the Storyboard screen (dashboard/app.py)


def go_screen(project_id, key: str, tab: int = 0) -> None:
    """Button callback: open `project_id` (when given) on the screen `key` (runs before the widgets, so it may set both pickers).
    `tab` picks the Storyboard tab (0 = Ảnh, 1 = Motion)."""
    if project_id is not None:
        st.session_state["global_pid"] = project_id
    st.session_state["step"] = screen_label(key)
    if key == "storyboard":
        st.session_state["sb_tab"] = SB_TABS[tab]


# Lịch sử / Bài học / Phân quyền moved off the step bar into the settings gear (see settings_menu()) --
# each opens as its own closable st.dialog panel instead of living inline in the stepper.
DIALOG_FLAGS = ("dlg_assets", "dlg_pricing", "dlg_knowledge", "dlg_history", "dlg_lessons", "dlg_users", "dlg_budget", "dlg_clone", "dlg_limits", "dlg_features",
                "dlg_money_days")


def expert() -> bool:
    """Kế hoạch V4 5.3: "Chuyên gia" (off by default) shows the advanced / by-hand panels; off, each step shows what a normal run
    needs. DASHBOARD_EXPERT=1 turns it on for every session (tests of the advanced panels, power users)."""
    if os.environ.get("DASHBOARD_EXPERT", "").strip() == "1":
        return True
    return bool(st.session_state.get("expert_mode", False))


def open_dialog(flag: str) -> None:
    """Only one st.dialog may be open per script run: opening one always closes any other."""
    for f in DIALOG_FLAGS:
        st.session_state[f] = (f == flag)

def close_dialog(flag: str) -> None:
    st.session_state[flag] = False

ERRORS = (sqlite3.IntegrityError, zipfile.BadZipFile, llm_runner.LlmError, InvalidTransition, llm_io.SchemaError, PipelinePaused, ffmpeg_studio.FFmpegNotFound,
          ffmpeg_studio.FFmpegError, ValueError, KeyError, access.AccessDenied,     # AccessDenied: lỗi quyền theo dự án, tiếng Việt (core/access.py)
          lessons.LessonError)                                                      # S14.4 C1b: bài học không ghi được tài liệu

CRITERIA_LABEL = {"character": "Đúng nhân vật", "hands_face": "Không lỗi tay/mặt", "composition": "Đúng bố cục",
                  "mood_lighting": "Đúng mood / ánh sáng", "consistency": "Không chi tiết thừa/sai",
                  "scale": "Đúng tỉ lệ người/cảnh", "grounding": "Chân chạm đất", "set_match": "Khớp layout / bối cảnh",
                  "identity": "Giữ đúng nhân vật", "physics": "Vật lý hợp lý", "motion_match": "Khớp motion prompt", "artifacts": "Không biến dạng"}

FILTERS = {"all": "Tất cả", "review": "Chờ duyệt", "pass": "Đã duyệt", "fail": "Lỗi / đã loại", "run": "Chờ / đang gen"}

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
        st.error(f"Deepix (tạo ảnh) chưa sẵn sàng: {e}")      # J1: the adapter's message is Vietnamese + says what to do
        return None
    return ImageRunner(p, provider, DATA) if provider else None

def llm_client():
    """Claude client (ANTHROPIC_API_KEY, LLM_PROVIDER=claude_cli or mock); None when not configured -> paste JSON by hand."""
    try:
        return llm_runner.client_from_env(ledger=DB)       # Claude API calls go into the cost ledger + the Claude cap
    except llm_runner.LlmError as e:
        st.error(f"Claude: {e}")
        return None

def subjects_visible(p: Pipeline, pid: int) -> bool:
    """Seedance Subject Library is not used any more (decision 2026-09-22: the project's own resource pictures do the job). Its panels
    stay only for a project that already uses it (so it can be switched off) or when SHOW_SUBJECT_LIBRARY=1."""
    if os.environ.get("SHOW_SUBJECT_LIBRARY", "").strip() == "1" or p.project(pid)["use_subjects"]:
        return True
    return bool(p.conn.execute("SELECT 1 FROM characters WHERE project_id=? AND subject_asset_id IS NOT NULL LIMIT 1", (pid,)).fetchone())

def llm_label(client) -> str:
    """How Claude is reached, for button labels: the API, the Claude Code on this PC (uses the plan's quota) or the simulator."""
    return {"anthropic": "Claude API", "claude-cli": "Claude (Claude Code trên máy)", "mock-llm": "Claude giả lập"}.get(
        getattr(client, "name", ""), "Claude")

def tokens_text(r: dict) -> str:
    return f"{r.get('input_tokens', 0)} token vào / {r.get('output_tokens', 0)} token ra"

def image_estimate(p: Pipeline, pid: int):
    from core import image_models
    return cost.estimate_images(p, pid, cost.load_pricing(), image_models.of_project(p.project(pid)))   # the project's picture model

def show_estimate(est, runner) -> bool:
    """Show the estimate; for real providers require a confirmation tick on large batches. Returns 'allowed'."""
    if est is None:
        return True
    if est["items"] == 0:
        return True
    st.info("Ước tính chi phí: " + cost.format_estimate(est))
    return _confirm_big_batch(est, runner)


def _confirm_big_batch(est, runner) -> bool:
    """S14.8 U5: dùng chung cho common.show_estimate + storyboard_cards.show_estimate — provider thật + lô ≥ confirm_batch_at → phải tick
    xác nhận. Giữ khóa `confirm_{kind}` (tools/ui_v2_acceptance.py so khóa widget)."""
    if runner is None or runner.provider.name.startswith("mock"):
        return True
    if est["items"] >= cost.load_pricing()["confirm_batch_at"]:
        return st.checkbox(f"Tôi xác nhận batch {est['items']} mục này sẽ tốn credit", key=f"confirm_{est['kind']}")
    return True

PERIODIC_SEC = 60        # kế hoạch V4 5.3: housekeeping (trash, rejected results, the problem scan) at most this often, not every rerun


def periodic(key: str, fn, every: float = PERIODIC_SEC):
    """Run fn() at most once per `every` seconds in this browser session; the last result is kept and returned in between."""
    import time as _time
    slot = st.session_state.get(f"_periodic_{key}")
    if slot is None or _time.time() - slot[0] >= every:
        slot = (_time.time(), fn())
        st.session_state[f"_periodic_{key}"] = slot
    return slot[1]


def diag_problems(p: Pipeline) -> list:
    """Errors found by the problem scan (every 60 s, not on each click)."""
    return periodic("diag", lambda: [f for f in diag.scan(p.conn, DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
                                     if f["severity"] == "error"])


def spend_text(p: Pipeline, pid: int):
    """The project's spending in a few words (None: nothing sent yet) — for the one status line under the top bar."""
    spend = cost.spend_summary(p.conn, pid, cost.load_pricing())
    if not (spend["images"] or spend["clips"] or spend["audios"]):
        return None
    if spend["mock"] and spend["mock"] == spend["events"]:
        return f"giả lập: {spend['images']} ảnh · {spend['clips']} clip · {spend['audios']} âm thanh (không tốn credit)"
    text = f"{spend['images']} ảnh · {spend['clips']} clip ({spend['seconds']:.0f} s) · {spend['audios']} âm thanh"
    if spend["unknown_prices"]:
        text += " · chưa có giá: " + ", ".join(spend["unknown_prices"])
    else:
        text += f" ≈ {spend['credits']:.1f} {spend['currency']}"
    return text



def project_dir(pid: int, *parts: str) -> str:
    path = os.path.join(DATA, str(pid), *parts)
    os.makedirs(path, exist_ok=True)
    return path

def act(fn, success: str = ""):
    """Run an action, show errors instead of crashing, rerun on success."""
    try:
        fn()
    except ERRORS as e:
        st.error(str(e) or "Có lỗi, không rõ nguyên nhân")        # TON_DONG E1: the person reads the message, not the English class name
        st.caption(f"Mã lỗi kỹ thuật: {type(e).__name__}")
        return False
    if success:
        st.toast(success)
    return True

def confirm_all(key: str, ids, label: str, question: str, container=st, yes_label: str = "Có, duyệt hết") -> bool:
    """One 'approve all' button, then a yes/no question. True only when the user answers Yes.
    The question is tied to the exact set of items it was asked about: if the set changes, it is asked again."""
    from dashboard.design import components
    return components.confirm_all(key, ids, label, question, container, yes_label)

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

def unit_label(p: Pipeline, pid: int, idx: int) -> str:
    """'Cảnh 3' (v2: one clip per script scene) or 'Shot S02·3' (v3 shot row: shot 3 of script scene 2)."""
    from core import shots
    row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    return f"Shot {shots.label(data, idx)}" if data.get("shot_no") else f"Cảnh {idx}"

def unit_code(p: Pipeline, pid: int, idx: int) -> str:
    """Short code: 'S02·3' for a shot row, 'S02' for a v2 scene."""
    from core import shots
    row = p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()
    return shots.label(json.loads(row["data"] or "{}") if row else {}, idx)

def scene_expander(p: Pipeline, scene_id, expanded: bool = False, with_motion: bool = False) -> None:
    """Drop-down under an image/video: the script text of that scene plus its spec, so the result can be checked
    against what the script says."""
    row = p.conn.execute("SELECT idx, title, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return
    d = json.loads(row["data"] or "{}")
    from core import shots
    head = f"Shot {shots.label(d, row['idx'])} — {row['title']}" if d.get("shot_no") else scene_title(row["idx"], row["title"])
    with st.expander(f"📖 {head} · nội dung kịch bản", expanded=expanded):
        if d.get("text"):
            ui.html(f'<div class="scenetext">{escape(d["text"])}</div>')
        else:
            st.caption("Chưa có nội dung kịch bản (chạy phân tích ở màn Kịch bản).")
        lines = [("Bối cảnh", " · ".join(filter(None, [d.get("time"), d.get("location")]))),
                 ("Nhân vật", ", ".join(d.get("characters") or [])),
                 ("Mood / ánh sáng / cỡ cảnh", " · ".join(filter(None, [d.get("mood"), d.get("lighting"), d.get("shot")]))),
                 ("Vị trí nhân vật", d.get("blocking") or ""),
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

def auth_on() -> bool:
    return os.environ.get("DASHBOARD_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")

def me() -> dict:
    """The signed-in person of THIS browser session ({'email','name','role','perms'})."""
    return st.session_state.get("identity") or {}

def allowed(permission: str) -> bool:
    return auth.can(me(), permission)

def access_user():
    """{'email','role'} of the signed-in person for the per-project rights (core/access.py); None when sign-in is off."""
    return access.user_of(me()) if auth_on() else None

def scoped(p: Pipeline) -> Pipeline:
    """Make `p` act as the signed-in person: every core write on it is then checked against their rights on the project."""
    p.user = access_user()
    return p

def project_level(p: Pipeline, pid: int):
    """The signed-in person's level on a project: 'admin' | 'own' | 'edit' | 'view' | None (core/access.level)."""
    return access.level(p.conn, pid, access_user())

def read_only(p: Pipeline, pid: int) -> bool:
    """True when the person may look at this project but not change it (a "Chỉ xem" watcher)."""
    return access.RANK[project_level(p, pid)] < access.RANK["edit"]

def request_source() -> tuple:
    """(where the request came from for the audit log, whether it is the dashboard machine itself)."""
    try:
        host = st.context.headers.get("Host", "") or ""
        ip = st.context.ip_address or ""
    except Exception:  # noqa: BLE001 - an older Streamlit or a test runner: unknown origin
        return "", True
    # The connecting address decides, not the Host header (a LAN visitor can send "Host: localhost"). Streamlit gives no address
    # for a browser on this machine, so only then is the Host header trusted.
    if ip:
        local = ip.strip("[]") in ("127.0.0.1", "::1") or ip.startswith("::ffff:127.")
    else:
        local = host.split(":")[0].strip("[]") in ("localhost", "127.0.0.1", "::1", "")
    return f"host={host} ip={ip}", local

def request_ip() -> str:
    """The connecting address of this browser session ("" when Streamlit gives none, i.e. a browser on this machine / a test runner)."""
    try:
        ip = st.context.ip_address
    except Exception:  # noqa: BLE001 - an older Streamlit or a test runner
        return ""
    return ip if isinstance(ip, str) else ""         # AppTest hands a stand-in object, not an address

def request_device() -> str:
    """S14.29: the device code this browser keeps (cookie core.machine_auth.DEVICE_COOKIE), "" when none / malformed / no cookies."""
    from core import machine_auth
    try:
        code = st.context.cookies.get(machine_auth.DEVICE_COOKIE)
    except Exception:  # noqa: BLE001 - an older Streamlit or a test runner
        return ""
    return code if machine_auth.valid_device_code(code) else ""

def ensure_device_cookie() -> None:
    """S14.29: a browser on another machine without a device code gets one (random, made here, written by a tiny script straight into
    the cookie — never in the address, never logged), then the page reloads once so the server reads it. Only when the dashboard is
    open to the LAN; the dashboard machine itself needs none."""
    from core import machine_auth
    if not machine_auth.lan_on() or request_source()[1] or request_device():
        return
    code = st.session_state.setdefault("_device_code_new", machine_auth.new_device_code())
    import streamlit.components.v1 as components
    components.html(
        "<script>try{const d=window.parent.document;"
        f"if(!d.cookie.split('; ').some(c=>c.startsWith('{machine_auth.DEVICE_COOKIE}='))){{"
        f"d.cookie='{machine_auth.DEVICE_COOKIE}={code}; max-age=315360000; path=/; SameSite=Strict';"
        "window.parent.location.reload();}}catch(e){}</script>", height=0)

def lan_address() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        ip = "localhost"
    return f"http://{ip}:{os.environ.get('DASHBOARD_PORT', '8501')}"

def clean_name(raw: str) -> str:
    return " ".join((raw or "").split())[:40]

def can_delete_project(proj) -> bool:
    """Only the person who created a project, or the Owner, may delete it (core/access.can_manage; a "theo dõi" watcher may not)."""
    if not auth_on():
        return True
    creator = ((proj["created_by"] if "created_by" in proj.keys() else None) or "").strip().lower()
    who = me()
    return who.get("role") == "owner" or (bool(creator) and creator == (who.get("email") or "").strip().lower())

# ---- step 1 --------------------------------------------------------------------------
@st.cache_resource
def autopilot_manager(db: str, data: str):
    return autopilot.Manager(db, data, poll_sec=float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))

# ---- step 2 --------------------------------------------------------------------------
POLL_SECONDS = {"image": 6, "video": 15}



def step_header(title: str, goal: str, progress: str = "", stale: int = 0) -> None:
    """Same head on every step: what the step is for, where it stands, what is outdated (uiux: one clear 'next thing')."""
    extra = (f' {ui.badge(f"⚠ {stale} mục cũ", "b-warn")}' if stale else "")
    ui.html(f'<div class="stephead"><b>{escape(title)}</b> <span class="muted">{escape(goal)}</span>'
            + (f' <span class="badge b-info">{escape(progress)}</span>' if progress else "") + extra + "</div>")


def claude_hint() -> str:
    return "Cần Claude: ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli (Claude Code trên máy)."


def scene_status_text(row) -> str:
    """One short status of a scene across the chain, from core.lineage.scan: 'ảnh ✓ · prompt ⚠ · video —'."""
    def mark(done, stale):
        return "⚠" if stale else ("✓" if done else "—")
    return " · ".join([f"ảnh {mark(row['image_job_id'], row['image_stale'])}",
                       f"prompt {mark(row['motion_state'] == 'approved', row['motion_stale'])}",
                       f"video {mark(row['video_state'] in ('succeeded', 'approved'), row['video_stale'])}"])

from dashboard.design.components import colored, data_table  # noqa: E402,F401  (v2: read-only tables follow light/dark; flag off = st.dataframe)
