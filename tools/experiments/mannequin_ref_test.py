"""Thử video tham chiếu MANNEQUIN qua API (người dùng duyệt 01/10, "2 đi") — Seedance 2.5 nhận ref không mặt trên web ClipAI; bài này
xem đường API có nhận không và màu → nhân vật có theo không (đỏ → Kelly, trắng xám → Maxim). Khuôn T3 của kenta_skill_test.py
(reference_only: bối cảnh + mỗi người một ảnh, không khung đầu) + 1 đoạn 5 s cắt từ clip mannequin của người dùng.

    py <đường dẫn>/tools/experiments/mannequin_ref_test.py setup              tạo dự án thử (0 USD) — in mã dự án
    py <đường dẫn>/tools/experiments/mannequin_ref_test.py --project N plan   cắt đoạn ref, in prompt + giá (không gửi)
    py <đường dẫn>/tools/experiments/mannequin_ref_test.py --project N submit gửi 1 clip (qua trần riêng + trần chung + sổ chi)
    py <đường dẫn>/tools/experiments/mannequin_ref_test.py --project N poll   tải clip về <data>/<pid>/experiments/

Chạy từ D:\\AI-Video-Pipeline (dùng code + CSDL ở thư mục hiện tại)."""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

NAME = "Thử ref mannequin Seedance 2.5 (01/10)"
CAP_USD = 2.0                    # trần cứng của bài: 1 clip 5 s ≈ 1,38 USD (công thức giá web) × 1,25 dự phòng ≈ 1,73
MODEL, CANONICAL, TIER, SECS, ASPECT = "seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 5, "16:9"
SOURCE = os.path.join("KHO TÀI NGUYÊN", "video ref test", "SeaTalk_VDO_20261001_111440.mp4")   # 14,08 s, 1280×720, 24 fps, SAR 1:1
CUT = (4.0, 9.0)                 # Maxim bước vào từ trái, cả hai mannequin trong khung toàn cảnh
ASSETS = [os.path.join("data", "assets", "263", "5.png"),     # Tháp Đồng Hồ — thay phông xanh
          os.path.join("data", "assets", "23", "10.png"),     # KELLY
          os.path.join("data", "assets", "33", "7.png")]      # MAXIM
PROMPT = (
    "[Goal] Two Free Fire in-game 3D characters in one continuous shot on a grass field: Kelly dances playfully, Maxim walks in "
    "from the left and stops near her.\n"
    "[Asset roles]\n"
    "@Image 1 is the place: use only the grass field, the red-roof brick house, the trees, the low brick wall and the clear midday "
    "light; not its camera.\n"
    "@Image 2 is Kelly: use only her face, short black bob with straight bangs, black choker, yellow cropped tracksuit jacket, white "
    "top, yellow pants with black side stripes and white sneakers; not the grey background.\n"
    "@Image 3 is Maxim: use only his face, silver hair, backwards black cap, black leather jacket over a red hoodie, ripped brown "
    "jeans with a wallet chain and sneakers; not the grey background.\n"
    "@Video 1 is used only for motion: the red mannequin is Kelly, the white-grey mannequin is Maxim. Take their body movement, "
    "positions, walking path and timing, and the camera framing and movement. Do not take the mannequins' bodies, faces, colours or "
    "materials, the green background, or the sound of @Video 1.\n"
    "The two people never swap faces, hair, clothes or places.\n"
    "[Keep] Kelly's and Maxim's identities and clothes, only these two people, the Free Fire in-game 3D render style. No green "
    "screen anywhere, no mannequin, no subtitles, no on-screen text, no watermark.")


def spent(p, pid: int) -> float:
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def estimate() -> float:
    from core import cost
    return cost.seedance_estimate(CANONICAL, TIER, ASPECT, SECS, CUT[1] - CUT[0])


def ref_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "experiments", "mannequin_ref_4-9s.mp4")


def cut_ref(data_dir: str, pid: int) -> str:
    """The 5 s piece, no sound (the prompt says not to take it), square pixels (ClipAI refuses others)."""
    out = ref_path(data_dir, pid)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(CUT[0]), "-i", SOURCE, "-t", str(CUT[1] - CUT[0]), "-an",
                        "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
    return out


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = p.create_project(NAME, created_by="claude-code-mannequin-ref", game="FF", aspect=ASPECT)
    p.set_project_field(pid, "look", "FF_INGAME")
    for aid in (263, 23, 33):
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    p.conn.commit()
    print("dự án thử:", pid)
    return pid


def cmd_plan(p, data_dir: str, pid: int) -> str:
    for f in ASSETS + [SOURCE]:
        if not os.path.exists(f):
            raise SystemExit("thiếu tài sản: " + f)
    ref = cut_ref(data_dir, pid)
    print(PROMPT, f"\n{len(PROMPT)} ký tự · ref {ref}")
    print(f"ước tính ${estimate():.3f} (×1,25 dự phòng = ${estimate() * 1.25:.3f}); đã chi ${spent(p, pid):.2f} / trần ${CAP_USD:.2f}")
    return ref


def cmd_submit(p, data_dir: str, pid: int) -> None:
    from core import budget, cost, experiments
    from core.adapters import factory
    from core.providers import ProviderError
    items = experiments.load(data_dir, pid)
    if any(e.get("method") == "MANNEQUIN" and e.get("state") != "failed" for e in items):
        print("đã gửi trước đó")
        return
    ref = cmd_plan(p, data_dir, pid)
    usd = estimate() * 1.25
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: đã chi ${s:.2f} + lần này ≈ ${usd:.2f} > trần ${CAP_USD:.2f}")
    # the ledger prices Seedance per output second (0,23); the web price adds the reference video's seconds → book the
    # equivalent seconds so the ledger matches what ClipAI charges (known gap: TODO "sổ chi thiếu giây video tham chiếu")
    booked_s = round(estimate() / cost.clip_price(cost.load_pricing(), CANONICAL, TIER, 1), 2)
    provider = factory.video_provider()
    entry = {"kind": "group_test", "scene": 1, "method": "MANNEQUIN", "group": 1, "shots": [1], "seconds": SECS, "film_s": SECS,
             "model": CANONICAL, "tier": TIER, "usd": round(estimate(), 3), "prompt": PROMPT, "external_id": None,
             "state": "running", "file": None, "sequence": 1, "scenes": [1],
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, CANONICAL, TIER, booked_s)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            entry["external_id"] = provider.submit(ASSETS[0], PROMPT, None, SECS, MODEL, aspect_ratio=ASPECT, resolution=TIER,
                                                   reference_only=ASSETS, reference_video={"path": ref, "refer_type": "feature"})
            cost.record_usage(p.conn, None, "video", provider.name, CANONICAL, TIER, booked_s, "second", pid)
        except ProviderError as e:
            entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
    items.append(entry)
    experiments._save(data_dir, pid, items)
    print("MANNEQUIN", entry["state"], entry["external_id"] or entry.get("message"), "· đã chi:", spent(p, pid))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "plan", "submit", "poll"))
    a = ap.parse_args()
    from tools.experiments.group_test import cmd_poll, load_env
    load_env(os.getcwd())
    data_dir = os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))
    if a.step == "setup":
        setup(p)
        return
    {"plan": lambda: cmd_plan(p, data_dir, a.project),
     "submit": lambda: cmd_submit(p, data_dir, a.project),
     "poll": lambda: cmd_poll(p, data_dir, a.project)}[a.step]()


if __name__ == "__main__":
    main()
