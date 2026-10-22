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


def errors_index(errors=None) -> Dict[str, Dict]:
    """{id / 'alias:Gx': mục sổ lỗi}. Nhận danh sách mục, chỉ mục đã dựng (trả lại nguyên), hoặc None = đọc devsys/errors.json."""
    if isinstance(errors, dict):
        return errors
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


FALLBACK_NOTE = "không vai nào nhận lỗi này (mã QC / mục sổ lỗi chưa gán vai trong data/crew_roles.json) → Director phân công"


def owner_of_error(qc_code: Optional[str] = None, registry_ids: Iterable[str] = (), reg: Optional[Dict] = None,
                   errors=None, layer: Optional[str] = None) -> Dict:
    """Lỗi → vai chủ. {"owner", "via", "candidates": [{role, via}], "registry_owner", "fix_field", "owner_cannot_fix", "note"}.
    Thứ tự: actionability.layer → trường sửa (layer_fields) → vai chủ trường đó (vai SỬA được) → mã QC → category sổ lỗi → khâu sổ lỗi
    → fallback (nói rõ trong note). registry_owner = vai của LOẠI lỗi (không tính layer). owner_cannot_fix: True khi vai chủ không có quyền
    ghi trường sửa; None khi không biết trường sửa (layer lạ / không có)."""
    reg = reg or load()
    rs = roles(reg)
    cands: List[Dict] = []

    def add(rid: str, via: str):
        if rid and all(c["role"] != rid for c in cands):
            cands.append({"role": rid, "via": via})

    fix_field = (reg.get("layer_fields") or {}).get(layer) if layer else None
    fix_owner = owner_of(fix_field, reg) if fix_field else None

    if qc_code:
        for r in rs:
            if any(fnmatch.fnmatchcase(qc_code, pat) for pat in (r.get("owns_errors") or {}).get("codes") or []):
                add(r["id"], f"code:{qc_code}")
    idx = errors_index(errors)
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
    reg_owner = cands[0]["role"] if cands else None
    if fix_owner:
        cands = [{"role": fix_owner, "via": f"layer:{layer} → {fix_field}"}] + [c for c in cands if c["role"] != fix_owner]
    if cands:
        owner = cands[0]["role"]
        return {"owner": owner, "via": cands[0]["via"], "candidates": cands, "registry_owner": reg_owner, "fix_field": fix_field,
                "owner_cannot_fix": (not can_write(owner, fix_field, reg)) if fix_field else None, "note": ""}
    fb = reg.get("fallback_owner") or "director"
    return {"owner": fb, "via": "fallback", "candidates": [{"role": fb, "via": "fallback"}], "registry_owner": None, "fix_field": fix_field,
            "owner_cannot_fix": (not can_write(fb, fix_field, reg)) if fix_field else None, "note": FALLBACK_NOTE}


# ---- kiểm hợp đồng (chỉ đọc mã nguồn / sổ, không ghi) ------------------------------------------------------------------------------
def _read(rel: str, root: str = ROOT) -> str:
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
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


def _errors_list(root: str) -> List[Dict]:
    try:
        return json.loads(_read(os.path.join("devsys", "errors.json"), root)).get("items") or []
    except (ValueError, AttributeError):
        return []


def problems(reg: Optional[Dict] = None, root: str = ROOT, errors=None) -> List[str]:
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
    db_src = _read(os.path.join("core", "db.py"), root)
    code_src = _code_text(root)
    if not db_src:
        out.append("không đọc được core/db.py — không kiểm được trường thật")
    if not code_src:
        out.append("không đọc được mã nguồn core/ tools/ — không kiểm được khóa scenes.data / claude_stage")
    try:
        from . import features
        flags = set(features.FEATURES)
    except Exception:  # noqa: BLE001
        flags = set()
    try:
        from . import qc_evidence
        qc_map = dict(qc_evidence.CODES)
    except Exception:  # noqa: BLE001
        qc_map = {}
    qc_codes = set(qc_map)
    try:
        stages = [s["id"] for s in json.loads(_read(os.path.join("devsys", "stages.json"), root))["stages"]]
    except (ValueError, KeyError, TypeError):
        stages = []
        out.append("không đọc được devsys/stages.json — không kiểm được khâu")
    eidx = errors_index(errors) if errors is not None else errors_index(_errors_list(root))
    if not eidx:
        out.append("không đọc được devsys/errors.json — không kiểm được category / mục sổ lỗi")
    cats = {e.get("category") for e in eidx.values() if e.get("category")}
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
    claim_cat = {c for r in rs for c in (r.get("owns_errors") or {}).get("categories") or []}
    claim_stage = {c for r in rs for c in (r.get("owns_errors") or {}).get("stages") or []}
    claim_code = [c for r in rs for c in (r.get("owns_errors") or {}).get("codes") or []]
    items = {e["id"]: e for e in eidx.values()}

    def claimed(e: Dict) -> bool:
        return e.get("category") in claim_cat or e.get("stage") in claim_stage

    for e in items.values():
        if not claimed(e):
            out.append(f"sổ lỗi {e['id']} (khâu {e.get('stage')!r}, category {e.get('category')!r}): không vai nào nhận — sẽ rơi về fallback")
    for code, meta in sorted(qc_map.items()):
        regs = meta[3] if len(meta) > 3 else ()
        if any(fnmatch.fnmatchcase(code, pat) for pat in claim_code):
            continue
        if not regs or not all(r in items and claimed(items[r]) for r in regs):
            out.append(f"mã QC {code}: không vai nào nhận (không ở owns_errors.codes, mục sổ lỗi của mã chưa đủ vai) — sẽ rơi về fallback")
    for layer, f in (reg.get("layer_fields") or {}).items():
        if f not in fields:
            out.append(f"layer_fields.{layer}: trường {f!r} không có trong bảng sở hữu")
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
        dec_ids = {d.get("id") for d in json.loads(_read(os.path.join("data", "decisions.json"), root)).get("items") or []}
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


# ---- Hồ sơ vai + danh mục sản phẩm (người dùng 22/10) — data/crew_profiles.json --------------------------------------------------
PROFILES_PATH = os.path.join(ROOT, "data", "crew_profiles.json")
PROFILE_KEYS = ("ban_la_ai", "vai_tro", "viec_lam", "chiu_trach_nhiem", "giam_sat", "dau_vao", "dau_ra")
MEASURE_KINDS = ("code", "tool", "doc", "test", "chua_co")


def load_profiles(path: Optional[str] = None) -> Dict:
    with open(path or PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _measure_real(cach_do: str, root: str) -> Optional[str]:
    """Lý do khi `cach_do` trỏ tới thứ không có (None = có / 'chua_co:' đã khai là chưa đo được)."""
    kind, _, ref = str(cach_do or "").partition(":")
    if kind not in MEASURE_KINDS or not ref:
        return f"cách đo {cach_do!r} phải là {'/'.join(MEASURE_KINDS)}:<chỗ>"
    if kind == "chua_co":
        return None
    path, _, name = ref.partition(":")
    if kind == "code" and not path.endswith(".py"):
        path += ".py"
    full = os.path.join(root, path)
    if not os.path.exists(full):
        return f"cách đo {cach_do!r}: {path} không có"
    if name and (not os.path.isfile(full) or name not in _read(path, root)):
        return f"cách đo {cach_do!r}: không thấy {name!r} trong {path}"
    return None


def link_problems(reg: Optional[Dict] = None, prof: Optional[Dict] = None, root: str = ROOT) -> List[str]:
    """Liên kết có hệ quả giữa các vai ([] = đạt) — không thiếu, không thừa:
      - mỗi vai có hồ sơ đủ mục; giam_sat là vai có thật; chuỗi quản lý (reports_to) về tới EP, không vòng;
      - mỗi sản phẩm đúng MỘT vai làm ra, vai đó khai trong outputs (crew_roles) và dau_ra (hồ sơ) — hai nơi trùng nhau;
      - mỗi sản phẩm có ≥ 1 người nhận (không thừa); người nhận là vai có thật (hoặc ngoài: external_consumers) và khai nó trong dau_vao;
      - mỗi đầu vào của vai là sản phẩm có thật CÓ ghi vai đó là người nhận (không thiếu);
      - mỗi yêu cầu của người nhận chỉ ra KPI nào của sản phẩm đáp ứng (dap_ung ∈ kpi.id);
      - mỗi KPI có ngưỡng + cách đo trỏ tới thứ có thật (code/tool/doc/test) hoặc khai 'chua_co:';
      - acceptance của vai (crew_roles) là id KPI của sản phẩm vai đó làm ra;
      - trường sản phẩm (fields) thuộc vai làm ra (bảng sở hữu trường) khi trường có vai chủ."""
    reg = reg if reg is not None else load()
    try:
        prof = prof if prof is not None else load_profiles()
    except (OSError, ValueError) as e:
        return [f"không đọc được data/crew_profiles.json: {e}"]
    out: List[str] = []
    rs = {r.get("id"): r for r in roles(reg)}
    profiles = prof.get("profiles") or {}
    products = prof.get("products") or {}
    external = set(prof.get("external_consumers") or [])
    fields = reg.get("fields") or {}
    for rid in rs:
        if rid not in profiles:
            out.append(f"vai {rid}: chưa có hồ sơ")
    for rid, p in profiles.items():
        if rid not in rs:
            out.append(f"hồ sơ {rid}: không phải vai có thật trong crew_roles.json")
            continue
        miss = [k for k in PROFILE_KEYS if k not in p or (k not in ("giam_sat", "dau_vao", "dau_ra") and not p[k])]
        if miss:
            out.append(f"vai {rid}: hồ sơ thiếu {miss}")
        for g in p.get("giam_sat") or []:
            if g not in rs:
                out.append(f"vai {rid}: giam_sat {g!r} không phải vai có thật")
        seen, cur = set(), rid
        while cur is not None and cur not in seen:
            seen.add(cur)
            cur = (rs.get(cur) or {}).get("reports_to")
        if cur is not None:
            out.append(f"vai {rid}: chuỗi quản lý có vòng ({cur})")
        elif "executive_producer" not in seen:
            out.append(f"vai {rid}: chuỗi quản lý không về tới executive_producer")
        mine = sorted(k for k, v in products.items() if v.get("producer") == rid)
        if sorted(p.get("dau_ra") or []) != mine:
            out.append(f"vai {rid}: dau_ra {sorted(p.get('dau_ra') or [])} ≠ sản phẩm vai làm ra {mine}")
        if sorted(rs[rid].get("outputs") or []) != mine:
            out.append(f"vai {rid}: outputs (crew_roles) {sorted(rs[rid].get('outputs') or [])} ≠ sản phẩm vai làm ra {mine}")
        for i in p.get("dau_vao") or []:
            if i not in products:
                out.append(f"vai {rid}: đầu vào {i!r} không phải sản phẩm có thật (THIẾU nguồn)")
            elif rid not in (products[i].get("consumers") or {}):
                out.append(f"vai {rid}: đầu vào {i!r} nhưng sản phẩm không ghi {rid} là người nhận")
        kpi_ids = {k["id"] for o in mine for k in products[o].get("kpi") or [] if isinstance(k, dict) and k.get("id")}
        for a in rs[rid].get("acceptance") or []:
            if a not in kpi_ids:
                out.append(f"vai {rid}: acceptance {a!r} không là KPI nào của sản phẩm vai làm ra")
    for pid, v in products.items():
        prod = v.get("producer")
        if prod not in rs:
            out.append(f"sản phẩm {pid}: vai làm ra {prod!r} không có thật")
        kpis = [k for k in v.get("kpi") or [] if isinstance(k, dict)]
        if len(kpis) != len(v.get("kpi") or []):
            out.append(f"sản phẩm {pid}: KPI phải là {{id, ten, nguong, cach_do}}")
        if not kpis:
            out.append(f"sản phẩm {pid}: không có KPI")
        ids = [k.get("id") for k in kpis]
        if len(ids) != len(set(ids)):
            out.append(f"sản phẩm {pid}: id KPI trùng")
        for k in kpis:
            if not k.get("nguong") or not k.get("ten"):
                out.append(f"sản phẩm {pid}: KPI {k.get('id')!r} thiếu tên / ngưỡng")
            why = _measure_real(k.get("cach_do"), root)
            if why:
                out.append(f"sản phẩm {pid}: KPI {k.get('id')!r} — {why}")
        cons = v.get("consumers") or {}
        if not cons:
            out.append(f"sản phẩm {pid}: không ai nhận (THỪA)")
        for c, reqs in cons.items():
            if c not in rs and c not in external:
                out.append(f"sản phẩm {pid}: người nhận {c!r} không có thật")
                continue
            if c == prod:
                out.append(f"sản phẩm {pid}: vai làm ra tự nhận sản phẩm của mình")
            if c in profiles and pid not in (profiles[c].get("dau_vao") or []):
                out.append(f"sản phẩm {pid}: người nhận {c} không khai trong dau_vao")
            if not reqs:
                out.append(f"sản phẩm {pid}: người nhận {c} chưa ghi đòi hỏi gì")
            for r in reqs or []:
                if not isinstance(r, dict):
                    out.append(f"sản phẩm {pid}: yêu cầu của {c} phải là {{yeu_cau, dap_ung}}")
                    continue
                if not r.get("yeu_cau"):
                    out.append(f"sản phẩm {pid}: người nhận {c} có yêu cầu trống")
                if r.get("dap_ung") not in ids:
                    out.append(f"sản phẩm {pid}: yêu cầu của {c} ({r.get('yeu_cau')!r}) không chỉ ra KPI đáp ứng có thật")
        for f in v.get("fields") or []:
            owner = (fields.get(f) or {}).get("owner")
            if owner is not None and owner != prod:
                out.append(f"sản phẩm {pid}: trường {f!r} thuộc vai {owner}, không phải vai làm ra {prod}")
    return out


def profile_gaps(prof: Optional[Dict] = None, reg: Optional[Dict] = None) -> List[str]:
    """Việc CÒN THIẾU (không phải lỗi hợp đồng): KPI chưa đo được tự động, vai sản xuất không đứng tên khâu nào."""
    prof = prof if prof is not None else load_profiles()
    reg = reg if reg is not None else load()
    out = [f"KPI {pid}.{k['id']} ({k['ten']}) chưa đo tự động — {k['cach_do'][len('chua_co:'):]}"
           for pid, v in (prof.get("products") or {}).items() for k in v.get("kpi") or [] if str(k.get("cach_do")).startswith("chua_co:")]
    for r in roles(reg):
        if r["id"] in ("executive_producer", "engineer", "continuity_validator"):
            continue
        if not (r.get("owns_errors") or {}).get("stages"):
            out.append(f"vai {r['id']} không đứng tên khâu nào (devsys/stages.json) — lỗi của vai rơi về khâu vai khác")
    return out


def hoso_text(prof: Optional[Dict] = None, reg: Optional[Dict] = None) -> str:
    """Hồ sơ từng vai dạng chữ (cho người đọc / tài liệu)."""
    prof = prof if prof is not None else load_profiles()
    reg = reg if reg is not None else load()
    products = prof.get("products") or {}
    lines = []
    for r in roles(reg):
        p = (prof.get("profiles") or {}).get(r["id"]) or {}
        lines += [f"## {r['name']} (`{r['id']}`)", "",
                  f"- **Bạn là ai:** {p.get('ban_la_ai', '')}", f"- **Vai trò:** {p.get('vai_tro', '')}",
                  "- **Làm gì:** " + "; ".join(p.get("viec_lam") or []),
                  "- **Chịu trách nhiệm:** " + "; ".join(p.get("chiu_trach_nhiem") or []),
                  f"- **Dưới quyền:** {r.get('reports_to') or '— (cao nhất)'} · **giám sát:** " + (", ".join(p.get("giam_sat") or []) or "—"),
                  "- **Đầu vào:** " + ("; ".join(f"{products[i]['ten']} ← {products[i]['producer']}" for i in p.get("dau_vao") or []
                                                 if i in products) or "—"),
                  "- **Đầu ra:**"]
        for o in p.get("dau_ra") or []:
            v = products.get(o) or {}
            lines.append(f"  - **{v.get('ten', o)}** (`{o}`)")
            for k in v.get("kpi") or []:
                lines.append(f"    - KPI `{k['id']}`: {k['ten']} — ngưỡng {k['nguong']} — đo: {k['cach_do']}")
            for c, reqs in (v.get("consumers") or {}).items():
                for q in reqs:
                    lines.append(f"    - → **{c}** cần: {q['yeu_cau']} (đáp ứng bằng `{q['dap_ung']}`)")
        lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """py -m core.crew check | hoso | owner <trường> | write <đường ghi> | route <mã QC hoặc id sổ lỗi>…  — chỉ đọc."""
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        bad = problems() + link_problems()
        for b in bad:
            print("✖", b)
        try:
            n_products = len(load_profiles().get("products") or {})
        except (OSError, ValueError):
            n_products = 0
        print(f"Role Registry: {len(roles())} vai, {len(load().get('fields') or {})} trường, {n_products} sản phẩm — {len(bad)} lỗi")
        return 1 if bad else 0
    if cmd == "hoso":
        print(hoso_text())
        gaps = profile_gaps()
        print(f"## Còn thiếu ({len(gaps)})\n" + "\n".join("- " + g for g in gaps))
        return 0
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
