"""What the person says about the result (S14.19, KE_HOACH_BO_NAO_PROMPT_TU_HOC Đợt 0) — one table, `user_feedback`, for:

  - 'delivery': "Bản này dùng được chứ?" on the finished video (Bước 5) — 👍 5 / 🤔 3 / 👎 1, what is not right, which stage;
                also the 1–5 marks of ⚖ So sánh (core/compare.save_scores, screen = compare.FEEDBACK_SCREEN, text = JSON);
  - 'scene':    a remark about one scene / shot (the picture / clip review keeps using review_log.note — not duplicated here);
  - 'screen':   💬 "Góp ý màn này" in the top bar — the dashboard itself.

Nothing reads it automatically yet: Đợt 1 puts `satisfaction` into each effectiveness snapshot, Đợt 6 turns rows into mistakes
(`handled` = 'mistake:<id>' | 'bỏ qua: <lý do>').
"""
import builtins
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

KINDS = ("delivery", "scene", "screen")
STAGES = {"director": "Đạo diễn / kịch bản", "image": "Ảnh", "motion": "Chuyển động / video", "audio": "Âm thanh",
          "render": "Dựng / xuất bản", "ui": "Giao diện"}
VERDICTS = {"👍": 5, "🤔": 3, "👎": 1}           # "Bản này dùng được chứ?" → rating
MAX_TEXT = 4000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add(conn, kind: str, project_id: Optional[int] = None, scene_id: Optional[int] = None, screen: Optional[str] = None,
        stage: Optional[str] = None, rating: Optional[int] = None, text: Optional[str] = None, created_by: Optional[str] = None) -> int:
    """Record one remark; returns its id. ValueError (never a silent drop) for an unknown kind / stage, a rating outside 1–5, or
    a remark with neither a rating nor a text."""
    if kind not in KINDS:
        raise ValueError(f"loại góp ý không hợp lệ: {kind!r} (chỉ {', '.join(KINDS)})")
    if stage is not None and stage not in STAGES:
        raise ValueError(f"khâu không hợp lệ: {stage!r} (chỉ {', '.join(STAGES)})")
    if rating is not None:
        rating = int(rating)
        if not 1 <= rating <= 5:
            raise ValueError(f"điểm phải từ 1 đến 5, nhận {rating}")
    text = (text or "").strip()[:MAX_TEXT] or None
    if rating is None and not text:
        raise ValueError("góp ý trống — chọn mức hài lòng hoặc viết vài chữ")
    cur = conn.execute("INSERT INTO user_feedback (at, kind, project_id, scene_id, screen, stage, rating, text, created_by)"
                       " VALUES (?,?,?,?,?,?,?,?,?)", (_now(), kind, project_id, scene_id, screen, stage, rating, text, created_by))
    conn.commit()
    return cur.lastrowid


def list(conn, kind: Optional[str] = None, project_id: Optional[int] = None, stage: Optional[str] = None,
         screen: Optional[str] = None, limit: int = 200) -> List[Dict]:
    """Newest first."""
    where, args = [], []
    for col, val in (("kind", kind), ("project_id", project_id), ("stage", stage), ("screen", screen)):
        if val is not None:
            where.append(f"{col}=?")
            args.append(val)
    sql = "SELECT * FROM user_feedback" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
    return [dict(r) for r in conn.execute(sql, (*args, int(limit))).fetchall()]


def _norm(rating: float) -> float:
    return (rating - 1) / 4                     # 1..5 → 0..1


def satisfaction(conn, project_id: Optional[int] = None) -> Dict:
    """Mean "is it usable" of the delivery remarks (0..1; None when nobody said anything yet) and how many there are.
    project_id None = every project."""
    sql = "SELECT AVG(rating), COUNT(rating) FROM user_feedback WHERE kind='delivery' AND rating IS NOT NULL"
    row = conn.execute(sql + (" AND project_id=?" if project_id is not None else ""),
                       (project_id,) if project_id is not None else ()).fetchone()
    n = int(row[1] or 0)
    return {"satisfaction": _norm(row[0]) if n else None, "n": n}


def summary(conn, stage: Optional[str] = None, days: Optional[int] = 30) -> Dict:
    """Remarks of the last `days` days (None = all): how many, by kind and by stage (count + mean rating 0..1), the newest texts."""
    where, args = [], []
    if stage is not None:
        where.append("stage=?")
        args.append(stage)
    if days:
        where.append("at >= ?")
        args.append((datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    rows = [dict(r) for r in conn.execute("SELECT * FROM user_feedback" + (" WHERE " + " AND ".join(where) if where else "")
                                          + " ORDER BY id DESC", args).fetchall()]
    by_stage: Dict[str, Dict] = {}
    by_kind: Dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        b = by_stage.setdefault(r["stage"] or "", {"n": 0, "ratings": []})
        b["n"] += 1
        if r["rating"] is not None:
            b["ratings"].append(r["rating"])
    for b in by_stage.values():
        ratings = b.pop("ratings")
        b["satisfaction"] = _norm(sum(ratings) / len(ratings)) if ratings else None
    return {"n": len(rows), "by_kind": by_kind, "by_stage": by_stage,
            "unhandled": sum(1 for r in rows if not r["handled"]),
            "latest": [r for r in rows if r["text"]][:10]}


def detach(conn, project_id: Optional[int] = None, scene_ids: Optional[builtins.list] = None) -> None:
    """Before a project / scene rows are deleted: the remarks stay (they are what the person said), without the link to the rows that
    go away (user_feedback.project_id / scene_id are foreign keys). No commit — part of the caller's delete."""
    if scene_ids:
        marks = ",".join("?" * len(scene_ids))
        conn.execute(f"UPDATE user_feedback SET scene_id=NULL WHERE scene_id IN ({marks})", builtins.list(scene_ids))
    if project_id is not None:
        conn.execute("UPDATE user_feedback SET scene_id=NULL WHERE scene_id IN (SELECT id FROM scenes WHERE project_id=?)", (project_id,))
