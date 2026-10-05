r"""Thử A/B 2026-09-28 — nền Tháp Đồng Hồ bị "xây nhiều lớp cao tầng" ở khung ngang tầm mắt (người dùng), ảnh toàn cảnh thì đúng map.
Nghi 2 nguyên nhân: (1) prompt thiếu câu bố cục thật (đã thêm vào mô tả Kho asset 263 → vào mọi prompt ảnh), (2) ảnh tham chiếu
render 3D chụp sát chân tháp (bệ đá, tường, bậc lớn). Mỗi shot vẽ 2 kiểu, cùng prompt sản xuất (runner.build_image_prompt + câu ánh
sáng), vẽ ĐƠN (không phiên storyboard) để chỉ khác một yếu tố:
  B = ảnh tham chiếu như sản xuất (nhân vật + render tháp + ảnh toàn cảnh của cảnh)
  A = bỏ các render của Kho tháp, chỉ giữ ảnh toàn cảnh của cảnh
So với khung cũ (render + KHÔNG có câu bố cục): cũ → B = tác dụng của câu bố cục; B → A = tác dụng của render sát chân tháp.

    py tools/experiments/tower_layout_test.py --project 8 --shots 157 159            kế hoạch
    py tools/experiments/tower_layout_test.py --project 8 --shots 157 159 --yes      gửi (2 ảnh / shot, qua trần ảnh + sổ chi)
Kết quả: data/projects/<id>/tower_layout_test/ (A_<id>.png, B_<id>.png, so_sanh.jpg). Không gọi Claude.
"""
import argparse
import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))

from core import assets, budget, cost, image_models, scene_establish, storyboard_frames  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from core.runner import build_image_prompt  # noqa: E402


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shots", type=int, nargs="+", required=True, help="scene ids (bảng scenes)")
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--yes", action="store_true")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.from_args(a, "tower_layout_test").start()
    from group_test import load_env
    load_env(".")
    p = Pipeline(connect(a.db))
    data_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "projects")
    model = image_models.of_project(p.project(a.project))
    plan = []
    for sid in a.shots:
        d = json.loads(p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"] or "{}")
        prompt, _ = build_image_prompt(p.conn, a.project, d)
        prompt = f"{prompt} {scene_establish.light_sentence(d)}".strip()
        refs = assets.scene_references(p.conn, a.project, d, limit=6, sheets=True)
        est = scene_establish.reference(data_dir, a.project, d.get("story_scene"))
        place = os.path.join("assets", str(d.get("location_asset") or 263)).replace("\\", "/")
        b_refs = [r["path"] for r in refs] + ([est["path"]] if est else [])
        a_refs = [r["path"] for r in refs if place not in r["path"].replace("\\", "/")] + ([est["path"]] if est else [])
        plan.append((sid, d, prompt, a_refs, b_refs))
        print(f"shot {sid} S{d.get('story_scene')}·{d.get('shot_no')} — câu bố cục trong prompt: {'Real map:' in prompt}")
        print("  B:", [os.path.basename(x) for x in b_refs])
        print("  A:", [os.path.basename(x) for x in a_refs])
    b = budget.get(p.conn)
    used = budget.spent(p.conn, since=b["since"])["images"] if b["enabled"] else None
    need = 2 * len(plan)
    print(f"model {model} · {need} ảnh · trần ảnh {used}/{b['image_cap']}")
    if not a.yes:
        print("(chưa gửi — thêm --yes --max-usd <USD>)")
        return
    if used is not None and used + need > b["image_cap"]:
        sys.exit("vượt trần ảnh — dừng")
    from core.adapters.deepix import DeepixImageProvider
    provider = DeepixImageProvider.from_env()
    out = os.path.join(data_dir, str(a.project), "tower_layout_test")
    os.makedirs(out, exist_ok=True)
    sent = []
    for sid, d, prompt, a_refs, b_refs in plan:
        for tag, refs in (("A", a_refs), ("B", b_refs)):
            with budget.SPEND_LOCK:
                over = budget.check_image(p.conn, provider.name, model)
                if over:
                    sys.exit(f"trần chặn: {over}")
                mid = provider.submit(prompt, refs, size="1152x2048", model=model)
                cost.record_usage(p.conn, None, "image", provider.name, model, "image", 1, "image", project_id=a.project,
                                  stage="tower_layout_test")
            print(f"gửi {tag} shot {sid}: {mid}", flush=True)
            sent.append((tag, sid, mid))
    got = {}
    for tag, sid, mid in sent:
        path = storyboard_frames._wait(provider, mid, os.path.join(out, f"{tag}_{sid}.png"), 5.0, 600.0, time.sleep)
        got[(tag, sid)] = path
        print(f"  {tag}_{sid}: {'về' if path else 'KHÔNG về'}", flush=True)
    from PIL import Image, ImageDraw
    w, h = 360, 640
    sheet = Image.new("RGB", (10 + 3 * (w + 10), 10 + len(plan) * (h + 40)), (20, 20, 20))
    for r, (sid, d, *_rest) in enumerate(plan):
        job = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                             (sid,)).fetchone()
        old = os.path.join(data_dir, str(a.project), "images", f"job_{job['id']}.png") if job else None
        for c, (label, path) in enumerate((("cũ (render, không câu bố cục)", old), ("B (render + câu bố cục)", got.get(("B", sid))),
                                           ("A (bỏ render, + câu bố cục)", got.get(("A", sid))))):
            x, y = 10 + c * (w + 10), 10 + r * (h + 40)
            ImageDraw.Draw(sheet).text((x, y), f"S{d.get('story_scene')}·{d.get('shot_no')} {label}", fill="yellow")
            if path and os.path.exists(path):
                sheet.paste(Image.open(path).convert("RGB").resize((w, h)), (x, y + 20))
    sheet.save(os.path.join(out, "so_sanh.jpg"), quality=88)
    print("so_sanh:", os.path.join(out, "so_sanh.jpg"))


if __name__ == "__main__":
    main()
