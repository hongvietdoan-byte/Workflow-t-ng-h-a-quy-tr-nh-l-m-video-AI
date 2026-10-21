"""V3.1 M6.1 (C-M61-M69, cloud-E 21/10) — Role Registry CHỈ ĐỌC. Sổ v31-ep-m6-pack-a-approved-2026-10-21.
Thiết kế: docs/KE_HOACH_TO_LAM_PHIM_CO_CHU_2026-10-21.md mục 2a (vai, quyền đọc/ghi, đầu vào/ra, công cụ, nghiệm thu, lỗi phụ trách, leo thang)
+ audit M6.0 (W1–W38 đường ghi theo vai, K1–K16 đường Kỹ sư ghi production, check đề xuất Q1–Q9 đọc từ đây).

Module này KHÔNG ghi gì (không tệp, không CSDL) và không đổi đường ghi / gửi job nào: chỉ nạp `data/crew_roles.json`, kiểm hợp đồng
(`problems`) và tra cứu (`owner_of`, `can_write`, `role_of_write`, `engineer_paths`, `owner_of_error`). Cờ `crew_registry` (TẮT): đường chạy
(Continuity Validator M6.9 …) lấy registry qua `active()` → None khi TẮT; `load()` / `problems()` / CLI `py -m core.crew check` luôn đọc được
(là kiểm tĩnh, như core.decisions check). Định tuyến lỗi: mã QC (owns_errors.codes) → category sổ lỗi (owns_errors.categories) → khâu sổ lỗi
(owns_errors.stages, devsys/stages.json) → không rõ = `fallback_owner` (Director phân công). Continuity Validator không đứng tên lỗi (QC độc lập)."""
import fnmatch
import json
import os
import re
import sys
from typing import Dict, Iterable, List, Optional

FLAG = "crew_registry"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "crew_roles.json")
REQUIRED = ("id", "name", "reports_to", "reads", "writes", "outputs", "tools", "acceptance", "owns_errors", "escalate", "claude_stage", "flag")
ESCALATE_TO = ("director", "executive_producer")
WRITE_OK = ("dung", "sai", "canh_bao")
LEVELS = ("cao", "trung_binh", "thap")


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def load(path: Optional[str] = None) -> Dict:
    with open(path or PATH, encoding="utf-8") as f:
        return json.load(f)


def active() -> Optional[Dict]:
    """Registry cho ĐƯỜNG CHẠY: cờ TẮT → None (không nạp gì)."""
    return load() if enabled() else None


def roles(reg: Optional[Dict] = None) -> List[Dict]:
    return list((reg or load()).get("roles") or [])


def role(role_id: str, reg: Optional[Dict] = None) -> Optional[Dict]:
    return next((r for r in roles(reg) if r.get("id") == role_id), None)


def owner_of(field: str, reg: Optional[Dict] = None) -> Optional[str]:
    meta = (reg or load()).get("fields", {}).get(field)
    return meta.get("owner") if isinstance(meta, dict) else None


def can_write(role_id: str, field: str, reg: Optional[Dict] = None) -> bool:
    """Vai được ghi trường này theo registry (EP: mọi trường — quyền mục 1b). Chỉ tra cứu: guard theo vai là M6.4."""
    r = role(role_id, reg)
    if r is None:
        return False
    return bool(r.get("writes_any")) or field in (r.get("writes") or [])


def _norm_where(s: str) -> str:
    s = s.strip().replace("\\", "/")
    if ":" not in s and "." in s and "/" not in s and not s.endswith(".py"):
        mod, _, fn = s.rpartition(".")                       # "camera_plan.apply" → "core/camera_plan.py:apply"
        s = f"core/{mod.replace('.', '/')}.py:{fn}"
    return s


def role_of_write(where: str, reg: Optional[Dict] = None) -> Optional[Dict]:
    """Đường ghi (W-id, 'tệp:hàm' hoặc 'module.hàm') → mục write_paths {id, where, fields, role, ok, note}; không có → None."""
    paths = (reg or load()).get("write_paths") or []
    hit = next((w for w in paths if w.get("id") == where), None)
    if hit is not None:
        return hit
    want = _norm_where(where)
    return next((w for w in paths if want in [_norm_where(x) for x in w.get("where") or []]), None)


def engineer_paths(reg: Optional[Dict] = None) -> List[Dict]:
    return list((reg or load()).get("engineer_paths") or [])


def _errors_index(errors: Optional[Iterable[Dict]] = None) -> Dict[str, Dict]:
    if errors is None:
        try:
            with open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8") as f:
                errors = json.load(f).get("items") or []
        except (OSError, ValueError):
            errors = []
    out = {}
    for e in errors:
        if isinstance(e, dict) and e.get("id"):
            out[e["id"]] = e
            for a in e.get("alias") or []:
                out.setdefault(f"alias:{a}", e)
    return out


def owner_of_error(qc_code: Optional[str] = None, registry_ids: Iterable[str] = (), reg: Optional[Dict] = None,
                   errors: Optional[Iterable[Dict]] = None) -> Dict:
    """Lỗi → vai chủ. {"owner", "via", "candidates": [{role, via}]}. Thứ tự: mã QC → category sổ lỗi → khâu sổ lỗi → fallback."""
    reg = reg or load()
    rs = roles(reg)
    cands: List[Dict] = []

    def add(rid: str, via: str):
        if rid and all(c["role"] != rid for c in cands):
            cands.append({"role": rid, "via": via})

    if qc_code:
        for r in rs:
            if any(fnmatch.fnmatchcase(qc_code, pat) for pat in (r.get("owns_errors") or {}).get("codes") or []):
                add(r["id"], f"code:{qc_code}")
    idx = _errors_index(errors)
    for rid_ in registry_ids or []:
        e = idx.get(rid_) or idx.get(f"alias:{rid_}")
        if e is None:
            continue
        cat, stage = e.get("category"), e.get("stage")
        by_cat = [r["id"] for r in rs if cat and cat in ((r.get("owns_errors") or {}).get("categories") or [])]
        by_stage = [r["id"] for r in rs if stage and stage in ((r.get("owns_errors") or {}).get("stages") or [])]
        for r in by_cat:
            add(r, f"category:{cat} ({rid_})")
        for r in by_stage:
            add(r, f"stage:{stage} ({rid_})")
    if cands:
        return {"owner": cands[0]["role"], "via": cands[0]["via"], "candidates": cands}
    fb = reg.get("fallback_owner") or "director"
    return {"owner": fb, "via": "fallback", "candidates": [{"role": fb, "via": "fallback"}]}


# ---- kiểm hợp đồng (chỉ đọc mã nguồn / sổ, không ghi) ------------------------------------------------------------------------------
def _read(rel: str) -> str:
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _code_text(root: str) -> str:
    parts = []
    for top in ("core", "tools"):
        for d, _dirs, files in os.walk(os.path.join(root, top)):
            for fn in files:
                if fn.endswith(".py"):
                    try:
                        with open(os.path.join(d, fn), encoding="utf-8") as f:
                            parts.append(f.read())
                    except (OSError, UnicodeDecodeError):
                        pass
    return "\n".join(parts)


def _field_real(field: str, db_src: str, code_src: str) -> bool:
    if field.startswith("file:"):
        return len(field) > 5
    parts = field.split(".")
    if f"CREATE TABLE IF NOT EXISTS {parts[0]} (" not in db_src:
        return False
    if len(parts) == 1 or parts[1] == "*":
        return True
    if parts[1] == "data" and len(parts) >= 3:
        return parts[2] == "*" or bool(re.search(r"[\"']" + re.escape(parts[2]) + r"[\"']", code_src))
    return bool(re.search(r"\b" + re.escape(parts[1]) + r"\b", db_src))


def _where_real(where: str, root: str) -> bool:
    if where.startswith("("):
        return True                                           # đường không có tệp (SQL tay của phiên — K14 / W38)
    rel, _, fn = where.partition(":")
    full = os.path.join(root, rel)
    if not os.path.exists(full):
        return False
    if fn and os.path.isfile(full):
        try:
            with open(full, encoding="utf-8") as f:
                return bool(re.search(r"^\s*def " + re.escape(fn) + r"\(", f.read(), re.M))
        except OSError:
            return False
    return True


def problems(reg: Optional[Dict] = None, root: str = ROOT) -> List[str]:
    """Lỗi hợp đồng của registry ([] = đạt). Kiểm: trường bắt buộc, id duy nhất, reports_to / escalate trỏ vai có thật, mỗi trường đúng
    MỘT vai chủ + vai đó khai trong writes, writes ⊂ trường thật (bảng CSDL / khóa scenes.data có trong code), owns_errors.stages ⊂
    devsys/stages.json và mỗi khâu đúng một vai, codes ⊂ qc_evidence.CODES, categories ⊂ devsys/errors.json, claude_stage là nhãn sổ chi
    có trong code, flag là cờ có thật, Continuity Validator không đứng tên lỗi, write_paths / engineer_paths trỏ tệp:hàm có thật."""
    reg = reg if reg is not None else load()
    out: List[str] = []
    rs = roles(reg)
    ids = [r.get("id") for r in rs]
    if reg.get("version") != 1:
        out.append("version phải = 1")
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        out.append(f"id vai trùng: {dup}")
    known = set(ids)
    db_src = _read(os.path.join("core", "db.py"))
    code_src = _code_text(root)
    try:
        from . import features
        flags = set(features.FEATURES)
    except Exception:  # noqa: BLE001
        flags = set()
    try:
        from . import qc_evidence
        qc_codes = set(qc_evidence.CODES)
    except Exception:  # noqa: BLE001
        qc_codes = set()
    try:
        stages = [s["id"] for s in json.loads(_read(os.path.join("devsys", "stages.json")))["stages"]]
    except (ValueError, KeyError, TypeError):
        stages = []
    cats = {e.get("category") for e in _errors_index().values() if e.get("category")}
    stage_known = set(reg.get("claude_stages_known") or [])
    fields = reg.get("fields") or {}
    for r in rs:
        rid = r.get("id")
        miss = [k for k in REQUIRED if k not in r]
        if miss:
            out.append(f"vai {rid}: thiếu trường {miss}")
        if r.get("reports_to") is not None and r.get("reports_to") not in known:
            out.append(f"vai {rid}: reports_to {r.get('reports_to')!r} không phải vai có thật")
        for k in ("reads", "writes", "outputs", "tools", "acceptance", "claude_stage"):
            if k in r and not isinstance(r[k], list):
                out.append(f"vai {rid}: {k} phải là danh sách")
        for f in r.get("writes") or []:
            if f not in fields:
                out.append(f"vai {rid}: writes {f!r} không có trong bảng sở hữu trường (fields)")
            elif fields[f].get("owner") != rid:
                out.append(f"vai {rid}: writes {f!r} nhưng vai chủ là {fields[f].get('owner')!r} (mỗi trường đúng MỘT vai chủ)")
        oe = r.get("owns_errors") if isinstance(r.get("owns_errors"), dict) else {}
        if "owns_errors" in r and not all(isinstance(oe.get(k), list) for k in ("stages", "codes", "categories")):
            out.append(f"vai {rid}: owns_errors cần stages / codes / categories (danh sách)")
        for s in oe.get("stages") or []:
            if stages and s not in stages:
                out.append(f"vai {rid}: owns_errors.stages {s!r} không có trong devsys/stages.json")
        for c in oe.get("codes") or []:
            if qc_codes and not any(fnmatch.fnmatchcase(q, c) for q in qc_codes):
                out.append(f"vai {rid}: owns_errors.codes {c!r} không khớp mã nào của qc_evidence.CODES")
        for c in oe.get("categories") or []:
            if cats and c not in cats:
                out.append(f"vai {rid}: owns_errors.categories {c!r} không có trong devsys/errors.json")
        if rid == "continuity_validator" and any(oe.get(k) for k in ("stages", "codes", "categories")):
            out.append("vai continuity_validator không được đứng tên lỗi (QC độc lập với vai tạo sản phẩm — kế hoạch M6 mục 5)")
        esc = r.get("escalate") if isinstance(r.get("escalate"), dict) else None
        if "escalate" in r and (esc is None or set(esc) - set(ESCALATE_TO)):
            out.append(f"vai {rid}: escalate chỉ có khóa {ESCALATE_TO}")
        for st in r.get("claude_stage") or []:
            if st not in stage_known:
                out.append(f"vai {rid}: claude_stage {st!r} không có trong claude_stages_known")
            elif code_src and not re.search(r"[\"']" + re.escape(st) + r"[\"']", code_src):
                out.append(f"vai {rid}: claude_stage {st!r} không thấy trong code (nhãn sổ chi usage_events.stage)")
        if r.get("flag") is not None and flags and r["flag"] not in flags:
            out.append(f"vai {rid}: flag {r['flag']!r} không phải cờ có thật (core/features.py)")
    for f, meta in fields.items():
        owner = (meta or {}).get("owner")
        if owner not in known:
            out.append(f"trường {f!r}: vai chủ {owner!r} không phải vai có thật")
        elif f not in (next(r for r in rs if r.get("id") == owner).get("writes") or []):
            out.append(f"trường {f!r}: vai chủ {owner!r} không khai trường này trong writes")
        if db_src and not _field_real(f, db_src, code_src):
            out.append(f"trường {f!r} không có thật (bảng/cột core/db.py hoặc khóa scenes.data trong code)")
    for s in stages:
        owners = [r.get("id") for r in rs if s in ((r.get("owns_errors") or {}).get("stages") or [])]
        if len(owners) != 1:
            out.append(f"khâu {s}: cần đúng một vai chủ, đang có {owners}")
    if reg.get("fallback_owner") not in known:
        out.append("fallback_owner phải là vai có thật")
    for w in reg.get("write_paths") or []:
        if w.get("role") is not None and w.get("role") not in known:
            out.append(f"{w.get('id')}: role {w.get('role')!r} không phải vai có thật")
        for a in w.get("also") or []:
            if a not in known:
                out.append(f"{w.get('id')}: also {a!r} không phải vai có thật")
        if w.get("ok") not in WRITE_OK:
            out.append(f"{w.get('id')}: ok ∉ {WRITE_OK}")
        for x in w.get("where") or []:
            if not _where_real(x, root):
                out.append(f"{w.get('id')}: đường ghi {x!r} không có (tệp / def hàm)")
        for f in w.get("fields") or []:
            if db_src and not _field_real(f, db_src, code_src):
                out.append(f"{w.get('id')}: trường {f!r} không có thật")
    try:
        dec_ids = {d.get("id") for d in json.loads(_read(os.path.join("data", "decisions.json"))).get("items") or []}
    except (ValueError, AttributeError):
        dec_ids = set()
    for k in reg.get("engineer_paths") or []:
        if k.get("level") not in LEVELS:
            out.append(f"{k.get('id')}: level ∉ {LEVELS}")
        if dec_ids and k.get("decision") not in dec_ids:
            out.append(f"{k.get('id')}: decision {k.get('decision')!r} không có trong data/decisions.json")
        for x in k.get("where") or []:
            if not _where_real(x, root):
                out.append(f"{k.get('id')}: đường {x!r} không có (tệp / def hàm)")
    for x in reg.get("job_insert_points") or []:
        if not os.path.isfile(os.path.join(root, x)):
            out.append(f"job_insert_points: {x!r} không có")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """py -m core.crew check | owner <trường> | write <đường ghi> | route <mã QC hoặc id sổ lỗi>…  — chỉ đọc."""
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        bad = problems()
        for b in bad:
            print("✖", b)
        print(f"Role Registry: {len(roles())} vai, {len(load().get('fields') or {})} trường — {len(bad)} lỗi")
        return 1 if bad else 0
    if cmd == "owner" and len(argv) > 1:
        print(owner_of(argv[1]))
        return 0
    if cmd == "write" and len(argv) > 1:
        print(json.dumps(role_of_write(argv[1]), ensure_ascii=False))
        return 0
    if cmd == "route" and len(argv) > 1:
        codes = [a for a in argv[1:] if a.startswith("QC-")]
        regs = [a for a in argv[1:] if not a.startswith("QC-")]
        print(json.dumps(owner_of_error(codes[0] if codes else None, regs), ensure_ascii=False))
        return 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
