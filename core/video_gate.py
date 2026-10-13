"""V7 (rà gốc video #27 13/10, G1 — 25 job video bỏ): cổng trước khi GỬI một clip (cờ `video_gate`, mặc định tắt, 0 USD).

Ảnh khung đầu được duyệt rồi xếp video ngay, sau đó mới thấy nền sai 3D / shot kề đổi nền → bỏ video + bản cao. Cổng giữ job video
(đang chờ, có lý do — runner.WAIT_REASONS, không hỏng job) tới khi:
  1. ảnh khung đầu của shot có render 3D đã qua kiểm nền `plate_layout_qc.check_strict` (không ĐỎ); chưa có kết quả → đo ngay (OpenCV,
     0 USD) và ghi diag như lúc ảnh về; ĐỎ → giữ, trừ khi người bấm "Bỏ qua" có LÝ DO (bảng video_gate_skips, theo đúng ảnh đó);
  2. CẢ nhóm shot liền mạch (cùng cảnh kịch bản + `sequence` > 0, shots.sequence_rows) đã có ảnh duyệt và không ảnh nào đang vẽ lại
     (tránh gen shot 3 trước khi shot 2 đổi nền).
Không đo được (thiếu OpenCV / render hỏng) → không giữ, ghi VÀNG (không im lặng). Bản cao nâng từ nháp đã duyệt không qua cổng (runner).
Chưa làm: checklist trạng thái nhân vật (bóng mờ / giày / đạo cụ) do QC ảnh chấm — cần tiêu chí QC riêng (tốn Claude), để việc sau.
"""
import json
import time
from typing import Dict, List, Optional

FLAG = "video_gate"
CODE = "video_gate"
LIVE_IMAGE = ("queued", "running", "retryable", "succeeded", "pending_review")


def enabled() -> bool:
    from . import features
    try:
        return features.on(FLAG)
    except KeyError:
        return False


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def skipped(conn, image_job_id: int) -> Optional[Dict]:
    """Lần người bấm Bỏ qua cổng nền của ảnh này (mới nhất), hoặc None."""
    try:
        row = conn.execute("SELECT * FROM video_gate_skips WHERE image_job_id=? ORDER BY id DESC LIMIT 1", (image_job_id,)).fetchone()
    except Exception:  # noqa: BLE001 - an old database without the table: nothing skipped
        return None
    return dict(row) if row else None


def skip(conn, image_job_id: int, reason: str, who: Optional[str] = None) -> None:
    """Người chấp nhận nền của ảnh này dù kiểm nền ĐỎ — bắt buộc có lý do (không bỏ qua im lặng)."""
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise ValueError("Cần ghi lý do bỏ qua kiểm nền (ít nhất vài chữ)")
    row = conn.execute("SELECT scene_id FROM jobs WHERE id=? AND type='image_gen'", (image_job_id,)).fetchone()
    if row is None:
        raise ValueError(f"không có ảnh job #{image_job_id}")
    conn.execute("INSERT INTO video_gate_skips(image_job_id, scene_id, reason, who, at) VALUES (?,?,?,?,?)",
                 (image_job_id, row["scene_id"], reason, who, _now()))
    conn.commit()


def _say(conn, job, severity: str, msg: str) -> None:
    from . import diag
    diag.record(conn, "video", severity, msg, CODE, job["project_id"], scene_id=job["scene_id"], job_id=job["id"])


def plate_verdict(conn, data_dir: str, project_id: int, image_scene_id: int, image_job_id: int) -> Optional[tuple]:
    """(severity, words) của kiểm nền ảnh này: kết quả đã ghi (diag plate_layout của job ảnh), chưa có → đo ngay. None = shot không có
    render 3D (không có gì để so)."""
    from . import place_refs, plate_layout_qc, diag
    if place_refs.shot_ref(data_dir, project_id, image_scene_id) is None:
        return None
    row = conn.execute("SELECT severity, message FROM diag_events WHERE job_id=? AND code=? ORDER BY last_at DESC, id DESC LIMIT 1",
                       (image_job_id, plate_layout_qc.CODE)).fetchone()
    if row is not None:
        return row["severity"], row["message"]
    job = conn.execute("SELECT result_path FROM jobs WHERE id=?", (image_job_id,)).fetchone()
    path = job["result_path"] if job else None
    if not path:
        return ("warn", "VÀNG: ảnh khung đầu không còn tệp để kiểm nền")
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    got = plate_layout_qc.check_strict(conn, data_dir, project_id, image_scene_id, image_job_id, path, place_refs.resolution_of(proj))
    diag.record(conn, "image", got[0], got[1], plate_layout_qc.CODE, project_id, scene_id=image_scene_id, job_id=image_job_id)
    return got


def group_missing(conn, scene_id: int) -> List[str]:
    """Shot trong nhóm liền mạch của shot này chưa có ảnh duyệt / đang vẽ lại ảnh: ['S03 chưa duyệt ảnh', …]."""
    from . import lineage, shots
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    if not isinstance(data.get("sequence"), int) or isinstance(data.get("sequence"), bool) or data["sequence"] <= 0:
        return []                                       # sequence 0 / trống = không nhóm (Bước 1: "0 = không nhóm")
    out = []
    for r in shots.sequence_rows(conn, scene_id):
        if r["id"] == scene_id or not shots.needs_own_image(conn, r["id"]):
            continue
        img = lineage.approved_image_id(conn, r["id"])
        label = f"S{r['idx']:02d}"
        if img is None:
            out.append(f"{label} chưa duyệt ảnh")
            continue
        q = ",".join("?" * len(LIVE_IMAGE))
        if conn.execute(f"SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND id>? AND state IN ({q})",
                        (r["id"], img, *LIVE_IMAGE)).fetchone():
            out.append(f"{label} đang vẽ lại ảnh")
    return out


def hold(conn, data_dir: str, job) -> Optional[str]:
    """Lý do GIỮ clip này trước khi gửi (tiếng Việt), None = được gửi. Cờ tắt → None (như trước)."""
    if not enabled() or not job["scene_id"]:
        return None
    from . import lineage, shots
    sid = job["scene_id"]
    img_sid = shots.image_scene(conn, sid)
    img = lineage.approved_image_id(conn, img_sid)
    why = []
    if img is not None:
        try:
            got = plate_verdict(conn, data_dir, job["project_id"], img_sid, img)
        except Exception as e:  # noqa: BLE001 - a measuring problem never holds by itself: said (VÀNG)
            _say(conn, job, "warn", f"VÀNG cổng video: không kiểm được nền ảnh khung đầu ({type(e).__name__}: {e}) — gửi, cần xem bằng mắt")
            got = None
        if got and got[0] == "error":
            s = skipped(conn, img)
            if s is None:
                why.append(f"ảnh khung đầu (job {img}) lệch nền 3D — vẽ lại ảnh hoặc bấm 'Bỏ qua kiểm nền' kèm lý do ở Bước 4 "
                           f"({str(got[1])[:160]})")
    missing = group_missing(conn, sid)
    if missing:
        why.append("nhóm shot liền mạch chưa đủ ảnh duyệt: " + ", ".join(missing[:6]) + (f" (+{len(missing) - 6})" if len(missing) > 6 else "")
                   + " — clip gửi khi cả nhóm đã duyệt ảnh")
    return ("Cổng ảnh → video: " + "; ".join(why)) if why else None


def red_images(conn, data_dir: str, project_id: int) -> List[Dict]:
    """Màn Bước 4: shot có clip đang chờ mà ảnh khung đầu bị kiểm nền ĐỎ chưa ai bỏ qua — [{scene_id, idx, image_job_id, msg}]."""
    from . import lineage, shots
    out = []
    rows = conn.execute("SELECT DISTINCT s.id, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.project_id=? AND "
                        "j.type='video_gen' AND j.state='queued' ORDER BY s.idx", (project_id,)).fetchall()
    for r in rows:
        img_sid = shots.image_scene(conn, r["id"])
        img = lineage.approved_image_id(conn, img_sid)
        if img is None or skipped(conn, img):
            continue
        hit = conn.execute("SELECT severity, message FROM diag_events WHERE job_id=? AND code='plate_layout' ORDER BY last_at DESC, "
                           "id DESC LIMIT 1", (img,)).fetchone()
        if hit and hit["severity"] == "error":
            out.append({"scene_id": r["id"], "idx": r["idx"], "image_job_id": img, "msg": hit["message"]})
    return out
