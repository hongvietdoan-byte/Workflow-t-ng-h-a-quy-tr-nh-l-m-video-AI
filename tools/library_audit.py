"""Rà soát chất lượng Kho tài nguyên (CHỈ ĐỌC, 0 USD) — ảnh hưởng trực tiếp khâu chọn ảnh tham chiếu rồi gen ảnh.

    py tools/library_audit.py                 in báo cáo markdown ra màn hình
    py tools/library_audit.py --out docs/x.md ghi ra file
    py tools/library_audit.py --db D:/AI-Video-Pipeline/data/manifest.sqlite --repo D:/AI-Video-Pipeline   (chạy từ worktree)

Kiểm: file mất / không đọc được · ảnh nhỏ · trùng · vai trò chưa gắn · hồ sơ chuẩn (đã duyệt / nháp / chưa có) · mục trống mô tả ·
mục tên rác · ảnh chung giữa nhiều mục · ảnh vuông / nhỏ có thể bị chọn làm ảnh tham chiếu."""
import argparse
import collections
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets  # noqa: E402

SMALL_SIDE = 400          # shorter side below this is too small to pin a face for a 1080p picture
JUNK_NAME = re.compile(r"^\d+$")


def audit(conn, game: str = "FF") -> dict:
    from PIL import Image
    rows = conn.execute("SELECT i.id, i.path, i.role, i.status, i.sha256, i.src_path, a.id AS aid, a.kind, a.name, a.profile, a.description"
                        " FROM asset_images i JOIN assets a ON a.id=i.asset_id WHERE a.game=? AND i.status IS NOT 'removed'", (game,)).fetchall()
    out = {"missing": [], "unreadable": [], "small": collections.Counter(), "no_role": collections.Counter(), "shared": [], "per_kind": {}}
    sizes = {}
    for r in rows:
        k = out["per_kind"].setdefault(r["kind"], {"approved": 0, "pending": 0, "redundant": 0})
        k["approved" if r["status"] == "approved" else "redundant" if r["status"] == "redundant" else "pending"] += 1
        path = assets.resolve(r["path"])
        if not path or not os.path.exists(path):
            out["missing"].append((r["name"], r["id"]))
            continue
        try:
            with Image.open(path) as im:
                sizes[r["id"]] = im.size
        except Exception:  # noqa: BLE001
            out["unreadable"].append((r["name"], r["id"]))
            continue
        if min(sizes[r["id"]]) < SMALL_SIDE:
            out["small"][r["kind"]] += 1
        if r["status"] == "approved" and not r["role"]:
            out["no_role"][r["kind"]] += 1
    sha = collections.defaultdict(set)
    for r in rows:
        if r["sha256"]:
            sha[r["sha256"]].add(r["name"])
    out["shared"] = [sorted(v) for v in sha.values() if len(v) > 1]
    assets_ = conn.execute("SELECT id, kind, name, description, profile FROM assets WHERE game=?", (game,)).fetchall()
    out["junk_names"] = [a["name"] for a in assets_ if JUNK_NAME.match(a["name"].strip())]
    out["short_desc"] = collections.Counter(a["kind"] for a in assets_ if len(a["description"] or "") < 40)
    out["kinds"] = collections.Counter(a["kind"] for a in assets_)
    prof = collections.Counter()
    for a in assets_:
        if a["kind"] != "character":
            continue
        p = json.loads(a["profile"]) if a["profile"] else {}
        prof["đã duyệt" if p.get("approved") else "nháp" if p else "chưa có"] += 1
        if p and not p.get("height_m"):
            prof["thiếu chiều cao"] += 1
    out["profiles"] = prof
    usable = collections.defaultdict(int)             # approved pictures a picture model could really use as a person reference
    for r in rows:
        if r["kind"] == "character" and r["status"] == "approved" and r["id"] in sizes:
            w, h = sizes[r["id"]]
            if min(w, h) >= SMALL_SIDE and h >= w * 1.05 and r["role"] not in ("design_sheet", "related"):
                usable[r["aid"]] += 1
    out["char_no_usable_ref"] = [a["name"] for a in assets_ if a["kind"] == "character" and not usable[a["id"]]]
    out["sources_mixed"] = sum(1 for a in assets_ if a["kind"] == "character" and sum(
        m in (a["description"] or "") for m in assets.BLOCK_MARKS) > 1)
    return out


def report(o: dict) -> str:
    L = ["# Rà soát Kho tài nguyên (tự động, chỉ đọc)", ""]
    L.append("| Loại | Mục | Ảnh đã duyệt | Ảnh chờ | Ảnh < %d px | Ảnh đã duyệt chưa có vai trò | Mô tả < 40 ký tự |" % SMALL_SIDE)
    L.append("|---|---|---|---|---|---|---|")
    for kind, n in o["kinds"].most_common():
        k = o["per_kind"].get(kind, {"approved": 0, "pending": 0, "redundant": 0})
        L.append(f"| {kind} | {n} | {k['approved']} | {k['pending']} | {o['small'][kind]} | {o['no_role'][kind]} | {o['short_desc'][kind]} |")
    L += ["", f"- File mất: {len(o['missing'])} · không đọc được: {len(o['unreadable'])}",
          f"- Hồ sơ nhân vật: {dict(o['profiles'])}",
          f"- Nhân vật KHÔNG có ảnh đủ dùng làm tham chiếu người (≥ {SMALL_SIDE} px, dọc, không phải bảng thiết kế): {len(o['char_no_usable_ref'])}"
          + (" — " + ", ".join(o["char_no_usable_ref"][:20]) if o["char_no_usable_ref"] else ""),
          f"- Mục tên rác (chỉ số): {', '.join(o['junk_names']) or '—'}",
          f"- Ảnh dùng chung cho nhiều mục: {len(o['shared'])} nhóm" + (f" (vd {o['shared'][0]})" if o["shared"] else ""),
          f"- Nhân vật có ≥ 2 khối tự động trong mô tả (cần luật nguồn): {o['sources_mixed']}"]
    return "\n".join(L)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--repo", default=None, help="thư mục gốc chứa data/assets (khi chạy từ worktree)")
    ap.add_argument("--game", default="FF")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.repo:
        assets.REPO = a.repo
    conn = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    text = report(audit(conn, a.game))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
