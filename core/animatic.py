"""Animatic at the storyboard gate (kế hoạch sau #8, S2.4 — 0 USD, ffmpeg only).

Before a single video second is paid for, the person watches the film as it will be cut: each shot's storyboard picture held for its
locked seconds (S2 timeline), a slow move drawn from the shot's `camera_move`, the voice lines where they will fall, the chosen music and
the subtitles. #8 was only seen whole after 42 USD of clips — its length, pacing and story gaps (lỗi 1.2, 1.9) would have shown here.

A still with a push-in is NOT what the video model will make: it shows timing and order, not acting (said on the page)."""
import json
import os
import subprocess
from typing import Dict, List, Optional

from . import audio_lib, ffmpeg_studio, voice

FPS = 24
SIZE = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (960, 960), "4:5": (864, 1080)}
MIN_SHOT = 0.5
ZOOM = 0.08                  # how far a push-in / pull-out travels over a shot (8 % of the frame)


def move_filter(move: str, frames: int, w: int, h: int) -> str:
    """zoompan for a camera move on a still (the picture is scaled to 2× first so the move stays smooth)."""
    n = max(frames, 1)
    m = str(move or "static").lower()
    z, x, y = "1.0", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if m in ("push_in", "dolly_in", "zoom_in", "zoom", "crane_down"):
        z = f"1+{ZOOM}*on/{n}"
    elif m in ("pull_out", "dolly_out", "zoom_out", "crane_up"):
        z = f"{1 + ZOOM}-{ZOOM}*on/{n}"
    elif m in ("pan", "pan_right", "truck", "track", "orbit", "arc", "handheld"):
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*on/{n}"
    elif m in ("pan_left",):
        z, x = f"{1 + ZOOM}", f"(iw-iw/zoom)*(1-on/{n})"
    elif m in ("tilt", "tilt_up", "pedestal"):
        z, y = f"{1 + ZOOM}", f"(ih-ih/zoom)*(1-on/{n})"
    return (f"scale={2 * w}:{2 * h}:force_original_aspect_ratio=increase,crop={2 * w}:{2 * h},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={FPS},format=yuv420p")


def still_clip(image: Optional[str], dst: str, seconds: float, move: str, size, label: str = "", ffmpeg: Optional[str] = None) -> str:
    """A shot's still as a clip of `seconds`; no picture yet → a dark card with the shot's label (said, not hidden)."""
    ffmpeg = ffmpeg or ffmpeg_studio.find_ffmpeg()
    w, h = size
    frames = max(int(round(seconds * FPS)), 1)
    if image and os.path.exists(image):
        cmd = [ffmpeg, "-y", "-v", "error", "-loop", "1", "-i", image, "-vf", move_filter(move, frames, w, h), "-frames:v", str(frames),
               "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", dst]
    else:
        text = (label or "chưa có ảnh").replace(":", r"\:").replace("'", "")
        font = "C\\:/Windows/Fonts/arial.ttf" if os.name == "nt" else ""
        draw = f",drawtext=fontfile='{font}':text='{text}':fontcolor=white:fontsize={w // 18}:x=(w-tw)/2:y=(h-th)/2" if font else ""
        cmd = [ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x202020:s={w}x{h}:r={FPS}:d={seconds:.3f}",
               "-vf", "format=yuv420p" + draw, "-c:v", "libx264", "-preset", "veryfast", "-an", dst]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def shots(p, project_id: int, data_dir: str) -> List[Dict]:
    """The film in order: scene id, idx, the picture (approved, else the newest one made), seconds, camera move."""
    from . import storyboard_gate
    from .shots import image_scene
    out = []
    for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall():
        d = json.loads(r["data"] or "{}")
        img = storyboard_gate.picture_path(p.conn, data_dir, project_id, image_scene(p.conn, r["id"]))[0]   # the picture the gate shows
        if img is None:
            j = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','pending_review') "
                               "ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
            cand = j and os.path.join(data_dir, str(project_id), "images", f"job_{j['id']}.png")
            img = cand if cand and os.path.exists(cand) else None
        out.append({"scene_id": r["id"], "idx": r["idx"], "image": img, "seconds": max(float(d.get("duration_s") or 2.0), MIN_SHOT),
                    "move": d.get("camera_move") or "static", "label": f"S{r['idx']:02d} " + str(d.get("size") or "")})
    return out


def voice_extras(data_dir: str, project_id: int, film: List[Dict]) -> List[Dict]:
    """Each finished voice line inside its shot, in speaking order (the same lead / gap as voice.place_on_timeline)."""
    directory = audio_lib.assets_dir(data_dir, project_id)
    lines: Dict[int, List[Dict]] = {}
    for e in audio_lib.load(directory):
        if e.get("kind") == "tts" and e.get("state") == "succeeded" and e.get("file") and e.get("scene_id"):
            lines.setdefault(e["scene_id"], []).append(e)
    out, t = [], 0.0
    for s in film:
        at = t + voice.LEAD
        for e in sorted(lines.get(s["scene_id"], []), key=lambda x: x.get("line") or 0):
            path = os.path.join(directory, e["file"])
            if os.path.exists(path):
                out.append({"path": path, "start": round(at, 2), "volume": 1.0})
                at += (e.get("duration_ms") or 0) / 1000.0 + voice.GAP
        t += s["seconds"]
    return out


def build(p, project_id: int, data_dir: str, with_music: bool = True, with_subtitles: bool = True) -> Dict:
    """Write <output>/ANIMATIC.mp4. {"path", "seconds", "shots", "missing": [shot labels without a picture], "voices", "music",
    "subtitles"}."""
    from . import delivery, formats, subtitles
    film = shots(p, project_id, data_dir)
    if not film:
        raise ValueError("chưa có shot nào")
    aspect = formats.project_aspect(p.project(project_id)) or "9:16"
    size = SIZE.get(aspect, SIZE["9:16"])
    out_dir = delivery.output_dir(data_dir, project_id)
    work = os.path.join(out_dir, "_animatic")
    os.makedirs(work, exist_ok=True)
    clips = [still_clip(s["image"], os.path.join(work, f"s{s['idx']:03d}.mp4"), s["seconds"], s["move"], size, s["label"]) for s in film]
    durations = [s["seconds"] for s in film]
    extras = voice_extras(data_dir, project_id, film)
    track = delivery.selected_music(data_dir, project_id) if with_music else None
    out = os.path.join(out_dir, "ANIMATIC.mp4")
    ffmpeg_studio.render_final(clips, out, durations, "cut", 0.0, music=track, music_volume=0.35 if extras else 0.6,
                               extras=extras, size=size)
    subbed = None
    if with_subtitles:
        cues = subtitles.build_cues(p, data_dir, project_id, "cut", 0.0, timeline=[{"idx": s["idx"], "seconds": s["seconds"]}
                                                                                     for s in film])
        if cues:
            try:
                sub = subtitles.get_settings(p, project_id)
                subbed = delivery._burn(out, cues, os.path.join(out_dir, "ANIMATIC_sub.mp4"), {**sub, "enabled": True})["video"]
            except Exception as e:  # noqa: BLE001 - the animatic without subtitles still shows timing; the reason is returned
                subbed = None
                return {"path": out, "seconds": round(sum(durations), 2), "shots": len(film),
                        "missing": [s["label"] for s in film if not s["image"]], "voices": len(extras), "music": bool(track),
                        "subtitles": False, "subtitle_error": str(e)[:200]}
    return {"path": subbed or out, "seconds": round(sum(durations), 2), "shots": len(film),
            "missing": [s["label"] for s in film if not s["image"]], "voices": len(extras), "music": bool(track),
            "subtitles": bool(subbed)}
