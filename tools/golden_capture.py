"""Đ20 M1.9a: chụp sổ gói gửi ngoại tuyến; chưa phải replay đường gửi."""
from __future__ import annotations

import argparse
import ast
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
import shutil
import sys
from urllib.parse import urlsplit


class GoldenError(ValueError):
    """Đầu vào thiếu hoặc chưa đủ an toàn để lưu fixture."""


def head_sha():
    # Không kế thừa môi trường máy chính, không nạp provider/config ứng dụng.
    git = Path("C:/Program Files/Git/cmd/git.exe")
    if not git.is_file():
        found = shutil.which("git")
        if not found:
            raise GoldenError("Không tìm thấy Git; chưa chụp được HEAD SHA")
        git = Path(found)
    result = subprocess.run([str(git), "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                            env={"SYSTEMROOT": "C:/Windows"}, capture_output=True, check=True, text=True)
    value = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise GoldenError("HEAD SHA không hợp lệ")
    return value


def compare_compat(expected: bytes, actual: bytes):
    """So byte do caller cung cấp; không chứng nhận replay/correctness."""
    if not isinstance(expected, bytes) or not isinstance(actual, bytes):
        raise GoldenError("COMPAT cần hai chuỗi bytes")
    if expected != actual:
        raise GoldenError("COMPAT lệch byte; chưa đạt tương thích")


def feature_catalog():
    """Đọc catalog literal, không import config/credential hay đọc môi trường."""
    tree = ast.parse((Path(__file__).resolve().parents[1] / "core/features.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "FEATURES":
            return ast.literal_eval(node.value)
    raise GoldenError("Không đọc được catalog FEATURES")


def validate_compat_flags(flags):
    needed = {name for name, meta in feature_catalog().items() if meta.get("verified") is False}
    if needed - flags.keys() or any(flags[name] is not False for name in needed & flags.keys()):
        raise GoldenError("COMPAT cần đủ mọi cờ verified False trong catalog và đều TẮT")


def validate_baseline_flags(flags, experimental):
    """C-GOLDEN2 (b) — COMPAT theo cờ SẢN XUẤT: `flags` = baseline_flags (trạng thái mọi cờ của máy lúc chụp, như lúc gửi), `experimental` = cờ MỚI
    của V3.1 do người chụp liệt kê tường minh, phải TẮT. Fail-closed: thiếu bất kỳ cờ nào của catalog, giá trị không phải bool, tên experimental
    lạ / lặp / không có trong catalog, hoặc experimental đang BẬT → GoldenError."""
    catalog = feature_catalog()
    if not isinstance(flags, dict) or any(not isinstance(k, str) or type(v) is not bool for k, v in flags.items()):
        raise GoldenError("baseline_flags phải là object tên cờ → boolean")
    if catalog.keys() - flags.keys():
        raise GoldenError("COMPAT baseline thiếu cờ của catalog (fail-closed): " + ", ".join(sorted(catalog.keys() - flags.keys())[:10]))
    if (not isinstance(experimental, list) or not all(isinstance(k, str) and k in catalog for k in experimental)
            or len(set(experimental)) != len(experimental)):
        raise GoldenError("experimental_flags cần list tên cờ duy nhất có trong catalog")
    if any(flags[k] for k in experimental):
        raise GoldenError("COMPAT yêu cầu các cờ thử nghiệm (experimental_flags) đều TẮT")


def _safe(value):
    # Từ chối cả bản chụp; không xuất giá trị hay tên trường đáng ngờ trong lỗi.
    if isinstance(value, dict):
        for key, item in value.items():
            low = str(key).lower().replace("-", "_")
            if (low in ("key", "auth", "headers") or low.startswith("auth_")
                    or low.endswith(("access_key", "private_key")) or any(w in low for w in
                    ("token", "secret", "password", "passwd", "credential", "authorization", "cookie", "api_key", "apikey"))):
                raise GoldenError("Gói chứa trường nhạy cảm; cần bản xuất đã lược bỏ trước khi chụp")
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise GoldenError("Gói chứa số không hữu hạn; cần JSON hợp lệ trước khi chụp")
    elif isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        url = urlsplit(value)
        if "?" in value or "#" in value or url.username is not None or url.password is not None:
            raise GoldenError("URL có credential/query/fragment; cần bản xuất đã lược bỏ trước khi chụp")


def _ref(ref, root):
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise GoldenError("refs thiếu path")
    result = dict(ref)
    result["captured_sha256"] = None
    path = ref["path"]
    if path.startswith(("http://", "https://")):
        status = "remote_not_fetched"
    elif "://" in path or path.startswith(("\\\\", "//")):
        status = "outside_scope"
    else:
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            status = "outside_scope"
        elif not candidate.is_file():
            status = "missing"
        else:
            try:
                with candidate.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError:
                status = "unreadable"
            else:
                result["captured_sha256"] = digest
                status = "missing_stored_hash" if not ref.get("sha256") else ("match" if digest == ref["sha256"] else "mismatch")
    result["hash_status"] = status
    return result


def capture(*, db, project, shot, flags_file, ref_root, purpose, input_snapshots_file=None, database_replay=False, latest_per_type=False, public_config_file=None):
    db, root = Path(db).resolve(), Path(ref_root).resolve()
    if not db.is_file() or not root.is_dir():
        raise GoldenError("Cần --db tồn tại và --ref-root là thư mục rõ ràng")
    if purpose not in ("compat", "correctness"):
        raise GoldenError("purpose cần compat hoặc correctness")
    if database_replay and purpose != "compat":
        raise GoldenError("Database replay hiện chỉ hỗ trợ COMPAT với cờ thử nghiệm TẮT")
    public_config = {}
    if public_config_file is not None:
        if not database_replay:
            raise GoldenError("public config chỉ dùng với database replay")
        public_config = json.loads(Path(public_config_file).read_text(encoding="utf-8-sig"))
        from tools.golden_db_replay import PUBLIC
        if not isinstance(public_config, dict) or any(k not in PUBLIC and not k.startswith("FEATURE_") for k in public_config):
            raise GoldenError("Config ngoài danh sách public")
        _safe(public_config)
    flag_input = json.loads(Path(flags_file).read_text(encoding="utf-8-sig"))
    baseline = isinstance(flag_input, dict) and "baseline_flags" in flag_input      # C-GOLDEN2 (b): cờ sản xuất lúc chụp
    structured = isinstance(flag_input, dict) and ("flags" in flag_input or baseline)
    flags = flag_input.get("baseline_flags" if baseline else "flags") if structured else flag_input
    if not isinstance(flags, dict) or not all(isinstance(k, str) and type(v) is bool for k, v in flags.items()):
        raise GoldenError("flags phải là JSON object tên cờ → boolean (không đọc môi trường)")
    experimental = flag_input.get("experimental_flags") if structured else list(flags)
    if (not isinstance(experimental, list) or not all(isinstance(k, str) and k in flags for k in experimental)
            or len(set(experimental)) != len(experimental)):
        raise GoldenError("experimental_flags cần list tên cờ duy nhất có trong flags")
    if purpose == "compat" and any(flags[k] for k in experimental):
        raise GoldenError("COMPAT yêu cầu các cờ thử nghiệm khai trong file đều TẮT")
    if purpose == "compat":
        if baseline:
            validate_baseline_flags(flags, experimental)
        else:
            validate_compat_flags(flags)
    inputs = {}
    if input_snapshots_file is not None:
        inputs = json.loads(Path(input_snapshots_file).read_text(encoding="utf-8-sig"))
        if not isinstance(inputs, dict):
            raise GoldenError("input snapshots cần object job id → snapshot trước lắp gói")
        _safe(inputs)
    warnings, jobs = [], []
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")  # Một snapshot đọc nhất quán cho mọi SELECT.
        schema = {key: conn.execute(f"PRAGMA {key}").fetchone()[0] for key in ("user_version", "schema_version")}
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        required = {"id", "project_id", "scene_id", "type", "state", "model", "quality_tier", "sent_package"}
        missing = required - columns
        if missing:
            raise GoldenError("jobs thiếu trường: " + ", ".join(sorted(missing)))
        running = conn.execute("SELECT count(*) FROM jobs WHERE project_id=? AND state IN ('queued','running','retryable')", (project,)).fetchone()[0]
        if running:
            warnings.append("Dự án có job đang chạy; nên dùng snapshot CSDL + ref nhất quán trước khi chụp")
        rows = conn.execute("SELECT * FROM jobs WHERE project_id=? AND scene_id=? AND type IN ('image_gen','video_gen') ORDER BY id", (project, shot)).fetchall()
        if not rows:
            raise GoldenError("Không có jobs ảnh/video cho project + shot chỉ định")
        if latest_per_type:
            rows=list({row['type']:row for row in rows}.values())
        for row in rows:
            selected_id = row["id"]
            if latest_per_type:
                visited = set()
                chain = [row["id"]]
                while True:
                    try:
                        try:
                            candidate = json.loads(row["sent_package"])
                        except (TypeError, ValueError):
                            candidate = None
                        _safe(candidate)
                        if isinstance(candidate, dict) and isinstance(candidate.get("prompt"), str) and candidate["prompt"]:
                            break
                        visited.add(row["id"])
                        # C-GOLDEN2 (a): bản final video (submit_final_from_sample, prompt rỗng) có source_job_id = job ẢNH; bản nháp
                        # video được nâng nằm ở draft_job_id → đi theo draft_job_id; ảnh / chưa có draft → source_job_id như cũ
                        draft_id = row["draft_job_id"] if "draft_job_id" in columns and row["type"] == "video_gen" else None
                        source_id = draft_id if type(draft_id) is int else (row["source_job_id"] if "source_job_id" in columns else None)
                        if type(source_id) is not int:
                            raise GoldenError(f"job {row['id']}: không có draft_job_id / source_job_id kiểu số (gói không có prompt)")
                        if source_id in visited:
                            raise GoldenError(f"job {row['id']}: vòng lặp về job {source_id}")
                        parent = conn.execute("SELECT * FROM jobs WHERE id=? AND project_id=? AND scene_id=? AND type=?",
                                              (source_id, project, shot, row["type"])).fetchone()
                        if parent is None:
                            other = conn.execute("SELECT type, project_id, scene_id FROM jobs WHERE id=?", (source_id,)).fetchone()
                            what = ("không tồn tại" if other is None else
                                    f"là {other['type']} của dự án {other['project_id']} shot {other['scene_id']}")
                            raise GoldenError(f"job {row['id']} → nguồn {source_id} {what} (cần {row['type']} cùng dự án/shot)")
                        row = parent
                        chain.append(row["id"])
                    except (GoldenError, TypeError, ValueError) as broken:
                        # C-GOLDEN4: in chuỗi id bị đứt + chỗ đứt (chỉ id/kiểu, không prompt/gói)
                        jobs.append({"id": selected_id, "type": row["type"], "selected_job_id": selected_id,
                                     "database_replay": {"status": "INSUFFICIENT_INPUT", "matched_at_capture": False,
                                                         "reason": "chuỗi source_job_id thiếu/hỏng hoặc không an toàn",
                                                         "chain": chain, "broken": str(broken)[:300]}})
                        row = None
                        break
                if row is None:
                    continue
            try:
                raw = row["sent_package"]
                try:
                    package = json.loads(raw)
                except (TypeError, ValueError):
                    raise GoldenError(f"job {row['id']}: thiếu/hỏng sent_package") from None
                if not isinstance(package, dict):
                    raise GoldenError(f"job {row['id']}: sent_package cần object")
                for name in ("v", "prompt", "provider", "model", "refs"):
                    if name not in package:
                        raise GoldenError(f"job {row['id']}: sent_package thiếu {name}")
                if not isinstance(package["refs"], list):
                    raise GoldenError("refs cần list giữ nguyên thứ tự")
                if not isinstance(package["prompt"], str) or not package["provider"] or not package["model"]:
                    raise GoldenError("prompt/provider/model thiếu giá trị")
                _safe(package)
                refs = [_ref(ref, root) for ref in package["refs"]]
            except GoldenError:
                if not latest_per_type:
                    raise
                jobs.append({"id": selected_id, "type": row["type"], "selected_job_id": selected_id,
                             "database_replay": {"status": "INSUFFICIENT_INPUT", "matched_at_capture": False,
                                                 "reason": "gói lịch sử thiếu/hỏng hoặc không an toàn"}})
                continue
            for index, ref in enumerate(refs):
                if ref["hash_status"] != "match":
                    warnings.append(f"job {row['id']} refs[{index}]: {ref['hash_status']}")
            if row["quality_tier"] is None:
                warnings.append(f"job {row['id']}: thiếu quality_tier (NULL), không suy đoán")
            jobs.append({"id": row["id"], "selected_job_id": selected_id, "type": row["type"], "state": row["state"], "model": row["model"],
                         "tier": row["quality_tier"], "provider": package["provider"], "prompt": package["prompt"],
                         "sent_package_raw": raw, "sent_package_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "refs": refs, "input_snapshot": inputs.get(str(row["id"]))})
    if database_replay:
        from tools.golden_db_replay import capture_database_job
        for job in jobs:
            if "sent_package_raw" not in job:
                continue
            try:
                job["database_replay"] = capture_database_job(job,db=db,ref_root=root,flags=flags,public_config=public_config,
                                                              experimental=experimental if baseline else None)
            except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
                # C-GOLDEN8-FIN (HANDOFF việc mở a): cùng cách báo lỗi với worker (loại thao tác + tệp:dòng); KHÔNG mang trạng thái
                # worker (`loaded`) — đây là tiến trình cha. DataChanged ở đây không có `paths` → replay_fixture coi là INSUFFICIENT như cũ.
                from tools.golden_db_replay import _failure_answer
                answer = _failure_answer(exc)
                job["database_replay"] = {"status": answer["status"], "matched_at_capture": False,
                                          "reason": "không dựng được ca; tiếp tục các ca khác",
                                          **({"diagnostic": answer["diagnostic"]} if "diagnostic" in answer else {})}
    return {"fixture_version": 1, "purpose": purpose, "head_sha": head_sha(), "flags": flags,
            "experimental_flags": experimental, "flags_mode": "baseline" if baseline else "all_unverified_off",
            "flags_provenance": "baseline_production_at_capture" if baseline else "explicit_file_unverified_at_send", "schema": schema, "project": project, "scene_id": shot,
            "jobs": jobs, "warnings": warnings, "replay_status": "CAPTURED_NOT_ACCEPTED" if database_replay else "OPEN", "correctness_status": "OPEN"}


def _utf8_console():
    """C-GOLDEN2 (f): bảng điều khiển Windows cp1252 + chữ Việt trong --help → UnicodeEncodeError khi thiếu PYTHONUTF8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    _utf8_console()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("db", "flags-file", "ref-root", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("project", "shot"):
        parser.add_argument("--" + name, required=True, type=int)
    parser.add_argument("--purpose", required=True, choices=("compat", "correctness"))
    parser.add_argument("--input-snapshots-file", type=Path, help="JSON job id → args/kwargs trước lắp gói; không suy ngược từ sent_package")
    parser.add_argument("--database-replay", action="store_true", help="Chụp dependency và dựng gói bằng prepare/build thật từ DB, không cần sidecar")
    parser.add_argument("--latest-per-type", action="store_true", help="Chỉ job cuối ảnh và video của shot; không chọn nhiều take cũ")
    parser.add_argument("--public-config-file", type=Path, help="JSON config public explicit (LLM_PROVIDER, image_model, video_model, FEATURE_*); không đọc môi trường")
    args = parser.parse_args(argv)
    try:
        result = capture(db=args.db, project=args.project, shot=args.shot, flags_file=args.flags_file,
                         ref_root=args.ref_root, purpose=args.purpose, input_snapshots_file=args.input_snapshots_file, database_replay=args.database_replay, latest_per_type=args.latest_per_type, public_config_file=args.public_config_file)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    except GoldenError as exc:
        parser.exit(2, str(exc) + "\n")
    except (OSError, ValueError, sqlite3.Error):
        # CLI không xuất exception chứa nội dung JSON/đường dẫn nhạy cảm.
        parser.exit(2, "Chụp thất bại: kiểm schema, trường bắt buộc, flags và đầu ra chưa tồn tại; dùng API để xem mã lỗi đã lược bỏ.\n")
    return 0


def replay_builder(snapshot, *, ref_root):
    """API: tiến trình riêng, không thay cwd hoặc environ của tiến trình gọi."""
    import tempfile
    _safe(snapshot)
    python = Path(sys.executable)
    if (sys.version_info[:2] != (3, 14) or not python.is_absolute()
            or python.name.lower() not in {"python.exe", "python", "python3", "python3.14"}
            or not python.is_file()):
        raise GoldenError("Replay cần native Python trong whitelist")
    with tempfile.TemporaryDirectory(prefix="golden-worker-") as scratch:
        request = Path(scratch) / "request.json"
        response = Path(scratch) / "response.json"
        request.write_text(json.dumps({"snapshot": snapshot, "root": str(Path(ref_root).resolve())}), encoding="utf-8")
        env = {"SYSTEMROOT": "C:/Windows", "TEMP": scratch, "TMP": scratch,
               "HOME": scratch, "USERPROFILE": scratch, "PYTHONUTF8": "1"}
        result = subprocess.run([str(python), "-I", str(Path(__file__).resolve()), "--isolated-builder", str(request), str(response)],
                                cwd=scratch, env=env, capture_output=True, timeout=90)
        if result.returncode or not response.is_file():
            raise GoldenError("Replay worker không hoàn tất; không xuất log chứa payload")
        answer = json.loads(response.read_text(encoding="utf-8"))
        if "error" in answer:
            raise GoldenError(answer["error"])
        return answer["raw"].encode("utf-8")


def _replay_builder_sandbox(snapshot, *, ref_root):
    """Replay biên lắp sổ gửi từ input trước lắp gói; không chạy prepare/send/poll.

    Snapshot độc lập chứa args/kwargs/meta, bytes ref nằm trong ref_root; baseline
    chỉ dùng ở comparator bên ngoài, không bao giờ làm đầu vào builder.
    """
    import datetime
    import os
    import socket
    from unittest.mock import patch
    required = {"kind", "args", "kwargs", "sent_kwargs", "job", "meta", "external_id", "at", "provider", "files", "flags"}
    if not isinstance(snapshot, dict) or required - snapshot.keys():
        raise GoldenError("snapshot thiếu trường bắt buộc trước lắp gói")
    _safe(snapshot)
    if snapshot["kind"] not in ("image", "video") or snapshot["provider"] not in ("fake", "clipai", "deepix"):
        raise GoldenError("Replay cần tên provider trong whitelist và loại image/video")
    if not isinstance(snapshot["flags"], dict) or any(type(v) is not bool for v in snapshot["flags"].values()) or any(snapshot["flags"].get(k) is not False for k in snapshot.get("experimental_flags", snapshot["flags"])):
        raise GoldenError("COMPAT replay cần cờ TẮT explicit")
    validate_compat_flags(snapshot["flags"])
    root = Path(ref_root).resolve()
    for name, digest in snapshot["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise GoldenError("snapshot ref thiếu/sai hash/ngoài phạm vi")
    # Mọi đường dẫn ref trong input phải được đóng băng và kiểm hash trước đọc.
    from_names = {"image_path", "references", "image_references", "reference_video", "last_frame", "reference_only", "reference_audio"}
    def check_ref(item):
        if isinstance(item, list):
            for value in item:
                check_ref(value)
        else:
            name = item.get("path") or item.get("file") or item.get("url") if isinstance(item, dict) else item
            if name and name not in snapshot["files"]:
                raise GoldenError("snapshot ref chưa đóng băng")
    args = snapshot["args"]
    if snapshot["kind"] == "image" and len(args) > 1:
        check_ref(args[1])
    if snapshot["kind"] == "video" and args:
        check_ref(args[0])
    if snapshot["kind"] == "video":
        for index in (7, 8):
            if len(args) > index:
                check_ref(args[index])
    for mapping in (snapshot["kwargs"], snapshot["sent_kwargs"]):
        for key in from_names & mapping.keys():
            check_ref(mapping[key])
        if mapping.get("_from_sample"):
            raise GoldenError("snapshot nâng nháp cần snapshot CSDL riêng; chưa hỗ trợ")
    moment = datetime.datetime.fromisoformat(snapshot["at"])
    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return moment
    def forbidden(*args, **kwargs):
        raise GoldenError("Replay cấm mạng/provider/subprocess")
    class FakeProvider:
        name = snapshot["provider"]
        submit = staticmethod(forbidden)
        submit_final_from_sample = staticmethod(forbidden)
    # Thay object env trước import ứng dụng; không khởi tạo registry/credential/client.
    with patch.object(os, "environ", {}), patch.object(socket, "socket", forbidden), patch.object(socket, "create_connection", forbidden), patch.object(subprocess, "Popen", forbidden):
        from core import runner, sent_package, features
        cls = runner.ImageRunner if snapshot["kind"] == "image" else runner.VideoRunner
        instance = object.__new__(cls)
        instance.provider = FakeProvider()
        instance._sent = {snapshot["job"]["id"]: snapshot["meta"]}
        instance._pregen_fingerprints = {snapshot["job"]["id"]: snapshot.get("pregen_fingerprint")}
        previous = Path.cwd()
        try:
            os.chdir(root)
            with patch.object(features, "on", side_effect=lambda name: snapshot["flags"].get(name, False)), patch.object(features, "active", side_effect=lambda name: snapshot["flags"].get(name, False)), patch.object(sent_package, "ROOT", str(root)), patch.object(sent_package.datetime, "datetime", FrozenDateTime):
                raw, warnings = instance._build_package(snapshot["job"], args, snapshot["kwargs"], snapshot["sent_kwargs"], snapshot["external_id"])
        finally:
            os.chdir(previous)
    if raw is None or warnings:
        raise GoldenError("Replay builder thiếu input hoặc không lắp được gói")
    return raw.encode("utf-8")


def check_correctness(actual, expectations):
    """Tiêu chí do người viết ca khai riêng; COMPAT xanh không suy ra đúng."""
    body = json.loads(actual)
    failures = []
    if any(text not in (body.get("prompt") or "") for text in expectations.get("prompt_contains", [])):
        failures.append("prompt_contains")
    if "ref_roles" in expectations and [r["role"] for r in body["refs"]] != expectations["ref_roles"]:
        failures.append("ref_roles")
    return failures


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "--isolated-builder":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        request = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        try:
            answer = {"raw": _replay_builder_sandbox(request["snapshot"], ref_root=request["root"]).decode("utf-8")}
        except GoldenError as exc:
            answer = {"error": str(exc)}
        except Exception:
            answer = {"error": "Replay worker thiếu đầu vào; không đủ bằng chứng"}
        Path(sys.argv[3]).write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
    else:
        raise SystemExit(main())
