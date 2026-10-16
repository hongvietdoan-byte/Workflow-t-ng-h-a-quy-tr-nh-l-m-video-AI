"""Thử V2V từ previs one-shot (người dùng duyệt 16/10 "thử đi", bản đánh giá docs/DANH_GIA_CHIA_VAI_SAN_KHAU_2026-10-16.md mục 4):
5 s previs clay shot 6–9 #31 (10–15 s: Kelly chạy ra khoảng trống trung tâm mê cung, khựng lại trước xe nôi) làm video tham chiếu +
ảnh nền plate 3D đêm của shot 8 + Kelly + dạng bóng mờ + xe nôi → Seedance 2.5 720p 9:16. Câu hỏi cần trả lời: model có theo ĐƯỜNG
MÁY của ref không (01/10 chỉ thấy theo động tác mannequin). Khuôn của mannequin_ref_test.py (dự án thử riêng, trần riêng + trần chung +
sổ chi).

    py <đường dẫn>/tools/experiments/previs_v2v_test.py setup                         tạo dự án thử (0 USD) — in mã dự án
    py <đường dẫn>/tools/experiments/previs_v2v_test.py --project N plan              cắt đoạn ref, in prompt + giá (không gửi)
    py <đường dẫn>/tools/experiments/previs_v2v_test.py --project N submit --max-usd 2 gửi 1 clip
    py <đường dẫn>/tools/experiments/previs_v2v_test.py --project N poll              tải clip về <data>/<pid>/experiments/

Chạy từ D:\\AI-Video-Pipeline (dùng code + CSDL ở thư mục hiện tại)."""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

NAME = "Thử V2V previs one-shot #31 shot 7–8 (16/10)"
CAP_USD = 3.5                    # trần cứng của dự án thử: 2 lượt (clay + depth) × 1 clip 5 s + 5 s ref ≈ 1,38 USD / lượt
MODEL, CANONICAL, TIER, SECS, ASPECT = "seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 5, "9:16"
SOURCES = {r: os.path.join("D:" + os.sep, "AI-Video-Output", "2026-10-15_du-an-31", "previs",
                           f"previs_canh2_shot6-9_xoay60_them7s3_7sau_trai_{r}.mp4")
           for r in ("clay", "depth")}   # 720×1280, 24 fps, SAR 1:1 (người dùng duyệt 16/10)
REF = "clay"                     # --ref (người dùng 16/10 lượt 2: depth thay clay — lượt clay theo động tác, KHÔNG theo đường máy)
METHOD = {"clay": "PREVIS_V2V", "depth": "PREVIS_V2V_DEPTH"}
CUT = (10.0, 15.0)               # cuối shot 7 (chạy ra khoảng trống) → shot 8 (khựng lại trước xe nôi), máy bám sau lưng chếch trái
ASSETS = [os.path.join("data", "_plates3d", "cache", "2764ab272dd78733cfe6", "plate.png"),   # nền: trung tâm mê cung Cổng Trời, đêm
          os.path.join("data", "assets", "23", "10.png"),       # KELLY (bộ chuẩn 1, không súng, người dùng duyệt)
          os.path.join("data", "assets", "427", "1.png"),       # BÓNG MỜ THẾ GIỚI SONG SONG (dạng bóng mờ phát sáng)
          os.path.join("data", "assets", "442", "2.png")]       # XE NÔI BỊ NGUYỀN (nền sạch)
ASSET_IDS = (265, 23, 427, 442)
PROMPT = (
    "[Goal] One continuous shot of a Free Fire in-game 3D character at night in a hedge maze of the parallel world: Kelly, in her "
    "glowing translucent ghost form, runs out of the maze corridor into the open centre, slows down and stops, startled, in front of "
    "a cursed baby carriage that rocks by itself. The camera follows close behind her, low, slightly over her left shoulder.\n"
    "[Asset roles]\n"
    "@Image 1 is the place: use only the dark hedge maze, the stone floor, the night sky and the cold blue moonlight; not its camera.\n"
    "@Image 2 is Kelly: use only her face, short black bob with straight bangs, black choker, yellow cropped tracksuit jacket, white "
    "top, yellow pants with black side stripes and white sneakers; not the grey background.\n"
    "@Image 3 is only the ghost look: Kelly's whole body is a glowing translucent blue-red silhouette like this; do not take the "
    "game HUD, buttons, map, text, the house or the camera of @Image 3.\n"
    "@Image 4 is the cursed baby carriage: an old black Victorian pram with a torn lace hood, red inside, a stitched doll and a faint "
    "red glow; not the grey background.\n"
    "@Video 1 is used only for motion and camera: the orange figure is Kelly, the beige cylinder is the baby carriage, the grey blocks "
    "are the hedges. Take Kelly's running path, speed, stop and timing, and EXACTLY the camera position, height, path, turns and "
    "framing of @Video 1. Do not take the clay bodies, colours or materials, or the grey sky of @Video 1.\n"
    "[Keep] Only Kelly and the carriage, Kelly's identity and clothes inside the ghost glow, the Free Fire in-game 3D render style, "
    "dark night mood. No game HUD, no subtitles, no on-screen text, no watermark.")
CLAY_ROLE = PROMPT[PROMPT.index("@Video 1 is"):PROMPT.index("[Keep]")]
DEPTH_ROLE = (
    "@Video 1 is a depth map used only for scene structure, motion and camera: brighter is nearer the camera, darker is farther, black "
    "is the sky. The tall shape just in front of the camera is Kelly, the short round shape is the baby carriage, the walls are the "
    "hedges. Follow EXACTLY the camera position, height, path, turns and framing of @Video 1 frame by frame, and Kelly's running path, "
    "speed, stop and timing. Do not take its black-and-white look.\n")


def prompt() -> str:
    return PROMPT if REF == "clay" else PROMPT.replace(CLAY_ROLE, DEPTH_ROLE)


def spent(p, pid: int) -> float:
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def estimate() -> float:
    from core import cost
    return cost.seedance_estimate(CANONICAL, TIER, ASPECT, SECS, CUT[1] - CUT[0])


def ref_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "experiments", f"previs_{REF}_10-15s.mp4")


def cut_ref(data_dir: str, pid: int) -> str:
    """Đoạn 5 s, không tiếng, điểm ảnh vuông (ClipAI từ chối loại khác)."""
    out = ref_path(data_dir, pid)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(CUT[0]), "-i", SOURCES[REF], "-t", str(CUT[1] - CUT[0]), "-an",
                        "-vf", "setsar=1", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], check=True)
    return out


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    pid = p.create_project(NAME, created_by="claude-code-previs-v2v", game="FF", aspect=ASPECT)
    p.set_project_field(pid, "look", "FF_INGAME")
    for aid in ASSET_IDS:
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    p.conn.commit()
    print("dự án thử:", pid)
    return pid


def cmd_plan(p, data_dir: str, pid: int) -> str:
    for f in ASSETS + [SOURCES[REF]]:
        if not os.path.exists(f):
            raise SystemExit("thiếu tài sản: " + f)
    ref = cut_ref(data_dir, pid)
    print(prompt(), f"\n{len(prompt())} ký tự · ref {ref}")
    print(f"ước tính ${estimate():.3f} (×1,25 dự phòng = ${estimate() * 1.25:.3f}); đã chi ${spent(p, pid):.2f} / trần ${CAP_USD:.2f}")
    return ref


def cmd_submit(p, data_dir: str, pid: int) -> None:
    from core import budget, cost, experiments
    from core.adapters import factory
    from core.providers import ProviderError
    items = experiments.load(data_dir, pid)
    if any(e.get("method") == METHOD[REF] and e.get("state") != "failed" for e in items):
        print("đã gửi trước đó")
        return
    ref = cmd_plan(p, data_dir, pid)
    usd = estimate() * 1.25
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: đã chi ${s:.2f} + lần này ≈ ${usd:.2f} > trần ${CAP_USD:.2f}")
    # sổ chi tính Seedance theo giây ra (giá / giây); giá web cộng giây video tham chiếu → ghi số giây tương đương (như mannequin_ref_test)
    booked_s = round(estimate() / cost.clip_price(cost.load_pricing(), CANONICAL, TIER, 1), 2)
    provider = factory.video_provider()
    entry = {"kind": "group_test", "scene": 1, "method": METHOD[REF], "group": 1, "shots": [1], "seconds": SECS, "film_s": SECS,
             "model": CANONICAL, "tier": TIER, "usd": round(estimate(), 3), "prompt": prompt(), "external_id": None,
             "state": "running", "file": None, "sequence": 1, "scenes": [1],
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, CANONICAL, TIER, booked_s)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            entry["external_id"] = provider.submit(ASSETS[0], prompt(), None, SECS, MODEL, aspect_ratio=ASPECT, resolution=TIER,
                                                   reference_only=ASSETS, reference_video={"path": ref, "refer_type": "feature"})
            cost.record_usage(p.conn, None, "video", provider.name, CANONICAL, TIER, booked_s, "second", pid)
        except ProviderError as e:
            entry.update(state="failed", message=f"[{e.code}] {e}"[:400], usd=0.0)
    items.append(entry)
    experiments._save(data_dir, pid, items)
    print(METHOD[REF], entry["state"], entry["external_id"] or entry.get("message"), "· đã chi:", spent(p, pid))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "plan", "submit", "poll"))
    ap.add_argument("--ref", choices=("clay", "depth"), default="clay", help="video tham chiếu: previs clay hoặc depth")
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    a = ap.parse_args()
    script_cap.require(a, "previs_v2v_test").start()
    global REF
    REF = a.ref
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
