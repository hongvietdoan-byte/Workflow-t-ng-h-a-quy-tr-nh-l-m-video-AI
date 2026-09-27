"""Seedance "reference only" video (flag seedance_ref_groups; docs/PHAN_TICH_GOP_SHOT_2026-09-27.md, mục 6).

Seedance refuses a Free Fire in-game start picture as a "real person" (privacy filter) and refuses start/last frames mixed with reference
pictures. What passed in the real test of 2026-09-27: NO start frame, every picture sent only as `reference_image` and marked as design
material (white "CHARACTER SHEET REFERENCE" banner + a red plus sign over one eye of every face). Two such generations each made 3 shots
cut in the storyboard's order, and the marks did not show in the video.

Order the person chose (2026-09-27): **P2m group** (2–4 consecutive shots of one continuity group, one generation, each shot with its own
storyboard picture) → refused: **Seedance per shot** (the same, one shot) → refused again: **Kling per shot** (start frame, as before).
The route of a shot is kept in its scene data (`video_route`: absent = group, "single", "kling"), so a refusal changes the input once and
the retry is not the same request (luật 6)."""
import json
import math
import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional

GROUP_MAX_SHOTS = 4           # tested with 3; more shots per clip = less control over each one
GROUP_MAX_SECONDS = 15.0      # Seedance 2.0: one clip is at most 15 s
SEEDANCE_MIN = 4              # Seedance bills at least 4 s
MAX_PICTURES = 9              # Seedance 2.0: at most 9 reference pictures
BANNER = "CHARACTER SHEET REFERENCE"
ROUTES = (None, "single", "kling")


def enabled(conn, project_id: int) -> bool:
    from . import features
    row = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (project_id,)).fetchone()
    return row is not None and row["shot_mode"] == "per_shot" and features.on("seedance_ref_groups")


def route(data: Dict) -> Optional[str]:
    value = data.get("video_route")
    return value if value in ROUTES else None


def eligible(data: Dict) -> bool:
    """A shot that goes by reference pictures: a v3 shot, not sent to Kling after refusals, not a green-screen plate shot (the green
    picture must be the start frame so it can be keyed)."""
    return bool(data.get("shot_no")) and route(data) != "kling" and data.get("plate_mode") != "green"


def _lip_sync(data: Dict) -> bool:
    from . import lipsync
    return lipsync.enabled() and lipsync.method_for(data) == "generate"


def _groupable(data: Dict) -> bool:
    """In a group clip: eligible, still on the group route, and not a lip-sync shot (its own voice line goes only with a one-shot clip)."""
    return eligible(data) and route(data) is None and not _lip_sync(data)


def groups(conn, project_id: int) -> List[List[Dict]]:
    """Consecutive groupable shots of one continuity group (script scene + sequence), at most GROUP_MAX_SHOTS and GROUP_MAX_SECONDS of
    film each; only groups of 2+ shots (a lone shot is a one-shot clip)."""
    from .shots import _group_key, _rows
    out: List[List[Dict]] = []
    cur: List[Dict] = []

    def close():
        if len(cur) > 1:
            out.append(list(cur))
        cur.clear()

    for r in _rows(conn, project_id):
        d = r["data"]
        if not d.get("shot_no") or not _groupable(d):
            close()
            continue
        sec = float(d.get("duration_s") or 0)
        if cur and (_group_key(cur[-1]["data"]) != _group_key(d) or len(cur) >= GROUP_MAX_SHOTS
                    or sum(float(x["data"].get("duration_s") or 0) for x in cur) + sec > GROUP_MAX_SECONDS):
            close()
        cur.append(r)
    close()
    return out


def group_of(conn, scene_id: int) -> Optional[List[Dict]]:
    row = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None or not enabled(conn, row["project_id"]):
        return None
    return next((g for g in groups(conn, row["project_id"]) if any(x["id"] == scene_id for x in g)), None)


def uses_refs(conn, scene_id: int) -> bool:
    """This shot's clip is made by reference pictures (group or one shot) rather than from a start frame."""
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return row is not None and enabled(conn, row["project_id"]) and eligible(json.loads(row["data"] or "{}"))


def mark(path: str, out_dir: str) -> str:
    """A copy of the picture in out_dir marked as design material: a white BANNER on top and a thick red plus sign over one eye of
    every face found (YuNet; none found: the upper middle). The mark is what let Seedance take in-game pictures (test 2026-09-27)."""
    from PIL import Image, ImageDraw, ImageFont
    from . import text_placement
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + "_marked.png")
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
        return out
    im = Image.open(path).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    band = int(h * 0.07)
    d.rectangle([0, 0, w, band], fill=(255, 255, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", int(band * 0.45))
    except OSError:
        font = ImageFont.load_default()
    d.text((w * 0.04, band * 0.25), BANNER, fill=(0, 0, 0), font=font)
    marks = [((l + (r - l) * 0.33) * w, (t + (b - t) * 0.4) * h, max((r - l) * w * 0.35, w * 0.03))
             for l, t, r, b in (text_placement.face_boxes(path) or [])] or [(w * 0.5, h * 0.3, w * 0.08)]
    stroke = max(int(w / 60), 5)
    for cx, cy, size in marks:
        d.line([cx - size, cy, cx + size, cy], fill=(220, 0, 0), width=stroke)
        d.line([cx, cy - size, cx, cy + size], fill=(220, 0, 0), width=stroke)
    im.save(out)
    return out


def identity_pictures(conn, project_id: int, rows: List[Dict], room: int) -> List[tuple]:
    """(name, path) of one reference picture per character of the shots, in order of appearance, at most `room`."""
    from . import assets
    names: List[str] = []
    for r in rows:
        for n in r["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    links = assets.link_characters(conn, project_id, names)
    out = []
    for n in names:
        ref = (links.get(n) or {}).get("ref")
        if ref and os.path.exists(ref.get("path", "")):
            out.append((n, ref["path"]))
    return out[:max(room, 0)]


def prompt(parts: List[tuple], identities: List[tuple], look: str = "") -> str:
    """parts: [(motion prompt, seconds)] in film order. The wording of the tested P2m prompt: the cut rule, which picture is which
    shot / whose identity, then the shots."""
    n = len(parts)
    head = (f"One clip with {n} shots cut in this order, hard cuts between shots, same place, same light, same characters and outfits "
            f"throughout. " if n > 1 else "One single shot, no cuts. ") + (look.strip() + " " if look.strip() else "")
    head += "The white banner and red marks on the reference pictures are annotations, never part of the video."
    mapping = " ".join(f"Image {i} is the storyboard frame of Shot {i}: Shot {i} starts with exactly this composition, framing and "
                       f"these character positions." for i in range(1, n + 1))
    mapping += " " + " ".join(f"Image {n + k} is {name}: identity only (face, hair, outfit) — not the framing."
                              for k, (name, _) in enumerate(identities, 1))
    t, shots = 0.0, []
    for i, (motion, sec) in enumerate(parts, 1):
        shots.append(f"Shot {i} ({t:.1f}–{t + sec:.1f} s): {str(motion).strip().rstrip('.')}.")
        t += sec
    return head + "\n" + mapping.strip() + "\n" + "\n".join(shots)


def seconds(parts_seconds: List[float]) -> int:
    return int(min(max(math.ceil(sum(parts_seconds) - 1e-6), SEEDANCE_MIN), GROUP_MAX_SECONDS))


def next_route(data: Dict, in_group: bool) -> Optional[str]:
    """After a Seedance refusal: a group shot tries alone, a lone shot goes to Kling. None = no further step."""
    current = route(data)
    if current is None and in_group:
        return "single"
    if current in (None, "single"):
        return "kling"
    return None


def set_route(conn, scene_ids: List[int], value: Optional[str]) -> None:
    for sid in scene_ids:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        data = json.loads(row["data"] or "{}")
        if value is None:
            data.pop("video_route", None)
        else:
            data["video_route"] = value
        conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    conn.commit()


def cut_points(path: str, n: int, ffmpeg: Optional[str] = None) -> Optional[List[float]]:
    """The n-1 hard cuts of a group clip (ffmpeg scdet), or None when the clip does not show exactly n-1 cuts (then the caller cuts
    by the planned seconds). The model decides where its cuts fall (test: ±1 s from the plan), so cutting by the plan alone would
    split a shot across two files."""
    if n < 2:
        return []
    try:
        from .ffmpeg_studio import find_ffmpeg
        ffmpeg = ffmpeg or find_ffmpeg()
        proc = subprocess.run([ffmpeg, "-hide_banner", "-i", path, "-vf", "scdet=threshold=12,metadata=print", "-an", "-f", "null", "-"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception:  # noqa: BLE001 - no ffmpeg / unreadable clip: cut by the plan
        return None
    times = sorted({round(float(x), 3) for x in re.findall(r"lavfi\.scd\.time=([0-9.]+)", proc.stderr + proc.stdout)})
    times = [t for t in times if t > 0.3]
    merged: List[float] = []
    for t in times:                                   # one cut can flag two neighbouring frames
        if not merged or t - merged[-1] > 0.4:
            merged.append(t)
    return merged if len(merged) == n - 1 else None


def split(path: str, group: List[Dict], dest_paths: List[str], ffmpeg: Optional[str] = None) -> Dict:
    """Cut a group clip into one file per shot at its detected cuts (else at the planned seconds scaled to the clip). The whole clip is
    kept as <name>_group.mp4. {"paths", "cuts", "by": "detected"|"plan"}."""
    from .ffmpeg_studio import find_ffmpeg, has_audio, probe_duration
    from .shots import _encode
    ffmpeg = ffmpeg or find_ffmpeg()
    whole = os.path.splitext(path)[0] + "_group.mp4"
    shutil.copyfile(path, whole)
    length = probe_duration(whole)
    cuts = cut_points(whole, len(group), ffmpeg)
    by = "detected"
    if cuts is None:
        by = "plan"
        planned = [float(r["data"].get("duration_s") or 1) for r in group]
        scale = (length or sum(planned)) / sum(planned)
        cuts, t = [], 0.0
        for sec in planned[:-1]:
            t += sec * scale
            cuts.append(round(t, 3))
    bounds = [0.0] + cuts + [length or (cuts[-1] + 2 if cuts else 4)]
    audio = ["-c:a", "aac", "-b:a", "256k"] if has_audio(whole) else ["-an"]
    out = []
    for (start, end), dest in zip(zip(bounds, bounds[1:]), dest_paths):
        proc = subprocess.run([ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", whole, "-t", f"{max(end - start, 0.2):.3f}", *_encode(), *audio,
                               dest], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0 or not os.path.exists(dest):
            shutil.copyfile(whole, dest)
        out.append(dest)
    return {"paths": out, "cuts": cuts, "by": by}


def shot_motion(data: Dict) -> str:
    """A shot's motion text from the Director's own fields (no Claude) — the wording of the tested P2m groups (2026-09-27: 3 shots cut
    in the storyboard's order from these words + the marked pictures)."""
    from .shots import SIZE_WORDS
    perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    acting = "; ".join(f"{k}: {perf[k]}" for k in ("face", "eyes", "body", "timing") if perf.get(k))
    talk = " ".join(f"{x.get('speaker')} speaks (mouth moving, no sound)." for x in data.get("dialogue") or [] if isinstance(x, dict))
    move = str(data.get("camera_move") or "static").replace("_", " ")
    return (f"{SIZE_WORDS.get(data.get('size'), data.get('size') or 'shot')}, {data.get('angle') or 'eye'} angle, camera {move}: "
            f"{str(data.get('image_prompt') or '').strip().rstrip('.')}. " + (f"Acting — {acting}. " if acting else "") + talk).strip()


def code_motion(p, pid: int) -> int:
    """Motion prompts written by code for the shots made by reference pictures that have an approved picture and no prompt yet — the
    group prompt is built from them (docs/THIET_KE_LAI_QC_VA_KET_NOI_2026-09-27.md mục 1: no Claude motion call for Seedance groups).
    Returns how many were written (approved at once: nothing here was guessed by a model)."""
    from . import llm_io
    from .shots import image_scene
    if not enabled(p.conn, pid):
        return 0
    todo = []
    for s in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(s["data"] or "{}")
        if not eligible(d) or p.conn.execute("SELECT 1 FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone():
            continue
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                              (image_scene(p.conn, s["id"]),)).fetchone():
            continue
        todo.append({"id": s["id"], "idx": s["idx"], "motion_prompt": shot_motion(d),
                     "duration_sec": min(max(float(d.get("duration_s") or 2), 1), 30)})
    if not todo:
        return 0
    llm_io.store_motion_prompts(p, pid, {"scenes": [{k: t[k] for k in ("idx", "motion_prompt", "duration_sec")} for t in todo]})
    for t in todo:
        llm_io.approve_motion_prompt(p, t["id"])
    return len(todo)
