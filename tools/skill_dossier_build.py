"""Build a character's skill dossier (data/skills/<NAME>/) from the official skill video — S10.1 (người dùng 2026-09-30).

The Kenta dossier was made by hand (30/09); this makes the same folder for any character, from the numbers kept in skill.json
`build` so it can be rebuilt and checked:

    py tools/skill_dossier_build.py sparse  <video> <out_dir>                 1 frame/s contact sheet — find the skill part
    py tools/skill_dossier_build.py dense   <video> <out_dir> --from 11 --to 26   every frame of that part + 1 sheet per second
    py tools/skill_dossier_build.py build   data/skills/ORION                 frames/, crops/, storyboard, video_ref from skill.json

skill.json `build` (all times in seconds of the source video, boxes as fractions [x0, y0, x1, y1] of the frame):
    {"source_video": "...", "dense_dir": "...", "dense_from": 11.0, "keyframes": [16.2, ...],
     "crops": {"<phase id>": [t, box]}, "video_ref": {"<name>": [from, to, box]}, "title": "storyboard title"}

Game interface (HUD: health bars, banners, damage-direction marks, buttons) is not the skill — the crops leave it out where they can, and the
reference note of every frame says not to copy it (lesson of 30/09: the red crescent was a damage-direction mark). The video cuts follow the
rules ClipAI checks (≥ 3 s, 700–4553 px wide, square pixels, 24–60 fps) so they can go as reference videos as they are."""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

MIN_REF_S = 3.0
REF_WIDTH = 720
MIN_PIXELS = 420_000          # Seedance 2.5: width × height ≥ 407 696 (BytePlus docs) — with a margin


def _ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    st = data["streams"][0]
    num, _, den = st["r_frame_rate"].partition("/")
    return {"width": int(st["width"]), "height": int(st["height"]), "fps": float(num) / float(den or 1),
            "duration": float(data["format"]["duration"])}


def _font(size, bold=False):
    from PIL import ImageFont
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(os.path.join("C:/Windows/Fonts", name) if os.name == "nt" else name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def sheet(files, out, labels, cols=6, width=480):
    from PIL import Image, ImageDraw
    ims = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im.thumbnail((width, width))
        ims.append(im)
    if not ims:
        return None
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    board = Image.new("RGB", (cols * w, rows * (h + 22)), "white")
    d = ImageDraw.Draw(board)
    for k, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (k % cols) * w, (k // cols) * (h + 22)
        board.paste(im, (x, y + 22))
        d.text((x + 4, y + 3), lab, fill="black", font=_font(16, True))
    board.save(out, quality=85)
    return out


def cmd_sparse(video, out):
    os.makedirs(os.path.join(out, "sparse"), exist_ok=True)
    _ff("-i", video, "-vf", "fps=1,scale=480:-2", os.path.join(out, "sparse", "%03d.jpg"))
    files = sorted(glob.glob(os.path.join(out, "sparse", "*.jpg")))
    print(sheet(files, os.path.join(out, "sparse_sheet.jpg"), [f"{k}s" for k in range(len(files))]))


def cmd_dense(video, out, t0, t1):
    info = probe(video)
    d = os.path.join(out, "dense")
    os.makedirs(d, exist_ok=True)
    _ff("-ss", f"{t0}", "-to", f"{t1}", "-i", video, "-fps_mode", "passthrough", os.path.join(d, "%05d.png"))
    files = sorted(glob.glob(os.path.join(d, "*.png")))
    fps = info["fps"]
    for s in range(int(t0), int(t1) + 1):          # one sheet per second of the source — every frame, labelled with its time
        part = [(f, t0 + k / fps) for k, f in enumerate(files) if s <= t0 + k / fps < s + 1]
        if part:
            sheet([f for f, _ in part], os.path.join(out, f"dense_{s:03d}s.jpg"), [f"{t:.2f}" for _, t in part], cols=5, width=384)
    print(len(files), "khung,", fps, "khung/giây →", d)


def frame_at(build, t, info):
    """The dense frame of source time t (or the kept 1080p key frame frames_png/<t>.png when the dense frames are gone)."""
    kept = os.path.join(build.get("_folder", ""), "frames_png", f"{t:05.2f}.png")
    if build.get("_folder") and os.path.exists(kept) and not os.path.isdir(build.get("dense_dir") or ""):
        return kept
    files = sorted(glob.glob(os.path.join(build["dense_dir"], "*.png")))
    k = int(round((t - float(build["dense_from"])) * info["fps"]))
    if not files or k < 0 or k >= len(files):
        raise SystemExit(f"không có khung ở {t:.2f} s (dense {build['dense_from']} s, {len(files)} khung) — chạy lệnh dense trước")
    return files[k]


def _box(im, box):
    w, h = im.size
    return im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def ref_width(cw, ch):
    """Output width of a reference cut: both sides ≥ 704 px (Kling: width AND height 700–4553) and enough pixels for Seedance
    (≥ 407 696), even."""
    import math
    need = max(REF_WIDTH, math.sqrt(MIN_PIXELS * cw / ch), 704 * cw / ch)
    return int(math.ceil(need)) // 2 * 2 + 2


def cut_ref(video, t0, t1, box, out, info):
    """A reference-video cut ClipAI takes: ≥ 3 s, 720 px wide, square pixels, source fps kept (24–60)."""
    if t1 - t0 < MIN_REF_S:
        pad = (MIN_REF_S - (t1 - t0)) / 2
        t0, t1 = max(0.0, t0 - pad), t1 + pad
    w, h = info["width"], info["height"]
    x0, y0, x1, y1 = (int(box[0] * w) // 2 * 2, int(box[1] * h) // 2 * 2, int(box[2] * w) // 2 * 2, int(box[3] * h) // 2 * 2)
    width = ref_width(x1 - x0, y1 - y0)
    _ff("-ss", f"{t0}", "-to", f"{t1}", "-i", video, "-vf",
        f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0},scale={width}:-2:flags=lanczos,setsar=1", "-an", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", out)
    got = probe(out)
    assert got["duration"] >= MIN_REF_S - 0.05 and min(got["width"], got["height"]) >= 700 and got["width"] * got["height"] >= 407_696, got
    return out


def clean_frame(im, hud_boxes, yellow_digits=True):
    """The frame without the game interface (người dùng 30/09: tối ưu ảnh gửi model): fixed HUD boxes (fractions [x0, y0, x1, y1] —
    health / energy bars, buttons, captions) and — optionally — the yellow damage numbers are painted over from their surroundings
    (OpenCV inpaint). The skill effect outside those boxes is left as it is."""
    import cv2
    import numpy as np
    from PIL import Image
    arr = cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = arr.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in hud_boxes:
        mask[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 255
    if yellow_digits:                       # damage numbers: small saturated yellow marks (the effect itself is red / blue)
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
        yel = cv2.inRange(hsv, (20, 120, 170), (38, 255, 255))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(yel)
        for k in range(1, n):
            x, y, bw, bh, area = stats[k]
            if area < 0.0015 * w * h and bh < 0.06 * h:
                mask[lab == k] = 255
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
    out = cv2.inpaint(arr, mask, 5, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def clean_sheet(d, info, out, height=768):
    """One picture of the skill's phases in order, clean: HUD removed, each phase cropped close, side by side, only a small number in
    each corner — for the image / video model (the storyboard with Vietnamese captions stays for people and the Director)."""
    from PIL import Image, ImageDraw
    b = d["build"]
    panels = []
    for pid, t, box in b["clean_sheet"]:
        im = clean_frame(Image.open(frame_at(b, t, info)).convert("RGB"), b.get("hud") or [], b.get("yellow_digits", True))
        im = _box(im, box)
        panels.append(im.resize((int(im.width * height / im.height), height), Image.LANCZOS))
    gap = 12
    import math
    cols = len(panels)                       # Seedance: a picture's width / height must be 0.4–2.5 → rows of panels, ≤ 2.4 wide
    while cols > 1:
        rows = math.ceil(len(panels) / cols)
        width = max(sum(p.width for p in panels[r * cols:(r + 1) * cols]) + gap * (cols - 1) for r in range(rows))
        if width / (rows * height + gap * (rows - 1)) <= 2.4:
            break
        cols -= 1
    rows = math.ceil(len(panels) / cols)
    width = max(sum(p.width for p in panels[r * cols:(r + 1) * cols]) + gap * (cols - 1) for r in range(rows))
    sheet = Image.new("RGB", (width, rows * height + gap * (rows - 1)), (40, 40, 40))
    dr = ImageDraw.Draw(sheet)
    for k, p in enumerate(panels, 1):
        r, c = divmod(k - 1, cols)
        x = sum(q.width for q in panels[r * cols:r * cols + c]) + gap * c
        y = r * (height + gap)
        sheet.paste(p, (x, y))
        dr.ellipse([x + 10, y + 10, x + 58, y + 58], fill=(20, 20, 20))
        dr.text((x + 25, y + 13), str(k), fill=(255, 255, 255), font=_font(34, True))
    if max(sheet.size) > 6000:              # Seedance 2.5: picture sides 300–6000 px
        k = 6000 / max(sheet.size)
        sheet = sheet.resize((int(sheet.width * k), int(sheet.height * k)), Image.LANCZOS)
    sheet.save(out, quality=92)
    return out


def storyboard(d, info, out):
    """Panels = the phases (crop + seconds + Vietnamese caption) and a 'KHÔNG ĐƯỢC VẼ' panel from never_vi."""
    from PIL import Image, ImageDraw
    b = d["build"]
    phases = [p for p in d["phases"] if p["id"] in b.get("crops", {})]
    W, H, CAP, cols = 600, 640, 190, 4
    n = len(phases) + 1
    rows = (n + cols - 1) // cols
    sb = Image.new("RGB", (W * cols, 70 + (H + CAP) * rows), (18, 20, 26))
    dr = ImageDraw.Draw(sb)
    dr.text((16, 14), b.get("title") or f"{d['character']} · {d.get('skill_vi', '')}", fill=(255, 255, 255), font=_font(28, True))

    def wrap(text, font, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if dr.textlength(test, font=font) <= width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        return lines + [cur]

    for k, p in enumerate(phases):
        t, box = b["crops"][p["id"]]
        x, y = (k % cols) * W, 70 + (k // cols) * (H + CAP)
        im = _box(Image.open(frame_at(b, t, info)).convert("RGB"), box)
        im.thumbnail((W - 8, H - 8))
        sb.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        dr.rectangle([x + 4, y + 4, x + 118, y + 40], fill=(0, 0, 0))
        dr.text((x + 10, y + 8), f"{t:05.2f}s", fill=(255, 220, 0), font=_font(24, True))
        dr.rectangle([x, y + H, x + W - 4, y + H + CAP - 6], fill=(34, 38, 48))
        dr.text((x + 10, y + H + 6), f"{k + 1} · {p['id']} ({p['t'][0]:.1f}–{p['t'][1]:.1f} s)", fill=(120, 220, 255), font=_font(22, True))
        for m, line in enumerate(wrap(p["vi"], _font(19), W - 24)[:7]):
            dr.text((x + 10, y + H + 36 + m * 22), line, fill=(235, 235, 235), font=_font(19))
    k = len(phases)
    x, y = (k % cols) * W, 70 + (k // cols) * (H + CAP)
    dr.rectangle([x, y, x + W - 4, y + H + CAP - 6], fill=(60, 18, 18))
    dr.text((x + 14, y + 12), "KHÔNG ĐƯỢC VẼ", fill=(255, 120, 120), font=_font(30, True))
    row = 0
    for item in d.get("never_vi") or []:
        for line in wrap("× " + item, _font(21), W - 30):
            dr.text((x + 14, y + 64 + row * 30), line, fill=(255, 225, 225), font=_font(21))
            row += 1
    sb.convert("RGB").save(out, quality=85)
    return out


def cmd_build(folder):
    from PIL import Image
    path = os.path.join(folder, "skill.json")
    d = json.load(open(path, encoding="utf-8"))
    b = d["build"]
    b["_folder"] = folder
    video = b["source_video"]
    info = probe(video)
    for sub in ("frames", "crops", "frames_png", "clips_local"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    for t in b.get("keyframes") or []:
        src = frame_at(b, t, info)
        shutil.copy2(src, os.path.join(folder, "frames_png", f"{t:05.2f}.png"))
        im = Image.open(src).convert("RGB")
        im.thumbnail((1280, 1280))
        im.save(os.path.join(folder, "frames", f"{t:05.2f}.jpg"), quality=88)
    for p in d["phases"]:
        if p["id"] in b.get("crops", {}):
            t, box = b["crops"][p["id"]]
            im = _box(Image.open(frame_at(b, t, info)).convert("RGB"), box)
            if im.height < 1024:
                im = im.resize((int(im.width * 1024 / im.height), 1024), Image.LANCZOS)
            name = f"crops/{p['id']}_{t:05.2f}.jpg"
            im.save(os.path.join(folder, name), quality=90)
            p["frame"] = name
            p.setdefault("frame_full", f"frames/{t:05.2f}.jpg")
    refs = {}
    for name, (t0, t1, box) in (b.get("video_ref") or {}).items():
        out = os.path.join(folder, "clips_local", f"{name}_{t0:.1f}-{t1:.1f}.mp4")
        cut_ref(video, t0, t1, box, out, info)
        refs[name] = os.path.relpath(out, folder).replace("\\", "/")
    if refs:
        d["video_ref"] = dict(refs, note="chỉ trên máy (không git): tạo lại bằng `py tools/skill_dossier_build.py build " + folder.replace("\\", "/") + "`")
    if b.get("clean_sheet"):
        clean_sheet(d, info, os.path.join(folder, "skill_sheet_clean.jpg"))
        d["skill_sheet"] = "skill_sheet_clean.jpg"
        d["skill_sheet_phases"] = [x[0] for x in b["clean_sheet"]]
    d["storyboard"] = "storyboard_ky_nang.jpg"
    storyboard(d, info, os.path.join(folder, "storyboard_ky_nang.jpg"))
    b.pop("_folder", None)
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("xong:", folder, "·", len(b.get("keyframes") or []), "khung ·", len(b.get("crops") or {}), "ảnh cắt ·", len(refs), "đoạn video")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("sparse", "dense", "build"))
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--from", dest="t0", type=float)
    ap.add_argument("--to", dest="t1", type=float)
    a = ap.parse_args(argv)
    if a.step == "sparse":
        cmd_sparse(*a.paths[:2])
    elif a.step == "dense":
        cmd_dense(a.paths[0], a.paths[1], a.t0, a.t1)
    else:
        cmd_build(a.paths[0])


if __name__ == "__main__":
    sys.exit(main())
