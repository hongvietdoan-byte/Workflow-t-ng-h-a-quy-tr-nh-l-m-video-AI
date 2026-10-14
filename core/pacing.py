"""Nhịp phim của dự án: "normal" (mặc định, hành vi y cũ) | "fast" — nhịp nhanh, ít khoảng lặng (người dùng 14/10, thử ở tập 2 #31).

Một LỰA CHỌN của dự án (cột `projects.pacing`, NULL = normal), không kế thừa sang dự án mới (không có trong
`project_defaults.INHERIT`). Bốn chỗ đọc nó, và mọi chỗ trả về y cũ khi normal:
  1. `director_block(proj)` / `screenwriter_block(proj)` — cách nghĩ nhịp nhanh (knowledge/craft/nhip_nhanh.md) cho Đạo diễn (một lượt,
     Tầng A, Tầng B) và Biên kịch; normal → "" (prompt không đổi một byte).
  2. `check_plan(p, pid)` — sau Đạo diễn, 0 USD: giây đọc lời mỗi cảnh (âm tiết ÷ (dialogue.RATE × tốc độ giọng)) so tổng giây shot →
     diag VÀNG có số liệu; không chặn gì.
  3. `line_start(...)` — voice.place_on_timeline: câu sau cách câu trước ≤ FAST_LINE_GAP (gối tiếng qua cú cắt tối đa FAST_J_MAX).
  4. `tighten(...)` — delivery.render: shot có lời mà sau câu cuối còn lặng > FAST_TAIL_MAX thì cắt bớt đuôi (bản sao, clip gốc giữ nguyên).
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

MODES = {"normal": "Bình thường", "fast": "Nhanh — ít khoảng lặng (thử)"}
DEFAULT = "normal"

FAST_LINE_GAP = 0.2      # giữa hai câu liền nhau (≤ 0,25 s người dùng đặt)
FAST_J_MAX = 0.5         # câu của shot sau được vào trước cú cắt tối đa chừng này (J-cut), không sớm hơn
FAST_TAIL_MAX = 0.5      # lặng sau câu cuối của một shot có lời giữ tối đa chừng này
FAST_MIN_SHOT = 1.0      # cắt đuôi không bao giờ làm shot ngắn hơn
GAP_WARN_S = 1.0         # check_plan: chỗ trống không lời / shot dài hơn lời quá chừng này → vàng

_KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "knowledge", "craft", "nhip_nhanh.md")


def of(proj) -> str:
    """'fast' | 'normal' (NULL, cột chưa có, giá trị lạ → normal)."""
    try:
        value = proj["pacing"] if proj is not None and "pacing" in proj.keys() else None
    except (KeyError, IndexError, TypeError, AttributeError):
        value = None
    return value if value in MODES else DEFAULT


def is_fast(proj) -> bool:
    return of(proj) == "fast"


def project_fast(conn, project_id: int) -> bool:
    try:
        row = conn.execute("SELECT pacing FROM projects WHERE id=?", (project_id,)).fetchone()
    except Exception:  # noqa: BLE001 - a database before the column: normal
        return False
    return bool(row is not None and row["pacing"] == "fast")


def _section(title: str) -> str:
    """The text under '## <title>' of knowledge/craft/nhip_nhanh.md (to the next '## '). Missing file / section → error (CHUAN luật 1:
    a project set to fast must not quietly get the normal prompt)."""
    with open(_KNOWLEDGE, encoding="utf-8") as f:
        text = f.read()
    m = re.search(rf"^## {re.escape(title)}\s*$\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m or not m.group(1).strip():
        raise ValueError(f"knowledge/craft/nhip_nhanh.md thiếu mục '## {title}' (dự án chọn nhịp nhanh)")
    return m.group(1).strip()


def director_block(proj) -> str:
    """Khối cho Đạo diễn (một lượt / Tầng A / Tầng B). normal → ''."""
    return _section("Đạo diễn") if is_fast(proj) else ""


def screenwriter_block(proj) -> str:
    """Khối cho Biên kịch. normal → ''."""
    return _section("Biên kịch") if is_fast(proj) else ""


# ---- 3. kiểm bằng code sau Đạo diễn ------------------------------------------------------------------------------------------------
def voice_speed(profile: Optional[Dict]) -> float:
    """Tốc độ đọc của hồ sơ giọng: `speed` (nhánh thêm tốc độ vào hồ sơ), else biến thể `variant.speed`, else 1,0. Đọc mềm."""
    prof = profile if isinstance(profile, dict) else {}
    for value in (prof.get("speed"), (prof.get("variant") or {}).get("speed") if isinstance(prof.get("variant"), dict) else None):
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if 0.3 <= v <= 3.0:
            return v
    return 1.0


def _speech_seconds(rows, speeds: Dict[str, float]) -> float:
    from . import dialogue
    total = 0.0
    for who, said in rows:
        n = dialogue.syllables(said)
        if n:
            total += n / (dialogue.RATE * speeds.get(" ".join(str(who or "").upper().split()), 1.0))
    return total


def check_plan(p, project_id: int, record: bool = True) -> List[Dict]:
    """Dự án nhịp nhanh: mỗi cảnh kịch bản, tổng `duration_s` của các shot so với giây đọc lời của chúng. Trả về
    [{scene, shots_s, speech_s, gap_s, long_shots: [{shot_no, duration_s, speech_s}]}] cho cảnh lệch, và (record) ghi một diag VÀNG có số
    liệu cho mỗi cảnh đó. normal → []. Không chặn, không đổi kế hoạch."""
    if not is_fast(p.project(project_id)):
        return []
    from . import diag, dialogue, shots, voice
    speeds = {name: voice_speed(prof) for name, prof in voice.profiles(p.conn, project_id).items()}
    by_scene: Dict = {}
    for s in shots.shots_of(p, project_id):
        d = s["data"]
        if not d.get("shot_no"):
            continue
        by_scene.setdefault(d.get("story_scene") or s["idx"], []).append(d)
    out = []
    for scene, rows in sorted(by_scene.items(), key=lambda kv: (str(type(kv[0])), kv[0])):
        shots_s = sum(float(d.get("duration_s") or 0) for d in rows)
        speech_s, long_shots = 0.0, []
        for d in rows:
            said = _speech_seconds(dialogue.scene_lines(d), speeds)
            speech_s += said
            if said and float(d.get("duration_s") or 0) - said > GAP_WARN_S:
                long_shots.append({"shot_no": d.get("shot_no"), "duration_s": float(d.get("duration_s") or 0), "speech_s": round(said, 1)})
        if not speech_s:
            continue                      # a scene with no words: its silence is the picture's, not a gap between lines
        gap = shots_s - speech_s
        if gap <= GAP_WARN_S and not long_shots:
            continue
        entry = {"scene": scene, "shots_s": round(shots_s, 1), "speech_s": round(speech_s, 1), "gap_s": round(gap, 1),
                 "long_shots": long_shots}
        out.append(entry)
        if record:
            msg = (f"Nhịp nhanh · cảnh {scene}: các shot {entry['shots_s']:g} s, lời đọc ~{entry['speech_s']:g} s → không lời "
                   f"{entry['gap_s']:g} s (ngưỡng {GAP_WARN_S:g} s)")
            if long_shots:
                msg += "; shot dài hơn lời: " + ", ".join(f"#{x['shot_no']} {x['duration_s']:g} s / lời {x['speech_s']:g} s"
                                                          for x in long_shots[:6])
            msg += ". Xem lại ở Bước 1 (↻ Chia shot lại cảnh này) nếu không có chủ ý — không chặn gen."
            diag.record(p.conn, "director", "warn", msg, "pacing_gap", project_id)
    return out


# ---- 4. khâu dựng ------------------------------------------------------------------------------------------------------------------
def line_start(t: float, prev_end: float, normal_start: float) -> float:
    """Where a clip's first line starts in a fast project (not lip-synced): right after the previous line (FAST_LINE_GAP), coming in
    before the cut at most FAST_J_MAX; never before the clip when no line was said yet, never over the previous line."""
    if prev_end < 0:
        return normal_start
    return max(prev_end + FAST_LINE_GAP, t - FAST_J_MAX)


def tighten(conn, project_id: int, data_dir: str, rows: List[Dict], durations: List[float], keep=()) -> Tuple[List[float], List[Dict]]:
    """Fast project: a shot with voiced lines keeps at most FAST_TAIL_MAX of silence after its last line (lead + lines + gaps, as
    voice.place_on_timeline lays them) — never below FAST_MIN_SHOT, never a lip-synced shot, never a shot in `keep` (the person's own
    edit). Returns (new durations, [{scene_id, idx, from_s, to_s}]). normal → unchanged, []."""
    if not project_fast(conn, project_id):
        return list(durations), []
    from . import audio_lib, lipsync, voice
    items = audio_lib.load(audio_lib.assets_dir(data_dir, project_id))
    synced = set(lipsync.synced_scene_ids(data_dir, project_id) or [])
    usable = [r for r in rows if r.get("path")]
    out, changes = list(durations), []
    for i, (r, d) in enumerate(zip(usable, durations)):
        sid = r.get("scene_id")
        if sid is None or sid in keep or sid in synced:
            continue
        said = [float(e.get("duration_ms") or 0) / 1000.0 for e in items
                if e.get("kind") == "tts" and e.get("scene_id") == sid and e.get("state") == "succeeded" and e.get("file")]
        said = [x for x in said if x > 0]
        if not said:
            continue                      # a shot without words is a picture beat — its length is the Director's
        end = voice.LEAD + sum(said) + voice.GAP * (len(said) - 1)
        want = round(max(end + FAST_TAIL_MAX, FAST_MIN_SHOT), 2)
        if float(d) - want > 0.05:
            out[i] = want
            changes.append({"scene_id": sid, "idx": r.get("idx"), "from_s": round(float(d), 2), "to_s": want})
    return out, changes
