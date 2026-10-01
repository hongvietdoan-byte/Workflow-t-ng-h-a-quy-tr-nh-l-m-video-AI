"""Cut the TURNAROUND of a character sheet into separate views (front, 3/4, side, back) — the input Meshy's multi-image 3D wants
("the first image is used as the primary (front) view"); a whole sheet sent as one picture would be read as one object.

  turnaround(path)  [{"view", "box": (l, t, r, b) in pixels, "image": PIL.Image}] left → right, or [] when the figures cannot be told
                    apart (a cape or a sword joining two figures, an odd layout) — then the person cuts by hand, nothing is guessed
  save(views, folder, stem)  PNG files, returns their paths

Two layouts: the team's sheet (sidebar left, panels right, the turnaround in the top band: FRONT · 3/4 VIEW · SIDE · BACK) and a plain
turnaround picture (only the figures, e.g. one drawn for a character that has no sheet yet). No AI: the background is a flat light grey.
"""
import os
from typing import Dict, List, Optional, Tuple

VIEWS = ("front", "three_quarter", "side", "back")
FG_DIFF = 25          # grey levels from the background that count as "something drawn"
COL_SHARE = 0.02      # a column belongs to a figure when this share of its pixels is drawn
MIN_W = 0.025         # a figure is at least this share of the picture's width …
MAX_W_SHEET = 0.12    # … and at most this (the sidebar and the right panels are wider)
MAX_W_PLAIN = 0.35
PAD = 0.04            # margin kept around each figure, share of the figure's height


def _segments(share, width: int, lo: float, hi: float) -> List[Tuple[int, int]]:
    out, start = [], None
    for x in range(width + 1):
        on = x < width and share[x] > COL_SHARE
        if on and start is None:
            start = x
        elif not on and start is not None:
            if lo * width <= x - start <= hi * width:
                out.append((start, x))
            start = None
    return out


def _longest_run(rows, gap: int) -> Optional[Tuple[int, int]]:
    """(start, end) of the longest stretch of drawn rows, bridging blank gaps up to `gap` rows (a hand apart from a hip)."""
    best, start, last = None, None, None
    for y, on in enumerate(list(rows) + [False] * (gap + 1)):
        if on:
            if start is None:
                start = y
            last = y
        elif start is not None and y - last > gap:
            if best is None or last + 1 - start > best[1] - best[0]:
                best = (start, last + 1)
            start = None
    return best


def turnaround(path: str) -> List[Dict]:
    import numpy as np
    from PIL import Image
    img = Image.open(path).convert("RGB")
    grey = np.asarray(img.convert("L"), dtype=float)
    H, W = grey.shape
    # a plain turnaround = only the figures; the sheet band starts under the panel title and stops above the FRONT / 3/4 VIEW / SIDE / BACK labels (team template: title at
    # ≈ 2 % of the height, feet end ≈ 44 %, labels ≈ 45–47 %)
    for band, max_w in (((0.0, 1.0), MAX_W_PLAIN), ((0.035, 0.448), MAX_W_SHEET)):     # a plain picture first: whole figures
        top, bottom = int(band[0] * H), int(band[1] * H)
        part = grey[top:bottom]
        bg = float(np.median(part))
        drawn = np.abs(part - bg) > FG_DIFF
        segs = _segments(drawn.mean(axis=0), W, MIN_W, max_w)
        if len(segs) != len(VIEWS):
            continue
        out = []
        for view, (l, r) in zip(VIEWS, segs):
            run = _longest_run(drawn[:, l:r].mean(axis=1) > COL_SHARE, gap=int(0.01 * H) + 2)
            if run is None:
                break
            t, b = top + run[0], top + run[1]          # the figure only: a title above / a label below is a separate run
            pad, vpad = int((b - t) * PAD), int((b - t) * 0.01)
            box = (max(0, l - pad), max(top, t - vpad), min(W, r + pad), min(bottom, b + vpad))
            out.append({"view": view, "box": box, "image": img.crop(box)})
        else:
            if all(v["box"][3] - v["box"][1] >= 0.25 * (bottom - top) for v in out):   # whole figures, not a row of icons
                return out
    return []


def save(views: List[Dict], folder: str, stem: str) -> List[str]:
    os.makedirs(folder, exist_ok=True)
    paths = []
    for v in views:
        p = os.path.join(folder, f"{stem}_{v['view']}.png")
        v["image"].save(p)
        paths.append(p)
    return paths


def from_asset_image(path: Optional[str]) -> List[Dict]:
    return turnaround(path) if path and os.path.exists(path) else []
