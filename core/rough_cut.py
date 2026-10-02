"""Measure the rough cut against the Director's intent (docs/KE_HOACH_DUYET_BAN_THO_2026-10-02.md P1) — code only, 0 USD, no Claude.

The rough cut is the latest `final` render (`delivery.render`, before subtitles / end card). Here it is read the way the review pass
(P2: Biên tập viên + Đạo diễn, not built yet) will need it: a clock of the shots, what the Director intended for each script scene
(`director_two_pass.intent_all` — one reader, no copy in scenes.data), the sound as numbers, code warnings, and sheets of frames
around the cuts (≤ MAX_SHEETS images — `llm_runner.MAX_IMAGES`; frames that do not fit are COUNTED and said, never dropped quietly).

    build(p, project_id, data_dir) -> {"fingerprint", "source", "stale", "shots", "scenes", "sound", "flags", "sheets", "coverage"}
    lines(result) -> [text]   # for the screen / the log
"""
import hashlib
import json
import os
import shutil
import tempfile
from typing import Dict, List, Optional

from . import delivery, director_two_pass, ffmpeg_studio, lineage, music_timing, performance, viewer_check

MAX_SHEETS = 12                     # llm_runner.MAX_IMAGES: more images than this in one call is refused
PAIRS_PER_SHEET = 6                 # 2 columns × 3 rows of "before | after" pairs
FRAME_W = 176                       # one frame of a pair (9:16 → 176×313; a sheet of 3 rows stays under the 1024 px long edge)
CUT_GAP_S = 0.3                     # frames taken this far before and after each cut
OFF_TARGET_MIN_S, OFF_TARGET_SHARE = 1.0, 0.15      # same tolerance as director_two_pass.review: ±max(1 s, 15 %)
PEAK_FROM = performance.STRONG      # intent `peak` ≥ this needs a shot of HOLD_S or more in the scene
LOUDNESS_STEP_S = 1.0
FILE = "rough_cut.json"


def _json(text) -> Dict:
    try:
        v = json.loads(text or "{}")
    except (TypeError, ValueError):
        return {}
    return v if isinstance(v, dict) else {}


def path_of(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), FILE)


def load(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(path_of(data_dir, project_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---- the clock ----------------------------------------------------------------------------------------------------------------------
def shot_clock(p, project_id: int, final_row) -> List[Dict]:
    """Every shot of the render with its start / end on the render's own timeline (a crossfade overlaps by `fade`) and what the
    Director / DP said about it. Shots without a scene row (a card) keep their seconds and no story scene."""
    man = _json(final_row["manifest"])
    timeline = [t for t in man.get("timeline") or [] if isinstance(t, dict)]
    cuts = delivery.cut_times(p, project_id, final_row)
    out = []
    for i, item in enumerate(timeline):
        data = {}
        if item.get("scene_id"):
            row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (item["scene_id"],)).fetchone()
            data = _json(row["data"]) if row else {}
        start = 0.0 if i == 0 else cuts[i - 1] if i - 1 < len(cuts) else 0.0
        end = cuts[i] if i < len(cuts) else round(start + float(item.get("seconds") or 0), 2)
        out.append({"n": i + 1, "idx": item.get("idx"), "scene_id": item.get("scene_id"), "story_scene": data.get("story_scene") or item.get("idx"),   # v1: one clip per script scene
                    "start": round(start, 2), "end": round(end, 2), "seconds": round(float(item.get("seconds") or 0), 2),
                    "dialogue": bool([d for d in data.get("dialogue") or [] if isinstance(d, dict) and str(d.get("text") or "").strip()]),
                    "lip_sync": bool(data.get("lip_sync")), "money_shot": bool(data.get("money_shot")),
                    "speed": data.get("speed"), "transition_in": data.get("transition_in")})
    return out


def by_scene(shots: List[Dict], intent: Dict) -> List[Dict]:
    """One record per script scene: the seconds it really got against the Director's `target_s`, its longest shot, the intent."""
    groups: Dict[object, List[Dict]] = {}
    for s in shots:
        groups.setdefault(s["story_scene"], []).append(s)
    out = []
    for idx, rows in groups.items():
        want = intent.get("scenes", {}).get(idx) or {}
        out.append({"scene": idx, "start": rows[0]["start"], "end": rows[-1]["end"], "shots": [r["n"] for r in rows],
                    "seconds": round(sum(r["seconds"] for r in rows), 2), "longest_s": max(r["seconds"] for r in rows),
                    "target_s": want.get("target_s"), "peak": want.get("peak"), "focus": want.get("focus"),
                    "emotional_intent": want.get("emotional_intent"), "editor_notes": want.get("editor_notes"),
                    "sound": want.get("sound")})
    return out


# ---- code warnings (facts the review pass starts from; no verdict on taste) -----------------------------------------------------------
def flags_for(scenes: List[Dict], intent: Dict, spans: List, source_error: Optional[str] = None) -> List[Dict]:
    out: List[Dict] = []
    if intent.get("stale"):
        out.append({"kind": "intent_stale", "level": "warn",
                    "text": "ý đồ Đạo diễn đã cũ (kế hoạch shot được thay sau khi viết ý đồ) — không so được với bản dựng; chạy lại Director"})
    elif intent.get("source") == "story_scene":
        out.append({"kind": "intent_partial", "level": "info",
                    "text": "dự án chưa có ý đồ Tầng A (`target_s`, `peak`, `focus`) — chỉ so được cảm xúc từng cảnh, không so được thời lượng / đỉnh"})
    elif intent.get("source") == "none":
        out.append({"kind": "intent_missing", "level": "info", "text": "không có ý đồ Đạo diễn cho dự án này — chỉ đo bản dựng"})
    for sc in scenes:
        target = sc.get("target_s")
        if isinstance(target, (int, float)) and sc["seconds"]:
            tol = max(OFF_TARGET_MIN_S, OFF_TARGET_SHARE * float(target))
            if abs(sc["seconds"] - float(target)) > tol:
                out.append({"kind": "off_target", "level": "warn", "scene": sc["scene"], "at": sc["start"],
                            "text": f"cảnh {sc['scene']} dài {sc['seconds']:g} s, Đạo diễn muốn {float(target):g} s (lệch quá ±{tol:g} s)"})
        peak = sc.get("peak")
        if isinstance(peak, int) and peak >= PEAK_FROM and sc["longest_s"] < performance.HOLD_S:
            out.append({"kind": "peak_no_hold", "level": "warn", "scene": sc["scene"], "at": sc["start"],
                        "text": f"cảnh {sc['scene']} là đỉnh (peak {peak}) nhưng shot dài nhất chỉ {sc['longest_s']:g} s "
                                f"(cần ≥ {performance.HOLD_S:g} s để người xem kịp nhận)"})
    for a, b in spans:
        out.append({"kind": "silence", "level": "warn", "at": a,
                    "text": f"cả bản trộn lặng hẳn {b - a:.1f} s ({a:.1f}–{b:.1f} s) — nếu là khoảng lặng Đạo diễn đặt thì bỏ qua"})
    if source_error:
        out.append({"kind": "sound_unmeasured", "level": "warn", "text": f"không đo được âm: {source_error}"})
    return out


# ---- frames around the cuts -----------------------------------------------------------------------------------------------------------
def moments(shots: List[Dict], scenes: List[Dict]) -> List[Dict]:
    """What the sheets must show, in time order: each cut ("before | after"), and one frame in the middle of the longest shot of every
    strong scene (intent `peak` ≥ 4) and of the `money_shot`."""
    out = [{"label": f"cắt {i} @{s['start']:.1f}s", "times": [max(0.0, s["start"] - CUT_GAP_S), s["start"] + CUT_GAP_S], "at": s["start"]}
           for i, s in enumerate(shots[1:], 1)]
    for sc in scenes:
        if isinstance(sc.get("peak"), int) and sc["peak"] >= PEAK_FROM:
            s = max((x for x in shots if x["n"] in sc["shots"]), key=lambda x: x["seconds"])
            mid = round((s["start"] + s["end"]) / 2, 2)
            out.append({"label": f"đỉnh cảnh {sc['scene']} @{mid:.1f}s", "times": [mid], "at": mid})
    for s in shots:
        if s["money_shot"]:
            mid = round((s["start"] + s["end"]) / 2, 2)
            out.append({"label": f"money shot @{mid:.1f}s", "times": [mid], "at": mid})
    return sorted(out, key=lambda m: m["at"])


def sheets(video: str, items: List[Dict], out_dir: str, ffmpeg: Optional[str] = None) -> Dict:
    """Pack the moments into at most MAX_SHEETS images (PAIRS_PER_SHEET per image). Returns {"paths", "seen", "total", "dropped"}:
    when the moments do not fit, the LAST ones are left out and listed — the review is told how many it can see (luật 1)."""
    from PIL import Image, ImageDraw
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    fit = MAX_SHEETS * PAIRS_PER_SHEET
    take, dropped = items[:fit], items[fit:]
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):                       # an old run's sheets must not stay next to the new ones
        if name.startswith("sheet_") and name.endswith(".png"):
            os.remove(os.path.join(out_dir, name))
    work = tempfile.mkdtemp()
    paths, seen = [], 0
    try:
        for s in range(0, len(take), PAIRS_PER_SHEET):
            chunk = take[s:s + PAIRS_PER_SHEET]
            cells = []
            for m in chunk:
                frames = []
                for k, t in enumerate(m["times"]):
                    png = os.path.join(work, f"f{s}_{len(cells)}_{k}.png")
                    if viewer_check._frame(ff, video, t, png):
                        with Image.open(png) as im:
                            frames.append(im.convert("RGB").resize((FRAME_W, max(1, int(im.height * FRAME_W / im.width)))))
                if frames:
                    cells.append((m["label"], frames))
            if not cells:
                continue
            seen += len(cells)
            h = max(f.height for _, fs in cells for f in fs)
            cell_w, cell_h = 2 * FRAME_W + 12, h + 22
            sheet = Image.new("RGB", (2 * cell_w, ((len(cells) + 1) // 2) * cell_h), (30, 30, 30))
            for i, (label, fs) in enumerate(cells):
                x, y = (i % 2) * cell_w, (i // 2) * cell_h
                ImageDraw.Draw(sheet).text((x + 4, y + 4), label, fill=(255, 255, 0))
                for k, f in enumerate(fs):
                    sheet.paste(f, (x + 4 + k * (FRAME_W + 4), y + 20))
            path = os.path.join(out_dir, f"sheet_{len(paths) + 1:02d}.png")
            sheet.save(path)
            paths.append(path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"paths": paths, "seen": seen, "total": len(items), "dropped": [m["label"] for m in dropped]}


# ---- the whole measurement ------------------------------------------------------------------------------------------------------------
def fingerprint(final_row, intent: Dict) -> str:
    man = _json(final_row["manifest"])
    blob = json.dumps({"out": final_row["id"], "path": final_row["path"], "timeline": man.get("timeline"),
                       "fade": man.get("fade"), "transition": man.get("transition"), "intent": intent.get("fingerprint")},
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def build(p, project_id: int, data_dir: str, ffmpeg: Optional[str] = None, force: bool = False) -> Dict:
    """Measure the newest rough cut. Raises ValueError when there is none. The same render and the same intent give the saved result
    back (no ffmpeg run); a new render or a changed intent builds again."""
    row = lineage.latest_output(p.conn, project_id, "final")
    if row is None or not os.path.exists(row["path"] or ""):
        raise ValueError("chưa có bản dựng thô (kind=final) — dựng ở Bước 5 trước")
    intent = director_two_pass.intent_all(p, project_id)
    fp = fingerprint(row, intent)
    saved = load(data_dir, project_id)
    if not force and saved and saved.get("fingerprint") == fp and all(os.path.exists(x) for x in saved.get("sheets") or []):
        return saved
    shots = shot_clock(p, project_id, row)
    scenes = by_scene(shots, intent)
    man = _json(row["manifest"])
    levels, spans, err = [], [], None
    try:
        from . import final_qc
        levels = [round(x, 1) for x in music_timing.loudness(row["path"], LOUDNESS_STEP_S)]
        spans = final_qc.silent_spans(row["path"])
    except (OSError, ffmpeg_studio.FFmpegNotFound, ValueError) as e:
        err = str(e)[:160]
    pics = sheets(row["path"], moments(shots, scenes), os.path.join(os.path.dirname(row["path"]), "rough_cut"), ffmpeg)
    result = {"fingerprint": fp, "output_id": row["id"], "path": row["path"], "source": intent["source"], "stale": intent["stale"],
              "seconds": shots[-1]["end"] if shots else 0.0, "shots": shots, "scenes": scenes,
              "sound": {"step_s": LOUDNESS_STEP_S, "mix_db": levels, "silent_spans": spans, "loudness": man.get("loudness"),
                        "music_breaths": man.get("music_breaths"), "sound_intent": man.get("sound_intent")},
              "flags": flags_for(scenes, intent, spans, err), "sheets": pics["paths"],
              "coverage": {"moments_seen": pics["seen"], "moments_total": pics["total"], "dropped": pics["dropped"],
                           "images": len(pics["paths"]), "images_max": MAX_SHEETS}}
    os.makedirs(os.path.dirname(path_of(data_dir, project_id)), exist_ok=True)
    with open(path_of(data_dir, project_id), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    return result


def lines(res: Optional[Dict]) -> List[str]:
    """What the screen shows: what was measured, what the sheets cover, then the warnings."""
    if not res:
        return []
    cov = res.get("coverage") or {}
    out = [f"📏 Bản dựng thô {res.get('seconds', 0):g} s · {len(res.get('shots') or [])} shot · {len(res.get('scenes') or [])} cảnh · "
           f"ý đồ: {res.get('source')} · thấy {cov.get('moments_seen', 0)}/{cov.get('moments_total', 0)} khoảnh khắc trong "
           f"{cov.get('images', 0)}/{cov.get('images_max', MAX_SHEETS)} ảnh"]
    if cov.get("dropped"):
        out.append("⚠ không vừa số ảnh tối đa, bỏ: " + ", ".join(cov["dropped"][:8]) + (" …" if len(cov["dropped"]) > 8 else ""))
    mark = {"warn": "⚠", "info": "ℹ️"}
    out += [f"{mark.get(f.get('level'), '•')} {f['text']}" for f in res.get("flags") or []]
    return out
