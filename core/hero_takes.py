"""S0.14 T4 (người dùng duyệt 2026-09-30): "ngân sách lần gen theo độ quan trọng" — cờ `hero_takes`, mặc định TẮT.

Nguồn: người làm phim AI Trung Quốc ("cảnh xịn = gen nhiều rồi chọn", 2–3 lần là thường — research/craft/trung_quoc/LUOT_2.md mục 2,
nguồn [26][27][28]). Dự án có trần chi và luật "gen lại ≤ 2 lần, phải đổi đầu vào" (docs/CHUAN_XAY_DUNG.md) → không gen nhiều cho mọi
shot; chỉ shot ⭐ (`shot_role` hero, hoặc `money_shot`) có THÊM MỘT bản cùng đầu vào để chọn. Đây không phải gen lại vì lỗi: hai bản là hai
ứng viên của lần đầu, nên cùng đầu vào là đúng (seed khác nhau của model); lần gen lại sau đó vẫn theo luật cũ.

Luồng (autopilot `_videos_phase`, sau QC clip, trước khi tự duyệt):
  1. clip đầu tiên của shot ⭐ gửi riêng (không nằm trong clip nhóm) có kết quả → cất tệp bản 1 (`NN_t4a.mp4`, + `NN_raw_t4a.mp4`)
     rồi tạo job bản 2 (tính vào lượt gửi của shot + trần job + trần tiền như mọi job — hết lượt / hết trần thì không tạo, có báo);
     bản 1 bị giữ, không tự duyệt, tới khi chọn xong (`hold_reason`).
  2. bản 2 có kết quả → cất tệp `NN_t4b.mp4`; đo cả hai bằng lớp 0 (core/clip_measure: nhìn lệch ảnh storyboard, giật / đứng hình,
     dấu đỏ lọt, khớp môi khi có thoại) → bản ít lỗi đo được hơn thắng, tệp của nó chép về `NN.mp4`, bản kia bị loại (không sinh
     lại); bằng nhau → giữ CẢ HAI cho người chọn ở Bước 4 (không đoán).
  3. người duyệt một bản ở Bước 4 → bản kia bị loại.
Shot ⭐ nằm trong clip nhóm (Seedance nhóm / Kling multi-shot) chưa áp: sinh lại cả nhóm tốn gấp nhiều lần — báo một lần, không im lặng.
Trạng thái lưu trong app_settings key "hero_takes:<pid>" = {scene_id: {"first", "second", "picked", "why"}}.
"""
import json
import os
import shutil
from typing import Callable, Dict, List, Optional

from . import features
from .states import JobState

FLAG = "hero_takes"
RESULT = ("succeeded", "pending_review", "approved")
HOLD_WAIT = "T4: chờ bản thứ 2 của shot ⭐ để chọn"
HOLD_TIE = "T4: 2 bản của shot ⭐ đo ngang nhau — bạn chọn một bản ở Bước 4"


def on() -> bool:
    return features.on(FLAG)


def is_hero(data: Dict) -> bool:
    return (data or {}).get("shot_role") == "hero" or bool((data or {}).get("money_shot"))


def solo(conn, scene_id: int) -> bool:
    """Sent on its own (not a part of a group clip) — the only case T4 covers."""
    from . import shots
    if conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND group_leader IS NOT NULL", (scene_id,)).fetchone():
        return False
    return len(shots.group_of(conn, scene_id) or []) < 2


def _key(pid: int) -> str:
    return f"hero_takes:{pid}"


def load(conn, pid: int) -> Dict[str, Dict]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_key(pid),)).fetchone()
    try:
        return json.loads(row[0]) if row else {}
    except ValueError:
        return {}


def save(conn, pid: int, data: Dict[str, Dict]) -> None:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (_key(pid), json.dumps(data)))
    conn.commit()


def hold_reason(conn, job) -> Optional[str]:
    """Why this clip must wait for the person / for its sibling instead of being approved automatically (None = no T4 reason)."""
    rec = load(conn, job["project_id"]).get(str(job["scene_id"]))
    if not rec or job["id"] not in (rec.get("first"), rec.get("second")):
        return None
    if rec.get("picked") == "tie":
        return HOLD_TIE
    if not rec.get("picked"):
        return HOLD_WAIT
    return None


def _state(conn, job_id: Optional[int]) -> Optional[str]:
    row = conn.execute("SELECT state FROM jobs WHERE id=?", (job_id,)).fetchone() if job_id else None
    return row[0] if row else None


def _stash(path: Optional[str], tag: str) -> Optional[str]:
    """Copy <dir>/NN.mp4 (and its NN_raw.mp4) to NN_<tag>.mp4 / NN_raw_<tag>.mp4; the path of the copy."""
    if not path or not os.path.exists(path):
        return None
    base, ext = os.path.splitext(path)
    out = f"{base}_{tag}{ext}"
    shutil.copy2(path, out)
    raw = f"{base}_raw{ext}"
    if os.path.exists(raw):
        shutil.copy2(raw, f"{base}_raw_{tag}{ext}")
    return out


def _restore(copy: str, dest: str, tag: str) -> None:
    """Put a stashed take back as the shot's clip (NN.mp4 and, when stashed, NN_raw.mp4)."""
    shutil.copy2(copy, dest)
    base, ext = os.path.splitext(dest)
    raw = f"{base}_raw_{tag}{ext}"
    if os.path.exists(raw):
        shutil.copy2(raw, f"{base}_raw{ext}")


def score(measured: Optional[Dict]) -> Optional[int]:
    """Fewer layer-0 flags = better; None = nothing could be measured."""
    if measured is None:
        return None
    return len(measured.get("flags") or [])


def pick(a: Optional[Dict], b: Optional[Dict]) -> Optional[str]:
    """'first' / 'second' when the numbers tell them apart, None when they do not (the person chooses)."""
    sa, sb = score(a), score(b)
    if sa is None or sb is None or sa == sb:
        return None
    return "first" if sa < sb else "second"


def drop(p, job_id: int, note: str) -> None:
    """Take the losing take out of use: rejected, never respawned (it was an extra candidate, not a failed clip)."""
    st = _state(p.conn, job_id)
    if st in ("succeeded", "pending_review", "approved"):
        p._log_review(job_id, "ai_agent", "reject", note)
        p.transition(job_id, JobState.REJECTED, actor="ai_agent", note=note)
    elif st in ("queued",):
        p.cancel(job_id, actor="ai_agent")


def _measure(conn, data_dir: str, pid: int, scene_id: int, clip: Optional[str]) -> Optional[Dict]:
    if not clip or not os.path.exists(clip):
        return None
    from . import clip_measure, shots
    picture = shots.approved_image_path(conn, data_dir, pid, scene_id)
    try:
        return clip_measure.measure(clip, picture)
    except Exception:  # noqa: BLE001 - no OpenCV / unreadable clip: the person chooses
        return None


def step(p, pid: int, data_dir: str, can_send: Callable[[int], Optional[str]],
         measure: Optional[Callable[[str, int, str], Optional[Dict]]] = None) -> List[str]:
    """One autopilot tick of T4 for the project; returns lines for the autopilot log. can_send(scene_id) -> None when one more clip may
    be sent, else the reason (shot's send cap, job cap). measure(path, scene_id, data_dir) is injectable for tests."""
    if not on():
        return []
    measure = measure or (lambda path, sid, d: _measure(p.conn, d, pid, sid, path))
    conn, out = p.conn, []
    recs = load(conn, pid)
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    for r in rows:
        data = json.loads(r["data"] or "{}")
        sid, key = r["id"], str(r["id"])
        if not is_hero(data):
            continue
        rec = recs.get(key)
        if rec is None:
            first = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state IN ('succeeded','pending_review',"
                                 "'approved') ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
            if first is None:
                continue
            if not solo(conn, sid):
                recs[key] = {"first": first["id"], "picked": "skipped", "why": "shot ⭐ nằm trong clip nhóm — T4 chưa áp (sinh lại cả nhóm)"}
                out.append(f"S{r['idx']:02d} ⭐: nằm trong clip nhóm — không gen bản thứ 2 (T4 chỉ áp shot gửi riêng)")
                continue
            why = can_send(sid)
            if why:
                recs[key] = {"first": first["id"], "picked": "skipped", "why": why}
                out.append(f"S{r['idx']:02d} ⭐: không gen bản thứ 2 — {why}")
                continue
            copy = _stash(first["result_path"], "t4a")
            if copy is None:
                recs[key] = {"first": first["id"], "picked": "skipped", "why": "không thấy tệp clip bản 1"}
                out.append(f"S{r['idx']:02d} ⭐: không thấy tệp clip bản 1 — không gen bản thứ 2")
                continue
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (copy, first["id"]))
            conn.commit()
            second = p.create_job(sid, "video_gen")
            recs[key] = {"first": first["id"], "second": second, "dest": first["result_path"]}
            out.append(f"S{r['idx']:02d} ⭐: gen bản thứ 2 để chọn (T4, cùng đầu vào)")
            continue
        if rec.get("picked"):
            if rec["picked"] == "tie":                        # the person approved one of the two at Step 4 -> the other goes
                sa, sb = _state(conn, rec["first"]), _state(conn, rec.get("second"))
                if "approved" in (sa, sb) and sa != sb:
                    keep, lose = (rec["first"], rec["second"]) if sa == "approved" else (rec["second"], rec["first"])
                    drop(p, lose, "T4: người chọn bản kia")
                    if keep == rec["first"] and rec.get("dest"):
                        _restore(rec["copy_a"], rec["dest"], "t4a")
                        conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (rec["dest"], keep))
                    rec["picked"] = "first" if keep == rec["first"] else "second"
                    rec["why"] = "người chọn ở Bước 4"
                    out.append(f"S{r['idx']:02d} ⭐: bạn chọn bản {1 if keep == rec['first'] else 2} — bản kia bị loại")
            continue
        s2 = _state(conn, rec.get("second"))
        if s2 in ("rejected", "cancelled") or (s2 == "failed" and conn.execute(
                "SELECT escalated FROM jobs WHERE id=?", (rec["second"],)).fetchone()[0]):
            _restore(conn.execute("SELECT result_path FROM jobs WHERE id=?", (rec["first"],)).fetchone()[0], rec["dest"], "t4a")
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (rec["dest"], rec["first"]))
            rec.update(picked="first", why="bản 2 không có kết quả")
            out.append(f"S{r['idx']:02d} ⭐: bản 2 không có kết quả — dùng bản 1")
            continue
        if s2 not in RESULT:
            continue                                          # still being made (or retrying after a transient failure)
        second = conn.execute("SELECT * FROM jobs WHERE id=?", (rec["second"],)).fetchone()
        copy_b = _stash(second["result_path"], "t4b") or second["result_path"]
        copy_a = conn.execute("SELECT result_path FROM jobs WHERE id=?", (rec["first"],)).fetchone()[0]
        rec.update(copy_a=copy_a, copy_b=copy_b)
        if _state(conn, rec["first"]) not in RESULT:          # the person threw take 1 away meanwhile
            rec.update(picked="second", why="bản 1 đã bị loại")
            out.append(f"S{r['idx']:02d} ⭐: bản 1 đã bị loại — dùng bản 2")
            continue
        ma, mb = measure(copy_a, sid, data_dir), measure(copy_b, sid, data_dir)
        rec["flags"] = {"first": score(ma), "second": score(mb)}
        win = pick(ma, mb)
        if win is None:
            rec.update(picked="tie", why="đo lớp 0 ngang nhau (hoặc không đo được)")
            out.append(f"S{r['idx']:02d} ⭐: 2 bản đo ngang nhau — giữ cả hai, bạn chọn ở Bước 4")
            continue
        keep, lose = (rec["first"], rec["second"]) if win == "first" else (rec["second"], rec["first"])
        drop(p, lose, f"T4: bản kia ít lỗi đo được hơn ({rec['flags']['first']} vs {rec['flags']['second']} cờ)")
        if win == "first":
            _restore(copy_a, rec["dest"], "t4a")
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (rec["dest"], keep))
            conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (copy_b, lose))
        rec.update(picked=win, why=f"lớp 0: bản 1 {rec['flags']['first']} cờ, bản 2 {rec['flags']['second']} cờ")
        out.append(f"S{r['idx']:02d} ⭐: chọn bản {1 if win == 'first' else 2} ({rec['why']})")
    conn.commit()
    save(conn, pid, recs)
    return out


def extra_clips(conn, pid: int, scene_ids: List[int]) -> List[int]:
    """For the estimate: the shots among `scene_ids` that T4 would send twice (flag on, ⭐, sent on their own, not decided yet)."""
    if not on():
        return []
    recs = load(conn, pid)
    out = []
    for sid in scene_ids:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        if row and is_hero(json.loads(row[0] or "{}")) and str(sid) not in recs and solo(conn, sid):
            out.append(sid)
    return out
