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
REF_MAX_SIDE = 1280           # reference pictures at or under the 720p output (Volcengine Seedance 2.5 提示词指南, 2026-09-29)
ROUTES = (None, "single", "kling")
OUTFIT_TAG = " OUTFIT"         # identity_pictures: the costume picture of a character, named "<NAME> OUTFIT"


def enabled(conn, project_id: int) -> bool:
    from . import features
    row = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (project_id,)).fetchone()
    return row is not None and row["shot_mode"] == "per_shot" and features.on("seedance_ref_groups")


def route(data: Dict) -> Optional[str]:
    value = data.get("video_route")
    return value if value in ROUTES else None


FACE_SIZES = ("ECU", "CU", "MCU")


def face_closeup(data: Dict) -> bool:
    """S4.1 (flag closeup_start_frame): a close shot with a character in it — its face must stay the approved storyboard picture, so it
    starts from that picture (Kling) instead of being redrawn from reference pictures (#8: a close-up of Kelly came out as anime)."""
    from . import features
    if not (features.on("closeup_start_frame") and str(data.get("size") or "").upper() in FACE_SIZES and bool(data.get("characters"))):
        return False
    from . import lipsync          # 01/10 (S4.2 × S4.1): a close shot whose speaker talks on screen stays in its dialogue take — Kling
    return not (lipsync.enabled() and lipsync.method_for(data) == "take")   # from a start frame takes no voice: the most visible
                                                                            # mouth would lose its lip sync, silently


def eligible(data: Dict) -> bool:
    """A shot that goes by reference pictures: a v3 shot, not sent to Kling after refusals, not a face close-up that keeps its start
    frame (S4.1). S14.44: an old row's `plate_mode` (green-screen plates, removed in S14.9) no longer changes the route — said once
    per project by groups() (diag plate_mode_ignored)."""
    return bool(data.get("shot_no")) and route(data) != "kling" and not face_closeup(data)


def _say_plate_mode_ignored(conn, project_id: int, rows: List[Dict]) -> None:
    """S14.44: old rows that still carry `plate_mode` — the value is read nowhere for behaviour any more; said once per project."""
    if not any((r.get("data") or {}).get("plate_mode") not in (None, "") for r in rows):
        return
    from . import diag
    try:                    # groups() runs on every runner tick: said once, the counter is not blown up
        seen = conn.execute("SELECT 1 FROM diag_events WHERE code='plate_mode_ignored' AND COALESCE(project_id,0)=? LIMIT 1",
                            (project_id or 0,)).fetchone()
    except Exception:  # noqa: BLE001 - no diag table: record() keeps it (_keep_lost)
        seen = None
    if not seen:
        diag.record(conn, "video", "info", "Shot cũ có `plate_mode` (phông xanh, đã bỏ từ S14.9) — bỏ qua giá trị, shot đi đường ảnh "
                    "tham chiếu như shot thường; hash/nhóm shot giữ nguyên.", "plate_mode_ignored", project_id)


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

    rows = _rows(conn, project_id)
    _say_plate_mode_ignored(conn, project_id, rows)
    for r in rows:
        d = r["data"]
        if not d.get("shot_no") or not _groupable(d):
            close()
            continue
        sec = floored(d, d.get("duration_s") or 0)
        if cur and (_group_key(cur[-1]["data"]) != _group_key(d) or len(cur) >= GROUP_MAX_SHOTS
                    or sum(floored(x["data"], x["data"].get("duration_s") or 0) for x in cur) + sec > GROUP_MAX_SECONDS
                    or _estimated_len(cur + [r]) > GROUP_PROMPT_BUDGET):
            close()
        cur.append(r)
    close()
    return out


def _estimated_len(rows: List[Dict]) -> int:
    names: List[str] = []
    for r in rows:
        for n in r["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    # 08/10 (#24): the estimate left out the PLACE render sentences (~330 characters per rendered shot) — a 3-shot group was estimated
    # at 2 923 characters and sent at 4 135 (> 4 000, blocked). Worst case (tính dư): every shot of the group has its own render.
    places = [{"shots": [i]} for i in range(1, len(rows) + 1)]
    return len(prompt([(shot_motion(r["data"]), float(r["data"].get("duration_s") or 2)) for r in rows], [(n, "") for n in names],
                      places=places))


def group_of(conn, scene_id: int) -> Optional[List[Dict]]:
    row = conn.execute("SELECT project_id FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None or not enabled(conn, row["project_id"]):
        return None
    return next((g for g in groups(conn, row["project_id"]) if any(x["id"] == scene_id for x in g)), None)


def uses_refs(conn, scene_id: int) -> bool:
    """This shot's clip is made by reference pictures (group or one shot) rather than from a start frame."""
    row = conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return row is not None and enabled(conn, row["project_id"]) and eligible(json.loads(row["data"] or "{}"))


MARK_STYLES = ("eye_plus", "banner", "corner_plus", "none")


def mark(path: str, out_dir: str, style: str = "eye_plus") -> str:
    """A copy of the picture in out_dir marked as design material: a white BANNER on top and a thick red plus sign over one eye of
    every face found (YuNet; none found: the upper middle). The mark is what let Seedance take in-game pictures (test 2026-09-27).
    style (S4.6 round 2 — the eye plus was drawn INTO a Seedance 2.0 Fast clip, #10 29/09): "eye_plus" as above, "banner" the banner
    only, "corner_plus" the banner + the plus in the picture's bottom-right corner (off every face), "none" an unmarked copy."""
    if style not in MARK_STYLES:
        raise ValueError(f"unknown mark style {style!r}")
    from PIL import Image, ImageDraw, ImageFont
    from . import text_placement
    os.makedirs(out_dir, exist_ok=True)
    import hashlib                        # 28/09: KENTA's and MAXIM's sheets are both '7.png' (assets/24, assets/33) — named by the
    key = hashlib.sha1(os.path.abspath(path).lower().encode("utf-8")).hexdigest()[:10]   # file name alone, one overwrote the other
    tag = "" if style == "eye_plus" else f"_{style}"
    out = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(path))[0]}_{key}_marked{tag}.png")   # and MAXIM's clip showed KENTA
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
        return out
    im = Image.open(path).convert("RGB")
    if max(im.size) > REF_MAX_SIDE:        # Seedance 2.5 guide: a reference sharper than the output makes moiré on grass / fine texture
        k = REF_MAX_SIDE / max(im.size)
        im = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
    w, h = im.size
    if style == "none":
        im.save(out)
        return out
    d = ImageDraw.Draw(im)
    band = int(h * 0.07)
    d.rectangle([0, 0, w, band], fill=(255, 255, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", int(band * 0.45))
    except OSError:
        font = ImageFont.load_default()
    d.text((w * 0.04, band * 0.25), BANNER, fill=(0, 0, 0), font=font)
    if style == "banner":
        im.save(out)
        return out
    if style == "corner_plus":
        marks = [(w * 0.9, h * 0.93, w * 0.05)]
    else:
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
        outfit = assets.outfit_images(conn, project_id, n)
        if outfit:     # 07/10 Khủng Long Đỏ: MAXIM KL / KELLY KL danced in their everyday clothes — only the library face picture
            out.append((n + OUTFIT_TAG, outfit[0]["path"]))   # (everyday look) went, the costume picture never did
    _say_speakers_without_picture(conn, project_id, rows, {n for n, _ in out})
    return out[:max(room, 0)]


def _say_speakers_without_picture(conn, project_id: int, rows: List[Dict], pictured: set) -> None:
    """S14.4 C1b: a SPEAKER of these shots with no identity picture (Kho) is said (diag) — Seedance cannot tell whose mouth moves."""
    from . import dialogue, diag
    who = []
    for r in rows:
        for s, _ in dialogue.scene_lines(r.get("data") or {}):
            s = str(s).strip()
            if s and not dialogue.is_non_speaker(s) and s not in pictured and s.upper() not in {p.upper() for p in pictured} \
                    and s not in who:
                who.append(s)
    if not who:
        return
    msg = (f"Người nói chưa có ảnh định danh: {', '.join(who)} — model không biết ai mở miệng, khớp môi có thể "
           "sai người. Cách xử lý: Bước 1 → Character Bible: gắn ảnh Kho cho nhân vật này rồi gen lại shot.")
    try:                    # called on every runner tick: said once per 10 minutes, the counter is not blown up
        seen = conn.execute("SELECT 1 FROM diag_events WHERE code='speaker_no_identity' AND COALESCE(project_id,0)=? AND message=?"
                            " AND (julianday('now') - julianday(last_at)) * 1440 < 10 LIMIT 1",
                            (project_id or 0, diag.redact(msg)[:400])).fetchone()
    except Exception:  # noqa: BLE001 - no diag table: record() keeps it (_keep_lost)
        seen = None
    if not seen:
        diag.record(conn, "video", "warn", msg, "speaker_no_identity", project_id)


def reads_seconds(model: Optional[str]) -> bool:
    """Seedance 2.5 follows whole-second time marks; 2.0 / 2.0 Fast follow only shot numbers ("2.0 does not respond to timestamps" —
    ClipAI Seedance Model Selection; Volcengine Seedance 2.5 提示词指南, research/craft/trung_quoc/PROMPT.md mục 2). #8's group prompts
    carried 0.0–1.5 s marks to 2.0 and the actions drifted (lỗi 1.5). Unknown model: shot numbers only (works for both)."""
    m = str(model or "").lower()
    return "2.5" in m or "2-5" in m


def whole_marks(secs: List[float]) -> List[tuple]:
    """(start, end) whole seconds per shot, back to back from 0 (2.5 guide: continuous ranges, no gaps, integer seconds); every shot
    keeps at least 1 s."""
    out, t, acc = [], 0, 0.0
    for i, sec in enumerate(secs):
        acc += float(sec)
        end = max(int(round(acc)), t + 1)
        out.append((t, end))
        t = end
    return out


def place_pictures(data_dir: str, project_id: int, rows: List[Dict]) -> List[Dict]:
    """Local renders only, appended after identities; a shared file keeps one Image number."""
    from . import place_refs
    if not place_refs.enabled():
        return []
    out, seen = [], {}
    for number, row in enumerate(rows, 1):
        ref = place_refs.shot_ref(data_dir, project_id, row["id"])
        if not ref or not os.path.isfile(ref["path"]):
            continue
        key = os.path.normcase(os.path.abspath(ref["path"]))
        if key not in seen:
            seen[key] = {"path": ref["path"], "shots": []}
            out.append(seen[key])
        seen[key]["shots"].append(number)
    return out


def prompt(parts: List[tuple], identities: List[tuple], look: str = "", clip_seconds: Optional[float] = None,
           model: Optional[str] = None, places: Optional[List[Dict]] = None) -> str:
    """parts: [(motion prompt, seconds)] in film order. The wording of the tested P2m prompt: the cut rule, which picture is which
    shot / whose identity, then the shots. clip_seconds: the length really asked for (Seedance makes ≥ 4 s) — the shots' marks are
    stretched to it, so the last shot does not end before the clip does (review 2026-09-27). model: time marks only for a model that
    reads them (`reads_seconds`); the others get "Shot N:" alone (S4.8, 2026-09-29)."""
    n = len(parts)
    total = sum(float(s) for _, s in parts) or 1.0
    if clip_seconds and clip_seconds > total:
        parts = [(m, float(s) * clip_seconds / total) for m, s in parts]
    head = (f"One clip with {n} shots cut in this order, hard cuts between shots, same place, same light, same characters and outfits "
            f"throughout. " if n > 1 else "One single shot, no cuts. ") + (look.strip() + " " if look.strip() else "")
    from . import features               # S4.7: with the Subject Library the pictures may go unmarked — a sentence true either way
    head += ("Any white banner or red mark on a reference picture is an annotation, never part of the video. "
             if features.on("seedance_subjects") else
             "The white banner and red marks on the reference pictures are annotations, never part of the video. ")
    head += "The buildings and the landmark behind the people keep exactly the shape they have in the storyboard frames."   # 28/09: a spire became a dome
    mapping = " ".join(f"Image {i} is the storyboard frame of Shot {i}: Shot {i} starts with exactly this composition, framing and "
                       f"these character positions." for i in range(1, n + 1))
    dressed = {name[:-len(OUTFIT_TAG)] for name, _ in identities if name.endswith(OUTFIT_TAG)}
    strip = features.on("outfit_strip_model")   # KLD-7 (08/10): Kelly KL took the silver hair of the model wearing the OUTFIT

    def says(name: str) -> str:
        if name.endswith(OUTFIT_TAG):
            who = name[:-len(OUTFIT_TAG)]
            return (f"the OUTFIT {who} wears in this video: dress {who} exactly in these clothes, cap, shoes and accessories "
                    + (f"— ignore the hair, face and body of any person modelling these clothes (those come only from {who}'s "
                       "identity picture); wear each accessory exactly as the picture shows it, for the whole clip " if strip else "")
                    + "— not the framing")
        if name in dressed:
            return f"{name}: identity only (face, hair, body build) — NOT the clothes, which come only from the OUTFIT picture"
        return f"{name}: identity only (face, hair, outfit) — not the framing"
    mapping += " " + " ".join(f"Image {n + k} is {says(name)}." for k, (name, _) in enumerate(identities, 1))
    for k, place in enumerate(places or [], 1):
        targets = ", ".join(f"Shot {i}" for i in place["shots"])
        mapping += (f" Image {n + len(identities) + k} is the PLACE render for {targets}: keep the buildings, tower, walls and ground "
                    "exactly as in this image throughout those shots, including during camera movement. "
                    "It decides architecture over conflicting text or storyboard details; people, outfits and starting framing "
                    "still follow their own references. Never move, add or remove a building.")
    marks = whole_marks([float(sec) for _, sec in parts]) if reads_seconds(model) else [None] * n
    shots = [f"Shot {i}" + (f" ({mk[0]}–{mk[1]} s)" if mk else "") + f": {str(motion).strip().rstrip('.')}."
             for i, ((motion, _), mk) in enumerate(zip(parts, marks), 1)]
    text = head + "\n" + mapping.strip() + "\n" + "\n".join(shots)
    # 08/10 (#24): a character named in Vietnamese ("YÊU NỮ TÀ LINH DẠNG 1") put accented letters into "Image N is …" and the shot
    # lines — the whole send was blocked as "prompt còn chữ tiếng Việt" though every Director field was translated. The names go
    # without accents (the same spelling in the mapping and the shots, so picture and name still match); spoken lines are untouched.
    for name in sorted({nm[:-len(OUTFIT_TAG)] if nm.endswith(OUTFIT_TAG) else nm for nm, _ in identities}, key=len, reverse=True):
        if ascii_name(name) == name:
            continue
        for form in dict.fromkeys((name, name.upper(), name.title(), name.capitalize(), name.lower())):   # "Yêu nữ tà linh…" in a motion line
            text = _outside_dialogue(text, lambda s, a=form, b=ascii_name(form): s.replace(a, b))
    return text


def ascii_name(name: str) -> str:
    """A character name without Vietnamese accents ("YÊU NỮ TÀ LINH DẠNG 1" → "YEU NU TA LINH DANG 1"; đ → d)."""
    import unicodedata
    text = str(name).replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def _outside_dialogue(text: str, change) -> str:
    """Apply `change` to the text except the quoted spoken lines (Dialogue (…): "…" stays Vietnamese on purpose, S4.2)."""
    out, last = [], 0
    for m in re.finditer(r'Dialogue \([^)]*\): "[^"]*"', text):
        out.append(change(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(change(text[last:]))
    return "".join(out)


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
        planned = [floored(r["data"], r.get("duration_s") or r["data"].get("duration_s") or 1) for r in group]
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


VI = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)
PROMPT_MAX = 4000          # Seedance 2.0 (clipai.PROMPT_LIMITS)
GROUP_PROMPT_BUDGET = 3500  # a group is closed before its prompt passes this — room left for a retry's "Fix:" sentence
SHORT_SHOT = 1.0            # a shot under 1 s inside a group is probably skipped by the model (said, not hidden)
MIN_GROUP_SHOT = 1.5        # #8 2026-09-28: shots of 0.46-1.4 s in group clips — the model skipped or froze the action (QC rejected
MIN_ACTION_SHOT = 2.0       # S1·4, S4·4 "never turns away", S5·1 "does not collapse"). A shot in a group gets at least this long;
_BIG_ACTION = re.compile(r"\b(turns?|turning|walks?|walking|runs?|running|falls?|falling|collapses?|collaps|jumps?|steps? (away|back|forward)"
                         r"|pivots?|spins?|kneels?|stands? up|sits? down|hugs?|embrac)\w*", re.I)   # a big body action even longer


def shot_floor(data: Dict) -> float:
    """The least time a shot needs inside a group clip."""
    text = " ".join(str(x or "") for x in ((data.get("motion_en") or {}).get("action"), data.get("action"), data.get("end_state"),
                                              (data.get("motion_en") or {}).get("end_state")))
    return MIN_ACTION_SHOT if _BIG_ACTION.search(text) else MIN_GROUP_SHOT


def floored(data: Dict, sec: float) -> float:
    return round(max(float(sec or 0), shot_floor(data)), 2)


def has_vietnamese(text: str) -> bool:
    return bool(VI.search(text or ""))


def _en(data: Dict, key: str):
    """The English form of a Director field: `motion_en` (translated once, claude_tasks.translate_motion_fields) or the field itself."""
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    return en.get(key) if en.get(key) else data.get(key)


def shot_motion(data: Dict, voice: bool = False) -> str:
    """A shot's motion text from the Director's fields (no Claude): size / angle / camera, then WHAT HAPPENS (the action, the end
    state), the acting, who speaks. No picture words: the shot's storyboard frame carries the composition, the identity pictures the
    looks (review 2026-09-27: image_prompt repeated looks and the style line in every shot → group prompts past 4,000 characters).
    voice: the shot goes with its own voice line (lip sync) — "no sound" would contradict the attached audio."""
    from .shots import SIZE_WORDS
    perf = _en(data, "performance")
    perf = perf if isinstance(perf, dict) else {}
    acting = "; ".join(f"{k}: {perf[k]}" for k in ("face", "eyes", "body", "timing") if perf.get(k))
    speakers = [str(x.get("speaker")) for x in data.get("dialogue") or [] if isinstance(x, dict) and x.get("speaker")]
    if voice:
        talk = " ".join(f"{s} says the line of the attached voice, lips in sync." for s in speakers)
    else:
        talk = " ".join(f"{s} speaks (mouth moving, no sound)." for s in speakers)
    if perf.get("intensity", 0) >= 4 or data.get("size") in ("CU", "ECU"):
        acting = soften(acting)            # Seedance 2.5 guide: over-strong emotion words make eyes glow — milder word, plain eyes
    eyes_guard = (" Natural human eyes, no glowing eyes." if acting and (perf.get("intensity", 0) >= 4) else "")
    move = str(data.get("camera_move") or "static").replace("_", " ")
    framing = _framing(data)
    action = str(_en(data, "action") or "").strip().rstrip(".")
    end = str(_en(data, "end_state") or "").strip().rstrip(".")
    from . import motion_physics
    body = motion_physics.sentence(action)          # S4.4: one body-physics sentence for the kind of action (weight, contact)
    return (f"{SIZE_WORDS.get(data.get('size'), data.get('size') or 'shot')}, {data.get('angle') or 'eye'} angle, camera {move}: "
            + (f"framing {framing}. " if framing else "") + (f"{action}. " if action else "") + (f"{body} " if body else "")
            + (f"It ends with {end}. " if end else "")
            + (f"Acting — {acting}.{eyes_guard} " if acting else "") + talk).strip()


_STRONG = ((r"\b(extremely|insanely|wildly|utterly|incredibly|hysterically)\s+", ""), (r"\becstatic\b", "delighted"),
           (r"\bhysterical\b", "distraught"), (r"\bterrified\b", "frightened"), (r"\benraged\b", "angry"),
           (r"\bfurious\b", "angry"), (r"\bmaniac(al)?\b", "intense"), (r"\bin shock\b", "stunned"))


def soften(text: str) -> str:
    """Over-strong emotion words → plainer ones (Volcengine Seedance 2.5 提示词指南: 狂热 / 极度震惊 → 惊讶, fewer glowing-eye faults).
    The acting stays a visible behaviour; only the loudest adjectives go."""
    for pat, new in _STRONG:
        text = re.sub(pat, new, text, flags=re.I)
    return text


def busy_shots(rows: List[Dict]) -> List[int]:
    """Shots whose action lists 3+ body actions (Seedance 2.5 guide: describe an action in general terms, detail only 1–2 highlights;
    #8 put 3–4 actions in ≤ 15 s and the model skipped some). A hint for the person, not a block."""
    out = []
    for i, r in enumerate(rows, 1):
        text = str(_en(r["data"], "action") or "")
        if len(_BIG_ACTION.findall(text)) + text.lower().count(" then ") >= 3:
            out.append(i)
    return out


FRAMING_MAX = 140


def _framing(data: Dict) -> str:
    """The composition in a few words (who is where, over whose shoulder) from the Director's blocking — #8 2026-09-28: with the
    storyboard frame alone, S1·3 (over Kenta's shoulder) came out with Kenta facing the camera. English only (a Vietnamese blocking
    stays out: the group prompt must be English); cut at a clause so it stays short."""
    text = " ".join(str(data.get("blocking") or "").split())
    if not text or has_vietnamese(text):
        return ""
    text = re.sub(r"(?i)^same (over-the-shoulder )?composition as (the )?previous shot:?\s*", "", text)
    if len(text) > FRAMING_MAX:
        cut = max(text.rfind(",", 0, FRAMING_MAX), text.rfind(";", 0, FRAMING_MAX))
        text = text[: cut if cut > 40 else FRAMING_MAX]
    return text.strip(" ,;.")


def lint_group(text: str, n_frames: int, n_pictures: int, n_expected_pictures: int, secs: List[float], audio: bool,
               model: Optional[str] = None) -> List[str]:
    """Faults of a reference-only request that can be seen before paying (review 2026-09-27). Hard faults block the send.
    model: Seedance 2.5 takes 5 000 characters (clipai.PROMPT_LIMITS) — a group with its dialogue block (S4.2) needs the room."""
    out = []
    limit = 5000 if reads_seconds(model) else PROMPT_MAX
    if len(text) > limit:
        out.append(f"prompt dài {len(text)} ký tự > {limit} (Seedance sẽ từ chối)")
    if has_vietnamese(re.sub(r'Dialogue \([^)]*\): "[^"]*"', "", text)):   # S4.2: the spoken lines stay Vietnamese on purpose
        out.append("prompt còn chữ tiếng Việt (chưa dịch trường Director)")
    if n_pictures != n_expected_pictures:
        out.append(f"gửi {n_pictures} ảnh nhưng bảng Image↔Shot ghi {n_expected_pictures} (thiếu khung / ảnh nhận diện)")
    if n_pictures > MAX_PICTURES:
        out.append(f"{n_pictures} ảnh vượt giới hạn {MAX_PICTURES}; tách nhóm shot trước khi gửi, không bỏ ảnh trang phục/địa điểm")
    if audio and "no sound" in text:
        out.append("có gửi giọng nhưng prompt ghi 'no sound'")
    return out


def short_shots(secs: List[float]) -> List[int]:
    return [i for i, s in enumerate(secs, 1) if len(secs) > 1 and s < SHORT_SHOT]


def write_by_code(p, pid: int, llm=None) -> Dict:
    """The motion step shared by the automatic run and the Step 3 button (08/10: the button paid Claude for shots the automatic run
    writes by code): ONE Claude call turns the Director's Vietnamese fields into English (only when some are Vietnamese), then every
    reference shot — missing or outdated — gets its prompt from code. Returns {translated, by_code, warn}."""
    from . import claude_tasks, lineage, llm_runner
    out = {"translated": 0, "by_code": 0, "warn": None}
    if not enabled(p.conn, pid):
        return out
    if llm is not None:
        try:
            out["translated"] = claude_tasks.translate_motion_fields(p, pid, llm)
        except (llm_runner.LlmError, ValueError) as e:
            out["warn"] = f"không dịch được trường tiếng Việt ({e}) — prompt nhóm sẽ bị chặn khi gửi nếu còn tiếng Việt"
    stale = [sid for sid, r in lineage.scan(p.conn, pid).items() if r["motion_stale"] and uses_refs(p.conn, sid)]
    out["by_code"] = code_motion(p, pid, redo_ids=stale)
    return out


def code_motion(p, pid: int, redo_ids=()) -> int:
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
        if not eligible(d):
            continue
        if s["id"] in redo_ids:                       # outdated: written again from the Director's fields, never by Claude (review)
            p.conn.execute("DELETE FROM motion_prompts WHERE scene_id=?", (s["id"],))
        elif p.conn.execute("SELECT 1 FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone():
            continue
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                              (image_scene(p.conn, s["id"]),)).fetchone():
            continue
        from . import lipsync
        voice = lipsync.enabled() and lipsync.voiced(lipsync.method_for(d))
        todo.append({"id": s["id"], "idx": s["idx"], "motion_prompt": shot_motion(d, voice=voice),
                     "duration_sec": min(floored(d, float(d.get("duration_s") or 2)), 30)})   # 28/09: a 1 s single was
                                                                                          # cut to 1 s — the collapse was cut off
    if not todo:
        return 0
    llm_io.store_motion_prompts(p, pid, {"scenes": [{k: t[k] for k in ("idx", "motion_prompt", "duration_sec")} for t in todo]})
    for t in todo:
        llm_io.approve_motion_prompt(p, t["id"])
    return len(todo)
