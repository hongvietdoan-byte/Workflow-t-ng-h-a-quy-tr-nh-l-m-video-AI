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
DOT = ("K0a", "K0b", "K1a", "K2", "K3", "K4", "K1b", "K5", "K6", "K7", "K8")    # mục 8 lộ trình, THỨ TỰ CHẠY (K1b sau K4)
VAI = ("kiem", "sinh", "nguoi_duyet")    # vai của id được sổ tham chiếu: chỉ 'kiem' được nằm trong kiem_truoc / kiem_sau
STAGE_FIELDS = ("id", "ten", "san_pham", "lam", "ton_tien", "khau_trang_thai", "kiem_truoc", "trang_thai_kiem", "kiem_sau",
                "trang_thai_sau", "doc_tu", "nguoi_kiem", "dot")
CODE_DO_STATES = ("co", "hoc_viec", "xay")     # hoc_viec = code có nhưng đo chưa đúng (thẩm định 4: plate_layout_qc mù) — không tính
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


CO_FIELDS = {"khau": "khau_trang_thai", "truoc": "trang_thai_kiem", "sau": "trang_thai_sau"}
_FLAG_STATE = {"on": "chay", "trainee": "hoc_viec", "off": "tat"}


def _flags_of(s: Dict) -> Dict[str, str]:
    """Trường `co` của một dòng: tên cờ (áp cho kiểm trước) hoặc {khau|truoc|sau|<id kiểm>: tên cờ}. Khóa là id trong kiem_truoc /
    kiem_sau = cờ của RIÊNG lớp kiểm đó (vd L3 d86 chỉ chạy khi stage_camera bật, d10/d11 thì không phụ thuộc)."""
    co = s.get("co")
    if not co:
        return {}
    return {"truoc": co} if isinstance(co, str) else dict(co)


def _id_flags(s: Dict) -> Dict[str, str]:
    return {k: v for k, v in _flags_of(s).items() if k not in CO_FIELDS and k in (s.get("kiem_truoc") or []) + (s.get("kiem_sau") or [])}


def _known_flags() -> set:
    try:
        from core import features
        return set(features.FEATURES)
    except Exception:  # noqa: BLE001 - devsys đọc checkout khác: không kiểm được tên cờ thì không báo nhầm
        return set()


def effective(doc: Dict, state=None) -> Dict:
    """Bản sao sổ với trạng thái ĐỌC TỪ CỜ THẬT (core.features.state) cho dòng có `co`: on → chay, trainee → hoc_viec, off → tat.
    Danh sách kiểm rỗng giữ 'khong_co'. Đọc cờ lỗi → giữ giá trị ghi tay + ghi chú `_co_ghi` (không im lặng)."""
    if state is None:
        from core import features
        state = features.state
    out = dict(doc, stages=[])
    for s in doc.get("stages", []):
        s = dict(s)
        notes = []
        idf = _id_flags(s)
        for lst, field in (("kiem_truoc", "trang_thai_kiem"), ("kiem_sau", "trang_thai_sau")):
            ids = list(s.get(lst) or [])
            flagged = [d for d in ids if d in idf]
            if not flagged:
                continue
            got = {}
            for d in flagged:
                try:
                    got[d] = _FLAG_STATE[state(idf[d])]
                except Exception as e:  # noqa: BLE001 - đọc cờ lỗi: giữ id (ghi tay), nói ra
                    notes.append(f"không đọc được cờ '{idf[d]}' của {d} ({type(e).__name__}: {e}) — giữ ghi tay")
            off = [d for d in flagged if got.get(d) == "tat"]
            if off:
                notes.append(f"{lst}: bỏ {', '.join(f'{d} (cờ {idf[d]} TẮT)' for d in off)}")
            s[lst] = [d for d in ids if d not in off]
            if not s[lst]:
                s[field] = "tat"
            elif all(d in got for d in s[lst]):        # mọi lớp còn lại đều theo cờ: trạng thái = cờ mạnh nhất
                s[field] = "chay" if "chay" in [got[d] for d in s[lst]] else "hoc_viec"
        for part, flag in _flags_of(s).items():
            field = CO_FIELDS.get(part)
            if not field:
                if part not in idf:
                    notes.append(f"co.{part}: phần lạ (khau / truoc / sau / id trong kiem_truoc, kiem_sau)")
                continue
            if part == "truoc" and not s.get("kiem_truoc") or part == "sau" and not s.get("kiem_sau"):
                continue
            try:
                val = _FLAG_STATE[state(flag)]
            except Exception as e:  # noqa: BLE001 - cờ bị đổi tên / settings hỏng: giữ ghi tay, nói ra
                notes.append(f"không đọc được cờ '{flag}' ({type(e).__name__}: {e}) — giữ '{s.get(field)}' ghi tay")
                continue
            if val != s.get(field):
                notes.append(f"{field}: ghi tay '{s.get(field)}' → cờ {flag} = '{val}'")
            s[field] = val
        if notes:
            s["_co_ghi"] = notes
        out["stages"].append(s)
    return out


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
    chung = list((doc.get("kiem_chung") or {}).get("ids", []))
    vai = doc.get("vai") or {}
    role = {d: r for r, lst in vai.items() for d in lst}
    now = doc.get("dot_hien_tai")
    if now is not None and now not in DOT:
        out.append(f"dot_hien_tai '{now}' không có trong lộ trình mục 8 ({', '.join(DOT)})")
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
        if dot in DOT and now in DOT and DOT.index(dot) <= DOT.index(now) and (
                (s.get("ton_tien") is True and s.get("khau_trang_thai") in LIVE and not has_live_pre_check(s))
                or s.get("doc_tu") == "chu_tu_do"):
            out.append(f"{i}: dot '{dot}' quá hạn (đợt hiện tại {now}) — chỗ thiếu vẫn còn: lấp hoặc ghi đợt mới có lý do")
        for lst in ("kiem_truoc", "kiem_sau"):
            for d in s.get(lst) or []:
                if d in chung:
                    out.append(f"{i}: {lst} '{d}' thuộc kiem_chung (cổng tiền / điều kiện vận hành) — không phải kiểm chất lượng (N3)")
                elif vai and role.get(d) != "kiem":
                    out.append(f"{i}: {lst} '{d}' vai '{role.get(d) or 'chưa ghi'}' — chỉ id vai 'kiem' (stages.json 'vai') được đếm"
                               + (" (bộ SINH không phải kiểm)" if role.get(d) == "sinh" else "")
                               + (" (người duyệt ghi ở nguoi_kiem)" if role.get(d) == "nguoi_duyet" else ""))
        for part, flag in _flags_of(s).items():
            if part not in CO_FIELDS and part not in _id_flags(s):
                out.append(f"{i}: co.{part} — phần lạ (khau / truoc / sau / id trong kiem_truoc, kiem_sau)")
            elif _known_flags() and flag not in _known_flags():
                out.append(f"{i}: co.{part} = '{flag}' không có trong core/features.FEATURES")
    for d in chung:
        if d not in ids:
            out.append(f"kiem_chung: '{d}' không có trong devsys/decisions.json")
    seen_role: Dict[str, str] = {}
    for r, lst in vai.items():
        if r not in VAI:
            out.append(f"vai: '{r}' không hợp lệ (phải {' / '.join(VAI)})")
        for d in lst:
            if d not in ids:
                out.append(f"vai.{r}: '{d}' không có trong devsys/decisions.json")
            if d in seen_role:
                out.append(f"vai: '{d}' vừa {seen_role[d]} vừa {r}")
            seen_role[d] = r
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
                if (e.get("trang_thai") == "hoc_viec" or e.get("bat") is False) and not _entry_flags(e):
                    out.append(f"{tag}: '{e.get('trang_thai')}'{' / bat:false' if e.get('bat') is False else ''} phải ghi 'co' "
                               f"(cờ quyết chạy) — đọc cờ thật, cờ TẮT thì không tính là cách kiểm có thật")
                for f in _entry_flags(e):
                    if _known_flags() and f not in _known_flags():
                        out.append(f"{tag}: co '{f}' không có trong core/features.FEATURES")
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


def _entry_flags(e: Dict) -> List[str]:
    co = e.get("co")
    return [co] if isinstance(co, str) else list(co or [])


def _real_state(state=None):
    if state is not None:
        return state
    from core import features
    return features.state


def _entry_live(e: Dict, state) -> bool:
    """Mục có code / Claude nhưng chỉ chạy dưới cờ (`co`, một tên hoặc danh sách — bật MỘT cờ là chạy): cờ TẮT → không chạy.
    `bat: false` không kèm `co` → coi như không chạy. Đọc cờ lỗi → không tính (không đếm thứ chưa chắc chạy)."""
    flags = _entry_flags(e)
    if not flags:
        return e.get("bat") is not False
    for f in flags:
        try:
            if state(f) in ("on", "trainee"):
                return True
        except Exception:  # noqa: BLE001 - cờ đổi tên / settings hỏng: không tính, error_type_problems báo tên cờ lạ
            continue
    return False


def _has_real(t: Dict, state=None) -> bool:
    state = _real_state(state)
    return any(e.get("trang_thai") == "co" and _entry_live(e, state) for e in t.get("code_do") or []) or \
        any(e.get("trang_thai") in ("co", "hoc_viec") and _entry_live(e, state) for e in t.get("claude_khai") or [])


def only_building(doc: Dict, state=None) -> List[Dict]:
    """Loại lỗi chưa có cách kiểm nào CÓ THẬT ĐANG CHẠY: mọi mục 'xay', hoặc mục có thật nhưng cờ của nó TẮT / `bat: false`
    (thẩm định 3). state: hàm cờ → 'on' / 'trainee' / 'off' (mặc định core.features.state)."""
    state = _real_state(state)
    return [t for t in doc.get("types", []) if not _has_real(t, state)]


def summary_rows(doc: Dict) -> List[Dict]:
    """Một dòng / khâu cho bảng 'Làm ↔ Kiểm': `thieu` = tô ĐỎ (tốn tiền, đang chạy, thiếu kiểm trước); `tu_do` = tô VÀNG (đọc chữ tự do).
    Truyền `effective(doc)` để trạng thái theo cờ thật."""
    return [{"id": s["id"], "ten": s["ten"], "ton_tien": s.get("ton_tien"), "khau": s.get("khau_trang_thai"),
             "kiem_truoc": s.get("trang_thai_kiem"), "kiem_sau": s.get("trang_thai_sau"), "doc_tu": s.get("doc_tu"),
             "dot": s.get("dot") or "", "co": ", ".join(f"{k}:{v}" for k, v in _flags_of(s).items()),
             "ghi_co": "; ".join(s.get("_co_ghi") or []),
             "thieu": s.get("ton_tien") is True and s.get("khau_trang_thai") in LIVE and not has_live_pre_check(s),
             "tu_do": s.get("doc_tu") == "chu_tu_do"}
            for s in doc.get("stages", [])]


def error_type_rows(doc: Dict, state=None) -> List[Dict]:
    """Một dòng / loại lỗi: cách kiểm có thật (co / hoc_viec, kèm cờ khi cờ TẮT) và việc còn xây (+ đợt)."""
    state = _real_state(state)
    rows = []
    for t in doc.get("types", []):
        es = [("code", e) for e in t.get("code_do") or []] + [("Claude", e) for e in t.get("claude_khai") or []]
        rows.append({"id": t["id"], "ten": t["ten"], "ap_dung": ", ".join(t.get("ap_dung") or []),
                     "co": "; ".join(f"{w}: {e['mo_ta']}" + (" (học việc)" if e.get("trang_thai") == "hoc_viec" else "")
                                     + ("" if _entry_live(e, state) else f" (cờ {'/'.join(_entry_flags(e)) or 'bat:false'} TẮT — không tính)")
                                     for w, e in es if e.get("trang_thai") in ("co", "hoc_viec")),
                     "xay": "; ".join(f"{w}: {e['mo_ta']} [{e.get('dot')}]" for w, e in es if e.get("trang_thai") == "xay"),
                     "chi_xay": not _has_real(t, state)})
    return rows


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
        lines.append(f"Loại lỗi không có cách kiểm nào đang chạy (chỉ 'xay' / cờ TẮT / bat:false):{len(ob)} / {len(types.get('types', []))} — {', '.join(ob)}")
    return "\n".join(lines)
