"""Bất biến khâu 3D theo GỐC (C-3D-GOC-A, người dùng 22/10: "sửa GỐC để đặt chỗ khác / cách khác không lặp lại") — R2 / R3 / R4.

Mỗi gốc = MỘT bộ kiểm chạy cho MỌI shot (không vá từng shot); sổ lỗi devsys/errors.json mục V31-GOC2/3/4. Thuần Python, 0 USD, không gọi
model, không sửa dữ liệu, không đổi gói gửi: kết quả là phát hiện VÀNG có số đo + câu thay (diag / báo cáo `tools/camera_invariants.py`).

R2 — hình học máy ↔ người ↔ sàn ĐO từ hình chiếu, không hằng số / chữ (G2, G3, G49, P33-A10, P33-B5):
  check_pitch      góc nghiêng máy ∈ dải của góc khai (PITCH_BANDS — một nguồn, lấy ngưỡng có sẵn của stage_grid.RULE_TH L7 + whitebox)
  check_framing    người chiếm % khung theo hình chiếu ↔ cỡ cảnh (FRAMING, ±L3_rel): máy quá sát / quá xa cho cỡ + ống kính
  check_floor      sàn dưới máy + dưới chân + bậc giữa máy và chân (floor_at = tia xuống sàn; Blender thật hoặc giả trong test)
  check_frame_pct  câu "N% of the frame height" trong chữ ↔ hình chiếu; câu thay SINH từ hình chiếu (pct_sentence)
R3 — chữ ↔ cái máy thấy (G26, G11, G9, P33-B3, P33-B7, P33-B10):
  view_of          mốc / vật (đáy, giữa, đỉnh) trong khung? bên nào (một phần ba)? đỉnh bị cắt?
  text_vs_view     chữ nhắc mốc ngoài khung / sai bên / đỉnh ngoài khung / đặt vật bằng chữ so với mốc → VÀNG + câu thay
  motion_vs_view   motion "lộ ra / hiện ra" một thứ khung đầu ĐÃ thấy; motion nhắc thứ khung đầu không thấy mà máy đứng yên
  vi_leaks         chữ có dấu tiếng Việt trong prompt tiếng Anh → câu thay không dấu / tên tiếng Anh (glossary)
  ref_leaks        từ chỉ chủ thể video mẫu (vd "cats") nằm ngoài câu chặn → câu thay "like the reference video"
R4 — BYĐ ↔ trường shot một chỗ (G18, P33-A12):
  byd_vs_fields    may.co ↔ size, may.do_cao / goc ↔ angle, may.chuyen_dong ↔ camera_move, thanh_phan ↔ characters
  byd_coverage     thiếu BYĐ: MỘT câu cho cả dự án (không 22 dòng VÀNG lặp), nói rõ kiểm nào bị bỏ

Phát hiện = {"code", "level": "vang", "errors": [mã sổ lỗi], "msg" (tiếng Việt, có số), "fix" (câu thay / việc sửa), "numbers"}.
Thiếu đầu vào → phát hiện "khong_ro" có lý do (luật 1 CHUAN_XAY_DUNG: không im lặng), không đoán.
"""
import math
import re
import unicodedata
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import plate_camera as pc
from . import stage_grid as sg
from . import whitebox as wb

VANG, KHONG_RO = "vang", "khong_ro"
ASPECT = 9 / 16


def _f(code: str, errors: Sequence[str], msg: str, fix: str = "", level: str = VANG, **numbers) -> Dict:
    return {"code": code, "level": level, "errors": list(errors), "msg": msg, "fix": fix,
            "numbers": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in numbers.items()}}


def _th(key: str) -> float:
    return float(sg.RULE_TH[key][0])


# ==== R2: hình học máy ↔ người ↔ sàn ==============================================================================================
# Dải nghiêng theo góc khai (độ, âm = cúi). MỘT nguồn: ngưỡng lớp máy của Sân khấu 3D (stage_grid.RULE_TH L7) + mức "hơi cao" của
# whitebox M3.2. 'eye' ngửa tối đa whitebox.EYE_MAX_DEG (G3: #31 shot 28 khai eye mà ngửa +17,3°, shot 35 +11,1°), cúi tối đa L7_ngang
# (camera_for nhìn vào giữa khung: MS cúi ~10°). Không có dải (None): ots / pov / góc lạ — nói rõ, không đoán.
def pitch_band(angle: Optional[str]) -> Optional[Tuple[float, float, str]]:
    a = str(angle or "eye").strip().lower()
    lo_sh, hi_sh = wb.SLIGHTLY_HIGH_RANGE
    bands = {
        "eye": (-_th("L7_ngang"), wb.EYE_MAX_DEG, f"ngang mắt: cúi ≤ {_th('L7_ngang'):g}° (stage_grid L7), ngửa ≤ {wb.EYE_MAX_DEG:g}° (whitebox)"),
        "slightly_high": (-hi_sh, -lo_sh, f"hơi cao: cúi {lo_sh:g}–{hi_sh:g}° (whitebox M3.2)"),
        "high": (_th("L7_tren_dau"), _th("L7_cui"), f"cao: cúi {-_th('L7_cui'):g}–{-_th('L7_tren_dau'):g}° (stage_grid L7)"),
        "overhead": (-90.0, _th("L7_tren_dau"), f"trên đầu: cúi ≥ {-_th('L7_tren_dau'):g}° (stage_grid L7)"),
        "low": (_th("L7_ngua"), pc.MAX_LOW_TILT_DEG + 15.0,
                f"thấp: ngửa {_th('L7_ngua'):g}–{pc.MAX_LOW_TILT_DEG + 15:g}° (stage_grid L7; quá {pc.MAX_LOW_TILT_DEG + 15:g}° chỉ còn trời)"),
    }
    return bands.get(a)


# BYĐ.may.do_cao / goc ↔ angle của shot (một bảng, dùng cả R2 lẫn R4)
DO_CAO_OF_ANGLE = {"eye": "ngang", "slightly_high": "cao", "high": "cao", "overhead": "tren_dau", "low": "thap"}
GOC_OF_ANGLE = {"eye": "ngang", "slightly_high": "cui", "high": "cui", "overhead": "cui", "low": "ngua"}


def pitch_of(cam: Sequence[float], aim: Sequence[float]) -> float:
    return sg.look(cam, aim)[1]


PITCH_TOL = 0.5             # độ — máy ghi tọa độ làm tròn mm: low 8° đo lại ra 7,99°


def check_pitch(angle: Optional[str], pitch_deg: Optional[float], declared: bool = True) -> List[Dict]:
    """Máy nghiêng ngoài dải của góc khai → VÀNG kèm độ nghiêng nên có (giữa dải). declared=False: shot không ghi angle (mặc định eye)."""
    if pitch_deg is None:
        return [_f("R2-PITCH", ("P31-G3",), "không đo được độ nghiêng máy (thiếu location / look_at)", level=KHONG_RO)]
    band = pitch_band(angle)
    a = str(angle or "eye").lower()
    if band is None:
        return []                                     # ots / pov: máy theo hướng nhìn của nhân vật, không có dải chung
    lo, hi, why = band
    if lo - PITCH_TOL <= pitch_deg <= hi + PITCH_TOL:
        return []
    want = max(lo, min(hi, (lo + hi) / 2 if a != "eye" else 0.0))
    errs = ["P31-G3"] + (["P33-A10"] if a in ("high", "slightly_high") else []) + (["P33-B5"] if a == "low" else [])
    return [_f("R2-PITCH", errs,
               f"shot khai angle '{a}'{'' if declared else ' (mặc định — shot thiếu angle)'} nhưng máy "
               f"{'ngửa' if pitch_deg > 0 else 'cúi'} {abs(pitch_deg):.1f}° — ngoài dải {why}",
               f"giải lại máy để nghiêng ≈ {want:+.0f}° (giữ khoảng cách, đổi độ cao máy), hoặc đổi angle khai cho khớp máy",
               pitch_deg=float(pitch_deg), lo=lo, hi=hi)]


def body_share(cam, aim, lens: float, aspect: float, spot: Sequence[float], height_m: float, share: float = 1.0) -> Optional[float]:
    """Phần chiều cao khung mà đoạn thân từ đỉnh đầu xuống `share` × chiều cao chiếm theo hình chiếu (không cắt theo mép khung).
    share = 1: toàn thân. None khi điểm đầu / điểm cắt sau lưng máy."""
    top = sg.project(cam, aim, (spot[0], spot[1], spot[2] + height_m), lens, aspect)
    cut = sg.project(cam, aim, (spot[0], spot[1], spot[2] + height_m * (1 - share)), lens, aspect)
    if top is None or cut is None:
        return None
    return cut[1] - top[1]


STEEP_DEG = 15.0            # không biết góc khai: máy nghiêng hơn → sai % khung chủ yếu do phối cảnh, sửa độ nghiêng trước
FRAMING_MAX_TILT_DEG = 35.0  # máy cúi / ngửa gắt hơn: chiều cao thân co theo phối cảnh, "% khung" của cỡ cảnh không còn là thước đo


def check_framing(size: Optional[str], cam, aim, lens: float, spot, height_m: float, aspect: float = ASPECT,
                  angle: Optional[str] = None) -> List[Dict]:
    """Đoạn thân của cỡ cảnh theo hình chiếu ↔ FRAMING: cỡ S cho body_share × chiều cao (từ đỉnh đầu) chiếm fill của khung (±L3_rel).
    Máy quá sát (G49: #31 shot 13 cách Kelly 0,9 m) hay quá xa cho cỡ + ống kính → VÀNG với khoảng cách / ống nên có.
    Máy nghiêng ngoài dải của `angle` (không khai angle: > STEEP_DEG) → câu sửa nói sửa độ nghiêng trước (lệch do phối cảnh).
    Không áp: GAME_TPS (giàn máy game định khoảng cách), máy nghiêng > FRAMING_MAX_TILT_DEG (overhead — thân co theo phối cảnh)."""
    s = str(size or "").upper()
    if s not in pc.FRAMING:
        return [_f("R2-FRAMING", ("P31-G2",), f"cỡ cảnh '{size}' không thuộc {'/'.join(pc.FRAMING)} — không kiểm được tỉ lệ người",
                   level=KHONG_RO)]
    if s == "GAME_TPS" or abs(pitch_of(cam, aim)) > FRAMING_MAX_TILT_DEG:
        return []
    body, fill, _ = pc.FRAMING[s]
    got = body_share(cam, aim, lens, aspect, spot, height_m, body)
    if got is None:
        return [_f("R2-FRAMING", ("P31-G2",), "nhân vật sau lưng máy — không đo được tỉ lệ người", level=KHONG_RO)]
    rel = got / fill - 1
    if abs(rel) <= _th("L3_rel") + 1e-9:
        return []
    dist = math.dist(cam, (spot[0], spot[1], spot[2] + height_m * (1 - body / 2)))
    tilt = pitch_of(cam, aim)
    steep = bool(check_pitch(angle, tilt)) if angle else abs(tilt) > STEEP_DEG
    need = dist * got / fill
    why = (f"máy nghiêng {tilt:+.0f}° ở {dist:.2f} m: thân co theo phối cảnh" if steep
           else f"máy {'quá sát' if rel > 0 else 'quá xa'} ({dist:.2f} m, ống {lens:g} mm)")
    fix = ("giải lại máy theo góc khai (độ nghiêng trước), rồi khoảng cách theo cỡ cảnh" if steep
           else f"đặt máy cách ≈ {need:.2f} m (cùng ống kính) hoặc đổi ống ≈ {lens * fill / got:.0f} mm (cùng chỗ)")
    return [_f("R2-FRAMING", ("P31-G2", "P31-G49"),
               f"cỡ {s}: {body * 100:.0f}% thân trên theo hình chiếu cao {got * 100:.0f}% khung, cỡ này cần ≈ {fill * 100:.0f}% "
               f"(±{_th('L3_rel') * 100:g}%) — {why}", fix, share=got, want=fill, distance_m=dist, need_m=need, pitch_deg=tilt)]


STEP_SEEN_M = 0.05          # mép sàn cao hơn sàn dưới chân ≥ 5 cm, lọt khung giữa máy và chân → model vẽ thành bậc che chân (G49)
CAM_MIN_ABOVE_FLOOR_M = pc.WIDE_MIN_CAM_M


def check_floor(cam, aim, lens: float, spot, height_m: float, floor_at: Callable[[float, float], Optional[float]],
                aspect: float = ASPECT, samples: int = 24) -> List[Dict]:
    """Tia xuống sàn (floor_at(x, y) → cao độ sàn, None = không có sàn / ngoài mô hình):
    - máy cách sàn dưới nó < CAM_MIN_ABOVE_FLOOR_M (hoặc dưới sàn) / không có sàn dưới máy;
    - chân không nằm trên sàn dưới chỗ đứng (lệch > stage_grid.SAME_FLOOR_M: lơ lửng / chìm);
    - giữa máy và chân có mép sàn cao hơn sàn dưới chân ≥ STEP_SEEN_M lọt khung (G49 #31 shot 13: ô cỏ 0,13 m)."""
    out = []
    zc = floor_at(cam[0], cam[1])
    if zc is None:
        out.append(_f("R2-FLOOR", ("P31-G49",), "không có sàn dưới máy (máy ngoài mô hình / trên khoảng trống)", level=KHONG_RO))
    elif cam[2] - zc < CAM_MIN_ABOVE_FLOOR_M:
        out.append(_f("R2-FLOOR", ("P31-G49",), f"máy cách sàn dưới nó {cam[2] - zc:.2f} m (< {CAM_MIN_ABOVE_FLOOR_M:g} m) — sàn choán khung / máy trong sàn",
                      f"nâng máy ≥ {zc + CAM_MIN_ABOVE_FLOOR_M:.2f} m", cam_above_floor_m=cam[2] - zc))
    zf = floor_at(spot[0], spot[1])
    if zf is None:
        out.append(_f("R2-FLOOR", ("P31-G49",), "không có sàn dưới chỗ đứng của nhân vật", level=KHONG_RO))
        return out
    if sg.floor_status(spot[2] - zf) != "same":
        out.append(_f("R2-FLOOR", ("P31-G49",), f"chân nhân vật ở {spot[2]:.2f} m nhưng sàn dưới chỗ đứng ở {zf:.2f} m (lệch {spot[2] - zf:+.2f} m) "
                      "— người lơ lửng / chìm trong nền", f"đặt chân xuống sàn đo được z = {zf:.2f}", feet_dz=spot[2] - zf))
    worst = None
    for k in range(1, samples):
        t = k / samples
        x, y = cam[0] + (spot[0] - cam[0]) * t, cam[1] + (spot[1] - cam[1]) * t
        z = floor_at(x, y)
        if z is None or z - zf < STEP_SEEN_M:
            continue
        uv = sg.project(cam, aim, (x, y, z), lens, aspect)
        if not sg.in_frame(uv):
            continue
        gap = math.hypot(spot[0] - x, spot[1] - y)
        if worst is None or z - zf > worst[0]:
            worst = (z - zf, gap)
    if worst:
        out.append(_f("R2-FLOOR", ("P31-G49",),
                      f"giữa máy và chân có mép sàn cao hơn chỗ đứng {worst[0]:.2f} m, cách chân {worst[1]:.2f} m, lọt khung — model vẽ thành "
                      "bậc / gờ che chân",
                      "dời máy sang phía sàn phẳng (cùng cao độ chỗ đứng), hoặc ghi rõ trong chữ độ cao mép đó (vd 'a 13 cm grass edge')",
                      step_m=worst[0], from_feet_m=worst[1]))
    return out


_PCT = re.compile(r"(\d{1,3})\s*%\s*of\s+(?:the\s+)?frame(?:'s)?\s+height", re.I)
PCT_TOL = 10.0              # điểm % — sai số chấp nhận giữa câu chữ và hình chiếu


def pct_sentence(share: float) -> str:
    """Câu tỉ lệ người SINH từ hình chiếu (cùng dạng câu place_refs đang viết)."""
    return f"the main character's whole body is about {min(share, 1.0) * 100:.0f}% of the frame height"


def check_frame_pct(text: str, share: Optional[float]) -> List[Dict]:
    """G2: câu "% of frame height" viết tay (#31 shot 23: 60%, "never resize her smaller") ↔ hình chiếu của máy shot."""
    found = [int(m.group(1)) for m in _PCT.finditer(str(text or ""))]
    if not found:
        return []
    if share is None:
        return [_f("R2-PCT", ("P31-G2",), "chữ ghi % khung nhưng không đo được hình chiếu người (thiếu máy / chỗ đứng)", level=KHONG_RO)]
    got = min(share, 1.0) * 100
    bad = [p for p in found if abs(p - got) > PCT_TOL]
    if not bad:
        return []
    return [_f("R2-PCT", ("P31-G2",), f"chữ ghi người chiếm {', '.join(f'{p}%' for p in bad)} khung nhưng máy 3D của shot cho {got:.0f}% "
                                      "— model vẽ theo chữ, nền theo máy: người sai tỉ lệ với nền",
               "thay bằng câu sinh từ hình chiếu: \"" + pct_sentence(share) + "\"", said=bad, measured=got)]


# ==== R3: chữ ↔ cái máy thấy =====================================================================================================
# các regex dưới chạy trên chữ ĐÃ bỏ dấu + chữ thường (stage_grid.fold): "bên trái" → "ben trai", "đỉnh" → "dinh"
_NEG = re.compile(r"\b(?:no|not|never|without|outside|out of (?:frame|view|shot)|off[- ]screen|hidden|khong|chua|ngoai khung)\b")
_RIGHT_ADV = re.compile(r"\bright (?:above|below|over|next|in front|behind|there|here|now|away|at|on|by|beside)\b")
_LEFT = re.compile(r"\b(?:left|ben trai|phia trai|trai)\b")
_RIGHT = re.compile(r"\b(?:right|ben phai|phia phai|phai)\b")
_TOP_WORDS = re.compile(r"\b(?:top|tip|spire|summit|peak|dinh|chop)\b")
_RELATIVE = re.compile(r"\b(?:above|over|on top of|atop|ngay tren|phia tren|tren dinh)\b")
_REVEAL = re.compile(r"\b(?:reveal(?:s|ing|ed)?|comes? into view|com(?:es|ing) into frame|appears?|emerg(?:es|ing)|not yet visible|"
                     r"lo ra|hien ra|chua thay|moi lo|dan hien)\b")


def landmarks_from_stage(stage: Dict, names: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Mốc từ stage.json `marks`: cặp <khóa>_chan / <khóa>_dinh (đáy / đỉnh) → {"key", "name", "words", "base", "top"}.
    names = {khóa: {"name": tiếng Anh, "words": [từ nhận]}}; thiếu → tên = khóa, từ = khóa bỏ dấu."""
    marks = (stage or {}).get("marks") or {}
    out = []
    for k, v in marks.items():
        if not k.endswith("_chan") or not isinstance(v, dict):
            continue
        key = k[:-len("_chan")]
        top = marks.get(key + "_dinh") or {}
        try:
            base = [float(c) for c in v["xyz"]]
            tip = [float(c) for c in top["xyz"]] if top.get("xyz") else None
        except (KeyError, TypeError, ValueError):
            continue
        meta = (names or {}).get(key) or {}
        out.append({"key": key, "name": meta.get("name") or key, "words": list(meta.get("words") or [sg.fold(key)]), "base": base, "top": tip})
    return out


def _third(u: float) -> str:
    return "left_third" if u < 1 / 3 else ("middle_third" if u < 2 / 3 else "right_third")


def view_of(cam, aim, lens: float, things: Iterable[Dict], aspect: float = ASPECT) -> Dict[str, Dict]:
    """Mỗi thứ {key, base, top?} → {"in": thấy (đáy / giữa / đỉnh trong khung), "third": bên (theo điểm thấy thấp nhất), "top_in",
    "base_in", "behind": cả ba sau lưng máy, "uv_top"}. Mốc cao: điểm giữa đại diện thân mốc."""
    out = {}
    for t in things:
        base = t["base"]
        top = t.get("top") or base
        mid = [(a + b) / 2 for a, b in zip(base, top)]
        st = {n: sg.point_state(cam, aim, p, lens, aspect) for n, p in (("base", base), ("mid", mid), ("top", top))}
        seen = [n for n in ("base", "mid", "top") if st[n]["state"] == "in"]
        third = _third(st[seen[0]]["uv"][0]) if seen else None
        out[t["key"]] = {"in": bool(seen), "third": third, "top_in": st["top"]["state"] == "in", "base_in": st["base"]["state"] == "in",
                         "behind": all(st[n]["state"] == "behind" for n in st), "uv_top": st["top"]["uv"], "has_top": bool(t.get("top")),
                         "name": t.get("name") or t["key"], "words": t.get("words") or [t["key"]]}
    return out


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s+|\n+", str(text or "")) if s.strip()]


def _mentions(sentence: str, words: Sequence[str]) -> Optional[re.Match]:
    low = sg.fold(sentence)
    for w in words:
        m = re.search(rf"\b{re.escape(sg.fold(w))}s?\b", low)
        if m:
            return m
    return None


def _negated(sentence: str, m: re.Match) -> bool:
    low = sg.fold(sentence)
    near = low[max(0, m.start() - 30):m.end() + 30]
    return bool(_NEG.search(near))


def in_view_sentence(v: Dict) -> str:
    if not v["in"]:
        return f"The {v['name']} is outside this frame (not visible)."
    where = v["third"].replace("_", " ")
    tail = "" if not v["has_top"] or v["top_in"] else ", its top cut off by the upper frame edge"
    return f"The {v['name']} sits in the {where} of the frame{tail}, exactly where the render shows it."


def text_vs_view(text: str, view: Dict[str, Dict], field: str = "prompt") -> List[Dict]:
    """Câu nhắc mốc trái tầm nhìn máy 3D → VÀNG + câu thay sinh từ tầm nhìn (G26, P33-B3, P33-B5)."""
    out = []
    for s in _sentences(text):
        for key, v in view.items():
            m = _mentions(s, v["words"])
            if not m or _negated(s, m):
                continue
            tag = f"{field}: \"{s[:160]}\""
            if not v["in"]:
                out.append(_f("R3-NOT-IN-FRAME", ("P31-G26",), f"{tag} nhắc {v['name']} nhưng máy 3D của shot không thấy nó "
                              f"({'sau lưng máy' if v['behind'] else 'ngoài khung'}) — model sẽ tự vẽ {v['name']} ở chỗ không có",
                              "bỏ câu đó, hoặc thay: \"" + in_view_sentence(v) + "\"", key=key, field=field))
                continue
            low = sg.fold(s)
            side = _RIGHT_ADV.sub(" ", low)                          # "right above" là trạng từ, không phải "bên phải"
            said = "left_third" if _LEFT.search(side) and not _RIGHT.search(side) else (
                "right_third" if _RIGHT.search(side) and not _LEFT.search(side) else None)
            if said and v["third"] != "middle_third" and said != v["third"]:
                out.append(_f("R3-SIDE", ("P31-G26",), f"{tag} đặt {v['name']} bên {'trái' if said == 'left_third' else 'phải'} nhưng máy 3D "
                              f"thấy nó ở {v['third'].replace('_', ' ')}", "thay: \"" + in_view_sentence(v) + "\"", key=key, field=field))
            if v["has_top"] and _TOP_WORDS.search(low) and not v["top_in"]:
                out.append(_f("R3-TOP-CUT", ("P33-B5",), f"{tag} tả đỉnh {v['name']} nhưng đỉnh ngoài mép khung của máy 3D (bị cắt)",
                              "bỏ câu tả đỉnh, hoặc đổi máy / cỡ cảnh cho thấy đỉnh (khai trong BYĐ), không sửa bằng chữ",
                              key=key, field=field))
            if _RELATIVE.search(low) and _TOP_WORDS.search(low) and v["top_in"]:
                u, w = v["uv_top"]
                out.append(_f("R3-RELATIVE", ("P33-B3",), f"{tag} đặt một thứ bằng chữ so với {v['name']} — model dời chính {v['name']} cho "
                              "khớp chữ (#33: \"mắt xoáy ngay trên đỉnh tháp\" → tháp ra giữa)",
                              f"đặt vật đó bằng nền 3D / ghép ảnh; chữ chỉ giữ mốc: \"Keep the {v['name']} exactly where the render shows it "
                              f"(its top at {u * 100:.0f}% from the left, {w * 100:.0f}% from the top of the frame).\"", key=key, field=field))
    return out


STILL_MOVES = ("", "static", "none", "locked", "dung_yen")


def motion_vs_view(motion: str, view: Dict[str, Dict], camera_move: Optional[str] = None) -> List[Dict]:
    """G11: motion phải khớp KHUNG ĐẦU đã duyệt (tầm nhìn máy lúc mở clip): "lộ ra / hiện ra / chưa thấy" một thứ khung đầu đã thấy → VÀNG;
    nhắc thứ khung đầu không thấy khi máy đứng yên → VÀNG (máy không quay tới được)."""
    out = []
    still = str(camera_move or "").strip().lower() in STILL_MOVES
    for s in _sentences(motion):
        for key, v in view.items():
            m = _mentions(s, v["words"])
            if not m:
                continue
            if _REVEAL.search(sg.fold(s)) and v["in"]:
                out.append(_f("R3-MOTION-REVEAL", ("P31-G11",), f"motion: \"{s[:160]}\" cho {v['name']} lộ ra / chưa thấy nhưng khung đầu ĐÃ "
                              f"thấy nó ({v['third'].replace('_', ' ')})", "tả đúng khung đầu: \"" + in_view_sentence(v) + "\"",
                              key=key))
            elif still and not v["in"] and not _negated(s, m):
                out.append(_f("R3-MOTION-UNSEEN", ("P31-G11", "P31-G26"), f"motion: \"{s[:160]}\" nhắc {v['name']} nhưng khung đầu không thấy "
                              "nó và máy đứng yên — clip sẽ bịa nó vào", "bỏ câu đó, hoặc thay: \"" + in_view_sentence(v) + "\"",
                              key=key))
    return out


def _plain(word: str) -> str:
    s = unicodedata.normalize("NFD", word.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def vi_leaks(text: str, glossary: Optional[Dict[str, str]] = None) -> List[Dict]:
    """P33-B7: chữ có dấu tiếng Việt còn trong prompt tiếng Anh (tên Kho "RỐI ĐỎ A", "Tháp Đồng Hồ") — cổng video chặn SAU khi dựng gói.
    Câu thay: glossary (tên tiếng Anh, so bỏ dấu) → không thì bỏ dấu giữ hoa/thường."""
    gl = {sg.fold(k): v for k, v in (glossary or {}).items()}
    text = str(text or "")
    toks = list(re.finditer(r"[^\W\d_]+", text))
    accented = [any(ord(c) > 127 for c in t.group(0)) for t in toks]
    out, seen, k = [], set(), 0
    while k < len(toks):
        if not accented[k]:
            k += 1
            continue
        a = b = k                               # một cụm: chữ có dấu + chữ Hoa liền kề (tên "RỐI ĐỎ A", "Tháp Đồng Hồ")
        while a > 0 and toks[a - 1].group(0)[:1].isupper() and toks[a - 1].end() + 1 >= toks[a].start() and toks[a].group(0)[:1].isupper():
            a -= 1
        while b + 1 < len(toks) and toks[b + 1].start() - toks[b].end() <= 1 and (
                accented[b + 1] or (toks[b + 1].group(0)[:1].isupper() and toks[b].group(0)[:1].isupper())):
            b += 1
        bit = text[toks[a].start():toks[b].end()]
        k = b + 1
        if bit in seen:
            continue
        seen.add(bit)
        fix = next((v for g, v in gl.items() if g and g in sg.fold(bit)), None) or _plain(bit)
        out.append(_f("R3-VI-TEXT", ("P33-B7",), f"prompt tiếng Anh còn chữ có dấu \"{bit}\" — cổng video chặn khi gửi",
                      f"thay \"{bit}\" → \"{fix}\"", said=bit, replace=fix))
    return out


_GUARD = re.compile(r"\bonly (?:give|gives|for|provides?)\b[^.]*\b(?:motion|movement|timing|rhythm)\b|\bdo not (?:draw|copy|show)\b|"
                    r"\bnever (?:draw|copy|show)\b", re.I)


def ref_leaks(text: str, ref_words: Sequence[str]) -> List[Dict]:
    """P33-B10: chủ thể của video mẫu (vd "cats") nhắc ngoài câu chặn ("the cats in the reference only give the motion…") → model vẽ chủ thể
    đó. Câu chặn (_GUARD) được phép nhắc."""
    out = []
    for s in _sentences(text):
        if _GUARD.search(s):
            continue
        for w in ref_words:
            m = re.search(rf"\b{re.escape(w)}\b", s, re.I)
            if m:
                out.append(_f("R3-REF-LEAK", ("P33-B10",), f"motion nhắc \"{m.group(0)}\" (chủ thể video mẫu) ngoài câu chặn: \"{s[:160]}\" — "
                              f"model có thể vẽ {m.group(0)}", f"thay \"{m.group(0)}\" bằng \"like the reference video\"; giữ tên chủ thể "
                              "chỉ trong câu chặn", word=m.group(0)))
    return out


# ==== R4: BYĐ ↔ trường shot ======================================================================================================
MOVE_OF_BYD = {"dung_yen": ("static", "none", "locked", ""), "tien": ("push_in", "dolly_in", "zoom"), "lui": ("pull_out", "dolly_out")}


def _byd_move(byd: Dict) -> Optional[str]:
    cd = ((byd or {}).get("may") or {}).get("chuyen_dong")
    return cd.get("kieu") if isinstance(cd, dict) else cd


def byd_vs_fields(data: Dict) -> List[Dict]:
    """G18: BYĐ của shot mâu thuẫn trường khác của CHÍNH shot (một chỗ kiểm): may.co ↔ size, may.do_cao / goc ↔ angle,
    may.chuyen_dong ↔ camera_move, thanh_phan (vai chinh / phu) ↔ characters. Shot thiếu BYĐ → [] (byd_coverage nói cho cả dự án)."""
    byd = (data or {}).get("byd")
    if not isinstance(byd, dict):
        return []
    out = []
    may = byd.get("may") if isinstance(byd.get("may"), dict) else {}
    size = str(data.get("size") or data.get("shot_size") or "").upper()
    if may.get("co") and size and str(may["co"]).upper() != size:
        out.append(_f("R4-SIZE", ("P31-G18",), f"BYĐ may.co '{may['co']}' ≠ size của shot '{size}'", "Đạo diễn chọn một: sửa BYĐ hoặc size"))
    angle = str(data.get("angle") or "").lower()
    if angle in DO_CAO_OF_ANGLE:
        if may.get("do_cao") and may["do_cao"] != DO_CAO_OF_ANGLE[angle] and not (angle == "eye" and may["do_cao"] == "ngang"):
            out.append(_f("R4-ANGLE", ("P31-G18",), f"BYĐ may.do_cao '{may['do_cao']}' ≠ angle '{angle}' của shot (cần '{DO_CAO_OF_ANGLE[angle]}')",
                          "Đạo diễn chọn một: sửa BYĐ hoặc angle"))
        if may.get("goc") and may["goc"] != GOC_OF_ANGLE[angle]:
            out.append(_f("R4-ANGLE", ("P31-G18",), f"BYĐ may.goc '{may['goc']}' ≠ angle '{angle}' của shot (cần '{GOC_OF_ANGLE[angle]}')",
                          "Đạo diễn chọn một: sửa BYĐ hoặc angle"))
    move = str(data.get("camera_move") or "").strip().lower()
    bm = _byd_move(byd)
    if bm and move:
        ok = MOVE_OF_BYD.get(bm, ())
        if move not in ok:
            out.append(_f("R4-MOVE", ("P31-G18",), f"BYĐ may.chuyen_dong '{bm}' ≠ camera_move '{move}' của shot"
                          + (" (BYĐ chưa có kiểu chuyển động này)" if not any(move in v for v in MOVE_OF_BYD.values()) else "")
                          + " — motion bị Tổ rà soát báo đỏ một phía", "Đạo diễn chọn một: sửa BYĐ hoặc camera_move; motion viết theo bên đã chọn"))
    cast = {sg.fold(c) for c in data.get("characters") or [] if str(c or "").strip()}
    if cast:
        for c in byd.get("thanh_phan") or []:
            if not isinstance(c, dict) or c.get("vai") not in ("chinh", "phu"):
                continue
            who = str(c.get("vat") or "")
            if who and who.isupper() and sg.fold(who) not in cast and not any(sg.fold(who) in x or x in sg.fold(who) for x in cast):
                out.append(_f("R4-CAST", ("P31-G18",), f"BYĐ thanh_phan có '{who}' (vai {c['vai']}) nhưng characters của shot không có",
                              "thêm vào characters hoặc bỏ khỏi BYĐ"))
    return out


def byd_coverage(shots: Sequence[Dict]) -> List[Dict]:
    """P33-A12: dự án thiếu BYĐ → MỘT phát hiện cho cả dự án (số shot thiếu + kiểm bị bỏ), không lặp 22 dòng."""
    missing = [s.get("shot", i + 1) for i, s in enumerate(shots) if not isinstance((s or {}).get("byd"), dict)]
    if not missing:
        return []
    return [_f("R4-NO-BYD", ("P33-A12",), f"{len(missing)}/{len(shots)} shot chưa có BYĐ (shot {', '.join(map(str, missing[:12]))}"
               f"{'…' if len(missing) > 12 else ''}) — không kiểm được nhịp đầu/đỉnh/cuối, khung cuối, BYĐ ↔ trường",
               "chạy Đạo diễn BYĐ (director_byd.settle, chạy được qua claude_cli) cho dự án", missing=len(missing), total=len(shots))]


# ==== gộp cho một shot =============================================================================================================
def shot_report(data: Dict, cam, aim, lens: float, spot, height_m: float, floor_at=None, things: Sequence[Dict] = (),
                aspect: float = ASPECT, texts: Optional[Dict[str, str]] = None, motion: Optional[str] = None,
                glossary: Optional[Dict[str, str]] = None, ref_words: Sequence[str] = ()) -> List[Dict]:
    """Mọi bất biến R2 + R3 + R4 của một shot (đã có máy). texts = {trường: chữ} (prompt ảnh, blocking…); motion = motion prompt."""
    data = data or {}
    out = check_pitch(data.get("angle"), pitch_of(cam, aim), declared=bool(data.get("angle")))
    out += check_framing(data.get("size") or data.get("shot_size") or pc.DEFAULT_SIZE, cam, aim, lens, spot, height_m, aspect,
                         data.get("angle") or "eye")
    if floor_at is not None:
        out += check_floor(cam, aim, lens, spot, height_m, floor_at, aspect)
    share = body_share(cam, aim, lens, aspect, spot, height_m)
    texts = dict(texts or {})
    for field, text in texts.items():
        out += check_frame_pct(text, share)
    view = view_of(cam, aim, lens, things, aspect) if things else {}
    for field, text in texts.items():
        out += text_vs_view(text, view, field)
        out += vi_leaks(text, glossary)
    if motion:
        out += motion_vs_view(motion, view, data.get("camera_move"))
        out += vi_leaks(motion, glossary)
        if ref_words:
            out += ref_leaks(motion, ref_words)
    out += byd_vs_fields(data)
    return out
