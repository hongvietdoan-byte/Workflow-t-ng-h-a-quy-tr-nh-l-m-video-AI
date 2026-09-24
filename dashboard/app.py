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


def step_done(p: Pipeline, pid: int) -> list:
    """Per step: (state, short progress) with state 'done' | 'stale' | 'todo' — counted per SCENE, outdated results not counted
    as done (core.lineage)."""
    summ = lineage.summary(p.conn, pid)
    n = summ["total"]
    locked = bool(p.conn.execute("SELECT COUNT(*) FROM characters WHERE project_id=? AND locked=1", (pid,)).fetchone()[0])

    def stage(done_stale):
        done, stale = done_stale
        state = "stale" if stale else ("done" if n and done >= n else "todo")
        return state, (f"{done}/{n}" + (f" ⚠{stale}" if stale else "")) if n else ""   # no scenes yet: no "0/0"

    fin = delivery.status(p, pid, DATA)["final"]
    return [("done" if locked else "todo", f"{n} cảnh" if n else ""), stage(summ["images"]), stage(summ["motion"]),
            stage(summ["videos"]),
            ({"fresh": "done", "stale": "stale", "missing": "todo"}[fin["state"]], {"fresh": "✓", "stale": "cũ", "missing": ""}[fin["state"]]),
            ("todo", "")]


def step_label(done: list):
    marks = {}
    for i, name in enumerate(STEPS):
        state, text = done[i] if i < len(done) else ("todo", "")
        head = {"done": "✓  ", "stale": "⚠  ", "todo": ""}[state]
        marks[name] = head + name + (f" · {text}" if text and state != "done" or (text and i in (1, 2, 3)) else "")
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
    if "asset_files_checked" not in st.session_state:   # A1: library pictures that cannot be read are reported, never skipped silently
        st.session_state["asset_files_checked"] = True
        lost = assets.missing_files(p.conn)
        if lost:
            diag.record(p.conn, "system", "error", f"{len(lost)} ảnh trong Kho tài nguyên không tìm thấy file (ví dụ {lost[0]['asset']}: "
                        f"{lost[0]['path']}) — Director/QC/gen ảnh sẽ thiếu ảnh tham chiếu này", "missing_asset_file")
    if "research_checked" not in st.session_state:      # monthly research, at most once per browser session
        st.session_state["research_checked"] = True
        research.maybe_run_in_background(DB)
    problems = [f for f in diag.scan(p.conn, DATA, float(os.environ.get("AUTOPILOT_POLL_SEC", "15")))
                if f["severity"] == "error" and f.get("project_id") in (None, pid)]
    if problems:
        st.caption(f"🔴 {len(problems)} vấn đề cần xem ở dự án này (ví dụ: {escape(diag.redact(problems[0]['title']))}) — tab “📊 Theo dõi”.")
    deep = st.query_params.get("step")  # ?step=2 opens a step directly (1..5, monitor); 5a/5b and the
    deep = {"5a": "5", "5b": "5"}.get(deep, deep)  # history/lessons/users dialog deep links still work (settings_menu)
    keys = ["1", "2", "3", "4", "5", "monitor"]
    visible = [s for s in STEPS if allowed(STEP_PERMISSION.get(s, "workflow"))]
    if deep in keys and "step" not in st.session_state and STEPS[keys.index(deep)] in visible:
        st.session_state["step"] = STEPS[keys.index(deep)]
    # The stepper's labels carry progress ("2 · Ảnh 3/3", "⚠ cũ"): when one changes Streamlit sees a new widget and would jump
    # back to step 1. Re-assert the current step every run so it survives label changes.
    cur = st.session_state.get("step", st.session_state.get("_step_keep"))
    if cur in visible:
        st.session_state["step"] = cur
    else:
        st.session_state.pop("step", None)
    step = st.radio("Bước", visible, horizontal=True, key="step", label_visibility="collapsed",
                    format_func=step_label(step_done(p, pid)))
    st.session_state["_step_keep"] = step
    {STEPS[0]: step1, STEPS[1]: step2, STEPS[2]: step3, STEPS[3]: step4, STEPS[4]: step5,
     STEPS[5]: monitor}[step](p, pid)


main()
