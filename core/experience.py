"""Sổ kinh nghiệm của nhà máy (người dùng 2026-10-01): every stage keeps CASES — one concrete frame / clip / decision each, a success, a
failure, a false alarm (looked like a fault, was right) or a miss — with its evidence picture and who confirmed it; any stage reads the
cases that match what it is about to do (same characters, same view) before acting.

Why cases and not only text lessons (core/lessons.py): S7.1 01/10 — the QC playbook already said in words that "Kenta from behind, the
star shoulder on the frame-left of his body = his LEFT arm = right", the person had relabelled exactly those frames (labels_v2.json, job
319/320), yet the agent blocked them twice; nobody showed it the case.

Sources, read again at every refresh (idempotent, keyed):
  review_log      every approve / reject a PERSON made with a note (image / video stages)
  QC labels       docs/qc_agent_2026-09-27/*verdicts.json + labels_v2.json overrides (human-confirmed frame verdicts)
  record()        any stage adds its own case at run time (e.g. the QC evaluation writes each agent–human disagreement)
"""
import glob
import json
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABELS_DIR = os.path.join(ROOT, "docs", "qc_agent_2026-09-27")
LABELS_PROJECT = 8                   # the QC label rounds were made on project #8
OUTCOMES = ("success", "failure", "false_alarm", "missed")
OUTCOME_VI = {"success": "đạt", "failure": "lỗi thật", "false_alarm": "BÁO NHẦM — trông như lỗi nhưng ĐÚNG", "missed": "BỎ SÓT lỗi thật"}

SCHEMA = """CREATE TABLE IF NOT EXISTS experience_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, at TEXT, stage TEXT, outcome TEXT, project_id INTEGER, job_id INTEGER,
    shot TEXT, subjects TEXT, view TEXT, kind TEXT, note TEXT, evidence TEXT, source TEXT, confirmed_by TEXT)"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure(conn) -> None:
    conn.execute(SCHEMA)


def record(conn, *, key: str, stage: str, outcome: str, note: str, source: str, project_id: Optional[int] = None,
           job_id: Optional[int] = None, shot: Optional[str] = None, subjects: Iterable[str] = (), view: Optional[str] = None,
           kind: Optional[str] = None, evidence: Optional[str] = None, confirmed_by: Optional[str] = None, replace: bool = False) -> bool:
    """Add one case (True = new). `replace` lets a later, better-confirmed source overwrite the same key."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome ∈ {OUTCOMES}")
    ensure(conn)
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    cur = conn.execute(f"{verb} INTO experience_cases (key, at, stage, outcome, project_id, job_id, shot, subjects, view, kind, note, "
                       "evidence, source, confirmed_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (key, _now(), stage, outcome, project_id, job_id, shot, json.dumps(sorted({str(s).upper() for s in subjects})),
                        view, kind, str(note or "")[:600], evidence, source, confirmed_by))
    conn.commit()
    return cur.rowcount > 0


def job_picture(data_dir: str, project_id: int, job_id: int) -> Optional[str]:
    """The job's picture, also when it was rejected and moved to the project's bin."""
    path = os.path.join(data_dir, str(project_id), "images", f"job_{job_id}.png")
    if os.path.exists(path):
        return path
    hits = sorted(glob.glob(os.path.join(data_dir, str(project_id), "trash", "images", f"job_{job_id}__*.png")))
    return hits[-1] if hits else None


def job_context(conn, job_id: int) -> Dict:
    """Who is in the job's shot and from which side the camera sees them ('behind' when any is seen from behind, 'camera' when the
    shot plainly faces them, None when the words do not say)."""
    from .runner import seen_from_behind
    row = conn.execute("SELECT j.project_id, s.data FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (job_id,)).fetchone()
    if not row:
        return {"project_id": None, "subjects": [], "view": None, "shot": None}
    data = json.loads(row["data"] or "{}")
    names = [str(n).upper() for n in data.get("characters") or []]
    sides = [seen_from_behind(data, n) for n in names]
    view = "behind" if any(v is True for v in sides) else ("camera" if names and all(v is False for v in sides) else None)
    return {"project_id": row["project_id"], "subjects": names, "view": view, "shot": data.get("shot")}


SCRIPT_MARK = "[thử tự động]"   # review_log allows only 'user' / 'ai_agent': a decision an experiment script makes carries this mark


def import_review_log(conn, data_dir: str) -> int:
    """Every decision a PERSON made with a note: approve = success, reject = failure (the note is the reason). Decisions experiment
    scripts made in the person's name (note starting with SCRIPT_MARK) are not a person's judgement and are left out (rà soát 01/10:
    7 approvals + 5 S5.5' rejections had entered the notebook as human cases)."""
    ensure(conn)
    added = 0
    rows = conn.execute("SELECT r.id, r.job_id, r.decision, r.note, j.type FROM review_log r JOIN jobs j ON j.id=r.job_id "
                        "WHERE r.reviewer_type='user' AND r.note IS NOT NULL AND trim(r.note)!='' AND r.note NOT LIKE ?",
                        (SCRIPT_MARK + "%",)).fetchall()
    for r in rows:
        ctx = job_context(conn, r["job_id"])
        stage = "video" if r["type"] == "video_gen" else "image"
        added += record(conn, key=f"review:{r['id']}", stage=stage, outcome="success" if r["decision"] == "approve" else "failure",
                        note=r["note"], source="review_log", project_id=ctx["project_id"], job_id=r["job_id"], shot=ctx["shot"],
                        subjects=ctx["subjects"], view=ctx["view"], evidence=job_picture(data_dir, ctx["project_id"] or 0, r["job_id"])
                        if stage == "image" else None, confirmed_by="người dùng")
    return added


def _label_rounds(labels_dir: str) -> List[Dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(labels_dir, "**", "verdicts.json"), recursive=True)):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items = data.get("verdicts") if isinstance(data, dict) else data
        try:
            name = os.path.relpath(path, ROOT)
        except ValueError:                             # another drive (Windows): keep the absolute path
            name = path
        out += [dict(x, _file=name) for x in items or [] if isinstance(x, dict) and x.get("job")]
    return out


def import_qc_labels(conn, data_dir: str, labels_dir: str = LABELS_DIR, project_id: int = LABELS_PROJECT) -> int:
    """The human-confirmed QC verdicts of the label rounds, with the labels_v2 corrections: a label changed from 'chặn' to 'đạt' is a
    FALSE ALARM case (it looked like a fault and was not) — the most useful kind for a checker."""
    ensure(conn)
    fixes = {}
    try:
        fixes = json.load(open(os.path.join(labels_dir, "labels_v2.json"), encoding="utf-8")).get("overrides") or {}
    except (OSError, ValueError):
        pass
    added = 0
    for item in _label_rounds(labels_dir):
        job = int(item["job"])
        fix = fixes.get(str(job))
        verdict = (fix or {}).get("verdict") or item.get("verdict")
        issues = (fix or {}).get("issues") if fix is not None else item.get("issues")
        ctx = job_context(conn, job)
        if fix and fix.get("old") == "chặn" and verdict in ("đạt", "nhỏ"):
            outcome, note = "false_alarm", f"Nhãn cũ 'chặn' sửa thành '{verdict}': {fix.get('why')}"
            kind = next((i.get("loai") for i in item.get("issues") or []), None) or "trái/phải"
        else:
            outcome = "failure" if verdict == "chặn" else "success"
            parts = [f"{i.get('loai')}: {i.get('mo_ta')}" for i in issues or [] if isinstance(i, dict)]
            note = f"Người chấm '{verdict}'" + (" — " + "; ".join(parts) if parts else "") + (f" · {item.get('ghi_chu')}" if item.get("ghi_chu") else "")
            kind = next((i.get("loai") for i in issues or [] if isinstance(i, dict)), None)
        added += record(conn, key=f"qc_label:{job}", stage="qc_image", outcome=outcome, note=note, source=item["_file"],
                        project_id=ctx["project_id"] or project_id, job_id=job, shot=item.get("shot") or ctx["shot"],
                        subjects=ctx["subjects"], view=ctx["view"], kind=kind,
                        evidence=job_picture(data_dir, ctx["project_id"] or project_id, job), confirmed_by="nhãn người", replace=True)
    return added


def refresh(conn, data_dir: str) -> int:
    """Read every source again (cheap, keyed — nothing is added twice)."""
    return import_qc_labels(conn, data_dir) + import_review_log(conn, data_dir)


def relevant(conn, stages: Iterable[str], subjects: Iterable[str], views: Iterable[Optional[str]] = (), limit: int = 4,
             exclude_jobs: Iterable[int] = (), exclude_shots: Iterable[tuple] = ()) -> List[Dict]:
    """The cases worth showing before a stage acts: same characters AND same view first; false alarms and misses (the mistakes a
    checker makes) before plain successes / failures; only confirmed cases; never the frames being judged right now."""
    ensure(conn)
    want, views, skip = {str(s).upper() for s in subjects}, {v for v in views if v}, set(exclude_jobs)
    skip_shots = {tuple(x) for x in exclude_shots}
    rows = conn.execute(f"SELECT * FROM experience_cases WHERE stage IN ({','.join('?' * len(list(stages)))}) AND confirmed_by IS NOT NULL",
                        list(stages)).fetchall()
    scored = []
    for r in rows:
        if r["job_id"] in skip or (r["project_id"], r["shot"]) in skip_shots:   # never the frames judged now, nor another take
            continue                                                             # of the same shot (that would hand over the answer)
        who = set(json.loads(r["subjects"] or "[]"))
        if want and not who & want:
            continue
        score = 2 * len(who & want) + (3 if r["view"] and r["view"] in views else 0) \
            + {"false_alarm": 4, "missed": 4, "failure": 2, "success": 0}[r["outcome"]] + (1 if r["evidence"] else 0)
        scored.append((score, r["id"], dict(r)))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    # balance: at most half of the cases of one outcome — four false alarms alone would teach a checker to wave real flips through
    # (S7.1 01/10 dry run: cảnh 2 #8 has 2 real blocks)
    # every character of the scene gets its own case first (S7.1 01/10: four Kenta cases, none for MAXIM's cap seen from behind —
    # the fault the agent then passed), then the rest by score
    out, used = [], set()
    for name in sorted(want):
        mine = [c for _, _, c in scored if name in json.loads(c["subjects"] or "[]") and c["key"] not in used]
        mine.sort(key=lambda c: name.lower() not in str(c.get("note") or "").lower())   # a case ABOUT this person (named in its note)
        if mine and len(out) < limit:
            out.append(mine[0])
            used.add(mine[0]["key"])
    per = max(1, (limit + 1) // 2)
    for _, _, case in scored:
        if len(out) >= limit:
            break
        if case["key"] not in used and sum(1 for c in out if c["outcome"] == case["outcome"]) < per:
            out.append(case)
            used.add(case["key"])
    for _, _, case in scored:
        if len(out) >= limit:
            break
        if case["key"] not in used:
            out.append(case)
            used.add(case["key"])
    return out


def text_line(case: Dict) -> str:
    who = ", ".join(json.loads(case.get("subjects") or "[]")) or "—"
    view = {"behind": "quay lưng / qua vai", "camera": "quay mặt vào máy"}.get(case.get("view") or "", "hướng không rõ")
    return (f"[{OUTCOME_VI[case['outcome']]}] {case.get('shot') or ''} · {who} · {view}"
            + (f" · {case['kind']}" if case.get("kind") else "") + f" — {case.get('note') or ''}")
