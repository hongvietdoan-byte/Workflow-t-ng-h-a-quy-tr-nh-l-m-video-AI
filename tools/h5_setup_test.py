"""Q2 / H5 (kế hoạch 2026-09-25): thử "quay theo vị trí máy" — MỘT clip cho nhiều shot cùng góc máy, rồi cắt ra từng shot.

Gửi 1 clip (ảnh đã duyệt của shot đầu làm khung đầu, motion prompt kể lần lượt từng nhịp), ghi vào sổ chi, chờ xong, tải về và cắt
theo độ dài từng shot. Tôn trọng trần đợt thử (core/budget.py). Không đụng job/clip của pipeline.

    py tools/h5_setup_test.py --project 7 --shots 9,10 --prompt "…" [--model kling]
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import budget, cost, db, ffmpeg_studio, formats  # noqa: E402
from core.adapters import factory  # noqa: E402
from core.pipeline import Pipeline  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shots", required=True, help="số shot (idx) cùng vị trí máy, theo thứ tự trên phim")
    ap.add_argument("--prompt", required=True, help="motion prompt kể lần lượt các nhịp (tiếng Anh)")
    ap.add_argument("--model", default="kling")
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--task", help="theo dõi tiếp task đã gửi (mã thật, vd omni:9322…) — không gửi lại, không ghi sổ lần nữa")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args(argv)
    script_cap.from_args(argparse.Namespace(paid=not a.task, max_usd=a.max_usd), "h5_setup_test").start()
    p = Pipeline(db.connect(a.db))
    pid, idxs = a.project, [int(x) for x in a.shots.split(",")]
    rows = [p.conn.execute("SELECT id, idx FROM scenes WHERE project_id=? AND idx=?", (pid, i)).fetchone() for i in idxs]
    durs = [float(p.conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (r["id"],)).fetchone()[0]) for r in rows]
    img = p.conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                         (rows[0]["id"],)).fetchone()
    image = os.path.join(a.data, str(pid), "images", f"job_{img['id']}.png")
    seconds = max(math.ceil(sum(durs) - 1e-6), 3)
    prov = factory.video_provider()
    model, tier, billed = prov.usage_info(a.model, seconds)
    if a.task:
        task = a.task
    else:
        over = budget.check_video(p.conn, prov.name, model, tier, billed)
        if over:
            print("DỪNG:", over)
            return 1
        aspect = formats.spec(formats.project_aspect(p.project(pid)))["clip"]
        task = prov.submit(image, a.prompt, None, seconds, a.model, aspect_ratio=aspect)
        cost.record_usage(p.conn, None, "video", prov.name, model, tier, billed, "second", project_id=pid, stage="h5_setup_test")
        print(f"gửi 1 clip {seconds}s cho shot {idxs} (từng shot sẽ trả {sum(max(math.ceil(d - 1e-6), 3) for d in durs)}s) — mã {task}",
              flush=True)
    out_dir = os.path.join(a.data, str(pid), "h5_test")
    os.makedirs(out_dir, exist_ok=True)
    end = time.time() + a.minutes * 60
    while time.time() < end:
        st = prov.status(task)
        print(time.strftime("%H:%M:%S"), st.state, flush=True)
        if st.state in ("succeeded", "failed"):
            break
        time.sleep(20)
    if st.state != "succeeded":
        print("không xong:", st)
        return 1
    whole = prov.download(task, os.path.join(out_dir, f"setup_{'_'.join(map(str, idxs))}.mp4"))
    ff = ffmpeg_studio.find_ffmpeg()
    start = 0.0
    parts = []
    for i, d in zip(idxs, durs):
        part = os.path.join(out_dir, f"shot_{i}_from_setup.mp4")
        ffmpeg_studio.run([ff, "-y", "-ss", f"{start:.2f}", "-i", whole, "-t", f"{d:.2f}", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", part])
        parts.append(part)
        start += d
    print(json.dumps({"clip": whole, "parts": parts, "billed_s": billed, "per_shot_billed_s":
                      sum(max(math.ceil(d - 1e-6), 3) for d in durs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
