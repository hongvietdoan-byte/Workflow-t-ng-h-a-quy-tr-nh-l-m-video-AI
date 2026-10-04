"""Experiments kept apart from the main pipeline (their results never enter the final cut automatically).

- Kling 3.0 Omni multi-shot: one generation for a whole sequence of scenes (up to 15 s), to compare continuity with scene-by-scene
  clips. Uses the approved first image of the sequence and each scene's approved motion prompt.
Results are listed in <data>/<project>/experiments/experiments.json.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List

from .pipeline import Pipeline
from .providers import ProviderError


def _dir(data_dir: str, project_id: int) -> str:
    path = os.path.join(data_dir, str(project_id), "experiments")
    os.makedirs(path, exist_ok=True)
    return path


def load(data_dir: str, project_id: int) -> List[Dict]:
    try:
        with open(os.path.join(_dir(data_dir, project_id), "experiments.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(data_dir: str, project_id: int, items: List[Dict]) -> None:
    with open(os.path.join(_dir(data_dir, project_id), "experiments.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def sequences(p: Pipeline, project_id: int) -> Dict[int, List[Dict]]:
    """sequence -> its scenes that have an approved image and an approved motion prompt (candidates for a multi-shot try)."""
    out: Dict[int, List[Dict]] = {}
    for r in p.conn.execute(
            "SELECT s.id, s.idx, s.data, m.motion_prompt, m.duration_sec, (SELECT j.id FROM jobs j WHERE j.scene_id=s.id AND "
            "j.type='image_gen' AND j.state='approved' ORDER BY j.id DESC LIMIT 1) AS jid FROM scenes s JOIN motion_prompts m ON "
            "m.scene_id=s.id WHERE s.project_id=? AND m.state='approved' ORDER BY s.idx", (project_id,)):
        seq = json.loads(r["data"] or "{}").get("sequence")
        if seq and r["jid"]:
            out.setdefault(seq, []).append(dict(r))
    return {k: v for k, v in out.items() if len(v) >= 2}


MODEL = "kling-v3-omni"


def _tier() -> str:
    return os.environ.get("CLIPAI_KLING_MODE", "pro")


def _plan(p: Pipeline, project_id: int, sequence: int):
    """The scenes, the per-scene shots (3-15 s each, 15 s in all) and the summed length one multi-shot try would send."""
    scenes = sequences(p, project_id).get(sequence)
    if not scenes:
        raise ValueError(f"nhóm cảnh {sequence} chưa đủ 2 cảnh có ảnh + motion prompt đã duyệt")
    shots, total = [], 0
    for s in scenes:
        d = min(max(int(round(s["duration_sec"] or 5)), 3), 15 - total)
        if d < 3:
            break
        shots.append({"prompt": s["motion_prompt"], "duration": d})
        total += d
    return scenes, shots, total


def estimate(p: Pipeline, project_id: int, sequence: int) -> Dict:
    """Seconds and USD of one multi-shot try (usd None when the model has no price), for the confirm box."""
    from .cost import clip_price, load_pricing
    _, _, total = _plan(p, project_id, sequence)
    return {"seconds": total, "usd": clip_price(load_pricing(), MODEL, _tier(), total)}


def kling_multishot(p: Pipeline, project_id: int, sequence: int, provider, data_dir: str) -> Dict:
    """Send one Kling multi-shot generation for the sequence (costs credit like one clip of the summed length, max 15 s).
    Goes through the money gate (core.spend_gate) like every clip: refused (ValueError, nothing sent) by the trial cap or the
    project's locked budget; PipelinePaused when the project is paused."""
    from . import formats, spend_gate
    scenes, shots, total = _plan(p, project_id, sequence)
    first = os.path.join(data_dir, str(project_id), "images", f"job_{scenes[0]['jid']}.png")
    aspect = formats.project_aspect(p.project(project_id))
    kwargs = {"multi_prompt": shots}
    if aspect:
        kwargs["aspect_ratio"] = formats.spec(aspect)["clip"]
    # limit check + submission + ledger entry as one step (S14.1: the gate adds the project's locked budget, a paused project and
    # 'out_of_credit' → halt)
    with spend_gate.spend(p.conn, "video", provider.name, project_id=project_id, model=MODEL, tier=_tier(), units=total,
                          ledger_stage="kling_multishot") as slot:
        slot.raise_if_over("Không gửi thử nghiệm multi-shot")
        task = slot.send(provider.submit, first, shots[0]["prompt"], None, total, "kling", **kwargs)
        slot.record()
    items = load(data_dir, project_id)
    entry = {"kind": "kling_multishot", "sequence": sequence, "scenes": [s["idx"] for s in scenes[:len(shots)]], "seconds": total,
             "external_id": task, "state": "running", "file": None, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    items.append(entry)
    _save(data_dir, project_id, items)
    return entry


def refresh(provider, data_dir: str, project_id: int) -> int:
    """Poll the running experiments once, download finished ones. Returns how many finished now."""
    items = load(data_dir, project_id)
    done = 0
    for e in items:
        if e["state"] != "running":
            continue
        try:
            status = provider.status(e["external_id"])
            if status.state == "succeeded":
                dest = os.path.join(_dir(data_dir, project_id), f"multishot_seq{e['sequence']}_{len(items)}_{e['external_id'].split(':')[-1]}.mp4")
                e["file"] = provider.download(e["external_id"], dest)
                e["state"] = "succeeded"
                done += 1
            elif status.state == "failed":
                e["state"], e["message"] = "failed", status.error_message
        except ProviderError as ex:
            if not ex.transient:
                e["state"], e["message"] = "failed", str(ex)
    _save(data_dir, project_id, items)
    return done
