"""Bất biến khâu 3D theo GỐC R1 (C-3D-GOC-B, người dùng 22/10: "sửa GỐC để đặt chỗ khác / cách khác không lặp lại"; "giữ liên kết chặt").

Gốc R1 (sổ lỗi V31-GOC1 ← P31-G46 ← G41/G43/G44/G45/G47/G50, G1): vị trí vật / người xuyên các shot chỉ tả bằng CHỮ riêng từng shot, mỗi ảnh
gen độc lập → model đặt lại mỗi lần; vá chữ shot này làm lệch shot kia. Nguồn sự thật DUY NHẤT của vị trí = bản đồ cảnh `core/world_map`
(D06: 3D / 2D / tương đối / UNKNOWN). Ở đây không có toạ độ thứ hai: mọi bất biến đọc map + máy của shot qua `world_map` (frame_xy,
position_sentence, side_review) và cùng hướng máy của `core/layout_facts` (same_view) — nên đúng cho MỌI chỗ đặt máy, mọi cảnh.

  R1-MAP          cảnh ≥ 2 shot mà chưa có map còn hiệu lực / map UNKNOWN → KHÔNG RÕ + lý do (không đoán vị trí)
  R1-SIDE         chữ của shot (image_prompt / blocking / motion) nói trái/phải NGƯỢC chỗ map đặt người/vật theo máy shot đó
                  → VÀNG + câu vị trí sinh từ map (world_map.position_sentence)
  R1-AXIS-JUMP    cùng vật đổi bên khung giữa hai shot LIỀN NHAU mà hai máy cùng phía trục (yaw lệch ≤ layout_facts.SAME_VIEW_YAW_DEG)
                  → VÀNG (G44 26↔27); hai máy ngược trục thì đổi bên là đúng, không báo
  R1-TRAVEL       chữ tả hướng đi (vào nền / về phía máy / sang trái-phải khung) + "về phía X" / "rời khỏi X": X trên map phải nằm
                  đúng phía hướng đi (G41 chạy "ra xa máy" vào chỗ địch, G43 "rời khỏi cái xác" mà đi về phía xác) → VÀNG
  R1-PROP-SCENE   khối giữ chỗ trong stage_camera mang từ "cảnh N" khác mà bản đồ / BYĐ cảnh này không có vật đó (G1 xác bay cảnh 6 ở
                  cảnh 8 thực tại) → VÀNG; vật cố định cùng sân khấu có ở cảnh này (stage_auto cố ý mang sang) → không báo

Thuần Python, 0 USD, chỉ đọc (không ghi map, không sửa prompt, không đổi gói gửi, không chặn gen). Phát hiện cùng dạng
core/camera_invariants: {"code", "level": vang | khong_ro, "errors": [mã sổ lỗi], "msg", "fix", "numbers"}.
"""
import json
import math
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import layout_facts, world_map

VANG, KHONG_RO = "vang", "khong_ro"
ERR_ROOT = ["V31-GOC1", "P31-G46"]
TEXT_FIELDS = ("image_prompt", "blocking", "action", "motion_en")
AHEAD_COS = math.cos(math.radians(60))     # X nằm "phía trước hướng đi" khi lệch ≤ 60° so với hướng đi
NO_SCENE_KEY = "?"                          # project_report: nhóm shot thiếu story_scene


def _f(code: str, errors: Sequence[str], msg: str, fix: str = "", level: str = VANG, **numbers) -> Dict:
    return {"code": code, "level": level, "errors": list(errors), "msg": msg, "fix": fix,
            "numbers": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in numbers.items()}}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "")).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _text(data: Dict, field: str) -> str:
    v = data.get(field)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values() if isinstance(x, str))
    return str(v or "")


def _camera(data: Dict) -> Optional[Dict]:
    """Máy của shot cho map 3D/2D: stage_camera CHỈ khi cờ stage_camera bật (cùng điều kiện layout_facts / ảnh / QC)."""
    from . import features
    sc = data.get("stage_camera")
    return sc if isinstance(sc, dict) and features.on("stage_camera") else None


def _yaw(cam: Optional[Dict]) -> Optional[float]:
    try:
        (x0, y0), (x1, y1) = cam["location"][:2], cam["look_at"][:2]
    except (TypeError, KeyError, ValueError):
        return None
    if abs(x1 - x0) + abs(y1 - y0) < 1e-6:
        return None
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def same_side_of_axis(cam_a: Optional[Dict], cam_b: Optional[Dict]) -> Optional[bool]:
    """Cùng phía trục (trái/phải giữ nguyên)? Cùng ngưỡng với layout_facts.same_view; thiếu máy → None (không đoán)."""
    ya, yb = _yaw(cam_a), _yaw(cam_b)
    if ya is None or yb is None:
        return None
    return abs((ya - yb + 180) % 360 - 180) <= layout_facts.SAME_VIEW_YAW_DEG


# ---- tra thực thể theo tên ---------------------------------------------------------------------------------------------------
def _names(e: Dict) -> List[str]:
    out = [e.get("entity_id"), e.get("label")]
    return [_plain(n) for n in out if n]


def find_entity(m: Dict, name: str, shot) -> Optional[Dict]:
    """Thực thể có hiệu lực ở shot mà tên (không dấu, không hoa) trùng entity_id / nhãn; hoặc nhãn ≥ 3 ký tự xuất hiện NGUYÊN TỪ trong tên
    (vd "the corpse" ↔ nhãn "corpse"). Nhiều thực thể cùng khớp → không chọn (None), không đoán."""
    want = _plain(name).strip()
    if not want:
        return None
    ents = world_map.entities_at(m, shot)
    exact = [e for e in ents if want in _names(e)]
    if exact:
        return exact[0]
    part = [e for e in ents if any(len(n) >= 3 and re.search(r"\b" + re.escape(n) + r"\b", want) for n in _names(e))]
    return part[0] if len(part) == 1 else None


def _frame_of(m: Dict, e: Dict, camera: Optional[Dict]) -> Optional[Tuple[float, float]]:
    cam = world_map._cam_rel(m, camera)
    xyz = (e.get("transform") or {}).get("xyz")
    if cam is None or not xyz:
        return None
    return world_map.frame_xy(cam[0], cam[1], xyz[:2])


# ---- R1-MAP ----------------------------------------------------------------------------------------------------------------
def check_map(m: Optional[Dict], story_scene, n_shots: int) -> List[Dict]:
    if n_shots < 2:
        return []
    if not m:
        return [_f("R1-MAP", ERR_ROOT, f"Cảnh {story_scene} có {n_shots} shot nhưng chưa có bản đồ cảnh (world map) — vị trí người/vật "
                   "chỉ nằm trong chữ từng shot, mỗi ảnh sẽ đặt lại", "Dựng map: core.world_map.refresh (cờ world_map, 0 USD) "
                   "hoặc vẽ sơ đồ 2D world/plan2d_<cảnh>.json", level=KHONG_RO, scene=str(story_scene), shots=n_shots)]
    if m.get("invalidated"):
        return [_f("R1-MAP", ERR_ROOT, f"Bản đồ cảnh {story_scene} đã cũ ({(m['invalidated'] or {}).get('why')}) — không dùng số cũ",
                   "Dựng lại map", level=KHONG_RO, scene=str(story_scene))]
    if m.get("kind") == "unknown":
        return [_f("R1-MAP", ERR_ROOT, f"Bản đồ cảnh {story_scene} UNKNOWN: {m.get('why')}", "Dựng sân khấu 3D / vẽ sơ đồ 2D",
                   level=KHONG_RO, scene=str(story_scene))]
    return []


# ---- R1-SIDE ---------------------------------------------------------------------------------------------------------------
def check_text_sides(m: Dict, shot, texts: Dict[str, str], camera: Optional[Dict]) -> List[Dict]:
    out = []
    for field, text in texts.items():
        if not text:
            continue
        r = world_map.side_review(m, shot, text, camera)
        for mm in r["mismatches"]:
            out.append(_f("R1-SIDE", ERR_ROOT + ["P31-G44"], f"shot {shot} · {field}: chữ đặt {mm['entity']} NGƯỢC bên so với bản đồ "
                          f"cảnh (map: {mm['map']} theo máy shot này) — «{mm['text'][:80]}»",
                          r["suggested"] or "", field=field, entity=mm["entity"], map_side=mm["map"]))
    return out


# ---- R1-AXIS-JUMP ----------------------------------------------------------------------------------------------------------
def check_axis_jumps(m: Dict, shots: List[Dict]) -> List[Dict]:
    """shots: [{"shot", "camera"}] theo thứ tự. Cùng thực thể đổi trái ↔ phải giữa hai shot liền nhau cùng phía trục → VÀNG."""
    out = []
    placed = []
    for s in shots:
        _, prov = world_map.position_sentence(m, s["shot"], s.get("camera"))
        placed.append(prov.get("placed") or {})
    for i in range(1, len(shots)):
        a, b = shots[i - 1], shots[i]
        same = same_side_of_axis(a.get("camera"), b.get("camera"))
        if same is not True:
            continue
        for eid, side in placed[i].items():
            before = placed[i - 1].get(eid)
            if {before, side} == {"left", "right"}:
                out.append(_f("R1-AXIS-JUMP", ERR_ROOT + ["P31-G44"], f"{eid}: shot {a['shot']} ở {before} khung, shot {b['shot']} ở {side} "
                              "khung mà hai máy cùng phía trục — nhảy trục (người xem thấy vật đổi chỗ)",
                              "Dời máy shot sau sang cùng phía của shot trước, hoặc khai đổi trục có chủ ý (máy vượt trục trong khung)",
                              entity=eid, shot_a=a["shot"], shot_b=b["shot"], side_a=before, side_b=side))
    return out


# ---- R1-TRAVEL -------------------------------------------------------------------------------------------------------------
_DIRS = [  # (mẫu không dấu, (ngang, sâu))
    (r"\b(?:away from (?:the )?camera|into the background|deeper into|toward(?:s)? the background|ra xa may|vao nen|di sau vao)\b", (0.0, 1.0)),
    (r"\b(?:toward(?:s)? (?:the )?camera|toward(?:s)? the lens|into the foreground|ve phia may|ra tien canh)\b", (0.0, -1.0)),
    (r"\b(?:(?:to|toward(?:s)?|exits?|exiting|leaving|out of) (?:the )?frame[- ]left|off (?:to )?(?:the )?left|sang trai khung|ra khung trai)\b",
     (-1.0, 0.0)),
    (r"\b(?:(?:to|toward(?:s)?|exits?|exiting|leaving|out of) (?:the )?frame[- ]right|off (?:to )?(?:the )?right|sang phai khung|ra khung phai)\b",
     (1.0, 0.0)),
]
# "về phía X" chỉ là hướng ĐI khi có động từ di chuyển ngay trước (nhìn / ngắm / chĩa về phía X không phải đi — rà 22/10)
_MOVE = r"\b(?:walk(?:s|ing)?|run(?:s|ning)?|mov(?:es|ing)|head(?:s|ing)?|go(?:es|ing)?|stride(?:s)?|striding|rush(?:es|ing)?|sprint(?:s|ing)?|" \
        r"di|chay|tien|buoc|lao)"
_TOWARD = re.compile(_MOVE + r"\s+(?:straight\s+|back\s+|slowly\s+|quickly\s+)?(?:toward(?:s)?|ve phia|ve|lai gan|towards?)\s+(?:the\s+)?([a-z0-9 _-]{3,40})"
                     r"|\b(?:approach(?:es|ing)?|tien ve|di ve)\s+(?:the\s+)?([a-z0-9 _-]{3,40})")
_AWAY = re.compile(r"\b(?:away from|leav(?:es|ing)|roi khoi|bo lai|tranh xa|quay lung voi)\s+(?:the\s+)?([a-z0-9 _-]{3,40})")
_CUT = re.compile(r"\b(?:and|while|then|as|into|in|to|toward|towards|at|on|from|with|exiting|va|roi|trong khi|vao|ve|di|chay|sau|ra)\b|[,.;]")
_STOP = re.compile(r"\b(?:camera|lens|frame|background|foreground|may|nen|khung)\b")
_SENT = re.compile(r"(?<=[.!?;])\s+|\n+")


def travel_direction(text: str) -> Optional[Tuple[float, float]]:
    t = _plain(text)
    for pat, d in _DIRS:
        if re.search(pat, t):
            return d
    return None


def _targets(text: str, rx) -> List[str]:
    out = []
    for mt in rx.finditer(_plain(text)):
        grp = next((g for g in mt.groups() if g), "")
        name = _CUT.split(grp)[0].strip()
        if name and not _STOP.search(name):
            out.append(name)
    return out


def _mover_of(sentence: str, cast: Sequence[str]) -> Optional[str]:
    """Người đi trong CÂU: tên nhân vật xuất hiện sớm nhất trong câu; không ai được nêu → chỉ khi shot có đúng một người."""
    t = _plain(sentence)
    hits = sorted((t.find(_plain(c)), c) for c in cast if _plain(c) and _plain(c) in t)
    if hits:
        return hits[0][1]
    return cast[0] if len(cast) == 1 else None


def check_travel(m: Dict, shot, cast: Sequence[str], text: str, camera: Optional[Dict]) -> List[Dict]:
    """Từng CÂU: hướng đi trong câu ↔ vị trí trên map của thứ được nhắc 'đi về phía' / 'rời khỏi' trong CÙNG câu. Không suy được hướng
    / người đi → không phán; thiếu toạ độ của thứ được nhắc → KHÔNG RÕ + lý do."""
    if isinstance(cast, str):
        cast = [cast]
    out = []
    for sent in (x for x in _SENT.split(text or "") if x.strip()):
        d = travel_direction(sent)
        toward, away = _targets(sent, _TOWARD), _targets(sent, _AWAY)
        mover = _mover_of(sent, list(cast or []))
        if d is None or not (toward or away) or not mover:
            continue
        out += _travel_one(m, shot, mover, d, toward, away, camera)
    return out


def _travel_one(m, shot, mover, d, toward, away, camera) -> List[Dict]:
    who = find_entity(m, mover, shot)
    p_who = _frame_of(m, who, camera) if who else None
    out = []
    for name, want_ahead in [(n, True) for n in toward] + [(n, False) for n in away]:
        tgt = find_entity(m, name, shot)
        p_t = _frame_of(m, tgt, camera) if tgt else None
        if p_who is None or p_t is None:
            out.append(_f("R1-TRAVEL", ERR_ROOT, f"shot {shot}: chữ tả {mover} đi {'về phía' if want_ahead else 'rời khỏi'} «{name}» nhưng "
                          "map / máy (cần map 3D có gốc O + máy 3D của shot) thiếu toạ độ của " + (mover if p_who is None else name)
                          + " — không kiểm được hướng đi", "Thêm thực thể vào map (blocking sân khấu) hoặc máy của shot", level=KHONG_RO,
                          target=name))
            continue
        vx, vy = p_t[0] - p_who[0], p_t[1] - p_who[1]
        n = math.hypot(vx, vy)
        if n < 0.3:
            continue
        cos = (vx * d[0] + vy * d[1]) / n
        ahead = cos >= AHEAD_COS
        if (want_ahead and cos < 0) or (not want_ahead and ahead):
            where = "phía trước hướng đi" if ahead else "ngược hướng đi"
            out.append(_f("R1-TRAVEL", ERR_ROOT + (["P31-G43"] if not want_ahead else ["P31-G41"]),
                          f"shot {shot}: chữ tả {mover} đi {'về phía' if want_ahead else 'rời khỏi'} {tgt.get('label') or tgt['entity_id']} "
                          f"nhưng theo map + máy shot này nó ở {where} (cos {cos:+.2f}) — clip sẽ đi sai hướng",
                          "Đổi hướng đi trong chữ cho khớp map (vd sang trái/phải khung), hoặc dời máy / vật trên map",
                          target=tgt["entity_id"], cos=cos, dx=vx, dy=vy))
    return out


# ---- R1-PROP-SCENE (G1) ----------------------------------------------------------------------------------------------------
_SCENE_N = re.compile(r"\bcanh\s*(\d+)\b")


def check_props_scene(stage_camera: Optional[Dict], story_scene, known: Optional[Iterable[str]] = None) -> List[Dict]:
    """Khối giữ chỗ mang từ cảnh N khác: stage_auto CỐ Ý mang vật cố định của cảnh trước cùng sân khấu (rà 15/10) — chỉ đúng khi vật đó
    CÓ ở cảnh này (bản đồ cảnh / BYĐ / nhân vật của shot, `known`). Không có trong `known` → VÀNG (G1: xác bay cảnh 6 ở cảnh 8 thực tại);
    `known` rỗng (không map, không BYĐ) → KHÔNG RÕ, không đoán."""
    names = {_plain(k) for k in known or [] if k}
    out = []
    for p in (stage_camera or {}).get("props") or []:
        src = _plain((p or {}).get("source") or "")
        mt = _SCENE_N.search(src)
        if not mt or str(mt.group(1)) == str(story_scene):
            continue
        label = p.get("label") or p.get("name") or "?"
        if _plain(label) in names or any(len(n) >= 3 and re.search(r"\b" + re.escape(n) + r"\b", _plain(label)) for n in names):
            continue
        out.append(_f("R1-PROP-SCENE", ERR_ROOT + ["P31-G1"],
                      f"Khối giữ chỗ «{label}» mang từ cảnh {mt.group(1)} vào máy của shot cảnh {story_scene} "
                      + ("mà bản đồ / BYĐ cảnh này không có nó — sẽ render vào nền cảnh khác" if names else
                         "— cảnh này chưa có bản đồ / BYĐ để biết vật có thật ở đây không"),
                      "Bỏ khối khỏi stage_camera.props của shot này, hoặc khai vật ở cảnh này trên map / BYĐ",
                      level=VANG if names else KHONG_RO, prop=label, from_scene=mt.group(1)))
    return out


def _known_names(m: Optional[Dict], shot, data: Dict) -> List[str]:
    names = [str(c) for c in data.get("characters") or []]
    if m and not m.get("invalidated"):
        for e in world_map.entities_at(m, shot):
            names += [e.get("entity_id") or "", e.get("label") or ""]
    from . import shot_intent                            # BYĐ v1 / v2 qua MỘT bộ đọc (M2.1) — `vat` v1 = chuỗi, v2 = {vat, kho_id…}
    byd = shot_intent.byd_of(data) or {}
    for c in byd.get("thanh_phan") or []:
        if isinstance(c, dict) and c.get("vat"):
            names.append(str(c["vat"]))
    for v in shot_intent.vat_items(byd):
        if isinstance(v, dict) and v.get("vat"):
            names.append(str(v["vat"]))
    return [n for n in names if n]


# ---- gộp cho một cảnh / một dự án --------------------------------------------------------------------------------------------
def scene_report(m: Optional[Dict], story_scene, shots: List[Dict]) -> List[Dict]:
    """shots: [{"shot" (= scenes.idx, cùng số với valid_from / valid_to của map), "data"}] theo thứ tự. Một danh sách cho cả cảnh."""
    out = check_map(m, story_scene, len(shots))
    for s in shots:
        d = s["data"] or {}
        if _camera(d):
            out += check_props_scene(d.get("stage_camera"), story_scene, _known_names(m, s["shot"], d))
    if any(f["code"] == "R1-MAP" for f in out):
        return out
    seq = []
    for s in shots:
        d, cam = s["data"] or {}, _camera(s["data"] or {})
        texts = {f: _text(d, f) for f in TEXT_FIELDS}
        out += check_text_sides(m, s["shot"], texts, cam)
        cast = [str(c) for c in d.get("characters") or []]
        motion = " ".join(texts[f] for f in ("blocking", "action", "motion_en") if texts[f])
        out += check_travel(m, s["shot"], cast, motion, cam)
        seq.append({"shot": s["shot"], "camera": cam})
    out += check_axis_jumps(m, seq)
    return out


def project_report(conn, pid: int, data_dir: str) -> Dict:
    """{"scenes": {cảnh: [phát hiện]}, "n": số phát hiện VÀNG}. Đọc CSDL + map tệp; không ghi gì. Số shot = scenes.idx (số của map)."""
    by_scene: Dict[str, List[Dict]] = {}
    no_scene: List[int] = []
    for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall():
        d = json.loads(r["data"] or "{}")
        if d.get("story_scene") in (None, ""):
            no_scene.append(r["idx"])                    # không thuộc map nào: báo dưới, không bỏ qua im lặng (luật 1)
            continue
        by_scene.setdefault(str(d["story_scene"]), []).append({"shot": r["idx"], "data": d})
    out = {}
    if no_scene:
        out[NO_SCENE_KEY] = [_f("R1-MAP", ERR_ROOT, f"{len(no_scene)} shot thiếu story_scene (shot {', '.join(map(str, no_scene[:12]))}"
                                f"{'…' if len(no_scene) > 12 else ''}) — không biết thuộc bản đồ cảnh nào, không kiểm vị trí",
                                "Khai story_scene cho shot (Đạo diễn / kịch bản)", level=KHONG_RO, shots=no_scene)]
    for sc, shots in by_scene.items():
        shots.sort(key=lambda s: s["shot"])
        try:
            m = world_map.load(data_dir, pid, sc)
        except (OSError, ValueError, TypeError) as e:
            out[sc] = [_f("R1-MAP", ERR_ROOT, f"Bản đồ cảnh {sc} đọc lỗi ({type(e).__name__}) — không kiểm vị trí", "Dựng lại map",
                          level=KHONG_RO, scene=sc)]
            continue
        out[sc] = scene_report(m, sc, shots)
    return {"scenes": out, "n": sum(1 for v in out.values() for f in v if f["level"] == VANG)}
