"""Storyboard picture mode (feature `storyboard_api`): the shots of one script scene are drawn as ONE Deepix storyboard, the way the web
Weave Canvas Storyboard node does it (read 2026-09-25; tested on #7 scene 1: same tower position, stairs, lamps and exposure across the 4
frames, where separate pictures moved the tower and changed the light).

  anchor     the scene's widest shot (the place is fully seen — the continuity anchor), else its first shot; drawn first with the
             scene's shared references (ref_mode "global")
  the rest   wait for the anchor's picture, then go out with the shared references + the anchor picture (in parallel, as the Canvas)
  every job  carries the storyboard fields (prompt_key 14: story_text, storyboard_id, frame_index, group_size, ref_mode, image_mapping)

The runner's normal machinery stays: one picture job per shot, the ledger, the cap, QC, regenerate one frame (same group fields).
"""
import hashlib
import json
import os
from typing import Dict, List, Optional

from . import assets, features
from .storyboard_frames import mapping_text

FEATURE = "storyboard_api"
_WIDE_ORDER = ("EWS", "WS", "GAME_TPS", "MLS", "MS", "MCU", "CU", "ECU")


def enabled() -> bool:
    return features.on(FEATURE)


def scene_shots(conn, pid: int, story_scene) -> List[Dict]:
    out = []
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(r["data"] or "{}")
        if d.get("story_scene") == story_scene and d.get("shot_no"):
            out.append({"id": r["id"], "idx": r["idx"], "data": d})
    return out


def anchor_of(shots: List[Dict]) -> Optional[Dict]:
    if not shots:
        return None
    rank = lambda s: _WIDE_ORDER.index(str(s["data"].get("size") or "MS").upper()) if str(s["data"].get("size") or "MS").upper() in _WIDE_ORDER else 4  # noqa: E731
    return min(shots, key=lambda s: (rank(s), s["idx"]))


def group_of(conn, pid: int, scene_id: int) -> Optional[Dict]:
    """{"shots", "anchor", "index" (0-based position of this shot in the scene), "story_scene"} for a shot of a scene with 2+ shots."""
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    d = json.loads(row["data"] or "{}") if row else {}
    if not d.get("story_scene") or not d.get("shot_no"):
        return None
    shots = scene_shots(conn, pid, d["story_scene"])
    if len(shots) < 2:
        return None
    return {"shots": shots, "anchor": anchor_of(shots), "index": next(i for i, s in enumerate(shots) if s["id"] == scene_id),
            "story_scene": d["story_scene"]}


def anchor_picture(conn, data_dir: str, pid: int, anchor_id: int) -> Optional[str]:
    """The anchor shot's picture as soon as it exists (made, waiting for review, or approved) — the Canvas uses frame 1 right away."""
    j = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN ('succeeded','pending_review','approved')"
                     " ORDER BY (state='approved') DESC, id DESC LIMIT 1", (anchor_id,)).fetchone()
    if j is None:
        return None
    path = os.path.join(data_dir, str(pid), "images", f"job_{j['id']}.png")
    return path if os.path.exists(path) else None


def _shot_data(g: Dict, scene_id: int) -> Dict:
    return next((s["data"] for s in g["shots"] if s["id"] == scene_id), {})


def turned_away(g: Dict, scene_id: int) -> bool:
    """08/10 (#24, lỗi D): this shot's `plate_view` turns the camera away from the place's landmark (away / left / right) while the
    anchor frame does not — the anchor picture (frame 1, #24 shot 1 WS looking at the Tháp Đồng Hồ) shows the landmark, and sent as a
    reference it pulled the tower into shot 4 (reverse shot towards the red-roof house; job 576 sent job_573.png)."""
    from .plate_choice import landmark_off_frame
    anchor = g.get("anchor")
    if not anchor or anchor["id"] == scene_id:
        return False
    return landmark_off_frame(_shot_data(g, scene_id)) and not landmark_off_frame(anchor["data"])


def own_camera(g: Dict, scene_id: int) -> bool:
    """10/10 (#24 QC sau V4): shot có máy Sân khấu 3D đã khóa (`stage_camera`, cờ stage_camera) — nền của nó là render của CHÍNH máy
    đó. Ảnh neo (frame 1 cũ nhìn tháp) + phiên storyboard chung kéo lại nền cũ: 9/9 ảnh vẽ 'nền mẫu' tháp giữa + nhà mái đỏ dù máy
    nhìn Tây (job 623–631). Như lỗi D: không ảnh neo, phiên riêng; câu dặn riêng (không ép bỏ mốc — máy có thể vẫn thấy tháp)."""
    from . import features, plate_camera
    if not features.on("stage_camera") or not g.get("anchor") or g["anchor"]["id"] == scene_id:
        return False
    return bool((_shot_data(g, scene_id) or {}).get(plate_camera.STAGE_FIELD))


OWN_CAMERA_NOTE = (" This frame has its OWN camera on the stage (another position, height, direction and tilt than frame 1): its "
                   "background is ONLY the 3D render of this frame's camera sent with it — the same buildings, walls, landmark (or none), "
                   "horizon line and tilt as that render; never the view of frame 1 or of another frame.")


def uses_anchor(g: Optional[Dict], scene_id: int) -> bool:
    """A shot of a storyboard scene drawn from the anchor picture: not the anchor itself, not a shot turned away from the landmark
    the anchor shows (lỗi D: it gets no anchor picture, so it neither waits for it nor shares its storyboard session)."""
    return bool(g) and g["anchor"]["id"] != scene_id and not turned_away(g, scene_id) and not own_camera(g, scene_id)


def waits(conn, data_dir: str, pid: int, scene_id: int) -> bool:
    """A non-anchor shot waits for its scene's anchor picture (a shot turned away from the landmark does not use it: uses_anchor)."""
    g = group_of(conn, pid, scene_id)
    return uses_anchor(g, scene_id) and anchor_picture(conn, data_dir, pid, g["anchor"]["id"]) is None


ON_ITS_WAY = ("queued", "running", "retryable", "succeeded", "pending_review", "approved")


def wait_reason(conn, data_dir: str, pid: int, scene_id: int) -> Optional[Dict]:
    """08/10 (#24, lỗi 11): why a shot's picture is not sent yet in storyboard mode — {"anchor_idx", "anchor_id", "stuck", "text"}, None
    when it does not wait. stuck = the anchor shot has no picture job on its way, so the wait never ends by itself (pilot without it)."""
    if not waits(conn, data_dir, pid, scene_id):
        return None
    g = group_of(conn, pid, scene_id)
    anchor = g["anchor"]
    live = conn.execute("SELECT 1 FROM jobs WHERE scene_id=? AND type='image_gen' AND state IN (" + ",".join("?" * len(ON_ITS_WAY)) + ")",
                        (anchor["id"], *ON_ITS_WAY)).fetchone()
    shot = next((s for s in g["shots"] if s["id"] == scene_id), {"idx": "?"})
    text = (f"Shot {shot['idx']} chờ ảnh neo của cảnh (shot {anchor['idx']}, khung rộng nhất — chế độ storyboard)"
            + ("" if live else f" — shot {anchor['idx']} CHƯA được xếp hàng: gen ảnh shot {anchor['idx']} trước (thêm vào gen thử / "
                                "▶ Gen ảnh), không thì ảnh này chờ mãi"))
    return {"anchor_idx": anchor["idx"], "anchor_id": anchor["id"], "stuck": not live, "text": text}


PERSON_ROLES = ("character", "outfit") + assets.STANDARD_ROLES


def shared_references(conn, pid: int, shots: List[Dict], limit: int = 8, cast_of: Optional[Dict] = None) -> List[Dict]:
    """The pictures every frame of the scene shares: each character once (the scene's cast), the place once.
    cast_of = the data of the shot being drawn: only ITS people's pictures go (the place and props stay shared). S4.6 (#10,
    2026-09-29): a KELLY-only and a KENTA-only frame were sent the pictures of Kelly, Kenta and Maxim (jobs 453-456 sent_refs) and came
    back with all three people; the sentence "only KELLY is in this frame" (vòng 2) helped but the pictures were still the pull."""
    keep = None
    if cast_of is not None:
        own = dict(cast_of)
        keep = {r["label"] for r in assets.scene_references(conn, pid, own, limit=99) if r.get("role") in PERSON_ROLES}
    out, seen = [], set()
    for s in shots:
        data = dict(s["data"])
        for r in assets.scene_references(conn, pid, data, limit=assets.MAX_REFERENCES):
            if r["path"] in seen or len(out) >= limit:
                continue
            if keep is not None and r.get("role") in PERSON_ROLES and r["label"] not in keep:
                continue                               # a person of another frame of the scene: not sent with this frame
            seen.add(r["path"])
            out.append(r)
    return out


def anchor_note(g: Dict, scene_id: int, image_no: int) -> str:
    """The anchor frame (frame 1) sent with a later frame shows the anchor shot's people; when this shot's people differ, say that the
    anchor gives the place and light, not its people (the mapping line alone says "inherit ... character appearance")."""
    shot = next((s for s in g["shots"] if s["id"] == scene_id), None)
    anchor = g.get("anchor")
    if shot is None or not anchor or anchor["id"] == scene_id:
        return ""
    cast = [str(n) for n in shot["data"].get("characters") or []]
    theirs = [str(n) for n in anchor["data"].get("characters") or [] if str(n) not in cast]
    if not theirs:
        return ""
    return (f"\nImage {image_no} is frame 1 of the scene: take its place, light and style only — {', '.join(theirs)} "
            f"{'is' if len(theirs) == 1 else 'are'} in frame 1 but NOT in this frame.")


def story_text(conn, pid: int, g: Dict) -> str:
    from .runner import no_minor_age
    from . import scene_establish
    row = conn.execute("SELECT heading, text FROM story_scenes WHERE project_id=? AND idx=?", (pid, g["story_scene"])).fetchone()
    head = f"{row['heading']}: " if row and row["heading"] else ""
    beats = " ".join(f"Frame {i + 1}{_in_frame(s['data'])}: {(s['data'].get('action') or s['data'].get('image_prompt') or '')[:140]}"
                     for i, s in enumerate(g["shots"]))
    frame = ("One continuous scene — same place, same light, the same people and outfits wherever they appear; each frame shows only "
             "the people it names.")
    datas = [s["data"] for s in g.get("shots") or []]
    # the scene's light: a flashback sentence only when EVERY frame is one (a flashback shot gets its own sentence in its prompt)
    if datas and not all(scene_establish.is_flashback(d) for d in datas):
        datas = [d for d in datas if not scene_establish.is_flashback(d)]
    light = scene_establish.light_sentence(datas[0] if datas else {})
    if light:
        frame += " " + light
    return no_minor_age(f"{head}{frame} {beats}")[:3000]


def _in_frame(data: Dict) -> str:
    cast = [str(n) for n in data.get("characters") or []]
    return f" (in frame: {', '.join(cast)})" if cast else " (no person in frame)"


def cast_note(g: Dict, scene_id: int) -> str:
    """S4.6 (#10, 2026-09-29): frames 1-2 of a one-person shot came back with all three people (Kelly-only and Kenta-only shots drew
    Kenta, Kelly and Maxim). The shot says who is NOT in it; since then only its own people's pictures are sent (shared_references
    cast_of) — the sentence stays for the anchor frame and the scene text, which still name the others."""
    shot = next((s for s in g["shots"] if s["id"] == scene_id), None)
    if shot is None:
        return ""
    cast = [str(n) for n in shot["data"].get("characters") or []]
    others = []
    for s in g["shots"]:
        for n in s["data"].get("characters") or []:
            if str(n) not in cast and str(n) not in others:
                others.append(str(n))
    if not others:
        return ""
    who = f"Only {', '.join(cast)} {'is' if len(cast) == 1 else 'are'} in this frame" if cast else "No person is in this frame"
    return (f" {who}; {', '.join(others)} {'is' if len(others) == 1 else 'are'} NOT in this frame (they appear in other frames "
            "of the scene) — do not draw them, not even in the background.")


def storyboard_id(pid: int, g: Dict, anchor_job_id: int, fresh_for: int = 0, own_shot: int = 0) -> str:
    """One id per scene and anchor picture: the anchor job and every frame drawn from its picture share it (a new anchor picture
    starts a new storyboard). fresh_for = a redraw job that gets a session of its own (see fresh_session). own_shot = a shot turned
    away from the landmark (lỗi D): a session of its own, not the anchor's (#8: the provider's session carries the earlier frames)."""
    key = (f"{pid}:{g['story_scene']}:{anchor_job_id}" + (f":away{own_shot}" if own_shot else "")
           + (f":redo{fresh_for}" if fresh_for else ""))
    return "sb_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def fresh_session(conn, job_id: int) -> bool:
    """A redraw WITH a fix goes out in a new storyboard session (the scene anchor picture is still sent as a reference).
    #8 2026-09-27: S4·2 redrawn twice in the same session (same storyboard_id + frame_index) came back as a sunset both times although
    the fix said "no sunset" and the failed picture was NOT among the references — the provider's session is the input that did not
    change. A resend after the provider created nothing (RESEND_NOTE) keeps the session: that is the same attempt again."""
    if not job_id:
        return False
    row = conn.execute("SELECT parent_job_id, retry_reason FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None or not row["parent_job_id"]:
        return False
    from .runner import RESEND_NOTE
    return not (row["retry_reason"] or "").startswith(RESEND_NOTE)


def away_note(landmark: Optional[str] = None) -> str:
    """The sentence that goes with a shot turned away from the landmark (lỗi D): the story text still describes frame 1 with the
    landmark — this frame looks the other way, its background comes from its own render / words."""
    mark = landmark or "the landmark seen in frame 1"
    return (f" The camera of this frame is turned away from {mark}: {mark} is NOT in this frame, not even far in the background — "
            "the background is the side of the place this frame's text and its 3D render show, not the view of frame 1.")


PREVIOUS_NOTE = ("\nImage {n} is the shot right before this one: keep exactly its camera position, framing, shot size, the character's spot "
                 "and the background — change only what this frame's text says.")


def job_fields(conn, data_dir: str, pid: int, scene_id: int, refs: List[Dict], job_id: int = 0,
               previous: Optional[str] = None, landmark: Optional[str] = None) -> Optional[Dict]:
    """(storyboard kwargs for the provider, the reference list to send) for this shot's picture job, or None (not in storyboard mode).
    refs = the shared references already chosen for the job; a non-anchor shot adds the anchor picture last.
    previous = the approved picture of the shot right before (project set to "always chain the previous shot"): sent after the anchor —
    07/10 Khủng Long Đỏ: "same frame as shot 3" came out in another frame because storyboard mode sent only the anchor (shot 1).
    A shot turned away from the landmark (turned_away, lỗi D 08/10 #24) gets NO anchor picture and a storyboard session of its own;
    its people/outfits still come from `refs` (the shared references keep each character's pictures) and away_note goes with the
    prompt. landmark = the place's landmark name for that sentence."""
    g = group_of(conn, pid, scene_id)
    if g is None:
        return None
    is_anchor = g["anchor"]["id"] == scene_id
    away = turned_away(g, scene_id)
    own = own_camera(g, scene_id)
    anchor_pic = None if is_anchor or away or own else anchor_picture(conn, data_dir, pid, g["anchor"]["id"])
    send = list(refs) + ([{"path": anchor_pic, "label": "frame 1 (scene anchor)", "role": "previous_scene"}] if anchor_pic else [])
    prev_note = ""
    if previous and os.path.exists(previous) and previous != anchor_pic:
        send.append({"path": previous, "label": "previous shot (same camera)", "role": "same_frame"})
        prev_note = PREVIOUS_NOTE.format(n=len(send))
    mode = "global" if refs else "sequential"
    anchor_job = job_id if is_anchor else int(os.path.basename(anchor_pic)[4:].split(".")[0].split("_")[0]) if anchor_pic else 0
    fresh = 0 if is_anchor or not fresh_session(conn, job_id) else job_id
    return {"storyboard": {"story_text": story_text(conn, pid, g),
                           "storyboard_id": storyboard_id(pid, g, anchor_job, fresh, own_shot=scene_id if (away or own) else 0),
                           "frame_index": g["index"], "group_size": len(g["shots"]), "ref_mode": mode,
                           "image_mapping": (mapping_text(send, len(refs)) + (anchor_note(g, scene_id, len(refs) + 1) if anchor_pic else "")
                                             + prev_note) if send else ""},
            "refs": send, "anchor": is_anchor,
            "cast_note": cast_note(g, scene_id) + (away_note(landmark) if away else (OWN_CAMERA_NOTE if own else "")),
            "anchor_skipped": away or own}
