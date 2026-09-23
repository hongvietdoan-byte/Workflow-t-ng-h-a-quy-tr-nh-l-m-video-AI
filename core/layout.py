"""Scene layout ("previz 2D"): build each shot as layers before any picture is generated.

    set analysis  - read ONCE per background picture (Claude Vision, cached): camera angle, horizon, walkable ground, landmarks with
                    real sizes. No marking by hand.
    shot layout   - per scene (Claude, one call for the whole script): which background picture, where each person's feet are,
                    which way they face, whether the background must be redrawn for this camera angle.
    compose       - CODE, not AI: puts every person on the ground at the size perspective gives them (so nobody is giant or
                    floating), far people first, a contact shadow under each.
    storyboard    - every composed shot on one sheet (no credit spent), for Claude's continuity check and an optional look.

The generated picture then follows the composed layout (image-to-image reference); the character pictures keep the identity.
Later a 3D map render or ClipAI's director desk can produce the same layout data, and nothing after this module changes.

Coordinates are fractions of the picture: x 0 (left) .. 1 (right), y 0 (top) .. 1 (bottom). The horizon may sit outside the
picture (a camera looking down from high up has its horizon above the frame).
"""
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

PERSON_HEIGHT_M = 1.75
CAMERA_CLASSES = ("eye", "low", "high", "top")
DEFAULT_CAMERA_HEIGHT_M = {"eye": 1.6, "low": 0.6, "high": 8.0, "top": 30.0}
FACINGS = ("left", "right", "camera", "away")
SIZE = (1280, 720)
COLORS = [(230, 57, 70), (29, 120, 220), (46, 170, 90), (245, 160, 30), (150, 80, 200), (20, 170, 170), (220, 90, 160),
          (120, 120, 120)]
COLOR_NAMES = ["red", "blue", "green", "orange", "purple", "teal", "pink", "grey"]


class LayoutError(ValueError):
    """The set analysis or the shot layout does not follow the expected shape."""


# ---- set analysis (per background picture) -------------------------------------------------------------------
def _num(value, where: str, lo: float, hi: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not lo <= value <= hi:
        raise LayoutError(f"{where}: must be a number in [{lo}, {hi}]")
    return float(value)


def _point(value, where: str) -> Tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise LayoutError(f"{where}: must be [x, y]")
    return _num(value[0], where + ".x", 0, 1), _num(value[1], where + ".y", 0, 1)


def validate_set_analysis(obj: Any) -> Dict:
    """{camera: eye|low|high|top, horizon_y: -2..3 or null, camera_height_m?: >0, ground: [[x,y], >=3 points],
    landmarks: [{name, box: [x0,y0,x1,y1], height_m}], light?: text, notes?: text}"""
    if not isinstance(obj, dict):
        raise LayoutError("set analysis must be an object")
    if obj.get("camera") not in CAMERA_CLASSES:
        raise LayoutError(f"camera: one of {', '.join(CAMERA_CLASSES)}")
    if obj.get("horizon_y") is not None:
        _num(obj["horizon_y"], "horizon_y", -2, 3)
    elif obj["camera"] != "top":
        raise LayoutError("horizon_y: needed unless the camera looks straight down (top)")
    if obj.get("camera_height_m") is not None:
        _num(obj["camera_height_m"], "camera_height_m", 0.1, 500)
    ground = obj.get("ground")
    if not isinstance(ground, list) or len(ground) < 3:
        raise LayoutError("ground: a polygon of at least 3 [x, y] points")
    for i, pt in enumerate(ground):
        _point(pt, f"ground[{i}]")
    for i, lm in enumerate(obj.get("landmarks") or []):
        w = f"landmarks[{i}]"
        if not isinstance(lm, dict) or not isinstance(lm.get("name"), str):
            raise LayoutError(f"{w}: needs a name")
        box = lm.get("box")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            raise LayoutError(f"{w}.box: [x0, y0, x1, y1]")
        x0, y0, x1, y1 = (_num(v, f"{w}.box", 0, 1) for v in box)
        if x1 <= x0 or y1 <= y0:
            raise LayoutError(f"{w}.box: x1 > x0 and y1 > y0")
        _num(lm.get("height_m"), f"{w}.height_m", 0.05, 500)
    return obj


def camera_height(analysis: Dict) -> float:
    """Camera height above the ground in metres. Best: from landmarks standing on the ground, since for a level camera
    object_height / camera_height = (y_bottom - y_top) / (y_bottom - y_horizon). Else the analysis' estimate, else a default
    for the camera class."""
    h = analysis.get("horizon_y")
    if h is not None:
        found = []
        for lm in analysis.get("landmarks") or []:
            x0, y0, x1, y1 = lm["box"]
            if y1 - h > 0.02:                                 # the landmark's foot is below the horizon: usable
                found.append(lm["height_m"] * (y1 - h) / (y1 - y0))
        if found:
            found.sort()
            return found[len(found) // 2]
    if analysis.get("camera_height_m"):
        return float(analysis["camera_height_m"])
    return DEFAULT_CAMERA_HEIGHT_M[analysis["camera"]]


def person_height(analysis: Dict, foot_y: float, person_m: float = PERSON_HEIGHT_M) -> float:
    """Height (fraction of the picture height) of a person whose feet are at foot_y. Level-camera approximation, which is close
    for the moderate tilts of establishing shots; far people come out smaller, near people bigger."""
    h = analysis.get("horizon_y")
    if h is None:                                            # straight down: everyone at one scale
        return min(max(0.9 * person_m / camera_height(analysis), 0.02), 0.9)
    return min(max((foot_y - h) * person_m / camera_height(analysis), 0.02), 1.5)


def _inside(pt, poly) -> bool:
    x, y = pt
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def on_ground(analysis: Dict, pt: Tuple[float, float]) -> Tuple[float, float]:
    """The foot point itself when it is on the walkable ground, else the nearest point of the ground's edge (a person placed on
    a wall or in the sky is moved to where they can stand)."""
    poly = [tuple(p) for p in analysis["ground"]]
    if _inside(pt, poly):
        return pt
    best, dist = pt, None
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (dx * dx + dy * dy)))
        q = (x1 + t * dx, y1 + t * dy)
        d = (q[0] - pt[0]) ** 2 + (q[1] - pt[1]) ** 2
        if dist is None or d < dist:
            best, dist = q, d
    return best


# ---- shot layout (per scene) ---------------------------------------------------------------------------------
def validate_shot_layout(obj: Any, cast: Sequence[str] = ()) -> Dict:
    """{background: <picture id or key>, redraw: bool, redraw_note?: text, camera?: text,
    people: [{name, foot: [x, y], facing: left|right|camera|away, pose?: text}]}"""
    if not isinstance(obj, dict):
        raise LayoutError("shot layout must be an object")
    if not isinstance(obj.get("redraw", False), bool):
        raise LayoutError("redraw: true or false")
    people = obj.get("people")
    if not isinstance(people, list):
        raise LayoutError("people: a list (empty when nobody is in the shot)")
    names = set(cast)
    for i, person in enumerate(people):
        w = f"people[{i}]"
        if not isinstance(person, dict) or not isinstance(person.get("name"), str):
            raise LayoutError(f"{w}: needs a name")
        if names and person["name"] not in names:
            raise LayoutError(f"{w}.name: '{person['name']}' is not in this scene")
        _point(person.get("foot"), f"{w}.foot")
        if person.get("facing", "camera") not in FACINGS:
            raise LayoutError(f"{w}.facing: one of {', '.join(FACINGS)}")
    return obj


def place(analysis: Dict, shot: Dict) -> List[Dict]:
    """Where each person goes, in drawing order (farthest first): [{name, foot, height, facing, color_index, moved}] with foot /
    height as picture fractions; `moved` = the foot was off the walkable ground and was put back on it."""
    out = []
    for i, person in enumerate(shot.get("people") or []):
        asked = tuple(person["foot"])
        foot = on_ground(analysis, asked)
        out.append({"name": person["name"], "foot": foot, "height": person_height(analysis, foot[1]),
                    "facing": person.get("facing", "camera"), "pose": person.get("pose") or "", "color_index": i % len(COLORS),
                    "moved": foot != asked})
    return sorted(out, key=lambda p: p["foot"][1])


# ---- drawing ----------------------------------------------------------------------------------------------------
def _cover(img, size):
    """Scale and centre-crop a picture to fill `size` exactly (like a background plate)."""
    from PIL import Image
    w, h = img.size
    scale = max(size[0] / w, size[1] / h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    left, top = (img.width - size[0]) // 2, (img.height - size[1]) // 2
    return img.crop((left, top, left + size[0], top + size[1]))


def _cutout(path: Optional[str]):
    """The person's picture when it has real transparency (a cut-out render), cropped to the figure; else None."""
    if not path or not os.path.exists(path):
        return None
    from PIL import Image
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:  # noqa: BLE001 - unreadable picture: fall back to a mannequin
        return None
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] > 250:                       # fully opaque: not a cut-out
        return None
    box = alpha.getbbox()
    return img.crop(box) if box else None


def _mannequin(draw, cx, foot_y, height, color, facing):
    """A plain figure: head + body + legs, with a nose mark showing which way the person faces."""
    head = height * 0.13
    top = foot_y - height
    w = height * 0.26
    draw.ellipse([cx - head / 2, top, cx + head / 2, top + head], fill=color)
    draw.rounded_rectangle([cx - w / 2, top + head * 1.05, cx + w / 2, foot_y - height * 0.45], radius=w * 0.25, fill=color)
    leg = w * 0.38
    draw.rectangle([cx - w / 2 + 1, foot_y - height * 0.47, cx - w / 2 + 1 + leg, foot_y], fill=color)
    draw.rectangle([cx + w / 2 - 1 - leg, foot_y - height * 0.47, cx + w / 2 - 1, foot_y], fill=color)
    mark = {"left": -1, "right": 1}.get(facing)
    if mark:
        y = top + head * 0.5
        draw.polygon([(cx + mark * head * 0.5, y - head * 0.15), (cx + mark * head * 0.85, y), (cx + mark * head * 0.5, y + head * 0.15)],
                     fill=color)


def compose(background: str, analysis: Dict, shot: Dict, pictures: Optional[Dict[str, str]] = None,
            out_path: Optional[str] = None, size: Tuple[int, int] = SIZE, labels: bool = False):
    """Draw one shot's layout: the background plate, then every person farthest-first on the ground at perspective size, with a
    contact shadow. A cut-out picture (transparent PNG) of the person is used when there is one, else a coloured mannequin.
    labels=True adds names (for the storyboard sheet; the layout sent to the image model has no text in it).
    Returns (PIL image, placed people)."""
    from PIL import Image, ImageDraw
    pictures = pictures or {}
    canvas = _cover(Image.open(background).convert("RGB"), size).convert("RGBA")
    W, H = size
    people = place(analysis, shot)
    for p in people:
        cx, fy, ph = p["foot"][0] * W, p["foot"][1] * H, p["height"] * H
        shadow = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse([cx - ph * 0.18, fy - ph * 0.025, cx + ph * 0.18, fy + ph * 0.025], fill=(0, 0, 0, 110))
        canvas = Image.alpha_composite(canvas, shadow)
        cut = _cutout(pictures.get(p["name"]))
        if cut is not None:
            scale = ph / cut.height
            fig = cut.resize((max(1, round(cut.width * scale)), max(1, round(ph))), Image.LANCZOS)
            if p["facing"] == "left":
                fig = fig.transpose(Image.FLIP_LEFT_RIGHT)
            layer = Image.new("RGBA", size, (0, 0, 0, 0))
            layer.paste(fig, (round(cx - fig.width / 2), round(fy - fig.height)), fig)
            canvas = Image.alpha_composite(canvas, layer)
        else:
            _mannequin(ImageDraw.Draw(canvas), cx, fy, ph, COLORS[p["color_index"]] + (255,), p["facing"])
        if labels:
            ImageDraw.Draw(canvas).text((cx - ph * 0.2, fy + 4), p["name"], fill=(255, 255, 255, 255), stroke_width=2,
                                        stroke_fill=(0, 0, 0, 255))
    img = canvas.convert("RGB")
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        img.save(out_path)
    return img, people


def layout_note(people: List[Dict], has_cutouts: bool = False) -> str:
    """Words for the image model: the attached layout fixes composition, camera, positions and sizes; which figure is who."""
    who = "; ".join(f"the {COLOR_NAMES[p['color_index']]} figure is {p['name']}" for p in people if not has_cutouts)
    return ("The LAYOUT image is a blocking mock-up of this exact shot: keep its camera angle, framing, the background layout and "
            "every person's position, size and facing exactly; people stand on the ground with their feet where the figures' feet "
            "are. Replace the flat figures by the real people from their reference images and render the whole frame as a finished "
            "shot. " + (f"In the layout {who}. " if who else ""))


def layout_reference(data_dir: str, project_id: int, idx: int, scene_data: Dict) -> Optional[Dict]:
    """The composed layout of a scene (<data>/<project>/layouts/S01.png, made by core.previz) as a reference picture for the image
    model and the QC agent: {path, label, role: "layout", people, redraw_note}. None when the scene has not been laid out."""
    shot = scene_data.get("layout")
    path = os.path.join(data_dir, str(project_id), "layouts", f"S{idx:02d}.png")
    if not shot or not os.path.exists(path):
        return None
    return {"path": path, "label": "layout", "role": "layout", "people": scene_data.get("layout_people") or [],
            "redraw_note": shot.get("redraw_note") if shot.get("redraw") else ""}


def storyboard(frames: Sequence[Tuple[str, str]], out_path: str, cols: int = 3, cell: Tuple[int, int] = (480, 270)) -> str:
    """All composed shots on one sheet, in order, each with its caption ("S01 · nhóm 1 · ..."). Returns out_path."""
    from PIL import Image, ImageDraw
    rows = max(1, -(-len(frames) // cols))
    pad, cap = 12, 26
    sheet = Image.new("RGB", (cols * (cell[0] + pad) + pad, rows * (cell[1] + cap + pad) + pad), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for i, (path, caption) in enumerate(frames):
        x = pad + (i % cols) * (cell[0] + pad)
        y = pad + (i // cols) * (cell[1] + cap + pad)
        try:
            sheet.paste(_cover(Image.open(path).convert("RGB"), cell), (x, y))
        except Exception:  # noqa: BLE001 - a missing frame stays an empty cell with its caption
            draw.rectangle([x, y, x + cell[0], y + cell[1]], outline=(90, 90, 90))
        draw.text((x, y + cell[1] + 6), caption, fill=(235, 235, 235))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    sheet.save(out_path)
    return out_path
