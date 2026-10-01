"""Is the workflow actually effective? Five figures per project, read from what the pipeline already records (no extra logging):

  1. time per second of finished video   - wall clock (project start -> last video done) and generation time (jobs running)
  2. cost per second of finished video   - declared prices x recorded submissions (core.cost.spend_summary)
  3. first-pass rate                     - share of scenes whose picture / clip was accepted on the first try, and tries per scene
  4. QC agent vs person agreement        - pictures both the QC agent scored and a person decided on
  5. manual touches per scene            - approve / reject / cancel clicks made by a person

A figure is None when there is not enough data yet (the page says so instead of showing a misleading 0).
"""
from datetime import datetime
from typing import Dict, List, Optional

from .cost import spend_summary

OK_STATES = {"image_gen": ("approved",), "video_gen": ("succeeded", "approved")}


def _t(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _finished_video_seconds(conn, project_id: int) -> float:
    """Seconds of video of every scene that has a finished clip (its motion prompt's duration)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(m.duration_sec), 0) FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id WHERE s.project_id=?"
        " AND EXISTS (SELECT 1 FROM jobs j WHERE j.scene_id=s.id AND j.type='video_gen' AND j.state IN ('succeeded','approved'))",
        (project_id,)).fetchone()
    return float(row[0] or 0)


def _times(conn, project_id: int) -> Dict:
    start = _t(conn.execute("SELECT created_at FROM projects WHERE id=?", (project_id,)).fetchone()["created_at"])
    last_done = _t(conn.execute(
        "SELECT MAX(e.at) FROM job_events e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=? AND j.type='video_gen'"
        " AND e.to_state='succeeded'", (project_id,)).fetchone()[0])
    running = 0.0
    rows = conn.execute(
        "SELECT e.job_id, e.to_state, e.at FROM job_events e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=?"
        " AND j.type IN ('image_gen','video_gen') ORDER BY e.job_id, e.id", (project_id,)).fetchall()
    began: Dict[int, datetime] = {}
    for r in rows:
        at = _t(r["at"])
        if r["to_state"] == "running" and at:
            began[r["job_id"]] = at
        elif r["job_id"] in began and at and r["to_state"] in ("succeeded", "failed", "cancelled"):
            running += (at - began.pop(r["job_id"])).total_seconds()
    wall = (last_done - start).total_seconds() if start and last_done and last_done >= start else None
    return {"wall_min": wall / 60 if wall is not None else None, "gen_min": running / 60}


def _first_pass(conn, project_id: int, job_type: str) -> Dict:
    ok = OK_STATES[job_type]
    scenes = conn.execute(
        "SELECT s.id, (SELECT COUNT(*) FROM jobs j WHERE j.scene_id=s.id AND j.type=?) AS tries,"
        f" (SELECT MIN(j.retry_count) FROM jobs j WHERE j.scene_id=s.id AND j.type=? AND j.state IN ({','.join('?' * len(ok))})) AS best"
        " FROM scenes s WHERE s.project_id=?", (job_type, job_type, *ok, project_id)).fetchall()
    done = [s for s in scenes if s["best"] is not None]
    if not done:
        return {"scenes": 0, "first_pass": None, "tries_per_scene": None}
    return {"scenes": len(done), "first_pass": sum(1 for s in done if s["best"] == 0 and s["tries"] == 1) / len(done),
            "tries_per_scene": sum(s["tries"] for s in done) / len(done)}


def _agreement(conn, project_id: int) -> Dict:
    """QC agent verdict (mean score >= the threshold of the time) vs the person's decision, on pictures that have both."""
    rows = conn.execute(
        "SELECT j.id, AVG(q.score) AS score, MAX(q.threshold_at_time) AS threshold,"
        " (SELECT r.decision FROM review_log r WHERE r.job_id=j.id AND r.reviewer_type='user' AND COALESCE(r.note, '') NOT LIKE '[thử tự động]%' ORDER BY r.id DESC LIMIT 1) AS person"
        " FROM jobs j JOIN qc_results q ON q.job_id=j.id WHERE j.project_id=? AND j.type='image_gen' GROUP BY j.id",
        (project_id,)).fetchall()
    both = [r for r in rows if r["person"]]
    if not both:
        return {"pairs": 0, "agreement": None, "ai_too_strict": 0, "ai_too_lenient": 0}
    ai_pass = [(r["score"] >= r["threshold"], r["person"] == "approve") for r in both]
    return {"pairs": len(both), "agreement": sum(1 for a, b in ai_pass if a == b) / len(both),
            "ai_too_strict": sum(1 for a, b in ai_pass if not a and b), "ai_too_lenient": sum(1 for a, b in ai_pass if a and not b)}


TRUST_PAIRS = 50          # W8 (kế hoạch tổng): the storyboard checkpoint may be skipped only after >= 50 pictures ...
TRUST_AGREEMENT = 0.90    # ... of the same look pack where the QC agent agreed with the person at least 90% of the time ...
TRUST_LENIENT = 0.02      # ... and passed at most 2% of the pictures the person rejected (lenient mistakes cost video money)
TRUST_MIN_REJECTED = 5    # 01/10 B2: ... among at least this many rejected pictures (with none the rate means nothing)


def look_trust(conn, look: Optional[str], image_model: Optional[str]) -> Dict:
    """W8: agreement of the QC agent with the person on every picture of the same look + picture model (all projects).
    {"pairs", "agreement", "lenient_rate", "trusted"}; `trusted` = the storyboard checkpoint can be skipped for a clean storyboard
    (only when the feature `storyboard_auto_trust` is on — it waits for its real test)."""
    rows = conn.execute(
        "SELECT j.id, AVG(q.score) AS score, MAX(q.threshold_at_time) AS threshold,"
        " (SELECT r.decision FROM review_log r WHERE r.job_id=j.id AND r.reviewer_type='user' AND COALESCE(r.note, '') NOT LIKE '[thử tự động]%' ORDER BY r.id DESC LIMIT 1) AS person"
        " FROM jobs j JOIN qc_results q ON q.job_id=j.id JOIN projects pr ON pr.id=j.project_id"
        " WHERE j.type='image_gen' AND COALESCE(pr.look,'')=COALESCE(?,'') AND COALESCE(pr.image_model,'')=COALESCE(?,'')"
        " GROUP BY j.id", (look, image_model)).fetchall()
    both = [r for r in rows if r["person"]]
    if not both:
        return {"pairs": 0, "agreement": None, "lenient_rate": None, "trusted": False}
    verdicts = [(r["score"] >= (r["threshold"] or 0), r["person"] == "approve") for r in both]
    agreement = sum(1 for a, b in verdicts if a == b) / len(both)
    rejected = sum(1 for a, b in verdicts if not b)
    missed = sum(1 for a, b in verdicts if a and not b)
    # 01/10 B2: the share of the pictures the PERSON rejected that the QC passed (it divided by all pictures: 50 pictures, 1 rejected,
    # all passed = 100% missed but "2%" → trusted, and the storyboard checkpoint was skipped)
    lenient = missed / rejected if rejected else None
    return {"pairs": len(both), "agreement": agreement, "lenient_rate": lenient, "rejected": rejected,
            "trusted": (len(both) >= TRUST_PAIRS and agreement >= TRUST_AGREEMENT and rejected >= TRUST_MIN_REJECTED
                        and lenient is not None and lenient <= TRUST_LENIENT)}


def report(conn, project_id: int, pricing: Dict) -> Dict:
    seconds = _finished_video_seconds(conn, project_id)
    times = _times(conn, project_id)
    spend = spend_summary(conn, project_id, pricing)
    scenes = conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]
    touches = conn.execute("SELECT COUNT(*) FROM job_events e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=? AND e.actor='user'",
                           (project_id,)).fetchone()[0]
    per_sec = (lambda v: v / seconds if seconds and v is not None else None)
    return {
        "video_seconds": seconds, "scenes": scenes,
        "wall_min": times["wall_min"], "gen_min": times["gen_min"],
        "wall_min_per_sec": per_sec(times["wall_min"]), "gen_min_per_sec": per_sec(times["gen_min"] or None),
        "cost": spend["credits"], "cost_per_sec": per_sec(spend["credits"] or None), "currency": spend["currency"],
        "unknown_prices": spend["unknown_prices"],
        "image": _first_pass(conn, project_id, "image_gen"), "video": _first_pass(conn, project_id, "video_gen"),
        "qc": _agreement(conn, project_id),
        "touches": touches, "touches_per_scene": touches / scenes if scenes else None,
    }


# người dùng chốt 2026-09-27: không đo từng dự án — so sánh với mức làm tay chung 30 phút cho 1 giây video
MANUAL_MIN_PER_SEC = 30.0


def summary_lines(r: Dict, manual_min_per_sec: Optional[float] = MANUAL_MIN_PER_SEC) -> List[str]:
    """Plain Vietnamese lines for a report / copy-paste."""
    pct = (lambda v: "chưa đủ dữ liệu" if v is None else f"{v:.0%}")
    num = (lambda v, unit: "chưa đủ dữ liệu" if v is None else f"{v:.1f} {unit}".strip())
    lines = [f"Video đã xong: {r['video_seconds']:g} giây / {r['scenes']} cảnh",
             f"1. Thời gian cho 1 giây video: {num(r['wall_min_per_sec'], 'phút')} (tổng thời gian) · "
             f"{num(r['gen_min_per_sec'], 'phút')} (máy gen)",
             f"2. Chi phí cho 1 giây video: {num(r['cost_per_sec'], r['currency'])}"
             + (f" (thiếu giá: {', '.join(r['unknown_prices'])})" if r["unknown_prices"] else ""),
             f"3. Đạt ngay lần đầu: ảnh {pct(r['image']['first_pass'])}, video {pct(r['video']['first_pass'])} · "
             f"số lần gen/cảnh: ảnh {num(r['image']['tries_per_scene'], '')}, video {num(r['video']['tries_per_scene'], '')}",
             f"4. QC Agent đồng ý với người: {pct(r['qc']['agreement'])} ({r['qc']['pairs']} ảnh; AI chặt quá {r['qc']['ai_too_strict']}, "
             f"lỏng quá {r['qc']['ai_too_lenient']})",
             f"5. Thao tác tay: {num(r['touches_per_scene'], 'lần/cảnh')} ({r['touches']} lần)"]
    if manual_min_per_sec and r["wall_min_per_sec"]:
        lines.append(f"So với làm tay ({manual_min_per_sec:g} phút/giây video): nhanh gấp {manual_min_per_sec / r['wall_min_per_sec']:.1f} lần")
    return lines
