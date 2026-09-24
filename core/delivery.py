"""From clips to ONE finished deliverable: render → subtitles → end card → extra formats, each layer optional, each recorded in
`outputs` with what it was made from (so the dashboard can say "⚠ cũ" when a clip, the sound or the settings changed).

Render settings live in the project (`projects.render_settings`), so the manual render in Step 5 and the automatic run make the
same video. File names stay the ones people know: FINAL_VIDEO.mp4, FINAL_VIDEO_sub_<lang>.mp4, FINAL_VIDEO_end.mp4,
FINAL_VIDEO_<W>x<H>.mp4.
"""
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from . import audio_lib, diag, ffmpeg_studio, final_cut, formats, lineage, music, subtitles, voice
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


def final_manifest(p: Pipeline, project_id: int, data_dir: str, clip_paths: List[str], settings: Dict) -> Dict:
    return {"clips": lineage.clip_manifest(p.conn, data_dir, project_id, clip_paths), "settings_hash": render_hash(settings),
            "audio_hash": audio_hash(data_dir, project_id), "aspect": formats.project_aspect(p.project(project_id))}


def status(p: Pipeline, project_id: int, data_dir: str) -> Dict:
    """Latest final render and its layers, each with '⚠ cũ' reasons: {"final": {...}, "layers": [{kind, path, stale}], "best": path}."""
    settings = get_settings(p, project_id)
    fin = lineage.final_status(p.conn, data_dir, project_id, render_hash(settings), audio_hash(data_dir, project_id))
    layers, seen = [], set()
    for kind in ("subtitle", "endcard", "export"):
        for row in p.conn.execute("SELECT * FROM outputs WHERE project_id=? AND kind=? ORDER BY id DESC", (project_id, kind)).fetchall():
            if not os.path.exists(row["path"]) or os.path.normcase(os.path.abspath(row["path"])) in seen:
                continue                                  # the same file name was written again later: only its newest record counts
            seen.add(os.path.normcase(os.path.abspath(row["path"])))
            layers.append({"id": row["id"], "kind": kind, "path": row["path"], "parent_id": row["parent_id"],
                           "stale": lineage.layer_status(p.conn, row, fin), "at": row["created_at"]})
            if kind != "export":
                break                                     # only the newest subtitle / end card matters
    best = latest_layer(p, project_id)
    return {"final": fin, "layers": layers, "best": best["path"] if best else fin.get("path")}


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
    placed = voice.place_on_timeline(p.conn, project_id, data_dir, settings["transition"], settings["fade"], paths)
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
    ffmpeg_studio.render_final(paths, out, durations, settings["transition"], settings["fade"], track, settings["music_volume"],
                               extras, keep_audio, formats.spec(aspect)["render"] if aspect else None)
    oid = record(p, project_id, "final", out, None, final_manifest(p, project_id, data_dir, paths, settings))
    return {"path": out, "output_id": oid, "seconds": final_cut.total_seconds(durations, settings["transition"], settings["fade"])}


def subtitle_layer(p: Pipeline, project_id: int, data_dir: str, parent_id: Optional[int] = None, llm=None,
                   cues: Optional[list] = None, force: bool = False) -> Optional[Dict]:
    """Burn the project's subtitle settings into a copy of the render. None when subtitles are off (unless forced) or there is
    no line. Cues are timed from the voice lines when they exist, else estimated with the SAVED transition (not a default)."""
    sub = subtitles.get_settings(p, project_id)
    if not (sub["enabled"] or force):
        return None
    parent = _parent(p, project_id, parent_id, ("final",))
    if parent is None:
        raise ValueError("chưa có video cuối để in phụ đề")
    rs = get_settings(p, project_id)
    if cues is None:
        cues = subtitles.build_cues(p, data_dir, project_id, rs["transition"], rs["fade"])
        if cues and sub["lang"] != "src":
            cues = subtitles.translate(llm, cues, sub["lang"])
    if not cues:
        return None
    out = os.path.join(output_dir(data_dir, project_id), f"FINAL_VIDEO_sub_{sub['lang']}.mp4")
    res = _burn(parent["path"], cues, out, sub)
    res["output_id"] = record(p, project_id, "subtitle", out, parent["id"],
                              {"settings": sub, "cues": len(cues), "cue_list": [asdict(c) for c in cues]})
    return res


def _burn(src: str, cues: list, out: str, sub: Dict) -> Dict:
    fonts = subtitles.discover()
    preferred = subtitles.font_by_family(fonts, sub["font"]) or subtitles.default_font(fonts)
    font, _ = subtitles.font_for_text(preferred, fonts, " ".join(c.text for c in cues))
    return subtitles.burn(src, cues, out, font, sub["size"], sub["pos"], sub["color"], sub["speaker"], sub.get("speaker_colors", False))


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
    ffmpeg_studio.append_still(parent["path"], png, float(card.get("seconds") or 3.0), out)
    return {"video": out, "output_id": record(p, project_id, "endcard", out, parent["id"], {"card": card})}


def export_layer(p: Pipeline, project_id: int, data_dir: str, spec: Dict, parent_id: Optional[int] = None) -> Dict:
    """Another size / file-size limit of the most finished version (with subtitles and card when they exist)."""
    parent = _parent(p, project_id, parent_id, ("final", "subtitle", "endcard"))
    if parent is None:
        raise ValueError("chưa có video cuối để xuất")
    w, h = int(spec["w"]), int(spec["h"])
    out = os.path.join(output_dir(data_dir, project_id), f"FINAL_VIDEO_{w}x{h}.mp4")
    fit = spec.get("fit") or "pad"
    size = ffmpeg_studio.probe_size(parent["path"])
    if fit == "crop" and parent["kind"] != "final" and size and abs(size[0] / size[1] - w / h) > 0.01:
        res = _reframe(p, parent, w, h, spec.get("max_mb") or None, out)
    else:
        res = ffmpeg_studio.resize_to_size(parent["path"], out, w, h, spec.get("max_mb") or None, fit=fit)
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
                cur = _burn(cur, cues, os.path.join(work, "sub.mp4"), {**subtitles.DEFAULTS, **man["settings"]})["video"]
        end_row = by_kind.get("endcard")
        if end_row is not None:
            card = json.loads(end_row["manifest"] or "{}").get("card") or {}
            png = card_picture(w, h, {**DEFAULT_CARD, **card}, os.path.join(work, "card.png"))
            ffmpeg_studio.append_still(cur, png, float(card.get("seconds") or 3.0), os.path.join(work, "end.mp4"))
            cur = os.path.join(work, "end.mp4")
        return ffmpeg_studio.resize_to_size(cur, out, w, h, max_mb, fit="pad")
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
