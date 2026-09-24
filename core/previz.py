"""Previz 2D, the Claude side: read each background picture once, lay out every shot of a script in one call, compose the layouts
and the storyboard with `core.layout`, and let Claude check the storyboard for continuity. Works with any `llm_runner` client
(`claude_cli` today, the Anthropic API later) — the calls go through `llm_runner.ask_json`.

Claude calls are kept few: one per background picture ever (cached by the picture's sha256 in `set_analyses`), one to lay out the
whole script, one to review the storyboard. Nothing here asks the person to approve anything; the storyboard is there to look at.

Files: <data>/<project>/layouts/S01.png (clean layout sent to the image model), S01_board.png (with names, for the sheet),
storyboard.png, review.json. Each scene keeps its shot in scenes.data["layout"] (+ "layout_people" for the image-model note).
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import assets, diag, layout
from .llm_runner import LlmError, ask_json, tagged
from .pipeline import Pipeline
from .prompts import _read

MAX_BACKGROUNDS_PER_CALL = 10          # pictures shown to Claude when laying out the script (llm_runner sends at most 12)


def layouts_dir(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), "layouts")


def layout_path(data_dir: str, project_id: int, idx: int, board: bool = False) -> str:
    """Same file name as core.layout.layout_reference reads."""
    return os.path.join(layouts_dir(data_dir, project_id), f"S{idx:02d}{'_board' if board else ''}.png")


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _note(p: Pipeline, project_id: Optional[int]):
    return lambda message: diag.record(p.conn, "previz", "warn", message, "bad_json_retry", project_id)


# ---- 1. background pictures ------------------------------------------------------------------------------------
def cached_analysis(conn, path: str) -> Optional[Dict]:
    row = conn.execute("SELECT data FROM set_analyses WHERE sha256=?", (_sha(path),)).fetchone()
    return json.loads(row["data"]) if row else None


def analyze_background(p: Pipeline, client, path: str, project_id: Optional[int] = None) -> Dict:
    """The set analysis of one background picture: from the cache, else one Claude call (then cached for every project)."""
    found = cached_analysis(p.conn, path)
    if found is not None:
        return found
    try:
        with tagged("set_analysis", project_id):
            obj, _, _ = ask_json(client, _read("prompts", "07_set_analysis.md"), layout.validate_set_analysis,
                                 [("Ảnh bối cảnh:", assets.thumbnail(path, 1280))], note=_note(p, project_id))
    except LlmError as e:
        diag.record(p.conn, "previz", "warn" if e.transient else "error", f"đọc ảnh nền lỗi: {e}", e.code, project_id)
        raise
    p.conn.execute("INSERT OR REPLACE INTO set_analyses (sha256, data, created_at) VALUES (?,?,?)",
                   (_sha(path), json.dumps(obj, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
    p.conn.commit()
    return obj


def scene_backgrounds(p: Pipeline, project_id: int, scene: Dict) -> List[Dict]:
    """Candidate background pictures of a scene: every picture of the place it is set in. [{id, path}]"""
    place = assets.scene_location(p.conn, project_id, scene)
    return [{"id": img["id"], "path": img["path"]} for img in (place or {}).get("images", []) if os.path.exists(img["path"])]


def _scenes(p: Pipeline, project_id: int) -> List[Dict]:
    rows = p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project_id,)).fetchall()
    return [dict(json.loads(r["data"] or "{}"), _id=r["id"], idx=r["idx"]) for r in rows]


# ---- 2. lay out the script --------------------------------------------------------------------------------------
def _validator(candidates: Dict[int, List[int]], casts: Dict[int, List[str]]):
    def check(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("shots"), list):
            raise layout.LayoutError("root: {\"shots\": [...]}")
        for shot in obj["shots"]:
            if not isinstance(shot, dict) or shot.get("idx") not in candidates:
                raise layout.LayoutError(f"shots: idx {shot.get('idx') if isinstance(shot, dict) else shot} is not a scene to lay out")
            if shot.get("background") not in candidates[shot["idx"]]:
                raise layout.LayoutError(f"scene {shot['idx']}: background must be one of {candidates[shot['idx']]}")
            layout.validate_shot_layout(shot, casts[shot["idx"]])
        return obj
    return check


def plan_layouts(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """Lay out every scene that has a place with pictures, compose its layout and the storyboard.
    Returns {"laid_out": [idx...], "skipped": [idx...] (no place picture), "moved": [(idx, name)...], "storyboard": path|None}."""
    scenes = _scenes(p, project_id)
    todo, skipped, pictures = [], [], {}
    for s in scenes:
        cands = scene_backgrounds(p, project_id, s)
        if not cands:
            skipped.append(s["idx"])
            continue
        todo.append((s, cands))
        for c in cands:
            pictures[c["id"]] = c["path"]
    if not todo:
        return {"laid_out": [], "skipped": skipped, "moved": [], "storyboard": None}
    analyses = {pid_: analyze_background(p, client, path, project_id) for pid_, path in pictures.items()}
    shown = list(pictures)[:MAX_BACKGROUNDS_PER_CALL]
    specs = [{"idx": s["idx"], "sequence": s.get("sequence"), "shot": s.get("shot", ""), "blocking": s.get("blocking", ""),
              "characters": s.get("characters") or [], "location": s.get("location", ""), "script": (s.get("text") or "")[:300],
              "backgrounds": [c["id"] for c in cands]} for s, cands in todo]
    backgrounds = {i: dict(analyses[i], image=f"ảnh {shown.index(i) + 1}" if i in shown else "không đính kèm") for i in pictures}
    prompt = (_read("prompts", "08_shot_layout.md") + "\n\n---\n\n# Ảnh nền ứng viên (id → phân tích)\n"
              + json.dumps(backgrounds, ensure_ascii=False, indent=1) + "\n\n# Các cảnh\n" + json.dumps(specs, ensure_ascii=False, indent=1))
    images = [(f"Ảnh {n} — ảnh nền id {i}:", assets.thumbnail(pictures[i], 900)) for n, i in enumerate(shown, 1)]
    candidates = {s["idx"]: [c["id"] for c in cands] for s, cands in todo}
    casts = {s["idx"]: [str(n) for n in s.get("characters") or []] for s, _ in todo}
    try:
        with tagged("layout", project_id):
            obj, _, _ = ask_json(client, prompt, _validator(candidates, casts), images, note=_note(p, project_id))
    except LlmError as e:
        diag.record(p.conn, "previz", "warn" if e.transient else "error", f"dựng layout lỗi: {e}", e.code, project_id)
        raise
    by_idx = {s["idx"]: s for s, _ in todo}
    laid_out, moved = [], []
    for shot in obj["shots"]:
        s = by_idx[shot["idx"]]
        moved += [(shot["idx"], m) for m in compose_scene(p, project_id, s, shot, pictures[shot["background"]],
                                                          analyses[shot["background"]], data_dir)]
        laid_out.append(shot["idx"])
    missing = [s["idx"] for s, _ in todo if s["idx"] not in laid_out]
    board = build_storyboard(p, project_id, data_dir)
    return {"laid_out": sorted(laid_out), "skipped": sorted(skipped + missing), "moved": moved, "storyboard": board}


def compose_scene(p: Pipeline, project_id: int, scene: Dict, shot: Dict, background: str, analysis: Dict, data_dir: str) -> List[str]:
    """Compose one scene's layout (clean + labelled) and keep the shot in the scene data. Returns the names whose feet had to be
    moved back onto the ground."""
    names = [pp["name"] for pp in shot.get("people") or []]
    linked = assets.link_characters(p.conn, project_id, names) if names else {}
    cutouts = {n: (a or {}).get("ref", {}).get("path") for n, a in linked.items()}
    if os.environ.get("PREVIZ_CUTOUT", "").strip() == "1":          # experiment: real cut-out figures instead of mannequins
        cutouts = {n: _deepix_cutout(p, project_id, path, data_dir) if path and layout._cutout(path) is None else path
                   for n, path in cutouts.items()}
    cutouts = {n: path for n, path in cutouts.items() if path and layout._cutout(path) is not None}
    from . import formats
    size = formats.canvas(formats.project_aspect(p.project(project_id)))       # the layout has the project's frame
    _, people = layout.compose(background, analysis, shot, cutouts, layout_path(data_dir, project_id, scene["idx"]), size=size)
    layout.compose(background, analysis, shot, cutouts, layout_path(data_dir, project_id, scene["idx"], board=True), size=size,
                   labels=True)
    data = {k: v for k, v in scene.items() if k not in ("_id", "idx")}
    data["layout"] = shot
    data["layout_people"] = [{"name": pp["name"], "color_index": pp["color_index"], "cutout": pp["name"] in cutouts} for pp in people]
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene["_id"]))
    p.conn.commit()
    return [pp["name"] for pp in people if pp["moved"]]


def build_storyboard(p: Pipeline, project_id: int, data_dir: str) -> Optional[str]:
    frames = []
    for s in _scenes(p, project_id):
        path = layout_path(data_dir, project_id, s["idx"], board=True)
        if s.get("layout") and os.path.exists(path):
            bits = [f"S{s['idx']:02d}", f"nhóm {s['sequence']}" if s.get("sequence") else "", s.get("shot", "")[:40],
                    "vẽ lại nền" if s["layout"].get("redraw") else ""]
            frames.append((path, " · ".join(b for b in bits if b)))
    if not frames:
        return None
    from . import formats
    cell = formats.spec(formats.project_aspect(p.project(project_id)))["cell"]
    return layout.storyboard(frames, os.path.join(layouts_dir(data_dir, project_id), "storyboard.png"), cell=cell)


# ---- 3. Claude checks the storyboard ------------------------------------------------------------------------------
def _check_review(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("ok"), bool) or not isinstance(obj.get("issues"), list):
        raise layout.LayoutError("root: {\"ok\": bool, \"issues\": [...]}")
    for i, issue in enumerate(obj["issues"]):
        if not isinstance(issue, dict) or not isinstance(issue.get("idx"), int) or not isinstance(issue.get("problem"), str):
            raise layout.LayoutError(f"issues[{i}]: {{idx, problem, fix}}")
    return obj


def review_storyboard(p: Pipeline, project_id: int, client, data_dir: str) -> Dict:
    """One Claude look at the whole storyboard for continuity (180° line, screen direction, jumps) and framing problems.
    Saved to layouts/review.json; nothing blocks on it."""
    board = os.path.join(layouts_dir(data_dir, project_id), "storyboard.png")
    if not os.path.exists(board):
        raise LlmError("no storyboard yet: lay out the scenes first", code="no_storyboard")
    scenes = [{"idx": s["idx"], "sequence": s.get("sequence"), "shot": s.get("shot", ""), "blocking": s.get("blocking", "")}
              for s in _scenes(p, project_id) if s.get("layout")]
    try:
        with tagged("storyboard_review", project_id):
            obj, _, _ = ask_json(client, _read("prompts", "09_storyboard_review.md") + "\n\n---\n\n# Các shot\n"
                                 + json.dumps(scenes, ensure_ascii=False, indent=1), _check_review,
                                 [("Storyboard:", board)], note=_note(p, project_id))
    except LlmError as e:
        diag.record(p.conn, "previz", "warn" if e.transient else "error", f"rà storyboard lỗi: {e}", e.code, project_id)
        raise
    with open(os.path.join(layouts_dir(data_dir, project_id), "review.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return obj


def last_review(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(os.path.join(layouts_dir(data_dir, project_id), "review.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _deepix_cutout(p: Pipeline, project_id: int, path: str, data_dir: str) -> Optional[str]:
    """Cached transparent PNG of a reference picture via Deepix cutout (PREVIZ_CUTOUT=1); None when it cannot be made."""
    import hashlib
    from .adapters import factory
    from .adapters.deepix import DeepixImageProvider, cutout
    try:
        with open(path, "rb") as f:
            digest = hashlib.sha1(f.read()).hexdigest()[:16]
        dest = os.path.join(data_dir, str(project_id), "cutouts", f"{digest}.png")
        if os.path.exists(dest):
            return dest
        provider = factory.image_provider()
        if not isinstance(provider, DeepixImageProvider):
            return None
        return cutout(provider, path, dest)
    except Exception as e:  # noqa: BLE001 - an experiment must never stop the layout
        diag.record(p.conn, "previz", "warn", f"tách nền Deepix lỗi, dùng ma-nơ-canh: {e}", "cutout", project_id)
        return None
