"""Hướng nền (plate_view) và hướng nhân vật sau Director — kiểm bằng code, không gọi model (người dùng 08/10, dự án #24).

Bài học #24 (Tháp Đồng Hồ, chỗ đứng plaza_front): Director + Quay phim không ghi `plate_view` cho shot nào → core/plate_choice.view_of
rơi về `facing` mặc định của chỗ đứng → cả 9 nền 3D cùng nhìn về tháp; ảnh tham chiếu địa điểm kéo tháp vào cả shot ngược (shot 4 nhìn
mặt Kelly từ phía giếng mà sau lưng vẫn là tháp); hai góc ngang nằm hai bên trục nhân vật–vật mốc (vượt 180°); "Kelly ngã ra sau" mà ảnh
Kelly quay lưng về giếng (blocking chỉ ghi "seated watching in fear", không ghi mặt hướng về đâu).

    warnings(shots) -> [câu tiếng Việt]       shots = [(cảnh, số shot, dict shot)] theo thứ tự phim

Chỉ CẢNH BÁO (báo cáo Director + diag), không sửa câu trả lời: người duyệt quyết. Shot "ở nơi có mô hình 3D" = shot có `plate_spot`.
"""
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

REPEAT_SHARE = 0.8            # ≥ 80 % shot 3D cùng một hướng nền → hậu cảnh lặp
REPEAT_MIN = 3
SIDES = ("left", "right")
_CROSS_OK = re.compile(r"vượt trục|cố ý|cross(?:es|ing)? the (?:line|axis)|180", re.I)
# a reverse / face-on angle: the camera looks at the character's face from where they are looking — the landmark they face is BEHIND
# the camera, so a "landmark" background contradicts it (#24 shot 4). The script's own words ("ngược", "đối diện") count too.
_REVERSE = re.compile(r"\breverse\b|góc ngược|ngược lại|đối diện|facing (?:the )?camera|face[- ]on|nhìn thẳng (?:vào )?(?:mặt|máy)", re.I)
_OTS = re.compile(r"\bots\b|over[- ]the[- ]shoulder|qua vai|sau vai", re.I)
# a reflex move (falls back, steps back, recoils) is read against what scares the character: the blocking must say where they face
_REFLEX = re.compile(r"ngã (?:ra )?(?:sau|ngửa)|ngã bệt|lùi lại|lùi về|giật lùi|fall(?:s|ing)? back(?:ward)?|stumbl\w* back|recoil|"
                     r"step(?:s|ping)? back|backs? away|scrambl\w* back", re.I)
_FACING = re.compile(r"\bfacing\b|\btoward|\baway from\b|\bback to\b|\bback toward|\blooking (?:at|toward|into)\b|eyes (?:locked|fixed) on|"
                     r"hướng về|mặt hướng|quay lưng|quay mặt|nhìn về phía|chân về phía|legs? (?:stretched )?toward", re.I)


def _view(s: Dict) -> Optional[str]:
    v = s.get("plate_view")
    if isinstance(v, dict):
        bg = str(v.get("background") or "").strip().lower()
        return bg or None
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    return None


def _why(s: Dict) -> str:
    v = s.get("plate_view")
    return str(v.get("why") or "") if isinstance(v, dict) else ""


def _text(s: Dict, *keys) -> str:
    return " ".join(str(s.get(k) or "") for k in keys)


def warnings(shots: List[Tuple[int, int, Dict]]) -> List[str]:
    out: List[str] = []
    at3d = [(sc, k, s) for sc, k, s in shots if isinstance(s, dict) and s.get("plate_spot")]
    missing = [f"{sc}·{k}" for sc, k, s in at3d if _view(s) is None]
    if missing:
        out.append(f"shot {', '.join(missing[:8])}{'…' if len(missing) > 8 else ''} ở nơi có mô hình 3D thiếu `plate_view` — nền dùng "
                   "hướng mặc định của chỗ đứng (mọi shot cùng một hậu cảnh); ghi hướng nền theo sơ đồ cảnh")
    if len(at3d) >= REPEAT_MIN:
        views = Counter(_view(s) or "mặc định" for _, _, s in at3d)
        top, n = views.most_common(1)[0]
        if n / len(at3d) >= REPEAT_SHARE:
            out.append(f"hậu cảnh lặp: {n}/{len(at3d)} shot 3D cùng hướng nền '{top}' — xen hướng (landmark / away / một bên trục) để "
                       "nền đổi theo góc máy")
    by_scene: Dict[int, List[Tuple[int, Dict]]] = {}
    for sc, k, s in at3d:
        by_scene.setdefault(sc, []).append((k, s))
    for sc, rows in by_scene.items():
        side = {v: [k for k, s in rows if _view(s) == v] for v in SIDES}
        if side["left"] and side["right"] and not any(_CROSS_OK.search(_why(s)) for k, s in rows if _view(s) in SIDES):
            out.append(f"cảnh {sc}: góc ngang ở CẢ hai bên trục (left: shot {', '.join(map(str, side['left']))}; right: shot "
                       f"{', '.join(map(str, side['right']))}) mà không ghi lý do — vượt trục 180°? chọn một bên cho mọi góc ngang")
    for sc, k, s in at3d:
        words = _text(s, "angle", "blocking", "start_frame", "why")
        if _view(s) == "landmark" and _REVERSE.search(words) and not _OTS.search(_text(s, "angle", "blocking")):
            out.append(f"shot {sc}·{k}: góc ngược / nhìn thẳng mặt nhân vật mà hướng nền 'landmark' — mốc nằm sau lưng MÁY, nền phải là "
                       "'away' (hoặc một bên trục)")
    for sc, k, s in shots:
        if not isinstance(s, dict):
            continue
        if _REFLEX.search(_text(s, "action", "start_frame", "end_state", "blocking")) and not _FACING.search(_text(s, "blocking", "start_frame")):
            out.append(f"shot {sc}·{k}: động tác phản xạ (ngã ra sau / lùi) mà blocking không ghi mặt hướng về đâu — ngã vì sợ thứ trước "
                       "mặt thì ngồi MẶT HƯỚNG vật đó, chân về phía nó; ghi 'facing …/toward …'")
    return out
