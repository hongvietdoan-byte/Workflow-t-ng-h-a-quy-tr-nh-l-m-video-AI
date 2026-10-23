#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HỘP THƯ dạng sự kiện — phối hợp nhiều phiên (phiên chính, cloud-B/C/D, Codex…) qua git.

Mỗi sự kiện là MỘT file JSON trong `hop_thu/su_kien/` (không bao giờ sửa file cũ) nên hai làn ghi
cùng lúc không đụng nhau. Trạng thái việc tính lại từ toàn bộ sự kiện theo thứ tự `ts`.

Chỉ dùng thư viện chuẩn, Python ≥ 3.8, chạy được Windows + Linux. Xem `hop_thu/README.md`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import string
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Giờ VN cố định +07:00 (không dùng zoneinfo: Windows có thể thiếu tzdata).
VN_TZ = timezone(timedelta(hours=7))
EVENT_DIR = Path("hop_thu") / "su_kien"
KINDS = ("giao", "nhan", "xong", "gop", "hoi", "tra_loi", "bo", "tin", "het_viec")
TASK_KINDS = ("giao", "nhan", "xong", "gop", "bo")
LANE_RE = re.compile(r"^(phien-chinh|codex|nguoi-dung|cloud-[A-Za-z0-9]+|phien-con-[A-Za-z0-9-]+)$")
TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CO_AUTHOR = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

CHO, CHO_DK, DANG_LAM, XONG, GOP, BO = "CHỜ", "CHỜ ĐIỀU KIỆN", "ĐANG LÀM", "XONG", "GỘP", "BỎ"


class HopThuError(Exception):
    """Lỗi người dùng — in ra rồi thoát mã 1."""


# ---------------------------------------------------------------- tiện ích


def now_vn() -> datetime:
    return datetime.now(VN_TZ)


def parse_ts(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN_TZ)
    return dt


def check_lane(lane, extra=()):
    if lane in extra or (lane and LANE_RE.match(lane)):
        return lane
    raise HopThuError(
        f"Tên làn không hợp lệ: '{lane}'. Hợp lệ: phien-chinh, cloud-B/C/D (cloud-*), codex, "
        f"nguoi-dung, phien-con-*" + (f", {', '.join(extra)}" if extra else "") + "."
    )


def check_task(task):
    if task and TASK_RE.match(task):
        return task
    raise HopThuError(f"Mã việc không hợp lệ: '{task}' (chỉ chữ, số, '.', '_', '-').")


def find_root(explicit=None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("HOP_THU_GOC")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, encoding="utf-8")
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except OSError:
        pass
    return Path(__file__).resolve().parent.parent


def event_dir(root: Path) -> Path:
    return root / EVENT_DIR


# ---------------------------------------------------------------- đọc / ghi sự kiện


def load_events(root: Path):
    """Trả (events, errors). errors = [(tên file, lý do)] — file hỏng KHÔNG bị bỏ qua im lặng."""
    d = event_dir(root)
    events, errors = [], []
    if not d.is_dir():
        return events, errors
    for p in sorted(d.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                ev = json.load(f)
            if not isinstance(ev, dict):
                raise ValueError("không phải object JSON")
            for key in ("ts", "lane", "kind"):
                if not ev.get(key):
                    raise ValueError(f"thiếu trường '{key}'")
            if ev["kind"] not in KINDS:
                raise ValueError(f"kind lạ '{ev['kind']}'")
            if ev["kind"] in TASK_KINDS and not ev.get("task"):
                raise ValueError("thiếu trường 'task'")
            ev["_ts"] = parse_ts(ev["ts"])
            ev["_file"] = p.name
            events.append(ev)
        except (ValueError, TypeError, OSError) as e:  # JSONDecodeError/UnicodeDecodeError là ValueError
            errors.append((p.name, str(e)))
    events.sort(key=lambda e: (e["_ts"], e["_file"]))
    return events, errors


def write_event(root: Path, lane: str, kind: str, now=None, **fields) -> Path:
    if kind not in KINDS:
        raise HopThuError(f"kind lạ: {kind}")
    now = (now or now_vn()).astimezone(VN_TZ)
    ev = {"ts": now.isoformat(timespec="microseconds"), "lane": lane, "kind": kind}
    for k, v in fields.items():
        if v not in (None, "", []):
            ev[k] = v
    d = event_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    alphabet = string.ascii_lowercase + string.digits
    while True:
        rnd = "".join(secrets.choice(alphabet) for _ in range(4))
        p = d / f"{now.strftime('%Y%m%d-%H%M%S')}-{lane}-{rnd}.json"
        if not p.exists():
            break
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        json.dump(ev, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return p


# ---------------------------------------------------------------- tính trạng thái


class Task:
    def __init__(self, code):
        self.code = code
        self.owner = None      # lane được giao hoặc "pool"
        self.claimer = None    # lane đã nhận
        self.status = CHO
        self.title = self.spec = self.branch = self.commit = self.report = self.text = None
        self.depends = []
        self.priority = 100
        self.ts_giao = None
        self.ts_status = None
        self.notes = []

    def eff_lane(self):
        return self.claimer or self.owner


def compute_state(events):
    tasks, notes_global = {}, []
    questions, answers, news, het_viec, last_claim = [], {}, [], {}, {}
    for ev in events:
        kind, lane, ts = ev["kind"], ev["lane"], ev["_ts"]
        hhmm = ts.strftime("%d/%m %H:%M")
        if kind in TASK_KINDS:
            code = ev["task"]
            t = tasks.get(code)
            if kind == "giao":
                to_new = ev.get("to") or "pool"
                if t is None:
                    t = tasks[code] = Task(code)
                else:
                    if to_new != t.eff_lane():
                        t.notes.append(f"giao lại {t.eff_lane()} → {to_new} ({hhmm})")
                    if to_new != t.claimer:
                        if t.status != CHO:
                            t.notes.append(f"mở lại từ {t.status} ({hhmm})")
                        t.claimer, t.status = None, CHO
                t.owner = to_new
                t.title = ev.get("title") or t.title
                t.spec = ev.get("spec") or t.spec
                if "depends" in ev:
                    t.depends = list(ev.get("depends") or [])
                if ev.get("priority") is not None:
                    t.priority = int(ev["priority"])
                t.ts_giao = t.ts_giao or ts
                t.ts_status = ts
                continue
            if t is None:
                notes_global.append(f"{ev['_file']}: '{kind}' cho việc {code} chưa từng được giao")
                t = tasks[code] = Task(code)
                t.owner, t.ts_giao = lane, ts
            if kind == "nhan":
                last_claim[lane] = ts
                if t.claimer and t.claimer != lane and t.status in (DANG_LAM, XONG, GOP):
                    t.notes.append(f"nhận trùng — bỏ ({lane} {hhmm}; {t.claimer} nhận trước)")
                    continue
                if t.status in (GOP, BO):
                    t.notes.append(f"nhận khi đã {t.status} — bỏ ({lane} {hhmm})")
                    continue
                t.claimer, t.status, t.ts_status = lane, DANG_LAM, ts
            elif kind == "xong":
                t.status, t.ts_status = XONG, ts
                t.claimer = t.claimer or lane
                t.branch = ev.get("branch") or t.branch
                t.commit = ev.get("commit") or t.commit
                t.report = ev.get("report") or t.report
                t.text = ev.get("text") or t.text
            elif kind == "gop":
                t.status, t.ts_status = GOP, ts
                t.commit = ev.get("commit") or t.commit
            elif kind == "bo":
                t.status, t.ts_status = BO, ts
                t.text = ev.get("text") or t.text
        elif kind == "hoi":
            questions.append(ev)
        elif kind == "tra_loi":
            answers.setdefault(ev.get("reply_to"), []).append(ev)
        elif kind == "tin":
            news.append(ev)
        elif kind == "het_viec":
            het_viec[lane] = ts
    # làn HẾT VIỆC = báo het_viec sau lần nhận cuối của làn đó
    idle = {ln: ts for ln, ts in het_viec.items() if ln not in last_claim or ts > last_claim[ln]}
    return {"tasks": tasks, "questions": questions, "answers": answers, "news": news,
            "idle": idle, "notes": notes_global}


def missing_deps(state, t):
    out = []
    for d in t.depends:
        dt = state["tasks"].get(d)
        if dt is None:
            out.append(f"{d}: chưa giao")
        elif dt.status != GOP:
            out.append(f"{d}: {display_status(state, dt) if dt.status == CHO else dt.status}")
    return out


def display_status(state, t, _seen=None):
    if t.status == CHO and t.depends:
        seen = _seen or set()
        if t.code in seen:
            return CHO_DK
        seen.add(t.code)
        for d in t.depends:
            dt = state["tasks"].get(d)
            if dt is None or dt.status != GOP:
                return CHO_DK
    return t.status


def next_task(state, lane):
    def ok(t):
        return t.status == CHO and not missing_deps(state, t)

    def key(t):
        return (t.priority, t.ts_giao)
    own = sorted([t for t in state["tasks"].values() if t.owner == lane and ok(t)], key=key)
    if own:
        return own[0]
    pool = sorted([t for t in state["tasks"].values() if t.owner == "pool" and ok(t)], key=key)
    return pool[0] if pool else None


# ---------------------------------------------------------------- git


def _git(root, *args, check=True, env=None):
    r = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    if check and r.returncode != 0:
        raise HopThuError(f"git {' '.join(args)} lỗi: {(r.stderr or r.stdout).strip()}")
    return r


def is_git_repo(root):
    try:
        return _git(root, "rev-parse", "--is-inside-work-tree", check=False).returncode == 0
    except OSError:
        return False


def git_pull(root):
    if not is_git_repo(root):
        print("Ghi chú: thư mục không phải repo git — bỏ qua git pull.", file=sys.stderr)
        return
    r = _git(root, "pull", "--rebase", "--autostash", check=False)
    if r.returncode != 0:
        print(f"CẢNH BÁO: git pull lỗi, dùng dữ liệu đang có: {(r.stderr or r.stdout).strip()}",
              file=sys.stderr)


def git_push_event(root: Path, path: Path, message: str, tries: int = 3):
    """Đưa MỘT file sự kiện lên origin/main, không force.

    - Đang ở nhánh main: add → commit → pull --rebase → push HEAD:main.
    - Đang ở nhánh khác: commit file vào nhánh hiện tại (sau gộp main là add/add giống hệt, không
      xung đột), đồng thời dựng một commit CHỈ chứa file đó trên đỉnh origin/main bằng index tạm +
      commit-tree rồi push — không đẩy commit khác của nhánh lên main.
    """
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    if not rel.startswith(EVENT_DIR.as_posix() + "/"):
        raise HopThuError(f"Chỉ được push file trong {EVENT_DIR.as_posix()}/ (nhận: {rel})")
    full_msg = f"{message}\n\n{CO_AUTHOR}\n"
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    _git(root, "add", "--", rel)
    _git(root, "commit", "-q", "-m", full_msg, "--only", "--", rel)
    last = ""
    for i in range(1, tries + 1):
        if branch == "main":
            r = _git(root, "pull", "--rebase", "--autostash", "origin", "main", check=False)
            if r.returncode != 0:
                _git(root, "rebase", "--abort", check=False)
                last = (r.stderr or r.stdout).strip()
                print(f"Pull lần {i} lỗi, thử lại… ({last.splitlines()[-1] if last else ''})", file=sys.stderr)
                continue
            r = _git(root, "push", "origin", "HEAD:main", check=False)
        else:
            _git(root, "fetch", "-q", "origin", "main")
            blob = _git(root, "hash-object", "-w", "--", rel).stdout.strip()
            idx = Path(_git(root, "rev-parse", "--git-path", "hop_thu_index").stdout.strip())
            if not idx.is_absolute():
                idx = root / idx
            env = dict(os.environ, GIT_INDEX_FILE=str(idx))
            try:
                _git(root, "read-tree", "origin/main", env=env)
                _git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
                tree = _git(root, "write-tree", env=env).stdout.strip()
            finally:
                if idx.exists():
                    idx.unlink()
            commit = _git(root, "commit-tree", tree, "-p", "origin/main", "-m", full_msg).stdout.strip()
            r = _git(root, "push", "origin", f"{commit}:refs/heads/main", check=False)
        if r.returncode == 0:
            print(f"Đã push lên origin/main (lần thử {i}).")
            return
        last = (r.stderr or r.stdout).strip()
        print(f"Push lần {i} chưa được, thử lại… ({last.splitlines()[-1] if last else ''})", file=sys.stderr)
    raise HopThuError(f"Push thất bại sau {tries} lần (không force). File vẫn ở {rel}. Lỗi cuối: {last}")


# ---------------------------------------------------------------- in bảng


def _cell(s):
    return (str(s) if s not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def _note(state, t, st):
    parts = []
    if st == CHO_DK:
        parts.append("thiếu: " + ", ".join(missing_deps(state, t)))
    if st == XONG:
        parts.append(f"chờ gộp; nhánh {t.branch or '?'} @ {t.commit or '?'}")
        if t.report:
            parts.append(f"báo cáo {t.report}")
    if st == DANG_LAM and t.owner == "pool":
        parts.append("từ pool")
    if t.spec:
        parts.append(f"đề: {t.spec}")
    parts += t.notes
    return "; ".join(parts)


def _table(state, rows):
    out = ["| Trạng thái | Mã | Việc | Ưu tiên | Ghi chú |", "|---|---|---|---|---|"]
    for _, _, _, st, t in sorted(rows, key=lambda x: x[:3]):
        out.append(f"| {st} | {t.code} | {_cell(t.title)} | {t.priority} | {_cell(_note(state, t, st))} |")
    return out


def render_board(state, errors, lane_filter=None):
    lines = ["# 📨 Hộp thư — bảng trạng thái", ""]
    if errors:
        lines += ["## ⚠ File sự kiện hỏng (KHÔNG được đọc — ghi sự kiện mới thay, đừng sửa file cũ)", ""]
        lines += [f"- `{n}`: {m}" for n, m in errors] + [""]
    if state["notes"]:
        lines += ["## ⚠ Sự kiện bất thường", ""] + [f"- {n}" for n in state["notes"]] + [""]
    order = [DANG_LAM, CHO, CHO_DK, XONG]
    by_lane = {}
    for t in state["tasks"].values():
        st = display_status(state, t)
        if st not in order:
            continue
        ln = t.claimer if st in (DANG_LAM, XONG) else t.owner
        by_lane.setdefault(ln, []).append((order.index(st), t.priority, t.ts_giao, st, t))
    lanes = sorted(k for k in by_lane if k != "pool")
    if lane_filter:
        lanes = [k for k in lanes if k == lane_filter]
    for ln in lanes:
        lines += [f"## Làn {ln}" + ("  _(HẾT VIỆC)_" if ln in state["idle"] else ""), ""]
        lines += _table(state, by_lane[ln]) + [""]
    lines += ["## Hàng dự phòng (pool)", ""]
    lines += (_table(state, by_lane["pool"]) if by_lane.get("pool") else ["_(trống)_"]) + [""]
    open_q = [q for q in state["questions"] if q["_file"] not in state["answers"]
              and (not lane_filter or q.get("to") in (lane_filter, "all") or q["lane"] == lane_filter)]
    lines += ["## Câu hỏi chưa trả lời", ""]
    lines += [f"- `{q['_file']}` {q['lane']} → {q.get('to', '?')}"
              + (f" [{q['task']}]" if q.get("task") else "") + f": {q.get('text', '')}"
              for q in open_q] or ["_(không có)_"]
    lines += ["", "## Làn HẾT VIỆC", ""]
    lines += [f"- {ln} (từ {ts.strftime('%d/%m %H:%M')})"
              for ln, ts in sorted(state["idle"].items())] or ["_(không có)_"]
    news = [n for n in state["news"]
            if not lane_filter or n.get("to") in (lane_filter, "all", None) or n["lane"] == lane_filter]
    lines += ["", "## 10 tin mới nhất", ""]
    lines += [f"- {n['_ts'].strftime('%d/%m %H:%M')} {n['lane']} → {n.get('to', 'all')}: {n.get('text', '')}"
              for n in reversed(news[-10:])] or ["_(không có)_"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- lệnh


def _load(root):
    events, errors = load_events(root)
    for n, m in errors:
        print(f"LỖI: file sự kiện hỏng {n}: {m}", file=sys.stderr)
    return compute_state(events), errors


def _finish(args, root, path, kind, task):
    print(f"Đã ghi {path.relative_to(root).as_posix()}")
    if args.push:
        label = f"{kind} {task}" if task else kind
        git_push_event(root, path, f"hộp thư: {label} ({args.lane})")


def cmd_giao(args, root):
    check_lane(args.lane)
    check_task(args.ma)
    check_lane(args.to, extra=("pool",))
    deps = [check_task(d.strip()) for d in (args.depends or "").split(",") if d.strip()]
    if args.ma in deps:
        raise HopThuError("Việc không thể phụ thuộc chính nó.")
    p = write_event(root, args.lane, "giao", task=args.ma, to=args.to, title=args.title,
                    spec=args.spec, depends=deps, priority=args.priority, text=args.text)
    _finish(args, root, p, "giao", args.ma)


def _claim(args, root, code):
    state, _ = _load(root)
    t = state["tasks"].get(code)
    if t is None:
        raise HopThuError(f"Từ chối: việc {code} chưa được giao.")
    if t.status == DANG_LAM:
        who = "chính bạn" if t.claimer == args.lane else t.claimer
        raise HopThuError(f"Từ chối: {code} đã có người nhận — {who} lúc {t.ts_status:%d/%m %H:%M}.")
    if t.status != CHO:
        raise HopThuError(f"Từ chối: {code} đang ở trạng thái {t.status}, không nhận được.")
    if t.owner not in ("pool", args.lane):
        raise HopThuError(f"Từ chối: {code} giao cho {t.owner}, không phải {args.lane} (nhờ người giao giao lại).")
    miss = missing_deps(state, t)
    if miss:
        raise HopThuError(f"Từ chối: {code} CHỜ ĐIỀU KIỆN — cần GỘP trước: {', '.join(miss)}.")
    p = write_event(root, args.lane, "nhan", task=code)
    _finish(args, root, p, "nhan", code)
    if t.spec:
        print(f"Đề bài: {t.spec}")


def cmd_nhan(args, root):
    check_lane(args.lane)
    check_task(args.ma)
    if not args.khong_pull:
        git_pull(root)
    _claim(args, root, args.ma)


def cmd_xong(args, root):
    check_lane(args.lane)
    check_task(args.ma)
    state, _ = _load(root)
    t = state["tasks"].get(args.ma)
    if t is None or t.status != DANG_LAM or t.claimer != args.lane:
        cur = "chưa giao" if t is None else t.status + (f" ({t.claimer})" if t.claimer else "")
        raise HopThuError(f"Từ chối: {args.ma} không phải việc {args.lane} ĐANG LÀM (hiện: {cur}).")
    p = write_event(root, args.lane, "xong", task=args.ma, branch=args.branch, commit=args.commit,
                    report=args.report, text=args.text)
    _finish(args, root, p, "xong", args.ma)


def cmd_gop(args, root):
    check_lane(args.lane)
    check_task(args.ma)
    state, _ = _load(root)
    t = state["tasks"].get(args.ma)
    if t is None or t.status != XONG:
        raise HopThuError(f"Từ chối: {args.ma} chưa XONG (hiện: {'chưa giao' if t is None else t.status}).")
    p = write_event(root, args.lane, "gop", task=args.ma, commit=args.commit, text=args.text)
    _finish(args, root, p, "gop", args.ma)
    if not args.giu_worktree and t.branch and t.commit:
        try:
            import don_rac
            result = don_rac.cleanup_merged_branch_worktree(root, t.branch, t.commit)
        except Exception as exc:
            # Việc ghi sự kiện GỘP đã hoàn tất; lỗi dọn chỉ là cảnh báo, không đảo trạng thái.
            print(f"CẢNH BÁO: chưa tự gỡ worktree/nhánh {t.branch}: {exc}", file=sys.stderr)
        else:
            print(f"Dọn sau gộp: {result}")


def cmd_bo(args, root):
    check_lane(args.lane)
    check_task(args.ma)
    state, _ = _load(root)
    t = state["tasks"].get(args.ma)
    if t is None:
        raise HopThuError(f"Từ chối: việc {args.ma} chưa được giao.")
    if t.status in (GOP, BO):
        raise HopThuError(f"Từ chối: {args.ma} đã {t.status}.")
    p = write_event(root, args.lane, "bo", task=args.ma, text=args.text)
    _finish(args, root, p, "bo", args.ma)


def cmd_hoi(args, root):
    check_lane(args.lane)
    check_lane(args.to, extra=("all",))
    if args.task:
        check_task(args.task)
    p = write_event(root, args.lane, "hoi", to=args.to, task=args.task, text=args.text)
    _finish(args, root, p, "hoi", args.task)


def cmd_tra_loi(args, root):
    check_lane(args.lane)
    name = Path(args.file).name
    events, _ = load_events(root)
    q = next((e for e in events if e["_file"] == name), None)
    if q is None or q["kind"] != "hoi":
        raise HopThuError(f"Không tìm thấy sự kiện hỏi '{name}' trong {EVENT_DIR.as_posix()}/.")
    p = write_event(root, args.lane, "tra_loi", to=q["lane"], task=q.get("task"), reply_to=name,
                    text=args.text)
    _finish(args, root, p, "tra_loi", q.get("task"))


def cmd_tin(args, root):
    check_lane(args.lane)
    check_lane(args.to, extra=("all",))
    if args.task:
        check_task(args.task)
    p = write_event(root, args.lane, "tin", to=args.to, task=args.task, text=args.text)
    _finish(args, root, p, "tin", args.task)


def cmd_het_viec(args, root):
    check_lane(args.lane)
    p = write_event(root, args.lane, "het_viec", text=args.text)
    _finish(args, root, p, "het_viec", None)


def cmd_bang(args, root):
    if args.lane:
        check_lane(args.lane)
    state, errors = _load(root)
    sys.stdout.write(render_board(state, errors, args.lane))


def cmd_ke(args, root):
    check_lane(args.lane)
    if args.nhan and not args.khong_pull:
        git_pull(root)
    state, _ = _load(root)
    t = next_task(state, args.lane)
    if t is None:
        print(f"HẾT VIỆC — {args.lane} không còn việc riêng hay việc pool nào đủ điều kiện. "
              f"Báo: py tools/hop_thu.py het-viec --lane {args.lane} --push")
        return
    nguon = "pool" if t.owner == "pool" else "việc riêng"
    print(f"Việc kế ({nguon}): {t.code} — {t.title or '—'} [ưu tiên {t.priority}]")
    if t.spec:
        print(f"Đề bài: {t.spec}")
    if args.nhan:
        _claim(args, root, t.code)


def build_parser():
    ap = argparse.ArgumentParser(prog="hop_thu", description="Hộp thư sự kiện giữa các phiên.")
    ap.add_argument("--goc", help="gốc repo (mặc định: git rev-parse --show-toplevel)")
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    def add(name, fn, write=True, help_=None):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn, push=False)
        if write:
            p.add_argument("--push", action="store_true", help="commit + push thẳng origin/main")
        return p

    p = add("giao", cmd_giao, help_="giao việc cho làn hoặc pool")
    p.add_argument("ma")
    p.add_argument("--to", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--spec")
    p.add_argument("--depends", help="mã việc phải GỘP trước, cách nhau dấu phẩy")
    p.add_argument("--priority", type=int, help="số nhỏ = làm trước (mặc định 100)")
    p.add_argument("--text")
    p.add_argument("--lane", required=True)

    p = add("nhan", cmd_nhan, help_="nhận việc (tự git pull trước)")
    p.add_argument("ma")
    p.add_argument("--lane", required=True)
    p.add_argument("--khong-pull", action="store_true", help="không git pull trước")

    p = add("xong", cmd_xong, help_="báo xong, chờ gộp")
    p.add_argument("ma")
    p.add_argument("--lane", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--report")
    p.add_argument("--text")

    p = add("gop", cmd_gop, help_="phiên chính báo đã gộp")
    p.add_argument("ma")
    p.add_argument("--lane", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--text")
    p.add_argument("--giu-worktree", action="store_true", help="không tự gỡ worktree sau khi gộp")

    p = add("bo", cmd_bo, help_="bỏ việc")
    p.add_argument("ma")
    p.add_argument("--lane", required=True)
    p.add_argument("--text", required=True)

    p = add("hoi", cmd_hoi, help_="hỏi một làn")
    p.add_argument("--lane", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--task")

    p = add("tra-loi", cmd_tra_loi, help_="trả lời một sự kiện hỏi")
    p.add_argument("file", help="tên file sự kiện hỏi")
    p.add_argument("--lane", required=True)
    p.add_argument("--text", required=True)

    p = add("tin", cmd_tin, help_="tin chung")
    p.add_argument("--lane", required=True)
    p.add_argument("--to", default="all")
    p.add_argument("--text", required=True)
    p.add_argument("--task")

    p = add("het-viec", cmd_het_viec, help_="báo làn hết việc")
    p.add_argument("--lane", required=True)
    p.add_argument("--text")

    p = add("bang", cmd_bang, write=False, help_="in bảng markdown")
    p.add_argument("--lane")

    p = add("ke", cmd_ke, help_="in việc kế nên làm")
    p.add_argument("--lane", required=True)
    p.add_argument("--nhan", action="store_true", help="nhận luôn việc kế")
    p.add_argument("--khong-pull", action="store_true")
    return ap


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    root = find_root(args.goc)
    try:
        args.fn(args, root)
    except HopThuError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
