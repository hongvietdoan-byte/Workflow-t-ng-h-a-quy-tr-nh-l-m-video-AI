"""Unified control dashboard (V2): one tool, stepper by step order, per-step control buttons.

Run:  py -m streamlit run dashboard/app.py
The steps live in dashboard/steps/, shared helpers in dashboard/common.py, header in dashboard/header.py,
settings / monitoring panels in dashboard/admin.py.
"""
import os
import subprocess
import sys
import threading

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dashboard import common as C  # noqa: E402
from dashboard.common import *  # noqa: E402,F401,F403
from dashboard.admin import monitor  # noqa: E402
from dashboard.header import account_bar, global_bar, require_login, user_bar  # noqa: E402
from dashboard.steps.step1 import step1  # noqa: E402
from dashboard.steps.step2 import step2  # noqa: E402
from dashboard.steps.step3 import step3  # noqa: E402
from dashboard.steps.step4 import step4  # noqa: E402
from dashboard.steps.step5 import step5  # noqa: E402

DB = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))

DATA = os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))

C.configure(DB, DATA)


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
