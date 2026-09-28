"""QC of the finished cut, by code, before anyone is told "done" (kế hoạch sửa sau #8, S1.9).

Trial #8 (2026-09-28): the delivery went to the person with a speaker's name as a subtitle line, 27 s without music, a gunshot 20 s away
from its shot over another line, a subtitle on a face, the film 43 % longer than planned — each measurable in seconds, none measured.
This module measures them on the real files (render manifest, voice/effect list, .srt, the video's frames and sound). Free: ffmpeg +
the YuNet face model when installed; no model call.

Each issue: {"code", "level": "block" | "warn", "msg" (Vietnamese, says what to do), "at": seconds or None}.
"block" = not ready to hand over (the automatic run stops for the person, Step 5 shows it red); "warn" = look at it.
"""
import json
import os
import re
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

from . import audio_lib, ffmpeg_studio, lineage, sound_intent, subtitles, text_placement
from .pipeline import Pipeline

LENGTH_WARN, LENGTH_BLOCK = 0.10, 0.20       # cut longer / shorter than the planned shot list
PEAK_BLOCK = -1.0                           # dBTP: above this the platform's re-encode clips (AES TD1008)
SILENT_DB, SILENT_S = -45.0, 2.5            # the whole mix this quiet for this long (not the last 1,5 s) = a hole in the sound
SHORT_SHOT_S = 1.0


def _issue(code: str, level: str, msg: str, at: Optional[float] = None) -> Dict:
    return {"code": code, "level": level, "msg": msg, "at": None if at is None else round(float(at), 2)}


def check_length(planned_s: float, final_s: float) -> List[Dict]:
    if not planned_s or not final_s:
        return []
    diff = (final_s - planned_s) / planned_s
    if abs(diff) <= LENGTH_WARN:
        return []
    level = "block" if abs(diff) > LENGTH_BLOCK else "warn"
    return [_issue("length", level, f"bản dựng {final_s:.1f} s so với bảng shot {planned_s:.1f} s ({diff:+.0%}) — xem lại thời lượng shot / "
                                    "giọng thật trước khi giao")]


def check_music(manifest: Dict) -> List[Dict]:
    out = []
    intent = manifest.get("sound_intent") or {}
    for a, b in intent.get("off") or []:
        if b - a > sound_intent.MAX_OFF_S + 0.05:
            out.append(_issue("music_hole", "block", f"nhạc tắt liền {b - a:.0f} s ({a:.0f}–{b:.0f} s) — quá {sound_intent.MAX_OFF_S:g} s", a))
    for t in intent.get("auto_in") or []:
        out.append(_issue("music_auto_in", "warn", f"khoảng lặng nhạc của Đạo diễn dài quá 8 s: nhạc lên lại hẳn ở {t:.1f} s (đã trở lại nhỏ từ "
                                                   "trước đó) — nghe thử; lâu dài: Đạo diễn đặt 'in' đúng chỗ (đợt S3)", t))
    return out


def check_peak(loudness: Optional[Dict]) -> List[Dict]:
    tp = (loudness or {}).get("true_peak_dbfs")
    if tp is None:
        return []
    if tp > PEAK_BLOCK:
        return [_issue("peak", "block", f"đỉnh âm {tp:g} dBTP > {PEAK_BLOCK:g} — dễ rè sau khi nền tảng mã hóa lại (bật loudness_normalize)")]
    if tp > ffmpeg_studio.TRUE_PEAK_MAX:
        return [_issue("peak", "warn", f"đỉnh âm {tp:g} dBTP, sát giới hạn {ffmpeg_studio.TRUE_PEAK_MAX:g}")]
    return []


def check_effects(items: Sequence[Dict]) -> List[Dict]:
    """AI effects without a shot anchor (made before the anchor existed) may sit at an old second; effects over a spoken line."""
    out = []
    speech = [(e["start"], e["start"] + (e.get("duration_ms") or 0) / 1000.0) for e in items
              if e.get("kind") == "tts" and e.get("use") and e.get("duration_ms")]
    for e in items:
        if e.get("kind") != "sound_effect" or not e.get("use"):
            continue
        label = str(e.get("label") or "")
        if label.startswith("AI: ") and e.get("anchor_idx") is None:
            out.append(_issue("sfx_unanchored", "block", f"hiệu ứng “{label[4:]}” ở {e['start']:.1f} s chưa gắn shot (đặt theo giây cũ) — có thể lệch "
                                                          "khỏi khoảnh khắc của nó; chạy lại AI chọn hiệu ứng hoặc gắn shot", e["start"]))
        a, b = e["start"], e["start"] + (e.get("duration_ms") or 500) / 1000.0
        if any(a < y and x < b for x, y in speech):
            out.append(_issue("sfx_over_speech", "warn", f"hiệu ứng “{label.replace('AI: ', '')}” ở {a:.1f} s đè câu thoại (đã hạ 6 dB)", a))
    return out


def check_srt(srt_text: str, speakers: Sequence[str]) -> List[Dict]:
    """A subtitle line that is only a name (trial #8: "KELLY", "KENTA", "MAXIM") or a game notice is not dialogue."""
    names = {s.strip().upper() for s in speakers if s}
    out = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        rows = block.strip().splitlines()
        if len(rows) < 3:
            continue
        text = " ".join(rows[2:]).strip()
        start = _srt_seconds(rows[1].split("-->")[0])
        if text.upper().strip(" .:") in names or text == subtitles.HUD:
            out.append(_issue("srt_not_dialogue", "block", f"dòng phụ đề “{text}” ở {start:.1f} s không phải lời thoại (tên / thông báo)", start))
    return out


def _srt_seconds(clock: str) -> float:
    h, m, rest = clock.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def check_short_shots(timeline: Sequence[Dict]) -> List[Dict]:
    out, t = [], 0.0
    for r in timeline:
        secs = float(r.get("seconds") or 0)
        if 0 < secs < SHORT_SHOT_S:
            out.append(_issue("short_shot", "warn", f"shot {r.get('idx')} chỉ {secs:.2f} s (< {SHORT_SHOT_S:g} s) — chỉ hợp với chèn cận có chủ ý", t))
        t += secs
    return out


def silent_spans(video: str, window: float = 0.5, ffmpeg: Optional[str] = None) -> List[Tuple[float, float]]:
    """Spans where the whole mix stays under SILENT_DB for SILENT_S or more (the last 1,5 s — the fade out — left out)."""
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    rate = 48000
    proc = subprocess.run([ff, "-hide_banner", "-nostats", "-i", video, "-vn", "-ac", "1", "-ar", str(rate), "-af",
                           f"asetnsamples={int(rate * window)},astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                           "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    levels = []
    for m in re.finditer(r"RMS_level=(-?[\d.]+|-inf)", proc.stderr or ""):
        v = m.group(1)
        levels.append(-200.0 if v == "-inf" else float(v))
    total = len(levels) * window
    out, start = [], None
    for i, db in enumerate(levels + [0.0]):
        t = i * window
        if db < SILENT_DB and t < total - 1.5:
            start = t if start is None else start
        else:
            if start is not None and t - start >= SILENT_S:
                out.append((round(start, 2), round(t, 2)))
            start = None
    return out


def check_silence(video: str) -> List[Dict]:
    try:
        spans = silent_spans(video)
    except (OSError, ffmpeg_studio.FFmpegNotFound):
        return []
    return [_issue("silence", "warn", f"cả bản trộn lặng hẳn {b - a:.1f} s ({a:.1f}–{b:.1f} s) — không nhạc, không tiếng", a) for a, b in spans]


def check_subtitle_faces(video: str, cues: Sequence, height: int = 1920, fontsize: int = 60, platform: str = "tiktok") -> List[Dict]:
    """Spoken lines whose final position (text_placement rules) still covers a face seen on the real frames. Needs the face model."""
    if not text_placement.model_path():
        return []
    spoken = [c for c in cues if c.speaker != subtitles.HUD]
    try:
        seen = text_placement.video_spans(video, spoken, ffmpeg_studio.find_ffmpeg())
    except (OSError, ffmpeg_studio.FFmpegNotFound):
        return []
    box = subtitles.safe_box(platform)
    where = text_placement.placements(spoken, {}, height, fontsize, lambda c: 1, box["bottom"], box["top"], seen=seen)
    out = []
    for i, span in seen.items():
        b = text_placement.bands(height, fontsize, 1, box["bottom"], box["top"])[where.get(i, "bottom")]
        if text_placement._overlap(b, span) > 0:
            out.append(_issue("subtitle_face", "block", f"phụ đề “{spoken[i].text[:40]}” ở {spoken[i].start:.1f} s đè mặt ở mọi vị trí — "
                                                        "rút gọn câu hoặc tách câu", spoken[i].start))
    return out


def run(p: Pipeline, project_id: int, data_dir: str, frames: bool = True) -> Dict:
    """Every check on the latest final render (+ its subtitle layer when there is one). frames=False skips the checks that read the
    video (tests, quick status). Returns {"ok", "blocks", "warns", "issues"}."""
    fin = lineage.latest_output(p.conn, project_id, "final")
    if fin is None:
        return {"ok": False, "blocks": 1, "warns": 0, "issues": [_issue("no_render", "block", "chưa có bản dựng")]}
    try:
        man = json.loads(fin["manifest"] or "{}")
    except ValueError:
        man = {}
    issues: List[Dict] = []
    datas = [json.loads(r["data"] or "{}") for r in p.conn.execute("SELECT data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,))]
    planned = sum(float(d.get("duration_s") or 0) for d in datas)
    timeline = man.get("timeline") or []
    final_s = ffmpeg_studio.probe_duration(fin["path"]) if frames and os.path.exists(fin["path"]) else sum(float(r.get("seconds") or 0) for r in timeline)
    issues += check_length(planned, final_s or 0.0)
    issues += check_music(man)
    issues += check_peak(man.get("loudness"))
    issues += check_effects(audio_lib.load(audio_lib.assets_dir(data_dir, project_id)))
    issues += check_short_shots(timeline)
    sub = lineage.latest_output(p.conn, project_id, "subtitle")
    speakers = sorted({str(c) for d in datas for c in (d.get("characters") or [])})
    if sub is not None:
        srt = os.path.splitext(sub["path"])[0] + ".srt"
        if os.path.exists(srt):
            with open(srt, encoding="utf-8") as f:
                issues += check_srt(f.read(), speakers)
    if frames and os.path.exists(fin["path"]):
        issues += check_silence(fin["path"])
        if sub is not None:
            try:
                sub_man = json.loads(sub["manifest"] or "{}")
                cue_list = [subtitles.Cue(**c) for c in (sub_man.get("cue_list") or [])]
            except (TypeError, ValueError):
                sub_man, cue_list = {}, []
            size = ffmpeg_studio.probe_size(fin["path"]) or (1080, 1920)
            if cue_list and size[1] > size[0]:
                issues += check_subtitle_faces(fin["path"], cue_list, size[1], max(int(min(size) * 0.055), 14),
                                               (sub_man.get("settings") or {}).get("platform") or "tiktok")
    blocks = sum(i["level"] == "block" for i in issues)
    return {"ok": blocks == 0, "blocks": blocks, "warns": len(issues) - blocks, "issues": issues}


def summary(res: Dict) -> str:
    if res["ok"] and not res["warns"]:
        return "✅ Kiểm bản dựng: không có lỗi"
    head = f"{'❌' if res['blocks'] else '⚠'} Kiểm bản dựng: {res['blocks']} lỗi chặn, {res['warns']} cần xem"
    return head + "\n" + "\n".join(f"- {'❌' if i['level'] == 'block' else '⚠'} {i['msg']}" for i in res["issues"])
