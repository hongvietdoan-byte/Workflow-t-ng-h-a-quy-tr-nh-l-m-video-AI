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

from core import memo, team  # noqa: E402
from dashboard import common as C  # noqa: E402
from dashboard.common import *  # noqa: E402,F401,F403
from dashboard.admin import monitor  # noqa: E402
from dashboard.header import global_bar, require_login, user_name  # noqa: E402
from dashboard.home import home  # noqa: E402
from dashboard.team_screen import team_screen  # noqa: E402
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
    """Label of each screen on the bar, with its progress. `done` = step_done()'s five old steps; Storyboard joins Ảnh + Motion."""
    def pick(*idx):
        parts = [done[i] if i < len(done) else ("todo", "") for i in idx]
        state = "stale" if any(x[0] == "stale" for x in parts) else ("done" if all(x[0] == "done" for x in parts) else "todo")
        return state, " · ".join(x[1] for x in parts if x[1])

    by_screen = {STEPS[1]: pick(0), STEPS[2]: pick(1, 2), STEPS[3]: pick(3), STEPS[4]: pick(4)}
    marks = {}
    for name in STEPS:
        state, text = by_screen.get(name, ("todo", ""))
        head = {"done": "✓  ", "stale": "⚠  ", "todo": ""}[state]
        shown = "Tất cả dự án" if name == STEPS[0] else name          # the ⌂ is drawn by the bar's CSS
        marks[name] = head + shown + (f" · {text}" if text and (state != "done" or name == STEPS[2]) else "")
    return lambda name: marks[name]


def storyboard(p: Pipeline, pid: int):
    """Storyboard = Ảnh + QC (step 2) and Motion & giọng (step 3) side by side in two tabs — every control of both is still there."""
    t_img, t_mot = st.tabs(list(C.SB_TABS), key="sb_tab", default=st.session_state.get("sb_tab") or C.SB_TABS[0])
    with t_img:
        step2(p, pid)
    with t_mot:
        step3(p, pid)


def shell_header(p: Pipeline, pid: int, done: list, cur) -> None:
    """UI v2: the project hero strip (project screens only — not ⌂ / Nhóm / Theo dõi) followed by the one status line."""
    from dashboard.design.screens import shell_parts
    from dashboard.header import level_bar, status_line
    if cur not in (STEPS[0], STEPS[5], STEPS[6]):
        shell_parts.project_hero(p, pid, done, STEPS.index(cur) if cur in STEPS else 1, DATA, lambda: level_bar(p, pid, compact=True))
    status_line(p, pid)


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
    p.actor = me()["email"] if auth_on() else (user_name() or None)     # the account / name box is in ⚙ (one-line top bar)
    pid = global_bar(p)
    if pid is None:
        return
    C.periodic("purge_trash", lambda: purge_trash(DATA))                # V4 5.3: housekeeping every 60 s, not on every click
    C.periodic(f"sweep_{pid}", lambda: trash.sweep_rejected(p, DATA, pid))
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
    # the problems of this project are in the one status line under the top bar (header.status_line, scanned every 60 s)
    on_project_screen = st.session_state.get("step") not in (STEPS[0], STEPS[5], STEPS[6])
    if auth_on() and on_project_screen:                 # đợt 3: tell others this project is open (🔒 on the all-projects page)
        team.touch(p.conn, pid, me().get("email"))
        creator = (p.project(pid)["created_by"] or "").strip()
        if creator and creator.lower() != (me().get("email") or "").lower() and me().get("role") != "owner":
            st.warning(f"Dự án của {creator}. Bạn mở được để xem; chỉ duyệt / gen khi chủ dự án nhờ — mỗi job ghi tên người gửi.")
    deep = st.query_params.get("step")  # ?step=1..5 / home / team / monitor opens a screen directly (old 1..5 links keep working)
    deep_screen = {"1": 1, "2": 2, "3": 2, "4": 3, "5": 4, "5a": 4, "5b": 4, "home": 0, "team": 5, "monitor": 6}.get(deep)
    visible = [s for s in STEPS if allowed(STEP_PERMISSION.get(s, "workflow"))]
    if deep_screen is not None and "step" not in st.session_state and STEPS[deep_screen] in visible:
        st.session_state["step"] = STEPS[deep_screen]
        if deep == "3":
            st.session_state["sb_tab"] = C.SB_TABS[1]       # the old step 3 (Motion & giọng) is the second tab of Storyboard
    if "step" not in st.session_state and "_step_keep" not in st.session_state and STEPS[1] in visible:
        st.session_state["step"] = STEPS[1]             # a project opens on its script, as before; ⌂ is one click away
    # The bar's labels carry progress ("Storyboard · ảnh 3/3", "⚠ cũ"): when one changes Streamlit sees a new widget and would jump
    # back to the first screen. Re-assert the current screen every run so it survives label changes.
    cur = st.session_state.get("step", st.session_state.get("_step_keep"))
    if cur in visible:
        st.session_state["step"] = cur
    else:
        st.session_state.pop("step", None)
    done = step_done(p, pid)
    if ui.v2_on():                                      # S13 nhánh B: hero of the project + 🎚 level + status line sit between the bar and the stepper
        shell_header(p, pid, done, cur)
    step = st.radio("Màn", visible, horizontal=True, key="step", label_visibility="collapsed", format_func=step_label(done))
    st.session_state["_step_keep"] = step
    if deep == "design" and ui.v2_on():                   # G1 (S13): the real-Streamlit vertical slice of UI v2, for the owner to approve
        from dashboard.design import preview
        preview.render()
        return
    {STEPS[0]: home, STEPS[1]: step1, STEPS[2]: storyboard, STEPS[3]: step4, STEPS[4]: step5,
     STEPS[5]: team_screen, STEPS[6]: monitor}[step](p, pid)


with memo.per_rerun():      # lineage.scan / summary, assets.project_assets: computed once per click and database state
    main()
