"""File điểm của AI Development System: kiểm, chuẩn hóa, lưu, gộp.

Điểm luôn do code tính lại từ các khoản trừ (người chấm AI, người chấm ngoài hay file sửa tay đều như nhau), rồi áp giới hạn do code
(thang: devsys/rubric.md). Một file = một khu vực của một lần chấm: devsys/data/scores/<giờ>_<khu_vực>.json
"""
import ast
import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from . import collect

FORMAT = "devsys-score/1"              # thang bản 1 (2026-09-26): 6 tiêu chí, người chấm tự ghi số điểm trừ
FORMAT_V2 = "devsys-score/2"           # thang bản 2 (2026-10-03): 8 tiêu chí, mức nghiêm trọng, khoản trừ tự động, checklist lỗi đã gặp
FORMAT_V21 = "devsys-score/2.1"        # thang bản 2.1 (S14.10, 2026-10-06): + K11/K12, `db:` cho khoản tự động, khu vực chỉ tài liệu không chấm test
FORMATS = (FORMAT, FORMAT_V2, FORMAT_V21)
V2_FORMATS = (FORMAT_V2, FORMAT_V21)
CURRENT_VERSION = 2.1                  # câu trả lời MỚI (chấm bằng API, nhập từ người chấm ngoài) luôn kiểm theo thang hiện tại
CRITERIA: Tuple[Tuple[str, str, int], ...] = (
    ("chuc_nang", "Hoàn thiện chức năng", 30),
    ("bang_chung", "Bằng chứng chạy thật", 20),
    ("test", "Test", 15),
    ("tuan_thu", "Tuân thủ CHUAN_XAY_DUNG", 15),
    ("trai_nghiem", "Trải nghiệm người dùng", 10),
    ("tai_lieu", "Tài liệu khớp code", 10),
)
CRITERIA_MAX = {k: m for k, _, m in CRITERIA}
CRITERIA_LABEL = {k: n for k, n, _ in CRITERIA}
CRITERIA_V2: Tuple[Tuple[str, str, int], ...] = (
    ("chuc_nang", "Hoàn thiện chức năng", 26),
    ("bang_chung", "Bằng chứng chạy thật & đo chất lượng đầu ra", 16),
    ("test", "Test", 12),
    ("tuan_thu", "Tuân thủ CHUAN_XAY_DUNG", 8),
    ("tin_cay", "Độ tin cậy & an toàn (lỗi, tiền, quyền, bí mật)", 12),
    ("bao_tri", "Khả năng bảo trì", 8),
    ("trai_nghiem", "Trải nghiệm người dùng", 10),
    ("tai_lieu", "Tài liệu khớp code", 8),
)
CRITERIA_MAX_V2 = {k: m for k, _, m in CRITERIA_V2}
CRITERIA_LABEL_V2 = {k: n for k, n, _ in CRITERIA_V2}
SEVERITY = ("chan", "lon", "nho")                           # chặn / lớn / nhỏ — điểm trừ do CODE gán theo mức, không do người chấm
SEVERITY_FRACTION = {"chan": 0.35, "lon": 0.12, "nho": 0.04}  # tỉ lệ điểm tối đa của tiêu chí bị trừ cho một khoản
SEVERITY_LABEL = {"chan": "Chặn", "lon": "Lớn", "nho": "Nhỏ"}
CHAN_CAPS = ((2, 79.0), (1, 89.0))                          # ≥ 2 khoản chặn → khu vực ≤ 79; ≥ 1 → ≤ 89
DRIFT_LIMIT = 5.0                                           # chênh điểm (chưa tính khoản trừ tự động) so với lần chấm trước phải có giải thích
UI_NO_MEASURE_CAP = 6.0                                     # khu vực có số đo giao diện thật mà chưa có file đo: trai_nghiem tối đa
CHECKLIST: Tuple[Tuple[str, str], ...] = (                  # các LOẠI lỗi đã từng gặp (B1–B6 của 01/10 + lỗi người chấm 26/09) — phải trả lời hết
    ("K1_khai_bao_chung", "Bảng/danh mục khai báo chung (khâu Claude, cờ, giá, luật model, bản đồ khu vực) không khớp nơi dùng thật (B1, B6)"),
    ("K2_cong_do_sai", "Công thức đo / cổng tin cậy / ngưỡng sai mẫu số, sai chiều so sánh, tự bỏ qua cổng (B2)"),
    ("K3_rang_buoc_ben_ngoai", "Ràng buộc của nhà cung cấp (tỉ lệ ảnh, độ dài, định dạng) không kiểm trước khi gửi tốn tiền (B3)"),
    ("K4_dien_giai_dau_ra_model", "Code diễn giải đầu ra LLM/QC sai ở biên (vd. dòng chữ trên màn bị coi là nhân vật) (B4)"),
    ("K5_du_lieu_mat", "File/dữ liệu tham chiếu mất, lỗi lặp lại mà giao diện không có đường sửa (B5)"),
    ("K6_bo_do_sot", "Bộ đo/dò (devsys, diag, QC) bỏ sót một cách viết hợp lệ nên báo sai (B6)"),
    ("K7_tien_ngoai_so", "Lời gọi tốn tiền không qua sổ chi / ước tính trước / trần (đường phụ, thí nghiệm, nút Claude)"),
    ("K8_im_lang", "Nuốt lỗi, bỏ qua đầu vào thiếu mà không báo (cảnh báo diag / thông báo người dùng)"),
    ("K9_quyen_bi_mat", "Quyền theo dự án (core/access.py), khóa/API key, dữ liệu web/ngoài coi là đáng tin"),
    ("K10_giao_dien_do_that", "Giao diện chưa đo thật: tương phản, cỡ chữ, số click, hiệu năng, màn quá nhiều nút"),
    ("K11_vong_doi_job", "Vòng đời job: job kẹt / gửi lại / hủy không tới nhà cung cấp / không dừng khi lỗi (rà soát B1, 04/10)"),
    ("K12_pha_huy_truoc_ban_moi", "Phá hủy-trước-khi-có-bản-mới: xóa / ghi đè bản cũ trước khi bản mới chắc chắn có (mất dữ liệu nếu bước sau lỗi)"),
)
CHECKLIST_IDS = tuple(k for k, _ in CHECKLIST)
CHECKLIST_IDS_V20 = CHECKLIST_IDS[:10]                      # bản 2 (03/10) chỉ hỏi K1–K10: file điểm cũ không bị từ chối vì thiếu K11/K12
CHECKLIST_CRITERION = {                                     # S8: tiêu chí MẶC ĐỊNH của khoản trừ mỗi loại lỗi (người chấm đổi được nếu có lý do)
    "K1_khai_bao_chung": "bao_tri", "K2_cong_do_sai": "tin_cay", "K3_rang_buoc_ben_ngoai": "tin_cay", "K4_dien_giai_dau_ra_model": "chuc_nang",
    "K5_du_lieu_mat": "trai_nghiem", "K6_bo_do_sot": "bang_chung", "K7_tien_ngoai_so": "tuan_thu", "K8_im_lang": "tuan_thu",
    "K9_quyen_bi_mat": "tin_cay", "K10_giao_dien_do_that": "trai_nghiem", "K11_vong_doi_job": "tin_cay", "K12_pha_huy_truoc_ban_moi": "tin_cay"}
CHECKLIST_ANSWERS = ("co", "khong", "khong_ap_dung")
REAL_RUN_PLACES = ("TODO.md", "PLAN.md", "docs/", "data/", "tests/fixtures/", "research/", "eval/")
_LINE_REF = re.compile(r"^(?P<path>[^\s:]+?)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$")


class ScoreError(ValueError):
    """A score answer / file that does not follow the format (the scorer is asked again once, a file is refused)."""


def rubric_hash(root: str = collect.ROOT) -> str:
    try:
        with open(os.path.join(root, "devsys", "rubric.md"), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "khong-co-rubric"


def scores_dir(root: str = collect.ROOT) -> str:
    return os.path.join(collect.data_dir(root), "scores")


def _test_ref_problem(item: str, root: str) -> Optional[str]:
    """S14.10 S2: `test:tests/x.py[::Lớp][::tên]` names a test that EXISTS — the file, then each name read with ast (a class, then a
    function inside it; `[param]` of a parametrised test is ignored). A lone name may be a top-level function or a method of any class
    (the bundle used to print failing tests as file::method)."""
    parts = [p.strip() for p in item[5:].strip().strip("`").split("::")]
    path = parts[0]
    if not (path.startswith("tests/") and path.endswith(".py")):
        return "không đúng dạng test:tests/<file>.py::Lớp::tên"
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return f"không có file test {path}"
    names = [re.sub(r"\[.*\]$", "", n) for n in parts[1:] if n]
    if not names:
        return None
    try:
        with open(full, encoding="utf-8", errors="replace") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError, ValueError) as e:
        return f"không đọc được {path} ({type(e).__name__})"
    defs = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    scope = tree.body
    for i, n in enumerate(names):
        found = next((x for x in scope if isinstance(x, defs) and x.name == n), None)
        if found is None and i == 0 and len(names) == 1:
            found = next((m for c in tree.body if isinstance(c, ast.ClassDef) for m in c.body if isinstance(m, defs) and m.name == n), None)
        if found is None:
            return f"không có {'::'.join(names[:i + 1])} trong {path}"
        scope = found.body if isinstance(found, ast.ClassDef) else []
    return None


def check_evidence(item: str, root: str, todo_lines: Optional[int] = None) -> Optional[str]:
    """None when an evidence string can be verified in the repo, else why not."""
    item = str(item).strip()
    if not item:
        return "rỗng"
    if item.startswith("db:"):                    # thang 2.1 (Đợt 6b): a row of the real database — only code's automatic deductions cite it
        return "db: chỉ dành cho khoản trừ tự động do code đo (người chấm dẫn file:dòng / test: / flag: / absent:)"
    if item.startswith(("test:", "flag:", "absent:")):
        if item.startswith("test:"):
            return _test_ref_problem(item, root)
        if item.startswith("flag:"):
            name = item[5:].strip()
            if name not in collect.read_features(root):
                return f"không có cờ {name} trong core/features.py"
        return None
    m = _LINE_REF.match(item)
    if not m:
        return "không đúng dạng file:dòng"
    path = m.group("path").strip("`")
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return f"không có file {path}"
    if m.group("a"):
        n = collect.line_count(full)
        last = int(m.group("b") or m.group("a"))
        if last > n or int(m.group("a")) < 1:
            return f"dòng {last} vượt độ dài {path} ({n} dòng)"
    return None


def _as_list(v) -> List[str]:
    return [str(x) for x in v] if isinstance(v, list) else [str(v)] if v else []


def _is_real_run_ref(item: str) -> bool:
    path = str(item).split(":")[0].strip("`")
    return any(path == p or path.startswith(p) for p in REAL_RUN_PLACES)


REAL_RUN_SIGN = re.compile(r"\d|đã chạy|chạy thật|đã thử|đo được|nghe thật|xem thật", re.I)
_TEXT_EXT = (".md", ".txt", "")
_AREA_TERMS: Dict[str, Tuple] = {}


def _area_terms(root: str, area: str) -> List[re.Pattern]:
    """The words that name an area (id, name, keywords of devsys/areas.json of `root`) — read once per file version."""
    path = os.path.join(root, "devsys", "areas.json")
    try:
        stamp = os.stat(path).st_mtime_ns
    except OSError:
        stamp = None
    key = f"{path}|{area}"
    if key not in _AREA_TERMS or _AREA_TERMS[key][0] != stamp:
        words = [area]
        try:
            with open(path, encoding="utf-8") as f:
                for a in json.load(f).get("areas", []):
                    if a.get("id") == area:
                        words += [a.get("name", "")] + list(a.get("keywords", []))
        except (OSError, ValueError):
            pass
        rx = [re.compile(r"(?<!\w)" + re.escape(collect.nfc(w)) + r"(?!\w)", re.I) for w in words if str(w).strip()]
        _AREA_TERMS[key] = (stamp, rx)
    return _AREA_TERMS[key][1]


def real_run_problem(item: str, root: str, area: str) -> Optional[str]:
    """S14.10 S15: None when `item` cites a record of a REAL run: a place where runs are written down (REAL_RUN_PLACES), a line number
    for a text file, and among the cited lines (headings, blank lines and table rules left out) one with a sign of a real run — a
    number / date, 'đã chạy', 'chạy thật'… — or naming the area. A data file (json, image…) under data/ or eval/ counts as a whole."""
    item = str(item).strip()
    if not _is_real_run_ref(item):
        return "không trỏ tới nơi ghi lần chạy thật (TODO.md / docs / PLAN.md / data / tests/fixtures / research / eval)"
    why = check_evidence(item, root)
    if why:
        return why
    m = _LINE_REF.match(item)
    path = m.group("path").strip("`")
    if os.path.splitext(path)[1].lower() not in _TEXT_EXT:
        return None                                   # a data file / fixture (json, csv, image…) recorded from a run: the file is the record
    if not m.group("a"):
        return "thiếu số dòng: trích dòng ghi lần chạy thật (file:dòng)"
    a = int(m.group("a"))
    b = min(int(m.group("b") or a), a + 40)
    try:
        with open(os.path.join(root, path), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()[a - 1:b]
    except OSError as e:
        return f"không đọc được {path} ({type(e).__name__})"
    body = [collect.nfc(x.strip()) for x in lines if x.strip() and not x.lstrip().startswith("#") and not re.fullmatch(r"[|:\-\s]+", x)]
    if not body:
        return "dòng trống / tiêu đề — không phải ghi chép chạy thật"
    text = " ".join(body)
    if REAL_RUN_SIGN.search(text) or any(r.search(text) for r in _area_terms(root, area)):
        return None
    return "dòng không có dấu hiệu chạy thật (số / ngày / 'đã chạy') và không nhắc tên khu vực"


FEEDBACK_TEXT = ("why", "fix", "verify")
EFFORTS = ("💻", "💵", "👤")


def feedback_of(fb) -> Optional[Dict]:
    """S8.1: the optional `feedback` of a deduction (devsys/feedback_format.md), kept only in its known shape — never refuses a score
    (an old / partial feedback is trimmed, not an error)."""
    if not isinstance(fb, dict):
        return None
    out: Dict = {k: str(fb[k]).strip()[:600] for k in FEEDBACK_TEXT if str(fb.get(k) or "").strip()}
    files = fb.get("files")
    if isinstance(files, list):
        out["files"] = [str(f) for f in files if str(f).strip()][:10]
    if fb.get("effort") in EFFORTS:
        out["effort"] = fb["effort"]
    try:
        pr = int(fb.get("priority"))
        if 1 <= pr <= 3:
            out["priority"] = pr
    except (TypeError, ValueError):
        pass
    return out or None


def version_of(raw: Dict, hint: Optional[str] = None) -> int:
    """Which rubric a score answer follows: its own `format`, else the format of the file that holds it (`hint`), else by shape
    (a `tin_cay` criterion = bản 2). Answers without any hint are bản 1 (the old tests / old files)."""
    for f in (raw.get("format") if isinstance(raw, dict) else None, hint):
        if f == FORMAT_V21:
            return 2.1
        if f == FORMAT_V2:
            return 2
        if f == FORMAT:
            return 1
    crit = raw.get("criteria") if isinstance(raw, dict) else None
    return 2 if isinstance(crit, dict) and "tin_cay" in crit else 1


def is_v2(rec: Optional[Dict]) -> bool:
    """A stored score of bản 2 or 2.1 (same 8 criteria, severities, automatic deductions)."""
    return bool(rec) and rec.get("format") in V2_FORMATS


def scale_label(rec: Optional[Dict]) -> str:
    f = (rec or {}).get("format")
    return "bản 2.1" if f == FORMAT_V21 else "bản 2" if f == FORMAT_V2 else "bản 1"


def criteria_of(rec: Dict) -> Tuple[Tuple[str, str, int], ...]:
    """The criteria (key, label, max) a stored score was computed with."""
    return CRITERIA_V2 if is_v2(rec) else CRITERIA


def normalize(raw: Dict, root: str = collect.ROOT, area_ids: Optional[Sequence[str]] = None, facts: Optional[Dict] = None,
              prev: Optional[Dict] = None, version: Optional[int] = None) -> Dict:
    """Validate a scorer answer / score file and compute the score. Raises ScoreError on a structural problem.

    facts (from the collector, optional): {"test_files": int, "has_run": bool, "failed": int} (+ for bản 2 "auto", "ui_*") — used for the
    code caps and the automatic deductions. prev (bản 2, optional): the area's previous score of the same rubric, for the stability rule.
    The version is the answer's own (see version_of) unless `version` forces it."""
    if not isinstance(raw, dict):
        raise ScoreError("câu trả lời phải là một object JSON")
    ver = version or version_of(raw)
    if ver >= 2:
        return _normalize_v2(raw, root, area_ids, facts, prev, minor=1 if ver >= 2.1 else 0)
    return _normalize_v1(raw, root, area_ids, facts)


def _normalize_v1(raw: Dict, root: str = collect.ROOT, area_ids: Optional[Sequence[str]] = None, facts: Optional[Dict] = None) -> Dict:
    """Bản 1 (frozen: old score files keep the score they were given)."""
    area = raw.get("area")
    if not isinstance(area, str) or not area:
        raise ScoreError("thiếu 'area'")
    if area_ids is not None and area not in area_ids:
        raise ScoreError(f"khu vực '{area}' không có trong devsys/areas.json")
    crit = raw.get("criteria")
    if not isinstance(crit, dict):
        raise ScoreError("thiếu 'criteria' (object 6 tiêu chí)")
    missing = [k for k in CRITERIA_MAX if k not in crit]
    if missing:
        raise ScoreError(f"thiếu tiêu chí: {', '.join(missing)}")
    out_crit, unverified, caps = {}, [], []
    for key, mx in CRITERIA_MAX.items():
        c = crit[key] if isinstance(crit[key], dict) else {}
        deds = c.get("deductions", [])
        if not isinstance(deds, list):
            raise ScoreError(f"{key}.deductions phải là danh sách")
        clean = []
        for i, d in enumerate(deds):
            if not isinstance(d, dict):
                raise ScoreError(f"{key}.deductions[{i}] phải là object")
            try:
                pts = float(d.get("points"))
            except (TypeError, ValueError):
                raise ScoreError(f"{key}.deductions[{i}].points phải là số") from None
            if pts <= 0:
                raise ScoreError(f"{key}.deductions[{i}].points phải > 0 (số điểm bị trừ)")
            ev = d.get("evidence")
            if isinstance(ev, str):
                ev = [ev]
            if not ev or not isinstance(ev, list):
                raise ScoreError(f"{key}.deductions[{i}] không có bằng chứng ('evidence') — mọi khoản trừ phải có bằng chứng")
            reason = str(d.get("reason") or "").strip()
            if not reason:
                raise ScoreError(f"{key}.deductions[{i}] thiếu 'reason'")
            bad = [(e, check_evidence(e, root)) for e in ev]
            for e, why in bad:
                if why:
                    unverified.append({"criterion": key, "evidence": e, "why": why})
            item = {"points": round(pts, 1), "reason": reason, "evidence": [str(e) for e in ev],
                    "unverified": [e for e, why in bad if why]}
            fb = feedback_of(d.get("feedback"))
            if fb:
                item["feedback"] = fb
            clean.append(item)
        ev_for = c.get("evidence_for") or []
        if isinstance(ev_for, str):
            ev_for = [ev_for]
        score = max(0.0, mx - sum(d["points"] for d in clean))
        crit_caps = []
        if key == "bang_chung" and score > 0:
            ok = [e for e in ev_for if _is_real_run_ref(e) and not check_evidence(e, root)]
            if not ok:
                crit_caps.append("code hạ về 0: không có trích dẫn chạy thật kiểm được (TODO.md / docs / data / tests/fixtures) trong evidence_for")
                score = 0.0
        if key == "test" and facts is not None:
            limit = None
            if facts.get("test_files", 0) == 0:
                limit, why = 3, "không có test file nào nhắm vào khu vực"
            elif not facts.get("has_run"):
                limit, why = 8, "chưa có lần chạy test lưu lại"
            elif facts.get("failed", 0) > 0:
                limit, why = 7, f"lần chạy mới nhất có {facts['failed']} test của khu vực lỗi"
            if limit is not None and score > limit:
                crit_caps.append(f"code giới hạn {limit}/{mx}: {why}")
                score = float(limit)
        caps += [f"{key}: {c_}" for c_ in crit_caps]
        out_crit[key] = {"score": round(score, 1), "max": mx, "deductions": clean, "evidence_for": [str(e) for e in ev_for],
                         "code_caps": crit_caps}
    total = round(sum(c["score"] for c in out_crit.values()), 1)
    checks = raw.get("can_kiem_lai") or []
    if not isinstance(checks, list):
        raise ScoreError("'can_kiem_lai' phải là danh sách")
    checks = [c if isinstance(c, dict) else {"what": str(c)} for c in checks]
    return {"format": FORMAT, "area": area, "score": total, "criteria": out_crit, "can_kiem_lai": checks,
            "summary": str(raw.get("summary") or "").strip(), "unverified_evidence": unverified, "code_caps": caps}


def severity_points(severity: str, mx: float) -> float:
    """Points a deduction of this severity costs in a criterion worth `mx` — fixed by code (SEVERITY_FRACTION), never by the scorer."""
    return round(mx * SEVERITY_FRACTION[severity], 1)


def _hard_evidence(e: str, root: str) -> bool:
    """A `chan` (blocking) deduction needs evidence a person can open and see: a verified file:line or a test name."""
    e = str(e).strip()
    if e.startswith(("flag:", "absent:")) or check_evidence(e, root):
        return False
    return e.startswith("test:") or bool(re.search(r":\d+(?:-\d+)?$", e))


def _checklist(raw_cl, deductions_by_loai: Dict[str, int], ids: Sequence[str] = CHECKLIST_IDS) -> List[Dict]:
    """The scorer's answer to every known bug class (CHECKLIST): all must be answered; 'co' needs a deduction tagged with that class."""
    if not isinstance(raw_cl, dict):
        raise ScoreError("thiếu 'checklist' (object trả lời đủ các loại lỗi đã gặp — xem thang, mục Checklist): " + ", ".join(ids))
    missing = [k for k in ids if k not in raw_cl]
    if missing:
        raise ScoreError(f"checklist thiếu: {', '.join(missing)}")
    out = []
    for key, label in [(k, lb) for k, lb in CHECKLIST if k in ids]:
        a = raw_cl[key] if isinstance(raw_cl[key], dict) else {}
        ans = str(a.get("tra_loi") or "").strip().lower()
        if ans not in CHECKLIST_ANSWERS:
            raise ScoreError(f"checklist.{key}.tra_loi phải là một trong {', '.join(CHECKLIST_ANSWERS)}")
        note = str(a.get("ghi_chu") or "").strip()
        if len(note) < 8:
            raise ScoreError(f"checklist.{key}.ghi_chu: ghi đã tìm ở đâu / vì sao không áp dụng (≥ 8 ký tự)")
        linked = deductions_by_loai.get(key, 0)
        if ans == "co" and not linked:
            raise ScoreError(f"checklist.{key} trả lời 'co' nhưng không có khoản trừ nào có loai=\"{key}\" — thêm khoản trừ (lỗi phải thành việc sửa)")
        ev = a.get("evidence") or []
        out.append({"id": key, "label": label, "tra_loi": ans, "ghi_chu": note[:400], "evidence": [str(e) for e in ev] if isinstance(ev, list) else [str(ev)],
                    "khoan_tru": linked})
    return out


def _normalize_v2(raw: Dict, root: str, area_ids: Optional[Sequence[str]], facts: Optional[Dict], prev: Optional[Dict], minor: int = 0) -> Dict:
    """Bản 2: người chấm chỉ PHÂN LOẠI khoản trừ (muc = chan / lon / nho, loai = loại lỗi) và dẫn bằng chứng; điểm trừ do code gán theo mức
    (severity_points), cộng khoản trừ TỰ ĐỘNG do code đo (facts["auto"]), áp giới hạn, kiểm checklist lỗi đã gặp và độ ổn định."""
    area = raw.get("area")
    if not isinstance(area, str) or not area:
        raise ScoreError("thiếu 'area'")
    if area_ids is not None and area not in area_ids:
        raise ScoreError(f"khu vực '{area}' không có trong devsys/areas.json")
    crit = raw.get("criteria")
    if not isinstance(crit, dict):
        raise ScoreError("thiếu 'criteria' (object 8 tiêu chí)")
    missing = [k for k in CRITERIA_MAX_V2 if k not in crit]
    if missing:
        raise ScoreError(f"thiếu tiêu chí: {', '.join(missing)}")
    facts = facts or {}
    auto_by: Dict[str, List[Dict]] = {}
    for a in facts.get("auto") or []:
        auto_by.setdefault(a.get("criterion"), []).append(a)
    out_crit, unverified, caps, by_loai = {}, [], [], {}
    sev_count = {s: 0 for s in SEVERITY}
    auto_points = 0.0
    for key, mx in CRITERIA_MAX_V2.items():
        c = crit[key] if isinstance(crit[key], dict) else {}
        deds = c.get("deductions", [])
        if not isinstance(deds, list):
            raise ScoreError(f"{key}.deductions phải là danh sách")
        clean = []
        for i, d in enumerate(deds):
            if not isinstance(d, dict):
                raise ScoreError(f"{key}.deductions[{i}] phải là object")
            sev = str(d.get("muc") or "").strip().lower()
            if sev not in SEVERITY:
                raise ScoreError(f"{key}.deductions[{i}].muc phải là một trong {', '.join(SEVERITY)} (mức nghiêm trọng; điểm trừ do code gán)")
            ev = d.get("evidence")
            if isinstance(ev, str):
                ev = [ev]
            if not ev or not isinstance(ev, list):
                raise ScoreError(f"{key}.deductions[{i}] không có bằng chứng ('evidence') — mọi khoản trừ phải có bằng chứng")
            reason = str(d.get("reason") or "").strip()
            if not reason:
                raise ScoreError(f"{key}.deductions[{i}] thiếu 'reason'")
            loai = str(d.get("loai") or "khac").strip()
            if loai != "khac" and loai not in CHECKLIST_IDS:
                raise ScoreError(f"{key}.deductions[{i}].loai '{loai}' không có trong checklist (dùng một mã K… hoặc 'khac')")
            bad = [(e, check_evidence(e, root)) for e in ev]
            for e, why in bad:
                if why:
                    unverified.append({"criterion": key, "evidence": e, "why": why})
            note = None
            if sev == "chan" and not any(_hard_evidence(e, root) for e in ev):
                sev = "lon"                          # a blocker must be provable: otherwise code treats it as 'lớn'
                note = "hạ từ 'chặn' xuống 'lớn': không có bằng chứng file:dòng / test kiểm được"
                caps.append(f"{key}: {note} ({reason[:60]})")
            sev_count[sev] += 1
            by_loai[loai] = by_loai.get(loai, 0) + 1
            item = {"points": severity_points(sev, mx), "muc": sev, "loai": loai, "reason": reason, "evidence": [str(e) for e in ev],
                    "unverified": [e for e, why in bad if why], "auto": False}
            if note:
                item["note"] = note
            try:
                if d.get("points") is not None and abs(float(d["points"]) - item["points"]) > 0.05:
                    item["claimed_points"] = float(d["points"])      # kept for the record; the code's number is the one that counts
            except (TypeError, ValueError):
                pass
            fb = feedback_of(d.get("feedback"))
            if fb:
                item["feedback"] = fb
            if sev in ("chan", "lon") and not (fb and len(fb.get("fix", "")) >= 10 and fb.get("effort")):
                raise ScoreError(f"{key}.deductions[{i}] mức '{sev}' phải kèm feedback.fix (≥ 10 ký tự: sửa ở file / hàm nào) và feedback.effort "
                                 "(💻 / 💵 / 👤) — khoản trừ lớn mà không thành việc sửa thì không có giá trị")
            clean.append(item)
        for a in auto_by.get(key, []):
            clean.append({"points": round(float(a["points"]), 1), "muc": "tu_dong", "loai": a.get("rule", "tu_dong"), "reason": a["reason"],
                          "evidence": list(a.get("evidence") or []), "unverified": [], "auto": True, "heuristic": bool(a.get("heuristic")),
                          "count": a.get("count")})
            auto_points += float(a["points"])
        ev_for = c.get("evidence_for") or []
        if isinstance(ev_for, str):
            ev_for = [ev_for]
        score = max(0.0, mx - sum(d["points"] for d in clean))
        crit_caps = []
        if key == "bang_chung" and score > 0:
            why_not = [(e, real_run_problem(e, root, area)) for e in ev_for]      # S14.10 S15: the cited LINE must record a real run
            if not any(w is None for _, w in why_not):
                crit_caps.append("code hạ về 0: không có trích dẫn chạy thật kiểm được (dòng TODO.md / docs / data / tests/fixtures có số, ngày, "
                                 "'đã chạy' hoặc nhắc khu vực) trong evidence_for"
                                 + (" — " + "; ".join(f"{e}: {w}" for e, w in why_not[:4]) if why_not else ""))
                score = 0.0
        if key == "test" and minor and facts.get("doc_only"):
            # S6 (thang 2.1): an area of documents only has nothing to test — `test` does not apply, the other 88 points are scaled to 100
            caps.append("test: không áp dụng — khu vực chỉ có tài liệu (không có module code); điểm khu vực chia lại trên 7 tiêu chí còn lại")
            out_crit[key] = {"score": 0.0, "max": 0, "deductions": clean, "evidence_for": [str(e) for e in ev_for],
                             "code_caps": ["không áp dụng: khu vực chỉ có tài liệu"], "khong_ap_dung": True}
            continue
        if key == "test" and facts:
            limit = None
            if facts.get("test_files", 0) == 0 and "test_files" in facts:
                limit, why = 3, "không có test file nào nhắm vào khu vực"
            elif "has_run" in facts and not facts.get("has_run"):
                # S4: a checkout without devsys/data/runs (a worktree / a fresh clone) is not "the tests were never run"
                limit, why = 8, ("không có thư mục devsys/data/runs ở bản sao này (worktree / clone mới?) — chấm và nhập ở repo gốc"
                                 if facts.get("runs_dir") is False else "chưa có lần chạy test lưu lại")
            elif facts.get("failed", 0) > 0:
                limit, why = 7, f"lần chạy mới nhất có {facts['failed']} test của khu vực lỗi"
            if limit is not None:
                lim = round(limit * mx / 15, 1)             # the bản 1 limits were set for a criterion worth 15
                if score > lim:
                    crit_caps.append(f"code giới hạn {lim:g}/{mx}: {why}")
                    score = lim
        if key == "trai_nghiem" and facts.get("ui_measured") and not facts.get("ui_present") and score > UI_NO_MEASURE_CAP:
            crit_caps.append(f"code giới hạn {UI_NO_MEASURE_CAP:g}/{mx}: khu vực giao diện chưa có số đo UI thật (devsys/data/ui_metrics.json — "
                             "py tools/devsys_ui_metrics.py)")
            score = UI_NO_MEASURE_CAP
        caps += [f"{key}: {c_}" for c_ in crit_caps]
        out_crit[key] = {"score": round(score, 1), "max": mx, "deductions": clean, "evidence_for": [str(e) for e in ev_for],
                         "code_caps": crit_caps}
    checklist = _checklist(raw.get("checklist"), by_loai, CHECKLIST_IDS if minor else CHECKLIST_IDS_V20)
    total = round(sum(c["score"] for c in out_crit.values()), 1)
    na = sum(CRITERIA_MAX_V2[k] for k, c in out_crit.items() if c.get("khong_ap_dung"))
    if na:
        total = round(total * 100 / (100 - na), 1)
    for n, limit in CHAN_CAPS:
        if sev_count["chan"] >= n:
            if total > limit:
                caps.append(f"khu vực: code giới hạn {limit:g}/100 vì còn {sev_count['chan']} lỗi chặn có bằng chứng")
                total = limit
            break
    checks = raw.get("can_kiem_lai") or []
    if not isinstance(checks, list):
        raise ScoreError("'can_kiem_lai' phải là danh sách")
    checks = [c if isinstance(c, dict) else {"what": str(c)} for c in checks]
    out = {"format": FORMAT_V21 if minor else FORMAT_V2, "area": area, "score": total, "criteria": out_crit, "can_kiem_lai": checks,
           "summary": str(raw.get("summary") or "").strip(), "unverified_evidence": unverified, "code_caps": caps,
           "severity": sev_count, "auto_points": round(auto_points, 1), "checklist": checklist}
    drift = drift_of(total + auto_points, prev, root)
    if drift:
        # S14.10 S2: an explanation counts only with at least one evidence code can check (a file:line that exists, a real test, …)
        expl = [e for e in (raw.get("giai_thich_chenh") or []) if isinstance(e, dict) and str(e.get("why") or "").strip()
                and any(not check_evidence(x, root) for x in _as_list(e.get("evidence") or e.get("evidence_for")))] \
            if isinstance(raw.get("giai_thich_chenh") or [], list) else []
        if abs(drift["delta"]) > DRIFT_LIMIT:
            if not expl:
                raise ScoreError(f"điểm (chưa tính khoản trừ tự động) lệch {drift['delta']:+g} so với lần chấm trước ({drift['prev_score']:g} → "
                                 f"{drift['now']:g}); lệch > {DRIFT_LIMIT:g} phải có 'giai_thich_chenh': danh sách {{criterion, why, evidence}} "
                                 "nói khoản trừ nào bị bỏ / thêm và vì sao (code đổi hay trước đây chấm sai), mỗi mục ≥ 1 bằng chứng kiểm "
                                 "được (file:dòng có thật, test:tests/…::Lớp::tên có thật)")
            drift["explained"] = True
            drift["explanations"] = [{"criterion": str(e.get("criterion") or ""), "why": str(e["why"]).strip()[:400],
                                      "evidence": [str(x) for x in (e.get("evidence") or [])]} for e in expl]
        out["drift"] = drift
    return out


def drift_of(adjusted_now: float, prev: Optional[Dict], root: str) -> Optional[Dict]:
    """How far this score (before the automatic deductions) is from the area's previous one of the SAME rubric — None when there is no
    comparable previous score. A scorer that judged differently on unchanged code is the main source of unstable scores."""
    if not prev or prev.get("score") is None or prev.get("rubric_hash") != rubric_hash(root) or prev.get("format") not in (None,) + V2_FORMATS:
        return None
    before = float(prev["score"]) + float(prev.get("auto_points") or 0.0)
    return {"prev_score": round(before, 1), "now": round(adjusted_now, 1), "delta": round(adjusted_now - before, 1), "prev_date": prev.get("date"),
            "prev_commit": prev.get("commit"), "limit": DRIFT_LIMIT, "explained": False}


def save(score: Dict, root: str = collect.ROOT) -> str:
    d = scores_dir(root)
    os.makedirs(d, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = os.path.join(d, f"{stamp}_{score['area']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(score, f, ensure_ascii=False, indent=1)
    return path


def load_all(root: str = collect.ROOT, area_ids: Optional[Sequence[str]] = None) -> Tuple[List[Dict], List[str]]:
    """All score files, oldest first, each re-normalised (score recomputed by code). Returns (scores, problems)."""
    d = scores_dir(root)
    out, problems = [], []
    if not os.path.isdir(d):
        return out, problems
    for n in sorted(os.listdir(d)):
        if not n.endswith(".json"):
            continue
        path = os.path.join(d, n)
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("format") not in FORMATS:
                raise ScoreError(f"format phải là một trong {', '.join(FORMATS)}")
            if not raw.get("scorer"):
                raise ScoreError("thiếu 'scorer' (ai chấm: claude-api, mock, claude-code-session…)")
            inner = raw.get("raw") or raw
            norm = normalize(inner, root, area_ids, raw.get("facts"), version=version_of({}, raw.get("format")) if raw.get("format") in V2_FORMATS else version_of(inner))
            if raw.get("drift") and is_v2(norm):
                norm["drift"] = raw["drift"]                 # decided when the score was made (it needs the previous score)
        except (OSError, ValueError) as e:
            problems.append(f"{n}: {e}")
            continue
        rec = {**{k: raw.get(k) for k in ("scorer", "model", "date", "commit", "dirty", "input_hash", "rubric_hash", "fingerprint",
                                          "usage", "facts", "provider")}, **norm, "_file": n}
        rec["date"] = rec.get("date") or datetime.fromtimestamp(os.path.getmtime(path)).astimezone().isoformat(timespec="seconds")
        out.append(rec)
    out.sort(key=lambda r: (r.get("date") or "", r["_file"]))
    return out, problems


def latest_by_area(scores: Sequence[Dict]) -> Dict[str, Dict]:
    """The newest score of each area (mock scores never replace a real one: they only count when an area has nothing else)."""
    real, mock = {}, {}
    for s in scores:
        (mock if str(s.get("scorer", "")).startswith("mock") else real)[s["area"]] = s
    return {**mock, **real}


def overall(latest: Dict[str, Dict], cfg: Dict, include_mock: bool = False, rubric: Optional[str] = None) -> Dict:
    """Weighted average of the latest area scores (areas.json `weight`), plus how much of the system it covers.

    S14 (thang 2.1): only scores of ONE scale are averaged — `rubric` (a rubric_hash; default: the scale of the newest score taken
    into account). Areas whose latest score is of another scale are left out and listed in `other_scale`; `mixed` says so."""
    num = den = 0.0
    covered, other = [], []
    total_w = sum(float(a.get("weight", 1)) for a in cfg["areas"])
    usable = {a["id"]: latest.get(a["id"]) for a in cfg["areas"]}
    usable = {k: s for k, s in usable.items() if s and (include_mock or not str(s.get("scorer", "")).startswith("mock"))}
    if rubric is None and usable:
        rubric = max(usable.values(), key=lambda s: str(s.get("date") or "")).get("rubric_hash")
    for a in cfg["areas"]:
        s = usable.get(a["id"])
        if not s:
            continue
        if s.get("rubric_hash") != rubric:
            other.append(a["id"])
            continue
        w = float(a.get("weight", 1))
        num += w * s["score"]
        den += w
        covered.append(a["id"])
    return {"score": round(num / den, 1) if den else None, "covered": covered, "areas": len(cfg["areas"]),
            "weight_share": round(den / total_w, 3) if total_w else 0.0, "rubric": rubric, "mixed": bool(other), "other_scale": other}


def trend(scores: Sequence[Dict], cfg: Dict, include_mock: bool = False) -> List[Dict]:
    """Overall completion after every scoring, replaying the score files in time order."""
    state: Dict[str, Dict] = {}
    points = []
    for s in scores:
        if not include_mock and str(s.get("scorer", "")).startswith("mock"):
            continue
        state[s["area"]] = s
        o = overall(state, cfg, include_mock, rubric=s.get("rubric_hash"))      # S14: each point averages the scale of the score just added
        points.append({"date": s.get("date"), "overall": o["score"], "covered": len(o["covered"]), "area": s["area"], "score": s["score"],
                       "mixed": o["mixed"]})
    return points


def band(score: Optional[float]) -> str:
    if score is None:
        return "none"
    return "ok" if score >= 80 else "warn" if score >= 60 else "bad"


# ---- độ ổn định, so thang cũ ↔ mới, báo cáo hành động ---------------------------------------------------------------------
def stability(all_scores: Sequence[Dict]) -> Dict:
    """Consecutive real scores of the same area under the SAME rubric: how far they moved, and whether the area's fingerprint
    (files + TODO + tests + flags) had changed in between. A big move with an equal fingerprint is scorer noise, not progress."""
    last: Dict[str, Dict] = {}
    pairs = []
    for s in all_scores:
        if str(s.get("scorer", "")).startswith("mock"):
            continue
        p = last.get(s["area"])
        if p and p.get("rubric_hash") == s.get("rubric_hash") and s.get("rubric_hash"):
            before = p["score"] + (p.get("auto_points") or 0.0)
            now = s["score"] + (s.get("auto_points") or 0.0)
            pairs.append({"area": s["area"], "from": p["score"], "to": s["score"], "delta": round(now - before, 1),
                          "same_fingerprint": bool(p.get("fingerprint") and p.get("fingerprint") == s.get("fingerprint")),
                          "same_scorer": p.get("scorer") == s.get("scorer"), "explained": bool((s.get("drift") or {}).get("explained")),
                          "date": s.get("date")})
        last[s["area"]] = s
    # S5 (thang 2.1): two different scorers may judge differently — a cross-scorer move counts in the figures only when it was NOT
    # explained (giai_thich_chenh), and "noise" (moved on unchanged code) is only ever said of the same scorer.
    counted = [p for p in pairs if p["same_scorer"] or not p["explained"]]
    deltas = [abs(p["delta"]) for p in counted]
    return {"pairs": pairs, "n": len(pairs), "mean_abs": round(sum(deltas) / len(deltas), 1) if deltas else None,
            "max_abs": max(deltas) if deltas else None, "over_limit": sum(1 for d in deltas if d > DRIFT_LIMIT),
            "cross_scorer": sum(1 for p in pairs if not p["same_scorer"]),
            "noise": [p for p in pairs if p["same_scorer"] and p["same_fingerprint"] and abs(p["delta"]) > 0]}


def compare_rounds(old: Dict[str, Dict], new: Dict[str, Dict], cfg: Dict) -> List[Dict]:
    """Old ↔ new scores per area (e.g. bản 1 of 01/10 against bản 2). Raw totals are both out of 100 but built from different criteria, so
    each shared criterion is also shown as a percentage of its own maximum; criteria only bản 2 has are listed separately."""
    rows = []
    for a in cfg["areas"]:
        o, n = old.get(a["id"]), new.get(a["id"])
        row = {"area": a["id"], "name": a["name"], "old": o["score"] if o else None, "new": n["score"] if n else None,
               "delta": round(n["score"] - o["score"], 1) if o and n else None,
               "old_format": o.get("format") if o else None, "new_format": n.get("format") if n else None, "criteria": {}, "only_new": {}}
        if o and n:
            for k, mx in CRITERIA_MAX_V2.items():
                nc = n["criteria"].get(k)
                if nc is None or nc.get("khong_ap_dung") or not nc.get("max"):
                    continue
                oc = o["criteria"].get(k)
                if oc is not None:
                    row["criteria"][k] = {"old_pct": round(100 * oc["score"] / oc["max"]), "new_pct": round(100 * nc["score"] / nc["max"])}
                else:
                    row["only_new"][k] = round(100 * nc["score"] / nc["max"])
        rows.append(row)
    return rows


def recurring(latest: Dict[str, Dict]) -> List[Dict]:
    """Deductions that point at the same evidence (a TODO line, a flag, a file:line) in two or more areas: one fix, several areas."""
    seen: Dict[str, Dict] = {}
    for aid, s in latest.items():
        for ck, c in s.get("criteria", {}).items():
            for d in c.get("deductions", []):
                if d.get("auto"):
                    continue
                for e in d.get("evidence", []):
                    if e.startswith("absent:"):
                        continue
                    r = seen.setdefault(e, {"evidence": e, "areas": set(), "points": 0.0, "reasons": []})
                    r["areas"].add(aid)
                    r["points"] += d["points"]
                    r["reasons"].append(d["reason"][:100])
    return sorted(({**r, "areas": sorted(r["areas"])} for r in seen.values() if len(r["areas"]) > 1), key=lambda r: -r["points"])


def action_report(latest: Dict[str, Dict], cfg: Dict) -> str:
    """Markdown: per area — why it lost points, what to fix, who does it, in what order (chan first, then priority, then points)."""
    who = {"💻": "Claude Code (code miễn phí)", "💵": "cần chi tiền — người dùng duyệt trần", "👤": "người dùng làm / quyết"}
    lines = ["# Báo cáo hành động theo khu vực (AI Development System)", ""]
    ordered = sorted(cfg["areas"], key=lambda a: (latest.get(a["id"]) or {"score": 101})["score"])
    lines += ["| Khu vực | Điểm | Lỗi chặn | Khoản trừ tự động | Thang |", "|---|---|---|---|---|"]
    for a in ordered:
        s = latest.get(a["id"])
        if s:
            lines.append(f"| {a['name']} | {s['score']:g} | {(s.get('severity') or {}).get('chan', '—')} | {s.get('auto_points', '—')} | "
                         f"{scale_label(s)} |")
    rec = recurring(latest)
    if rec:
        lines += ["", "## Một việc — nhiều khu vực (sửa một lần)", ""]
        lines += [f"- `{r['evidence']}` — {len(r['areas'])} khu vực ({', '.join(r['areas'])}), −{r['points']:g} điểm cộng dồn: {r['reasons'][0]}" for r in rec[:15]]
    order = {"chan": 0, "lon": 1, "nho": 2, "tu_dong": 3}
    for a in ordered:
        s = latest.get(a["id"])
        if not s:
            continue
        lines += ["", f"## {a['name']} — {s['score']:g}/100", ""]
        if s.get("summary"):
            lines += [s["summary"], ""]
        items = [(ck, d) for ck, c in s["criteria"].items() for d in c["deductions"]]
        items.sort(key=lambda x: (order.get(x[1].get("muc"), 2), (x[1].get("feedback") or {}).get("priority", 9), -x[1]["points"]))
        hand = [(k, d) for k, d in items if not d.get("auto")]
        auto = [(k, d) for k, d in items if d.get("auto")]
        for ck, d in hand:
            fb = d.get("feedback") or {}
            label = SEVERITY_LABEL.get(d.get("muc"), "")
            lines.append(f"- **[{label or '—'} · −{d['points']:g} · {ck}]** {d['reason']} (`{'`, `'.join(d['evidence'][:3])}`)")
            if fb.get("fix"):
                lines.append(f"  - Sửa: {fb['fix']} · Ai: {who.get(fb.get('effort'), 'chưa rõ ai làm')} · Ưu tiên {fb.get('priority', '—')}"
                             + (f" · File: {', '.join(fb['files'])}" if fb.get("files") else ""))
            elif d.get("muc") != "nho":
                lines.append("  - ⚠ Chưa có hướng sửa cụ thể (khoản trừ không hành động được).")
        if auto:
            lines.append("- Khoản trừ tự động (code đo, không cần người chấm): " + "; ".join(f"−{d['points']:g} {k}: {d['reason']}" for k, d in auto))
        open_ck = [c for c in s.get("checklist", []) if c["tra_loi"] == "co"]
        if open_ck:
            lines.append("- Loại lỗi đã gặp còn thấy: " + ", ".join(c["id"] for c in open_ck))
        if s.get("drift"):
            dr = s["drift"]
            lines.append(f"- Độ ổn định: lệch {dr['delta']:+g} so với lần trước ({dr['prev_score']:g}) — "
                         + ("đã giải thích." if dr.get("explained") else "trong ngưỡng."))
    return "\n".join(lines) + "\n"
