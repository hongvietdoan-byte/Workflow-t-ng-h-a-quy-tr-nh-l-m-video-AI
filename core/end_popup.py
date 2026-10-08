"""Popup quảng cáo cuối phim ghép lên CẢNH CUỐI (người dùng chốt 08/10, dự án #24) — 0 USD, PIL + ffmpeg.

Trước đây Director sinh 2 shot "nền tối mờ sương, chờ icon hiện ở hậu kỳ" (gen tốn tiền mà không thêm nội dung; người dùng xóa tay). Nay:
  - shot chỉ để chờ popup/hậu kỳ bị gộp thành GHI CHÚ end card cho shot cuối (core/shot_normalize.fold_post_only);
  - lúc dựng, các icon PNG trong suốt (tài nguyên `prop` của dự án, vd #421/#422 của #24) bật lên LẦN LƯỢT (phóng to rồi về cỡ — scale-pop),
    tên hành động dưới mỗi icon + một dòng lớn ("Hành động sắp ra mắt"), chồng lên ~3–4 s cuối của video.

Cấu hình ở `projects.render_settings["end_popup"]` (delivery.DEFAULTS):
  {"items": [{"asset_id": 421, "label": "Hành động Trồi Lên"} | {"path": "...png", "label": "..."}], "headline": "...", "seconds": 3.5}
Chữ vẽ bằng PIL với font có đủ dấu tiếng Việt (subtitles.font_for_text) — không dùng drawtext.
"""
import os
import shutil
import tempfile
from typing import Dict, List, Optional

FPS = 24
POP_S = 0.35            # one icon grows 0 → 115 % → 100 % in this time
STAGGER_S = 0.6         # the next icon pops this long after the previous one
DEFAULT_SECONDS = 3.5
ICON_SHARE = 0.30       # icon width = this share of the frame width


def config(settings: Dict) -> Optional[Dict]:
    """The project's popup (render settings), cleaned; None when there is nothing to show."""
    cfg = (settings or {}).get("end_popup") or None
    if not isinstance(cfg, dict):
        return None
    items = [i for i in cfg.get("items") or [] if isinstance(i, dict) and (i.get("asset_id") or i.get("path"))]
    headline = str(cfg.get("headline") or "").strip()
    if not items and not headline:
        return None
    return {"items": items, "headline": headline, "seconds": min(max(float(cfg.get("seconds") or DEFAULT_SECONDS), 1.5), 8.0)}


def resolve(conn, cfg: Dict) -> List[Dict]:
    """[{"path", "label"}] — an asset gives its first approved picture. A missing picture is an error (luật 1: never a silent gap)."""
    from . import assets
    out = []
    for it in cfg["items"]:
        path = it.get("path")
        if not path and it.get("asset_id"):
            a = assets.get(conn, int(it["asset_id"]))
            if a is None or not a["images"]:
                raise ValueError(f"popup cuối: tài nguyên #{it['asset_id']} không có ảnh icon dùng được")
            path = a["images"][0]["path"]
        if not path or not os.path.exists(path):
            raise ValueError(f"popup cuối: không thấy file icon {path}")
        out.append({"path": path, "label": str(it.get("label") or "").strip()})
    return out


def suggest(conn, pid: int, script: str = "") -> Optional[Dict]:
    """A first popup from the project's resources: every `prop` whose name starts with "ICON" (label = the rest of the name, in
    sentence case), headline = a quoted line of the script that says "sắp ra mắt" when there is one. None when no icon is attached."""
    import re
    from . import assets
    icons = [a for a in assets.project_assets(conn, pid) if a["kind"] == "prop" and a["name"].strip().upper().startswith("ICON")
             and a["images"]]
    if not icons:
        return None
    items = []
    for a in sorted(icons, key=lambda a: a["id"]):
        rest = a["name"].strip()[4:].strip(" :-—")
        label = rest[:1].upper() + rest[1:].lower() if rest else a["name"]
        items.append({"asset_id": a["id"], "label": label})
    m = re.search(r"[\"“]([^\"”]*sắp ra mắt[^\"”]*)[\"”]", script or "", re.I)
    return {"items": items, "headline": m.group(1).strip() if m else "", "seconds": DEFAULT_SECONDS}


def _font(text: str, px: int):
    from PIL import ImageFont
    from . import subtitles
    fonts = subtitles.discover()
    font, _ = subtitles.font_for_text(subtitles.default_font(fonts), fonts, text)
    try:
        return ImageFont.truetype(font.path, px) if font else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def _card(icon_path: str, label: str, width: int):
    """One icon with its label under it, transparent around (RGBA)."""
    from PIL import Image, ImageDraw
    with Image.open(icon_path) as im:
        icon = im.convert("RGBA")
    w = int(width * ICON_SHARE)
    icon = icon.resize((w, max(1, int(icon.height * w / icon.width))))
    px = max(int(width * 0.032), 14)
    f = _font(label or "A", px)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(probe.textlength(label, font=f)) if label else 0
    cw = max(w, tw + px)
    card = Image.new("RGBA", (cw, icon.height + (int(px * 1.8) if label else 0)), (0, 0, 0, 0))
    card.alpha_composite(icon, ((cw - w) // 2, 0))
    if label:
        d = ImageDraw.Draw(card)
        x, y = (cw - tw) // 2, icon.height + int(px * 0.3)
        d.text((x, y), label, font=f, fill=(255, 255, 255, 255), stroke_width=max(2, px // 10), stroke_fill=(0, 0, 0, 220))
    return card


def _scale(t: float) -> float:
    """Pop: 0 → 1.15 (70 % of POP_S) → 1.0."""
    if t <= 0:
        return 0.0
    if t >= POP_S:
        return 1.0
    a = t / POP_S
    return 1.15 * a / 0.7 if a < 0.7 else 1.15 - 0.15 * (a - 0.7) / 0.3


def frames(items: List[Dict], headline: str, size, seconds: float, out_dir: str) -> int:
    """The popup as transparent PNG frames (FPS) of the video's size. Returns the frame count."""
    from PIL import Image, ImageDraw
    W, H = size
    cards = [_card(i["path"], i["label"], W) for i in items]
    n = len(cards)
    gap = int(W * 0.04)
    row_w = sum(c.width for c in cards) + gap * max(n - 1, 0)
    if row_w > W * 0.94 and n:                         # too wide: shrink every card the same
        k = W * 0.94 / row_w
        cards = [c.resize((max(1, int(c.width * k)), max(1, int(c.height * k)))) for c in cards]
        row_w = sum(c.width for c in cards) + gap * max(n - 1, 0)
    row_h = max((c.height for c in cards), default=0)
    head_px = max(int(W * 0.06), 18)
    hf = _font(headline or "A", head_px)
    top = int(H * 0.36) - row_h // 2
    head_y = top + row_h + int(head_px * 0.8)
    total = max(1, int(round(seconds * FPS)))
    head_at = n * STAGGER_S
    for k in range(total):
        t = k / FPS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shade = min(1.0, t / 0.4) * 110                # the shot behind dims a little so the popup reads
        img.paste((0, 0, 0, int(shade)), (0, 0, W, H))
        x = (W - row_w) // 2
        for i, c in enumerate(cards):
            s = _scale(t - i * STAGGER_S)
            if s > 0:
                cw, ch = max(1, int(c.width * s)), max(1, int(c.height * s))
                cx, cy = x + c.width // 2, top + row_h // 2
                img.alpha_composite(c.resize((cw, ch)), (max(0, cx - cw // 2), max(0, cy - ch // 2)))
            x += c.width + gap
        if headline:
            s = _scale(t - head_at)
            if s > 0:
                d = ImageDraw.Draw(img)
                f = _font(headline, max(1, int(head_px * s)))
                tw = d.textlength(headline, font=f)
                d.text(((W - tw) / 2, head_y), headline, font=f, fill=(255, 225, 120, 255), stroke_width=max(2, head_px // 12),
                       stroke_fill=(0, 0, 0, 230))
        img.save(os.path.join(out_dir, f"p_{k:04d}.png"))
    return total


def apply(conn, video: str, output: str, cfg: Dict) -> Dict:
    """The popup over the last `seconds` of `video` (the end of its last shot); sound copied. {"start_s", "seconds", "items"}."""
    from . import ffmpeg_studio
    items = resolve(conn, cfg)
    size = ffmpeg_studio.probe_size(video)
    total = ffmpeg_studio.probe_duration(video) or 0.0
    if not size or total <= 0:
        raise ValueError("popup cuối: không đọc được kích thước / độ dài video")
    seconds = min(cfg["seconds"], total)
    start = max(0.0, total - seconds)
    work = tempfile.mkdtemp(prefix="end_popup_")
    try:
        frames(items, cfg["headline"], size, seconds, work)
        ffmpeg_studio.run([ffmpeg_studio.find_ffmpeg(), "-y", "-i", video, "-framerate", str(FPS), "-itsoffset", f"{start:.3f}",
                           "-i", os.path.join(work, "p_%04d.png"), "-filter_complex",
                           f"[0:v][1:v]overlay=0:0:eof_action=pass,{ffmpeg_studio.TO_YUV709}[v]",
                           "-map", "[v]", "-map", "0:a?", *ffmpeg_studio._ENCODE, "-c:a", "copy", output])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"start_s": round(start, 2), "seconds": round(seconds, 2), "items": [i["label"] for i in items], "headline": cfg["headline"]}
