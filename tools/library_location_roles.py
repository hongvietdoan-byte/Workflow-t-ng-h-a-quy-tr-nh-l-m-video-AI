"""Gắn góc máy cho ảnh ĐỊA ĐIỂM trong Kho bằng Claude nhìn ảnh (người dùng 02/10/2026). Tốn tiền Claude: ước tính trước.

    py tools/library_location_roles.py                        chỉ ước tính
    py tools/library_location_roles.py --yes --max-usd 0.25   gọi Claude: 1 lượt / 12 ảnh (ảnh ghép đánh số) và GHI vai trò
Vai trò: eye_level (nền ngang tầm mắt, không người) · low_angle · high_angle · top_down (bản đồ / toàn cảnh từ trên: chỉ thông tin, không làm nền) ·
detail (mốc / chi tiết) · interior (trong nhà). Chỉ ảnh đã duyệt CHƯA có vai trò; ảnh đã gắn tay không đụng tới.
Chạy từ thư mục gốc: --db D:/AI-Video-Pipeline/data/manifest.sqlite --repo D:/AI-Video-Pipeline."""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets, script_cap  # noqa: E402

EST_USD = 0.012
BATCH = 12
CELL = (260, 190)
ROLES = ("eye_level", "low_angle", "high_angle", "top_down", "detail", "interior")


def sheet(items, out):
    from PIL import Image, ImageDraw
    cols = 4
    rows = (len(items) + cols - 1) // cols
    img = Image.new("RGB", (cols * CELL[0], rows * CELL[1]), (90, 90, 90))
    d = ImageDraw.Draw(img)
    for k, it in enumerate(items):
        with Image.open(it["path"]) as im:
            im = im.convert("RGB")
            im.thumbnail((CELL[0] - 4, CELL[1] - 22))
            x, y = (k % cols) * CELL[0], (k // cols) * CELL[1]
            img.paste(im, (x + 2, y + 20))
        d.rectangle([x, y, x + 70, y + 16], fill=(0, 0, 0))
        d.text((x + 3, y + 2), f"#{it['id']}", fill=(255, 255, 0))
    img.save(out, "JPEG", quality=85)
    return out


def prompt_for(items) -> str:
    names = "; ".join(f"#{i['id']} = {i['name']}" for i in items)
    return ("The picture is a contact sheet of Free Fire PLACE pictures, each with its id written on it (" + names + "). For EACH id choose the "
            "camera class of the picture: eye_level (a ground-level view, horizon at eye height, an environment you could stand in); low_angle (looking "
            "up from below); high_angle (an elevated view looking down at an angle, still a real scene); top_down (a map, a layout or a straight-down "
            "aerial); detail (a close view of one landmark or object); interior (inside a building). Describe what you see only. Answer ONE JSON: "
            "{\"images\": [{\"id\": 123, \"role\": \"eye_level\"}]} with every id once.")


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
    script_cap.add_argument(ap)          # S14.2: trần CỨNG, bắt buộc khi --yes
    a = ap.parse_args()
    cap = script_cap.from_args(a, "gắn góc máy ảnh địa điểm")
    if a.repo:
        assets.REPO = a.repo
    from core.db import connect
    conn = connect(a.db)
    todo = []
    for p in assets.list_assets(conn, a.game, "location"):
        for i in p["images"]:
            if not i.get("role") and i.get("path") and os.path.exists(i["path"]):
                todo.append({"id": i["id"], "path": i["path"], "name": p["name"]})
    batches = [todo[k:k + BATCH] for k in range(0, len(todo), BATCH)]
    print(f"{len(todo)} ảnh địa điểm chưa có góc máy · {len(batches)} lượt · ước tính ≈ ${EST_USD * len(batches):.2f} Claude")
    if not a.yes:
        print("(chưa gọi Claude — thêm --yes --max-usd <USD>)")
        return
    from core import budget, llm_io, llm_runner
    from core.adapters.check import load_dashboard_env
    load_dashboard_env()
    if budget.check_llm(conn):
        sys.exit(budget.check_llm(conn))
    client = llm_runner.client_from_env(ledger=a.db)
    if client is None:
        sys.exit("Chưa cấu hình Claude API.")

    def check(obj) -> None:
        if not isinstance(obj, dict) or not isinstance(obj.get("images"), list) or any(
                not isinstance(x, dict) or x.get("role") not in ROLES or not isinstance(x.get("id"), int) for x in obj["images"]):
            raise llm_io.SchemaError(f"root: {{images: [{{id, role in {ROLES}}}]}}")

    start, set_n, left = budget.llm_spent(conn), 0, 0
    cap.start()
    for b in batches:
        if not cap.allow(max(EST_USD, cap.estimate_llm("library_check", images=1))):
            left += len(b)
            continue
        out = sheet(b, os.path.join(tempfile.gettempdir(), f"locroles_{b[0]['id']}.jpg"))
        try:
            with llm_runner.tagged("library_check"):
                obj = llm_runner.ask_json(client, prompt_for(b), check, [("sheet", out)])[0]
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ lượt #{b[0]['id']}: {e}")
            left += len(b)
            continue
        ids = {i["id"] for i in b}
        for x in obj["images"]:
            if x["id"] in ids:
                assets.set_image_meta(conn, x["id"], role=x["role"])
                set_n += 1
    print(f"đã gắn {set_n} ảnh · chưa làm {left} · đã dùng ≈ ${budget.llm_spent(conn) - start:.3f}")


if __name__ == "__main__":
    main()
