"""G0 mục 5 (cờ director_camera_plan): QC bố cục bằng CODE sau khi vẽ ảnh — so ảnh vừa vẽ với render nền 3D đã gửi kèm, không gọi
model, 0 USD. Chỉ ĐÁNH DẤU "nền lệch render" cho người duyệt (diag + <data_dir>/<pid>/plate_layout.json), không tự vẽ lại.

Ba số, ngoài ô nhân vật (subject_box nới 15 %):
  - đường chân trời: hàng có bước sáng/tối mạnh nhất (trời ↔ đất) của ảnh so với của render — model chép máy cúi/ngang sai thì lệch;
  - vùng quanh chân trời của render: mật độ cạnh của ảnh / của render — một bức tường / mảng phẳng che cảnh xa thì gần 0
    (#24 shot 5: "2 lớp tường che kín khung");
  - độ khớp đường nét (place_refs.background_match, KLD-17) — chỉ ghi số, chưa hiệu chỉnh nên chỉ tính khi rất thấp.
Ngưỡng tạm (chưa hiệu chỉnh trên ảnh thật — ghi kèm số để người duyệt tự xem)."""
import json
import os
import threading
from typing import Dict, List, Optional, Sequence

HORIZON_DIFF = 0.15        # chân trời lệch quá 15 % chiều cao khung
BAND = 0.15                # dải ± quanh chân trời của render
BAND_RATIO_LOW = 0.30      # ảnh còn < 30 % mật độ cạnh của render trong dải đó → mảng phẳng che cảnh xa
EDGE_VERY_LOW = 0.15       # đường nét gần như không liên quan (F1 Canny)
MIN_STEP = 0.06            # bước sáng tối nhỏ hơn: không có chân trời rõ
SIDE = 144
CODE = "plate_layout"
_LOCK = threading.Lock()


def _gray(path: str, size) -> Optional["object"]:
    import numpy as np
    from PIL import Image
    try:
        with Image.open(path) as im:
            return np.asarray(im.convert("L").resize(size), dtype=np.float32) / 255.0
    except (OSError, ValueError):
        return None


def _mask(shape, box: Optional[Sequence[float]]):
    import numpy as np
    h, w = shape
    m = np.ones((h, w), dtype=bool)
    if box:
        x0, y0, x1, y1 = box
        pw, ph = (x1 - x0) * 0.15, (y1 - y0) * 0.15
        m[int(max(y0 - ph, 0) * h):int(min(y1 + ph, 1) * h), int(max(x0 - pw, 0) * w):int(min(x1 + pw, 1) * w)] = False
    return m


def horizon_row(a, mask) -> Optional[float]:
    """Fraction from the top of the strongest bright↔dark step of the row means (columns outside the mask), None when there is none."""
    import warnings
    import numpy as np
    h = a.shape[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)            # a row fully inside the character's box: its plain mean is used
        rows = np.nanmean(np.where(mask, a, np.nan), axis=1)
    rows = np.where(np.isnan(rows), a.mean(axis=1), rows)
    k = max(3, h // 32)
    best, at = 0.0, None
    for r in range(max(k, int(h * 0.05)), min(h - k, int(h * 0.95))):
        step = abs(float(rows[r - k:r].mean()) - float(rows[r:r + k].mean()))
        if step > best:
            best, at = step, r
    return round(at / h, 3) if at is not None and best >= MIN_STEP else None


def _edges(a):
    import numpy as np
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    gx[:, 1:] = np.abs(np.diff(a, axis=1))
    gy[1:, :] = np.abs(np.diff(a, axis=0))
    return gx + gy


def _band_density(a, mask, centre: float) -> float:
    h = a.shape[0]
    r0, r1 = int(max(centre - BAND, 0) * h), int(min(centre + BAND, 1) * h)
    e = _edges(a)[r0:r1]
    m = mask[r0:r1]
    return float(e[m].mean()) if m.any() else 0.0


def compare(image_path: str, plate_path: str, box: Optional[Sequence[float]] = None,
            horizon_expected: Optional[float] = None) -> Dict:
    """{"mismatch", "reasons" (tiếng Việt), "horizon_plate", "horizon_image", "band_ratio", "edge", "horizon_source"}. Unreadable → not
    flagged, said. horizon_expected (10/10, core/stage_facts.horizon): the horizon row computed from the stage camera's pitch + FOV —
    used when the render shows none (night fog: the old blind measure gave None and the horizon was never compared)."""
    from PIL import Image
    try:
        with Image.open(plate_path) as im:
            pw, ph = im.size
    except (OSError, ValueError):
        return {"mismatch": False, "reasons": ["không đọc được render nền — không so bố cục"]}
    size = (SIDE, max(8, int(round(SIDE * ph / max(pw, 1)))))
    b, a = _gray(plate_path, size), _gray(image_path, size)
    if a is None or b is None:
        return {"mismatch": False, "reasons": ["không đọc được ảnh vẽ / render — không so bố cục"]}
    mask = _mask(a.shape, box)
    reasons: List[str] = []
    hb, ha = horizon_row(b, mask), horizon_row(a, mask)
    source = "render" if hb is not None else None
    from .place_refs import LIFT_BELOW
    # rà kỹ 10/10 lỗi 5: số giải tích chỉ thay đo mù khi render TỐI (đêm sương: đo không ra); render sáng mà không có chân trời là
    # cảnh không có chân trời (tường, nhà che) — không ép số. Và chỉ so khi ảnh vẽ đo được chân trời (ảnh tối không có → không cờ)
    dark = float(b.mean()) * 255.0 < LIFT_BELOW
    analytic = hb is None and dark and horizon_expected is not None and 0.0 < float(horizon_expected) < 1.0
    if analytic:
        hb, source = float(horizon_expected), "giai_tich"
    if hb is not None and (ha is None or abs(ha - hb) > HORIZON_DIFF) and not (analytic and ha is None):
        reasons.append(f"đường chân trời ảnh ở {ha * 100:.0f}% khung, render ở {hb * 100:.0f}% — máy (cúi/ngang) khác render"
                       if ha is not None else f"render có đường chân trời ở {hb * 100:.0f}% khung, ảnh không có — nền khác render")
    if analytic and reasons:
        reasons[-1] += " (chân trời render tính bằng giải tích từ góc máy 3D — render tối không đo được)"
    ratio = None
    if hb is not None and not analytic:
        db = _band_density(b, mask, hb)
        if db > 1e-3:
            ratio = round(_band_density(a, mask, hb) / db, 3)
            if ratio < BAND_RATIO_LOW:
                reasons.append(f"vùng quanh chân trời của render trong ảnh gần như phẳng (đường nét còn {ratio * 100:.0f}% so với render) — "
                               "có thể tường / mảng phẳng che cảnh xa")
    edge = None
    try:
        from .place_refs import background_match
        edge = background_match(image_path, plate_path, list(box) if box else None)
    except Exception:  # noqa: BLE001 - no opencv: the other two numbers stay
        edge = None
    if edge is not None and edge < EDGE_VERY_LOW:
        reasons.append(f"đường nét kiến trúc gần như không khớp render (F1 {edge:.2f})")
    return {"mismatch": bool(reasons), "reasons": reasons, "horizon_plate": hb, "horizon_image": ha, "band_ratio": ratio, "edge": edge,
            "horizon_source": source}


def _stage_horizon(conn, pid: int, scene_id: int) -> Optional[float]:
    """Hàng chân trời giải tích của máy Sân khấu 3D (cờ stage_camera + shot có stage_camera), None khi không có."""
    from . import features, stage_facts
    if not features.on("stage_camera"):
        return None
    try:
        row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
        data = json.loads((row[0] if row else None) or "{}")
        st = stage_facts.stage_of(data)
        if st is None:
            return None
        from . import place_refs
        proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        w, h = place_refs.resolution_of(proj) if proj is not None else (9, 16)
        aspect = w / h
        return stage_facts.horizon(st["cam"], st["aim"], st["lens"], aspect)["w"]
    except Exception:  # noqa: BLE001 - no number: the render's own measure stays (as before)
        return None


def record_path(data_dir: str, pid: int) -> str:
    return os.path.join(data_dir, str(pid), "plate_layout.json")


def check_job(conn, data_dir: str, pid: int, scene_id: int, job_id: int, image_path: str, resolution=None):
    """After a picture arrives (core/runner ImageRunner._after_download): (severity, words) for diag, or None when the flag is off.
    `resolution` given → a render the plan has left (stale) is not compared (the number would be about the wrong place)."""
    from . import camera_plan, place_refs
    if not camera_plan.enabled():
        return None
    ref = place_refs.shot_ref(data_dir, pid, scene_id)
    if ref is None:
        return ("info", "không có render 3D của shot — không so bố cục nền")
    if resolution is not None:
        gone = place_refs.stale(conn, data_dir, pid, resolution)
        if -1 in gone or scene_id in gone:
            return ("info", "không so bố cục: render đang gắn không còn là render của kế hoạch")
    res = compare(image_path, ref["path"], ref["_rec"].get("subject_box"), horizon_expected=_stage_horizon(conn, pid, scene_id))
    row = {"job_id": job_id, "scene_id": scene_id, "plate_key": ref.get("plate_key"), **res}
    path = record_path(data_dir, pid)
    with _LOCK:
        try:
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
        except (OSError, ValueError):
            rows = []
        rows = [r for r in rows if r.get("job_id") != job_id] + [row]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    if res["mismatch"]:
        return ("warn", "nền lệch render 3D (chỉ đánh dấu cho người duyệt, không tự vẽ lại): " + "; ".join(res["reasons"]))
    return ("info", "bố cục nền khớp render 3D" + (f" (chân trời {res['horizon_image']:.2f}/{res['horizon_plate']:.2f})"
                                                   if res.get("horizon_plate") is not None and res.get("horizon_image") is not None
                                                   else ""))
