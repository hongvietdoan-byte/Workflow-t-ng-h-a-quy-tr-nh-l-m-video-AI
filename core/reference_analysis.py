"""Reading reference videos (Free Fire channel videos, internal edits, viral fan 3D) into shot-by-shot editing data.

Kế hoạch v3, GĐ1: the Director learns how Free Fire videos are cut — shot sizes, camera moves, what each shot does (hook / setup /
action / reaction / insert / dialogue / transition / ending), how long each kind of shot lasts, where text, game UI and effects go —
per style profile (anime CGI, realistic CGI/VFX, in-game, Kelly Show, short film, fan 3D).

Only TEXT data is kept (cut times, labels, statistics) in research/ff_styles/<STYLE>/<video_id>.json — never pictures of the videos.

Pipeline for a video file on this PC:
  detect_cuts (ffmpeg scene score) -> shots_from_cuts -> mid_frames (one frame per shot) -> contact_sheets (12 frames per sheet, so a
  long video fits in llm_runner.MAX_IMAGES) -> label (Claude via llm_runner.ask_json, prompts/16_reference_shots.md) -> save_record.
Videos that cannot be downloaded (YouTube) are cut in the browser (canvas frame difference) and labelled in the chat session; they are
saved with the same save_record so every statistic reads one format.
"""
import json
import os
import re
import statistics
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from .ffmpeg_studio import FFmpegNotFound, find_ffmpeg

ROOT = os.path.join(os.path.dirname(__file__), "..")
RESEARCH_DIR = os.path.join(ROOT, "research", "ff_styles")

STYLES = {
    "ANIME_CGI": "Anime / hoạt hình CGI",
    "REAL_CGI_VFX": "CGI tả thực / kỹ xảo",
    "INGAME": "Gameplay trong game",
    "KELLY_SHOW": "Kelly Show (tiểu phẩm với nhân vật game)",
    "SHORT_FILM": "Phim ngắn",
    "FAN_3D": "Video 3D fan làm (viral)",
}
SIZES = ("ECU", "CU", "MCU", "MS", "WS", "EWS", "GAME_TPS", "GRAPHIC")
ANGLES = ("eye", "low", "high", "overhead", "dutch", "ots", "pov")
MOVES = ("static", "push_in", "pull_out", "pan", "tilt", "track", "orbit", "handheld", "crane", "whip", "zoom")
ROLES = ("hook", "setup", "action", "reaction", "insert", "dialogue", "transition", "ending")
TRANSITIONS = ("cut", "fade", "whip", "flash", "match", "dissolve", "wipe")
SIZE_LABEL = {"ECU": "cận đặc tả", "CU": "cận", "MCU": "trung cận", "MS": "trung", "WS": "toàn", "EWS": "toàn rộng",
              "GAME_TPS": "camera game (góc thứ ba sau lưng)", "GRAPHIC": "đồ họa / tiêu đề toàn khung"}
ROLE_LABEL = {"hook": "mở móc", "setup": "thiết lập", "action": "hành động", "reaction": "phản ứng", "insert": "chèn chi tiết",
              "dialogue": "thoại", "transition": "chuyển", "ending": "kết"}

DEFAULT_THRESHOLD = 0.30
MIN_SHOT = 0.25          # cuts closer than this are flash frames / double detections -> one cut
PER_SHEET = 12

_PTS = re.compile(r"pts_time:(\d+(?:\.\d+)?)")


class ReferenceAnalysisError(Exception):
    def __init__(self, message: str, code: str = "error"):
        super().__init__(message)
        self.code = code


# ---- cutting ------------------------------------------------------------------------------------------------------------
def detect_cuts(path: str, threshold: float = DEFAULT_THRESHOLD) -> List[float]:
    """Cut times (seconds) where ffmpeg's scene-change score passes `threshold`. The picture is scaled down first (much faster;
    the score only needs a thumbnail)."""
    try:
        ffmpeg = find_ffmpeg()
    except FFmpegNotFound as e:
        raise ReferenceAnalysisError(str(e), code="config") from e
    proc = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-an", "-sn",
                           "-vf", f"scale=192:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 and "pts_time" not in (proc.stderr or ""):
        raise ReferenceAnalysisError("ffmpeg không đọc được video: " + (proc.stderr or "")[-300:], code="bad_video")
    return sorted(float(m.group(1)) for m in _PTS.finditer(proc.stderr or ""))


def shots_from_cuts(cuts: Sequence[float], duration: float, min_shot: float = MIN_SHOT) -> List[Dict]:
    """[{i, start, end, dur}] from cut times; cuts within `min_shot` of the previous boundary (or of the end) are dropped."""
    if not duration or duration <= 0:
        raise ReferenceAnalysisError("không biết thời lượng video", code="bad_video")
    bounds = [0.0]
    for c in sorted(cuts):
        if min_shot <= c <= duration - min_shot and c - bounds[-1] >= min_shot:
            bounds.append(round(float(c), 2))
    bounds.append(round(float(duration), 2))
    return [{"i": i, "start": a, "end": b, "dur": round(b - a, 2)} for i, (a, b) in enumerate(zip(bounds, bounds[1:]), 1)]


def cuts_from_diffs(diffs: Sequence[Tuple[float, float]], floor: float = 18.0, factor: float = 4.0,
                    local_floor: float = 25.0, local_factor: float = 3.0, window: int = 5) -> List[float]:
    """Cut times from a browser frame-difference scan ([(t, mean abs diff)] sampled every ~0.2-0.3s of video).

    Two rules, joined: (1) the difference passes max(floor, factor x the whole video's median) — the rule of the hand-off note;
    (2) a LOCAL peak: higher than both neighbours and than local_factor x the median of the `window` samples each side. Rule 2
    finds cuts inside a static frame (gameplay shown in a decorated box, split screens) where the whole-frame difference stays
    low, and ignores fast camera motion that keeps every sample high. Cuts closer than 0.35s are one cut."""
    if not diffs:
        return []
    values = [d for _, d in diffs]
    limit = max(floor, factor * statistics.median(values))
    found = [float(t) for t, d in diffs if d > limit]
    for i, (t, d) in enumerate(diffs):
        around = values[max(0, i - window):i] + values[i + 1:i + window + 1]
        peak = (i == 0 or d >= values[i - 1]) and (i == len(values) - 1 or d >= values[i + 1])
        if around and peak and d > local_floor and d > local_factor * statistics.median(around):
            found.append(float(t))
    cuts: List[float] = []
    for t in sorted(found):
        if not cuts or t - cuts[-1] > 0.35:
            cuts.append(t)
    return cuts


# ---- pictures for the labelling -------------------------------------------------------------------------------------------
def mid_frames(path: str, shots: List[Dict], out_dir: str) -> List[str]:
    """One JPEG per shot, taken at the middle of the shot (a missing frame is simply left out of the sheet)."""
    ffmpeg = find_ffmpeg()
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for s in shots:
        t = s["start"] + s["dur"] / 2
        dest = os.path.join(out_dir, f"shot_{s['i']:03d}.jpg")
        subprocess.run([ffmpeg, "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", dest],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
        out.append(dest if os.path.exists(dest) else "")
    return out


def contact_sheets(frames: List[str], shots: List[Dict], out_dir: str, portrait: bool = False,
                   per_sheet: int = PER_SHEET) -> List[Tuple[str, str]]:
    """[(caption, sheet path)]: the shots' frames in order, `per_sheet` per sheet, each captioned "#N 1.2-3.4s (2.2s)"."""
    from .layout import storyboard
    cell = (216, 384) if portrait else (384, 216)
    cols = 6 if portrait else 4
    sheets = []
    for k in range(0, len(shots), per_sheet):
        part = shots[k:k + per_sheet]
        items = [(frames[s["i"] - 1] if s["i"] - 1 < len(frames) else "", f"#{s['i']} {s['start']:.1f}-{s['end']:.1f}s ({s['dur']:.1f}s)")
                 for s in part]
        dest = storyboard(items, os.path.join(out_dir, f"sheet_{k // per_sheet + 1:02d}.png"), cols=cols, cell=cell)
        sheets.append((f"Bảng khung hình shot #{part[0]['i']}–#{part[-1]['i']} (mỗi ô = khung giữa của 1 shot, có số shot và thời gian):", dest))
    return sheets


# ---- labelling --------------------------------------------------------------------------------------------------------------
def _read_prompt() -> str:
    with open(os.path.join(ROOT, "prompts", "16_reference_shots.md"), encoding="utf-8") as f:
        return f.read()


def build_prompt(style: str, meta: Dict, shots: List[Dict], title: str = "", note: str = "") -> str:
    head = (f"- Tên/nguồn: {title or '(không tên)'}\n- Dạng phong cách dự kiến: {style} — {STYLES.get(style, style)}\n"
            f"- Thời lượng: {meta.get('duration_sec') or 0:.1f}s · khung {meta.get('width')}x{meta.get('height')} · {len(shots)} shot")
    if note.strip():
        head += f"\n- Ghi chú của người xem: {note.strip()}"
    return (_read_prompt() + "\n\n# Video\n" + head + "\n\n# Các shot\n```json\n"
            + json.dumps([{k: s[k] for k in ("i", "start", "end", "dur")} for s in shots], ensure_ascii=False) + "\n```")


def validate_labels(obj, n_shots: int) -> Dict:
    """Checks the labelling JSON: one entry per shot with values from the fixed vocabularies (unknown words are errors so the
    statistics stay comparable across videos)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("shots"), list):
        raise ValueError("cần {\"shots\": [...], \"overall\": {...}}")
    seen = set()
    for j, s in enumerate(obj["shots"]):
        w = f"shots[{j}]"
        if not isinstance(s, dict) or not isinstance(s.get("i"), int):
            raise ValueError(f"{w}: thiếu số shot i")
        for key, allowed in (("size", SIZES), ("angle", ANGLES), ("camera_move", MOVES), ("role", ROLES)):
            if s.get(key) not in allowed:
                raise ValueError(f"{w}.{key}: phải là một trong {', '.join(allowed)}")
        if s.get("transition_in") is not None and s["transition_in"] not in TRANSITIONS:
            raise ValueError(f"{w}.transition_in: phải là một trong {', '.join(TRANSITIONS)}")
        for key in ("text_on_screen", "game_ui", "vfx"):
            if not isinstance(s.get(key, False), bool):
                raise ValueError(f"{w}.{key}: true/false")
        seen.add(s["i"])
    missing = sorted(set(range(1, n_shots + 1)) - seen)
    if missing:
        raise ValueError(f"thiếu nhãn cho shot {missing[:10]}")
    if not isinstance(obj.get("overall", {}), dict):
        raise ValueError("overall phải là object")
    return obj


def label(client, style: str, meta: Dict, shots: List[Dict], sheets: List[Tuple[str, str]], title: str = "",
          note: str = "") -> Dict:
    from . import llm_runner
    with llm_runner.tagged("style_research"):
        obj, _, _ = llm_runner.ask_json(client, build_prompt(style, meta, shots, title, note),
                                        lambda o: validate_labels(o, len(shots)), sheets)
    return obj


def merge_labels(shots: List[Dict], labels: Dict) -> List[Dict]:
    by_i = {s["i"]: s for s in labels.get("shots") or []}
    keep = ("size", "angle", "camera_move", "role", "subject", "text_on_screen", "game_ui", "vfx", "transition_in", "note")
    return [{**s, **{k: by_i.get(s["i"], {}).get(k) for k in keep if k in by_i.get(s["i"], {})}} for s in shots]


# ---- storage + statistics -------------------------------------------------------------------------------------------------
def video_id(source: str) -> str:
    """YouTube id when the source is a YouTube link, else a short name from the file."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", source or "")
    if m:
        return m.group(1)
    from .assets import fold
    stem = fold(os.path.splitext(os.path.basename(source or "video"))[0]).replace("đ", "d")
    return re.sub(r"[^a-z0-9-]+", "_", stem).strip("_")[:60] or "video"


def save_record(style: str, source: str, title: str, meta: Dict, shots: List[Dict], overall: Optional[Dict] = None,
                method: str = "ffmpeg", research_dir: Optional[str] = None, extra: Optional[Dict] = None) -> str:
    if style not in STYLES:
        raise ReferenceAnalysisError(f"dạng phong cách không hợp lệ: {style}", code="bad_style")
    folder = os.path.join(research_dir or RESEARCH_DIR, style)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{video_id(source)}.json")
    record = {"video_id": video_id(source), "title": title, "source": source if source.startswith("http") else os.path.basename(source),
              "style": style, "method": method, "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "duration_sec": round(float(meta.get("duration_sec") or 0), 2), "width": meta.get("width"), "height": meta.get("height"),
              "shots": shots, "overall": overall or {}, **(extra or {})}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    return path


def load_records(style: Optional[str] = None, research_dir: Optional[str] = None) -> List[Dict]:
    base = research_dir or RESEARCH_DIR
    out = []
    for st in ([style] if style else sorted(STYLES)):
        folder = os.path.join(base, st)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                try:
                    with open(os.path.join(folder, name), encoding="utf-8") as f:
                        out.append(json.load(f))
                except (OSError, ValueError):
                    continue
    return out


def _q(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (pos - lo), 2)


def style_stats(records: List[Dict]) -> Dict:
    """Numbers the style file is written from: how long videos and shots are, per-role length RANGES (p25-p75, not a fixed
    number — pacing follows the script), how often each size / move is used, how often text / game UI / effects appear."""
    shots = [s for r in records for s in r.get("shots") or []]
    labelled = [s for s in shots if s.get("role")]
    durs = [s["dur"] for s in shots if s.get("dur")]
    total = sum(r.get("duration_sec") or 0 for r in records)
    out = {"videos": len(records), "shots": len(shots), "seconds": round(total, 1),
           "video_len": {"median": _q([r.get("duration_sec") or 0 for r in records], .5)},
           "shot_len": {"p10": _q(durs, .1), "p25": _q(durs, .25), "median": _q(durs, .5), "p75": _q(durs, .75), "p90": _q(durs, .9)},
           "shots_per_min": round(len(shots) / (total / 60), 1) if total else 0.0, "roles": {}, "sizes": {}, "moves": {}, "angles": {}}
    for key, field in (("roles", "role"), ("sizes", "size"), ("moves", "camera_move"), ("angles", "angle")):
        counts: Dict[str, int] = {}
        for s in labelled:
            counts[s.get(field) or "?"] = counts.get(s.get(field) or "?", 0) + 1
        out[key] = {k: round(v / len(labelled), 3) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])} if labelled else {}
    by_role: Dict[str, List[float]] = {}
    for s in labelled:
        by_role.setdefault(s["role"], []).append(s["dur"])
    out["role_len"] = {r: {"p25": _q(v, .25), "median": _q(v, .5), "p75": _q(v, .75), "n": len(v)} for r, v in by_role.items()}
    for flag in ("text_on_screen", "game_ui", "vfx"):
        out[flag] = round(sum(1 for s in labelled if s.get(flag)) / len(labelled), 3) if labelled else 0.0
    firsts = [(r.get("shots") or [{}])[0].get("role") for r in records if r.get("shots")]
    lasts = [(r.get("shots") or [{}])[-1].get("role") for r in records if r.get("shots")]
    out["opens_with"] = {k: firsts.count(k) for k in sorted(set(firsts)) if k}
    out["ends_with"] = {k: lasts.count(k) for k in sorted(set(lasts)) if k}
    return out


def stats_markdown(style: str, stats: Dict) -> str:
    """The numeric part of knowledge/ff_styles/<STYLE>.md (written again whenever more videos are analysed)."""
    def share(d: Dict, labels: Dict) -> str:
        return ", ".join(f"{labels.get(k, k)} {v * 100:.0f}%" for k, v in list(d.items())[:6]) or "—"
    sl = stats["shot_len"]
    rows = [f"- **{stats['videos']} video, {stats['shots']} shot, {stats['seconds']:.0f}s** · video dài trung vị {stats['video_len']['median']:.0f}s · "
            f"**{stats['shots_per_min']:.0f} shot/phút**",
            f"- Độ dài shot: phần lớn {sl['p25']:.1f}–{sl['p75']:.1f}s (trung vị {sl['median']:.1f}s; 10% ngắn nhất ≤ {sl['p10']:.1f}s, "
            f"10% dài nhất ≥ {sl['p90']:.1f}s)",
            "- Độ dài theo vai trò (khoảng p25–p75): " + "; ".join(
                f"{ROLE_LABEL.get(r, r)} {v['p25']:.1f}–{v['p75']:.1f}s" for r, v in sorted(stats["role_len"].items(), key=lambda kv: -kv[1]["n"])),
            "- Vai trò: " + share(stats["roles"], ROLE_LABEL),
            "- Cỡ cảnh: " + share(stats["sizes"], SIZE_LABEL),
            "- Chuyển động máy: " + share(stats["moves"], {}),
            f"- Chữ trên hình {stats['text_on_screen'] * 100:.0f}% shot · giao diện game {stats['game_ui'] * 100:.0f}% · hiệu ứng {stats['vfx'] * 100:.0f}%",
            "- Mở bằng: " + (", ".join(f"{ROLE_LABEL.get(k, k)} ×{v}" for k, v in stats["opens_with"].items()) or "—")
            + " · kết bằng: " + (", ".join(f"{ROLE_LABEL.get(k, k)} ×{v}" for k, v in stats["ends_with"].items()) or "—")]
    return f"## Số liệu ({STYLES.get(style, style)})\n" + "\n".join(rows)


def analyze_file(client, path: str, style: str, work_dir: str, title: str = "", note: str = "",
                 threshold: float = DEFAULT_THRESHOLD, research_dir: Optional[str] = None) -> Dict:
    """Whole pipeline for one video file on this PC. Returns {"path": saved json, "shots": n, "record": {...}}."""
    from .video_analysis import VideoAnalysisError, probe
    try:
        meta = probe(path)
    except VideoAnalysisError as e:
        raise ReferenceAnalysisError(str(e), code=e.code) from e
    shots = shots_from_cuts(detect_cuts(path, threshold), meta.get("duration_sec") or 0)
    frames = mid_frames(path, shots, work_dir)
    sheets = contact_sheets(frames, shots, work_dir, portrait=bool(meta.get("height") and meta.get("width")
                                                                    and meta["height"] > meta["width"]))
    labels = label(client, style, meta, shots, sheets, title or os.path.basename(path), note)
    merged = merge_labels(shots, labels)
    saved = save_record(style, path, title or os.path.splitext(os.path.basename(path))[0], meta, merged, labels.get("overall"),
                        research_dir=research_dir)
    return {"path": saved, "shots": len(merged), "record": load_json(saved)}


def load_json(path: str) -> Dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
