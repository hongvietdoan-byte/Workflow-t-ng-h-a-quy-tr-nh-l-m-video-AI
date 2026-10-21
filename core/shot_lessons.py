"""Bài học duyệt ảnh #24 (người dùng 11/10: "rút kinh nghiệm tính toán, đánh giá tương tự cho các dự án sau") — kiểm bằng CODE, mức
VÀNG (không chặn, không gọi model, 0 USD). Công thức chung cho mọi dự án, không vá theo #24. Tài liệu: knowledge/checks/L4, L6, L8,
L13, A4 (mục "Ca lỗi thật" ghi ca #24).

  movement_gaps(blocking, order)     (2) nhịp có động tác di chuyển → điểm cuối = điểm đầu + quãng; nhịp sau lấy điểm cuối
  layout_drift(old, new, approved)   (3) sửa blocking: vị trí tương đối ở các shot ĐÃ DUYỆT không được đổi theo
  load_ref_beats / ref_coverage      (4) ref động tác/emote có nhiều nhịp + chi tiết nhỏ → kịch bản phủ đủ hoặc ghi rõ lược nhịp nào
  framing_amplitude(data, prompt)    (5) cỡ khung chứa biên độ động tác; nhân vật quá nhỏ thì chi tiết mặt (nước mắt) không thấy
  post_fx_in_image(prompt)           (6) nhiễu / glitch TOÀN KHUNG là hậu kỳ — không nướng vào ảnh khởi đầu video

So chữ: tiếng Việt CÓ DẤU (không bỏ dấu: "bò" ≠ "bỏ", "lùi" ≠ "lũi"), tiếng Anh theo ranh giới từ — không khớp nhầm từ ngắn.
Dữ liệu ref (4) là tệp kèm `<video>.beats.json` cạnh video (cùng thư mục, đường dẫn tuyệt đối hay tương đối đều được — không phụ
thuộc thư mục chạy khi đường dẫn tuyệt đối):
  {"nhip": [{"ten": "om_mat", "mo_ta": "quỳ ôm mặt nấc", "tu_khoa": ["ôm mặt", "hands over her face"], "bien_do": "nua_tren"}, …],
   "chi_tiet": [{"ten": "nuoc_mat", "mo_ta": "dòng mảnh ánh xanh từ kẽ tay", "tu_khoa": ["tears", "nước mắt"]}]}
  bien_do ∈ toan_than (dang tay / cả người) · nua_tren · mat. Shot lược nhịp: scenes.data["ref_luoc"] = [{"nhip": ten, "ly_do": …}].
"""
import json
import math
import os
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence

LEVEL = "vang"
SAME_POS_M = 0.2          # (2) nhịp sau "giữ nguyên" vị trí khi lệch < 0,2 m
END_TOL_M = 0.3           # (2) nhịp sau lấy điểm cuối `den` (lệch ≤ 0,3 m)
EXIT_CLEAR = 0.5          # (2) trườn / bò ra khỏi vật rỗng: cả thân ra ngoài → tâm người cách thành ≥ 0,5·H đứng
DRIFT_M = 0.3             # (3) khoảng cách giữa hai vật trong shot đã duyệt đổi > 0,3 m
MOVED_M = 0.05            # (3) vật coi là "bị đổi chỗ"
SMALL_SHARE = 0.25        # (5) nhân vật < 25 % chiều cao khung: động tác từ ref truyền yếu
DETAIL_SHARE = 0.40       # (5) chi tiết mặt (nước mắt) cần nhân vật ≥ ~40 % chiều cao khung
DEFAULT_H = 1.7
# chiều cao người nộm theo tư thế / đứng (prompt 29 dòng 11–13) — để ước % khung khi chỉ có cỡ cảnh
POSE_FACTOR = {"dung": 1.0, "ngoi": 0.58, "quy": 0.7, "bo": 0.35, "nga_ngua": 0.45, "nam": 0.2}
CLOSE = ("ECU", "CU", "MCU")

# (2) động tác di chuyển — tiếng Việt có dấu, tiếng Anh theo ranh giới từ
_MOVE_VI = ("bò", "trườn", "đi", "lùi", "chạy", "bước", "tiến", "lao", "nhích", "rướn", "lết", "lại gần", "tới gần", "ra khỏi")
_MOVE_EN = ("crawl", "crawls", "crawling", "walk", "walks", "walking", "run", "runs", "running", "step", "steps", "stepping",
            "backs away", "back away", "retreat", "retreats", "approach", "approaches", "slide", "slides", "sliding", "drag", "drags",
            "dragging", "climb out", "climbs out", "moves toward", "move toward", "moves forward", "move forward")
# (5) động tác biên độ lớn (dang tay / cả người)
_WIDE_ACT = re.compile(r"\b(?:arms? (?:spread|flung|thrown|stretched|wide|outstretched|raised wide)|spreads? (?:her|his|their|both) arms|"
                       r"flings? (?:her|his|their|both) arms|(?:arms|hands) (?:wide open|out wide)|outstretched arms)\b|"
                       r"dang (?:rộng )?(?:hai )?tay|giang (?:rộng )?(?:hai )?tay|gục rạp", re.I)
# "tears" danh từ (nước mắt) — không khớp động từ "he tears the poster": cần ngữ cảnh mắt / mặt / chảy (rà 11/10)
_TEAR_CTX = r"(?:eyes?|cheeks?|face|mask|fingers|roll\w*|stream\w*|seep\w*|drip\w*|run\w*|glint\w*|flow\w*|well\w* up)"
_DETAIL = re.compile(rf"\btears?\b(?=[^.;,]{{0,40}}\b{_TEAR_CTX}\b)|\b(?:eyes?|cheeks?|face)\b[^.;,]{{0,30}}\btears?\b|\bteardrops?\b|"
                     r"\btear[- ]?streaks?\b|\bcrying eyes\b|nước mắt|giọt lệ", re.I)
# (6) hiệu ứng màn hình toàn khung — "static camera" / "static composition" / "noise hum" (âm thanh) không phải hiệu ứng (rà 11/10)
_FX = (r"(?:glitch\w*|(?:tv |screen )?static (?:interference|noise|lines?)|tv static|noise(?!\s+(?:hum|sound|audio|level))|distortion|"
       r"interference|signal loss|scan ?lines?|vhs|datamosh\w*|chromatic aberration|rgb split|nhiễu\w*)")
_FRAME = re.compile(r"\b(?:whole|entire|full)[- ](?:frame|image|picture|screen)\b|\bacross the (?:frame|image|screen|picture)\b|"
                    r"\b(?:lost|losing|weak) (?:tv )?signal\b|\bsignal (?:loss|lost|drops?)\b|\bvhs\b|\bscan ?lines?\b|\bdatamosh\w*|"
                    r"\bchromatic aberration\b|\brgb split\b|toàn khung|toàn màn hình|cả màn hình|mất (?:kết nối|sóng)|nhiễu sóng", re.I)
_FX_RX = re.compile(rf"\b{_FX}\b|nhiễu sóng|sọc nhiễu", re.I)
_NEG = re.compile(r"\b(?:no|not|never|without|clean|free of)\b|không", re.I)
_CLAUSE = re.compile(r"[,;:()—–.]")


def _issue(part: str, msg: str, **kw) -> Dict:
    return {"level": "warn", "muc": LEVEL, "part": part, "msg": msg, **kw}


def _has(text: str, words: Iterable[str]) -> Optional[str]:
    low = unicodedata.normalize("NFC", str(text or "")).lower()
    for w in words:
        w = unicodedata.normalize("NFC", w).lower()
        if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", low):
            return w
    return None


# ---- (2) vị trí sau động tác di chuyển ------------------------------------------------------------------------------------------
def beat_order(blocking: Dict, specs: Optional[Sequence[Dict]] = None, rest: bool = True) -> List[str]:
    """Thứ tự nhịp: theo số shot của shot_specs (nhịp xuất hiện lần đầu); rest=True thêm các nhịp còn lại theo thứ tự trong
    blocking.beats (dict không nói thứ tự thời gian — có specs thì nên rest=False)."""
    beats = list((blocking.get("beats") or {}).keys())
    seen: List[str] = []
    for s in sorted([s for s in specs or [] if isinstance(s, dict)], key=lambda s: (s.get("shot") is None, s.get("shot") or 0)):
        n = s.get("nhip")
        if n in beats and n not in seen:
            seen.append(n)
    return seen + ([b for b in beats if b not in seen] if rest or not seen else [])


def _people(blocking: Dict) -> Dict[str, Dict]:
    return {o["key"]: o for o in blocking.get("objects", []) if isinstance(o, dict) and o.get("kind") == "nguoi"}


def _props(blocking: Dict) -> Dict[str, Dict]:
    return {o["key"]: o for o in blocking.get("objects", []) if isinstance(o, dict) and o.get("kind") not in ("nguoi", "moc") and o.get("at")}


def _state(blocking: Dict, beat: str, key: str) -> Optional[Dict]:
    """Người `key` ở nhịp `beat` = objects + ghi đè của nhịp (đúng như stage_solver.beat_raw) — None khi vắng mặt."""
    base = _people(blocking).get(key)
    if base is None:
        return None
    b = (blocking.get("beats") or {}).get(beat)
    ov = (b.get(key) if isinstance(b, dict) else None) or {}
    if not isinstance(ov, dict):                       # nhịp viết sai dạng: coi như không ghi đè (kiểm VÀNG không làm vỡ bộ giải)
        ov = {}
    if ov.get("hidden") or (not ov and base.get("hidden")):
        return None
    st = {k: v for k, v in base.items() if k != "hidden"}
    if "at" in ov and "in" not in ov:
        st.pop("in", None)
    st.update({k: v for k, v in ov.items() if v is not None and k != "hidden"})
    if "in" in ov and ov["in"] is None:
        st.pop("in", None)
    st["_ov"] = ov
    return st


def _xy(st: Dict, props: Dict[str, Dict]) -> Optional[List[float]]:
    if st.get("at"):
        return list(st["at"][:2])
    if st.get("in") in props:
        return list(props[st["in"]]["at"][:2])
    return None


def movement_gaps(blocking: Dict, order: Optional[Sequence[str]] = None) -> List[Dict]:
    """(2) [{muc, part, msg, nhip, vat}] — nhịp có động tác di chuyển (chữ trong `_ly_do` / `hanh_dong`, hoặc rời khỏi vật `in`) mà:
    (a) không ghi điểm cuối `den` và nhịp sau GIỮ NGUYÊN vị trí; (b) ghi `den` mà nhịp sau không lấy `den`; (c) vừa trườn / bò ra
    khỏi vật rỗng mà các nhịp sau vẫn sát thành (< 0,5·H đứng — cả thân người phải ra ngoài)."""
    order = list(order) if order else beat_order(blocking)
    props = _props(blocking)
    out: List[Dict] = []
    for key, person in _people(blocking).items():
        h = float(person.get("H") or DEFAULT_H)
        prev, prev_beat, moving, exit_from = None, None, None, None
        for beat in order:
            st = _state(blocking, beat, key)
            if st is None:
                prev, prev_beat, moving = None, None, None
                continue
            xy = _xy(st, props)
            ov = st.pop("_ov")
            if moving and xy and prev_beat:
                start, end = moving["start"], moving.get("den")
                if end is None and start and math.dist(start, xy) < SAME_POS_M:
                    out.append(_issue("vi_tri_sau_di_chuyen",
                                      f"'{key}': nhịp '{prev_beat}' có động tác di chuyển (“{moving['word']}”) mà nhịp '{beat}' giữ nguyên vị trí "
                                      f"{[round(v, 2) for v in xy]} — vị trí sau động tác = điểm đầu + quãng (ước theo thân người ≈ {h:.1f} m / "
                                      "theo ref). Ghi `den` (điểm cuối) cho nhịp di chuyển và cho nhịp sau lấy `den`; nếu `at` đã là điểm cuối "
                                      "thì ghi `den` = `at` để xác nhận.", nhip=beat, vat=key))
                elif end is not None and math.dist(end[:2], xy) > END_TOL_M:
                    out.append(_issue("vi_tri_sau_di_chuyen",
                                      f"'{key}': nhịp '{prev_beat}' kết thúc ở `den` {list(end[:2])} nhưng nhịp '{beat}' đặt ở "
                                      f"{[round(v, 2) for v in xy]} (lệch {math.dist(end[:2], xy):.2f} m) — nhịp sau phải bắt đầu từ điểm cuối.",
                                      nhip=beat, vat=key))
            if exit_from and xy and not st.get("in"):
                p = props[exit_from]
                gap = math.dist(xy, p["at"][:2]) - float(p.get("d") or 1.0) / 2
                if gap < EXIT_CLEAR * h and "den" not in ov:
                    out.append(_issue("vi_tri_sau_di_chuyen",
                                      f"'{key}': đã trườn / bò ra khỏi '{exit_from}' mà ở nhịp '{beat}' tâm người chỉ cách thành {gap:.2f} m "
                                      f"(< {EXIT_CLEAR:g}·H = {EXIT_CLEAR * h:.2f} m) — cả thân người dài ≈ {h:.1f} m phải nằm ngoài thành; "
                                      "đặt xa hơn hoặc ghi `den` có lý do.", nhip=beat, vat=key))
                    exit_from = None                   # báo một lần cho mỗi lần ra khỏi vật (các nhịp sau thường chép cùng số)
            word = _has(str(ov.get("_ly_do") or "") + " " + str(ov.get("hanh_dong") or ""), _MOVE_VI + _MOVE_EN)
            left = bool(prev and prev.get("in") and not st.get("in"))
            crawl = word in _CRAWL
            near = _near_hollow(xy, props) if crawl and xy and not st.get("in") else None
            if left and crawl:
                exit_from = prev["in"]
            elif near:                                 # điểm đầu đoạn trườn sát thành vật rỗng (r11 #24: 'vừa trườn qua thành giếng')
                exit_from = near
            elif not st.get("in") and exit_from and word is None and xy and math.dist(xy, props[exit_from]["at"][:2]) > 3:
                exit_from = None
            if word or left or "den" in ov:
                moving = {"start": xy, "den": ov.get("den"), "word": word or ("rời khỏi " + str(prev.get("in")) if left else "den")}
            else:
                moving = None
            prev, prev_beat = st, beat
    return out


_CRAWL = ("bò", "trườn", "ra khỏi", "crawl", "crawls", "crawling", "climb out", "climbs out", "drag", "drags", "dragging")


def _near_hollow(xy: Sequence[float], props: Dict[str, Dict]) -> Optional[str]:
    """Vật rỗng (giếng…) mà điểm xy cách thành < 0,5 m — chỗ bắt đầu trườn ra."""
    for k, p in props.items():
        if p.get("hollow") and math.dist(xy, p["at"][:2]) - float(p.get("d") or 1.0) / 2 < 0.5:
            return k
    return None


# ---- (3) sửa blocking: shot đã duyệt giữ bố cục --------------------------------------------------------------------------------
def _positions(blocking: Dict, beat: Optional[str]) -> Dict[str, List[float]]:
    from . import stage_solver as ss
    raw = ss.beat_raw(blocking, beat)
    props = {k: o for k, o in raw.items() if o.get("kind") not in ("nguoi", "moc") and o.get("at")}
    out = {}
    for k, o in raw.items():
        if o.get("kind") == "moc":
            continue
        xy = list(o["at"][:2]) if o.get("at") else (list(props[o["in"]]["at"][:2]) if o.get("in") in props else None)
        if xy:
            out[k] = xy
    return out


def _lateral(cam: Dict, xy: Sequence[float]) -> float:
    """Toạ độ ngang trong khung (dương = bên phải) của điểm sàn xy với máy {at, aim} cùng hệ toạ độ O."""
    cx, cy = cam["at"][:2]
    ax, ay = cam["aim"][:2]
    fx, fy = ax - cx, ay - cy
    n = math.hypot(fx, fy) or 1.0
    return ((xy[0] - cx) * fy - (xy[1] - cy) * fx) / n


def layout_drift(old: Dict, new: Dict, approved: Dict[int, Optional[str]], moved: Optional[Iterable[str]] = None,
                 cams: Optional[Dict[int, Dict]] = None) -> List[Dict]:
    """(3) approved = {số shot đã duyệt: nhịp}. Với mỗi shot: vật KHÁC `moved` bị đổi chỗ; khoảng cách giữa hai vật đổi > 0,3 m;
    trái/phải trong khung đổi (khi có `cams` = {shot: {"at", "aim"}} của máy đã duyệt, cùng hệ O — v2.json best.m). VÀNG + tên shot."""
    moved = set(moved or ())
    out: List[Dict] = []
    for shot, beat in sorted(approved.items()):
        try:
            a, b = _positions(old, beat), _positions(new, beat)
        except (ValueError, KeyError) as e:
            out.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): không dựng được nhịp '{beat}' để so — {e}", shot=shot))
            continue
        keys = [k for k in a if k in b]
        for k in keys:
            if k not in moved and math.dist(a[k], b[k]) > MOVED_M:
                out.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): '{k}' bị đổi chỗ theo ({math.dist(a[k], b[k]):.2f} m) "
                                  "dù không phải vật được sửa — giữ nguyên vị trí cũ hoặc duyệt lại shot này.", shot=shot, vat=k))
        for i, k in enumerate(keys):
            for j in keys[i + 1:]:
                if not ({k, j} & (moved or set(keys))):
                    continue
                d0, d1 = math.dist(a[k], a[j]), math.dist(b[k], b[j])
                if abs(d1 - d0) > DRIFT_M:
                    out.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): khoảng cách '{k}'↔'{j}' đổi {d0:.2f} → {d1:.2f} m — "
                                      "ảnh đã duyệt không còn khớp (sửa lại vị trí hoặc đưa shot về duyệt lại).", shot=shot, vat=f"{k}|{j}"))
                cam = (cams or {}).get(shot)
                if cam and (_lateral(cam, a[k]) - _lateral(cam, a[j])) * (_lateral(cam, b[k]) - _lateral(cam, b[j])) < 0:
                    out.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): '{k}' và '{j}' đổi bên trái/phải trong khung "
                                      "so với ảnh đã duyệt.", shot=shot, vat=f"{k}|{j}"))
    return out


# ---- (4) độ phủ nhịp + chi tiết của ref động tác / emote -------------------------------------------------------------------
def ref_beats_path(video: str) -> str:
    return os.path.splitext(str(video))[0] + ".beats.json"


def load_ref_beats(video: Optional[str]) -> Optional[Dict]:
    """Tệp kèm `<video>.beats.json` — None khi không có video; {"_missing": đường dẫn} khi có video mà chưa ghi nhịp (không im lặng)."""
    if not video:
        return None
    path = ref_beats_path(video)
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {"_missing": path}
    except (OSError, ValueError):
        return {"_missing": path}


def _shot_text(data: Dict) -> str:
    keys = ("image_prompt", "action", "action_peak", "end_state", "blocking", "_ref_text")
    parts = [str(data.get(k) or "") for k in keys]
    for k in ("motion_en", "performance", "tears", "byd"):
        v = data.get(k)
        if v:
            parts.append(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
    return " ".join(parts)


def _skipped(data: Dict) -> set:
    out = set()
    for x in data.get("ref_luoc") or []:
        out.add(str(x.get("nhip") if isinstance(x, dict) else x))
    return out


def ref_coverage(doc: Optional[Dict], data: Dict) -> List[Dict]:
    """(4) Mỗi nhịp / chi tiết của ref mà chữ của shot không nhắc (tu_khoa) và không ghi lược (`ref_luoc`) → VÀNG."""
    if not doc:
        return []
    if doc.get("_missing"):
        return [_issue("phu_nhip_ref", f"Shot gắn video ref động tác mà ref chưa ghi các nhịp + chi tiết nhỏ ({os.path.basename(doc['_missing'])}) "
                                       "— xem ref, liệt kê nhịp (vd quỳ ôm mặt → dang tay gào → gục rạp) và chi tiết (nước mắt, hiệu ứng) để "
                                       "kiểm kịch bản phủ đủ.")]
    items = [it for kind in ("nhip", "chi_tiet") for it in (doc.get(kind) or [])]
    blank = [it for it in items if not isinstance(it, dict) or not str(it.get("ten") or "").strip()
             or not [w for w in it.get("tu_khoa") or [] if str(w).strip()]]
    if not doc.get("nhip") or blank:
        # Mẫu tools/ref_beats.py chưa điền (ô ten/tu_khoa rỗng) — không coi là "đã ghi nhịp" (luật 1: không im lặng)
        return [_issue("phu_nhip_ref", f"Tệp nhịp ref còn {len(blank) or 'không có'} nhịp/chi tiết chưa điền tên + từ khóa — điền xong rồi chạy "
                                       "`tools/ref_beats.py --check` trước khi dùng để kiểm kịch bản phủ đủ.")]
    text, skip = _shot_text(data), _skipped(data)
    out = []
    for kind, label in (("nhip", "nhịp"), ("chi_tiet", "chi tiết")):
        for it in doc.get(kind) or []:
            if not isinstance(it, dict) or it.get("ten") in skip:
                continue
            words = [w for w in it.get("tu_khoa") or [] if str(w).strip()]
            if words and not _has(text, words):
                out.append(_issue("phu_nhip_ref", f"Ref có {label} “{it.get('mo_ta') or it.get('ten')}” mà shot không tả — phủ {label} này hoặc "
                                                  f"ghi `ref_luoc` [{{\"nhip\": \"{it.get('ten')}\", \"ly_do\": …}}] (lược vì sao)."))
    return out


# ---- (5) cỡ khung theo biên độ động tác -------------------------------------------------------------------------------------
def _main_pose(data: Dict) -> Optional[str]:
    from . import shot_intent                      # V3.1 M2.1: đọc BYĐ qua adapter
    byd = shot_intent.byd_of(data) or {}
    for h in byd.get("hanh_dong") or []:
        for nhip in ("dinh", "bat_dau", "ket_thuc"):
            pose = ((h or {}).get(nhip) or {}).get("tu_the")
            if pose:
                return pose
    return None


def frame_share(data: Dict) -> Optional[float]:
    """Ước % chiều cao khung của nhân vật chính = tỉ lệ của cỡ cảnh (stage_grid.FRAMING, người đứng) × hệ số tư thế (BYĐ)."""
    from .stage_grid import FRAMING
    from . import shot_intent                      # V3.1 M2.1: đọc BYĐ qua adapter
    byd = shot_intent.byd_of(data) or {}
    size = data.get("size") or (byd.get("may") or {}).get("co")
    if size not in FRAMING or size in CLOSE:           # cỡ cận cắt theo mặt / ngực — tư thế không làm người nhỏ đi (rà 11/10)
        return None
    return FRAMING[size][1] * POSE_FACTOR.get(_main_pose(data) or "dung", 1.0)


def framing_amplitude(data: Dict, prompt: str = "", doc: Optional[Dict] = None) -> List[Dict]:
    """(5) [VÀNG] (a) động tác biên độ lớn (dang tay / cả người, hoặc ref có nhịp `bien_do: toan_than`) trong cỡ CU / MCU / ECU;
    (b) cần chi tiết mặt (nước mắt) mà nhân vật ước < 40 % chiều cao khung; (c) có ref động tác mà nhân vật ước < 25 % khung."""
    size = data.get("size")
    text = " ".join([str(prompt or ""), str(data.get("action") or ""), str(data.get("action_peak") or "")])
    out = []
    wide_ref = any(isinstance(n, dict) and n.get("bien_do") == "toan_than" for n in (doc or {}).get("nhip") or [])
    m = _WIDE_ACT.search(text)
    if size in CLOSE and (m or wide_ref):
        out.append(_issue("bien_do_khung", f"Cỡ {size} không chứa động tác biên độ lớn (“{m.group(0) if m else 'ref có nhịp toàn thân'}”) — "
                                           "cỡ khung phải chứa biên độ (MS/WS cho nhịp dang tay / cả người), hoặc tách nhịp đó sang shot khác."))
    share = frame_share(data)
    if share is not None:
        detail = _DETAIL.search(text + " " + json.dumps(data.get("tears") or "", ensure_ascii=False))
        if detail and share < DETAIL_SHARE:
            out.append(_issue("bien_do_khung", f"Cần chi tiết mặt (“{detail.group(0)}”) mà nhân vật chỉ ≈ {share * 100:.0f} % chiều cao khung "
                                               f"(cỡ {size}) — chi tiết nhỏ sẽ không thấy; dùng MS/MCU cho nhịp đó hoặc thêm một shot cận."))
        elif (data.get("_ref_motion") or doc) and share < SMALL_SHARE:
            out.append(_issue("bien_do_khung", f"Có video ref động tác mà nhân vật chỉ ≈ {share * 100:.0f} % chiều cao khung (cỡ {size}) — "
                                               "động tác từ ref truyền yếu; chọn cỡ chặt hơn (MLS/MS) để động tác đọc được."))
    return out


# ---- (6) hiệu ứng màn hình là hậu kỳ ---------------------------------------------------------------------------------------------
def post_fx_in_image(prompt: str) -> List[Dict]:
    """(6) Câu có từ nhiễu / glitch / distortion GẮN với toàn khung (màn hình, tín hiệu, VHS, sọc…) và không phủ định → VÀNG. Nhiễu
    cục bộ của nhân vật ("red glitch noise around her wrists" — thiết kế trang phục) và câu phủ định ("no screen noise") không báo."""
    for s in re.split(r"(?<=[.!?;])\s+|\n+", str(prompt or "")):
        for m in _FX_RX.finditer(s):
            a = max((x.end() for x in _CLAUSE.finditer(s, 0, m.start())), default=0)
            b = next((x.start() for x in _CLAUSE.finditer(s, m.end())), len(s))
            clause = s[a:b]
            if _FRAME.search(clause) and not _NEG.search(clause):
                return [_issue("hieu_ung_hau_ky", f"Hiệu ứng màn hình “{clause.strip()[:90]}” trong ảnh khởi đầu video — model video coi nhiễu "
                                                  "là nội dung (giữ / lan cả clip). Bỏ khỏi image_prompt, ghi vào `post_fx` để dựng bằng ffmpeg.")]
    return []


def image_issues(prompt: str, data: Dict) -> List[Dict]:
    """Phần prompt_formula.lint_image gọi: (4) độ phủ ref (khi data có `_ref_beats`), (5), (6). Không bao giờ ném lỗi."""
    try:
        doc = data.get("_ref_beats")
        return ref_coverage(doc, data) + framing_amplitude(data, prompt, doc if isinstance(doc, dict) and not doc.get("_missing") else None) \
            + post_fx_in_image(prompt)
    except Exception as e:  # noqa: BLE001 - một kiểm VÀNG không bao giờ làm mất kế hoạch
        return [_issue("bien_do_khung", f"không kiểm được bài học #24: {type(e).__name__}: {e}")]


# ---- dòng lệnh: so hai lượt sân khấu (3) + kiểm nhịp (2) -------------------------------------------------------------------------
def _load_dir(d: str):
    bl = json.load(open(os.path.join(d, "blocking.json"), encoding="utf-8"))
    try:
        sp = json.load(open(os.path.join(d, "shot_specs.json"), encoding="utf-8"))
        sp = sp.get("shots", sp) if isinstance(sp, dict) else sp
    except (OSError, ValueError):
        sp = []
    cams = {}
    try:
        for s in json.load(open(os.path.join(d, "v2.json"), encoding="utf-8")).get("shots", []):
            if s.get("best"):
                cams[s["shot"]] = {"at": s["best"]["m"]["at"], "aim": s["best"]["m"]["aim"]}
    except (OSError, ValueError, KeyError):
        pass
    return bl, sp, cams


def _cli_source(blocking: Dict, specs: Sequence[Dict], db: Optional[str], project: Optional[int]):
    """Nguồn CLI: idx thật + nhịp khai rõ, không suy từ tên shot hay vị trí trong danh sách.

    BYĐ được ghi từ shot_specs qua core.shot_intent.from_shot_spec:
    scenes.data.byd.truyen.nhip. Specs là ánh xạ bổ sung, không là danh sách shot DB.
    Trả các đoạn nhịp liên tục; thiếu ánh xạ ngắt đoạn để không so vượt shot chưa rõ.
    """
    import sqlite3
    from pathlib import Path

    warnings = []
    explicit = {}
    for spec in specs:
        if isinstance(spec, dict) and isinstance(spec.get("shot"), int):
            beat = spec.get("nhip")
            if beat is not None:
                explicit.setdefault(spec["shot"], set()).add(str(beat))
    if db is None:
        warnings.append(_issue("thu_tu_shot", "thứ tự suy từ shot_specs; chưa đối chiếu CSDL"))
        if project is not None:
            warnings.append(_issue("thu_tu_shot", "--project cần --db để đối chiếu dự án"))
        rows = [(shot, None) for shot in sorted({s["shot"] for s in specs
                if isinstance(s, dict) and isinstance(s.get("shot"), int)})]
        if not rows:
            warnings.append(_issue("thu_tu_shot", "shot_specs thiếu danh sách shot; không kiểm được thứ tự nhịp"))
    else:
        try:
            if project is None:
                raise ValueError("--db cần --project")
            path = Path(db).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"CSDL không tồn tại: {path}")
            # as_uri mã hóa #/% và ổ đĩa Windows; mode=ro không tạo DB/migration.
            conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                if not conn.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise ValueError(f"không có dự án {project} trong CSDL")
                rows = conn.execute("SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx", (project,)).fetchall()
            finally:
                conn.close()
            if not rows:
                raise ValueError(f"dự án {project} chưa có shot trong CSDL")
        except (OSError, sqlite3.Error, ValueError) as e:
            return [], {}, [_issue("thu_tu_shot", f"không kiểm được nguồn CSDL: {e}")]
    segments, current, mapping = [], [], {}
    beats = blocking.get("beats") or {}
    for shot, raw in rows:
        candidates = set(explicit.get(shot, ()))
        invalid = None
        if raw:
            try:
                data = json.loads(raw)
                byd = data.get("byd") or {}
                truyen = byd.get("truyen") or {}
                beat = truyen.get("nhip")
                if beat is not None:
                    candidates.add(str(beat))
            except (ValueError, AttributeError, TypeError):
                invalid = "scenes.data/BYĐ hỏng"
        beat = next(iter(candidates)) if len(candidates) == 1 else None
        reason = invalid or ("thiếu ánh xạ nhịp" if not candidates else
                            "ánh xạ nhịp mâu thuẫn" if len(candidates) > 1 else
                            "nhịp không có trong blocking" if beat not in beats else None)
        if reason:
            warnings.append(_issue("thu_tu_shot", f"shot {shot}: {reason}; không so vượt qua shot này", shot=shot))
            if current:
                segments.append(current)
            current = []
            continue
        mapping[shot] = beat
        if not current or current[-1] != beat:
            current.append(beat)
    if current:
        segments.append(current)
    return segments, mapping, warnings


def main(argv=None) -> int:
    """py -m core.shot_lessons nhip <thư mục lượt>  |  py -m core.shot_lessons drift <lượt cũ> <lượt mới> --approved 8,9 [--moved yeunu]"""
    import argparse
    ap = argparse.ArgumentParser(prog="core.shot_lessons")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("nhip")
    a1.add_argument("dir")
    a2 = sub.add_parser("drift")
    a2.add_argument("old")
    a2.add_argument("new")
    a2.add_argument("--approved", required=True, help="số shot đã duyệt, cách nhau dấu phẩy")
    a2.add_argument("--moved", default="", help="khóa vật được sửa (cách nhau dấu phẩy)")
    for parser in (a1, a2):
        parser.add_argument("--db", help="CSDL chỉ đọc; đường dẫn tương đối theo thư mục chạy")
        parser.add_argument("--project", type=int, help="mã dự án trong CSDL")
    a = ap.parse_args(argv)
    from . import features
    enabled = features.on("shot_lessons_db_order")
    if not enabled and (a.db is not None or a.project is not None):
        print("[VÀNG] cần bật cờ shot_lessons_db_order để dùng --db/--project; chưa kiểm nguồn CSDL")
        print("1 mục VÀNG")
        return 0
    if a.cmd == "nhip":
        bl, sp, _ = _load_dir(a.dir)
        if enabled:
            segments, _, found = _cli_source(bl, sp, a.db, a.project)
            for order in segments:
                found.extend(movement_gaps(bl, order))
        else:
            found = movement_gaps(bl, beat_order(bl, sp, rest=False))
    else:
        old, sp_old, cams = _load_dir(a.old)
        new, sp_new, _ = _load_dir(a.new)
        by_shot = {s["shot"]: s.get("nhip") for s in list(sp_old) + list(sp_new) if isinstance(s, dict) and "shot" in s}
        shots = [int(x) for x in a.approved.split(",") if x.strip()]
        if enabled:
            _, by_shot, found = _cli_source(old, list(sp_old) + list(sp_new), a.db, a.project)
            approved = {}
            for shot in shots:
                if shot not in by_shot:
                    found.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): thiếu ánh xạ nhịp hợp lệ; chưa so bố cục", shot=shot))
                elif by_shot[shot] not in (new.get("beats") or {}):
                    found.append(_issue("bo_cuc_shot_da_duyet", f"shot {shot} (đã duyệt): nhịp không có trong blocking mới; chưa so bố cục", shot=shot))
                else:
                    approved[shot] = by_shot[shot]
            found.extend(layout_drift(old, new, approved, [m for m in a.moved.split(",") if m], cams))
        else:
            found = layout_drift(old, new, {s: by_shot.get(s) for s in shots}, [m for m in a.moved.split(",") if m], cams)
    for f in found:
        print(f"[VÀNG] {f['msg']}")
    print(f"{len(found)} mục VÀNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
