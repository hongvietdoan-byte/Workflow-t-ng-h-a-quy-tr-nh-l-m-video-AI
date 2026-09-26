"""Git post-commit hook của AI Development System: mỗi commit → một sự kiện trong devsys/data/events.jsonl + gom số đo miễn phí
(không chạy test, không AI). Không bao giờ chặn commit: mọi lỗi bị nuốt và ghi vào devsys/data/hook_errors.log.

    py tools/devsys_hook.py install      thêm khối devsys vào .git/hooks/post-commit (giữ nguyên nội dung hook đã có)
    py tools/devsys_hook.py uninstall    gỡ khối devsys
    py tools/devsys_hook.py status       đã cài chưa
    py tools/devsys_hook.py run          (hook gọi) ghi sự kiện commit + ảnh chụp số đo
"""
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BEGIN = "# >>> devsys (AI Development System) — tools/devsys_hook.py"
END = "# <<< devsys"


def hook_path(root: str = ROOT) -> str:
    from devsys import collect
    rel = collect.git(root, "rev-parse", "--git-path", "hooks/post-commit").strip()
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(root, rel))


def block(python: str = sys.executable) -> str:
    py = python.replace("\\", "/")
    return (f"{BEGIN}\n"
            'DEVSYS_TOP="$(git rev-parse --show-toplevel 2>/dev/null)"\n'
            f'if [ -f "$DEVSYS_TOP/tools/devsys_hook.py" ]; then "{py}" "$DEVSYS_TOP/tools/devsys_hook.py" run >/dev/null 2>&1 || true; fi\n'
            f"{END}\n")


def _strip(text: str) -> str:
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith(BEGIN):
            skip = True
            continue
        if skip and line.startswith(END):
            skip = False
            continue
        if not skip:
            out.append(line)
    return "".join(out)


def install(root: str = ROOT, python: str = sys.executable) -> str:
    path = hook_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            old = f.read()
    text = _strip(old)
    if not text.strip():
        text = "#!/bin/sh\n"
    if not text.endswith("\n"):
        text += "\n"
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    warn = " (cảnh báo: hook cũ kết thúc bằng 'exit' — khối devsys đặt sau có thể không chạy)" if lines and lines[-1].startswith("exit") else ""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + block(python))
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass
    return path + warn


def uninstall(root: str = ROOT) -> bool:
    path = hook_path(root)
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        old = f.read()
    new = _strip(old)
    if new == old:
        return False
    if new.strip() in ("", "#!/bin/sh"):
        os.remove(path)
    else:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return True


def installed(root: str = ROOT) -> bool:
    try:
        with open(hook_path(root), encoding="utf-8", errors="replace") as f:
            return BEGIN in f.read()
    except OSError:
        return False


def run(root: str = ROOT) -> int:
    """Called by the hook: record the commit, refresh the free snapshot. Always returns 0."""
    t0 = time.time()
    try:
        from devsys import collect
        cfg = collect.load_areas(os.path.join(root, "devsys", "areas.json"))
        commits = collect.timeline(root, cfg, limit=1)
        c = commits[0] if commits else {}
        collect.append_event("commit", root, hash=c.get("hash"), short=c.get("short"), subject=c.get("subject"), author=c.get("author"),
                             date=c.get("date"), files=c.get("files", [])[:200], areas=c.get("areas", []))
        snap = collect.collect(root, cfg)
        collect.save_snapshot(snap, root)
        collect.append_event("snapshot", root, commit=c.get("short"), seconds=round(time.time() - t0, 2),
                             unmapped=snap["coverage"]["unmapped"])
    except Exception:  # noqa: BLE001 - a hook must never block or break a commit
        try:
            d = os.path.join(root, "devsys", "data")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "hook_errors.log"), "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
        except OSError:
            pass
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "status"
    if cmd == "run":
        return run(ROOT)
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if cmd == "install":
        print(f"Đã cài hook post-commit: {install(ROOT)}")
    elif cmd == "uninstall":
        print("Đã gỡ khối devsys khỏi hook." if uninstall(ROOT) else "Hook không có khối devsys.")
    elif cmd == "status":
        print(("Đã cài" if installed(ROOT) else "Chưa cài") + f" — {hook_path(ROOT)}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
