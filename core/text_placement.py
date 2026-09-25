"""Editor: subtitles never sit on a face (knowledge/editor/safe_zones.md rule 2-3, kế hoạch V4 5.1). The subtitle stays in ONE place
for the whole video (bottom band of the common safe box) and a whole line moves to the top band only when its shot puts eyes or mouth
in the bottom band — mostly close-ups on a vertical frame, where the bottom band of the safe box (about 55-64 % of the height) is
exactly the mouth and chin.

Where the face is comes from the DP's shot table (shot size + start_frame position words) — no detector is installed (OpenCV 5 ships no
face model; a YuNet file would have to be downloaded, ask the person first). A composited shot (gói bối cảnh) knows its character box
exactly and can pass it as `zones` directly.

Numbers are fractions of the frame height for a 9:16 frame, eyes-to-mouth span of the main face; measured on the 2A frames by eye,
to be refined on real frames.
"""
import json
from typing import Dict, List, Optional, Tuple

# eyes-to-mouth span (top, bottom) of the main face by shot size, 9:16 frame
KEEP_CLEAR = {"ECU": (0.20, 0.80), "CU": (0.30, 0.66), "MCU": (0.22, 0.46), "MS": (0.15, 0.32), "MLS": (0.14, 0.26)}
_RAISED = ("low angle", "from below", "góc thấp")
_LOWERED = ("high angle", "from above", "góc cao")


def keep_clear(data: Dict) -> Optional[Tuple[float, float]]:
    """(top, bottom) of the part of the frame a subtitle must not cover for this shot, or None (wide shot: faces are small)."""
    size = str(data.get("size") or data.get("shot_size") or "").upper()
    span = KEEP_CLEAR.get(size)
    if span is None:
        return None
    words = f"{data.get('start_frame') or ''} {data.get('angle') or ''}".lower()
    shift = 0.0
    if any(w in words for w in _RAISED) or str(data.get("angle") or "").lower() == "low":
        shift = 0.05                      # camera below the face: the face sits lower in the frame
    elif any(w in words for w in _LOWERED) or str(data.get("angle") or "").lower() == "high":
        shift = -0.04
    if "foreground" in words or "tiền cảnh" in words:
        shift += 0.03
    return (max(0.0, span[0] + shift), min(1.0, span[1] + shift))


def zones(conn, project_id: int) -> Dict[int, Tuple[float, float]]:
    """Scene idx -> keep-clear span for every shot of the project that has one."""
    out = {}
    for r in conn.execute("SELECT idx, data FROM scenes WHERE project_id=?", (project_id,)):
        span = keep_clear(json.loads(r["data"] or "{}"))
        if span is not None:
            out[r["idx"]] = span
    return out


def _overlap(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def bands(height: int, fontsize: int, lines: int, bottom_margin: float, top_margin: float) -> Dict[str, Tuple[float, float]]:
    """Where a subtitle of `lines` lines sits (fractions of the height) in the bottom and the top position."""
    h = lines * fontsize * 1.25 / height
    bottom = (1.0 - bottom_margin - h, 1.0 - bottom_margin)
    top = (top_margin, top_margin + h)
    return {"bottom": bottom, "top": top}


def placements(cues: List, zone_of: Dict[int, Tuple[float, float]], height: int, fontsize: int, lines_of, bottom_margin: float,
               top_margin: float) -> Dict[int, str]:
    """Cue index -> "top" for the lines that would cover a face at the bottom and are clear (or clearer) at the top."""
    out = {}
    for i, c in enumerate(cues):
        span = zone_of.get(getattr(c, "scene", None))
        if span is None:
            continue
        b = bands(height, fontsize, lines_of(c), bottom_margin, top_margin)
        low, high = _overlap(b["bottom"], span), _overlap(b["top"], span)
        if low > 0 and high < low:
            out[i] = "top"
    return out
