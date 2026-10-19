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
FORM_TAG = " FORM"             # 19/10 (#31 G27): the picture of the FORM a character is in (Kho style "Dạng của nhân vật"), "<NAME> FORM"
OBJECT_TAG = " OBJECT"         # 19/10 (#31 G27): a library object the shots name (prop / skill object with its skin), "<NAME> OBJECT"
TAGS = (OUTFIT_TAG, FORM_TAG, OBJECT_TAG)


def base_name(name: str) -> str:
    """The person / object name of an identity_pictures entry, without its OUTFIT / FORM / OBJECT tag."""
    for tag in TAGS:
        if name.endswith(tag):
            return name[:-len(tag)]
    return name


def is_person(name: str) -> bool:
    """An identity_pictures entry that is a PERSON's own identity picture (not an outfit, form or object picture)."""
    return not any(name.endswith(tag) for tag in TAGS)


def enabled(conn, project_id: int) -> bool:
    from . import features
    row = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (project_id,)).fetchone()
    return row is not None and row["shot_mode"] == "per_shot" and features.on("seedance_ref_groups")


def route(data: Dict) -> Optional[str]:
    value = data.get("video_route")
    return value if value in ROUTES else None


def eligible(data: Dict) -> bool:
    """A shot that goes by reference pictures: a v3 shot, not sent to Kling after refusals (18/10: the S4.1 face close-up exception —
    flag closeup_start_frame — is removed, see features.REMOVED). S14.44: an old row's `plate_mode` (green-screen plates, removed in S14.9) no longer changes the route — said once
    per project by groups() (diag plate_mode_ignored)."""
    return bool(data.get("shot_no")) and route(data) != "kling"


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
    film each; only groups of 2+ shots (a lone shot is a one-shot clip).
    09/10 (người dùng: bấm chọn bị lag): một lượt màn Video #24 gọi hàm này ~300 lần, mỗi lần dựng prompt mọi shot để ước độ dài
    (≈ 6/8 s một lượt) → `memo.cached` (một lần mỗi lượt Streamlit và trạng thái CSDL; ngoài Dashboard không đệm)."""
    from .memo import cached
    return cached(conn, ("seedance_refs.groups", project_id), lambda: _groups(conn, project_id))


def _groups(conn, project_id: int) -> List[List[Dict]]:
    from .shots import _group_key, _rows
    out: List[List[Dict]] = []
    cur: List[Dict] = []

    def close():
        if len(cur) > 1:
            out.append(list(cur))
        cur.clear()

    rows = _rows(conn, project_id)
    _say_plate_mode_ignored(conn, project_id, rows)
    from . import looks                  # F1 sửa #8: only an FF project gets the gore-restraint sentence (room counted only there)
    ff = looks.is_ff(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())
    dressed = {r["name"] for r in conn.execute("SELECT name, outfit_image_ids FROM characters WHERE project_id=?", (project_id,))
               if (r["outfit_image_ids"] or "").strip()}
    for r in rows:
        d = r["data"]
        if not d.get("shot_no") or not _groupable(d):
            close()
            continue
        sec = floored(d, d.get("duration_s") or 0)
        if cur and (_group_key(cur[-1]["data"]) != _group_key(d) or len(cur) >= GROUP_MAX_SHOTS
                    or sum(floored(x["data"], x["data"].get("duration_s") or 0) for x in cur) + sec > GROUP_MAX_SECONDS
                    or _estimated_len(cur + [r], ff, dressed) > GROUP_PROMPT_BUDGET):
            close()
        cur.append(r)
    close()
    if keep_approved_on() and out:
        kept = person_kept(conn, project_id, [r["id"] for g in out for r in g])
        out = [g for g in out if not (any(r["id"] in kept for r in g) and not all(r["id"] in kept for r in g))]
    return out


# ---- V8 (rà gốc video #27 13/10, G3): a group must not re-make a shot the PERSON already approved ----------------------------------
# (5,6) 788 → 879: shot 6 approved v1, shot 5 failed → the group clip was made again for both, the person "dùng lại bản v1"; (10,11)
# three rounds. With the flag a group with a person-approved, still current member is not sent as a group: every shot of it goes
# alone (a lone shot is a one-shot clip, route "single" in effect) — the approved take stays, only the others are made again. A
# group whose members are ALL approved stays a group (its final upgrade is priced / sent per group clip, core.quality_tier).
def keep_approved_on() -> bool:
    try:
        from . import features
        return features.on("group_keep_approved")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def person_kept(conn, project_id: int, scene_ids: List[int]) -> set:
    """The scenes whose newest clip job is APPROVED BY A PERSON (review_log 'user') and still current: made from the scene's approved
    picture and from the motion prompt as it is now (the clip's own model counted). Never asks the model router (no loop back here)."""
    from . import lineage
    from .shots import image_scene
    aspect = lineage._aspect(conn, project_id)
    out = set()
    for sid in scene_ids:
        job = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='video_gen' AND state NOT IN ('failed','cancelled','rejected')"
                           " ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
        if job is None or job["state"] != "approved":
            continue
        who = conn.execute("SELECT reviewer_type FROM review_log WHERE job_id=? AND decision='approve' ORDER BY id DESC LIMIT 1",
                           (job["id"],)).fetchone()
        if who is None or who["reviewer_type"] != "user":
            continue
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                           (image_scene(conn, sid),)).fetchone()
        keys = job.keys()
        if img is None or ("source_job_id" in keys and job["source_job_id"] and job["source_job_id"] != img["id"]):
            continue
        mp = conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()
        stored = job["input_hash"] if "input_hash" in keys else None
        model = job["model"] if "model" in keys else None
        if mp is None or (stored and stored not in {lineage.video_input_hash(mp, aspect)} | {
                lineage.video_input_hash(mp, aspect, model, a) for a in (True, False) if model}):
            continue
        out.add(sid)
    return out


def _estimated_len(rows: List[Dict], ff: bool = True, dressed: Optional[set] = None) -> int:
    """ff: the project is a Free Fire one (looks.is_ff) — only then may the runner add the gore-restraint sentence; default True
    (worst case, tính dư) for a caller that does not know. dressed: characters with an OUTFIT picture (F1-C: their costume picture
    and its sentence go with the prompt too — identity_pictures; left out of the estimate before)."""
    names: List[str] = []
    for r in rows:
        for n in r["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    # 08/10 (#24): the estimate left out the PLACE render sentences (~330 characters per rendered shot) — a 3-shot group was estimated
    # at 2 923 characters and sent at 4 135 (> 4 000, blocked). Worst case (tính dư): every shot of the group has its own render.
    places = [{"shots": [i]} for i in range(1, len(rows) + 1)]
    motions = [shot_motion(r["data"]) for r in rows]
    from . import looks                  # F1-B: the FF gore-restraint sentence the runner may add (≤ GORE_VIDEO_MAX characters)
    gore = looks.GORE_VIDEO_MAX if ff and looks.gore_words(" ".join(motions) + " " + " ".join(
        str(r["data"].get(k) or "") for r in rows for k in ("image_prompt", "action", "end_state"))) else 0
    ids = []
    for n in names:
        ids.append((n, ""))
        if n in (dressed or ()):
            ids.append((n + OUTFIT_TAG, ""))
    return len(prompt([(m, float(r["data"].get("duration_s") or 2)) for m, r in zip(motions, rows)], ids, places=places)) + gore


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
    if style == "eye_plus" and mark_off_face():
        style = "corner_plus"             # V5 (rà gốc 13/10): flag ref_mark_off_face on → no caller ever marks an eye (a start frame
        #                                   included — quality_samples / experiments still ask for the default "eye_plus")
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


MARK_KEY = "ref_mark"        # scenes.data: old rows may carry "eye_plus" (written until V5, 13/10) — read by nothing any more


def mark_off_face() -> bool:
    try:
        from . import features
        return features.on("ref_mark_off_face")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def _scene_data(conn, scene_ids) -> List[Dict]:
    out = []
    for sid in scene_ids or []:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        out.append(json.loads(row["data"] or "{}") if row else {})
    return out


def mark_style(conn, scene_ids) -> str:
    """Lỗi hệ thống 4 (#27 13/10: Seedance 2.5 drew the red plus of the marked pictures onto Kelly's face, shots 8–9, 18). Flag
    ref_mark_off_face off: "eye_plus" (as before). On: always "corner_plus" (banner + plus in the corner, off every face).
    V5 (rà gốc video #27 13/10, G9): the old step back to the eye mark after a "real person" refusal put the plus on the START FRAME's
    face again (job 852/853/896) — gone: a refusal now goes down the route ladder (step_mark_back False); an old row still carrying
    ref_mark = "eye_plus" is not followed any more."""
    if not mark_off_face():
        return "eye_plus"
    return "corner_plus"


SENT_KEY = "ref_mark_sent"   # scenes.data: how the last reference-only send carried its pictures — a mark style, or "hosted"


def note_sent(conn, scene_ids, how: str) -> None:
    """Remember how the pictures of this send went (flag ref_mark_off_face only): "hosted" = Subject Library, unmarked — a
    "real person" refusal then cannot be answered by changing the mark (nothing was marked)."""
    if not mark_off_face():
        return
    for sid in scene_ids or []:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()
        if row is None:
            continue
        data = json.loads(row["data"] or "{}")
        if data.get(SENT_KEY) != how:
            data[SENT_KEY] = how
            conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), sid))
    conn.commit()


def step_mark_back(conn, scene_ids) -> bool:
    """After a "real person" refusal: is there a mark step to take before the route ladder? Always False now (V5, rà gốc 13/10):
    flag ref_mark_off_face off — there never was one; on — the only step was back to the EYE mark, which drew the plus onto the
    start frame's face (G9). The caller goes down the route ladder (group → single → Kling), which changes the input (luật 6)."""
    return False


def mark_ban_sentence(names: List[str]) -> str:
    """The sentence that forbids drawing the reference marks on the people (flag ref_mark_off_face; #27 shots 8–9, 18)."""
    who = ", ".join(ascii_name(n) for n in names) if names else "anyone"
    return (f"Never draw a plus sign, cross, crosshair or any red mark on {who}'s face, head, body or clothes, at any moment — the red "
            "plus and the white banner on the reference pictures are only labels.")


def identity_pictures(conn, project_id: int, rows: List[Dict], room: int) -> List[tuple]:
    """(name, path) of one reference picture per character of the shots, in order of appearance, at most `room`."""
    from . import assets
    names: List[str] = []
    for r in rows:
        for n in r["data"].get("characters") or []:
            if str(n) not in names:
                names.append(str(n))
    links = assets.link_characters(conn, project_id, names)
    from . import character_forms        # rà 17/10: a person in a form in EVERY shot of the clip → no OUTFIT picture ("dress exactly in
    formed = {w for w, f in character_forms.for_rows(conn, project_id, rows).items() if f.get("all")}   # these clothes" fought the form)
    out = []
    for n in names:
        link = links.get(n) or {}
        ref = link.get("ref")
        if ref and os.path.exists(ref.get("path", "")):
            # rà video #27 (12/10): KAPELLA's chosen 21/2.png (220×394) went and ClipAI refused the whole job at send, while 3.png
            # (550×800) of the same library entry passes — the chosen pictures first, then the entry's others in reference order
            more = assets.best_references(link, len(link.get("images") or []), name=n) if link.get("images") else []
            pool = [i["path"] for i in list(link.get("refs") or [ref]) + more if i.get("path") and os.path.exists(i["path"])]
            out.append((n, _rule_ok_picture(conn, project_id, n, list(dict.fromkeys(pool)) or [ref["path"]])))
        outfit = assets.outfit_images(conn, project_id, n) if n.strip().upper() not in formed else []
        if outfit:     # 07/10 Khủng Long Đỏ: MAXIM KL / KELLY KL danced in their everyday clothes — only the library face picture
            out.append((n + OUTFIT_TAG, _rule_ok_picture(conn, project_id, n + OUTFIT_TAG, [o["path"] for o in outfit])))   # (everyday
            # look) went, the costume picture never did
    _say_speakers_without_picture(conn, project_id, rows, {n for n, _ in out})
    out += form_and_object_pictures(conn, project_id, rows)
    # over the room (rà 17/10): an OUTFIT picture goes first, then (19/10) an object, then a form — a person keeps their face picture
    for tag in (OUTFIT_TAG, OBJECT_TAG, FORM_TAG):
        while len(out) > max(room, 0) and any(n.endswith(tag) for n, _ in out):
            out.pop(max(i for i, (n, _) in enumerate(out) if n.endswith(tag)))
    return out[:max(room, 0)]


def form_and_object_pictures(conn, project_id: int, rows: List[Dict]) -> List[tuple]:
    """19/10 (#31 G27): the FORM pictures (a person in a form, e.g. Kelly's ghost form #427) and the library OBJECT pictures (SKORP,
    the Gloowall with its skin, the floating figure) the shots name — the same pictures the image package of each shot sends
    (assets.scene_references, roles character_form / object), once each, in film order. Before, a video clip sent only one face
    picture per person: shot 28 came out in Kelly's yellow jacket, the glue wall of shots 17/35/36 was drawn in another design."""
    from . import assets, character_forms
    out, seen = [], set()
    # forms: by the SHOT's character name (rà G27: the library label differs for an alias, e.g. "Kelly KL" → Kho "KELLY", and the
    # form picture must not compete with faces for scene_references' slots) — the lint and says() look the form up by that name
    for who, f in character_forms.for_rows(conn, project_id, rows).items():
        path = assets.resolve((f.get("image") or {}).get("path"))
        if path and os.path.exists(path):
            out.append((who + FORM_TAG, path))
    for r in rows:
        try:
            refs = assets.scene_references(conn, project_id, r.get("data") or {})
        except Exception:  # noqa: BLE001 - a shot whose references cannot be read keeps the old behaviour (the caller's lint says it)
            continue
        for ref in refs:
            path = ref.get("path")
            if ref.get("role") != "object" or not path or not os.path.exists(path):
                continue
            key = str(ref.get("label") or "").strip().upper()
            if key in seen:
                continue
            seen.add(key)
            out.append((str(ref.get("label") or "").strip() + OBJECT_TAG, path))
    return out


def _rule_ok_picture(conn, project_id: int, who: str, paths: List[str]) -> str:
    """The first of `paths` ClipAI takes as a reference picture (sides ≥ 300 px, width/height 0.4–2.5 — clipai.reference_image_problems;
    an unreadable file is not judged here, the send says it). paths[0] when it passes; another one → said; none → paths[0] kept and
    said (the pre-gen check video_pregen holds the job with the reason instead of a refused send)."""
    from .adapters import clipai
    from .assets import _shape

    def problems(path):
        size = _shape(path)
        return clipai.reference_image_problems("seedance", [size]) if size else []
    first = problems(paths[0])
    if not first:
        return paths[0]
    pick = next((p for p in paths[1:] if not problems(p)), None)
    why = "; ".join(first).replace("ảnh 1 ", "")
    if pick is None and rule_early_on():
        padded = pad_to_rule(paths[0], conn)  # V13 (#27 s17 job 798: 488×1280, the library had nothing else) — padded, not refused
        if padded and not problems(padded):
            _say_once(conn, project_id, "identity_picture_padded",
                      f"Ảnh nhận diện {who}: {os.path.basename(paths[0])} không đạt luật ClipAI ({why}) và mục Kho không có ảnh nào đạt — "
                      f"gửi bản đệm nền trơn {os.path.basename(padded)} (0 USD, hình giữ nguyên). Muốn ảnh tốt hơn: thêm vào Kho ảnh "
                      "cạnh ≥ 300 px, tỉ lệ rộng/cao 0,4–2,5.")
            return padded
    if pick:
        msg = (f"Ảnh nhận diện {who}: {os.path.basename(paths[0])} không đạt luật ClipAI ({why}) — gửi {os.path.basename(pick)} cùng mục "
               "Kho. Muốn ảnh khác: Bước 1 → Character Bible chọn ảnh cạnh ≥ 300 px, tỉ lệ rộng/cao 0,4–2,5.")
    else:
        msg = (f"Ảnh nhận diện {who}: {os.path.basename(paths[0])} không đạt luật ClipAI ({why}) và mục Kho không có ảnh nào đạt — clip "
               "bị giữ ở lớp kiểm trước gen / ClipAI từ chối. Cách xử lý: thêm vào Kho ảnh cạnh ≥ 300 px, tỉ lệ rộng/cao 0,4–2,5.")
    _say_once(conn, project_id, "identity_picture_rule", msg)
    return pick or paths[0]


# ---- V13 (rà gốc video #27 13/10, G13): a reference picture against ClipAI's size rule is caught BEFORE the send ------------------
# (job 798: "ảnh 4 (488×1280) tỉ lệ 0.38 — cần 0.4–2.5" found only when sending). Flag ref_rule_early: (1) a picture with no passing
# alternative is padded on a plain background (and enlarged to the least side) instead of refused; (2) what still breaks the rule is a
# ĐỎ of the prompt formula (prompt_formula.red_issues → queue / price / autopilot / send), not a refused paid send.
PAD_DIR: Optional[str] = None     # where padded copies go (None: <data folder in use>/ref_padded — never the Kho folder, the library
                                  # scans it; rà S2 13/10 mục 8: the running data folder, not the source code's place)
PAD_RATIO = (0.4, 2.5)
PAD_MIN_SIDE = 300


def rule_early_on() -> bool:
    try:
        from . import features
        return features.on("ref_rule_early")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def pad_dir(conn=None) -> str:
    """Where padded copies go: PAD_DIR; else next to the database file in use (data/manifest.sqlite → data/ref_padded); else beside
    the projects folder (PIPELINE_DATA, default data/projects → data/ref_padded)."""
    if PAD_DIR:
        return PAD_DIR
    try:
        db = next((r[2] for r in conn.execute("PRAGMA database_list") if r[1] == "main"), "") if conn is not None else ""
    except Exception:  # noqa: BLE001 - a closed / odd connection: the projects folder decides
        db = ""
    if db:
        return os.path.join(os.path.dirname(os.path.abspath(db)), "ref_padded")
    projects = os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")
    return os.path.join(os.path.dirname(os.path.abspath(projects)), "ref_padded")


def pad_to_rule(path: str, conn=None) -> Optional[str]:
    """A copy of the picture padded with its own edge colour to width/height within PAD_RATIO and enlarged (LANCZOS) so its short side
    is ≥ PAD_MIN_SIDE; made again only when the source is newer. None when it cannot be read."""
    try:
        from PIL import Image
        import hashlib
        out_dir = pad_dir(conn)
        os.makedirs(out_dir, exist_ok=True)
        key = hashlib.sha1(os.path.abspath(path).lower().encode("utf-8")).hexdigest()[:10]
        out = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(path))[0]}_{key}_pad.png")
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
            return out
        im = Image.open(path).convert("RGB")
        w, h = im.size
        lo, hi = PAD_RATIO
        nw, nh = w, h
        if w / h < lo:
            nw = int(math.ceil(h * lo)) + 1
        elif w / h > hi:
            nh = int(math.ceil(w / hi)) + 1
        bg = im.getpixel((0, 0))
        canvas = Image.new("RGB", (nw, nh), bg)
        canvas.paste(im, ((nw - w) // 2, (nh - h) // 2))
        if min(canvas.size) < PAD_MIN_SIDE:
            k = PAD_MIN_SIDE / min(canvas.size)
            canvas = canvas.resize((int(math.ceil(canvas.size[0] * k)), int(math.ceil(canvas.size[1] * k))), Image.LANCZOS)
        canvas.save(out)
        return out
    except Exception:  # noqa: BLE001 - unreadable picture: not padded, the rule check says it
        return None


def reference_rule_issues(conn, project_id: int, rows: List[Dict]) -> List[str]:
    """V13: the identity pictures this clip would send that still break ClipAI's rule (after the alternative / pad) — Vietnamese
    lines for a ĐỎ before queueing. [] with flag ref_rule_early off."""
    if not rule_early_on():
        return []
    from .adapters import clipai
    from .assets import _shape
    from .memo import cached
    names = tuple(dict.fromkeys(str(n) for r in rows for n in (r["data"].get("characters") or [])))
    if not names:                     # C1 15/10 (cờ bật mặc định): shot không nhân vật → không ảnh nhận diện, không truy vấn
        return []
    out = []
    # một lượt vẽ Dashboard (memo.per_rerun): cùng bộ nhân vật của nhiều shot → tra Kho một lần (readiness cả dự án không N+1)
    from . import character_forms        # rà 17/10 vòng 2: the pictures depend on who is in a form all clip (no OUTFIT) — in the key
    formed = frozenset(w for w, f in character_forms.for_rows(conn, project_id, rows).items() if f.get("all"))
    pictures = cached(conn, ("ref_rule_pictures", project_id, names, formed),
                      lambda: identity_pictures(conn, project_id, rows, MAX_PICTURES))
    for name, path in pictures:
        size = _shape(path) if path and os.path.exists(path) else None
        bad = clipai.reference_image_problems("seedance", [size]) if size else []
        if bad:
            out.append(f"ảnh nhận diện {ascii_name(name)} ({os.path.basename(path)}) sai luật ClipAI: {'; '.join(bad).replace('ảnh 1 ', '')}"
                       " — đổi ảnh Kho (cạnh ≥ 300 px, tỉ lệ rộng/cao 0,4–2,5) trước khi gửi")
    return out


def _say_once(conn, project_id: int, code: str, msg: str) -> None:
    """A warn diag said once per 10 minutes (identity_pictures runs on every runner tick)."""
    from . import diag
    try:
        seen = conn.execute("SELECT 1 FROM diag_events WHERE code=? AND COALESCE(project_id,0)=? AND message=?"
                            " AND (julianday('now') - julianday(last_at)) * 1440 < 10 LIMIT 1",
                            (code, project_id or 0, diag.redact(msg)[:400])).fetchone()
    except Exception:  # noqa: BLE001 - no diag table: record() keeps it (_keep_lost)
        seen = None
    if not seen:
        diag.record(conn, "video", "warn", msg, code, project_id)


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


def place_pictures(data_dir: str, project_id: int, rows: List[Dict], starts: Optional[Dict[int, str]] = None) -> List[Dict]:
    """Local renders only, appended after identities; a shared file keeps one Image number.
    starts: {scene_id: approved start frame} — with flag plate_view_sentence, each render is measured against the start frames of
    its shots (`plate_view`) and carries "view": "same" | "other" | None (None = not measured: no start frame / no OpenCV / too few
    points — `prompt` then writes the careful sentence, as for "other"). Without `starts` nothing is measured (None)."""
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
        if plate_view_on() and starts is not None:
            view = plate_view(ref["path"], starts.get(row["id"]))["view"]
            prev = seen[key].get("view", "same")
            seen[key]["view"] = view if prev == "same" else prev          # one shot of another camera / unmeasured → not "same"
    return out


# ---- V1 (rà gốc video #27 13/10, G6): the 3D place render must not win over the approved start frame ------------------------------
# s17 job 858/912: the render was a camera AT GROUND LEVEL facing the tower foot, the approved start frame a HIGH camera behind Kelly.
# The prompt said the render "decides architecture over conflicting text or storyboard details" → Seedance reconciled the two by
# pulling the camera back and drawing a clock face. With the flag: the start frame decides framing, camera distance / angle and what
# is in view; the render is a reference for the architecture's details only — and when it is another camera, it is said so.
PLATE_SAME_SCALE = 1.30       # background scale outside [1/1.30, 1.30] → another camera distance (framing_guard.ZOOM_IN)
PLATE_SAME_CORNER = 0.15      # a picture corner moved more than 15 % of the frame → another framing / angle
PLATE_SAME_INLIERS = 0.05     # fewer than 5 % of the render's points match the start frame → another view (framing_guard.F0_INLIERS)


def plate_view_on() -> bool:
    try:
        from . import features
        return features.on("plate_view_sentence")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def plate_view(plate_path: Optional[str], start_path: Optional[str]) -> Dict:
    """{"view": "same" | "other" | None, "why"} — the render against the approved start frame (framing_guard.similarity, 0 USD).
    None = not measurable (said in "why", the caller writes the careful sentence — never silently 'same')."""
    if not plate_path or not start_path or not os.path.isfile(plate_path) or not os.path.isfile(start_path):
        return {"view": None, "why": "thiếu render hoặc ảnh khung đầu — không so được góc máy"}
    try:
        from . import framing_guard
        a, b = framing_guard._read(plate_path), framing_guard._read(start_path)
        if a is None or b is None:
            return {"view": None, "why": "không đọc được render / ảnh khung đầu"}
        sim = framing_guard.similarity(a, b)
    except Exception as e:  # noqa: BLE001 - no OpenCV: not measured, said
        return {"view": None, "why": f"không đo được ({type(e).__name__})"}
    if sim.get("scale") is None:
        return {"view": "other", "why": sim.get("note") or "không khớp điểm nào"}
    s, corner, share = sim["scale"], sim.get("corner") or 0.0, sim.get("inlier_share") or 0.0
    same = (1 / PLATE_SAME_SCALE <= s <= PLATE_SAME_SCALE and corner <= PLATE_SAME_CORNER and share >= PLATE_SAME_INLIERS)
    return {"view": "same" if same else "other",
            "why": f"tỉ lệ {s:.2f}, lệch góc {corner:.2f}, điểm khớp {share:.0%}"}


def _place_sentence(number: int, targets: str, view: Optional[str]) -> str:
    """The PLACE render sentence (flag plate_view_sentence): never 'the render decides'; a render of another / unmeasured camera is
    said to be one, so the model does not move the camera to match it."""
    head = f" Image {number} is the 3D PLACE render for {targets}"
    rule = (" The storyboard frame decides framing, camera distance, angle and what is in view — never pull back or re-frame to match "
            "this render; never move, add or remove a building.")
    if view == "same":
        return head + ": buildings, tower, walls and ground keep exactly these shapes, also where camera movement reveals more." + rule
    return (head + ", from ANOTHER camera position: only a reference for the shape and material of buildings already in view or "
            "revealed by camera movement." + rule)


def prompt(parts: List[tuple], identities: List[tuple], look: str = "", clip_seconds: Optional[float] = None,
           model: Optional[str] = None, places: Optional[List[Dict]] = None, scales: Optional[List[str]] = None,
           reserve: int = 0, objects: Optional[List[tuple]] = None, forms: Optional[Dict[str, Dict]] = None) -> str:
    """parts: [(motion prompt, seconds)] in film order. The wording of the tested P2m prompt (cut rule, which picture is which shot /
    whose identity, the shots), assembled in the motion formula's order (F1-C, docs/CONG_THUC_PROMPT_F0 mục 3.2 + 4): start point
    (the cut rule and each shot's storyboard frame) → each shot's action (what changes, first) → sentences shared by several shots, once
    → what stays still → identity lock (each picture's role, the costume once for the whole group) → the place renders → the rules
    (reference marks). clip_seconds: the length really asked for (Seedance makes ≥ 4 s) — the shots' marks are stretched to it, so the
    last shot does not end before the clip does (review 2026-09-27). model: time marks only for a model that reads them
    (`reads_seconds`); the others get "Shot N:" alone (S4.8, 2026-09-29). objects: [(Kho name, path)] of DEPLOYED skill-object
    pictures sent after the place renders (V4; the caller sends them in that order — None: nothing, as before)."""
    from . import features               # S4.7: with the Subject Library the pictures may go unmarked — a sentence true either way
    from . import prompt_template as pt
    n = len(parts)
    total = sum(float(s) for _, s in parts) or 1.0
    if clip_seconds and clip_seconds > total:
        parts = [(m, float(s) * clip_seconds / total) for m, s in parts]
    # 1. start point
    start = ((f"One clip with {n} shots cut in this order, hard cuts between shots. " if n > 1 else "One single shot, no cuts. ")
             + (look.strip() + " " if look.strip() else "")
             + " ".join(f"Image {i} is the storyboard frame of Shot {i}: Shot {i} starts with exactly this composition, framing and "
                        f"these character positions." for i in range(1, n + 1)))
    # 2. the shots — a sentence repeated word for word in several shots (costume, background) is said once, after them (#22 lỗi 5)
    raw = [str(m).replace(START_SENTENCE, "").strip() for m, _ in parts]   # 12/10: the start block above says it for every shot
    texts, shared = pt.shared_sentences(raw) if n > 1 else (raw, [])
    marks = whole_marks([float(sec) for _, sec in parts]) if reads_seconds(model) else [None] * n
    shots = [f"Shot {i}" + (f" ({mk[0]}–{mk[1]} s)" if mk else "") + f": {t.strip().rstrip('.')}."
             for i, (t, mk) in enumerate(zip(texts, marks), 1)]
    shared_lines = [f"{pt.shots_label(nums, n)}: {sent}" for sent, nums in shared]
    # 3. what stays still
    changes = any(f.get("shots") and not f.get("all") for f in (forms or {}).values())   # rà 17/10: a form in only some shots
    still = ((("Same place, same light, same characters throughout. " if changes else
               "Same place, same light, same characters and outfits throughout. ") if n > 1 else "")
             + "The buildings and the landmark behind the people keep exactly the shape they have in the storyboard frames.")  # 28/09
    # 4. identity lock
    dressed = {name[:-len(OUTFIT_TAG)] for name, _ in identities if name.endswith(OUTFIT_TAG)}
    strip = features.on("outfit_strip_model")   # KLD-7 (08/10): Kelly KL took the silver hair of the model wearing the OUTFIT

    def says(name: str) -> str:
        if name.endswith(FORM_TAG):      # 19/10 (#31 G27): the picture of the form itself, next to the person's face picture
            who = name[:-len(FORM_TAG)]
            form = (forms or {}).get(who.strip().upper()) or {}
            nums = form.get("shots")
            where = (", ".join(f"Shot {i}" for i in nums) if nums and n > 1 and len(nums) < n else "this clip")
            return (f"{who}'s {form.get('form') or 'form'} in {where}: draw {who}'s whole body, clothes and surface exactly as this "
                    f"picture shows, with the face and hair from {who}'s identity picture — never {who}'s everyday outfit")
        if name.endswith(OBJECT_TAG):
            what = name[:-len(OBJECT_TAG)]
            return (f"the object {what}: whenever it appears, draw it exactly as this picture shows — same shape, design, colours, "
                    "material and skin; never another design — not the framing")
        if name.endswith(OUTFIT_TAG):
            who = name[:-len(OUTFIT_TAG)]
            return (f"the OUTFIT {who} wears in this video: dress {who} exactly in these clothes, cap, shoes and accessories "
                    + (f"— ignore the hair, face and body of any person modelling these clothes (those come only from {who}'s "
                       "identity picture); wear each accessory exactly as the picture shows it, for the whole clip " if strip else "")
                    + "— not the framing")
        form = (forms or {}).get(name.strip().upper())
        if form:                         # G2 17/10 (#31): in a form the clip's shots name (core/character_forms) — never the outfit
            nums = form.get("shots")     # rà 17/10: per shot (character_forms.for_rows) — #31 shot 30 leaves the ghost form
            if nums and not form.get("all") and n > 1:
                where = ", ".join(f"Shot {i}" for i in nums)
                return (f"{name}: identity only (face, hair, body build); in {where} {name} is in the {form['form']} — NOT the clothes "
                        f"or their colours there, as the storyboard frame shows; in the other shots {name} looks as their storyboard "
                        "frames show")
            where = (", ".join(f"Shot {i}" for i in nums) if nums and n > 1 and len(nums) < n else "this clip")
            return (f"{name}: identity only (face, hair, body build) — NOT the clothes or their colours: in {where} {name} is in "
                    f"the {form['form']}, as the storyboard frame shows")
        if name in dressed:
            return f"{name}: identity only (face, hair, body build) — NOT the clothes, which come only from the OUTFIT picture"
        return f"{name}: identity only (face, hair, outfit) — not the framing"
    identity = " ".join(f"Image {n + k} is {says(name)}." for k, (name, _) in enumerate(identities, 1))
    if dressed:                          # F1-C: one source for the costume (#22: GREEN ↔ blue dinosaur print between shots)
        identity += " Each costume follows its OUTFIT picture; any other colour word for these garments is wrong."
    # 5. the place renders
    place_text = ""
    for k, place in enumerate(places or [], 1):
        targets = ", ".join(f"Shot {i}" for i in place["shots"])
        if plate_view_on():              # V1 (rà gốc 13/10): the start frame decides framing + camera distance, not the render
            place_text += _place_sentence(n + len(identities) + k, targets, place.get("view"))
            continue
        place_text += (f" Image {n + len(identities) + k} is the PLACE render for {targets}: keep the buildings, tower, walls and ground "
                       "exactly as in this image throughout those shots, including during camera movement. "
                       "It decides architecture over conflicting text or storyboard details; people, outfits and starting framing "
                       "still follow their own references. Never move, add or remove a building.")
    for sent in scales or []:            # F5-A: measured sizes of the library objects (place_refs.object_scale_sentence, short)
        place_text += " " + sent.strip()
    if objects:                          # V4: the DEPLOYED skill-object pictures (skill_objects.deployed_pictures), after the renders
        from . import skill_objects
        first = n + len(identities) + len(places or []) + 1
        place_text += "".join(" " + skill_objects.deployed_line(first + k, ascii_name(name),
                                                                   skill_objects._MANNEQUIN_PATHS.get(skill_objects._norm_path(path), False))
                             for k, (name, path) in enumerate(objects))
    # 6. rules
    rules = ("Any white banner or red mark on a reference picture is an annotation, never part of the video."
             if features.on("seedance_subjects") else
             "The white banner and red marks on the reference pictures are annotations, never part of the video.")
    if mark_off_face():                  # lỗi hệ thống 4 (#27 13/10): the plus was drawn onto Kelly's face — said by name, always
        rules += " " + mark_ban_sentence(list(dict.fromkeys(base_name(nm) for nm, _ in identities
                                                            if not nm.endswith(OBJECT_TAG))))
    blocks = [start.strip(), "\n".join(shots), "\n".join(shared_lines), still, identity.strip(), place_text.strip(), rules]
    text = "\n".join(b for b in blocks if b)
    # 08/10 (#24): a character named in Vietnamese ("YÊU NỮ TÀ LINH DẠNG 1") put accented letters into "Image N is …" and the shot
    # lines — the whole send was blocked as "prompt còn chữ tiếng Việt" though every Director field was translated. The names go
    # without accents (the same spelling in the mapping and the shots, so picture and name still match); spoken lines are untouched.
    for name in sorted({base_name(nm) for nm, _ in identities}, key=len, reverse=True):
        if ascii_name(name) == name:
            continue
        for form in dict.fromkeys((name, name.upper(), name.title(), name.capitalize(), name.lower())):   # "Yêu nữ tà linh…" in a motion line
            text = _outside_dialogue(text, lambda s, a=form, b=ascii_name(form): s.replace(a, b))
    if scales and len(text) + max(int(reserve or 0), 0) > prompt_limit(model):
        # F5-A: the object sizes are the first thing to go when the prompt (+ `reserve`, e.g. the dialogue block added after) would pass
        # the model's limit — lint_group would block the whole send otherwise
        return prompt(parts, identities, look, clip_seconds, model, places, None, reserve, objects, forms)
    return text


def prompt_limit(model: Optional[str]) -> int:
    """F1-C: the model's prompt limit in characters — data/provider_rules.json `prompt_limit` (core.video_rules.rule), else the
    adapter's table (clipai.PROMPT_LIMITS), else 5 000 for a model that reads seconds (2.5) / PROMPT_MAX."""
    canonical, table = str(model or "").strip(), {}
    try:
        from .adapters.clipai import MODEL_ALIASES, PROMPT_LIMITS
        canonical, table = MODEL_ALIASES.get(canonical.lower(), canonical), PROMPT_LIMITS
    except Exception:  # noqa: BLE001 - no adapter table: the fallbacks below
        pass
    from . import video_rules
    limit = video_rules.rule(canonical).get("prompt_limit") if canonical else None
    if isinstance(limit, (int, float)) and limit > 0:
        return int(limit)
    return int(table.get(canonical) or (5000 if reads_seconds(canonical or model) else PROMPT_MAX))


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


REFINE_WINDOW = 1.5          # 08/10 #24 S08–S09: scdet saw no cut, the plan said 3.024 s, the real hard cut was at 3.875 s (0.85 s later)
INNER_CUT_EDGE = 1.2         # a cut this close to a part's start / end (clip_measure) = the group was cut at the wrong place: cut again


def _snap(t: float, fps: float) -> float:
    """A time on the frame grid (a cut between two frames), so a part never keeps one frame of its neighbour."""
    return round(round(t * fps) / fps, 3)


def refine_cuts(path: str, planned: List[float], length: Optional[float] = None) -> Dict:
    """08/10 (#24 S08–S09): scdet (threshold 12) missed the cut between two shots of one palette, the group was cut at the planned
    seconds and 0.83 s of shot 8 opened shot 9's file. Around each planned cut (±REFINE_WINDOW s) the frame pair that changes most is
    looked for with the measure the clip QC uses (clip_measure: colour-histogram correlation + optical flow); it is taken as the cut
    only when it is clear (a hard cut: correlation < CUT_CORR, or a motion jump with a colour change < SPIKE_CUT_CORR).
    {"cuts", "found": [s | None]}; no OpenCV / unreadable clip → the planned cuts, nothing found."""
    found: List[Optional[float]] = [None] * len(planned)
    try:
        from . import clip_measure as cm
        series, fps, same = cm.motion_series(path)
    except Exception:  # noqa: BLE001 - no OpenCV / unreadable clip: the plan stays
        return {"cuts": list(planned), "found": found}
    fps = fps or 24.0
    total = length or (len(series) + 1) / fps
    cuts: List[float] = []
    prev = 0.0
    for k, p in enumerate(planned):
        lo, hi = max(p - REFINE_WINDOW, prev + 0.5, 0.3), min(p + REFINE_WINDOW, total - 0.3)
        idx = [i for i in range(len(same)) if lo <= (i + 1) / fps <= hi]
        if idx:
            best = min(idx, key=lambda i: same[i])
            rest = sorted(series[i] for i in idx if abs(i - best) > 2) or [0.0]
            local = rest[len(rest) // 2]
            jump = series[best] > cm.SPIKE * max(local, 0.25) and series[best] > 1.5
            if same[best] < cm.CUT_CORR or (same[best] < cm.SPIKE_CUT_CORR and jump):
                found[k] = round((best + 1) / fps, 3)
        cut = found[k] if found[k] is not None else p
        cuts.append(cut)
        prev = cut
    return {"cuts": cuts, "found": found}


def _cut_parts(whole: str, bounds: List[float], dest_paths: List[str], ffmpeg: str) -> List[str]:
    from .ffmpeg_studio import has_audio
    from .shots import _encode
    audio = ["-c:a", "aac", "-b:a", "256k"] if has_audio(whole) else ["-an"]
    out = []
    for (start, end), dest in zip(zip(bounds, bounds[1:]), dest_paths):
        proc = subprocess.run([ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", whole, "-t", f"{max(end - start, 0.2):.3f}", *_encode(), *audio,
                               dest], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0 or not os.path.exists(dest):
            shutil.copyfile(whole, dest)
        out.append(dest)
    return out


def inner_cut_moves(bounds: List[float], parts: List[str], edge: float = INNER_CUT_EDGE) -> Dict[int, float]:
    """08/10: each part measured as the clip QC will measure it (clip_measure.jerks); a cut inside a part within `edge` s of its start /
    end means the neighbour's frames are in it → {bound index: new time in the group clip}. An unmeasurable part moves nothing."""
    from . import clip_measure as cm
    moves: Dict[int, float] = {}
    n = len(parts)
    for i, part in enumerate(parts):
        try:
            series, fps, same = cm.motion_series(part)
            cuts = cm.jerks(part, series, fps, same).get("cuts") or []
        except Exception:  # noqa: BLE001 - no OpenCV / unreadable part: nothing to move
            continue
        fps = fps or 24.0
        have = bounds[i + 1] - bounds[i]
        for t in cuts:
            at = _snap(bounds[i] + _snap(t, fps), fps)
            if i > 0 and t <= edge and bounds[i - 1] + 0.3 < at < bounds[i + 1] - 0.3:
                moves[i] = at                    # the part opens with the previous shot's end
            elif i < n - 1 and have - t <= edge and bounds[i] + 0.3 < at < bounds[i + 2] - 0.3:
                moves[i + 1] = at                # the part ends with the next shot's start
    return moves


def _sidecar(whole: str) -> str:
    return os.path.splitext(whole)[0] + ".cuts.json"


def saved_cuts(whole: str) -> Optional[Dict]:
    """What split / recut wrote next to a group clip (<name>_group.cuts.json), or None."""
    try:
        with open(_sidecar(whole), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save_cuts(whole: str, res: Dict, length: Optional[float]) -> None:
    try:
        with open(_sidecar(whole), "w", encoding="utf-8") as f:
            json.dump({**{k: res.get(k) for k in ("cuts", "by", "planned", "found", "moved")}, "length": length}, f, ensure_ascii=False)
    except OSError:
        pass


def split(path: str, group: List[Dict], dest_paths: List[str], ffmpeg: Optional[str] = None) -> Dict:
    """Cut a group clip into one file per shot at its detected cuts. When scdet does not show them all, the cuts are looked for again
    around the planned seconds (refine_cuts); a cut still not found stays at the planned seconds scaled to the clip. Then every part is
    measured (inner_cut_moves): a cut close to a part's edge moves that bound and the group is cut again — 0 USD, before the clip QC
    (08/10 #24: QC rejected S09 and paid a new take for frames that only had to be cut elsewhere). The whole clip is kept as
    <name>_group.mp4 and the cuts as <name>_group.cuts.json.
    {"paths", "cuts", "by": "detected"|"refined"|"plan", "planned", "found", "moved": [[old, new], ...]}."""
    from .ffmpeg_studio import find_ffmpeg, probe_duration
    ffmpeg = ffmpeg or find_ffmpeg()
    whole = os.path.splitext(path)[0] + "_group.mp4"
    shutil.copyfile(path, whole)
    length = probe_duration(whole)
    cuts = cut_points(whole, len(group), ffmpeg)
    by, plan_cuts, found = "detected", None, None
    if cuts is None:
        planned = [floored(r["data"], r.get("duration_s") or r["data"].get("duration_s") or 1) for r in group]
        scale = (length or sum(planned)) / sum(planned)
        plan_cuts, t = [], 0.0
        for sec in planned[:-1]:
            t += sec * scale
            plan_cuts.append(round(t, 3))
        ref = refine_cuts(whole, plan_cuts, length)
        cuts, found = ref["cuts"], ref["found"]
        by = "refined" if any(x is not None for x in found) else "plan"
    bounds = [0.0] + list(cuts) + [length or (cuts[-1] + 2 if cuts else 4)]
    out = _cut_parts(whole, bounds, dest_paths, ffmpeg)
    moved: List[List[float]] = []
    for _ in range(2):                                   # a moved bound is measured once more
        moves = inner_cut_moves(bounds, out) if len(out) > 1 else {}
        if not moves:
            break
        for k, at in sorted(moves.items()):
            moved.append([bounds[k], at])
            bounds[k] = at
        out = _cut_parts(whole, bounds, dest_paths, ffmpeg)
    res = {"paths": out, "cuts": bounds[1:-1], "by": by, "planned": plan_cuts, "found": found, "moved": moved, "end": bounds[-1]}
    _save_cuts(whole, res, length)
    return res


def split_notes(res: Dict, n: int) -> List[tuple]:
    """The diag lines (code, severity, message) of one split: refined cuts, cuts left at the plan, bounds moved after measuring."""
    notes = []
    planned, found = res.get("planned") or [], res.get("found") or []
    if res.get("by") == "refined":
        got = [f"{f:.3f} s (dự kiến {p:.3f} s)" for p, f in zip(planned, found) if f is not None]
        notes.append(("group_cut_refined", "info", f"clip nhóm {n} shot: scdet không dò đủ {n - 1} điểm cắt — dò lại quanh mốc dự kiến "
                      f"(±{REFINE_WINDOW:g} s, so màu từng khung) và cắt theo điểm dò được ở {', '.join(got)}"))
    missing = [p for p, f in zip(planned, found) if f is None] if res.get("by") in ("refined", "plan") else []
    if missing:
        notes.append(("group_cut_by_plan", "warn", f"clip nhóm {n} shot: {len(missing)} điểm cắt không dò được kể cả khi dò lại — cắt theo "
                      f"số giây dự kiến ({missing}); xem lại và chỉnh chỗ cắt ở Bước 4 (✂ Điểm cắt clip nhóm, 0 USD)"))
    for old, new in res.get("moved") or []:
        notes.append(("group_cut_moved", "info", f"đo từng phần sau khi tách thấy điểm cắt cảnh sát mép phần một shot → tách lại cả nhóm: "
                      f"điểm cắt {old:.3f} s → {new:.3f} s (0 USD, trước khi chấm QC)"))
    return notes


def group_members(conn, leader_id: int) -> List:
    """The jobs of one group clip in shot order: the leader, then the latest follower job of each other shot (jobs.group_leader)."""
    lead = conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.id=?", (leader_id,)).fetchone()
    if lead is None:
        return []
    rows = conn.execute("SELECT j.*, s.idx FROM jobs j JOIN scenes s ON s.id=j.scene_id WHERE j.group_leader=? AND j.type='video_gen'"
                        " AND j.id!=? ORDER BY s.idx, j.id", (leader_id, leader_id)).fetchall()
    latest: Dict[int, object] = {}
    for r in rows:
        latest[r["scene_id"]] = r
    return [lead] + sorted(latest.values(), key=lambda r: r["idx"])


def group_whole(job) -> Optional[str]:
    """The whole group clip kept next to the leader's file (<name>_group.mp4), when it exists."""
    rp = job["result_path"] if job is not None else None
    if not rp:
        return None
    whole = os.path.splitext(rp)[0] + "_group.mp4"
    return whole if os.path.exists(whole) else None


def recut(p, leader_id: int, cuts: List[float]) -> Dict:
    """Bước 4 (08/10): the person sets the cut seconds of a group clip; its shot files are cut again from <name>_group.mp4 — 0 USD,
    nothing is sent. A shot whose scene already has a later take with a file (or one running) is never overwritten (its part goes to
    <idx>_recut_unused.mp4, said in "skipped"). Job states are kept (an approved part stays approved — the person cut it on purpose);
    said in diag. {"paths", "cuts", "skipped"}."""
    from . import access, diag
    from .ffmpeg_studio import find_ffmpeg, probe_duration
    leader = p.job(leader_id)
    access.need_edit(p, leader["project_id"], "cắt lại clip nhóm")
    members = group_members(p.conn, leader_id)
    whole = group_whole(leader)
    if whole is None or len(members) < 2:
        raise ValueError("không có clip nhóm gốc (_group.mp4) hoặc nhóm chỉ có 1 shot")
    length = probe_duration(whole) or 0.0
    cuts = [round(float(c), 3) for c in cuts]
    if len(cuts) != len(members) - 1:
        raise ValueError(f"cần {len(members) - 1} điểm cắt cho {len(members)} shot, nhận {len(cuts)}")
    bounds = [0.0] + cuts + [length]
    if any(b - a < 0.3 for a, b in zip(bounds, bounds[1:])):
        raise ValueError(f"điểm cắt phải tăng dần, mỗi phần ≥ 0,3 s, trong 0–{length:.2f} s")
    dests, skipped = [], []
    for m in members:
        dest = m["result_path"] or os.path.join(os.path.dirname(leader["result_path"]), f"{m['idx']:02d}.mp4")
        later = p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='video_gen' AND id>? AND (result_path IS NOT NULL OR "
                               "state='running')", (m["scene_id"], m["id"])).fetchone()
        if later is not None:
            skipped.append(m["idx"])
            dest = os.path.splitext(dest)[0] + "_recut_unused.mp4"   # the newer take's file is never overwritten
        dests.append(dest)
    out = _cut_parts(whole, bounds, dests, find_ffmpeg())
    old = (saved_cuts(whole) or {}).get("cuts")
    _save_cuts(whole, {"cuts": cuts, "by": "user", "moved": [[a, b] for a, b in zip(old or [], cuts) if a != b]}, length)
    for k, (m, dest) in enumerate(zip(members, out)):
        if m["idx"] not in skipped and not m["result_path"] and os.path.exists(dest):
            p.conn.execute("UPDATE jobs SET result_path=? WHERE id=?", (dest, m["id"]))
        if m["idx"] not in skipped:                       # rà 12/10: the final upgraded from this task is cut where the person cut
            span = {"start": round(bounds[k], 3), "length": round(bounds[k + 1] - bounds[k], 3), "trim": None, "lone_ref": False,
                    "whole": round(length, 3) if length else None}
            try:
                p.conn.execute("UPDATE jobs SET clip_span=? WHERE id=?", (json.dumps(span), m["id"]))
            except Exception:  # noqa: BLE001 - an old database without the column: the final says it cannot find the span
                pass
    p.conn.commit()
    data_dir = type(p)._data_dir_of(leader) if hasattr(type(p), "_data_dir_of") else None
    if data_dir:                                          # S4.2: a take shot's voice follows where its part now starts
        from . import lipsync
        idx = lipsync.index(data_dir, leader["project_id"])
        for m, start in zip(members, bounds):
            rec = idx.get(str(m["scene_id"])) or {}
            if m["idx"] not in skipped and rec.get("method") == "take" and rec.get("state") == "done" and rec.get("job_id") == leader_id:
                lipsync.mark(data_dir, leader["project_id"], m["scene_id"],
                             shift=round(float(start) - float(rec.get("planned_start") or 0), 3))
    diag.record(p.conn, "video", "info", f"người dùng cắt lại clip nhóm {len(members)} shot ở {cuts} s (trước: {old}) — 0 USD, không gửi lại"
                + (f"; shot {skipped} đã có bản mới nên không ghi đè" if skipped else ""), "group_recut_by_user",
                leader["project_id"], leader["scene_id"], leader_id)
    return {"paths": out, "cuts": cuts, "skipped": skipped}


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


# KLD-32: the translation keeps a Vietnamese word of several meanings in square brackets ("a hat [mũ]", reported in
# motion_en_ambiguous + diag). The bracket is for the person, never for the paid video prompt: it is dropped here (1–2 words only).
KEPT_WORD = re.compile(r"\s*\[\s*[^\[\]\s]+(?:\s+[^\[\]\s]+)?\s*\]")


def strip_kept_words(value):
    """`value` (text, or a dict / list of texts) without the "[chữ Việt]" kept by the translation (KLD-32)."""
    if isinstance(value, str):
        return KEPT_WORD.sub("", value)
    if isinstance(value, dict):
        return {k: strip_kept_words(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_kept_words(v) for v in value]
    return value


def _en(data: Dict, key: str):
    """The English form of a Director field: `motion_en` (translated once, claude_tasks.translate_motion_fields) or the field itself."""
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    if en.get(key):
        from . import claude_tasks                    # lỗi 6 (cờ end_state_fresh): a translation of an edited field is not sent
        if claude_tasks.fresh_on() and key in claude_tasks.stale_en_keys(data):
            return data.get(key)
    return strip_kept_words(en.get(key)) if en.get(key) else data.get(key)


_GLOWING_EYES = re.compile(r"\bglow\w*[^.;]{0,20}\beyes?\b|\beyes?\b[^.;]{0,30}\bglow\w*|\b(?:red|burning|luminous) eyes\b"
                           r"|\bmắt\b[^.;]{0,20}(?:đỏ|phát sáng|rực)", re.IGNORECASE)


# F1 sửa #12: red eyes from crying are a person's eyes ("red eyes from crying", "teary red eyes", "mắt đỏ hoe") — such a clause is left out
_CRYING = re.compile(r"\b(?:cry\w*|cries|tears?|teary|tearful|weep\w*|sob\w*)\b|đỏ hoe|khóc|ngấn (?:lệ|nước)|rơm rớm", re.IGNORECASE)


def glowing_eyes_written(data: Dict) -> bool:
    """The Director wrote glowing / red eyes for someone in the shot (performance, action, image_prompt — English or Vietnamese).
    A clause about crying (red, teary eyes) does not count."""
    bits = []
    for src in (data, data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}):
        perf = src.get("performance") if isinstance(src.get("performance"), dict) else {}
        bits += [f"{k}: {v}" for k, v in perf.items() if isinstance(v, str)]
        bits += [str(src.get(k) or "") for k in ("action", "end_state", "image_prompt")]
    import unicodedata
    text = unicodedata.normalize("NFC", " | ".join(bits))
    kept = ", ".join(c for c in re.split(r"[,;.|\n]", text) if not _CRYING.search(c))   # "her eyes, now glowing" still read across
    return bool(_GLOWING_EYES.search(kept))


def eyes_guard(data: Dict, humans: Optional[Dict[str, bool]] = None) -> str:
    """F1-B (09/10, #24 shot 5): the plain-eyes guard is a rule for PEOPLE. It goes only when every character in the frame is a person
    (`humans` from assets.cast_humans; unknown → judged by the name) and nobody is written with glowing eyes, and it names who it is
    for. A shot with no character listed keeps the old general sentence."""
    from .assets import looks_non_human
    if glowing_eyes_written(data):
        return ""
    names = [str(n) for n in dict.fromkeys(data.get("characters") or [])]
    if not names:
        return " Natural human eyes, no glowing eyes."
    if not all((humans or {}).get(n, not looks_non_human(n)) for n in names):
        return ""
    # rà video #27 (12/10): the stored motion said "KELLY, XÚC TU ĐỎ: …" — a group send strips the accents, a per-shot / Kling send
    # did not; the name is written the way prompt() names it in the Image labels
    return f" {', '.join(ascii_name(n) for n in names)}: natural human eyes, no glowing eyes."


# 12/10 (#27: 19/21 VÀNG "Điểm bắt đầu"): the formula's start sentence (knowledge/formula, prompt_formula._START) for a code-written
# shot prompt — only with the flag prompt_formula; a group prompt says it once in its own start block (prompt() drops it from the shots).
START_SENTENCE = "The clip starts exactly on the pose and framing of the first image."


def untranslated(data: Dict) -> List[str]:
    """The Director fields shot_motion would write in Vietnamese (no English in motion_en) — 12/10 #27: the translation call failed
    (Anthropic out of credit) and 21 prompts went out with Vietnamese action sentences, approved."""
    out = [k for k in ("action", "end_state") if has_vietnamese(str(_en(data, k) or ""))]
    perf = _en(data, "performance")
    if isinstance(perf, dict) and any(has_vietnamese(str(perf.get(k) or "")) for k in ("face", "eyes", "body", "timing")):
        out.append("performance")
    return out


def shot_motion(data: Dict, voice: bool = False, humans: Optional[Dict[str, bool]] = None, voice_only=()) -> str:
    """A shot's motion text from the Director's fields (no Claude): size / angle / camera, then WHAT HAPPENS (the action, the end
    state), the acting, who speaks. No picture words: the shot's storyboard frame carries the composition, the identity pictures the
    looks (review 2026-09-27: image_prompt repeated looks and the style line in every shot → group prompts past 4,000 characters).
    voice: the shot goes with its own voice line (lip sync) — "no sound" would contradict the attached audio.
    humans: {character: is a person} (assets.cast_humans) — the plain-eyes guard only for people (eyes_guard).
    voice_only: characters whose profile says they are never seen (speaker_lint.voice_only_names) — no mouth for their lines.
    12/10 (#27): only a speaker IN the frame speaks (a narrator / voice-over never does); with prompt_formula the start sentence leads,
    with ambient_motion the background layer (prompt_formula.ambient_sentence) follows the people — both flags off: the old text."""
    from .shots import SIZE_WORDS
    from . import prompt_formula, speaker_lint
    perf = _en(data, "performance")
    perf = perf if isinstance(perf, dict) else {}
    back = back_view(data)                          # 13/10 #27 shot 4: a face written for a back view turns the person round
    cast = {ascii_name(str(n)) for n in data.get("characters") or []}
    all_back = bool(back) and (not cast or cast <= set(back))   # face / eyes dropped only when nobody in the shot faces the camera
    acting = "; ".join(f"{k}: {perf[k]}" for k in (("body", "timing") if all_back else ("face", "eyes", "body", "timing"))
                       if perf.get(k))
    speakers = [str(x.get("speaker")) for x in data.get("dialogue") or [] if isinstance(x, dict) and x.get("speaker")
                and speaker_lint.in_frame(data, x.get("speaker"), voice_only)]
    if voice:
        talk = " ".join(f"{s} says the line of the attached voice, lips in sync." for s in speakers)
    else:
        talk = " ".join(f"{s} speaks (mouth moving, no sound)." for s in speakers)
    if perf.get("intensity", 0) >= 4 or data.get("size") in ("CU", "ECU"):
        acting = soften(acting)            # Seedance 2.5 guide: over-strong emotion words make eyes glow — milder word, plain eyes
    guard = eyes_guard(data, humans) if acting and (perf.get("intensity", 0) >= 4) else ""
    move = str(data.get("camera_move") or "static").replace("_", " ")
    from . import motion_prose
    prose = motion_prose.enabled()       # thử D6 14/10: diễn xuất thành câu kể + máy track nói chiều (cờ tắt: chữ cũ từng byte)
    if prose:
        who = motion_prose.who_of([ascii_name(str(n)) for n in data.get("characters") or []])
        keys = ("body", "timing") if all_back else ("face", "eyes", "body", "timing")
        soft = perf.get("intensity", 0) >= 4 or data.get("size") in ("CU", "ECU")
        told = motion_prose.acting_sentence(who, {k: (soften(str(perf[k])) if soft else str(perf[k])) for k in keys if perf.get(k)})
        move = motion_prose.camera_phrase(data, who) or move
    framing = _framing(data)
    action = str(_en(data, "action") or "").strip().rstrip(".")
    end = str(_en(data, "end_state") or "").strip().rstrip(".")
    from . import motion_physics
    body = motion_physics.sentence(action, data.get("camera_move"))   # S4.4 + cờ locomotion_end_frame (câu mốc cảnh vật khi máy bám theo)
    # S4.4: one body-physics sentence for the kind of action (weight, contact)
    # F1-C (công thức motion): what changes first — the action, its end, the acting, who speaks — then the camera, then the physics
    camera = (f"{SIZE_WORDS.get(data.get('size'), data.get('size') or 'shot')}, {data.get('angle') or 'eye'} angle, camera {move}"
              + (f"; framing {framing}" if framing else "") + ".")
    camera = camera[0].upper() + camera[1:]
    start = f"{START_SENTENCE} " if prompt_formula.enabled() else ""
    ambient = prompt_formula.ambient_sentence(data)[0] if prompt_formula.ambient_on() else ""
    keep_back = (f"{', '.join(back)} stays with the back to the camera for the whole shot — the face is never seen, no turning around. "
                 if back else "")
    keep_state = state_sentences(data) if state_lock_on() else ""   # V10: the state written in words wins over the identity picture
    return (start + (f"{action}. " if action else "") + (f"It ends with {end}. " if end else "")
            + ((f"{told}{guard} " if told else "") if prose else (f"Acting — {acting}.{guard} " if acting else "")) + keep_back + (f"{keep_state} " if keep_state else "")
            + (f"{talk} " if talk else "") + (f"{ambient} " if ambient else "") + f"{camera} " + (body or "")).strip()


# ---- V10 (rà gốc video #27 13/10, G10): a character STATE written only in words (Kelly a blurred ghost, shots 4–11) while the
# identity picture is the normal look → the model drifted back to the picture by the end of the clip (shot 9 lost the ghost). With
# flag character_state_lock: a lock sentence per state for the whole shot (code-written motion) + a VÀNG in the prompt formula that
# the identity picture shows the normal look (prompt_formula.state_issues). The state comes from scenes.data["character_state"]
# ({name: words}, set by a person / the Director) or from a clause that puts the state right after the name ("KELLY, a blurred
# translucent ghost, …", "KELLY dạng bóng mờ") — never from a ghost / shadow that merely passes in the shot.
_STATE_EN = (r"(?:(?:blurred|blurry|semi-transparent|translucent|see-through|faded|ghostly)\s+){1,3}(?:ghost|figure|form|body|silhouette)"
             r"|(?:blurred|blurry)\s+ghost|ghost(?:ly)?\s+(?:form|state|body)")
_STATE_VI = {"bóng mờ": "a blurred translucent ghost", "mờ ảo": "blurred and translucent", "trong suốt": "translucent",
             "hồn ma": "a translucent ghost"}
_STATE_LINK = r"(?:\s*[,(:—–-]\s*|\s+)(?:(?:is|as|in|a|an|the|still|now|stays|remains|dạng|ở|là|vẫn|trong|một|thành)\s+){0,3}"


def state_lock_on() -> bool:
    try:
        from . import features
        return features.on("character_state_lock")
    except Exception:  # noqa: BLE001 - unreadable settings: the old behaviour (off)
        return False


def character_states(data: Dict) -> Dict[str, str]:
    """{NAME without accents: English words of the state} of the characters of the shot (see the block comment above)."""
    data = data or {}
    cast = [str(n) for n in dict.fromkeys(data.get("characters") or []) if str(n).strip()]
    out: Dict[str, str] = {}
    given = data.get("character_state") if isinstance(data.get("character_state"), dict) else {}
    for name, words in given.items():
        words = str(words or "").strip()
        en = _STATE_VI.get(words.lower(), words) if has_vietnamese(words) else words
        if en and not has_vietnamese(en):
            out[ascii_name(str(name))] = en.rstrip(".")
    en_src = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    text = " | ".join(str(src.get(k) or "") for src in (data, en_src) for k in ("image_prompt", "blocking", "action", "start_frame"))
    for name in cast:
        key = ascii_name(name)
        if key in out:
            continue
        forms = "|".join(re.escape(f) for f in dict.fromkeys((name, key)))
        m = re.search(rf"(?<!\w)(?:{forms})(?:'s)?{_STATE_LINK}(?P<s>{_STATE_EN}|{'|'.join(map(re.escape, _STATE_VI))})(?!\w)",
                      text, re.I)
        if m:
            found = m.group("s").lower()
            state = _STATE_VI.get(found, found)
            if re.search(r"(?:ghost|figure|form|body|silhouette)$", state) and not re.match(r"(?:a|an|the)\s", state):
                state = "a " + state
            out[key] = state
    return out


def state_sentences(data: Dict) -> str:
    """The lock sentence of each state ('' when none)."""
    return " ".join(f"{name} stays {state} for the whole shot, first to last frame — the identity picture shows the normal look; keep "
                    f"this state, not the picture." for name, state in character_states(data).items())


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


# rà quy ước 7: never a bare "from behind" ("peeking from behind the glue wall", "an enemy rushes in from behind")
_BACK = re.compile(r"\bback (?:turned )?to (?:the )?camera\b|\b(?:seen|shot|filmed|viewed|framed) from behind\b"
                   r"(?!\s+(?:the|a|an|his|her|their)\b)|\b(?:walk|runn|run|mov|step)\w* away from (?:the )?camera\b|"
                   r"quay lưng (?:về|lại) (?:phía )?máy", re.IGNORECASE)
_TURNS_TO_CAMERA = re.compile(r"\b(?:turns?|spins?|pivots?|swings?|looks?|glances?)\b[^.;]{0,25}?\b(?:to|toward|towards|at|into)\b"
                              r"[^.;]{0,10}?\b(?:camera|lens|viewer)\b|\bfaces? (?:the )?(?:camera|lens|viewer)\b|"
                              r"\bglances? back over (?:his|her|their) shoulder\b|quay (?:mặt |đầu )?(?:lại|về phía máy)|ngoảnh lại|"
                              r"nhìn vào máy", re.IGNORECASE)


def back_view(data: Dict) -> List[str]:
    """13/10 #27 shot 4: the names (no accents) of the people seen from BEHIND — a blocking / acting clause says back to the camera
    and names them (one-person shot: that person) — for the 'stays with the back to the camera' sentence; [] when not a back view, when the action itself turns the person round on
    purpose, or with flag back_view_guard off. A face / eyes written for a back view made Seedance turn Kelly round mid-shot."""
    from . import features
    if not features.on("back_view_guard"):
        return []
    from .continuity import _said                    # a negated match ("never with her back to camera") does not count
    perf = _en(data, "performance")
    perf = perf if isinstance(perf, dict) else {}
    moves = " ".join(str(x or "") for x in (_en(data, "action"), _en(data, "end_state"), perf.get("body"), perf.get("timing")))
    if _said(_TURNS_TO_CAMERA, moves):
        return []
    cast = [str(n) for n in dict.fromkeys(data.get("characters") or [])]
    out = []
    for clause in re.split(r"[.;\n]", ". ".join(str(x or "") for x in (data.get("blocking"), perf.get("face"), perf.get("eyes")))):
        if not _said(_BACK, clause):
            continue
        low = clause.lower()
        named = [n for n in cast if n.lower() in low or ascii_name(n).lower() in low]
        out += named or (cast if len(cast) == 1 else [])   # unnamed back view of a many-person shot: not guessed
    return [ascii_name(n) for n in dict.fromkeys(out)] or (["The character"] if not cast and _said(_BACK, " ".join(
        str(x or "") for x in (data.get("blocking"), perf.get("face"), perf.get("eyes")))) else [])


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
    limit = prompt_limit(model)             # F1-C: the model's own limit (provider_rules) — 2.5 takes 5 000, 2.0 4 000
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
    reference shot — missing or outdated — gets its prompt from code. Returns {translated, by_code, warn, held}; `held` = the shots
    whose prompt was kept waiting for a person (code_motion: Vietnamese left / VÀNG of the formula), [] when none (12/10 #27)."""
    from . import claude_tasks, lineage, llm_runner
    out = {"translated": 0, "by_code": 0, "warn": None}
    if not enabled(p.conn, pid):
        return out
    if llm is not None:
        try:
            out["translated"] = claude_tasks.translate_motion_fields(p, pid, llm)
        except (llm_runner.LlmError, ValueError) as e:
            out["warn"] = (f"không dịch được trường tiếng Việt ({e}) — shot còn tiếng Việt được viết nhưng để CHỜ DUYỆT (không tự duyệt), "
                           "prompt nhóm sẽ bị chặn khi gửi nếu còn tiếng Việt")
    elif translate_estimate(p.conn, pid):
        out["warn"] = ("chưa dịch trường tiếng Việt sang tiếng Anh (chưa có Claude) — shot còn tiếng Việt được viết nhưng để CHỜ DUYỆT; "
                       "cấu hình Claude rồi bấm lại 'Viết motion prompt'")
    stale = [sid for sid, r in lineage.scan(p.conn, pid).items() if r["motion_stale"] and uses_refs(p.conn, sid)]
    held: List[Dict] = []
    out["by_code"] = code_motion(p, pid, redo_ids=stale, out_held=held)
    out["held"] = held
    return out


def code_motion(p, pid: int, redo_ids=(), out_held: Optional[List[Dict]] = None) -> int:
    """Motion prompts written by code for the shots made by reference pictures that have an approved picture and no prompt yet — the
    group prompt is built from them (docs/THIET_KE_LAI_QC_VA_KET_NOI_2026-09-27.md mục 1: no Claude motion call for Seedance groups).
    Returns how many were written. Approved at once (nothing here was guessed by a model) — except (12/10 #27) a prompt with Vietnamese
    left in it or a VÀNG / ĐỎ of the prompt formula: kept 'pending', said per shot in ⚙ Chẩn đoán and listed in `out_held`."""
    from . import llm_io
    from .shots import image_scene
    if not enabled(p.conn, pid):
        return 0
    vi_held = {sid for sid in vietnamese_held(p.conn, pid)
               if not untranslated(json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"] or "{}"))}
    todo = []
    for s in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(s["data"] or "{}")
        if not eligible(d):
            continue
        if s["id"] in redo_ids or s["id"] in vi_held:  # outdated: written again from the Director's fields, never by Claude (review)
            p.conn.execute("DELETE FROM motion_prompts WHERE scene_id=?", (s["id"],))
        elif p.conn.execute("SELECT 1 FROM motion_prompts WHERE scene_id=?", (s["id"],)).fetchone():
            continue
        if not p.conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved'",
                              (image_scene(p.conn, s["id"]),)).fetchone():
            continue
        from . import lipsync
        voice = lipsync.enabled() and lipsync.voiced(lipsync.method_for(d))
        from .assets import cast_humans                    # F1-B: the plain-eyes guard only for people (profiles read)
        humans = cast_humans(p.conn, pid, d.get("characters") or [])
        from .speaker_lint import voice_only_names          # 12/10 #27: a voice-over character opens no mouth
        todo.append({"id": s["id"], "idx": s["idx"],
                     "motion_prompt": shot_motion(d, voice=voice, humans=humans, voice_only=voice_only_names(p.conn, pid)),
                     "duration_sec": min(floored(d, float(d.get("duration_s") or 2)), 30)})   # 28/09: a 1 s single was
                                                                                          # cut to 1 s — the collapse was cut off
    if not todo:
        return 0
    llm_io.store_motion_prompts(p, pid, {"scenes": [{k: t[k] for k in ("idx", "motion_prompt", "duration_sec")} for t in todo]})
    held = []
    from . import diag
    for t in todo:
        why, notes = _hold_reasons(p.conn, t["id"], t["motion_prompt"])
        if why:
            held.append({"scene_id": t["id"], "idx": t["idx"], "why": "; ".join(why + notes),
                         "red": any(w.startswith("ĐỎ") for w in why)})
            diag.record(p.conn, "motion", "warn", f"Shot {t['idx']}: motion viết bằng code để CHỜ DUYỆT, không tự duyệt — "
                        + "; ".join(why + notes), "code_motion_held", pid, scene_id=t["id"])
            continue
        llm_io.approve_motion_prompt(p, t["id"])
        if notes:
            diag.record(p.conn, "motion", "info", f"Shot {t['idx']}: motion viết bằng code TỰ DUYỆT dù có VÀNG ngoài phần công thức code "
                        "viết (viết từ trường Đạo diễn, không đoán) — " + "; ".join(notes), "code_motion_note", pid, scene_id=t["id"])
    if out_held is not None:
        out_held.extend(held)
    return len(todo)


def vietnamese_held(conn, pid: int) -> List[int]:
    """Shots made by reference pictures whose prompt waits ('pending') with Vietnamese in it — held by code_motion when the translation
    did not run; written again by code once their English is there (a prompt a person rewrote in English is never touched)."""
    rows = conn.execute("SELECT m.scene_id, m.motion_prompt FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id"
                        " WHERE s.project_id=? AND m.state='pending'", (pid,)).fetchall()
    out = []
    for r in rows:
        d = conn.execute("SELECT data FROM scenes WHERE id=?", (r["scene_id"],)).fetchone()
        if _vi_besides_names(r["motion_prompt"], json.loads(d["data"] or "{}")) and uses_refs(conn, r["scene_id"]):
            out.append(r["scene_id"])
    return out


def _vi_besides_names(text: str, data: Dict) -> bool:
    """Vietnamese in a code-written prompt other than the characters' names ("YÊU NỮ TÀ LINH DẠNG 1: natural human eyes" is a name —
    prompt() writes it without accents for the group, 08/10)."""
    names = [str(n) for n in data.get("characters") or []] + [str(x.get("speaker")) for x in data.get("dialogue") or []
                                                               if isinstance(x, dict) and x.get("speaker")]
    text = str(text or "")
    for name in sorted({n for n in names if n.strip()}, key=len, reverse=True):
        for form in {name, name.upper(), name.title(), name.capitalize(), name.lower()}:
            text = text.replace(form, "")
    return has_vietnamese(text)


# The parts of the motion formula the code writer itself must produce (knowledge/formula: start, action, camera, end state, who speaks,
# source of the moves, background layer). A VÀNG there = the code-written prompt is short of the formula → held for a person. Any other
# VÀNG (e.g. "hồ sơ trang phục không so được" — a note about the checker's own reach) is approved with the reason said.
HOLD_PARTS = ("diem_bat_dau", "hanh_dong", "may_quay", "trang_thai_cuoi", "thoai", "nguon_dong_tac", "chuyen_dong_nen")


def _hold_reasons(conn, scene_id: int, text: str):
    """(hold, notes) for a code-written prompt (12/10 #27: 21/21 approved at once with Vietnamese sentences and the formula's VÀNG).
    hold — must not be approved by itself: Vietnamese left in it (the translation did not run / failed), an ĐỎ of the prompt formula,
    or a VÀNG of a HOLD_PARTS part. notes — other VÀNG: approved, the reason said (formula_check written when the prompt was saved,
    flag prompt_formula). ([], []) = approved at once, as before."""
    hold, notes = [], []
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    data = json.loads(row["data"] or "{}") if row else {}
    if _vi_besides_names(text, data):
        fields = untranslated(data)
        from . import claude_tasks
        old = [k for k in claude_tasks.stale_en_keys(data) if k in fields] if claude_tasks.fresh_on() else []
        hold.append("còn chữ tiếng Việt" + (f" ở {', '.join(fields)}" if fields else "")
                    + (f" — bản dịch cũ của {', '.join(old)} không dùng vì trường đã sửa" if old else "") + " (chưa dịch sang tiếng Anh — bấm lại "
                    "'Viết motion prompt' khi Claude dịch được, hoặc sửa tay sang tiếng Anh) — chờ duyệt")
    from . import prompt_formula
    if prompt_formula.enabled():
        fc = data.get("formula_check") or {}
        if fc.get("motion_sha") != prompt_formula._sha(text):     # the check of THIS prompt did not get written (on_prompt_saved
            hold.append("chưa kiểm được công thức của prompt này (xem ⚙ Chẩn đoán) — chờ duyệt")   # never raises): not a stale verdict
            return hold, notes
        for i in fc.get("motion") or []:
            if not isinstance(i, dict) or i.get("level") not in ("warn", "red"):
                continue
            label = prompt_formula.PART_LABELS.get(i.get("part"), i.get("part"))
            line = f"{'ĐỎ' if i['level'] == 'red' else 'VÀNG'} công thức {label}: {i.get('msg', '')}"
            (hold if i["level"] == "red" or i.get("part") in HOLD_PARTS else notes).append(line)
    return hold, notes


def translate_estimate(conn, pid: int) -> float:
    """USD of the ONE translation call write_by_code would make now (claude_tasks.translate_motion_fields, worst case as the budget
    lock reads it — project_budget._translate_worst) — 0 when no shot made by reference pictures still needs English. For the Step 3
    button: the price is shown before the click (luật chi phí)."""
    from . import claude_tasks, project_budget
    need = False
    for sid, raw in conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (pid,)).fetchall():
        d = json.loads(raw or "{}")
        item = {k: d[k] for k in claude_tasks.TRANSLATE_KEYS if d.get(k) and claude_tasks._vi(d[k])}
        perf = d.get("performance") if isinstance(d.get("performance"), dict) else {}
        pv = {k: perf[k] for k in claude_tasks.TRANSLATE_PERF if perf.get(k) and claude_tasks._vi(perf[k])}
        if pv:                                                   # the same item translate_motion_fields sends
            item["performance"] = pv
        if item and d.get("motion_en_src") != claude_tasks._src_key(item) and uses_refs(conn, sid):
            need = True
            break
    return project_budget._translate_worst(conn, pid) if need else 0.0
