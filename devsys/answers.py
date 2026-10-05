"""Câu trả lời của người dùng cho các việc ⏸ (chờ người dùng) trong kế hoạch — S14.27, người dùng chốt 05/10 phương án (b).

Lưu ở `devsys/data/user_answers.json` của bản làm việc chính (`D:\\AI-Video-Pipeline`, nơi web 8502 chạy) — KHÔNG vào git. Phiên Claude
trong worktree cũng ghi về đúng file đó (tìm bản chính qua `.git`); `DEVSYS_ANSWERS_FILE` đặt đường dẫn khác (test).
Mỗi việc một bản ghi: task_id, choice (Duyệt/Không/Để sau hoặc rỗng), text, source (devsys|chat), who, at, status (answered → applied),
applied_note, applied_at, history (các lần trả lời trước). Câu trả lời KHÔNG đổi trạng thái việc trong kế hoạch: phiên Claude áp dụng,
sửa `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`, rồi `applied`. Ghi nguyên tử (file tạm + os.replace); file hỏng → AnswersError, không ghi đè.

CLI (phiên Claude):
    py -m devsys.answers list [--pending] [--json]
    py -m devsys.answers add S14.12 "nội dung" [--choice Duyệt|Không|"Để sau"] [--source chat|devsys] [--who tên]
    py -m devsys.answers applied S14.12 "ghi chú · mã commit"
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAT = "devsys-answers/1"
FILE_NAME = "user_answers.json"
CHOICES = ("Duyệt", "Không", "Để sau")
SOURCES = ("devsys", "chat")
TASK_ID_RE = re.compile(r"^[A-Z]+\d*(?:\.\d+)?$")


class AnswersError(ValueError):
    """Bad input or an unreadable answers file — always shown to the person, never skipped in silence."""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main_checkout(root: str = ROOT) -> str:
    """The main working tree (where the web runs). In a git worktree `.git` is a file pointing at `<main>/.git/worktrees/<name>`."""
    dot_git = os.path.join(root, ".git")
    if not os.path.isfile(dot_git):
        return root
    try:
        with open(dot_git, encoding="utf-8") as f:
            line = f.read().strip()
        gitdir = line.split(":", 1)[1].strip() if line.startswith("gitdir:") else ""
        if not gitdir:
            return root
        gitdir = os.path.normpath(gitdir if os.path.isabs(gitdir) else os.path.join(root, gitdir))
        common = os.path.join(gitdir, "commondir")
        if os.path.isfile(common):
            with open(common, encoding="utf-8") as f:
                rel = f.read().strip()
            common_dir = os.path.normpath(rel if os.path.isabs(rel) else os.path.join(gitdir, rel))
        else:
            common_dir = os.path.dirname(os.path.dirname(gitdir))
        if os.path.basename(common_dir) == ".git":
            return os.path.dirname(common_dir)
    except (OSError, IndexError):
        pass
    return root


def default_path() -> str:
    env = os.environ.get("DEVSYS_ANSWERS_FILE")
    if env:
        return env
    return os.path.join(main_checkout(), "devsys", "data", FILE_NAME)


def load(path: Optional[str] = None) -> Dict[str, Dict]:
    """{task_id: record}. Missing file → {}. Unreadable or wrong format → AnswersError naming the file."""
    path = path or default_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise AnswersError(f"Không đọc được file câu trả lời {path}: {e}. Sửa hoặc đổi tên file (không ghi đè tự động).") from e
    if not isinstance(raw, dict) or raw.get("format") != FORMAT or not isinstance(raw.get("answers"), dict):
        raise AnswersError(f"File câu trả lời {path} sai định dạng (cần format {FORMAT!r} + answers). Không ghi đè tự động.")
    return raw["answers"]


def _save(data: Dict[str, Dict], path: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".user_answers.", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"format": FORMAT, "updated": _now(), "answers": data}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def answer(task_id: str, text: str, source: str = "devsys", who: Optional[str] = None, choice: Optional[str] = None,
           path: Optional[str] = None) -> Dict:
    """Save (or replace) the answer for one task; the previous answer goes into `history`. Returns the new record."""
    path = path or default_path()
    task_id = (task_id or "").strip()
    text = (text or "").strip()
    choice = (choice or "").strip() or None
    if not TASK_ID_RE.match(task_id):
        raise AnswersError(f"Mã việc không hợp lệ: {task_id!r} (vd. S14.12).")
    if source not in SOURCES:
        raise AnswersError(f"Nguồn {source!r} không hợp lệ (chỉ {', '.join(SOURCES)}).")
    if choice is not None and choice not in CHOICES:
        raise AnswersError(f"Lựa chọn {choice!r} không hợp lệ (chỉ {', '.join(CHOICES)}).")
    if not text and not choice:
        raise AnswersError(f"Câu trả lời cho {task_id} trống: chọn nhanh hoặc ghi chữ.")
    data = load(path)
    old = data.get(task_id)
    history = list(old.get("history") or []) if old else []
    if old:
        history.append({k: v for k, v in old.items() if k != "history"})
    rec = {"task_id": task_id, "choice": choice, "text": text, "source": source, "who": (who or "").strip() or None, "at": _now(),
           "status": "answered", "applied_note": None, "applied_at": None, "history": history}
    data[task_id] = rec
    _save(data, path)
    return rec


def pending(path: Optional[str] = None) -> List[Dict]:
    """Answers Claude has not applied yet, oldest first."""
    return sorted((r for r in load(path).values() if r.get("status") == "answered"), key=lambda r: r.get("at") or "")


def mark_applied(task_id: str, note: str, path: Optional[str] = None) -> Dict:
    path = path or default_path()
    data = load(path)
    rec = data.get((task_id or "").strip())
    if rec is None:
        raise AnswersError(f"Chưa có câu trả lời cho {task_id} — không đánh dấu đã áp dụng được.")
    rec.update(status="applied", applied_note=(note or "").strip() or None, applied_at=_now())
    _save(data, path)
    return rec


def describe(rec: Dict) -> str:
    """One line: choice · text (who, source, time)."""
    body = " · ".join(x for x in (rec.get("choice"), rec.get("text")) if x)
    meta = ", ".join(x for x in (rec.get("who"), rec.get("source"), (rec.get("at") or "")[:16].replace("T", " ")) if x)
    return f"{body} ({meta})" if meta else body


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="py -m devsys.answers", description="Câu trả lời của người dùng cho việc ⏸ trong kế hoạch.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list", help="liệt kê câu trả lời")
    pl.add_argument("--pending", action="store_true", help="chỉ những câu chưa áp dụng")
    pl.add_argument("--json", action="store_true")
    pa = sub.add_parser("add", help="ghi câu trả lời (vd. người dùng nói trong chat)")
    pa.add_argument("task_id")
    pa.add_argument("text", nargs="?", default="")
    pa.add_argument("--choice", choices=CHOICES)
    pa.add_argument("--source", choices=SOURCES, default="chat")
    pa.add_argument("--who")
    pd = sub.add_parser("applied", help="đánh dấu Claude đã áp dụng")
    pd.add_argument("task_id")
    pd.add_argument("note", nargs="?", default="")
    args = p.parse_args(argv)
    try:
        if args.cmd == "list":
            data = load()
            if args.pending:
                data = {r["task_id"]: r for r in pending()}
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            elif not data:
                print("Không có câu trả lời" + (" chờ áp dụng." if args.pending else "."))
            else:
                for tid, r in sorted(data.items()):
                    mark = "✅ chờ áp dụng" if r.get("status") == "answered" else f"✔ đã áp dụng ({r.get('applied_note') or ''})"
                    print(f"{tid} · {mark} · {describe(r)}")
        elif args.cmd == "add":
            r = answer(args.task_id, args.text, source=args.source, who=args.who, choice=args.choice)
            print(f"Đã ghi {r['task_id']}: {describe(r)}")
        else:
            r = mark_applied(args.task_id, args.note)
            print(f"Đã đánh dấu {r['task_id']} đã áp dụng: {r.get('applied_note') or ''}")
    except AnswersError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
