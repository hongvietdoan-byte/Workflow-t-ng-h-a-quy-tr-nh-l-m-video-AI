"""Thử video tham chiếu NHẢY cho Seedance 2.5 (người dùng 06/10, dự án "Khủng Long Đỏ" — duyệt mọi chi phí, vẫn qua trần + sổ chi).
Ba bài, mỗi bài 1 clip 5 s, dọc 9:16, 720p, khuôn `mannequin_ref_test.py` (reference_only: bối cảnh + ảnh nhân vật + 1 video ref):
  RAW   — đoạn clip trend người THẬT (xem Seedance có nhận không)            · 1 nhân vật (Maxim)
  BW    — cùng đoạn, đổi thành bóng người ĐEN TRẮNG không mặt (nếu RAW bị từ chối) · 1 nhân vật (Maxim)
  DUO   — 1 người mẫu → 2 nhân vật (Maxim + Kelly) cùng nhảy theo (dùng ref đã được nhận: --ref raw|bw)

    py tools/experiments/dance_ref_test.py setup                                   tạo dự án thử (0 USD)
    py tools/experiments/dance_ref_test.py --project N prep                        cắt đoạn + làm bản đen trắng (0 USD)
    py tools/experiments/dance_ref_test.py --project N plan  --test RAW            in prompt + giá (không gửi)
    py tools/experiments/dance_ref_test.py --project N submit --test RAW --max-usd 2   gửi 1 clip
    py tools/experiments/dance_ref_test.py --project N poll                        tải clip về <data>/<pid>/experiments/

Chạy từ D:\\AI-Video-Pipeline. Bản đen trắng: máy quay trong clip đứng yên → nền = trung vị các khung, bóng người = khác nền (0 USD,
không tải mô hình)."""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

NAME = "Thử ref nhảy Seedance 2.5 (06/10)"
CAP_USD = 2.2                    # mỗi bài: 1 clip 5 s ≈ 1,4 USD × 1,25 dự phòng
MODEL, CANONICAL, TIER, SECS, ASPECT = "seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 5, "9:16"
SOURCE = os.path.join("D:" + os.sep, "2026", "OB55", "Thao", "KHỦNG LONG ĐỎ", "snaptik.vn_7685363124970523924.mp4")
CUT = (9.0, 14.0)                # đoạn động tác rộng (giơ tay, xoay hông) — toàn thân trong khung
PLACE = os.path.join("data", "assets", "263", "5.png")
KELLY = os.path.join("data", "assets", "23", "10.png")
MAXIM = os.path.join("data", "assets", "33", "7.png")

_MOTION = ("@Video 1 is used only for motion: take the dancer's full-body dance movement, rhythm and timing, beat by beat. Do not take "
           "the dancer's body, face, hair, clothes, colours, the room or the camera of @Video 1.")
_KEEP = ("[Keep] Free Fire in-game 3D render style, full body always in frame, static camera at chest height, clear midday light. "
         "No real people, no silhouette, no subtitles, no on-screen text, no watermark.")
PROMPTS = {
    "SOLO": ("[Goal] One Free Fire in-game 3D character, Maxim, dances a trendy TikTok dance in one continuous shot in front of a "
             "house in a small town square.\n[Asset roles]\n@Image 1 is the place: use only the town square, the houses and the light; "
             "not its camera.\n@Image 2 is Maxim: use only his face, silver hair, backwards black cap, black leather jacket over a red "
             "hoodie, ripped brown jeans and sneakers; not the grey background.\n" + _MOTION + "\n" + _KEEP),
    "DUO": ("[Goal] Two Free Fire in-game 3D characters, Maxim (left) and Kelly (right), stand side by side and dance the SAME trendy "
            "TikTok dance in perfect sync in one continuous shot in front of a house in a small town square.\n[Asset roles]\n"
            "@Image 1 is the place: use only the town square, the houses and the light; not its camera.\n"
            "@Image 2 is Kelly: use only her face, short black bob with straight bangs, yellow cropped tracksuit jacket, white top, "
            "yellow pants with black side stripes and white sneakers; not the grey background.\n"
            "@Image 3 is Maxim: use only his face, silver hair, backwards black cap, black leather jacket over a red hoodie, ripped "
            "brown jeans and sneakers; not the grey background.\n" + _MOTION.replace("take the dancer's", "BOTH Maxim and Kelly copy "
            "the one dancer's") + "\nThe two people never swap faces, hair, clothes or places; both dance every move at the same time.\n"
            + _KEEP),
}


def spent(p, pid: int) -> float:
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def estimate() -> float:
    from core import cost
    return cost.seedance_estimate(CANONICAL, TIER, ASPECT, SECS, CUT[1] - CUT[0])


def ref_paths(data_dir: str, pid: int) -> dict:
    d = os.path.join(data_dir, str(pid), "experiments")
    return {"raw": os.path.join(d, "dance_raw_9-14s.mp4"), "bw": os.path.join(d, "dance_bw_9-14s.mp4")}


def make_bw(src: str, out: str) -> None:
    """Bóng người đen trên nền trắng: nền = trung vị 60 khung của CẢ clip (người di chuyển → nền lộ ra), mặt nạ = khác nền > ngưỡng,
    đóng/mở hình thái + giữ vùng lớn nhất (người), làm mượt theo thời gian. Không còn mặt / da / quần áo thật."""
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(SOURCE)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    samples = []
    for i in np.linspace(0, n - 1, 60).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, f = cap.read()
        if ok:
            samples.append(cv2.GaussianBlur(f, (5, 5), 0))
    bg = np.median(np.stack(samples), axis=0).astype(np.uint8)
    cap.release()
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = out + ".raw.mp4"
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    prev = None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        diff = cv2.absdiff(cv2.GaussianBlur(f, (5, 5), 0), bg).max(axis=2)
        m = (diff > 38).astype(np.uint8) * 255
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k, iterations=2)
        cnt, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        if cnt > 1:
            big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            m = np.where(lab == big, 255, 0).astype(np.uint8)
            cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            m = cv2.drawContours(np.zeros_like(m), cs, -1, 255, -1)            # lấp lỗ bên trong thân người
        m = cv2.medianBlur(m, 7)
        if prev is not None:
            m = cv2.addWeighted(m, 0.7, prev, 0.3, 0)
        prev = m
        frame = np.full((h, w, 3), 255, np.uint8)
        frame[m > 127] = (0, 0, 0)
        vw.write(frame)
    vw.release()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-an", "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", out], check=True)
    os.remove(tmp)


def cmd_prep(data_dir: str, pid: int) -> dict:
    refs = ref_paths(data_dir, pid)
    os.makedirs(os.path.dirname(refs["raw"]), exist_ok=True)
    if not os.path.exists(refs["raw"]):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(CUT[0]), "-i", SOURCE, "-t", str(CUT[1] - CUT[0]), "-an",
                        "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", refs["raw"]], check=True)
    if not os.path.exists(refs["bw"]):
        make_bw(refs["raw"], refs["bw"])
    print("ref:", refs)
    return refs


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = p.create_project(NAME, created_by="claude-code-dance-ref", game="FF", aspect=ASPECT)
    p.set_project_field(pid, "look", "FF_INGAME")
    for aid in (263, 23, 33):
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    p.conn.commit()
    print("dự án thử:", pid)
    return pid


def _job(test: str, ref: str):
    if test == "DUO":
        return PROMPTS["DUO"], [PLACE, KELLY, MAXIM]
    return PROMPTS["SOLO"], [PLACE, MAXIM]


def cmd_plan(p, data_dir: str, pid: int, test: str, ref_kind: str) -> str:
    refs = cmd_prep(data_dir, pid)
    prompt, images = _job(test, ref_kind)
    for f in images:
        if not os.path.exists(f):
            raise SystemExit("thiếu tài sản: " + f)
    print(prompt, f"\n{len(prompt)} ký tự · ref {refs[ref_kind]}")
    print(f"ước tính ${estimate():.3f} (×1,25 = ${estimate() * 1.25:.3f}); đã chi cả dự án ${spent(p, pid):.2f}")
    return refs[ref_kind]


def cmd_submit(p, data_dir: str, pid: int, test: str, ref_kind: str) -> None:
    from core import budget, cost, experiments
    from core.adapters import factory
    from core.providers import ProviderError
    method = f"{test}_{ref_kind.upper()}"
    items = experiments.load(data_dir, pid)
    if any(e.get("method") == method and e.get("state") != "failed" for e in items):
        print("đã gửi trước đó:", method)
        return
    ref = cmd_plan(p, data_dir, pid, test, ref_kind)
    prompt, images = _job(test, ref_kind)
    usd = estimate() * 1.25
    if usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: lần này ≈ ${usd:.2f} > trần mỗi bài ${CAP_USD:.2f}")
    booked_s = round(estimate() / cost.clip_price(cost.load_pricing(), CANONICAL, TIER, 1), 2)
    provider = factory.video_provider()
    entry = {"kind": "group_test", "scene": 1, "method": method, "group": 1, "shots": [1], "seconds": SECS, "film_s": SECS,
             "model": CANONICAL, "tier": TIER, "usd": round(estimate(), 3), "prompt": prompt, "external_id": None,
             "state": "running", "file": None, "sequence": 1, "scenes": [1],
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, CANONICAL, TIER, booked_s)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            entry["external_id"] = provider.submit(images[0], prompt, None, SECS, MODEL, aspect_ratio=ASPECT, resolution=TIER,
                                                   reference_only=images, reference_video={"path": ref, "refer_type": "feature"})
            cost.record_usage(p.conn, None, "video", provider.name, CANONICAL, TIER, booked_s, "second", pid)
        except ProviderError as e:
            entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
    items.append(entry)
    experiments._save(data_dir, pid, items)
    print(method, entry["state"], entry["external_id"] or entry.get("message"), "· đã chi:", spent(p, pid))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "prep", "plan", "submit", "poll"))
    ap.add_argument("--test", choices=("SOLO", "DUO"), default="SOLO")
    ap.add_argument("--ref", choices=("raw", "bw"), default="raw")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    if a.step in ("submit", "poll"):
        script_cap.require(a, "dance_ref_test").start()
    from tools.experiments.group_test import cmd_poll, load_env
    load_env(os.getcwd())
    data_dir = os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    if a.step == "setup":
        setup(p)
        return
    {"prep": lambda: cmd_prep(data_dir, a.project),
     "plan": lambda: cmd_plan(p, data_dir, a.project, a.test, a.ref),
     "submit": lambda: cmd_submit(p, data_dir, a.project, a.test, a.ref),
     "poll": lambda: cmd_poll(p, data_dir, a.project)}[a.step]()


if __name__ == "__main__":
    main()
