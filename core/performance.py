"""Acting of an AI character (kế hoạch V4 GĐ4, knowledge/roles/director.md Đ4): the Director writes a `performance` for each shot with
people in it — how strong the feeling is (1–5), what the face, the eyes and the body do, the timing, how the listener reacts and why —
and the DP carries it into the first-frame prompt (this module) and the motion prompt (the Motion writer reads the field).

Why a field and not words inside image_prompt: real runs show the video model picking an expression on its own when nobody names one
(#6 job 166: QC "he looks angry with a wide-open mouth — keep the cocky smirk"), and a vague emotion word ("sad") gives a generic
face. A visible behaviour at a stated strength is what the models follow.

The Director's answer is never refused for this field (a refused answer is a paid re-ask): bad parts are dropped and reported.
"""
from typing import Dict, List, Optional, Tuple

TEXT_FIELDS = ("face", "eyes", "body", "timing", "listener", "motive")
# words for the picture / video model — a scale the model can act on (1 = almost nothing shows, 5 = the peak of the film)
INTENSITY_WORDS = {1: "barely visible micro-expression", 2: "subtle, restrained", 3: "clear but natural",
                   4: "strong, visibly emotional", 5: "peak emotion, full intensity"}
CLOSE = ("ECU", "CU")                 # the face fills the frame: every change reads bigger — the prompt shows one step less (Đ4)
PEAKS_PER_FILM = 2                    # intensity 5 more often than this flattens the climax
FLAT_RUN = 6                          # this many acted shots in a row at one strength: a flat curve
STRONG, HOLD_S = 4, 2.0               # a strong moment needs a shot this long in it or right after it (director.md Đ2)
# a face written as one emotion word gives the model nothing to act (describe what the face DOES)
_BARE_EMOTIONS = {"sad", "happy", "angry", "scared", "afraid", "surprised", "shocked", "worried", "nervous", "calm", "neutral",
                  "serious", "emotional", "upset", "crying", "smiling", "buồn", "vui", "giận", "sợ", "bất ngờ", "lo lắng", "bình tĩnh"}


def clean(value) -> Tuple[Optional[Dict], List[str]]:
    """(the usable performance or None, what was dropped and why)."""
    if value is None:
        return None, []
    if not isinstance(value, dict):
        return None, ["performance phải là object {intensity, face, eyes, body, timing, listener, motive} — bỏ"]
    out, problems = {}, []
    raw = value.get("intensity")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not 1 <= raw <= 5:
        if raw is not None:
            problems.append(f"performance.intensity '{raw}' không phải số 1–5 — bỏ")
    else:
        out["intensity"] = int(round(raw))
    for key in TEXT_FIELDS:
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            out[key] = text.strip()
        elif text is not None and not isinstance(text, str):
            problems.append(f"performance.{key} phải là chữ — bỏ")
    return (out or None), problems


def shown_intensity(data: Dict) -> Optional[int]:
    """How big the acting is drawn: the Director's `intensity` is the strength of the moment in the story (the curve of the film, 5 = the
    peak); a close-up shows it one step smaller, because the face fills the frame and every change reads bigger (grader GĐ4: one number
    for both meanings bent the curve)."""
    p = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    level = p.get("intensity")
    if level not in INTENSITY_WORDS:
        return None
    return max(level - 1, 1) if data.get("size") in CLOSE else level


def for_prompt(data: Dict) -> Optional[Dict]:
    """The performance as the motion writer and the QC see it: the Director's fields + `shown_intensity` (the strength to draw — one
    step smaller in a close-up), so the picture, the clip and their checks all use the same strength."""
    p = data.get("performance") if isinstance(data.get("performance"), dict) else None
    if not p:
        return None
    shown = shown_intensity(data)
    return dict(p, shown_intensity=shown) if shown is not None else dict(p)


def image_sentence(data: Dict) -> str:
    """The start frame shows ONE moment: the face, eyes and body at the start of the shot, at the stated strength. Timing and the
    motive belong to the motion prompt (they happen over time); the listener goes in only when that person is in the frame."""
    p = data.get("performance") if isinstance(data.get("performance"), dict) else None
    if not p:
        return ""
    bits = [f"{k}: {p[k]}" for k in ("face", "eyes", "body") if p.get(k)]
    if p.get("listener") and len(data.get("characters") or []) > 1:
        bits.append(f"listener: {p['listener']}")
    if not bits:
        return ""
    level = shown_intensity(data)
    head = f"Acting ({INTENSITY_WORDS[level]}, intensity {level}/5)" if level in INTENSITY_WORDS else "Acting"
    return f" {head} — " + "; ".join(bits) + "."


def warnings(shots: List[Dict]) -> List[str]:
    """Over-acting / dead acting the code can see in a plan (the shots of the whole film, in order). Soft: they go to the Director
    report and the storyboard, they never refuse the answer."""
    out: List[str] = []
    acted = [(k, s) for k, s in enumerate(shots, 1) if isinstance(s.get("performance"), dict)]
    if not acted:
        return out
    peaks = [k for k, s in acted if s["performance"].get("intensity") == 5]
    if len(peaks) > PEAKS_PER_FILM:
        out.append(f"cường độ 5 ở {len(peaks)} shot ({', '.join(map(str, peaks))}) — đỉnh cảm xúc chỉ nên 1–{PEAKS_PER_FILM} lần, "
                   "còn lại hạ xuống để đỉnh còn là đỉnh")
    for k, s in acted:
        p = s["performance"]
        face = str(p.get("face") or "").strip().lower().rstrip(".")
        words = face.replace(",", " ").split()
        if face and len(words) <= 3 and (face in _BARE_EMOTIONS or any(w in _BARE_EMOTIONS for w in words)):
            out.append(f"shot {k}: face \"{p['face']}\" chỉ là tên cảm xúc — tả việc khuôn mặt làm (mắt, miệng, hàm, lông mày)")
    run, start = 1, 0
    levels = [(k, s["performance"].get("intensity")) for k, s in acted]
    for i in range(1, len(levels) + 1):
        if i < len(levels) and levels[i][1] and levels[i][1] == levels[i - 1][1]:
            run += 1
            continue
        if run >= FLAT_RUN:
            out.append(f"shot {levels[start][0]}–{levels[i - 1][0]}: {run} shot liền cùng cường độ {levels[i - 1][1]} — đường cảm xúc "
                       "phẳng (cần lên xuống theo nhịp)")
        run, start = 1, i
    # director.md Đ2 "giữ cho người xem thấm" (Handbook ch. III anchor shot; lần chạy 4: a 0,5 s silent shot cut away too fast): a run
    # of strong moments (intensity ≥ 4) needs one shot of HOLD_S or more in it or right after it
    def level(s: Dict) -> int:
        p = s.get("performance")
        value = p.get("intensity") if isinstance(p, dict) else None
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

    k = 0
    while k < len(shots):
        if level(shots[k]) < STRONG:
            k += 1
            continue
        end = k
        while end + 1 < len(shots) and level(shots[end + 1]) >= STRONG:
            end += 1
        span = shots[k:end + 2]                    # the strong run + the shot after it
        if not any(float(s.get("duration_s") or 0) >= HOLD_S for s in span):
            where = f"shot {k + 1}" if end == k else f"shot {k + 1}–{end + 1}"
            out.append(f"{where}: khoảnh khắc cường độ ≥ {STRONG} mà không shot nào (kể cả shot ngay sau) dài ≥ {HOLD_S:g} s — người xem "
                       "chưa kịp thấm; giữ một shot mặt/phản ứng 2–4 s ngay tại hoặc sau khoảnh khắc (trừ khi cố ý dồn nhịp, ghi `why`)")
        k = end + 1
    people = [k for k, s in enumerate(shots, 1) if s.get("characters") and s.get("role") in ("dialogue", "reaction", "hook", "ending")
              and not isinstance(s.get("performance"), dict)]
    if people:
        out.append(f"shot có người mà thiếu performance: {', '.join(map(str, people[:12]))}" + ("…" if len(people) > 12 else "")
                   + " — model sẽ tự chọn biểu cảm (dễ diễn đơ / sai cảm xúc)")
    return out
