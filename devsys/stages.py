"""K0a kế hoạch kiểm soát (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.9, N3, N6, N7): SỔ KHÂU + BẢNG LOẠI LỖI.

devsys/stages.json      — mỗi khâu làm L1–L16 (+ âm / chữ / dựng tách riêng): kiểm trước, kiểm sau (id trong devsys/decisions.json),
                          đọc từ gì để kết luận, trạng thái, đợt sẽ lấp chỗ thiếu.
devsys/error_types.json — mỗi loại lỗi mục 4 (L1–L15, V1–V4, A1–A4): cách đo bằng code + điều Claude khai, cho từng sản phẩm áp dụng.

Module chỉ ĐỌC + KIỂM (không im lặng): `stage_problems`, `error_type_problems` trả danh sách lỗi; `missing_pre_checks`, `only_building`,
`summary_text` cho test `-s` và trang devsys "Làm ↔ Kiểm" sau này. Chỗ thiếu ĐÃ BIẾT không đỏ khi có `dot` (đợt kế hoạch sẽ lấp).
"""
import json
import os
import re
from typing import Dict, List, Optional

from devsys import decisions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES_FILE = os.path.join(ROOT, "devsys", "stages.json")
ERROR_TYPES_FILE = os.path.join(ROOT, "devsys", "error_types.json")
DOC_TU = ("byd", "goi", "ket_qua", "chu_tu_do")
TRANG_THAI = ("chay", "hoc_viec", "tat", "khong_co")
KHAU_TRANG_THAI = ("chay", "hoc_viec", "tat")
LIVE = ("chay", "hoc_viec")
DOT = ("K0a", "K0b", "K1a", "K1b", "K2", "K3", "K4", "K5", "K6", "K7", "K8")    # mục 8 lộ trình
STAGE_FIELDS = ("id", "ten", "san_pham", "lam", "ton_tien", "khau_trang_thai", "kiem_truoc", "trang_thai_kiem", "kiem_sau",
                "trang_thai_sau", "doc_tu", "nguoi_kiem", "dot")
CODE_DO_STATES = ("co", "xay")
KHAI_STATES = ("co", "hoc_viec", "xay")
SAN_PHAM = ("chu", "bang_shot", "kho", "san_khau", "anh", "goi", "video", "am_thanh", "phu_de", "dung")


def _load(path: str) -> Dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_stages(path: Optional[str] = None) -> Dict:
    return _load(path or STAGES_FILE)


def load_error_types(path: Optional[str] = None) -> Dict:
    return _load(path or ERROR_TYPES_FILE)


def base_id(sid: str) -> str:
    """'L14a' → 'L14' (khâu L14 tách theo sản phẩm âm / chữ)."""
    m = re.match(r"^(L\d+)", str(sid))
    return m.group(1) if m else str(sid)


def has_live_pre_check(s: Dict) -> bool:
    return bool(s.get("kiem_truoc")) and s.get("trang_thai_kiem") in LIVE


def missing_pre_checks(doc: Dict) -> List[Dict]:
    """Khâu TỐN TIỀN đang chạy (hoặc học việc) mà không có lớp kiểm trước đang chạy / học việc (N3)."""
    return [s for s in doc.get("stages", []) if s.get("ton_tien") is True and s.get("khau_trang_thai") in LIVE
            and not has_live_pre_check(s)]


def stage_problems(doc: Dict, deci: Dict) -> List[str]:
    ids = {d["id"] for d in deci.get("items", [])}
    out: List[str] = []
    seen = set()
    for s in doc.get("stages", []):
        i = s.get("id")
        if i in seen:
            out.append(f"{i}: id trùng")
        seen.add(i)
        for k in STAGE_FIELDS:
            if k not in s:
                out.append(f"{i}: thiếu '{k}'")
        if s.get("san_pham") not in ((doc.get("enums") or {}).get("san_pham") or SAN_PHAM):
            out.append(f"{i}: san_pham '{s.get('san_pham')}' không hợp lệ")
        if not isinstance(s.get("ton_tien"), bool):
            out.append(f"{i}: ton_tien phải true/false")
        if s.get("khau_trang_thai") not in KHAU_TRANG_THAI:
            out.append(f"{i}: khau_trang_thai '{s.get('khau_trang_thai')}' (phải {' / '.join(KHAU_TRANG_THAI)})")
        for k in ("trang_thai_kiem", "trang_thai_sau"):
            if s.get(k) not in TRANG_THAI:
                out.append(f"{i}: {k} '{s.get(k)}' (phải {' / '.join(TRANG_THAI)})")
        if s.get("doc_tu") not in DOC_TU:
            out.append(f"{i}: doc_tu '{s.get('doc_tu')}' (phải {' / '.join(DOC_TU)})")
        dot = s.get("dot")
        if dot is not None and dot not in DOT:
            out.append(f"{i}: dot '{dot}' không có trong lộ trình mục 8 ({', '.join(DOT)})")
        for k in ("lam", "kiem_truoc", "kiem_sau"):
            for d in s.get(k) or []:
                if d not in ids:
                    out.append(f"{i}: {k} '{d}' không có trong devsys/decisions.json")
        for lst, st in (("kiem_truoc", "trang_thai_kiem"), ("kiem_sau", "trang_thai_sau")):
            if not (s.get(lst) or []) and s.get(st) != "khong_co":
                out.append(f"{i}: {lst} rỗng thì {st} phải 'khong_co' (đang '{s.get(st)}')")
            if (s.get(lst) or []) and s.get(st) == "khong_co":
                out.append(f"{i}: {st} 'khong_co' mà {lst} có id")
        if (s.get("ton_tien") is True and s.get("khau_trang_thai") in LIVE and not has_live_pre_check(s) and not dot):
            out.append(f"{i}: khâu tốn tiền đang chạy không có kiểm trước đang chạy / học việc — ghi 'dot' (đợt sẽ lấp) hoặc thêm kiểm")
        if s.get("doc_tu") == "chu_tu_do" and not dot:
            out.append(f"{i}: lớp kiểm đọc chu_tu_do để kết luận (N1) — chỉ được khi có 'dot' (đợt chuyển sang BYĐ / gói)")
    for d in (doc.get("kiem_chung") or {}).get("ids", []):
        if d not in ids:
            out.append(f"kiem_chung: '{d}' không có trong devsys/decisions.json")
    return out


def _where_problem(where: Optional[str], root: str) -> Optional[str]:
    if not where:
        return None
    path, _, symbol = where.partition(":")
    full = os.path.join(root, *path.split("/"))
    if not os.path.isfile(full):
        return f"{where} — không có file"
    if symbol:
        with open(full, encoding="utf-8", errors="ignore") as f:
            if not decisions._has_symbol(f.read(), symbol):
                return f"{where} — không còn hàm/tên '{symbol}'"
    return None


def error_type_problems(doc: Dict, root: str = ROOT) -> List[str]:
    products = set(doc.get("san_pham") or ("anh", "video", "am_chu"))
    out: List[str] = []
    for t in doc.get("types", []):
        i = t.get("id")
        ap = t.get("ap_dung") or []
        if not ap:
            out.append(f"{i}: ap_dung rỗng")
        for p in ap:
            if p not in products:
                out.append(f"{i}: sản phẩm '{p}' không hợp lệ")
        covered = set()
        for kind, states in (("code_do", CODE_DO_STATES), ("claude_khai", KHAI_STATES)):
            for e in t.get(kind) or []:
                tag = f"{i}.{kind} '{e.get('mo_ta')}'"
                if not str(e.get("mo_ta") or "").strip():
                    out.append(f"{i}.{kind}: thiếu mo_ta")
                if e.get("trang_thai") not in states:
                    out.append(f"{tag}: trang_thai '{e.get('trang_thai')}' (phải {' / '.join(states)})")
                if e.get("trang_thai") in ("xay", "hoc_viec") and e.get("dot") not in DOT:
                    out.append(f"{tag}: trang_thai '{e.get('trang_thai')}' phải có dot trong lộ trình (đang {e.get('dot')!r})")
                if e.get("trang_thai") == "co" and kind == "code_do" and not e.get("where"):
                    out.append(f"{tag}: 'co' mà không ghi where")
                if kind == "claude_khai" and not e.get("enum"):
                    out.append(f"{tag}: claude_khai phải ghi enum (N4: khai điều thấy, không khai đúng/sai)")
                bad = _where_problem(e.get("where"), root)
                if bad:
                    out.append(f"{tag}: {bad}")
                for p in e.get("san_pham") or ap:
                    if p not in ap:
                        out.append(f"{tag}: san_pham '{p}' không thuộc ap_dung")
                    covered.add(p)
        for p in ap:
            if p not in covered:
                out.append(f"{i}: sản phẩm '{p}' không có code_do / claude_khai nào")
    return out


def _has_real(t: Dict) -> bool:
    return any(e.get("trang_thai") == "co" for e in t.get("code_do") or []) or \
        any(e.get("trang_thai") in ("co", "hoc_viec") for e in t.get("claude_khai") or [])


def only_building(doc: Dict) -> List[Dict]:
    """Loại lỗi chưa có cách kiểm nào CÓ THẬT (mọi mục đều 'xay')."""
    return [t for t in doc.get("types", []) if not _has_real(t)]


def summary_rows(doc: Dict) -> List[Dict]:
    return [{"id": s["id"], "ten": s["ten"], "ton_tien": s.get("ton_tien"), "kiem_truoc": s.get("trang_thai_kiem"),
             "kiem_sau": s.get("trang_thai_sau"), "doc_tu": s.get("doc_tu"), "dot": s.get("dot") or "",
             "thieu": s.get("ton_tien") is True and s.get("khau_trang_thai") in LIVE and not has_live_pre_check(s)}
            for s in doc.get("stages", [])]


def summary_text(doc: Dict, types: Optional[Dict] = None) -> str:
    rows = summary_rows(doc)
    lines = ["Sổ khâu (K0a) — ✗ = khâu tốn tiền đang chạy thiếu kiểm trước", f"{'khâu':6} {'tiền':4} {'trước':9} {'sau':9} {'đọc từ':10} đợt  tên"]
    for r in rows:
        lines.append(f"{('✗ ' if r['thieu'] else '  ') + r['id']:6} {'có' if r['ton_tien'] else '—':4} {r['kiem_truoc']:9} {r['kiem_sau']:9} "
                     f"{r['doc_tu']:10} {r['dot']:4} {r['ten']}")
    miss = [s["id"] for s in missing_pre_checks(doc)]
    lines.append(f"Thiếu kiểm trước (tốn tiền, đang chạy): {len(miss)} — {', '.join(miss)}")
    if types:
        ob = [t["id"] for t in only_building(types)]
        lines.append(f"Loại lỗi chỉ có 'xay' (chưa có cách kiểm thật): {len(ob)} / {len(types.get('types', []))} — {', '.join(ob)}")
    return "\n".join(lines)
