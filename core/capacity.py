"""System limits, measured (kế hoạch V4 6.3) — from the real job history in the database, never guessed.

    config()                     the limits as set in code / env (exact numbers)
    measured(conn)               per job kind + model: time waiting before the provider took it, time running, per clip second (video),
                                 failure rate, the highest number running at once, the highest reached with no rate-limit hit
    queue(conn)                  jobs waiting / running right now
    estimate(conn, seconds)      "a video of X s ≈ Y minutes of video generation", from the measures (or "chưa đủ dữ liệu")

Every number carries its sample size `n`, the last day it was measured and a confidence (n < 10 thấp, < 30 trung bình, else cao).
Times come from job_events (queued → running → succeeded / failed): a job's own moments, not the row's update time.
  wait  = queued → sent: the time a job waits INSIDE the pipeline (approval gates, the previous shot's picture, the throttle)
  run   = sent → finished: the provider's queue + generation (multi-shot followers and re-linked tasks are left out)
"""
import math
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Sequence

KINDS = {"image_gen": "Ảnh", "video_gen": "Video"}
RATE_LIMIT = re.compile(r"1130|rate[- ]?limit|429|too many", re.I)
MIN_SAMPLES = 3
MIN_REAL_VIDEO_S = 20       # a video "run" shorter than this was a multi-shot follower or a re-linked task, not a generation
SHOT_SECONDS = 2.0          # a Free Fire shot is ~2 s (ff_directing.md, 519 shots) — the estimate's default when the project has none


def _t(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def confidence(n: int) -> str:
    return "thấp" if n < 10 else "trung bình" if n < 30 else "cao"


def _pct(values: Sequence[float], q: float) -> Optional[float]:
    vals = sorted(values)
    if not vals:
        return None
    k = (len(vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 1)


def config() -> Dict:
    from . import autopilot, perf, throttle
    t = throttle.THROTTLE
    return {
        "autopilot_parallel": int(os.environ.get("AUTOPILOT_MAX_PARALLEL", "2")),
        "per_project_running": 5,
        "throttle_start": t.start, "throttle_max": t.maximum, "throttle_up_every": t.up_every,
        "provider_caps": {k: t.cap(k) or None for k in KINDS},
        "autopilot_max_scenes": autopilot.MAX_SCENES,
        "learned": {k: t.limit(k) for k in KINDS},
    }


def _jobs(conn, kind: str) -> List[Dict]:
    """Each finished job of a kind: model, created / started / ended times (seconds), outcome, clip seconds, rate-limited."""
    rows = conn.execute("SELECT j.id, j.model, j.state, j.created_at, j.retry_reason, j.group_leader, m.duration_sec FROM jobs j "
                        "LEFT JOIN motion_prompts m ON m.scene_id=j.scene_id WHERE j.type=?", (kind,)).fetchall()
    events: Dict[int, List] = {}
    for e in conn.execute("SELECT je.job_id, je.to_state, je.note, je.at FROM job_events je JOIN jobs j ON j.id=je.job_id WHERE j.type=? "
                          "ORDER BY je.id", (kind,)):
        events.setdefault(e["job_id"], []).append(e)
    out = []
    for r in rows:
        ev = events.get(r["id"], [])
        start = next((_t(e["at"]) for e in ev if e["to_state"] in ("submitted", "running")), None)
        end = next((_t(e["at"]) for e in ev if e["to_state"] in ("succeeded", "failed")), None)
        outcome = next((e["to_state"] for e in ev if e["to_state"] in ("succeeded", "failed")), None)
        limited = bool(RATE_LIMIT.search(str(r["retry_reason"] or ""))) or any(RATE_LIMIT.search(str(e["note"] or "")) for e in ev)
        follower = r["group_leader"] is not None and r["group_leader"] != r["id"]
        quick = kind == "video_gen" and start and end and end - start < MIN_REAL_VIDEO_S
        out.append({"id": r["id"], "model": r["model"] or "(không ghi model)", "created": _t(r["created_at"]), "start": start, "end": end,
                    "outcome": outcome, "clip_s": r["duration_sec"], "limited": limited, "not_a_run": bool(follower or quick),
                    "day": (ev[-1]["at"][:10] if ev else str(r["created_at"] or "")[:10])})
    return out


def peak_running(jobs: List[Dict]) -> Dict:
    """The most jobs running at the same moment, and the most reached while no job of that moment was rate-limited."""
    marks = []
    for j in jobs:
        if j["start"] and j["end"] and j["end"] >= j["start"]:
            marks += [(j["start"], 1, j), (j["end"], -1, j)]
    marks.sort(key=lambda m: (m[0], m[1]))
    now, peak, peak_ok, live = 0, 0, 0, set()
    for _, step, j in marks:
        if step > 0:
            live.add(j["id"])
            now += 1
            peak = max(peak, now)
            if not any(x["limited"] for x in jobs if x["id"] in live):
                peak_ok = max(peak_ok, now)
        else:
            live.discard(j["id"])
            now -= 1
    return {"peak": peak, "peak_without_rate_limit": peak_ok}


def measured(conn) -> Dict:
    out = {}
    for kind in KINDS:
        jobs = _jobs(conn, kind)
        done = [j for j in jobs if j["outcome"]]
        by_model: Dict[str, List[Dict]] = {}
        for j in done:
            by_model.setdefault(j["model"], []).append(j)
        models = {}
        for model, js in sorted(by_model.items()):
            wait = [j["start"] - j["created"] for j in js if j["start"] and j["created"] and j["start"] >= j["created"]]
            real = [j for j in js if j["start"] and j["end"] and j["outcome"] == "succeeded" and not j["not_a_run"]]
            run = [j["end"] - j["start"] for j in real]
            per_s = [(j["end"] - j["start"]) / j["clip_s"] for j in real if (j["clip_s"] or 0) > 0]
            n = len(js)
            models[model] = {"n": n, "confidence": confidence(n), "last_day": max((j["day"] for j in js), default=None),
                             "wait_s": {"median": _pct(wait, 0.5), "p90": _pct(wait, 0.9), "n": len(wait)},
                             "run_s": {"median": _pct(run, 0.5), "p90": _pct(run, 0.9), "n": len(run)},
                             "run_per_clip_s": {"median": _pct(per_s, 0.5), "n": len(per_s)},
                             "fail_rate": round(sum(j["outcome"] == "failed" for j in js) / n, 3) if n else None,
                             "rate_limited": sum(j["limited"] for j in js),
                             "not_a_run": sum(j["not_a_run"] for j in js)}   # group followers / re-linked tasks: no generation time
        out[kind] = {"models": models, **peak_running(jobs), "n": len(done)}
    return out


def queue(conn) -> Dict:
    rows = conn.execute("SELECT type, state, count(*) n FROM jobs WHERE state IN ('queued','submitted','running') GROUP BY type, state")
    q: Dict = {k: {"queued": 0, "running": 0} for k in KINDS}
    for r in rows:
        if r["type"] in q:
            q[r["type"]]["queued" if r["state"] == "queued" else "running"] += r["n"]
    return q


def estimate(conn, seconds: float, shot_s: float = SHOT_SECONDS, model: Optional[str] = None, m: Optional[Dict] = None) -> Dict:
    """Minutes of video generation for a film of `seconds`: its shots in waves of the video concurrency (the provider cap, else the
    peak measured without a rate-limit hit), each wave taking the model's median run (the busiest model when not given)."""
    m = m or measured(conn)
    video = m["video_gen"]
    models = video["models"]
    name = model if model in models else max(models, key=lambda k: models[k]["n"], default=None)
    if name is None or models[name]["run_s"]["n"] < MIN_SAMPLES:
        return {"minutes": None, "note": "chưa đủ dữ liệu (cần ≥ 3 clip xong của một model)", "model": name}
    info = models[name]
    conc = config()["provider_caps"].get("video_gen") or video["peak_without_rate_limit"] or 1
    clips = max(1, math.ceil(seconds / shot_s))
    per_wave = info["run_s"]["median"]                  # the provider's time; waiting at approval gates depends on the person
    slow = info["run_s"]["p90"] or per_wave
    waves = math.ceil(clips / conc)
    return {"minutes": round(waves * per_wave / 60, 1), "minutes_p90": round(waves * slow / 60, 1), "clips": clips, "concurrency": conc,
            "model": name, "n": info["run_s"]["n"], "confidence": confidence(info["run_s"]["n"]),
            "note": f"{clips} clip ÷ {conc} cùng lúc = {waves} đợt × {per_wave:.0f} s (trung vị chạy thật) — chưa tính gen lại, chờ duyệt"}
