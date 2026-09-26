"""Số đo miễn phí và khách quan của AI Development System — mọi thứ đọc thẳng từ repo mỗi lần gọi (không đoán, không AI).

    load_areas()                 bản đồ khu vực (devsys/areas.json)
    repo_files(root)             file của repo (git ls-files + file mới chưa add; bỏ file bị .gitignore)
    coverage(cfg, files)         file .py dưới core/ + dashboard/ → khu vực; file không thuộc khu vực nào = cảnh báo
    timeline(root, cfg)          git log (hash, giờ, dòng đầu message, tác giả, file) + khu vực mỗi commit chạm tới
    working_changes(root, cfg)   thay đổi chưa commit ("đang sửa ở đâu ngay lúc này")
    test_map(root, cfg)          test file → module core/dashboard nó import → khu vực
    run_tests(root)              chạy pytest --junitxml, lưu devsys/data/runs/<giờ>.json
    parse_todo(text)             dòng còn mở trong TODO.md ([ ], chưa làm, chưa thử thật, ⏳, còn:) kèm số dòng nguồn
    flags_state(root, cfg)       cờ trong core/features.py (đọc bằng ast, không import) + nơi dùng trong code
    diag_summary(db)             cảnh báo diag_events của CSDL thật (chỉ đọc; không có CSDL thì bỏ qua và nói rõ)
    collect(root)                gom tất cả thành một ảnh chụp (snapshot)
    area_health(snap, cfg)       số đo từng khu vực cho trang Sức khỏe / Tổng quan
"""
import ast
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "devsys", "data")
AREAS_FILE = os.path.join(ROOT, "devsys", "areas.json")
BIG_FILE_LINES = 900
KINDS = ("code", "assets", "docs", "tests")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def nfc(text: str) -> str:
    """Tiếng Việt có hai cách mã hóa dấu (dựng sẵn / tổ hợp): so chữ luôn trên dạng NFC."""
    return unicodedata.normalize("NFC", text or "")


def data_dir(root: str = ROOT) -> str:
    return os.path.join(root, "devsys", "data")


# ---- bản đồ khu vực ---------------------------------------------------------------------------------------------------
def load_areas(path: Optional[str] = None) -> Dict:
    with open(path or AREAS_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    ids = [a["id"] for a in cfg.get("areas", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("devsys/areas.json: trùng id khu vực")
    for a in cfg["areas"]:
        for k in KINDS + ("flags", "diag_stages", "keywords"):
            a.setdefault(k, [])
        a.setdefault("weight", 1.0)
        a.setdefault("description", "")
    cfg.setdefault("scan_roots", ["core", "dashboard"])
    cfg.setdefault("infra_modules", [])
    return cfg


def area_by_id(cfg: Dict) -> Dict[str, Dict]:
    return {a["id"]: a for a in cfg["areas"]}


def _posix(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def matches(path: str, patterns: Iterable[str]) -> bool:
    p = _posix(path)
    return any(fnmatch.fnmatchcase(p, pat) for pat in patterns)


def areas_of_path(cfg: Dict, path: str, kinds: Sequence[str] = KINDS) -> List[str]:
    return [a["id"] for a in cfg["areas"] if any(matches(path, a[k]) for k in kinds)]


def area_files(cfg_area: Dict, files: Sequence[str], kinds: Sequence[str] = KINDS) -> List[str]:
    pats = [p for k in kinds for p in cfg_area.get(k, [])]
    return sorted(f for f in files if matches(f, pats))


# ---- git -------------------------------------------------------------------------------------------------------------
def git(root: str, *args: str, timeout: int = 60) -> str:
    """Output of one git command (UTF-8, tên file không bị mã hóa \\ooo). Lỗi → GitError (người gọi quyết định bỏ qua hay báo)."""
    try:
        proc = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitError(f"không chạy được git: {e}") from None
    if proc.returncode != 0:
        raise GitError((proc.stderr or proc.stdout or "").strip()[:300] or f"git {args[0]} lỗi {proc.returncode}")
    return proc.stdout


class GitError(Exception):
    pass


def repo_files(root: str = ROOT) -> List[str]:
    """Every file of the repo that git tracks or would track (new files not yet added included, ignored files excluded)."""
    try:
        out = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        files = sorted({_posix(p) for p in out.split("\0") if p})
        return [f for f in files if os.path.isfile(os.path.join(root, f))]
    except GitError:
        found = []
        for base, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "data", "node_modules")]
            for n in names:
                found.append(_posix(os.path.relpath(os.path.join(base, n), root)))
        return sorted(found)


def head(root: str = ROOT) -> Optional[Dict]:
    try:
        out = git(root, "log", "-1", "--date=iso-strict", "--pretty=format:%H%x1f%h%x1f%ad%x1f%s").strip()
    except GitError:
        return None
    if not out:
        return None
    h, short, date, subject = (out.split("\x1f") + ["", "", "", ""])[:4]
    try:
        branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except GitError:
        branch = ""
    return {"hash": h, "short": short, "date": date, "subject": subject, "branch": branch}


def parse_log(text: str) -> List[Dict]:
    """Records of `git log --name-only --pretty=format:%x1e%H%x1f%h%x1f%ad%x1f%an%x1f%s`."""
    out = []
    for rec in text.split("\x1e"):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        first, _, rest = rec.partition("\n")
        parts = first.split("\x1f")
        if len(parts) < 5:
            continue
        files = [_posix(f.strip()) for f in rest.splitlines() if f.strip()]
        out.append({"hash": parts[0], "short": parts[1], "date": parts[2], "author": parts[3], "subject": "\x1f".join(parts[4:]),
                    "files": files})
    return out


def timeline(root: str, cfg: Dict, limit: int = 150) -> List[Dict]:
    try:
        text = git(root, "log", f"-n{int(limit)}", "--date=iso-strict", "--name-only",
                   "--pretty=format:%x1e%H%x1f%h%x1f%ad%x1f%an%x1f%s")
    except GitError:
        return []
    commits = parse_log(text)
    for c in commits:
        c["areas"] = sorted({a for f in c["files"] for a in areas_of_path(cfg, f)})
    return commits


def parse_porcelain(text: str) -> List[Dict]:
    """`git status --porcelain=v1 -z -uall` → [{"path", "status", "orig"}]. Renames carry the old path in the next NUL field."""
    fields = text.split("\0")
    out, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        orig = None
        if code[0] in "RC" or code[1] in "RC":
            orig = fields[i] if i < len(fields) else None
            i += 1
        status = {"??": "mới (chưa add)", "A": "thêm", "M": "sửa", "D": "xóa", "R": "đổi tên", "C": "chép", "U": "xung đột"}
        label = status.get(code) or status.get(code.strip()[:1] or "M", "sửa")
        out.append({"path": _posix(path), "status": label, "code": code, "orig": _posix(orig) if orig else None})
    return out


def working_changes(root: str, cfg: Dict) -> List[Dict]:
    try:
        entries = parse_porcelain(git(root, "status", "--porcelain=v1", "-z", "-uall"))
    except GitError:
        return []
    counts: Dict[str, Tuple[int, int]] = {}
    try:
        for line in git(root, "diff", "--numstat", "HEAD").splitlines():
            a, d, p = (line.split("\t") + ["", "", ""])[:3]
            if p:
                counts[_posix(p)] = (int(a) if a.isdigit() else 0, int(d) if d.isdigit() else 0)
    except GitError:
        pass
    for e in entries:
        full = os.path.join(root, e["path"])
        if e["code"] == "??" and os.path.isfile(full):
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    counts.setdefault(e["path"], (sum(1 for _ in f), 0))
            except OSError:
                pass
        e["added"], e["deleted"] = counts.get(e["path"], (0, 0))
        e["areas"] = areas_of_path(cfg, e["path"])
        try:
            e["mtime"] = os.path.getmtime(full)
        except OSError:
            e["mtime"] = None
    return entries


def status_key(root: str = ROOT) -> str:
    """Cheap fingerprint of 'what the working copy looks like now' (HEAD + changed files + their mtimes) — the cache key of the app."""
    parts = []
    try:
        parts.append(git(root, "rev-parse", "HEAD").strip())
        for e in parse_porcelain(git(root, "status", "--porcelain=v1", "-z", "-uall")):
            full = os.path.join(root, e["path"])
            parts.append(f"{e['code']}{e['path']}{os.path.getmtime(full) if os.path.exists(full) else 0}")
    except GitError as e:
        parts.append(str(e))
    for rel in ("TODO.md", "devsys/areas.json", "core/features.py", "devsys/rubric.md"):
        full = os.path.join(root, rel)
        parts.append(str(os.path.getmtime(full)) if os.path.exists(full) else "-")
    for sub in ("runs", "scores"):
        d = os.path.join(data_dir(root), sub)
        parts.append(str(max((os.path.getmtime(os.path.join(d, n)) for n in os.listdir(d)), default=0)) if os.path.isdir(d) else "-")
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


# ---- khu vực: phủ file ------------------------------------------------------------------------------------------------
def code_files(files: Sequence[str], scan_roots: Sequence[str]) -> List[str]:
    return [f for f in files if f.endswith(".py") and any(f.startswith(r.rstrip("/") + "/") for r in scan_roots)]


def coverage(cfg: Dict, files: Sequence[str]) -> Dict:
    """Every .py under the scan roots → the areas whose `code` patterns include it; `unmapped` = belongs to none (a warning)."""
    mapping = {f: areas_of_path(cfg, f, ("code",)) for f in code_files(files, cfg["scan_roots"])}
    return {"files": mapping, "unmapped": sorted(f for f, a in mapping.items() if not a),
            "multi": sorted(f for f, a in mapping.items() if len(a) > 1)}


def line_count(path: str) -> int:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


# ---- test → khu vực ---------------------------------------------------------------------------------------------------
_IMPORT = re.compile(r"^[ \t]*(?:from[ \t]+((?:core|dashboard)(?:\.\w+)*)[ \t]+import[ \t]+(\([^)]*\)|[^\n#]+)"
                     r"|import[ \t]+((?:core|dashboard)(?:\.\w+)*))", re.M)


def _module_file(root: str, dotted: str) -> Optional[str]:
    rel = dotted.replace(".", "/")
    if os.path.isfile(os.path.join(root, rel + ".py")):
        return rel + ".py"
    if os.path.isfile(os.path.join(root, rel, "__init__.py")):
        return rel + "/__init__.py"
    return None


def imported_modules(root: str, source: str) -> List[str]:
    """core/dashboard module files a Python source imports (`from core import a, b`, `from core.x import y`, `import core.x`)."""
    found = set()
    for m in _IMPORT.finditer(source):
        base = m.group(1) or m.group(3)
        names = m.group(2) or ""
        if m.group(1):
            for raw in names.strip("() \t\n").replace("\n", " ").split(","):
                name = raw.strip().split(" as ")[0].strip()
                if not name or name == "*":
                    continue
                sub = _module_file(root, f"{base}.{name}")
                if sub:
                    found.add(sub)
                    continue
                own = _module_file(root, base)
                if own:
                    found.add(own)
        else:
            own = _module_file(root, base)
            if own:
                found.add(own)
    return sorted(f for f in found if not f.endswith("/__init__.py") or f.count("/") > 1)


def test_map(root: str, cfg: Dict, files: Optional[Sequence[str]] = None) -> Dict[str, Dict]:
    """tests/test_*.py → {"modules": [...], "areas": [...]}.

    Shared modules — the infrastructure list of areas.json plus any module imported by ≥ 30% of the test files (the job runner, the
    Claude runner used as a mock…) — only decide the areas of a test that imports nothing more specific, or whose file name names
    them (test_runner.py → core/runner.py). So a test of `capacity` is not counted for every area that uses the database."""
    files = files if files is not None else repo_files(root)
    tests = sorted(f for f in files if re.match(r"tests/test_[^/]*\.py$", f))
    imports = {}
    for t in tests:
        try:
            with open(os.path.join(root, t), encoding="utf-8", errors="replace") as fh:
                imports[t] = imported_modules(root, fh.read())
        except OSError:
            imports[t] = []
    freq: Dict[str, int] = {}
    for mods in imports.values():
        for m in mods:
            freq[m] = freq.get(m, 0) + 1
    shared = set(cfg.get("infra_modules", [])) | {m for m, n in freq.items() if n >= max(10, 0.3 * len(tests))}
    out = {}
    for t in tests:
        mods = imports[t]
        stem = os.path.splitext(os.path.basename(t))[0][5:]
        named = [m for m in mods if os.path.splitext(os.path.basename(m))[0] == stem]
        specific = named + [m for m in mods if m not in shared and m not in named] or mods
        areas = {a for m in specific for a in areas_of_path(cfg, m, ("code",))}
        areas |= {a["id"] for a in cfg["areas"] if matches(t, a.get("tests", []))}
        out[t] = {"modules": mods, "areas": sorted(areas), "counted": sorted(specific)}
    return out


# ---- chạy test (pytest --junitxml) ------------------------------------------------------------------------------------
def _test_file(root: str, classname: str, file_attr: str = "") -> str:
    if file_attr:
        return _posix(file_attr)
    parts = classname.split(".")
    for i in range(1, len(parts) + 1):
        cand = "/".join(parts[:i]) + ".py"
        if os.path.isfile(os.path.join(root, cand)):
            return cand
    return "/".join(parts[:2]) + ".py" if len(parts) >= 2 else classname


def parse_junit(xml_text: str, root: str = ROOT) -> Dict:
    """JUnit XML of pytest → {"totals": {...}, "files": {"tests/test_x.py": {"passed", "failed", "errors", "skipped", "failed_names"}}}."""
    tree = ET.fromstring(xml_text)
    files: Dict[str, Dict] = {}
    totals = {"tests": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for case in tree.iter("testcase"):
        f = _test_file(root, case.get("classname", ""), case.get("file", ""))
        rec = files.setdefault(f, {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failed_names": []})
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        kind = "passed"
        for child in case:
            if child.tag == "failure":
                kind = "failed"
            elif child.tag == "error":
                kind = "errors"
            elif child.tag == "skipped" and kind == "passed":
                kind = "skipped"
        rec[kind] += 1
        totals[kind] += 1
        totals["tests"] += 1
        if kind in ("failed", "errors"):
            msg = ""
            for child in case:
                if child.tag in ("failure", "error"):
                    text = (child.get("message") or child.text or "").strip()
                    msg = text.splitlines()[0][:200] if text else ""
            rec["failed_names"].append({"name": name, "message": msg})
    return {"totals": totals, "files": files}


def running_lock(root: str = ROOT) -> str:
    return os.path.join(data_dir(root), "runs", ".running")


def tests_running(root: str = ROOT, stale_min: int = 40) -> Optional[Dict]:
    """The test run in progress (started from the app or the collector), None when none. A lock older than 40 min is stale."""
    path = running_lock(root)
    try:
        with open(path, encoding="utf-8") as f:
            info = json.load(f)
        if time.time() - float(info.get("started", 0)) > stale_min * 60:
            return None
        return info
    except (OSError, ValueError):
        return None


def run_tests(root: str = ROOT, timeout: int = 1800, extra_args: Sequence[str] = (), python: Optional[str] = None) -> Dict:
    """Run the whole suite with --junitxml and store the result in devsys/data/runs/<time>.json. Returns the stored record."""
    runs = os.path.join(data_dir(root), "runs")
    os.makedirs(runs, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    xml_path = os.path.join(runs, f"{stamp}.xml")
    lock = running_lock(root)
    with open(lock, "w", encoding="utf-8") as f:
        json.dump({"started": time.time(), "pid": os.getpid()}, f)
    t0 = time.time()
    hd = head(root)
    try:
        cmd = [python or sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml_path}", *extra_args]
        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            code, tail = proc.returncode, (proc.stdout or "")[-3000:] + (proc.stderr or "")[-1500:]
        except subprocess.TimeoutExpired:
            code, tail = -1, f"quá thời gian {timeout} s"
        record = {"date": now_iso(), "commit": hd["hash"] if hd else None, "short": hd["short"] if hd else None,
                  "dirty": bool(working_changes(root, {"areas": []})), "duration_s": round(time.time() - t0, 1),
                  "returncode": code, "args": list(extra_args), "tail": tail}
        if os.path.exists(xml_path):
            with open(xml_path, encoding="utf-8") as f:
                record.update(parse_junit(f.read(), root))
            os.remove(xml_path)
        else:
            record.update({"totals": None, "files": {}, "error": "pytest không tạo file junit — xem 'tail'"})
        with open(os.path.join(runs, f"{stamp}.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        return record
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def list_runs(root: str = ROOT) -> List[Dict]:
    runs = os.path.join(data_dir(root), "runs")
    out = []
    if os.path.isdir(runs):
        for n in sorted(os.listdir(runs)):
            if n.endswith(".json"):
                try:
                    with open(os.path.join(runs, n), encoding="utf-8") as f:
                        rec = json.load(f)
                    rec["_file"] = n
                    out.append(rec)
                except (OSError, ValueError):
                    continue
    return out


def tests_by_area(run: Optional[Dict], tmap: Dict[str, Dict], cfg: Dict) -> Dict[str, Dict]:
    """Per area: mapped test files, and — when a run exists — passed/failed/errors/skipped of those files + failing test names."""
    out = {a["id"]: {"test_files": [], "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failed_names": [], "not_run": []}
           for a in cfg["areas"]}
    files = (run or {}).get("files") or {}
    for t, info in tmap.items():
        for a in info["areas"]:
            if a not in out:
                continue
            rec = out[a]
            rec["test_files"].append(t)
            r = files.get(t)
            if r is None:
                rec["not_run"].append(t)
                continue
            for k in ("passed", "failed", "errors", "skipped"):
                rec[k] += r.get(k, 0)
            rec["failed_names"] += [dict(n, file=t) for n in r.get("failed_names", [])]
    return out


# ---- TODO.md ----------------------------------------------------------------------------------------------------------
TODO_MARKERS = (("[ ]", re.compile(r"\[ \]")), ("chưa làm", re.compile(r"chưa làm", re.I)),
                ("chưa thử thật", re.compile(r"chưa (?:thử|chạy) thật", re.I)), ("⏳", re.compile("⏳")),
                ("còn:", re.compile(r"(?<!\w)còn\s*:", re.I)))
WAITING_USER = re.compile(r"(cần|chờ) người dùng|chờ feedback|người dùng (quyết|duyệt|chốt)", re.I)


def parse_todo(text: str) -> List[Dict]:
    """Open items of TODO.md: lines with "[ ]", "chưa làm", "chưa thử/chạy thật", "⏳" or "còn:". Each keeps its line number, the
    heading it sits under, the markers found and the full source line. kind: open · recurring (the fixed 'MỖI LẦN' checklist) ·
    paused ('Tạm gác'). `waiting_user`: the line says a person must decide/provide something."""
    items, section, kind = [], "", "open"
    for no, raw in enumerate(nfc(text).splitlines(), 1):
        line = raw.rstrip()
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            section = h.group(2).strip()
            kind = "recurring" if "MỖI LẦN" in section.upper() else "paused" if "tạm gác" in section.lower() else "open"
            continue
        if re.match(r"^\s*[-*]\s*\[x\]", line, re.I) and not re.search(r"chưa (?:thử|chạy) thật|còn\s*:", line, re.I):
            continue
        found = [name for name, rx in TODO_MARKERS if rx.search(line)]
        if not found:
            continue
        focus = ""
        m = re.search(r"(?<!\w)còn\s*:(.{0,300})", line, re.I)
        if m:
            focus = "còn:" + m.group(1).split("|")[0].strip()
        items.append({"line": no, "section": section, "markers": found, "kind": kind, "text": line.strip(),
                      "focus": focus, "waiting_user": bool(WAITING_USER.search(line))})
    return items


def _strong_terms(area: Dict) -> List[re.Pattern]:
    """Terms that tie a TODO line to an area without doubt: code paths, `name.py`, module names with '_' and the area's flags."""
    terms = []
    for pat in area.get("code", []):
        if any(ch in pat for ch in "*?["):
            continue
        stem = os.path.splitext(os.path.basename(pat))[0]
        if stem == "__init__":
            continue
        terms.append(re.compile(re.escape(pat), re.I))
        terms.append(re.compile(r"(?<![\w/])" + re.escape(stem) + r"\.py\b", re.I))
        if "_" in stem:
            terms.append(re.compile(r"(?<![\w/])" + re.escape(stem) + r"(?!\w)", re.I))
    for flag in area.get("flags", []):
        terms.append(re.compile(r"(?<!\w)" + re.escape(flag) + r"(?!\w)"))
    return terms


def todo_by_area(items: List[Dict], cfg: Dict) -> Dict[str, List[Dict]]:
    """Open TODO items per area: a line naming an area's code file / module / flag belongs to it; a line naming none goes by the
    area keywords (whole words). Lines that match nothing are listed under '_chung'."""
    strong = {a["id"]: _strong_terms(a) for a in cfg["areas"]}
    weak = {a["id"]: [re.compile(r"(?<!\w)" + re.escape(nfc(k)) + r"(?!\w)", re.I) for k in a.get("keywords", [])] for a in cfg["areas"]}
    out: Dict[str, List[Dict]] = {a["id"]: [] for a in cfg["areas"]}
    out["_chung"] = []
    for it in items:
        if it["kind"] == "recurring":
            continue
        hits = [aid for aid, rx in strong.items() if any(r.search(it["text"]) for r in rx)]
        how = "tên file/cờ"
        if not hits:
            hits = [aid for aid, rx in weak.items() if any(r.search(it["text"]) for r in rx)]
            how = "từ khóa"
        for aid in hits or ["_chung"]:
            out[aid].append(dict(it, matched_by=how if hits else ""))
    return out


# ---- cờ tính năng (core/features.py) ----------------------------------------------------------------------------------
def read_features(root: str = ROOT) -> Dict[str, Dict]:
    """FEATURES of core/features.py read with ast (the file on disk now, not an imported copy)."""
    path = os.path.join(root, "core", "features.py")
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return {}
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "FEATURES" and node.value is not None:
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return {}
    return {}


def flags_state(root: str, cfg: Dict, files: Optional[Sequence[str]] = None) -> List[Dict]:
    feats = read_features(root)
    files = files if files is not None else repo_files(root)
    sites: Dict[str, List[str]] = {k: [] for k in feats}
    rx = re.compile(r"""features\.on\(\s*["']([a-z0-9_]+)["']|feature_on\(\s*["']([a-z0-9_]+)["']""")
    for f in files:
        if not f.endswith(".py") or not (f.startswith("core/") or f.startswith("dashboard/")) or f == "core/features.py":
            continue
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                for no, line in enumerate(fh, 1):
                    for m in rx.finditer(line):
                        name = m.group(1) or m.group(2)
                        if name in sites:
                            sites[name].append(f"{f}:{no}")
        except OSError:
            continue
    out = []
    for name, meta in feats.items():
        env = os.environ.get("FEATURE_" + name.upper(), "").strip().lower()
        on = True if env in ("1", "true", "on", "yes") else False if env in ("0", "false", "off", "no") else bool(meta.get("verified"))
        out.append({"name": name, "label": meta.get("label", ""), "why": meta.get("why", ""), "verified": bool(meta.get("verified")),
                    "env": env or None, "on": on, "sites": sites.get(name, []),
                    "areas": [a["id"] for a in cfg["areas"] if name in a.get("flags", [])]})
    return out


# ---- diag (CSDL thật, chỉ đọc) ---------------------------------------------------------------------------------------
def default_db(root: str = ROOT) -> str:
    return os.environ.get("PIPELINE_DB") or os.path.join(root, "data", "manifest.sqlite")


def diag_summary(db_path: Optional[str] = None, days: int = 14, root: str = ROOT) -> Dict:
    """Warnings/errors of the last `days` days from diag_events, opened read-only. No database → available False with the reason."""
    db_path = db_path or default_db(root)
    if not os.path.exists(db_path):
        return {"available": False, "note": f"không có CSDL {os.path.relpath(db_path, root) if db_path.startswith(root) else db_path} "
                                             "(máy này chưa chạy Dashboard thật) — bỏ qua phần diag", "by_stage": {}, "recent": []}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    try:
        uri = "file:" + db_path.replace("\\", "/") + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT stage, severity, code, message, count, last_at FROM diag_events WHERE last_at>=? "
                                "ORDER BY last_at DESC LIMIT 400", (since,)).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        return {"available": False, "note": f"không đọc được diag_events ({type(e).__name__}: {e})", "by_stage": {}, "recent": []}
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from core.diag import redact
    except Exception:  # noqa: BLE001 - redaction is best effort; messages are short already
        def redact(t):
            return str(t)
    by_stage: Dict[str, Dict[str, int]] = {}
    recent = []
    for r in rows:
        s = by_stage.setdefault(r["stage"], {"info": 0, "warn": 0, "error": 0})
        s[r["severity"]] = s.get(r["severity"], 0) + int(r["count"] or 1)
        if r["severity"] in ("warn", "error") and len(recent) < 60:
            recent.append({"stage": r["stage"], "severity": r["severity"], "code": r["code"], "message": redact(r["message"])[:300],
                           "count": r["count"], "last_at": r["last_at"]})
    return {"available": True, "note": f"{len(rows)} dòng diag trong {days} ngày", "by_stage": by_stage, "recent": recent, "days": days}


# ---- ảnh chụp toàn bộ -------------------------------------------------------------------------------------------------
def collect(root: str = ROOT, cfg: Optional[Dict] = None, db_path: Optional[str] = None, log_limit: int = 150) -> Dict:
    t0 = time.time()
    cfg = cfg or load_areas(os.path.join(root, "devsys", "areas.json"))
    files = repo_files(root)
    cov = coverage(cfg, files)
    tmap = test_map(root, cfg, files)
    runs = list_runs(root)
    latest = runs[-1] if runs else None
    try:
        with open(os.path.join(root, "TODO.md"), encoding="utf-8") as f:
            todo = parse_todo(f.read())
        todo_note = ""
    except OSError as e:
        todo, todo_note = [], f"không đọc được TODO.md: {e}"
    lines = {f: line_count(os.path.join(root, f)) for f in files if f.endswith(".py")}
    snap = {
        "generated_at": now_iso(), "root": root, "head": head(root), "areas_version": cfg.get("version"),
        "files_total": len(files), "coverage": cov, "timeline": timeline(root, cfg, log_limit), "working": working_changes(root, cfg),
        "test_map": tmap, "latest_run": latest, "runs": [{k: r.get(k) for k in ("date", "short", "commit", "totals", "duration_s",
                                                                                "returncode", "_file")} for r in runs],
        "todo": todo, "todo_note": todo_note, "todo_by_area": todo_by_area(todo, cfg), "flags": flags_state(root, cfg, files),
        "diag": diag_summary(db_path, root=root), "line_counts": lines,
        "big_files": sorted(([f, n] for f, n in lines.items() if n > BIG_FILE_LINES and (f.startswith("core/") or f.startswith("dashboard/"))),
                            key=lambda x: -x[1]),
        "tests_by_area": tests_by_area(latest, tmap, cfg), "files": files,
    }
    snap["collect_s"] = round(time.time() - t0, 2)
    return snap


def area_health(snap: Dict, cfg: Dict) -> Dict[str, Dict]:
    """Free, objective measures of each area (the Sức khỏe page, the overview and the scorer's facts)."""
    out = {}
    files = snap["files"]
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    for a in cfg["areas"]:
        code = area_files(a, files, ("code",))
        t = snap["tests_by_area"].get(a["id"], {})
        flags = [f for f in snap["flags"] if a["id"] in f["areas"]]
        diag_n = {"warn": 0, "error": 0}
        for st in a.get("diag_stages", []):
            s = snap["diag"].get("by_stage", {}).get(st, {})
            diag_n["warn"] += s.get("warn", 0)
            diag_n["error"] += s.get("error", 0)
        commits = [c for c in snap["timeline"] if a["id"] in c.get("areas", [])]
        recent = 0
        for c in commits:
            try:
                if datetime.fromisoformat(c["date"]) >= week_ago:
                    recent += 1
            except ValueError:
                pass
        todo_items = snap["todo_by_area"].get(a["id"], [])
        out[a["id"]] = {
            "code_files": len(code), "lines": sum(snap["line_counts"].get(f, 0) for f in code),
            "big_files": [[f, n] for f, n in snap["big_files"] if f in code],
            "test_files": len(t.get("test_files", [])), "passed": t.get("passed", 0), "failed": t.get("failed", 0) + t.get("errors", 0),
            "skipped": t.get("skipped", 0), "not_run": len(t.get("not_run", [])), "failed_names": t.get("failed_names", []),
            "flags_total": len(flags), "flags_verified": sum(1 for f in flags if f["verified"]),
            "flags_unverified": [f["name"] for f in flags if not f["verified"]],
            "todo_open": sum(1 for i in todo_items if i["kind"] == "open"), "todo_waiting_user": sum(1 for i in todo_items if i["waiting_user"]),
            "diag_warn": diag_n["warn"], "diag_error": diag_n["error"],
            "commits": len(commits), "commits_7d": recent, "last_commit": commits[0] if commits else None,
            "working": [w for w in snap["working"] if a["id"] in w["areas"]],
        }
    return out


def append_event(kind: str, root: str = ROOT, **fields) -> Dict:
    os.makedirs(data_dir(root), exist_ok=True)
    ev = {"at": now_iso(), "kind": kind, **fields}
    with open(os.path.join(data_dir(root), "events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def read_events(root: str = ROOT, limit: int = 200) -> List[Dict]:
    path = os.path.join(data_dir(root), "events.jsonl")
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out[-limit:]


def save_snapshot(snap: Dict, root: str = ROOT) -> str:
    os.makedirs(data_dir(root), exist_ok=True)
    path = os.path.join(data_dir(root), "snapshot.json")
    slim = {k: v for k, v in snap.items() if k not in ("files", "line_counts")}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)
    return path
