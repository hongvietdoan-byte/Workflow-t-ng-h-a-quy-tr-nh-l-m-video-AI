"""From clips to ONE finished deliverable: render → subtitles → end card → extra formats, each layer optional, each recorded in
`outputs` with what it was made from (so the dashboard can say "⚠ cũ" when a clip, the sound or the settings changed).

Render settings live in the project (`projects.render_settings`), so the manual render in Step 5 and the automatic run make the
same video. File names stay the ones people know: FINAL_VIDEO.mp4, FINAL_VIDEO_sub_<lang>.mp4, FINAL_VIDEO_end.mp4,
FINAL_VIDEO_<W>x<H>.mp4.
"""
import contextlib
import functools
import json
import os
import shutil
import tempfile
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from . import audio_lib, diag, ffmpeg_studio, final_cut, formats, lineage, music, subtitles, text_placement, voice
from .pipeline import Pipeline

DEFAULT_CARD = {"enabled": False, "title": "", "subtitle": "", "seconds": 3.0, "bg": "#000000", "color": "#FFFFFF", "font": ""}
DEFAULTS = {"transition": "cut", "fade": 1.0, "music_volume": 0.6, "keep_audio": None, "end_card": DEFAULT_CARD, "exports": []}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---- settings ---------------------------------------------------------------------------------------------------------
def get_settings(p: Pipeline, project_id: int) -> Dict:
    row = p.project(project_id)
    try:
        saved = json.loads((row["render_settings"] if "render_settings" in row.keys() else None) or "{}")
    except ValueError:
        saved = {}
    out = {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}
    out["end_card"] = {**DEFAULT_CARD, **(out.get("end_card") or {})}
    out["exports"] = [e for e in out.get("exports") or [] if isinstance(e, dict) and e.get("w") and e.get("h")]
    if out["keep_audio"] is None:
        out["keep_audio"] = bool(row["video_audio"])
    return out


def save_settings(p: Pipeline, project_id: int, settings: Dict) -> None:
    clean = {k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}
    if clean["transition"] not in ("cut", "crossfade", "dip_to_black"):
        raise ValueError("transition phải là cut / crossfade / dip_to_black")
    clean["fade"] = min(max(float(clean["fade"]), 0.3), 2.0)
    clean["music_volume"] = min(max(float(clean["music_volume"]), 0.0), 1.0)
    p.set_project_field(project_id, "render_settings", json.dumps(clean, ensure_ascii=False))


def render_hash(settings: Dict) -> str:
    """The part of the settings that changes the render itself (card / exports are layers of their own)."""
    return lineage.settings_hash({k: settings.get(k) for k in ("transition", "fade", "music_volume", "keep_audio")})


def selected_music(data_dir: str, project_id: int) -> Optional[str]:
    _, selected = music.project_dirs(data_dir, project_id)
    files = sorted(os.listdir(selected))
    return os.path.join(selected, files[0]) if files else None


def audio_hash(data_dir: str, project_id: int) -> str:
    """Music + every sound effect / voice line switched on for the mix, with their times and file dates."""
    track = selected_music(data_dir, project_id)
    extras = audio_lib.mix_list(audio_lib.assets_dir(data_dir, project_id))
    stamp = lambda path: round(os.path.getmtime(path), 2) if path and os.path.exists(path) else None  # noqa: E731
    return lineage.settings_hash({"music": [os.path.basename(track) if track else None, stamp(track)],
                                  "extras": [[os.path.basename(e["path"]), e["start"], e["volume"], stamp(e["path"])] for e in extras]})


# ---- outputs table ------------------------------------------------------------------------------------------------------
def record(p: Pipeline, project_id: int, kind: str, path: str, parent_id: Optional[int] = None,
           manifest: Optional[Dict] = None) -> int:
    cur = p.conn.execute("INSERT INTO outputs (project_id, kind, path, parent_id, manifest, created_at, created_by) VALUES (?,?,?,?,?,?,?)",
                         (project_id, kind, path, parent_id, json.dumps(manifest or {}, ensure_ascii=False), _now(), p.actor))
    p.conn.commit()
    return cur.lastrowid


def output_dir(data_dir: str, project_id: int) -> str:
    path = os.path.join(data_dir, str(project_id), "output")
    os.makedirs(path, exist_ok=True)
    return path


LOCK_STALE_SEC = 3600    # a lock older than this was left by a render that died (crash, closed window) and is taken over
_held = threading.local()


@contextlib.contextmanager
def render_lock(data_dir: str, project_id: int):
    """D6: one render of a project at a time (Step 5 button, automatic run, a second window). A file lock (<output>/.render.lock)
    so it also holds across processes; nested calls in the same thread (deliver → render → subtitles) reuse it."""
    path = os.path.join(output_dir(data_dir, project_id), ".render.lock")
    held = getattr(_held, "paths", None)
    if held is None:
        held = _held.paths = set()
    if path in held:
        yield
        return
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - os.path.getmtime(path)
        except OSError:
            age = LOCK_STALE_SEC + 1                     # removed meanwhile: try once more below
        if age < LOCK_STALE_SEC:
            raise ValueError(f"Dự án đang được dựng ở nơi khác (bắt đầu {int(age // 60)} phút trước) — đợi xong rồi làm lại. "
                             f"Nếu chắc chắn không còn bản nào đang dựng, xóa file {path}.") from None
        try:
            os.remove(path)
        except OSError:
            pass
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, f"{os.getpid()} {_now()}".encode("ascii"))
    os.close(fd)
    held.add(path)
    try:
        yield
    finally:
        held.discard(path)
        try:
            os.remove(path)
        except OSError:
            pass


def _locked(fn):
    """Run fn(p, project_id, data_dir, ...) under the project's render lock."""
    @functools.wraps(fn)
    def wrapper(p, project_id, data_dir, *args, **kwargs):
        with render_lock(data_dir, project_id):
            return fn(p, project_id, data_dir, *args, **kwargs)
    return wrapper


def final_manifest(p: Pipeline, project_id: int, data_dir: str, clip_paths: List[str], settings: Dict) -> Dict:
    return {"clips": lineage.clip_manifest(p.conn, data_dir, project_id, clip_paths), "settings_hash": render_hash(settings),
            "audio_hash": audio_hash(data_dir, project_id), "aspect": formats.project_aspect(p.project(project_id))}


def status(p: Pipeline, project_id: int, data_dir: str) -> Dict:
    """Latest final render and its layers, each with '⚠ cũ' reasons: {"final": {...}, "layers": [{kind, path, stale}], "best": path}."""
    settings = get_settings(p, project_id)
    fin = lineage.final_status(p.conn, data_dir, project_id, render_hash(settings), audio_hash(data_dir, project_id))
    current = {"subtitle": subtitles.get_settings(p, project_id), "end_card": settings["end_card"]}
    layers, seen = [], set()
    for kind in ("subtitle", "endcard", "export"):
        for row in p.conn.execute("SELECT * FROM outputs WHERE project_id=? AND kind=? ORDER BY id DESC", (project_id, kind)).fetchall():
            if not os.path.exists(row["path"]) or os.path.normcase(os.path.abspath(row["path"])) in seen:
                continue                                  # the same file name was written again later: only its newest record counts
            seen.add(os.path.normcase(os.path.abspath(row["path"])))
            layers.append({"id": row["id"], "kind": kind, "path": row["path"], "parent_id": row["parent_id"],
                           "stale": lineage.layer_status(p.conn, row, fin) or _layer_change(p, row, current),
                           "at": row["created_at"]})
            if kind != "export":
                break                                     # only the newest subtitle / end card matters
    best = latest_layer(p, project_id)
    best_path = best["path"] if best else fin.get("path")
    best_stale = next((x["stale"] for x in layers if x["path"] == best_path and x["stale"]), None) if best is not None else None
    return {"final": fin, "layers": layers, "best": best_path, "best_stale": best_stale}


def _same(a: Dict, b: Dict) -> bool:
    return lineage.settings_hash(a) == lineage.settings_hash(b)


def _layer_change(p: Pipeline, row, current: Dict, depth: int = 0) -> Optional[str]:
    """D7: what changed since this subtitle / end card / export was made — its own settings (read from its manifest), or, for an
    export, the subtitle / card version it was made from. None when it still matches (or it has nothing to compare with)."""
    try:
        man = json.loads(row["manifest"] or "{}")
    except ValueError:
        man = {}
    kind = row["kind"]
    if kind == "subtitle" and man.get("settings"):
        now = current["subtitle"]
        if not now.get("enabled"):
            return "phụ đề đã tắt"
        if not _same({**subtitles.DEFAULTS, **man["settings"]}, {**subtitles.DEFAULTS, **now}):
            return "thiết lập phụ đề đã đổi"
    if kind == "endcard" and "card" in man:
        now = current["end_card"]
        if not now.get("enabled"):
            return "card cuối đã tắt"
        if not _same({**DEFAULT_CARD, **(man["card"] or {})}, {**DEFAULT_CARD, **now}):
            return "card cuối đã đổi"
    if row["parent_id"] is not None and depth < 5:
        parent = p.conn.execute("SELECT * FROM outputs WHERE id=?", (row["parent_id"],)).fetchone()
        if parent is not None and parent["kind"] in ("subtitle", "endcard"):
            newest = lineage.latest_output(p.conn, row["project_id"], parent["kind"])
            if newest is not None and newest["id"] != parent["id"]:
                return {"subtitle": "đã có phụ đề mới hơn", "endcard": "đã có card cuối mới hơn"}[parent["kind"]]
            if _layer_change(p, parent, current, depth + 1):
                return {"subtitle": "phụ đề của bản gốc đã cũ", "endcard": "card cuối của bản gốc đã cũ"}[parent["kind"]]
    return None


def latest_layer(p: Pipeline, project_id: int):
    """The most finished version of the latest render: end card > subtitles > final (a layer made from an older render is skipped)."""
    fin = lineage.latest_output(p.conn, project_id, "final")
    if fin is None:
        return None
    best = fin
    for kind in ("subtitle", "endcard"):
        row = p.conn.execute("SELECT * FROM outputs WHERE project_id=? AND kind=? ORDER BY id DESC LIMIT 1", (project_id, kind)).fetchone()
        if row is None or not os.path.exists(row["path"]):
            continue
        chain, cur = [], row["parent_id"]
        while cur is not None:
            chain.append(cur)
            r = p.conn.execute("SELECT parent_id FROM outputs WHERE id=?", (cur,)).fetchone()
            cur = r["parent_id"] if r else None
        if fin["id"] in chain and (best["id"] in chain or best["id"] == fin["id"]):
            best = row
    return best


# ---- the layers ------------------------------------------------------------------------------------------------------------
_IMPACT = None


def impact_times(directory: str) -> List[float]:
    """D9: the starts of the effects in the mix that are hits (impact, explosion, gunshot, punch…), from their labels."""
    import re
    global _IMPACT
    _IMPACT = _IMPACT or re.compile(r"(?<!\w)(impact|explosion|explode|blast|gunshot|gun ?shot|punch|hit|slam|body fall|va chạm|nổ|"
                                    r"tiếng súng|bắn|đấm|đập mạnh)(?!\w)", re.I)
    return sorted(round(float(e.get("start") or 0), 2) for e in audio_lib.load(directory)
                  if e.get("kind") == "sound_effect" and e.get("use") and e.get("state") == "succeeded"
                  and _IMPACT.search(str(e.get("label") or "")))[:12]


def twist_times(p: Pipeline, project_id: int, rows: List[Dict], durations: List[float], transition: str = "cut", fade: float = 1.0) -> List[float]:
    """D6: where the film turns — the start of the first shot of a script section called TWIST / CAO TRÀO / CLIMAX, else the first ⭐ hero
    shot — on the render's own timeline (the clips' cut lengths). At most two times."""
    import re
    heads = {r["idx"]: r["heading"] or "" for r in p.conn.execute("SELECT idx, heading FROM story_scenes WHERE project_id=?",
                                                                  (project_id,))}
    turn = re.compile(r"twist|cao trào|climax|bước ngoặt", re.IGNORECASE)
    overlap = fade if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    t, seen, marked, hero = 0.0, set(), [], None
    for r, d in zip([r for r in rows if r.get("path")], durations):
        row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (r.get("scene_id"),)).fetchone() if r.get("scene_id") else None
        data = json.loads(row["data"] or "{}") if row else {}
        sc = data.get("story_scene")
        if sc is not None and sc not in seen:
            seen.add(sc)
            if t > 1 and turn.search(heads.get(sc, "")):
                marked.append(round(t, 2))
        if hero is None and data.get("shot_role") == "hero" and t > 1:
            hero = round(t, 2)
        t += float(d) - overlap
    return (marked or ([hero] if hero is not None else []))[:2]


def sound_plan(p: Pipeline, rows: List[Dict], durations: List[float], transition: str = "cut", fade: float = 1.0) -> Dict:
    """director.md Đ9: the music silences the Director planned per shot (sound.music cut / in / breath) on the render's timeline."""
    from . import sound_intent
    datas = []
    for r in [r for r in rows if r.get("path")]:
        row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (r.get("scene_id"),)).fetchone() if r.get("scene_id") else None
        datas.append(json.loads(row["data"] or "{}") if row else {})
    return sound_intent.music_plan(datas, durations, transition, fade, tuple(ffmpeg_studio.OVERLAP_STYLES))


def _colour_match(p: Pipeline, project_id: int, rows: List[Dict], paths: List[str], work_dir: str) -> Optional[List[Dict]]:
    """editing.md E5 (việc code D7): shots of one place and size class are measured against their anchor (black / white points, cast of
    grey things); with the feature `shot_color_match` on, the drifting ones go into the cut as corrected copies (originals untouched).
    `paths` is changed in place. A meter that fails never loses the render."""
    from . import color_match, features
    usable = [r for r in rows if r.get("path")]
    try:
        res = color_match.check_and_fix(p.conn, project_id, usable, work_dir, fix=features.on("shot_color_match"))
    except Exception:  # noqa: BLE001
        return None
    for i, new in res["paths"].items():
        paths[paths.index(usable[i]["path"])] = new
    return res["report"]


def _loudness(path: str) -> Optional[Dict]:
    """editing.md E8 (việc code D11): the delivery's loudness is always measured (free, a few seconds of ffmpeg); with the feature
    `loudness_normalize` on and the measure off target, the sound is brought to -14 LUFS / -1,5 dBTP by a linear gain (video untouched)."""
    from . import features
    try:
        before = ffmpeg_studio.measure_loudness(path)
    except Exception:  # noqa: BLE001 - a meter that fails must not lose the render; the missing number is shown as missing
        return None
    if not before:
        return None
    out = dict(before, problems=ffmpeg_studio.loudness_problems(before))
    if out["problems"] and features.on("loudness_normalize"):
        staged = path + ".norm.mp4"
        try:
            after = ffmpeg_studio.normalize_loudness(path, staged)
            os.replace(staged, path)
            out = dict(after, problems=ffmpeg_studio.loudness_problems(after), before=before, normalized=True)
        except Exception as e:  # noqa: BLE001 - keep the un-normalized render and say why
            out["normalize_error"] = str(e)[:200]
            if os.path.exists(staged):
                os.remove(staged)
    return out


@_locked
def render(p: Pipeline, project_id: int, data_dir: str, music_path: Optional[str] = "auto", clips: Optional[List[str]] = None,
           durations: Optional[List[float]] = None, settings: Optional[Dict] = None) -> Dict:
    """Cut the clips (the chosen ones, or every usable clip) with the project's render settings, the selected music and the
    mix (sound effects + voice lines placed on the timeline). Returns {"path", "output_id", "seconds"}."""
    settings = settings or get_settings(p, project_id)
    rows = final_cut.collect_clips_for_render(p.conn, data_dir, project_id, clips)
    paths = [r["path"] for r in rows if r.get("path")]
    if not paths:
        raise ValueError("chưa có clip nào để ghép")
    if durations is None or len(durations) != len(paths):
        durations = [final_cut.clip_seconds(r["path"], r.get("requested_sec")) for r in rows]
    problems = final_cut.render_problems(durations, settings["transition"], settings["fade"])
    if problems:
        raise ValueError("; ".join(problems))
    placed = voice.place_on_timeline(p.conn, project_id, data_dir, settings["transition"], settings["fade"], paths, durations)
    keep_audio = settings["keep_audio"]
    if placed and keep_audio:        # AU-e: the video model's own speech under the Vietnamese TTS lines = two voices at once
        keep_audio = False
        from . import diag
        diag.record(p.conn, "delivery", "info", "đã có giọng thoại TTS: tắt tiếng gốc của clip trong bản ghép (tránh 2 giọng chồng nhau)",
                    "clip_audio_muted", project_id)
    track = selected_music(data_dir, project_id) if music_path == "auto" else music_path
    extras = audio_lib.mix_list(audio_lib.assets_dir(data_dir, project_id))
    aspect = formats.project_aspect(p.project(project_id))
    out = os.path.join(output_dir(data_dir, project_id), "FINAL_VIDEO.mp4")
    originals = list(paths)                   # lineage follows the shots' own clips, never the colour-matched copies
    colour = _colour_match(p, project_id, rows, paths, os.path.join(output_dir(data_dir, project_id), "_colour"))
    from . import features
    amb = None
    if features.on("ambience_bed"):            # D4/D5: a quiet bed per scene from the person's sound library, under everything
        from . import ambience
        try:
            amb = ambience.beds(p.conn, rows, durations, os.path.join(output_dir(data_dir, project_id), "_ambience"),
                                settings["transition"], settings["fade"])
            extras = list(extras) + [dict({k: e[k] for k in ("path", "start", "volume")}, key=False) for e in amb["extras"]]
        except Exception as e:  # noqa: BLE001 - no bed is better than no render; the reason is kept
            amb = {"extras": [], "missing": [], "error": str(e)[:200]}
    breaths = twist_times(p, project_id, rows, durations, settings["transition"], settings["fade"]) if features.on("music_breath") and track else []
    music_off, intent = [], None
    plan = sound_plan(p, rows, durations, settings["transition"], settings["fade"])
    if plan["planned"]:                        # director.md Đ9: the Director's music silences (cut … in, breath before a shot)
        if features.on("sound_intent") and track:
            breaths, music_off = sorted(set(breaths) | set(plan["breaths"])), plan["off"]
            intent = {"applied": True, "off": plan["off"], "breaths": plan["breaths"]}
        else:                                  # CHUAN luật 1: planned and not applied is said, not dropped in silence
            intent = {"applied": False, "planned": plan["planned"],
                      "why": "cờ sound_intent đang TẮT" if track else "bản dựng không có nhạc nền"}
    ffmpeg_studio.render_final(paths, out, durations, settings["transition"], settings["fade"], track, settings["music_volume"],
                               extras, keep_audio, formats.spec(aspect)["render"] if aspect else None, breaths=breaths,
                               music_off=music_off)
    hits = impact_times(audio_lib.assets_dir(data_dir, project_id)) if features.on("impact_shake") else []
    shake_error = None
    if hits:                              # D9: the frame shakes on the hits the sound design placed
        staged = out + ".shake.mp4"
        try:
            ffmpeg_studio.add_shake(out, staged, hits)
            os.replace(staged, out)
        except Exception as e:  # noqa: BLE001 - the unshaken render is kept; the reason goes into the manifest
            shake_error, hits = str(e)[:200], []
            if os.path.exists(staged):
                os.remove(staged)
    manifest = final_manifest(p, project_id, data_dir, originals, settings)
    manifest["loudness"] = _loudness(out)
    manifest["color_match"] = colour
    if breaths:
        manifest["music_breaths"] = breaths
    if intent is not None:
        manifest["sound_intent"] = intent
    if hits:
        manifest["shakes"] = hits
    if shake_error:
        manifest["shake_error"] = shake_error
    if amb is not None:
        manifest["ambience"] = {"beds": [{"scene": e["scene"], "sound": e["sound"]} for e in amb["extras"]],
                                "missing": amb["missing"], **({"error": amb["error"]} if amb.get("error") else {})}
    manifest["timeline"] =[{"idx": r.get("idx"), "scene_id": r.get("scene_id"), "seconds": float(d)} for r, d in zip(rows, durations)]
    manifest["transition"], manifest["fade"] = settings["transition"], settings["fade"]
    oid = record(p, project_id, "final", out, None, manifest)
    return {"path": out, "output_id": oid, "seconds": final_cut.total_seconds(durations, settings["transition"], settings["fade"])}


@_locked
def subtitle_layer(p: Pipeline, project_id: int, data_dir: str, parent_id: Optional[int] = None, llm=None,
                   cues: Optional[list] = None, force: bool = False) -> Optional[Dict]:
    """Burn the project's subtitle settings into a copy of the render. None when subtitles are off (unless forced) or there is
    no line. Cues are timed from the voice lines when they exist, else estimated with the SAVED transition (not a default)."""
    sub = subtitles.get_settings(p, project_id)
    hud_only = not (sub["enabled"] or force)      # subtitles off: game notices (on_screen_text) are story, they are still drawn
    parent = _parent(p, project_id, parent_id, ("final",))
    if parent is None:
        if hud_only:
            return None
        raise ValueError("chưa có video cuối để in phụ đề")
    if cues is None:
        cues = subtitle_cues(p, project_id, data_dir, parent)
        if hud_only:
            cues = [c for c in cues if c.speaker == subtitles.HUD]
        elif cues:   # D8: saved translations + the person's fixes; Claude only for lines never translated
            cues = subtitles.localize(llm, cues, sub["lang"], data_dir, project_id)
    elif hud_only:
        cues = [c for c in cues if c.speaker == subtitles.HUD]
    if not cues:
        return None
    out = os.path.join(output_dir(data_dir, project_id), "FINAL_VIDEO_hud.mp4" if hud_only else f"FINAL_VIDEO_sub_{sub['lang']}.mp4")
    with ffmpeg_studio.atomic_output(out) as staged:
        res = _burn(parent["path"], cues, staged, sub, text_placement.zones(p.conn, project_id))
    res.update(video=out, srt=os.path.splitext(out)[0] + ".srt")
    res["output_id"] = record(p, project_id, "subtitle", out, parent["id"],
                              {"settings": sub, "cues": len(cues), "cue_list": [asdict(c) for c in cues]})
    return res


def subtitle_cues(p: Pipeline, project_id: int, data_dir: str, final_row=None) -> list:
    """D2: subtitle lines timed on the render they go into — the clips it used, their seconds and its transition (kept in the final
    render's manifest); a render made before that was recorded falls back to the saved settings + the usable clips."""
    row = final_row if final_row is not None else lineage.latest_output(p.conn, project_id, "final")
    try:
        man = json.loads(row["manifest"] or "{}") if row is not None else {}
    except ValueError:
        man = {}
    rs = get_settings(p, project_id)
    if man.get("timeline"):
        return subtitles.build_cues(p, data_dir, project_id, man.get("transition", rs["transition"]), man.get("fade", rs["fade"]),
                                    timeline=man["timeline"])
    return subtitles.build_cues(p, data_dir, project_id, rs["transition"], rs["fade"])


def _burn(src: str, cues: list, out: str, sub: Dict, zones: Optional[Dict] = None) -> Dict:
    fonts = subtitles.discover()
    preferred = subtitles.font_by_family(fonts, sub["font"]) or subtitles.default_font(fonts)
    font, _ = subtitles.font_for_text(preferred, fonts, " ".join(c.text for c in cues))
    return subtitles.burn(src, cues, out, font, sub["size"], sub["pos"], sub["color"], sub["speaker"], sub.get("speaker_colors", False),
                          zones=zones)


def _parent(p: Pipeline, project_id: int, parent_id: Optional[int], kinds) -> Optional[Dict]:
    if parent_id is not None:
        row = p.conn.execute("SELECT * FROM outputs WHERE id=?", (parent_id,)).fetchone()
    else:
        row = latest_layer(p, project_id) if kinds != ("final",) else lineage.latest_output(p.conn, project_id, "final")
    return dict(row) if row is not None and os.path.exists(row["path"]) else None


def card_picture(width: int, height: int, card: Dict, out_png: str) -> str:
    """Draw the end card (title + optional second line, centred) with a font that has every letter of the text."""
    from PIL import Image, ImageColor, ImageDraw, ImageFont
    bg = ImageColor.getrgb(card.get("bg") or "#000000")
    fg = ImageColor.getrgb(card.get("color") or "#FFFFFF")
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    fonts = subtitles.discover()
    text_all = f"{card.get('title', '')} {card.get('subtitle', '')}"
    preferred = subtitles.font_by_family(fonts, card.get("font") or "") or subtitles.default_font(fonts)
    font, _ = subtitles.font_for_text(preferred, fonts, text_all)
    short = min(width, height)

    def load(size):
        try:
            return ImageFont.truetype(font.path, size) if font else ImageFont.load_default()
        except OSError:
            return ImageFont.load_default()

    blocks = [(card.get("title") or "").strip(), (card.get("subtitle") or "").strip()]
    sizes = [int(short * 0.075), int(short * 0.045)]
    lines = []
    for text, size in zip(blocks, sizes):
        if not text:
            continue
        f = load(size)
        wrapped = subtitles.wrap_text(text, max(int(width * 0.85 / (size * 0.55)), 8)).split("\n")
        lines += [(w, f, size) for w in wrapped]
    total = sum(int(s * 1.35) for _, _, s in lines)
    y = (height - total) / 2
    for text, f, size in lines:
        w = draw.textlength(text, font=f)
        draw.text(((width - w) / 2, y), text, font=f, fill=fg)
        y += int(size * 1.35)
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    img.save(out_png)
    return out_png


@_locked
def end_card_layer(p: Pipeline, project_id: int, data_dir: str, parent_id: Optional[int] = None,
                   card: Optional[Dict] = None) -> Optional[Dict]:
    card = card or get_settings(p, project_id)["end_card"]
    if not card.get("enabled") or not (card.get("title") or card.get("subtitle")):
        return None
    parent = _parent(p, project_id, parent_id, ("final", "subtitle"))
    if parent is None:
        raise ValueError("chưa có video cuối để thêm card")
    size = ffmpeg_studio.probe_size(parent["path"]) or formats.spec(formats.project_aspect(p.project(project_id)))["render"]
    folder = output_dir(data_dir, project_id)
    png = card_picture(size[0], size[1], card, os.path.join(folder, "end_card.png"))
    out = os.path.join(folder, "FINAL_VIDEO_end.mp4")
    with ffmpeg_studio.atomic_output(out) as staged:
        ffmpeg_studio.append_still(parent["path"], png, float(card.get("seconds") or 3.0), staged)
    return {"video": out, "output_id": record(p, project_id, "endcard", out, parent["id"], {"card": card})}


@_locked
def export_layer(p: Pipeline, project_id: int, data_dir: str, spec: Dict, parent_id: Optional[int] = None) -> Dict:
    """Another size / file-size limit of the most finished version (with subtitles and card when they exist)."""
    parent = _parent(p, project_id, parent_id, ("final", "subtitle", "endcard"))
    if parent is None:
        raise ValueError("chưa có video cuối để xuất")
    w, h = int(spec["w"]), int(spec["h"])
    out = os.path.join(output_dir(data_dir, project_id), f"FINAL_VIDEO_{w}x{h}.mp4")
    fit = spec.get("fit") or "pad"
    size = ffmpeg_studio.probe_size(parent["path"])
    with ffmpeg_studio.atomic_output(out) as staged:
        if fit == "crop" and parent["kind"] != "final" and size and abs(size[0] / size[1] - w / h) > 0.01:
            res = _reframe(p, parent, w, h, spec.get("max_mb") or None, staged)
        else:
            res = ffmpeg_studio.resize_to_size(parent["path"], staged, w, h, spec.get("max_mb") or None, fit=fit)
    res["path"] = out
    res["output_id"] = record(p, project_id, "export", out, parent["id"], {"spec": spec})
    return res


def _reframe(p: Pipeline, top: Dict, w: int, h: int, max_mb: Optional[float], out: str) -> Dict:
    """Cutting a finished version to another shape would cut its subtitles and card text off (a vertical video's subtitles sit
    below a square crop). Instead: crop the plain final render, burn the same subtitle lines again and draw the card for the new
    frame, then compress."""
    chain, row = [], top
    while row is not None:
        chain.append(row)
        row = p.conn.execute("SELECT * FROM outputs WHERE id=?", (row["parent_id"],)).fetchone() if row["parent_id"] else None
    by_kind = {r["kind"]: r for r in chain}
    work = tempfile.mkdtemp()
    try:
        cur = os.path.join(work, "crop.mp4")
        ffmpeg_studio.resize_to_size(by_kind["final"]["path"], cur, w, h, None, fit="crop")
        sub_row = by_kind.get("subtitle")
        if sub_row is not None:
            man = json.loads(sub_row["manifest"] or "{}")
            cues = [subtitles.Cue(**c) for c in man.get("cue_list") or []]
            if cues and man.get("settings"):
                cur = _burn(cur, cues, os.path.join(work, "sub.mp4"), {**subtitles.DEFAULTS, **man["settings"]},
                            text_placement.zones(p.conn, top["project_id"]))["video"]
        end_row = by_kind.get("endcard")
        if end_row is not None:
            card = json.loads(end_row["manifest"] or "{}").get("card") or {}
            png = card_picture(w, h, {**DEFAULT_CARD, **card}, os.path.join(work, "card.png"))
            ffmpeg_studio.append_still(cur, png, float(card.get("seconds") or 3.0), os.path.join(work, "end.mp4"))
            cur = os.path.join(work, "end.mp4")
        return ffmpeg_studio.resize_to_size(cur, out, w, h, max_mb, fit="pad")
    finally:
        shutil.rmtree(work, ignore_errors=True)


@_locked
def deliver(p: Pipeline, project_id: int, data_dir: str, llm=None, music_path: Optional[str] = "auto",
            render_fn: Optional[Callable] = None, subtitle_fn: Optional[Callable] = None, clips=None, durations=None) -> Dict:
    """The whole chain in one go. A failing optional layer is reported (diag + warnings) and the chain goes on: the final video
    always comes out when the render works. render_fn / subtitle_fn: replaceable (automatic run, tests)."""
    warnings = []
    before = lineage.latest_output(p.conn, project_id, "final")
    if render_fn is None:
        final_path = render(p, project_id, data_dir, music_path, clips, durations)["path"]
    else:
        track = selected_music(data_dir, project_id) if music_path == "auto" else music_path
        final_path = render_fn(p, project_id, data_dir, track)
        after = lineage.latest_output(p.conn, project_id, "final")
        if after is None or (before is not None and after["id"] == before["id"]):
            record(p, project_id, "final", final_path, None,
                   final_manifest(p, project_id, data_dir, [c["path"] for c in final_cut.usable_clips(p, data_dir, project_id)],
                                  get_settings(p, project_id)))
    layers = []
    try:
        if subtitle_fn is not None:
            made = subtitle_fn(p, project_id, data_dir, final_path, llm)
            if made:
                fin = lineage.latest_output(p.conn, project_id, "final")
                made["output_id"] = record(p, project_id, "subtitle", made["video"], fin["id"] if fin else None,
                                           {"cues": made.get("cues")})
        else:
            made = subtitle_layer(p, project_id, data_dir, llm=llm)
        if made:
            layers.append(("subtitle", made["video"]))
    except Exception as e:  # noqa: BLE001 - an optional layer never costs the finished video
        warnings.append(f"phụ đề: {e}")
        diag.record(p.conn, "render", "warn", f"phụ đề thất bại, video cuối vẫn có: {e}", "subtitles", project_id)
    try:
        card = end_card_layer(p, project_id, data_dir)
        if card:
            layers.append(("endcard", card["video"]))
    except Exception as e:  # noqa: BLE001
        warnings.append(f"card cuối: {e}")
        diag.record(p.conn, "render", "warn", f"card cuối thất bại: {e}", "end_card", project_id)
    for spec in get_settings(p, project_id)["exports"]:
        try:
            layers.append(("export", export_layer(p, project_id, data_dir, spec)["path"]))
        except Exception as e:  # noqa: BLE001
            warnings.append(f"xuất {spec.get('w')}x{spec.get('h')}: {e}")
            diag.record(p.conn, "render", "warn", f"xuất bản {spec} thất bại: {e}", "export", project_id)
    return {"final": final_path, "layers": layers, "warnings": warnings}


# ---- animatic: the film's rhythm before any video credit ------------------------------------------------------------------
def animatic(p: Pipeline, project_id: int, data_dir: str, with_music: bool = True) -> Dict:
    """Approved pictures held for each scene's planned length, with the voiced lines and the chosen music: judge the pacing and the
    dialogue timing before paying for video. Returns {"path", "seconds", "scenes"}."""
    import tempfile
    aspect = formats.project_aspect(p.project(project_id))
    size = formats.spec(aspect)["render"] if aspect else (1920, 1080)
    rows = p.conn.execute(
        "SELECT s.id, s.idx, s.data, m.duration_sec, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND j.type='image_gen'"
        " AND j.state='approved' ORDER BY j.id DESC LIMIT 1) AS jid FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id"
        " WHERE s.project_id=? ORDER BY s.idx", (project_id,)).fetchall()
    scenes = [r for r in rows if r["jid"] and os.path.exists(os.path.join(data_dir, str(project_id), "images", f"job_{r['jid']}.png"))]
    if not scenes:
        raise ValueError("chưa có ảnh đã duyệt nào để dựng animatic")
    ffmpeg = ffmpeg_studio.find_ffmpeg()
    work = tempfile.mkdtemp(prefix="animatic_")
    stills, durations = [], []
    for r in scenes:
        secs = float(r["duration_sec"] or json.loads(r["data"] or "{}").get("duration_s") or 5)
        img = os.path.join(data_dir, str(project_id), "images", f"job_{r['jid']}.png")
        clip = os.path.join(work, f"{r['idx']:02d}.mp4")
        ffmpeg_studio.run([ffmpeg, "-y", "-loop", "1", "-t", f"{secs:.2f}", "-i", img, "-vf", ffmpeg_studio._fit(size),
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", "-an", clip])
        stills.append(clip)
        durations.append(secs)
    extras = voice.timeline_extras(p.conn, project_id, data_dir, [(r["id"], d) for r, d in zip(scenes, durations)])
    track = selected_music(data_dir, project_id) if with_music else None
    out = os.path.join(output_dir(data_dir, project_id), "ANIMATIC.mp4")
    try:
        ffmpeg_studio.render_final(stills, out, durations, "cut", 1.0, track, 0.5, extras, False, size)
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    return {"path": out, "seconds": sum(durations), "scenes": len(scenes)}
