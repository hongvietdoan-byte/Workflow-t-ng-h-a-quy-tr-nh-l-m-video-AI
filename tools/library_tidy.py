"""Dọn Kho tài nguyên (người dùng 02/10/2026) — 0 USD, mặc định CHỈ XEM; thêm --apply mới ghi. Không xóa file ảnh nào ở bước nhân vật.

    py tools/library_tidy.py characters [--apply]    A: gắn vai trò ảnh nhân vật theo kích thước + nguồn; ảnh trùng / thừa / icon → "ảnh thừa"
    py tools/library_tidy.py locations [--apply]     D: xem mục địa điểm tên rác + ảnh dùng chung giữa đảo và khu vực

Chạy từ worktree: thêm --db D:/AI-Video-Pipeline/data/manifest.sqlite --repo D:/AI-Video-Pipeline.

Luật nhân vật (chỉ ảnh đã duyệt CHƯA có vai trò — ảnh người đã gắn tay như Kelly / Kenta / Maxim / Orion không đụng tới):
  - bảng nhiều góc (composite) → design_sheet;
  - cạnh dài ≤ 150 px (icon đầu) → "ảnh thừa" (quá nhỏ làm tham chiếu);
  - cùng một bức ở nhiều cỡ / nhập hai lần (so khung 22×40 trên nền xám) → giữ bản lớn nhất, các bản kia → "ảnh thừa";
  - còn lại: cao ≥ 700 px → full_body; nhỏ hơn → half_body.
"ảnh thừa" (status redundant) = pipeline không dùng, KHÔNG nằm trong hộp 📥 Ảnh chờ duyệt (khỏi bị "Duyệt cả" duyệt nhầm); không xóa file."""
import argparse
import collections
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets  # noqa: E402

ICON_SIDE = 150
SAME_ART = 2.0            # mean grey-level difference of the 22×40 signatures below which two pictures are the same art


def _signature(path: str):
    import numpy as np
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
        bg.alpha_composite(im)
        return np.array(bg.convert("RGB").resize((22, 40)), dtype=float)


def plan_characters(conn, game: str = "FF") -> dict:
    """{image_id: {"role": …, "status": …, "why": …}} for approved, role-less pictures of characters."""
    import numpy as np
    from PIL import Image
    plan, per = {}, collections.defaultdict(list)
    rows = conn.execute("SELECT i.id, i.path, i.role, i.status, a.id AS aid, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id"
                        " WHERE a.game=? AND a.kind='character' AND i.status='approved' ORDER BY a.name, i.sort, i.id", (game,)).fetchall()
    for r in rows:
        per[r["aid"]].append(r)
    for aid, imgs in per.items():
        curated = any(i["role"] for i in imgs)                  # the person (or a tool) already labelled this character: leave it
        if curated:
            continue
        info = []
        for i in imgs:
            p = assets.resolve(i["path"])
            try:
                with Image.open(p) as im:
                    w, h = im.size
                info.append({"id": i["id"], "path": p, "w": w, "h": h, "name": i["name"]})
            except Exception:  # noqa: BLE001
                continue
        keep = []
        for x in sorted(info, key=lambda x: -(x["w"] * x["h"])):
            if max(x["w"], x["h"]) <= ICON_SIDE:
                plan[x["id"]] = {"status": "redundant", "why": "icon nhỏ"}
                continue
            if assets._is_composite_sheet((x["w"], x["h"])):
                plan[x["id"]] = {"role": "design_sheet", "why": "bảng nhiều góc"}
                continue
            sig = _signature(x["path"])
            twin = next((k for k in keep if float(np.abs(k["sig"] - sig).mean()) < SAME_ART), None)
            if twin:
                plan[x["id"]] = {"status": "redundant", "why": f"trùng ảnh #{twin['id']}"}
                continue
            x["sig"] = sig
            keep.append(x)
            plan[x["id"]] = {"role": "full_body" if x["h"] >= 700 else "half_body", "why": f"{x['w']}×{x['h']}"}
    return plan


def apply_characters(conn, plan: dict) -> dict:
    n = collections.Counter()
    for iid, p in plan.items():
        if p.get("role"):
            assets.set_image_meta(conn, iid, role=p["role"])
            n["role:" + p["role"]] += 1
        if p.get("status"):
            assets.set_image_meta(conn, iid, status=p["status"])
            n["redundant"] += 1
    return dict(n)


def plan_locations(conn, game: str = "FF") -> dict:
    """junk: places named by a bare number (map screenshots from a folder, never used by a project, no description);
    shared: a picture stored under an island AND under one of its areas — the island's copy is held back (the area owns it)."""
    junk = [r for r in conn.execute("SELECT a.id, a.name FROM assets a WHERE a.game=? AND a.kind='location' AND TRIM(a.name) GLOB '[0-9]*'"
                                    " AND NOT EXISTS (SELECT 1 FROM project_assets p WHERE p.asset_id=a.id)", (game,)).fetchall()
            if r["name"].strip().isdigit()]
    groups = collections.defaultdict(list)
    for r in conn.execute("SELECT i.id, i.sha256, i.status, a.id AS aid, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id"
                          " WHERE a.game=? AND a.kind='location' AND i.sha256 IS NOT NULL AND i.status='approved'", (game,)):
        groups[r["sha256"]].append(r)
    held = []
    for g in groups.values():
        if len({x["aid"] for x in g}) < 2:
            continue
        area = [x for x in g if x["name"].startswith("Khu vực")]
        if area:
            held += [x["id"] for x in g if not x["name"].startswith("Khu vực")]
    return {"junk": [dict(j) for j in junk], "held": held}


def apply_locations(conn, plan: dict, backup_dir: str) -> dict:
    import shutil
    os.makedirs(backup_dir, exist_ok=True)
    for j in plan["junk"]:
        for r in conn.execute("SELECT path FROM asset_images WHERE asset_id=?", (j["id"],)).fetchall():
            src = assets.resolve(r["path"])
            if src and os.path.exists(src):
                shutil.copy2(src, os.path.join(backup_dir, f"{j['name']}_{os.path.basename(src)}"))
        assets.delete(conn, j["id"])
    for iid in plan["held"]:
        assets.set_image_meta(conn, iid, status="redundant")
    return {"deleted": len(plan["junk"]), "held": len(plan["held"])}



def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["characters", "locations"])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--repo", default=None)
    ap.add_argument("--game", default="FF")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.repo:
        assets.REPO = a.repo
    from core.db import connect
    conn = connect(a.db)
    if a.what == "characters":
        plan = plan_characters(conn, a.game)
        c = collections.Counter(p.get("role") or p.get("status") for p in plan.values())
        print(f"{len(plan)} ảnh sẽ đổi:", dict(c))
        why = collections.Counter(p["why"].split(" #")[0] if p.get("status") else "" for p in plan.values())
        print("lý do chờ duyệt:", {k: v for k, v in why.items() if k})
        if a.apply:
            print("đã ghi:", apply_characters(conn, plan))
        else:
            print("(chỉ xem — thêm --apply để ghi)")
    else:
        plan = plan_locations(conn, a.game)
        print(f"mục tên rác sẽ xóa ({len(plan['junk'])}):", ", ".join(j["name"] for j in plan["junk"]))
        print(f"ảnh của đảo trùng ảnh của khu vực → ảnh thừa: {len(plan['held'])}")
        if a.apply:
            print("đã ghi:", apply_locations(conn, plan, os.path.join(os.path.dirname(a.db), "backup", "library_tidy_2026-10-02")))
        else:
            print("(chỉ xem — thêm --apply để ghi)")


if __name__ == "__main__":
    main()
