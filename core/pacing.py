"""Nhịp phim của dự án: "normal" (mặc định, hành vi y cũ) | "fast" — nhịp nhanh, ít khoảng lặng (người dùng 14/10, thử ở tập 2 #31).

Một LỰA CHỌN của dự án (cột `projects.pacing`, NULL = normal), không kế thừa sang dự án mới (không có trong
`project_defaults.INHERIT`). Bốn chỗ đọc nó, và mọi chỗ trả về y cũ khi normal:
  1. `director_block(proj)` / `screenwriter_block(proj)` — cách nghĩ nhịp nhanh (knowledge/craft/nhip_nhanh.md) cho Đạo diễn (một lượt,
     Tầng A, Tầng B) và Biên kịch; normal → "" (prompt không đổi một byte).
  2. `check_plan(p, pid)` — sau Đạo diễn, 0 USD: giây đọc lời mỗi cảnh (dialogue.line_seconds: âm tiết ÷ tốc độ của giọng; speed chỉ tính khi model đã đo là theo speed) so tổng giây shot →
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
SPEED_RANGE = (0.7, 1.2)   # ClipAI TTS speed (core/adapters/clipai_audio.py) — the same clamp as voice.line_params (claude/voice-speed)


def _num(value) -> Optional[float]:
    try:
        v = float(str(value).replace(",", ".")) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        return None
    return None if isinstance(value, bool) or v != v or v in (float("inf"), float("-inf")) or v <= 0 else v


def voice_speed(profile: Optional[Dict]) -> float:
    """Tốc độ đọc thật của hồ sơ giọng = tốc độ riêng của hồ sơ (`speed`) × tốc độ biến thể (`variant.speed`), kẹp 0,7–1,2 — đúng
    cách TTS nhận (voice.line_params nhánh claude/voice-speed; có `voice.profile_speed` thì dùng hàm đó). Đọc mềm: thiếu / sai → 1,0."""
    from . import voice
    prof = profile if isinstance(profile, dict) else {}
    own = voice.profile_speed(prof) if hasattr(voice, "profile_speed") else _num(prof.get("speed"))
    variant = prof.get("variant") if isinstance(prof.get("variant"), dict) else {}
    speed = (own or 1.0) * (_num(variant.get("speed")) or 1.0)
    return round(min(max(speed, SPEED_RANGE[0]), SPEED_RANGE[1]), 3)


def _number_syllables(digits: str) -> int:
    """Âm tiết khi đọc một số tiếng Việt: 5 = 1 (năm), 10 = 1 (mười), 15 = 2, 25 = 3 (hai mươi lăm), 100 = 2 (một trăm),
    105 = 4 (một trăm lẻ năm), 2025 = 7 (hai nghìn không trăm hai mươi lăm). Số quá dài (mã, số điện thoại) = đọc từng chữ số."""
    digits = digits.lstrip("0") or "0"
    if digits == "0":
        return 1
    if len(digits) > 12:
        return len(digits)
    groups = []
    while digits:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    total = 0
    for k, g in enumerate(groups):
        h, t, u = (int(c) for c in g.rjust(3, "0"))
        if not (h or t or u):
            continue
        full = k > 0                      # a group after the first is read whole: "không trăm", "lẻ"
        if h or full:
            total += 2                    # "x trăm"
        if t == 1:
            total += 1                    # "mười"
        elif t:
            total += 2                    # "x mươi"
        elif u and (h or full):
            total += 1                    # "lẻ"
        if u:
            total += 1
        if k < len(groups) - 1:
            total += 1                    # nghìn / triệu / tỷ
    return total


def syllables(said: str) -> int:
    """Âm tiết tiếng Việt của một câu đọc: chữ ghép dấu kiểu NFD được gộp lại (NFC) trước khi đếm — "Bốn" NFD không thành 2 âm; dấu câu
    '…', '—', '_' không đếm; số đọc thành chữ (15 → mười lăm = 2)."""
    import unicodedata
    text = unicodedata.normalize("NFC", str(said or ""))
    total = 0
    for word in re.findall(r"[^\W_]+", text, re.UNICODE):
        for part in re.findall(r"\d+|[^\d]+", word):
            total += _number_syllables(part) if part.isdigit() else 1
    return total


def _speech_seconds(rows, ctx: Optional[Dict]) -> float:
    """Giây đọc các câu (không nghỉ) — dialogue.line_seconds theo giọng/tốc độ người nói (15/10: một hàm cho mọi chỗ ước giây; tốc độ
    chỉ đổi ước tính khi model đã đo là đọc theo speed)."""
    from . import dialogue
    return sum(dialogue.line_seconds(said, dialogue.voice_of(ctx, who)) for who, said in rows)


def check_plan(p, project_id: int, record: bool = True) -> List[Dict]:
    """Dự án nhịp nhanh: mỗi cảnh kịch bản, tổng `duration_s` của các shot so với giây đọc lời của chúng. Trả về
    [{scene, shots_s, speech_s, gap_s, long_shots: [{shot_no, duration_s, speech_s}]}] cho cảnh lệch, và (record) ghi một diag VÀNG có số
    liệu cho mỗi cảnh đó. normal → []. Không chặn, không đổi kế hoạch."""
    if not is_fast(p.project(project_id)):
        return []
    from . import diag, dialogue, shots
    ctx = dialogue.speech_ctx(p.conn, project_id)
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
            said = _speech_seconds(dialogue.scene_lines(d), ctx)
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
def line_start(t: float, prev_end: float, normal_start: float, j_ok: bool = True) -> float:
    """Where a clip's first line starts in a fast project (not lip-synced): right after the previous line (FAST_LINE_GAP), coming in
    before the cut at most FAST_J_MAX; never before the clip when no line was said yet, never over the previous line.
    j_ok False (rà 14/10: the shot before is lip-synced and this is the same voice) → never before the cut."""
    if prev_end < 0:
        return normal_start
    return max(prev_end + FAST_LINE_GAP, t - (FAST_J_MAX if j_ok else 0.0))


def tighten(conn, project_id: int, data_dir: str, rows: List[Dict], durations: List[float], keep=(),
            transition: str = "cut", fade: float = 1.0) -> Tuple[List[float], List[Dict]]:
    """Fast project: a shot with voiced lines keeps at most FAST_TAIL_MAX of silence after its last line — the line where
    voice.layout really lays it (spilled over from the shot before, or come in before the cut), shot after shot on the new lengths —
    never below FAST_MIN_SHOT nor the crossfade, never a lip-synced shot, never a shot in `keep` (the person's own edit).
    Returns (new durations, [{scene_id, idx, from_s, to_s}]): every shot whose cut length is now shorter than its clip — also one
    already given a short length (editor_apply renders again on the last render's seconds), so the render fits its file (a cut
    joins whole files). normal → unchanged, []."""
    if not project_fast(conn, project_id):
        return list(durations), []
    from . import audio_lib, ffmpeg_studio, final_cut, lipsync, voice
    items = audio_lib.load(audio_lib.assets_dir(data_dir, project_id))
    synced = set(lipsync.synced_scene_ids(data_dir, project_id) or [])
    usable = [r for r in rows if r.get("path")]
    out, changes = [float(d) for d in durations], []
    overlap = float(fade) if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    floor = max(FAST_MIN_SHOT, overlap + 0.5)          # final_cut.render_problems: a shot must outlast its crossfade
    for i, r in enumerate(usable[:len(out)]):
        sid = r.get("scene_id")
        if sid is None or sid in keep or sid in synced:
            continue
        clips = [{**c, "_seconds": d} for c, d in zip(usable, out)]
        here = voice.layout(conn, project_id, data_dir, clips, items, overlap)[i]
        said = [(start, float(e.get("duration_ms") or 0) / 1000.0) for e, start in here["lines"]]
        said = [(s, x) for s, x in said if x > 0]
        if not said:
            continue                      # a shot without words is a picture beat — its length is the Director's
        end = max(s + x for s, x in said) - here["t"]
        want = round(max(end + FAST_TAIL_MAX, floor), 2)
        if out[i] - want > 0.05:
            out[i] = want
        have = final_cut.clip_seconds(r["path"], r.get("requested_sec"))
        if have - out[i] > 0.05:
            changes.append({"scene_id": sid, "idx": r.get("idx"), "from_s": round(float(have), 2), "to_s": round(out[i], 2)})
    return out, changes
