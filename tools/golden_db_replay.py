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
PUBLIC = {"LLM_PROVIDER", "image_model", "video_model"}


class SandboxDenied(ValueError):
    def __init__(self, kind, path=None):
        super().__init__("INSUFFICIENT_INPUT: sandbox chặn")
        self.diagnostic = {"kind": kind, "path": path or "<outside-root>"}


def _job_ref_paths(package, root):
    """Chỉ cấp quyền FILE ảnh được gói job tham chiếu, không cấp cây thư mục."""
    from tools.golden_capture import _safe
    _safe(package)
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


def _digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _signature(path):
    if path.is_file():
        return _digest(path)
    if path.is_dir():
        return {"directory_sha256": hashlib.sha256(json.dumps(sorted(os.listdir(path))).encode()).hexdigest()}
    return None


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


def build_from_database(*, db, ref_root, job_id, flags, envelope, manifest=None, public_config=None):
    """Không nhận baseline/prompt/args. Manifest None = chụp dependency, có manifest = replay."""
    from tools.golden_capture import _safe, validate_compat_flags, feature_catalog
    if not isinstance(flags,dict) or any(not isinstance(k,str) or type(v) is not bool for k,v in flags.items()):
        raise ValueError("INSUFFICIENT_INPUT: cờ phải explicit boolean")
    validate_compat_flags(flags)
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
            if manifest.get("flags") != flags or manifest.get("public_config") != public_config:
                return {"status": "DATA_CHANGED", "reason": "cờ/config public đã đổi"}
            if manifest["job_id"] != int(job_id) or manifest["envelope"] != envelope:
                return {"status": "DATA_CHANGED", "reason": "định danh/envelope capture đã đổi"}
            for name, expected in manifest["files"].items():
                path = _plain(name, root)
                actual = _signature(path)
                if actual != expected:
                    return {"status": "DATA_CHANGED", "reason": "file đầu vào đã đổi"}
        request = {"root": str(root), "job_id": int(job_id), "flags": flags, "envelope": envelope,
                   "public_config": public_config, "expected_files": None if manifest is None else manifest["files"]}
        (box / "request.json").write_text(json.dumps(request), encoding="utf-8")
        python = Path(sys.executable)
        if (sys.version_info[:2] != (3, 14) or sys.prefix != sys.base_prefix or not python.is_absolute()
                or python.name.lower() not in {"python.exe", "python", "python3", "python3.14"}):
            raise ValueError("INSUFFICIENT_INPUT: cần native Python3.14")
        env = {"SYSTEMROOT": "C:/Windows", "HOME": scratch, "USERPROFILE": scratch, "TEMP": scratch,
               "TMP": scratch, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([str(python), "-I", "-B", str(Path(__file__).resolve()), str(box / "request.json")],
                                cwd=box, env=env, capture_output=True, timeout=120)
        response = box / "response.json"
        if result.returncode or not response.is_file():
            return {"status": "INSUFFICIENT_INPUT", "reason": "worker không dựng được gói"}
        answer = json.loads(response.read_text(encoding="utf-8"))
        if answer.get("status") != "BUILT":
            return answer
        for name,expected in answer["files"].items():
            if _signature(_plain(name,root)) != expected:
                return {"status":"DATA_CHANGED", "reason":"nguồn đổi trong lúc capture/replay"}
        answer["manifest"] = {"version": 1, "db_sha256": digest, "files": answer.pop("files"),
                              "flags": flags, "public_config": public_config,
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
    if job.get("database_replay", {}).get("matched_at_capture") is True:
        return {"status": "CODE_MISMATCH", "reason": "input capture ổn định nhưng builder đổi"}
    return {"status": "INSUFFICIENT_INPUT", "reason": "không đủ bằng chứng đầu vào lúc gửi"}


def capture_database_job(job, *, db, ref_root, flags, public_config=None):
    package = json.loads(job["sent_package_raw"])
    if any(k not in package for k in ("provider","at","external_id")):
        return {"status":"INSUFFICIENT_INPUT", "matched_at_capture":False, "reason":"thiếu envelope lịch sử"}
    envelope = {k:package[k] for k in ("provider", "at", "external_id")}
    actual = build_from_database(db=db, ref_root=ref_root, job_id=job["id"], flags=flags,
                                 envelope=envelope, public_config=public_config)
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
            results.append({**identity, "status":"INSUFFICIENT_INPUT", "reason":recorded.get("reason", "thiếu manifest"), **({"diagnostic": recorded["diagnostic"]} if "diagnostic" in recorded else {})})
            continue
        actual = build_from_database(db=db, ref_root=ref_root, job_id=job["id"], flags=fixture["flags"],
            envelope=recorded["envelope"], manifest=recorded["manifest"], public_config=recorded["manifest"].get("public_config"))
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
        return (name.startswith((f"data/projects/{project}/", "data/knowledge/", "knowledge/", "prompts/"))
                or name == f"data/projects/{project}"
                or name in {"data/pricing.json", "data/feature_settings.json", "data/provider_rules.json"} or name in asset_paths)
    def locate(path, write=False):
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
            target = _plain(name, source)
            if request["expected_files"] is not None and name not in request["expected_files"]:
                block("manifest", path)
                forbidden()
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
            block("data", path)
            forbidden()
        return path
    def wrapped_open(path, mode="r", *args, **kwargs):
        return original_open(locate(path, any(c in str(mode) for c in "wax+")), mode, *args, **kwargs)
    def wrapped_io(path, mode="r", *args, **kwargs):
        return original_io(locate(path, any(c in str(mode) for c in "wax+")), mode, *args, **kwargs)
    def wrapped_stat(path, *args, **kwargs):
        return original_stat(locate(path), *args, **kwargs)
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
                code = path.is_relative_to(ROOT) and path.suffix in {".py", ".pyc", ".pyd"}
                if not (runtime or code or (name and allowed(name))):
                    block("read", path)
                    forbidden()
        elif event in {"os.listdir", "os.scandir"}:
            path = Path(os.path.abspath(os.fspath(args[0])))
            name = relpath(path)
            code_directory = path == ROOT or path.is_relative_to(ROOT / "core") or path.is_relative_to(ROOT / "tools")
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
            from core import runner, features, sent_package, seedance_refs
            from core.pipeline import Pipeline
            cls = runner.ImageRunner if job["type"] == "image_gen" else runner.VideoRunner
            instance = cls(Pipeline(conn), ImageProvider() if job["type"] == "image_gen" else VideoProvider(), "data/projects")
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
            with patch.object(features, "on", side_effect=lambda n: flags.get(n, False)), patch.object(features, "active", side_effect=lambda n: flags.get(n, False)), patch.object(features, "shadow", return_value=False), patch.object(sent_package, "ROOT", str(scratch)), patch.object(sent_package,"rel_path",side_effect=relative_input), patch.object(seedance_refs,"mark",side_effect=canonical_mark), patch.object(sent_package.datetime, "datetime", Frozen):
                args = instance._submit_args(job)
                if args is None:
                    return {"status": "INSUFFICIENT_INPUT", "reason": "shot thiếu input prepare"}
                kwargs = instance._prepare_kwargs(job)
                if kwargs.get("_wait") or kwargs.get("_hold") or kwargs.get("_from_sample"):
                    return {"status": "INSUFFICIENT_INPUT", "reason": "prepare chờ hoặc cần draft lịch sử"}
                kwargs = instance._finish_kwargs(job, kwargs)
                raw, warnings = instance._build_package(job, args, kwargs, {k:v for k,v in kwargs.items() if not k.startswith('_')}, request["envelope"]["external_id"])
                if changed:
                    return {"status":"DATA_CHANGED", "reason":"nguồn đổi trong lúc worker đọc"}
                if not raw or warnings or denied:
                    return {"status": "INSUFFICIENT_INPUT", "reason": "dependency thiếu hoặc sandbox chặn", "diagnostic": denied or [{"kind": "dependency", "path": "<unavailable>"}]}
                from tools.golden_capture import _safe
                _safe(json.loads(raw))
                return {"status": "BUILT", "raw": raw, "files": files, "registry":registry_used}


def main(argv=None):
    import argparse
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
    sys.path.insert(0, str(ROOT))
    if Path(sys.argv[1]).parent != Path.cwd() or not Path.cwd().name.startswith('golden-db-'):
        raise SystemExit(2)
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
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
    raise SystemExit(main())
