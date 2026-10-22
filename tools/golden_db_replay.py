"""Replay prepare/build từ bản sao DB và dependency chỉ đọc; không gửi provider."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = ROOT          # C-GOLDEN5: cây chứa CÔNG CỤ này; ROOT = cây code ĐANG SO (worker --ab đổi theo request["code_root"])
PUBLIC = {"LLM_PROVIDER", "image_model", "video_model"}


class SandboxDenied(ValueError):
    def __init__(self, kind, path=None):
        super().__init__("INSUFFICIENT_INPUT: sandbox chặn")
        self.diagnostic = {"kind": kind, "path": path or "<outside-root>"}


def _job_ref_paths(package, root):
    """Chỉ cấp quyền FILE ảnh được gói job tham chiếu, không cấp cây thư mục."""
    _tool_capture()._safe(package)       # C-GOLDEN5: của CÂY CÔNG CỤ (trong worker --ab, `tools.*` là của cây code đang so)
    paths = set()
    for ref in package.get("refs", []):
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            continue
        path = Path(ref["path"])
        if path.is_absolute():
            try:
                path = path.relative_to(root)
            except ValueError:
                continue
        name = path.as_posix()
        if (name.startswith(("data/_plates3d/cache/", "data/assets/"))
                and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".avif"}):
            candidate = _plain(name, root)
            if candidate.is_file():
                paths.add(name)
    return paths


class DataChanged(ValueError):
    pass


# C-GOLDEN4: worker đọc MỌI tệp dưới data/ của ref-root (chỉ đọc, mỗi lần đọc vào manifest có sha) — trừ danh sách cấm cứng này.
# Lần 1 thiếu data/_plates3d, lần 3 thiếu data/skills: allowlist từng thư mục luôn sót dependency mới → sửa gốc bằng danh sách CẤM.
DENIED_SUFFIXES = (".key", ".pem", ".p12", ".pfx", ".crt", ".log", ".bak", ".old", ".zip", ".7z", ".tar", ".gz")
DENIED_SEGMENTS = ("env", "db", "bak", "log")           # một khúc giữa các dấu chấm của tên: x.env.local, dashboard.env.bak, a.db-wal …
DENIED_WORDS = ("token", "secret", "password", "passwd", "credential", "cookie", "apikey", "api_key", "private_key", "owner_setup_code",
                "id_rsa", "id_ed25519", "service_account")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif")


def read_denied(name):
    """Tên tương đối (posix) bị cấm đọc dù nằm dưới data/ — so KHÔNG phân biệt hoa thường: CSDL (mọi *.sqlite* / *.db* — worker chỉ dùng
    snapshot trong scratch), mọi biến thể .env (dashboard.env, x.env.local, .env.bak), log / bản sao lưu / nén, tệp khóa / credential, data/backup*.
    Tên lạ kiểu Windows (':' luồng NTFS, khúc kết thúc bằng '.' hoặc dấu cách) cũng cấm. Ảnh (đuôi ảnh) không xét từ khóa (gold_token.png là ảnh Kho).
    True = cấm."""
    low = str(name).casefold()
    parts = Path(low).parts
    if not parts or ":" in low or any(p.endswith((".", " ")) for p in parts):
        return True
    base = parts[-1]
    if low == "data/backup" or low.startswith("data/backup"):
        return True
    segments = base.split(".")
    if any(s in DENIED_SEGMENTS or s.startswith(("sqlite", "db-", "env")) for s in segments[1:]) or segments[0] in ("", "env"):
        return True
    if base.endswith(IMAGE_SUFFIXES):
        return False
    return base.endswith(DENIED_SUFFIXES) or any(w in base for w in DENIED_WORDS)


FINGERPRINT = "pregen_fingerprint"
# C-GOLDEN2 (e): builder đòi tệp nền 3D / ảnh Kho KHÁC tệp trong refs đã gửi = dữ liệu sân khấu / Kho đổi sau ngày gửi
CHANGED_DATA_PREFIXES = ("data/_plates3d/", "data/assets/")
CHANGED_DATA_KINDS = {"data", "read", "manifest", "directory"}


def pinned_choice(choice, job):
    """C-GOLDEN2 (c): model của lần dựng lại = cột jobs.model của CHÍNH job (như lúc gửi), không từ cấu hình chung / chế độ thử rẻ."""
    model = (job or {}).get("model")
    return {**choice, "model": model} if model else choice


def _without_fingerprint(raw):
    try:
        body = json.loads(raw)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(body, dict):
        return None, None
    fp = body.pop(FINGERPRINT, None)
    return json.dumps(body, ensure_ascii=False, sort_keys=True), fp


def classify_answer(answer):
    """C-GOLDEN2 (e): INSUFFICIENT_INPUT vì sandbox chặn đọc tệp nền/Kho ngoài refs đã gửi → DATA_CHANGED có lý do (tệp nào).
    C-GOLDEN4: worker nay đọc được mọi tệp dưới data/ trừ danh sách cấm — lần chặn vì bí mật mang kind "secret" (ngoài CHANGED_DATA_KINDS)
    nên KHÔNG bị gán DATA_CHANGED; còn lại là tệp mới chỉ có ở lần replay (kind manifest) dưới nền/Kho."""
    if not isinstance(answer, dict) or answer.get("status") != "INSUFFICIENT_INPUT":
        return answer
    diag = answer.get("diagnostic")
    items = diag if isinstance(diag, list) else [diag] if isinstance(diag, dict) else []
    paths = [str(d.get("path")) for d in items if isinstance(d, dict) and d.get("kind") in CHANGED_DATA_KINDS
             and str(d.get("path") or "").startswith(CHANGED_DATA_PREFIXES)]
    if not paths or len(paths) != len(items):
        return answer
    return {**answer, "status": "DATA_CHANGED", "paths": sorted(set(paths)),
            "reason": "builder đòi tệp nền/Kho khác refs đã gửi (dữ liệu sân khấu/Kho đổi sau ngày gửi): " + ", ".join(sorted(set(paths))[:5])}


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _signature(path, expected=None):
    """Chữ ký tệp/thư mục để so manifest. expected dạng {"stat": …} (C-GOLDEN4: builder chỉ hỏi tồn tại / kích thước, không mở) → so dạng đó."""
    if isinstance(expected, dict) and "stat" in expected:
        return {"stat": _stat_value(path)}
    if path.is_file():
        return _digest(path)
    if path.is_dir():
        return {"directory_sha256": hashlib.sha256(json.dumps(sorted(os.listdir(path))).encode()).hexdigest()}
    return None


def _stat_value(path, stat=None):
    """Kích thước tệp / "dir" / None (không có). stat: os.stat GỐC khi gọi trong worker (os.stat ở đó đã bị bọc bởi locate)."""
    try:
        st = (stat or os.stat)(path)
    except OSError:
        return None
    return "dir" if __import__("stat").S_ISDIR(st.st_mode) else st.st_size


def _plain(path, root):
    path = Path(path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("INSUFFICIENT_INPUT: đường dẫn manifest không an toàn")
    candidate = root / path
    for part in (candidate, *candidate.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("INSUFFICIENT_INPUT: không nhận symlink/junction")
        if part == root:
            break
    if not candidate.resolve().is_relative_to(root):
        raise ValueError("INSUFFICIENT_INPUT: đường dẫn ngoài nguồn")
    return candidate


def _db_snapshot(db, target):
    with closing(sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
    return _digest(target)


def _tool_capture():
    """tools/golden_capture của CÂY CÔNG CỤ (không phải cây code đang so — main có thể chưa có / khác): nạp theo đường dẫn tệp."""
    import importlib.util
    mod = sys.modules.get("_golden_capture_tool")
    if mod is None:
        spec = importlib.util.spec_from_file_location("_golden_capture_tool", TOOL_ROOT / "tools" / "golden_capture.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_golden_capture_tool"] = mod
        spec.loader.exec_module(mod)
    return mod


def _home_of(name, root, code_root):
    """C-GOLDEN6: cây chứa tệp `name` khi kiểm chữ ký — --ab đọc prompts/ + knowledge/ từ cây code đang so (như worker locate), còn lại ref-root."""
    return Path(code_root).resolve() if code_root and name.startswith(("prompts/", "knowledge/")) else root


def loaded_outside(loaded, code_root):
    """C-GOLDEN6: module core.runner / core.sent_package mà worker THẬT SỰ nạp phải nằm trong `code_root`; trả tên module nạp sai / thiếu."""
    if not isinstance(loaded, dict):
        return ["core.runner", "core.sent_package"]
    norm = lambda p: Path(os.path.normcase(os.path.realpath(p)))   # noqa: E731 - Windows: chữ hoa / thường
    root = norm(code_root)
    out = []
    for name in ("core.runner", "core.sent_package"):
        path = loaded.get(name)
        if not path or not norm(path).is_relative_to(root):
            out.append(name)
    return out


def _native_python():
    python = Path(sys.executable)
    if (sys.version_info[:2] != (3, 14) or sys.prefix != sys.base_prefix or not python.is_absolute()
            or python.name.lower() not in {"python.exe", "python", "python3", "python3.14"}):
        raise ValueError("INSUFFICIENT_INPUT: cần native Python3.14")
    return python


def build_from_database(*, db, ref_root, job_id, flags, envelope, manifest=None, public_config=None, experimental=None, code_root=None,
                        catalog_union=None):
    """Không nhận baseline/prompt/args. Manifest None = chụp dependency, có manifest = replay.
    experimental (C-GOLDEN2 b): None = định nghĩa cũ (mọi cờ verified False TẮT); list = `flags` là baseline cờ sản xuất, chỉ các cờ này phải TẮT.
    code_root (C-GOLDEN5 --ab): dựng gói bằng `core/` của cây code này (worktree) thay cho cây chứa công cụ; None = như cũ."""
    from tools.golden_capture import _safe, validate_compat_flags, validate_baseline_flags, feature_catalog
    if not isinstance(flags,dict) or any(not isinstance(k,str) or type(v) is not bool for k,v in flags.items()):
        raise ValueError("INSUFFICIENT_INPUT: cờ phải explicit boolean")
    if code_root is not None:
        # C-GOLDEN7 (--ab): cờ theo catalog CỦA CHÍNH cây đang dựng (+ hợp A∪B cho experimental), không theo cây công cụ — main có cờ
        # mới (gen_auth_shadow) mà cây công cụ chưa có → trước: ValueError mọi ca → 158/158 BOTH_FAIL trước worker
        validate_ab_flags(flags, experimental, code_root, catalog_union)
    else:
        if experimental is None:
            validate_compat_flags(flags)
        else:
            validate_baseline_flags(flags, experimental)
        if feature_catalog().keys() - flags.keys():
            raise ValueError("INSUFFICIENT_INPUT: thiếu cờ legacy explicit")
    public_config = public_config or {}
    if any(k not in PUBLIC and not k.startswith("FEATURE_") for k in public_config):
        raise ValueError("INSUFFICIENT_INPUT: config ngoài danh sách public")
    if set(envelope) != {"provider", "at", "external_id"} or envelope["provider"] not in {"fake", "clipai", "deepix"}:
        raise ValueError("INSUFFICIENT_INPUT: envelope thiếu/hỏng")
    _safe({"flags": flags, "envelope": envelope, "public_config": public_config})
    root = Path(ref_root).resolve()
    original_root=Path(ref_root).absolute()
    if not root.is_dir() or any(p.is_symlink() or p.is_junction() for p in (original_root,*original_root.parents)):
        raise ValueError("INSUFFICIENT_INPUT: nguồn không hợp lệ")
    required = {"version","db_sha256","files","flags","public_config","job_id","envelope","schema","head_sha","provenance"}
    if manifest is not None and (not isinstance(manifest, dict) or required - manifest.keys() or manifest.get("version") != 1 or not isinstance(manifest.get("files"), dict)):
        return {"status": "INSUFFICIENT_INPUT", "reason": "thiếu manifest"}
    with tempfile.TemporaryDirectory(prefix="golden-db-") as scratch:
        box = Path(scratch)
        (box / "data").mkdir()
        digest = _db_snapshot(db, box / "data/manifest.sqlite")
        with closing(sqlite3.connect(box / "data/manifest.sqlite")) as copied:
            schema = {k: copied.execute("PRAGMA "+k).fetchone()[0] for k in ("user_version","schema_version")}
        if manifest is not None:
            if manifest.get("db_sha256") != digest:
                return {"status": "DATA_CHANGED", "reason": "CSDL đã đổi"}
            if (manifest.get("flags") != flags or manifest.get("public_config") != public_config
                    or manifest.get("experimental_flags") != experimental):
                return {"status": "DATA_CHANGED", "reason": "cờ/config public đã đổi"}
            if manifest["job_id"] != int(job_id) or manifest["envelope"] != envelope:
                return {"status": "DATA_CHANGED", "reason": "định danh/envelope capture đã đổi"}
            for name, expected in manifest["files"].items():
                path = _plain(name, _home_of(name, root, code_root))
                actual = _signature(path, expected)
                if actual != expected:
                    return {"status": "DATA_CHANGED", "reason": "file đầu vào đã đổi"}
        request = {"root": str(root), "job_id": int(job_id), "flags": flags, "envelope": envelope,
                   "public_config": public_config, "expected_files": None if manifest is None else manifest["files"]}
        if code_root is not None:
            code = Path(code_root).resolve()
            if not (code / "core" / "runner.py").is_file() or not (code / "core" / "sent_package.py").is_file():
                raise ValueError("INSUFFICIENT_INPUT: cây code không có core/runner.py + core/sent_package.py")
            request["code_root"] = str(code)
        (box / "request.json").write_text(json.dumps(request), encoding="utf-8")
        python = _native_python()
        env = {"SYSTEMROOT": "C:/Windows", "HOME": scratch, "USERPROFILE": scratch, "TEMP": scratch,
               "TMP": scratch, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([str(python), "-I", "-B", str(Path(__file__).resolve()), str(box / "request.json")],
                                cwd=box, env=env, capture_output=True, timeout=120)
        response = box / "response.json"
        if result.returncode or not response.is_file():
            return {"status": "INSUFFICIENT_INPUT", "reason": "worker không dựng được gói"}
        answer = classify_answer(json.loads(response.read_text(encoding="utf-8")))
        if code_root is not None and (answer.get("status") == "BUILT" or "loaded" in answer):   # C-GOLDEN6: bằng chứng nạp ĐÚNG cây
            outside = loaded_outside(answer.get("loaded"), request["code_root"])
            if outside:
                return {"status": "INSUFFICIENT_INPUT", "reason": "worker nạp core ngoài cây code được so: " + ", ".join(outside),
                        "loaded": answer.get("loaded")}
        if answer.get("status") != "BUILT":
            return answer
        for name,expected in answer["files"].items():
            if _signature(_plain(name, _home_of(name, root, request.get("code_root"))), expected) != expected:   # C-GOLDEN6: prompts/knowledge --ab đọc từ cây code
                return {"status":"DATA_CHANGED", "reason":"nguồn đổi trong lúc capture/replay"}
        answer["manifest"] = {"version": 1, "db_sha256": digest, "files": answer.pop("files"),
                              "flags": flags, "public_config": public_config,
                              **({"experimental_flags": experimental} if experimental is not None else {}),
                              "schema": schema,
                              "job_id":int(job_id), "envelope":envelope,
                              "head_sha": __import__("tools.golden_capture", fromlist=["head_sha"]).head_sha(),
                              "provenance": "snapshot_at_capture_not_at_send"}
        return answer


def compare_database_job(job, actual):
    """Baseline chỉ tới comparator; dữ liệu tại capture không suy thành lịch sử gửi."""
    if actual.get("status") != "BUILT":
        return {k: v for k, v in actual.items() if k != "raw"}
    if actual["raw"] == job["sent_package_raw"]:
        return {"status": "COMPAT"}
    # C-GOLDEN2 (d): pregen_fingerprint gắn NGOÀI _build_package (VideoRunner._pregen → _build_package khi đã có task id) — so RIÊNG trường
    # này: phần còn lại giống hệt → COMPAT có ghi chú; giá trị fingerprint lúc gửi giữ trong kết quả để đối chiếu tay.
    sent_rest, sent_fp = _without_fingerprint(job["sent_package_raw"])
    built_rest, built_fp = _without_fingerprint(actual["raw"])
    if sent_rest is not None and sent_rest == built_rest and sent_fp != built_fp:
        return {"status": "COMPAT", FINGERPRINT: "so_rieng", "fingerprint_sent": sent_fp, "fingerprint_built": built_fp}
    if job.get("database_replay", {}).get("matched_at_capture") is True:
        return {"status": "CODE_MISMATCH", "reason": "input capture ổn định nhưng builder đổi"}
    return {"status": "INSUFFICIENT_INPUT", "reason": "không đủ bằng chứng đầu vào lúc gửi"}


def capture_database_job(job, *, db, ref_root, flags, public_config=None, experimental=None):
    package = json.loads(job["sent_package_raw"])
    if any(k not in package for k in ("provider","at","external_id")):
        return {"status":"INSUFFICIENT_INPUT", "matched_at_capture":False, "reason":"thiếu envelope lịch sử"}
    envelope = {k:package[k] for k in ("provider", "at", "external_id")}
    actual = build_from_database(db=db, ref_root=ref_root, job_id=job["id"], flags=flags,
                                 envelope=envelope, public_config=public_config, experimental=experimental)
    result = {"envelope": envelope, "matched_at_capture": actual.get("raw") == job["sent_package_raw"]}
    result.update({k:v for k,v in actual.items() if k not in {"raw"}})
    result["comparison"] = compare_database_job(job, actual)
    return result


def replay_fixture(fixture, *, db, ref_root):
    results = []
    for job in fixture["jobs"]:
        identity={"project_id":fixture["project"],"scene_id":fixture["scene_id"],"type":job["type"],"job_id":job["id"]}
        recorded = job.get("database_replay") or {}
        if not recorded.get("manifest"):
            # C-GOLDEN4: capture đã phân loại DATA_CHANGED (dữ liệu đổi sau ngày gửi) giữ nguyên nhân — không gộp thành INSUFFICIENT_INPUT
            # chỉ DATA_CHANGED đã phân loại có tệp (classify_answer: paths); DATA_CHANGED do race lúc chụp → INSUFFICIENT_INPUT như cũ
            status = "DATA_CHANGED" if recorded.get("status") == "DATA_CHANGED" and recorded.get("paths") else "INSUFFICIENT_INPUT"
            extra = {k: recorded[k] for k in ("diagnostic", "paths", "chain") if k in recorded}
            results.append({**identity, "status":status, "reason":recorded.get("reason", "thiếu manifest"), **extra})
            continue
        actual = build_from_database(db=db, ref_root=ref_root, job_id=job["id"], flags=fixture["flags"],
            envelope=recorded["envelope"], manifest=recorded["manifest"], public_config=recorded["manifest"].get("public_config"),
            experimental=fixture.get("experimental_flags") if fixture.get("flags_mode") == "baseline" else None)
        results.append({**identity, **compare_database_job(job,actual)})
    return summarize(results)


def summarize(results):
    unique={(r['project_id'],r['scene_id'],r['type'],r['job_id']):r for r in results}
    rows=list(unique.values())
    projects={}
    for project in sorted({r['project_id'] for r in rows}):
        selected=[r for r in rows if r['project_id']==project]
        counts={s:sum(r['status']==s for r in selected) for s in ('COMPAT','CODE_MISMATCH','DATA_CHANGED','INSUFFICIENT_INPUT')}
        enough=counts['COMPAT']+counts['CODE_MISMATCH']
        projects[str(project)]={**counts,'selected_cases':len(selected),
            'compat_percent_complete_input':100*counts['COMPAT']/enough if enough else None,
            'data_changed_denominator':len(selected),'data_changed_fraction':counts['DATA_CHANGED']/len(selected),
            'distinct_compat_image_shots':len({r['scene_id'] for r in selected if r['status']=='COMPAT' and r['type']=='image_gen'}),
            'distinct_compat_video_shots':len({r['scene_id'] for r in selected if r['status']=='COMPAT' and r['type']=='video_gen'})}
    return {'jobs':rows,'projects':projects,'acceptance':'OPEN_OWNER_ONLY_24_27'}


def _worker(request):
    import builtins
    import io
    import socket
    import datetime
    from unittest.mock import patch
    scratch, source = Path.cwd(), Path(request["root"])
    scratch_real, source_real = Path(os.path.realpath(scratch)), Path(os.path.realpath(source))
    files, denied, changed = {}, [], []
    original_open, original_io, original_stat = builtins.open, io.open, os.stat
    original_os_open = os.open
    original_listdir, original_scandir = os.listdir, os.scandir
    project = None
    asset_paths = set()
    def forbidden(*args, **kwargs):
        last = denied[-1] if denied else {"kind": "operation", "path": "<outside-root>"}
        raise SandboxDenied(last["kind"], last["path"])
    def relpath(path):
        p = Path(os.path.abspath(os.fspath(path)))
        for home in (scratch, source, ROOT):
            try:
                return p.relative_to(home).as_posix()
            except ValueError:
                pass
        return None
    def block(kind, path=None):
        name = relpath(path) if path is not None else None
        if name and (".." in Path(name).parts or ":" in name or "?" in name or "#" in name):
            name = None
        denied.append({"kind": kind, "path": name or "<outside-root>"})
    def allowed(name):
        if read_denied(name):
            return False
        return name.startswith(("data/", "knowledge/", "prompts/")) or name in asset_paths
    def locate(path, write=False, light=False):
        """light=True (os.stat / exists / getsize): chỉ ghi tồn tại + kích thước, không băm nội dung (C-GOLDEN4: tránh DATA_CHANGED giả và băm lại
        tệp lớn mỗi lần hỏi tồn tại); lần MỞ tệp ghi sha đầy đủ. Lúc replay theo đúng dạng đã ghi lúc capture."""
        if not isinstance(path, (str, bytes, os.PathLike)):
            return path
        name = relpath(path)
        absolute = Path(os.path.abspath(os.fspath(path)))
        if write:
            if not absolute.is_relative_to(scratch):
                block("write", path)
                forbidden()
            return absolute
        if name and allowed(name):
            local = scratch / name
            try:
                original_stat(local)
                return local
            except OSError:
                pass
            # C-GOLDEN5 --ab: prompts/ + knowledge/ là CỦA CÂY CODE đang so (M2 sửa prompt phải thấy); data/ vẫn từ nguồn (ref-root)
            target = _plain(name, ROOT if request.get("code_root") and name.startswith(("prompts/", "knowledge/")) else source)
            expected_files = request["expected_files"]
            if expected_files is not None and name not in expected_files:
                block("manifest", path)
                forbidden()
            if expected_files is not None:
                want_stat = isinstance(expected_files[name], dict) and "stat" in expected_files[name]
            else:
                want_stat = light and name not in files
            if want_stat:
                files[name] = {"stat": _stat_value(target, original_stat)}
                if expected_files is not None and files[name] != expected_files[name]:
                    changed.append(True)
                    raise DataChanged()
                return target
            try:
                st = original_stat(target)
                if __import__('stat').S_ISDIR(st.st_mode):
                    files[name] = {"directory_sha256": hashlib.sha256(json.dumps(sorted(original_listdir(target))).encode()).hexdigest()}
                    if request["expected_files"] is not None and files[name] != request["expected_files"][name]:
                        changed.append(True)
                        raise DataChanged()
                    return target
                with original_open(target, "rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
            except FileNotFoundError:
                digest = None
            files[name] = digest
            if request["expected_files"] is not None and digest != request["expected_files"][name]:
                changed.append(True)
                raise DataChanged()
            return target
        if name and name.startswith("data/") and not absolute.is_relative_to(scratch):
            block("secret" if read_denied(name) else "data", path)
            forbidden()
        return path
    def wrapped_open(path, mode="r", *args, **kwargs):
        return original_open(locate(path, any(c in str(mode) for c in "wax+")), mode, *args, **kwargs)
    def wrapped_io(path, mode="r", *args, **kwargs):
        return original_io(locate(path, any(c in str(mode) for c in "wax+")), mode, *args, **kwargs)
    def wrapped_stat(path, *args, **kwargs):
        return original_stat(locate(path, light=True), *args, **kwargs)
    def wrapped_os_open(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            forbidden()
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        return original_os_open(locate(path, writing), flags, mode)
    def wrapped_listdir(path="."):
        return original_listdir(locate(path))
    def wrapped_scandir(path="."):
        return original_scandir(locate(path))
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.path.abspath(os.fspath(args[0])))
            mode, flags = args[1:3]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            if writing and not path.is_relative_to(scratch):
                block("write", path)
                forbidden()
            if not writing and not path.is_relative_to(scratch):
                name = relpath(path)
                runtime = path.is_relative_to(Path(sys.base_prefix))
                code = (path.is_relative_to(ROOT) or path.is_relative_to(TOOL_ROOT)) and path.suffix in {".py", ".pyc", ".pyd"}
                if not (runtime or code or (name and allowed(name))):
                    block("secret" if name and read_denied(name) else "read", path)
                    forbidden()
                if name and allowed(name) and not runtime and not code:
                    # C-GOLDEN4: đọc thẳng (FileIO / _io.open, không qua locate) — tệp thật phải nằm trong nguồn/scratch, không symlink ra ngoài
                    real = Path(os.path.realpath(path))
                    if not (real.is_relative_to(source_real) or real.is_relative_to(scratch_real) or real.is_relative_to(ROOT)
                            or real.is_relative_to(TOOL_ROOT)):
                        block("read", path)
                        forbidden()
        elif event in {"os.listdir", "os.scandir"}:
            path = Path(os.path.abspath(os.fspath(args[0])))
            name = relpath(path)
            code_directory = (path == ROOT or path.is_relative_to(ROOT / "core") or path.is_relative_to(ROOT / "tools")
                              or path == TOOL_ROOT or path.is_relative_to(TOOL_ROOT / "tools"))
            if not path.is_relative_to(scratch) and not path.is_relative_to(Path(sys.base_prefix)) and not code_directory and not (name and allowed(name)):
                block("directory", path)
                forbidden()
        elif event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile")) or event in {"os.system", "os.fork", "os.forkpty"}:
            block("network")
            forbidden()
        elif event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.link", "os.symlink", "os.utime", "os.chmod", "os.chown", "os.truncate"}:
            for arg in args[:2] if event in {"os.rename", "os.link", "os.symlink"} else args[:1]:
                if isinstance(arg, (str, bytes, os.PathLike)) and not Path(os.path.abspath(arg)).is_relative_to(scratch):
                    block("write", arg)
                    forbidden()
        elif event == "sqlite3.connect":
            if not Path(str(args[0])).resolve().is_relative_to(scratch):
                block("db")
                forbidden()
    with closing(sqlite3.connect(scratch / "data/manifest.sqlite")) as conn:
        conn.row_factory = sqlite3.Row
        job = dict(conn.execute("SELECT * FROM jobs WHERE id=?", (request["job_id"],)).fetchone())
        project = int(job["project_id"])
        try:
            reference_package = json.loads(job.get("sent_package") or "{}")
            asset_paths.update(_job_ref_paths(reference_package, source))
        except (ValueError, TypeError):
            pass  # Baseline không hợp lệ không cấp thêm quyền đọc.
        scene = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (job["scene_id"],)).fetchone()[0] or "{}")
        scene_text = json.dumps(scene, ensure_ascii=False).casefold()
        ids = {r["id"] for r in conn.execute("SELECT id,name FROM assets") if r["name"].casefold() in scene_text}
        for row in conn.execute("SELECT name,ref_asset_id,weapon_asset_id FROM characters WHERE project_id=?", (project,)):
            if row["name"].casefold() in scene_text:
                ids.update(v for v in (row["ref_asset_id"], row["weapon_asset_id"]) if v is not None)
        for row in conn.execute("SELECT asset_id,path FROM asset_images"):
            if row["asset_id"] in ids and row["path"]:
                p = Path(row["path"])
                if p.is_absolute():
                    p = p.relative_to(source)
                # Registry ảnh không được mở rộng allowlist sang config/văn bản tùy ý.
                if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".avif"}:
                    forbidden()
                asset_paths.add(p.as_posix())
        # Không cho builder đọc baseline từ DB làm đầu vào.
        conn.execute("UPDATE jobs SET sent_package=NULL")
        job.pop("sent_package", None)
        conn.commit()
        fake_env = {"PIPELINE_DB": str(scratch / "data/manifest.sqlite"), "FEATURE_SETTINGS_FILE": str(scratch / "data/feature_settings.json"),
                    "FEATURE_BASELINE": "0"}                       # M7.2: replay theo cờ ghi trong yêu cầu, không theo baseline
        for key,value in request["public_config"].items():
            fake_env[{"image_model":"DEEPIX_MODEL", "video_model":"VIDEO_MODEL"}.get(key,key)] = str(value)
        moment = datetime.datetime.fromisoformat(request["envelope"]["at"])
        class Frozen(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return moment
        class Provider:
            name = request["envelope"]["provider"]
            supports_aspect = True
            submit_final_from_sample = staticmethod(forbidden)
            upload_image = staticmethod(forbidden)
        class ImageProvider(Provider):
            supports_model = supports_storyboard = True
            def submit(self, prompt, references=None, size=None, model=None, storyboard=None):
                forbidden()
        class VideoProvider(Provider):
            supports_subjects = request["envelope"]["provider"] == "clipai"
            def submit(self, image_path, prompt, negative_prompt, duration_sec, model=None, with_audio=False, subjects=None,
                       image_references=None, reference_video=None, aspect_ratio=None, resolution=None, multi_prompt=None,
                       last_frame=None, kling_mode=None, kling_image_refs=False, reference_audio=None, reference_only=None,
                       draft=False, high_res_sample=False):
                forbidden()
        sys.addaudithook(audit)
        with patch.object(os, "environ", fake_env), patch.object(socket, "socket", forbidden), patch.object(socket, "create_connection", forbidden), patch.object(subprocess, "Popen", forbidden), patch.object(builtins, "open", wrapped_open), patch.object(io, "open", wrapped_io), patch.object(os, "open", wrapped_os_open), patch.object(os, "stat", wrapped_stat), patch.object(os, "listdir", wrapped_listdir), patch.object(os, "scandir", wrapped_scandir):
            stale = sorted(m for m, mod in list(sys.modules.items()) if (m == "core" or m.startswith("core."))
                           and getattr(mod, "__file__", None)
                           and not Path(os.path.realpath(mod.__file__)).is_relative_to(Path(os.path.realpath(ROOT))))
            if stale:                                # C-GOLDEN6: `core` đã nạp trước TỪ CÂY KHÁC → không dựng, nói rõ
                return {"status": "INSUFFICIENT_INPUT", "reason": "worker: core đã nạp trước khi chọn cây code",
                        "diagnostic": [{"kind": "preloaded", "path": stale[0]}]}
            from core import runner, features, sent_package, seedance_refs, image_models
            from core.pipeline import Pipeline
            # chỉ đường --ab mới trả (capture / replay thường không mang đường dẫn tuyệt đối của máy chụp vào fixture)
            loaded = ({"core.runner": os.path.realpath(runner.__file__), "core.sent_package": os.path.realpath(sent_package.__file__)}
                      if request.get("code_root") else None)
            extra = {"loaded": loaded} if loaded else {}
            cls = runner.ImageRunner if job["type"] == "image_gen" else runner.VideoRunner
            instance = cls(Pipeline(conn), ImageProvider() if job["type"] == "image_gen" else VideoProvider(), "data/projects")
            if job["type"] == "video_gen":         # C-GOLDEN2 (c): model như lúc gửi = jobs.model của job
                plain_choice = instance._choice
                instance._choice = lambda j, _c=plain_choice: pinned_choice(_c(j), job)
            registry_used = []
            class CachedLibrary:
                def get(self,asset_id):
                    try:
                        rows=conn.execute("SELECT sha,asset_id,asset_uri,status FROM seedance_subject_pictures WHERE asset_id=?",(asset_id,)).fetchall()
                    except sqlite3.Error:
                        forbidden()
                    if len(rows) != 1:
                        forbidden()
                    row = rows[0]
                    if row['status']!='active' or not str(row['asset_uri'] or '').startswith('asset://'):
                        forbidden()
                    public={k:row[k] for k in ('sha','asset_id','asset_uri','status')}
                    registry_used.append(public)
                    return {'asset_id':row['asset_id'],'asset_uri':row['asset_uri'],'provider_status':'active'}
                def list_assets(self):
                    # Không tìm/nghĩ ra mapping thiếu asset_id từ tên hay qua mạng.
                    forbidden()
                upload = staticmethod(forbidden)
            instance.subject_library=CachedLibrary()
            flags = request["flags"]
            original_rel_path = sent_package.rel_path
            original_mark=seedance_refs.mark
            def canonical_mark(path,out_dir,style="eye_plus"):
                name=relpath(path)
                canonical=str(source/name) if name and allowed(name) else path
                return original_mark(canonical,out_dir,style)
            def relative_input(path):
                p=Path(str(path))
                if p.is_absolute():
                    for home in (source,scratch):
                        if p.is_relative_to(home):
                            return p.relative_to(home).as_posix()
                return original_rel_path(path)
            plain_of_project = image_models.of_project
            def job_image_model(proj):             # C-GOLDEN2 (c): model ảnh = jobs.model của job ảnh
                return job["model"] if job["type"] == "image_gen" and job.get("model") else plain_of_project(proj)
            with patch.object(features, "on", side_effect=lambda n: flags.get(n, False)), patch.object(features, "active", side_effect=lambda n: flags.get(n, False)), patch.object(features, "shadow", return_value=False), patch.object(sent_package, "ROOT", str(scratch)), patch.object(sent_package,"rel_path",side_effect=relative_input), patch.object(seedance_refs,"mark",side_effect=canonical_mark), patch.object(sent_package.datetime, "datetime", Frozen), patch.object(image_models, "of_project", side_effect=job_image_model):
                args = instance._submit_args(job)
                if args is None:
                    return {"status": "INSUFFICIENT_INPUT", "reason": "shot thiếu input prepare"}
                kwargs = instance._prepare_kwargs(job)
                # C-GOLDEN6: tách lý do để BOTH_FAIL gom được theo nhóm (trước chung "prepare chờ hoặc cần draft lịch sử")
                for key, why in (("_from_sample", "cần draft lịch sử (bản cao nâng từ nháp)"), ("_wait", "prepare chờ (_wait)"),
                                 ("_hold", "prepare giữ (_hold)")):
                    if kwargs.get(key):
                        return {"status": "INSUFFICIENT_INPUT", "reason": why, **extra}
                kwargs = instance._finish_kwargs(job, kwargs)
                raw, warnings = instance._build_package(job, args, kwargs, {k:v for k,v in kwargs.items() if not k.startswith('_')}, request["envelope"]["external_id"])
                if changed:
                    return {"status":"DATA_CHANGED", "reason":"nguồn đổi trong lúc worker đọc"}
                if not raw or warnings or denied:
                    return {"status": "INSUFFICIENT_INPUT", "reason": "dependency thiếu hoặc sandbox chặn", "diagnostic": denied or [{"kind": "dependency", "path": "<unavailable>"}]}
                _tool_capture()._safe(json.loads(raw))
                return {"status": "BUILT", "raw": raw, "files": files, "registry":registry_used, **extra}


# ---- C-GOLDEN5 (sổ v31-ep-golden-ab-acceptance-2026-10-21): so A/B HAI cây code trên CÙNG snapshot + CÙNG cờ ------------------------
AB_STATUSES = ("SAME", "DIFF", "ONE_FAIL", "BOTH_FAIL")


def first_diff(a, b, path=""):
    """Chỗ lệch ĐẦU TIÊN giữa hai gói (đã parse JSON) — đường trường + kiểu lệch; chuỗi chỉ nói vị trí ký tự + độ dài, KHÔNG in nội dung."""
    if type(a) is not type(b):
        return {"path": path or "$", "kind": "type", "a": type(a).__name__, "b": type(b).__name__}
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return {"path": f"{path}.{k}" if path else k, "kind": "missing_in_" + ("a" if k not in a else "b")}
            d = first_diff(a[k], b[k], f"{path}.{k}" if path else k)
            if d:
                return d
        return None
    if isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None if len(a) == len(b) else {"path": path or "$", "kind": "length", "a": len(a), "b": len(b)}
    if a == b:
        return None
    if isinstance(a, str):
        at = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        return {"path": path or "$", "kind": "text", "at_char": at, "len_a": len(a), "len_b": len(b)}
    return {"path": path or "$", "kind": "value", "a": a if isinstance(a, (int, float, bool)) or a is None else "…",
            "b": b if isinstance(b, (int, float, bool)) or b is None else "…"}


def compare_ab(res_a, res_b):
    """SAME / DIFF (trường lệch đầu tiên) / ONE_FAIL (một bên không dựng được — tính như DIFF) / BOTH_FAIL (ghi riêng)."""
    built_a, built_b = res_a.get("status") == "BUILT", res_b.get("status") == "BUILT"
    if not built_a and not built_b:
        return {"status": "BOTH_FAIL", "a": _fail_view(res_a), "b": _fail_view(res_b)}
    if built_a != built_b:
        return {"status": "ONE_FAIL", "failed": "a" if not built_a else "b", "reason": _fail_view(res_a if not built_a else res_b)}
    if res_a["raw"] == res_b["raw"]:
        return {"status": "SAME"}
    try:
        diff = first_diff(json.loads(res_a["raw"]), json.loads(res_b["raw"]))
    except ValueError:
        diff = {"path": "$", "kind": "raw"}
    return {"status": "DIFF", "first_diff": diff or {"path": "$", "kind": "raw_bytes"}}


def _fail_view(res):
    return {k: res[k] for k in ("status", "reason", "diagnostic") if k in res}


def _history(job_raw, res):
    """Cột THAM KHẢO: gói dựng lại so với gói đã gửi lúc đó (không quyết ĐẠT)."""
    if not job_raw:
        return "NO_SENT"
    if res.get("status") != "BUILT":
        return "NOT_BUILT"
    if res["raw"] == job_raw:
        return "SAME_AS_SENT"
    sent_rest, _ = _without_fingerprint(job_raw)
    built_rest, _ = _without_fingerprint(res["raw"])
    return "SAME_EXCEPT_FINGERPRINT" if sent_rest is not None and sent_rest == built_rest else "DIFF_FROM_SENT"


class ABError(ValueError):
    """Đầu vào / môi trường của lượt so A/B sai (cây code, cờ, Python) — dừng cả lượt, mã thoát 2."""


_CATALOGS = {}


def _catalog(code_root):
    """Tên cờ trong FEATURES (literal, đọc AST) của cây `code_root` — cache theo (đường dẫn, mtime, size) (C-GOLDEN7: trước parse lại mỗi ca)."""
    import ast
    fp = Path(code_root) / "core" / "features.py"
    if not fp.is_file():
        raise ABError(f"{code_root}: không phải cây code (thiếu core/features.py)")
    st = fp.stat()
    key = (str(fp.resolve()), st.st_mtime_ns, st.st_size)
    if key in _CATALOGS:
        return set(_CATALOGS[key])
    tree = ast.parse(fp.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "FEATURES":
            _CATALOGS[key] = frozenset(ast.literal_eval(node.value))
            return set(_CATALOGS[key])
    raise ABError(f"không đọc được FEATURES của {code_root}")


def validate_ab_flags(flags, experimental, code_root, union=None):
    """C-GOLDEN7: cờ của MỘT bên --ab, fail-closed theo catalog của cây `code_root`: mọi cờ của catalog cây đó có trong `flags` (bool);
    experimental = list tên DUY NHẤT, mỗi tên có trong catalog cây đó HOẶC trong hợp A∪B (`union` — cờ chỉ có ở một cây = TẮT ở cây kia
    là đúng nghĩa), và đều TẮT. Lỗi = lỗi cấu hình cả lượt (ABError → mã 2), không phải lỗi từng ca."""
    catalog = _catalog(code_root)
    allowed = catalog | set(union or ())
    if not isinstance(flags, dict) or any(not isinstance(k, str) or type(v) is not bool for k, v in flags.items()):
        raise ABError("file cờ: baseline_flags phải là object tên cờ → boolean")
    missing = sorted(catalog - set(flags))
    if missing:
        raise ABError(f"file cờ thiếu {len(missing)} cờ của {Path(code_root).name}: " + ", ".join(missing[:12]))
    if not isinstance(experimental, list) or len(set(experimental)) != len(experimental) or \
            any(not isinstance(k, str) or k not in allowed for k in experimental):
        bad = [k for k in experimental if k not in allowed] if isinstance(experimental, list) else []
        raise ABError("experimental_flags cần list tên cờ DUY NHẤT có trong catalog cây A ∪ B"
                      + (f" — lạ: {', '.join(map(str, bad[:8]))}" if bad else ""))
    on = [k for k in experimental if flags.get(k)]
    if on:
        raise ABError("experimental_flags phải TẮT: " + ", ".join(on[:8]))


def _preflight(flags, code_roots, experimental=None, public_config=None, ref_root=None):
    """Mỗi cây code: có core/runner.py + sent_package.py + features.py; file cờ hợp lệ theo catalog CỦA cây đó (validate_ab_flags, fail-
    closed — thiếu thì cờ lặng lẽ = False ở worker). Rà C-GOLDEN7: MỌI lỗi cấu hình cả lượt kiểm ở đây (ABError → mã 2), không để từng ca
    gộp thành BOTH_FAIL: experimental phải là list (--ab không có chế độ compat ngầm), public_config chỉ khóa public, ref-root hợp lệ,
    cờ / config không chứa trường nhạy cảm. Trả hợp catalog A∪B (cho validator từng ca)."""
    if not isinstance(experimental, list):
        raise ABError("--ab cần experimental_flags là list (có thể rỗng) — không có chế độ compat ngầm")
    public_config = public_config or {}
    if not isinstance(public_config, dict) or any(k not in PUBLIC and not str(k).startswith("FEATURE_") for k in public_config):
        raise ABError("public_config chỉ được có khóa public: " + ", ".join(sorted(PUBLIC)) + " hoặc FEATURE_*")
    if ref_root is not None:
        original = Path(ref_root).absolute()
        if not Path(ref_root).resolve().is_dir() or any(p.is_symlink() or p.is_junction() for p in (original, *original.parents)):
            raise ABError("ref-root không hợp lệ (không phải thư mục / nằm dưới symlink-junction)")
    try:
        _tool_capture()._safe({"flags": flags, "public_config": public_config})
    except ValueError:
        raise ABError("file cờ / public_config chứa trường nhạy cảm — cần bản đã lược bỏ") from None
    for code in code_roots:
        code = Path(code)
        if not all((code / "core" / f).is_file() for f in ("runner.py", "sent_package.py", "features.py")):
            raise ABError(f"{code}: không phải cây code (thiếu core/runner.py / sent_package.py / features.py)")
    union = set().union(*(_catalog(c) for c in code_roots))
    for code in code_roots:
        validate_ab_flags(flags, experimental, code, union)
    return union


def ab_jobs(db, projects):
    """Mỗi shot có job ảnh / video của các dự án: job MỚI NHẤT mỗi loại; envelope từ gói đã gửi, không có → envelope giả cố định
    (cùng cho A và B — so code, không so lịch sử)."""
    out = []
    with closing(sqlite3.connect("file:" + str(Path(db).resolve()).replace("\\", "/") + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        for pid in projects:
            for r in conn.execute("SELECT j.id, j.project_id, j.scene_id, j.type, j.state, j.sent_package, j.created_at FROM jobs j WHERE j.project_id=? "
                                  "AND j.type IN ('image_gen','video_gen') AND j.id = (SELECT MAX(k.id) FROM jobs k WHERE k.scene_id=j.scene_id "
                                  "AND k.type=j.type) ORDER BY j.scene_id, j.type", (int(pid),)):
                env = None
                try:
                    pkg = json.loads(r["sent_package"] or "null")
                    if isinstance(pkg, dict) and all(k in pkg for k in ("provider", "at", "external_id")):
                        env = {k: pkg[k] for k in ("provider", "at", "external_id")}
                except ValueError:
                    pass
                if env is None or env["provider"] not in {"fake", "clipai", "deepix"}:
                    env = {"provider": "fake", "at": "2026-01-01T00:00:00", "external_id": "golden-ab"}
                out.append({"job_id": r["id"], "project_id": r["project_id"], "scene_id": r["scene_id"], "type": r["type"], "state": r["state"],
                            "envelope": env, "sent_package_raw": r["sent_package"]})
    return out


def run_ab(*, db, ref_root, flags, experimental, code_a, code_b, projects, public_config=None, builder=None):
    """Dựng gói từng ca bằng cây A và cây B (worker cách ly mỗi bên) → bảng SAME / DIFF / ONE_FAIL / BOTH_FAIL. ĐẠT = 0 DIFF + 0 ONE_FAIL
    (BOTH_FAIL ghi riêng, không tính lệch). `builder` để test (mặc định build_from_database)."""
    if builder is None:
        builder = build_from_database
        _native_python()                    # môi trường sai → dừng cả lượt (ABError), không thành BOTH_FAIL giả
    union = _preflight(flags, (code_a, code_b), experimental, public_config, ref_root)
    rows = []
    for job in ab_jobs(db, projects):
        res = {}
        for side, code in (("a", code_a), ("b", code_b)):
            try:
                res[side] = builder(db=db, ref_root=ref_root, job_id=job["job_id"], flags=flags, envelope=job["envelope"],
                                    public_config=public_config, experimental=experimental, code_root=code, catalog_union=union)
            except ABError:
                raise                               # C-GOLDEN7: lỗi cấu hình của cả lượt → main_ab mã 2, không gộp thành BOTH_FAIL từng ca
            except (ValueError, subprocess.TimeoutExpired) as e:
                res[side] = {"status": "INSUFFICIENT_INPUT", "reason": str(e)[:200]}
        rows.append({k: job[k] for k in ("job_id", "project_id", "scene_id", "type", "state")} | compare_ab(res["a"], res["b"])
                    | {"history_a": _history(job["sent_package_raw"], res["a"]), "history_b": _history(job["sent_package_raw"], res["b"])}
                    | {"loaded_a": res["a"].get("loaded"), "loaded_b": res["b"].get("loaded")})   # C-GOLDEN6: module thật đã nạp mỗi bên
    projects_out = {}
    for pid in sorted({r["project_id"] for r in rows}):
        sel = [r for r in rows if r["project_id"] == pid]
        projects_out[str(pid)] = {s: sum(r["status"] == s for r in sel) for s in AB_STATUSES} | {"cases": len(sel)}
    total = {s: sum(r["status"] == s for r in rows) for s in AB_STATUSES}
    # ĐẠT = 0 DIFF + 0 ONE_FAIL VÀ mỗi dự án có ≥ 1 ca SAME (toàn BOTH_FAIL = không so được gì → không phải đạt)
    no_same = sorted(p for p, c in projects_out.items() if c["SAME"] == 0)
    return {"rows": rows, "projects": projects_out, "total": total, "no_same_projects": no_same,
            "pass": bool(rows) and total["DIFF"] == 0 and total["ONE_FAIL"] == 0 and not no_same,
            "code_a": str(code_a), "code_b": str(code_b)}


def ab_table(result):
    lines = ["| Dự án | Ca | SAME | DIFF | ONE_FAIL | BOTH_FAIL |", "|---|---|---|---|---|---|"]
    for pid, c in result["projects"].items():
        lines.append(f"| #{pid} | {c['cases']} | {c['SAME']} | {c['DIFF']} | {c['ONE_FAIL']} | {c['BOTH_FAIL']} |")
    lines.append(f"\nKẾT LUẬN: {'ĐẠT' if result['pass'] else 'CHƯA ĐẠT'} (ĐẠT = 0 DIFF + 0 ONE_FAIL + mỗi dự án ≥ 1 SAME)"
                 + (f" — dự án không có ca SAME nào: {', '.join('#' + p for p in result['no_same_projects'])}" if result.get("no_same_projects") else "")
                 + "\nGhi chú: job chưa từng gửi dùng envelope giả (provider fake) cho CẢ hai bên — nhánh Kho chủ thể ClipAI không được so ở các ca đó.")
    for r in result["rows"]:
        if r["status"] in ("DIFF", "ONE_FAIL"):
            lines.append(f"- #{r['project_id']} shot {r['scene_id']} {r['type']} job {r['job_id']}: {r['status']} "
                         + json.dumps(r.get("first_diff") or r.get("reason"), ensure_ascii=False))
    return "\n".join(lines)


def main_ab(argv):
    import argparse
    ap = argparse.ArgumentParser(description="C-GOLDEN5: so A/B gói gửi của hai cây code trên cùng snapshot + cùng cờ")
    ap.add_argument("--ab", action="store_true", required=True)
    for name in ("db", "ref-root", "flags", "code-a", "code-b", "output"):
        ap.add_argument("--" + name, required=True, type=Path)
    ap.add_argument("--project", type=int, action="append", required=True)
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):    # console cp1252: bảng chữ Việt
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    if a.output.exists():
        ap.exit(2, f"{a.output} đã có — chọn tên tệp kết quả mới (không ghi đè)\n")
    try:
        spec = json.loads(a.flags.read_text(encoding="utf-8-sig"))
        if not isinstance(spec.get("baseline_flags"), dict):
            raise ABError("file cờ thiếu baseline_flags")
        experimental = list(spec.get("experimental_flags") or [])
        on = [n for n in experimental if spec["baseline_flags"].get(n) is True]
        if on:                               # rà C-GOLDEN7: trước ép False LẶNG LẼ — cờ đang BẬT ở sản xuất bị tắt mà không ai biết
            raise ABError("experimental_flags đang BẬT trong baseline_flags (phải TẮT, sửa file cờ): " + ", ".join(on[:8]))
        flags = dict(spec["baseline_flags"]) | {n: False for n in experimental if n not in spec["baseline_flags"]}
        result = run_ab(db=a.db, ref_root=a.ref_root, flags=flags, experimental=experimental, code_a=a.code_a, code_b=a.code_b,
                        projects=a.project, public_config=spec.get("public_config") or {})
    except (ABError, OSError, ValueError, sqlite3.Error) as e:    # sqlite3.Error: --db sai / hỏng → mã 2, không traceback
        ap.exit(2, f"Không chạy được so A/B (đầu vào / môi trường): {str(e)[:300]}\n")
    with a.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(ab_table(result))
    return 0 if result["pass"] else 1


def main(argv=None):
    import argparse
    for stream in (sys.stdout, sys.stderr):    # C-GOLDEN2 (f): console cp1252 không in được chữ Việt của --help
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',required=True,type=Path,action='append')
    for name in ("db", "ref-root", "output"):
        parser.add_argument("--"+name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        rows=[]
        for path in args.fixture:
            fixture = json.loads(path.read_text(encoding="utf-8-sig"))
            rows.extend(replay_fixture(fixture,db=args.db,ref_root=args.ref_root)['jobs'])
        result=summarize(rows)
        with args.output.open("x",encoding="utf-8") as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
    except Exception:
        parser.exit(2,"Replay không hoàn tất: kiểm manifest, schema và đầu ra mới; không xuất payload/log.\n")
    return 0


if __name__ == "__main__" and len(sys.argv) == 2 and not sys.argv[1].startswith('--'):
    if Path(sys.argv[1]).parent != Path.cwd() or not Path.cwd().name.startswith('golden-db-'):
        raise SystemExit(2)
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        if request.get("code_root"):              # C-GOLDEN5 --ab: `core` của cây code đang so (main / M2), công cụ vẫn của cây này
            ROOT = Path(request["code_root"]).resolve()
            sys.pycache_prefix = str(Path.cwd() / "_pyc")   # C-GOLDEN6 (chỉ --ab): KHÔNG đọc .pyc trong cây code (cũ / của cây khác) — luôn dịch từ nguồn
        sys.path.insert(0, str(ROOT))
        answer = _worker(request)
    except DataChanged:
        answer = {"status":"DATA_CHANGED", "reason":"input thay đổi trong lúc worker đọc"}
    except Exception as exc:
        trace = exc.__traceback__
        positions = []
        while trace is not None:
            positions.append(f"{Path(trace.tb_frame.f_code.co_filename).name}:{trace.tb_lineno}")
            trace = trace.tb_next
        answer = {"status": "INSUFFICIENT_INPUT", "reason": "worker thiếu dependency hoặc schema", "diagnostic": getattr(exc, "diagnostic", {"kind": type(exc).__name__, "positions": positions[-8:]})}
    Path("response.json").write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
elif __name__ == "__main__":
    sys.path.insert(0,str(ROOT))
    raise SystemExit(main_ab(sys.argv[1:]) if "--ab" in sys.argv[1:] else main())
