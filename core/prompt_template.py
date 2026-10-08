"""Khuôn ghép prompt (F1-C, 09/10/2026) — docs/CONG_THUC_PROMPT_F0_NHAP_2026-10-09.md mục 3–4.

Prompt ảnh: danh sách PHẦN có tên theo đúng thứ tự công thức (phong cách → khung → nhân vật + hành động (+ câu sửa) → nền → ánh sáng
→ khóa/luật → chốt chất lượng); mỗi phần tự đóng câu (#22 lỗi 4: "not blurred background KELLY KL keeps…" — câu khóa ghép vào cuối
không có dấu chấm, model đọc thành một câu). Câu trùng nghĩa bỏ một lần: mệnh đề phong cách của Đạo diễn khi câu look của dự án đã nói;
mệnh đề chốt chất lượng ("everything in focus", "not blurred background") gom về phần cuối, một lần.

Motion nhóm Seedance: câu lặp giữa các shot (trang phục, nền — #22 lỗi 5: ~1.200 ký tự lặp ở motion 7–9) viết MỘT lần sau phần hành động.
Không gọi model, không đọc data/.
"""
import re
from typing import Iterable, List, Sequence, Tuple

IMAGE_PARTS = ("phong_cach", "khung_hinh", "hanh_dong", "sua", "nen", "anh_sang", "khoa_luat", "chot_chat_luong")

# Mệnh đề CHỈ gồm chữ phong cách — câu look FF_INGAME (looks.LOOKS) đã nói đủ; so trọn mệnh đề (fullmatch), không cắt giữa câu.
_STYLE_CLAUSE = re.compile(
    r"(?:garena )?free fire(?: in-game)?(?: 3d)?(?: (?:character|game))?(?: (?:render|art|look))?(?: style)?"
    r"|in-game(?: 3d)? (?:render|art|look)(?: style)?|3d (?:game )?render(?: style)?|game render(?: style)?"
    r"|stylized(?: mobile-game)? proportions|moderate texture detail|clear gameplay lighting", re.I)
# Mệnh đề chốt chất lượng: khóa = nghĩa (hai cách viết cùng nghĩa → một khóa).
_QUALITY = ((re.compile(r"everything (?:is )?(?:sharp(?:ly)? )?in (?:sharp )?focus", re.I), "focus_all"),
            (re.compile(r"(?:the )?background (?:is )?(?:sharp|in focus)|(?:not|no) blurr?(?:ed|y) background|sharp background", re.I),
             "focus_bg"),
            (re.compile(r"(?:not|no) (?:a )?(?:cinematic )?movie still", re.I), "movie_still"),
            (re.compile(r"no depth[- ]of[- ]field(?: blur)?", re.I), "dof"))


def close(text: str) -> str:
    """One part as closed sentence(s): trimmed, ending with . ! ? (or a closing quote after one)."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t:
        return ""
    t = t.rstrip(" ,;:—-")
    return t if re.search(r"[.!?][\"'”)]?$", t) else t + "."


def sentences(text: str) -> List[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if s.strip()]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower()).rstrip(" .!?")


def join(parts: Iterable[str]) -> str:
    """Parts in order, each closed, exact repeated sentences (case/space-insensitive) said once."""
    seen, out = set(), []
    for part in parts:
        kept = []
        for s in sentences(close(part)):
            k = _norm(s)
            if k and k in seen:
                continue
            seen.add(k)
            kept.append(s)
        if kept:
            out.append(" ".join(kept))
    return " ".join(out)


def quality_keys(text: str) -> set:
    return {key for rx, key in _QUALITY if rx.search(text or "")}


def split_director(text: str, drop_style: bool, move_quality: bool) -> Tuple[str, List[str]]:
    """(the Director's text without the clauses said elsewhere, the quality clauses taken out in order). Only whole clauses
    (between , ; and the sentence end) that consist of style / quality words go; everything else stays word for word."""
    if not (drop_style or move_quality):
        return text or "", []
    out_sents, quality = [], []
    for sent in sentences(text):
        end = re.search(r"[.!?]+[\"'”)]?$", sent)
        tail = end.group(0) if end else ""
        body = sent[: len(sent) - len(tail)] if tail else sent
        bits = re.split(r"([,;])", body)
        keep: List[str] = []
        for i in range(0, len(bits), 2):
            clause = bits[i].strip()
            sep = bits[i + 1] if i + 1 < len(bits) else ""
            if drop_style and clause and _STYLE_CLAUSE.fullmatch(clause):
                continue
            if move_quality and clause and any(rx.fullmatch(clause) for rx, _k in _QUALITY):
                quality.append(clause)
                continue
            if clause:
                keep += [clause, sep]
        while keep and keep[-1] in (",", ";", ""):
            keep.pop()
        rebuilt = ""
        for piece in keep:
            rebuilt += piece if piece in (",", ";") else ((" " if rebuilt else "") + piece)
        if rebuilt.strip():
            out_sents.append(rebuilt.strip() + (tail or "."))
    return " ".join(out_sents), quality


def quality_part(look_quality: str, director_quality: Sequence[str]) -> str:
    """The closing quality part: the Director's clauses whose meaning the look sentence does not already say (once each), then the
    look's own quality sentence."""
    have, kept = quality_keys(look_quality), []
    for c in director_quality:
        keys = quality_keys(c)
        if keys and keys <= have:
            continue
        have |= keys
        kept.append(c.strip())
    head = ", ".join(kept)
    if not head:
        return close(look_quality)
    if not look_quality.strip():
        return close(head[0].upper() + head[1:])
    return close(f"{look_quality.strip().rstrip('.')}; {head}")      # the Director's words kept as written, inside one sentence


# ---- motion nhóm --------------------------------------------------------------------------------------------------------
def shared_sentences(texts: Sequence[str], min_len: int = 25) -> Tuple[List[str], List[Tuple[str, List[int]]]]:
    """(each shot's text without the sentences repeated in other shots, [(sentence, [shot numbers])] in first-seen order).
    A sentence found word for word (case/space-insensitive) in ≥ 2 shots is said once for those shots. Short sentences stay."""
    per = [sentences(t) for t in texts]
    where: dict = {}
    first: dict = {}
    for i, ss in enumerate(per, 1):
        for s in ss:
            k = _norm(s)
            if len(k) < min_len:
                continue
            first.setdefault(k, s)
            if i not in where.setdefault(k, []):
                where[k].append(i)
    common = {k for k, shots in where.items() if len(shots) >= 2}
    stripped = [" ".join(s for s in ss if _norm(s) not in common) for ss in per]
    return stripped, [(close(first[k]), where[k]) for k in where if k in common]


def shots_label(numbers: Sequence[int], n: int) -> str:
    if len(numbers) == n:
        return "All shots" if n > 2 else "Both shots"
    return "Shots " + ", ".join(str(x) for x in numbers)

