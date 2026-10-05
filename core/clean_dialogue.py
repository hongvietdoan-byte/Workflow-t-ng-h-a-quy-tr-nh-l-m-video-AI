"""S14.41 (chấm phiếu 05c, 05/10): lời thoại sạch — kịch bản Biên kịch không có xưng hô mày/tao, nói tục, chửi thề (0 USD).

Danh sách từ ở data/clean_dialogue_words.json (sửa tay được). Quy tắc bắt:
  - pronouns / swears: so CÓ DẤU, đúng chữ (NFC, chữ thường) — vì bỏ dấu thì 'tao' trùng 'tạo/táo', 'mày' trùng 'máy/may'.
  - unaccented: cụm KHÔNG DẤU đã chọn sao cho không trùng từ sạch ('dit me'…), so trên chữ thường nguyên bản.
  - short_forms: viết tắt ('đm', 'vcl'…), không phân biệt hoa thường.
  - Ranh giới từ: chữ, số hoặc gạch nối sát bên thì không bắt ('Vlog', 'DM-2', 'tạo').
  - allow: cụm sạch chứa từ bị cấm ('mày mò', 'lông mày') bị xoá khỏi chữ trước khi bắt.
Thiếu / hỏng file danh sách → WordListError (luật 1: không im lặng cho qua)."""
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Dict, List

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clean_dialogue_words.json")
KINDS = ("pronouns", "swears", "unaccented", "short_forms")
LABEL = {"pronouns": "xưng hô mày/tao", "swears": "nói tục / chửi thề", "unaccented": "nói tục (không dấu)", "short_forms": "viết tắt tục"}


class WordListError(RuntimeError):
    """The word list is missing or unreadable — the check cannot run, said instead of passing."""


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def _rx(words: List[str]):
    words = sorted({_norm(w).strip() for w in words if str(w).strip()}, key=len, reverse=True)
    if not words:
        return None
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in words) + r")(?![\w-])")


@lru_cache(maxsize=4)
def load(path: str = PATH) -> Dict:
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise WordListError(f"không đọc được danh sách từ lời thoại sạch {path}: {e}") from e
    if not isinstance(data, dict) or not any(data.get(k) for k in KINDS):
        raise WordListError(f"danh sách từ lời thoại sạch {path} trống")
    return {"rx": {k: _rx(data.get(k) or []) for k in KINDS},
            "allow": _rx(data.get("allow") or [])}


def find(text: str, path: str = PATH) -> List[Dict]:
    """[{word, kind, label}] in order of appearance, each word once."""
    lst = load(path)
    body = _norm(text)
    if lst["allow"]:
        body = lst["allow"].sub(lambda m: " " * len(m.group(0)), body)
    hits = []
    for kind in KINDS:
        rx = lst["rx"][kind]
        if rx:
            hits += [(m.start(), re.sub(r"\s+", " ", m.group(1)), kind) for m in rx.finditer(body)]
    out, seen = [], set()
    for _, word, kind in sorted(hits):
        if word not in seen:
            seen.add(word)
            out.append({"word": word, "kind": kind, "label": LABEL[kind]})
    return out


def describe(hits: List[Dict]) -> str:
    return "lời thoại không sạch (" + ", ".join(f"'{h['word']}' — {h['label']}" for h in hits) + \
           ") — viết lại bằng từ sạch (tớ/cậu, tôi/bạn, tên riêng), giữ cá tính bằng giọng điệu"
