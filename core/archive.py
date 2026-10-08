"""📦 Cất dự án (người dùng chốt 2026-09-26): old projects are put away while the pipeline is finished, then a new trial project is
run. An archived project is hidden from the project picker and never picked up by the automatic run; NOTHING is deleted (scenes,
jobs, pictures, clips, spending all stay) and it can be restored at any time from ⚙ → "Dự án đã cất".

Archiving also pauses the project (no queued picture/clip is sent) and stops its automatic run; restoring keeps it paused, so
nothing is sent by surprise — the person presses ▶ Tiếp tục when they want to work on it again.
"""
from . import access
from typing import List

from .pipeline import Pipeline

ACTIVE_AUTOPILOT = ("running", "queued", "waiting", "needs_attention")


def is_archived(row) -> bool:
    return bool(row is not None and "archived" in row.keys() and row["archived"])


def active_projects(conn, user=None) -> List:
    """(id, name) of the projects in use, oldest first — the project picker. `user` (core/access.py): only what that person may view
    (None = everything: the Owner, the system, sign-in off)."""
    rows = conn.execute("SELECT id, name FROM projects WHERE COALESCE(archived, 0)=0 ORDER BY id").fetchall()
    return access.filter_rows(conn, rows, user)


def archived_projects(conn, user=None) -> List:
    rows = conn.execute("SELECT id, name, created_at FROM projects WHERE COALESCE(archived, 0)=1 ORDER BY id").fetchall()
    return access.filter_rows(conn, rows, user)


def finished_projects(conn, user=None) -> List:
    """S14.18 "Kho dự án đã xong": put-away projects whose delivery was EXPORTED (S14.30 core/delivered) — kept to look things up, never limited."""
    from .person_limits import is_finished
    return [r for r in archived_projects(conn, user) if is_finished(conn, r["id"])]


def parked_projects(conn, user=None) -> List:
    """S14.18: put-away projects NOT finished (a person keeps at most `parked` of them, core/person_limits)."""
    from .person_limits import is_finished
    return [r for r in archived_projects(conn, user) if not is_finished(conn, r["id"])]


def _move(p: Pipeline, put_away=None, bring_back=None, approval=None) -> None:
    """Rà 05/10: the 📦 flags (+ pause of the one put away) and the approval used change in ONE transaction — a failure half way leaves
    everything as it was. The automatic run of the project put away is stopped after the commit (its own writes)."""
    from . import autopilot, person_limits
    stop = put_away is not None and p.project(put_away)["autopilot_state"] in ACTIVE_AUTOPILOT
    try:
        if put_away is not None:
            p.conn.execute("UPDATE projects SET archived=1, paused=1 WHERE id=?", (put_away,))   # paused: nothing queued is sent
        if bring_back is not None:
            p.conn.execute("UPDATE projects SET archived=0 WHERE id=?", (bring_back,))
        if approval is not None:
            person_limits._use(p.conn, approval, put_away)
        p.conn.commit()
    except Exception:
        p.conn.rollback()
        raise
    person_limits.audit_use(p.conn, approval, put_away)
    if put_away is not None:                      # 08/10 phương án 1: phần trích riêng chưa dùng trả về hàng chung khi cất
        from . import project_reserve
        project_reserve.release_quietly(p.conn, put_away, p.actor, "cất dự án (📦)")
    if stop:
        autopilot.stop(p, put_away, "Dự án đã cất (📦) — chạy tự động dừng")


def archive(p: Pipeline, project_id: int) -> None:
    """S14.18: an unfinished project counts against the person's 📦 limit (core/person_limits.check_archive raises LimitReached with
    the numbers and the choices); a finished one goes to the "Kho dự án đã xong", unlimited."""
    access.need_manage(p, project_id, "cất dự án")
    from . import person_limits
    with person_limits.LOCK:
        approval = person_limits.check_archive(p.conn, p.user, project_id)
        _move(p, put_away=project_id, approval=approval)


def restore(p: Pipeline, project_id: int) -> None:
    """Back in the picker, still paused (see the module note). S14.18: an unfinished project takes one of the person's 'open' places."""
    access.need_manage(p, project_id, "khôi phục dự án")
    from . import person_limits
    with person_limits.LOCK:
        person_limits.check_restore(p.conn, p.user, project_id)
        _move(p, bring_back=project_id)


def swap(p: Pipeline, put_away: int, bring_back: int) -> None:
    """S14.18 GIỮ / BỎ in one move: put `put_away` away and bring `bring_back` back, the limits counted after the move (never 3
    unfinished open nor 2 unfinished put away in between) — one transaction (_move)."""
    access.need_manage(p, put_away, "cất dự án")
    access.need_manage(p, bring_back, "khôi phục dự án")
    from . import person_limits
    with person_limits.LOCK:
        approval = person_limits.check_archive(p.conn, p.user, put_away, bringing_back=bring_back)
        person_limits.check_restore(p.conn, p.user, bring_back, putting_away=put_away)
        _move(p, put_away=put_away, bring_back=bring_back, approval=approval)
