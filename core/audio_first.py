"""Timeline by sound first (kế hoạch sau #8, S2 — lỗi 1.2: #8 planned 58 s and came out 83 s, because the voices were made after the
clips and every clip was then stretched to its line).

With the feature `audio_first` on, the run voices every line right after the Director (a few cents of TTS), sizes each shot's
`duration_s` to its real voice, checks the total against the script's target (±10 %) and locks the timeline before a picture is paid
for. Everything after — images, motion, clips, music — works from the locked seconds."""
import json
import math
from typing import Dict, List, Optional

LENGTH_TOLERANCE = 0.10      # the script's target ± 10 % (plan S2.3)


def fit_shots(conn, project_id: int, data_dir: str) -> List[Dict]:
    """Each voiced shot gets at least the seconds its real voice needs (lead + lines + gaps + tail). Only lengthens: a shot longer
    than its line keeps the Director's length (a reaction, a held look). Returns the changes."""
    from . import voice
    changes = []
    for sid, secs in voice.scene_seconds(conn, project_id, data_dir).items():
        row = conn.execute("SELECT idx, data FROM scenes WHERE id=?", (sid,)).fetchone()
        if row is None:
            continue
        data = json.loads(row["data"] or "{}")
        need = round(math.ceil((voice.LEAD + secs + voice.TAIL) * 10) / 10, 1)
        have = float(data.get("duration_s") or 0)
        if need > have + 0.05:
            data["duration_s"] = need
            data["duration_from_voice"] = {"was": have, "voice_s": secs}
            conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
            changes.append({"scene_id": sid, "idx": row["idx"], "from": have, "to": need})
    conn.commit()
    return changes


def planned_total(conn, project_id: int) -> float:
    return round(sum(float(json.loads(r["data"] or "{}").get("duration_s") or 0)
                     for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (project_id,))), 1)


def length_check(conn, project_id: int) -> Dict:
    """{"total", "target": (lo, hi) | None, "off": fraction outside the target (0 inside), "ok"}."""
    from .prompts import target_seconds
    row = conn.execute("SELECT script_text FROM projects WHERE id=?", (project_id,)).fetchone()
    target = target_seconds(row["script_text"] if row else "")
    total = planned_total(conn, project_id)
    if not target or not total:
        return {"total": total, "target": target, "off": 0.0, "ok": True}
    lo, hi = target
    off = (lo - total) / lo if total < lo else ((total - hi) / hi if total > hi else 0.0)
    return {"total": total, "target": target, "off": round(off, 3), "ok": abs(off) <= LENGTH_TOLERANCE}


def speakers_without_voice(conn, project_id: int) -> List[str]:
    from . import voice
    return sorted({ln["speaker"] for ln in voice.planned_lines(conn, project_id) if ln["speaker"] and not ln["voice"]})


def lock_note(check: Dict) -> str:
    tgt = f"{check['target'][0]}–{check['target'][1]} s" if check.get("target") else "kịch bản không ghi thời lượng"
    return f"timeline khóa theo giọng thật: {check['total']:g} s (mục tiêu {tgt})"


def gate_message(check: Dict) -> Optional[str]:
    """The question put to the person when the voiced plan misses the target by more than 10 % (S2.3) — before any picture."""
    if check["ok"]:
        return None
    lo, hi = check["target"]
    way = "dài hơn" if check["off"] > 0 else "ngắn hơn"
    return (f"Độ dài theo giọng thật {check['total']:g} s {way} mục tiêu {lo}–{hi} s ({abs(check['off']) * 100:.0f} %) — trước khi làm ảnh / "
            "video: sửa kịch bản / bảng shot (bớt câu, bớt shot) ở Bước 1 rồi chạy tiếp, hoặc bấm “Chấp nhận độ dài này”.")
