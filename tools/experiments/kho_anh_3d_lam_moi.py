"""Kho #263 / #265: refresh the 3D render pictures after a re-render (30/09: warm sunny daylight). The pictures of the two places are
all 3D renders (kho_anh_3d_2026_09_29.py); each is backed up, removed and added again from the new render with the same role and note.
Run from the repo root after tools/tower_pack.py has rendered both packs again."""
import importlib.util
import os
import shutil
import sys

sys.path.insert(0, os.getcwd())
from core import assets  # noqa: E402
from core.db import connect  # noqa: E402

spec = importlib.util.spec_from_file_location("kho0", os.path.join(os.path.dirname(os.path.abspath(__file__)), "kho_anh_3d_2026_09_29.py"))
src = open(spec.origin, encoding="utf-8").read()
NEW = {}
exec(src[src.index("NEW = {"):src.index("c = connect(DB)")], {"T": r"D:\AI-Video-Output\2026-09-29_bo-boi-canh-thap-chinh-thuc",
                                                              "C": r"D:\AI-Video-Output\2026-09-29_bo-boi-canh-cong-troi"}, NEW)
NEW, NOTE = NEW["NEW"], "render 3D Blender 5.0.1 — file 3D chính thức của game, ánh sáng ngày tông ấm trời nắng (2026-09-30)"
BACKUP = r"D:\AI-Video-Pipeline\data\backup\kho_anh_3d_ban_truoc_2026-09-30"
c = connect(r"D:\AI-Video-Pipeline\data\manifest.sqlite")
for aid, (folder, items) in NEW.items():
    for name, _, _ in items:
        assert os.path.exists(os.path.join(folder, name)), name
    os.makedirs(os.path.join(BACKUP, str(aid)), exist_ok=True)
    for r in c.execute("SELECT id, path FROM asset_images WHERE asset_id=?", (aid,)).fetchall():
        path = assets.resolve(r["path"])
        if path and os.path.exists(path):
            shutil.copy2(path, os.path.join(BACKUP, str(aid), f"{r['id']}_{os.path.basename(path)}"))
        assets.remove_image(c, r["id"])
    for name, role, label in items:
        with open(os.path.join(folder, name), "rb") as fh:
            assets.add_image(c, aid, f"3d_{name}", fh.read(), status="approved", role=role, look="ingame", variant=f"{NOTE}; {label}")
    print(aid, [(r["id"], r["role"]) for r in c.execute("SELECT id, role FROM asset_images WHERE asset_id=?", (aid,))])
