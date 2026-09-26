"""📦 Cất dự án (người dùng chốt 2026-09-26): old projects are put away while the pipeline is finished, then a new trial project is
run. An archived project is hidden from the project picker and never picked up by the automatic run; NOTHING is deleted (scenes,
jobs, pictures, clips, spending all stay) and it can be restored at any time from ⚙ → "Dự án đã cất".

Archiving also pauses the project (no queued picture/clip is sent) and stops its automatic run; restoring keeps it paused, so
nothing is sent by surprise — the person presses ▶ Tiếp tục when they want to work on it again.
"""
from typing import List

from .pipeline import Pipeline

ACTIVE_AUTOPILOT = ("running", "queued", "waiting", "needs_attention")


def is_archived(row) -> bool:
    return bool(row is not None and "archived" in row.keys() and row["archived"])


def active_projects(conn) -> List:
    """(id, name) of the projects in use, oldest first — the project picker."""
    return conn.execute("SELECT id, name FROM projects WHERE COALESCE(archived, 0)=0 ORDER BY id").fetchall()


def archived_projects(conn) -> List:
    return conn.execute("SELECT id, name, created_at FROM projects WHERE COALESCE(archived, 0)=1 ORDER BY id").fetchall()


def archive(p: Pipeline, project_id: int) -> None:
    from . import autopilot
    row = p.project(project_id)
    if row["autopilot_state"] in ACTIVE_AUTOPILOT:
        autopilot.stop(p, project_id, "Dự án đã cất (📦) — chạy tự động dừng")
    p.set_paused(project_id, True)
    p.conn.execute("UPDATE projects SET archived=1 WHERE id=?", (project_id,))
    p.conn.commit()


def restore(p: Pipeline, project_id: int) -> None:
    """Back in the picker, still paused (see the module note)."""
    p.conn.execute("UPDATE projects SET archived=0 WHERE id=?", (project_id,))
    p.conn.commit()
