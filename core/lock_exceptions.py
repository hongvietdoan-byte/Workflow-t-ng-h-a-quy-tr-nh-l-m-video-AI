"""Ngoại lệ chủ ý của shot (BYĐ `byd.ngoai_le`) đè lên Character Lock — MỘT nguồn cho mọi nơi đọc khóa nhân vật (11/10, #24 shot 9–10).

Vì sao: ngoai_le "không có hiệu ứng glitch toàn thân trong ảnh (ảnh sạch)" (phạm vi [9, 10]) trong khi khóa nhân vật vẫn gửi "keep …
full-body glitch/noise effect; never … losing glitch effect" — khóa thắng ngoại lệ của chính shot: ảnh ra có vệt glitch (runner.lock_note,
sửa ở p24-r12-fix), và QC ảnh / clip / cảnh (prompts.lock_text, qc_spec.compile_frame) cùng prompt viết motion vẫn đọc khóa cũ → chấm ảnh
sạch là "mất glitch". Ở đây: đọc ngoại lệ theo `pham_vi` của shot, bỏ mệnh đề khóa nói về món được ngoại lệ, câu nói rõ ngoại lệ.
Thuần dữ liệu, không gọi model.
"""
import re
from typing import Dict, Iterable, List, Optional, Sequence

_NEGATION = re.compile(r"(?<!\w)(không|no|without|never|bỏ|sạch|clean)(?!\w)", re.I)


def shot_label(data: Optional[Dict]):
    """Số shot dùng để so `pham_vi`: byd.shot, không có thì shot_no."""
    byd = (data or {}).get("byd") or {}
    return byd.get("shot", (data or {}).get("shot_no"))


def for_shot(data: Optional[Dict]) -> Dict[str, Dict]:
    """BYĐ `ngoai_le` của CHÍNH shot này theo tên nhân vật (viết hoa) → {"items": [khóa identity_declare.ITEMS ngoại lệ nhắc tới],
    "without": True khi ngoại lệ nói KHÔNG có món đó}. Ngoại lệ có `pham_vi` không chứa shot này → bỏ qua."""
    from .identity_declare import ITEMS
    byd = (data or {}).get("byd") or {}
    shot = shot_label(data)
    out: Dict[str, Dict] = {}
    for n in byd.get("ngoai_le") or []:
        if not isinstance(n, dict) or not n.get("doi_tuong"):
            continue
        scope = n.get("pham_vi")
        if isinstance(scope, list) and scope and shot is not None and str(shot).strip() not in {str(x).strip() for x in scope}:
            continue
        text = f"{n.get('dieu_trai') or ''} {n.get('cach_hien') or ''}"
        items = [k for k, (en, vi) in ITEMS.items()
                 if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, re.I) for w in en + vi + (k,))]
        if items:
            e = out.setdefault(str(n["doi_tuong"]).strip().upper(), {"items": [], "without": False})
            e["items"] += [k for k in items if k not in e["items"]]
            e["without"] = e["without"] or bool(_NEGATION.search(text))
    return out


def drop_excepted(body: str, items: Iterable[str]) -> str:
    """Bỏ khỏi chữ khóa của một nhân vật mọi mệnh đề (tách ';' rồi ',') nhắc tới món được ngoại lệ."""
    from .identity_declare import ITEMS
    words = [w for k in items for w in ITEMS[k][0] + ITEMS[k][1] + (k,)]
    if not words:
        return body
    hit = re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I)
    keep = []
    for clause in str(body or "").split(";"):
        pieces = [x for x in clause.split(",") if not hit.search(x)]
        txt = ",".join(pieces).strip()
        if txt and txt.lower() not in ("keep", "never"):
            keep.append(txt)
    return "; ".join(keep)


def words(e: Dict) -> str:
    from .identity_declare import ITEMS
    return ", ".join(w for k in e["items"] for w in ITEMS[k][0][:3])


def note_en(name: str, e: Dict) -> str:
    """Câu tiếng Anh cho model ảnh (runner.lock_note)."""
    return (f"in THIS shot (intentional exception of the shot plan) draw {name} WITHOUT any {words(e)}" if e["without"]
            else f"in THIS shot the shot text decides the {words(e)} (intentional exception of the shot plan)")


def note_vi(name: str, e: Dict, shot=None) -> str:
    """Câu cho QC / người viết motion: ngoại lệ chủ ý — không chấm là lỗi."""
    where = f"shot {shot}" if shot is not None else "shot này"
    return (f"{name} ở {where}: ngoại lệ chủ ý của BYĐ — vẽ KHÔNG có {words(e)}; thiếu {words(e)} KHÔNG phải lỗi" if e["without"]
            else f"{name} ở {where}: ngoại lệ chủ ý của BYĐ — {words(e)} theo chữ của shot, không theo khóa nhân vật")


def apply_rules(rules: Optional[Dict], e: Optional[Dict]) -> Optional[Dict]:
    """Bản sao hồ sơ khóa (must_keep / forbidden / may_change) đã bỏ mệnh đề nói về món được ngoại lệ; e None → giữ nguyên."""
    if not rules or not e:
        return rules
    out = dict(rules)
    for k in ("must_keep", "forbidden", "may_change"):
        if isinstance(out.get(k), str) and out[k]:
            out[k] = drop_excepted(out[k], e["items"])
    return out


def notes_for_shots(shots: Sequence[Optional[Dict]], names: Optional[Iterable[str]] = None) -> List[str]:
    """Câu ngoại lệ (tiếng Việt) của nhiều shot một lúc — QC cảnh / người viết motion đọc chung một khóa cho cả cảnh."""
    wanted = {str(n).strip().upper() for n in names} if names is not None else None
    out: List[str] = []
    for d in shots or []:
        for name, e in for_shot(d).items():
            if wanted is None or name in wanted:
                line = note_vi(name, e, shot_label(d))
                if line not in out:
                    out.append(line)
    return out
