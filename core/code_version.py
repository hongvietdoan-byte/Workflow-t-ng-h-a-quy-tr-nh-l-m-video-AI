"""V3.1 M1.7 (G55, #31: Dashboard 8503/8504 chạy core cũ cả ngày sau khi cập nhật code → `FAIL_SOURCE`; tools/stop_dashboard.ps1 chỉ tắt
8501). Cờ `stale_code_alarm` (TẮT = như cũ):

- mỗi tiến trình Dashboard (dashboard/serve.py) ghi sổ `<thư mục CSDL>/run/dashboard_<cổng>.json` {port, pid, sha lúc khởi động, at};
- `stale_instances` đọc sổ: tiến trình còn sống mà sha ≠ HEAD hiện tại của repo → Dashboard nào đang mở cũng báo băng vàng (kể cả khi
  CỔNG KHÁC chạy code cũ) + lệnh tắt mọi cổng (`tools/stop_dashboard.ps1 -All`);
- `check_round` (vòng nền, core/bg_poll.round_once): tiến trình đang giữ vòng nền mà chạy code cũ → diag `stale_code` (gộp 10 phút như
  mọi diag) — vòng nền là thứ GỬI job, chạy code cũ là nguy hiểm nhất, kể cả khi không ai mở trang của cổng đó.
Chỉ đọc `.git` (không gọi git), không chặn gì (0 USD)."""
import json
import os
import time
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "stale_code"
FLAG = "stale_code_alarm"


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def head_sha(root: str = ROOT) -> Optional[str]:
    """SHA của HEAD đọc thẳng từ .git (HEAD → ref → tệp ref / packed-refs); None khi không đọc được (không phải repo git)."""
    git = os.path.join(root, ".git")
    try:
        if os.path.isfile(git):                       # worktree / submodule: ".git" là tệp "gitdir: <đường>"
            with open(git, encoding="utf-8") as f:
                line = f.read().strip()
            if line.startswith("gitdir:"):
                git = os.path.normpath(os.path.join(root, line.split(":", 1)[1].strip()))
        with open(os.path.join(git, "HEAD"), encoding="utf-8") as f:
            head = f.read().strip()
        if not head.startswith("ref:"):
            return head or None
        ref = head.split(":", 1)[1].strip()
        common = git
        cfile = os.path.join(git, "commondir")
        if os.path.isfile(cfile):
            with open(cfile, encoding="utf-8") as f:
                common = os.path.normpath(os.path.join(git, f.read().strip()))
        for base in (git, common):
            path = os.path.join(base, *ref.split("/"))
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    return f.read().strip() or None
        packed = os.path.join(common, "packed-refs")
        if os.path.isfile(packed):
            with open(packed, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" ")
                    if len(parts) == 2 and parts[1] == ref:
                        return parts[0]
    except OSError:
        return None
    return None


CODE_DIRS = ("core", "dashboard")


def code_fingerprint(root: str = ROOT) -> Optional[str]:
    """C-FIX-M16-17 (VỪA): dấu vân tay CODE đang có trên đĩa — (đường, cỡ, mtime) của mọi .py trong core/ + dashboard/. Commit chỉ đổi
    TODO.md / hộp thư / tài liệu không đổi số này (trước: so sha HEAD → mọi commit báo 'code cũ' giả). Không đọc được → None."""
    import hashlib
    h, n = hashlib.sha1(), 0
    for sub in CODE_DIRS:
        base = os.path.join(root, sub)
        for folder, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(folder, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                h.update(f"{os.path.relpath(path, root)}|{st.st_size}|{st.st_mtime_ns}\n".encode("utf-8"))
                n += 1
    return h.hexdigest()[:16] if n else None


BOOT = {"sha": head_sha(), "code": code_fingerprint(), "at": time.time(), "pid": os.getpid(), "port": None}
"""HEAD + dấu vân tay code lúc tiến trình này nạp code (module nạp một lần; Streamlit giữ module cũ tới khi khởi động lại)."""


def run_dir(db_path: Optional[str] = None) -> str:
    db = db_path or os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
    return os.path.join(os.path.dirname(os.path.abspath(db)), "run")


def register(port, db_path: Optional[str] = None, root: str = ROOT) -> Optional[str]:  # noqa: ARG001 - root: test thư mục giả
    """dashboard/serve.py: ghi sổ tiến trình này (cờ bật). Trả đường tệp hoặc None (cờ tắt / không ghi được — không chặn máy chủ)."""
    if not enabled():
        return None
    BOOT["port"] = str(port) if port else None
    path = os.path.join(run_dir(db_path), f"dashboard_{port or 'noport'}.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"port": BOOT["port"], "pid": BOOT["pid"], "sha": BOOT["sha"], "code": BOOT.get("code"), "at": BOOT["at"]}, f)
        return path
    except OSError:
        return None


def _alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)     # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259                                # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _started_at(pid) -> Optional[float]:
    """Giờ (epoch) tiến trình `pid` bắt đầu, hoặc None khi không biết — để nhận ra pid đã bị tiến trình KHÁC dùng lại (THẤP rà M1.7)."""
    try:
        pid = int(pid)
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            ok = ctypes.windll.kernel32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times])
            ctypes.windll.kernel32.CloseHandle(handle)
            if not ok:
                return None
            ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime     # 100 ns từ 1601-01-01
            return ticks / 1e7 - 11644473600
        return os.stat(f"/proc/{pid}").st_ctime
    except (OSError, ValueError, TypeError, AttributeError):
        return None


START_SLACK_S = 5.0            # tiến trình bắt đầu SAU bản ghi quá chừng này → pid đã bị dùng lại, không phải Dashboard đã ghi


def _same_process(rec: Dict, alive) -> bool:
    if not alive(rec.get("pid")):
        return False
    started = _started_at(rec.get("pid"))
    return started is None or not rec.get("at") or started <= float(rec["at"]) + START_SLACK_S


def stale_instances(db_path: Optional[str] = None, head: Optional[str] = None, alive=None, root: str = ROOT) -> List[Dict]:
    """Dashboard còn sống (sổ run/) chạy CODE khác code trên đĩa: [{port, pid, sha, head}]. Bản ghi của tiến trình đã chết (hoặc pid bị
    dùng lại) bị xóa. Bản ghi cũ chưa có dấu vân tay code → so sha HEAD như trước. Cờ tắt → []."""
    if not enabled():
        return []
    head = head or head_sha(root)
    code = code_fingerprint(root)
    if not head and not code:
        return []
    alive = alive or _alive
    out = []
    folder = run_dir(db_path)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    for name in names:
        if not (name.startswith("dashboard_") and name.endswith(".json")):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            continue
        if not _same_process(rec, alive):
            try:                                   # tiến trình đã tắt: bản ghi không còn nghĩa (pid có thể bị dùng lại sau này)
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
            continue
        old = (rec["code"] != code) if rec.get("code") and code else bool(rec.get("sha") and head and rec["sha"] != head)
        if old:
            out.append({"port": rec.get("port"), "pid": rec.get("pid"), "sha": rec.get("sha") or "?", "head": head or "?",
                        "code": rec.get("code")})
    return out


def self_stale(head: Optional[str] = None, root: str = ROOT) -> Optional[str]:
    """Câu báo khi CHÍNH tiến trình này chạy code cũ (code .py trên đĩa đã đổi từ lúc nạp), hoặc None. Commit không đổi .py → None."""
    head = head or head_sha(root)
    code = code_fingerprint(root)
    if BOOT.get("code") and code:
        if BOOT["code"] == code:
            return None
    elif not head or not BOOT["sha"] or BOOT["sha"] == head:
        return None
    where = f"cổng {BOOT['port']}" if BOOT["port"] else f"tiến trình {BOOT['pid']}"
    if BOOT.get("code") and code:                 # C-FIX-THAP-1: nói theo dấu vân tay code (cái thật sự so), không theo sha HEAD
        what = f"code cũ — tệp .py của core/ / dashboard/ đã đổi từ lúc khởi động (dấu {BOOT['code'][:8]} → {code[:8]})"
    else:                                         # bản ghi / tiến trình cũ chưa có dấu vân tay: như trước
        what = f"code cũ {BOOT['sha'][:8]} ≠ HEAD {head[:8]}"
    return (f"{where} chạy {what} — vòng nền gửi job bằng code cũ; tắt / mở lại Dashboard "
            "(tools/stop_dashboard.ps1 -All tắt mọi cổng)")


def banner(db_path: Optional[str] = None) -> str:
    """Băng cảnh báo cho Dashboard đang mở: mọi cổng (kể cả cổng khác) chạy code cũ; '' khi không có / cờ tắt."""
    if not enabled():
        return ""
    rows = stale_instances(db_path)
    if not rows:
        return ""
    def why(r) -> str:                            # C-FIX-THAP-2: bản ghi cũ (chưa có dấu vân tay) chỉ biết sha — nói đúng điều đã so
        if r.get("code"):
            return f"pid {r['pid']}: tệp .py của core/ / dashboard/ đã đổi từ lúc khởi động (dấu {r['code'][:8]})"
        return f"pid {r['pid']}: bản ghi cũ chỉ có sha {r['sha'][:8]} ≠ HEAD {str(r.get('head') or '?')[:8]} — chưa biết tệp .py có đổi"
    ports = ", ".join(f"{r['port'] or '?'} ({why(r)})" for r in rows)
    return (f"⚠ Dashboard có thể chạy code cũ: cổng {ports} — tắt / mở lại "
            "(tools/stop_dashboard.ps1 -All tắt mọi cổng dashboard.serve).")


def check_round(conn) -> Optional[str]:
    """core/bg_poll.round_once: tiến trình giữ vòng nền chạy code cũ → diag `stale_code` (cờ bật). Trả câu báo hoặc None."""
    if not enabled():
        return None
    msg = self_stale()
    if msg:
        from . import diag
        diag.record(conn, "system", "warn", "Vòng nền: " + msg, CODE)
    return msg
