"""KLD-2 (người dùng duyệt 08/10 — docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md mục 4.12): "bản dùng cho shot".

#22 shot 8: QC loại take 560 (0,81 < 0,82), tự gen lại 569 (tệ hơn, 0,72); người dùng chọn 560 nhưng chuỗi nối (`start_from_prev_clip`), bản
dựng và bản đồ khâu đều lấy job số LỚN NHẤT → phải hoán đổi dòng 560 ↔ 569, và `qc_results` (theo số job) lệch nội dung tệp.
Bây giờ:
- mỗi take giữ tệp riêng: khi take mới tải về `NN.mp4`, tệp cũ vào thùng rác và `result_path` của take cũ trỏ theo (make_room);
- người chọn một take (`choose`, nút "✔ Dùng bản này cho shot" ở Bước 4, hoặc "Vẫn dùng bản này" = keep_rejected) → tệp của nó về `NN.mp4`,
  `scenes.data.chosen_video_job` = số job; các take khác của shot bị loại/hủy; không dòng job nào đổi số;
- người đọc "take của shot" (final_cut.collect_clips, runner._chain_frame, batch.chain_waits, lineage.scan → stage_map) gọi `used()`:
  bản đã chọn còn hợp lệ, nếu không thì job mới nhất như trước.
KHÔNG hoán đổi dòng job để chọn bản (điểm QC, review_log, job_events đi theo số job)."""
import json
import os
import shutil
from typing import List, Optional

from . import access, trash
from .states import JobState

KEY = "chosen_video_job"
WITH_FILE = ("succeeded", "pending_review", "approved", "rejected")
USABLE = ("succeeded", "pending_review", "approved")


def _same(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _data(conn, scene_id: int) -> dict:
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        return json.loads(row["data"] or "{}") if row else {}
    except ValueError:
        return {}


def mark(conn, scene_id: int, job_id: Optional[int]) -> None:
    """Write (or with None clear) the shot's chosen take."""
    data = _data(conn, scene_id)
    if job_id is None:
        if KEY not in data:
            return
        data.pop(KEY)
    else:
        data[KEY] = int(job_id)
    conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene_id))
    conn.commit()


def owner(conn, scene_id: int, path: str, exclude: Optional[int] = None) -> Optional[int]:
    """The take whose file `path` is: the newest video job of the shot linked to it (an older row linked to the same name was
    overwritten — its content is not there any more)."""
    for r in conn.execute("SELECT id, result_path FROM jobs WHERE scene_id=? AND type='video_gen' AND result_path IS NOT NULL"
                          " ORDER BY id DESC", (scene_id,)):
        if r["id"] != exclude and _same(r["result_path"], path):
            return r["id"]
    return None


def has_own_file(conn, job) -> bool:
    path = job["result_path"]
    return bool(path) and os.path.isfile(path) and owner(conn, job["scene_id"], path) == job["id"]


def chosen(conn, scene_id: int):
    """The take the person chose for the shot, while it is still usable and its file is its own; else None."""
    jid = _data(conn, scene_id).get(KEY)
    if not jid:
        return None
    job = conn.execute("SELECT * FROM jobs WHERE id=? AND scene_id=? AND type='video_gen'", (jid, scene_id)).fetchone()
    if job is None or job["state"] not in USABLE or not has_own_file(conn, job):
        return None
    return job


def used(conn, scene_id: int, skip_cancelled: bool = True):
    """THE take of the shot for every reader: the chosen one, else the newest video job (as before KLD-2)."""
    pick = chosen(conn, scene_id)
    if pick is not None:
        return pick
    return conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen'" + (" AND state!='cancelled'" if skip_cancelled else "")
                        + " ORDER BY id DESC LIMIT 1", (scene_id,)).fetchone()


def candidates(conn, scene_id: int) -> List:
    """Other takes of the shot that still have their own file (the person may pick one), oldest first."""
    cur = used(conn, scene_id)
    rows = conn.execute(f"SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN {WITH_FILE} ORDER BY id",
                        (scene_id,)).fetchall()
    return [r for r in rows if (cur is None or r["id"] != cur["id"]) and has_own_file(conn, r)]


def make_room(conn, data_dir: str, job, target: str) -> Optional[str]:
    """Before a new take is written to `target` (the shot's NN.mp4): the file there goes to the trash under the job it belongs to,
    and that job's result_path follows it — the older take stays reachable (and choosable). A new take ends an earlier choice."""
    prev = owner(conn, job["scene_id"], target, exclude=job["id"]) if os.path.isfile(target) else None
    moved = trash.move_to_trash(target, data_dir, job["project_id"], "videos", "bị thay bằng bản gen lại", prev or job["id"])
    if moved and prev:
        conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (moved, prev))
        conn.commit()
    mark(conn, job["scene_id"], None)
    return moved


def choose(p, data_dir: str, job_id: int, note: Optional[str] = None) -> None:
    """The person picks this take for its shot: its file becomes the shot's NN.mp4, it is approved, every other take of the shot is
    rejected (queued / failed ones cancelled) and `chosen_video_job` is set. Raises ValueError (Vietnamese) when it cannot be chosen."""
    access.need_edit_job(p, job_id, "chọn bản dùng cho shot")
    conn = p.conn
    job = p.job(job_id)
    if job is None or job["type"] != "video_gen":
        raise ValueError("chỉ chọn được bản video của một shot")
    if job["state"] not in WITH_FILE:
        raise ValueError(f"job {job_id} đang ở trạng thái {job['state']} — chưa có bản để chọn")
    if not has_own_file(conn, job):
        raise ValueError(f"job {job_id} không còn tệp riêng (đã bị bản sau ghi đè hoặc thùng rác đã dọn) — không chọn được")
    sid = job["scene_id"]
    if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND state='running' AND id!=?", (sid, job_id)).fetchone():
        raise ValueError("shot đang gen một bản khác — chờ bản đó xong (hoặc hủy) rồi mới chọn")
    idx = conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]
    pid = job["project_id"]
    dest = os.path.join(data_dir, str(pid), "videos", f"{idx:02d}.mp4")
    why = note or f"người chọn bản job {job_id} cho shot"
    if not _same(job["result_path"], dest):
        prev = owner(conn, sid, dest) if os.path.isfile(dest) else None
        moved = trash.move_to_trash(dest, data_dir, pid, "videos", f"đổi bản dùng cho shot sang job {job_id}", prev, idx)
        if moved and prev:
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (moved, prev))
        # the uncut original next to it belongs to the old take: a later re-cut must not cut the wrong clip
        trash.move_to_trash(os.path.splitext(dest)[0] + "_raw.mp4", data_dir, pid, "videos", "bản gốc chưa cắt của bản cũ", prev, idx)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(job["result_path"], dest)
        # rows still linked to NN.mp4 from before KLD-2 hold no file of their own (it was overwritten): unlinked, not left pointing
        # at the chosen take's content
        for r in conn.execute("SELECT id, result_path FROM jobs WHERE scene_id=? AND type='video_gen' AND id!=?", (sid, job_id)).fetchall():
            if _same(r["result_path"], dest):
                conn.execute("UPDATE jobs SET result_path=NULL WHERE id=?", (r["id"],))
        conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, job_id))
        conn.commit()
    for other in conn.execute("SELECT id, state FROM jobs WHERE scene_id=? AND type='video_gen' AND id!=?", (sid, job_id)).fetchall():
        state = JobState(other["state"])
        if state in (JobState.SUCCEEDED, JobState.PENDING_REVIEW, JobState.APPROVED):
            p._log_review(other["id"], "user", "reject", f"người chọn bản job {job_id}")
            p.transition(other["id"], JobState.REJECTED, actor="user", note=f"người chọn bản job {job_id}")
        elif state == JobState.FAILED:
            p.transition(other["id"], JobState.RETRYABLE, note=f"người chọn bản job {job_id}")
            p.transition(other["id"], JobState.CANCELLED, actor="user", note=f"người chọn bản job {job_id}")
        elif state in (JobState.QUEUED, JobState.RETRYABLE):
            p.transition(other["id"], JobState.CANCELLED, actor="user", note=f"người chọn bản job {job_id}")
        conn.execute("UPDATE jobs SET escalated=0 WHERE id=?", (other["id"],))
    state = p.state(job_id)
    if state == JobState.REJECTED:
        p._log_review(job_id, "user", "approve", why)
        p.transition(job_id, JobState.APPROVED, actor="user", note=why)
    elif state in (JobState.SUCCEEDED, JobState.PENDING_REVIEW):
        p.approve(job_id, "user", why)
    conn.execute("UPDATE scenes SET state='ready' WHERE id=? AND state='needs_attention'", (sid,))
    conn.commit()
    mark(conn, sid, job_id)
