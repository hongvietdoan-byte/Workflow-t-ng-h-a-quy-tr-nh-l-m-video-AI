"""S4.5 (after #8): video QC layer 0 — what a clip can be measured for without AI, before Claude or a person looks at it.

  look_drift     the clip's faces against the approved storyboard picture's faces: skin texture and colour saturation. #8 clip 01 (a
                 Kelly close-up redrawn from reference pictures) came out doll-smooth "anime" while the storyboard was the 3D render;
                 the QC scored identity and action, never the look (TONG_KET_DU_AN_8 1.3).
  jerks          optical flow between consecutive frames: a sudden spike of the whole picture's motion (a jump inside a shot) and a
                 freeze followed by a jump (TONG_KET 1.5: "khựng, giật"). Foot sliding is NOT measured (needs pose tracking) — said.
  lip_activity   how much the mouth region moves while the voice is loud vs quiet (TONG_KET 1.7: 19 dialogue shots not in sync).
                 NOT A CHECK: on #8's 4 lip-synced shots the right voice gave 0.79–1.26 and a wrong voice 0.70–1.03 — pixel change
                 around the mouth does not tell them apart (head motion, a 720p mouth of ~20 px). Kept as the fallback without the
                 landmark model; its numbers are recorded, it flags nothing.
  lip_sync       mouth landmarks (MediaPipe Face Landmarker, `data/models/face_landmarker.task`, on each YuNet face cropped and scaled
                 up — the landmarker's own detector misses the small faces of a 3-person wide shot): inner-lip gap / face height per
                 frame, per face, correlated with the voice envelope inside each spoken line's window (± 4 frames of lag). Calibrated
                 29/09 on the #10 dialogue take (S4.6 (c), 2 clips, 3 speakers; by eye Maxim and Kenta open their mouth on their turn):
                 those 4 turns score 0.72–0.96, the same voice moved ≥ 0.75 s off its time ≤ 0.58, #8's 4 lip-synced shots (mouth
                 moving ~1 s away from the voice — seen on the plotted series) 0.04–0.18. What it checks is TIMING: the mouth opens
                 while the line is heard and rests around it. It does not prove syllables: another voice put at the same seconds
                 still reached 0.50–0.64 (median), up to 0.87. Kelly's turns scored 0.31 / 0.12 and are flagged: in-game her lips stay
                 parted through the others' lines (cropped frames), in the "real 3D" clip she stands up and the best face is another.
  ref_mark       the red plus sign that marks a reference picture (seedance_refs.mark) drawn INTO the clip. A/B S4.6 (#10, 29/09):
                 Seedance 2.0 Fast kept the plus on Kelly's face for the whole clip (17/17 sampled frames, a 44×44 px square);
                 0 on the 8 other clips of the A/B and on #8's clips (Maxim's red hood gave 36×48 blobs — not square, rejected).

Thresholds were set on #8's own clips (tools/clip_measure_calibrate.py, numbers in the constants' comments); every check returns its
numbers so a person can see why. Nothing here blocks on its own: the flags go to the clip QC as evidence."""
import os
from typing import Dict, List, Optional, Tuple

FLOW_WIDTH = 256           # optical flow on a small copy: enough for whole-picture motion, fast
TEXTURE_MIN = 0.40         # face texture clip / storyboard below this → too smooth. #8: anime clip 01 = 0.30, the 11 right-look clips 0.49–0.87
SATURATION_MAX = 1.45       # face saturation clip / storyboard above this → another colour look. #8: 0.97–1.20, no bad sample yet (not calibrated)
SPIKE = 4.0                # a frame's motion > SPIKE × its neighbours' (and clearly moving) → a jerk
CUT_CORR = 0.5             # colour-histogram correlation of two consecutive frames below this → a hard cut (#8 clips 01: 0.28, 11: 0.49)
SPIKE_CUT_CORR = 0.85      # a motion jump with correlation below this is a cut too (#8 clips 03: 0.69, 24: 0.68 — checked by eye)
FREEZE = 0.15              # motion < FREEZE × the neighbours' right before a spike → freeze-then-jump
MARK_SHARE = 0.3            # the red plus in ≥ this share of the sampled frames → the reference mark is in the clip (#10: 1.0; others 0)
LIP_RATIO_MIN = 1.15       # mouth motion while speaking / while silent below this → 'lips_still' (informational only, see doc)
LANDMARK_MODEL = os.path.join(os.path.dirname(__file__), "..", "data", "models", "face_landmarker.task")
LIP_SYNC_MIN = 0.65        # a line's best mouth ↔ voice correlation below this → 'lips_off_voice'. #10 synced turns 0.72–0.96; the voice
                           # moved off its time ≤ 0.58; #8's unsynced shots 0.04–0.18
LIP_MARGIN = 0.10          # …or less than this above the same voice moved ≥ LIP_SHIFT s (#10 synced turns: +0.15 … +0.42)
LIP_SHIFT = 0.75           # seconds — the smallest move of the voice for the "wrong time" comparison
LIP_LAG = 4                # frames of lag searched each way (≈ 0.17 s at 24 fps)
LIP_PAD = 0.15             # seconds around a line that belong to it (the mouth opens a little before the sound)
LIP_SEEN = 0.6             # a face must be measured on this share of a line's frames to count for it


def _cv():
    import cv2
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)   # OpenCV 5 warns on every YuNet load
    except Exception:  # noqa: BLE001 - an older OpenCV
        pass
    return cv2


def frames(clip: str, every: int = 1, width: Optional[int] = None) -> Tuple[List, float]:
    """(BGR frames, fps) — every n-th frame, optionally scaled to `width`."""
    cv2 = _cv()
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    out, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % every == 0:
            if width and f.shape[1] != width:
                f = cv2.resize(f, (width, int(f.shape[0] * width / f.shape[1])))
            out.append(f)
        i += 1
    cap.release()
    return out, fps


def _faces(img) -> List[Tuple[int, int, int, int, List[Tuple[float, float]]]]:
    """YuNet faces (x, y, w, h, 5 landmarks) — [] without the model file."""
    from . import text_placement
    model = text_placement.model_path()
    if not model:
        return []
    cv2 = _cv()
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(model, "", (w, h), text_placement.MIN_SCORE, 0.3, 50)
    _, found = det.detect(img)
    out = []
    for f in found if found is not None else []:
        x, y, fw, fh = (int(max(0, v)) for v in f[:4])
        out.append((x, y, fw, fh, [(float(f[4 + 2 * k]), float(f[5 + 2 * k])) for k in range(5)]))
    return sorted(out, key=lambda b: -b[2] * b[3])


def _face_stats(img) -> Optional[Dict]:
    """Texture (mean Laplacian magnitude on the face, scaled to the face size) and saturation of the biggest face."""
    cv2 = _cv()
    faces = _faces(img)
    if not faces:
        return None
    x, y, w, h, _ = faces[0]
    crop = img[y:y + h, x:x + w]
    if crop.size == 0 or w < 24:
        return None
    crop = cv2.resize(crop, (128, 128))
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    texture = float(abs(cv2.Laplacian(gray, cv2.CV_32F)).mean())
    sat = float(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[..., 1].mean())
    return {"texture": round(texture, 2), "saturation": round(sat, 1)}


def look_drift(clip: str, picture: str, samples: int = 5) -> Dict:
    """The clip's faces against the storyboard picture's face. {"texture_ratio", "saturation_ratio", "flag"} — flag None when there is
    no face to compare (said in "note")."""
    cv2 = _cv()
    ref = cv2.imread(picture)
    base = _face_stats(ref) if ref is not None else None
    if base is None:
        return {"flag": None, "note": "không thấy mặt trong ảnh storyboard"}
    fs, _ = frames(clip)
    if not fs:
        return {"flag": None, "note": "không đọc được clip"}
    picks = [fs[int(i * (len(fs) - 1) / max(1, samples - 1))] for i in range(samples)]
    stats = [s for s in (_face_stats(f) for f in picks) if s]
    if not stats:
        return {"flag": None, "note": "không thấy mặt trong clip"}
    tex = sorted(s["texture"] for s in stats)[len(stats) // 2] / max(base["texture"], 1e-6)
    sat = sorted(s["saturation"] for s in stats)[len(stats) // 2] / max(base["saturation"], 1e-6)
    flag = None
    if tex < TEXTURE_MIN:
        flag = "look_drift"
        why = f"mặt trong clip mịn hơn hẳn ảnh storyboard (độ chi tiết × {tex:.2f}) — kiểu vẽ khác (anime / búp bê)?"
    elif sat > SATURATION_MAX:
        flag = "look_drift"
        why = f"màu mặt đậm hơn hẳn ảnh storyboard (bão hòa × {sat:.2f}) — kiểu màu khác?"
    return {"texture_ratio": round(tex, 3), "saturation_ratio": round(sat, 3), "faces_seen": len(stats), "flag": flag,
            **({"why": why} if flag else {})}


def motion_series(clip: str) -> Tuple[List[float], float, List[float]]:
    """Per pair of consecutive frames: mean optical-flow magnitude (pixels at FLOW_WIDTH) and colour-histogram correlation (a hard cut
    drops it), plus fps."""
    cv2 = _cv()
    fs, fps = frames(clip, width=FLOW_WIDTH)
    flow_out, same, prev, prev_h = [], [], None, None
    for f in fs:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        if prev is not None:
            flow = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            flow_out.append(float(((flow[..., 0] ** 2 + flow[..., 1] ** 2) ** 0.5).mean()))
            same.append(float(cv2.compareHist(prev_h, hist, cv2.HISTCMP_CORREL)))
        prev, prev_h = g, hist
    return flow_out, fps, same


def jerks(clip: str, series: Optional[List[float]] = None, fps: Optional[float] = None, same: Optional[List[float]] = None) -> Dict:
    """Inside ONE shot's clip: a hard cut (frames of the neighbouring shot left in — #8 clips 01, 03, 11, 24) and a jerk (an isolated jump
    of the whole picture's motion, several times its neighbours; sustained fast motion — a run, a whip pan — is not a jerk).
    {"cuts": [s], "jerks": [s], "freezes": [s], "flag"}."""
    if series is None:
        series, fps, same = motion_series(clip)
    fps = fps or 24.0
    same = same or [1.0] * len(series)
    if len(series) < 5:
        return {"flag": None, "note": "clip quá ngắn để đo"}
    cuts, jumps, freezes = [], [], []
    for i, m in enumerate(series):
        t = round((i + 1) / fps, 2)
        if same[i] < CUT_CORR:
            cuts.append(t)
            continue
        around = [series[j] for j in range(max(0, i - 3), min(len(series), i + 4)) if j != i and same[j] >= CUT_CORR]
        local = sorted(around)[len(around) // 2] if around else 0.0
        if m > SPIKE * max(local, 0.25) and m > 1.5:
            if same[i] < SPIKE_CUT_CORR:        # a jump AND a colour change: a cut between two shots of one palette (#8 clips 03, 24)
                cuts.append(t)
                continue
            jumps.append(t)
            if i > 0 and series[i - 1] < FREEZE * max(local, 0.25):
                freezes.append(t)
    flag = "cut_inside" if cuts else ("jerk" if jumps else None)
    why = []
    if cuts:
        why.append(f"có điểm cắt cảnh bên trong clip một shot ở {cuts} s (lẫn khung của shot kề)")
    if jumps:
        why.append(f"chuyển động cả khung nhảy vọt ở {jumps} s" + (f" (đứng hình rồi nhảy ở {freezes} s)" if freezes else ""))
    return {"cuts": cuts, "jerks": jumps, "freezes": freezes, "median": round(sorted(series)[len(series) // 2], 3), "flag": flag,
            **({"why": "; ".join(why)} if why else {})}


EDGE_S = 0.8               # a cut this close to a shot clip's start / end = frames of the neighbouring shot left in


def stray_edges(clip: str) -> Tuple[float, float]:
    """(seconds to drop at the start, seconds to drop at the end) of a shot clip cut from a group clip: the frames before the last cut
    in its first EDGE_S / after the first cut in its last EDGE_S belong to the neighbouring shot (#8: 4 of 33 shot clips — 01, 03, 11
    ended with 1–2 frames of the next shot, 24 began with 0.46 s of the previous one; checked by eye)."""
    series, fps, same = motion_series(clip)
    total = (len(series) + 1) / (fps or 24.0)
    cuts = jerks(clip, series, fps, same).get("cuts") or []
    head = max([t for t in cuts if t <= EDGE_S] or [0.0])
    tail_cut = min([t for t in cuts if t >= total - EDGE_S] or [total])
    return round(head, 3), round(max(0.0, total - tail_cut), 3)


def _voice_envelope(audio: str, fps: float, n: int) -> Optional[List[float]]:
    """RMS of the voice per video frame (ffmpeg → 16 kHz mono)."""
    import subprocess
    import numpy as np
    from .ffmpeg_studio import find_ffmpeg
    try:
        raw = subprocess.run([find_ffmpeg(), "-v", "quiet", "-i", audio, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, timeout=60).stdout
    except Exception:  # noqa: BLE001 - no ffmpeg / unreadable
        return None
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if not len(x):
        return None
    hop = 16000 / fps
    return [float(np.sqrt((x[int(i * hop):int((i + 1) * hop)] ** 2).mean() or 0.0)) if int(i * hop) < len(x) else 0.0 for i in range(n)]


def lip_activity(clip: str, audio: Optional[str] = None) -> Dict:
    """Mouth-region change per frame while the voice is loud vs quiet. audio: the shot's voice (default: the clip's own track)."""
    import numpy as np
    cv2 = _cv()
    fs, fps = frames(clip)
    if len(fs) < 6:
        return {"flag": None, "note": "clip quá ngắn để đo"}
    faces = _faces(fs[len(fs) // 2])
    if not faces:
        return {"flag": None, "note": "không thấy mặt để đo miệng"}
    x, y, w, h, marks = faces[0]
    (rx, ry), (lx, ly) = marks[3], marks[4]
    cx, cy = (rx + lx) / 2, (ry + ly) / 2
    half = max(abs(lx - rx) * 0.9, w * 0.18)
    box = (int(max(0, cx - half)), int(max(0, cy - half * 0.7)), int(cx + half), int(cy + half * 0.9))
    mouth = [cv2.cvtColor(f[box[1]:box[3], box[0]:box[2]], cv2.COLOR_BGR2GRAY).astype(np.float32) for f in fs]
    change = [0.0] + [float(abs(a - b).mean()) for a, b in zip(mouth[1:], mouth[:-1])]
    env = _voice_envelope(audio or clip, fps, len(fs))
    if not env or max(env) < 0.01:
        return {"flag": None, "note": "không có tiếng để so"}
    loud = max(env) * 0.35
    speak = [c for c, e in zip(change, env) if e >= loud]
    quiet = [c for c, e in zip(change, env) if e < loud * 0.3]
    if len(speak) < 3 or len(quiet) < 3:
        return {"flag": None, "note": "không đủ đoạn nói / đoạn lặng để so", "speaking_frames": len(speak)}
    ratio = (sum(speak) / len(speak)) / max(sum(quiet) / len(quiet), 1e-3)
    flag = "lips_still" if ratio < LIP_RATIO_MIN else None
    return {"ratio": round(ratio, 3), "speaking_frames": len(speak), "flag": flag,
            **({"why": f"miệng lúc nói không động hơn lúc lặng (× {ratio:.2f}) — chưa khớp môi"} if flag else {})}


def landmark_model_path() -> Optional[str]:
    path = os.environ.get("LIP_MODEL") or LANDMARK_MODEL
    return path if os.path.exists(path) else None


_landmarker = None


def _mouth_open(crop) -> Optional[float]:
    """Inner-lip gap (landmarks 13 / 14) over face height (10 / 152) on a face crop (BGR); None when no face mesh is found."""
    global _landmarker
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    if _landmarker is None:
        _landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=landmark_model_path()), running_mode=vision.RunningMode.IMAGE, num_faces=1,
            min_face_detection_confidence=0.3))
    rgb = np.ascontiguousarray(_cv().cvtColor(crop, _cv().COLOR_BGR2RGB))
    found = _landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)).face_landmarks
    if not found:
        return None
    pts = found[0]
    gap = ((pts[13].x - pts[14].x) ** 2 + (pts[13].y - pts[14].y) ** 2) ** 0.5
    height = ((pts[10].x - pts[152].x) ** 2 + (pts[10].y - pts[152].y) ** 2) ** 0.5
    return gap / height if height > 1e-6 else None


def mouth_tracks(clip: str) -> Tuple[List[Dict], float, int]:
    """([{"x": face centre x, "open": [per frame, None when not measured]}], fps, frames): every YuNet face tracked by its nearest centre,
    cropped with a margin and scaled to 384 px for the landmarker (the small faces of a wide shot)."""
    cv2 = _cv()
    fs, fps = frames(clip)
    tracks: List[Dict] = []
    for i, f in enumerate(fs):
        H, W = f.shape[:2]
        used = set()
        for x, y, w, h, _ in _faces(f):
            if w < 20:
                continue
            c = (x + w / 2, y + h / 2)
            near = [(((c[0] - t["c"][0]) ** 2 + (c[1] - t["c"][1]) ** 2) ** 0.5, k) for k, t in enumerate(tracks) if k not in used]
            near = [(d, k) for d, k in near if d < max(w, tracks[k]["w"]) * 0.8]
            if near:
                k = min(near)[1]
            else:
                tracks.append({"c": c, "w": w, "open": [None] * i})
                k = len(tracks) - 1
            used.add(k)
            t = tracks[k]
            t["c"], t["w"] = c, w
            m = int(w * 0.6)
            x0, y0, x1, y1 = max(0, x - m), max(0, y - m), min(W, x + w + m), min(H, y + h + m)
            scale = 384 / max(1, x1 - x0)
            if len(t["open"]) == i:
                t["open"].append(_mouth_open(cv2.resize(f[y0:y1, x0:x1], None, fx=scale, fy=scale)))
        for t in tracks:
            t["open"] += [None] * (i + 1 - len(t["open"]))
    return [{"x": round(t["c"][0]), "open": t["open"]} for t in tracks], fps, len(fs)


def _lag_corr(a, b, lag: int = LIP_LAG) -> Optional[float]:
    """The best Pearson correlation of two series (NaN = not measured) over ± lag frames; None when nothing overlaps."""
    import numpy as np
    best = None
    for L in range(-lag, lag + 1):
        x, y = (a[L:], b[:len(b) - L]) if L >= 0 else (a[:L], b[-L:])
        ok = ~np.isnan(x) & ~np.isnan(y)
        if ok.sum() < 10 or np.std(x[ok]) < 1e-9 or np.std(y[ok]) < 1e-9:
            continue
        r = float(np.corrcoef(x[ok], y[ok])[0, 1])
        best = r if best is None else max(best, r)
    return best


def _line_env(env, fps: float, start: float, end: float, shift: float = 0.0):
    """The voice envelope inside one line's window (± LIP_PAD), zero elsewhere, moved by `shift` seconds."""
    import numpy as np
    t = np.arange(len(env)) / fps
    return np.roll(np.where((t >= start - LIP_PAD) & (t <= end + LIP_PAD), env, 0.0), int(round(shift * fps)))


def sync_turns(tracks: List[Dict], env: List[float], fps: float, turns: List[Dict]) -> List[Dict]:
    """Per spoken line {speaker, start, end}: the face whose mouth follows the voice best ("score", "face_x") and the best any face
    does with the same voice moved ≥ LIP_SHIFT s off its time ("wrong_time", None when the clip has no room), or "note"."""
    import numpy as np
    env = np.asarray(env, dtype=float)
    series = [np.array([np.nan if v is None else v for v in t["open"]], dtype=float) for t in tracks]
    n, dur = len(env), len(env) / fps
    out = []
    for turn in turns:
        a, b = float(turn["start"]), float(turn["end"])
        row = {"speaker": turn.get("speaker"), "start": round(a, 2), "end": round(b, 2)}
        t = np.arange(n) / fps
        win = (t >= a - LIP_PAD) & (t <= b + LIP_PAD)
        seen = [k for k, s in enumerate(series) if win.any() and (~np.isnan(s[win])).mean() >= LIP_SEEN]
        if not seen:
            out.append(dict(row, note="không thấy mặt nào đủ lâu trong câu này để đo môi"))
            continue
        scores = {k: _lag_corr(series[k], _line_env(env, fps, a, b)) for k in seen}
        scores = {k: v for k, v in scores.items() if v is not None}
        if not scores:
            out.append(dict(row, note="miệng / giọng không đổi trong câu này — không đo được"))
            continue
        best = max(scores, key=scores.get)
        wrong = []
        for s in np.arange(-dur, dur, 0.25):
            if abs(s) >= LIP_SHIFT and a + s >= 0 and b + s <= dur:
                vals = [_lag_corr(series[k], _line_env(env, fps, a, b, s)) for k in seen]
                vals = [v for v in vals if v is not None]
                if vals:
                    wrong.append(max(vals))
        out.append(dict(row, score=round(scores[best], 3), face_x=tracks[best]["x"],
                        wrong_time=round(max(wrong), 3) if wrong else None))
    return out


def voiced_span(env: List[float], fps: float) -> Optional[Tuple[float, float]]:
    """(first, last) second the voice is above 10 % of its peak — the one 'line' of a shot whose lines are not known."""
    peak = max(env) if env else 0.0
    on = [i for i, e in enumerate(env) if e > peak * 0.1]
    return (on[0] / fps, (on[-1] + 1) / fps) if peak >= 0.01 and on else None


def lip_sync(clip: str, audio: Optional[str] = None, turns: Optional[List[Dict]] = None,
             tracks: Optional[Tuple[List[Dict], float, int]] = None) -> Dict:
    """Does a mouth open while each line is heard (module doc)? audio: the shot's voice on the clip's timeline (default: the clip's own
    track); turns: [{speaker, start, end}] seconds in the clip (default: the whole voiced span as one line). {"turns", "flag", "why"}
    or {"flag": None, "note"} when it cannot measure — never a silent pass."""
    if not landmark_model_path():
        return {"flag": None, "note": "thiếu data/models/face_landmarker.task — chưa đo được mốc môi"}
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        return {"flag": None, "note": "chưa cài mediapipe (pip install mediapipe) — chưa đo được mốc môi"}
    trk, fps, n = tracks or mouth_tracks(clip)
    if n < 10:
        return {"flag": None, "note": "clip quá ngắn để đo"}
    if not trk:
        return {"flag": None, "note": "không thấy mặt để đo miệng"}
    env = _voice_envelope(audio or clip, fps, n)
    if not env or max(env) < 0.01:
        return {"flag": None, "note": "không có giọng để so (clip không có tiếng và chưa có file giọng của shot)"}
    if not turns:
        span = voiced_span(env, fps)
        turns = [{"speaker": None, "start": span[0], "end": span[1]}] if span else []
    rows = sync_turns(trk, env, fps, turns)
    bad = [r for r in rows if "score" in r and (r["score"] < LIP_SYNC_MIN or
                                                (r["wrong_time"] is not None and r["score"] - r["wrong_time"] < LIP_MARGIN))]
    out: Dict = {"turns": rows, "faces": len(trk), "flag": "lips_off_voice" if bad else None}
    faces = {}
    for r in rows:
        if "score" in r and r["score"] >= LIP_SYNC_MIN and r.get("speaker"):
            faces.setdefault(r["face_x"], set()).add(r["speaker"])
    if any(len(v) > 1 for v in faces.values()):
        out["note"] = "hai người nói khác nhau nhưng cùng một khuôn mặt mấp máy — xem lại ai nói"
    if bad:
        out["why"] = "miệng không theo giọng ở " + "; ".join(
            f"{r.get('speaker') or 'câu thoại'} {r['start']}–{r['end']} s (tương quan {r['score']:.2f}"
            + (f", giọng dời giờ {r['wrong_time']:.2f}" if r["wrong_time"] is not None else "") + ")" for r in bad)
    return out


def _plus_signs(img) -> List[Tuple[int, int, int, int]]:
    """Saturated red plus signs (x, y, w, h): a near-square red blob with a full-length horizontal and vertical bar through its middle,
    thin arms and empty corners — the shape seedance_refs.mark draws (pure (220, 0, 0), stroke ≈ size / 4)."""
    cv2 = _cv()
    import numpy as np
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    red = (((hsv[..., 0] <= 6) | (hsv[..., 0] >= 174)) & (hsv[..., 1] >= 190) & (hsv[..., 2] >= 150)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(red, 8)
    width = red.shape[1]
    out = []
    for i in range(1, n):
        x, y, w, h, _ = (int(v) for v in st[i])
        if w < width * 0.02 or h < width * 0.02 or not 0.8 <= w / h <= 1.25:
            continue
        box = lab[y:y + h, x:x + w] == i
        cy, cx, q = h // 2, w // 2, max(1, min(w, h) // 4)
        row = box[max(cy - 2, 0):cy + 3].any(axis=0).mean()
        col = box[:, max(cx - 2, 0):cx + 3].any(axis=1).mean()
        corners = float(np.mean([box[:q, :q].mean(), box[:q, -q:].mean(), box[-q:, :q].mean(), box[-q:, -q:].mean()]))
        arm = box[:, q].mean()                   # a quarter across: only the horizontal bar's thickness is red
        if 0.15 <= box.mean() <= 0.6 and row >= 0.7 and col >= 0.7 and corners <= 0.1 and arm <= 0.45:
            out.append((x, y, w, h))
    return out


def ref_mark(clip: str, every: int = 6) -> Dict:
    """The reference picture's red plus sign drawn into the clip (see module doc)."""
    pics, _ = frames(clip, every=every)
    hits = [i * every for i, f in enumerate(pics) if _plus_signs(f)]
    share = len(hits) / len(pics) if pics else 0.0
    out = {"frames": len(pics), "hits": len(hits), "share": round(share, 2), "first_hit_frame": hits[0] if hits else None}
    if pics and share >= MARK_SHARE:
        out["flag"] = (f"dấu chữ thập đỏ của ảnh tham chiếu hiện trong clip ({len(hits)}/{len(pics)} khung lấy mẫu) — gen lại với "
                       "ảnh tham chiếu không có dấu trên mặt hoặc model khác")
    return out


def measure(clip: str, picture: Optional[str] = None, audio: Optional[str] = None, speaking: bool = False,
            turns: Optional[List[Dict]] = None) -> Dict:
    """All the checks that apply; {"flags": [...], each check's numbers}. turns: the shot's lines [{speaker, start, end}] on the clip."""
    out: Dict = {}
    if picture and os.path.exists(picture):
        out["look"] = look_drift(clip, picture)
    out["motion"] = jerks(clip)
    out["ref_mark"] = ref_mark(clip)
    if speaking:
        lips = lip_sync(clip, audio, turns)
        if "turns" not in lips:              # no landmark model / no face / no voice: say why, keep the old numbers (not a check)
            old = lip_activity(clip, audio)
            lips = dict(lips, pixel_ratio=old.get("ratio"))
        out["lips"] = lips
    out["flags"] = [v["flag"] for v in out.values() if isinstance(v, dict) and v.get("flag")]
    return out
