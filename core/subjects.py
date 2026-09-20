"""Character <-> Seedance subject (Kho chủ thể) links stored on the Character Bible.

A character with an ACTIVE subject can be attached to Seedance video requests as a `reference_image`
(`asset://` uri), which lets the character keep its look and lowers the chance of a risk-control block.
Copyright: Free Fire (FF) has a signed agreement with Clip AI, so an active FF subject also counts as copyright
reviewed. AOV, DF and other games: real-person review only, blocks are still possible.
"""
from typing import Dict, List, Optional

from .pipeline import Pipeline

# key -> (label, covered by the signed copyright agreement)
GAMES: Dict[str, tuple] = {
    "FF": ("Free Fire (FF)", True),
    "AOV": ("AOV", False),
    "DF": ("DF", False),
    "OTHER": ("Game khác", False),
}
STATUS_LABEL = {None: "chưa có", "submitted": "đã gửi", "processing": "đang xử lý", "active": "active ✓",
                "failed": "lỗi"}
_IMAGE_CAP = {"seedance-2.5": 29, "default": 8}  # reference images left after the first-frame image


def is_covered(game: str) -> bool:
    return GAMES.get(game, GAMES["OTHER"])[1]


def link(pipeline: Pipeline, project_id: int, character: str, asset: Dict) -> None:
    """Attach a library asset (dict from the library) to a character."""
    if not asset.get("asset_id"):
        raise ValueError("asset has no asset_id")
    n = pipeline.conn.execute(
        "UPDATE characters SET subject_asset_id=?, subject_asset_uri=?, subject_status=?, subject_name=?"
        " WHERE project_id=? AND name=?",
        (asset["asset_id"], asset.get("asset_uri"), asset.get("provider_status"), asset.get("name"),
         project_id, character)).rowcount
    if n == 0:
        raise KeyError(f"character '{character}' does not exist")
    pipeline.conn.commit()


def unlink(pipeline: Pipeline, project_id: int, character: str) -> None:
    """Forget the link (the asset itself stays in the library)."""
    pipeline.conn.execute("UPDATE characters SET subject_asset_id=NULL, subject_asset_uri=NULL, subject_status=NULL,"
                          " subject_name=NULL WHERE project_id=? AND name=?", (project_id, character))
    pipeline.conn.commit()


def refresh(pipeline: Pipeline, project_id: int, library) -> int:
    """Re-read the status of every linked subject that is not active yet. Returns how many became active."""
    became = 0
    rows = pipeline.conn.execute("SELECT name, subject_asset_id FROM characters WHERE project_id=?"
                                 " AND subject_asset_id IS NOT NULL AND COALESCE(subject_status,'')!='active'",
                                 (project_id,)).fetchall()
    for r in rows:
        asset = library.get(r["subject_asset_id"])
        if asset is not None:
            link(pipeline, project_id, r["name"], asset)
            became += asset.get("provider_status") == "active"
    return became


def reference_cap(model: Optional[str]) -> int:
    return _IMAGE_CAP["seedance-2.5"] if model and "2-5" in model or model == "seedance-2.5" else _IMAGE_CAP["default"]


def usable_for_scene(pipeline: Pipeline, scene_id: int, limit: int) -> List[Dict]:
    """Active subjects of the characters that appear in the scene, in the order the scene lists them."""
    import json
    scene = pipeline.conn.execute("SELECT project_id, data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    cast = (json.loads(scene["data"] or "{}").get("characters") or []) if scene else []
    out = []
    for name in cast:
        row = pipeline.conn.execute(
            "SELECT name, subject_asset_uri FROM characters WHERE project_id=? AND name=? AND subject_status='active'"
            " AND subject_asset_uri IS NOT NULL", (scene["project_id"], name)).fetchone()
        if row:
            out.append({"name": row["name"], "uri": row["subject_asset_uri"]})
    return out[:limit]
