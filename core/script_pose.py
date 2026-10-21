"""Tư thế trong BYĐ (hanh_dong[].<nhịp>.tu_the) ↔ chữ kịch bản gốc — kiểm bằng code, không gọi model (người dùng 14/10: "quan trọng là tư
thế nào đúng theo kịch bản, vì theo kịch bản các tư thế đôi khi rất quan trọng").

Thử D6 #28/#29 shot 3: kịch bản "Kelly đứng sát, núp ở bên trái bức tường keo, ló ra ngó" → Đạo diễn bỏ chữ "đứng" khi chia shot ("Kelly
núp sát bên trái…") và ghi BYĐ `quy` → ảnh + clip cả hai bản ngồi xổm.

    mismatches(script_text, shots) -> [câu tiếng Việt]     shots = [(số shot, dict shot)]

Cách so: tách kịch bản thành câu → vế (dấu phẩy / gạch / chấm phẩy); mỗi shot lấy vế khớp chữ nhất với `action`/`text` của shot (≥ 3 chữ
chung) cộng vế NGAY TRƯỚC nó trong cùng câu (tư thế hay nói trước: "đứng sát, núp…"). Vế đó ghi tư thế (đứng / ngồi / quỳ / nằm / bò) mà
không nhịp BYĐ nào có tư thế ấy → một câu cảnh báo (VÀNG). Ca chắc chắn (kịch bản chỉ "đứng", BYĐ một người toàn quỳ/ngồi, chưa khóa
tay) → fix_standing() sửa BYĐ trước khi gen (cờ script_pose_fix, core/llm_io._script_pose_fix); còn lại người duyệt / Đạo diễn sửa.
"""
import re
import unicodedata
from typing import Dict, List, Sequence, Tuple

# chữ CÓ DẤU (bỏ dấu thì "đứng" trùng "dùng" / "đúng"); "bò" chỉ khi là động từ bò (không "con bò")
POSE_WORDS = {"dung": re.compile(r"(?<!\w)đứng(?!\w)", re.I), "ngoi": re.compile(r"(?<!\w)ngồi(?!\w)", re.I),
              "quy": re.compile(r"(?<!\w)quỳ(?!\w)", re.I), "nam": re.compile(r"(?<!\w)nằm(?!\w)", re.I),
              "bo": re.compile(r"(?<!\w)(?<!con )bò(?!\w)", re.I)}
POSE_VI = {"dung": "đứng", "ngoi": "ngồi", "quy": "quỳ", "nam": "nằm", "bo": "bò", "nga_ngua": "ngã ngửa"}
MIN_SHARED = 3
_SENT = re.compile(r"(?<=[.!?\n])\s+")
_CLAUSE = re.compile(r"\s*[,;—–]\s*|\s+-\s+")
_WORD = re.compile(r"\w+", re.U)


def _words(text: str) -> set:
    return {w.lower() for w in _WORD.findall(text or "") if len(w) >= 2}


def _clauses(script: str) -> List[List[str]]:
    return [[c for c in _CLAUSE.split(s) if c.strip()] for s in _SENT.split(script or "") if s.strip()]


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")     # rà 14/10: decomposed accents (NFD) would miss the accented pose words


def _index(script: str) -> List[List[Tuple[str, set]]]:
    return [[(c, _words(c)) for c in sent] for sent in _clauses(_nfc(script))]


def script_poses(script, shot_text: str) -> Tuple[List[str], str]:
    """(poses the matching script words name, the script words) for one shot; ([], '') when no clause shares ≥ MIN_SHARED words.
    `script` = the script text, or its `_index` (built once per film by `mismatches`)."""
    idx = script if isinstance(script, list) else _index(script)
    want = _words(_nfc(shot_text))
    best, where = 0, None
    for si, sent in enumerate(idx):
        for ci, (_, words) in enumerate(sent):
            n = len(want & words)
            if n > best:
                best, where = n, (si, ci)
    if best < MIN_SHARED or where is None:
        return [], ""
    sent = [c for c, _ in idx[where[0]]]
    words = ", ".join(sent[max(where[1] - 1, 0):where[1] + 1])
    return [k for k, rx in POSE_WORDS.items() if rx.search(words)], words


def byd_poses(data: Dict) -> List[str]:
    from . import shot_intent                      # V3.1 M2.1: đọc BYĐ qua adapter
    byd = shot_intent.byd_of(data) or {}
    out = []
    for h in byd.get("hanh_dong") or []:
        for nhip in ("bat_dau", "dinh", "ket_thuc"):
            st = (h or {}).get(nhip) if isinstance(h, dict) else None
            if isinstance(st, dict) and st.get("tu_the"):
                out.append(st["tu_the"])
    return out


def mismatches(script: str, shots: Sequence[Tuple[int, Dict]]) -> List[str]:
    out, idx = [], _index(script)
    for no, data in shots:
        if not isinstance(data, dict):
            continue
        have = byd_poses(data)
        if not have:
            continue
        said, words = script_poses(idx, " ".join(str(data.get(k) or "") for k in ("action", "text")))
        if said and not set(said) & set(have):
            out.append(f"shot {no}: kịch bản ghi '{POSE_VI[said[0]]}' (\"{words[:90]}\") mà BYĐ ghi "
                       f"{' → '.join(dict.fromkeys(POSE_VI.get(p, p) for p in have))} — sửa tư thế theo kịch bản trước khi gen ảnh")
    return out


# ---- 14/10 (người dùng: "tư thế đúng kịch bản rất quan trọng"): ca CHẮC CHẮN thì code sửa BYĐ trước khi gen, không chỉ báo VÀNG ----
# Chắc chắn = vế kịch bản chỉ ghi "đứng" (không chữ chuyển tư thế: "đứng dậy", "ngồi xuống"…, không phủ định), BYĐ của shot có ĐÚNG MỘT
# người ghi tư thế, mọi nhịp của người đó là quỳ / ngồi (ngã / nằm / bò có thể là cố ý → giữ VÀNG), và người dùng chưa khóa tay `byd`.
FIX_FLAG = "script_pose_fix"
_FIX_FROM = {"quy", "ngoi"}
_SHIFT = re.compile(r"(?<!\w)(?:đứng\s+(?:dậy|lên)|(?:ngồi|quỳ|nằm|ngã|cúi|khom)\s+(?:xuống|thấp|người)|(?:không|chưa|chẳng)\s+đứng)(?!\w)",
                    re.I)
_LOW_EN = re.compile(r"\b(?:crouch\w*|kneel\w*|knelt|squat\w*|sitting|sits?|seated|sat|hunch\w*)\b", re.I)
_LOW_CONTACT = {"dau_goi", "mong"}


def fix_enabled() -> bool:
    from . import features
    return features.on(FIX_FLAG)


def fix_standing(script: str, shots: Sequence[Tuple[int, Dict]]) -> List[str]:
    """Sửa tại chỗ `byd.hanh_dong[].<nhịp>.tu_the` quỳ/ngồi → đứng ở ca chắc chắn (xem trên); trả câu tiếng Việt cho mỗi shot đã sửa.
    Shot mơ hồ không đụng — mismatches() vẫn báo VÀNG."""
    out, idx = [], _index(script)
    for no, data in shots:
        if not isinstance(data, dict) or "byd" in set(data.get("_user_locked") or []):
            continue
        have = byd_poses(data)
        if not have or not set(have) <= _FIX_FROM:
            continue
        said, words = script_poses(idx, " ".join(str(data.get(k) or "") for k in ("action", "text")))
        if said != ["dung"] or _SHIFT.search(words):
            continue
        from . import shot_intent
        people = [h for h in (shot_intent.byd_of(data) or {}).get("hanh_dong") or [] if isinstance(h, dict)
                  and any(isinstance(h.get(n), dict) and h[n].get("tu_the") for n in ("bat_dau", "dinh", "ket_thuc"))]
        if len({h.get("ai") for h in people}) != 1:
            continue
        old = " → ".join(dict.fromkeys(POSE_VI.get(p, p) for p in have))
        why = f"code sửa tư thế theo kịch bản: \"{words[:90]}\" ghi 'đứng', BYĐ cũ {old}"
        for h in people:
            for nhip in ("bat_dau", "dinh", "ket_thuc"):
                st = h.get(nhip)
                if isinstance(st, dict) and st.get("tu_the") in _FIX_FROM:
                    st["tu_the"] = "dung"
                    if isinstance(st.get("cham_dat"), list) and set(st["cham_dat"]) & _LOW_CONTACT:
                        st["cham_dat"] = ["ban_chan"]
            h["sua_tu_the"] = why
        low = sorted({m.group(0).lower() for m in _LOW_EN.finditer(str(data.get("image_prompt") or ""))})
        out.append(f"shot {no}: kịch bản ghi 'đứng' (\"{words[:90]}\") mà BYĐ ghi {old} — code đổi BYĐ thành đứng"
                   + (f"; prompt ảnh của Đạo diễn còn chữ {', '.join(low)} — sửa prompt theo tư thế đứng trước khi gen" if low else ""))
    return out
