"""Hướng CHẠY (lên / xuống, theo chiều nào so với máy) — sự thật do CODE viết từ độ cao chỗ đứng 3D, không để chữ (người dùng 14/10,
kiểm thật #30 shot 1, cờ `travel_truth`).

Gốc lỗi: kịch bản "Kelly đứng ở điểm A — chân cầu thang … chạy nhanh lên tới điểm B — bậc cao nhất". Sân khấu 3D biết A = chỗ đứng
`bac_thang_giua` (z 3,93 m), B = `dinh_bac_thang_giua` (z 8,5 m) — nhưng không câu nào trong prompt nói điều đó; chữ Đạo diễn ("chạy về
phía máy, cầu thang đổ xuống sau lưng") lại trái với nền render (máy đứng phía dưới nhìn lên theo hướng chạy) → model vẽ Kelly chạy
XUỐNG. Lớp sửa trước (plate_view_fix) chỉ sửa hướng NỀN, không nói hướng CHẠY.

    for_shot(conn, pid, scene_id, data, rec) -> {"sentence": str, "warn": [str], "facts": {...} | None}

- Điểm đi A = chỗ đứng của shot (location_pack.spot_for); điểm đến B = chỗ đứng KHÁC của shot kế tiếp cùng cảnh kịch bản (cùng
  `story_scene`, cùng `sequence` nếu có) khi shot này nối liền shot sau (`continuous_with_next`) và chữ shot có động từ di chuyển.
- Chỉ viết khi chênh độ cao RÕ: |Δz| ≥ MIN_RISE_M (1,5 m ≈ nửa tầng nhà — dưới mức đó là gồ ghề mặt đất / hai bậc quảng trường, nói
  "lên/xuống" dễ sai) VÀ độ dốc |Δz| / quãng ngang ≥ MIN_GRADE (0,12 ≈ 7° — dốc thoải hơn nhìn như mặt phẳng).
- Chiều so với máy: từ máy của render (rec.camera_plan location → look_at, cùng hệ toạ độ mô hình với chỗ đứng): đi theo hướng máy nhìn
  (cos ≥ 0,5) = ra xa máy; ngược (≤ −0,5) = về phía máy; còn lại = ngang khung (phải / trái). Không có render → chỉ nói lên/xuống.
- Chữ shot nói chiều so với máy ngược với render → VÀNG nêu cách sửa (hướng nền), không đoán bên nào đúng.
- Không có dữ liệu 3D (không gói 3D / không biết điểm đến) mà chữ shot nói cầu thang / dốc + di chuyển → VÀNG, không viết câu.
Không gọi model, 0 USD.
"""
import math
import re
from typing import Dict, List, Optional

FLAG = "travel_truth"
MIN_RISE_M = 1.5
MIN_GRADE = 0.12
MARK = "Direction of travel (measured on the 3D map):"

_MOVE = re.compile(r"(?<!\w)(?:run(?:s|ning)?|ran|sprint(?:s|ing)?|dash(?:es|ing)?|jog(?:s|ging)?|walk(?:s|ing)?|climb(?:s|ing)?|"
                   r"rush(?:es|ing)?|hurr(?:y|ies|ying)|charg(?:e|es|ing)|ascend(?:s|ing)?|descend(?:s|ing)?|"
                   r"chạy|đi lên|đi xuống|leo|trèo|lao|bước)(?!\w)", re.I)
_SLOPE_WORDS = re.compile(r"(?<!\w)(?:stair(?:s|case|way)?|steps|slope|ramp|hill|cầu thang|bậc thang|bậc|dốc)(?!\w)", re.I)
_UPDOWN = re.compile(r"(?<!\w)(?:up|down|upward|downward|uphill|downhill|ascend\w*|descend\w*|climb\w*|lên|xuống|leo|trèo)(?!\w)", re.I)
_STAIR_WORDS = re.compile(r"(?<!\w)(?:stair(?:s|case|way)?|steps|cầu thang|bậc thang|bậc)(?!\w)", re.I)
_TOWARD = re.compile(r"toward(?:s)? (?:the )?(?:camera|lens|viewer)|(?:at|into) the camera|về phía (?:máy|camera)|lao về phía máy", re.I)
_AWAY = re.compile(r"away from (?:the )?camera|back to (?:the )?camera|from behind|seen from behind|quay lưng|xa (?:dần )?máy", re.I)
_NEG = re.compile(r"(?:\bnot|\bnever|\bno|n't|không|chưa)\s+(?:\w+\s+){0,2}$", re.I)
_TEXT_KEYS = ("action", "text", "image_prompt", "blocking", "action_peak")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _words(data: Dict) -> str:
    return " ".join(str((data or {}).get(k) or "") for k in _TEXT_KEYS)


def _said(rx: "re.Pattern", text: str) -> bool:
    return any(not _NEG.search(text[max(0, m.start() - 30):m.start()]) for m in rx.finditer(text or ""))


def _spot(entry: Dict, data: Dict) -> Optional[Dict]:
    from . import location_pack
    try:
        sp = location_pack.spot_for(entry, data)
    except Exception:  # noqa: BLE001 - gói 3D không có chỗ đứng: không đoán
        return None
    at = sp.get("at")
    return sp if isinstance(at, (list, tuple)) and len(at) >= 3 else None


def _next_spot(conn, pid: int, scene_id: int, data: Dict, entry: Dict, here: str) -> Optional[Dict]:
    """Chỗ đứng (khác chỗ này) của shot KẾ NGAY sau, cùng cảnh kịch bản (cùng sequence nếu có), khi shot này nối liền shot đó."""
    import json
    row = conn.execute("SELECT idx FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None
    if not data.get("continuous_with_next"):
        return None
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? AND idx>? ORDER BY idx", (pid, row["idx"])).fetchall()
    for r in rows:
        d = json.loads(r["data"] or "{}")
        if d.get("story_scene") != data.get("story_scene"):
            return None
        if data.get("sequence") is not None and d.get("sequence") != data.get("sequence"):
            return None
        sp = _spot(entry, d)
        # chỉ shot KẾ NGAY: shot sau cùng chỗ đứng = đường chạy chưa rời chỗ này trong shot này (không nối qua nhiều shot)
        return sp if sp is not None and sp.get("name") != here else None
    return None


def _prev_spot(conn, pid: int, scene_id: int, data: Dict, entry: Dict, here: str) -> Optional[Dict]:
    """Shot là CHẶNG CUỐI của đường chạy (không có điểm đến phía sau): chỗ đứng (khác chỗ này) của shot TRƯỚC NGAY, cùng cảnh kịch bản,
    nối liền tới shot này (`continuous_with_next`)."""
    import json
    row = conn.execute("SELECT idx FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None
    rows = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? AND idx<? ORDER BY idx DESC", (pid, row["idx"])).fetchall()
    for r in rows:
        d = json.loads(r["data"] or "{}")
        if d.get("story_scene") != data.get("story_scene") or not d.get("continuous_with_next"):
            return None
        if data.get("sequence") is not None and d.get("sequence") != data.get("sequence"):
            return None
        sp = _spot(entry, d)
        return sp if sp is not None and sp.get("name") != here else None   # chỉ shot TRƯỚC NGAY (như _next_spot)
    return None


def _relation(rec: Optional[Dict], a, b) -> Optional[str]:
    """'away' | 'toward' | 'right' | 'left' — chiều đi A→B so với máy của render; None khi không có máy (không đoán)."""
    cam = (rec or {}).get("camera_plan") or {}
    loc, look = cam.get("location"), cam.get("look_at")
    if not (isinstance(loc, (list, tuple)) and isinstance(look, (list, tuple)) and len(loc) >= 2 and len(look) >= 2):
        return None
    fx, fy = float(look[0]) - float(loc[0]), float(look[1]) - float(loc[1])
    tx, ty = float(b[0]) - float(a[0]), float(b[1]) - float(a[1])
    fn, tn = math.hypot(fx, fy), math.hypot(tx, ty)
    if fn < 1e-6 or tn < 1e-6:
        return None
    fx, fy, tx, ty = fx / fn, fy / fn, tx / tn, ty / tn
    dot = fx * tx + fy * ty
    if dot >= 0.5:
        return "away"
    if dot <= -0.5:
        return "toward"
    return "right" if tx * fy - ty * fx > 0 else "left"     # khung phải của máy = hướng nhìn quay 90° theo chiều kim đồng hồ


def _label(sp: Dict) -> str:
    return str(sp.get("label") or sp.get("name") or "").split(" (", 1)[0].strip() or str(sp.get("name"))


def for_shot(conn, pid: int, scene_id: int, data: Dict, rec: Optional[Dict] = None) -> Dict:
    out = {"sentence": "", "warn": [], "facts": None}
    words = _words(data)
    if not _said(_MOVE, words):
        return out                                   # shot không di chuyển: không có hướng chạy để nói
    # VÀNG "không đủ dữ liệu" chỉ khi chữ shot thật sự nói đi LÊN / XUỐNG cầu thang / dốc (shot đứng trên bậc mà chạy ngang thì không)
    slope_said = _said(_SLOPE_WORDS, words) and _said(_UPDOWN, words)
    from . import assets, location_pack
    try:
        place = assets.scene_location(conn, pid, data)
        entry = location_pack.model3d(conn, place["id"]) if place else None
    except Exception:  # noqa: BLE001 - CSDL không có bảng Kho (test cũ): như không có gói 3D
        entry = None
    a = _spot(entry, data) if entry and entry.get("spots") else None
    if a is None:
        if slope_said:
            out["warn"].append("shot di chuyển trên cầu thang/dốc mà bối cảnh không có gói 3D / chỗ đứng có độ cao — không viết câu "
                               "hướng lên/xuống (không đoán)")
        return out
    b = _next_spot(conn, pid, scene_id, data, entry, a.get("name"))
    arriving = False
    if b is None:                                    # chặng cuối: đi từ chỗ đứng của shot trước tới chỗ đứng của shot này
        prev = _prev_spot(conn, pid, scene_id, data, entry, a.get("name"))
        if prev is not None:
            a, b, arriving = prev, a, True
    if b is None:
        if slope_said:
            out["warn"].append(f"shot di chuyển trên cầu thang/dốc từ chỗ đứng '{a.get('name')}' mà không biết điểm đến (shot kế cùng "
                               "cảnh không nối liền / cùng chỗ đứng) — không viết câu hướng lên/xuống (không đoán)")
        return out
    za, zb = float(a["at"][2]), float(b["at"][2])
    dz = zb - za
    run = math.hypot(float(b["at"][0]) - float(a["at"][0]), float(b["at"][1]) - float(a["at"][1]))
    rel = _relation(rec, a["at"], b["at"])
    out["facts"] = {"from": a.get("name"), "to": b.get("name"), "z_from": round(za, 2), "z_to": round(zb, 2), "rise_m": round(dz, 2),
                    "run_m": round(run, 2), "relation": rel, "arriving": arriving}
    if abs(dz) < MIN_RISE_M or (run > 0 and abs(dz) / run < MIN_GRADE):
        return out                                   # gần như phẳng: "lên/xuống" dễ sai, không viết
    up = dz > 0
    stairs = bool(_STAIR_WORDS.search(f"{a.get('label') or ''} {b.get('label') or ''} {words}"))
    who = next((str(n) for n in data.get("characters") or [] if str(n).strip()), "the character")
    way = ("UP the stairs" if up else "DOWN the stairs") if stairs else ("UPHILL" if up else "DOWNHILL")
    rel_words = {
        "away": f"{who} moves AWAY from the camera, into the depth of the frame, toward the {'higher' if up else 'lower'} ground in the "
                f"background — seen from behind",
        "toward": f"{who} moves TOWARD the camera, coming {'up from the lower' if up else 'down from the higher'} ground behind "
                  f"{who} — the ground behind {who} is {'lower' if up else 'higher'} than where {who} is now",
        "right": f"{who} moves across the frame toward FRAME-RIGHT while going {'up' if up else 'down'}",
        "left": f"{who} moves across the frame toward FRAME-LEFT while going {'up' if up else 'down'}",
    }
    bits = [f"{MARK} {who} goes {way} — from {_label(a)} (ground {za:.1f} m) to {_label(b)} ({zb:.1f} m), "
            f"{abs(dz):.1f} m {'higher' if up else 'lower'}" + (f" (this shot is the end of that run: {who} is arriving at the "
                                                                 f"{'top' if up else 'bottom'})" if arriving else "")]
    if rel:
        bits.append(rel_words[rel])
    bits.append(f"never going {'down' if up else 'up'}")
    out["sentence"] = "; ".join(bits) + "."
    if rel in ("away", "toward"):
        claims_toward, claims_away = _said(_TOWARD, words), _said(_AWAY, words)
        if (rel == "away" and claims_toward and not claims_away) or (rel == "toward" and claims_away and not claims_toward):
            from .plate_choice import bearing
            fix = bearing(b["at"], a["at"]) if rel == "away" else bearing(a["at"], b["at"])
            out["warn"].append(
                f"chữ shot nói {who} chạy {'VỀ PHÍA máy' if rel == 'away' else 'RA XA máy / quay lưng'} nhưng máy của nền 3D "
                f"{'đứng sau lưng hướng chạy' if rel == 'away' else 'đứng trước hướng chạy'} ({_label(a)} → {_label(b)}, "
                f"{'lên' if up else 'xuống'} {abs(dz):.1f} m) — câu hướng chạy theo nền; muốn {'chạy về phía máy' if rel == 'away' else 'máy sau lưng'}"
                f" thì đặt plate_view background ≈ {fix:g}° rồi render lại nền (0 USD)")
    return out


def kept_after_rewrite(assembled: str, prompt: str, limit: Optional[int] = None) -> str:
    """D6 viết lại prompt: câu hướng chạy của code phải còn nguyên chữ (như side_truth.kept_after_rewrite)."""
    from . import side_truth
    lines = list(dict.fromkeys(m.group(0) for m in re.finditer(re.escape(MARK) + r"[^\n]*?\.(?=\s|$)", assembled or "")))
    if not lines or prompt == assembled:
        return prompt
    out = prompt
    for line in lines:
        out = side_truth.append(out, line)
    return assembled if limit and len(out) > limit else out

