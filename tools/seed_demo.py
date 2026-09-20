"""Create a demo project (fake scenes, placeholder images, QC scores, jobs in every state) for UI work.

    py tools/seed_demo.py --out data/demo
    $env:PIPELINE_DB="data/demo/manifest.sqlite"; $env:PIPELINE_DATA="data/demo/projects"; py -m streamlit run dashboard/app.py

No API calls, no credits. Needs Pillow only to draw the placeholder images.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import connect  # noqa: E402
from core.llm_io import approve_motion_prompt, lock_character_bible, store_motion_prompts, store_scene_analysis  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402
from core.preflight import record_failure  # noqa: E402

COLORS = [("#2B3A67", "#8A9BD1"), ("#3D2C4E", "#B58DB6"), ("#264653", "#7FB7BE"), ("#3A2E1F", "#C9A66B"),
          ("#1D3A2F", "#7FC8A9"), ("#40263A", "#D08DA7"), ("#2F2F4A", "#9A9AC9"), ("#33402A", "#A9C98A")]
CRITERIA = ["character", "hands_face", "composition", "mood_lighting", "consistency"]
SCENES = [("Rừng Elder", "Đêm", ["Lyra"], "u ám, sương mù", "wide"), ("Rừng Elder", "Đêm", ["Lyra", "Kael"], "căng thẳng", "medium"),
          ("Pháo đài", "Ngày", ["Kael"], "hùng vĩ", "low angle"), ("Pháo đài", "Hoàng hôn", ["Lyra"], "buồn", "close-up"),
          ("Làng nhỏ", "Ngày", ["Ông lão Orin"], "ấm áp", "medium"), ("Hang động", "Đêm", ["Nữ chiến binh Amazon"], "nguy hiểm", "wide"),
          ("Đồi cỏ", "Bình minh", ["Lyra", "Kael"], "hy vọng", "wide"), ("Đỉnh núi", "Ngày", ["Kael"], "kết thúc", "drone")]


def draw(path: str, top: str, bottom: str, label: str) -> None:
    from PIL import Image, ImageDraw
    w, h = 640, 360
    img = Image.new("RGB", (w, h))
    a = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3)))
    d.text((24, 20), label, fill="white")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("data", "demo"))
    out = ap.parse_args().out
    os.makedirs(out, exist_ok=True)
    db = os.path.join(out, "manifest.sqlite")
    if os.path.exists(db):
        os.remove(db)
    p = Pipeline(connect(db))
    pid = p.create_project("Trailer Ep.1 (demo)")
    for i, (loc, t, ch, mood, shot) in enumerate(SCENES, 1):
        sid = p.create_scene(pid, i, f"CẢNH {i}")
        text = (f"CẢNH {i}. {t.upper()} — {loc.upper()}\n{', '.join(ch)} xuất hiện trong khung cảnh {mood}. "
                f"Camera {shot}. (Đoạn kịch bản mẫu để thử giao diện.)\n{ch[0]}: Chúng ta phải đi tiếp trước khi trời sáng.")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": text}, ensure_ascii=False), sid))
    p.conn.commit()
    store_scene_analysis(p, pid, {
        "characters": [{"name": "Lyra", "description": "Nữ, 25 tuổi, tóc bạc dài, giáp xanh cobalt, sẹo mắt trái"},
                       {"name": "Kael", "description": "Nam, 35, râu ngắn, áo choàng đen, kiếm rune"},
                       {"name": "Nữ chiến binh Amazon", "description": "Nữ, 30, giáp vàng, khiên tròn", "wardrobe": "vòng tay bạc"},
                       {"name": "Ông lão Orin", "description": "Nam, 70, râu bạc, gậy gỗ, áo len xám"}],
        "scenes": [{"idx": i, "location": loc, "time": t, "characters": ch, "mood": mood, "lighting": "tự nhiên",
                    "shot": shot, "image_prompt": f"{loc}, {t}, {mood}"} for i, (loc, t, ch, mood, shot) in enumerate(SCENES, 1)]})
    lock_character_bible(p, pid)
    images = os.path.join(out, "projects", str(pid), "images")
    plan = ["approved", "approved", "review_low", "review_high", "ok", "failed", "running", "auto_rejected"]
    for i, kind in enumerate(plan, 1):
        scene = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (pid, i)).fetchone()["id"]
        job = p.create_job(scene)
        if kind == "queued":
            continue
        p.start(job)
        if kind == "running":
            continue
        if kind == "failed":
            p.fail(job, "risk control")
            continue
        p.succeed(job)
        draw(os.path.join(images, f"job_{job}.png"), *COLORS[i - 1], f"S{i:02d}")
        if kind == "ok":
            continue
        scores = {"approved": .92, "review_high": .90, "review_low": .61, "auto_rejected": .30}[kind]
        vals = [scores + d for d in (0.03, -0.08, 0.02, -0.02, 0.05)] if kind not in ("review_low", "auto_rejected")             else ([.78, .42, .71, .55, .60] if kind == "review_low" else [.35, .20, .30, .25, .40])
        p.apply_qc(job, dict(zip(CRITERIA, vals)), issues="tay trái 6 ngón, sai màu áo" if kind == "auto_rejected" else None)
        if kind == "approved":
            p.approve(job)
    store_motion_prompts(p, pid, {"scenes": [
        {"idx": 1, "motion_prompt": "Slow push-in, sương mù trôi ngang, Lyra quay đầu chậm", "duration_sec": 5},
        {"idx": 2, "motion_prompt": "Medium two-shot, camera orbit 15°, ánh lửa nhấp nháy", "duration_sec": 5}]})
    approve_motion_prompt(p, p.conn.execute("SELECT id FROM scenes WHERE idx=2").fetchone()["id"])
    for idx, kind in ((1, "succeeded"), (2, "running")):
        scene = p.conn.execute("SELECT id FROM scenes WHERE idx=?", (idx,)).fetchone()["id"]
        job = p.create_job(scene, "video_gen")
        p.start(job)
        if kind == "succeeded":
            p.succeed(job)
    scene = p.conn.execute("SELECT id FROM scenes WHERE idx=3").fetchone()["id"]
    job = p.create_job(scene, "video_gen")
    p.start(job)
    p.fail(job, "risk control")
    record_failure(p.conn, job, "clipai", "Failure to pass the risk control system")
    print(f"Demo ready. PIPELINE_DB={db}  PIPELINE_DATA={os.path.join(out, 'projects')}")


if __name__ == "__main__":
    main()
