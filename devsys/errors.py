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


def load_plan() -> Dict:
    """Đọc đúng kế hoạch chính trong checkout, dùng parser CODE/cổng hiện có."""
    from . import plan_progress
    with open(plan_progress.main_plan_file(ROOT), encoding="utf-8") as stream:
        return plan_progress.parse(stream.read())


def _commit_is_ancestor(sha: str) -> bool:
    """Chỉ đọc Git local, không mạng/config người dùng/credential."""
    import subprocess
    import tempfile
    git = "C:/Program Files/Git/cmd/git.exe" if os.name == "nt" else "/usr/bin/git"
    with tempfile.TemporaryDirectory(prefix="error_evidence_") as home:
        env = {"SYSTEMROOT": "C:/Windows", "HOME": home, "USERPROFILE": home,
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "PYTHONUTF8": "1"}
        try:
            result = subprocess.run([git, "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


def code_evidence_problems(item: Dict, root: str = ROOT, commit_check=None) -> List[str]:
    """Kiểm tham chiếu commit/test mà không import/chạy test hay sửa trạng thái.

    Hợp lệ mới được đề xuất rà chuyển FIXED_UNVERIFIED; kết quả test và phạm vi
    sửa vẫn phải được người rà đối chiếu trước khi áp dụng đề xuất.
    """
    import ast
    from pathlib import Path
    out = []
    commits, tests = item.get("fix_commit") or [], item.get("tests") or []
    commits = [commits] if isinstance(commits, str) else commits
    tests = [tests] if isinstance(tests, str) else tests
    if not commits:
        out.append("thiếu fix_commit đã kiểm")
    checker = commit_check or _commit_is_ancestor
    for value in commits:
        match = re.match(r"^([0-9a-f]{7,40})(?=\s|$)", str(value))
        if not match or not checker(match.group(1)):
            out.append("fix_commit không xác nhận thuộc lịch sử HEAD")
    if not tests:
        out.append("thiếu test hồi quy đã kiểm")
    base = Path(root).resolve()
    for value in tests:
        pieces = str(value).split("::")
        path = (base / pieces[0]).resolve()
        if not path.is_relative_to(base / "tests") or path.suffix != ".py" or not path.is_file():
            out.append(f"test không tồn tại trong tests/: {value}")
            continue
        try:
            nodes = ast.parse(path.read_text(encoding="utf-8-sig")).body
            for selector in pieces[1:]:
                name = selector.split("[", 1)[0]
                node = next((n for n in nodes if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
                if node is None:
                    raise ValueError("nodeid không có")
                nodes = node.body
        except (OSError, SyntaxError, ValueError):
            out.append(f"test nodeid không xác nhận được: {value}")
    return out


def sync_findings(doc: Dict, plan: Dict, verify=None) -> List[Dict]:
    """Đối soát chỉ đọc: ✅ CODE mà lỗi còn mở; không nâng cổng/VERIFIED.

    `verify` cho caller kiểm tham chiếu commit/test; kết quả chỉ là đề xuất,
    không phải bằng chứng chạy lại test hoặc nghiệm thu sản phẩm.
    """
    out = []
    for bad in plan.get("bad") or []:
        out.append({"id": None, "code": "PLAN_INVALID", "suggested_status": None, "reason": bad})
    tasks = {task["id"]: task for wave in plan.get("waves") or [] for task in wave.get("tasks") or []}
    if verify is None:
        # Nhiều mã cùng một commit: cache đúng một lượt, không giữ qua HEAD mới.
        commit_cache = {}

        def checked_commit(sha):
            if sha not in commit_cache:
                commit_cache[sha] = _commit_is_ancestor(sha)
            return commit_cache[sha]

        verify = lambda item: code_evidence_problems(item, commit_check=checked_commit)
    for item in doc.get("items") or []:
        task = tasks.get(item.get("plan_task"))
        if not task or task.get("status") != "✅" or item.get("status") not in ("OPEN", "IN_PROGRESS", "REOPENED"):
            continue
        issues = verify(item)
        reason = str(item.get("status_reason") or "").strip()
        # Chưa chạy thật là giới hạn đúng của FIXED_UNVERIFIED. Các phần code
        # còn thiếu/shadow/chỉ đề xuất phải giữ mở dù ✅ việc liên quan.
        plan_scope = " · ".join(part for part in str(task.get("note") or "").split(" · ")
                                if not part.strip().casefold().startswith("cổng:"))
        scope = " ".join((reason, str(task.get("title") or ""), plan_scope))
        scope = re.sub(r"chưa (?:có bằng chứng )?chạy thật", "", scope, flags=re.I)
        partial = bool(re.search(r"shadow|chỉ (?:phát hiện|đề xuất|báo)|còn mở|chưa|mới làm|phần \d|cờ[^.;·\n]{0,70}TẮT", scope, re.I))
        suggestion = "FIXED_UNVERIFIED" if not issues and not partial else None
        detail = "; ".join(issues) if issues else "tham chiếu commit và test hợp lệ; cần rà kết quả test và phạm vi sửa trước khi chuyển"
        if reason:
            detail += "; status_reason: " + reason
        if partial:
            detail += "; phạm vi sổ/kế hoạch còn partial/shadow/chưa áp dụng, chưa đủ kết luận sửa toàn lỗi"
        out.append({"id": item.get("id"), "plan_task": task["id"], "error_status": item.get("status"),
                    "code": "PLAN_DONE_ERROR_OPEN", "suggested_status": suggestion,
                    "reason": f"{task['id']} đã ✅ code, sổ còn {item.get('status')}: {detail}"})
    return out


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
    try:
        findings = sync_findings(doc, load_plan())
    except (OSError, ValueError) as exc:
        findings = [{"id": None, "code": "PLAN_UNREADABLE", "suggested_status": None,
                     "reason": f"không đối soát được kế hoạch ({type(exc).__name__})"}]
    for finding in findings:
        suggest = f"; đề xuất {finding['suggested_status']} sau rà" if finding["suggested_status"] else "; giữ trạng thái hiện tại"
        _print(f"🟡 {finding['code']} {finding.get('id') or '-'}: {finding['reason']}{suggest}")
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
