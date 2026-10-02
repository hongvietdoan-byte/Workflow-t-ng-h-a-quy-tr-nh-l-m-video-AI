"""B — Claude NHÌN ảnh nhân vật trong Kho để bắt ảnh không đúng (người dùng 02/10/2026). Tốn tiền Claude: luôn ước tính trước.

    py tools/library_vision_check.py                          chỉ ƯỚC TÍNH (không gọi gì)
    py tools/library_vision_check.py --yes --max-usd 0.9      gọi Claude: 1 lượt / nhân vật, MỘT ảnh ghép tất cả ảnh đã duyệt của nhân vật
    py tools/library_vision_check.py --apply                  áp kết quả đã lưu (ảnh không phải người / sai người → "ảnh thừa")

Mỗi lượt Claude trả, cho từng ảnh (đánh số trên ảnh ghép): ok / not_character (biểu tượng, kỹ năng, vũ khí, logo, ảnh rỗng) /
other_person (người khác) / other_look (cùng người nhưng ngoại hình khác hồ sơ — chỉ ghi chú, người quyết); và hồ sơ nháp có mâu thuẫn
với ảnh không. Kết quả lưu ở data/library_check.json (mỗi nhân vật làm một lần; chạy lại bỏ qua người đã có — dùng --redo để làm lại).
Chạy từ worktree: thêm --db D:/AI-Video-Pipeline/data/manifest.sqlite --repo D:/AI-Video-Pipeline."""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets  # noqa: E402

EST_USD = 0.015
MAX_IMAGES = 8
CELL = (210, 300)
VERDICTS = ("ok", "not_character", "other_person", "other_look")


def contact_sheet(items, out_path: str) -> str:
    """One picture of up to MAX_IMAGES pictures, each with its id written on it (grey background so transparent art is visible)."""
    from PIL import Image, ImageDraw
    items = items[:MAX_IMAGES]
    cols = min(len(items), 4)
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * CELL[0], rows * CELL[1]), (128, 128, 128))
    d = ImageDraw.Draw(sheet)
    for k, it in enumerate(items):
        with Image.open(it["path"]) as im:
            im = im.convert("RGBA")
            im.thumbnail((CELL[0] - 4, CELL[1] - 22))
            x, y = (k % cols) * CELL[0], (k // cols) * CELL[1]
            sheet.paste(im, (x + 2, y + 20), im)
        d.rectangle([x, y, x + 70, y + 16], fill=(0, 0, 0))
        d.text((x + 3, y + 2), f"#{it['id']}", fill=(255, 255, 0))
    sheet.save(out_path, "JPEG", quality=88)
    return out_path


def prompt_for(name: str, profile: dict, official: str, ids) -> str:
    return (f"The picture is a contact sheet of the reference images of ONE Free Fire character, \"{name}\". Every image has its id written on it "
            f"(ids: {', '.join('#' + str(i) for i in ids)}). Judge each image. verdict: 'ok' = a picture of this character as a person "
            "(any crop: full body, half body, close-up, design sheet of the character); 'not_character' = NOT a picture of the character as a "
            "person (a skill or ability icon, an emblem, a weapon, a logo, an empty frame, a map); 'other_person' = a different person; "
            "'other_look' = the same person in a clearly different outfit or look than the profile below (say what differs).\n"
            f"Standard profile (draft): identity: {profile.get('identity', '—')}\nmust_keep: {profile.get('must_keep', '—')}\n"
            f"Official site text (excerpt): {official[:500] or '—'}\n\n"
            "Also say whether the profile CONTRADICTS what you see (a wrong colour, garment, hair, or a detail that is not there) and list the "
            "contradictions briefly in profile_issues (empty list when none). Describe only what you can see; never guess left/right. "
            "Answer ONE JSON: {\"images\": [{\"id\": 123, \"verdict\": \"ok\", \"note\": \"\"}], \"profile_issues\": []}")


def _check(obj) -> None:
    from core import llm_io
    if not isinstance(obj, dict) or not isinstance(obj.get("images"), list) or not isinstance(obj.get("profile_issues"), list):
        raise llm_io.SchemaError("root: {images: [{id, verdict, note}], profile_issues: []}")
    for x in obj["images"]:
        if not isinstance(x, dict) or x.get("verdict") not in VERDICTS or not isinstance(x.get("id"), int):
            raise llm_io.SchemaError(f"each image needs an integer id and verdict in {VERDICTS}")


def targets(conn, game: str):
    out = []
    for a in assets.list_assets(conn, game, "character"):
        imgs = [i for i in a["images"] if i.get("path") and os.path.exists(i["path"])]
        if imgs:
            out.append(dict(a, images=imgs))
    return out


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--repo", default=None)
    ap.add_argument("--game", default="FF")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--max-usd", type=float, default=0.9)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--results", default=os.path.join("data", "library_check.json"))
    a = ap.parse_args()
    if a.repo:
        assets.REPO = a.repo
    from core.db import connect
    conn = connect(a.db)
    done = json.load(open(a.results, encoding="utf-8")) if os.path.exists(a.results) else {}
    if a.apply:
        n = 0
        for name, r in done.items():
            for x in r["images"]:
                if x["verdict"] in ("not_character", "other_person"):
                    assets.set_image_meta(conn, x["id"], status="redundant")
                    n += 1
        print(f"đã chuyển {n} ảnh sang 'ảnh thừa'")
        return
    only = {s.strip().lower() for s in a.only.split(",") if s.strip()}
    todo = [c for c in targets(conn, a.game) if (a.redo or c["name"] not in done) and (not only or c["name"].lower() in only)]
    print(f"{len(todo)} nhân vật cần xem · ước tính ≈ ${EST_USD * len(todo):.2f} Claude (1 ảnh ghép + câu hỏi mỗi người)")
    if not a.yes:
        print("(chưa gọi Claude — thêm --yes để chạy)")
        return
    from core import budget, llm_runner
    from core.adapters.check import load_dashboard_env
    load_dashboard_env()
    if budget.check_llm(conn):
        sys.exit(budget.check_llm(conn))
    client = llm_runner.client_from_env(ledger=a.db)
    if client is None:
        sys.exit("Chưa cấu hình Claude API.")
    import tempfile
    start = budget.llm_spent(conn)
    for c in todo:
        if budget.llm_spent(conn) - start + EST_USD > a.max_usd:
            print("dừng: chạm trần --max-usd của lượt này")
            break
        prof = assets.get_profile(conn, c["id"])
        official = (c.get("description") or "").split("[ff.garena.com]")[-1] if "[ff.garena.com]" in (c.get("description") or "") else ""
        imgs = c["images"][:MAX_IMAGES]
        sheet = contact_sheet(imgs, os.path.join(tempfile.gettempdir(), f"libchk_{c['id']}.jpg"))
        try:
            with llm_runner.tagged("library_check"):
                obj = llm_runner.ask_json(client, prompt_for(c["name"], prof, official, [i["id"] for i in imgs]), _check, [(c["name"], sheet)])[0]
        except Exception as e:  # noqa: BLE001 - one character must not stop the run
            print(f"  ✗ {c['name']}: {e}")
            continue
        done[c["name"]] = obj
        os.makedirs(os.path.dirname(a.results) or ".", exist_ok=True)
        json.dump(done, open(a.results, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        bad = [f"#{x['id']} {x['verdict']}" for x in obj["images"] if x["verdict"] != "ok"]
        print(f"  {c['name']}: " + ("; ".join(bad) if bad else "ok") + (f" | hồ sơ lệch: {obj['profile_issues']}" if obj["profile_issues"] else ""))
    print(f"đã dùng ≈ ${budget.llm_spent(conn) - start:.3f}")


if __name__ == "__main__":
    main()
