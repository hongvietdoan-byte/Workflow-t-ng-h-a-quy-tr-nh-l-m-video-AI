r"""Thử 2026-09-27 (người dùng đề xuất): mỗi cảnh một ẢNH TOÀN CẢNH NGANG (2048×1152: trọn tháp, quảng trường, ánh sáng của cảnh), dùng
làm ảnh tham chiếu bối cảnh cho các khung dọc của cảnh — khung dọc vẽ bằng storyboard Deepix, model tự vẽ cả cảnh (cách 4 frame #7,
data/projects/7/storyboard_test/run/), không ghép phông xanh.

    py tools/experiments/scene_wide_test.py --project 8 --shots 1 2 3 4            chỉ in kế hoạch
    py tools/experiments/scene_wide_test.py --project 8 --shots 1 2 3 4 --yes      gửi (1 ảnh ngang + N khung, qua trần ảnh + sổ chi)

Kết quả: data/projects/<id>/scene_wide_test/<storyboard_id>/ (wide.png, frame_N.png, so_sanh.jpg). Không gọi Claude.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))

from core import budget, cost, image_models, storyboard_frames  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from core.runner import no_minor_age  # noqa: E402

LIGHT = {"night": ("Night, yet every face is clearly lit and readable: a soft warm street-lamp key light on the faces, a cool moonlight "
                   "rim light separating the people from the background, lamps glowing on the plaza — dark sky, never muddy or crushed "
                   "into black."),
         "day": "Bright late-afternoon sun, clear shadows on the ground under the people, natural contact with the floor."}


def tower_pictures(conn, asset_id: int):
    """The place's approved full-view renders (eye level first)."""
    rows = conn.execute("SELECT path, role FROM asset_images WHERE asset_id=? AND status='approved' ORDER BY (role='eye_level') DESC, id",
                        (asset_id,)).fetchall()
    return [{"path": r["path"], "label": f"the Free Fire clock tower ({r['role'] or 'view'})"} for r in rows if os.path.exists(r["path"])]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shots", type=int, nargs="+", required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--model", help="model ảnh (mặc định: model của dự án); 4 frame #7 dùng gpt-image-2.5-sunburst")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.from_args(a, "scene_wide_test").start()
    import storyboard_test
    p = Pipeline(connect(a.db))
    prompts, refs, story, proj = storyboard_test.build(p, a.project, a.shots)
    first = json.loads(p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (a.project, a.shots[0])).fetchone()["data"])
    time = first.get("time") or "day"
    light = LIGHT.get(time, LIGHT["day"])
    towers = tower_pictures(p.conn, int(first.get("location_asset") or 263))[:3]
    wide_prompt = no_minor_age(
        f"Free Fire in-game 3D render, wide establishing shot of the Free Fire clock tower and its stone plaza, the whole tower from its base "
        f"to the tip of its spire in frame, palm trees, low parapet walls, {time}. {light} No people. Keep exactly the architecture of the "
        f"reference pictures (the same tower: spire, windows, stairs).")
    prompts = [f"{t} {light}" for t in prompts]
    story = story.replace("One continuous scene at night", "One continuous scene" + (" at night" if time == "night" else "")) + " " + light
    model = a.model or image_models.of_project(proj)
    b = budget.get(p.conn)
    used = budget.spent(p.conn, since=b["since"])["images"] if b["enabled"] else None
    need = 1 + len(prompts)
    print(f"model {model} · 1 ảnh ngang + {len(prompts)} khung · tháp: {len(towers)} ảnh · tham chiếu khung: "
          + ", ".join(r["label"] for r in refs) + " + ảnh ngang")
    print(f"trần ảnh: {used}/{b['image_cap']} → sau lần này {None if used is None else used + need}")
    print("ảnh ngang:", wide_prompt[:300])
    if not a.yes:
        print("(chưa gửi — thêm --yes)")
        return
    if used is not None and used + need > b["image_cap"]:
        sys.exit("vượt trần ảnh — dừng")
    from core.adapters.deepix import DeepixImageProvider
    provider = DeepixImageProvider.from_env()
    data = os.path.dirname(os.path.abspath(a.db))
    out = os.path.join(data, "projects", str(a.project), "scene_wide_test", "run")
    os.makedirs(out, exist_ok=True)
    with budget.SPEND_LOCK:
        over = budget.check_image(p.conn, provider.name, model)
        if over:
            sys.exit(f"trần chặn: {over}")
        mid = provider.submit(wide_prompt, [t["path"] for t in towers], size="2048x1152", model=model)
        cost.record_usage(p.conn, None, "image", provider.name, model, "image", 1, "image", project_id=a.project, stage="scene_wide_test")
    print("gửi ảnh ngang:", mid, flush=True)
    wide = storyboard_frames._wait(provider, mid, os.path.join(out, "wide.png"), 5.0, 600.0, __import__("time").sleep)
    if not wide:
        sys.exit("ảnh ngang không về")
    refs = refs[:7] + [{"path": wide, "label": "the place of this scene (wide view: the whole clock tower, the plaza and this scene's light)"}]

    def ledger(i, m):
        cost.record_usage(p.conn, None, "image", provider.name, model, "image", 1, "image", project_id=a.project, stage="scene_wide_test")
        print(f"  gửi khung {i + 1}: {m}", flush=True)

    res = storyboard_frames.run(provider, prompts, refs, story, out, size="1152x2048", model=model, on_submit=ledger,
                                conn=p.conn)   # rà soát A2: trần --max-usd + hết tiền kiểm TRƯỚC mỗi khung
    if res.get("stopped"):
        print(res["stopped"])
    final = os.path.join(os.path.dirname(out), res["storyboard_id"])
    os.replace(out, final)
    print(json.dumps({"storyboard_id": res["storyboard_id"], "frames": [{k: v for k, v in f.items() if k != "path"} for f in res["frames"]]},
                     ensure_ascii=False))
    from PIL import Image
    old7 = [os.path.join(data, "projects", "7", "storyboard_test", "run", f"frame_{k}.png") for k in range(1, 5)]
    new = [os.path.join(final, f"frame_{k}.png") for k in range(1, len(prompts) + 1)]
    w, h = 300, int(300 * 16 / 9)
    sheet = Image.new("RGB", (10 + 4 * (w + 10), 30 + 2 * (h + 10) + int(4 * (w + 10) * 9 / 16)), (20, 20, 20))
    for r, row in enumerate((old7, new)):
        for k, path in enumerate(row[:4]):
            if os.path.exists(path):
                sheet.paste(Image.open(path).convert("RGB").resize((w, h)), (10 + k * (w + 10), 10 + r * (h + 10)))
    ww = 4 * (w + 10) - 10
    sheet.paste(Image.open(os.path.join(final, "wide.png")).convert("RGB").resize((ww, int(ww * 9 / 16))), (10, 20 + 2 * (h + 10)))
    sheet.save(os.path.join(final, "so_sanh.jpg"), quality=88)
    print("so sánh:", os.path.join(final, "so_sanh.jpg"))


if __name__ == "__main__":
    main()
