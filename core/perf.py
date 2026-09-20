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


def daily_limit() -> int:
    return int(os.environ.get("AUTOPILOT_DAILY_JOBS", "300"))


def jobs_today(conn) -> int:
    """Image + video jobs created since 00:00 UTC, by anyone (autopilot or manual)."""
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


def alerts(kinds: List[Dict], today: int, limit: int, queued_projects: int, running_projects: int, max_parallel: int) -> List[str]:
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
    if limit and today >= 0.8 * limit:
        out.append(f"Đã tạo {today}/{limit} job hôm nay — gần chạm trần ngày (các dự án tự động sẽ dừng khi chạm).")
    if queued_projects:
        out.append(f"{queued_projects} dự án đang xếp hàng (đang chạy {running_projects}/{max_parallel}).")
    return out


def snapshot(conn, queued_projects: int = 0, running_projects: int = 0, max_parallel: int = 0) -> Dict:
    kinds = [by_kind(conn, k) for k, _ in KINDS]
    today, limit = jobs_today(conn), daily_limit()
    units = conn.execute("SELECT kind, unit, SUM(quantity) q FROM usage_events WHERE at>=? GROUP BY kind, unit",
                         (_iso(_midnight()),)).fetchall()
    from .throttle import THROTTLE
    learned = {k: THROTTLE.info(k) for k, _ in KINDS}
    return {"kinds": kinds, "learned": learned, "projects": project_rows(conn), "jobs_today": today, "daily_limit": limit,
            "usage_today": [(u["kind"], u["unit"], u["q"]) for u in units],
            "alerts": alerts(kinds, today, limit, queued_projects, running_projects, max_parallel)}
