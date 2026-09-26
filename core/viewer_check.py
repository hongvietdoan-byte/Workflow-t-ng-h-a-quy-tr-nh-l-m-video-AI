"""Watch the delivery like a viewer on a phone (knowledge/editor/editing.md E9, việc code D13) — code only, free.

One sheet of frames taken evenly through the video, each shown twice: at phone size with the app's interface bands painted over it
(top 15 %, bottom 35 %, right 18 % — knowledge/editor/safe_zones.md), and at ~360×640 to see whether the text is still readable. Faces
found under an interface band (YuNet, the model the subtitles already use) are listed: in the app, that face is behind a button.
Text too (E9 "chữ/mặt"): given the render WITHOUT text (`plain`), the pixels that differ at the same moment are the text drawn on it
(subtitles, notices, name cards); text reaching into a band is listed — the end card (full frame by design) is not.

    sheet(video, out_png, ffmpeg=None, count=8, plain=None) -> {"path", "frames": [{"t", "faces_hidden", "text_hidden"}], "hidden",
                                                                "text_hidden"}
"""
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

from . import ffmpeg_studio, subtitles, text_placement

BANDS = {"top": (0.0, subtitles.SAFE_TOP), "bottom": (1 - 0.35, 1.0)}      # official 35 % (the code's own margin keeps 36 %)
RIGHT = subtitles.SAFE_RIGHT
THUMB_W = 240                          # each frame on the sheet
SMALL_W = 120                          # the "phone held at arm's length" copy (~360 px wide on a 1080 frame, scaled with the sheet)


def hidden_faces(boxes: List[tuple], vertical: bool = True) -> List[str]:
    """Which interface band each face (left, top, right, bottom as frame fractions) is under by more than half: the top / bottom bars
    by its height, the right-hand button column by its width. The app's bands are those of a vertical video; a horizontal one has none."""
    if not vertical:
        return []
    out = []
    for left, top, right, bottom in boxes:
        h, w = max(bottom - top, 1e-6), max(right - left, 1e-6)
        for name, (a, b) in BANDS.items():
            if (min(bottom, b) - max(top, a)) / h > 0.5:
                out.append(name)
        if (right - max(left, 1 - RIGHT)) / w > 0.5:
            out.append("right")
    return out


TEXT_DIFF = 60                         # grey-level change that counts as drawn text (subtitle fill / outline against the picture)
TEXT_MIN_PX = 40                       # fewer changed pixels than this in a band = encoding noise, not text


def text_bands(with_text, without_text) -> List[str]:
    """Interface bands the drawn text reaches: pixels that changed between the two frames (same size, grey), by band."""
    import numpy as np
    a = np.asarray(with_text.convert("L"), np.int16)
    b = np.asarray(without_text.convert("L").resize(with_text.size), np.int16)
    mask = np.abs(a - b) > TEXT_DIFF
    h, w = mask.shape
    out = [name for name, (top, bottom) in BANDS.items() if mask[int(top * h):int(bottom * h)].sum() >= TEXT_MIN_PX]
    if mask[:, int((1 - RIGHT) * w):].sum() >= TEXT_MIN_PX:
        out.append("right")
    return out


def _frame(ff: str, video: str, t: float, png: str) -> bool:
    subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", png], capture_output=True,
                   timeout=60)
    return os.path.exists(png)


def sheet(video: str, out_png: str, ffmpeg: Optional[str] = None, count: int = 8, plain: Optional[str] = None) -> Dict:
    from PIL import Image, ImageDraw
    ff = ffmpeg or ffmpeg_studio.find_ffmpeg()
    dur = ffmpeg_studio.probe_duration(video) or 0
    if dur <= 0:
        raise ValueError("không đọc được độ dài video")
    work = tempfile.mkdtemp()
    frames, tiles = [], []
    try:
        for n in range(count):
            t = dur * (n + 0.5) / count
            png = os.path.join(work, f"f{n}.png")
            if not _frame(ff, video, t, png):
                continue
            boxes = text_placement.face_boxes(png)
            text_hidden: List[str] = []
            with Image.open(png) as im:
                vertical = im.height > im.width
                bare = os.path.join(work, f"p{n}.png")
                plain_len = ffmpeg_studio.probe_duration(plain) if plain else None
                if vertical and plain and plain_len and t < plain_len - 0.1 and _frame(ff, plain, t, bare):
                    with Image.open(bare) as pm:
                        text_hidden = text_bands(im, pm)
                big = im.convert("RGB").resize((THUMB_W, int(im.height * THUMB_W / im.width)))
            frames.append({"t": round(t, 2), "faces_hidden": hidden_faces(boxes or [], vertical), "faces_seen": boxes is not None,
                           "text_hidden": text_hidden})
            over = Image.new("RGBA", big.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(over)
            if vertical:                         # the app's interface bands belong to a vertical (9:16) video
                for a, b in BANDS.values():
                    d.rectangle([0, int(a * big.height), big.width, int(b * big.height)], fill=(220, 40, 40, 90))
                d.rectangle([int((1 - RIGHT) * big.width), 0, big.width, big.height], fill=(220, 40, 40, 70))
            big = Image.alpha_composite(big.convert("RGBA"), over).convert("RGB")
            ImageDraw.Draw(big).text((4, 4), f"{t:.1f}s" + (" ⚠ mặt dưới giao diện" if frames[-1]["faces_hidden"] else "")
                                     + (" ⚠ chữ dưới giao diện" if text_hidden else ""), fill=(255, 255, 0))
            small = big.resize((SMALL_W, int(big.height * SMALL_W / big.width)))
            tiles.append((big, small))
        if not tiles:
            raise ValueError("không lấy được khung nào từ video")
        cell_w = THUMB_W + SMALL_W + 12
        cell_h = max(b.height for b, _ in tiles) + 8
        cols = 4
        rows = (len(tiles) + cols - 1) // cols
        out = Image.new("RGB", (cols * cell_w, rows * cell_h), (30, 30, 30))
        for i, (big, small) in enumerate(tiles):
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            out.paste(big, (x + 4, y + 4))
            out.paste(small, (x + THUMB_W + 8, y + 4))
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        out.save(out_png)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"path": out_png, "frames": frames, "hidden": sum(1 for f in frames if f["faces_hidden"]),
            "text_hidden": sum(1 for f in frames if f["text_hidden"]), "text_checked": bool(plain)}
