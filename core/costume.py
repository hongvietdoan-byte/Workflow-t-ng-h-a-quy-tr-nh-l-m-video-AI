"""Changing a character's outfit with pictures + text (no 3D file needed).

Two levels, both optional:
  * outfit pictures (assets.set_outfit): every scene sends the person's face picture + the outfit picture, and the note tells the
    image model to take the face/hair from one and the clothes from the other;
  * a character set (make_character_set): 2 full-body pictures of the person already wearing the new outfit (front + three-quarter),
    generated once. They become the person's reference pictures for this project (a project-only resource, linked through the same
    "reference picture comes from" choice as any other), so every scene then copies one consistent look. Nothing to approve: the set
    is used as soon as it exists, and the person can switch back in the Character Bible.
"""
import os
import time
from typing import Callable, Dict, List

from . import assets, spend_gate
from .pipeline import Pipeline
from .providers import ProviderError

VIEWS = (("front", "full body, front view, standing straight, arms relaxed at the sides"),
         ("three_quarter", "full body, three-quarter view turned slightly to the left, standing"))
PORTRAIT_SIZE = "1152x2048"          # Seedream 5.0 Pro: multiples of 16, inside its pixel bounds; a standing person fills it


def _refs(p: Pipeline, project_id: int, name: str) -> List[Dict]:
    linked = assets.link_characters(p.conn, project_id, [name]).get(name)
    refs = [{"path": img["path"], "label": linked["name"], "role": "character"} for img in (linked["refs"][:1] if linked else [])]
    label = linked["name"] if linked else name
    return refs + [{"path": img["path"], "label": label, "role": "outfit"} for img in assets.outfit_images(p.conn, project_id, name)[:2]]


def set_prompt(p: Pipeline, project_id: int, name: str, view: str, refs: List[Dict]) -> str:
    row = p.conn.execute("SELECT description, wardrobe FROM characters WHERE project_id=? AND name=?", (project_id, name)).fetchone()
    if row is None:
        raise KeyError(f"'{name}' is not in the Character Bible")
    wearing = f" Wearing: {row['wardrobe']}." if (row["wardrobe"] or "").strip() else ""
    text = (f"Character reference picture of {name}: {row['description']}.{wearing} {view}, the whole body from head to feet inside "
            "the frame, plain light grey studio background, soft even lighting, sharp details of face, hair and clothes, "
            "one person only, no text, no logo.")
    return (assets.reference_note(refs) + "Scene: " + text) if refs else text


def make_character_set(p: Pipeline, project_id: int, name: str, provider, data_dir: str, timeout: float = 600,
                       poll_every: float = 6, sleep: Callable[[float], None] = time.sleep) -> Dict:
    """Generate the 2 pictures, store them as a project resource "<NAME> · trang phục N", make it this character's reference and
    clear the separate outfit pictures (the set already wears the outfit). Returns {"asset_id", "paths"}. Costs 2 image credits."""
    refs = _refs(p, project_id, name)
    prompts = [(key, set_prompt(p, project_id, name, view, refs)) for key, view in VIEWS]
    info = getattr(provider, "usage_info", None)
    model, tier = info() if info is not None else (None, None)
    # S14.1: the set used to skip every money cap (trial round, the project's locked budget, a service out of credit) and was
    # recorded only after both sends — the gate checks both pictures before the first goes and records each one right after it.
    with spend_gate.spend(p.conn, "image", provider.name, project_id=project_id, model=model, tier=tier, units=len(VIEWS),
                          ledger_stage="character_set") as slot:
        slot.raise_if_over(f"Không tạo bộ ảnh nhân vật {name}")
        old_size = getattr(provider, "size", None)
        if old_size is not None:
            provider.size = PORTRAIT_SIZE
        tasks = []
        try:
            for key, prompt in prompts:
                tasks.append((key, slot.send(provider.submit, prompt, [r["path"] for r in refs])))
                slot.record()
        finally:
            if old_size is not None:
                provider.size = old_size
    folder = os.path.join(data_dir, str(project_id), "costumes")
    os.makedirs(folder, exist_ok=True)
    stem = assets.fold(name).replace(" ", "_") or "character"
    paths, waited = {}, 0.0
    while len(paths) < len(tasks):
        for key, task in tasks:
            if key in paths:
                continue
            status = provider.status(task)
            if status.state == "succeeded":
                paths[key] = provider.download(task, os.path.join(folder, f"{stem}_{key}_{int(time.time())}.png"))
            elif status.state == "failed" and not status.transient:
                raise ProviderError(f"character set picture failed: {status.error_message}", code=status.error_code or "failed")
        if len(paths) < len(tasks):
            if waited >= timeout:
                raise ProviderError("character set took too long; try again later", code="timeout", transient=True)
            sleep(poll_every)
            waited += poll_every
    game = p.project(project_id)["game"] or "FF"
    base = f"{name.upper()} · trang phục"
    n = 1 + p.conn.execute("SELECT COUNT(*) FROM assets WHERE project_id=? AND name LIKE ?", (project_id, base + "%")).fetchone()[0]
    asset_id = assets.create(p.conn, game, "character", f"{base} {n}", f"Bộ ảnh nhân vật {name} với trang phục mới (tự tạo)", "",
                             project_id, None)
    for key, _ in VIEWS:
        with open(paths[key], "rb") as f:
            assets.add_image(p.conn, asset_id, f"{key}.png", f.read())
    assets.attach(p.conn, project_id, asset_id)
    assets.set_character_link(p.conn, project_id, name, asset_id)
    assets.set_outfit(p.conn, project_id, name, None)
    return {"asset_id": asset_id, "paths": [paths[k] for k, _ in VIEWS]}
