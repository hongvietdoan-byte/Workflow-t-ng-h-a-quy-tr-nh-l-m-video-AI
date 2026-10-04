"""T1 — hồ sơ chuẩn cho MỌI nhân vật trong Kho (kế hoạch V4 GĐ1; khuôn = 3 hồ sơ KELLY / KENTA / MAXIM người dùng đã duyệt 2026-09-25).

    py tools/draft_profiles.py                     chỉ xem (miễn phí, không ghi gì): ảnh gần như trùng, ảnh chưa có vai trò, mục có
                                                   nhiều ngoại hình, nhân vật chưa có hồ sơ
    py tools/draft_profiles.py --apply             ghi phần miễn phí: ảnh gần như trùng → "chờ duyệt" (KHÔNG xóa), đoán vai trò ảnh theo tỉ lệ
    py tools/draft_profiles.py --draft --limit 5   ƯỚC TÍNH tiền Claude để soạn nháp hồ sơ cho 5 nhân vật (không gọi gì)
    py tools/draft_profiles.py --draft --limit 5 --yes   gọi Claude (có sổ chi + trần Claude): 1 lượt / nhân vật, lưu NHÁP (chưa duyệt)

Thứ tự soạn: nhân vật đã dùng trong dự án → nhân vật còn lại (thú cưng sau cùng). Nháp không bao giờ tự duyệt — người duyệt ở
⚙ → 📁 Kho → 📋 Hồ sơ chuẩn. Luật tuổi (người dùng chốt 2026-09-25): KHÔNG ghi số tuổi dưới 18 — tả "young, not yet 20".
"""
import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets  # noqa: E402

NEAR_SAME = 6                   # average-hash bits that may differ for two pictures to count as "the same picture"
LOOK_WORDS = re.compile(r"\b(ob\s?\d+|skin|awaken(ed)?|rework|phiên bản|bản mới|bản cũ|v\d)\b", re.I)
EST_USD_PER_CHARACTER = 0.02    # ~2 pictures + a short answer on the API (plan T1 estimate; measured after the first calls)
AGE_RULE = ("Never write an age number under 18 (the picture models refuse it). For a character under 18 write 'young, not yet 20' "
            "and keep the look youthful; adults may keep their age.")


def ahash(path: str) -> Optional[int]:
    """64-bit average hash of a picture (Pillow): near-identical pictures differ in a few bits."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            small = im.convert("L").resize((8, 8))
            px = list(small.getdata())
    except Exception:  # noqa: BLE001 - unreadable picture: no hash
        return None
    avg = sum(px) / len(px)
    return sum(1 << i for i, v in enumerate(px) if v >= avg)


def near_duplicates(images: List[Dict]) -> List[Dict]:
    """Pictures of one entry that repeat an earlier one (kept: the first; the later ones are listed)."""
    seen, out = [], []
    for img in images:
        h = ahash(assets.resolve(img["path"]) or img["path"])
        if h is None:
            continue
        twin = next((s for s in seen if bin(s[0] ^ h).count("1") <= NEAR_SAME), None)
        if twin is not None:
            out.append({"image": img, "same_as": twin[1]})
        else:
            seen.append((h, img))
    return out


def looks_split(characters: List[Dict]) -> List[Dict]:
    """Entries that are another look of an existing character ("Kenta OB55", "Kelly skin …"): the person picks the standard look
    or keeps them as separate entries (like KENTA = OB55)."""
    by_name = {assets.fold(c["name"]): c for c in characters}
    out = []
    for c in characters:
        if not LOOK_WORDS.search(c["name"]):
            continue
        base = assets.fold(LOOK_WORDS.sub("", c["name"])).strip(" -·")
        if base and base in by_name and by_name[base]["id"] != c["id"]:
            out.append({"entry": c, "base": by_name[base]})
    return out


def used_in_projects(conn) -> set:
    rows = conn.execute("SELECT DISTINCT asset_id FROM project_assets").fetchall()
    return {r[0] for r in rows}


def report(conn, game: str) -> Dict:
    chars = [c for c in assets.list_assets(conn, game, "character") + assets.list_assets(conn, game, "pet")]
    dups, unlabelled, missing = [], [], []
    for c in chars:
        imgs = [i for i in c["images"] + c.get("pending", []) if i.get("path")]
        for d in near_duplicates(imgs):
            dups.append({"entry": c["name"], **d})
        for i in c["images"]:
            if not i.get("role"):
                role = assets.guess_role(assets.resolve(i["path"]) or i["path"], c["kind"])
                unlabelled.append({"entry": c["name"], "image": i, "guess": role})
        if not assets.get_profile(conn, c["id"]).get("approved") and not assets.get_profile(conn, c["id"]).get("identity"):
            missing.append(c)
    used = used_in_projects(conn)
    missing.sort(key=lambda c: (c["id"] not in used, c["kind"] == "pet", c["name"]))
    return {"characters": chars, "duplicates": dups, "unlabelled": unlabelled, "looks": looks_split(chars), "missing": missing}


def apply_free(conn, rep: Dict) -> Dict:
    """Near-duplicates back to 'pending' (never deleted), guessed roles written where a picture had none."""
    held = 0
    for d in rep["duplicates"]:
        if d["image"].get("status") != "pending":
            assets.set_image_meta(conn, d["image"]["id"], status="pending")
            held += 1
    roles = 0
    for u in rep["unlabelled"]:
        if u["guess"]:
            assets.set_image_meta(conn, u["image"]["id"], role=u["guess"])
            roles += 1
    return {"held": held, "roles": roles}


def draft_prompt(entry: Dict) -> str:
    keys = ", ".join(assets.PROFILE_KEYS)
    return ("You write the STANDARD PROFILE of a Free Fire character for picture/video models, from its reference pictures (the pictures "
            "are the truth — describe what you SEE, never guess left/right or colours you cannot see). Same shape as the approved "
            "KELLY / KENTA / MAXIM profiles: identity (one sentence: who + the 3-5 things that identify them), must_keep (every "
            "visible detail that must never change: hair, face, each garment with colour, accessories, which arm/side), may_change "
            "(pose, expression, camera, lighting, what they hold), forbidden (the typical mistakes: other outfits, wrong colours, "
            "old looks), height_m (from the design sheet if shown, else null), build. " + AGE_RULE +
            f"\n\nCharacter: {entry['name']}\nLibrary description: {entry.get('description') or '—'}\n\n"
            f"Answer ONE JSON object with the keys {keys}. English.")


def _check(obj) -> None:
    from core import llm_io
    if not isinstance(obj, dict) or not all(k in obj for k in ("identity", "must_keep", "forbidden")):
        raise llm_io.SchemaError("root: {identity, must_keep, may_change, forbidden, height_m, build}")
    if re.search(r"\b(1[0-7]|[1-9])[- ]?(year[- ]old|yo)\b", json.dumps(obj), re.I):
        raise llm_io.SchemaError("an age under 18 is written — use 'young, not yet 20' instead")


def draft(conn, entries: List[Dict], client) -> List[Dict]:
    from core import llm_runner
    out = []
    for c in entries:
        refs = assets.best_references(c, limit=2)
        images = [(f"{c['name']} — ảnh {i + 1}", assets.thumbnail(r["path"], 900)) for i, r in enumerate(refs)]
        with llm_runner.tagged("profile_draft"):
            obj = llm_runner.ask_json(client, draft_prompt(c), _check, images)[0]
        saved = assets.set_profile(conn, c["id"], obj, approved=False)              # a draft: never approved here
        out.append({"entry": c["name"], "profile": saved})
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--game", default="FF")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--skip", default="", help="bỏ các mục này (tên, cách nhau bằng dấu phẩy)")
    ap.add_argument("--no-pets", action="store_true", help="bỏ thú cưng (người dùng 02/10: chỉ làm hồ sơ nhân vật)")
    ap.add_argument("--only", default="", help="chỉ soạn các nhân vật này (tên, cách nhau bằng dấu phẩy)")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.from_args(a, "draft_profiles").start()
    from core.db import connect
    conn = connect(a.db)
    rep = report(conn, a.game)
    print(f"{len(rep['characters'])} nhân vật/thú cưng · {len(rep['duplicates'])} ảnh gần như trùng · "
          f"{len(rep['unlabelled'])} ảnh chưa có vai trò ({sum(1 for u in rep['unlabelled'] if u['guess'])} đoán được) · "
          f"{len(rep['looks'])} mục là ngoại hình khác · {len(rep['missing'])} chưa có hồ sơ")
    for d in rep["duplicates"][:30]:
        print(f"  trùng: {d['entry']} — ảnh {d['image']['id']} giống ảnh {d['same_as']['id']}")
    for lk in rep["looks"]:
        print(f"  ngoại hình khác: “{lk['entry']['name']}” của “{lk['base']['name']}” — chọn ngoại hình chuẩn hoặc giữ 2 mục")
    if a.apply:
        print("đã ghi:", apply_free(conn, rep))
    if a.draft:
        skip = {n.strip().lower() for n in a.skip.split(",") if n.strip()}
        rep["missing"] = [c for c in rep["missing"] if c["images"] and c["name"].lower() not in skip]   # no picture = nothing to describe
        if a.no_pets:
            rep["missing"] = [c for c in rep["missing"] if c["kind"] != "pet"]
        names = {n.strip().lower() for n in a.only.split(",") if n.strip()}
        todo = [c for c in rep["missing"] if c["name"].lower() in names] if names else rep["missing"][:max(a.limit, 0)]
        print(f"soạn nháp {len(todo)} hồ sơ: " + ", ".join(c["name"] for c in todo)
              + f"\nƯớc tính ≈ ${EST_USD_PER_CHARACTER * len(todo):.2f} Claude API (tính vào trần Claude, ⚙ → 💵)")
        if not a.yes:
            print("(chưa gọi Claude — thêm --yes để chạy)")
            return
        from core import budget, llm_runner
        from core.adapters.check import load_dashboard_env
        load_dashboard_env()
        stop = budget.check_llm(conn)
        if stop:
            sys.exit(stop)
        client = llm_runner.client_from_env(ledger=a.db)
        if client is None:
            sys.exit("Chưa cấu hình Claude API (dashboard.env).")
        for r in draft(conn, todo, client):
            print(f"  nháp: {r['entry']} — {r['profile'].get('identity', '')[:120]}")


if __name__ == "__main__":
    main()
