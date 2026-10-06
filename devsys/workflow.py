"""S14.45: bảng chấm hiệu quả quy trình nhiều phiên (skill `vong-lam-viec-theo-plan`) — số đo mỗi nhánh nằm TRONG GIT.

File `devsys/workflow_runs.jsonl`: mỗi dòng một nhánh đã gộp —
    task (S14.x) · part (A/B khi một việc chia nhiều nhánh) · date (YYYY-MM-DD) · mode (goi | usd | cloud) · review (ky | nhe | None = không rõ)
    work_k / review_k / fix_k (nghìn token phiên làm / rà / sửa; None = không ghi) · fix_rounds · bugs · bugs_major · commit · note · source (cli | plan:dòng N)
Ghi:  python -m devsys.workflow add S14.45 --mode cloud --review nhe --work 150 [--review-k 0 --fix 0 --rounds 0 --bugs 0 --major 0 --note …]
Xem:  python -m devsys.workflow list
Nhập lại từ kế hoạch:  python -m devsys.workflow import-plan [--write]   (đọc các dòng "Số đo: …" của docs/KE_HOACH_SUA_SAU_DU_AN_8.md;
      dòng không đọc được → liệt kê, không im lặng bỏ; chạy lại không nhân đôi).
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_FILE = os.path.join(ROOT, "devsys", "workflow_runs.jsonl")
MODES = ("goi", "usd", "cloud")
MODE_LABEL = {"goi": "gói", "usd": "$", "cloud": "cloud"}
REVIEWS = ("ky", "nhe")
REVIEW_LABEL = {"ky": "rà kỹ", "nhe": "rà nhẹ", "?": "không rõ"}

# Hai mốc ghi sẵn (skill vong-lam-viec-theo-plan mục 2 + 2b).
BASELINES = {
    "A": {"label": "Mốc A 04–05/10", "branches": 7, "work_k": 2000, "review_k": 1100, "per_branch_k": 443, "pct_review": 35.0,
          "bugs_per_branch": "1–3"},
    "B": {"label": "Mốc B 05–06/10", "per_branch_ky_k": 653, "per_branch_nhe_k": 124, "pct_review": 20.0, "pct_fix": 48.0,
          "bugs_per_branch": 5.2},
}


class WorkflowError(ValueError):
    """File số đo hỏng hoặc dữ liệu nhập sai — báo người dùng, không ghi đè im lặng."""


def runs_file() -> str:
    return os.environ.get("DEVSYS_WORKFLOW_FILE") or RUNS_FILE


# ---- đọc / ghi ----------------------------------------------------------------------------------------------------------
def load(path: Optional[str] = None) -> List[Dict]:
    path = path or runs_file()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError as e:
                raise WorkflowError(f"{path} dòng {n} không phải JSON ({e}) — sửa tay rồi chạy lại") from e
            if not isinstance(rec, dict) or not rec.get("task"):
                raise WorkflowError(f"{path} dòng {n} thiếu mã việc 'task'")
            rows.append(rec)
    return rows


def _write(rows: List[Dict], path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _key(r: Dict):
    return (r.get("task"), r.get("part") or "")


def validate(rec: Dict) -> Dict:
    if not re.match(r"^[A-Z]+\d*(\.\d+)?$", str(rec.get("task") or "")):
        raise WorkflowError(f"mã việc '{rec.get('task')}' không đúng dạng (vd. S14.45)")
    if rec.get("mode") not in MODES:
        raise WorkflowError(f"chế độ '{rec.get('mode')}' phải là một trong {', '.join(MODES)}")
    if rec.get("review") not in REVIEWS + (None,):
        raise WorkflowError(f"mức rà '{rec.get('review')}' phải là ky hoặc nhe")
    for k in ("work_k", "review_k", "fix_k", "fix_rounds", "bugs", "bugs_major"):
        v = rec.get(k)
        if v is not None and v < 0:
            raise WorkflowError(f"{k} = {v} là số âm")
    if rec.get("work_k") is None:
        raise WorkflowError("thiếu token phiên làm (--work)")
    try:
        datetime.strptime(rec.get("date") or "", "%Y-%m-%d")
    except ValueError as e:
        raise WorkflowError(f"ngày '{rec.get('date')}' phải dạng YYYY-MM-DD") from e
    if rec.get("bugs_major") is not None and rec.get("bugs") is not None and rec["bugs_major"] > rec["bugs"]:
        raise WorkflowError("số lỗi nặng lớn hơn tổng số lỗi")
    return rec


def add(rec: Dict, path: Optional[str] = None, force: bool = False) -> Dict:
    path = path or runs_file()
    rows = load(path)
    validate(rec)
    if not force and any(_key(r) == _key(rec) for r in rows):
        raise WorkflowError(f"{rec['task']}{(' ' + rec['part']) if rec.get('part') else ''} đã có trong {path} (thêm --force nếu là nhánh khác)")
    rec.setdefault("added_at", datetime.now().astimezone().isoformat(timespec="seconds"))
    rows.append(rec)
    _write(rows, path)
    return rec


# ---- nhập lại từ dòng "Số đo:" của kế hoạch ------------------------------------------------------------------------------
TASK_LINE = re.compile(r"^\s*- \[(?P<x> |x|X)\] (?P<id>[A-Z]+\d*(?:\.\d+)?) · ")
_NUM = r"(?P<n>\d+(?:[.,]\d+)?)\s*(?P<u>k\b|nghìn|triệu)?"
_UNIT = {"k": 1, "nghìn": 1, "triệu": 1000}
_STATUS_DONE = re.compile(r" · (✅|🔄|⏸) ")


def _tok(m) -> int:
    n = float(m.group("n").replace(",", "."))
    if m.group("u") is None:
        if n == 0:
            return 0
        raise WorkflowError(f"'{m.group(0).strip()}' thiếu đơn vị k/nghìn")
    return int(round(n * _UNIT[m.group("u")]))


def _field(seg: str, word: str) -> Optional[int]:
    m = re.search(rf"(?<!\w){word}\s*(?:≈\s*)?{_NUM}", seg)
    return _tok(m) if m else None


def parse_measure(seg: str) -> Dict:
    """Một nhánh: 'làm ≈ 233k + sửa ≈ 257k token, rà ≈ 138k (≈ 28 %), rà bắt 5 lỗi' → các trường. Không đọc được → WorkflowError."""
    work = _field(seg, "làm")
    if work is None:
        m = re.match(rf"\s*≈\s*{_NUM}", seg)                                            # "≈ 343k token (1 phiên làm, rà nhẹ)"
        work = _tok(m) if m else None
    if work is None:
        raise WorkflowError("không thấy token phiên làm")
    fix, extra = _field(seg, "sửa"), _field(seg, "thêm")
    review = _field(seg, "rà")
    b = re.search(r"(?:rà bắt|lỗi bắt được)\s*(\d+)", seg)
    notes = []
    if extra is not None:
        notes.append(f"thêm ≈ {extra}k (đánh thức lại) tính vào sửa")
    fix_total = (fix or 0) + (extra or 0)
    level = "ky" if review else ("nhe" if review == 0 or "rà nhẹ" in seg else None)
    return {"work_k": work, "review_k": review, "fix_k": fix_total, "fix_rounds": 1 if fix_total else 0,
            "bugs": int(b.group(1)) if b else None, "review": level, "note": "; ".join(notes)}


_MARK = re.compile(r"(?<!['\"«“‘])Số đo:")       # 06/10: chữ 'Số đo:' trong ngoặc = câu mô tả (vd dòng S14.45), không phải số đo


def _segment(line: str) -> str:
    seg = line[_MARK.search(line).end():]
    seg = re.split(r"\.\s|\s·\s", seg + " ", maxsplit=1)[0]
    return seg.strip().rstrip(".")


def parse_plan(text: str, year: Optional[int] = None) -> Dict:
    """{"runs": [...], "bad": ["dòng N S14.x: lý do — trích"], "skipped": [việc chưa làm có chữ 'Số đo:']}."""
    year = year or date.today().year
    runs, bad, skipped = [], [], []
    for n, line in enumerate(text.splitlines(), 1):
        if "Số đo:" not in line:
            continue
        t = TASK_LINE.match(line)
        if not t:
            continue                                                                    # câu văn trong bảng/đoạn mô tả, không phải dòng việc
        tid = t.group("id")
        st = _STATUS_DONE.search(line)
        if not st:
            skipped.append(f"dòng {n} {tid}: việc chưa làm — chữ 'Số đo:' chỉ là mô tả")
            continue
        if not _MARK.search(line):
            skipped.append(f"dòng {n} {tid}: chữ 'Số đo:' trong ngoặc — chỉ là mô tả, dòng không có số đo")
            continue
        rest = line[st.end():]
        cm = re.match(r"[\s·]*([0-9a-f]{7,40})\b", rest)
        dm = re.search(r"\b(\d{2})/(\d{2})\b", rest)
        seg = _segment(line)
        parts = [p.strip() for p in seg.split(";") if p.strip()]
        try:
            if not dm:
                raise WorkflowError("không thấy ngày dd/mm sau trạng thái")
            day = f"{year}-{dm.group(2)}-{dm.group(1)}"
            datetime.strptime(day, "%Y-%m-%d")
            got = []
            for p in parts:
                lab = re.match(r"([A-Z])\s+(?=làm)", p)
                rec = parse_measure(p[lab.end():] if lab else p)
                rec.update({"task": tid, "date": day, "mode": "goi", "commit": cm.group(1) if cm else None,
                            "source": f"plan:dòng {n}", "bugs_major": None})
                if lab:
                    rec["part"] = lab.group(1)
                rec["note"] = "; ".join(x for x in (rec["note"], "nhập từ kế hoạch — chế độ gói giả định") if x)
                got.append(rec)
            if not got:
                raise WorkflowError("trống")
        except (WorkflowError, ValueError) as e:
            bad.append(f"dòng {n} {tid}: {e} — «Số đo: {seg[:100]}»")
            continue
        runs.extend(got)
    return {"runs": runs, "bad": bad, "skipped": skipped}


def import_plan(text: str, path: Optional[str] = None, write: bool = False) -> Dict:
    got = parse_plan(text)
    have = {_key(r) for r in load(path or runs_file())}
    new = [r for r in got["runs"] if _key(r) not in have]
    if write and new:
        rows = load(path or runs_file()) + new
        _write(rows, path or runs_file())
    got["new"] = new
    return got


# ---- chỉ số ------------------------------------------------------------------------------------------------------------
def total_k(r: Dict) -> int:
    return (r.get("work_k") or 0) + (r.get("review_k") or 0) + (r.get("fix_k") or 0)


def _pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def _group(rows: List[Dict]) -> Dict:
    n = len(rows)
    tot = sum(total_k(r) for r in rows)
    rev = sum(r.get("review_k") or 0 for r in rows)
    fix = sum(r.get("fix_k") or 0 for r in rows)
    with_bugs = [r for r in rows if r.get("bugs") is not None]
    bugs = sum(r["bugs"] for r in with_bugs)
    rev_bugs = sum(r.get("review_k") or 0 for r in with_bugs)
    return {"n": n, "total_k": tot, "work_k": sum(r.get("work_k") or 0 for r in rows), "review_k": rev, "fix_k": fix,
            "per_branch_k": round(tot / n) if n else None, "pct_review": _pct(rev, tot), "pct_fix": _pct(fix, tot),
            "bugs": bugs, "bugs_per_branch": round(bugs / len(with_bugs), 2) if with_bugs else None,
            "review_per_bug_k": round(rev_bugs / bugs, 1) if bugs and rev_bugs else None,
            "fix_rounds_per_branch": round(sum(r.get("fix_rounds") or 0 for r in rows) / n, 2) if n else None}


def summarize(rows: List[Dict]) -> Dict:
    def by(fn):
        keys = sorted({fn(r) for r in rows})
        return {k: _group([r for r in rows if fn(r) == k]) for k in keys}
    return {"all": _group(rows), "by_review": by(lambda r: r.get("review") or "?"), "by_date": by(lambda r: r.get("date") or "?"),
            "by_mode": by(lambda r: r.get("mode") or "?")}


def compare(s: Dict) -> List[Dict]:
    """Bảng so với 2 mốc: mỗi dòng một chỉ số, cột Hiện tại / Mốc A / Mốc B ('' = mốc không có số đó)."""
    ky, nhe, al = s["by_review"].get("ky") or {}, s["by_review"].get("nhe") or {}, s["all"]
    a, b = BASELINES["A"], BASELINES["B"]
    la, lb = a["label"], b["label"]
    rows = [("Số nhánh", al.get("n"), a["branches"], ""),
            ("Token/nhánh tất cả (nghìn)", al.get("per_branch_k"), a["per_branch_k"], ""),
            ("Token/nhánh rà kỹ (nghìn)", ky.get("per_branch_k"), "", b["per_branch_ky_k"]),
            ("Token/nhánh rà nhẹ (nghìn)", nhe.get("per_branch_k"), "", b["per_branch_nhe_k"]),
            ("% rà (rà kỹ)", ky.get("pct_review"), a["pct_review"], b["pct_review"]),
            ("% sửa (rà kỹ)", ky.get("pct_fix"), "", b["pct_fix"]),
            ("Lỗi rà bắt / nhánh rà kỹ", ky.get("bugs_per_branch"), a["bugs_per_branch"], b["bugs_per_branch"]),
            ("Token rà / lỗi bắt (nghìn)", ky.get("review_per_bug_k"), "", ""),
            ("Vòng sửa / nhánh", al.get("fix_rounds_per_branch"), "", "")]
    return [{"Chỉ số": k, "Hiện tại": "—" if v is None else v, la: va, lb: vb} for k, v, va, vb in rows]


# ---- CLI ---------------------------------------------------------------------------------------------------------------
def _fmt(v) -> str:
    return "—" if v is None else str(v)


def _print_rows(rows: List[Dict]) -> None:
    print(f"{'việc':<10} {'ngày':<10} {'chế độ':<6} {'rà':<6} {'làm':>5} {'rà':>5} {'sửa':>5} {'tổng':>6} {'vòng':>4} {'lỗi':>4}  ghi chú")
    for r in rows:
        name = r["task"] + ((" " + r["part"]) if r.get("part") else "")
        print(f"{name:<10} {_fmt(r.get('date')):<10} {MODE_LABEL.get(r.get('mode'), '?'):<6} {REVIEW_LABEL.get(r.get('review') or '?'):<6} "
              f"{_fmt(r.get('work_k')):>5} {_fmt(r.get('review_k')):>5} {_fmt(r.get('fix_k')):>5} {total_k(r):>6} "
              f"{_fmt(r.get('fix_rounds')):>4} {_fmt(r.get('bugs')):>4}  {r.get('note') or ''}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m devsys.workflow", description="Số đo hiệu quả quy trình nhiều phiên (token làm/rà/sửa, lỗi rà bắt).")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", default=None, help="file số đo (mặc định devsys/workflow_runs.jsonl)")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", parents=[common], help="ghi số đo một nhánh vừa gộp")
    a.add_argument("task")
    a.add_argument("--part", default=None, help="A/B khi một việc chia nhiều nhánh")
    a.add_argument("--date", default=date.today().isoformat())
    a.add_argument("--mode", required=True, choices=MODES)
    a.add_argument("--review", required=True, choices=REVIEWS)
    a.add_argument("--work", type=int, required=True, help="nghìn token phiên làm")
    a.add_argument("--review-k", type=int, default=0, help="nghìn token phiên rà")
    a.add_argument("--fix", type=int, default=0, help="nghìn token vòng sửa")
    a.add_argument("--rounds", type=int, default=None, help="số vòng sửa (mặc định 1 nếu có --fix, không thì 0)")
    a.add_argument("--bugs", type=int, default=None, help="số lỗi phiên rà bắt")
    a.add_argument("--major", type=int, default=None, help="trong đó lỗi nặng")
    a.add_argument("--commit", default=None)
    a.add_argument("--note", default="")
    a.add_argument("--force", action="store_true", help="thêm dù đã có dòng cùng mã việc")
    sub.add_parser("list", parents=[common], help="liệt kê + tổng")
    i = sub.add_parser("import-plan", parents=[common], help="nhập lại từ dòng 'Số đo:' của kế hoạch")
    i.add_argument("--plan", default=None)
    i.add_argument("--write", action="store_true", help="ghi vào file (mặc định chỉ xem)")
    args = p.parse_args(argv)
    path = args.file or runs_file()
    try:
        if args.cmd == "add":
            rec = {"task": args.task, "date": args.date, "mode": args.mode, "review": args.review, "work_k": args.work,
                   "review_k": args.review_k, "fix_k": args.fix, "fix_rounds": args.rounds if args.rounds is not None else (1 if args.fix else 0),
                   "bugs": args.bugs, "bugs_major": args.major, "commit": args.commit, "note": args.note, "source": "cli"}
            if args.part:
                rec["part"] = args.part
            add(rec, path, force=args.force)
            print(f"Đã ghi {args.task}: tổng {total_k(rec)}k → {path}")
        elif args.cmd == "list":
            rows = load(path)
            _print_rows(rows)
            s = summarize(rows)["all"]
            print(f"\n{s['n']} nhánh · tổng {s['total_k']}k · {_fmt(s['per_branch_k'])}k/nhánh · rà {_fmt(s['pct_review'])} % · sửa {_fmt(s['pct_fix'])} %")
        else:
            from devsys import plan_progress
            plan = args.plan or plan_progress.PLAN_FILE
            with open(plan, encoding="utf-8") as f:
                got = import_plan(f.read(), path, write=args.write)
            _print_rows(got["runs"])
            print(f"\n{len(got['runs'])} nhánh đọc được · {len(got['new'])} chưa có trong file" + (" → ĐÃ GHI" if args.write and got["new"] else
                                                                                                    "" if args.write else " (thêm --write để ghi)"))
            for b in got["bad"]:
                print("⚠ KHÔNG ĐỌC ĐƯỢC " + b)
            for s_ in got["skipped"]:
                print("· bỏ qua " + s_)
    except WorkflowError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
