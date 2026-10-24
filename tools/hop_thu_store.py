"""Metadata hộp thư: ID bất biến, receipt, snapshot đọc, archive và queue riêng Git.

Không truy cập data dự án, provider hoặc desktop. File local nằm trong git-dir;
archive chỉ chuyển metadata sau khi bản sao đã được kiểm lại.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

VN = timezone(timedelta(hours=7))
KINDS = {"giao", "nhan", "xong", "gop", "bo", "hoi", "tra_loi", "tin", "het_viec"}
PREFIXES = ("hop_thu/su_kien/", "hop_thu/luu_tru/", "hop_thu/da_doc/")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def timestamp(value):
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("timestamp không hợp lệ") from None
    return dt.replace(tzinfo=VN) if dt.tzinfo is None else dt


def safe_path(root, rel):
    """Kiểm containment/ancestor trước mọi thao tác metadata, không theo symlink."""
    root = Path(root).resolve()
    rel = Path(rel)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("metadata path không hợp lệ")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
            raise ValueError("metadata có symlink; chưa đọc/ghi/chuyển")
    if not current.resolve().is_relative_to(root):
        raise ValueError("metadata vượt phạm vi repo")
    return current


def local_dir(root):
    root = Path(root).resolve()
    git = root / ".git"
    if git.is_file():
        text = git.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir: "):
            raise ValueError("git-dir không hợp lệ")
        git = (root / text[8:]).resolve()
    return (git if git.is_dir() else root / ".hop_thu_local") / "hop_thu_local"


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root, name):
    path = local_dir(root) / (name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 20
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError("metadata đang bị khóa; chưa thay đổi nguồn")
            time.sleep(.05)
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def event_id(value):
    if not isinstance(value, str) or Path(value).name != value or not value.endswith(".json") or "/" in value or "\\" in value:
        raise ValueError("ID sự kiện không hợp lệ")
    return value


def validate_event(ev):
    if not isinstance(ev, dict) or not isinstance(ev.get("kind"), str) or ev.get("kind") not in KINDS:
        raise ValueError("nội dung sự kiện không hợp lệ")
    lane_pattern = r"(?:phien-chinh|codex|nguoi-dung|cloud-[A-Za-z0-9]+|phien-con-[A-Za-z0-9-]+)"
    if not isinstance(ev.get("lane"), str) or not re.fullmatch(lane_pattern, ev["lane"]):
        raise ValueError("trường lane không hợp lệ")
    if "to" in ev and (not isinstance(ev["to"], str) or not re.fullmatch(lane_pattern + r"|all|pool", ev["to"])):
        raise ValueError("trường to không hợp lệ")
    if "task" in ev and (not isinstance(ev["task"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ev["task"])):
        raise ValueError("trường task không hợp lệ")
    if "priority" in ev and (not isinstance(ev["priority"], int) or isinstance(ev["priority"], bool)):
        raise ValueError("trường priority phải là số nguyên")
    if "depends" in ev and (not isinstance(ev["depends"], list) or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", v) for v in ev["depends"])):
        raise ValueError("trường depends phải là danh sách mã việc")
    for field in ("reader", "branch", "commit", "text", "title", "spec", "report", "reply_to"):
        if field in ev and not isinstance(ev[field], str):
            raise ValueError("trường chữ điều khiển không hợp lệ: " + field)
    timestamp(ev["ts"])
    if ev["kind"] in {"giao", "nhan", "xong", "gop", "bo"} and not ev.get("task"):
        raise ValueError("thiếu task")
    return ev


def _metadata_views(root):
    yield Path(root)
    pointer = local_dir(root) / "remote.json"
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("snapshot"), str) or not re.fullmatch(r"[0-9a-f]{40,64}-[0-9a-f]{32}", data["snapshot"]):
            raise ValueError("snapshot remote không hợp lệ")
        view = local_dir(root) / "remote" / data["snapshot"]
        if view.parent != local_dir(root) / "remote" or not view.is_dir():
            raise ValueError("snapshot metadata remote không đầy đủ")
        yield view


def load_records(root):
    records, errors = {}, []
    def put(iid, ev, source):
        try:
            event_id(iid)
            validate_event(ev)
            if iid in records and digest(records[iid]) != digest(ev):
                raise ValueError("cùng ID nhưng khác nội dung")
            records.setdefault(iid, ev)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append((source, str(exc)))
    try:
        views = list(_metadata_views(root))
    except (OSError, ValueError, KeyError) as exc:
        return {}, [("remote-cache", str(exc))]
    for view in views:
        try:
            active = safe_path(view, "hop_thu/su_kien")
            archived = safe_path(view, "hop_thu/luu_tru")
        except ValueError:
            errors.append(("metadata", "thư mục symlink/ngoài phạm vi"))
            continue
        for path in sorted(active.glob("*.json")):
            try:
                path = safe_path(view, path.relative_to(view))
                put(path.name, json.loads(path.read_text(encoding="utf-8-sig")), str(path.relative_to(view)))
            except (OSError, ValueError) as exc:
                errors.append((path.name, str(exc)))
        for path in sorted(archived.glob("*.jsonl")):
            try:
                path = safe_path(view, path.relative_to(view))
                for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    try:
                        row = json.loads(line)
                        put(row["id"], row["event"], f"{path.name}:{n}")
                    except (ValueError, KeyError, TypeError) as exc:
                        errors.append((f"{path.name}:{n}", str(exc)))
            except (OSError, ValueError) as exc:
                errors.append((path.name, str(exc)))
    return records, errors


def require_records(root):
    records, errors = load_records(root)
    if errors:
        raise ValueError("metadata lỗi: " + "; ".join(f"{name}: {why}" for name, why in errors))
    return records


def readers(lane, reader=None):
    if lane == "codex":
        if reader not in ("codex1", "codex2", "codex3"):
            raise ValueError("lane codex cần --reader codex1/codex2/codex3")
        return reader
    if not lane or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in lane):
        raise ValueError("lane reader không hợp lệ")
    if reader and reader != lane:
        raise ValueError("reader phải bằng lane (ngoại trừ codex)")
    return lane


def recipient_map(records):
    result = {}
    for iid, ev in sorted(records.items(), key=lambda row: (timestamp(row[1]["ts"]), row[0])):
        to = ev.get("to")
        if "recipients" in ev:
            listed = ev["recipients"]
            if ev.get("recipient_version") != 1 or not isinstance(listed, list) or not listed or any(not isinstance(r, str) for r in listed):
                raise ValueError("recipient snapshot không hợp lệ")
            if any(not re.fullmatch(r"(?:codex[123]|phien-chinh|nguoi-dung|cloud-[A-Za-z0-9]+|phien-con-[A-Za-z0-9-]+)", r) for r in listed):
                raise ValueError("recipient snapshot reader không hợp lệ")
            required = new_recipients({}, ev["lane"], to)
            if to != "all" and (required is None or set(listed) != set(required)):
                raise ValueError("recipient snapshot không khớp địa chỉ gửi")
            if to == "all" and not set(new_recipients({}, ev["lane"], "all")) <= set(listed):
                raise ValueError("broadcast snapshot thiếu reader bắt buộc")
            result[iid] = sorted(set(listed))
            continue
        # Legacy all không có snapshot: UNKNOWN, không được archive hoặc che unread.
        target = {to} if to else {"phien-chinh"}
        result[iid] = (None if to == "all" or "pool" in target else sorted({r for lane in target
                       for r in (("codex1", "codex2", "codex3") if lane == "codex" else (lane,))}))
    return result


def new_recipients(records, lane, to=None):
    target = {to} if to else {"phien-chinh"}
    if to == "all":
        target = {"phien-chinh", "codex", lane}
        for ev in records.values():
            target.add(ev["lane"])
            if ev.get("to") not in (None, "all", "pool"):
                target.add(ev["to"])
    if "pool" in target:
        return None
    return sorted({reader for target_lane in target
                   for reader in (("codex1", "codex2", "codex3") if target_lane == "codex" else (target_lane,))})


def _is_recipient(ev, required, reader):
    return reader in (required or []) or (required is None and ev.get("to") == "all")


def receipt_records(root, records):
    out = {}
    for view in _metadata_views(root):
        folder = safe_path(view, "hop_thu/da_doc")
        for path in sorted(folder.glob("*/*.json")):
            path = safe_path(view, path.relative_to(view))
            row = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) for key in ("lane", "reader", "event_id", "sha256", "read_at")):
                raise ValueError("receipt thiếu/sai trường điều khiển")
            reader = readers(row["lane"], row["reader"])
            iid = event_id(row["event_id"])
            if iid not in records or row["sha256"] != digest(records[iid]) or path.parent.name != reader:
                raise ValueError("receipt không khớp event/reader/hash: " + path.name)
            dt = timestamp(row["read_at"])
            key = (iid, reader)
            out[key] = min(dt, out.get(key, dt))
    return out


def unread_snapshot(root, lane, reader=None, save=True):
    reader = readers(lane, reader)
    records = require_records(root)
    receipts, recipients = receipt_records(root, records), recipient_map(records)
    found = [{"id": iid, "sha256": digest(ev), "event": ev} for iid, ev in sorted(records.items(), key=lambda r: (timestamp(r[1]["ts"]), r[0]))
             if _is_recipient(ev, recipients[iid], reader) and (iid, reader) not in receipts]
    if save:
        save_snapshot(root, lane, reader, found)
    return found


def save_snapshot(root, lane, reader, items):
    reader = readers(lane, reader)
    path = local_dir(root) / "snapshots" / (reader + ".json")
    with locked(root, "reader-" + reader):
        atomic_bytes(path, canonical({"lane": lane, "reader": reader, "items": items}))


def acknowledge_snapshot(root, lane, reader=None, upto=None, now=None):
    reader = readers(lane, reader)
    records = require_records(root)
    receipt_records(root, records)
    recipients = recipient_map(records)
    with locked(root, "reader-" + reader):
        path = local_dir(root) / "snapshots" / (reader + ".json")
        if not path.exists():
            raise ValueError("chưa có snapshot chua-doc của reader")
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("items"), list):
            raise ValueError("snapshot đọc không hợp lệ")
        if snapshot["lane"] != lane or snapshot["reader"] != reader:
            raise ValueError("snapshot khác reader")
        items = snapshot["items"]
        if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("sha256"), str) for row in items):
            raise ValueError("snapshot đọc thiếu ID/hash")
        if upto:
            ids = [row["id"] for row in items]
            if upto not in ids:
                raise ValueError("--den không thuộc snapshot đã hiển thị")
            items = items[:ids.index(upto) + 1]
        for row in items:
            iid = row["id"]
            if iid not in records or digest(records[iid]) != row["sha256"] or not _is_recipient(records[iid], recipients[iid], reader):
                raise ValueError("snapshot thay đổi hoặc reader không phải người nhận")
        existing = receipt_records(root, records)
        paths = []
        for row in items:
            if (row["id"], reader) in existing:
                continue
            data = {"event_id": row["id"], "sha256": row["sha256"], "lane": lane, "reader": reader,
                    "read_at": (now or datetime.now(VN)).isoformat()}
            dest = safe_path(root, Path("hop_thu/da_doc") / reader / (row["id"][:-5] + "--" + uuid.uuid4().hex + ".json"))
            atomic_bytes(dest, canonical(data) + b"\n")
            queue_path(root, dest)
            paths.append(dest)
    return paths


def unread_counts(root):
    records = require_records(root)
    receipts, recipients = receipt_records(root, records), recipient_map(records)
    counts = {}
    for iid, required in recipients.items():
        expected = required
        if expected is None and records[iid].get("to") == "all":
            expected = new_recipients(records, "phien-chinh", "all")
            counts.setdefault("UNKNOWN legacy all", 0)
            counts["UNKNOWN legacy all"] += 1
        for reader in expected or []:
            counts.setdefault(reader, 0)
            counts[reader] += (iid, reader) not in receipts
    return counts


def archive(root, state, now=None, apply=False):
    now = now or datetime.now(VN)
    cutoff = now - timedelta(days=3)
    with locked(root, "archive"):
        records = require_records(root)
        recipients, receipts = recipient_map(records), receipt_records(root, records)
        open_questions = {q["_file"] for q in state["questions"] if q["_file"] not in state["answers"]}
        eligible, held = [], {}
        active = {path.name for view in _metadata_views(root)
                  for path in safe_path(view, "hop_thu/su_kien").glob("*.json")}
        for iid, ev in sorted(records.items()):
            source = safe_path(root, Path("hop_thu/su_kien") / iid)
            if iid not in active:
                continue
            task = state["tasks"].get(ev.get("task"))
            why = ""
            if iid in open_questions:
                why = "câu hỏi chưa trả lời"
            elif not recipients[iid]:
                why = "chưa xác minh đủ người nhận"
            elif any((iid, reader) not in receipts or receipts[iid, reader] > cutoff for reader in recipients[iid]):
                why = "chưa đủ receipt hoặc chưa đọc quá 3 ngày"
            elif timestamp(ev["ts"]) >= cutoff:
                why = "sự kiện chưa quá 3 ngày"
            elif task and (task.status not in ("GỘP", "BỎ") or task.ts_status >= cutoff):
                why = "việc chưa GỘP/BỎ quá 3 ngày"
            elif not task and ev["kind"] not in ("tin", "hoi", "tra_loi", "het_viec"):
                why = "không đủ trạng thái việc"
            if why:
                held[iid] = why
            else:
                eligible.append(iid)
        if apply:
            for iid in eligible:
                ev = records[iid]
                destination = safe_path(root, Path("hop_thu/luu_tru") / (timestamp(ev["ts"]).strftime("%Y-%m") + ".jsonl"))
                merged = {}
                if destination.exists():
                    for line in destination.read_text(encoding="utf-8").splitlines():
                        row = json.loads(line)
                        if row["id"] in merged and digest(merged[row["id"]]) != digest(row["event"]):
                            raise ValueError("archive có ID xung đột")
                        merged[row["id"]] = row["event"]
                if iid in merged and digest(merged[iid]) != digest(ev):
                    raise ValueError("archive có ID xung đột")
                merged[iid] = ev
                atomic_bytes(destination, b"".join(canonical({"id": key, "event": value}) + b"\n" for key, value in sorted(merged.items())))
                verified = {row["id"]: row["event"] for row in (json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines())}
                if digest(verified.get(iid)) != digest(ev):
                    raise ValueError("bản sao archive không khớp, giữ nguồn")
                source = safe_path(root, Path("hop_thu/su_kien") / iid)
                if source.exists() and digest(json.loads(source.read_text(encoding="utf-8-sig"))) != digest(ev):
                    raise ValueError("nguồn đổi trong lúc archive, giữ nguồn")
                queue_path(root, destination)
                source.unlink(missing_ok=True)
                queue_path(root, source, delete=True, event_sha=digest(ev))
        return {"eligible": eligible, "held": held}


def allowed_path(rel):
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or "\\" in rel:
        return False
    parts = path.parts
    if len(parts) == 3 and parts[:2] == ("hop_thu", "su_kien"):
        return bool(parts[-1].endswith(".json") and not parts[-1].startswith("."))
    if len(parts) == 3 and parts[:2] == ("hop_thu", "luu_tru"):
        return bool(re.fullmatch(r"\d{4}-(?:0[1-9]|1[012])\.jsonl", parts[-1]))
    if len(parts) == 4 and parts[:2] == ("hop_thu", "da_doc"):
        return bool(re.fullmatch(r"(?:codex[123]|phien-chinh|nguoi-dung|cloud-[A-Za-z0-9]+|phien-con-[A-Za-z0-9-]+)", parts[2])
                    and parts[-1].endswith(".json") and not parts[-1].startswith("."))
    return False


def queue_path(root, path, delete=False, event_sha=None):
    root, path = Path(root).resolve(), Path(path).absolute()
    rel = path.relative_to(root).as_posix()
    if not allowed_path(rel):
        raise ValueError("queue chỉ cho phép metadata hộp thư")
    path = safe_path(root, rel)
    row = {"path": rel, "delete": bool(delete), "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if not delete else event_sha}
    manifest = local_dir(root) / "pending" / (hashlib.sha256(rel.encode()).hexdigest() + ".json")
    atomic_bytes(manifest, canonical(row))
    return manifest


def _remote_files(root, git):
    ref = "refs/hop-thu/" + uuid.uuid4().hex
    try:
        git(root, "fetch", "-q", "origin", "refs/heads/main:" + ref)
        base = git(root, "rev-parse", ref).stdout.strip()
        tree = git(root, "ls-tree", "-rz", base, "--", "hop_thu/su_kien", "hop_thu/luu_tru", "hop_thu/da_doc").stdout
        files = {}
        for row in tree.split("\0"):
            if not row:
                continue
            meta, rel = row.split("\t", 1)
            mode, kind, oid = meta.split()
            if mode != "100644" or kind != "blob" or not allowed_path(rel):
                raise ValueError("remote có metadata ngoài whitelist hoặc symlink")
            if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", oid):
                raise ValueError("OID metadata không hợp lệ")
            cache = local_dir(root) / "blobs" / oid
            if cache.exists():
                content = cache.read_bytes()
            else:
                raw = git(root, "cat-file", "blob", oid, binary=True).stdout
                content = raw.encode("utf-8") if isinstance(raw, str) else raw
            algorithm = hashlib.sha1 if len(oid) == 40 else hashlib.sha256 if len(oid) == 64 else None
            if not algorithm or algorithm(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() != oid:
                raise ValueError("cache/blob Git không khớp OID")
            if not cache.exists():
                atomic_bytes(cache, content)
            files[rel] = content
        return base, files
    finally:
        git(root, "update-ref", "-d", ref, check=False)


def _cache_remote(root, base, files):
    pointer = local_dir(root) / "remote.json"
    expected = {rel: hashlib.sha256(content).hexdigest() for rel, content in files.items()}
    if pointer.exists():
        previous = json.loads(pointer.read_text(encoding="utf-8"))
        if previous.get("commit") == base and previous.get("files") == expected:
            existing = local_dir(root) / "remote" / previous["snapshot"]
            if all(hashlib.sha256(safe_path(existing, rel).read_bytes()).hexdigest() == sha for rel, sha in expected.items()):
                require_records(existing)
                return
    folder = local_dir(root) / "remote" / (base + "-" + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    for rel, content in files.items():
        if not allowed_path(rel):
            raise ValueError("remote path ngoài whitelist")
        atomic_bytes(safe_path(folder, rel), content)
    records = require_records(folder)
    receipt_records(folder, records)
    atomic_bytes(pointer, canonical({"snapshot": folder.name, "commit": base, "files": expected}))


def sync_remote(root, git):
    base, files = _remote_files(root, git)
    _cache_remote(root, base, files)
    require_records(root)  # Local/cache trùng ID khác nội dung phải chặn nhận/ghi.
    return base


def _archive_rows(content):
    out = {}
    for line in content.decode("utf-8").splitlines():
        row = json.loads(line)
        if not isinstance(row, dict) or "id" not in row or "event" not in row:
            raise ValueError("archive thiếu/sai ID hoặc event")
        iid, ev = event_id(row["id"]), validate_event(row["event"])
        if iid in out and digest(out[iid]) != digest(ev):
            raise ValueError("archive trùng ID khác nội dung")
        out[iid] = ev
    return out


def _union_files(remote, updates):
    merged = dict(remote)
    for rel, content in updates.items():
        if rel.startswith("hop_thu/luu_tru/"):
            rows = _archive_rows(remote.get(rel, b""))
            for iid, ev in _archive_rows(content).items():
                if iid in rows and digest(rows[iid]) != digest(ev):
                    raise ValueError("remote archive cùng ID khác nội dung")
                rows[iid] = ev
            merged[rel] = b"".join(canonical({"id": iid, "event": ev}) + b"\n" for iid, ev in sorted(rows.items()))
        elif rel in remote and digest(json.loads(remote[rel])) != digest(json.loads(content)):
            raise ValueError("remote có ID/receipt khác nội dung")
        else:
            merged[rel] = content
    return merged


def git_environment(root):
    # Network Git vẫn dùng cơ chế credential chuẩn đã đăng nhập. Chỉ giữ đường
    # dẫn hệ thống/auth agent; không truyền toàn bộ môi trường/API key/token.
    names = ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
             "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "TEMP", "TMP", "SSH_AUTH_SOCK",
             "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "GIT_ALLOW_PROTOCOL")
    env = {name: os.environ.get(name) for name in names if os.environ.get(name) is not None}
    env.setdefault("PATH", "C:/Program Files/Git/cmd;C:/Windows/System32" if os.name == "nt" else "/usr/bin:/bin")
    env.setdefault("SYSTEMROOT", "C:/Windows")
    if not env.get("HOME") and not env.get("USERPROFILE"):
        home = local_dir(root) / "git-home"
        home.mkdir(parents=True, exist_ok=True)
        env.update(HOME=str(home), USERPROFILE=str(home))
    env.update(GIT_TERMINAL_PROMPT="0", PYTHONUTF8="1")
    return env


def _git_index_env(root, index):
    home = local_dir(root) / "git-private-home"
    home.mkdir(parents=True, exist_ok=True)
    return dict(git_environment(root), HOME=str(home), USERPROFILE=str(home), GIT_INDEX_FILE=str(index),
                GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def _drop_pushed_untracked(root, git, updates):
    """Rà gộp 24/10: file metadata CHƯA track mà đã nằm trên origin/main (đã xác minh + có trong cache remote) làm
    `git pull`/`git merge origin/main` của checkout ghi báo 'untracked working tree files would be overwritten'.
    Chỉ bỏ bản local khi chưa track và còn đúng nội dung đã đẩy; file đã track/đã đổi giữ nguyên."""
    for rel, content in updates.items():
        local = safe_path(root, rel)
        if not local.is_file() or local.read_bytes() != content:
            continue
        if git(root, "ls-files", "--error-unmatch", "--", rel, check=False).returncode == 0:
            continue
        local.unlink()


def flush_pending(root, git, message=None, tries=3, co_author=""):
    """Commit-tree trên ref riêng đã pin; index/HEAD/staged code không đổi.

    Manifest là whitelist tường minh. Mỗi retry dựng lại union từ remote mới,
    không force; chỉ xóa đúng phiên bản queue sau xác minh commit ở remote.
    """
    root = Path(root).resolve()
    with locked(root, "flush"):
        manifests = []
        updates, deletes = {}, {}
        for path in sorted((local_dir(root) / "pending").glob("*.json")):
            raw = path.read_bytes()
            row = json.loads(raw)
            if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("delete"), bool) or not isinstance(row.get("sha256"), str):
                raise ValueError("manifest thiếu/sai trường điều khiển")
            rel = row["path"]
            if not allowed_path(rel):
                raise ValueError("manifest path ngoài whitelist")
            source = safe_path(root, rel)
            if row["delete"]:
                if not rel.startswith("hop_thu/su_kien/") or source.exists():
                    raise ValueError("manifest xóa không phải event đã archive")
                deletes[rel] = row["sha256"]
            else:
                if not source.is_file():
                    raise ValueError("file queue không phải file thường")
                content = source.read_bytes()
                if hashlib.sha256(content).hexdigest() != row["sha256"]:
                    raise ValueError("file queue đã đổi; cần đăng ký lại, không gửi snapshot cũ")
                updates[rel] = content
            manifests.append((path, raw))
        if not manifests:
            return {"paths": 0, "commit": None}
        for attempt in range(tries):
            base, remote = _remote_files(root, git)
            merged = _union_files(remote, updates)
            archived = {}
            for rel, content in merged.items():
                if rel.startswith("hop_thu/luu_tru/"):
                    for iid, ev in _archive_rows(content).items():
                        if iid in archived and digest(archived[iid]) != digest(ev):
                            raise ValueError("archive cùng ID khác nội dung")
                        archived[iid] = ev
            for rel, expected in deletes.items():
                iid = Path(rel).name
                if iid not in archived or digest(archived[iid]) != expected:
                    raise ValueError("chưa có bản sao archive khớp, không xóa remote")
                if rel in merged and digest(json.loads(merged[rel])) != expected:
                    raise ValueError("remote event thay đổi, không xóa")
                merged.pop(rel, None)
            # Kiểm cả union raw/archive/receipt TRƯỚC khi tạo commit gửi.
            with tempfile.TemporaryDirectory(prefix="union-", dir=local_dir(root)) as scratch:
                view = Path(scratch)
                for rel, content in merged.items():
                    atomic_bytes(view / rel, content)
                records = require_records(view)
                receipt_records(view, records)
                env = _git_index_env(root, view / "index")
                git(root, "read-tree", base, env=env)
                for rel in sorted(set(updates) | set(deletes)):
                    if rel in merged:
                        path = view / rel
                        oid = git(root, "hash-object", "-w", "--no-filters", "--", str(path), env=env).stdout.strip()
                        git(root, "update-index", "--add", "--cacheinfo", f"100644,{oid},{rel}", env=env)
                    else:
                        git(root, "update-index", "--force-remove", "--", rel, env=env)
                tree = git(root, "write-tree", env=env).stdout.strip()
                summary = f"hộp thư: lô {len(manifests)} sự kiện/metadata"
                text = (message + "\n\n" if message else "") + summary + ("\n\n" + co_author if co_author else "")
                commit = git(root, "-c", "user.name=Hộp thư AI Video", "-c", "user.email=mailbox@localhost",
                             "commit-tree", tree, "-p", base, "-m", text, env=env).stdout.strip()
                pushed = git(root, "push", "origin", f"{commit}:refs/heads/main", check=False)
            if pushed.returncode:
                continue
            # Push trả về thành công chưa đủ: fetch/ancestor xác minh remote.
            verified, files = _remote_files(root, git)
            if git(root, "merge-base", "--is-ancestor", commit, verified, check=False).returncode:
                raise ValueError("chưa xác minh remote chứa lô; giữ queue")
            _cache_remote(root, verified, files)
            for path, raw in manifests:
                if path.exists() and path.read_bytes() == raw:
                    path.unlink()
            _drop_pushed_untracked(root, git, updates)
            return {"paths": len(manifests), "commit": commit, "attempts": attempt + 1}
        raise ValueError("push thất bại sau retry; giữ nguyên queue, không force")
