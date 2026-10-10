"""Bảng luật thế giới CÓ PHẠM VI (tầng T2, A8 — docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.2 dòng "Luật thế giới", mục 5).

Chuẩn so theo tầng: T1 ý đồ shot (BYĐ + ngoai_le) → T2 luật thế giới (bảng này) → T3 lẽ thường. Khi chỉ T3 lệch mà T1/T2 im lặng, lớp
kiểm hỏi người dùng "cố ý hay lỗi?"; trả lời "cố ý" → một luật T2 CÓ PHẠM VI, có hạn dùng, có nút gỡ — và KHÔNG áp ngầm cho vật khác
(bài học "không khái quát từ 1 mẫu"): luật cho vật Kho X không khớp vật Y cùng loại; luật theo loại phải ghi rõ `loai:<tên>`.

Hai nguồn tệp (đường dẫn TUYỆT ĐỐI neo theo gốc repo, không theo cwd):
- luật chung FF đã biết: `knowledge/world_rules.json` (`pham_vi` = "chung");
- luật dự án: `<data_dir>/<id>/world_rules.json` (data_dir = tham số / biến PIPELINE_DATA / `data/projects`; tương đối → neo ROOT).

Một luật: id · vat ("kho:<mã>" | "loai:<tên>") · ngu_canh ("*" | "ky_nang:…" | "hieu_ung:…" | "phong_cach:…" | "du_an:…") · dieu (điều
mong đợi) · pham_vi ("chung" | "du_an:<id>" | {"du_an": id, "shot": [n…]}) · nguon ("nguoi_dung: …" | "tu_lieu: …") · het_han (YYYY-MM-DD,
tùy chọn) · go (đã gỡ, tùy chọn). Một lỗi = {"muc": "do" | "vang", "luat": id, "loi": "…"} — thiếu trường / tệp hỏng → báo, không im lặng.

K0b: CHƯA nối vào luồng nào (K3 đọc khi đối chiếu điều Claude khai thấy). Không gọi model.
"""
import datetime
import json
import os
import re
import tempfile
import unicodedata
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERAL_PATH = os.path.join(ROOT, "knowledge", "world_rules.json")
FILE_NAME = "world_rules.json"

REQUIRED = ("id", "vat", "ngu_canh", "dieu", "pham_vi", "nguon")
OPTIONAL = ("het_han", "go", "go_ly_do", "ngay_go", "ngay", "loai", "ghi_chu")
NGU_CANH_LOAI = ("ky_nang", "hieu_ung", "phong_cach", "du_an")
NGUON_LOAI = ("nguoi_dung", "tu_lieu")
_ID = re.compile(r"^[a-z0-9_]+$")
_VAT = re.compile(r"^(kho:\d+|loai:[a-z0-9_]+)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _norm(text) -> str:
    """So khớp CHÍNH XÁC sau NFC + chữ thường — không bỏ dấu ('van' ≠ 'vàng'), không so chuỗi con."""
    return unicodedata.normalize("NFC", str(text or "")).strip().lower()


def _issue(muc: str, luat, loi: str) -> Dict:
    return {"muc": muc, "luat": luat, "loi": loi}


# ---- đường dẫn --------------------------------------------------------------------------------------------------------------------
def data_dir_abs(data_dir: Optional[str] = None) -> str:
    """Thư mục dự án. Ưu tiên `data_dir` NGƯỜI GỌI truyền — người gọi (K3: ctx của autopilot, DATA của dashboard) phải truyền đường
    dẫn TUYỆT ĐỐI (os.path.abspath của thư mục họ đang dùng), vì nơi khác trong repo hiểu PIPELINE_DATA tương đối theo cwd còn ở đây
    tương đối bị neo theo ROOT của mã (bản sao thử có cwd khác → hai nơi lệch thư mục). Không truyền → PIPELINE_DATA → data/projects."""
    d = data_dir or os.environ.get("PIPELINE_DATA") or os.path.join("data", "projects")
    return os.path.normpath(d if os.path.isabs(d) else os.path.join(ROOT, d))


def project_path(du_an: int, data_dir: Optional[str] = None) -> str:
    return os.path.join(data_dir_abs(data_dir), str(int(du_an)), FILE_NAME)


# ---- phạm vi --------------------------------------------------------------------------------------------------------------------
def _scope(pham_vi) -> Optional[Tuple[str, Optional[int], Tuple[int, ...]]]:
    """→ ("chung", None, ()) | ("du_an", id, ()) | ("shot", id, (shots…)); None = sai dạng."""
    if pham_vi == "chung":
        return ("chung", None, ())
    if isinstance(pham_vi, str):
        m = re.fullmatch(r"du_an:(\d+)", pham_vi.strip())
        return ("du_an", int(m.group(1)), ()) if m else None
    if isinstance(pham_vi, dict) and set(pham_vi) == {"du_an", "shot"}:
        du_an, shots = pham_vi.get("du_an"), pham_vi.get("shot")
        if isinstance(du_an, int) and not isinstance(du_an, bool) and isinstance(shots, list) and shots \
                and all(isinstance(s, int) and not isinstance(s, bool) for s in shots):
            return ("shot", du_an, tuple(shots))
    return None


def validate_rule(rule) -> List[Dict]:
    if not isinstance(rule, dict):
        return [_issue("do", None, "luật phải là bảng")]
    rid = rule.get("id")
    out = [_issue("do", rid, f"thiếu '{k}'") for k in REQUIRED if rule.get(k) in (None, "", [], {})]
    for k in rule:
        if k not in REQUIRED and k not in OPTIONAL:
            out.append(_issue("do", rid, f"trường lạ '{k}' (cho phép: {', '.join(REQUIRED + OPTIONAL)})"))
    if rid and not (isinstance(rid, str) and _ID.match(rid)):
        out.append(_issue("do", rid, "id: chữ thường, số, '_'"))
    if rule.get("vat") and not (isinstance(rule["vat"], str) and _VAT.match(rule["vat"])):
        out.append(_issue("do", rid, f"vat '{rule['vat']}' phải là 'kho:<mã>' hoặc 'loai:<tên chữ thường không dấu>'"))
    nc = rule.get("ngu_canh")
    if nc and nc != "*" and not (isinstance(nc, str) and nc.split(":", 1)[0] in NGU_CANH_LOAI and nc.split(":", 1)[-1].strip()
                                 and ":" in nc):
        out.append(_issue("do", rid, f"ngu_canh '{nc}' phải là '*' hoặc '<{'|'.join(NGU_CANH_LOAI)}>:<tên>'"))
    if rule.get("dieu") is not None and not str(rule.get("dieu")).strip():
        out.append(_issue("do", rid, "dieu rỗng"))
    if rule.get("pham_vi") not in (None, "") and _scope(rule["pham_vi"]) is None:
        out.append(_issue("do", rid, "pham_vi phải là 'chung' | 'du_an:<id>' | {'du_an': id, 'shot': [n, …]} (≥ 1 shot)"))
    src = rule.get("nguon")
    if src and not (isinstance(src, str) and src.split(":", 1)[0].strip() in NGUON_LOAI and ":" in src
                    and src.split(":", 1)[1].strip()):
        out.append(_issue("do", rid, "nguon phải là 'nguoi_dung: …' (trả lời 'cố ý hay lỗi') hoặc 'tu_lieu: …'"))
    for k in ("het_han", "ngay_go", "ngay"):
        if rule.get(k) not in (None, "") and not (isinstance(rule[k], str) and _DATE.match(rule[k])):
            out.append(_issue("do", rid, f"{k} phải là YYYY-MM-DD"))
    if "go" in rule and not isinstance(rule["go"], bool):
        out.append(_issue("do", rid, "go phải là true/false"))
    return out


# ---- tải ------------------------------------------------------------------------------------------------------------------------
def _read(path: str) -> Tuple[Optional[Dict], List[Dict]]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        return None, [_issue("do", None, f"{path}: JSON hỏng ({e})")]
    if not isinstance(data, dict) or not isinstance(data.get("luat"), list):
        return None, [_issue("do", None, f"{path}: cần {{'version': 1, 'luat': [...]}}")]
    return data, []


def load_file(path: str, required: bool = False, du_an: Optional[int] = None) -> Tuple[List[Dict], List[Dict]]:
    """→ (luật hợp lệ, lỗi). Luật sai bị loại VÀ báo. `du_an` = tệp của dự án đó: chỉ nhận luật phạm vi dự án ấy; None = tệp chung:
    chỉ nhận 'chung'. Tệp không có: lỗi nếu `required` (tệp chung), không thì rỗng hợp lệ (dự án chưa có luật nào)."""
    if not os.path.exists(path):
        return [], ([_issue("do", None, f"không có tệp luật {path}")] if required else [])
    data, issues = _read(path)
    if data is None:
        return [], issues
    rules, seen = [], set()
    for r in data["luat"]:
        bad = validate_rule(r)
        if not bad:
            sc = _scope(r["pham_vi"])
            if du_an is None and sc[0] != "chung":
                bad = [_issue("do", r["id"], "tệp luật chung chỉ nhận pham_vi 'chung'")]
            elif du_an is not None and (sc[0] == "chung" or sc[1] != int(du_an)):
                bad = [_issue("do", r["id"], f"tệp dự án {du_an} chỉ nhận luật phạm vi dự án {du_an}")]
            elif r["id"] in seen:
                bad = [_issue("do", r["id"], "trùng id")]
        if bad:
            issues += bad
            continue
        seen.add(r["id"])
        rules.append(r)
    return rules, issues


def load_project(du_an: int, data_dir: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    return load_file(project_path(du_an, data_dir), required=False, du_an=du_an)


def load_all(du_an: Optional[int] = None, data_dir: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    rules, issues = load_file(GENERAL_PATH, required=True)
    if du_an is not None:
        r2, i2 = load_project(du_an, data_dir)
        ids = {r["id"] for r in rules}
        for r in r2:
            if r["id"] in ids:
                i2.append(_issue("do", r["id"], "trùng id với luật chung"))
        rules, issues = rules + [r for r in r2 if r["id"] not in ids], issues + i2
    return rules, issues


# ---- tìm ------------------------------------------------------------------------------------------------------------------------
def tim(rules: List[Dict], vat: str, ngu_canh: Optional[str] = None, du_an: Optional[int] = None, shot: Optional[int] = None,
        loai: Optional[str] = None, hom_nay: Optional[str] = None) -> List[Dict]:
    """Luật áp dụng cho vật `vat` ("kho:<mã>"), cụ thể nhất trước: phạm vi (shot > dự án > chung) → vật (đúng mã Kho > theo loại) →
    ngữ cảnh (đúng tên > '*'). Luật theo loại chỉ khớp khi người hỏi KHAI `loai`; luật cho mã Kho khác không bao giờ khớp. Không biết
    shot / ngữ cảnh → luật chỉ cho shot / ngữ cảnh cụ thể KHÔNG áp. Luật đã gỡ hoặc hết hạn bị bỏ."""
    today = hom_nay or datetime.date.today().isoformat()
    want_vat = _norm(vat)
    want_loai = f"loai:{_norm(loai)}" if loai else None
    want_nc = _norm(ngu_canh) if ngu_canh else None
    hits = []
    for r in rules or []:
        if r.get("go") or (r.get("het_han") and str(r["het_han"]) < today):
            continue
        rv = _norm(r.get("vat"))
        if rv == want_vat:
            s_vat = 2
        elif want_loai and rv == want_loai:
            s_vat = 1
        else:
            continue
        rn = _norm(r.get("ngu_canh"))
        if rn == "*":
            s_nc = 0
        elif want_nc and rn == want_nc:
            s_nc = 1
        else:
            continue
        sc = _scope(r.get("pham_vi"))
        if sc is None:
            continue
        if sc[0] == "chung":
            s_pv = 1
        elif du_an is None or sc[1] != int(du_an):
            continue
        elif sc[0] == "du_an":
            s_pv = 2
        elif shot is not None and shot in sc[2]:
            s_pv = 3
        else:
            continue
        hits.append(((s_pv, s_vat, s_nc), r))
    hits.sort(key=lambda x: x[0], reverse=True)              # sort ổn định: cùng mức giữ thứ tự tệp
    return [r for _, r in hits]


# ---- thêm / gỡ (ghi nguyên tử) ---------------------------------------------------------------------------------------------------
def _write(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # tệp tạm TÊN DUY NHẤT trong cùng thư mục (os.replace nguyên tử chỉ khi cùng ổ) — tên cố định '<tệp>.tmp' đụng nhau khi hai người ghi
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".part", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _load_for_write(path: str) -> Tuple[Optional[Dict], List[Dict]]:
    if not os.path.exists(path):
        return {"version": 1, "luat": []}, []
    return _read(path)


def add(path: str, rule: Dict, du_an: Optional[int] = None) -> List[Dict]:
    """Thêm một luật vào tệp `path` (du_an = tệp của dự án đó; None = tệp chung). → lỗi (rỗng = đã ghi). Không ghi đè id trùng."""
    issues = validate_rule(rule)
    if not issues:
        sc = _scope(rule["pham_vi"])
        if du_an is None and sc[0] != "chung":
            issues = [_issue("do", rule["id"], "tệp luật chung chỉ nhận pham_vi 'chung'")]
        elif du_an is not None and (sc[0] == "chung" or sc[1] != int(du_an)):
            issues = [_issue("do", rule["id"], f"tệp dự án {du_an} chỉ nhận luật phạm vi dự án {du_an}")]
    if issues:
        return issues
    data, issues = _load_for_write(path)
    if data is None:
        return issues
    if any(r.get("id") == rule["id"] for r in data["luat"]):
        return [_issue("do", rule["id"], "trùng id — gỡ luật cũ hoặc đặt id khác")]
    data["luat"].append(dict(rule, ngay=rule.get("ngay") or datetime.date.today().isoformat()))
    _write(path, data)
    return []


def remove(path: str, rule_id: str, ly_do: str) -> List[Dict]:
    """Gỡ = đánh dấu go=true + lý do + ngày (giữ lịch sử, không xóa). → lỗi (rỗng = đã ghi)."""
    if not str(ly_do or "").strip():
        return [_issue("do", rule_id, "gỡ luật phải có lý do")]
    if not os.path.exists(path):
        return [_issue("do", rule_id, f"không có tệp luật {path}")]
    data, issues = _read(path)
    if data is None:
        return issues
    for r in data["luat"]:
        if isinstance(r, dict) and r.get("id") == rule_id:
            r.update(go=True, go_ly_do=str(ly_do).strip(), ngay_go=datetime.date.today().isoformat())
            _write(path, data)
            return []
    return [_issue("do", rule_id, "không có luật id này")]
