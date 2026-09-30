"""S4.7 + S4.10 — thử có trả tiền (người dùng duyệt 01/10; nhánh A2, trần riêng CAP_USD video + ảnh, ≤ MAX_IMAGES ảnh, không gọi Claude).

S4.7  Kho chủ thể ClipAI thay mẹo dấu đỏ trên mắt (P2m): tải ẢNH KHÔNG ĐÁNH DẤU (khung storyboard + ảnh định danh) lên kho chủ thể
      (core.subjects.ensure_picture: nhớ theo sha256, không tải lại), gửi Seedance bằng asset:// (chế độ chỉ ảnh tham chiếu).
S4.10 A/B cùng đầu vào: Seedance 2.5 720P vs Seedance 2.0 Fast 720P — shot thoại cận của Kelly (#8 cảnh 158, "Anh nói sẽ không để mất
      em…", có tham chiếu âm thanh tiếng Việt = giọng của shot đặt đúng giờ). Mốc so miễn phí: clip #8 cùng shot (Fast, P2m).

    py <worktree>/tools/experiments/s47_s410_test.py setup                dự án thử MỚI + chép khung/giọng của #8 (chỉ đọc #8) — 0 USD
    py <worktree>/tools/experiments/s47_s410_test.py --project N subjects  tải ảnh lên kho chủ thể (không tính tiền video) + in trạng thái
    py <worktree>/tools/experiments/s47_s410_test.py --project N plan A25  in prompt + tài sản + giá (provider giả, 0 USD)
    py <worktree>/tools/experiments/s47_s410_test.py --project N submit A25   gửi 1 clip (trần nhánh + trần chung + sổ chi), không gửi lại
    py <worktree>/tools/experiments/s47_s410_test.py --project N poll A25     chờ + nối mã chờ tạm → task thật + tải về
    py <worktree>/tools/experiments/s47_s410_test.py --project N measure      đo khớp môi / nhìn / chuyển động + tờ khung so sánh

Chạy từ D:\\AI-Video-Pipeline (CSDL thật, token qua group_test.load_env)."""
import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NAME = "Thử S4.7 kho chủ thể + S4.10 A/B 2.5/Fast (01/10)"
CAP_USD = 2.5                   # nhánh A2: video + ảnh
MAX_IMAGES = 6
ASSETS = (23, 24)               # KELLY, KENTA
SRC_PID, SRC_SCENE, SRC_IDX = 8, 158, 21            # #8 shot 21: Kelly MCU, nói với Kenta (ảnh job 377, giọng lipsync/shot_158.wav)
SRC_FRAME = os.path.join("data", "projects", "8", "images", "job_377.png")
SRC_VOICE = os.path.join("data", "projects", "8", "lipsync", "shot_158.wav")
SRC_CLIP = os.path.join("data", "projects", "8", "videos", "21_raw.mp4")      # mốc so: #8, Seedance Fast, P2m (dấu đỏ) + cùng giọng
LINE = "Anh nói sẽ không để mất em…"
TURNS = [{"speaker": "KELLY", "start": 0.3, "end": 2.34}]          # lipsync/index.json offsets [0.3] + 2,037 s câu thoại
OUT = r"D:\AI-Video-Output\2026-10-01_s4-7_s4-10"
DATA = os.path.join("data", "projects")
SHOT = {"shot_no": 1, "size": "MCU", "angle": "eye", "camera_move": "static", "duration_s": 4.0, "characters": ["KELLY", "KENTA"],
        "dialogue": [{"speaker": "KELLY", "text": LINE}], "source": "#8 cảnh 158 (shot 21)"}
CASES = {   # case: (model alias, canonical, tier, seconds, pictures)  — pictures: "subjects" = asset://, "marked" = P2m (local, dấu đỏ)
    "A25": ("seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 4, "subjects"),
    "BF": ("seedance-fast", "dreamina-seedance-2-0-fast-260128", "720p", 4, "subjects"),
    # gen lại lần 1 (đổi đầu vào có lý do): A25 mở miệng trễ ~1,3 s so với giọng → thêm khối khớp môi + mốc giây của S4.2
    # (dialogue_take.group_block — cách (c) đã cho 0,72–0,96 ở #10); 2.5 theo mốc giây nguyên, Fast thì không (tài liệu ClipAI)
    "A25t": ("seedance-2.5", "dreamina-seedance-2-5-260628", "720p", 4, "subjects"),
}
TIMELINE_CASES = {"A25t"}


def _p():
    from tools.experiments.group_test import load_env
    load_env(os.getcwd())
    # the models live outside git in the main checkout's data/models (this script's code may run from a worktree)
    for var, name in (("FACE_MODEL", "face_detection_yunet_2023mar.onnx"), ("LIP_MODEL", "face_landmarker.task")):
        path = os.path.abspath(os.path.join("data", "models", name))
        if not os.environ.get(var) and os.path.exists(path):
            os.environ[var] = path
    from core.db import connect
    from core.pipeline import Pipeline
    return Pipeline(connect(os.environ.get("PIPELINE_DB") or os.path.join("data", "manifest.sqlite")))


def work(pid):
    return os.path.join(DATA, str(pid), "s47")


def state_path(pid):
    return os.path.join(work(pid), "state.json")


def load_state(pid):
    try:
        with open(state_path(pid), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}


def save_state(pid, st):
    with open(state_path(pid), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def spent(p, pid):
    from core import project_budget
    return round(sum(project_budget.spent_by_stage(p.conn, pid).values()), 4)


def images_made(p, pid):
    return p.conn.execute("SELECT COUNT(*) FROM usage_events WHERE project_id=? AND kind='image'", (pid,)).fetchone()[0]


def guard(p, pid, usd, what):
    s = spent(p, pid)
    if s + usd > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN NHÁNH CHẶN ({what}): đã chi ${s:.2f} + ≈ ${usd:.2f} > trần ${CAP_USD:.2f}")
    if images_made(p, pid) > MAX_IMAGES:
        raise SystemExit(f"TRẦN ẢNH: đã {images_made(p, pid)} ảnh > {MAX_IMAGES}")
    print(f"trần nhánh: đã chi ${s:.2f}, lần này ≈ ${usd:.2f}, còn ${CAP_USD - s - usd:.2f}")


def setup(p):
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (NAME,)).fetchone()
    if row:
        print("đã có dự án:", row["id"])
        return row["id"]
    for f in (SRC_FRAME, SRC_VOICE, SRC_CLIP):
        if not os.path.exists(f):
            raise SystemExit("thiếu: " + f)
    pid = p.create_project(NAME, created_by="claude-code-s47", game="FF", aspect="9:16")
    p.set_project_field(pid, "look", "FF_INGAME")
    for aid in ASSETS:
        p.conn.execute("INSERT OR IGNORE INTO project_assets (project_id, asset_id) VALUES (?, ?)", (pid, aid))
    sid = p.create_scene(pid, 1, "Shot 1 — Kelly MCU thoại")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(SHOT, ensure_ascii=False), sid))
    p.conn.commit()
    os.makedirs(work(pid), exist_ok=True)
    shutil.copy2(SRC_FRAME, os.path.join(work(pid), "frame_8_158.png"))
    shutil.copy2(SRC_VOICE, os.path.join(work(pid), "voice_8_158.wav"))
    print("dự án thử:", pid)
    return pid


def pictures(p, pid):
    """[(label, unmarked copy ≤ 1280 px), …] — @Image 1 the storyboard frame, @Image 2 Kelly's identity picture (the pipeline's pick)."""
    from core import seedance_refs
    rows = [{"id": None, "data": SHOT}]
    ids = seedance_refs.identity_pictures(p.conn, pid, rows, 8)
    kelly = next((path for n, path in ids if n == "KELLY"), None)
    if not kelly:
        raise SystemExit("KELLY chưa có ảnh định danh trong dự án thử (gắn tài nguyên 23)")
    out = os.path.join(work(pid), "clean")
    frame = seedance_refs.mark(os.path.join(work(pid), "frame_8_158.png"), out, style="none")
    face = seedance_refs.mark(kelly, out, style="none")
    return [("FF_storyboard_8_158", frame), ("FF_KELLY", face)], kelly


def marked(p, pid):
    from core import seedance_refs
    pics, _ = pictures(p, pid)
    out = os.path.join(work(pid), "marked")
    return [seedance_refs.mark(src if "storyboard" not in lab else os.path.join(work(pid), "frame_8_158.png"), out)
            for lab, src in pics]


def subjects_step(p, pid):
    from core import subjects
    from core.adapters import factory
    lib = factory.subject_library()
    if lib is None:
        raise SystemExit("chưa có thư viện chủ thể (VIDEO_PROVIDER / SUBJECT_PROVIDER)")
    pics, src = pictures(p, pid)
    print("ảnh định danh Kelly (nguồn):", src)
    t0 = time.time()
    res = subjects.picture_refs(p.conn, lib, pics)
    print(f"xong sau {time.time() - t0:.0f} s")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    for lab, path in pics:
        print(lab, path, subjects.picture_row(p.conn, subjects.picture_sha(path)))
    st = load_state(pid)
    st["subjects"] = res
    save_state(pid, st)


def prompt(p, pid, case=None):
    from core import dialogue_take, looks
    look = looks.video_sentence(p.project(pid))
    if case in TIMELINE_CASES:
        segs = [{"speaker": "KELLY", "text": LINE, "start": TURNS[0]["start"], "end": TURNS[0]["end"]}]
        return "\n".join([
            "@Image 1 is the storyboard frame of this shot: keep its place, framing, light and where each person stands — Kelly facing "
            "the camera, Kenta seen from behind at the right edge of the frame.",
            "@Image 2 is KELLY: keep exactly her face, hair, choker and yellow track suit; take only her look from it, not its background.",
            "One single shot, no cuts. " + (look + " " if look else "") + "Kelly, eyes wet, hands held at her chest, looks at Kenta. "
            "Kenta stays still with his back to the camera and does not speak. The camera stays still.",
            dialogue_take.group_block(segs, ["KELLY"])])
    return "\n".join([
        "@Image 1 is the storyboard frame of this shot: keep its place, framing, light and where each person stands — Kelly facing the "
        "camera, Kenta seen from behind at the right edge of the frame.",
        "@Image 2 is KELLY: keep exactly her face, hair, choker and yellow track suit; take only her look from it, not its background.",
        "@Audio 1 is Kelly's voice: she says this line in Vietnamese and her lips move exactly with the voice; nobody else speaks.",
        "One single shot, no cuts. " + (look + " " if look else "") + "Kelly, eyes wet, hands held at her chest, looks at Kenta and "
        f"says: \"{LINE}\" Kenta stays still with his back to the camera. The camera stays still."])


def send_kwargs(p, pid, case):
    alias, canonical, tier, secs, how = CASES[case]
    st = load_state(pid)
    if how == "subjects":
        refs = (st.get("subjects") or {}).get("refs")
        if not refs:
            raise SystemExit("chưa có chủ thể active cho mọi ảnh — chạy bước subjects trước (hoặc kho đã từ chối: xem state.json)")
        ref_only = [{"uri": r["uri"]} for r in refs]
    else:
        ref_only = marked(p, pid)
    return dict(reference_only=ref_only, reference_audio=[os.path.join(work(pid), "voice_8_158.wav")], aspect_ratio="9:16",
                resolution=tier), alias, canonical, tier, secs


def plan(p, pid, case):
    """The real adapter with a transport that answers locally: prints the exact `ctx` ClipAI would receive (0 USD, nothing sent)."""
    import re
    from core import cost
    from core.adapters.clipai import ClipAIVideoProvider
    from core.adapters.http import HttpResponse
    kw, alias, canonical, tier, secs = send_kwargs(p, pid, case)
    text = prompt(p, pid, case)
    print("MODEL:", alias, canonical, tier, secs, "s — giá ≈ $%.2f" % cost.clip_price(cost.load_pricing(), canonical, tier, secs))
    seen = []

    def fake(method, url, headers, body, timeout):
        seen.append(body or b"")
        return HttpResponse(200, json.dumps({"code": 0, "data": {"tasks": [{"task_id": "plan", "task_status": "submitted"}]}}).encode())

    ext = ClipAIVideoProvider("plan-token", "https://clipai.invalid", fake).submit("", text, None, secs, alias, **kw)
    body = seen[0].decode("utf-8", "replace")
    ctx = json.loads(re.search(r'name="ctx"\r\n\r\n(.*?)\r\n--', body, re.S).group(1))
    print("GỬI (giả):", ext, "| file:", re.findall(r'name="(\w+_files)"; filename="([^"]+)"', body))
    print(json.dumps({k: v for k, v in ctx.items() if k != "content"}, ensure_ascii=False))
    for c in ctx["content"]:
        print(" ", c["type"], c.get("role"), (c.get("image_url") or c.get("audio_url") or {}).get("url"), (c.get("text") or "")[:0])
    print(text)


def submit(p, pid, case):
    from core import budget, cost
    from core.adapters import factory
    from core.cost import record_usage
    from core.providers import ProviderError
    st = load_state(pid)
    if (st.get("cases") or {}).get(case, {}).get("ext"):
        raise SystemExit(f"{case} đã gửi ({st['cases'][case]['ext']}) — không gửi lại (tránh trả 2 lần); dùng poll")
    kw, alias, canonical, tier, secs = send_kwargs(p, pid, case)
    text = prompt(p, pid, case)
    usd = cost.clip_price(cost.load_pricing(), canonical, tier, secs)
    guard(p, pid, usd, f"clip {case}")
    provider = factory.video_provider()
    with budget.SPEND_LOCK:
        over = budget.check_video(p.conn, provider.name, canonical, tier, secs)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        sent_at = time.time()
        try:
            ext = provider.submit("", text, None, secs, alias, **kw)
        except ProviderError as e:
            st.setdefault("cases", {})[case] = {"refused": f"[{e.code}] {e}", "at": time.strftime("%Y-%m-%d %H:%M:%S"), "prompt": text}
            save_state(pid, st)
            raise SystemExit(f"ClipAI từ chối lúc tạo (0 USD): [{e.code}] {e}")
        record_usage(p.conn, None, "video", provider.name, canonical, tier, secs, "second", pid)
    st.setdefault("cases", {})[case] = {"ext": ext, "sent_at": sent_at, "prompt": text, "model": canonical, "seconds": secs,
                                        "usd": usd, "pictures": kw["reference_only"]}
    save_state(pid, st)
    print("đã gửi:", ext, f"(≈ ${usd:.2f}); đã chi nhánh: ${spent(p, pid):.2f}")


def poll(p, pid, case, wait_s=2400):
    from core.adapters import factory
    st = load_state(pid)
    rec = (st.get("cases") or {}).get(case)
    if not rec or not rec.get("ext"):
        raise SystemExit(f"{case} chưa gửi")
    provider = factory.video_provider()
    dest = os.path.join(DATA, str(pid), "videos", f"{case}.mp4")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    t0, misses = time.time(), 0
    while time.time() - t0 < wait_s:
        stt = provider.status(rec["ext"])
        print(time.strftime("%H:%M:%S"), rec["ext"], stt.state, stt.error_code or "", flush=True)
        if stt.state == "running" and not provider.memory.state(rec["ext"])[0]:
            misses += 1
            if misses >= 3:                         # queue id: the real task has a NEW id, found by the prompt that was sent
                taken = {c.get("ext") for k, c in (st.get("cases") or {}).items() if k != case}
                real = provider.find_by_prompt(rec["ext"], rec["prompt"], rec["sent_at"], taken)
                if real and real != rec["ext"]:
                    print("mã chờ tạm → task thật:", real)
                    rec.setdefault("queue_ids", []).append(rec["ext"])
                    rec["ext"] = real
                    save_state(pid, st)
                    misses = 0
                    continue
        if stt.state == "succeeded":
            provider.download(rec["ext"], dest)
            rec["file"] = dest
            task, _ = provider._find_ex(rec["ext"], pages=6)
            rec["provider_cost"] = (task or {}).get("cost")
            save_state(pid, st)
            os.makedirs(OUT, exist_ok=True)
            shutil.copy2(dest, os.path.join(OUT, f"{case}.mp4"))
            print("tải về:", dest, "cost ClipAI:", rec["provider_cost"])
            return
        if stt.state == "failed":
            rec["failed"] = f"[{stt.error_code}] {stt.message or ''}"
            save_state(pid, st)
            print("thất bại:", rec["failed"])
            return
        time.sleep(30)
    print("hết giờ chờ — chạy poll lại sau")


def measure(p, pid):
    from core import clip_measure as cm
    st = load_state(pid)
    frame = os.path.join(work(pid), "frame_8_158.png")
    voice = os.path.join(work(pid), "voice_8_158.wav")
    clips = [("base8_fast_p2m", SRC_CLIP)] + [(k, c["file"]) for k, c in (st.get("cases") or {}).items() if c.get("file")]
    res = {}
    for name, clip in clips:
        m = cm.measure(clip, picture=frame, audio=voice, speaking=True, turns=TURNS)
        res[name] = m
        lips = m.get("lips") or {}
        print(name, "cờ:", m["flags"], "| môi:", [(t.get("score"), t.get("wrong_time")) for t in lips.get("turns") or []] or lips.get("note"),
              "| nhìn:", {k: m.get("look", {}).get(k) for k in ("texture_ratio", "saturation_ratio", "flag")},
              "| chuyển động:", {k: m["motion"].get(k) for k in ("jerks", "cuts", "freezes", "median", "flag") if k in m["motion"]},
              "| dấu đỏ:", m["ref_mark"].get("share"))
    for name, clip in clips:                      # how late the mouth is: best mouth ↔ voice correlation over ±1.5 s of shift
        res[name]["lag"] = best_lag(clip, voice)
        print(name, "độ trễ miệng tốt nhất (r, giây):", res[name]["lag"])
    st["measure"] = res
    save_state(pid, st)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "do_luong.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    sheet(clips, voice)


def best_lag(clip, voice):
    """(r, seconds the mouth is later than the voice) of the best-matching shift, first face — the lip_sync score only looks ± 0.17 s."""
    import numpy as np
    from core import clip_measure as cm
    trk, fps, n = cm.mouth_tracks(clip)
    if not trk:
        return None
    env = np.array(cm._voice_envelope(voice, fps, n))
    o = np.array([np.nan if x is None else x for x in trk[0]["open"]], dtype=float)
    best = None
    for lag in range(-int(fps * 1.5), int(fps * 1.5) + 1):
        a, b = o[max(lag, 0): n + min(lag, 0)], env[max(-lag, 0): n - max(lag, 0)]
        m = np.isfinite(a)
        if m.sum() > 10 and np.std(a[m]) > 0 and np.std(b[m]) > 0:
            r = float(np.corrcoef(a[m], b[m])[0, 1])
            if best is None or r > best[0]:
                best = (round(r, 3), round(lag / fps, 2))
    return best


def sheet(clips, voice):
    """One row per clip, 6 frames (0.3 … 3.8 s) + a copy of each clip with the voice mixed in, for a person to watch and listen."""
    import subprocess
    from PIL import Image, ImageDraw
    from core import ffmpeg_studio
    ff = ffmpeg_studio.find_ffmpeg()
    times = [0.3, 0.9, 1.5, 2.1, 2.7, 3.8]
    rows = []
    for name, clip in clips:
        cells = []
        for t in times:
            tmp = os.path.join(OUT, f"_f_{name}_{t}.png")
            subprocess.run([ff, "-v", "error", "-y", "-ss", str(t), "-i", clip, "-frames:v", "1", "-vf", "scale=240:-2", tmp], check=False)
            if os.path.exists(tmp):
                cells.append(Image.open(tmp).convert("RGB"))
                os.remove(tmp)
        if cells:
            rows.append((name, cells))
        subprocess.run([ff, "-v", "error", "-y", "-i", clip, "-i", voice, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-shortest", os.path.join(OUT, f"{name}_co-giong.mp4")], check=False)
    if not rows:
        return
    w, h = rows[0][1][0].size
    im = Image.new("RGB", (w * len(times), (h + 24) * len(rows)), "white")
    d = ImageDraw.Draw(im)
    for r, (name, cells) in enumerate(rows):
        d.text((6, r * (h + 24) + 4), f"{name}   ({', '.join(f'{t:g}s' for t in times)})", fill=(0, 0, 0))
        for c, cell in enumerate(cells):
            im.paste(cell.resize((w, h)), (c * w, r * (h + 24) + 24))
    im.save(os.path.join(OUT, "so_sanh_khung.jpg"), quality=88)
    print("tờ khung:", os.path.join(OUT, "so_sanh_khung.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int)
    ap.add_argument("step", choices=("setup", "pics", "subjects", "plan", "submit", "poll", "measure"))
    ap.add_argument("case", nargs="?", default="A25")
    a = ap.parse_args()
    p = _p()
    if a.step == "setup":
        setup(p)
        return
    if not a.project:
        raise SystemExit("cần --project")
    if a.step in ("plan", "submit", "poll") and a.case not in CASES:
        raise SystemExit(f"case phải là {sorted(CASES)}")
    {"pics": lambda: print(pictures(p, a.project)), "subjects": lambda: subjects_step(p, a.project), "plan": lambda: plan(p, a.project, a.case),
     "submit": lambda: submit(p, a.project, a.case), "poll": lambda: poll(p, a.project, a.case),
     "measure": lambda: measure(p, a.project)}[a.step]()


if __name__ == "__main__":
    main()
