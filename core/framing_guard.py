"""Lỗi hệ thống 2 (#27, 13/10 — docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md mục 6.2): video tự đổi bố cục / kiến trúc hoặc cắt cảnh.

  #27 shot 17 (job 858, 890, 912): Seedance 2.5 bỏ khung đầu đã duyệt ngay từ khung 0 — máy lùi + chúc, nền vẽ lại (tháp có mặt đồng
  hồ, tháp 3D không có); QC Claude chấm 1,00 "đạt" cả ba lần. #27 shot 16 (job 898, 907): khung cuối vẽ Kelly ở xa sau tường trong khi
  ảnh đầu Kelly đứng sát máy → model kéo lùi Kelly / nhảy cóc ra xa trong 0,2 s (người dùng: "khung cuối mới cùng khoảng cách máy").

Công thức chung (0 USD, chỉ OpenCV trên máy), cờ `framing_guard` (MẶC ĐỊNH TẮT — tắt: không đo, không đổi gì):
  (a) TRƯỚC gen — `end_frame_distance(ảnh đầu, khung cuối)`: khung cuối phải CÙNG khoảng cách máy / cỡ cảnh với ảnh đầu. Đo hai thứ:
      tỉ lệ nền (ORB + affine đồng dạng RANSAC: cảnh vật đứng yên phóng / thu bao nhiêu) và tỉ lệ cỡ mặt người lớn nhất (YuNet — người
      ở gần / xa máy). Lệch quá ngưỡng → runner KHÔNG gửi khung cuối đó (VÀNG có số đo, `core/runner._end_frame`).
  (b) SAU gen — `clip_framing(clip, ảnh đầu)`: khung 0 so ảnh đầu (tỉ lệ + dịch khung + tỉ lệ điểm khớp), tỉ lệ nền từng ~0,25 s so
      khung 0 (zoom / lùi máy), cỡ mặt nhảy vọt trong ≤ 0,35 s (người dịch chỗ tức thì), điểm cắt cảnh (clip_measure.jerks). Có lỗi →
      cờ đo `framing` (ĐỎ): `pipeline.apply_qc` giữ clip cho người (không tự duyệt) + gợi ý đổi model / bỏ khung cuối. Không đo được
      → nói rõ (VÀNG), không coi là đạt.

Ngưỡng đặt trên clip / ảnh thật #27 (số trong chú thích từng hằng; fixture thu nhỏ ở tests/fixtures/framing_p27/)."""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

FLAG = "framing_guard"
WIDTH = 480                 # ORB on a 480-px copy: enough for the background's scale, fast
ORB_N = 4000
RATIO = 0.75                # Lowe ratio test
RANSAC_PX = 4.0
MIN_KEYPOINTS = 150         # fewer keypoints in the reference picture → cannot measure (sky / dark / blank), said
# (a) end frame vs start picture
END_SCALE = 1.15            # background scale outside [1/1.15, 1.15] → another camera distance. #27 end_284_16…21 vs job 836: 0.998–0.999
END_FACE = 1.33             # biggest face height ratio outside [1/1.33, 1.33] → the subject at another distance from the camera. #27 shot
                            # 16: job 836 Kelly 12–13 % of the height, end frames 16 / 19 / 20 ×0,57–0,74 (by resolution) — Kelly further
                            # back; the person rejected those end frames and their clips (889, 898) and kept 21 (Kelly hidden behind the
                            # wall). The same face at the same distance measures within ±10 %
# (b) clip
F0_CORNER = 0.07            # frame 0 vs start picture: a corner of the picture moved more than this share of the frame (scale + shift
                            # together) → reframed. #27: Kling 915 0.00, 849 0.00; Seedance 899 0.049, 903 0.055, 905 0.057 (approved by
                            # the person — Seedance always slides ~4–5 % down); bad 912 0.088 (×0.95 + 6 % down, clock face drawn), 812 0.20
F0_INLIERS = 0.05           # …or fewer than this share of the picture's keypoints match frame 0 → another layout (#27: 915 0.12, 812
                            # 0.06, 908 0.01 — the glue wall drawn over the whole frame)
ZOOM_OUT = 0.85             # a frame's background scale vs frame 0 below this → the camera pulled back
ZOOM_IN = 1.30              # …above this → pushed in hard (a slow push-in of a motion prompt stays below)
STEP_S = 0.25               # seconds between frames for the zoom series
FACE_JUMP = 1.8             # biggest face height changes more than × this inside FACE_JUMP_S → the person jumped (#27 907: Kelly ×3,6
FACE_JUMP_S = 0.35          # in 0,2 s); a walk away over seconds stays below
FACE_MIN_H = 0.03           # faces smaller than this share of the frame height are too noisy to compare
FACE_WIDTH = 960            # pictures are compared at one width: YuNet's box on a stylised face moves ±10 % with the resolution
# (b2) V2 (rà gốc 13/10, G6): the clip's LAST frame vs the start picture — the camera stayed, the architecture was redrawn as the clip
# went (858: a clock face grown on the tower, frame 0 fine). #27: kept 903 last/start 0.24 (frame 0 0.21), 915 0.14 (0.12); 907 (the
# person jumps away, background unchanged) 0.054 (0.144) — must stay out of this check, "jump" flags it
END_DRIFT = 0.30            # last frame's inlier share below this × frame 0's share …
END_DRIFT_MIN = 0.03        # … (and below at least this) → the background is not the start picture's any more
CAM_STILL = 0.10            # the samples of the clip's first half moved a picture corner less than this → the camera stayed


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _cv():
    from .clip_measure import _cv as cv
    return cv()


def _gray(img):
    cv2 = _cv()
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return cv2.resize(g, (WIDTH, max(1, int(g.shape[0] * WIDTH / g.shape[1]))), interpolation=cv2.INTER_AREA)


def _features(img):
    cv2 = _cv()
    g = _gray(img)
    k, d = cv2.ORB_create(ORB_N, edgeThreshold=15, patchSize=15).detectAndCompute(g, None)
    return g.shape, k, d


def similarity(a, b, fa=None, fb=None) -> Dict:
    """b against a (BGR images, any size; b is resized to a's aspect): {"scale", "dx", "dy" (share of width / height), "inliers",
    "keypoints" (of a), "inlier_share"} — scale < 1: b shows the same things smaller (camera further back). "scale" None when there is
    nothing to match (said in "note")."""
    import numpy as np
    cv2 = _cv()
    (h, w), ka, da = fa or _features(a)
    if fb is None:
        bb = cv2.resize(b, (w, h), interpolation=cv2.INTER_AREA) if b.shape[1] * h != b.shape[0] * w else b
        fb = _features(bb)
    _, kb, db = fb
    out: Dict = {"keypoints": len(ka or ())}
    if da is None or db is None or len(ka) < MIN_KEYPOINTS:
        return dict(out, scale=None, note=f"ít điểm đặc trưng ({len(ka or ())}) — ảnh trơn / tối, không đo được tỉ lệ")
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < RATIO * p[1].distance]
    if len(good) < 8:
        return dict(out, scale=None, inliers=0, inlier_share=0.0, note="hai ảnh gần như không có điểm khớp")
    pa = np.float32([ka[g.queryIdx].pt for g in good])
    pb = np.float32([kb[g.trainIdx].pt for g in good])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX)
    if M is None:
        return dict(out, scale=None, inliers=0, inlier_share=0.0, note="không ước được phép biến đổi giữa hai ảnh")
    n = int(inl.sum())
    s = float(np.hypot(M[0, 0], M[1, 0]))
    # where a's centre lands in b, minus the centre: the frame's shift (scale about the centre is not a shift)
    cx, cy = w / 2, h / 2
    dx = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2]) - cx
    dy = (M[1, 0] * cx + M[1, 1] * cy + M[1, 2]) - cy
    corner = max(max(abs(M[0, 0] * x + M[0, 1] * y + M[0, 2] - x) / w, abs(M[1, 0] * x + M[1, 1] * y + M[1, 2] - y) / h)
                 for x in (0, w) for y in (0, h))
    return dict(out, scale=round(s, 3), dx=round(float(dx) / w, 3), dy=round(float(dy) / h, 3), corner=round(float(corner), 3),
                inliers=n, inlier_share=round(n / len(ka), 3))


def face_height(img, pictures: bool = False) -> Optional[float]:
    """The biggest face's height as a share of the picture height (YuNet), None without a face / the model. pictures: two stills of
    different sizes are compared — measure both at FACE_WIDTH."""
    from .clip_measure import _faces
    if pictures:
        cv2 = _cv()
        h0, w0 = img.shape[:2]
        img = cv2.resize(img, (FACE_WIDTH, max(1, int(h0 * FACE_WIDTH / w0))),
                         interpolation=cv2.INTER_AREA if w0 > FACE_WIDTH else cv2.INTER_LINEAR)
    faces = _faces(img)
    if not faces:
        return None
    h = faces[0][3] / img.shape[0]
    return h if h >= FACE_MIN_H else None


def _read(path: str):
    cv2 = _cv()
    try:
        import numpy as np
        data = np.fromfile(path, dtype=np.uint8)            # cv2.imread fails on non-ASCII Windows paths
        return cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    except (OSError, ValueError):
        return None


# ---- (a) TRƯỚC gen -----------------------------------------------------------------------------------------------------------------
def end_frame_distance(start_path: str, end_path: str) -> Dict:
    """Is the end frame at the same camera distance / shot size as the start picture? {"ok": True | False | None, "scale",
    "face_ratio", "why" (Vietnamese, with the numbers) | "note" (why it could not be measured)}. ok None = could not measure."""
    a, b = (_read(start_path) if start_path else None), (_read(end_path) if end_path else None)
    if a is None or b is None:
        return {"ok": None, "note": "không đọc được " + ("ảnh đầu" if a is None else "khung cuối")}
    sim = similarity(a, b)
    fa, fb = face_height(a, True), face_height(b, True)
    ratio = round(fb / fa, 3) if fa and fb else None
    out: Dict = {"scale": sim.get("scale"), "corner": sim.get("corner"), "inliers": sim.get("inliers"), "face_ratio": ratio,
                 "face_start": round(fa, 3) if fa else None, "face_end": round(fb, 3) if fb else None}
    bad = []
    s = sim.get("scale")
    if s is not None and not 1 / END_SCALE <= s <= END_SCALE:
        bad.append(f"nền {'thu nhỏ' if s < 1 else 'phóng to'} × {s:.2f} (máy {'lùi xa' if s < 1 else 'tiến gần'}; cho phép "
                   f"{1 / END_SCALE:.2f}–{END_SCALE:.2f})")
    if ratio is not None and not 1 / END_FACE <= ratio <= END_FACE:
        bad.append(f"mặt người lớn nhất cao {fb * 100:.1f} % khung so với {fa * 100:.1f} % ở ảnh đầu (× {ratio:.2f}; cho phép "
                   f"{1 / END_FACE:.2f}–{END_FACE:.2f}) — người ở khoảng cách máy khác")
    if bad:
        return dict(out, ok=False, why="khung cuối khác khoảng cách máy với ảnh đầu: " + "; ".join(bad))
    if s is None and ratio is None:
        return dict(out, ok=None, note="không đo được khoảng cách máy (" + (sim.get("note") or "không khớp được nền")
                    + ("" if fa and fb else "; không thấy mặt ở " + ("cả hai ảnh" if not fa and not fb else "ảnh đầu" if not fa else
                                                                    "khung cuối")) + ")")
    part = [] if s is not None else ["chưa đo được tỉ lệ nền"]
    if ratio is None:
        # V3 (rà gốc 13/10, G7): end_284_21 (Kelly behind the wall, no face) passed as ok=True → 907 jumped. Not measured is never a
        # pass (CHUAN_XAY_DUNG): ok None, the runner decides (a person acting → the end frame is not sent)
        part.append("chưa so được cỡ người (không thấy mặt ở " + ("ảnh đầu" if not fa else "khung cuối") + " — người khuất / quay đi?)"
                    if (fa or fb) else "chưa so được cỡ người (không thấy mặt)")
        return dict(out, ok=None, note="; ".join(part))
    return dict(out, ok=True, **({"note": "; ".join(part)} if part else {}))


_END_CACHE: Dict[Tuple, Dict] = {}


def end_frame_check(start_path: Optional[str], end_path: Optional[str]) -> Optional[Dict]:
    """end_frame_distance cached by (paths, mtimes) — the runner asks several times per send. None when the flag is off."""
    if not enabled() or not end_path:
        return None
    if not start_path or not os.path.exists(start_path):
        return {"ok": None, "note": "không có ảnh khung đầu đã duyệt để so khung cuối"}
    try:
        key = (os.path.abspath(start_path), os.path.getmtime(start_path), os.path.abspath(end_path), os.path.getmtime(end_path))
    except OSError:
        return {"ok": None, "note": "không đọc được tệp ảnh đầu / khung cuối"}
    if key not in _END_CACHE:
        try:
            _END_CACHE[key] = end_frame_distance(start_path, end_path)
        except Exception as e:  # noqa: BLE001 - OpenCV missing / broken file: said, never a silent pass
            return {"ok": None, "note": f"lỗi khi đo khung cuối: {e}"}
    return _END_CACHE[key]


# ---- (b) SAU gen -------------------------------------------------------------------------------------------------------------------
def _clip_frames(clip: str) -> Tuple[List, float]:
    from .clip_measure import frames
    return frames(clip, width=WIDTH)          # the measures all work on a WIDTH copy (a 1080p clip: 4× fewer pixels for the faces)


def clip_framing(clip: str, picture: Optional[str], cuts: Optional[List[float]] = None) -> Dict:
    """Did the clip keep the start picture's layout (module doc)? {"flag": "framing" | None, "why", "frame0", "zoom", "face_jumps",
    "cuts", "suggest"} or {"flag": None, "measured": False, "note"} when nothing could be measured — never a silent pass."""
    fs, fps = _clip_frames(clip)
    if len(fs) < 3:
        return {"flag": None, "measured": False, "note": "không đọc được clip / clip quá ngắn — chưa đo được bố cục"}
    fps = fps or 24.0
    why, notes, kinds = [], [], []
    out: Dict = {"measured": True, "frame0_measured": False}
    # 1. frame 0 vs the approved start picture
    pic = _read(picture) if picture and os.path.exists(picture) else None
    if pic is None:
        notes.append("không có ảnh khung đầu để so khung 0")
    else:
        f0 = similarity(pic, fs[0])
        out["frame0"] = f0
        out["frame0_measured"] = f0.get("keypoints", 0) >= MIN_KEYPOINTS
        if not out["frame0_measured"]:
            notes.append("khung 0: " + f0.get("note", "không đo được"))
        elif f0.get("scale") is None or f0.get("inlier_share", 0) < F0_INLIERS:
            kinds.append("frame0")
            why.append(f"khung 0 khác hẳn ảnh đầu (khớp {f0.get('inliers', 0)}/{f0['keypoints']} điểm) — model vẽ lại bố cục")
        else:
            if f0["corner"] > F0_CORNER:
                kinds.append("frame0")
                why.append(f"khung 0 lệch ảnh đầu: tỉ lệ × {f0['scale']:.2f}"
                           + (f" ({'lùi máy' if f0['scale'] < 1 else 'tiến máy'})" if abs(f0["scale"] - 1) > 0.02 else "")
                           + f", khung dịch {f0['dx'] * 100:+.0f} % ngang / {f0['dy'] * 100:+.0f} % dọc — góc khung lệch "
                           f"{f0['corner'] * 100:.0f} % (cho phép {F0_CORNER * 100:.0f} %): model không giữ khung đầu đã duyệt")
    # 2. background scale over time vs frame 0
    step = max(1, int(round(STEP_S * fps)))
    base = _features(fs[0])
    zoom = []
    if len(base[1] or ()) >= MIN_KEYPOINTS:
        for i in range(step, len(fs), step):
            r = similarity(fs[0], fs[i], fa=base)
            if r.get("scale") is not None and r.get("inliers", 0) >= 20:
                zoom.append((round(i / fps, 2), r["scale"]))
        out["zoom"] = zoom
        lo = min(zoom, key=lambda z: z[1]) if zoom else None
        hi = max(zoom, key=lambda z: z[1]) if zoom else None
        if lo and lo[1] < ZOOM_OUT:
            kinds.append("zoom")
            why.append(f"máy lùi / thu nhỏ cảnh trong clip (nền × {lo[1]:.2f} ở {lo[0]} s so khung 0)")
        if hi and hi[1] > ZOOM_IN:
            kinds.append("zoom")
            why.append(f"máy tiến / phóng cảnh trong clip (nền × {hi[1]:.2f} ở {hi[0]} s so khung 0)")
    else:
        notes.append("khung 0 ít điểm đặc trưng — chưa đo được zoom / lùi máy")
    # 2b. V2: the last frame vs the start picture — the camera stayed but the architecture changed (only when frame 0 kept the picture)
    if pic is not None and out["frame0_measured"] and "frame0" not in kinds:
        _end_drift(out, pic, fs, step, why, notes, kinds)
    # 3. the person jumps (face size leaps inside FACE_JUMP_S)
    sizes = [(i / fps, face_height(f)) for i, f in enumerate(fs)]
    sizes = [(t, h) for t, h in sizes if h]
    jumps = []
    for k, (t, h) in enumerate(sizes):
        for t2, h2 in sizes[k + 1:]:
            if t2 - t > FACE_JUMP_S:
                break
            r = max(h, h2) / min(h, h2)
            if r > FACE_JUMP:
                jumps.append({"from_s": round(t, 2), "to_s": round(t2, 2), "ratio": round(r, 2)})
                break
    out["faces_seen"] = len(sizes)
    out["face_jumps"] = jumps[:5]
    if jumps:
        j = max(jumps, key=lambda x: x["ratio"])
        kinds.append("jump")
        why.append(f"người nhảy vọt: cỡ mặt đổi × {j['ratio']:.1f} trong {j['to_s'] - j['from_s']:.2f} s ({j['from_s']}→{j['to_s']} s)")
    if not sizes:
        notes.append("không thấy mặt — chưa đo được người nhảy vọt")
    # 4. a cut inside the clip (clip_measure.jerks)
    if cuts:
        out["cuts"] = list(cuts)
        kinds.append("cut")
        why.append(f"cắt cảnh bên trong clip ở {list(cuts)} s")
    if notes:
        out["note"] = "; ".join(notes)
    if why:
        out["flag"] = "framing"
        out["kinds"] = list(dict.fromkeys(kinds))
        out["why"] = "đổi bố cục / cắt cảnh: " + "; ".join(why)
        out["suggest"] = suggestion(out["kinds"])
    else:
        out["flag"] = None
    return out


def _end_drift(out: Dict, pic, fs, step, why, notes, kinds) -> None:
    """V2: {"frame_end": {...}} and a "frame_end" kind when the camera stayed (the samples of the clip's first half moved < CAM_STILL)
    but the last frame matches the start picture much less than frame 0 did — the model redrew the place as the clip went. A moving
    camera (pan / follow) is not judged (said in the note): its last frame shows another view by design."""
    f0 = out.get("frame0") or {}
    last = similarity(pic, fs[-1])
    out["frame_end"] = {k: last.get(k) for k in ("scale", "corner", "inliers", "inlier_share")}
    base = _features(fs[0])
    half = [similarity(fs[0], fs[i], fa=base) for i in range(step, len(fs) // 2 + 1, step)]
    if any(h.get("scale") is None or (h.get("corner") or 0) > CAM_STILL for h in half):
        out["frame_end"]["camera"] = "moves"
        notes.append("máy chuyển động trong nửa đầu clip — không so khung cuối clip với ảnh đầu (kiến trúc)")
        return
    share0 = f0.get("inlier_share") or 0.0
    limit = max(END_DRIFT_MIN, END_DRIFT * share0)
    share = (last.get("inlier_share") or 0.0) if last.get("scale") is not None else 0.0
    if share < limit:
        kinds.append("frame_end")
        why.append(f"khung cuối clip khác ảnh đầu dù máy đứng yên (khớp {last.get('inliers', 0)}/{last.get('keypoints', 0)} điểm = "
                   f"{share * 100:.1f} % so với khung 0 {share0 * 100:.1f} %, ngưỡng {limit * 100:.1f} %) — model vẽ thêm / bớt "
                   "kiến trúc trong clip; xem khung đầu ↔ khung cuối clip cạnh nhau")


def suggestion(kinds: List[str]) -> str:
    """What to change before generating again (rule 6: a retry changes its input) — kinds: frame0 / zoom / jump / cut."""
    tips = []
    if "jump" in kinds or "cut" in kinds:
        tips.append("bỏ khung cuối (hoặc vẽ lại khung cuối CÙNG khoảng cách máy với ảnh đầu)")
    if "frame0" in kinds or "zoom" in kinds or "cut" in kinds:
        tips.append("đổi model (Kling giữ khung đầu sát hơn — #27 shot 17: Seedance lùi máy ×3, Kling 915 giữ đúng)")
    if "frame_end" in kinds:
        tips.append("prompt nói rõ kiến trúc giữ nguyên như ảnh khung đầu (không thêm mặt đồng hồ / tầng / cửa)")
    tips.append("hoặc dựng phần vật / kiến trúc bằng ghép code")
    return "gợi ý: " + "; ".join(dict.fromkeys(tips))
