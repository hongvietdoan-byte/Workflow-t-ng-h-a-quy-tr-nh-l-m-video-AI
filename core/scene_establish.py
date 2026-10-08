"""One wide establishing picture per script scene (flag scene_establishing; người dùng đề xuất + chốt 2026-09-27).

Trial #8: pasting green-screen characters on 3D plates gave the exact geometry but no contact with the ground, weak light and a lost
tower silhouette (the plate camera stood 1–2 m from the character); the 4 frames of #7 — the model drawing the whole scene with the 3D
renders of the tower as references — had both the tower and the quality. So each script scene first gets ONE wide 2048×1152 picture of
its place, time and light (no people), drawn from the place's own approved pictures (the tower renders), and that picture goes with
every shot of the scene as the shared reference for the place: the details of the place stay the same from shot to shot and the model
still draws the people into the scene with real light, shadows and dust. The video stays vertical (a 16:9 → 9:16 crop keeps 32 % of the
width). Sent, polled and priced inside the picture runner's heartbeat — the same in the automatic run and from the Step 2 buttons.

State per project: data/projects/<id>/establish/index.json {story_scene: {"key", "message_id", "state", "path", "error"}}."""
import hashlib
import json
import os
import re
from typing import Callable, Dict, List, Optional

from . import features

FEATURE = "scene_establishing"
SIZE = "2048x1152"
MAX_PLACE_PICTURES = 3
LIGHT = {"night": ("Night, yet every face is clearly lit and readable: a soft warm street-lamp key light on the faces, a cool moonlight "
                   "rim light separating the people from the background, lamps glowing around — dark sky, never muddy or crushed into black."),
         "dusk": "Dusk: warm low sun from the side, long soft shadows, faces lit and readable.",
         "day": "Bright daylight, clear shadows on the ground under the people, natural contact with the floor."}
LABEL = "the place of this scene (wide view of the whole place, its architecture and this scene's light)"


def enabled() -> bool:
    return features.on(FEATURE)


def shadow() -> bool:
    """🎓 học việc (B1 08/10): runs and records its decision, never acts."""
    return features.shadow(FEATURE)


def active() -> bool:
    """On or học việc — for choosing a branch only."""
    return features.active(FEATURE)


FLASHBACK = ("This is a FLASHBACK: warm amber, soft, slightly hazy light with a gentle glow — it must look clearly different from the "
             "present-day shots of the same place (not the same hard midday light).")
_FLASHBACK = re.compile(r"flash\s*back|hồi tưởng|ký ức|memory|in the past", re.I)


def is_flashback(data: Dict) -> bool:
    """THIS shot is a flashback: its own words (action, picture prompt) or an explicit flag. Not the scene-level notes: #8 2026-09-27
    the story `beat` of scene 4 said "plant for the flashback promise in scene 5" and scene 5's `lighting` said "the flashback uses
    warmer light" — reading those made all of scene 4 and S5·1/S5·2 "flashbacks", and every redraw of S4·2 came back as a sunset."""
    if data.get("flashback"):
        return True
    return bool(_FLASHBACK.search(" ".join(str(data.get(k) or "") for k in ("action", "image_prompt"))))


def light_sentence(data: Dict) -> str:
    """Trial #8: the Director asked for "most of the frame sunk in deep shadow" and the night frames came out muddy — dark scenes still
    light the faces. A flashback gets its own light: agent QC #8 found S5·3 (flashback) identical to the present day, the scene's
    establishing picture's hard noon light won."""
    if not enabled():
        return ""
    if is_flashback(data):
        return FLASHBACK
    return LIGHT.get(str(data.get("time") or "day").lower(), LIGHT["day"])


def _dir(data_dir: str, pid: int, trainee: bool = False) -> str:
    """🎓 học việc pictures live apart (establish/trainee/): picture(), reference() and the light sentence never see them."""
    base = os.path.join(data_dir, str(pid), "establish")
    return os.path.join(base, "trainee") if trainee else base


def _load(data_dir: str, pid: int, trainee: bool = False) -> Dict:
    try:
        with open(os.path.join(_dir(data_dir, pid, trainee), "index.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data_dir: str, pid: int, idx: Dict, trainee: bool = False) -> None:
    os.makedirs(_dir(data_dir, pid, trainee), exist_ok=True)
    with open(os.path.join(_dir(data_dir, pid, trainee), "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)


TRAINEE_USD = 0.05                                   # ≈ one establishing picture (kế hoạch học việc mục 2)
_INDOOR = re.compile(r"\b(indoors?|interior|inside)\b|trong nhà|^\s*INT\.", re.I)


def indoor(conn, pid: int, rows: List[Dict]) -> Optional[str]:
    """Why the scene is indoor (a wide establishing view of the place does not apply), else None: the 3D spot says so, or the
    scene's place / `indoor` field does."""
    d = rows[0]["data"] if rows else {}
    if d.get("indoor") is True:
        return "indoor"
    if _INDOOR.search(str(d.get("location") or "")):
        return str(d.get("location"))
    try:
        from .runner import indoor_spot
        return indoor_spot(conn, pid, d)
    except Exception:                                  # noqa: BLE001 — no 3D model → not known as indoor
        return None


def _trainee_record(conn, pid: int, story_scene, rows: List[Dict], decision: str, would_do: Dict, cost: float = 0.0) -> None:
    from . import trainee
    trainee.record(conn, FEATURE, pid, f"scene:{story_scene}", decision, would_do=would_do, cost_usd=cost,
                   scene_id=rows[0]["id"] if rows else None, story_scene=story_scene if isinstance(story_scene, int) else None)


def scene_rows(conn, pid: int, story_scene) -> List[Dict]:
    return [{"id": r["id"], "data": json.loads(r["data"] or "{}")} for r in conn.execute(
        "SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
        if json.loads(r["data"] or "{}").get("story_scene") == story_scene]


def place_pictures(conn, asset_id) -> List[str]:
    """The place's approved pictures, full views first (eye level, then the rest) — the 3D renders of the tower for #8."""
    if not asset_id:
        return []
    rows = conn.execute("SELECT path FROM asset_images WHERE asset_id=? AND status IN ('approved','claude_ok')"
                        " ORDER BY (role='eye_level') DESC, (role='detail') ASC, id", (asset_id,)).fetchall()
    from . import assets                                             # 06/10: stored paths are relative to the install folder
    paths = [assets.resolve(r["path"]) for r in rows if r["path"]]
    return [p for p in paths if os.path.exists(p)][:MAX_PLACE_PICTURES]


RENDER_NOTE = (" The FIRST reference picture is the exact 3D model of the real game map seen from this scene's main camera: keep the "
               "same buildings in the same places, the same number of floors, roof shapes, windows, stairs, walls and trees, the same "
               "horizon line, camera height and perspective — only add light, atmosphere and texture detail.")


def scene_pictures(conn, pid: int, rows: List[Dict], data_dir: Optional[str]) -> List[str]:
    """The place pictures of a scene's establishing picture: with `place_render_refs`, the render of the scene's widest shot first
    (the exact place), then the library's approved pictures."""
    pictures = place_pictures(conn, rows[0]["data"].get("location_asset")) if rows else []
    from . import place_refs
    if data_dir and rows and place_refs.enabled():
        render = place_refs.scene_render(data_dir, pid, rows)
        if render:
            pictures = [render] + [p for p in pictures if p != render][:MAX_PLACE_PICTURES - 1]
    return pictures


def prompt_for(conn, pid: int, rows: List[Dict], with_render: bool = False) -> str:
    from . import looks
    from .runner import no_minor_age
    d = rows[0]["data"] if rows else {}
    place = str(d.get("location") or "the place").strip()
    time = str(d.get("time") or "day").lower()
    weather = str(d.get("weather") or "clear").lower()
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return no_minor_age(
        f"Wide establishing shot of {place}: the whole place with its main landmark fully in frame (from its base to its top), "
        f"{time}, {weather} weather. {LIGHT.get(time, LIGHT['day'])} No people, no characters. Keep exactly the architecture of the "
        f"reference pictures (the same buildings, shapes, windows, stairs, vegetation)." + (RENDER_NOTE if with_render else "")
        + looks.image_sentence(proj))


def key_of(rows: List[Dict], pictures: List[str]) -> str:
    d = rows[0]["data"] if rows else {}
    raw = json.dumps([d.get("location"), d.get("location_asset"), d.get("time"), d.get("weather"), pictures], ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def picture(data_dir: str, pid: int, story_scene) -> Optional[str]:
    rec = _load(data_dir, pid).get(str(story_scene)) or {}
    return rec["path"] if rec.get("state") == "ready" and rec.get("path") and os.path.exists(rec["path"]) else None


def reference(data_dir: str, pid: int, story_scene) -> Optional[Dict]:
    path = picture(data_dir, pid, story_scene) if enabled() else None
    return {"path": path, "label": LABEL, "role": "location"} if path else None


def step(conn, pid: int, story_scene, provider, data_dir: str, model: Optional[str] = None,
         say: Callable[[str, str, str], None] = lambda sev, code, msg: None, trainee: bool = False) -> str:
    """Move the scene's establishing picture one step: "ready" / "waiting" (sent, not back yet — the shots wait) / "skipped" (off, no
    place, provider without submit, refused, over the limit: the shots draw without it, said once).
    `trainee` (🎓 học việc, B6 08/10): the picture goes to establish/trainee/ (ledger stage `trainee_establishing`), nothing is said,
    the caller never waits on it; trainee_log gets "establish" once it is back, "skip" (establish_skip_indoor) for an indoor scene."""
    if not (shadow() if trainee else enabled()) or story_scene is None:
        return "skipped"
    rows = scene_rows(conn, pid, story_scene)
    if not rows:
        return "skipped"
    if trainee:
        say = lambda sev, code, msg: None                  # noqa: E731 — nothing shown before the person decides
        why = indoor(conn, pid, rows)
        if why:
            idx = _load(data_dir, pid, True)
            if (idx.get(str(story_scene)) or {}).get("state") != "skipped_indoor":
                idx[str(story_scene)] = {"state": "skipped_indoor", "why": why}
                _save(data_dir, pid, idx, True)
                _trainee_record(conn, pid, story_scene, rows, "skip", {"reason": "establish_skip_indoor", "where": why})
            return "skipped"
    from . import place_refs
    if place_refs.enabled() and any(place_refs.missing(conn, data_dir, pid, r["id"], r["data"]) for r in rows):
        return "waiting"                                   # the 3D renders of the scene come first (ImageRunner._wait starts them)
    pictures = scene_pictures(conn, pid, rows, data_dir)
    with_render = bool(pictures) and place_refs.enabled() and pictures[0] == place_refs.scene_render(data_dir, pid, rows)
    key = key_of(rows, pictures)
    idx = _load(data_dir, pid, trainee)
    rec = idx.get(str(story_scene)) or {}
    if rec.get("key") == key and rec.get("state") == "ready" and rec.get("path") and os.path.exists(rec["path"]):
        return "ready"
    if rec.get("key") == key and rec.get("state") == "failed":
        return "skipped"
    from .providers import ProviderError
    if rec.get("key") == key and rec.get("state") == "running" and rec.get("message_id"):
        try:
            st = provider.status(rec["message_id"])
            if st.state == "succeeded":
                dest = os.path.join(_dir(data_dir, pid, trainee), f"scene_{story_scene}.png")
                os.makedirs(_dir(data_dir, pid, trainee), exist_ok=True)
                rec.update(path=provider.download(rec["message_id"], dest), state="ready")
                if trainee:
                    _trainee_record(conn, pid, story_scene, rows, "establish",
                                    {"path": rec["path"], "refs": rec.get("refs") or [], "prompt": rec.get("prompt")}, TRAINEE_USD)
            elif st.state == "failed":
                rec.update(state="failed", error=st.error_message)
                say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene} hỏng ({st.error_message}) — các shot vẽ không có nó")
        except ProviderError as e:
            if not e.transient:
                rec.update(state="failed", error=str(e))
                say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene}: {e} — các shot vẽ không có nó")
        idx[str(story_scene)] = rec
        _save(data_dir, pid, idx, trainee)
        return {"ready": "ready", "failed": "skipped"}.get(rec.get("state"), "waiting")
    from . import spend_gate
    # S14.1: the gate adds the project's locked budget (it was skipped), a paused project and 'out_of_credit' → halt
    with spend_gate.spend(conn, "image", getattr(provider, "name", "?"), project_id=pid, model=model,
                          ledger_stage="trainee_establishing" if trainee else "establishing") as slot:
        if slot.over:
            say("warn", "budget", f"ảnh toàn cảnh cảnh {story_scene} không gửi: {slot.over}")
            return "skipped"
        prompt = prompt_for(conn, pid, rows, with_render)
        try:
            try:
                mid = slot.send(provider.submit, prompt, pictures or None, size=SIZE, model=model)
            except TypeError:                                  # a provider without per-job models (mock)
                mid = slot.send(provider.submit, prompt, pictures or None, size=SIZE)
        except ProviderError as e:
            idx[str(story_scene)] = {"key": key, "state": "failed", "error": str(e)}
            _save(data_dir, pid, idx, trainee)
            say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene} bị từ chối: {e} — các shot vẽ không có nó")
            return "skipped"
        info = getattr(provider, "usage_info", None)             # the same model / tier the picture runner records
        used, tier = (info(model) if model else info()) if info is not None else (model or "unknown", "image")
        slot.record(model=used, tier=tier)
    idx[str(story_scene)] = {"key": key, "state": "running", "message_id": mid, "prompt": prompt, "refs": pictures}
    _save(data_dir, pid, idx, trainee)
    say("info", "establishing", f"gửi ảnh toàn cảnh cảnh {story_scene} ({len(pictures)} ảnh bối cảnh tham chiếu)")
    return "waiting"


def pending(conn, pid: int, data_dir: str) -> int:
    """Establishing pictures a run would still pay for (for the estimate)."""
    if not enabled():
        return 0
    scenes = {json.loads(r["data"] or "{}").get("story_scene") for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,))}
    return sum(1 for s in scenes if s is not None and picture(data_dir, pid, s) is None)
