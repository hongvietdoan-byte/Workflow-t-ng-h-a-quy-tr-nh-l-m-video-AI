"""S4.11 Chế độ bản mẫu + S4.12 Sửa clip (Advanced Edit) — thử có trả tiền (người dùng duyệt 01/10; trần nhánh CAP_USD, 0 ảnh Deepix,
0 Claude). Tham số API đọc từ mã web ClipAI (docs/KET_QUA_S4_11_S4_12_2026-10-01.md). Không sửa dữ liệu dự án #1–#13: đọc clip / ảnh
của #8, mọi lần gửi ghi sổ chi vào dự án thử mới, kết quả ở OUT.

    py tools/experiments/s411_s412_test.py setup                  dự án thử (0 USD) — in mã dự án
    py tools/experiments/s411_s412_test.py --project N sample     bản mẫu 480p 4 s cận Kelly (#8 shot 1, khung đầu = storyboard job 369)
    py tools/experiments/s411_s412_test.py --project N final      bản cuối 1080p từ bản mẫu (bị trần chặn nếu không đủ tiền)
    py tools/experiments/s411_s412_test.py --project N final_probe  gửi bản cuối với mã bản mẫu KHÔNG tồn tại: xem API có hiểu `draft_task`
    py tools/experiments/s411_s412_test.py --project N edit_prep  cắt 4 s đầu clip nhóm 01 của #8 + ảnh mặt Kelly sau điểm cắt (0 USD)
    py tools/experiments/s411_s412_test.py --project N edit       sửa clip 480p (cận Kelly kiểu anime → kiểu render 3D như sau điểm cắt)
    py tools/experiments/s411_s412_test.py --project N usage EXT  đọc token ClipAI tính cho một task (0 USD)

Chạy từ D:\\AI-Video-Pipeline (token qua group_test.load_env)."""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

NAME = "Thử S4.11 bản mẫu + S4.12 sửa clip (01/10)"
CAP_USD = 1.5
MODEL = "dreamina-seedance-2-5-260628"
OUT = r"D:\AI-Video-Output\2026-10-01_s4-11_s4-12"
P8 = os.path.join("data", "projects", "8")
FIRST_FRAME = os.path.join(P8, "images", "job_369.png")           # #8 shot 1 storyboard (CU Kelly, render 3D) — read only
SOURCE = os.path.join(P8, "videos", "01_group.mp4")               # #8 group clip: 0–1.08 s = the anime-looking Kelly close-up (lỗi 1.3)
STATE = os.path.join(OUT, "state.json")
ENV = {"FEATURE_SEEDANCE_SAMPLE_MODE": "1", "FEATURE_SEEDANCE_VIDEO_EDIT": "1"}

SAMPLE_PROMPT = (
    "@Image 1 is the first frame: keep this girl's face, hair, choker, the 3D game-render look, the framing and the night light. "
    "Close-up, eye level, the camera stays still. In the dark, a tear rolls slowly down her left cheek; her eyes stay red-rimmed and "
    "glassy, fixed straight at the camera, unblinking; her lower lip presses tight; her chin lowers slightly. By the end the tear has "
    "reached her jawline. Photoreal 3D game render, not anime, not an illustration.")

EDIT_PROMPT = (
    "Edit @Video 1. @Video 1 is the only editing master.\n"
    "The only change: the first shot, from 0 s until the cut at about 1 s — the extreme close-up of the girl with the short dark bob, "
    "the black choker and the yellow jacket collar. Redraw her face in the same 3D game-render style she has after the cut: the same "
    "face shape, eye size and shape, skin texture and night lighting as in @Image 1. Not anime, not doll-like: no oversized eyes, no "
    "glossy doll skin. Keep her sad, teary expression, the tear on her cheek, her head position, the framing and the moment of the cut.\n"
    "@Image 1 is used only for her face and hair as they look after the cut; do not take its framing or background.\n"
    "Everything else in @Video 1 stays exactly as it is: the shot after the cut, the man with the blue scarf, every pose, motion, "
    "framing, camera move, background, light and the cut timing.")


def _p():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    os.environ.update(ENV)
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


def state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(**kw):
    s = state()
    s.update(kw)
    os.makedirs(OUT, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)


def spent(p, pid):
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def guard(p, pid, usd, what):
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN ({what}): đã chi ${s:.2f} + ≈ ${usd:.2f} > trần ${CAP_USD:.2f} — không gửi")
    print(f"trần nhánh: đã chi ${s:.2f}, lần này ≈ ${usd:.2f}, còn ${CAP_USD - s - usd:.2f}")


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return
    pid = p.create_project(NAME, created_by="claude-code-s411", game="FF", aspect="9:16")
    print("dự án thử:", pid)


def _send(p, pid, provider, tier, seconds, usd, what, fn):
    """Cap check (branch + shared trial budget) → send → ledger, under the shared spend lock."""
    from core import budget
    from core.cost import record_usage
    from core.providers import ProviderError
    guard(p, pid, usd, what)
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, MODEL, tier, seconds)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        sent_at = time.time()
        try:
            ext = fn()
        except ProviderError as e:
            print(f"ClipAI từ chối (0 USD, không ghi sổ): [{e.code}] {e}")
            return None, sent_at
        record_usage(p.conn, None, "video", provider.name, MODEL, tier, seconds, "second", pid)
    print("đã gửi:", ext)
    return ext, sent_at


def wait(provider, ext, dest, prompt=None, sent_at=None, limit=3000):
    """Poll until done; a short queue id (ClipAI past its 2 parallel tasks) is replaced by the real task found by its prompt."""
    t0 = time.time()
    while time.time() - t0 < limit:
        st = provider.status(ext)
        print(time.strftime("%H:%M:%S"), ext, st.state, flush=True)
        if st.state == "succeeded":
            provider.download(ext, dest)
            print("tải về:", dest)
            return ext, True
        if st.state == "failed":
            real = provider.find_by_prompt(ext, prompt, sent_at) if prompt and sent_at else None
            if real and real != ext:
                print("mã chờ tạm → task thật:", real)
                ext = real
                continue
            print("thất bại:", st.code, st.message)
            return ext, False
        time.sleep(30)
    return ext, False


def show_usage(provider, ext):
    u = provider.task_usage(ext)
    print("ClipAI tính:", json.dumps(u, ensure_ascii=False))
    return u


def sample(p, pid):
    from core import cost
    from core.adapters import factory
    if state().get("sample"):
        raise SystemExit("đã gửi bản mẫu: " + state()["sample"] + " — không gửi lại (tránh trả 2 lần)")
    usd = cost.seedance_estimate(MODEL, "480p", "9:16", 4)
    provider = factory.video_provider()
    ext, sent_at = _send(p, pid, provider, "480p", 4, usd, "bản mẫu 480p",
                         lambda: provider.submit(FIRST_FRAME, SAMPLE_PROMPT, None, 4, "seedance-2.5", aspect_ratio="9:16",
                                                 resolution="480p", draft=True))
    if not ext:
        return
    save(sample=ext, sample_sent_at=sent_at, sample_estimate=usd)
    ext, ok = wait(provider, ext, os.path.join(OUT, "s411_ban_mau_480p.mp4"), SAMPLE_PROMPT, sent_at)
    save(sample=ext)
    save(sample_usage=show_usage(provider, ext))
    print("đã chi (sổ):", spent(p, pid))


def final(p, pid):
    from core import cost
    from core.adapters import factory
    s = state()
    if not s.get("sample"):
        raise SystemExit("chưa có bản mẫu")
    if s.get("final"):
        raise SystemExit("đã gửi bản cuối: " + s["final"])
    usd = cost.seedance_estimate(MODEL, "1080p", "9:16", 4)
    provider = factory.video_provider()
    ext, sent_at = _send(p, pid, provider, "1080p", 4, usd, "bản cuối 1080p",
                         lambda: provider.submit_final_from_sample(s["sample"]))
    if not ext:
        return
    save(final=ext)
    ext, ok = wait(provider, ext, os.path.join(OUT, "s411_ban_cuoi_1080p.mp4"))
    save(final_usage=show_usage(provider, ext))


def final_probe(p, pid):
    """A final from a sample id that does not exist: a refusal naming the sample = the API reads `draft_task` (0 USD)."""
    from core.adapters import factory
    from core.providers import ProviderError
    provider = factory.video_provider()
    try:
        ext = provider.submit_final_from_sample("seedance:cgt-20000101000000-zzzzz")
    except ProviderError as e:
        print(f"ClipAI trả lời (không tạo task): [{e.code}] {e}")
        save(final_probe=str(e))
        return
    print("CÓ TASK ĐƯỢC TẠO (không mong đợi):", ext)
    save(final_probe_task=ext)
    from core.cost import record_usage
    record_usage(p.conn, None, "video", provider.name, MODEL, "1080p", 4, "second", pid)


def edit_prep():
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(OUT, "s412_nguon_4s.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SOURCE, "-t", "4.0", "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-r", "24", src], check=True)
    face = os.path.join(OUT, "s412_mat_kelly_sau_cat.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.6", "-i", SOURCE, "-frames:v", "1",
                    "-vf", "crop=320:480:40:260,scale=640:960:flags=lanczos", face], check=True)
    print(src, face)


def edit(p, pid):
    from core import cost
    from core.adapters import factory
    from core.adapters.clipai import _probe_video
    if state().get("edit"):
        raise SystemExit("đã gửi sửa clip: " + state()["edit"] + " — không gửi lại")
    src = os.path.join(OUT, "s412_nguon_4s.mp4")
    face = os.path.join(OUT, "s412_mat_kelly_sau_cat.png")
    if not (os.path.exists(src) and os.path.exists(face)):
        raise SystemExit("chạy edit_prep trước")
    secs = _probe_video(src).get("duration") or 4.0
    usd = cost.seedance_estimate(MODEL, "480p", "9:16", secs, secs)
    provider = factory.video_provider()
    ext, sent_at = _send(p, pid, provider, "480p_edit", round(2 * secs, 2), usd, "sửa clip 480p",
                         lambda: provider.submit_video_edit(src, EDIT_PROMPT, "480p", [face]))
    if not ext:
        return
    save(edit=ext, edit_sent_at=sent_at, edit_estimate=usd)
    ext, ok = wait(provider, ext, os.path.join(OUT, "s412_sau_sua_480p.mp4"), EDIT_PROMPT, sent_at)
    save(edit=ext)
    save(edit_usage=show_usage(provider, ext))
    print("đã chi (sổ):", spent(p, pid))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "sample", "final", "final_probe", "edit_prep", "edit", "usage"))
    ap.add_argument("ext", nargs="?")
    a = ap.parse_args()
    p = _p()
    if a.step == "setup":
        setup(p)
    elif a.step == "edit_prep":
        edit_prep()
    elif a.step == "usage":
        from core.adapters import factory
        show_usage(factory.video_provider(), a.ext)
    else:
        if not a.project:
            raise SystemExit("cần --project")
        {"sample": sample, "final": final, "final_probe": final_probe, "edit": edit}[a.step](p, a.project)


if __name__ == "__main__":
    main()
