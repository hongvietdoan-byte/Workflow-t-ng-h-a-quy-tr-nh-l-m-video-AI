"""Tư thế trong BYĐ (hanh_dong[].<nhịp>.tu_the) ↔ chữ kịch bản gốc — kiểm bằng code, không gọi model (người dùng 14/10: "quan trọng là tư
thế nào đúng theo kịch bản, vì theo kịch bản các tư thế đôi khi rất quan trọng").

Thử D6 #28/#29 shot 3: kịch bản "Kelly đứng sát, núp ở bên trái bức tường keo, ló ra ngó" → Đạo diễn bỏ chữ "đứng" khi chia shot ("Kelly
núp sát bên trái…") và ghi BYĐ `quy` → ảnh + clip cả hai bản ngồi xổm.

    mismatches(script_text, shots) -> [câu tiếng Việt]     shots = [(số shot, dict shot)]

Cách so: tách kịch bản thành câu → vế (dấu phẩy / gạch / chấm phẩy); mỗi shot lấy vế khớp chữ nhất với `action`/`text` của shot (≥ 3 chữ
chung) cộng vế NGAY TRƯỚC nó trong cùng câu (tư thế hay nói trước: "đứng sát, núp…"). Vế đó ghi tư thế (đứng / ngồi / quỳ / nằm / bò) mà
không nhịp BYĐ nào có tư thế ấy → một câu cảnh báo. Chỉ báo (VÀNG), người duyệt / Đạo diễn sửa.
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
    byd = data.get("byd") if isinstance(data.get("byd"), dict) else {}
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
