"""S14.30 (người dùng chốt 05/10): một dự án "HOÀN THIỆN" = đã XUẤT BẢN GIAO — bước Bản giao (`delivery.deliver`: dựng → phụ đề → card →
nhãn AI → các kích thước) chạy xong — KHÔNG phải lần ghép bản cuối đầu tiên (`outputs` 'final' / FINAL_VIDEO.mp4 có ngay từ "Dựng thử").

Tín hiệu riêng: bảng `deliveries` (core/db.py SCHEMA, CREATE TABLE IF NOT EXISTS — không đụng bảng `outputs` có CHECK). Ghi đúng lúc xuất
thành công (`delivery.deliver` cuối chuỗi); render lỗi / một kích thước xuất lỗi → không ghi. Một nguồn duy nhất cho mọi chỗ mang nghĩa
"dự án đã xong": giới hạn theo người (core/person_limits.is_finished gọi vào đây), Kho dự án đã xong (core/archive), hộp 📥, ⌂ "Sản phẩm
đã hoàn tất". Chỗ mang nghĩa "đã có bản ghép cuối" (autopilot.progress, effectiveness.finished_projects…) giữ định nghĩa cũ.

Dự án cũ: `backfill()` (chạy một lần qua tools/backfill_delivered.py, idempotent) ghi tín hiệu cho dự án đã có bản giao thật; dự án chỉ có
bản ghép thì KHÔNG còn tính là xong — báo số dự án đổi trạng thái (in + diag 'delivered_backfill'), không im lặng.
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

DEFAULT_OUTPUT_ROOT = r"D:\AI-Video-Output"
"""Thư mục giao ngoài git (memory reference_video_exports): mỗi bản giao một thư mục <ngày>_du-an-<id>. Biến DELIVERY_OUTPUT_ROOT đổi được."""
FOLDER_RE = re.compile(r"_du-an-(\d+)$", re.IGNORECASE)
VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv")
HINT = "xuất bản giao để tính là xong"
"""Câu dùng chung khi một dự án có bản cuối nhưng chưa xuất bản giao (lời báo giới hạn, 📥)."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _data_dir(data_dir: Optional[str]) -> str:
    return data_dir or os.environ.get("PIPELINE_DATA", os.path.join("data", "projects"))


def is_delivered(conn, project_id: int) -> bool:
    """The ONE answer to "is this project finished?" (S14.30)."""
    return conn.execute("SELECT 1 FROM deliveries WHERE project_id=? LIMIT 1", (project_id,)).fetchone() is not None


def delivered_ids(conn) -> List[int]:
    return [r[0] for r in conn.execute("SELECT DISTINCT project_id FROM deliveries ORDER BY project_id")]


def latest(conn, project_id: int):
    return conn.execute("SELECT * FROM deliveries WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()


def has_render(conn, project_id: int, data_dir: Optional[str] = None) -> bool:
    """A final cut exists (an outputs 'final' row, or a pre-v2 <data>/<id>/output/FINAL_VIDEO.mp4) — NOT 'finished' by itself."""
    if conn.execute("SELECT 1 FROM outputs WHERE project_id=? AND kind='final' LIMIT 1", (project_id,)).fetchone() is not None:
        return True
    return os.path.exists(os.path.join(_data_dir(data_dir), str(project_id), "output", "FINAL_VIDEO.mp4"))


def rendered_not_delivered(conn, project_id: int, data_dir: Optional[str] = None) -> bool:
    """Has a final cut but the delivery was never exported: the person is told to deliver it to count it as done."""
    return not is_delivered(conn, project_id) and has_render(conn, project_id, data_dir)


def mark(conn, project_id: int, path: str, by: Optional[str] = None, source: str = "deliver", manifest: Optional[Dict] = None) -> int:
    """Record a delivery (commits). Called by delivery.deliver after the whole chain worked, and by backfill()."""
    cur = conn.execute("INSERT INTO deliveries (project_id, path, source, manifest, delivered_at, delivered_by) VALUES (?,?,?,?,?,?)",
                       (project_id, path, source, json.dumps(manifest or {}, ensure_ascii=False), _now(), by))
    conn.commit()
    return cur.lastrowid


# ---- chuyển đổi dự án cũ ----------------------------------------------------------------------------------------------------------------
def _folders(output_root: Optional[str]) -> Dict[int, str]:
    """{project id: delivery folder holding at least one video} under the delivery root (<ngày>_du-an-<id>; the newest name wins)."""
    out: Dict[int, str] = {}
    if not output_root or not os.path.isdir(output_root):
        return out
    for name in sorted(os.listdir(output_root)):
        m = FOLDER_RE.search(name)
        full = os.path.join(output_root, name)
        if not m or not os.path.isdir(full):
            continue
        if any(f.lower().endswith(VIDEO_EXT) for f in os.listdir(full)):
            out[int(m.group(1))] = full
    return out


def _evidence(conn, pid: int, folders: Dict[int, str], data_dir: str) -> Optional[Dict]:
    """Proof that the old project WAS delivered, strongest first:
    1. a delivery folder <root>/<ngày>_du-an-<id> with a video in it;
    2. a 'final' outputs row whose manifest has 'final_qc' — written ONLY at the end of delivery.deliver (the whole chain ran);
    3. the automatic run reached DONE (its last step is delivery.deliver) and the final cut is there."""
    if pid in folders:
        return {"source": "backfill_folder", "path": folders[pid]}
    export_failed = conn.execute("SELECT 1 FROM diag_events WHERE project_id=? AND code='export' AND severity IN ('warn','error') LIMIT 1",
                                 (pid,)).fetchone() is not None    # rà: final_qc is written even when one export size failed
    for row in ([] if export_failed else
                conn.execute("SELECT path, manifest FROM outputs WHERE project_id=? AND kind='final' ORDER BY id DESC", (pid,))):
        try:
            if "final_qc" in json.loads(row["manifest"] or "{}"):
                return {"source": "backfill_deliver", "path": row["path"]}
        except ValueError:
            continue
    st = conn.execute("SELECT autopilot_state FROM projects WHERE id=?", (pid,)).fetchone()
    if st is not None and st["autopilot_state"] == "done" and has_render(conn, pid, data_dir):
        fin = conn.execute("SELECT path FROM outputs WHERE project_id=? AND kind='final' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        return {"source": "backfill_autopilot_done", "weak": True,    # rà: an old run could be DONE with only a cut — the person checks
                "path": fin["path"] if fin else os.path.join(data_dir, str(pid), "output", "FINAL_VIDEO.mp4")}
    return None


def backfill(conn, data_dir: Optional[str] = None, output_root: Optional[str] = None, apply: bool = False) -> Dict:
    """One-time conversion of the old projects (idempotent: a project already delivered is left as it is).
    Returns {"apply", "marked": [{project_id, source, path}], "already": [ids], "rendered_only": [ids], "summary"} where
    rendered_only = projects with a final cut and NO proof of delivery: under S14.18 they counted as finished, now they do not.
    With apply=True the rows are written and the summary goes to diag (code 'delivered_backfill')."""
    data_dir = _data_dir(data_dir)
    output_root = output_root if output_root is not None else os.environ.get("DELIVERY_OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT)
    folders = _folders(output_root)
    marked, already, rendered_only = [], [], []
    has_table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='deliveries'").fetchone() is not None   # read-only dry run
    for r in conn.execute("SELECT id FROM projects ORDER BY id").fetchall():
        pid = r[0]
        if has_table and is_delivered(conn, pid):
            already.append(pid)
            continue
        ev = _evidence(conn, pid, folders, data_dir)
        if ev is not None:
            marked.append({"project_id": pid, **ev})
        elif has_render(conn, pid, data_dir):
            rendered_only.append(pid)
    if apply:
        for m in marked:
            mark(conn, m["project_id"], m["path"], by="backfill S14.30", source=m["source"], manifest={"evidence": m["path"]})
    ids = lambda xs: ", ".join(f"#{i}" for i in xs) or "—"      # noqa: E731
    weak = [m["project_id"] for m in marked if m.get("weak")]
    summary = (f"S14.30 chuyển đổi 'hoàn thiện' = đã xuất bản giao ({'ĐÃ GHI' if apply else 'chạy thử, chưa ghi'}): "
               f"{len(marked)} dự án ghi là đã giao ({ids([m['project_id'] for m in marked])}); "
               f"{len(rendered_only)} dự án có bản cuối nhưng chưa xuất bản giao — KHÔNG còn tính là xong ({ids(rendered_only)}); "
               + (f"⚠ {len(weak)} dự án chỉ có bằng chứng YẾU (chạy tự động xong, không thấy bản giao) — xem lại trước khi ghi: {ids(weak)}; "
                  if weak else "")
               + f"{len(already)} dự án đã có tín hiệu từ trước. Thư mục giao: {output_root} ({len(folders)} thư mục _du-an-<id> có video).")
    if apply:
        from . import diag
        diag.record(conn, "render", "info", summary, "delivered_backfill")
    return {"apply": apply, "marked": marked, "already": already, "rendered_only": rendered_only, "summary": summary,
            "output_root": output_root}
