"""Is the workflow actually effective? Five figures per project, read from what the pipeline already records (no extra logging):

  1. time per second of finished video   - wall clock (project start -> last video done) and generation time (jobs running)
  2. cost per second of finished video   - declared prices x recorded submissions (core.cost.spend_summary)
  3. first-pass rate                     - share of scenes whose picture / clip was accepted on the first try, and tries per scene
  4. QC agent vs person agreement        - pictures both the QC agent scored and a person decided on
  5. manual touches per scene            - approve / reject / cancel clicks made by a person

A figure is None when there is not enough data yet (the page says so instead of showing a misleading 0).
"""
import json
import os
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


# ---- S14.19 Đợt 1 (KE_HOACH_BO_NAO_PROMPT_TU_HOC): snapshots — the figures AND what was on when they were taken ----------------------
# Taken on purpose only (after a delivery, the 📌 button, tools/effectiveness_baseline.py) — never on page open: report() reads every
# job event of the project. `at` is rounded to the minute and UNIQUE (project_id, at) → a double click keeps one row.

TRIGGERS = ("delivery", "manual", "weekly")
METRICS = ("video_seconds", "scenes", "wall_min_per_sec", "gen_min_per_sec", "cost_per_sec", "image_first_pass", "video_first_pass",
           "qc_agreement", "qc_pairs", "touches_per_scene", "satisfaction", "feedback_n", "lessons_on")
KNOWLEDGE_GROUPS = ("director", "motion")


def flags_on() -> List[str]:
    """Names of the feature flags ON right now (core/features.on — the screen choice, preset or FEATURE_<NAME>)."""
    from . import features
    return sorted(n for n in features.FEATURES if features.on(n))


def _knowledge_inputs(g: str) -> List[tuple]:
    """(name, text) of everything group `g` can read: every built-in file of knowledge.GROUPS (main prompt, gameplay, eval/golden.json…),
    the film-crew role books (sent or not — flags_on says which), the genre folder (Director), the person's ENABLED documents and the
    distilled playbook in use. Wider than distill_inputs (only the foldable documents): a change to the Director prompt must show."""
    from . import knowledge
    rels = [rel for rel, _, _ in knowledge.GROUPS[g][2]] + [c[0] for c in knowledge.CREW_DOCS.get(g, [])]
    inputs = [(rel, knowledge._read(os.path.join(knowledge.ROOT, *rel.split("/")))) for rel in dict.fromkeys(rels)]
    if g == "director" and os.path.isdir(knowledge.GENRE_DIR):
        inputs += [(f"knowledge/genre/{n}", knowledge._read(os.path.join(knowledge.GENRE_DIR, n)))
                   for n in sorted(os.listdir(knowledge.GENRE_DIR)) if os.path.isfile(os.path.join(knowledge.GENRE_DIR, n))]
    inputs += [(f"user:{d['file']}", knowledge._read(d["path"])) for d in knowledge.user_docs(g) if d["enabled"]]
    active = knowledge.distilled_active(g)
    if active:
        inputs.append(("__distilled__", str(active.get("text") or "")))
    return inputs


def knowledge_fp() -> str:
    """What the Director + motion writer read (_knowledge_inputs): 'director:<12>|motion:<12>'; a group that cannot be read says 'lỗi'
    instead of failing the snapshot."""
    from . import knowledge
    parts = []
    for g in KNOWLEDGE_GROUPS:
        try:
            parts.append(f"{g}:{knowledge.fingerprint(_knowledge_inputs(g))[:12]}")
        except Exception:  # noqa: BLE001 - a broken document must not lose the figures
            parts.append(f"{g}:lỗi")
    return "|".join(parts)


def _lessons(conn) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT id, group_name, title FROM lessons WHERE state='approved' ORDER BY id").fetchall()]


def finished_projects(conn) -> List[int]:
    """Projects with a delivered video (an outputs row 'final')."""
    return [r[0] for r in conn.execute("SELECT DISTINCT o.project_id FROM outputs o JOIN projects p ON p.id=o.project_id"
                                        " WHERE o.kind='final' ORDER BY o.project_id").fetchall()]


def report_all(conn, pricing: Dict, project_ids: Optional[List[int]] = None) -> Dict:
    """The whole system: the reports of `project_ids` (default: the finished ones) added up, each figure weighted by what it is
    measured on (seconds, scenes, QC pairs). Same keys as report(), plus 'projects'."""
    ids = finished_projects(conn) if project_ids is None else project_ids
    reps = [report(conn, i, pricing) for i in ids]
    secs = sum(r["video_seconds"] for r in reps)

    def per_sec(key):
        vals = [(r[key], r["video_seconds"]) for r in reps if r[key] is not None and r["video_seconds"]]
        s = sum(w for _, w in vals)
        return sum(v * w for v, w in vals) / s if s else None

    def weighted(part, key, weight):
        vals = [(r[part][key], r[part][weight]) for r in reps if r[part][key] is not None and r[part][weight]]
        s = sum(w for _, w in vals)
        return sum(v * w for v, w in vals) / s if s else None

    scenes = sum(r["scenes"] for r in reps)
    touches = sum(r["touches"] for r in reps)
    qc_pairs = sum(r["qc"]["pairs"] for r in reps)
    return {"projects": ids, "video_seconds": secs, "scenes": scenes,
            "wall_min_per_sec": per_sec("wall_min_per_sec"), "gen_min_per_sec": per_sec("gen_min_per_sec"),
            "cost_per_sec": per_sec("cost_per_sec"), "currency": pricing.get("currency"),
            "image": {"first_pass": weighted("image", "first_pass", "scenes")},
            "video": {"first_pass": weighted("video", "first_pass", "scenes")},
            "qc": {"agreement": weighted("qc", "agreement", "pairs"), "pairs": qc_pairs},
            "touches": touches, "touches_per_scene": touches / scenes if scenes else None}


def _minute(now: Optional[datetime] = None) -> str:
    return (now or datetime.now()).strftime("%Y-%m-%dT%H:%M")


def snapshot(conn, project_id: Optional[int], pricing: Dict, trigger: str, now: Optional[datetime] = None) -> int:
    """Record the figures of one project (None = the whole system, report_all) with the flags / approved lessons / knowledge in use.
    Returns the row id — the existing one when a snapshot of the same project was already taken in the same minute."""
    from . import feedback
    if trigger not in TRIGGERS:
        raise ValueError(f"trigger không hợp lệ: {trigger!r} (chỉ {', '.join(TRIGGERS)})")
    r = report(conn, project_id, pricing) if project_id is not None else report_all(conn, pricing)
    at = _minute(now)
    found = conn.execute("SELECT id FROM effectiveness_snapshots WHERE project_id IS ? AND at=?", (project_id, at)).fetchone()
    if found:                      # UNIQUE does not stop two NULL project ids; this does (and a double click returns the same row)
        return found[0]
    sat = feedback.satisfaction(conn, project_id)
    lessons = _lessons(conn)
    detail = dict(r, lessons=lessons)
    cur = conn.execute(
        "INSERT INTO effectiveness_snapshots (at, project_id, trigger, video_seconds, scenes, wall_min_per_sec, gen_min_per_sec,"
        " cost_per_sec, currency, image_first_pass, video_first_pass, qc_agreement, qc_pairs, touches_per_scene, satisfaction,"
        " feedback_n, lessons_on, flags_on, knowledge_fp, detail) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (at, project_id, trigger, r["video_seconds"], r["scenes"], r["wall_min_per_sec"], r["gen_min_per_sec"], r["cost_per_sec"],
         r["currency"], r["image"]["first_pass"], r["video"]["first_pass"], r["qc"]["agreement"], r["qc"]["pairs"],
         r["touches_per_scene"], sat["satisfaction"], sat["n"], len(lessons), json.dumps(flags_on()), knowledge_fp(),
         json.dumps(detail, ensure_ascii=False, default=str)))
    conn.commit()
    return cur.lastrowid


def history(conn, project_id: Optional[int] = None, limit: int = 50) -> List[Dict]:
    """Snapshots of one project (None = the whole-system ones), oldest first; flags_on / detail decoded."""
    rows = conn.execute("SELECT * FROM (SELECT * FROM effectiveness_snapshots WHERE project_id IS ? ORDER BY at DESC, id DESC LIMIT ?)"
                        " ORDER BY at, id", (project_id, int(limit))).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        for k, empty in (("flags_on", []), ("detail", {})):
            try:
                d[k] = json.loads(d[k]) if d[k] else empty
            except ValueError:
                d[k] = empty
        out.append(d)
    return out


def trend(conn, metric: str, project_id: Optional[int] = None, limit: int = 50) -> List[tuple]:
    """[(at, value)] of one figure over the snapshots, oldest first (like devsys/scores.trend)."""
    if metric not in METRICS:
        raise ValueError(f"chỉ số không có: {metric!r} (chỉ {', '.join(METRICS)})")
    return [(h["at"], h[metric]) for h in history(conn, project_id, limit)]


def delta(a: Dict, b: Dict) -> Dict:
    """Snapshot a → snapshot b (rows of history()): each figure (before, after, change) and WHAT changed in between — flags switched
    on / off, approved lessons added / gone, the knowledge read by the Director / motion writer. 'changed' = plain lines."""
    metrics = {}
    for m in METRICS:
        x, y = a.get(m), b.get(m)
        metrics[m] = (x, y, (y - x) if x is not None and y is not None else None)
    fa, fb = set(a.get("flags_on") or []), set(b.get("flags_on") or [])
    la = {x["id"]: x for x in (a.get("detail") or {}).get("lessons") or []}
    lb = {x["id"]: x for x in (b.get("detail") or {}).get("lessons") or []}
    out = {"metrics": metrics, "flags_added": sorted(fb - fa), "flags_removed": sorted(fa - fb),
           "lessons_on": (a.get("lessons_on"), b.get("lessons_on")),
           "lessons_added": [lb[i] for i in sorted(set(lb) - set(la))], "lessons_removed": [la[i] for i in sorted(set(la) - set(lb))],
           "knowledge_changed": (a.get("knowledge_fp") or "") != (b.get("knowledge_fp") or "")}
    lines = []
    if out["flags_added"]:
        lines.append("Bật cờ: " + ", ".join(out["flags_added"]))
    if out["flags_removed"]:
        lines.append("Tắt cờ: " + ", ".join(out["flags_removed"]))
    if out["lessons_added"] or out["lessons_removed"] or out["lessons_on"][0] != out["lessons_on"][1]:
        lines.append(f"Bài học đang bật: {out['lessons_on'][0]} → {out['lessons_on'][1]}"
                     + "".join(f"; + {x['title']}" for x in out["lessons_added"]) + "".join(f"; − {x['title']}" for x in out["lessons_removed"]))
    if out["knowledge_changed"]:
        lines.append(f"Kiến thức Director/motion đã đổi ({a.get('knowledge_fp')} → {b.get('knowledge_fp')})")
    out["changed"] = lines
    return out