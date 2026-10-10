"""S14.50 (ý 1 từ tài liệu 'Prompt Spider', 06/10): bản đồ AI QUYẾT ở mỗi điểm của pipeline — code / claude / human.

Nguồn: devsys/decisions.json (liệt kê tay, mỗi điểm một dòng: bước, ai quyết, file:hàm, khâu Claude, gợi ý chuyển sang code). Module này
kiểm bản đồ KHỚP code (không im lặng): khâu Claude nào có trong code mà thiếu trên bản đồ, 'where' nào trỏ tới hàm không còn, trường nào
sai — rồi đếm tỉ lệ để trang 'Ai quyết' chỉ ra chỗ đang trả tiền Claude mà code làm được. Đếm theo LOẠI quyết định, không theo số lượt chạy.
"""
import json
import os
import re
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_FILE = os.path.join(ROOT, "devsys", "decisions.json")
WHO = {"code": "Code (0 USD, tất định)", "claude": "Claude (tốn token)", "human": "Người duyệt"}
_STAGE_PATTERNS = (r'tagged\(\s*"([a-z_0-9]+)"', r'_run\(\s*[a-z_]+\s*,\s*[a-z_\[\]"\']+\s*,\s*"([a-z_0-9]+)"',
                   r'_diagnosed\(\s*"([a-z_0-9]+)"', r'^STAGE\s*=\s*"([a-z_0-9]+)"')


def load(path: Optional[str] = None) -> Dict:
    with open(path or MAP_FILE, encoding="utf-8") as f:
        return json.load(f)


def claude_stages_in_code(root: str = ROOT) -> Dict[str, List[str]]:
    """Khâu Claude → các file nhắc tới nó: tagged("…"), claude_tasks._run(…, "…"), _diagnosed("…"), STAGE = "…", STAGE_SETTINGS."""
    found: Dict[str, set] = {}
    for d in ("core", "dashboard", "devsys", "tools"):
        for base, _, files in os.walk(os.path.join(root, d)):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(base, name)
                with open(path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                for pat in _STAGE_PATTERNS:
                    for m in re.finditer(pat, text, re.M):
                        found.setdefault(m.group(1), set()).add(rel)
    try:
        from core import llm_runner
        for st in llm_runner.STAGE_SETTINGS:
            found.setdefault(st, set()).add("core/llm_runner.py")
    except Exception:  # noqa: BLE001 - devsys reads another checkout; the regex scan alone still works
        pass
    return {k: sorted(v) for k, v in sorted(found.items())}


def unmapped_stages(doc: Dict, root: str = ROOT) -> List[str]:
    mapped = {d.get("stage") for d in doc.get("items", []) if d.get("who") == "claude"}
    return [st for st in claude_stages_in_code(root) if st not in mapped]


def _has_symbol(text: str, symbol: str) -> bool:
    if "." in symbol:
        cls, meth = symbol.split(".", 1)
        m = re.search(rf"^class {re.escape(cls)}\b.*?(?=^class |\Z)", text, re.M | re.S)
        return bool(m and re.search(rf"^\s+def {re.escape(meth)}\(", m.group(0), re.M))
    return bool(re.search(rf"^(def {re.escape(symbol)}\(|class {re.escape(symbol)}\b|{re.escape(symbol)}\s*[:=])", text, re.M))


def broken_wheres(doc: Dict, root: str = ROOT) -> List[str]:
    out = []
    for d in doc.get("items", []):
        where = d.get("where") or ""
        path, _, symbol = where.partition(":")
        full = os.path.join(root, *path.split("/"))
        if not path or not symbol or not os.path.isfile(full):
            out.append(f"{d.get('id')}: {where} — không có file")
            continue
        with open(full, encoding="utf-8", errors="ignore") as f:
            if not _has_symbol(f.read(), symbol):
                out.append(f"{d.get('id')}: {where} — không còn hàm/tên '{symbol}'")
    return out


def problems(doc: Dict) -> List[str]:
    steps = doc.get("steps") or {}
    out = []
    for d in doc.get("items", []):
        i = d.get("id")
        if d.get("step") not in steps:
            out.append(f"{i}: bước '{d.get('step')}' không có trong 'steps'")
        if d.get("who") not in WHO:
            out.append(f"{i}: who = '{d.get('who')}' (phải code / claude / human)")
        if not str(d.get("what") or "").strip():
            out.append(f"{i}: thiếu 'what'")
        if ":" not in str(d.get("where") or ""):
            out.append(f"{i}: 'where' phải dạng file:hàm")
        if d.get("who") == "claude" and not d.get("stage"):
            out.append(f"{i}: điểm claude thiếu 'stage' (khâu trong sổ chi)")
    return out


def _count(items: List[Dict]) -> Dict:
    """Đếm điểm quyết ĐANG NỐI luồng; điểm `bat: false` (code có, chưa nối — d95/d96) không vào n / code, đếm riêng `chua_noi`."""
    live = [d for d in items if d.get("bat") is not False]
    n = len(live)
    c = {w: sum(1 for d in live if d.get("who") == w) for w in WHO}
    return {"n": n, **c, "chua_noi": len(items) - n, "pct": {w: round(100.0 * c[w] / n, 1) if n else None for w in WHO}}


def summary(doc: Dict) -> Dict:
    items = doc.get("items", [])
    by_step = {s: _count([d for d in items if d.get("step") == s]) for s in (doc.get("steps") or {})}
    return {"all": _count(items), "by_step": by_step, "suggest": [d for d in items if d.get("suggest")]}
