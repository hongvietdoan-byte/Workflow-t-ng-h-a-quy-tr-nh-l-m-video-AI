"""C2 (người dùng 13/10, chốt 14/10 — docs/handoff/KE_HOACH_TRUOC_TAP2_P27_2026-10-14.md): "Chờ bạn" thừa ở dự án đã xong / gần xong.

Tra CSDL thật 13/10: #27 (98 %) hiện "9 chờ bạn", #24 (100 %) "15 chờ bạn" — phần lớn là việc đã lỗi thời: bản cũ còn `pending_review` khi
shot đã có bản MỚI HƠN được duyệt / bản người đã chọn, lỗi gen cũ khi shot đã có bản dùng được, mục Tổ rà soát còn mở khi shot đã có kết
quả được duyệt SAU mục đó, mọi thứ của dự án đã xuất bản giao (`delivered`). Không ẩn bừa: mỗi mục có lý do, và chỉ những loại trên.

- `stale(conn, pid)`: danh sách mục thừa + lý do (đọc, không ghi) — 📥 và thẻ dự án KHÔNG đếm chúng (`skip_sets`).
- `clean(p, pid, who)`: nút "🧹 Dọn việc thừa của dự án" (xem trước + xác nhận ở ⌂): KHÔNG xóa gì — bản chờ duyệt thừa → `rejected`
  (ghi `job_events`, người vẫn "Vẫn dùng bản này" được), mục rà soát thừa → `resolved` (resolved_by ghi người dọn). Lỗi gen cũ và bản
  chờ duyệt của dự án đã giao mà shot KHÔNG có bản khác chỉ là "không đếm" — giữ nguyên (đổi chúng có thể làm rơi shot khỏi bản dựng lại).
"""
from typing import Dict, List, Optional, Set

from . import delivered, takes

GEN = ("image_gen", "video_gen")
LABEL = {"image_gen": "ảnh", "video_gen": "clip"}
WHO = "dọn việc thừa"
CLIP_KHAU = ("motion", "khung_cuoi", "video", "lien_tuc")


def _approved_at(conn, job_id: int) -> str:
    row = conn.execute("SELECT at FROM job_events WHERE job_id=? AND to_state='approved' ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    if row:
        return row[0]
    row = conn.execute("SELECT updated_at FROM jobs WHERE id=?", (job_id,)).fetchone()
    return row[0] if row else ""


def _stamp(at: Optional[str]) -> str:
    """'2026-10-13T21:24:18Z' (change_review) and '2026-10-13T21:24:18+00:00' (pipeline) compare by their first 19 characters."""
    return (at or "").replace(" ", "T")[:19]


def _in_use(conn, scene_id: int, typ: str, job_id: int, newer_only: bool) -> Optional[int]:
    """Another take of the shot that the person keeps: the chosen clip (takes.chosen), else an approved job of the same type
    (`newer_only`: only one made AFTER `job_id` — an older approved one does not make a newer pending take a leftover)."""
    if typ == "video_gen":
        pick = takes.chosen(conn, scene_id)
        if pick is not None and pick["id"] != job_id:
            return pick["id"]
    row = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type=? AND state='approved' AND id!=?" + (" AND id>?" if newer_only else "")
                       + " ORDER BY id DESC LIMIT 1", (scene_id, typ, job_id) + ((job_id,) if newer_only else ())).fetchone()
    return row[0] if row else None


def stale(conn, project_id: int) -> Dict[str, List[Dict]]:
    """{"jobs": bản chờ duyệt thừa, "failed": lỗi gen cũ, "findings": mục rà soát thừa} — each row has `reason` (Vietnamese) and
    `action` ("reject" / "resolve" / None = chỉ không đếm)."""
    gone = delivered.is_delivered(conn, project_id)
    out: Dict[str, List[Dict]] = {"jobs": [], "failed": [], "findings": []}
    for j in conn.execute("SELECT j.id, j.type, j.scene_id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND "
                          f"j.type IN {GEN} AND j.state='pending_review' ORDER BY s.idx, j.id", (project_id,)).fetchall():
        keep = _in_use(conn, j["scene_id"], j["type"], j["id"], newer_only=True)
        if keep is None and gone:
            keep = _in_use(conn, j["scene_id"], j["type"], j["id"], newer_only=False)
        if keep is not None:
            why = f"shot đã dùng bản job {keep}" + (" (dự án đã giao)" if gone else "")
            out["jobs"].append({"job_id": j["id"], "type": j["type"], "idx": j["idx"], "reason": why, "action": "reject"})
        elif gone:
            out["jobs"].append({"job_id": j["id"], "type": j["type"], "idx": j["idx"], "action": None,
                                "reason": "dự án đã giao, shot chưa có bản khác — không đếm, giữ nguyên"})
    # the same "latest job of the shot failed" rows as core/inbox.items (Lỗi gen)
    for j in conn.execute("SELECT j.id, j.type, j.scene_id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND "
                          f"j.type IN {GEN} AND j.state IN ('failed','retryable') AND NOT EXISTS (SELECT 1 FROM jobs k WHERE "
                          "k.scene_id=j.scene_id AND k.type=j.type AND k.id>j.id) ORDER BY s.idx", (project_id,)).fetchall():
        keep = _in_use(conn, j["scene_id"], j["type"], j["id"], newer_only=False)
        if keep is not None or gone:
            why = (f"shot đã có bản dùng được (job {keep})" if keep is not None else "dự án đã giao") + " — không đếm, giữ nguyên"
            out["failed"].append({"job_id": j["id"], "type": j["type"], "idx": j["idx"], "reason": why, "action": None})
    try:
        rows = conn.execute("SELECT f.id, f.scene_id, f.level, f.khau, f.at, s.idx FROM change_findings f LEFT JOIN scenes s ON "
                            "s.id=f.scene_id WHERE f.project_id=? AND f.status='open' ORDER BY s.idx, f.id", (project_id,)).fetchall()
    except Exception:  # noqa: BLE001 - an old database without the table: nothing to clean
        rows = []
    for f in rows:
        why = None
        if f["scene_id"] is not None:
            # a clip-stage item (motion / end frame / clip / continuity) is answered only by an approved CLIP — an approved picture
            # after it does not mean the clip was redone (its hold must stay); a picture-stage item by either
            types = ("video_gen",) if f["khau"] in CLIP_KHAU else GEN
            q = ",".join("?" * len(types))
            for k in conn.execute(f"SELECT id FROM jobs WHERE scene_id=? AND type IN ({q}) AND state='approved' ORDER BY id DESC",
                                  (f["scene_id"], *types)).fetchall():
                if _stamp(_approved_at(conn, k[0])) >= _stamp(f["at"]):
                    why = f"shot đã có kết quả được duyệt sau mục này (job {k[0]})"
                    break
        if why is None and gone:
            why = "dự án đã giao"
        if why:
            out["findings"].append({"id": f["id"], "idx": f["idx"], "level": f["level"], "khau": f["khau"], "reason": why,
                                    "action": "resolve"})
    return out


def skip_sets(conn, project_id: int) -> Dict[str, Set[int]]:
    """Ids 📥 / the project card do not count: {"jobs": pending_review ids, "failed": failed job ids, "findings": finding ids}."""
    s = stale(conn, project_id)
    return {"jobs": {r["job_id"] for r in s["jobs"]}, "failed": {r["job_id"] for r in s["failed"]},
            "findings": {r["id"] for r in s["findings"]}}


def preview(conn, project_id: int) -> List[str]:
    """One line per item, what the button will do (or that it is only no longer counted)."""
    s = stale(conn, project_id)
    lines = []
    for r in s["jobs"]:
        act = "đánh dấu loại" if r["action"] == "reject" else "không đếm"
        lines.append(f"{LABEL[r['type']]} shot {r['idx']} · job {r['job_id']} chờ duyệt → {act}: {r['reason']}")
    for r in s["failed"]:
        lines.append(f"{LABEL[r['type']]} shot {r['idx']} · job {r['job_id']} gen lỗi → {r['reason']}")
    for r in s["findings"]:
        shot = f"shot {r['idx']}" if r["idx"] is not None else "cả dự án"
        lines.append(f"rà soát {'ĐỎ' if r['level'] == 'do' else 'vàng'} {shot} · {r['khau']} → đóng: {r['reason']}")
    return lines


def action_ids(conn, project_id: int) -> List[str]:
    """What `clean` would change (the confirmation is tied to exactly this set)."""
    s = stale(conn, project_id)
    return [f"j{r['job_id']}" for r in s["jobs"] if r["action"]] + [f"f{r['id']}" for r in s["findings"]]


def clean(p, project_id: int, who: Optional[str] = None) -> Dict[str, int]:
    """Do what `preview` said (recomputed now, never from a stale screen). Nothing deleted. Returns {"rejected", "resolved", "kept"}."""
    from . import access
    from .change_review import _now
    from .states import JobState
    access.need_edit(p, project_id, "dọn việc thừa của dự án")
    s = stale(p.conn, project_id)
    by = f"{WHO} ({who})" if who else WHO
    res = {"rejected": 0, "resolved": 0, "kept": 0}
    for r in s["jobs"]:
        if r["action"] != "reject":
            res["kept"] += 1
            continue
        p.transition(r["job_id"], JobState.REJECTED, actor=who or "user", note=f"🧹 {WHO}: {r['reason']}")
        res["rejected"] += 1
    for r in s["findings"]:
        p.conn.execute("UPDATE change_findings SET status='resolved', resolved_at=?, resolved_by=? WHERE id=? AND status='open'",
                       (_now(), f"{by}: {r['reason']}"[:300], r["id"]))
        res["resolved"] += 1
    res["kept"] += len(s["failed"])
    p.conn.commit()
    return res
