r"""Thử Storyboard Deepix qua API (prompt_key 14, cách node Storyboard của Weave Canvas) trên 4 shot đầu của một dự án.

    py tools/experiments/storyboard_test.py --project 7 --shots 1 2 3 4            chỉ in kế hoạch (không gửi)
    py tools/experiments/storyboard_test.py --project 7 --shots 1 2 3 4 --yes      gửi (4 ảnh Deepix, tính trần ảnh + sổ chi)

Kết quả: data/projects/<id>/storyboard_test/<storyboard_id>/frame_N.png + so_sanh.jpg (khung storyboard cạnh ảnh shot cũ).
Cần DEEPIX_TOKEN trong biến môi trường (không in ra).
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from core import assets, budget, cost, image_models, looks, storyboard_frames  # noqa: E402
from core.db import connect  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from core.runner import framing_sentence, lock_note, no_minor_age  # noqa: E402


def build(p, pid, idxs):
    rows = {r["idx"]: r for r in p.conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=?", (pid,))}
    proj = p.project(pid)
    prompts, refs, seen, actions = [], [], set(), []
    for i in idxs:
        d = json.loads(rows[i]["data"] or "{}")
        text = framing_sentence(d) + (d.get("image_prompt") or "")
        if (d.get("blocking") or "").strip():
            text += f". Blocking: {d['blocking'].strip()}"
        text += lock_note(p.conn, pid, d.get("characters")) + looks.image_sentence(proj)
        prompts.append(no_minor_age(text))
        actions.append(f"Frame {len(prompts)}: " + (d.get("action") or d.get("image_prompt") or "")[:160])
        for r in assets.scene_references(p.conn, pid, d, limit=assets.MAX_REFERENCES):
            if r["path"] not in seen and len(refs) < 8:
                seen.add(r["path"])
                refs.append({"path": r["path"], "label": r["label"]})
    story = no_minor_age("One continuous scene at night in front of the Free Fire clock tower, same place, same light, same people in "
                         "every frame. " + " ".join(actions))
    return prompts, refs, story, proj


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shots", type=int, nargs="+", required=True)
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))   # run from the main folder
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    p = Pipeline(connect(a.db))
    prompts, refs, story, proj = build(p, a.project, a.shots)
    model = image_models.of_project(proj)
    b = budget.get(p.conn)
    used = budget.spent(p.conn, since=b["since"])["images"] if b["enabled"] else None
    print(f"model {model} · {len(prompts)} khung · {len(refs)} ảnh tham chiếu: " + ", ".join(r["label"] for r in refs))
    print(f"trần ảnh đợt thử: {used}/{b['image_cap']} → sau lần này {None if used is None else used + len(prompts)}")
    for i, t in enumerate(prompts, 1):
        print(f"  khung {i}: {t[:180]}…")
    if not a.yes:
        print("(chưa gửi — thêm --yes)")
        return
    if used is not None and used + len(prompts) > b["image_cap"]:
        sys.exit("vượt trần ảnh đợt thử — dừng")
    from core.adapters.deepix import DeepixImageProvider
    provider = DeepixImageProvider.from_env()
    data = os.path.dirname(os.path.abspath(a.db))
    out = os.path.join(data, "projects", str(a.project), "storyboard_test")

    def ledger(i, mid):
        cost.record_usage(p.conn, None, "image", provider.name, model, "image", 1, "image", project_id=a.project, stage="storyboard_test")
        print(f"  gửi khung {i + 1}: {mid}", flush=True)

    res = storyboard_frames.run(provider, prompts, refs, story, os.path.join(out, "run"), size="1152x2048", model=model, on_submit=ledger)
    final = os.path.join(out, res["storyboard_id"])
    os.replace(os.path.join(out, "run"), final)
    print(json.dumps({"storyboard_id": res["storyboard_id"], "frames": [{k: v for k, v in f.items() if k != "path"} for f in res["frames"]]},
                     ensure_ascii=False))
    from PIL import Image
    rows = {r["idx"]: r["id"] for r in p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=?", (a.project,))}
    tiles = []
    for n, i in enumerate(a.shots, 1):
        new = os.path.join(final, f"frame_{n}.png")
        old = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                             (rows[i],)).fetchone()
        oldp = os.path.join(data, "projects", str(a.project), "images", f"job_{old['id']}.png") if old else None
        tiles.append((oldp, new if os.path.exists(new) else None))
    w = 300
    sheet = Image.new("RGB", (len(tiles) * (w + 10) + 10, 2 * int(w * 16 / 9) + 30), (20, 20, 20))
    for k, (o, nw) in enumerate(tiles):
        for r, path in enumerate((o, nw)):
            if path and os.path.exists(path):
                im = Image.open(path).convert("RGB").resize((w, int(w * 16 / 9)))
                sheet.paste(im, (10 + k * (w + 10), 10 + r * (int(w * 16 / 9) + 10)))
    sheet.save(os.path.join(final, "so_sanh.jpg"), quality=88)
    print("so sánh:", os.path.join(final, "so_sanh.jpg"))


if __name__ == "__main__":
    main()
