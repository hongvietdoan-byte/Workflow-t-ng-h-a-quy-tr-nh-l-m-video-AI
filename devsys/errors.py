"""V3.1 M0.4 (D09 chọn C, người dùng 20/10): SỔ LỖI trung tâm — devsys/errors.json (trong git, đọc được mọi tài khoản / phiên).

errors.json = ĐỊNH NGHĨA + VÒNG ĐỜI một lỗi gốc (mã bất biến `P31-G1`, `P33-A1` + alias lịch sử); LẦN PHÁT SINH nằm ở diag_events / jobs
(chỉ trỏ tới bằng project/shot/job ids). Lỗi gốc ≠ lần xuất hiện: nhiều mục cùng nguyên nhân trỏ `root_cause_id`. Trạng thái tách bạch
đã sửa code (FIXED_UNVERIFIED: có commit + test) với đã xác minh chạy thật (VERIFIED: cần thêm `real_run_evidence`) — KHÔNG đóng lỗi chỉ
vì unit test qua. Loại lỗi / khâu không chép lại: `stage` trỏ devsys/stages.json (L1–L16), xem thêm devsys/error_types.json.

  python -m devsys.errors check [--file F]          — luật hợp đồng (mã thoát 1 khi sai)
  python -m devsys.errors list [--status S] [--ws WS]
0 USD, chỉ đọc."""
import json
import os
import re
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "devsys", "errors.json")
STAGES_PATH = os.path.join(ROOT, "devsys", "stages.json")
SCHEMA_VERSION = 1
FIELDS = ("id", "alias", "title", "source_document", "project_ids", "shot_ids", "job_ids", "stage", "category",
          "root_cause_hypothesis", "root_cause_confirmed", "root_cause_id", "evidence", "severity", "status", "first_seen", "last_seen",
          "affected_flows", "owner", "fix_commit", "tests", "real_run_evidence", "plan_workstream", "plan_task", "dependencies",
          "reopen_history", "status_reason")
STATUSES = ("OPEN", "IN_PROGRESS", "FIXED_UNVERIFIED", "VERIFIED", "REOPENED", "WONT_FIX")
SEVERITIES = ("cao", "vua", "thap")
WORKSTREAMS = tuple(f"WS{i}" for i in range(7))
ID_RE = re.compile(r"^(P\d+|V\d+)-[A-Z]+\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(path: Optional[str] = None) -> Dict:
    with open(path or PATH, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
        raise ValueError(f"{path or PATH}: cần {{'schema_version', 'items': [...]}}")
    return doc


def stage_ids() -> set:
    try:
        with open(STAGES_PATH, encoding="utf-8") as f:
            return {v.get("id") for v in json.load(f).get("stages") or [] if isinstance(v, dict) and v.get("id")}
    except (OSError, ValueError):
        return set()


def register_problems(doc: Dict) -> List[str]:
    """Kiểm cấu trúc trước problems(), để trang/sơ đồ báo rõ JSON sai schema."""
    if not isinstance(doc.get('items'), list):
        return ['errors.json: items phải là danh sách']
    for n, row in enumerate(doc['items']):
        if not isinstance(row, dict):
            return [f'errors.json: mục {n} không phải object']
        for field in ('alias', 'project_ids', 'shot_ids', 'job_ids', 'affected_flows',
                      'dependencies', 'reopen_history'):
            value = row.get(field)
            if value is not None and not isinstance(value, list):
                return [f'errors.json: mục {n} trường {field} phải là danh sách']
        if any(not isinstance(a, str) for a in row.get('alias') or []):
            return [f'errors.json: mục {n} alias phải chứa chuỗi']
        if row.get('stage') is not None and not isinstance(row['stage'], str):
            return [f'errors.json: mục {n} stage phải là chuỗi hoặc null']
    try:
        return problems(doc)
    except (TypeError, AttributeError) as exc:
        return [f'errors.json: cấu trúc trường không hợp lệ ({type(exc).__name__})']


def problems(doc: Dict, stages: Optional[set] = None) -> List[str]:
    """Lỗi hợp đồng của sổ (rỗng = hợp lệ)."""
    out: List[str] = []
    if doc.get("schema_version") != SCHEMA_VERSION:
        out.append(f"schema_version {doc.get('schema_version')!r} (cần {SCHEMA_VERSION})")
    stages = stage_ids() if stages is None else stages
    items = doc.get("items") or []
    ids = set()
    alias_of: Dict[str, str] = {}
    for it in items:
        iid = it.get("id")
        if iid in ids:
            out.append(f"mã trùng: {iid!r}")
        ids.add(iid)
        for a in it.get("alias") or []:
            if a in alias_of and alias_of[a] != iid:
                out.append(f"{iid!r}: alias {a!r} đã thuộc {alias_of[a]!r}")
            alias_of.setdefault(a, iid)
    for it in items:
        iid = it.get("id")
        miss = [f for f in FIELDS if f not in it]
        if miss:
            out.append(f"{iid!r}: thiếu trường {', '.join(miss)}")
            continue
        if not isinstance(iid, str) or not ID_RE.match(iid):
            out.append(f"{iid!r}: sai dạng mã (cần P31-G1 / P33-A1 / V21-R3)")
        st = it["status"]
        if st not in STATUSES:
            out.append(f"{iid!r}: status {st!r} (cần {' / '.join(STATUSES)})")
        if it["severity"] not in SEVERITIES:
            out.append(f"{iid!r}: severity {it['severity']!r} (cần {' / '.join(SEVERITIES)})")
        if it["stage"] is not None and stages and it["stage"] not in stages:
            out.append(f"{iid!r}: stage {it['stage']!r} không có trong devsys/stages.json")
        if not str(it["source_document"] or "").strip():
            out.append(f"{iid!r}: thiếu source_document")
        for d in ("first_seen", "last_seen"):
            if it[d] and not DATE_RE.match(str(it[d])):
                out.append(f"{iid!r}: {d} {it[d]!r} (cần YYYY-MM-DD)")
        if it["first_seen"] and it["last_seen"] and str(it["last_seen"]) < str(it["first_seen"]):
            out.append(f"{iid!r}: last_seen trước first_seen")
        if st in ("OPEN", "IN_PROGRESS", "REOPENED", "FIXED_UNVERIFIED") and it["plan_workstream"] not in WORKSTREAMS:
            out.append(f"{iid!r}: {st} cần plan_workstream WS0–WS6 (có {it['plan_workstream']!r})")
        if st in ("FIXED_UNVERIFIED", "VERIFIED"):
            if not it["fix_commit"]:
                out.append(f"{iid!r}: {st} thiếu fix_commit")
            if not it["tests"]:
                out.append(f"{iid!r}: {st} thiếu tests")
        if st == "VERIFIED" and not it["real_run_evidence"]:
            out.append(f"{iid!r}: VERIFIED thiếu real_run_evidence (unit test qua không đủ — giữ FIXED_UNVERIFIED)")
        if st == "WONT_FIX" and not str(it["status_reason"] or "").strip():
            out.append(f"{iid!r}: WONT_FIX thiếu lý do (status_reason)")
        if st == "REOPENED" and not it["reopen_history"]:
            out.append(f"{iid!r}: REOPENED thiếu reopen_history")
        for d in it["dependencies"] or []:
            if d not in ids:
                out.append(f"{iid!r}: dependencies trỏ {d!r} không có trong sổ")
        rc = it["root_cause_id"]
        if rc is not None and (rc not in ids or rc == iid):
            out.append(f"{iid!r}: root_cause_id {rc!r} không hợp lệ")
    return out


def _print(s: str = "") -> None:
    print(s)


def cmd_list(doc: Dict, status: Optional[str] = None, ws: Optional[str] = None) -> int:
    for it in doc["items"]:
        if status and it.get("status") != status or ws and it.get("plan_workstream") != ws:
            continue
        _print(f"{it['id']:9s} {it['status']:17s} {it.get('plan_workstream') or '-':4s} {it.get('severity'):5s} "
               f"[{'/'.join(it.get('alias') or [])}] {it.get('title')}")
    return 0


def cmd_check(doc: Dict, path: str) -> int:
    probs = problems(doc)
    for p in probs:
        _print(f"🔴 {p}")
    counts: Dict[str, int] = {}
    for it in doc["items"]:
        counts[it.get("status")] = counts.get(it.get("status"), 0) + 1
    _print(f"{len(doc['items'])} mục — " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: str(x[0]))))
    _print(f"{'Hợp lệ' if not probs else f'{len(probs)} lỗi'} — sổ {path}")
    return 1 if probs else 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="python -m devsys.errors", description="Sổ lỗi V3.1 (devsys/errors.json)")
    ap.add_argument("cmd", choices=("list", "check"))
    ap.add_argument("--file", default=PATH)
    ap.add_argument("--status", choices=STATUSES)
    ap.add_argument("--ws", choices=WORKSTREAMS)
    a = ap.parse_args(argv)
    doc = load(a.file)
    return cmd_list(doc, a.status, a.ws) if a.cmd == "list" else cmd_check(doc, a.file)


if __name__ == "__main__":
    raise SystemExit(main())
