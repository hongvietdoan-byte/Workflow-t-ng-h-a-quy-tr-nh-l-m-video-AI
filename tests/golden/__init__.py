"""Bộ ca hồi quy (K0a kế hoạch kiểm soát, mục 3.9) — định dạng ở tests/golden/README.md. Mỗi ca một tệp tests/golden/cases/<id>.json.

load_cases(lop=None)       → mọi ca (lọc theo lớp phải bắt, vd "d85")
problems(case, …)          → lỗi định dạng của một ca (rỗng = đúng)
stage_facts_cases()        → ca có ky_vong.stage_facts, dạng cũ của tests/fixtures/stage_facts_golden.json (name, stage_camera, objects,
                             image_prompt, expect) cho tests/test_stage_facts.py
"""
import json
import os
from typing import Dict, Iterable, List, Optional

GOLDEN_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(GOLDEN_DIR, "cases")
REQUIRED = ("id", "nguon", "ca_vang_tay", "byd", "may", "kho", "goi", "anh_ket_qua", "loi_dung", "loai_loi", "lop_phai_bat", "ky_vong")
# Khóa ky_vong có LỚP CHẠY trong test (tests/test_stage_facts.py, test_identity_declare.py, test_world_rules.py — test_devsys_stages giữ
# khớp). Khóa khác (am_chu, dung, do_tu_the, shot_intent) chưa lớp nào chạy → bắt buộc `chua_co_lop: "<đợt>"` (thẩm định 4 #4).
LOP_CHAY = ("stage_facts", "identity_declare", "world_rules")


def load_cases(lop: Optional[str] = None) -> List[Dict]:
    out = []
    for name in sorted(os.listdir(CASES_DIR)):
        if name.endswith(".json"):
            with open(os.path.join(CASES_DIR, name), encoding="utf-8") as f:
                case = json.load(f)
            case["_file"] = name
            out.append(case)
    return [c for c in out if lop is None or lop in c.get("lop_phai_bat", [])]


def problems(case: Dict, error_type_ids: Iterable[str] = (), decision_ids: Iterable[str] = (),
             kiem_ids: Optional[Iterable[str]] = None) -> List[str]:
    """Lỗi định dạng: thiếu trường, id ≠ tên tệp, loại lỗi / lớp không có trong sổ, lớp phải bắt không có vai 'kiem' (kiem_ids =
    devsys/stages.json vai.kiem), ca vàng tay thiếu BYĐ, BYĐ sai schema, kỳ vọng không lớp nào chạy mà thiếu `chua_co_lop`."""
    from core import shot_intent
    cid = case.get("id")
    out = [f"{cid}: thiếu '{k}'" for k in REQUIRED if k not in case]
    if case.get("_file") and case["_file"] != f"{cid}.json":
        out.append(f"{cid}: tên tệp {case['_file']} phải là {cid}.json")
    types, deci = set(error_type_ids), set(decision_ids)
    if not case.get("loai_loi"):
        out.append(f"{cid}: loai_loi rỗng")
    for t in case.get("loai_loi") or []:
        if types and t not in types:
            out.append(f"{cid}: loại lỗi '{t}' không có trong devsys/error_types.json")
    if not case.get("lop_phai_bat"):
        out.append(f"{cid}: lop_phai_bat rỗng")
    for d in case.get("lop_phai_bat") or []:
        if deci and d not in deci:
            out.append(f"{cid}: lớp '{d}' không có trong devsys/decisions.json")
        if kiem_ids is not None and d not in set(kiem_ids):
            out.append(f"{cid}: lop_phai_bat '{d}' không có vai 'kiem' (bộ sinh / bộ làm ghi ở lop_lam)")
    lam = case.get("lop_lam", [])
    if not isinstance(lam, list):
        out.append(f"{cid}: lop_lam phải là danh sách id devsys/decisions.json")
        lam = []
    for d in lam:
        if deci and d not in deci:
            out.append(f"{cid}: lop_lam '{d}' không có trong devsys/decisions.json")
    if case.get("ca_vang_tay") and not case.get("byd"):
        out.append(f"{cid}: ca_vang_tay phải có BYĐ nhập tay")
    if case.get("byd"):
        for i in shot_intent.validate(case["byd"]):
            if i["muc"] == "do":
                out.append(f"{cid}: BYĐ {i['truong']} — {i['loi']}")
    if not isinstance(case.get("ky_vong"), dict) or not case.get("ky_vong"):
        out.append(f"{cid}: ky_vong rỗng (lớp nào phải ra gì)")
    for k, v in (case.get("ky_vong") or {}).items() if isinstance(case.get("ky_vong"), dict) else ():
        if k not in LOP_CHAY and not (isinstance(v, dict) and str(v.get("chua_co_lop") or "").strip()):
            out.append(f"{cid}: ky_vong.{k} không lớp nào chạy — ghi chua_co_lop = đợt sẽ có lớp")
    return out


def stage_facts_cases() -> List[Dict]:
    return [{"name": c["id"], "source": c["nguon"], "stage_camera": c["may"], "objects": c["kho"],
             "image_prompt": (c.get("goi") or {}).get("image_prompt", ""), "expect": c["ky_vong"]["stage_facts"]}
            for c in load_cases() if "stage_facts" in (c.get("ky_vong") or {})]
