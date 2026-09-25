"""The main screen's four cards (kế hoạch V4 5.3 item 6): Kịch bản → Duyệt kế hoạch → Đang sản xuất → Video cuối.

One glance at where the project is, each card opening its step. "Đang sản xuất" shows the progress, the queue, the background score of
shots on a 3D place and the lip-sync count. The step bar stays under the cards for the detailed work.
"""
import json
import os

from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C


def _go(step: str) -> None:
    st.session_state["step"] = step


def _counts(p: Pipeline, pid: int) -> dict:
    conn = p.conn
    shots = conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    story = conn.execute("SELECT COUNT(*) FROM story_scenes WHERE project_id=?", (pid,)).fetchone()[0]
    chars = conn.execute("SELECT COUNT(*), SUM(locked) FROM characters WHERE project_id=?", (pid,)).fetchone()
    done = lambda kind, states: conn.execute(  # noqa: E731
        f"SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type=? AND state IN ({','.join('?' * len(states))})",
        (pid, kind, *states)).fetchone()[0]
    live = conn.execute("SELECT type, COUNT(*) FROM jobs WHERE project_id=? AND state IN ('queued','running') GROUP BY type",
                        (pid,)).fetchall()
    return {"shots": shots, "story": story or shots, "chars": chars[0] or 0, "locked": chars[1] or 0,
            "images": done("image_gen", ("approved",)), "clips": done("video_gen", ("approved", "succeeded")),
            "queue": {r[0]: r[1] for r in live}}


def _plates(pid: int) -> str:
    """Background kept by the video model on 3D-place shots (mode 1) and the lip-synced shots, from their per-project records."""
    bits = []
    try:
        from core import location_pack, lipsync
        qc = location_pack.video_qc(C.DATA, pid)
        scores = [r.get("score") for r in qc.values() if isinstance(r.get("score"), (int, float))]
        if scores:
            bits.append(f"nền giữ {sum(scores) / len(scores):.0%} ({len(scores)} clip)")
        synced = lipsync.synced_scene_ids(C.DATA, pid)
        if synced:
            bits.append(f"khớp môi {len(synced)} shot")
    except Exception:  # noqa: BLE001 - a missing record must not break the main screen
        pass
    return " · ".join(bits)


def _final(pid_dir: str, p: Pipeline, pid: int) -> tuple:
    row = p.conn.execute("SELECT kind, path, manifest FROM outputs WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    if not row or not os.path.exists(row["path"] or ""):
        return "chưa dựng", ""
    try:
        man = json.loads(row["manifest"] or "{}")
    except ValueError:
        man = {}
    loud = man.get("loudness") or {}
    extra = f"{loud['lufs']:g} LUFS" if loud.get("lufs") is not None else ""
    return f"có bản {row['kind']}", extra


def cards(p: Pipeline, pid: int, steps) -> None:
    c = _counts(p, pid)
    ap = autopilot.status(p, pid)
    final, final_extra = _final("", p, pid)
    items = [
        ("📜 Kịch bản", f"{c['story']} cảnh" + (f" → {c['shots']} shot" if c["shots"] != c["story"] else ""), "", steps[0]),
        ("🧭 Duyệt kế hoạch", f"{c['locked']}/{c['chars']} nhân vật đã khóa" if c["chars"] else "chưa chạy Director", "", steps[0]),
        ("🏭 Đang sản xuất", f"ảnh {c['images']}/{c['shots']} · clip {c['clips']}/{c['shots']}",
         " · ".join(x for x in [
             (f"hàng đợi: {c['queue'].get('image_gen', 0)} ảnh, {c['queue'].get('video_gen', 0)} clip" if c["queue"] else ""),
             (f"🚀 {ap['note']}" if ap["state"] in ("running", "queued", "waiting") and ap["note"] else ""), _plates(pid)] if x),
         steps[3]),
        ("🎬 Video cuối", final, final_extra, steps[4]),
    ]
    cols = st.columns(4)
    for i, (col, (title, main, extra, step)) in enumerate(zip(cols, items)):
        with col.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(main + (f"  \n{extra}" if extra else ""))
            st.button("Mở →", key=f"ov_{i}_{pid}", on_click=_go, args=(step,), width="stretch")
