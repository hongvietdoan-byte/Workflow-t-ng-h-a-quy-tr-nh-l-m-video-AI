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


def light_sentence(data: Dict) -> str:
    """Trial #8: the Director asked for "most of the frame sunk in deep shadow" and the night frames came out muddy — dark scenes still
    light the faces."""
    return LIGHT.get(str(data.get("time") or "day").lower(), LIGHT["day"]) if enabled() else ""


def _dir(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "establish")


def _load(data_dir: str, pid: int) -> Dict:
    try:
        with open(os.path.join(_dir(data_dir, pid), "index.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data_dir: str, pid: int, idx: Dict) -> None:
    os.makedirs(_dir(data_dir, pid), exist_ok=True)
    with open(os.path.join(_dir(data_dir, pid), "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)


def scene_rows(conn, pid: int, story_scene) -> List[Dict]:
    return [{"id": r["id"], "data": json.loads(r["data"] or "{}")} for r in conn.execute(
        "SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
        if json.loads(r["data"] or "{}").get("story_scene") == story_scene]


def place_pictures(conn, asset_id) -> List[str]:
    """The place's approved pictures, full views first (eye level, then the rest) — the 3D renders of the tower for #8."""
    if not asset_id:
        return []
    rows = conn.execute("SELECT path FROM asset_images WHERE asset_id=? AND status='approved'"
                        " ORDER BY (role='eye_level') DESC, (role='detail') ASC, id", (asset_id,)).fetchall()
    return [r["path"] for r in rows if r["path"] and os.path.exists(r["path"])][:MAX_PLACE_PICTURES]


def prompt_for(conn, pid: int, rows: List[Dict]) -> str:
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
        f"reference pictures (the same buildings, shapes, windows, stairs, vegetation)." + looks.image_sentence(proj))


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
         say: Callable[[str, str, str], None] = lambda sev, code, msg: None) -> str:
    """Move the scene's establishing picture one step: "ready" / "waiting" (sent, not back yet — the shots wait) / "skipped" (off, no
    place, provider without submit, refused, over the limit: the shots draw without it, said once)."""
    if not enabled() or story_scene is None:
        return "skipped"
    rows = scene_rows(conn, pid, story_scene)
    if not rows:
        return "skipped"
    pictures = place_pictures(conn, rows[0]["data"].get("location_asset"))
    key = key_of(rows, pictures)
    idx = _load(data_dir, pid)
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
                dest = os.path.join(_dir(data_dir, pid), f"scene_{story_scene}.png")
                os.makedirs(_dir(data_dir, pid), exist_ok=True)
                rec.update(path=provider.download(rec["message_id"], dest), state="ready")
            elif st.state == "failed":
                rec.update(state="failed", error=st.error_message)
                say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene} hỏng ({st.error_message}) — các shot vẽ không có nó")
        except ProviderError as e:
            if not e.transient:
                rec.update(state="failed", error=str(e))
                say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene}: {e} — các shot vẽ không có nó")
        idx[str(story_scene)] = rec
        _save(data_dir, pid, idx)
        return {"ready": "ready", "failed": "skipped"}.get(rec.get("state"), "waiting")
    from . import budget, cost
    with budget.SPEND_LOCK:
        over = budget.check_image(conn, getattr(provider, "name", "?"), model)
        if over:
            say("warn", "budget", f"ảnh toàn cảnh cảnh {story_scene} không gửi: {over}")
            return "skipped"
        prompt = prompt_for(conn, pid, rows)
        try:
            try:
                mid = provider.submit(prompt, pictures or None, size=SIZE, model=model)
            except TypeError:                                  # a provider without per-job models (mock)
                mid = provider.submit(prompt, pictures or None, size=SIZE)
        except ProviderError as e:
            idx[str(story_scene)] = {"key": key, "state": "failed", "error": str(e)}
            _save(data_dir, pid, idx)
            say("warn", "establishing", f"ảnh toàn cảnh cảnh {story_scene} bị từ chối: {e} — các shot vẽ không có nó")
            return "skipped"
        info = getattr(provider, "usage_info", None)             # the same model / tier the picture runner records
        used, tier = (info(model) if model else info()) if info is not None else (model or "unknown", "image")
        cost.record_usage(conn, None, "image", getattr(provider, "name", "?"), used, tier, 1, "image", project_id=pid,
                          stage="establishing")
    idx[str(story_scene)] = {"key": key, "state": "running", "message_id": mid, "prompt": prompt, "refs": pictures}
    _save(data_dir, pid, idx)
    say("info", "establishing", f"gửi ảnh toàn cảnh cảnh {story_scene} ({len(pictures)} ảnh bối cảnh tham chiếu)")
    return "waiting"


def pending(conn, pid: int, data_dir: str) -> int:
    """Establishing pictures a run would still pay for (for the estimate)."""
    if not enabled():
        return 0
    scenes = {json.loads(r["data"] or "{}").get("story_scene") for r in conn.execute("SELECT data FROM scenes WHERE project_id=?", (pid,))}
    return sum(1 for s in scenes if s is not None and picture(data_dir, pid, s) is None)
