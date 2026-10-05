"""Load and performance figures for the pipeline (read-only queries over the database).

Answers "is the system overloaded?": how many provider jobs run right now, how long they take, how often they fail,
whether they are getting slower, how many projects wait in the queue and how close the daily job cap is.
"""
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

KINDS = (("image_gen", "Gen ảnh (Deepix)"), ("video_gen", "Gen video (Clip AI)"))
MAX_ACTIVE = int(os.environ.get("PERF_MAX_ACTIVE", "8"))       # provider jobs in flight before we warn
FAIL_WARN = float(os.environ.get("PERF_FAIL_WARN", "0.3"))       # share of failed outcomes among the last 20
SLOW_WARN = float(os.environ.get("PERF_SLOW_WARN", "2.0"))       # recent average vs earlier average


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _midnight() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _sql_midnight() -> str:
    """Today 00:00 UTC in the format of usage_events.at (SQLite datetime('now'): 'YYYY-MM-DD HH:MM:SS' — an ISO 'T…+00:00' string
    sorts AFTER every row of the day)."""
    return _midnight().strftime("%Y-%m-%d %H:%M:%S")


def sends_today(conn) -> int:
    """Paid picture + clip sends since 00:00 UTC, by anyone (button, automatic run, any project): the ledger rows (usage_events) of
    kind image/video whose provider is not simulated (mock*). Shown on 📊 (S14.18: the machine-wide daily cap that counted it is gone)."""
    return conn.execute("SELECT COUNT(*) FROM usage_events WHERE kind IN ('image','video') AND provider NOT LIKE 'mock%' AND at>=?",
                        (_sql_midnight(),)).fetchone()[0]


def jobs_today(conn) -> int:
    """Image + video jobs created since 00:00 UTC, by anyone (autopilot or manual) — shown only."""
    return conn.execute("SELECT COUNT(*) c FROM jobs WHERE type IN ('image_gen','video_gen') AND created_at>=?",
                        (_iso(_midnight()),)).fetchone()["c"]


def _durations(conn, kind: str, since: str, limit: int = 200) -> List[float]:
    rows = conn.execute(
        "SELECT (julianday(s.at) - julianday((SELECT MIN(r.at) FROM job_events r WHERE r.job_id=s.job_id AND r.to_state='running')))"
        " * 86400 AS sec FROM job_events s JOIN jobs j ON j.id=s.job_id WHERE s.to_state='succeeded' AND j.type=? AND s.at>=?"
        " ORDER BY s.id DESC LIMIT ?", (kind, since, limit)).fetchall()
    return [r["sec"] for r in rows if r["sec"] is not None and r["sec"] >= 0]


def _avg(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def by_kind(conn, kind: str, now: Optional[datetime] = None) -> Dict:
    now = now or datetime.now(timezone.utc)
    hour, day = _iso(now - timedelta(hours=1)), _iso(now - timedelta(hours=24))

    def count(sql: str, *args) -> int:
        return conn.execute(sql, args).fetchone()["c"]

    def live(states: str) -> int:
        return count("SELECT COUNT(*) c FROM jobs WHERE type=? AND state IN (%s)" % states, kind)

    def events(state: str, since: str) -> int:
        return count("SELECT COUNT(*) c FROM job_events e JOIN jobs j ON j.id=e.job_id"
                     " WHERE j.type=? AND e.to_state=? AND e.at>=?", kind, state, since)

    durations = _durations(conn, kind, day)          # newest first
    recent, earlier = durations[:5], durations[5:25]
    last = conn.execute("SELECT e.to_state s FROM job_events e JOIN jobs j ON j.id=e.job_id WHERE j.type=? AND e.to_state IN"
                        " ('succeeded','failed') ORDER BY e.id DESC LIMIT 20", (kind,)).fetchall()
    last_fail = sum(1 for r in last if r["s"] == "failed")
    return {"kind": kind, "running": live("'running'"), "queued": live("'queued','retryable'"),
            "ok_1h": events("succeeded", hour), "failed_1h": events("failed", hour),
            "ok_24h": events("succeeded", day), "failed_24h": events("failed", day),
            "avg_sec": _avg(durations), "recent_sec": _avg(recent), "earlier_sec": _avg(earlier),
            "recent_fail_rate": (last_fail / len(last)) if last else 0.0, "recent_outcomes": len(last)}


STEP_LABELS = ("① Kịch bản", "② Gen ảnh", "③ Video Prompt", "④ Gen video", "⑤ Ghép & render", "✅ Hoàn tất")


def _progress(conn, pid: int):
    """(scenes, approved pictures, approved motion prompts, finished clips) of one project."""
    def c(sql: str) -> int:
        return conn.execute(sql, (pid,)).fetchone()[0]
    return (c("SELECT COUNT(*) FROM scenes WHERE project_id=?"),
            c("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved'"),
            c("SELECT COUNT(DISTINCT s.id) FROM scenes s JOIN motion_prompts mp ON mp.scene_id=s.id WHERE s.project_id=? AND mp.state='approved'"),
            c("SELECT COUNT(DISTINCT scene_id) FROM jobs WHERE project_id=? AND type='video_gen' AND state='succeeded'"))


def _step(done: bool, scenes: int, images: int, motion: int, videos: int) -> int:
    if done:
        return 5
    if not scenes:
        return 0
    if images < scenes:
        return 1
    if motion < scenes:
        return 2
    if videos < scenes:
        return 3
    return 4


def step_label(conn, pid: int, done: bool = False) -> str:
    """Where a project is (the ⌂ list's step), from the database only — S14.18 lists the person's unfinished projects with it."""
    return STEP_LABELS[_step(done, *_progress(conn, pid))]


def portfolio_rows(conn, data_dir: str) -> List[Dict]:
    """Every project (auto or step-by-step, running or idle) with its current step and final output, so a
    portfolio of many projects (e.g. 10 auto, or 3 semi-auto + 7 auto) can be tracked from one table.
    `done` = has the final cut (the step "✅ Hoàn tất" of the progress bar); `delivered` = the delivery was exported (S14.30: "Xong")."""
    from . import delivered
    out = []
    for r in conn.execute("SELECT id, name, operating_mode, autopilot_state, autopilot_note, paused, created_by"
                          " FROM projects ORDER BY id DESC").fetchall():
        def c(sql: str) -> int:
            return conn.execute(sql, (r["id"],)).fetchone()["c"]

        scenes, images, motion, videos = _progress(conn, r["id"])
        active = c("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND state IN ('queued','running','retryable')")
        needs_review = c("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND state='pending_review'")
        final_video = os.path.join(data_dir, str(r["id"]), "output", "FINAL_VIDEO.mp4")
        done = os.path.exists(final_video)
        step = _step(done, scenes, images, motion, videos)
        out.append({"id": r["id"], "name": r["name"], "operating_mode": r["operating_mode"],
                    "running_auto": bool(r["autopilot_state"] and r["autopilot_state"] not in ("done", "stopped", "error")),
                    "autopilot_state": r["autopilot_state"], "autopilot_note": r["autopilot_note"] or "",
                    "paused": bool(r["paused"]), "created_by": r["created_by"] or "",
                    "scenes": scenes, "images": images, "motion": motion, "videos": videos,
                    "active": active, "needs_review": needs_review, "step": step, "step_label": STEP_LABELS[step],
                    "done": done, "final_video": final_video if done else None,
                    "delivered": delivered.is_delivered(conn, r["id"])})   # S14.30: "hoàn thiện" = đã xuất bản giao
    return out


def project_rows(conn) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT id, name, autopilot_state, autopilot_note, autopilot_beat FROM projects"
                          " WHERE autopilot_state IS NOT NULL ORDER BY id DESC").fetchall():
        def c(sql: str) -> int:
            return conn.execute(sql, (r["id"],)).fetchone()["c"]

        out.append({"id": r["id"], "name": r["name"], "state": r["autopilot_state"], "note": r["autopilot_note"] or "",
                    "scenes": c("SELECT COUNT(*) c FROM scenes WHERE project_id=?"),
                    "images": c("SELECT COUNT(DISTINCT scene_id) c FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved'"),
                    "videos": c("SELECT COUNT(DISTINCT scene_id) c FROM jobs WHERE project_id=? AND type='video_gen' AND state='succeeded'"),
                    "active": c("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND state IN ('queued','running','retryable')"),
                    "idle_sec": None if not r["autopilot_beat"] else max(0, time.time() - r["autopilot_beat"])})
    return out


NO_NAME = "(chưa nhập tên)"


def by_user(conn, days: Optional[float] = None) -> List[Dict]:
    """Per person: videos/images sent to the providers by them (dashboard clicks and the automatic runs they started)."""
    since = _iso(datetime.now(timezone.utc) - timedelta(days=days)) if days else "0000"
    rows = conn.execute(
        "SELECT COALESCE(NULLIF(TRIM(created_by), ''), ?) AS who,"
        " SUM(type='video_gen') AS videos, SUM(type='video_gen' AND state IN ('succeeded','pending_review','approved')) AS videos_ok,"
        " SUM(type='video_gen' AND state='failed') AS videos_failed,"
        " SUM(type='video_gen' AND parent_job_id IS NOT NULL) AS videos_retry,"
        " SUM(type='image_gen') AS images, MAX(created_at) AS last_at, COUNT(DISTINCT project_id) AS projects"
        " FROM jobs WHERE type IN ('image_gen','video_gen') AND created_at>=? GROUP BY who ORDER BY videos DESC, images DESC",
        (NO_NAME, since)).fetchall()
    out = []
    for r in rows:
        seconds = conn.execute(
            "SELECT COALESCE(SUM(u.quantity), 0) FROM usage_events u JOIN jobs j ON j.id=u.job_id WHERE u.kind='video'"
            " AND u.unit='second' AND j.created_at>=? AND COALESCE(NULLIF(TRIM(j.created_by), ''), ?)=?",
            (since, NO_NAME, r["who"])).fetchone()[0]
        out.append({"who": r["who"], "videos": r["videos"] or 0, "videos_ok": r["videos_ok"] or 0,
                    "videos_failed": r["videos_failed"] or 0, "videos_retry": r["videos_retry"] or 0,
                    "images": r["images"] or 0, "seconds": seconds, "projects": r["projects"], "last_at": r["last_at"]})
    return out


def alerts(kinds: List[Dict], queued_projects: int, running_projects: int, max_parallel: int) -> List[str]:
    out = []
    labels = dict(KINDS)
    active = sum(k["running"] + k["queued"] for k in kinds)
    if active > MAX_ACTIVE:
        out.append(f"Đang có {active} job chờ/chạy cùng lúc (ngưỡng {MAX_ACTIVE}): dễ bị nhà cung cấp giới hạn tốc độ.")
    for k in kinds:
        label = labels[k["kind"]]
        if k["recent_outcomes"] >= 5 and k["recent_fail_rate"] >= FAIL_WARN:
            out.append(f"{label}: {k['recent_fail_rate']:.0%} trong {k['recent_outcomes']} kết quả gần nhất bị lỗi — "
                       "nên giảm số dự án chạy song song.")
        if k["recent_sec"] and k["earlier_sec"] and k["recent_sec"] >= SLOW_WARN * k["earlier_sec"]:
            out.append(f"{label}: đang chậm dần (gần đây {k['recent_sec']:.0f}s so với {k['earlier_sec']:.0f}s trước đó) — có thể quá tải.")
    if queued_projects:
        out.append(f"{queued_projects} dự án đang xếp hàng (đang chạy {running_projects}/{max_parallel}).")
    return out


def snapshot(conn, queued_projects: int = 0, running_projects: int = 0, max_parallel: int = 0) -> Dict:
    kinds = [by_kind(conn, k) for k, _ in KINDS]
    today, sends = jobs_today(conn), sends_today(conn)
    units = conn.execute("SELECT kind, unit, SUM(quantity) q FROM usage_events WHERE at>=? GROUP BY kind, unit",
                         (_sql_midnight(),)).fetchall()
    from .throttle import THROTTLE
    learned = {k: THROTTLE.info(k) for k, _ in KINDS}
    return {"kinds": kinds, "learned": learned, "projects": project_rows(conn), "jobs_today": today, "sends_today": sends,
            "usage_today": [(u["kind"], u["unit"], u["q"]) for u in units],
            "alerts": alerts(kinds, queued_projects, running_projects, max_parallel)}
