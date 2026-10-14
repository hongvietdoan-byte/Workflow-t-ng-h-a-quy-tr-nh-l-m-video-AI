"""Hướng CHẠY (lên / xuống, theo chiều nào so với máy) — sự thật do CODE viết từ độ cao chỗ đứng 3D, không để chữ (người dùng 14/10,
kiểm thật #30 shot 1, cờ `travel_truth`).

Gốc lỗi: kịch bản "Kelly đứng ở điểm A — chân cầu thang … chạy nhanh lên tới điểm B — bậc cao nhất". Sân khấu 3D biết A = chỗ đứng
`bac_thang_giua` (z 3,93 m), B = `dinh_bac_thang_giua` (z 8,5 m) — nhưng không câu nào trong prompt nói điều đó; chữ Đạo diễn ("chạy về
phía máy, cầu thang đổ xuống sau lưng") lại trái với nền render (máy đứng phía dưới nhìn lên theo hướng chạy) → model vẽ Kelly chạy
XUỐNG. Lớp sửa trước (plate_view_fix) chỉ sửa hướng NỀN, không nói hướng CHẠY.

    for_shot(conn, pid, scene_id, data, rec) -> {"sentence": str, "warn": [str], "facts": {...} | None}

- Điểm đi A = chỗ đứng của shot (location_pack.spot_for); điểm đến B = chỗ đứng KHÁC của shot KẾ NGAY cùng cảnh kịch bản (cùng
  `story_scene`, cùng `sequence` nếu có) khi shot này nối liền shot sau (`continuous_with_next`) và chữ shot có động từ di chuyển.
  Không có điểm đến mà shot TRƯỚC NGAY (nối liền) đứng chỗ khác → shot này là chặng cuối (đi từ chỗ đó tới đây, "arriving").
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
# "up the stairs", "lên cầu thang", "climbs the steps", "uphill" — hướng lên/xuống GẮN với cầu thang / dốc (không lấy "dựng lên", "looking down")
_UPDOWN = re.compile(r"(?<!\w)(?:(?:up|down|climb\w*|ascend\w*|descend\w*|lên|xuống|leo|trèo)\s+(?:\w+\s+){0,3}?"
                     r"(?:stair(?:s|case|way)?|steps|slope|ramp|hill|cầu thang|bậc thang|bậc|dốc)|uphill|downhill)(?!\w)", re.I)
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
    r = conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx>? ORDER BY idx LIMIT 1", (pid, row["idx"])).fetchone()
    if r is None:
        return None
    d = json.loads(r["data"] or "{}")
    if d.get("story_scene") != data.get("story_scene"):
        return None
    if data.get("sequence") is not None and d.get("sequence") != data.get("sequence"):
        return None
    sp = _spot(entry, d)
    # chỉ shot KẾ NGAY: shot sau cùng chỗ đứng = đường chạy chưa rời chỗ này trong shot này (không nối qua nhiều shot)
    return sp if sp is not None and sp.get("name") != here else None


def _prev_spot(conn, pid: int, scene_id: int, data: Dict, entry: Dict, here: str) -> Optional[Dict]:
    """Shot là CHẶNG CUỐI của đường chạy (không có điểm đến phía sau): chỗ đứng (khác chỗ này) của shot TRƯỚC NGAY, cùng cảnh kịch bản,
    nối liền tới shot này (`continuous_with_next`)."""
    import json
    row = conn.execute("SELECT idx FROM scenes WHERE id=?", (scene_id,)).fetchone()
    if row is None:
        return None
    r = conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx<? ORDER BY idx DESC LIMIT 1", (pid, row["idx"])).fetchone()
    if r is None:
        return None
    d = json.loads(r["data"] or "{}")
    if d.get("story_scene") != data.get("story_scene") or not d.get("continuous_with_next"):
        return None
    if data.get("sequence") is not None and d.get("sequence") != data.get("sequence"):
        return None
    sp = _spot(entry, d)
    return sp if sp is not None and sp.get("name") != here else None   # chỉ shot TRƯỚC NGAY (như _next_spot)


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
    """Nhãn chỗ đứng cho NGƯỜI (diag tiếng Việt)."""
    return str(sp.get("label") or sp.get("name") or "").split(" (", 1)[0].strip() or str(sp.get("name"))


def _label_en(sp: Dict, low: bool, stairs: bool) -> str:
    """Nhãn chỗ đứng cho PROMPT tiếng Anh (14/10 #30: "from chân cầu thang nhiều tầng …" lọt vào prompt ảnh): `label_en` của chỗ
    đứng nếu có; nhãn đã là chữ ASCII thì dùng nguyên; còn lại mô tả trung tính theo thấp / cao — không để tiếng Việt vào prompt."""
    for key in ("label_en", "label"):
        text = str(sp.get(key) or "").split(" (", 1)[0].strip()
        if text and (key == "label_en" or all(ord(ch) < 128 for ch in text)):
            return text
    if stairs:
        return "the foot of the stairs" if low else "the top of the stairs"
    return "the bottom of the slope" if low else "the top of the slope"


def route(conn, pid: int, scene_id: int, data: Dict) -> Dict:
    """Đường đi A→B của shot — MỘT nguồn cho câu hướng chạy (for_shot) VÀ chỗ đặt máy 3D (camera_route → plate_camera.travel_camera):
    {"entry", "here" (chỗ đứng của shot), "a", "b", "arriving", "why"}; a/b None khi không biết (why = lý do, tiếng Việt)."""
    out = {"entry": None, "here": None, "a": None, "b": None, "arriving": False, "why": None}
    from . import assets, location_pack
    try:
        place = assets.scene_location(conn, pid, data)
        entry = location_pack.model3d(conn, place["id"]) if place else None
    except Exception:  # noqa: BLE001 - CSDL không có bảng Kho (test cũ): như không có gói 3D
        entry = None
    out["entry"] = entry
    a = _spot(entry, data) if entry and entry.get("spots") else None
    if a is None:
        out["why"] = "bối cảnh không có gói 3D / chỗ đứng có độ cao"
        return out
    out["here"] = a
    b = _next_spot(conn, pid, scene_id, data, entry, a.get("name"))
    if b is None:                                    # chặng cuối: đi từ chỗ đứng của shot trước tới chỗ đứng của shot này
        prev = _prev_spot(conn, pid, scene_id, data, entry, a.get("name"))
        if prev is not None:
            out.update(a=prev, b=a, arriving=True)
            return out
        out["why"] = (f"không biết điểm đến từ chỗ đứng '{a.get('name')}' (shot kế cùng cảnh không nối liền / cùng chỗ đứng, shot "
                      "trước không nối tới)")
        return out
    out.update(a=a, b=b)
    return out


# ---- (b) chỗ đặt máy theo đường chạy (14/10 #30, người dùng: "máy đi theo nhân vật còn nhân vật chạy lên, hoặc máy ở trên cao lùi,
# nhân vật chạy lên theo máy") — trước đây máy 3D LUÔN đứng tại chỗ đứng của shot, nhìn theo plate_view ----
LEAD_MOVES = ("pull_out",)                     # shots.MOVES (dolly_out / pull đã quy về pull_out ở shot_normalize): máy LÙI trước mặt
NO_LEAD_MOVES = ("orbit", "crane", "whip", "pan", "tilt")   # máy vòng / cẩu / lia: khung đầu không chắc ở trước mặt → không đặt theo đường
# máy lùi / bám sau: chữ MÁY của shot (`shot`, `camera_setup`) — "pulls out" trong chữ hành động là rút súng, không phải máy lùi;
# trong chữ hành động chỉ nhận câu có chủ ngữ là máy ("camera pulls back", "máy lùi", "máy bám sau")
_LEAD_CAM = re.compile(r"(?<!\w)(?:pull(?:s|ing)?[ -](?:out|back)|dolly(?:ing)?[ -](?:out|back)|truck(?:s|ing)?[ -]back|leading shot)(?!\w)", re.I)
_LEAD_WORDS = re.compile(r"(?<!\w)(?:camera (?:pulls|pulling|dollies|dollying|backs|backing|retreats|retreating|moves back|leads|leading)|"
                         r"máy (?:quay )?lùi|lùi máy)(?!\w)", re.I)
_FOLLOW_CAM = re.compile(r"(?<!\w)(?:(?:track|follow)(?:s|ing)?(?: shot)? behind|chase cam)(?!\w)", re.I)
_FOLLOW_WORDS = re.compile(r"(?<!\w)(?:camera (?:follows|following|tracks|tracking) (?:behind|from behind)|camera follows|"
                           r"(?:máy|camera) (?:quay )?(?:đi |chạy )?(?:bám|theo) sau)(?!\w)", re.I)


def camera_mode(data: Dict) -> Dict:
    """Máy đứng đâu so với đường chạy: {"mode": "lead" | "follow" | None, "why", "problem"}.
    lead = máy TRƯỚC mặt trên đường A→B, nhìn về A (camera_move pull_out / chữ máy lùi / chữ nhân vật chạy VỀ PHÍA máy, trừ máy vòng/cẩu/lia);
    follow = máy SAU LƯNG, nhìn về B (chữ bám sau / follow, hoặc track + máy sau lưng). Cả hai nghĩa → None + problem (không đoán)."""
    from .plate_choice import is_behind
    words = _words(data)
    cam_words = " ".join(str(data.get(k) or "") for k in ("shot", "camera_setup"))
    move = str(data.get("camera_move") or "").strip().lower()
    toward, away = _said(_TOWARD, words), _said(_AWAY, words)
    behind = is_behind(data)
    lead = move in LEAD_MOVES or (move not in NO_LEAD_MOVES and (
        _said(_LEAD_CAM, cam_words) or _said(_LEAD_WORDS, words + " " + cam_words) or (toward and not away)))
    follow = (_said(_FOLLOW_CAM, cam_words) or _said(_FOLLOW_WORDS, words + " " + cam_words)
              or (move == "track" and (behind or (away and not toward))))
    if lead and (follow or behind):
        return {"mode": None, "why": None,
                "problem": ("chữ shot vừa nói máy LÙI trước mặt / nhân vật chạy về phía máy, vừa nói máy bám sau lưng — không đặt máy "
                            "theo đường chạy (không đoán); sửa camera_move / chữ shot")}
    if lead:
        return {"mode": "lead", "why": f"camera_move '{move or '-'}'" + (" + chữ chạy về phía máy" if toward else ""), "problem": None}
    if follow:
        return {"mode": "follow", "why": f"camera_move '{move or '-'}' + chữ máy bám sau", "problem": None}
    return {"mode": None, "why": None, "problem": None}


def camera_route(conn, pid: int, scene_id: int, data: Dict) -> Optional[Dict]:
    """location_pack.plan (cờ travel_truth): {"mode", "here", "a", "b", "arriving", "why"} khi shot DI CHUYỂN A→B và chữ nói máy lùi
    trước mặt / bám sau; {"problem"} khi chữ nói vậy mà không có đường (không gói 3D / không điểm đến / hai nghĩa); None = không liên
    quan (máy như cũ, không nói gì)."""
    if not _said(_MOVE, _words(data)):
        return None
    m = camera_mode(data)
    if m["problem"]:
        return {"problem": m["problem"]}
    if not m["mode"]:
        return None
    r = route(conn, pid, scene_id, data)
    if r["a"] is None or r["b"] is None:
        return {"problem": f"shot di chuyển, máy {'lùi trước mặt' if m['mode'] == 'lead' else 'bám sau'} nhưng {r['why']} — máy 3D "
                           "giữ chỗ cũ (tại chỗ đứng của shot), không đặt theo đường chạy (không đoán)"}
    return {"mode": m["mode"], "here": r["here"], "a": r["a"], "b": r["b"], "arriving": r["arriving"], "why": m["why"]}


def for_shot(conn, pid: int, scene_id: int, data: Dict, rec: Optional[Dict] = None) -> Dict:
    out = {"sentence": "", "warn": [], "facts": None, "needs": None}
    words = _words(data)
    if not _said(_MOVE, words):
        return out                                   # shot không di chuyển: không có hướng chạy để nói
    # VÀNG "không đủ dữ liệu" chỉ khi chữ shot thật sự nói đi LÊN / XUỐNG cầu thang / dốc (shot đứng trên bậc mà chạy ngang thì không)
    slope_said = _said(_UPDOWN, words)
    r = route(conn, pid, scene_id, data)
    a, b, arriving = r["a"] or r["here"], r["b"], r["arriving"]
    if r["here"] is None:
        if slope_said:
            out["warn"].append("shot di chuyển trên cầu thang/dốc mà bối cảnh không có gói 3D / chỗ đứng có độ cao — không viết câu "
                               "hướng lên/xuống (không đoán)")
        return out
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
    # cầu thang: nhãn chỗ đứng 3D, hoặc chữ shot nói đi lên/xuống CẦU THANG (không lấy "steps" lẻ: "takes two steps" trên dốc ≠ cầu thang)
    stairs = bool(_STAIR_WORDS.search(f"{a.get('label') or ''} {b.get('label') or ''}")) or any(
        _STAIR_WORDS.search(m.group(0)) for m in _UPDOWN.finditer(words))
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
    bits = [f"{MARK} {who} goes {way} — from {_label_en(a, up, stairs)} (ground {za:.1f} m) to {_label_en(b, not up, stairs)} "
            f"({zb:.1f} m), "
            f"{abs(dz):.1f} m {'higher' if up else 'lower'}" + (f" (this shot is the end of that run: {who} is arriving at the "
                                                                 f"{'top' if up else 'bottom'})" if arriving else "")]
    conflict = False
    if rel in ("away", "toward"):
        claims_toward, claims_away = _said(_TOWARD, words), _said(_AWAY, words)
        conflict = (rel == "away" and claims_toward and not claims_away) or (rel == "toward" and claims_away and not claims_toward)
    if rel and not conflict:       # 14/10 #30: chữ ↔ nền mâu thuẫn → KHÔNG viết câu quan hệ với máy theo nền sai (chỉ lên/xuống)
        bits.append(rel_words[rel])
    bits.append(f"never going {'down' if up else 'up'}")
    out["sentence"] = "; ".join(bits) + "."
    if rel in ("away", "toward"):
        if conflict:
            from .plate_choice import bearing
            fix = bearing(b["at"], a["at"]) if rel == "away" else bearing(a["at"], b["at"])
            out["warn"].append(
                f"chữ shot nói {who} chạy {'VỀ PHÍA máy' if rel == 'away' else 'RA XA máy / quay lưng'} nhưng máy của nền 3D "
                f"{'đứng sau lưng hướng chạy' if rel == 'away' else 'đứng trước hướng chạy'} ({_label(a)} → {_label(b)}, "
                f"{'lên' if up else 'xuống'} {abs(dz):.1f} m) — KHÔNG viết câu chiều chạy so với máy (chỉ lên/xuống); muốn {'chạy về phía máy' if rel == 'away' else 'máy sau lưng'}"
                f" thì đặt plate_view background ≈ {fix:g}° (hoặc camera_move "
                f"{'pull_out — máy lùi trước mặt trên đường chạy' if rel == 'away' else 'track + chữ máy bám sau'}) rồi render lại nền (0 USD)")
            # (c) 14/10 #30: chữ ↔ nền 3D trái nhau CHẮC CHẮN (chữ nói một chiều, không nói chiều kia; máy render đo ra chiều kia) →
            # CHẶN trước gen (location_pack.plan → index `needs` → ảnh chờ, như plate_choice.view_of), không chỉ VÀNG
            out["needs"] = "hướng chạy trái nền 3D: " + out["warn"][-1] + " — ảnh chờ tới khi chữ shot / hướng nền khớp nhau"
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

