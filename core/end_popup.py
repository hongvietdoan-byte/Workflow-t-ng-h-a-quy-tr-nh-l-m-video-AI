"""Popup quảng cáo cuối phim ghép lên CẢNH CUỐI (người dùng chốt 08/10, dự án #24) — 0 USD, PIL + ffmpeg.

Trước đây Director sinh 2 shot "nền tối mờ sương, chờ icon hiện ở hậu kỳ" (gen tốn tiền mà không thêm nội dung; người dùng xóa tay). Nay:
  - shot chỉ để chờ popup/hậu kỳ bị gộp thành GHI CHÚ end card cho shot cuối (core/shot_normalize.fold_post_only);
  - lúc dựng, các icon PNG trong suốt (tài nguyên `prop` của dự án, vd #421/#422 của #24) bật lên LẦN LƯỢT (phóng to rồi về cỡ — scale-pop),
    tên hành động dưới mỗi icon + một dòng lớn ("Hành động sắp ra mắt"), chồng lên ~3–4 s cuối của video;
  - góp ý 08/10 sau bản nháp #24: chữ TO, RÕ, VIẾT HOA (giữ dấu), dòng lớn vàng sáng (#FFD400) viền + bóng đổ đậm, nhãn trắng có viền;
    mỗi icon bật lên kèm một TIẾNG POP ngắn (Kho âm thanh, hoặc `sound`) trộn vào tiếng sẵn có.

Cấu hình ở `projects.render_settings["end_popup"]` (delivery.DEFAULTS):
  {"items": [{"asset_id": 421, "label": "Hành động Trồi Lên"} | {"path": "...png", "label": "..."}], "headline": "...", "seconds": 3.5,
   "uppercase": true, "headline_color": "#FFD400", "label_color": "#FFFFFF", "scale": 1.0,
   "sound": null (= tự lấy tiếng pop ≤ 0,5 s trong Kho) | "<đường dẫn>" | false (= tắt), "sound_volume": 0.9}
Chữ vẽ bằng PIL với font có đủ dấu tiếng Việt (subtitles.font_for_text) — không dùng drawtext.
"""
import os
import shutil
import tempfile
import unicodedata
from typing import Dict, List, Optional, Tuple

FPS = 24
POP_S = 0.35            # one icon grows 0 → 115 % → 100 % in this time
STAGGER_S = 0.6         # the next icon pops this long after the previous one
DEFAULT_SECONDS = 3.5
ICON_SHARE = 0.30       # icon width = this share of the frame width
HEADLINE_COLOR = "#FFD400"   # 08/10: bright yellow (the old (255,225,120) read as a dull, washed-out yellow on the dark noisy shot)
LABEL_COLOR = "#FFFFFF"
LABEL_SHARE = 0.046     # label letter height = this share of the frame width × scale (was 0.032: too small)
HEAD_SHARE = 0.085      # headline letter height (was 0.06)
SOUND_VOLUME = 0.9
POP_MAX_S = 0.5         # a pop from the sound Kho: a short one


def _colour(value, default: str) -> Tuple[int, int, int]:
    from PIL import ImageColor
    try:
        return ImageColor.getrgb(str(value or default))[:3]
    except ValueError:
        return ImageColor.getrgb(default)[:3]


def config(settings: Dict) -> Optional[Dict]:
    """The project's popup (render settings), cleaned; None when there is nothing to show."""
    cfg = (settings or {}).get("end_popup") or None
    if not isinstance(cfg, dict):
        return None
    items = [i for i in cfg.get("items") or [] if isinstance(i, dict) and (i.get("asset_id") or i.get("path"))]
    headline = str(cfg.get("headline") or "").strip()
    if not items and not headline:
        return None
    sound = cfg.get("sound")
    sound = False if sound is False else (str(sound).strip() or None) if sound else None
    try:
        scale = min(max(float(cfg.get("scale") or 1.0), 0.5), 2.0)
    except (TypeError, ValueError):
        scale = 1.0
    try:
        vol = min(max(float(cfg["sound_volume"] if cfg.get("sound_volume") is not None else SOUND_VOLUME), 0.0), 2.0)
    except (TypeError, ValueError):
        vol = SOUND_VOLUME
    return {"items": items, "headline": headline, "seconds": min(max(float(cfg.get("seconds") or DEFAULT_SECONDS), 1.5), 8.0),
            "uppercase": cfg.get("uppercase") is not False,
            "headline_color": "#%02X%02X%02X" % _colour(cfg.get("headline_color"), HEADLINE_COLOR),
            "label_color": "#%02X%02X%02X" % _colour(cfg.get("label_color"), LABEL_COLOR),
            "scale": scale, "sound": sound, "sound_volume": vol}


def caps(text: str) -> str:
    """VIẾT HOA giữ dấu: NFC first so a decomposed "ạ" (a + dấu nặng) becomes one letter, then upper (đ → Đ, ắ → Ắ)."""
    return unicodedata.normalize("NFC", text or "").upper()


def pop_sound(conn, cfg: Dict) -> Optional[str]:
    """The pop played when each icon pops: `sound` (a path; missing file = error, luật 1), else the shortest-fitting "Pop" of the
    sound Kho (sfx ≤ POP_MAX_S, the one named exactly "Pop" first), else None. `sound: false` = no pop."""
    want = cfg.get("sound")
    if want is False:
        return None
    if want:
        if not os.path.exists(want):
            raise ValueError(f"popup cuối: không thấy file tiếng pop {want}")
        return want
    try:
        rows = conn.execute("SELECT path, name, duration FROM sounds WHERE kind='sfx' AND duration>0 AND duration<=? AND "
                            "(LOWER(name) LIKE '%pop%' OR LOWER(name) LIKE '%ding%') "
                            "ORDER BY (LOWER(name)='pop') DESC, (LOWER(name) LIKE '%pop%') DESC, duration DESC", (POP_MAX_S,)).fetchall()
    except Exception:  # noqa: BLE001 - a database without the sound Kho
        return None
    for r in rows:
        if os.path.exists(r[0]):
            return r[0]
    return None


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


def _wrap(text: str, font, max_w: float) -> List[str]:
    """Greedy word wrap so a long label stays under its icon (at most 3 lines; the card shrinks if a word alone is wider)."""
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    words = text.split()
    if len(words) < 2 or d.textlength(text, font=font) <= max_w:
        return [text]
    two = min((max(d.textlength(" ".join(words[:k]), font=font), d.textlength(" ".join(words[k:]), font=font)), k)
              for k in range(1, len(words)))
    if two[0] <= max_w:                                # balanced 2 lines ("HÀNH ĐỘNG / TRỒI LÊN", not "HÀNH ĐỘNG TRỒI / LÊN")
        return [" ".join(words[:two[1]]), " ".join(words[two[1]:])]
    lines: List[str] = []
    for word in words:
        if lines and d.textlength(lines[-1] + " " + word, font=font) <= max_w:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) > 3:
        lines = lines[:2] + [" ".join(lines[2:])]
    return lines or [""]


def _text_block(lines: List[str], font, px: int, fill, stroke_px: int):
    """Centred lines with a thick dark outline AND a blurred drop shadow, so the words read on a dark noisy shot (RGBA)."""
    from PIL import Image, ImageDraw, ImageFilter
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    widths = [int(d.textlength(t, font=font)) for t in lines]
    asc, desc = font.getmetrics() if hasattr(font, "getmetrics") else (px, px // 4)
    line_h = asc + desc + int(px * 0.12)
    pad = stroke_px * 2 + int(px * 0.25)
    w, h = max(widths, default=1) + pad * 2, line_h * len(lines) + pad * 2
    shadow, text = Image.new("RGBA", (w, h), (0, 0, 0, 0)), Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(text)
    off = max(2, px // 12)
    for i, t in enumerate(lines):
        x, y = pad + (max(widths) - widths[i]) // 2, pad + i * line_h
        ds.text((x + off, y + off), t, font=font, fill=(0, 0, 0, 255), stroke_width=stroke_px + off // 2, stroke_fill=(0, 0, 0, 255))
        dt.text((x, y), t, font=font, fill=tuple(fill) + (255,), stroke_width=stroke_px, stroke_fill=(10, 8, 0, 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, px // 10)))
    shadow.alpha_composite(text)
    return shadow


def _card(icon_path: str, label: str, width: int, label_px: int = 0, colour=(255, 255, 255), max_label_w: float = 0):
    """One icon with its label under it, transparent around (RGBA)."""
    from PIL import Image
    with Image.open(icon_path) as im:
        icon = im.convert("RGBA")
    w = int(width * ICON_SHARE)
    icon = icon.resize((w, max(1, int(icon.height * w / icon.width))))
    px = label_px or max(int(width * LABEL_SHARE), 14)
    block = None
    if label:
        f = _font(label, px)
        block = _text_block(_wrap(label, f, max(max_label_w, w)), f, px, colour, max(2, px // 7))
    cw = max(w, block.width if block else 0)
    card = Image.new("RGBA", (cw, icon.height + (block.height if block else 0)), (0, 0, 0, 0))
    card.alpha_composite(icon, ((cw - w) // 2, 0))
    if block:
        card.alpha_composite(block, ((cw - block.width) // 2, icon.height - int(px * 0.15)))
    return card


def _scale(t: float) -> float:
    """Pop: 0 → 1.15 (70 % of POP_S) → 1.0."""
    if t <= 0:
        return 0.0
    if t >= POP_S:
        return 1.0
    a = t / POP_S
    return 1.15 * a / 0.7 if a < 0.7 else 1.15 - 0.15 * (a - 0.7) / 0.3


def _style(style: Optional[Dict]) -> Dict:
    style = dict(style or {})
    return {"uppercase": style.get("uppercase", True) is not False, "scale": float(style.get("scale") or 1.0),
            "headline_color": _colour(style.get("headline_color"), HEADLINE_COLOR),
            "label_color": _colour(style.get("label_color"), LABEL_COLOR)}


def frames(items: List[Dict], headline: str, size, seconds: float, out_dir: str, style: Optional[Dict] = None) -> int:
    """The popup as transparent PNG frames (FPS) of the video's size. Returns the frame count."""
    from PIL import Image
    st = _style(style)
    W, H = size
    if st["uppercase"]:
        headline = caps(headline)
        items = [dict(i, label=caps(i["label"])) for i in items]
    n = len(items)
    gap = int(W * 0.04)
    label_px = max(int(W * LABEL_SHARE * st["scale"]), 14)
    slot = (W * 0.94 - gap * max(n - 1, 0)) / max(n, 1)      # each label wraps to its share of the row
    cards = [_card(i["path"], i["label"], W, label_px, st["label_color"], slot) for i in items]
    row_w = sum(c.width for c in cards) + gap * max(n - 1, 0)
    if row_w > W * 0.94 and n:                         # too wide: shrink every card the same
        k = W * 0.94 / row_w
        cards = [c.resize((max(1, int(c.width * k)), max(1, int(c.height * k)))) for c in cards]
        row_w = sum(c.width for c in cards) + gap * max(n - 1, 0)
    row_h = max((c.height for c in cards), default=0)
    head = None
    if headline:
        head_px = max(int(W * HEAD_SHARE * st["scale"]), 18)
        hf = _font(headline, head_px)
        head = _text_block([headline], hf, head_px, st["headline_color"], max(3, head_px // 8))
        if head.width > W * 0.96 * 1.3:                # far too long for one line: 2 balanced lines
            head = _text_block(_wrap(headline, hf, W * 0.92), hf, head_px, st["headline_color"], max(3, head_px // 8))
        if head.width > W * 0.96:                      # a little too wide: one line, shrunk to fit — never cut
            k = W * 0.96 / head.width
            head = head.resize((max(1, int(head.width * k)), max(1, int(head.height * k))))
    top = int(H * 0.36) - row_h // 2
    head_cy = top + row_h + int(W * 0.02) + (head.height // 2 if head else 0)
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
        if head is not None:
            s = _scale(t - head_at)
            if s > 0:
                hw, hh = max(1, int(head.width * s)), max(1, int(head.height * s))
                img.alpha_composite(head.resize((hw, hh)), (max(0, (W - hw) // 2), max(0, head_cy - hh // 2)))
        img.save(os.path.join(out_dir, f"p_{k:04d}.png"))
    return total


def pop_times(n_items: int, start: float) -> List[float]:
    """When each icon starts its scale-pop (seconds in the video) — the pop sound plays exactly there."""
    return [round(start + i * STAGGER_S, 3) for i in range(n_items)]


def apply(conn, video: str, output: str, cfg: Dict) -> Dict:
    """The popup over the last `seconds` of `video` (the end of its last shot) + a pop sound as each icon pops, mixed into the
    video's own sound (a silent video gets a track). {"start_s", "seconds", "items", "headline", "sound", "pops_s"}."""
    from . import ffmpeg_studio
    items = resolve(conn, cfg)
    size = ffmpeg_studio.probe_size(video)
    total = ffmpeg_studio.probe_duration(video) or 0.0
    if not size or total <= 0:
        raise ValueError("popup cuối: không đọc được kích thước / độ dài video")
    seconds = min(cfg["seconds"], total)
    start = max(0.0, total - seconds)
    sound = pop_sound(conn, cfg) if items else None
    pops = [t for t in pop_times(len(items), start) if t < total] if sound else []
    work = tempfile.mkdtemp(prefix="end_popup_")
    try:
        frames(items, cfg["headline"], size, seconds, work, cfg)
        cmd = [ffmpeg_studio.find_ffmpeg(), "-y", "-i", video, "-framerate", str(FPS), "-itsoffset", f"{start:.3f}",
               "-i", os.path.join(work, "p_%04d.png")]
        video_graph = f"[0:v][1:v]overlay=0:0:eof_action=pass,{ffmpeg_studio.TO_YUV709}[v]"
        if pops:
            has_audio = ffmpeg_studio.has_audio(video)
            cmd += ["-i", sound]
            if not has_audio:                          # a silent video: the pops go on a new track as long as the video
                cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            norm = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
            vol = float(cfg.get("sound_volume", SOUND_VOLUME))
            graph = [video_graph, f"[{0 if has_audio else 3}:a]{norm}[base]"]
            split = f",asplit={len(pops)}" if len(pops) > 1 else ""
            graph.append(f"[2:a]{norm},volume={vol:.2f}{split}" + "".join(f"[s{i}]" for i in range(len(pops))))
            for i, t in enumerate(pops):
                graph.append(f"[s{i}]adelay=delays={int(round(t * 1000))}:all=1[d{i}]")
            graph.append("[base]" + "".join(f"[d{i}]" for i in range(len(pops)))
                         + f"amix=inputs={len(pops) + 1}:normalize=0:duration=first,{ffmpeg_studio.PEAK_LIMIT}[a]")
            cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]", *ffmpeg_studio._ENCODE,
                    *ffmpeg_studio.AAC, "-t", f"{total:.3f}", output]
        else:
            cmd += ["-filter_complex", video_graph, "-map", "[v]", "-map", "0:a?", *ffmpeg_studio._ENCODE, "-c:a", "copy", output]
        ffmpeg_studio.run(cmd)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out = {"start_s": round(start, 2), "seconds": round(seconds, 2), "items": [i["label"] for i in items], "headline": cfg["headline"],
           "sound": sound, "pops_s": pops}
    if items and not sound and cfg.get("sound") is not False:     # luật 1: say it, never a silent gap
        out["sound_note"] = "không có tiếng pop: Kho âm thanh không có tiếng pop ≤ 0,5 s và chưa đặt end_popup.sound"
    return out
