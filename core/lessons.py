"""Learning from repeated mistakes across projects.

Flow (nothing reaches the prompts without a human click):
  harvest()  read what already went wrong from the database (rejected images/videos with their reasons,
             risk-control blocks) into `mistakes`, once per record;
  propose()  when the same kind of mistake shows up often enough (several times, in several projects) write a
             short "lesson" (Claude when available, a plain template otherwise) as state 'proposed';
  approve()  a person accepts it: it joins the step's knowledge base (one auto-maintained document per step), which
             the Director / QC / Motion steps then read (after the usual distillation).
Research lessons (core/research.py) use the same table and the same approval.
"""
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import diag, knowledge

DOC_TITLE = "Bài học đã duyệt (tự động cập nhật)"
MIN_EVENTS = 3          # same kind of mistake at least this many times ...
MIN_PROJECTS = 2        # ... in at least this many projects
# tag -> (label, keywords). A mistake can carry several tags.
TAGS = {
    "hands": ("Bàn tay / ngón tay", ("tay", "ngón", "hand", "finger")),
    "face": ("Khuôn mặt / mắt", ("mặt", "khuôn", "mắt", "face", "eye")),
    "text": ("Chữ / logo / watermark lạ", ("chữ", "text", "logo", "watermark", "phụ đề")),
    "lighting": ("Ánh sáng / độ sáng", ("tối", "ánh sáng", "dark", "light", "exposure", "cháy sáng")),
    "consistency": ("Nhân vật không nhất quán (mặt, trang phục)", ("trang phục", "nhất quán", "sai nhân vật", "khác nhân vật",
                                                                    "costume", "outfit", "consisten", "character")),
    "anatomy": ("Cơ thể méo / thừa chi tiết", ("thừa", "méo", "dị dạng", "anatomy", "extra", "deform", "limb")),
    "scale": ("Tỉ lệ người / lơ lửng", ("tỉ lệ", "quá to", "quá nhỏ", "lơ lửng", "chạm đất", "scale", "too big", "too small",
                                        "floating", "feet", "ground")),
    "composition": ("Bố cục / cỡ cảnh", ("bố cục", "cỡ cảnh", "framing", "crop", "composition")),
    "mismatch": ("Không khớp kịch bản", ("kịch bản", "sai bối cảnh", "không khớp", "mismatch", "sai địa điểm")),
    "motion": ("Chuyển động giật / biến dạng", ("giật", "morph", "flicker", "jitter", "biến dạng", "artifact")),
    "risk_control": ("Bị risk control chặn", ("risk_control", "risk control", "moderation", "content policy")),
}
GROUP_OF_STAGE = {"image": "director", "video": "motion"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tags_of(text: str) -> List[str]:
    low = (text or "").lower()
    return [t for t, (_, words) in TAGS.items() if any(w in low for w in words)]


def _clean(note: Optional[str]) -> str:
    text = (note or "").strip()
    if " — " in text:                      # "QC 0.62 < mức tối thiểu 0.7 — <the defects>": keep the defects
        text = text.split(" — ", 1)[1]
    text = re.sub(r"\d+([.,]\d+)?", "#", text)
    return diag.redact(text)[:300]


# ---- 1. collect ---------------------------------------------------------------------------------
def harvest(conn) -> int:
    """Copy new mistakes out of the workflow tables. Idempotent: (source, ref_id) is unique. Returns rows added."""
    added = 0
    rows = conn.execute(
        "SELECT r.id, r.note, r.decided_at, j.type, j.project_id FROM review_log r JOIN jobs j ON j.id=r.job_id"
        " WHERE r.decision='reject' AND j.type IN ('image_gen','video_gen')").fetchall()
    for r in rows:
        stage = "image" if r["type"] == "image_gen" else "video"
        added += _add(conn, "review", r["id"], r["decided_at"], r["project_id"], stage, _clean(r["note"]))
    rows = conn.execute(
        "SELECT m.id, m.error_message, m.at, j.type, j.project_id, s.data FROM content_moderation_failures m"
        " JOIN jobs j ON j.id=m.job_id JOIN scenes s ON s.id=j.scene_id").fetchall()
    for r in rows:
        stage = "image" if r["type"] == "image_gen" else "video"
        prompt = ""
        try:
            prompt = (json.loads(r["data"] or "{}").get("image_prompt") or "")[:120]
        except ValueError:
            pass
        added += _add(conn, "moderation", r["id"], r["at"], r["project_id"], stage,
                      _clean(f"risk_control: {r['error_message']} | prompt: {prompt}"))
    conn.commit()
    return added


def _add(conn, source: str, ref: int, at: Optional[str], project_id: int, stage: str, text: str) -> int:
    cur = conn.execute("INSERT OR IGNORE INTO mistakes (source, ref_id, at, project_id, stage, group_name, text)"
                       " VALUES (?,?,?,?,?,?,?)", (source, ref, at or _now(), project_id, stage, GROUP_OF_STAGE[stage], text))
    return cur.rowcount


def clusters(conn, min_events: int = MIN_EVENTS, min_projects: int = MIN_PROJECTS) -> List[Dict]:
    """Kinds of mistakes that repeat: same (step, tag) often enough, across enough projects."""
    buckets: Dict[tuple, List] = {}
    for m in conn.execute("SELECT * FROM mistakes ORDER BY id").fetchall():
        for tag in tags_of(m["text"]):
            buckets.setdefault((m["group_name"], tag), []).append(m)
    out = []
    for (group, tag), items in buckets.items():
        projects = {m["project_id"] for m in items}
        out.append({"group": group, "tag": tag, "label": TAGS[tag][0], "events": len(items), "projects": len(projects),
                    "examples": list(dict.fromkeys(m["text"] for m in items))[:4],
                    "ready": len(items) >= min_events and len(projects) >= min_projects})
    return sorted(out, key=lambda c: (-c["ready"], -c["events"]))


# ---- 2. propose ---------------------------------------------------------------------------------
def _known(conn, group: str, key: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM lessons WHERE group_name=? AND key=?", (group, key)).fetchone())


def _write_rule(client, cluster: Dict) -> str:
    """One short imperative rule from the examples (Claude), or a plain template without a model."""
    examples = "\n".join(f"- {e}" for e in cluster["examples"])
    if client is None:
        return (f"Lỗi \"{cluster['label']}\" đã lặp lại {cluster['events']} lần ở {cluster['projects']} dự án. "
                f"Ví dụ thực tế:\n{examples}\nHãy chú ý tránh lỗi này khi viết prompt / kiểm tra.")
    prompt = ("Biên tập viên bài học. Dưới đây là các lỗi lặp lại của quy trình làm video AI (bước: "
              f"{knowledge.GROUPS[cluster['group']][0]}). Nhóm lỗi: {cluster['label']} ({cluster['events']} lần, "
              f"{cluster['projects']} dự án).\nVí dụ:\n{examples}\n\nViết MỘT quy tắc ngắn (tối đa 3 câu, tiếng Việt, "
              "mệnh lệnh, cụ thể, có thể áp dụng ngay khi viết prompt hoặc chấm ảnh) để lần sau không lặp lại lỗi. "
              "Chỉ trả về nội dung quy tắc.")
    from .llm_runner import tagged
    with tagged("lessons"):
        return client.complete(prompt).text.strip()[:600]


def propose(conn, client=None) -> int:
    """Turn ready clusters into proposed lessons (skips kinds that already have a lesson, whatever its state)."""
    harvest(conn)
    made = 0
    for c in clusters(conn):
        key = f"mistake:{c['tag']}"
        if not c["ready"] or _known(conn, c["group"], key):
            continue
        body = _write_rule(client, c)
        conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, evidence, state)"
                     " VALUES (?,?,?,?,?,?,?, 'proposed')",
                     (_now(), c["group"], key, f"Tránh lỗi lặp: {c['label']}", body, "mistakes",
                      json.dumps({"events": c["events"], "projects": c["projects"], "examples": c["examples"]},
                                 ensure_ascii=False)))
        made += 1
    conn.commit()
    return made


def add_research(conn, group: str, title: str, body: str, url: str) -> bool:
    key = "research:" + re.sub(r"\W+", " ", title.lower()).strip()[:80]
    if _known(conn, group, key):
        return False
    conn.execute("INSERT INTO lessons (created_at, group_name, key, title, body, source, evidence, state)"
                 " VALUES (?,?,?,?,?,?,?, 'proposed')",
                 (_now(), group, key, title[:120], body[:800], "research", json.dumps({"urls": [url]}, ensure_ascii=False)))
    conn.commit()
    return True


# ---- 3. decide ----------------------------------------------------------------------------------
def list_lessons(conn, state: Optional[str] = None) -> List[Dict]:
    sql = "SELECT * FROM lessons" + (" WHERE state=?" if state else "") + " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql, (state,) if state else ()).fetchall()]


def edit(conn, lesson_id: int, title: str, body: str) -> None:
    conn.execute("UPDATE lessons SET title=?, body=? WHERE id=?", (title.strip(), body.strip(), lesson_id))
    conn.commit()
    row = conn.execute("SELECT group_name, state FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    if row and row["state"] == "approved":
        sync_knowledge(conn, row["group_name"])


def decide(conn, lesson_id: int, approve: bool) -> None:
    row = conn.execute("SELECT group_name FROM lessons WHERE id=?", (lesson_id,)).fetchone()
    if row is None:
        raise KeyError(lesson_id)
    conn.execute("UPDATE lessons SET state=?, decided_at=? WHERE id=?", ("approved" if approve else "rejected", _now(), lesson_id))
    conn.commit()
    sync_knowledge(conn, row["group_name"])


def sync_knowledge(conn, group: str) -> Optional[Dict]:
    """(Re)write the step's auto-maintained knowledge document from all approved lessons."""
    for d in knowledge.user_docs(group):
        if d["title"] == DOC_TITLE:
            knowledge.remove_doc(group, d["file"])
    approved = [r for r in list_lessons(conn, "approved") if r["group_name"] == group]
    if not approved:
        return None
    lines = ["# Bài học rút ra từ các dự án trước (đã được người duyệt)", ""]
    for r in reversed(approved):
        lines.append(f"- **{r['title']}**: {r['body'].strip()}")
    return knowledge.add_doc(group, "bai_hoc.md", "\n".join(lines).encode("utf-8"), title=DOC_TITLE,
                             note="tự sinh từ tab Bài học; đừng sửa tay")


# ---- settings kept next to the data ----------------------------------------------------------------
def meta(conn, key: str, default: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM learning_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn, key: str, value: str) -> None:
    conn.execute("INSERT INTO learning_meta (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, value))
    conn.commit()
